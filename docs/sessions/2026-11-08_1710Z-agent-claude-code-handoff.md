# Session: prepare the repository for Claude Code

- Session ID / UTC date: claude.ai session_01RU5FbdnrA8K1yPNmLNi61y, 2026-11-04 to 2026-11-08
- Agent or human / platform: Claude (Opus 5.5), cloud session, with the user
- Task ID and scope: TEN-02 planning, seed file format, and repository handoff; no code change
- Branch: `repo-handoff-prep`, which includes `555a58d` from `feat/spiral-tensors`
- Base commit at session start: `main` at `a0ec0b8`
- Working-tree changes already present: none
- Related spec / prior session: [TEN-01 handoff](2026-11-04_1845Z-agent-ten01-remove-orchestration.md)
- Status: complete

## Work performed

- Prototyped `symmetry.py` in a scratch directory, not committed, to fix the TEN-02
  design. The results, interfaces, guards and expected counts are in
  `plans/ten-02-symmetry.md`.
- Agreed the seed file format with the user: TOML, sites numbered from 1, no
  machine paths, and an optional `spacegroup` check. Recorded in
  `docs/seed_file.md`, D-016 and D-017.
- Added `CLAUDE.md`, which imports `AGENTS.md`, and `materials/fe/seed.toml`.
- Removed `examples/fe-f0-pilot/`: its commands and campaign schema were deleted
  in TEN-01. Moved `plans/perlmutter-fe-pilot-runner.md` to `docs/archive/`, so
  `plans/` holds only current task specs.
- AGENTS: task specs in `plans/`, a spec approved before coding, one branch per
  task from `main`, and the user merges every pull request.
- STATUS: TEN-01 done (PR #7, `a0ec0b8`), TEN-02 ready with its spec, and the
  TEN-01 leftovers for TEN-03 and TEN-04. CHANGELOG: this entry, and a dead
  T4b-2 log link replaced with a note.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `cd "pipeline v3" && python -m pytest -q` | PASS, 13 passed | No code changed; confirms the suite still runs |
| Seed TOML parse of `materials/fe/seed.toml` and the `docs/seed_file.md` example | PASS | Format only; the loader does not exist yet |
| spglib on the spec's BFO and FeGe coordinates | PASS: `R3c`, `P2_13` | Test geometries, not relaxed structures |
| Scratch prototype of the TEN-02 tables | PASS | Prototype only; TEN-02 must reproduce them in the real module |

## Decisions or deviations

D-016 and D-017.

## Handoff

- Completed work: TEN-02 spec, seed format, repository records for Claude Code.
- Remaining work / blockers: TEN-02 implementation; the TEN-03 spec.
- Next concrete command or action: implement TEN-02 from `plans/ten-02-symmetry.md`
  on branch `ten-02-symmetry`.
- Files another session should read: `AGENTS.md`, `STATUS.md`,
  `plans/ten-02-symmetry.md`, `docs/seed_file.md`, math Section 7.
- Last tested commit, if available: `main` at `a0ec0b8` for the code.
- Uncommitted/unpushed work and where it exists: none after this branch is pushed.
