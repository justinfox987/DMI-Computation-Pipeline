# Magnetic tensors from VASP spin spirals

This project computes the spiralization tensor $\mathcal D$, the stiffness tensor
$A$ and exchange classes from SOC-free spin spirals in VASP, then uses them to
predict magnetic properties. It covers materials with one magnetic order
parameter: ferromagnets and collinear patterns of site signs.

The project has moved away from bond-resolved DMI vectors. The current state,
including what has and has not been tested on VASP output, is in
[STATUS.md](STATUS.md) and nowhere else.

## What it computes

| Quantity | Source | Needs Patch B |
|---|---|---|
| Spiralization $\mathcal D$ | First-order SOC trace on paired spirals at small $q$ | Yes |
| Stiffness $A$ | SOC-free total energies at small $q$ | No |
| Exchange classes $J_c$ | SOC-free total energies on a coarse $q$ grid | No |
| Anisotropy $K$ | Self-consistent SOC runs at $q=0$ (later module) | No |

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

Each material is one folder under `materials/` with a POSCAR and a `seed.toml`
([format](docs/seed_file.md)). The commands are `plan` and `prepare`, which
take the seed path, then `collect`, `dumps` and `fit`, which take the run
directory. `dumps` writes one CSO dump per material, and `fit` traces every run
from the dump files each time it runs. Run them as `python -m dmi_pipeline <command>`; none submits a job.

## Where to look

| File or folder | Purpose |
|---|---|
| [AGENTS.md](AGENTS.md) | Instructions agents read at the start of work; `CLAUDE.md` imports it |
| [STATUS.md](STATUS.md) | Current state, task ownership, blockers and next actions |
| [CHANGELOG.md](CHANGELOG.md) | Meaningful changes to code, interfaces and documents |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Durable choices and why they were made |
| [docs/sessions/](docs/sessions/) | One factual handoff log per session |
| [plans/](plans/) | One spec per task, written and approved before coding |
| [docs/seed_file.md](docs/seed_file.md) | Format of the per-material seed file |
| [materials/](materials/) | One folder per material, with its seed and inputs |
| [Math source](docs/math/heide_math_v3.tex) | Revision 3.2; the only copy of the mathematics |
| [Agent notes](docs/math/heide_math_v3.md) | Module map and the rules that must not drift |
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

This needs Python 3.11 or later. Install into a virtual environment at the
repository root; system Python on Ubuntu and WSL refuses `pip install`. From the
repository root:

```text
python3 -m venv .venv
source .venv/bin/activate
cd "pipeline v3"
python -m pip install -e ".[test]"
python -m pytest -q
```

If `venv` is missing, install it with `sudo apt install python3-venv`. Activate
the environment in each new shell, and use `.venv/bin/python` from scripts.

This runs a deliberately small test suite. Passing it says nothing about VASP
results. `spglib` is installed with the package, for `symmetry.py`.

The math source is standalone LaTeX. From `docs/math`:

```text
latexmk -pdf -outdir=build heide_math_v3.tex
```

Generated build products belong in the ignored build directory. Keep the source
as the authoritative document; publish a compiled PDF deliberately when needed.

VASP runs need the Patch B build for the trace, and licensed POTCAR files, which
stay outside this repository.
