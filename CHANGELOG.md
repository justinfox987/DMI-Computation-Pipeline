# Changelog

Record meaningful delivered changes, newest first. Include a session log or
commit reference when available. Do not use this as a command transcript.

## Unreleased

- SIGN-1: TEN-07b is done and D-020's sign is confirmed. On BFO, the pipeline pair at q_frac = (1/4, 0, 0) gives y_x = [T_x(q) - T_x(-q)] / 2 = +1.266 meV per Fe; the self-consistent SOC supercell gives (E_plus - E_minus) / 8 = +1.2659 meV per Fe. The supercell README and `plans/ten-07b-supercell.md` gain the traces and the verdict, with its limits (one q and one axis; on-site SOC in both; 700 against an effective 600 eV). D-020 is amended. The math gains one sentence in Section 9.2 and one in Section 11, and an amendment note dated 24 November 2026; `heide_math_v3.md` one sentence. `dmi fit` now prints the sign as "follows VASP's SOC energy (D-020); confirmed against a full-SOC supercell (TEN-07b, BFO)" (`tensors.SIGN`), and the command-chain test checks the new text. Tests stay at 15. The pair's `traces.json` and `fit.log` are referenced, not yet in the record. No VASP or cluster jobs. See the [session log](docs/sessions/2026-11-24_0034Z-agent-sign-1.md).

- REC-1 (D-029): TEN-07 Stages A to C and the TEN-07b supercell control are recorded. New `evidence/2026-11-20-bfo-ten07/` (stage folders with their JSON reports; README: settings, Stage A all checks pass with D_yx = 2.1623 meV Å, A 131.19/151.41 meV Å², pitch 76.24 nm; Stage B 9x9x9 changes |y| by -0.015%, Gate 3 passed; Stage C Fe U 4.00 changes |y| by +44.8%; Stage A KPOINTS corrected from 9 9 9 to the 8 8 8 that ran). New `evidence/2026-11-23-bfo-supercell/` and `plans/ten-07b-supercell.md` (a record; run without a prior spec): 4x1x1 supercell, E_plus - E_minus = +1.2659 meV per Fe, same sign as the Stage A tensor; the pipeline pair's y_x is a placeholder. New `materials/bfo/` (inputs as given, KPOINTS 8 8 8, `POTCAR.spec` with the LDA datasets; `dmi plan`: group 161, 6 of 6 kept, `p_D 1  p_A 2`, 31 runs). D-029 records the U sensitivity as a finding. The TEN-07 spec records what was run. STATUS updated: Gate 3 passed, three stale unresolved items and the two diagnostic to-confirm notes removed, the parity-sigma understatement added. Safety: `evidence/BFO-initial-tree/` deleted (it duplicated stageA and had held a POTCAR); `.gitignore` keeps ignoring `POTCAR*` and now lets `POTCAR.info` be tracked. Docs and data only; no code, tests unchanged. No VASP or cluster jobs. See the [session log](docs/sessions/2026-11-24_0021Z-agent-rec-1.md).

- PACK-1: `dmi prepare` and `dmi dumps` take `--slots N` (and `--max-time`), and then also write `pack.sh` or `pack_dumps.sh`: one batch job that keeps N runs going at once, each `srun` step on its own `$DMI_RUN_NODES` nodes with `--exact`. The header scales `--nodes` and `--gpus` by the slots and `--time` by the rounds (`spiral.pack_header`, a pure function); the body skips finished runs with the same rule as `run.sh`, throttles with `wait -n`, prints run/skip/done/failed lines and exits 1 if any run failed (`spiral.write_pack`). A job body without `DMI_RUN_NODES` and `--exact` is refused. Without `--slots` nothing changes. `write_sequence` now shares the skip test and the list guard; its output is unchanged. Tests stay at 15 (extended: header scaling and refusals; `pack.sh` executed on a fake tree; `pack_dumps.sh` in the command chain); mutations of the slot limit and the skip are caught. Docs: `docs/seed_file.md` (the option, the job-script contract, array vs sequence vs pack, limits), [spec](plans/pack-1.md). Untested on Perlmutter. No VASP or cluster jobs. See the [session log](docs/sessions/2026-11-20_2122Z-agent-pack-1.md).

