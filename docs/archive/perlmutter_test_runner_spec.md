# Perlmutter full-test staging script: implementation spec

Status: design only; no jobs have been generated or submitted.

Final implementation sequence and resolved pilot changes:
[next_steps.md](next_steps.md). The production constraint rerun is specified in
[constraint_probe_v2_protocol.md](constraint_probe_v2_protocol.md).

## 1. Deliverable and scope

Build one small Python entry point, `stage_full_test.py`, around the v3
materialization and validation functions. It stages the internal test bundle
in [full_test_data_requirements.md](full_test_data_requirements.md), sections
1–7. Rev 2 remains authoritative. T9 needs a separately agreed protocol.

The first release prepares only the pilot, then launches with one command:

```bash
python stage_full_test.py prepare --scope pilot --config campaign.json --root full_test
cd full_test
sbatch jobsall.sh
```

After pilot review, `prepare --scope full --resume` expands the same campaign
with the pinned settings; `sbatch jobsall.sh` launches its missing bulk work.
These are proposed commands, not existing functionality. `jobsall.sh` is a
short submission job: it submits the calculation jobs and validation barriers,
records their IDs, and exits. Each calculation gets its own allocation using
the supplied working `job.sh`. Its completion means **submission finished**;
only the final validation report means the campaign finished.

Use individual jobs and explicit dependencies. At this scale, arrays, a
persistent scheduler, a database, and a general workflow framework add little.
Keep scheduler code in this script; scientific checks belong in `dmi_pipeline`.

## 2. Inputs and generated files

`campaign.json` supplies only campaign-specific information:

- Reference directory containing the accepted production inputs and restart
  files; existing N0 evidence and the production z-axis CSO.
- Path to the working `job.sh`, Python environment, and actual VASP executable
  used by its launcher. Snapshot and hash these inputs.
- Validated Fe/Bi/O RWIGS and the material/frame convention evidence.
- Explicit replica initialization protocol and any independent seed paths it
  requires; see section 6. Never silently label repeated identical starts as noise.
- Maximum concurrent calculation jobs (initial default: 4), SCF-chain walltime,
  and short controller/gate walltimes. Resource requests otherwise inherit the
  working template. Optional small CPU controller/gate template is permitted.

The q/family/scan tables come from the requirements document and should be
encoded once as a short, visible table. Print the expanded plan for inspection.
Do not require the user to enter every individual case.

```text
full_test/
  campaign.json                 # resolved settings, absolute paths, hashes
  plan.json                     # case IDs, target parameters, parents, gates
  jobsall.sh                    # the only user-facing submission script
  stage_full_test.py            # fixed snapshot of the entry point
  templates/job.sh              # original working template, preserved
  jobs/<id>.sh                  # generated Slurm wrappers
  inputs/                      # shared immutable material inputs
  runs/<id>/
    scf/lambda_<value>/         # F0 uses scf/unconstrained/
    dump_P/
    result.json                # per-case completion and evidence
  validation/material/dump_C_<axis>/
  validation/f1_policy/<variant>/
  gates/<name>.json
  logs/
  submissions.json             # job IDs and submission state
  report.json
  return_files.txt
```

Freeze the v3 code version used by the campaign as well as the script. The
manifest must identify that version; a mutable local checkout is insufficient.
F1 production entries may exist in `plan.json` before policy selection, but
their VASP inputs must not be materialized until the policy is pinned. Explicit
CP policy/frame comparison cases are permitted as labelled diagnostic runs;
their candidate settings must never become implicit production defaults.

## 3. Calculation sets and actual parallelism

A **configuration job** owns one parity side: its SCF/ramp, realization checks,
and one projection dump run sequentially in one allocation. It reserves enough
walltime for the worst permitted ramp plus the dump. Plus/minus are separate
jobs with separate restart ancestry.

