# Session: simplification review and decisions

- Session ID / UTC date: 2026-11-10 to 2026-11-11
- Agent or human / platform: Claude (cloud session linked to the user's computer)
- Task ID and scope: review of code, plans and math for simplification; decisions D-020 to D-025; documents only
- Branch: `incar-user-settings` checkout; nothing committed
- Base commit at session start: `454afa2`
- Working-tree changes already present: untracked `materials/fe/{INCAR,KPOINTS,POSCAR,job.sh}` and `plans/ten-06-fe-pilot.md`
- Related spec / prior session: `plans/simplify-1.md`, `plans/anisotropy-1.md`
- Status: complete for documents; code not started

## Work performed

Inspected: all of `pipeline v3/dmi_pipeline` and `tests`, the plans, DECISIONS,
STATUS, both math editions, `vasp files/vasp-heide-patch-NEW/src`
(`relativistic.F`, `us.F`, `csodump.F`), `acceptance/manifest.json`, and the
real dumps in `pipeline v3/noq/` and `vasp files/sample-files/`.

Edited (documents only): `docs/math/heide_math_v3.tex` (Revision 3.2),
`docs/math/heide_math_v3.md` (agent notes only), `docs/DECISIONS.md` (D-020 to
D-025), `STATUS.md`, `CHANGELOG.md`, `AGENTS.md`, `README.md`,
`plans/ten-06-fe-pilot.md`. Added `plans/simplify-1.md`,
`plans/anisotropy-1.md` and this log.

No file under `pipeline v3/` was changed.

## Verification

All commands ran in a scratch copy of the package outside the repository.

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `python -m pytest -q` at `454afa2` | PASS, 21 tests | Software only |
| `load_ferwe` on the fixture with occupations 0.7/0.3, then 1.04/-0.04 | FAIL: "fractional FERWE", "outside [0, 1]" | Shows a smeared state cannot pass M1 |
| Layout test: `CSO`/`COCC` built in VASP's index order from random spinors on a p shell | VASP's `Re sum CSO*conj(COCC)` equals `<H>`; `trace_vector` returns minus the exact value on x, y, z; with `.conj()` it is exact | Bookkeeping from the source, not a VASP run |
| Handedness of the split triple on real `noq/dump-C/CSO.dat` | -0.707 (six O), -0.523 (Fe), -0.440 (Bi); the layout test gives -0.707 | Confirms ket-first storage with flip blocks `ud, du` |
| Current `load_cso`, `load_cocc`, `gate_c0`, `trace_vector`, `gate_n0` on real `noq/` dumps | PASS; total T = (-2.1e-8, -4.3e-8, -5.2e-8) eV | One collinear BFO state |
| Single-solve fit against `tensors.py` on the FeGe and BFO spin models | Agree to 1e-12 relative | Prototype |
| 12-line OSZICAR reader against `spiral.check_run` on `Fe_q0_test/q0` and `reader_test_2` | Same `M_int` | Two real static runs |
| `dmi plan` on the user's `materials/fe` | Stops on `MAGMOM`, then on missing `ENINI`; with both edited in a copy, `plan` and `prepare` write 19 runs | Software only |
| `latexmk -pdf heide_math_v3.tex` | PASS, 18 pages, no undefined reference; every pre-existing label keeps its number | Document build |
| Anisotropy basis prototype | `p` = 0/1 (cubic), 1/3 (3m, 4/mmm), 2/5 (mmm), 5/14 (-1) at orders 2/4 | Algebra |

The scratch scripts are not in the repository. FIX-1 turns the layout test into
a repository test.

## Decisions or deviations

D-020 to D-025. Two choices differ from the 2026-11-10 proposal: the twist
count and its gate are kept, and exchange classes stay in the math for a later
task. The patch change of item 2.11 is not taken.

## Handoff

- Completed work: the review, the decisions and the document updates.
- Remaining work / blockers: FIX-1 and SIM-1 are unwritten. TEN-06 is blocked
  by FIX-1. The document changes are uncommitted.
- Next concrete command or action: merge `incar-user-settings`, branch, commit
  these documents, then FIX-1.
- Files another session should read: `plans/simplify-1.md`, D-020 to D-025,
  math Sections 4.2, 4.4, 9.4 and 13.
- Last tested commit, if available: `454afa2` (21 tests).
- Uncommitted/unpushed work and where it exists: every file listed under
  "Edited", in the user's checkout.
