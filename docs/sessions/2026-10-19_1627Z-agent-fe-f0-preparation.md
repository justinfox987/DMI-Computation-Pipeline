# Session: one Fe F0 pilot preparation

- Session ID / UTC date: 2026-10-19_1627Z-agent-fe-f0-preparation; 2026-10-19 UTC.
- Agent or human / platform: Codex / Windows local checkout.
- Task ID and scope: DMI-02 preparation only; inspect existing writers, fill missing shared-material assembly, and prepare one reviewable F0 Fe pilot. No scheduler, VASP submission or execution.
- Branch: `feat/dmi-step1-vectors`; one writer. Initial HEAD matches local `origin/feat/dmi-step1-vectors`, without a fetch or remote-state verification.
- Base commit at session start: `6b9c342`.
- Working-tree changes already present: only untracked `vasp files/` assets; preserved. Root AGENTS.md is the only applicable AGENTS.md found.
- Related spec / prior session: [Step 1 spec](../dmi_step1_implementation_spec.md), [logical readback handoff](2026-10-19_1556Z-agent-step1-logical-readback.md); archive runner/materializer documents inspected for context, with current physical conventions retained.
- Status: preparation complete as a review-only local candidate; working launch script and calculation choices require review before a runnable pilot is claimed.

## Work performed

Inspected `pipeline v3/dmi_pipeline/{__main__,step1,realized,workflow,manifest}.py`, Step 1 callers/tests and original Fe material files. The existing `prepare` already generates physical targets, seeds, constraint tags and schema-3 config. `write_inputs` already writes config/INCAR.step1 and rejects a nonempty destination. The archived v2 materializer can copy material files, but depends on older schemas, conventions and dependencies; it cannot directly serve the current schema-3 path. Archived probe helpers and job scripts do not establish a usable launch for these runs.

Extended only the live preparation command and its existing writer. `step1-prepare` now accepts either existing `--poscar` fragment mode or `--inputs` shared-material mode. Shared mode parses the base INCAR using existing `realized.incar`, rejects unreviewed tags using existing `workflow.INCAR_TAGS`, merges generated tags over inherited values, and copies POSCAR/KPOINTS/POTCAR unchanged. Required files are read/checked before output creation; shared POSCAR identity is checked against the generated config. Missing/empty inputs and nonempty destinations fail. Config, INCAR.step1 and full INCAR all derive from the same generated record; no second target formula, parser, data model or dependency was added.

The user clarified: assume working job.sh will be in the current directory when they generate F0. Shared preparation copies that file by default when present; optional `--job-template` selects an explicit script. Script bytes are preserved, never parsed into a new scheduler or executed. Missing default job.sh permits material preparation with an explicit review-only message; exit 0 means input writing succeeded. An explicitly named missing template fails before output. The checkout contains no working template: the archived HEIDE-STUFF/job.sh is fully commented, and other discovered scripts are examples, probe submission code or dummy fixtures. No placeholder script was invented.

Prepared ignored `artifacts/local/2026-10-19-fe-f0-pilot/shared/` from q0 POSCAR/KPOINTS/POTCAR and reader_test_2 INCAR, changing only SYSTEM in the copied base to Fe-F0-pilot-review. The original source files remain unchanged. Added the tracked [recipe](../../evidence/2026-10-19-fe-f0-preparation/recipe.json), then invoked the public preparation CLI to write ignored `artifacts/local/2026-10-19-fe-f0-pilot/F0-plus/`. This contains all four VASP input files plus config/fragment and review notes; no local job.sh or VASP outputs. The [review record](../../evidence/2026-10-19-fe-f0-preparation/README.md) supplies settings, sources, hashes and the missing requirements. Usage, STATUS and CHANGELOG were updated.

The candidate uses F0, positive side, q=(0.25,0,0), ferromagnetic signs (+,+), seeds 2.2, RWIGS 1.5 and lambda 1.0. Targets are Fe1 `(1,0,0)`, Fe2 `(0.70710678118655,0.70710678118655,0)`; the second MAGMOM is `(1.55563491861,1.55563491861,0)`. These signs follow the supplied ferro reference as a review candidate, rather than silently imposing G-type signs. All other electronic settings come from the historical sample: cold ISTART=0/ICHARG=2, ALGO All, EDIFF 1e-7, ENCUT 550, NBANDS 56, mesh 5x5x5, SIGMA 0.05, NCORE=16/KPAR=4. Lambda and numerical settings are not production-validated by preparation.

