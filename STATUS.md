# Current project status

**Last reconciled:** 2026-11-11 UTC, at the simplification decisions (D-020 to D-025). Documents only; uncommitted in the `incar-user-settings` checkout at `454afa2`.

**Project state:** pivoting from bond-resolved DMI vectors to the spiralization
tensor, stiffness tensor and exchange classes ([D-007](docs/DECISIONS.md)). The
campaign orchestration and `step1.py` are removed. TEN-02 (`symmetry.py`) and
TEN-03 (`spiral.py`: seed, `plan`, `prepare`, `collect`), TEN-04 (`dumps`,
`trace`) and TEN-05 (`tensors.py`, `dmi fit`) and cleanup 1 are merged. The full
workflow exists; none of it has run on a spiral. **The trace has the wrong
overall sign and the FERWE reader rejects smeared states (D-020, D-021); both
are fixed in the documents and not yet in the code.**

**Integration branch / base commit:** `main` at `b082893`; `incar-user-settings` (`454afa2`, D-019) is pushed and awaits merge. Tag
`archive/bond-dmi-v3` marks `490a4e1`, the last pre-pivot commit. From TEN-02 on,
each task gets its own branch from `main`, and the user merges each pull request.
`feat/spiral-tensors` is retired once this handoff merges.

**Handoff owner / scope:** none active. The document changes of 2026-11-11 are
uncommitted and need a branch. One writer per branch.

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

| Trace sign and CSO layout (D-020) | VASP source (`relativistic.F`, `us.F`, `csodump.F`); a bookkeeping test with those layouts; handedness -0.707 (O), -0.523 (Fe), -0.440 (Bi) on the real BFO `CSO.dat` ([log](docs/sessions/2026-11-11_1600Z-agent-simplify-decisions.md)) | Source reading and a scratch-copy test. Not a VASP run, and not yet a repository test |
| Current readers on real dumps | `load_cso`, `load_cocc`, C0, and N0 on all three axes pass on `pipeline v3/noq/` (BFO, q = 0): total T = (-2.1e-8, -4.3e-8, -5.2e-8) eV ([log](docs/sessions/2026-11-11_1600Z-agent-simplify-decisions.md)) | Run in a scratch copy on 2026-11-10. One collinear state; says nothing about finite q |
| Single-solve fit and parity noise (D-023) | Reproduces `D_free`, `D`, `F`, `A` to 1e-12 on the FeGe and BFO spin models; parity sigma 1.32e-6 against a true 1.41e-6 ([log](docs/sessions/2026-11-11_1600Z-agent-simplify-decisions.md)) | Prototype in a scratch copy, not repository code |

No VASP calculation has tested Revision 3.2. There is no finite-q trace evidence,
and no parity (P0) measurement has been made with Patch B.

## Work queue