| Set | Work | Runs concurrently within the set | Required evidence before release |
|---|---|---|---|
| 0 | Pin the current corrected production executable/source/environment; verify or reconverge reference | Local checks, then reference SCF if needed | Settings and restart compatibility |
| A | Fresh x/y/z CSO triplet; matching dump_P0 when required; q1/F0 pilot ±, initialization and EDIFF checks | Independent operator/dump/configuration jobs subject to the cap; replicas follow initialization decision | Set 0; fresh N0 before finite-q projection production |
| A gates | N0 on selected z operator; T3; z-only P0 with fresh paired F0 noise | Checks run when their own inputs are ready | Respective A results |
| B | Corrected CP suite, including F1 policy/frame/lambda checks, F2 cold starts and signed psi chains | Independent CP branches; each ramp and psi chain is sequential | Production reference and respective CP parents; no T3 dependency for SOC-free probe |
| B gates | CP compatibility, frames, F1 policy, signed parity/decoration paths and F2 viability | Each check consumes its own evidence | Required CP results |
| C1 | q1/F1, F2a, F2b baseline ±; replicas; F1 psi=60°/90° ±; lambda diagnostics | Separate parity/family/replica branches; psi=30° → 60° → 90° within each side | A/B gates and actual parents; first F2 dump supplies T4 barrier |
| C2 | q2 baseline F0/F1/F2a/F2b ± and F1 psi=60°/90° ± | Independent branches once their q1 parents pass | Corresponding q1 branch and pilot/policy gates |
| C3 | q3 baseline F0/F1/F2a/F2b ± and F1 psi=60°/90° ± | Independent branches once their q2 parents pass | Corresponding q2 branch |
| D | Collect pairs, noise, T4–T8 diagnostics and nine-parameter fits | Analysis only | All required data and evidence |

The remaining F0 q2/q3 chain can start after A gates; it need not wait for the
F1 policy. C1/C2/C3 are dependency levels, not global barriers: q2/F2a+ may
start once its q1 parent, CP6 and the first-F2 T4 barrier pass. B is a probe
lane alongside A, not a globally later wave. Pilot preparation precedes
freezing the bulk settings; bulk submission is a subsequent release.

**Intra-family calculations can run concurrently when they do not share a
restart dependency.** Rev 2 requires neighboring-q chaining. For each baseline
family, parity and decoration branch, use q1 → q2 → q3. These three q points
are sequential within that branch. Different branches remain parallel.
The positive and negative branches never restart from one another.

Concrete parent rules:

- F0 q1± starts from the imported q=0 reference, in separate writable copies.
- F0 q2±/q3± starts from the preceding same-side F0 q point.
- At q1, F1 starts from same-side F0 at psi=±30°, then chains
  +30° → +60° → +90° and -30° → -60° → -90°. Never jump directly from
  F0 to psi=±90°. Each child uses an accepted signed realization of its parent.
- F2a/F2b at q1 use separate near-target cold starts (`ISTART=0`, `ICHARG=2`)
  with the lab-frame MAGMOM and signed frozen-sublattice target. A one-rung
  flat-F0 restart is a probe diagnostic, not a production parent.
- At q2/q3, use the preceding same-family, same-decoration, same-side q state.
  This retains q1 → q2 → q3 within each branch. The q1 psi chains seed these
  branches; no conflicting second parent or repeat psi chain is required at q2/q3.
  Record the actual parent explicitly. Near-target cold starts are a documented
  recovery path, never an automatic unrecorded substitution.
- Each constrained configuration performs its own ascending lambda ramp
  1 → 3 → 10 → 30, stopping at the first valid realized state. Its first step
  starts at lambda=1 even if the neighboring parent terminated at higher lambda.
- Lambda diagnostics may reuse CP chains only when dump_P was enabled at
  every required rung on both sides of the selected policy. Otherwise retain
  separate fixed-lambda pairs at 3, 10 and 30 from same-side q1/F0 parents.
  Do not launch both equivalent datasets by default. Chained data retain
  their shared ancestry; nonpassing states remain diagnostic-only.
- Noise branches use the declared independent initialization protocol, not a
  renamed copy of the accepted terminal state.

The core finite bundle still contains 26 pairs / 52 terminal SCFs / 52 projection
dumps before additional lambda diagnostics, CP-only runs, and three operator
dumps. Include any new reference/dump_P0, intermediate ramps and seed preparation
in the expanded plan; the old two-policy-SCF estimate is superseded by CP.
Reuse an existing lambda point only when **both sides** have that exact
terminal lambda and the required target/settings/provenance match. Otherwise
run the missing points; the two sides can stop their baseline ramps differently.

## 4. Slurm submission and template contract

Reuse the supplied template's account, node type, ranks, threads, GPUs, binding,
modules, environment, and VASP launch command. Do not guess a Perlmutter account
or replace a working MPI/GPU launch recipe.

Extract its leading `#SBATCH` directives into generated job wrappers. Preserve
the original script body in `templates/job.sh`; run that body synchronously
from the selected VASP run directory inside the allocated worker. Its directives
are already applied by the wrapper. Generated wrappers own job names, log paths,
working directory, dependency and walltime fields; reject conflicting duplicate
directives. Require a Bash template that runs exactly one foreground VASP call,
propagates its failure, and operates in the current run directory. Detect and
report hard-coded `cd`, embedded submission loops, background launches, or
cleanup of shared files before preparation succeeds. Do not attempt a general
shell-script rewriter; make any necessary small template adaptation explicit.

