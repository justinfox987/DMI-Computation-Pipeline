# Project decisions

Keep entries concise and link the governing spec. Add a superseding entry if a
decision changes; do not erase why the previous choice was made. The entries
below record decisions already reached before repository integration.

## D-001 — Lab-vector input and sphere readback

**Status:** accepted working convention; production-build confirmation remains.  
Write MAGMOM and mode-1 M_CONSTR as physical vectors at SAXIS=(0,0,1).
Read OSZICAR M_int for geometry and MW_int for constraints. Do not introduce a
generic winding/unwinding layer or an OUTCAR fallback for fitted directions.

**Reason:** the Fe tests distinguish the sphere and projected readouts; supplied
VASP source performs the MAGMOM counter-rotation internally.
**Authority:** [math Revision 2.4](math/heide_math_v2.tex), Sections 3–4;
[Step 1 spec](dmi_step1_implementation_spec.md).

## D-002 — Use measured vectors directly in paired rows

**Status:** accepted.  
Keep F1 offset and F2 tilt as input controls. Normalize each state's M_int,
rotate a neighbor only by its bond cell translation, and evaluate both states.
Use y=(T_plus−T_minus)/N_m and the matching difference of model coefficients.

**Reason:** this removes redundant angle extraction, avoids double-counting the
intracell phase and preserves actual partner differences.
**Authority:** math Sections 3 and 8; Step 1 spec Sections 3–6.

## D-003 — Select Cartesian components through the SOC operator

**Status:** accepted; genuine-dump validation still required.  
Production SCFs stay in the fixed z spin convention. Rotate the full SOC operator
to select x/y/z, then retain diagonal spin blocks. Do not also rotate the targets.

**Reason:** one state supplies all three measurement axes consistently.
**Authority:** math Section 5 and the retained T3 requirement.

## D-004 — First-order method and staged production validation

**Status:** accepted.  
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
**Authority:** [repository setup](REPOSITORY_SETUP.md) and root AGENTS.md.

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
**Authority:** [Perlmutter pilot sequence](PERLMUTTER_F0_PILOT.md).
