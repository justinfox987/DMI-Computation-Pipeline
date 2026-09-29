# Data required for a full v3 test

Execution plan: [Perlmutter staging script specification](perlmutter_test_runner_spec.md).
Final pilot/build decisions: [next_steps.md](next_steps.md).

Baseline: the production Patch B files in `noq/`. Existing C0, W0, M1, R0,
I0 and N0 evidence is available. Do not rerun the null merely to populate
this checklist. This document specifies data to collect; the v3 campaign
generator, paired analysis and solver migration still need implementation.

Authority: `decorated_spiral_implementation_rev2.md`, especially sections
2.3, 3, 4 and 7; `new_direction.md` for paired observables/restarts.
The particular q vectors and replica count below are a proposed concrete
test design, not additional empirically pinned conventions.

## 1. Material-level axis validation: a matching x/y/z triplet

Freeze the current corrected Perlmutter executable and produce genuine CSO
dumps for SAXIS=x, y and z. The old reference/z dump and dump_P0 have different
build stamps; do not choose the old executable merely to reuse its operator.
Use one accepted production reference, PAWs, structure and settings for all
three siblings. Verify or reconverge the reference as described in next_steps.md;
start each dump independently from it, never from another SOC dump's output.

For new dump runs use the Rev 2 settings: `LSORBIT=T`, `LSPIRAL=F`,
`ISTART=1`, `ICHARG=11`, `ALGO=Normal`, `NELM=1`, `LDUMPCSO=T`,
`LWAVE=F`, `LCHARG=F`; leave `LDUMPONLY` disabled. Change SAXIS to the
requested axis. A matching accepted reference requires no additional SCF.

Suggested directories: `validation/material/dump_C_x`, `dump_C_y`, `dump_C_z`.
Keep the output filename `CSO.dat`; its SAXIS header identifies the axis.
Recompute N0 with the selected new z operator. Reuse existing q=0 projections
only with matching executable hash and reference/settings provenance; otherwise
produce a new dump_P0. Preserve the original accepted null as historical evidence.

## 2. Resolve the F1 LZEROZ policy before F1 production

Run the corrected [CP suite](constraint_probe_v2_protocol.md) on the frozen
production executable. CP7 replaces the earlier two-run lambda=20 comparison:
compare F1 LZEROZ=T/F at q1, psi=+30°, through matched lambda rungs 1,3,10,30.
It also supplies frame/activity evidence and tests F2 and signed decoration
initialization. The old LRC probe is historical, not a production acceptance.

Return both complete readback records even if one fails to realize its target.
No projection dumps are needed just to choose the policy.
Reuse matching evidence when available. The older compatibility-only V8
result does not decide the policy; CP9 must validate its larger decorations.

## 3. Baseline complete fit: 12 pairs / 24 SCFs / 24 projection dumps

Use the existing Gamma-centered 8x8x8 k mesh, POSCAR order, PAWs, +U settings,
ENCUT and other material settings. Magnetic signs are Fe1=+1, Fe2=-1.
The following are fractional reciprocal coordinates:

| Label | q_plus | q_minus |
|---|---|---|
| q1 | (1/4,0,0) | (-1/4,0,0) |
| q2 | (1/4,1/8,0) | (-1/4,-1/8,0) |
| q3 | (1/4,1/8,1/8) | (-1/4,-1/8,-1/8) |

For EACH q label, produce EACH of these four parity pairs:

| Family | psi_plus | psi_minus | theta_Fe1 | theta_Fe2 | Winding |
|---|---:|---:|---:|---:|---|
| F0 | 0 deg | 0 deg | 90 deg | 90 deg | both |
| F1 | +30 deg | -30 deg | 90 deg | 90 deg | both |
| F2a | 0 deg | 0 deg | 30 deg | 0 deg | Fe1 |
| F2b | 0 deg | 0 deg | 0 deg | 30 deg | Fe2 |

Both sides have the same cone angles and winding assignment. Each side
needs its own converged SOC-free state and its own PRE_LOOP projection dump.
Do not substitute an inferred negative-q trace or reuse the partner's occupations.
Keep the plus/minus restart chains separate.

All configuration SCFs/dumps use SAXIS=z and LSORBIT=F. F0 is unconstrained,
with LZEROZ=T. F1 uses the policy established above. F2 uses LZEROZ=F.
F1/F2 use I_CONSTRAINED_M=1, explicit RWIGS and a documented lambda ramp
{1,3,10,30}, stopping at the smallest value that passes realization.
Preserve every ramp step's readback, including failures.

At q1, initialize F1 via same-side F0 → ±30° → ±60° → ±90°, never directly
F0 → ±90°. Initialize F2a/F2b with separate near-target cold starts. At q2/q3,
continue each family/decoration/parity branch from its preceding q point.
R0 checks signed Fe orientations and frozen-axis polarity, not only unsigned
axes or small penalty. The first F2 dump supplies T4 before bulk F2 release.

MAGMOM carries the intracell q.tau phase; M_CONSTR removes that phase.
The corrected generator must write these vectors separately. These tables
are target-state specifications, not a substitute for generated INCARs.

Each dump_P restarts from its own terminal stage2 WAVECAR/CHGCAR:
ISTART=1, ICHARG=11, ALGO=Normal, NELM=1, LSORBIT=F,
LDUMPCPROJ=T, LDUMPCOCC=T, LWAVE=F, LCHARG=F; no LDUMPONLY.
Carry over that state's QSPIRAL, SAXIS and family/constraint settings.

