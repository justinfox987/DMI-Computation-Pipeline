# Current project status

**Last reconciled:** 2026-11-20 UTC, at PACK-1 on branch `pack-1` ([log](docs/sessions/2026-11-20_2122Z-agent-pack-1.md)).

**Project state:** pivoting from bond-resolved DMI vectors to the spiralization
tensor, stiffness tensor and exchange classes ([D-007](docs/DECISIONS.md)). The
campaign orchestration and `step1.py` are removed. TEN-02 (`symmetry.py`) and
TEN-03 (`spiral.py`: seed, `plan`, `prepare`, `collect`), TEN-04 (`dumps`,
`trace`), TEN-05 (`tensors.py`, `dmi fit`), cleanup 1, FIX-1 (trace sign,
smeared FERWE; D-020), SIM-1a (recompute from the VASP files, M1 per build,
handedness for T3; D-021) and SIM-1b (INCAR overrides, single-solve fit with
parity noise, 1% Forbidden floor; D-022, D-023) are merged, as are the TEN-06
code (PR #21), SEQ-1 (PR #22), FIX-2 (PR #23) and FIT-1 (PR #24, the Fit
check, D-026). TEN-06 is done: the bcc Fe pilot passes Gate 2's machinery on
real VASP files. Its non-quadratic `A` is resolved for Fe as an artifact of PBE
in VASP's locally collinear GGA (D-027): an LDA control at 10x10x10 passes the
Fit check with `A = 182.5 meV A^2` (not final)
([evidence](evidence/2026-11-17-fe-ten06-pilot/README.md)). A BFO LDA+U
diagnostic confirms the artifact for BFO and passes Fit A and Fit D, with D
antisymmetric, 2.3446 meV Å per Fe ([evidence](evidence/2026-11-18-bfo-lda-diagnostic/README.md)). The user chose LSDA+U throughout for
production (D-028). The TEN-07 spec was approved on 2026-11-19; it waits for
the user's LSDA+U inputs.

**Integration branch / base commit:** `main` at `a1735be`, the PR #27 merge (TEN-07 approval). PRs #15 to #27 are merged. Tag
`archive/bond-dmi-v3` marks `490a4e1`, the last pre-pivot commit. From TEN-02 on,
each task gets its own branch from `main`, and the user merges each pull request.
`feat/spiral-tensors` is retired once this handoff merges.

**Handoff owner / scope:** Claude / `pack-1`, `--slots` and the pack scripts
(PACK-1, code, tests and docs); done and awaiting review.
One writer per branch.

## Established

| Claim | Evidence | Limits |
|---|---|---|
| Patch B frozen-state null holds on BFO | Recorded N0 PASS in `acceptance/`: total -5.19e-8 eV, imaginary 1.4e-19 eV, for the z operator at q = 0 | Historical record, not replayed. Builds are stamped Sep 14 2026 07:13 (ref, dump_C) and 08:43 (dump_P) |
| Lab-frame MAGMOM and OSZICAR sphere readback | bcc Fe tests and supplied VASP source | Convention evidence for that setup, not production-build acceptance |
| Revision 3.0 algebra | Spin models and repository fixtures: transformation law, normalization, fits, rank conditions, twist count, pitch, magnon sign | Algebra only. The PAW steps are not independently tested |
| Local software | 21 tests pass on `cleanup-1`; the full command chain gives byte-identical outputs to `main` at `ec3e961`; 28 of 28 injected faults across TEN-02 to TEN-05 caught ([cleanup log](docs/sessions/2026-11-09_1930Z-agent-cleanup-1.md)) | Software behavior only, not VASP results |
| Symmetry module (TEN-02) | Tests pass; the spec's expected-results table and the Section 7.4 forms reproduced; 9 of 9 injected faults caught ([log](docs/sessions/2026-11-08_1735Z-agent-ten02-symmetry.md)). The follow-up also catches a dropped stiffness symmetrizer and a dropped `-orbit` ([log](docs/sessions/2026-11-08_1829Z-agent-ten02-followup.md)) | Symmetry algebra only; says nothing about VASP |
| Spiral inputs and readback (TEN-03) | Merged in PR #12; BFO's three rhombohedral axes fail the A rank condition as in math Section 8.2; 19 of 19 injected faults caught ([log](docs/sessions/2026-11-08_2010Z-agent-ten03-spiral.md)) | Synthetic files only; no VASP output has been read by `collect` |
| Dumps, trace vector and Section 11 checks (TEN-04) | COCC trace equals the independent CPROJ route to 1e-12 on all three axes; `dmi trace` passes N0, P0, E0 and T3 on a synthetic tree ([log](docs/sessions/2026-11-08_2245Z-agent-ten04-trace.md)) | Merged in PR #13. Synthetic dumps only; no real `COCC.dat` or `CSO.dat` has been read |
| Tensor fits and the spiral prediction (TEN-05, Gate 1) | Spin-model `D` and `A` (Eq 6.3) recovered through Eqs (1.3), (1.4) and Section 9 for FeGe (23) and BFO (3m), `F` at roundoff; Section 10.1 scalar, polar and chain cases reproduced ([log](docs/sessions/2026-11-09_0300Z-agent-ten05-tensors.md)) | Merged in PR #14. Spin-model data only; Gate 2 needs the bcc Fe pilot |

