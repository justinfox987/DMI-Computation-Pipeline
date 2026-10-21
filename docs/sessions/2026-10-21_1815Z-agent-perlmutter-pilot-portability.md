# Session: explicit Perlmutter pilot preparation and readback interfaces

- Session ID / UTC date: 2026-10-21_1815Z-agent-perlmutter-pilot-portability; 2026-10-21 UTC.
- Agent or human / platform: Codex / Windows local checkout.
- Task ID and scope: DMI-02 single-pilot portability; finish the applicable local generator interfaces, document cluster generation/launch/readback, remove current-directory script assumptions. No calculations or cluster submission.
- Branch: `feat/dmi-step1-vectors`; one writer, one commit ahead of local tracking reference at start; no fetch/push.
- Base commit at session start: `bbea7ef`.
- Working-tree changes already present: only untracked `vasp files/` assets; preserved. Root AGENTS.md is the only applicable AGENTS.md found.
- Related spec / prior session: [Step 1 spec](../dmi_step1_implementation_spec.md), [single-pilot preparation](2026-10-19_1627Z-agent-fe-f0-preparation.md), [Perlmutter sequence](../PERLMUTTER_F0_PILOT.md).
- Status: complete within the local single-pilot interface scope; real cluster checks remain unperformed.

## Work performed

Inspected current CLI preparation, writer, recipe generation, shared INCAR parsing/whitelist, external job-template ownership, package entry point, manifest hashes and readback/row provenance. Material, recipe, template, generated output, run, references and state already accept caller paths. `pyproject.toml` supports installation and an installed `dmi` command; the Python runtime contains no fixed Windows input/output/executable paths. The Windows interpreter example in current usage was documentation, and is now replaced with selected-environment commands.

The user clarified that the local F0 directory is a generator test and that the actual pilot will be generated and run on Perlmutter after transfer. Removed the three-line current-directory job.sh fallback from the existing preparation CLI. A template is now included only through `--job-template PATH`; otherwise preparation reports review-only inputs, even if a job.sh exists in the caller's directory. Explicit missing-template failure and all existing writer behavior remain. No new launcher, scheduler, executable wrapper, parser or configuration schema was introduced.

Executable configuration stays with the existing working launch script. The runbook gives an explicit exported `VASP_EXECUTABLE` contract, without rewriting its MPI/GPU options, and uses ordinary sbatch with explicit working/log paths. Scripts that hardcode a binary do not acquire a different executable merely by exporting a variable; that contract must be reviewed on the cluster. Cluster-only scripts, potentials and binaries need not exist on the development host. Synthetic template tests preserve an unresolved executable environment variable without accessing or executing a real binary.

A concrete configurability gap was found in the shared INCAR whitelist: ENINI was not accepted, despite the known unresolved ENCUT/ENINI choice. Verified its read path in supplied VASP `src/reader.F:412` and added this supported tag to existing `workflow.INCAR_TAGS`, which is used by both preparation and echo checking. No value/default was selected; typo ENINII remains rejected. No VASP source or numerical acceptance criteria changed.

Extended the existing shared-input regression: explicit script copied byte-for-byte; working-directory job.sh ignored when not requested; explicit absent template rejected before writing; ENINI retained; unknown ENINII rejected; generated full INCAR/config/targets consistent; synthetic completion reaches the existing readback gate using independently supplied synthetic references and a chosen state path from another working directory. The synthetic launcher is never run. Other existing tests retain physical rejection and field/penalty behavior.

Added [PERLMUTTER_F0_PILOT.md](../PERLMUTTER_F0_PILOT.md) with the exact later sequence: supply cluster paths and reviewed inputs, install using selected Python, generate from shared inputs plus explicit template, inspect/record identities, submit the supplied script using sbatch, then read OUTCAR/OSZICAR with explicit config/reference/state paths. It handles a template using SLURM_SUBMIT_DIR by submitting from the pilot as well as setting chdir. The commands are documentation only. Consulted official [Slurm sbatch](https://slurm.schedmd.com/sbatch.html) and [NERSC job examples](https://docs.nersc.gov/jobs/examples/) for submission semantics; no resource requests/account were guessed.

Readback needs no new portability adapter. Config stores target/POSCAR identity without the development source path; a new cluster read uses its supplied runtime paths to create cluster absolute-path fingerprints. Old host-bound state should be regenerated from raw files after relocation rather than edited for row reuse. Updated current usage, STATUS, CHANGELOG, [D-006](../DECISIONS.md) and a dated clarification atop the old generator evidence record. Historical session logs remain historical.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| cwd `pipeline v3`: `C:/Users/finny/miniconda3/envs/research/python.exe -B -m pytest -q -p no:cacheprovider tests/test_step1.py --tb=short` outside sandbox | PASS: 20 focused tests. | Before final ENINII rejection assertion; final suite below covers it. No VASP executable used. |
| Same cwd/interpreter: `-B -m pytest -q -p no:cacheprovider --tb=short` outside sandbox | PASS: 55 total tests on final code. | Synthetic material preparation-to-readback and existing physical gate regressions; not Perlmutter execution. |
| Extracted four Bash blocks from the runbook into ignored `artifacts/local/2026-10-21-portability-check/runbook-block-1.sh` through `-4.sh`; ran `C:/Program Files/Git/bin/bash.exe -n` on each | PASS outside sandbox: four syntax-valid blocks. | Syntax only: no command within the blocks, sbatch, executable or cluster check was executed. |
| Same Bash syntax check inside sandbox | ENVIRONMENT ERROR: Git Bash could not create its signal pipe (Win32 error 5). | Reran syntax-only check outside sandbox successfully. |
| `rg` of live package paths, supplied VASP reader and current usage; `git diff --check`, staged review | PASS: no fixed Windows runtime paths; ENINI source path located; only relevant code/tests/docs changed. | Runtime state paths deliberately bind to the machine performing readback. |
| Perlmutter installation, real template syntax/resources, executable identity, MPI/GPU launch, real convergence and physical readback | NOT RUN. | Requires real cluster; missing local copies of these assets are not local software blockers. |

## Decisions or deviations

[D-006](../DECISIONS.md) records the user's cluster-generation boundary and supersedes implicit current-directory job discovery. Kept the existing launch approach and executable ownership in the working script; no redundant Python executable argument or scheduler was added. Scientific recipe/base-INCAR values remain explicit caller choices.

## Handoff

- Completed work: explicit template-only preparation, ENINI input/echo support, synthetic portability regression, portable usage and exact cluster runbook, verification/limitations recorded.
- Remaining work / blockers: no local software blocker for this single-pilot path. On Perlmutter, select/verify material inputs, q/signs/lambda/cutoffs, compatible independent norm references, working template/executable identity and resources, then install/generate and perform actual cluster checks. Full trace/paired/BFO campaign acceptance remains separate and incomplete.
- Next concrete action: transfer the committed code using the approved method, follow the runbook with real cluster paths and reviewed settings; submission requires the user's later action/request. Do not transfer the local pilot as the production run or reuse Windows state provenance.
- Files another session should read: runbook, this log, D-006, current `__main__.py`/`workflow.py`, shared-input test, Step 1 usage and spec.
- Last tested commit, if available: `bbea7ef` plus this focused change; tests ran before its commit.
- Uncommitted/unpushed work and where it exists: relevant code/tests/docs/session pending local commit at log creation. Bash syntax scratch files are ignored; original VASP assets stay untracked. No push or cluster submission.