Numerical design check performed on the supplied production POSCAR, Rmax=6 A:
3 orbits, 9 parameters, 36 measurement-axis rows, rank 9, unweighted
kappa=78.6005. F0 alone has rank 4; removing F0 leaves rank 9.
These are target-state checks. Realized rows and noise-weighted conditioning
must be checked again before fitting. Three axes use the same projections
after T3; they do not require three configuration SCFs.

Run q1/F0 plus and minus first: this is the first nonzero-q P0 check.
Review it before committing the rest of the campaign.

## 4. Restart noise and T8: eight additional pairs

For q1 in each of F0, F1, F2a and F2b, collect three independent paired
SCF-plus-dump realizations in total. The baseline pair counts as replicate 1;
add replicates 2 and 3. This adds 8 pairs = 16 SCFs + 16 dump_P runs.

Document the starting wavefunctions/initialization for each replica.
Each replica must be independently reconverged; repeated contractions or
repeated dumps of the same converged WAVECAR do not measure SCF restart noise.
Record plus/minus replica association to estimate their covariance.
Three is an initial variance estimate; collect more if uncertainty is unstable
or a configuration/family shows different noise. No Patch A sigma is reused.

## 5. Lambda dependence (T5)

For q1/F1 at psi_plus=+30 deg, psi_minus=-30 deg, collect a COMPLETE
plus/minus SCF-and-dump pair at each lambda in {3,10,30}.
Use the resolved LZEROZ policy. A baseline pair at one of these lambdas
can be reused. Collect all readback evidence, including nonpassing states;
only valid realized pairs can establish a plateau.

This adds 4 SCFs/dumps if the baseline overlaps one lambda, otherwise 6,
unless matching CP rung dumps already supply them. In that mode both sides
of the selected policy must run/dump every required rung through lambda=30.
If the three points do not provide a valid plateau, further lambdas are a
measurement-dependent follow-up, not something the current spec predetermines.

## 6. Decoration dependence (T6) and cross-family consistency (T7)

At each of q1, q2 and q3, add F1 pairs with psi_plus=60 and 90 degrees
(psi_minus=-60 and -90 degrees). This adds 6 pairs = 12 SCFs + 12 dump_P runs.
Use the validated constraint policy and retain the per-run terminal lambda.
The baseline supplies the psi=30-degree F1 data and the shared F0/F2 controls.

For the three corresponding target-design fits, ranks are all 9 and
unweighted kappas are 78.6005, 75.0619 and 71.3340 respectively.
Reuse the F0/F2 controls with their shared-data covariance accounted for when
comparing fits. T7 uses these existing data; it needs no separate runs.

## 7. Files to return

For EVERY SCF/ramp step and every dump:

- INCAR, POSCAR, KPOINTS, OUTCAR, OSZICAR, stdout/stderr and job script.
- Run metadata: id, family, parity side, q_frac, psi in degrees or explicitly
  labelled radians, cone angles, winding sublattice, lambda, LZEROZ,
  replica/scan id, and exact parent run.
- Executable SHA-256 and build banner; runtime module/environment record.

For each dump_C additionally: CSO.dat.

For each dump_P additionally: EVERY CPROJ.*.bin rank file, FERWE.dat, COCC.dat.
For stage2 additionally: EIGENVAL and IBZKPT for spectral parity/cross-checks.

Keep WAVECAR/CHGCAR on the cluster. Record SHA-256 hashes of each parent's
outputs and each dump's inputs BEFORE launching the dump; for new dump runs
disable restart-output writing as specified above. Also record POTCAR hashes
and species order, retaining one shared local POTCAR rather than duplicating it.
Full WAVECAR/CHGCAR transfers are only needed if a restart discrepancy requires
inspection. The current bootstrap's byte-identity check will need to consume
these recorded hashes for remote runs.

PROCAR, DOSCAR, CHG, vasprun.xml and vaspout.h5 are not required by this
validation path. Do not generate corrupted or incomplete VASP runs for negative
tests: those test fixtures are created locally.

## 8. Remaining external physics validation (T9)

A complete test of the software through the nine-parameter fit uses sections
1-7. Completing EVERY rung of the research validation ladder also requires:

- qSO F0 +q/-q total-energy anchor(s), with matched material settings and
  physical-frame spin states; return complete inputs, OUTCAR and OSZICAR.
- Commensurate supercell SOC energy-difference anchor(s), including the
  primitive-to-supercell mapping and explicit physical spin configurations.
- TB2J exchange/DMI output plus structure, pair indexing, units, Hamiltonian
  convention and calculation settings sufficient to compare the same bonds.

The project documents do not fix the exact supercell configurations or TB2J
setup. Those protocols must be specified before spending compute on them;
claiming a fully validated physics result from sections 1-7 alone would omit T9.

## Execution order and outstanding inputs

1. Freeze the corrected executable and matched reference. Produce the x/y/z
   operator triplet and matching dump_P0 as needed; re-evaluate N0 and T3.
2. Run the corrected CP suite alongside the F0 measurement pilot where actual
   dependencies permit; establish readbacks, policy, signed initialization,
   convergence and replica settings before bulk generation.
3. Remaining baseline pairs, restart replicas and scans after pilot gates pass.
4. Agreed external-anchor protocols and outputs.

The finite internal bundle consists of 26 pairs (52 terminal SCFs and 52
projection dumps) before missing lambda-scan points, CP-only runs, and three
axis dumps. Counts exclude any new reference/dump_P0, intermediate lambda ramps
and convergence/noise follow-ups; reuse matching pilot data without double
counting. Raw traces alone do not guarantee that
the realized campaign is full rank or sufficiently reproducible.