| Trace sign and CSO layout (D-020) | VASP source (`relativistic.F`, `us.F`, `csodump.F`); the layout test `test_vasp_file_layout_fixes_the_trace_sign` on `fix-1-trace-sign`; handedness -0.707 (O), -0.523 (Fe), -0.440 (Bi) on the real BFO `CSO.dat` ([log](docs/sessions/2026-11-11_1946Z-agent-fix-1-trace-sign.md)) | Source reading and a repository test. Not a VASP run; TEN-07b confirms |
| Current readers on real dumps | On `pipeline v3/noq/` (BFO, q = 0): `load_cso`, `load_cocc`, C0 with h = -0.523 (Fe), -0.440 (Bi), -0.707 (O), and N0 on all three axes pass; total T = (+2.1e-8, +4.3e-8, +5.2e-8) eV; `acceptance/m1.py` gives 5.3e-15, as recorded. The new OSZICAR reader returns the old `M_int` on `Fe_q0_test/q0` and `reader_test_2` ([log](docs/sessions/2026-11-11_2109Z-agent-sim-1a-recompute.md)) | One collinear state; says nothing about finite q |
| Gate 2 machinery on real VASP files (TEN-06, fe-k12) | `dmi fit` after FIX-2 exits 0 with C0 (including `h < 0`), N0, the null at every q (worst \|T\| 2.02e-7 eV), I0, P0 and E0 passing; `dump_P` without `LDUMPCPROJ` gives `COCC.dat`, and the `LSORBIT = T` CSO dump accepts `q0`'s spiral `CHGCAR` ([evidence](evidence/2026-11-17-fe-ten06-pilot/README.md)) | User-reported output; the JSON reports and dump files are not yet in the record. Not covered: trace sign, Forbidden, `A`. M1 is covered: the user confirmed on 2026-11-17 that the build is the 14 September build |
| bcc Fe energies are not quadratic in q (TEN-06 diagnostics) | Fit A fails on every tree run after FIT-1; g/t^2 rises from 212 to 956 meV Å² as t falls from 0.30 to 0.02 1/Å; the misfit survives an 18x18x18 mesh, PREC Accurate, a 4x wider Methfessel-Paxton smearing and NBANDS 40 with empty top bands; no jump at \|q\| = 2.2e-4 1/Å ([evidence](evidence/2026-11-17-fe-ten06-pilot/README.md)) | User-reported output and the reviewer's hand fits. Cause: see the next row |
| The Fe misfit is a PBE artifact (D-027) | Fe 10x10x10, same cutoffs and t: PBE fails Fit A (+0.0764 meV, bound 0.0419 meV), LDA passes (0.00249 meV, bound 0.0173 meV; A 182.5 meV Å², sigma_g 1.25e-9 eV). BFO with PBE+U fails Fit A at d1_t1 (+0.0928 meV, bound 0.0234 meV): not a metal effect ([evidence](evidence/2026-11-17-fe-ten06-pilot/README.md)) | User-reported output. The locally collinear GGA mechanism is the reviewer's inference, confirmed for Fe and for BFO by LDA controls; LDA A not final (mesh, PBE POTCAR, PBE lattice constant) |
| BFO D and A under LDA+U (diagnostic) | Two directions, 7x7x7: `dmi fit` exits 0; C0, N0, P0, E0 pass; Fit A pass (0.00513 of 0.01315 meV), A 141.02, 141.02, 155.04 meV Å²; Fit D pass (2.2e-4 of 3.85e-3 meV), D_yx = -D_xy = 2.3446 ± 0.0010 meV Å; cycloid, pitch 75.58 nm ([evidence](evidence/2026-11-18-bfo-lda-diagnostic/README.md)) | User-reported output; JSON reports not yet in the record. Diagnostic setup (PBE POTCARs with LDA, U and structure from PBE+U). Not established: the sign of D, Forbidden, mesh convergence |
| Single-solve fit and parity noise (D-023) | Reproduces `D_free`, `D`, `F`, `A` to 1e-12 on the FeGe and BFO spin models; parity sigma 1.32e-6 against a true 1.41e-6 ([log](docs/sessions/2026-11-11_1600Z-agent-simplify-decisions.md)) | Prototype in a scratch copy, not repository code |

