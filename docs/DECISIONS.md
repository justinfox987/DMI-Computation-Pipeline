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
**Amended 2026-11-08 (TEN-04):** the Euler search is deleted. T3 now checks that C_uu of a genuine SAXIS = x or y dump equals Lambda_x or Lambda_y from the z dump (math Section 11).

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

**Amended 2026-11-08 (TEN-03):** there is no `status` command; `collect` prints one state per run.

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

## D-016 — Describe each material with one seed file

**Status:** accepted 2026-11-04.  
Each material is a folder under `materials/` holding a POSCAR, an `INCAR` with
electronic settings only, a `KPOINTS` and a `seed.toml`. The seed is TOML, numbers
magnetic sites from 1 in POSCAR order, and holds no machine paths; the Slurm
template is passed on the command line. Unknown keys are rejected.
**Reason:** POSCAR stays the main input, TOML allows comments and is read by the
standard library, 1-based sites match how atoms are counted in a POSCAR, and a
seed without paths works on any machine and is safe in the public repository.
**Authority:** `docs/seed_file.md`.

## D-017 — Detect symmetry from POSCAR, with an optional space-group check

**Status:** accepted 2026-11-04.  
spglib finds the space group from POSCAR at `symprec = 1e-3` Å, which a seed can
change. An optional `spacegroup` in the seed stops the run if spglib finds another
group; it is a check, not an override. Every operation must be orthogonal and map
magnetic sites onto each other within `2 * symprec`. `plan` prints the group and
the kept and dropped counts first. No `symprec` sensitivity report.
**Reason:** a prototype showed both tolerance errors pass silently: strained
zincblende reads as cubic with a loose tolerance, and noisy BFO reads as `P1` with
a tight one. The orthogonality and site checks catch strain and wrong site lists.
Only the space-group check catches the rest, so production seeds should set it.
The sensitivity report tripped on correct settings and could not say which answer
was right.
**Authority:** `plans/ten-02-symmetry.md`, math Section 7.

## D-018 — Use finite smearing and the free energy

**Status:** accepted 2026-11-09.  
Every material INCAR sets `ISMEAR` and `SIGMA`. `ISMEAR` must be `-1`, `0` or
`1` (Fermi-Dirac, Gaussian, Methfessel-Paxton order 1), with `SIGMA` about
0.05 eV. `prepare` and `plan` reject any other `ISMEAR`, and a `SIGMA` below
0.05 eV unless the seed sets a lower `min_sigma` for a convergence series.
Energies come from the OUTCAR `free energy TOTEN`.
**Reason:** the force theorem needs a variational energy. `free energy TOTEN` is
the Mermin free energy, which is variational at finite smearing. Tetrahedron
modes are not variational, so their first-order SOC energy is not the trace of
the frozen state.
**Authority:** [math Revision 3.1](math/heide_math_v3.tex), Sections 3.2 and 3.3.

## D-019 — The user owns the electronic settings and inputs

**Status:** accepted 2026-11-09; supersedes the TEN-03 rejection of unreviewed
INCAR tags.  
The user supplies each material's `POSCAR`, `INCAR`, `KPOINTS` and `POTCAR`,
and they are committed as given. The `POTCAR` is never committed; a
`POTCAR.spec` with its name, TITEL and SHA-256 is committed instead. Agents and
specs do not choose structures, potentials, functionals, cutoffs, smearing,
spheres, SCF or parallel settings. Specs give factual notes only. The code:

- writes the Section 3.2 spiral tags and rejects a contradiction;
- requires `RWIGS` (one per species type), `ENCUT`, `ENINI`, `ISMEAR` and
  `SIGMA`, and applies D-018;
- rejects `KSPACING`, because the `KPOINTS` file sets the one mesh for every
  `q`.

Any other tag the code has not seen is kept as given: `plan` prints a warning,
and the OUTCAR echo check accepts it.

**Reason:** the electronic settings are the user's physics decisions. The
whitelist turned every new tag into a code change and an agent judgment. The
rules that protect the method stay: the spiral tags, the force-theorem smearing
rule, the single mesh, and the echo check that VASP received each tag.
**Authority:** user decision, 2026-11-09; math Section 3.2.

## D-020 — Contract the dump files as VASP does

**Status:** accepted 2026-11-11; code change pending (FIX-1). Supersedes the
"contract elementwise, not with a matrix trace" rule of Revisions 2.4 to 3.1.  
`CSO.dat` and `COCC.dat` both store the ket index first. The trace is
`Re sum Lambda_file * conj(COCC_uu - COCC_dd)`, VASP's own form of the SOC
energy. The code up to `454afa2` drops the conjugate, which reverses the sign of
every `T`, so of `D` and the predicted rotation sense. Magnitudes, the forbidden
part, the pitch, N0, P0 and M1 are unaffected.

**Reason:** `relativistic.F` stores `D(lm, l'm', a + 2a') = <a'|<l'm'|D|lm>|a>`
and computes `Re sum CSO * CONJG(COCC)`; `DEPSUM` and `COCC_FROM_INPUT` share one
layout. A bookkeeping test with those layouts returns minus the exact value
without the conjugate. The real BFO `CSO.dat` has the handedness that layout
predicts (-0.707 on O). This is source reading and a bookkeeping test, not a
VASP run; the supercell control confirms it.
**Authority:** math Revision 3.2, Sections 4.2 and 4.4; `plans/simplify-1.md`
item 1.1.

