# Current project status

**Last reconciled:** 2026-11-08 UTC, at the end of TEN-04 on branch `ten-04-trace` (base `main` at `dba823d`), pending review.

**Project state:** pivoting from bond-resolved DMI vectors to the spiralization
tensor, stiffness tensor and exchange classes ([D-007](docs/DECISIONS.md)). The
campaign orchestration and `step1.py` are removed. TEN-02 (`symmetry.py`) and
TEN-03 (`spiral.py`: seed, `plan`, `prepare`, `collect`) are merged. TEN-04
(`dumps`, `trace`: COCC trace vector, N0, I0, P0, E0, Section 11 T3) is on
`ten-04-trace` pending review. There is no fit until TEN-05.

**Integration branch / base commit:** `main` at `dba823d`. Tag
`archive/bond-dmi-v3` marks `490a4e1`, the last pre-pivot commit. From TEN-02 on,
each task gets its own branch from `main`, and the user merges each pull request.
`feat/spiral-tensors` is retired once this handoff merges.

**Handoff owner / scope:** TEN-04 by Claude Code on `ten-04-trace`, complete
pending review. One writer per branch.

## Established

| Claim | Evidence | Limits |
|---|---|---|
| Patch B frozen-state null holds on BFO | Recorded N0 PASS in `acceptance/`: total -5.19e-8 eV, imaginary 1.4e-19 eV, for the z operator at q = 0 | Historical record, not replayed. Builds are stamped Sep 14 2026 07:13 (ref, dump_C) and 08:43 (dump_P) |
| Lab-frame MAGMOM and OSZICAR sphere readback | bcc Fe tests and supplied VASP source | Convention evidence for that setup, not production-build acceptance |
| Revision 3.0 algebra | Spin models and repository fixtures: transformation law, normalization, fits, rank conditions, twist count, pitch, magnon sign | Algebra only. The PAW steps are not independently tested |
| Local software | 18 tests pass on `ten-04-trace`; injected faults caught at each task ([TEN-04 log](docs/sessions/2026-11-08_2245Z-agent-ten04-trace.md)) | Software behavior only, not VASP results |
| Symmetry module (TEN-02) | Tests pass; the spec's expected-results table and the Section 7.4 forms reproduced; 9 of 9 injected faults caught ([log](docs/sessions/2026-11-08_1735Z-agent-ten02-symmetry.md)). The follow-up also catches a dropped stiffness symmetrizer and a dropped `-orbit` ([log](docs/sessions/2026-11-08_1829Z-agent-ten02-followup.md)) | Symmetry algebra only; says nothing about VASP |
| Spiral inputs and readback (TEN-03) | Merged in PR #12; BFO's three rhombohedral axes fail the A rank condition as in math Section 8.2; 19 of 19 injected faults caught ([log](docs/sessions/2026-11-08_2010Z-agent-ten03-spiral.md)) | Synthetic files only; no VASP output has been read by `collect` |
| Dumps, trace vector and Section 11 checks (TEN-04) | COCC trace equals the independent CPROJ route to 1e-12 on all three axes; `dmi trace` passes N0, P0, E0 and T3 on a synthetic tree ([log](docs/sessions/2026-11-08_2245Z-agent-ten04-trace.md)) | Not yet merged. Synthetic dumps only; no real `COCC.dat` or `CSO.dat` has been read |

No VASP calculation has tested Revision 3.1. There is no finite-q trace evidence,
and no parity (P0) measurement has been made with Patch B.

## Work queue

