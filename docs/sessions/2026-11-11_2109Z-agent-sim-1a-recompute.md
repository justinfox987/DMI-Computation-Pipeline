# Session: SIM-1a, recompute from the VASP files (D-021)

- Session ID / UTC date: 2026-11-11, 21:09Z
- Agent or human / platform: Claude (Opus 5.5) in Claude Code, WSL
- Task ID and scope: SIM-1a, `plans/simplify-1.md` items 2.2, 2.3, 2.4 and 2.6 under D-021. The D-022 INCAR handling, the D-023 fit, the `exchange_grid`/`rmax` keys and the Slurm array writer are left unchanged.
- Branch: `sim-1a-recompute`
- Base commit at session start: `27bfe86` (`main`, PR #18 merge)
- Working-tree changes already present: untracked `Claude outputs/` and `materials/fe/{INCAR,KPOINTS,POSCAR,job.sh}`; left alone and not added.
- Related spec / prior session: `plans/simplify-1.md`; [FIX-1](2026-11-11_1946Z-agent-fix-1-trace-sign.md)
- Status: complete

## Work performed

Package `pipeline v3/dmi_pipeline/`, 2,537 -> 1,590 lines:

- **Commands.** The commands are `plan`, `prepare`, `collect`, `dumps` and `fit`; the `trace` command is gone.
  - `spiral.read_runs` reads every run's OUTCAR and OSZICAR and applies the Section 11 state checks.
  - `collect` writes the result as `collected.json`, a report.
  - `dumps` and `fit` call `read_runs` themselves.
  - `fit` calls `gates.check_tree`, which loads `dump_C/CSO.dat` and every `dump_P/COCC.dat` and applies C0, N0, I0, P0 and E0. It writes `traces.json` as a report and refuses the fit if a check fails.
- **Removed guards and bookkeeping:**
  - the SHA-256 records and `spiral.unchanged`;
  - `parent.json`, `_stat` and `parent_unchanged`;
  - `provenance.json`, `gates.finish`, `manifest.require_done` and `manifest.check_files`;
  - the INCAR-against-`config.json` comparison in `read_run`;
  - `realized.echo_check`;
  - the rebuilt-symmetry comparison and the per-run sites and lattice re-checks in `tensors.observables`;
  - `FileProvenance` and the atomic write in `manifest.save`;
  - the input hashes in `plan.json`.

  `manifest.file_hash` stays for one use: the job-script hash that the Slurm array writer quotes, and that writer is out of scope.
- **New guard** (`trace.trace_run`): a `dump_P/COCC.dat` older than its run's OUTCAR is reported as an error for that run.
- **M1** moved out of the package into `acceptance/m1.py`, 132 lines, run as `python acceptance/m1.py DUMP_P_DIR`.
  - It reads CPROJ with a fixed little-endian i4/f8 layout and fails loudly on a wrong magic string or record size.
  - It requires each (k, band) record exactly once and cross-checks FERWE against the CPROJ records.
  - It reuses the package's `load_cocc`.

  `dumpio.py` keeps only `load_cso` and `load_cocc`: 809 -> 199 lines. `conventions.UNDETERMINED`, `VASP_BUILD_ID` and `DUMP_FORMAT_VERSION` are deleted, and `COCC_SPIN_BLOCKS` moved into `m1.py`. `dmi dumps` no longer sets `LDUMPCPROJ`, and q0's `dump_P` is like any other.
- **T3 replaced by handedness.**
  - `dmi dumps` writes `dump_C` only, with `SAXIS = 0 0 1` in its deck.
  - `gate_c0` requires h < 0 on every ion and reports `handedness_per_ion`.
  - `gate_t3`, the `T_y` strings, `y_flip_visible`, `F_flipped_norm` and `FLIP` are deleted.
  - `load_cso` now accepts only SAXIS = z.
  - The `tensors.json` sign entry reads "follows VASP's SOC energy (D-020); not yet confirmed by a VASP run".
- **OSZICAR reader.** `spiral.read_static` replaces `sphere` and `check_run`. It requires "aborting loop because EDIFF is reached" and the timing footer, takes the last `ion MW_int M_int` block with one row per ion, and takes the last free energy TOTEN. Every `collect` state check is kept: collapsed moment, pair phase, `|M_z|`, drift against q0, and `|delta| < 1°` when `n_twist = 0`.

Tests, 22 -> 14 (1,120 -> 973 lines):

- **Deleted**, because they only guarded removed code or tested the CPROJ oracle:
  - `test_assembly_does_not_depend_on_the_rank_grid` and `test_duplicate_record_is_rejected`, now part of the M1 test;
  - `test_cproj_trace_matches_density_oracle` and `test_spin_swap_sign_origin_phase_and_flip_independence`, which tested the oracle itself;
  - `test_collinear_null_and_same_capture_checks`, `test_m1_observes_off_diagonal_order_and_corruption` and `test_trace_vector_and_t3`, whose N0 and I0 parts moved to `test_parity_checks`;
  - `test_dumps_provenance_and_trace` and `test_fit_command`, merged into `test_command_chain`.
- **New:**
  - `test_m1_script`: passes on a smeared 2 x 2 rank grid by subprocess, and fails on exchanged COCC flip blocks and on a repeated record;
  - `test_cso_and_cocc_readers`;
  - `test_command_chain`: `prepare`, `collect`, `dumps` and `fit` on a BFO tree whose OUTCARs and COCC files carry spin-model values, plus the COCC-older-than-OUTCAR error, the exchanged-flip-block C0 failure and the rank refusal.
- **Changed:** `test_c0_rejects_operator_defects` gains the exchanged-flip-block case. `test_readback` covers the new reader: the last block is taken, missing EDIFF, missing footer, and an incomplete block.
- **Unchanged:** the FIX-1 layout test, the three symmetry tests and `test_fits_recover_spin_model_tensors`.
- **Edited although the brief said unchanged:** `test_predictions` lost its `FLIP` and `y_flip_visible` assertions, because those functions are deleted. The remaining assertions are unchanged.
- The `cproj_trace` oracle is gone from `tests/fixtures.py`.

Documents: `plans/simplify-1.md` (status line and order of work), `docs/seed_file.md` and `README.md` (commands, one CSO dump), the `heide_math_v3.md` module map, STATUS (SIM-1 split into SIM-1a and SIM-1b), CHANGELOG.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `cd "pipeline v3" && .venv/bin/python -m pytest -q` at `27bfe86` | PASS, 22 passed | Baseline |
| Same on this branch | PASS, 14 passed | Software only |
| Item 5: `tensors.json` of `test_fit_command` at `27bfe86` against `test_command_chain` here | Max absolute difference, meV units: D 5.6e-17, A 0, F 5.0e-16, D_free 5.0e-16, pitch 0 nm (258.07358254273583 both) | Same synthetic BFO tree; the new tree's energies and traces come from OUTCAR and COCC files |
| Fault injections, each reverted | All 8 caught: handedness off; COCC-age guard off; first sphere block; `LDUMPCPROJ` back on q0; conjugate dropped; footer check off; conjugated CPROJ in M1; a minus run reading its plus trace | Scratch edits |
| `load_cso`, `load_cocc`, `gate_c0`, trace on `noq/dump-C/CSO.dat` + `noq/dump-P0/COCC.dat` | C0 pass; h = -0.523 (Fe x2), -0.440 (Bi x2), -0.707 (O x6); total T = (+2.149e-8, +4.346e-8, +5.188e-8) eV; N0 and I0 pass | Real BFO q = 0 dumps, gitignored, not committed |
| `python acceptance/m1.py "pipeline v3/noq/dump-P0"` | PASS, 5.329e-15 at (IS, ION, I, J) = (3, 2, 2, 2); the old `gate_m1` gave the same value and location | 16 rank files, 512 k, 152 bands; little-endian i4 |
| Old `sphere` vs new `read_static` on `vasp files/sample-files/Fe_q0_test/q0` and `reader_test_2` | `M_int` identical bit for bit; E identical (-16.55294258, -16.38086575) | `reader_test_2` is a lambda = 1 run, which the new reader no longer detects |
| `python -m pyflakes dmi_pipeline tests ../acceptance/m1.py` | No findings | pyflakes was installed into the local `.venv` for this check |

Not run: any VASP job.

## Decisions or deviations

None new; this implements D-021. Choices made within it:

- **Guard comparison.** The guard reports a COCC strictly older than its OUTCAR. Equal timestamps pass, so a coarse filesystem clock cannot fail a fresh dump.
- **C0 failure.** When C0 fails, `fit` still traces every run for the report and then refuses.
- **The parameter check stays.** The check that `plan.json` and q0's `config.json` agree on the number of sites stays, because both files are inputs written by `prepare`. It has no test.
- **`plan.json` hashes.** They were only a record and nothing read them, so they went with the SHA-256 bookkeeping.

## Handoff

- Completed work: SIM-1a.
- Remaining work / blockers: SIM-1b (D-022, D-023, the D-025 seed keys), then TEN-06.
- Next concrete command or action: review and merge `sim-1a-recompute`.
- Files another session should read: `plans/simplify-1.md` items 2.5, 2.7 and 2.9; `STATUS.md`.
- Last tested commit, if available: the commit carrying this log.
- Uncommitted/unpushed work and where it exists: see the final response of this session.
