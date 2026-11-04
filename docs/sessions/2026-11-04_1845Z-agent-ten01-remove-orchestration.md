# Session: TEN-01, remove orchestration and cut the tests

- Session ID / UTC date: session_01RU5FbdnrA8K1yPNmLNi61y / 2026-11-04
- Agent or human / platform: Claude / Claude Code remote session
- Task ID and scope: TEN-01, plus the user's direction to cut the test suite
- Branch: `feat/spiral-tensors`
- Base commit at session start: `4f793c5`
- Working-tree changes already present: none
- Related spec / prior session: D-013, D-015, math Revision 3.0
- Status: complete, pending the user's merge

## Work performed

- Deleted `runner.py`, `campaign.py`, `reference.py` and `workflow.py` with their tests.
- Moved `INCAR_TAGS` and `echo_check` to `realized.py`, renaming `_echo_check`.
- Added `cso.t3`, a T3 wrapper with no N0 campaign manifest. The `t3` command now
  takes `--z`, `--x`, `--y` and `--output`.
- Removed `null_state`, its OUTCAR moment readers and unused conventions.
- Replaced `/vasp files/` subpath rules in `.gitignore` with the whole folder, and
  added `/pipeline v4/`.
- Cut the tests from 210 cases to 13 and removed unused fixtures.
- Updated AGENTS, DECISIONS (D-015), STATUS, README and CHANGELOG.

Reused: the readers, trace, gates and `validate_rotation`, all unchanged. Removed:
3,331 lines in the first commit, before the test cut.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `python -m pytest -q` in `pipeline v3` | PASS, 13 tests | Baseline at `4f793c5` was 210 passed |
| `python -m pyflakes dmi_pipeline tests` | PASS | Static check only |
| 11 injected faults in a scratch copy | PASS, all caught | Trace, gate, reader and target faults; not exhaustive |
| One manual `t3` run on synthetic rotated dumps | PASS | Unique convention found; mixed builds rejected. No test added |

No VASP run, cluster contact or physical validation.

## Decisions or deviations

Added D-015. The prepared `.gitignore` change drops the old exception that kept the
Patch B spec visible; that spec was never tracked.

## Handoff

- `step1.py` keeps its bond rows and constrained families until TEN-03. Most of
  that code no longer has tests, which is acceptable because it is being removed.
- `trace_config` needs a `provenance.json` that nothing writes now. TEN-04 replaces
  it with the trace vector and restores an N0 command.
- `gate_n0` still has the hard-coded Bi check, also for TEN-04.
- `manifest.require_done` is used only by `trace_config`.
- Next: TEN-02. The repository was still public when this session ended.