## D-021 — Recompute from the VASP files; M1 once per build; no T3 runs

**Status:** accepted 2026-11-11; code change pending (SIM-1). Amends D-009,
D-011 and D-013.  
- Every command reads OUTCAR, OSZICAR, COCC and CSO again. `collected.json` and
  `traces.json` are reports and are never inputs. The hash, `parent.json`,
  `provenance.json`, `config.json` and OUTCAR-echo guards go. One guard stays:
  a `COCC.dat` must be newer than its parent's OUTCAR.
- M1 moves to a standalone script and runs once per production build, on one
  state whose `dump_P` the user gives `LDUMPCPROJ = T`. The package keeps only
  the CSO and COCC readers. `dmi dumps` no longer sets `LDUMPCPROJ`.
- `dmi dumps` no longer writes `dump_C_x` and `dump_C_y`. C0 gains the
  handedness check of math Section 4.2, which pins the flip-block order from
  the z dump. T3 is optional, by hand, once.
- The OSZICAR reader takes the last `M_int` block of a static run.

**Reason:** the guards protect against a stale intermediate file, which
recomputing removes; a 1 MB dump loads in 0.05 s. M1 tests the Fortran routine
`COCC_FROM_INPUT`, a property of the build, and already passed at 5e-15 on the
BFO dump. The CPROJ and FERWE readers are about 600 of the package's 2,537
lines, and the FERWE reader rejects every smeared state. T3 pinned one bit that
D-020's evidence already fixes.
**Authority:** `plans/simplify-1.md` items 1.2, 2.2 to 2.4 and 2.6.

## D-022 — The one smearing rule is no tetrahedron

**Status:** accepted 2026-11-11; code change pending (SIM-1). Narrows D-018 and
completes D-019.  
The code overrides the tags it owns (`LNONCOLLINEAR`, `LSPIRAL`, `LSORBIT`,
`LZEROZ`, `SAXIS`, `ISYM`, `I_CONSTRAINED_M`, `LAMBDA`, `QSPIRAL`, `MAGMOM`,
`M_CONSTR`) and prints one line per override. It refuses tetrahedron smearing.
It checks no other tag: the `ISMEAR` allowlist, the `SIGMA` floor, `min_sigma`,
the required `ENCUT`, `ENINI` and `RWIGS`, the `KSPACING` rejection and the
known-tag list go. Energies still come from `free energy TOTEN`.

**Reason:** the force theorem needs a variational energy, and tetrahedron modes
do not give one; that is the whole physics content of D-018. Everything else is
the user's choice. The user's own Fe INCAR was stopped twice by the old checks.
**Authority:** `plans/simplify-1.md` item 2.5; math Section 3.2.

## D-023 — Noise from the parity residuals; one solve per tensor

**Status:** accepted 2026-11-11; code change pending (SIM-1). Replaces
decisions 3 and 4 of `plans/ten-05-tensors.md`.  
`sigma_y` is the RMS of `[T(q) + T(-q)]/N_m` over all pairs and axes, and
`sigma_g` that of `[E(q) - E(-q)]/2N_m`. The fit is one linear solve with the
tensor components and one nuisance term per direction and axis; covariances
follow from its pseudoinverse. The pooled fit variance, `MIN_PAIRS` and the
`poorly_determined` flag go. The rank condition is full column rank of the
design matrix.

**Reason:** the pairs measure the noise directly, with 27 samples for the
standard plan against 9 degrees of freedom. The single solve reproduces the
current `D_free`, `D`, `F` and `A` to 1e-12 on the spin models.
**Authority:** math Revision 3.2, Section 9.4; `plans/simplify-1.md` item 2.7.

## D-024 — Anisotropy by self-consistent SOC energies, in its own module

**Status:** accepted 2026-11-11; build deferred until the spiralization tensor
works on VASP output.  
`K` comes from self-consistent SOC total energies along symmetry-chosen
directions, fitted to the symmetry-allowed even polynomials of order 2 or 4. A
uniaxial magnet gets five runs: the fit directions, one spare and two noise
runs. The code writes `submit.sh` and the user submits. The force-theorem value
is not computed.

**Reason:** canting is second order in SOC, like `K` itself, so the functional
needs the relaxed energy. The spare and noise runs are what detect a wrong
order or a different electronic branch.
**Authority:** `plans/anisotropy-1.md`; math Revision 3.2, Section 13.

## D-025 — One math document

**Status:** accepted 2026-11-11.  
`docs/math/heide_math_v3.tex` is the only copy of the mathematics, now Revision
3.2. `heide_math_v3.md` holds the agent notes only. The project copy
`claude/heide_math_v3.tex` is replaced by the repository file. New material
goes in a new last section or an unnumbered display, so no equation number
moves. Exchange classes and the twist count stay in the math: exchange is a
project goal for a later task, and the twist gate is a real check on twist-free
materials. The half-built `exchange_grid` and `rmax` seed keys leave the code
until that task.

**Reason:** two different documents were both called Revision 3.1, with
different equation numbers, and the Markdown edition was kept in step by hand.
**Authority:** `plans/simplify-1.md` items 2.1 and 2.9.