- TEN-07 approved by the user on 2026-11-19: `plans/ten-07-bfo.md` status updated, and the Gate 3 tolerance set to 5% (Stage B changes D by less than 5%). How Stages B and C are built stays open. STATUS: next actions are the LSDA+U inputs for `materials/bfo/` and Stage A. Docs only; no code, tests unchanged. No VASP or cluster jobs. See the [session log](docs/sessions/2026-11-19_2011Z-agent-ten-07-approve.md).

- BFO-EV1 (D-028): the BFO LDA+U diagnostic of 2026-11-18 is recorded in `evidence/2026-11-18-bfo-lda-diagnostic/README.md` (two directions, 7x7x7; `dmi fit` passes, including Fit A and Fit D; A 141.02, 141.02, 155.04 meV Å²; D_yx = -D_xy = 2.3446 meV Å; cycloid, pitch 75.58 nm), with what it does not establish (the sign of D, Forbidden, mesh convergence, production values) and the reviewer's literature conversions. Its JSON reports are not yet in the folder. D-027 and the Fe record now say the PBE artifact is confirmed for BFO; math Section 11's 18 November sentence and `heide_math_v3.md` likewise. M1 is covered in the Fe record: the user confirmed the 14 September build. D-028 records the user's decision: LSDA+U throughout, with the production inputs open (D-019). `plans/ten-07-bfo.md` is a draft spec for approval (Stage A three directions, Stage B mesh check of D, Stage C U sensitivity; TEN-07b the sign anchor). STATUS updated. Docs only; no code, tests unchanged. No VASP or cluster jobs. See the [session log](docs/sessions/2026-11-18_1922Z-agent-bfo-ev1.md).

- TEN-06-EV2 (D-027): the 18 November runs find the cause of the non-quadratic Fe energies. `evidence/2026-11-17-fe-ten06-pilot/README.md` gains "18 November: the cause": Fe PBE at 10x10x10 (Fit A fails), an Fe LDA control at the same settings (Fit A passes, A = 182.5 meV Å², not final) and a BFO PBE+U two-direction scan (Fit A fails: not a metal effect), with the reviewer's `c t + A t^2` fits, the locally collinear GGA mechanism (the reviewer's inference, confirmed for Fe only), literature pointers and two side findings. The open question, the verdict (no longer "investigation closed"), the diagnostics table (a functional row) and the implication for other materials are revised. D-027 records the finding and lists the three functional options without choosing (the user's decision, D-019). Math Revision 3.2 is amended 18 November 2026 with an unnumbered warning in Section 11 and a line in the revision note; `heide_math_v3.md` gains one rule. STATUS and the TEN-06 spec status line are updated. Docs only; no code, tests unchanged. No VASP or cluster jobs. See the [session log](docs/sessions/2026-11-18_1648Z-agent-ten-06-ev2.md).

- TEN-06-EV: the bcc Fe pilot evidence record is complete and TEN-06 is closed. `evidence/2026-11-17-fe-ten06-pilot/README.md` gains "Diagnostics after Gate 2": one table of every hypothesis tested (k mesh to 18x18x18, PREC Accurate, spiral cutoffs, a jump at q = 0, empty bands, smearing width and scheme) and two seven-point t scans at 8x8x8 with the reviewer's model comparison. Also an "Open question" (g/t^2 rises without levelling off as t falls; cause not identified), the final verdict (Gate 2 machinery passes; A for Fe is non-quadratic, not understood, not usable; Fe closed by the user's decision; next TEN-07) and the implication for the metals in TEN-08 and TEN-09. The 24x24x24 result is recorded as not supplied. Every number is user-reported or the reviewer's hand calculation. The TEN-06 spec's status line and STATUS are updated. Docs only; no code, tests unchanged. No VASP or cluster jobs. See the [session log](docs/sessions/2026-11-18_0033Z-agent-ten-06-evidence.md).

