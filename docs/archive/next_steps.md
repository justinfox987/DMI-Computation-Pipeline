# Next steps: implement the Perlmutter Fe pilot workflow

Revised: 2026-10-30. This is the current coding handoff. It replaces the
2026-09-17 immediate implementation sequence in this file. The broader DMI
validation program remains planned, but is not all part of this coding task.

## 1. Goal and execution environment

Finish the software locally so the user can transfer it to Perlmutter,
generate the actual inputs there, submit the small Fe pilot, and read and
summarize its results through the pipeline.

The Windows pilot directory is a generator fixture. VASP execution, licensed
POTCAR assets, the working cluster launch template, and executable paths belong
on Perlmutter. Their absence locally does not block software implementation
or synthetic/fake-launcher tests. Do not submit VASP or contact the cluster as
part of this implementation task.

The immediate deliverable is a small Fe preparation/execution/readback pilot:
one compatible q0 reference, imported or newly generated, and an F0 +q/-q
pair. This is not yet the full SOC measurement pilot or BFO campaign.

## 2. Inspect the current repository before coding

Read applicable AGENTS.md instructions, STATUS, recent session handoffs, the
current Step 1 specification and usage guide, and the actual preparation,
readback, reference, and submission code. Inspect the working tree and preserve
unrelated changes. Reuse existing functions and commands; implement missing
behavior rather than duplicating it. Choose CLI names consistent with the
repository, and document the actual implemented commands.

The following is reported progress, not a fresh code audit:

- The full historical Fe step1-read workflow ran with independent q0 sphere
  references and produced a meaningful physical rejection.
- Equivalent INCAR logical spellings are normalized using the strict parser.
- Field sign/factor evidence is separate from field-penalty identity; the
  exact-lambda discrepancy remains visible without an unsupported same-update
  verdict.
- Single-recipe preparation generates targets, config.json, INCAR.step1 and
  a merged INCAR, and copies shared material inputs.
- The supplied Perlmutter run guide reports explicit --inputs and
  --job-template paths, no current-directory job.sh discovery, and ENINI
  support at preparation/readback.

Verify these claims against the checkout. Do not reimplement completed work or
claim that the new pilot has run. Earlier reports mentioned 55 total tests;
report the actual current baseline and final results, not an inherited count.

## 3. Scientific conventions and scope boundaries

Use the current Step 1 specification and audited implementation for physical
conventions. The September runner/probe/data documents remain useful for
workflow architecture and deferred tests, but contain superseded frame text.

- Generate physical lab-frame MAGMOM seeds and mode-1 M_CONSTR target unit
  vectors through the existing target generator. Do not introduce an extra
  intracell unwinding transformation.
- Read OSZICAR M_int and MW_int under the current schema/convention contract;
  keep the two definitions and their reference norms distinct.
- Preserve signed alignment and polarity checks, magnitude-drift checks,
  family geometry checks, and penalty limits. Any permitted common gauge in
  a geometry check must not erase absolute alignment errors against M_CONSTR.
- Keep sign/factor evidence separate from the field-penalty numerical identity.
  Use a coefficient independently bound to run inputs when available; do not
  add uncertainty just because printed LAMBDA has fewer digits. Do not infer
  same-update association or exempt all CGA runs from the identity diagnostic.
- Preserve schema markers, unavailable evidence, physical rejections, and
  original VASP files. Do not relax thresholds to obtain a pass.
- Fe uses its explicit magnetic-site map and ferromagnetic signs. Do not
  import BFO's antiferromagnetic signs or numerical settings.

The existing Fe candidate is F0, q=(0.25,0,0), signs (+,+), seeds 2.2,
RWIGS=1.5, lambda=1 and LZEROZ=true. These are diagnostic candidate settings,
not validated production defaults. Generate the negative partner using the
current recipe/parity contract; check the expanded q and targets so the sign
is applied exactly once.

The immediate pair may retain the explicitly selected cold-start, fixed-lambda
diagnostic protocol. Do not silently convert it into production unconstrained
F0, add a lambda ramp, or switch restart ancestry. State acceptance is an
observed result, not a prerequisite for implementing the runner.

## 4. Required implementation

### A. Campaign preparation over the single-recipe generator

Add a small campaign input containing shared material/template paths, shared
recipe defaults, explicit per-case overrides, reference selection, and run
root. Reuse an existing compatible schema if one exists; otherwise document
the new schema and its merge rules. Keep executable/resource configuration
with the launch configuration, separate from magnetic recipes.