The bcc Fe pilot (fe-k12) is the first VASP test of Revision 3.2: finite-q
traces and P0 with Patch B on a centrosymmetric metal, where T should vanish.
No trace with D ≠ 0 has been measured, so the sign is untested.

## Work queue

| ID | Work | Status | Owner / branch | Completion evidence |
|---|---|---|---|---|
| TEN-00 | Tag the pre-pivot state and commit the pivot documents | Done | `feat/spiral-tensors` | Tag on `490a4e1`; documents and math Revision 3.0 committed |
| TEN-01 | Remove `runner`, `campaign`, `reference`, `workflow` and their tests; move `INCAR_TAGS`, `echo_check`, T3 wrapper; cut the test suite | Done | Merged in PR #7, `a0ec0b8` | [Handoff](docs/sessions/2026-11-04_1845Z-agent-ten01-remove-orchestration.md) |
| TEN-02 | `symmetry.py`: kept operations, bases, twist count, exchange classes; one POSCAR reader | Done, [spec](plans/ten-02-symmetry.md) | Merged in PRs #10 and #11, `8d50eb6` | Section 7.4 table and spec table reproduced ([log](docs/sessions/2026-11-08_1735Z-agent-ten02-symmetry.md)) |
| TEN-03 | `spiral.py`: seed loader, N-site F0 at lambda 0, q plan, `submit.sh`, readback, energy reader | Done, [spec](plans/ten-03-spiral.md) | Merged in PR #12, `dba823d` | Both rank conditions enforced; synthetic readback tests ([log](docs/sessions/2026-11-08_2010Z-agent-ten03-spiral.md)) |
| TEN-04 | Dump inputs, `provenance.json`, COCC trace vector, N0/I0/P0/E0, Section 11 T3; remove the `Bi` check and the Euler search | Done, [spec](plans/ten-04-trace.md) | Merged in PR #13, `6aceeea` | Agrees with the CPROJ trace on fixtures |
| TEN-05 | `tensors.py`: fits, forbidden part, predictions, units | Done, [spec](plans/ten-05-tensors.md) | Merged in PR #14, `ec3e961` | **Gate 1:** spin-model tensors recovered end to end |
| Cleanup 1 | Remove dead and duplicate code without changing behavior | Done, [spec](plans/cleanup-1.md) | Merged in PR #15, `b082893` | Identical outputs to `main`; tests and fault injections unchanged |
| FIX-1 | Conjugate in the trace and its oracle, the layout test, delete the FERWE occupation checks (D-020) | Done; [spec](plans/simplify-1.md) Part 1 | Merged in PR #18, `27bfe86` | Layout test passes; the smeared fixture loads; 22 tests ([log](docs/sessions/2026-11-11_1946Z-agent-fix-1-trace-sign.md)) |
| SIM-1a | Recompute from VASP files, M1 to `acceptance/m1.py`, handedness in C0, lean OSZICAR reader (D-021) | Done; [spec](plans/simplify-1.md) items 2.2, 2.3, 2.4, 2.6 | Merged in PR #19, `22a0110` | D, A, F and the pitch agree with `main` to 5e-16 meV; 14 tests ([log](docs/sessions/2026-11-11_2109Z-agent-sim-1a-recompute.md)) |
| SIM-1b | INCAR overrides and the tetrahedron rule (D-022); single-solve fit with parity noise (D-023); `exchange_grid` and `rmax` out of the seed (D-025); energies-only trees | Done, merged in PR #20, `e514eed`; [spec](plans/simplify-1.md) items 2.5, 2.7, 2.9, 2.10 | Claude / `sim-1b-incar-fit` | D_free, D, F and A agree with the two-step fit to 3e-14 relative on the spin models and 1e-15 on the old chain tree; Forbidden bound with 1% floor and geometry-only rank test (D-023 amended); 15 tests ([log](docs/sessions/2026-11-11_2255Z-agent-sim-1b-incar-fit.md)) |
| TEN-06 | bcc Fe F0 pilot at lambda 0 | Done 2026-11-17. [Spec](plans/ten-06-fe-pilot.md); code merged in PR #21, `2e0ec61`. Gate 2 machinery passes on fe-k12; the non-quadratic PBE `A` is a locally collinear GGA artifact (D-027); LDA gives 182.5 meV Å² with Fit A pass, not final ([evidence](evidence/2026-11-17-fe-ten06-pilot/README.md)) | Claude / `ten-06-fe-pilot` (code), `ten-06-evidence` (record); the user (runs) | **Gate 2:** T near zero on all axes, plausible A, first wall times |
| TEN-07 | BFO production tree with LSDA+U (D-028): Stage A three directions, Stage B mesh check of D, Stage C U sensitivity | [Spec](plans/ten-07-bfo.md) approved by the user 2026-11-19; waits for the LSDA+U inputs | Unassigned | **Gate 3:** Stage A passes (C0, N0, I0, P0, E0, Fit A, Fit D, Forbidden) and Stage B changes D by less than 5% |
| TEN-07b | Sign anchor: strained CrSb supercell control (D-020) | Spec to write | Unassigned | Supercell SOC energies confirm the sign and magnitude of D |
| TEN-08 | BFO FLEUR match, FeGe k series, twist test | Pending Gate 3 | Unassigned | **Gate 4:** agreement with FLEUR within stated error |
| TEN-09 | Mn2RhSn, exchange grids, BFO U scan | Pending Gate 4 | Unassigned | Tensor and prediction table |
| SEQ-1 | `run.sh` and `run_dumps.sh`: the same run list one directory at a time in one allocation, skipping finished runs | Done, [spec](plans/seq-1-run-sequence.md) approved 2026-11-16; merged in PR #22, `9a9fc2b` | Claude / `seq-1-run-sequence` | 15 tests; `run.sh` executed on a small tree: finished run skipped, failure does not stop the loop, list order kept ([log](docs/sessions/2026-11-16_1921Z-agent-seq-1-run-sequence.md)) |
| PACK-1 | `--slots` on `prepare` and `dumps`: `pack.sh` and `pack_dumps.sh` keep several runs going in one batch job | Done on `pack-1`, [spec](plans/pack-1.md), design approved 2026-11-20; awaiting review | Claude / `pack-1` | 15 tests; `pack.sh` executed on a small tree (never more than 2 slots, finished run skipped, failure does not stop the others, each unfinished run once); mutations of the slot limit and the skip caught ([log](docs/sessions/2026-11-20_2122Z-agent-pack-1.md)). Concurrent GPU steps with `--exact` untested on Perlmutter |
| FIX-2 | `trace_run` no longer compares NELECT, which the real Patch B `CSO.dat` does not print; `write_cso` fixtures match the real header | Done; found by the Fe pilot 2026-11-17; merged in PR #23, `2ceb27f` | Claude / `fix-2-cso-nelect` | 15 tests; the command-chain and Fe pilot tests run `dmi fit` on a CSO with no NELECT line and failed with the field `TypeError` before the fix ([log](docs/sessions/2026-11-17_1827Z-agent-fix-2-cso-nelect.md)) |
| FIT-1 | Fit check on every tensor solve (D-026); TEN-06 evidence record | Done, [spec](plans/fit-1-model-check.md) approved 2026-11-17; merged in PR #24, `138c3c0` | Claude / `fit-1-model-check` | 15 tests; the real fe-k12 energies fail `Fit A` at d1_t1 (+0.258 meV against 0.064 meV) and `fit` exits 1; spin models pass; 3 mutations caught ([log](docs/sessions/2026-11-17_1855Z-agent-fit-1-model-check.md)) |
| ANI-1 | Anisotropy module (D-024) | Deferred until the spiralization tensor works; [spec](plans/anisotropy-1.md) approved | Unassigned | Known surface recovered; A1 to A5 on a first real tree |
| TEN-10 | Literature check and paper draft | Pending | Unassigned | Draft with reproducible data |