- FIT-1 (D-026), with the TEN-06 evidence record.
  - **Fit check.** Every tensor solve (`A` always; `D` and `D_free` when traced) now checks its residual: each row within `3 sigma + 0.01 max|data|`, with that solve's parity sigma and the Forbidden floor (`gates.gate_fit`, applied in `tensors.tensor_fit`). A failure names the worst pair (and axis for D), keeps the tensor in the report, sets `passed` false and makes `dmi fit` exit 1. An exactly determined solve is "not evaluated", never a pass. `tensors.json` gains `fit_check` with each solve's residual vector; `fit` prints one `Fit` line per solve.
  - **Why.** On the Fe pilot at 12x12x12, `fit` reported `A = 433 +- 0.04 meV A^2` while `A t^2 + b t^4` missed t = 0.05 by 0.26 meV (about 1000 sigma_g). The parity sigma does not see model error.
  - **Math.** Revision 3.2 amended 17 November 2026: the Fit check in Section 11 (unnumbered display) and one sentence in Section 9.4. D-026.
  - **Tests.** Still 15: the spin-model test asserts the check passes; the Fe pilot test runs the real fe-k12 energies (Fit A fails at d1_t1, exit 1) and an exactly determined A (not evaluated).
  - **Evidence.** `evidence/2026-11-17-fe-ten06-pilot/README.md`: the k series, the fe-k12 hand check, Gate 2 per item and the verdict, all user-reported (the JSON reports and dump files are not yet in the record), with a placeholder for the 24x24x24 diagnostic. The TEN-06 convergence plan is amended to what was run.

  No VASP or cluster jobs from this session. See the [session log](docs/sessions/2026-11-17_1855Z-agent-fit-1-model-check.md).

- FIX-2: `dmi fit` crashed in `trace.trace_run` with `TypeError` on the Fe pilot's real `dump_C/CSO.dat`, because the Patch B CSO header has no NELECT line and `trace_run` compared it with COCC's. The NELECT comparison is removed; the NIONS, LMDIM and NCDIJ checks against each other and the POSCAR stay. `tests/fixtures.write_cso` no longer writes NELECT (and takes no `nelect`), so the CSO fixtures match the real writer; COCC fixtures keep NELECT. The command-chain and bcc Fe pilot tests now run `fit` on such a CSO. Tests stay at 15. No VASP or cluster jobs. See the [session log](docs/sessions/2026-11-17_1827Z-agent-fix-2-cso-nelect.md).

- SEQ-1: `dmi prepare` also writes `run.sh`, and `dmi dumps` also writes `run_dumps.sh`. Each runs the same list as the array script, one directory at a time in one allocation (`sbatch run.sh`, or `bash run.sh` inside `salloc`). It skips a directory whose OUTCAR has the timing footer, keeps going after a failed run, and exits 1 if any run failed. The array scripts and the job.sh rules are unchanged. Limits: the time limit covers the whole sequence, a run cut off mid-SCF is redone from scratch, and one slow run delays the rest. The OUTCAR footer string is now one constant, `spiral.FINISHED`. Tests stay at 15. No VASP or cluster jobs. See the [session log](docs/sessions/2026-11-16_1921Z-agent-seq-1-run-sequence.md).

- TEN-06 code (spec approved 2026-11-13).
  - **Centrosymmetric null.** When the kept operations contain inversion, `dmi fit` requires every \|T_a\| of every traced run, ion and axis below `N0_FLOOR_EV` (`gates.gate_null`, math Sections 7.3 and 11). On a failure it exits 1 and names the worst run, ion and axis. The check is "not applicable" without inversion and "not evaluated" in an energies-only tree, and is recorded in `traces.json` and `tensors.json`.
  - **Total moment.** The static reader also returns `mag=` from OSZICAR's last `F=` line. `collect` stores `M_total = |mag| / N_m` for q0, and `fit` reports `D_sw` as `4A/M_int` and `4A/M_total` side by side, each with its sigma and the moment it uses.
  - **Fix.** `prepare` no longer fails for `p_D = 0` (bcc Fe): the D rank value of a design with no tensor columns is null, not infinity.
  - **`materials/fe/`.** The user's POSCAR, INCAR and KPOINTS are committed unchanged. `POTCAR.spec` gives `PAW_PBE Fe_pv 02Aug2007` and the SHA-256. The seed has `t = 0.05, 0.10, 0.15`. `job.sh` stays untracked.
  - **Tests.** Still 15: the energies-only test became the bcc Fe pilot test.

  No VASP or cluster jobs. See the [session log](docs/sessions/2026-11-13_1939Z-agent-ten06-fe-pilot.md).