Preserve the single-recipe CLI. Each expanded case must pass through the same
scientific validation and writer used by that CLI. Save the original campaign,
fully resolved per-case recipes/configs, and an inspectable plan.json.

The plan must identify case IDs, purpose, pair membership, initialization,
reference source, execution parents, and acceptance prerequisites. A magnitude
reference dependency is not automatically a restart dependency: cold-start
pair calculations can run independently, but their acceptance needs the
verified reference. Distinguish those relationships explicitly.

Validate the whole plan before submission: reject duplicate/unsafe case IDs,
output collisions, invalid settings, missing parents, cycles, and ambiguous
parity pairs. Plan output must show the actual run count and dependencies.
Do not invent runtime estimates without supporting measurements.

For this release provide one small Fe example. Do not require users to hand
write every recipe in the eventual full campaign, but do not implement a
general scan framework or all later test tables now.

### B. Independent reference preparation and extraction

Support either an explicitly supplied completed q0 reference or generation
of a new q0 reference through existing preparation helpers. For a generated
sphere-readback reference use the supported mode-1, lambda=0 setup with
explicit compatible material and sphere settings.

Reuse the final-table parser and convergence checks to extract reference
norms. Preserve the reader's supported references.json format (currently
M_int and MW_int arrays); add a companion provenance record if needed rather
than forcing an unrelated schema migration.

Record source paths/hashes, selected final segment/step/table, magnetic-site
order, sphere definition/RWIGS, relevant input/output settings and convergence.
Check compatibility against each consuming case, including structure, PAWs,
k sampling, cutoff settings, bands and other relevant DFT settings. Document
allowed intentional differences, such as q and lambda; fail clearly on
unresolved compatibility. Never derive an independent reference from the
finite-q case being evaluated.

### C. Submission, readback, and aggregate reporting

Use a small runner around the existing functions and ordinary Slurm submission.
Reuse existing scheduler helpers and the working template contract. Preserve
the planned single submission entry point, sbatch jobsall.sh, if that interface
is already present; otherwise add the minimal equivalent without a new
scheduler service, database or workflow framework.

Provide preparation/plan inspection, explicit submission, status, and resume.
Preparation must never submit jobs. Preserve template resources/modules/binding;
do not guess accounts, queue access, executable paths or GPU launch arguments.
Validate the one-foreground-invocation/current-directory/failure-propagation
template contract and report any adaptation required.

Keep each attempt in its own directory. Record job IDs and bound concurrency.
Resume must reconcile live jobs and recorded results, reuse only matching
completed evidence, and avoid duplicate submission. Use a submission lock and
an interrupted-submission reconciliation strategy; uncertainty must not cause
blind resubmission. Preserve failed attempts and use new attempt directories.

Run existing readback functions after electronic completion and reference
availability. Propagate execution/readback/gate failure to jobs whose
descendants require acceptance. The run guide's interactive pattern that
catches an exit code and prints it is not an adequate acceptance gate by itself.

Diagnostic completion and physical acceptance are different. A fixed-lambda
diagnostic can be fully reported even when its state is rejected, but cannot
release work that requires an accepted state. Final reporting must run despite
case failures and list execution failures, readback failures, rejected states,
accepted states, and blocked/unresolved work separately.

A pair report must show both members and their individual results. Do not
label the pair as SOC/parity validated merely because both SCFs or readers
completed. Preserve existing pair checks if implemented; do not invent new
physics tolerances in the orchestration layer.

### D. Provenance and file ownership

Freeze a dedicated code checkout/package snapshot and record its identity and
dependencies. An editable install plus a commit hash is insufficient if the
checkout can change or contains unrecorded edits. Keep preparation and readback
bound to the recorded code version.

Snapshot recipes, launch templates and material inputs. Verify recorded input
hashes before execution and readback. Record the executable actually launched,
its hash and runtime environment inside the job after environment setup. For
module/container launchers, record the corresponding resolved executable or
image identity. A login-node hash alone does not establish launch identity.
Keep executable identification distinct from verified source/build provenance.

Each writing SCF owns private restart files if restarts are enabled. Never
share writable WAVECAR/CHGCAR links between cases. The immediate cold-start
pilot must not accidentally consume stale restart files. Preserve licensed
POTCAR handling and Git exclusions; a shared immutable campaign POTCAR is
acceptable. Never overwrite original outputs or silently clean parent data.

