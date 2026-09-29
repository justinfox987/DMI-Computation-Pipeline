# Session: DMI Step 1 local lab-vector software migration

- Session ID / UTC date: 2026-09-29_2328Z-agent-dmi-step1-vectors; 2026-09-29 UTC.
- Agent or human / platform: Zoo / Windows 11 local checkout, one writer.
- Task ID and scope: DMI-01 offline target writer, sphere reader, vector row and diagnostic numerical fit; no production jobs or BFO acceptance.
- Branch: `feat/dmi-step1-vectors`, created from committed local baseline `56288bfd726ebc15eafc57e59a0d74cbca03de11`; `main` and `origin/main` still initial `e2b85cb`. No fetch or push.
- Base commit at session start: `56288bfd726ebc15eafc57e59a0d74cbca03de11`.
- Working-tree changes already present: no tracked/staged modifications; untracked `vasp files/` (38 visible paths, plus ignored distributions and local output) untouched and unstaged.
- Related spec / prior session: `docs/dmi_step1_implementation_spec.md`, `docs/math/heide_math_v2.tex` Revision 2.4, `docs/DECISIONS.md`, `docs/sessions/2026-09-29_2024Z-agent-baseline-finalization.md`.
- Status: complete for an **offline software subset**; production Step 1 acceptance and BFO fit blocked.

## Work performed

Inspected root instructions, STATUS, decisions, full spec and math, latest handoff/template, branch/history/status, tracked N0 workflow, POSCAR/INCAR parser, gates, manifest, trace boundary and tests. Baseline 35 software tests passed. Scope stated before editing; no more-specific tracked repository instructions found. Created a focused branch from the audited local commit without merging it into main.

Added `pipeline v3/dmi_pipeline/step1.py`: lab targets and reflected partners using direct POSCAR coordinates and explicit two-ion signed mapping; fixed SAXIS/mode-1 inputs, supplied RWIGS/LAMBDA/F1 policy; schema-3 convention records; terminal OSZICAR sphere moments and printed penalty/field; matching INCAR/OUTCAR echo plus single-run final-EDIFF checks and file hashes; signed M_int and absolute MW_int geometry, separate magnitude references, optional common-z geometry-only adjustment, factor-two field diagnostic, measured partner checks; one canonical cell-translation kernel shared by direct target planning and measured paired rows; diagnostic weighted rank-checked solve. Reused the existing POSCAR/INCAR parser, atomic JSON/hashes, OUTCAR echo checker and NumPy. No BFO symmetry generator, speculative parameters, production uncertainty estimates, job submission, new spin-axis rotation or trace math change. Historical schema-2 N0 records and OUTCAR-based null-state implementation remain byte-for-byte and functionally unchanged; the legacy unwound constant is isolated to its N0 diagnostic label and not a Step 1 switch.

Extended `pipeline v3/dmi_pipeline/__main__.py` with offline Step 1 prepare/read/row/fit commands; added `pipeline v3/tests/test_step1.py` with independent Fe excerpt oracles, signed failures, canonical intrabond energy and commensurate average, q-wrap checks and synthetic CLI integration; added `docs/STEP1_LOCAL_USAGE.md` with input contract and archived probe supersession notice. Updated STATUS and CHANGELOG only for this work. No durable new scientific decision beyond D-001 through D-004; DECISIONS unchanged. No archive or VASP asset edits.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `C:\Users\finny\miniconda3\envs\research\python.exe -B -m pytest -q -p no:cacheprovider` (working directory `pipeline v3`, before edits) | PASS: 35 passed | Existing local N0 software regression, no N0 replay. |
| `C:\Users\finny\miniconda3\envs\research\python.exe -B -m pytest -q -p no:cacheprovider` (working directory `pipeline v3`, after changes) | PASS: 40 passed | 35 existing plus 5 Step 1 local tests, synthetic entry-point integration, Fe excerpt parser only. |
| `git diff --check`; `git diff --cached --check`; `git diff --cached --stat`; focused staged review | PASS | No whitespace errors; exactly seven scoped files staged, zero VASP assets. |
| VASP jobs, production N0 replay, BFO basis/T3/P0 and paired replica covariance | NOT RUN | No production-acceptance evidence invented. |

During development the new tests initially exposed test fixture ion-count errors, a recipe metadata NameError, and a combined shell command whose semicolon was passed as an argument in this terminal. All were corrected or rerun with standalone commands; no pre-existing baseline test failed. Tests do not prove physics or accepted trace convergence.

## Decisions or deviations

The tracked checkout has no vetted canonical BFO bond/orbit basis or nine-parameter fixture and no accepted paired trace/noise evidence. Therefore a synthetic supplied-basis/uncertainty diagnostic solver is provided, never an accepted production BFO fit. The Step 1 trace input CLI accepts separately supplied labelled trace energies instead of certifying synthetic values as Patch B traces; the existing indexed trace implementation is reused conceptually and remains untouched. Future production wiring must enforce actual Patch B completion, T3/P0 and covariance before declaring acceptance. The historical N0 `FRAME_MINT` declaration is left as forensic metadata rather than changing old record meaning. OSZICAR reader parses final excerpts for diagnostics but `step1-read` rejects concatenated/ambiguous run segments and requires independent final OUTCAR EDIFF and echoed tags. Old records are rejected instead of converted without original sphere evidence. See usage guide for limitations.

## Handoff

- Completed work: local testable offline writer/readback/gate/canonical row/weighted diagnostic entry points and usage, preserved N0 and assets.
- Remaining work / blockers: vetted production BFO canonical symmetry basis/9-parameter fixture; real matching parent POSCAR, RWIGS and F1 LZEROZ choice; build hash and zero-target source evidence; converged paired Patch B traces/validated full-operator axes, P0 thresholds, paired replicas/covariance and production validation. Parser excerpts are not convergence evidence. Current CLI numerical fit is not an accepted scientific result.
- Next concrete action: inspect this branch's staged diff and merge the baseline locally only after integration/remote privacy reconciliation; source and independently validate the BFO bond basis and production run/trace evidence before extending acceptance gates or claiming a BFO fit. Do not stage `vasp files/` or submit VASP jobs in Step 1.
- Files another session should read: `AGENTS.md`, `STATUS.md`, `docs/STEP1_LOCAL_USAGE.md`, `docs/dmi_step1_implementation_spec.md`, `docs/DECISIONS.md`, `pipeline v3/dmi_pipeline/step1.py` and this log.
- Last tested commit, if available: baseline `56288bf` plus uncommitted Step 1 edits at test time; exact final commit determined by Git after focused review.
- Uncommitted/unpushed work and where it exists: this session's scoped edits reside on the local Step 1 branch until focused commit; branch has not been pushed. Existing untracked VASP assets and ignored distributions remain untouched.

The commit containing this log can be found from Git history. No self-referential commit hash is asserted here.