- SIM-1b (D-022, D-023), which completes SIM-1.
  - **INCAR:** the code overrides the eleven tags it owns and prints one `override` line each. It refuses only tetrahedron smearing. The INCAR_TAGS warning, the ISMEAR allowlist, the SIGMA floor, `min_sigma`, the required ENCUT, ENINI, RWIGS, ISMEAR and SIGMA, and the KSPACING rejection are removed.
  - **Fit:** one linear solve per tensor, with cubic and quartic nuisances (math Section 9.4). Noise comes from the parity residuals, and both sigmas and their sample counts are in `tensors.json`. The rank condition is the smallest singular value of each column-normalized design, shared by `plan` and `fit`. The per-direction fits, pooled variance, MIN_PAIRS and the poorly-determined flag are removed.
  - **Fewer directions:** explicit `directions` may be fewer than three. D_free and F are then reported as not evaluated.
  - **Energies-only:** with no `dump_C`, `fit` gives A, D_sw and E0.
  - **Removed:** the `exchange_grid` and `rmax` seed keys.
  - **Follow-ups:** a refused fit overwrites `tensors.json`; a run with a nonzero printed `lambda` is an error.
  - **Results:** the tensors agree with the two-step fit to 3e-14 relative. The default BFO directions change to (1-10), (10-1), (111). Tests 14 -> 15.
  - **Your Fe INCAR:** `dmi plan` now runs on it.
  - **After review (D-023 amended):**
    - The Forbidden bound is `3 sigma + 0.01 max|D_free|` (`FORBIDDEN_FLOOR`), and `tensors.json` records `max|F| / max|D_free|`.
    - The rank test uses the tensor columns of each design, with t set aside, plus at least two distinct magnitudes per direction used. `fit` drops a direction that has fewer.
    - Math Sections 9.4 and 11 and D-023 are amended.

  No VASP or cluster jobs. See the [session log](docs/sessions/2026-11-11_2255Z-agent-sim-1b-incar-fit.md).

- SIM-1a (D-021): every command reads the VASP files again, and no derived file is an input.
  - **Commands:** `plan`, `prepare`, `collect`, `dumps` and `fit`; `dmi trace` is removed. `fit` traces every run from `dump_C/CSO.dat` and the `dump_P/COCC.dat` files and applies C0, N0, I0, P0 and E0 itself. `collected.json` and `traces.json` are reports.
  - **Guards:** the SHA-256, `parent.json`, `provenance.json`, OUTCAR-echo and INCAR-against-config guards are replaced by one: a COCC.dat older than its run's OUTCAR is an error.
  - **M1** moved to `acceptance/m1.py`, which reads a fixed little-endian layout and runs once per build. The CPROJ and FERWE readers left the package, and `dmi dumps` no longer sets `LDUMPCPROJ`.
  - **T3 removed:** `dmi dumps` writes `dump_C` only, and C0 requires handedness h < 0 on every ion. `gate_t3`, `T_y`, `y_flip_visible` and `F_flipped_norm` are removed. The `tensors.json` sign entry now says it follows VASP's SOC energy and is not yet VASP-confirmed.
  - **OSZICAR:** a lean reader takes the last `M_int` block and the last free energy of a finished static run.
  - **Size:** package 2,537 -> 1,590 lines; tests 22 -> 14.
  - **Checks:** D, A, F and the pitch agree with the previous code to 5e-16 meV on the synthetic BFO tree. On the real BFO dump, C0 passes, the trace is unchanged and M1 gives 5.3e-15.

  No VASP or cluster jobs. See the [session log](docs/sessions/2026-11-11_2109Z-agent-sim-1a-recompute.md).

- FIX-1 (D-020): `trace_vector` contracts `Lambda` with `conj(COCC_uu - COCC_dd)`, VASP's own SOC energy form, so every `T`, and therefore `D`, changes sign. The CPROJ test oracles now read `CSO.dat` as ket-first. `load_ferwe` accepts smeared occupations, including Methfessel-Paxton values outside [0, 1], and the fake dump is now smeared. New layout test (math Section 4.4) builds both files in VASP's layout from known spinors. Tests 21 -> 22; four injected faults caught. On the real BFO q = 0 dumps, C0 and N0 still pass. No VASP or cluster jobs. See the [session log](docs/sessions/2026-11-11_1946Z-agent-fix-1-trace-sign.md).

- Simplification decisions, documents only (D-020 to D-025). Math Revision 3.2: the dump files are contracted as VASP does, `Re sum Lambda * conj(COCC)`, which reverses the sign of every trace; the storage layout and a handedness check replace T3; M1 runs once per build; noise comes from the parity residuals; the smearing rule is narrowed to "no tetrahedron"; new Section 13 on anisotropy. No equation number moved. `heide_math_v3.md` now holds agent notes only. Added `plans/simplify-1.md` and `plans/anisotropy-1.md`; revised `plans/ten-06-fe-pilot.md` (20 dumps, energies-only convergence trees, no per-tree M1 or T3). README carries no status. **No code change:** the code still has the old sign and still rejects smeared FERWE files until FIX-1. See the [session log](docs/sessions/2026-11-11_1600Z-agent-simplify-decisions.md).

