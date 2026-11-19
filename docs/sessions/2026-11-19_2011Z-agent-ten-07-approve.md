# Session: TEN-07 approval

- Session ID / UTC date: 2026-11-19, 20:11Z
- Agent or human / platform: Claude Code (Opus 5.5), WSL2
- Task ID and scope: record the user's approval of the TEN-07 spec and the Gate 3 tolerance; docs only
- Branch: `ten-07-approve`, from `main`
- Base commit at session start: `96a6c96` (PR #26 merge; PR #25 also merged)
- Working-tree changes already present: untracked `Claude outputs/` and `materials/fe/job.sh` (not this task's; left untouched)
- Related spec / prior session: `plans/ten-07-bfo.md`; [BFO-EV1 log](2026-11-18_1922Z-agent-bfo-ev1.md)
- Status: complete, awaiting review

## Work performed

- `plans/ten-07-bfo.md`: status "Approved by the user 2026-11-19"; Gate 3
  tolerance 5% on the Stage B change in D. The "Open for the user" note on how
  Stages B and C are built is kept and marked as not settled by this approval.
- `STATUS.md`: header, base commit (`96a6c96`, PRs to #26 merged), handoff
  scope, the TEN-07 row, and next actions (1) the LSDA+U inputs for
  `materials/bfo/`, (2) Stage A on Perlmutter. The other outstanding record
  items are kept under "Also outstanding".
- `CHANGELOG.md`.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `git log origin/main`, `gh pr list` | #25 and #26 merged; `main` at `96a6c96` | Branch base |
| Tests | NOT RUN | Docs only |

No VASP run, no cluster contact.

## Decisions or deviations

None. The tolerance is recorded in the spec, not as a DECISIONS entry: it is a
task acceptance criterion.

## Handoff

- Completed work: the files above.
- Remaining work / blockers: the user's BFO inputs. When they arrive: commit
  POSCAR, INCAR, KPOINTS and `seed.toml` under `materials/bfo/` as given, write
  `POTCAR.spec` as for `materials/fe/` (never the POTCAR), run
  `dmi plan materials/bfo/seed.toml` and check group 161, 6 of 6 kept,
  `p_D 1  p_A 2`, 19 runs. Also: how Stages B and C are built.
- Next concrete command or action: the user supplies the inputs.
- Files another session should read: `plans/ten-07-bfo.md`, `materials/fe/POTCAR.spec` (the format to copy).
- Last tested commit, if available: none (docs only).
- Uncommitted/unpushed work and where it exists: see the final response.
