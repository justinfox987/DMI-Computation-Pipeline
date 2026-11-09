# Session: INCAR tags are the user's (D-019)

- Session ID / UTC date: 2026-11-09
- Agent or human / platform: Claude Code (Opus 5.5)
- Task ID and scope: Replace the "Unreviewed INCAR tags" rejection with a `plan` warning; keep rejecting `KSPACING` and Section 3.2 contradictions; record D-019
- Branch: `incar-user-settings`
- Base commit at session start: `main` at `b082893`
- Working-tree changes already present: untracked `plans/ten-06-fe-pilot.md` (the TEN-06 draft, awaiting approval); not part of this branch
- Related spec / prior session: user request 2026-11-09; [TEN-05 log](2026-11-09_0300Z-agent-ten05-tensors.md)
- Status: complete, pending review

## Work performed

- `spiral.material_incar`: unseen tags are no longer rejected, and `KSPACING`
  is rejected explicitly. `plan` returns `unseen_tags`.
- `realized.echo_check`: the unseen-tag rejection is removed. Each tag is still
  checked against the OUTCAR echo.
- `__main__.plan_lines`: prints the warning as the last line.
- `tests/test_spiral.py`, extending existing tests, with no new test:
  - `test_seed_and_plan`: no warning on the default INCAR, and the exact warning
    for `NBLOCK`;
  - `test_prepare_writes_paired_f0_inputs`: the `LSORBT` rejection case is
    replaced by a `KSPACING` rejection;
  - `test_readback`: the material INCAR carries `NBLOCK`, so `collect` and the
    echo check must accept a user tag.
- D-019, `docs/seed_file.md`, STATUS (next action) and CHANGELOG.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `cd "pipeline v3" && .venv/bin/python -m pytest -q` | PASS, 21 passed | Whole suite |
| Fault injection, one at a time | 4 of 4 caught | Rejection put back in `echo_check`; rejection put back in `material_incar`; `KSPACING` accepted; warning not printed. Files compared with the good copies afterwards |

No VASP or cluster jobs.

## Decisions or deviations

D-019 recorded. It supersedes the TEN-03 unseen-tag rejection.

## Handoff

- Next concrete action: review and merge this PR. Then approve the TEN-06 spec,
  and add the Fe inputs to `materials/fe/`.
- Uncommitted/unpushed work: `plans/ten-06-fe-pilot.md` stays untracked until
  the TEN-06 approval.