- D-019: the user owns each material's electronic settings and inputs. INCAR tags outside the known list no longer stop `plan`, `prepare` or the OUTCAR echo check; `plan` prints a warning instead. `KSPACING` and Section 3.2 contradictions are still rejected. Same 21 tests, extended. See the [session log](docs/sessions/2026-11-09_2100Z-agent-incar-user-settings.md).

- Cleanup 1, behavior-preserving: the CPROJ trace of Eq (4.7) moved from `trace.py` into `tests/fixtures.py`, where it is the oracle for the COCC trace; its explicit-loop copy and `TraceResult` are deleted. The OSZICAR reader returns only `M_int`, `lambda` and the step counters, with every check kept. Deleted `dumpio.read_header`, `manifest.fingerprints`, the standalone `gate` and `t3` commands (`dmi trace` runs C0, M1 and T3 through `finish`) and `gates.t3`. One `spiral.run_names` reads `runs.txt`. `__main__.py` is table-driven. pytest filters spglib's error-handling `DeprecationWarning`. The readback test now also rejects a run whose final printed `lambda` is not 0, a gap that `main` had. Package code 2741 -> 2534 lines; 21 tests. The full command chain on a synthetic BFO tree gives byte-identical outputs to `main`. See the [cleanup log](docs/sessions/2026-11-09_1930Z-agent-cleanup-1.md).

- TEN-05: added `dmi_pipeline/tensors.py` and `dmi fit DIR` (writes `tensors.json`): `y` and `g` per magnetic site (Eqs 1.3, 1.4), per-direction fits with pooled sigma (Eqs 9.1, 9.9), `D_free`, its forbidden part `F` with the Section 11 check, the constrained `D` and `A` in the TEN-02 bases with propagated covariances, element-resolved `D` by species (9.5), the Section 10.1 prediction (Gamma, `n*`, `q*`, `e*`, pitch, first-order sigma and a poorly-determined flag), `D_sw` for ferromagnets (10.2), meV and micromagnetic units (10.4), and the provisional-`T_y` report (`y_flip_visible_in_F`, `F_flipped_norm`). `fit` refuses unless `traces.json` passed, drops directions with fewer than 3 complete pairs and rechecks the rank. One hash-recheck helper, `spiral.unchanged`, replaces two inline copies. Tests 18 -> 21. No VASP or cluster jobs. See the [TEN-05 handoff](docs/sessions/2026-11-09_0300Z-agent-ten05-tensors.md).

- Math Revision 3.1 (TeX and Markdown together): an `ISMEAR`/`SIGMA` row in Section 3.2 and the Mermin free-energy statement in Section 3.3. D-018: the material INCAR must set `ISMEAR` (allowlist `-1`, `0`, `1`) and `SIGMA`; `plan` prints both and rejects other `ISMEAR` values and `SIGMA` below 0.05 eV unless the seed sets a lower `min_sigma`. AGENTS and README point at Revision 3.1. `load_seed` sorts `t` ascending, so `d{i}_t1` is the smallest `t`, where P0 and E0 gate. New optional seed key `min_sigma`. Same 18 tests, extended. No VASP or cluster jobs.

- TEN-04: added `dmi dumps` (Section 5 decks: `dump_P` under each ok run, `dump_C`/`dump_C_x`/`dump_C_y` from `q0`'s `CHGCAR` with `ISTART = 0`, `ICHARG = 11` and no `LSPIRAL` in any SOC deck; `parent.json` records parent hashes and linked-file size/mtime) and `dmi trace` (`gates.finish` writes each dump's `provenance.json` with C0, M1 or T3; `trace.split_operator`/`trace_vector` give the Eq (4.4)/(4.8) trace vector from COCC; N0 on all axes and ions, I0, P0 and E0 at 10%; `traces.json`). `collect` now applies the Section 11 SCF-and-state checks (`|delta_a| < 1°` when `n_twist = 0`, `M_a` within 5% of `q0`, `|M_z| < 0.05 μB`). T3 rewritten to the Section 11 form; deleted the Euler search, `rotate_saxis`, `cso.py`, `trace_config`, the `DONE`/`FAILED` markers and the `Bi` check in `gate_n0` (D-009 amended). Tests 15 -> 18. No VASP or cluster jobs. See the [TEN-04 handoff](docs/sessions/2026-11-08_2245Z-agent-ten04-trace.md).

