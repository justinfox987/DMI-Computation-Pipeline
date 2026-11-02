# Session: Perlmutter Fe pilot runner T4b-0 — interrupted-work checkpoint

- Session ID / UTC date: 2026-11-02_1618Z (actual system UTC clock; filename retains the requested 2026-10-30 T4b-0 prefix).
- Agent or human / platform: Zoo / Windows 11, research Python.
- Task ID and scope: T4b-0 checkpoint of interrupted T4b work only; verify and commit the current diff. No source/test edits, T4b-1 fixes, VASP, cluster contact, or real sbatch.
- Branch: `feat/dmi-step1-vectors`; one writer; local commit only, no push.
- Base commit at session start: `348f590` (seven commits ahead of the local tracking reference).
- Working-tree changes already present: modified `pipeline v3/dmi_pipeline/runner.py` and `pipeline v3/tests/test_runner.py`; untracked `vasp files/` untouched and unstaged. No other tracked/untracked paths outside `vasp files/` were changed at session start.
- Related spec / prior session: `AGENTS.md`, `STATUS.md`, `docs/DECISIONS.md`, `plans/perlmutter-fe-pilot-runner.md` (T4), `docs/sessions/2026-10-30_2124Z-agent-pilot-runner-t4a-submit-path.md`.
- Status: checkpoint complete only; **T4b is NOT complete**.

## Work performed

- Inspected status, last five commits, diff/stat, T4a handoff and relevant runner/test hunks; ran the requested checks. The source/test diff is checkpointed as found, with no new source/test edits. Full suite green, so the ordering hunk was **kept**, not reverted; T4b-1 still must review and revert it as directed by the follow-up scope.
- The pre-existing `runner.py` diff adds terminal short-circuit for recorded failure statuses instead of changing them to unresolved on missing scheduler history; removes the raise on unresolved in `_advance`; unifies `cache_valid` as the evidence boundary with a `code_identity` seam and pinned plan inputs; uses in-place `plan.update` after generated-reference verification so later cases see the updated plan; saves the ledger per case during reconciliation; and keeps completed finite-q results in a `pending_reference` waiting state until the reference can be checked. It also changes `_plan` to order one ready entry at a time, prioritizing `reference-q0` among peers; that ordering change is unreviewed beyond the local passing suite.
- Existing test expectation edits are in `test_dry_run_submission_and_exact_argv_cwd`, `test_generated_reference_runs_independently_and_blocks_acceptance`, `test_interrupted_submission_never_resubmits_and_lock`, and `test_synthetic_submit_dependencies_keep_science_and_lane_ancestors`. Newly added tests are `test_reference_verified_mid_pass_releases_both_synthetic_gates`, `test_pending_reference_synthetic_resume_releases_without_duplicate_readback`, `test_terminal_failures_remain_terminal_without_scheduler_history`, `test_uncertain_job_is_not_retried`, `test_failed_parent_blocks_descendant_without_new_submission`, `test_blocked_restart_child_waits_for_new_accepted_parent`, `test_rejected_parent_blocks_accepted_child_without_releasing_it`, `test_cached_synthetic_acceptance_invalidates_without_mutating_attempt`, `test_reference_incompatibility_blocks_completed_case_without_readback`, `test_parent_restart_hash_change_invalidates_accepted_child`, `test_live_job_does_not_write_result_or_resubmit_and_readback_only_once`, `test_reconcile_orders_reference_then_execution_parent_then_plan_peers`, `test_scheduler_terminal_synthetic_execution_failure`, `test_completed_missing_outputs_is_readback_failed_and_nonzero_does_not_read`, and `test_crash_on_second_scheduler_lookup_keeps_atomic_ledger_and_releases_lock`.
- Added only this log and one handoff-list line in `STATUS.md`; no CHANGELOG or plan edit. This is preservation of existing work, not review/approval of its design or physical validation.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| cwd workspace: `git status --short --branch && git log --oneline -n 5 && git diff --stat` | PASS: HEAD `348f590`, only two tracked modified files; unrelated untracked `vasp files/` present. Diff: 495 insertions, 140 deletions in two files; CRLF-to-LF working-copy warnings. | No fetch or push; no other paths staged. |
| cwd `pipeline v3`: `C:/Users/finny/miniconda3/envs/research/python.exe -B -m pytest -q -p no:cacheprovider --tb=short` | PASS: **182 passed in 121.89s**, 0 failures. | Current tree including the later ordering edit, synthetic/local software tests only. Earlier intermediate 182-pass report was not independently rerun on its earlier tree; source/test tree is unchanged before vs. after this checkpoint (182 vs. 182). |
| cwd `pipeline v3`: `C:/Users/finny/miniconda3/envs/research/python.exe -B -m py_compile "dmi_pipeline/runner.py" "tests/test_runner.py"` | PASS: exit 0, no output. | Syntax only; no source/test edit. |
| VASP, real sbatch/squeue/sacct, Perlmutter contact or physical gate | NOT RUN. | Out of scope; no production acceptance claim. |

## Decisions or deviations

- No durable decision. Keep the current ordering edit **solely because the full suite is green**, as required by T4b-0; review and revert in T4b-1. Do not infer correctness of ordering or completion of T4b from passing local tests.
- Actual UTC clock reads 2026-11-02; the prescribed 2026-10-30 filename prefix is not a claim that this session ran on October 30.

## Handoff

- Completed work: checkpoint of the already-uncommitted runner/test changes plus this factual log and one STATUS handoff line; no source/test edit during T4b-0.
- Known not done: ordering edit unreviewed and to be reverted in T4b-1; `pending_reference` not yet documented in the runner state-machine comment or `campaign-status`; terminal scheduler state mapping not yet a single table (including DEADLINE/BOOT_FAIL/PREEMPTED/REQUEUED); weak tests (a), (c), (f), (i), (j) to sharpen; risk that `_plan(root)` after an input edit turns a finished job into permanent `readback_failed`; crash window between writing `state.json`/`result.json` and saving the ledger; no T4b hand-off docs; no plan update. **This checkpoint is NOT a completed T4b.**
- Remaining work / blockers: T4b-1..T4b-4 review and repair the above; T5 code/executable provenance and actual Perlmutter physical checks remain outstanding. No real jobs or cluster checks were performed.
- Next concrete action: in T4b-1, inspect and revert the one-entry-at-a-time `_plan` ordering hunk and its matching test expectations, then review the pending-reference/state-machine behavior and rerun the full suite.
- Files another session should read: `pipeline v3/dmi_pipeline/runner.py`, `pipeline v3/tests/test_runner.py`, `plans/perlmutter-fe-pilot-runner.md`, `STATUS.md`, this log and the preceding T4a log.
- Last tested commit, if available: `348f590` plus the pre-existing T4b runner/test working-tree diff; the checkpoint commit containing this log is not identified here in advance.
- Uncommitted/unpushed work and where it exists: intended local checkpoint commit includes exactly the two existing edits, this log and `STATUS.md`; after commit only the unrelated untracked `vasp files/` should remain. Local branch is not pushed.