Remaining decisions: the original finite-q OUTCAR warned that ENINI=550 requires ENMAX >575.402 eV while current ENMAX is 550. That inherited cutoff needs an ENCUT/ENINI decision and numerical validation, potentially with a matching new q0 reference. Resource tags need reconciliation with the eventual GPU job.sh. The exact executable path/hash, modules, account and binding are absent locally and must come from the working template/environment. No acceptance thresholds were changed and no realization/trace/binary acceptance was asserted.

## Verification

Python command prefix below is `C:/Users/finny/miniconda3/envs/research/python.exe`; cwd is `pipeline v3`.

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `-B -m pytest -q -p no:cacheprovider tests/test_step1.py --tb=short` outside restricted sandbox | PASS: 20 tests, including material/tag consistency, explicit/default script copying, missing script review-only output, missing potential, and overwrite rejection. | Before final empty-INCAR guard addition; final suite below includes that guard. Synthetic potential and job are labelled test data. |
| `-B -m pytest -q -p no:cacheprovider --tb=short` outside restricted sandbox | PASS: 55 tests on final code. | Local software regression only; includes legacy fragment mode and the new empty-INCAR failure check. |
| `-B -m dmi_pipeline step1-prepare --recipe ../evidence/2026-10-19-fe-f0-preparation/recipe.json --inputs ../artifacts/local/2026-10-19-fe-f0-pilot/shared --output ../artifacts/local/2026-10-19-fe-f0-pilot/F0-plus` | PASS for input writing, exit 0; explicitly reports missing current-directory job.sh and review-only status. | A complete set of VASP input files, not a verified runnable launch. |
| Python using existing `incar`, `numbers`, `manifest.file_hash`, NumPy and byte comparisons | PASS: all config tags match final INCAR; MAGMOM/M_CONSTR match generated vectors, three material copies match bytes; no OUTCAR/OSZICAR/restarts/job.sh. | Input consistency, not calculated moments or convergence. |
| `rg` searches of local scripts / archived materializers | Working launch template absent locally; existing generation and parsing reused as described. | Searches encountered inaccessible historical pytest cache directories, unrelated to source/scripts. |
| `git diff --check`, source hash checks, staged path review | PASS; source sample files preserved, no assets or local POTCAR staged. | Documentation/preservation check. |
| VASP run, scheduler submission, real job syntax/executable validation | NOT RUN. | User expressly requested preparation only; actual working script absent locally. |

## Decisions or deviations

No new scientific convention. The shared writer modestly extends existing preparation rather than importing the archived materializer. Missing default job.sh is explicit review-only output; the user expects to provide it in the current directory later. The recipe's q/signs/lambda and inherited numerical settings are documented candidates, with cutoff/resource choices unresolved.

## Handoff

- Completed work: existing-path inventory, shared-input assembly and template copying, one local F0 Fe input directory, focused regression and full suite, settings/provenance review.
- Remaining work / blockers: local working job.sh absent; cutoff and resource choices unresolved; exact executable identity unavailable. No physical gate or production acceptance exists for the new pilot.
- Next concrete action: review the candidate settings, resolve the spiral cutoff, and regenerate to a new empty output from a directory containing working job.sh (or pass an explicit template). Submission requires a later user request.
- Files another session should read: this log, [preparation review](../../evidence/2026-10-19-fe-f0-preparation/README.md), recipe, local pilot INCAR/config, current `step1-prepare` CLI and `write_inputs`.
- Last tested commit, if available: `6b9c342` plus this preparation change; tests ran before its focused commit.
- Uncommitted/unpushed work and where it exists: preparation code/tests/usage, evidence recipe/review, STATUS/CHANGELOG and this log pending local commit at log creation. Actual pilot/shared inputs are ignored; original `vasp files/` assets remain untracked. No push in this session.
