# Project decisions

Keep entries concise and link the governing spec. Add a superseding entry if a
decision changes; do not erase why the previous choice was made. The entries
below record decisions already reached before repository integration.

## D-001 — Lab-vector input and sphere readback

**Status:** accepted working convention; production-build confirmation remains.
The constraint use of MW_int is dormant under D-008.  
Write MAGMOM and mode-1 M_CONSTR as physical vectors at SAXIS=(0,0,1).
Read OSZICAR M_int for geometry and MW_int for constraints. Do not introduce a
generic winding/unwinding layer or an OUTCAR fallback for fitted directions.

**Reason:** the Fe tests distinguish the sphere and projected readouts; supplied
VASP source performs the MAGMOM counter-rotation internally.
**Authority:** [math Revision 2.4](math/heide_math_v2.tex), Sections 3–4;
[Step 1 spec](archive/dmi_step1_implementation_spec.md).

## D-002 — Use measured vectors directly in paired rows

**Status:** superseded by D-007 and D-008. Measured M_int directions and paired
observables remain; bond rows, F1 and F2 do not.  
Keep F1 offset and F2 tilt as input controls. Normalize each state's M_int,
rotate a neighbor only by its bond cell translation, and evaluate both states.
Use y=(T_plus−T_minus)/N_m and the matching difference of model coefficients.

**Reason:** this removes redundant angle extraction, avoids double-counting the
intracell phase and preserves actual partner differences.
**Authority:** math Sections 3 and 8; Step 1 spec Sections 3–6.

## D-003 — Select Cartesian components through the SOC operator

**Status:** principle retained; the method is replaced by D-009. Genuine-dump
validation is still required.  
Production SCFs stay in the fixed z spin convention. Rotate the full SOC operator
to select x/y/z, then retain diagonal spin blocks. Do not also rotate the targets.

**Reason:** one state supplies all three measurement axes consistently.
**Authority:** math Section 5 and the retained T3 requirement.

## D-004 — First-order method and staged production validation

**Status:** first-order method retained; the stage list is replaced by D-013 and
D-014.  
Second-order SOC is deferred. Complete the local migration, then corrected
production probes/pilots, then the bulk BFO campaign and external comparisons.

**Reason:** unresolved executable, realization and numerical settings must be
measured before relying on a bulk dataset.
**Authority:** Step 1 scope; archived next_steps.md except superseded conventions.

## D-005 — Repository files carry the project handoff

**Status:** selected for this setup; integration pending.  
Use STATUS for current work, CHANGELOG for delivered changes, this file for
durable reasons, and one session file per session. Use one writing agent per
branch/worktree, and synchronize commits through a private remote.

**Reason:** multiple tools and sessions need inspectable shared state; chat
memory and uncommitted local files do not provide a reliable handoff.
**Authority:** [repository setup](archive/REPOSITORY_SETUP.md) and root AGENTS.md.

## D-006 — Generate the actual pilot on the cluster with explicit paths

**Status:** accepted; supersedes the 2026-10-19 current-directory job.sh default.
Local pilot directories are generator tests. Transfer the tested code, then
generate on Perlmutter from explicit recipe, material, launch-template and output
paths. The working launch script owns executable configuration and resources;
existing sbatch submission remains external. Readback receives explicit cluster
paths and writes host-bound provenance there. Cluster assets need not exist on
the development machine.

**Reason:** the user clarified the deployment boundary on 2026-10-21; implicit
working-directory discovery and local asset requirements obscure that boundary.
**Authority:** [Perlmutter pilot sequence](archive/PERLMUTTER_F0_PILOT.md).

## D-007 — Compute magnetic tensors, not bond vectors

**Status:** accepted 2026-11-02; supersedes the bond-resolved goal.  
Compute the spiralization tensor, stiffness tensor and exchange classes for any
material with one magnetic order parameter, then use them to predict properties.
BFO is a test material, not a special case. Mathematics Revision 3.0 is the
authority, with its Markdown edition for agents; if they disagree, the TeX wins.

**Reason:** the user concluded that interatomic DMI vectors are not feasible to
compute. Flat spirals have a structural rank ceiling for bonds, and the decorated
route depends on constrained families. The tensors are single sums that flat
spirals determine directly, and they are the quantities that predict textures.
The bond-era state remains available at tag `archive/bond-dmi-v3`.
**Authority:** [math Revision 3.0](math/heide_math_v3.tex), Sections 1 and 6.

## D-008 — Run unconstrained F0 spirals only

**Status:** accepted 2026-11-02; supersedes the constrained families.  
All spirals are flat F0 states at `LAMBDA = 0`. `I_CONSTRAINED_M = 1` stays only
for sphere moments. F1, F2, the lambda ladder, signed decoration chains and the
constraint-probe rerun are retired.

