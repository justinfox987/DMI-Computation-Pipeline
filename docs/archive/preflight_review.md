# Review of the full-test preflight and glossary

Reviewed 2026-09-17 against the supplied preflight document, glossary, Rev 2,
current v3 acceptance records, v2 constraint-probe code, and checked-in VASP
source. This records recommendations; it does not change the campaign policy
or authorize a launch.

## Overall assessment

Keep the provenance, constraint-source, RWIGS, pair-row, conditioning, runtime
and convergence checks. The user has confirmed that the old constraint probe
used a different cluster and VASP version: repeat the corrected probe on the
actual Perlmutter production executable. Historical results guide its design
but do not establish production acceptance.

The combined F1 pilot is useful, but does not replace the entire constraint
suite: it omits the independent frame test, free-relaxation control, F2 viability
and F2 initialization checks. The glossary correctly identifies a missing
explicit T4 barrier in my runner specification. Add it before bulk F2 work.

## Findings and proposed corrections

### A2/A3: use the existing evidence, not historical recollections

The saved `acceptance/configs/n0/trace.json` and `acceptance/manifest.json` give:

| Quantity | Actual result |
|---|---:|
| Total N0 trace | -5.1878291032873435e-8 eV |
| Bi ion 3 | -2.015403357260723e-9 eV |
| Bi ion 4 | -5.3751277351309276e-9 eV |
| Imaginary total | 1.4098257061040608e-19 eV |
| M1 maximum residual | 5.3291074533414665e-15 |
| Applied N0 threshold | 5e-5 eV |

This is an actual pass under Rev 2, not a provisional pass against an obsolete
1e-4 or 5e-4 threshold. Rev 2 specifies `max(5e-5, 3*sigma)`, not a replacement
pure `3*sigma` threshold. Do not change that silently. A finite-q pair's noise
also is not automatically the uncertainty of a q=0 single trace or each ion.

The recorded reference/z-CSO build is Sep 14 2026 07:13:49; dump_P0 is Sep 14
08:43:24, both VASP 6.4.2. The preflight's June production-build recollection
is stale. Moreover, the supplied CSO header does not identify a unique
executable build: use OUTCAR, executable hashes and job provenance. Reconcile
the executable for the new campaign; do not infer it from a generic patch label.
If z CSO is replaced, recompute N0 with the new operator and existing projections.
A materially changed projection-producing executable needs its own acceptance
evidence; old N0 is not a certification of every future binary.

### B1: zero-target behavior is already explicit in the local source

`vasp files/vasp-heide-patch-NEW/src/constrmag.F` skips ions with zero
M_CONSTR in both the constraining potential (lines 578–580) and penalty
energy (725–727). The normalization also guards zero norm (81–85).

For this source, zero Bi/O targets do not apply a direct moment-quenching
penalty. Retain zero targets; do not introduce Bi/O directional constraints
to solve a problem this source does not have. First confirm source-to-binary
identity on Perlmutter. Indirect changes to induced moments from constraining
Fe remain worth measuring.

### B2/B3: distinguish three different moment readbacks

The constraint acts on the smoothed sphere moment `MW_int`. OSZICAR also
prints the unsmoothed sphere moment `M_int`; the ordinary OUTCAR projected
moments are another readback whose definition must be checked. These cannot
be substituted without validation. The local source uses `MW` in both the
field and penalty and prints both columns at lines 830–834.

