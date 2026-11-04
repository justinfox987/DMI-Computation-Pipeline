# Magnetic tensors from VASP spin spirals

This project computes the spiralization tensor $\mathcal D$, the stiffness tensor
$A$ and exchange classes from SOC-free spin spirals in VASP, then uses them to
predict magnetic properties. It covers materials with one magnetic order
parameter: ferromagnets and collinear patterns of site signs.

**Status: mid-pivot.** The project has moved away from bond-resolved DMI vectors.
The code in `pipeline v3/` still implements that earlier workflow. The new
workflow below is specified but not yet implemented, and no VASP calculation has
tested it. See [STATUS.md](STATUS.md) for the current state.

## What it computes

| Quantity | Source | Needs Patch B |
|---|---|---|
| Spiralization $\mathcal D$ | First-order SOC trace on paired spirals at small $q$ | Yes |
| Stiffness $A$ | SOC-free total energies at small $q$ | No |
| Exchange classes $J_c$ | SOC-free total energies on a coarse $q$ grid | No |
| Anisotropy $K$ | Standard SOC static runs at $q=0$ | No |

From these the code predicts the spiral period, spin plane and texture class,
along with magnon stiffness, a mean-field ordering temperature and spiral
stability. Results are harmonic and first order in SOC; the
[math document](docs/math/heide_math_v3.tex) states the limits.

## How it works

1. Read a structure and a magnetic sign pattern, and find the symmetry operations
   that apply.
2. Count the allowed tensor components, then choose $q$ points that determine them.
3. Run unconstrained flat spirals at $\pm q$ and capture the SOC-free state.
4. Form the trace vector from the on-site density matrix and SOC operator.
5. Fit the tensors, test them against symmetry, and evaluate the predictions.

The planned commands are `plan`, `prepare`, `status`, `collect` and `fit`. None of
them exists yet.

## Where to look

| File or folder | Purpose |
|---|---|
| [AGENTS.md](AGENTS.md) | Instructions agents read at the start of work |
| [STATUS.md](STATUS.md) | Current state, task ownership, blockers and next actions |
| [CHANGELOG.md](CHANGELOG.md) | Meaningful changes to code, interfaces and documents |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Durable choices and why they were made |
| [docs/sessions/](docs/sessions/) | One factual handoff log per session |
| [Math source](docs/math/heide_math_v3.tex) | Revision 3.0; the authoritative foundation |
| [Math for agents](docs/math/heide_math_v3.md) | Same numbering, plus module map and rules |
| [pipeline v3/](pipeline%20v3/) | Python package `dmi_pipeline` and its tests |
| [acceptance/](acceptance/) | Historical Patch B N0 record |
| [evidence/](evidence/) | Small selected validation records and links to external run data |
| [docs/archive/](docs/archive/) | Older supporting documents, with authority limitations |

Revision 2.4, the Step 1 specification and the Perlmutter pilot documents remain
for history and are superseded for current work. The bond-era code state is at
tag `archive/bond-dmi-v3`.

## Daily workflow

Read STATUS → choose/continue a task branch → edit and test → update the session
log and relevant shared records → commit → synchronize the branch to the remote.
Another computer or agent must fetch/checkout that branch to see its commits.
Git does not transfer uncommitted files or supply the private context of a chat.

Use one hosted repository as the shared integration point. Start with one active
coding task. Introduce separate worktrees only when concurrent work is actually
useful; do not require a worktree for every ordinary session.

## Local setup and tests

This needs Python 3.11 or later. From the repository root:

```text
cd "pipeline v3"
python -m pip install -e ".[test]"
python -m pytest -q
```

This runs a deliberately small suite of 13 tests. Passing them says nothing about
VASP results. `spglib` becomes a dependency when `symmetry.py` is added.

The math source is standalone LaTeX. From `docs/math`:

```text
latexmk -pdf -outdir=build heide_math_v3.tex
```

Generated build products belong in the ignored build directory. Keep the source
as the authoritative document; publish a compiled PDF deliberately when needed.

VASP runs need the Patch B build for the trace, and licensed POTCAR files, which
stay outside this repository.