Write a final report and return_files.txt covering small inputs, resolved
recipes/configs, reference records, state records, job scripts/IDs, logs,
hashes and relevant VASP outputs. Retain large restart files on Perlmutter.

## 5. Validation and definition of done

Use focused local tests and synthetic outputs/fake submission tools. Verify:

1. Batch expansion matches the single-case generator, including +q/-q targets,
   overrides, IDs and invalid-plan rejection.
2. Reference extraction selects the correct converged final table and site
   order; incompatible or incomplete references cannot pass acceptance.
3. Launcher/readback failures and physical rejection remain distinguishable;
   rejected/missing prerequisites cannot release accepted-state descendants.
4. Execution versus reference dependencies permit only intended concurrency;
   cases cannot mutate shared inputs or another case's restart data.
5. Resume skips verified completed work and live jobs, preserves failed
   attempts, and handles interruption after submission without duplicate jobs.
6. Changed code, inputs, references or parents invalidate cached acceptance.
7. Reporting includes failed and blocked cases, and never upgrades a synthetic
   fixture or successful submission into real physical evidence.

Run the relevant existing regression suite and shell syntax checks. Stop once
the concrete changes and required failure modes are sufficiently verified.
Local tests cannot certify actual MPI/GPU launching or physical realization.

Update the Perlmutter guide with copyable commands for environment setup,
campaign preparation, plan review, submission, status/resume, reference
extraction, readback and returned results. Clearly label any proposed command
until implemented. Explain cluster-only choices without requiring their assets
locally: actual paths/template, resource layout, explicit ENCUT/ENINI, compatible
reference, executable/build evidence and a real compute-node smoke test.

Completion means the small pilot workflow is implemented and locally verified,
with a precise Perlmutter procedure. It does not mean that the pilot was run
or accepted. Follow repository commit/handoff policy; do not push or submit
calculations as part of this task.

## 6. Deferred broader DMI work (preserved roadmap, not this task)

After the Fe workflow is exercised, the broader program still requires:

- A verified corrected production executable and compatible material reference;
  fresh x/y/z SOC operator dumps and matching q0 projections unless reuse is
  justified by complete identity/settings evidence; renewed N0 and genuine T3.
- Corrected material-specific CP0-CP9 probes, including frame/activity checks,
  F1 LZEROZ policy selection, F2 viability and signed decoration paths.
- Production F0 +/- SCFs/projection dumps, initialization and tighter-EDIFF
  checks, declared independently reconverged paired replicas, and P0/noise
  evidence. The current constrained Fe trial does not establish that protocol.
- Later branch rules: independent parity ancestry; same-branch q1 -> q2 -> q3;
  same-side F1 decoration chains through signed 30/60/90 degrees; near-target
  F2 cold starts at q1. Constrained production configurations retain the
  per-configuration 1/3/10/30 ramp and smallest-accepted-rung rule. Do not apply
  that rule blindly to unconstrained F0 or fixed-rung diagnostics.
- Production F1 policy remains unresolved until measured; larger decorations
  need their signed-chain evidence. F2 projection validation gates later F2
  descendants. Failed/missing evidence cannot choose a policy.
- The gated internal campaign, paired SOC observables, realized/noise-weighted
  rank and fits, and T5-T8 checks. The older 26-pair core is not the size of
  this Fe pilot and excludes additional diagnostics/reference work.
- Separately specified T9 physical anchors and a nonzero-DMI benchmark. Ideal
  bulk bcc Fe is a zero-DMI control; passing its workflow does not establish
  correct extraction of a nonzero DMI. Second-order SOC remains deferred.

Consult perlmutter_test_runner_spec.md, constraint_probe_v2_protocol.md,
full_test_data_requirements.md and preflight_review.md for those stages, while
applying the current Step 1 overrides above. Do not resurrect obsolete frame
adapters, old pass labels, or assumptions that printed fields and penalty
necessarily describe one moment update. Report unresolved conflicts explicitly.

## 7. Required coding-model handoff

Report the baseline inspected, reused functionality, implemented interfaces,
changed files, exact test commands/results, and a minimal complete Fe campaign
example. Identify remaining cluster-only decisions separately from unimplemented
software. Update STATUS and the session log per repository policy, and state
commit/uncommitted status accurately. Do not claim readiness for the broader
DMI campaign from completion of this scoped task.