Use `bash -e -o pipefail` for the preserved body, check its return code, and
then run completion checks. A template that deliberately suppresses launcher
errors does not meet the contract. Set the worker's run-directory context,
including `SLURM_SUBMIT_DIR` if the template uses it, for each SCF/dump invocation.

`jobsall.sh` uses the same valid resource header by default with a short,
explicit walltime; it launches only Python submission work, never VASP. Small
gate jobs use that short profile too. This costs a brief ordinary allocation
but needs no additional queue access. A supplied CPU profile can reduce the
overhead. Do not silently select `workflow` QOS: NERSC requires access approval
for it. [NERSC workflow QOS](https://docs.nersc.gov/jobs/workflow/workflow-queue/)

Submission algorithm:

1. Lock submission state, verify the frozen plan and topologically sort it;
   reject cycles and missing parents before submitting anything.
2. Submit wrappers with `sbatch --parsable --chdir=...`; retain job IDs and
   handle the optional `;cluster` suffix. Use argument lists, not shell `eval`.
3. Scientific dependencies use `afterok`. The F1 comparison gate uses `afterany`
   on its two probes so it can report both outcomes; missing/crashed evidence
   cannot produce a passing policy. The final reporting job similarly runs
   after all jobs terminate so failures still get summarized.
4. Bound concurrent calculation jobs with N simple submission lanes. Assign
   jobs in topological order; each also waits `afterany` for all earlier
   submitted jobs in its lane. Retain those ancestor dependencies: cancellation
   of an intermediate job must not let a later job overtake a running ancestor.
   Combine these with its scientific dependencies using AND.
   This conservative cap may leave capacity idle, which is acceptable here.
   Gate/controller jobs are short and excluded from this calculation cap.
5. Use `--kill-on-invalid-dep=yes` so scientific descendants of failed jobs
   do not remain pending forever. Record each returned ID atomically.
6. Explicitly prevent inherited submission-option environment variables from
   overriding generated child requests. Preserve the required runtime/module
   environment. Do not run several unrestricted copies of `job.sh` in one
   allocation.

Slurm's exit-based dependencies only enforce our physics gates if failing gates
exit nonzero. These options and dependency semantics follow the
[official sbatch documentation](https://slurm.schedmd.com/sbatch.html).

## 5. Files and sequential execution inside a worker

Stage small inputs during preparation when possible; stage restart files only
after their producing job and required acceptance checks have finished.

| File/use | Action |
|---|---|
| INCAR | Write per invocation using the v3 materializer; retain the exact file |
| POSCAR, KPOINTS | Copy small, frozen source files into each invocation |
| POTCAR | Link to one immutable campaign copy; record hash and species order |
| WAVECAR/CHGCAR for a writing SCF | Private copy from the explicit parent; never symlink or hard-link |
| WAVECAR/CHGCAR for dump_C/dump_P | Read-only input links to an immutable parent, with LWAVE=F and LCHARG=F |
| OUTCAR, OSZICAR, dumps, logs | Unique invocation directory; never shared or overwritten |

Hash the completed parent's restarts once, verify each staged input before
launch, and record its resolved source path. Stage copies through temporary
names and rename only when complete. Never follow a pre-existing output link
when opening a writable SCF restart. Retain parent restart files for every
pending child and for resumption; do not implement automatic cleanup initially.

For each normal configuration:

1. Check prerequisite gate records and parent hashes.
2. Materialize the family-specific INCAR, including separate MAGMOM/M_CONSTR
   frame adapters; all configuration runs remain SOC-free with SAXIS=z.
3. Run the SCF. Check electronic completion and finite-q realization R0,
   including signed Fe orientations and frozen-axis polarity. Use one allowed
   common azimuthal gauge, never independent per-ion sign flips. Mode 1's zero
   penalty on an antiparallel target is not an acceptance condition.
4. If electronically converged but R0 fails and another ramp step exists,
   archive that attempt and restart the next lambda from its private outputs.
   An execution/convergence failure stops the job; do not ramp blindly.
5. Once R0 passes, run exactly one PRE_LOOP dump_P from that terminal state.
   Apply the Rev 2 dump flags from the requirements document, including frozen
   restart outputs. Do not inherit a stale LDUMPONLY or unrelated dump flag.
6. Verify rank-file completeness, W0/M1 and trace I0; write evidence and mark
   the case complete. Record terminal lambda and both restart hashes.

Policy and fixed-lambda diagnostic runs preserve nonpassing realization records
instead of treating them as accepted production. For an electronically valid
fixed-lambda state, collect the requested dump even if R0 fails, explicitly
marking it diagnostic-only. A completed diagnostic job is not a valid fit row.

The x/y/z material dumps start independently from the selected reference, never
from each other's SOC outputs. Use the single frozen campaign executable.
T3 validates full-operator rotation; subsequent measurement axes reuse each
configuration's single projection dump. Require equality of trace-axis and
design-row labels at assembly.

## 6. Physics decisions and honest stopping points

This script must call scientific functions, not implement substitute checks
such as “OUTCAR exists.” The current v3 CLI covers the N0 bootstrap and T3;
finite-q materialization/R0, paired noise/P0, F1 policy selection and campaign
analysis still need implementation before the full launcher is usable.

- Retain existing N0 as historical accepted evidence. Recompute it with the
  selected fresh z operator and matching q=0 projections; obtain new dump_P0
  whenever the projection executable or reference state changes, or identity
  cannot be established. See the binary/reference decision in next_steps.md.
- A gates require genuine T3 and a z-only P0 decision using the new paired
  F0 noise data. Failure blocks expensive production.
- CP7 uses angular realization criteria: choose T when both candidates are
  acceptable and equivalent; choose F when T fails and F passes. Both fail,
  missing evidence or material disagreement remain UNDETERMINED. CP9 validates
  the chosen policy at psi=60°/90°. Energy diagnostics use separate tolerances.
- Replica initialization must be specified and validated before bulk generation;
  pilot generation is allowed to establish that protocol.
  Record exactly how each independently reconverged starting state is produced
  and paired. Copying files, changing a metadata replica number, or changing
  MAGMOM while reading unchanged wavefunctions does not by itself establish
  independent initialization. Any required seed-generation jobs belong in the
  dependency plan and cost estimate. Do not invent a random-seed VASP tag.
- T5/T6/T7/T8 and realized/weighted rank checks consume collected data. Report
  insufficient precision, missing plateaus or invalid states as unresolved;
  do not automatically expand the scientific campaign or claim a full pass.
- T9 remains explicitly outstanding even after the internal suite passes.

Each prepared release uses one submission. Pilot and bulk are separate releases
with a review between them. A failed/undetermined physics gate stops its
descendants and leaves a concrete report.

## 7. Resume and return bundle

Provide `status --root ...` and `prepare --resume ...` on the same entry point.
Rerun the generated `sbatch jobsall.sh` to submit only missing work after review.
Do not submit duplicate live jobs. Use per-case atomic result files so parallel
workers never rewrite one shared campaign JSON. An exclusive submission lock
and scheduler reconciliation are required if submission was interrupted between
Slurm accepting a job and recording its ID.

A cached completion is reusable only if inputs, parent provenance, code version,
required outputs and gate results match. Existence of OUTCAR, a zero launcher
exit code, or an unverified DONE file is insufficient. Changed/failed attempts
get new directories. Successful parent evidence can satisfy a resumed child
without referring to an expired Slurm job ID; regenerate dependencies for jobs
that actually need resubmission.

Write a final report distinguishing collected data, accepted fit rows, failed
jobs, blocked jobs and unresolved physics tests. Emit `return_files.txt` with
all artifacts requested in section 7 of the data requirements, plus manifests,
hashes, templates, generated scripts and logs. Exclude large restart files from
the transfer list while retaining them on Perlmutter. Include all CPROJ ranks.

## 8. Reuse and implementation order

Reuse the small `sbatch --parsable` / dependency pattern from
`pipeline v2/constrsint probe/constraint_probe/templates/run_all.sh` and its
template-copy approach. Reuse sound file-staging helpers from `noisefloor.py`
only where their file ownership matches section 5. Do not copy the old
OUTCAR-existence skip, writable restart symlinks, Patch A stage3 generation,
or the large v2 execution framework.

Build in this order:

1. Finish the missing finite-q scientific adapters/gates and pin policy/replica
   protocols; expose small callable functions with evidence-bearing results.
2. Implement the static case table, explicit parent map, input staging and dry
   plan output. Check counts, parity signs, q chains and frame-specific vectors.
3. Implement the template wrapper, per-case sequential worker, barrier jobs and
   single submission entry point. Add resumable submission and status reporting.
4. Test with a fake launcher/sbatch: dependency and gate failure propagation,
   no parent mutation, lambda early stop, unknown-policy refusal, independent
   replica provenance, and interrupted submission without duplicate jobs.
5. Run `bash -n` on generated scripts and a small on-cluster smoke test with
   the actual template. Release the real pilot before the bulk descendants.

Keep tests focused on these failure modes. A scheduler smoke test or synthetic
physics fixture cannot certify the real-data validation gates.