Gate 3 decides the pivot. If parity fails there, use the positive control to
separate a code fault from physics before spending more runs.

## Immediate next action

1. The user supplies the LSDA+U production inputs for `materials/bfo/`
   (D-028): POSCAR, INCAR, KPOINTS, `seed.toml`, and the POTCAR TITELs and
   SHA-256 sums for `POTCAR.spec`. They are committed as given, with no POTCAR,
   and `dmi plan materials/bfo/seed.toml` must show group 161, 6 of 6 kept,
   `p_D 1  p_A 2`, 19 runs.
2. Stage A of [TEN-07](plans/ten-07-bfo.md) on Perlmutter (the user runs it).

Also outstanding, for the records:

- How Stages B and C are built (hand-made decks or full trees; TEN-07 spec,
  "Known limit"), before Stage B.
- Add the BFO diagnostic's `tensors.json`, `traces.json`, `collected.json`,
  `plan.json` and `fit.log` to its evidence folder.
- Optional, for the Fe record: the fe-k12 JSON reports, `q0/dump_P/COCC.dat`,
  `dump_C/CSO.dat`, `hashes.txt`, the job resources, the wall times and the
  build banner and SHA-256.

`run.sh` and `run_dumps.sh` (SEQ-1) may replace `submit.sh` and
`submit_dumps.sh` when one allocation is wanted, and `pack.sh` and
`pack_dumps.sh` (PACK-1, `--slots`) run several at once in one job. The pack
needs a one-run job script whose `srun` uses `$DMI_RUN_NODES` and `--exact`
(`docs/seed_file.md`). The local, untracked `materials/fe/job.sh` sizes `srun`
from `SLURM_JOB_NUM_NODES`, so `--slots` refuses it as it stands.