- TEN-03: added `dmi_pipeline/spiral.py` with the seed loader, the q plan (both Section 8.2 rank conditions at `RANK_FLOOR = 0.1`, default low-index directions), F0 inputs at every ±q and q = 0 from unwrapped POSCAR positions, a Slurm-array `submit.sh` spliced from the user's `job.sh`, and `collect` readback of E and `M_int` with the Eq (3.3) phases. Commands `plan`, `prepare` and `collect` replace the five `step1-*` commands. Deleted `step1.py` (bond rows, F1/F2, λ>0 penalty checks) and `test_step1.py`; `sphere` and `check_run` moved unchanged. The readback rejects a reversed site by pair phase instead of the approved `|delta_a| < 90°`, which cannot see a reversal in a 2-site cell. Dropped `dmi status` (D-013 amended). Tests 16 -> 15. No VASP or cluster jobs. See the [TEN-03 handoff](docs/sessions/2026-11-08_2010Z-agent-ten03-spiral.md).

- TEN-02 follow-up: `test_section_7_4_table` now requires the inversion group's stiffness basis to span all 6 symmetric matrices, and `test_exchange_classes` adds FeGe (5 classes of 12, each closed under the kept R and r -> -r). Both catch an injected fault (dropped symmetrizer; dropped `-orbit`). Corrected three background notes in `plans/ten-02-symmetry.md`. No code change; 16 tests. See the [follow-up log](docs/sessions/2026-11-08_1829Z-agent-ten02-followup.md).

- TEN-02: added `dmi_pipeline/symmetry.py` (kept operations with the space-group, orthogonality and site-map guards; spiralization and stiffness bases; twist count; exchange classes) and the `spglib>=2.6` dependency. Replaced `step1.positions` and `realized.poscar_species` with one reader, `realized.poscar(path) -> (lattice, species, tau)`, which applies the scale factor and rejects Cartesian positions and negative or three-value scales. Added three tests (13 -> 16). Reproduced the spec's expected-results table; 9 of 9 injected faults caught. No VASP or cluster jobs. See the [TEN-02 handoff](docs/sessions/2026-11-08_1735Z-agent-ten02-symmetry.md).

- Prepared the repository for coding in Claude Code: added `CLAUDE.md` importing `AGENTS.md`, the TEN-02 spec (`plans/ten-02-symmetry.md`), the seed file format (`docs/seed_file.md`, D-016) and the symmetry detection rules (D-017). Added `materials/fe/seed.toml`, removed the obsolete `examples/fe-f0-pilot/` campaign example, moved the old runner plan to `docs/archive/`, marked TEN-01 done and set one branch per task. No code change. See the [handoff log](docs/sessions/2026-11-08_1710Z-agent-claude-code-handoff.md).

- TEN-01: removed `runner`, `campaign`, `reference` and `workflow` with their tests, about 3,300 lines. Moved `INCAR_TAGS` and `echo_check` to `realized`, gave T3 a small wrapper in `cso`, and ignored `vasp files/` and `pipeline v4/`. There is no N0 command until TEN-04. Cut the test suite from 210 cases to 13 (D-015). No VASP or cluster jobs. See the [TEN-01 handoff](docs/sessions/2026-11-04_1845Z-agent-ten01-remove-orchestration.md).

- Pivoted the project from bond-resolved DMI vectors to the spiralization tensor, stiffness tensor and exchange classes. Added math Revision 3.0 with a Markdown agent edition, recorded D-007 to D-014, updated AGENTS, STATUS and README, and moved bond-era documents to `docs/archive/`. No code or VASP change; the pre-pivot state is at tag `archive/bond-dmi-v3`.

- Fe pilot T4b-2: expose completed jobs waiting on reference verification in the status table and additive JSON fields/counts; consolidate scheduler-state reconciliation in one table. Synthetic local tests only; no VASP or cluster jobs. No handoff log was committed for T4b-2.

- Added the Fe pilot T4 runner baseline and hardened the submit path: prepared, hashed Slurm `jobsall.sh`, locked and explicitly confirmed fake-tested submission, private restart staging and exact scheduler options. Local 153 -> 160 tests and generated-script Bash syntax pass; reconcile/readback/resume are still being hardened in T4b. No VASP or cluster jobs. See the [T4a handoff](docs/sessions/2026-10-30_2124Z-agent-pilot-runner-t4a-submit-path.md).

