# DMI extraction with VASP

This project extracts bond Dzyaloshinskii–Moriya vectors from paired SOC-free
spin spirals and first-order SOC traces.

**Starter-kit status:** this folder contains the project documents and
coordination files. It does not contain the application code, an initialized
Git repository, or a hosted remote. Merge it into the actual pipeline checkout
using [the setup guide](docs/REPOSITORY_SETUP.md).

## Where to look

| File or folder | Purpose |
|---|---|
| [AGENTS.md](AGENTS.md) | Instructions agents read at the start of work |
| [STATUS.md](STATUS.md) | Current state, task ownership, blockers and next actions |
| [CHANGELOG.md](CHANGELOG.md) | Meaningful changes to code, interfaces and documents |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Durable choices and why they were made |
| [docs/sessions/](docs/sessions/) | One factual handoff log per session |
| [Step 1 spec](docs/dmi_step1_implementation_spec.md) | Current code-migration contract |
| [Math source](docs/math/heide_math_v2.tex) | Revision 2.4; editable LaTeX foundation |
| [docs/archive/](docs/archive/) | Older supporting documents, with authority limitations |
| [evidence/](evidence/) | Small selected validation records and links to external run data |

Keep the existing package, scripts and tests in place for the initial import.
Directory cleanup should be a later change with its own verification.

## Daily workflow

Read STATUS → choose/continue a task branch → edit and test → update the session
log and relevant shared records → commit → synchronize the branch to the remote.
Another computer or agent must fetch/checkout that branch to see its commits.
Git does not transfer uncommitted files or supply the private context of a chat.

Use one private hosted repository as the shared integration point. Start with
one active coding task. Introduce separate worktrees only when concurrent work
is actually useful; do not require a worktree for every ordinary session.

## Local setup and tests

These commands are **not yet established from the current codebase**. During
integration, replace this section with the verified environment, installation,
test and CLI commands. Do not copy an old environment or historical PASS count
as though it were current evidence.

The math source is standalone LaTeX. From `docs/math`, a local build can use:

```text
latexmk -pdf -outdir=build heide_math_v2.tex
```

Generated build products belong in the ignored build directory. Keep the source
as the authoritative document; publish a compiled PDF deliberately when needed.
