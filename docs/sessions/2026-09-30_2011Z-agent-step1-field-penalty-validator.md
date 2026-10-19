# Session: Step 1 field and penalty validator follow-up

- Session ID / UTC date: 2026-09-30_2011Z-agent-step1-field-penalty-validator; 2026-09-30 UTC.
- Agent or human / platform: Codex / Windows local checkout.
- Task ID and scope: DMI-01, apply the field/penalty source finding to the existing Step 1 diagnostic only; no VASP change or run.
- Branch: `feat/dmi-step1-vectors`, tracking `origin/feat/dmi-step1-vectors`, ahead one local commit; no fetch or push.
- Base commit at session start: `b9a3b095957eacca9261fc6b84f99251c3eb3ebc`.
- Working-tree changes already present: modified `STATUS.md` and `CHANGELOG.md`, untracked prior 1919Z and 1933Z audit logs, and untracked `vasp files/`; all preserved. No more-specific AGENTS.md found.
- Related spec / prior session: [math Revision 2.4](../math/heide_math_v2.tex) Section 4, [Step 1 spec](../dmi_step1_implementation_spec.md) Section 5.2, and [source audit](2026-09-30_1933Z-agent-step1-field-penalty-source-audit.md).
- Status: complete as a local software diagnostic change; no production VASP validation.

## Work performed

Updated the authoritative `validate` path in `pipeline v3/dmi_pipeline/step1.py` and its focused test, the Step 1 implementation spec and offline usage, plus STATUS/CHANGELOG. Reused the existing `read_state` binding of requested LAMBDA to run INCAR/OUTCAR echo and the existing printed-precision intervals. The diagnostic now uses that requested value rather than treating the coarser OSZICAR lambda rendering as independent coefficient uncertainty. The output names its coefficient source; the effective runtime value still requires source/build evidence. The source audit supports a fixed 1.0 for the inspected code path but does not authenticate the sample executable.

`field_check.status` now concerns only signed factor-two evidence against printed `MW_int`. `field_check.identity` separately records field-implied and printed penalty intervals, their overlap or positive gap, and an unavailable same-update status. The validator does not infer update association from `CGA` text or from the presence of one terminal block. Thus an interval gap remains visible without becoming an unexplained field-factor failure, and interval overlap is not called a same-update PASS. Physical weighted alignment, printed penalty threshold, and the separate `penalty_check` remain active. No tolerance was widened and no new parser/parallel calculation path was added.

The regression uses the original Fe lambda=1 printed values in synthetic indexed files: `MW_int,y=±0.044`, signed field `±0.088629`, and `E_p=0.0039272` eV. It asserts factor-two/sign support, an unavailable same-update interpretation, a disjoint identity with approximately `2.55506125e-7` eV minimum gap, and unchanged alignment/penalty failures. The synthetic electronic line is `CGA`; the code gives it no automatic exemption. Existing zero-field and older Fe-excerpt tests were updated to the distinct diagnostic meanings. The original VASP files were not copied into a tracked fixture, edited, or rerun.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| cwd `pipeline v3`: `C:/Users/finny/miniconda3/envs/research/python.exe -B -m pytest -q -p no:cacheprovider tests/test_step1.py --tb=short` outside sandbox | PASS: 18 focused tests. | Local software path; includes the CGA-format printed-value regression, not production binary verification. |
| cwd `pipeline v3`: `C:/Users/finny/miniconda3/envs/research/python.exe -B -m pytest -q -p no:cacheprovider --tb=short` outside sandbox | PASS: 53 tests. | Local suite only; run before a final test-line change from DAV to CGA, followed by the focused rerun above. |
| Same focused command inside sandbox, then with `--basetemp .pytest_step1_codex_20260930` | ENVIRONMENT ERROR: pytest could not access default or workspace temporary directories; no test assertions ran. | Reran outside sandbox; the temporary workspace directory created by the failed attempt was verified inside the workspace and removed. |
| `git diff --check`, diff/status inspection | PASS: no tracked whitespace errors; existing audit and VASP assets retained. | No staging, commit or push. |
| VASP/sample rerun, production gate, source/binary authentication | NOT RUN. | Outside request and still unavailable. |

## Decisions or deviations

No new scientific convention. The same-update identity is observational until update association is evidenced. The Step 1 spec and usage now state that limitation and the supplied source timing explanation without applying a CGA-wide exception.

## Handoff

- Completed work: separated signed factor evidence from numerical identity in the existing diagnostic, retained the known printed gap, updated tests and documentation.
- Remaining work / blockers: exact executable/source identity and per-update full-precision moments are unavailable; a complete schema-3 read of the original Fe run lacks independent matching references. No production acceptance is claimed.
- Next concrete action: obtain authenticated source/build and, if strict identity is required for a run, establish the moment update used by each print before assigning a same-update pass/fail. Keep existing physical realization gates.
- Files another session should read: this log, the source audit, `pipeline v3/dmi_pipeline/step1.py`, `pipeline v3/tests/test_step1.py`, Step 1 spec and offline usage.
- Last tested commit, if available: `b9a3b095957eacca9261fc6b84f99251c3eb3ebc` with local uncommitted changes under test.
- Uncommitted/unpushed work and where it exists: code, test, spec, usage, STATUS, CHANGELOG and this log are local unstaged changes; preceding audit docs and untracked VASP assets remain local. No push.