| ID | Work | Status | Owner / branch | Completion evidence |
|---|---|---|---|---|
| TEN-00 | Tag the pre-pivot state and commit the pivot documents | Done | `feat/spiral-tensors` | Tag on `490a4e1`; documents and math Revision 3.0 committed |
| TEN-01 | Remove `runner`, `campaign`, `reference`, `workflow` and their tests; move `INCAR_TAGS`, `echo_check`, T3 wrapper; cut the test suite | Done | Merged in PR #7, `a0ec0b8` | [Handoff](docs/sessions/2026-11-04_1845Z-agent-ten01-remove-orchestration.md) |
| TEN-02 | `symmetry.py`: kept operations, bases, twist count, exchange classes; one POSCAR reader | Done, [spec](plans/ten-02-symmetry.md) | Merged in PRs #10 and #11, `8d50eb6` | Section 7.4 table and spec table reproduced ([log](docs/sessions/2026-11-08_1735Z-agent-ten02-symmetry.md)) |
| TEN-03 | `spiral.py`: seed loader, N-site F0 at lambda 0, q plan, `submit.sh`, readback, energy reader | Done, [spec](plans/ten-03-spiral.md) | Merged in PR #12, `dba823d` | Both rank conditions enforced; synthetic readback tests ([log](docs/sessions/2026-11-08_2010Z-agent-ten03-spiral.md)) |
| TEN-04 | Dump inputs, `provenance.json`, COCC trace vector, N0/I0/P0/E0, Section 11 T3; remove the `Bi` check and the Euler search | In review, [spec](plans/ten-04-trace.md) | Claude Code / `ten-04-trace` | Agrees with the CPROJ trace on fixtures |
| TEN-05 | `tensors.py`: fits, forbidden part, predictions, units | Not started | Unassigned | **Gate 1:** spin-model tensors recovered end to end |
| TEN-06 | bcc Fe F0 pilot at lambda 0; genuine x and y CSO for T3 | Blocked by TEN-01 to TEN-05 | Unassigned | **Gate 2:** T near zero on all axes, plausible A, first wall times |
| TEN-07 | BFO pairs and strained zincblende control with a supercell check | Pending Gate 2 | Unassigned | **Gate 3:** parity, forbidden terms and sign pass |
| TEN-08 | BFO FLEUR match, FeGe k series, twist test | Pending Gate 3 | Unassigned | **Gate 4:** agreement with FLEUR within stated error |
| TEN-09 | Mn2RhSn, exchange grids, K, BFO U scan | Pending Gate 4 | Unassigned | Tensor and prediction table |
| TEN-10 | Literature check and paper draft | Pending | Unassigned | Draft with reproducible data |

Gate 3 decides the pivot. If parity fails there, use the positive control to
separate a code fault from physics before spending more runs.

## Immediate next action

Review and merge the TEN-04 pull request from `ten-04-trace`. Then write the
TEN-05 spec (`tensors.py`: fits, forbidden part, predictions, units).

Two cluster checks can run in parallel, because neither needs the new code: genuine
x and y CSO dumps for T3, and one `dump_P` with `LDUMPCOCC` on and `LDUMPCPROJ` off.

The old Fe F0 recipe used lambda 1 and is retired. Its replacement is
[materials/fe/seed.toml](materials/fe/seed.toml); POSCAR, INCAR and KPOINTS are
added at TEN-06, and its `t` values are placeholders.

## Unresolved inputs

- Whether the remote should be public. It was served to an anonymous clone on
  2026-11-02, while earlier documents assume a private repository. No POTCAR,
  WAVECAR or VASP source files are tracked.
- Perlmutter executable path, hash and source identity. The Sep 14 builds differ
  between runs, and the campaign executable needs reconciling.
- Genuine x and y CSO dumps for T3. None exist for the current build.
- Whether `LDUMPCOCC` works without `LDUMPCPROJ` on a real run.
- Finite-q parity noise, and the k mesh and q magnitudes that control it.
- DFT+U with LSPIRAL at finite q. Check against one commensurate supercell.
- RWIGS, ENCUT and ENINI for each material; the earlier Fe cutoff warning.
- Strained CrSb: FM stability at the chosen strain, and the strain itself.
- Mn2RhSn: suitability as a single-pattern ferrimagnet, and any reference values.
- The assumption that VASP magnetization follows the spin expectation. Only the
  magnon sign depends on it.
- Whether VASP accepts `q0`'s `LSPIRAL = T` `CHGCAR` with `ICHARG = 11` in the
  `LSORBIT = T` CSO dumps (fallback: a separate `LSPIRAL`-free reference SCF),
  and how `dump_C_x` and `dump_C_y` read its magnetization relative to `SAXIS`.
- The CSO flip-block order, which T3 settles on the first genuine x/y dumps.

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
