# Session: TEN-06 code and the Fe material folder

- Session ID / UTC date: 2026-11-13
- Agent or human / platform: Claude (Opus 5.5) in Claude Code, WSL
- Task ID and scope: TEN-06, the code part only: the centrosymmetric null (decision 13), the total moment for D_sw (decision 7), and the material folder. No VASP job, no evidence record, no Gate 2 evaluation.
- Branch: `ten-06-fe-pilot`
- Base commit at session start: `e514eed` (`main`, PR #20 merge)
- Working-tree changes already present:
  - an uncommitted user edit to `STATUS.md` that dropped the "rebuild the math PDF" line, carried onto this branch by stash;
  - untracked `Claude outputs/` and `materials/fe/{INCAR,KPOINTS,POSCAR,job.sh}`, plus the ignored `POTCAR`.
- Related spec / prior session: `plans/ten-06-fe-pilot.md` (approved 2026-11-13); [SIM-1b](2026-11-11_2255Z-agent-sim-1b-incar-fit.md)
- Status: complete

## Work performed

**Centrosymmetric null.**
- `gates.gate_null` runs inside `check_tree`, on the per-ion traces that `check_tree` already computes, so the files are not read a second time.
- `tensors.tree_symmetry` builds the kept operations once, before the checks. It sets `inversion` when a rotation equals -I, and `observables` reuses its result.
- The check is recorded under `checks.Null` in `traces.json` and as `null` in `tensors.json`. A failure adds `Null (<run, ion, axis, value>)` to the failures, so `fit` exits 1 and the refusal record names it.

**Total moment.**
- `spiral.read_static` returns `mag` from the last OSZICAR line matching `<n> F=`, or None when that line has no `mag=`.
- `read_run` stores `M_total = |mag| / N_m` for q0 only. A spiral's cell moment says nothing about D_sw.
- `tensors.report_tree` writes `D_sw.M_int` and `D_sw.M_total`. Each has its value, sigma, `M_muB` and a sentence on the moment it uses. Without `mag=`, `M_total` is reported as not evaluated.

**Fix found on the way.** `prepare` failed on a p_D = 0 material: `plan.json` cannot hold the D rank value `inf`, and `manifest.save` refuses NaN and infinity. `spiral.rank_value` now returns None for a design with no tensor columns, and `spiral.undetermined` is the one comparison against `RANK_FLOOR`. `plan` prints "-". This would have stopped the pilot's first `dmi prepare`.

**Tests (15, unchanged in number).**
- `test_readback`: the fixture's `F=` line carries `mag=` in VASP's format. q0 gets an earlier `F=` line with a different `mag=`, and the test asserts `M_total = 0.25` from the last line, and None away from q0.
- `test_command_chain` (BFO, R3c): both D_sw values are None for an antiferromagnet, and the null is "not applicable".
- `test_energies_only_tree` became `test_bcc_fe_pilot_tree`, on the 2-site bcc cell with one direction and `t = 0.05, 0.10, 0.15`. It checks:
  - the plan's first two lines;
  - the energies-only fit: A, both D_sw values with the fixture's 1.1 x interstitial factor, and the null not evaluated;
  - after `dmi dumps` with zero COCC, the null passes with threshold 5e-5;
  - one run's COCC set to give |T_y| = 1e-4 eV on ion 2 makes `fit` exit 1, naming `d1_t2_minus`, ion 2.

**Material folder.**
- POSCAR, INCAR and KPOINTS are committed byte for byte.
- `POTCAR.spec` was written from the local POTCAR. `.gitignore` already allows it, as the spec says.
- `seed.toml` has `t = [0.05, 0.10, 0.15]` and an updated comment, and nothing else changed.
- `job.sh` is untracked: it holds an account name and cluster paths (D-016).

**Documents.**
- `plans/ten-06-fe-pilot.md`: the status paragraph only.
- STATUS:
  - TEN-06 approved, its code in review, the runs waiting on the user;
  - the cluster steps;
  - the PDF line removed: per the user, it was compiled on 2026-11-12, 20 pages, no errors, no equation number moved;
  - two superseded paragraphs removed: the standalone LDUMPCOCC check, now fact 1 of the pilot, and the old λ = 1 recipe note.
- Also updated: CHANGELOG, `docs/seed_file.md` (what `fit` reports) and the `gates.py` row of the module map.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `cd "pipeline v3" && .venv/bin/python -m pytest -q` at `e514eed` | PASS, 15 | Baseline |
| Same on this branch | PASS, 15 | Software only |
| Fault injections, each reverted | 6 of 6 caught: null always passes; inversion never detected; inversion always assumed; `mag=` ignored; M_total not per site; first `F=` line instead of the last (caught after the readback test gained an earlier `F=` line) | Scratch edits |
| `read_static` on `vasp files/sample-files/Fe_q0_test/q0` (untracked) | `mag = (4.2885, 0.0000, 0.0000)`; M_int rows (2.131, 0, 0) twice; `M_total = 2.144` μB per site against M_int 2.131 | Real VASP OSZICAR, a q = 0 FM state with ISPIN = 2 in its INCAR. The test fixture follows its format |
| `python -m dmi_pipeline plan materials/fe/seed.toml` | exit 0; first two lines as the spec gives; ENCUT 550, ISMEAR 0, SIGMA 0.05; one MAGMOM override line; rank D -, A 1.000, D_free 1.000; (001), (010), (100); 19 runs | Committed inputs |
| `python -m dmi_pipeline prepare materials/fe/seed.toml --job <scratch job> --out <scratch>` | 19 runs written; `plan.json` D rank null | Scratch; the user's `job.sh` was not used |
| `python -m pyflakes dmi_pipeline tests` | No findings | |

Not run: any VASP job.

## Decisions or deviations

No DECISIONS entry. Notes for the user:

- **Spec statements that no longer match the code.** Line 6 says D-019 is "pending on `incar-user-settings`", which is merged. The "Factual notes" say `plan` requires ENCUT and ENINI, which is no longer true under D-022. "Code in this task" names `test_fit_command`, which is now `test_command_chain`. Only the status paragraph was edited, as instructed.
- **The committed KPOINTS is 5 x 5 x 5.** The convergence plan starts its k series at 12. This is a factual note, and the file is yours (D-019).
- **ISPIN = 2 and ICHARG = 2 in the user's INCAR.** They are passed through, and VASP ignores ISPIN in a noncollinear run. This is a factual note only.
- **The null threshold is the plain N0 floor**, as the spec says, without the N0 gate's optional 3 sigma term.

## Handoff

- Completed work: the TEN-06 code and the material folder.
- Remaining work / blockers: the Perlmutter runs (STATUS "Immediate next action"), then the evidence record and the Gate 2 evaluation.
- Next concrete command or action: review and merge `ten-06-fe-pilot`.
- Files another session should read: `plans/ten-06-fe-pilot.md`, `STATUS.md`.
- Last tested commit, if available: the commit carrying this log.
- Uncommitted/unpushed work and where it exists: `materials/fe/job.sh` and `Claude outputs/` stay untracked by design.
