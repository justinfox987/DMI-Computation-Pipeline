# Session: audit and preserve current repository baseline

- Session ID / UTC date: 2026-09-29_2003Z-agent-baseline-audit; 2026-09-29 UTC
- Agent or human / platform: Zoo / Windows 11 local workspace
- Task ID and scope: REPO-01 baseline audit and preservation handoff only; no DMI-01 implementation, physics changes or VASP jobs.
- Branch: started on `main` tracking `origin/main`; created `docs/repo-baseline-audit` from that commit for these handoff documents only.
- Base commit at session start: `e2b85cb422e327e0c17268b56ede5a79a649fd79` (`Initial project commit`, 2026-09-29 13:45:46 -04:00). `main` and local `origin/main` both point to this commit. Configured origin at time of audit: `https://github.com/justinfox987/DMI-Computation-Pipeline.git` (fetch/push); no network fetch or remote privacy check performed.
- Working-tree changes already present: tracked and staged diffs empty; `git status --short --branch` showed only `?? "vasp files/"`. `git ls-files --others --exclude-standard -z` returned 6,504 untracked paths (not a count of ignored files): 1 under `vasp files/.roo`, 12 under `vasp files/vasp-6.4.2-heide-gpu`, 24 under `vasp files/vasp-heide-patch`, 3,236 under `vasp files/vasp-heide-patch-NEW`, 3,231 under `vasp files/vasp.6.4.2-heide-cpu`. These are pre-existing user material, not part of the Git baseline; nothing in these trees was moved, deleted, staged or edited. The ignored local run directories `pipeline v3/noq/ref`, `pipeline v3/noq/dump-C`, and `pipeline v3/noq/dump-P0` also exist; they were not touched. The existing ignore rules do not cover the entire `vasp files/` tree.
- Related spec / prior session: `docs/dmi_step1_implementation_spec.md`, math Revision 2.4, `docs/DECISIONS.md`, `docs/sessions/2026-09-29-bootstrap.md`. The bootstrap report had no code checkout and is not evidence of current source.
- Status: complete for audit; Step 1 implementation not started here.

## Work performed

Read in full the root `AGENTS.md`, `STATUS.md`, `docs/DECISIONS.md`, and `docs/dmi_step1_implementation_spec.md`, plus `docs/sessions/TEMPLATE.md` and the latest prior session. Searched for narrower `AGENTS.md` files (none found). Inspected the untracked `vasp files/.roo/rules/windows.md` instruction without editing it, the project manifest, active package, tests, ignore rules, setup instructions, and examples of the separate untracked source/assets. No application code or evidence was changed.

Observed source baseline: `pipeline v3/pyproject.toml` defines Python >=3.11, NumPy >=1.24 and optional pytest >=8; CLI `pipeline v3/dmi_pipeline/__main__.py` exposes N0 acceptance commands (`init-null`, `finish`, `trace`, `status`, `gate`, `t3`). `pipeline v3/dmi_pipeline/workflow.py` handles N0 registration, completion, recorded convergence evidence, and the null trace; `pipeline v3/dmi_pipeline/realized.py` reads OUTCAR projected final moments only for N0. `pipeline v3/dmi_pipeline/dumpio.py`, `trace.py`, `cso.py` and `gates.py` implement Patch B dump parsing, first-order trace and local checks, with operator rotation gated by T3 evidence. `pipeline v3/dmi_pipeline/conventions.py` still declares `FRAME_MCONSTR = FRAME_MINT = "unwound"`. A search over tracked Python source found no live Step 1 target writer, OSZICAR `M_int`/`MW_int` reader, vector bond kernel, paired-row assembly, or fit CLI. That absence describes this checkout, not other machines or untracked historical work; DMI-01 is not complete. The N0 OUTCAR parser is not an OSZICAR production readback.