- Added independent q0 sphere-reference preparation/extraction with hashed provenance and strict per-case compatibility; campaign import/generate and `campaign-reference` now verify before acceptance. 106 -> 136 local tests pass; no VASP or cluster run. See the [T3 handoff](docs/sessions/2026-10-30_1559Z-agent-pilot-runner-t3-reference.md).

### Fe F0 pilot campaign preparation (2026-10-30)

- Added `campaign-prepare` and `campaign-plan` with pre-write plan validation, two-kind dependencies, explicit imported-reference provenance pending T3, SHA-256 input inventory, and per-case expansion through the unchanged Step 1 generator/writer. Added a two-run Fe example and 44 synthetic tests; 106 total local tests pass. Generated q0 preparation, submission and reference checks remain for T3/T4. See the [T2 handoff](docs/sessions/2026-10-30_1538Z-agent-pilot-runner-t2-campaign.md).

### Shared Step 1 run convergence check (2026-10-30)

- Extracted `step1.check_run(directory, nions)` for independent OUTCAR convergence, run INCAR echo and terminal OSZICAR sphere/step association; `read_state` retains config-specific comparisons and unchanged provenance/readback. Seven synthetic boundary cases added; 62 local tests pass. No physical validation or cluster execution. See the [T1 handoff](docs/sessions/2026-10-30_1526Z-agent-pilot-runner-t1-check-run.md).

### Explicit Perlmutter pilot interfaces (2026-10-21)

- Removed current-directory job.sh discovery: include a launch script only through `--job-template`. Material/recipe/run/readback paths stay caller supplied, with executable configuration in the existing working launch script. Added ENINI to the shared input whitelist so cutoff settings can be supplied and echoed without selecting new values. Added the [Perlmutter sequence](docs/archive/PERLMUTTER_F0_PILOT.md), portable installation instructions and regression coverage through synthetic shared-input preparation/readback. Local pilot directories are generator tests; no local cluster assets are required. No calculation submitted. See the [handoff](docs/sessions/2026-10-21_1815Z-agent-perlmutter-pilot-portability.md).

### Single-directory Step 1 pilot preparation (2026-10-19)

- Extended existing `step1-prepare`/`write_inputs` with shared material assembly: generated tags override the base INCAR once, while POSCAR/KPOINTS/POTCAR and a supplied launch template are copied unchanged. The default launch template is current-directory job.sh; its absence is explicitly reported as review-only. Existing fragment-only preparation remains available. A local ferromagnetic Fe F0 candidate is prepared with consistent targets/config/INCAR, with launch availability and inherited cutoff/resource choices recorded for review. See the [preparation handoff](docs/sessions/2026-10-19_1627Z-agent-fe-f0-preparation.md). No scheduler, VASP execution or physical acceptance change.

### Step 1 logical INCAR equivalence (2026-10-19)

- Reused the shared strict logical parser for the four Step 1 run/config boolean tags. A prepared T/F config now reads the original Fe True/False INCAR without a config edit; invalid or opposite boolean values still fail. The full real-file CLI readback reproduces the same failed physical gate and field/penalty diagnostics with unchanged thresholds. See the [follow-up session](docs/sessions/2026-10-19_1556Z-agent-step1-logical-readback.md). No VASP rerun.

### Historical Fe q0 reference and full Step 1 readback (2026-10-05)

- Recorded a converged q0 Fe sphere reference, a diagnostic F1 reconstruction of the historical +x/+x lambda=1 inputs, and the full CLI readback. The physical gate fails absolute weighted alignment, M_int norm drift and penalty limits; signed factor evidence passes, while the field/penalty same-update identity remains unavailable with a recorded interval gap. The generated config's T/F tokens fail literal comparison with historical True/False inputs, so the evidence includes a clearly labelled spelling-only historical config. No validator/tolerance or VASP change. See the [readback session](docs/sessions/2026-10-05_2030Z-agent-step1-q0-readback.md) and [evidence record](evidence/2026-10-05-fe-q0-step1-readback/README.md).

### Step 1 field and penalty diagnostics (2026-09-30)

- Split signed factor-two evidence from the field/penalty identity in the existing Step 1 validator. The identity now records printed intervals and any gap at the requested coefficient matched to run inputs, with same-update interpretation unavailable until separately established. The lambda=1 Fe discrepancy remains visible; alignment and penalty acceptance limits are unchanged. Added a focused CGA-format regression and updated the spec/usage; 18 focused and 53 total local tests pass. See the [validator handoff](docs/sessions/2026-09-30_2011Z-agent-step1-field-penalty-validator.md). No VASP rerun or production acceptance.

