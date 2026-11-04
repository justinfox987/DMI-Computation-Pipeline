# Current project status

**Last reconciled:** 2026-11-02 UTC against `main` at `490a4e1`.

**Project state:** pivoting from bond-resolved DMI vectors to the spiralization
tensor, stiffness tensor and exchange classes ([D-007](docs/DECISIONS.md)). The
pivot documents exist. The code has not changed, so `pipeline v3/` still
implements the bond-era workflow.

**Integration branch / base commit:** `main` at `490a4e1`. The planned tag is
`archive/bond-dmi-v3` and the planned branch is `feat/spiral-tensors`. Neither
existed when this file was written.

**Handoff owner / scope:** unassigned. One writer per branch.

## Established

| Claim | Evidence | Limits |
|---|---|---|
| Patch B frozen-state null holds on BFO | Recorded N0 PASS in `acceptance/`: total -5.19e-8 eV, imaginary 1.4e-19 eV, for the z operator at q = 0 | Historical record, not replayed. Builds are stamped Sep 14 2026 07:13 (ref, dump_C) and 08:43 (dump_P) |
| Lab-frame MAGMOM and OSZICAR sphere readback | bcc Fe tests and supplied VASP source | Convention evidence for that setup, not production-build acceptance |
| Revision 3.0 algebra | Spin models and repository fixtures: transformation law, normalization, fits, rank conditions, twist count, pitch, magnon sign | Algebra only. The PAW steps are not independently tested |
| Local software | 183 tests pass at `490a4e1` | Covers pre-pivot code only |

No VASP calculation has tested Revision 3.0. There is no finite-q trace evidence,
and no parity (P0) measurement has been made with Patch B.

## Work queue

| ID | Work | Status | Owner / branch | Completion evidence |
|---|---|---|---|---|
| TEN-00 | Tag the pre-pivot state, then commit the pivot documents | Next | Unassigned | Tag on `490a4e1`; documents on the integration branch |
| TEN-01 | Remove `runner`, `campaign`, `reference`, `workflow` and their tests; move `INCAR_TAGS`, `_echo_check`, T3 wrapper | Not started | Unassigned | Own commit; surviving tests pass |
| TEN-02 | `symmetry.py`: kept operations, bases, twist count, exchange classes | Not started | Unassigned | Regression table of math Section 7.4 reproduced |
| TEN-03 | `spiral.py`: N-site F0 at lambda 0, q plan, `submit.sh`, readback, energy reader | Not started | Unassigned | Both rank conditions enforced; synthetic readback tests |
| TEN-04 | Trace vector and COCC contraction; add P0 and E0; remove hard-coded Bi check | Not started | Unassigned | Agrees with the CPROJ trace on fixtures |
| TEN-05 | `tensors.py`: fits, forbidden part, predictions, units | Not started | Unassigned | **Gate 1:** spin-model tensors recovered end to end |
| TEN-06 | bcc Fe F0 pilot at lambda 0; genuine x and y CSO for T3 | Blocked by TEN-01 to TEN-05 | Unassigned | **Gate 2:** T near zero on all axes, plausible A, first wall times |
| TEN-07 | BFO pairs and strained zincblende control with a supercell check | Pending Gate 2 | Unassigned | **Gate 3:** parity, forbidden terms and sign pass |
| TEN-08 | BFO FLEUR match, FeGe k series, twist test | Pending Gate 3 | Unassigned | **Gate 4:** agreement with FLEUR within stated error |
| TEN-09 | Mn2RhSn, exchange grids, K, BFO U scan | Pending Gate 4 | Unassigned | Tensor and prediction table |
| TEN-10 | Literature check and paper draft | Pending | Unassigned | Draft with reproducible data |

Gate 3 decides the pivot. If parity fails there, use the positive control to
separate a code fault from physics before spending more runs.

## Immediate next action

Tag `490a4e1` as `archive/bond-dmi-v3` first, so that the tag holds only pre-pivot
work. Then create `feat/spiral-tensors`, commit `docs/math/heide_math_v3.tex` and
`.md` with the updated AGENTS, DECISIONS, STATUS and README, and begin TEN-01.

The prepared Fe F0 recipe uses lambda 1 and needs lambda 0 before it can serve
TEN-06. Its q also needs revisiting against math Section 8.

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
- OUTCAR energy-line spacing, and the assumption that VASP magnetization follows
  the spin expectation. Only the magnon sign depends on the latter.

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
