# Final next steps: production constraint probe and pilot runner

Status: agreed implementation direction, 2026-09-17. Documents updated;
implementation and Perlmutter runs are the next work. No jobs submitted.

## 1. Decision

Build the corrected production constraint probe and a small pilot runner first.
Reuse sound v2 code, repair its frame/readback/acceptance defects, and retain
the single submission entry point `sbatch jobsall.sh`. Release the full internal
campaign only after the pilot has established its scientific settings.

Use these documents together:

- [Constraint probe v2 protocol](constraint_probe_v2_protocol.md): CP0–CP9 runs,
  measurements, verdicts and dependencies.
- [Runner specification](perlmutter_test_runner_spec.md): file ownership,
  Slurm wrappers, parent rules, evidence and resumption.
- [Data requirements](full_test_data_requirements.md): eventual internal dataset
  and the separately outstanding T9 anchors.
- [Preflight review](preflight_review.md): evidence and reasons for corrections.

This document resolves the initialization/build/probe-staging decisions from
the final discussion. Rev 2 remains the physics authority; do not infer changes
to its observable, operator rotation or per-configuration lambda policy.

## 2. Accepted recommendations and their precise meaning

### Avoid perpendicular mode-1 starts

For a fixed weighted moment magnitude, the mode-1 penalty is
`E_p = lambda * |MW|^2 * sin(beta)^2`. Its angular derivative vanishes at
90°, while both parallel and antiparallel states have zero penalty. This
follows from the documented [VASP penalty functional](https://vasp.at/wiki/I_CONSTRAINED_M).
It makes a perpendicular restart unreliable as a rotation strategy. It does
not guarantee that the full electronic calculation stays there: other forces,
coupled moments and numerical perturbations can move it.

Adopt these production parents:

| Branch | Initial path at q1 | Continuation |
|---|---|---|
| F0+ / F0− | Separate copies of accepted reference | Same parity q1 → q2 → q3 |
| F1+ | F0+ → +30° → +60° → +90° | Each decoration continues at q2/q3 from its same-decoration, same-parity preceding q |
| F1− | F0− → −30° → −60° → −90° | Same rule, independent of positive branch |
| F2a / F2b, each parity | Independent near-target cold starts with correct lab-frame MAGMOM and signed axis targets | Same family and parity q1 → q2 → q3 |

The q1 decoration chain seeds the three q chains; there is no need to give a
job two restart parents. Different branches can overlap once their actual
parents pass. Initial decoration steps and lambda ramps are sequential.

R0 must inspect full signed orientations, moment magnitude and family geometry.
Account for the fixed POSCAR magnetic signs and one allowed common azimuthal
gauge; never use absolute dot products or independent sign flips to hide a
wrong solution. Axial moments have a polarity but no defined azimuth.

Keep one `f2_chain` lambda=1 flat-parent attempt as a documented dead-point
diagnostic. Its result is not required to be FAIL. Use near-target cold starts
for both F2 assignments in production, and CP9 to test both signed decoration
chains through 90° under the selected F1 policy.

### Pin one current corrected campaign executable

**Choose the verified current Perlmutter production executable containing the
dump fixes, corresponding to the 08:43 build or a later verified build. Do not
select the older 07:13 executable merely to reuse its z operator.** Freeze its
absolute path, SHA-256, source revision/diff, build settings, runtime libraries
and module versions. The exact path/hash must be captured on Perlmutter; it is
not supplied by a timestamp or a generic `HEIDE PATCH B` header.

The two local Sep 14 build stamps establish different builds, not their exact
source differences. Do not presume that only dump code changed without checking.
The existing mixed-build N0 remains an accepted historical result for its exact
files (total -5.19e-8 eV against 5e-5 eV).

For the new campaign:

1. Reuse `ref` only if its identity and settings meet the frozen production
   protocol. Otherwise reconverge a separate production reference, using the
   old restart only when compatible; use a cold start if incompatible. Preserve
   the original `noq` data and acceptance record.
2. Produce a **fresh x/y/z CSO triplet**, each independently from that same
   reference with the frozen executable. This is now the planned operator set.
3. Reuse existing q=0 projections only if the executable hash, reference state,
   settings and restart provenance match. A changed executable, changed
   reference or unverified identity requires a fresh `dump_P0`. Budget this
   one-shot by default; waive it only with matching evidence.
4. Run C0/W0/M1/I0 and recompute N0 using the selected new z operator. Perform
   genuine-dump T3. Preserve historical results separately; never rewrite their
   provenance to describe the new inputs.

This resolves the operator count now: **three new operator dumps**, plus a
matching q=0 projection dump unless proven reusable. It does not require a new
reference SCF when a matching production reference is already available.

## 3. Probe decisions to implement

- **CP0/CP1:** parse MW_int, M_int and OUTCAR tables separately and pin their
  frames/readback definitions. A first printed SCF moment is not necessarily
  the untouched MAGMOM seed; use matched-source initialization evidence or a
  verified pre-update capture for that pin. Compare azimuths only where the
  transverse moment is resolved, with wrapped differences.
- **CP2/CP3:** retain free-relaxation and mis-targeted movement controls. Require
  finite nonzero penalty during a demonstrably misaligned part of the run,
  not at exact convergence. A stationary unconstrained state is informative,
  not automatically a broken constraint.
- **CP4:** use MW_int for `B^c = 2*lambda*MW_perp`; verify against the printed
  vector field and its factor convention. Field constancy, lambda*E_p and
  inverse-lambda angular behavior are diagnostics. They do not automatically
  authorize a family-wide lambda or gate on the ratio 3.5.
- **CP5:** matched local source skips zero Bi/O targets. Keep them zero and
  report indirect changes in induced moments; do not force those changes to
  vanish or automatically add Bi/O constraints.
- **CP6/CP9:** establish signed F2 viability and the actual signed decoration
  paths, including the 90° endpoints. Keep failures and their inputs/readbacks.
- **CP7:** compare theta/psi with angular tolerances. Select T when both
  policies pass and agree; select F if only F passes. Otherwise report an
  unresolved decision. CP9 must pass with the chosen policy before releasing
  larger decorations.
- **CP8:** compare both sides at common accepted lambda, with an explicit
  k-point mapping. Energy/spectral tolerances need convergence evidence;
  a few times EDIFF is not a certified error bound. A mismatch can reflect
  wrong inputs, different realized states or incomplete convergence.

The standalone CP suite needs no CSO/projection dumps. Optional dumps at each
F1 rung can supply T5 later, provided both signs of the selected policy run
through all required lambda values. Do not call an early-stopped negative chain
a complete T5 dataset or run duplicate scans when matching data already exist.

The updated maximum is 43 CP SCF steps before a new reference, optional
controls or recovery work. Many are ramp intermediates; reuse accepted terminal
states where valid. Generate the actual expanded count and storage/runtime
estimate, rather than treating that bound as a promise of cost.

## 4. Implementation sequence and completion criteria

### Step 1 — freeze inputs and implement the corrected probe

Inputs to capture on Perlmutter: the working `job.sh`, exact production
executable/source/build identity, runtime environment, reference paths/material
settings, candidate RWIGS, and allocation/resource limits. Audit RWIGS geometry
and fix one set for the probe. Retain source-specific moment references; do not
mix projected OUTCAR magnitudes with weighted sphere integrals.

Copy usable v2 probe generation, geometry, parsing and submission pieces.
Correct the readers and verdicts rather than importing their old PASS labels.
Use the same v3 target/frame and signed realization helpers for probe and
campaign. The current N0-only `realized.py` is not yet that general reader.

**Done when:** the CP plan emits correct signed targets, explicit parents,
all readback fields and evidence-bearing results; local checks catch frame
confusion, antiparallel false passes and missing convergence/provenance.

### Step 2 — build a pilot-only path in the simple runner

Keep the one-script design and `sbatch jobsall.sh` interface. Add an explicit
pilot scope; it must prepare diagnostic candidate settings without treating
them as established production policy. Each job owns its writable restart
copies. Frozen-input dumps may link immutable parents with restart writing off.

Use these concurrent lanes:

| Lane | Work after its prerequisites | What it releases |
|---|---|---|
| Material acceptance | Matched reference → sibling x/y/z dumps and dump_P0 | New N0 and T3 evidence |
| Constraint probe | Probe F0/control states → independent policy/frame/F2 branches → CP7/CP1 → signed decoration/parity branches | Frames, readbacks, F1 policy, F2 and decoration viability |
| F0 measurement pilot | Accepted N0 → F0± SCFs/dumps; initialization and tighter-EDIFF checks → declared paired replicas | P0, paired uncertainty and bulk convergence/replica settings |

The SOC-free CP lane does not need T3. Production x/y traces do. Reference
production and individual parent jobs remain true dependencies in every lane.
Probe F0 with mode 1/lambda=0 is not automatically identical to production
unconstrained F0: establish equivalence before reuse, otherwise keep it separate.

**Done when:** dry planning, fake-launcher failure/resume tests and generated
shell syntax checks pass; the actual template passes a small Perlmutter smoke
test. No scientific gate can pass merely because a job exited zero.

### Step 3 — run pilots, record decisions, then freeze bulk settings

Pilot preparation is allowed before knowing its results. Choose and record the
bulk replica protocol and EDIFF afterward. Separate deterministic repeatability,
initial-state sensitivity and genuine state changes; preserve parity association
and the covariance needed for both the trace sum and difference.

Keep Rev 2's smallest-passing per-configuration ramp as the default. A faster
policy may be proposed from data, but does not follow automatically from CP4.
Per-run and per-pair tolerances must be explicit before acceptance; unresolved
frames, numerical tolerances or policy decisions block only their descendants.

**Done when:** required N0/T3/P0 and CP evidence passes, signed parent paths are
demonstrated, the numerical/noise settings are pinned, and estimates fit the
available resources. This is the review point before committing bulk compute.

### Step 4 — extend the same runner to the internal campaign

Complete paired assembly from both realized sides, the lambda/decoration
diagnostics and solver migration. Ensure trace-axis/design-axis equality.
The first accepted F2 projection dump supplies an explicit T4 barrier before
bulk F2 descendants. Reuse matching probe/pilot data and retain all evidence.

Run the planned 26-pair core plus missing scan points, reevaluate realized and
noise-weighted rank, and produce the final internal validation report. T9 still
requires separately specified external-anchor calculations.

## 5. Immediate next coding task

Implement **Step 1 and the pilot portion of Step 2**. Do not start with a general
workflow framework or pre-submit the bulk campaign. The parent rules and probe
run list are now specified; the remaining empirical decisions belong to the
pilot and must be reported rather than guessed.