**Reason:** the first-order energy is complete only on the relaxed SOC-free state.
Rigid phases are biased whenever symmetry allows intracell twist. An FeGe-like
toy model shifted the stiffness by 7% and the spiralization by 35%, while a
BFO-like model with no allowed twist did not change. These are model results.
No VASP run has tested them.
**Authority:** math Sections 2.3 and 7.5.

## D-009 — Read all three axes from one state

**Status:** accepted 2026-11-02; replaces the Euler rotation of D-003 in
production. Fixture-level evidence only.  
Split the SOC operator into orbital matrices and form the trace vector directly.
No U matrices or Euler search are needed. Keep all four CSO blocks when reading.
T3 still compares the result with genuine x and y dumps.

**Reason:** the surviving operator is linear in the rotation axis, so one state
supplies a whole vector. This matched the rotated-operator trace to 10^-14 on
repository fixtures for x, y, z and generic axes.
**Authority:** math Sections 4.2 to 4.4.

## D-010 — Use structural symmetry as planner and test

**Status:** accepted 2026-11-02.  
Take operations from `spglib`, the one approved new dependency. Keep those that
map the sign pattern to itself or its reverse. Magnetic space groups are not used.
Build tensor bases by group average, retaining the det(R) factor for spiralization.
Report the free 9-component fit and its forbidden part alongside the constrained
result. Check both rank conditions on the q directions before writing inputs.

**Reason:** the SOC-free tensors describe all orientations of a pattern, not one
fixed spin direction. The forbidden part tests axis, frame and transpose errors
without external data. It cannot see an overall sign, so the sign needs an
external anchor. Symmetry-equivalent directions can leave the stiffness
underdetermined: BFO's three rhombohedral axes give rank 1 of 2.
**Authority:** math Sections 7, 8.2 and 9.2.

## D-011 — Use density-matrix dumps in production

**Status:** accepted 2026-11-02; pending a first real dump.  
Production `dump_P` writes COCC only. The first state of each material also writes
CPROJ and FERWE so that M1 can compare them.

**Reason:** the trace needs only on-site density matrices. At the size of the BFO
N0 run, one state falls from about 0.3 GB to about 0.2 MB of binary data, and dense
metallic k meshes become practical. The match to the CPROJ trace is established
on fixtures, and independent use of the COCC flag is not yet confirmed on VASP.
**Authority:** math Sections 4.4 and 5.

## D-012 — Compute both signs of q by default

**Status:** accepted 2026-11-02.  
Run an SCF and dump at both +q and -q, for twice the SCFs of a single-sided plan.
Going single-sided would need a new decision backed by parity data.

**Reason:** ideal states obey T(-q) = -T(q), but independent SCFs can differ. The
pair is the check that catches a repeat of the old even background.
**Authority:** math Section 4.5.

## D-013 — Replace the orchestration with a flat workflow

**Status:** accepted 2026-11-02; supersedes the T4b/T5 runner plan.  
Delete `runner.py`, `campaign.py`, `reference.py` and `workflow.py` with their
tests, after tagging and after moving `INCAR_TAGS`, `_echo_check` and the T3
wrapper. The new workflow is `plan`, `prepare`, `status`, `collect` and `fit`
around one material file, with a generated Slurm array. D-006 still applies:
inputs are generated on the cluster from explicit paths, and the user submits.

**Reason:** the ledger, locks, attempt tree and dependency graph served a campaign
that no longer exists, and T4b was unfinished. A run directory can be its own
state, so rerunning readback is always safe. This removes about 1,600 lines.

## D-014 — Validate through a small ladder of materials

**Status:** accepted 2026-11-02.  
Use bcc Fe as the null, strained zincblende CrSb as a synthetic positive control
and sign anchor, then BFO, FeGe and Mn2RhSn. Compare with published FLEUR
first-order results for BFO and FeGe. Compute K from standard SOC runs. For BFO,
start production from the N0 run's functional and U, and add a three-point U scan.

**Reason:** each system tests something different: a symmetry null, sign and
magnitude, a polar antiferromagnet, intracell twist and an antiskyrmion class.
Code-to-code agreement is the validation target. Published calculations of this
type give about 80 nm against 62 nm for BFO and about 140 nm against about 70 nm
for FeGe, so a gap from experiment is a result, not automatically a bug.
**Authority:** math Section 11.

## D-015 — Keep the test suite small

**Status:** accepted 2026-11-04.  
Aim for under 30 tests in total, with one test per physics result or file-format
contract. Do not write a test for each validation branch, input variant or fixed
bug. The suite went from 210 cases to 13 at TEN-01.

**Reason:** the user directed that the project does not need hundreds of tests.
Most of the old cases guarded orchestration or individual validation branches,
and they cost more to maintain than they protected. The 13 tests caught all 11
faults injected at the cut, including a wrong transpose and swapped COCC blocks.