### Step 1 field and penalty source audit (2026-09-30)

- Traced the original lambda=1 Fe sample against supplied VASP mode-1 source: the final printed penalty is cached before a later moment refresh, while signed fields use current moments; the source coefficient remains the requested 1.0. The field/penalty printed intervals are disjoint at exact lambda 1, while factor-two and sign remain supported at printed-moment precision. No code or tolerance change, VASP rerun, or production gate; see the [source audit](docs/sessions/2026-09-30_1933Z-agent-step1-field-penalty-source-audit.md).

### Step 1 original-file reader repair handoff (2026-09-30)

- Committed the reviewed reader repair for repeated OSZICAR sphere tables, SDA/CGA iterations, actual OUTCAR run banners and `Iteration I(E)` association, with distinct missing-summary and missing-OUTCAR-footer checks. The original Fe sample parses at ionic/electronic step 1/50 (95 sphere tables, one ionic summary); 17 focused and 52 total local software tests pass. No push.
- The sample's requested both-Fe +x directions do not establish physical F0 realization, and zero lambda/field cannot verify a nonzero-lambda convention. No versioned config/reference-bound read, production gate or VASP job; see [real-sample handoff](docs/sessions/2026-09-30_1610Z-agent-step1-reader-real-sample.md).

### Step 1 final review follow-up (2026-09-30)

- Rejected malformed or broadcastable QSPIRAL values at stored/requested/run/echo boundaries and mismatched per-species RWIGS between otherwise valid partners.
- Kept zero-field states valid without claiming factor-two evidence below printed resolution; retained separate zero-field consistency and positive-signal Fe excerpt checks. See [final review log](docs/sessions/2026-09-30_0024Z-agent-step1-final-review.md). No production VASP validation.

### Step 1 corrective review (2026-09-30)

- Bound readback and row gates to checked config/run file hashes and re-read sphere
  moments, checked stored q/target identity, and added safe CLI wrapped-partner
  representation without changing physical targets.
- Allowed one common-z pair-validation rotation while retaining raw model spins;
  checked printed penalty and signed field against MW_int within decimal rounding;
  required indexed terminal OSZICAR and final OUTCAR loop agreement or failed closed.
  Synthetic tests are not VASP validation. See [corrective session log](docs/sessions/2026-09-30_0005Z-agent-step1-review-fixes.md).

### Step 1 offline vector software path (2026-09-29)

- Added versioned lab-frame target recipes and INCAR fragments, strict OSZICAR
  sphere-moment readback with separate electronic convergence, signed realization
  checks, one canonical cell-translation bond kernel and two-sided diagnostic rows.
- Added offline CLI input/readback/row/weighted-solve entry points and synthetic
  regression coverage while preserving the historical N0 manifest and trace.
  Missing BFO symmetry basis, production trace/parity and noise evidence are
  explicit blockers, not new validation passes. See [local usage](docs/archive/STEP1_LOCAL_USAGE.md)
  and the [implementation handoff](docs/sessions/2026-09-29_2328Z-agent-dmi-step1-vectors.md).

### Local baseline handoff (2026-09-29)

- Audited the tracked N0-only baseline, recorded its local test result and
  outstanding Step 1 work in [the handoff](docs/sessions/2026-09-29_2024Z-agent-baseline-finalization.md).
- Excluded the two local full VASP distribution copies while leaving the small
  Patch B spec and other untracked patch/source candidates visible for review.
  No VASP assets, production results or Step 1 changes were committed.

### Documentation and coordination

- Prepared repository instructions, status/ownership tracking, a decision log,
  session-log template, evidence guidance and a Windows-friendly setup guide.
- Bundled the current Revision 2.4 LaTeX source and Step 1 implementation spec.
- Preserved the nine supplied older documents under docs/archive with a clear
  notice about superseded frame assumptions.
- Added starter ignore and line-ending rules for local Python/HPC work.

The documentation-and-coordination entries above describe the starter kit, not
Step 1 implementation or a new production validation result.

## Earlier document milestones

- **2026-09-29:** Step 1 implementation specification written.
- **2026-09-26:** Math Revision 2.4 replaced redundant angular bookkeeping with
  vector-based targets, readback, checks and fitting.

Software releases and production validation milestones remain to be recorded
from actual repository commits and evidence.