Calculate `2*lambda*MW_perp` from that weighted quantity, preferably checking
against the explicitly printed constraint field. Match each magnitude reference
to its readback definition and RWIGS. In particular, do not automatically use
the bootstrap OUTCAR Fe moment as a sphere-integral reference.
This distinction is documented in the
[VASP constraint documentation](https://vasp.at/wiki/I_CONSTRAINED_M).

### B3/E1: useful lambda diagnostics, but conclusions go too far

I agree with the correction to Rev 2's rationale: increasing lambda does not
necessarily increase the converged constraining field. At approximately fixed
field, the penalty falls as 1/lambda. That observation does not prove that the
SOC trace is lambda-independent once a finite R0 tolerance passes, nor that an
F1 pilot establishes a good lambda for F2, other q points or larger decorations.

- Treat constant field and lambda*E_p as diagnostics, not sufficient permission
  to replace the per-configuration ramp with a family-wide fixed lambda.
- The ratio 3.5 follows only if a leading, nonzero 1/lambda term dominates.
  On a genuine plateau both numerator and denominator may be noise-sized;
  this ratio must not be an acceptance gate.
- Use the uncertainty of the **difference between lambda points**, including
  covariance, for a plateau test. `2*sigma_pair` is ambiguous unless defined
  for that exact difference. Also require adequate absolute precision.
- A common lambda for both parity sides is a reasonable controlled-pilot
  choice. Making it mandatory in production changes Rev 2's smallest-passing
  per-configuration policy; propose and record that amendment explicitly.
- Chained lambda scans are reasonable and VASP documents stepwise increases.
  They introduce a shared initialization history: retain parent provenance and
  use an independent-start check if hysteresis/branch dependence is suspected.

The field is not literally the torque: their units differ; a torque involves
the moment crossed with the field. Correct that shorthand in the glossary.

### B4/T4: test the F2 starting state on production

An old cold-start success does not prove a flat restart fails. Conversely, my
specified flat-F0 restart is not established merely by assuming the constraint
will rotate it. With direction-only penalties, exactly perpendicular or
antiparallel states deserve explicit checks; a nonzero penalty is not proof
that the desired rotation will occur.

Make F2 initialization part of the production probe, use a demonstrated
near-target cold start if needed, and pin that parent rule before bulk F2.
Check signed Fe orientations as well as cone angles: mode 1 does not itself
enforce the target sign. Do not switch constraint modes silently.

The first accepted F2 SCF/dump can supply T4 without an extra duplicate job.
Its I0/per-ion checks must be an explicit prerequisite for subsequent F2 jobs.

### B5/E1: keep a tie-break, correct its units and scope

Choosing LZEROZ=T when both policies give acceptable, equivalent F1 states is
a reasonable pre-registered tie-break. However, angles cannot be compared with
an energy sigma. Use angular criteria for theta/psi and an appropriate trace
uncertainty for energy. F0 noise may be an initial diagnostic but is not a
validated F1 uncertainty. If both policies fail, or disagree materially, the
decision remains unresolved. The negative parity chain must use the policy
actually selected, not merely the policy expected to win.

Constraint activity should be demonstrated with a deliberately mis-targeted
state and a control. Do not require terminal E_p>0 for every valid run: an
exactly satisfied target can have zero penalty.

### C1–C3: accept the checks, qualify what they establish

Use both measured traces and both realized rows, with the same normalization:
`y=(T_plus-T_minus)/N_m`, `A=(K_plus-K_minus)/N_m`, where K maps one
configuration to its trace. Check trace/design axis identity here. This removes
the geometric substitution error; it does not automatically absorb changes in
moment magnitude, electronic state or effects outside the model. This assembly
path still needs implementation in v3; it is not merely a known small edit.

Leave-one-q-out rank and a larger-Rmax design check are useful free diagnostics.
Rank-deficient training sets do not make every truncation effect undetectable:
some held-out predictions may remain identifiable. Full rank does not uniquely
identify truncation as the cause of a residual either. Choose any fourth q by
added rank/conditioning and distinguishability, not only by a different length.

Re-read old parity outputs if available, but a small same-sign residual near
zero does not by itself refute parity. A verified 1.2-degree target error would
fail a strict 1-degree gate; do not retain its historical PASS label.

### E2/E3: separate repeatability, starting-state sensitivity and accuracy

Keep both pilots. Two nonidentical GPU runs do not establish independent
replicas or a reliable variance estimate. Conversely, identical rounded
OSZICAR text does not establish identical states. Use traces, realized states
and provenance; record the initialization and pairing procedure. A different
electronic basin is a diagnostic problem, not automatically extra Gaussian noise.

EDIFF constrains changes between electronic iterations, not a certified energy
error or density norm. Therefore trace error proportional to sqrt(EDIFF) is a
heuristic, not a guaranteed scaling law. Measure the convergence of the actual
observable. [VASP EDIFF definition](https://vasp.at/wiki/EDIFF)
Start with the suggested F0+ check; if consequential, tighten and compare both
parity sides, including their sum and difference. Check a representative
constrained state before extending an F0 conclusion to all families.

There is a staging circularity to remove: E2 cannot be required before any
preparation while itself requiring a prepared pilot. Allow pilot preparation
first, then freeze the bulk replica protocol and EDIFF after its results.
Distinguish the variance of the parity sum from the variance of its difference;
their covariance contributions have opposite signs.

### D: retain the requested entry point and preserve evidence

The suggestion to replace `sbatch jobsall.sh` with `bash jobsall.sh` conflicts
with the user's explicit interface request. A lightweight direct submission
option could be supported, but keep the requested sbatch entry point.

Use measured runtime/storage estimates; the proposed roughly 50 SCFs under
a changed lambda policy is an estimate, not an established saving. A storage
policy may remove unneeded large intermediate restarts only after protecting
all live dependencies; retain every attempt's small inputs/readbacks/evidence.
Back up required parents to appropriate persistent storage when needed; do not
make timestamp refreshing the retention strategy. Scratch is not backed up
and is purged. [NERSC scratch documentation](https://docs.nersc.gov/filesystems/perlmutter-scratch/)

## Glossary corrections

- Keep the W0/T0 name separation. Mark finite-q T1 evidence as requiring
  confirmation on production; historical frame evidence is not a new-build pass.
- C0 requires conjugate-transpose-related flip blocks; each flip block need
  not itself be Hermitian. The current C0 check is explicitly for the z operator.
  Bi > Fe > O is a material diagnostic, not a universal structural invariant.
- Write the I0 bound using absolute imaginary values.
- Separate the COCC block packing `(uu,du,ud,dd)` in current v3 from a candidate
  CSO rotation convention. No universal spin-block map or old Euler label may
  bypass the genuine-dump T3 check.
- V5 is free-state drift versus tighter convergence. V7 is penalty-energy
  bookkeeping (`v7_penalty_bookkeeping` in the old probe). Its no-op case with
  negligible penalty cannot distinguish competing energy-bookkeeping signs;
  audit before reuse.
- Describe a dependency order, not a globally serial ladder: unconstrained
  pilots can run independently of the constraint-suite rerun. T6/T8 inherently
  require data from multiple jobs.
- Flag EDIFF scaling, fixed-field scaling and imported statuses as qualified
  statements. Do not present them as universally pinned constants.

## Recommended next steps

1. Update the documents with the verified N0/source facts and agreed corrections;
   retain Rev 2 policy until an explicit amendment is justified.
2. Repair and reuse the constraint-probe generator/readers for a small production
   rerun: tag/activity/control, finite-q frame discrimination, RWIGS/readback,
   lambda response, F1 policy, and F2 initialization/viability. Audit old verdict
   logic rather than copying its acceptance labels.
3. Implement a pilot-only staging path using the real Perlmutter job template.
   Run operator validation and unconstrained F0 convergence/noise work alongside
   the corrected constraint probe wherever their actual dependencies permit.
4. Use those results to pin the production executable/environment, readback
   definitions, F1 policy, F2 restart rule, lambda policy, replica protocol and
   convergence settings. Complete finite-q gates and paired assembly locally.
5. Expand the same runner to the bulk campaign, with explicit pilot/T4 barriers,
   then perform fits and internal validation. T9 remains separately specified.

The immediate implementation target is the corrected production probe plus
pilot runner, not an unattended full campaign with unresolved scientific choices.
