# Generate, submit and read one Fe F0 pilot on Perlmutter

Finish and test the generator locally, transfer/install the code, then generate
the actual pilot on Perlmutter. The Windows `artifacts/local/` pilot is a
generator fixture. Cluster material inputs, launch template and executable
belong on the cluster and are not prerequisites for local software completion.
This runbook describes a later user submission; no calculation was submitted
while implementing or testing it.

## Existing functionality and explicit interfaces

| Operation | Interface / ownership |
|---|---|
| Material and electronic inputs | `step1-prepare --inputs PATH`; directory contains POSCAR, INCAR, KPOINTS, POTCAR |
| Scientific target settings | `--recipe PATH`; required q, signs, seeds, lambda, radii, family and site map |
| Launch template | `--job-template PATH`; copied unchanged to output/job.sh; never discovered in the current directory |
| Executable and launch resources | Supplied working template; for the sequence below it consumes exported `VASP_EXECUTABLE` |
| Run output directory | Preparation `--output PATH`; later passed to sbatch as working directory |
| Readback paths | `step1-read --config PATH --run PATH --references PATH --output PATH` |

The existing target generator and writer produce config, INCAR.step1 and full
INCAR from one generated tag dictionary. Generated magnetic tags override the
base INCAR; other base settings remain explicit in the shared INCAR. Required
material files are copied unchanged, and a nonempty destination is rejected.
Without `--job-template`, shared inputs may still be generated for review, with
an explicit message; a job.sh in the current directory is ignored. An explicit
missing template fails before output creation. Script contents are not rewritten
or executed by preparation.

There is no Python submission command to configure: the launch approach is the
supplied script plus ordinary sbatch. A second scheduler or shell rewriter is
unnecessary for this single pilot. The executable setting belongs to the launch
template, rather than the magnetic recipe or INCAR.

## Inputs and unresolved choices

Choose these on Perlmutter before the generation command:

- A Python >=3.11 environment with the project's NumPy dependency, the transferred
  code checkout, and explicit absolute paths in the next section.
- A reviewed Fe POSCAR/site map, species-ordered POTCAR and KPOINTS. Shared INCAR
  supplies ENCUT/ENINI, bands, convergence, smearing, restart and parallel tags.
  ENINI is supported by the same tag whitelist used at preparation and readback.
- A reviewed recipe. The [local example](../evidence/2026-10-19-fe-f0-preparation/recipe.json)
  is an F0 candidate with q=(0.25,0,0), positive signs on both Fe sites, seeds 2.2,
  RWIGS 1.5 and lambda 1. These are configurable choices, not accepted defaults.
  G-type signs must be requested explicitly if intended. F0 requires LZEROZ T.
- Resolve the old finite-q warning: ENINI=550 eV required ENMAX >575.402 eV while
  the old run used 550 eV. Select and validate ENCUT/ENINI deliberately; no cutoff
  is silently raised. Reconcile NCORE/KPAR with the working GPU allocation.
- This sequence is for a cold pilot: shared INCAR must request ISTART=0 and
  ICHARG=2. Other restart choices need their actual parent/restart files staged
  separately; preparation does not infer or copy restart files.
- Independent verified M_int and MW_int reference norms in magnetic-site order,
  with the same sphere definitions/RWIGS and compatible structure/DFT settings.
  `references.json` has two arrays named `M_int` and `MW_int`. Do not infer them
  from the pilot itself or automatically reuse the historical Fe values after
  changing numerical settings.
- A working cluster launch script with the actual account, queue, walltime,
  ranks, GPUs, threads, modules and binding. Keep its working MPI/GPU launch
  options. It must run one foreground VASP invocation in the selected run
  directory, preserve a failure exit code, and avoid changing to an old hardcoded
  directory or redirecting VASP outputs to another run. These are cluster checks.

For explicit executable selection in the commands below, the reviewed template
must consume `VASP_EXECUTABLE`. It can require the variable before its existing
launch command:

```bash
: "${VASP_EXECUTABLE:?Supply the cluster VASP executable}"
test -x "$VASP_EXECUTABLE"
```

Use `"$VASP_EXECUTABLE"` as the executable operand in that existing launch
command, retaining its resource/binding arguments. Exporting a variable does
not override a binary path hardcoded in a script. If the working script instead
uses a site module/container wrapper, configure its executable there explicitly
and adapt the executable-identity recording accordingly. Preparation does not
require a local copy of the binary, inspect its libraries, or authenticate it.

## Perlmutter generation sequence

Transfer the committed code using the project's approved method. Retain the
`pipeline v3/` package and the reviewed recipe; obtain licensed material and
executable assets on the cluster. Do not transfer the Windows environment or
reuse Windows state JSON as live cluster provenance. Set these example path
values to real absolute Perlmutter paths; no account or executable is inferred:

```bash
set -euo pipefail
export REPO='/absolute/cluster/path/to/checkout'
export PYTHON='/absolute/cluster/path/to/python-environment/bin/python'
export MATERIAL='/absolute/cluster/path/to/fe-shared-inputs'
export RECIPE='/absolute/cluster/path/to/reviewed-fe-f0-recipe.json'
export JOB_TEMPLATE='/absolute/cluster/path/to/working-job.sh'
export VASP_EXECUTABLE='/absolute/cluster/path/to/vasp_ncl'
export PILOT='/absolute/cluster/path/to/new-fe-f0-plus'
export REFERENCE_JSON='/absolute/cluster/path/to/verified-references.json'
export STATE='/absolute/cluster/path/to/readback/fe-f0-plus-state.json'

"$PYTHON" -m pip install -e "$REPO/pipeline v3"
"$PYTHON" -c 'import sys, numpy; assert sys.version_info >= (3, 11)'
test -f "$RECIPE"
test -s "$MATERIAL/POSCAR"
test -s "$MATERIAL/INCAR"
test -s "$MATERIAL/KPOINTS"
test -s "$MATERIAL/POTCAR"
test -s "$JOB_TEMPLATE"
test -x "$VASP_EXECUTABLE"

"$PYTHON" -B -m dmi_pipeline step1-prepare \
  --recipe "$RECIPE" \
  --inputs "$MATERIAL" \
  --job-template "$JOB_TEMPLATE" \
  --output "$PILOT"

"$PYTHON" -m json.tool "$PILOT/config.json"
cat "$PILOT/INCAR"
cmp "$JOB_TEMPLATE" "$PILOT/job.sh"
bash -n "$PILOT/job.sh"
git -C "$REPO" rev-parse HEAD > "$PILOT/pipeline-commit.txt"
sha256sum "$VASP_EXECUTABLE" > "$PILOT/executable.sha256"
sha256sum "$PILOT/job.sh" "$PILOT/POSCAR" "$PILOT/INCAR" \
  "$PILOT/KPOINTS" "$PILOT/POTCAR" "$PILOT/config.json" \
  > "$PILOT/prepared-inputs.sha256"
```

Inspect the recipe, final INCAR, template and identities before submission.
Syntax checking is not an MPI/GPU smoke test. This generates a fresh run with
no expected OUTCAR/OSZICAR yet. Repeat preparation only to a new empty directory
when changing inputs; do not edit generated magnetic tags separately from the
recipe/config. A local absence of these cluster paths is not a software blocker.

## Later user submission using the working template

Execute this section only when ready to submit the reviewed pilot. It preserves
the resource requests and launch body of the supplied template. Submission is
from the pilot so a template using SLURM_SUBMIT_DIR sees that directory; chdir
and scheduler output paths are also explicit:

```bash
submission=$(
  cd "$PILOT"
  sbatch --parsable \
    --chdir="$PILOT" \
    --export=ALL \
    --output="$PILOT/slurm-%j.out" \
    --error="$PILOT/slurm-%j.err" \
    "$PILOT/job.sh"
)
printf '%s\n' "$submission" > "$PILOT/submission-id.txt"
job_id="${submission%%;*}"
squeue -j "$job_id"
```

The exported executable variable is inherited by the batch environment. The
flags and working-directory behavior follow the official
[Slurm sbatch reference](https://slurm.schedmd.com/sbatch.html); NERSC's
[job examples](https://docs.nersc.gov/jobs/examples/) explain the site launch
context. The copied working template remains the source of actual resources.
Submission success means a job ID was assigned, not that VASP completed.
After the job leaves the queue, inspect scheduler logs/accounting and the VASP
OUTCAR/OSZICAR in PILOT. Keep the files and their locations for readback.

## Readback after completion

Run with the same selected Python environment and explicit cluster paths.
Use a fresh state path so a previous file cannot be mistaken for a new result:

```bash
test -f "$REFERENCE_JSON"
test ! -e "$STATE"
sha256sum "$REFERENCE_JSON" > "$PILOT/reference-input.sha256"
read_status=0
"$PYTHON" -B -m dmi_pipeline step1-read \
  --config "$PILOT/config.json" \
  --run "$PILOT" \
  --references "$REFERENCE_JSON" \
  --output "$STATE" || read_status=$?
printf 'step1-read exit status: %s\n' "$read_status"
if test -f "$STATE"; then
  "$PYTHON" - "$STATE" <<'PY'
import json, sys
with open(sys.argv[1]) as source:
    state = json.load(source)
print(json.dumps(state['gate'], indent=2))
PY
else
  printf '%s\n' 'No new state: inspect the input, parsing or convergence error above.'
fi
```

Exit 0 means this realization gate passes. Exit 1 with a newly written state
records a physical gate rejection; exit 1 without a state indicates an input,
parsing or convergence failure. Retain weighted alignment, norm drift and penalty
rejections. Signed factor evidence and the field/penalty same-update identity
remain distinct; production source/build evidence is still required.

The generated config has no stored source-machine paths. Readback fingerprints
and absolute paths are created on the machine that performs the read, using the
supplied config/run arguments. Read on Perlmutter for cluster provenance. If
later moving raw files to another host, rerun readback there to create new
host-bound state; do not hand-edit paths/hashes in an old state for row reuse.

## Verification boundary

Locally verified: package CLI argument handling, explicitly selected paths,
ignored current-directory job.sh, byte-preserved template/material copies,
generated magnetic consistency, ENINI whitelist/echo handling, and synthetic
prepare-to-readback including chosen output directories. Existing real-file Fe
readback remains historical evidence, not a run of this new pilot.

Requires Perlmutter: Python/environment installation there, real material and
template paths, executable hash/build provenance, template syntax and job
resource agreement, environment export and filesystem access on compute nodes,
MPI/GPU launch, convergence, correct physical realization and compatible
independent reference norms. Local tests neither need these assets nor establish
those results. This single-pilot path does not complete trace/parity, paired-row,
BFO, or production campaign acceptance.
