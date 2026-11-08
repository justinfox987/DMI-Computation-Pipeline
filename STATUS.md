# Current project status

**Last reconciled:** 2026-11-08 UTC, at the end of the TEN-02 follow-up on branch `ten-02-followup` (base `main` at `f46f0f1`), pending review.

**Project state:** pivoting from bond-resolved DMI vectors to the spiralization
tensor, stiffness tensor and exchange classes ([D-007](docs/DECISIONS.md)). The
campaign orchestration is removed. `step1.py` still holds the bond rows and
constrained families until TEN-03, and the new workflow does not exist yet.
There is no N0 command until TEN-04. TEN-02 (`symmetry.py` and the single POSCAR
reader) is merged in PR #10; a test-only follow-up is on `ten-02-followup`. The seed
file format is agreed ([D-016, D-017](docs/DECISIONS.md)).

**Integration branch / base commit:** `main` at `a0ec0b8`. Tag
`archive/bond-dmi-v3` marks `490a4e1`, the last pre-pivot commit. From TEN-02 on,
each task gets its own branch from `main`, and the user merges each pull request.
`feat/spiral-tensors` is retired once this handoff merges.

**Handoff owner / scope:** TEN-02 follow-up (two test assertions, spec notes) by
Claude Code on `ten-02-followup`, complete pending review. One writer per branch.

## Established

| Claim | Evidence | Limits |
|---|---|---|
| Patch B frozen-state null holds on BFO | Recorded N0 PASS in `acceptance/`: total -5.19e-8 eV, imaginary 1.4e-19 eV, for the z operator at q = 0 | Historical record, not replayed. Builds are stamped Sep 14 2026 07:13 (ref, dump_C) and 08:43 (dump_P) |
| Lab-frame MAGMOM and OSZICAR sphere readback | bcc Fe tests and supplied VASP source | Convention evidence for that setup, not production-build acceptance |
| Revision 3.0 algebra | Spin models and repository fixtures: transformation law, normalization, fits, rank conditions, twist count, pitch, magnon sign | Algebra only. The PAW steps are not independently tested |
| Local software | 13 tests pass on `main` at `c660cab`; 11 of 11 injected faults caught at TEN-01 | Software behavior only, not VASP results |
| Symmetry module (TEN-02) | 16 tests pass; the spec's expected-results table and the Section 7.4 forms reproduced; 9 of 9 injected faults caught ([log](docs/sessions/2026-11-08_1735Z-agent-ten02-symmetry.md)). The follow-up also catches a dropped stiffness symmetrizer and a dropped `-orbit` ([log](docs/sessions/2026-11-08_1829Z-agent-ten02-followup.md)) | Follow-up not yet merged. Symmetry algebra only; says nothing about VASP |

No VASP calculation has tested Revision 3.0. There is no finite-q trace evidence,
and no parity (P0) measurement has been made with Patch B.

## Work queue

| ID | Work | Status | Owner / branch | Completion evidence |
|---|---|---|---|---|
| TEN-00 | Tag the pre-pivot state and commit the pivot documents | Done | `feat/spiral-tensors` | Tag on `490a4e1`; documents and math Revision 3.0 committed |
| TEN-01 | Remove `runner`, `campaign`, `reference`, `workflow` and their tests; move `INCAR_TAGS`, `echo_check`, T3 wrapper; cut the test suite | Done | Merged in PR #7, `a0ec0b8` | [Handoff](docs/sessions/2026-11-04_1845Z-agent-ten01-remove-orchestration.md) |
| TEN-02 | `symmetry.py`: kept operations, bases, twist count, exchange classes; one POSCAR reader | Done; test follow-up in review, [spec](plans/ten-02-symmetry.md) | Merged in PR #10, `f46f0f1`; follow-up on `ten-02-followup` | Section 7.4 table and spec table reproduced ([log](docs/sessions/2026-11-08_1735Z-agent-ten02-symmetry.md)) |
| TEN-03 | `spiral.py`: seed loader, N-site F0 at lambda 0, q plan, `submit.sh`, readback, energy reader | Not started; needs a spec | Unassigned | Both rank conditions enforced; synthetic readback tests |
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

Review and merge the TEN-02 follow-up pull request from `ten-02-followup`. Then write the
TEN-03 spec and get it approved before coding. TEN-03's `plan` must print the
space group and kept/dropped counts first, as `symmetry.operations` returns them. TEN-03 must also carry two TEN-01 leftovers into
TEN-04: `trace_config` needs a `provenance.json` that nothing writes yet, and
`gate_n0` checks a hard-coded Bi.

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
