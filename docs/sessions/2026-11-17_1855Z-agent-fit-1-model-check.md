# Session: FIT-1 Fit check and the TEN-06 evidence record

- Session ID / UTC date: 2026-11-17
- Agent or human / platform: Claude Code (Opus 5.5), WSL2
- Task ID and scope: FIT-1, the residual (Fit) check on every tensor solve (D-026), and the TEN-06 Fe evidence record
- Branch: `fit-1-model-check`, from `main`
- Base commit at session start: `2ceb27f` (PR #23 merge)
- Working-tree changes already present: untracked `Claude outputs/` and `materials/fe/job.sh` (not this task's; left untouched)
- Related spec / prior session: [plans/fit-1-model-check.md](../../plans/fit-1-model-check.md); [FIX-2 log](2026-11-17_1827Z-agent-fix-2-cso-nelect.md)
- Status: complete, awaiting review

## Work performed

- `pipeline v3/dmi_pipeline/gates.py`: `gate_fit`, next to `gate_forbidden` and
  sharing its `FORBIDDEN_FLOOR`.
- `pipeline v3/dmi_pipeline/tensors.py`: `tensor_fit` computes the residual and
  the check for each solve and takes row labels; `fit_pairs` labels rows by
  pair name (`d1_t1`), plus the axis for D and D_free; `observables` names
  each pair; `report_tree` writes `fit_check` (passed, row, worst, bound, rule,
  units, residual vector, in meV) and includes it in `passed`; `_lines` prints
  one Fit line per solve.
- `pipeline v3/tests/test_tensors.py`: spin-model pairs carry names; the
  spin-model test asserts Fit passes on A, D and D_free, with and without noise;
  `test_bcc_fe_pilot_tree` uses the real Fe lattice constant, asserts Fit A
  passes on the spin model, fails on the real fe-k12 energies (d1_t1,
  +0.258 meV against 0.0641 meV, A = 433.04, exit 1), and is not evaluated
  when one run is lost and A is exactly determined.
- Math TeX Sections 9.4 and 11 and the Revision 3.2 amendment note; D-026;
  `heide_math_v3.md`; `docs/seed_file.md`.
- `evidence/2026-11-17-fe-ten06-pilot/README.md`; the TEN-06 convergence plan
  amended to what was run; STATUS; CHANGELOG; `plans/fit-1-model-check.md`.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `cd "pipeline v3" && .venv/bin/python -m pytest -q` at `2ceb27f` | PASS, 15 | Baseline (after FIX-2) |
| Hand solve of the fe-k12 energies (numpy, `[t^2, t^4]` design) | A = 433.039 meV Å², residual +0.2575, -0.1030, +0.0172 meV, sigma_g 2.435e-7 eV, bound 0.0641 meV | Matches the spec's numbers |
| `cd "pipeline v3" && .venv/bin/python -m pytest -q` | PASS, 15 | Software only |
| Mutation: `gate_fit` always passes | FAIL, `test_bcc_fe_pilot_tree` | The failure is tested |
| Mutation: Fit checks left out of `report["passed"]` | FAIL, `test_bcc_fe_pilot_tree` | The exit code is tested |
| Mutation: exactly determined solve evaluated (`dof < 0`) | FAIL, `test_bcc_fe_pilot_tree` | "not evaluated, never a pass" is tested |
| `latexmk` / `pdflatex` | NOT RUN: not installed here | The amended TeX is not compiled |

No VASP run, no cluster contact. Every number in the evidence record was
reported by the user or the reviewer; none is copied from a JSON file.

## Decisions or deviations

Not covered by the spec, decided here:

- The floor reuses `FORBIDDEN_FLOOR` (0.01) rather than a second constant, so
  the two bounds cannot drift. The name stays, to avoid churn.
- `fit_check` entries are in meV, like every reported value in `tensors.json`;
  the residual vector is per magnetic site (g for A, y for D).
- The check sits inside `tensor_fit`, so every solve gets it; rows are labelled
  by pair name, `d1_t1`, and for D by `d1_t1 x`.
- The evidence record departs from the TEN-06 spec's "no number typed by hand"
  rule, because the JSON reports and dump files were not supplied. The record
  says so at the top and marks every missing item as not supplied.
- Gate 2.1 is recorded as a pass because `fit` used all three pairs, so `collect`
  passed every run. Fact 1 (`LDUMPCOCC` without `LDUMPCPROJ`) is recorded as
  settled on the condition that the decks ran as `dmi dumps` wrote them.

## Handoff

- Completed work: FIT-1 as specified; the evidence record, partial as stated.
- Remaining work / blockers: review and merge; the 24x24x24 diagnostic result;
  the JSON reports, dump files, hashes, wall times and build identity for the record;
  compile the TeX on a machine with LaTeX.
- Next concrete command or action: fill the 24x24x24 placeholder in
  `evidence/2026-11-17-fe-ten06-pilot/README.md`.
- Files another session should read: D-026, `gates.gate_fit`, `tensors.tensor_fit`, the evidence README.
- Last tested commit, if available: the FIT-1 commit on `fit-1-model-check`.
- Uncommitted/unpushed work and where it exists: none of this task's after the push.
