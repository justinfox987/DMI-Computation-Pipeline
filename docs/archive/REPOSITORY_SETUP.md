# Set up the actual project repository

This kit supplies coordination files and the current documents. It contains
neither the application code nor a Git history. Apply it to the existing Python
pipeline directory; do not initialize the temporary ChatGPT document workspace
and call that the code repository.

## 1. Choose the root and preserve the current layout

Open the actual pipeline folder in VS Code. Prefer the directory containing the
Python package, tests and entry points, rather than a parent containing complete
VASP installations and unrelated calculation trees.

Before moving or deleting anything, establish an initial Git baseline. Later
cleanup can be a separate commit with test coverage. Keep a separate backup of
any untracked calculation data; the Git baseline will not contain ignored files.

From a PowerShell terminal in that folder:

```powershell
git --version
git rev-parse --show-toplevel
```

If the second command identifies this project's existing repository, reuse it.
If it identifies an unexpected parent repository, resolve the intended root
before making a nested repository. If it reports that this is not a repository,
initialize here:

```powershell
git init -b main
```

For an existing repository, keep its current default branch/history. Use a
focused setup branch after inspecting existing working-tree changes.

## 2. Merge the starter files

Extract the archive into a temporary folder. Copy the **contents** of
`dmi_repo_starter` into the project root, reviewing collisions in VS Code.
Merge existing AGENTS.md, README.md, ignore rules and attributes; do not
overwrite them wholesale.

Keep the active Step 1 spec at `docs/dmi_step1_implementation_spec.md` and the
math source at `docs/math/heide_math_v2.tex`. The files in `docs/archive` are
unchanged historical snapshots. If the actual repository has newer decisions
or implementation work, reconcile those rather than overwriting them with this
starter snapshot.

Before the initial commit:

- Replace the README's starter-kit notice with the actual repository status.
- Add verified environment, installation, test and CLI commands to README.
- Update STATUS with current branches/owners and any Step 1 work already done.
- Record what can and cannot be tested locally in a new session log.

## 3. Decide what belongs in Git

Track your application code, tests, small fixtures, input templates, specs,
LaTeX source, coordination logs and selected scientific evidence.

Keep bulky calculations, restart files, VASP installation/source trees,
POTCAR datasets and local credentials outside the tracked repository. The
starter ignore rules cover common names, not every possible existing layout.
Add the actual bulk/source directories to the ignore rules before staging.

For an existing repository, ignore rules do not remove already tracked files
or erase history. Inspect existing tracked content before pushing; adding a
pattern alone does not retroactively exclude it.

Review candidates:

```powershell
git status --short --untracked-files=all
git status --short --ignored
```

Stage the coordination files explicitly:

```powershell
git add -- AGENTS.md README.md STATUS.md CHANGELOG.md .gitignore .gitattributes docs evidence
```

For a new repository, also stage the actual source, tests and environment
definition. The following is only an example for the historical package layout:

```powershell
git add -- dmi_pipeline tests run_dmi.py
```

Use paths that actually exist. Include other required source/configuration files
after inspection. On an existing repository, stage only changes belonging to
this setup task; do not sweep another session's changes into it.

Inspect and commit:

```powershell
git diff --cached --stat
git diff --cached --check
git diff --cached
git commit -m "chore: establish DMI repository baseline and handoff docs"
```

If Git needs an author identity, configure the intended identity for this
repository. Do not copy a name/email from another agent or set a machine-wide
identity without intending to.

## 4. Add one private shared remote

Create an empty private repository on your chosen Git host. For an existing
repository, inspect and reuse its intended remote instead of adding another
origin or replacing history.

```powershell
git remote -v
```

For a newly created local repository with no origin, replace the placeholder
below with the chosen repository URL:

```powershell
git remote add origin <YOUR_PRIVATE_REPOSITORY_URL>
git push -u origin main
```

Use the actual branch name if it is not main. A newly created remote should be
empty, without a separately generated README/license commit, to avoid an
unnecessary initial-history conflict.

Every other machine needs a clone and access to that remote. Commits synchronize
through push/fetch/pull; uncommitted changes and chat conversations do not.
Raw scientific data still need their own storage and transfer strategy.

## 5. Keep coordination simple

For sequential work, one task branch is enough:

```powershell
git switch -c feat/dmi-step1-vectors
```

If that branch already exists, continue it instead of creating competing copies.
At the start of a later session inspect status, read STATUS and the latest
session log, then fetch and reconcile the intended remote branch.
Use `git pull --ff-only` only on a branch with the correct upstream and a clean
or otherwise understood working tree. Divergence requires a deliberate merge
or rebase decision, not a hard reset.

For genuinely concurrent tasks on one machine, separate worktrees provide
separate writable checkouts. From an established repository, for example:

```powershell
git worktree add ..\dmi-doc-review -b docs/review main
```

Choose an unused path/branch and the correct integration base. Give agents
nonoverlapping scopes where possible. Two agents should not simultaneously
edit the same working checkout or branch.

A task claim must be visible to its collaborators: push its coordination commit
or communicate the claim before concurrent work starts. A status table is not
an automatic lock. Review and merge task branches into the integration branch;
reconcile STATUS and CHANGELOG during integration. Distinct session files
usually merge without competing edits to one long transcript.

## 6. Use each record for one purpose

| Record | Update when | Keep out of it |
|---|---|---|
| STATUS.md | Starting, pausing, handing off or integrating a task | Full command transcripts |
| docs/sessions/<session>.md | During/end of each substantive session | Invented validation or private chain-of-thought |
| CHANGELOG.md | A meaningful behavior/interface/document change is delivered | Every tiny edit or unsuccessful attempt |
| docs/DECISIONS.md | A durable choice is made or superseded | Temporary guesses presented as settled policy |
| evidence/<record>/ | Actual scientific validation evidence is retained | Bulk restart/dump files and unsupported PASS labels |

Session logs record actions, observations and next steps. They are factual
handoffs, not a request for an agent's hidden reasoning.

## 7. Prompt for Codex in VS Code

Open the real project folder, provide this kit, and use:

> Set up Git-based coordination for this existing DMI project using
> docs/REPOSITORY_SETUP.md. Inspect whether a repository already exists and
> preserve current code layout and unrelated work. Merge the starter instructions,
> status, changelog, decision and session files with any existing equivalents.
> Inspect source/test paths and ignore rules, record baseline tests, and create
> a focused local baseline/setup commit. Update README and STATUS to reflect
> what is actually present. Do not implement the DMI migration during this setup
> task. Report the resulting branch/commit and what remains to connect the chosen
> private remote; do not invent a remote URL or production validation results.

Once setup is complete, start or continue DMI-01 with the prompt at the end of
the Step 1 implementation spec.

## References

- [Git worktrees](https://git-scm.com/docs/git-worktree): separate checkouts for concurrent branches.
- [Git ignore rules](https://git-scm.com/docs/gitignore): exclusion of untracked files, not history removal.
