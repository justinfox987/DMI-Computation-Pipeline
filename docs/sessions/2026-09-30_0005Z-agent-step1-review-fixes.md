# Session: Step 1 independent review corrective follow-up

- Session ID / UTC date: 2026-09-30_0005Z-agent-step1-review-fixes; 2026-09-30 UTC.
- Agent or human / platform: Zoo / Windows 11 local checkout, single writer.
- Task ID and scope: DMI-01, only the five reviewed Step 1 issues: readback/row provenance and q identity; common-z pair geometry; printed penalty/field; OSZICAR/OUTCAR final-loop association; wrapped negative partner.
- Branch: feat/dmi-step1-vectors; no fetch or push.
- Base commit at session start: 7a5931b.
- Working-tree changes already present: no tracked/staged changes; untracked vasp files/ and ignored assets untouched.
- Related spec / prior session: docs/dmi_step1_implementation_spec.md, docs/DECISIONS.md, docs/sessions/2026-09-29_2328Z-agent-dmi-step1-vectors.md.
- Status: local corrective software path complete; production validation remains blocked.

## Work performed

Read full root instructions, status, decisions, spec, last session and template, checkout status/history, Step 1 writer/CLI/tests, N0 manifest hashes and OUTCAR echo. No more-specific tracked instructions found. Changed pipeline v3/dmi_pipeline/step1.py and __main__.py: require matching run and config identity and stored q/targets; reuse manifest fingerprints/check_files and re-read/read-gate before a paired row can trust spins; apply one common rotation for pair validation only, preserving raw kernel vectors; compute precision bounds from printed OSZICAR decimal digits to compare MW_int, E_p and signed factor-two field, distinguishing unavailable from fail/pass; match terminal indexed OSZICAR ionic/electronic steps to the last OUTCAR EDIFF loop, rejecting missing IDs, restarted, incomplete, concatenated or mismatched records; add step1-wrap-partner that only changes q and QSPIRAL for a prepared negative configuration. Fixed OUTCAR iteration ordering (electronic first, ionic second). No trace math, N0 path or VASP inputs/assets altered.

Changed pipeline v3/tests/test_step1.py with synthetic full-file fixtures for gate and CLI prepare/read/row/fit negative cases, Fe excerpt-precision checks, wrapped CLI invariance, stale files/forged gates, printed contradictions, final loop failures, and raw-spin pair checks. Existing 40 tests retained; original Fe excerpts without electronic IDs remain parser-level data and cannot pass final association. Updated docs/STEP1_LOCAL_USAGE.md, STATUS.md and CHANGELOG.md. DECISIONS unchanged because the corrections implement D-001/D-002 and the existing spec, not a new durable physics policy.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `C:\Users\finny\miniconda3\envs\research\python.exe -B -m pytest -q -p no:cacheprovider tests/test_step1.py` (cwd `pipeline v3`) | PASS: 9 passed | Synthetic and Fe-excerpt local software checks only. |
| `C:\Users\finny\miniconda3\envs\research\python.exe -B -m pytest -q -p no:cacheprovider` (cwd `pipeline v3`) | PASS: 44 passed | 35 historical plus nine Step 1; no N0 replay. |
| `git diff --cached --check` and `git diff --check` (cwd `pipeline v3`) | PASS | No whitespace errors; seven intended paths staged, VASP assets unstaged. |
| VASP jobs, BFO production fixtures, production readback/trace/P0/T3 and replica noise/covariance | NOT RUN | No production acceptance or executable identity claimed. |

Development failures were fixture/contract mismatches (Fe excerpt lacks iteration IDs; synthetic Fe formatting too precise for its reported penalty; early tests had nested approx and wrong OUTCAR iteration ordering); fixed and rerun. The final checks above were repeated after staging; Git warned only about Windows CRLF normalization. Seven scoped paths staged and inspected; VASP assets unstaged.

## Decisions or deviations

Fail closed rather than associating an unindexed excerpt or restarted/incomplete run with a passing gate. Consecutive IDs and a single completed OUTCAR segment are evidence checks, not proof that synthetic files correspond to real VASP execution. A deliberate actor can modify/recompute files and records; matching hashes do not authenticate executable or externally supplied trace, bond basis or norm references. No new DECISIONS entry.

## Handoff

- Completed work: focused five-issue offline corrections, local tests, usage and handoff.
- Remaining work / blockers: inspect true production VASP OSZICAR/OUTCAR formatting and final-step association; obtain validated BFO basis, production build/hash, matching parent and Patch B traces, F1 policy, P0/T3, independent noise/covariance. No production jobs submitted.
- Next concrete action: independently review staged diff, then production indexed readback evidence before claiming a run gate; integrate only after repository privacy/synchronization review. Do not push automatically.
- Files another session should read: AGENTS.md, STATUS.md, docs/STEP1_LOCAL_USAGE.md, docs/dmi_step1_implementation_spec.md, pipeline v3/dmi_pipeline/step1.py, pipeline v3/tests/test_step1.py and this log.
- Last tested commit, if available: base 7a5931b plus uncommitted corrections at test time; final focused commit is visible in Git history.
- Uncommitted/unpushed work and where it exists: focused branch will be locally committed if staged review passes; no push. Untracked vasp files/ remains untouched.

The commit containing this log can be found from Git history; no self-referential hash is asserted here.