Tracked `acceptance/manifest.json` records historical N0 PASS for its recorded files and checks; this audit did not rerun the recorded VASP workflow. The manifest points to local ignored `pipeline v3/noq/` reference/dump run directories, which exist, but its `pipeline v3/acceptance/cso` and `pipeline v3/acceptance/configs/n0` paths do not exist at their recorded locations; root `acceptance/` contains tracked snapshots. The committed README and setup guide still say there is no application code/Git repository; that starter-kit wording is stale and should be corrected in a separately scoped documentation integration. No build hash or production gate was newly verified.

Edited only `STATUS.md` and this new session log to record the observed baseline and next action. No CHANGELOG entry (no meaningful interface/code/spec change) and no DECISIONS entry (no durable scientific or workflow choice changed).

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `git status --short --branch`; `git branch -vv`; `git log -6 --date=iso-strict --format="%H %ad %an %s"`; `git remote -v`; `git rev-parse --show-toplevel` | PASS | Local branch/base/history/remote identity inspected; no fetch/push. |
| `git diff --stat`; `git diff --cached --stat`; `git ls-files --others --exclude-standard -z` (counted by read-only Python subprocess) | PASS | Before edits, no tracked/staged changes; 6,504 untracked file paths, excluding ignored material. |
| `C:\Users\finny\miniconda3\envs\research\python.exe -B -c "import sys,pytest,numpy;print(sys.version);print('pytest',pytest.__version__);print('numpy',numpy.__version__)"` | PASS | Python 3.11.15, pytest 9.1.1, NumPy 2.4.6 in specified local environment. |
| `C:\Users\finny\miniconda3\envs\research\python.exe -B -m pytest -q -p no:cacheprovider` (working directory `pipeline v3`) | PASS: 35 passed in 2.54s | Local synthetic fixture/software tests only; no Step 1 integration test or VASP validation. Pytest temp artifacts remain outside source. |
| Read-only Python inspection of tracked `acceptance/manifest.json` path existence | OBSERVED | Recorded N0 PASS and existing local run directories; referenced cso/config directories absent at recorded locations, so historical result not freshly revalidated. |
| VASP runs, production executable hash, BFO campaign, Step 1 acceptance and T3 genuine-dump revalidation | NOT RUN | Outside this audit; no new scientific gate claims. |

The initial combined Git command failed because this terminal passed a PowerShell-style semicolon as part of a Git option; the commands were rerun separately and succeeded. A PowerShell-only directory/date command likewise failed in this `cmd.exe` terminal; subsequent queries used compatible commands. These were tool/shell invocation failures, not test failures.

## Decisions or deviations

None. Retained the existing baseline commit, historical evidence, other owners' unassigned queue and untracked/ignored work. Used an isolated documentation branch instead of modifying `main`; did not stage, commit, fetch, push or change ignore rules.

## Handoff

- Completed work: actual Git/code/test inventory, preservation record and updated `STATUS.md`; no migration code.
- Remaining work / blockers: decide how to keep the large untracked VASP source/assets and ignored run outputs outside future commits; reconcile stale README/setup wording; establish intended owner and branch for DMI-01; implement/test Step 1 separately. Production build identity, reference and numerical/constraint inputs remain unresolved as recorded in STATUS and spec.
- Next concrete command or action: review this log and `STATUS.md`, then make a separate scoped DMI-01 task claim/branch after coordination; use the Step 1 spec and inspect existing N0 implementation before editing. Do not stage `vasp files/` by accident.
- Files another session should read: `AGENTS.md`, `STATUS.md`, `docs/DECISIONS.md`, `docs/dmi_step1_implementation_spec.md`, this log, and `pipeline v3/pyproject.toml` plus the N0 package/tests.
- Last tested commit: `e2b85cb422e327e0c17268b56ede5a79a649fd79`; tests preceded the documentation-only edits.
- Uncommitted/unpushed work and where it exists: this session's `STATUS.md` and this log on `docs/repo-baseline-audit` (not staged/committed/pushed); all pre-existing untracked `vasp files/` and ignored local run directories remain in this checkout, untracked/ignored and unsynchronized by this audit.
