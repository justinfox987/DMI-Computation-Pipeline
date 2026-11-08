# Session: TEN-02 follow-up tests and spec notes

- Session ID / UTC date: 2026-11-08
- Agent or human / platform: Claude Code (Opus 5.5)
- Task ID and scope: TEN-02 follow-up. Two test assertions and three spec-note corrections; no code changes
- Branch: `ten-02-followup`
- Base commit at session start: `main` at `f46f0f1` (TEN-02 merged, PR #10)
- Working-tree changes already present: none
- Related spec / prior session: [plans/ten-02-symmetry.md](../../plans/ten-02-symmetry.md), [TEN-02 log](2026-11-08_1735Z-agent-ten02-symmetry.md)
- Status: complete

## Work performed

- `pipeline v3/tests/test_symmetry.py` (edited):
  - `test_section_7_4_table`: the inversion row now requires the stiffness basis
    to span all 6 symmetric matrices (`SYMMETRIC`); A was unchecked before.
    Every row now checks A, so the `None` option is removed.
  - `test_exchange_classes`: FeGe, sites 0-3, FM, `rmax = 6.0`, `tol = 1e-6`.
    Expects 5 classes of 12 vectors, and each class with its negatives is closed
    under every kept R.
- `plans/ten-02-symmetry.md` (edited background notes): the conventional
  zincblende cell has 32 operations; one-Fe BFO is rejected at a 3.9 Å site
  distance, not 6.8 Å; noisy-BFO recovery at `symprec = 3e-2` and the
  `0.99 * symprec` figure depend on the random seed.
- `symmetry.py` is unchanged. Test count stays at 16.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `cd "pipeline v3" && .venv/bin/python -m pytest -q` | PASS, 16 passed | Whole suite |
| Fault (a): `stiffness_basis` returns `_basis(projector)` without the symmetrizer | FAIL as intended, at the inversion row's A assertion (`p_A = 9`) | Restored with `git checkout`; diff empty |
| Fault (b): `exchange_classes` stores `orbit` without `-orbit` | FAIL as intended: FeGe classes become `[6, 6, 6, 6, 6, 6, 12, 6, 6]`. Run separately, the closure check alone also fails (88 class/operation failures) | Restored with `git checkout`; diff empty |
| Scratch script: one-Fe BFO site map at `symprec = 1e-3` | Largest site distance 3.909 Å | Supports the spec correction |
| Scratch script: BFO, `sigma = 1e-3`, seeds 0-9 | `symprec = 1e-2`: all `P1`. `3e-2`: seeds 0, 8 `R3c`; 5, 7, 9 `R3`; 1, 2 `Cc`; others `P1` | Supports the seed-dependence note |
| Zincblende 32 operations | Already asserted by `test_section_7_4_table` | — |

Symmetry algebra only; no VASP or cluster jobs.

## Decisions or deviations

None.

## Handoff

- Completed work: the two assertions and the spec corrections above.
- Remaining work / blockers: none for this follow-up. TEN-03 still needs a spec.
- Next concrete command or action: review and merge the `ten-02-followup` PR, then write the TEN-03 spec.
- Files another session should read: `STATUS.md`, `plans/ten-02-symmetry.md`.
- Last tested commit, if available: the `ten-02-followup` commit containing this log.
- Uncommitted/unpushed work and where it exists: none after push.
