# Session: Perlmutter Fe pilot runner T4b-1 — ordering revert

- Session ID / UTC date: 2026-11-02_1629Z (system UTC clock; filename retains the requested 2026-10-30 task prefix).
- Agent or human / platform: Zoo / Windows 11, research Python.
- Task ID and scope: T4b-1 only: restore the original planning order and test generated-plan ordering through reconciliation; no T4b-2 work.
- Branch: `feat/dmi-step1-vectors`; single writer; local commit only, no push.
- Base commit at session start: `27116d6` (T4b-0 checkpoint on `348f590`).
- Working-tree changes already present: only untracked `vasp files/`; untouched and unstaged.
- Related spec / prior session: `AGENTS.md`, `STATUS.md`, `docs/DECISIONS.md`, `plans/perlmutter-fe-pilot-runner.md`, `docs/sessions/2026-10-30_1618Z-agent-pilot-runner-t4b0-checkpoint.md`.
- Status: complete for T4b-1 only; T4b remains incomplete.

## Work performed

- Compared `git diff 348f590 27116d6 -- "pipeline v3/dmi_pipeline/runner.py" "pipeline v3/tests/test_runner.py"` and inspected `git show 348f590:"pipeline v3/dmi_pipeline/runner.py"`. Restored only `ordered.extend(ready)` in `_plan`, removing the one-at-a-time `reference-q0` priority/comment. The old loop collects ready entries in plan order, appends a complete layer, then discovers children in the next layer: deterministic and parent-first. `campaign.py` inserts generated `reference-q0` at plan index 0; it therefore runs before consumers with either ordering. Reference verification's in-place `plan.update` remains necessary for same-pass release, but does **not** depend on the one-at-a-time order. Kept input verification and all other checkpoint fixes.
- Restored the T4a expectation in `test_synthetic_submit_dependencies_keep_science_and_lane_ancestors`: `plus`, `other`, `minus`; peer `other` has `afterany:10001`; child `minus` has `afterok:10001,afterany:10001:10002`. Left the generated-reference submission-order assertion in place because it holds for a real generated plan under both orderings; the pending-reference and ledger assertions are not ordering edits.
- Replaced `test_reconcile_orders_reference_then_execution_parent_then_plan_peers` (private `_plan` and hand-reordered impossible plan) with parametrized `test_generated_reference_and_execution_parent_reconcile_in_one_pass`. It prepares a real generated-reference campaign with the existing `execution_parents` option (`minus` depends on `plus`), submits to the fake scheduler, completes all jobs synthetically and calls public `runner.status` once. Wrappers call the real reference verification and readback while recording `reference-q0`, `plus`, `minus` order. Both pass/fail parent outcomes assert verified reference first, parent accepted/rejected before child accepted/blocked, correct readback sequence, no premature child readback, and no waiting when the reference completes in the same pass. This test passed with both old and new ordering; it guards behavior rather than detecting the revert. Existing `test_failed_parent_blocks_descendant_without_new_submission` and `test_rejected_parent_blocks_accepted_child_without_releasing_it` also cover parent blocking.
- No plan edit: the current plan has no one-at-a-time ordering description. No CHANGELOG entry or change to unrelated checkpoint behavior.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| cwd root: `git status --short --branch && git log --oneline -n 4 && git branch --show-current && git diff 348f590 27116d6 -- "pipeline v3/dmi_pipeline/runner.py" "pipeline v3/tests/test_runner.py"`; `git show 348f590:"pipeline v3/dmi_pipeline/runner.py"` | PASS: HEAD `27116d6`, branch correct; original layer-by-layer ready-list ordering verified. | No existing tracked edits; no fetch/push. |
| cwd `pipeline v3`, before edit: `C:/Users/finny/miniconda3/envs/research/python.exe -B -m pytest -q -p no:cacheprovider --tb=short` | PASS: **182 passed**, 0 failures (122.68s). | Local synthetic/software tests only. |
| cwd `pipeline v3`, replacement test before ordering revert: `C:/Users/finny/miniconda3/envs/research/python.exe -B -m pytest -q -p no:cacheprovider --tb=short tests/test_runner.py -k generated_reference_and_execution_parent_reconcile_in_one_pass` | PASS: **2 passed, 45 deselected** (12.66s). | Behavior guard passes with checkpoint ordering. |
| cwd `pipeline v3`, after revert: `C:/Users/finny/miniconda3/envs/research/python.exe -B -m pytest -q -p no:cacheprovider --tb=short` | PASS: **183 passed**, 0 failures (150.68s); +1 net from replacing one test with two parameter cases. | Behavior guard also passes with restored ordering. |
| cwd `pipeline v3`: `C:/Users/finny/miniconda3/envs/research/python.exe -B -m py_compile "dmi_pipeline/runner.py" "tests/test_runner.py"` | PASS: exit 0. | Syntax only. |
| cwd root: `git diff --check && git diff -- "pipeline v3/dmi_pipeline/runner.py" "pipeline v3/tests/test_runner.py" && git status --short --branch` | PASS: diff contains only the ordering revert, three restored ordering-sensitive assertion lines and test replacement; no whitespace errors. | Git reported Windows CRLF-to-LF working-copy warnings, not diff errors. |
| VASP, real sbatch/squeue/sacct, Perlmutter, physical gates | NOT RUN. | Explicitly out of scope. |

## Decisions or deviations

- No durable decision. The generated-reference submission-order assertion from the checkpoint is retained because its observation comes from real campaign preparation and does not depend on the removed priority. Nothing else in the checkpoint depended on that priority.

## Handoff

- Completed work: T4b-1 ordering-only revert, real-plan reconcile behavior guard, local verification and focused commit of `runner.py`, `test_runner.py`, this log and one `STATUS.md` line.
- Remaining work / blockers: T4b-2 waiting-state docs/status output and terminal-state table; T4b-3 sharpen tests and review status assignments; T4b-4 `_plan(root)` input-edit risk and crash window. T5 provenance and production VASP/cluster validation are separate and not done.
- Next concrete action: begin T4b-2 in a separate scoped session; do not infer production readiness from local tests.
- Files another session should read: `pipeline v3/dmi_pipeline/runner.py`, `pipeline v3/tests/test_runner.py`, `plans/perlmutter-fe-pilot-runner.md`, `STATUS.md`, this log.
- Last tested commit, if available: `27116d6` plus the scoped T4b-1 working-tree diff; the commit containing this log can be found in Git history.
- Uncommitted/unpushed work and where it exists: after the intended local commit, only unrelated untracked `vasp files/` should remain; local branch not pushed.