| ID | Work | Status | Owner / branch | Completion evidence |
|---|---|---|---|---|
| TEN-00 | Tag the pre-pivot state and commit the pivot documents | Done | `feat/spiral-tensors` | Tag on `490a4e1`; documents and math Revision 3.0 committed |
| TEN-01 | Remove `runner`, `campaign`, `reference`, `workflow` and their tests; move `INCAR_TAGS`, `echo_check`, T3 wrapper; cut the test suite | Done | Merged in PR #7, `a0ec0b8` | [Handoff](docs/sessions/2026-11-04_1845Z-agent-ten01-remove-orchestration.md) |
| TEN-02 | `symmetry.py`: kept operations, bases, twist count, exchange classes; one POSCAR reader | Done, [spec](plans/ten-02-symmetry.md) | Merged in PRs #10 and #11, `8d50eb6` | Section 7.4 table and spec table reproduced ([log](docs/sessions/2026-11-08_1735Z-agent-ten02-symmetry.md)) |
| TEN-03 | `spiral.py`: seed loader, N-site F0 at lambda 0, q plan, `submit.sh`, readback, energy reader | Done, [spec](plans/ten-03-spiral.md) | Merged in PR #12, `dba823d` | Both rank conditions enforced; synthetic readback tests ([log](docs/sessions/2026-11-08_2010Z-agent-ten03-spiral.md)) |
| TEN-04 | Dump inputs, `provenance.json`, COCC trace vector, N0/I0/P0/E0, Section 11 T3; remove the `Bi` check and the Euler search | Done, [spec](plans/ten-04-trace.md) | Merged in PR #13, `6aceeea` | Agrees with the CPROJ trace on fixtures |
| TEN-05 | `tensors.py`: fits, forbidden part, predictions, units | Done, [spec](plans/ten-05-tensors.md) | Merged in PR #14, `ec3e961` | **Gate 1:** spin-model tensors recovered end to end |
| Cleanup 1 | Remove dead and duplicate code without changing behavior | In review, [spec](plans/cleanup-1.md) | Claude / `cleanup-1` | Identical outputs to `main`; tests and fault injections unchanged |
| FIX-1 | Conjugate in the trace and its oracle, the layout test, delete the FERWE occupation checks (D-020) | Next; [spec](plans/simplify-1.md) Part 1 | Unassigned | Layout test passes; a smeared FERWE fixture loads |
| SIM-1 | Recompute from VASP files, M1 to `acceptance/m1.py`, handedness in C0, lean OSZICAR reader, INCAR overrides, single-solve fit with parity noise (D-021 to D-023) | After FIX-1; [spec](plans/simplify-1.md) | Unassigned | Same tensors on the synthetic trees; about 12 tests |
| TEN-06 | bcc Fe F0 pilot at lambda 0 | After SIM-1; [spec](plans/ten-06-fe-pilot.md) drafted, awaits approval; Fe inputs are in `materials/fe/` uncommitted | Unassigned | **Gate 2:** T near zero on all axes, plausible A, first wall times |
| TEN-07 | BFO pairs and strained zincblende control with a supercell check | Pending Gate 2 | Unassigned | **Gate 3:** parity, forbidden terms and sign pass |
| TEN-08 | BFO FLEUR match, FeGe k series, twist test | Pending Gate 3 | Unassigned | **Gate 4:** agreement with FLEUR within stated error |
| TEN-09 | Mn2RhSn, exchange grids, BFO U scan | Pending Gate 4 | Unassigned | Tensor and prediction table |
| ANI-1 | Anisotropy module (D-024) | Deferred until the spiralization tensor works; [spec](plans/anisotropy-1.md) approved | Unassigned | Known surface recovered; A1 to A5 on a first real tree |
| TEN-10 | Literature check and paper draft | Pending | Unassigned | Draft with reproducible data |

Gate 3 decides the pivot. If parity fails there, use the positive control to
separate a code fault from physics before spending more runs.

## Immediate next action

1. Merge `incar-user-settings` (D-019).
2. Put the 2026-11-11 document changes on a branch and review them: math
   Revision 3.2, D-020 to D-025, `plans/simplify-1.md`,
   `plans/anisotropy-1.md` and the revised `plans/ten-06-fe-pilot.md`.
3. FIX-1, then SIM-1, then TEN-06. The pilot cannot pass `dmi trace` before
   FIX-1: bcc Fe is a smeared metal.

One cluster check can run now, because it needs no new code: one `dump_P` with
`LDUMPCOCC` on and `LDUMPCPROJ` off.

`dmi plan materials/fe/seed.toml` currently stops on the user's INCAR, first
for `MAGMOM` and then for a missing `ENINI`. SIM-1 turns both into overrides
(D-022).

The old Fe F0 recipe used lambda 1 and is retired. Its replacement is
[materials/fe/seed.toml](materials/fe/seed.toml); POSCAR, INCAR and KPOINTS are
added at TEN-06, and its `t` values are placeholders.

## Unresolved inputs

- Whether the remote should be public. It was served to an anonymous clone on
  2026-11-02, while earlier documents assume a private repository. No POTCAR,
  WAVECAR or VASP source files are tracked.
- Perlmutter executable path, hash and source identity. The Sep 14 builds differ
  between runs, and the campaign executable needs reconciling.
- Whether `LDUMPCOCC` works without `LDUMPCPROJ` on a real run.
- Finite-q parity noise, and the k mesh and q magnitudes that control it.
- DFT+U with LSPIRAL at finite q. Check against one commensurate supercell.
- RWIGS, ENCUT and ENINI for each material; the earlier Fe cutoff warning.
- Strained CrSb: FM stability at the chosen strain, and the strain itself.
- Mn2RhSn: suitability as a single-pattern ferrimagnet, and any reference values.
- The assumption that VASP magnetization follows the spin expectation. Only the
  magnon sign depends on it.
- Whether VASP accepts `q0`'s `LSPIRAL = T` `CHGCAR` with `ICHARG = 11` in the
  `LSORBIT = T` CSO dump (fallback: a separate `LSPIRAL`-free reference SCF).
- A VASP confirmation of the trace sign (D-020): the TEN-07 supercell control.
- Whether M1 must be rerun: only if the production executable is not the
  14 September build.

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