`dmi plan materials/fe/seed.toml` runs on the committed inputs: group 229, 96
operations kept, `p_D 0  p_A 1  n_twist 0`, one MAGMOM override line, directions
(001), (010), (100), 19 runs.

## Unresolved inputs

- Concurrent GPU `srun` steps with `--exact` inside one allocation (PACK-1):
  untested until the user runs a `pack.sh` on Perlmutter. The Perlmutter bash
  version (the pack needs 4.3 or later for `wait -n`) is also unchecked.
- Whether the remote should be public. It was served to an anonymous clone on
  2026-11-02, while earlier documents assume a private repository. No POTCAR,
  WAVECAR or VASP source files are tracked.
- Perlmutter executable path, hash and source identity. The Sep 14 builds differ
  between runs, and the campaign executable needs reconciling.
- Finite-q parity noise, and the k mesh and q magnitudes that control it.
- DFT+U with LSPIRAL at finite q. Check against one commensurate supercell.
- RWIGS, ENCUT and ENINI for each material; the earlier Fe cutoff warning.
- Strained CrSb: FM stability at the chosen strain, and the strain itself.
- Mn2RhSn: suitability as a single-pattern ferrimagnet, and any reference values.
- The assumption that VASP magnetization follows the spin expectation. Only the
  magnon sign depends on it.
- The LSDA+U production inputs for BFO (D-028), all the user's: potpaw_LDA
  datasets, U, J and `LDAUTYPE`, structure, cutoffs, mesh.
- The BFO diagnostic's functional setting (`GGA = CA` on the PBE POTCARs) and
  the order of Bi and O in its LDAU lines: to confirm ([evidence](evidence/2026-11-18-bfo-lda-diagnostic/README.md)).
- Whether D under PBE is affected by the D-027 artifact (even in q). Not needed
  for production under D-028; D under LDA+U is clean.
- A VASP confirmation of the trace sign (D-020): TEN-07b, the supercell control.

## Retired work

These are closed by [D-007, D-008 and D-013](docs/DECISIONS.md), not failed:

- DMI-01: bond rows, paired fit and BFO symmetry fixture.
- DMI-02: the campaign runner, T4b and T5, and the corrected constraint probe.
- DMI-03 to DMI-05: constrained pilots, the bond campaign and bond comparisons.

The failed lambda 1 Fe readback remains diagnostic evidence for that state. The
remote privacy and sync question from REPO-01 carries over to the list above.

## Handoff records

Session logs are in [docs/sessions/](docs/sessions/). The bond-era status history
is in this file's Git history and at tag `archive/bond-dmi-v3`.

Keep this file a current snapshot. Detailed commands and attempts belong in
session logs; durable reasons belong in DECISIONS.
