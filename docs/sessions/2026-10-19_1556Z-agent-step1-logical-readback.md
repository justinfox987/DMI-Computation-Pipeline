# Session: Step 1 logical input comparison and direct Fe readback

- Session ID / UTC date: 2026-10-19_1556Z-agent-step1-logical-readback; 2026-10-19 UTC.
- Agent or human / platform: Codex / Windows local checkout.
- Task ID and scope: DMI-01; compare equivalent Step 1 INCAR logical values by meaning, reject invalid values, and repeat full real-file readback with the unmodified prepared config. No VASP or acceptance-threshold change.
- Branch: `feat/dmi-step1-vectors`, tracking `origin/feat/dmi-step1-vectors`, ahead three local commits at start; no fetch or push.
- Base commit at session start: `170f1c9`.
- Working-tree changes already present: only untracked `vasp files/` assets; preserved. No more-specific AGENTS.md found.
- Related spec / prior session: [Step 1 implementation spec](../dmi_step1_implementation_spec.md), [q0 reference/readback](2026-10-05_2030Z-agent-step1-q0-readback.md), and [evidence record](../../evidence/2026-10-05-fe-q0-step1-readback/README.md).
- Status: complete local input-comparison fix and real-file readback; historical Fe realization gate still fails.

## Work performed

Inspected `step1.read_state`, the existing `realized.logical` parser and its N0 callers, the CLI, test fixture and q0 evidence. `realized.logical` already accepts T/F, TRUE/FALSE and dotted variants, raises `ValueError` for invalid values, and has no implicit conversion of arbitrary strings. The authoritative Step 1 reader now uses that parser for LNONCOLLINEAR, LSORBIT, LSPIRAL and LZEROZ from both requested config and run INCAR. It retains the existing missing-tag check and mismatched-input error. Numeric and other tag comparisons are unchanged. No duplicate parser, new option or alternate readback path was added.

Added one focused synthetic readback test in `tests/test_step1.py`: the generated T/F config accepts all four historical True/False run tags; opposite LSORBIT, invalid run LSORBIT and invalid requested LZEROZ still fail. Existing Step 1 tests and full local suite pass. Updated [local usage](../STEP1_LOCAL_USAGE.md), the [evidence follow-up](../../evidence/2026-10-05-fe-q0-step1-readback/README.md), STATUS and CHANGELOG. The original 2026-10-05 spelling-adjusted config and state remain forensic evidence of the prior code behavior.

The full `step1-read` command used the unchanged [prepared/config.json](../../evidence/2026-10-05-fe-q0-step1-readback/prepared/config.json) and existing independent [references.json](../../evidence/2026-10-05-fe-q0-step1-readback/references.json) against the original `reader_test_2` run. It reached realization checks and wrote ignored local `artifacts/local/2026-10-05-fe-q0-step1-readback/state-prepared.json` (SHA-256 `28f10cc939d6fd70a34ad2535d60b66166e9dac13179cacf6accc5e0d9337530`). Its gate object and measured moment/penalty/field readback equal those of the earlier spelling-adjusted state. The CLI exits 1 for the same physical reasons:

| Check | Result |
|---|---|
| Input/config and OUTCAR/OSZICAR association | PASS; final sample step `(1,32)` |
| Signed M_int geometry and transverse phase | PASS; 0.83693 degrees per ion, 1 degree limit |
| M_int/MW_int directional agreement | PASS; below 1 degree |
| Absolute MW_int alignment | FAIL; 1.39101 degrees per ion, 1 degree limit |
| M_int norm drift versus q0 reference | FAIL; 6.01788% per ion, 5% limit |
| MW_int norm drift versus q0 reference | PASS; 3.10206% per ion, 5% limit |
| Printed E_p versus printed MW_int precision | PASS |
| Physical printed penalty | FAIL; 0.0039272 eV, 0.001 eV limit |
| Signed factor-two field | PASS at printed precision |
| Field/penalty identity | UNAVAILABLE as a same-update check; intervals disjoint by at least 2.55506125e-7 eV at lambda 1 |
| Overall realization | FAIL: two weighted-alignment reasons, M_int magnitude drift, and printed penalty threshold |

The supplied source's cached-penalty/later-moment timing explanation remains limited by the missing sample executable/source identity. No CGA-wide exception or tolerance change was made. The original VASP files retain the hashes in the [earlier evidence record](../../evidence/2026-10-05-fe-q0-step1-readback/README.md), and neither the generated config nor q0 references were edited.

## Verification

Commands below ran from `pipeline v3` with `C:/Users/finny/miniconda3/envs/research/python.exe` unless noted.

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `-B -m pytest -q -p no:cacheprovider --basetemp ../artifacts/local/pytest-step1-logical-20261019 tests/test_step1.py --tb=short` inside sandbox | ENVIRONMENT ERROR: pytest could not access its temporary fixture directory; no useful assertion outcome. | Reran outside the restricted sandbox. |
| `-B -m pytest -q -p no:cacheprovider tests/test_step1.py --tb=short` outside sandbox | PASS: 19 focused tests, including the new logical-value regression. | Local software only. |
| `-B -m pytest -q -p no:cacheprovider --tb=short` outside sandbox | PASS: 54 total tests. | Local software only. |
| `-B -m dmi_pipeline step1-read --config ../evidence/2026-10-05-fe-q0-step1-readback/prepared/config.json --run '../vasp files/sample-files/reader_test_2' --references ../evidence/2026-10-05-fe-q0-step1-readback/references.json --output ../artifacts/local/2026-10-05-fe-q0-step1-readback/state-prepared.json` | Reached realization gate, wrote state; exit 1 with the same four physical reasons. | Unmodified generated config and original VASP run, no VASP rerun. |
| Python JSON comparison of new and prior local states | PASS: gate objects and measured M_int, MW_int, E_p, lambda and signed fields equal. | Config provenance and hashes intentionally differ. |
| `git diff --check`, Git diff of generated config, `Get-FileHash` of original VASP files, `git check-ignore` of new state | PASS: no whitespace issue; prepared config unchanged, original run hashes unchanged, state ignored. | Local preservation check. |

## Decisions or deviations

None. Reused the established strict logical parser and retained all physical acceptance criteria. The successful pytest runs required execution outside the restricted filesystem sandbox because temporary fixtures were denied inside it.

## Handoff

- Completed work: strict boolean equivalence in Step 1 input comparison, focused rejection coverage, full direct readback with unchanged prepared config, and documentation.
- Remaining work / blockers: historical Fe state still fails physical realization. Exact GPU executable/source identity and production BFO prerequisites remain unavailable.
- Next concrete action: use a newly converged physically aligned parent if pursuing an accepted Step 1 row; retain this failed sample as diagnostic evidence.
- Files another session should read: this log, `pipeline v3/dmi_pipeline/{step1,realized}.py`, focused test, the [q0 evidence record](../../evidence/2026-10-05-fe-q0-step1-readback/README.md), prepared config, and ignored local state.
- Last tested commit, if available: `170f1c9` plus this uncommitted fix; tests and CLI ran before the focused commit.
- Uncommitted/unpushed work and where it exists: code, test, usage, evidence follow-up, STATUS, CHANGELOG and this log pending local commit at log creation; ignored state remains local and `vasp files/` remains untracked. No push.
