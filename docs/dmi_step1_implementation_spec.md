# DMI pipeline Step 1: lab-vector inputs, readback and paired fitting

**Version:** 1.0 · **Date:** 29 September 2026  
**Mathematical baseline:** *From Heide’s Force Theorem to the VASP Trace*, Revision 2.4, 26 September 2026 (`heide_math_v2.tex`).  
**Deliverable:** a tested code migration and a short implementation report. This specification is sufficient to start in a fresh Codex session.

## 1. Objective and scope

Make the target writer, moment reader, realization checks and paired design matrix use one consistent representation: physical Cartesian moment vectors in the calculation cell, with `SAXIS = 0 0 1`.

The scientific workflow is unchanged: prepare SOC-free spin spirals, evaluate their first-order SOC traces, and fit bond DMI vectors from paired states. This patch replaces redundant angle/frame bookkeeping. It does not implement second-order SOC or change the Hamiltonian.

In scope:

- Direct lab-vector `MAGMOM` and mode-1 `M_CONSTR` generation.
- OSZICAR `M_int` and `MW_int` parsing with explicit source and convergence checks.
- Signed vector-based realization and pair checks.
- A vector-based bond kernel, wired into planning, pair assembly and fitting.
- Explicit handling of old records, focused regression tests and updated usage/probe instructions.

Out of scope: Slurm orchestration, submitting VASP jobs, the full constraint campaign, new SOC dump/rotation research, new noise estimates, production parameter choices, broad code cleanup and second-order SOC. Leave unresolved production choices unresolved. Local synthetic tests must not certify production physics gates.

## 2. Authority and known evidence

Use Revision 2.4 and this specification for the changes above. Older September 15–17 inventories are **navigation aids**, not a statement of the current repository. Inspect the actual checkout, its `AGENTS.md`, working-tree changes and baseline tests before editing. Locate symbols by search; do not rely on historical line numbers or assume the active directory is still named `pipeline v2`.

These older instructions are superseded:

| Old assumption | Required behavior |
|---|---|
| `FRAME_MCONSTR = "unwound"` | Write physical lab targets directly. |
| `FRAME_MINT = "unwound"` used for all moment outputs | Distinguish the outputs; use OSZICAR sphere moments as lab vectors under the tested contract. |
| Recover site azimuths/cone angles, then rebuild the model spins | Normalize `M_int` once and use the resulting vectors. |
| Apply a generic frame adapter to every input/output | No such conversion in the production path. |
| Rotate targets to each measurement axis | Keep SCF targets at fixed spin axes; select the measurement axis through the SOC operator. |
| Build a bond phase with full displacement and measured lab moments | Rotate only by the bond’s **cell translation**. |
| Use an exact-partner shortcut for measured data | Evaluate both measured states independently. |

The user’s bcc Fe tests and supplied VASP source support this contract. In `main.F`, `LSPIRAL` triggers `COUNTER_SPIRAL` before initial-density construction. That routine rotates initial moments by minus the position-dependent spiral phase; pre-unwinding `MAGMOM` would compensate twice. The Fe constrained runs independently support lab-frame `M_CONSTR`, `M_int` and `MW_int`.

This evidence does not supply the production executable hash or validate BFO. Keep convention evidence separate from production-build acceptance. Historical N0 passed for its recorded files; do not invalidate that record or relabel it as evidence for a new executable.

## 3. Target generation and VASP interface

### 3.1 One target vector per magnetic site

Let `q_frac` be reciprocal fractional coordinates and `tau_frac[a]` the matching POSCAR direct fractional position. Both are dimensionless triples. All internal trigonometric arguments are radians; user-facing recipe fields must label degrees or radians explicitly.

Use the ordinary rotation:

```text
rotate_z((x,y,z), t) = (x*cos(t) - y*sin(t),
                        x*sin(t) + y*cos(t),
                        z)
target[a] = rotate_z(base[a], 2*pi*dot(q_frac, tau_frac[a]))
```

For the existing two-Fe G-type reference, the base vectors are:

| Family | Fe1 base | Fe2 base |
|---|---|---|
| F0 | `(1,0,0)` | `(-1,0,0)` |
| F1 | `(1,0,0)` | `(-cos(psi),-sin(psi),0)` |
| F2a | `(sin(theta),0,cos(theta))` | `(0,0,-1)` |
| F2b | `(0,0,1)` | `(-sin(theta),0,-cos(theta))` |

`psi` is the extra F1 rotation of Fe2 relative to F0, positive from +x toward +y. `theta` tilts the active F2 site from +z toward +x on Fe1, or from −z toward −x on Fe2, before the position rotation. Baseline values are 30 degrees. They are **recipe inputs only**, not required fields of the measured state.

Use the repository’s explicit magnetic-site mapping and reference signs. The table must not silently impose BFO’s antiferromagnetic signs on a ferromagnetic Fe test or a different material. For existing supported signed references, form the corresponding signed base vectors directly. Preserve that support; do not build a new arbitrary-magnetic-order framework.

### 3.2 Write the physical vectors unchanged

- `MAGMOM`: target unit direction multiplied by that site’s positive seed magnitude.
- `M_CONSTR`: the same target unit direction, without magnitude scaling, for `I_CONSTRAINED_M = 1`.
- Write all ions in POSCAR order. Keep the established nonmagnetic seed policy and zero Bi/O constraint targets; zero-target exclusion still requires matched production source/binary evidence.
- Keep `SAXIS = 0 0 1`, `LNONCOLLINEAR = T`, `LSORBIT = F`; use `LSPIRAL = T` for finite-q preparation. Do not change inputs when evaluating x/y/z SOC traces from the same state.
- Enable mode 1 and explicit `LAMBDA = 0` for unconstrained sphere readback. Positive constraint strength must be supplied by the run configuration. Do not omit `LAMBDA` and inherit an unintended default.
- Require one explicit `RWIGS` value per species. `LORBIT = 11` does not provide a substitute for constraint-sphere integration.
- F0 is planar; F2 requires `LZEROZ = F`. F1’s production `LZEROZ` choice remains unvalidated. Permit explicitly labeled diagnostic candidates; do not silently select a production winner.

Changing `MAGMOM` on a magnetic restart does not rotate inherited wavefunctions. Preserve the established parent policies: signed F1 continuation through 30→60→90 degrees, and near-target F2 cold starts. This patch may correct emitted inputs and metadata but must not build or launch their scheduler.

### 3.3 Construct the partner as a vector operation

```text
q_minus = -q_plus
target_minus[:, :] = target_plus[:, :] * (1, -1, 1)
```

Keep site ordering, family, rotating/axial assignment and longitudinal signs. For F1 this also means `psi_minus = -psi_plus`; for F2 the tilt stays fixed.

If existing code reduces q modulo a reciprocal lattice vector, preserve the already-constructed physical cell targets. Regenerating them from the reduced q and unchanged recipe can change intracell directions. The translation kernel is invariant under integer reciprocal shifts when cell vectors are held fixed; target generation need not be.

## 4. OSZICAR reader and state record

### 4.1 Separate parsing, validity and acceptance

Use one shared reader for the main pipeline and the constraint probe.

1. Parse per-ion OSZICAR rows headed `ion MW_int M_int`. Retain both three-component vectors without rotation.
2. Associate them with the same run segment and final SCF/ionic record as `E_p`, `lambda` and, when printed, `lambda*MW_perp`. Moment rows can precede the `F=` summary and penalty rows can follow it; do not assume they are all on one line.
3. Require a complete block with each expected ion exactly once. Handle whitespace, signed zero, and Fortran `E`/`D` exponents. Reject nonfinite values, missing columns, duplicate IDs and count mismatches.
4. Do not silently use a previous complete block when the terminal block is truncated. For concatenated restarts, explicitly identify the final run segment and its convergence evidence. Ambiguous segments are not production input.
5. Reuse the existing verified electronic-convergence check. A final `F=` line, an OUTCAR file, or a process exit code alone does not prove convergence. Parseable excerpts may support parser tests without becoming accepted calculations.

OUTCAR remains useful for settings, build identity, convergence and optional projected-moment diagnostics. It must not supply fitted spin directions when OSZICAR data are absent. Do not read `lambda` from an INCAR echo as if it were the final printed penalty coefficient.

### 4.2 Minimal data contract

Extend existing records instead of creating a second manifest system. Field names may follow repository style, but preserve these meanings:

| Data | Requirement |
|---|---|
| Configuration identity | ID, family/F2 assignment, parity side, actual q, POSCAR identity and explicit magnetic-ion mapping |
| Requested directions | Lab unit target vectors; seed magnitudes separate; recipe controls retained only as input provenance |
| Raw readback | `M_int`, `MW_int`, and their norms; retain every ion’s values |
| Fitted directions | `S[a] = M_int[a] / norm(M_int[a])` for resolved magnetic sites |
| Constraint record | Printed `E_p`, final `lambda`, and printed field when available |
| Provenance | Moment source, selected segment/block or line range, relevant input tags, file identities and executable evidence available |
| Acceptance | Individual and pair results, actual tolerances, failure reasons and convention/schema version |

Small or zero nonmagnetic moments are not normalized into model spins. A required magnetic moment below the explicit resolution threshold makes the state unusable. Preserve norms for collapse/drift checks; normalized vectors alone cannot detect collapse.

Do not require measured `phi`, `psi`, `theta` or an unwound vector. Angles may be produced for human-readable diagnostics, but no downstream production calculation may depend on them.

## 5. Signed realization and constraint checks

### 5.1 Geometry

For unit vectors, a signed dot product greater than `cos(1 degree)` implements the nominal direction tolerance. Clamp dot products only if converting them to diagnostic angles.

- Compare the full `M_int` directions with targets.
- For nonaxial targets, also compare normalized xy projections with the same nominal 1-degree phase tolerance. A small 3D deviation near the axis does not guarantee the correct in-plane direction.
- A nonaxial target with unresolved transverse readback fails. For an axial target, check the full signed direction instead; there is no azimuth to extract.
- Preserve the existing phase-RMS report. Passing every resolved phase error at 1 degree implies that RMS bound; it need not create another state variable.
- Reject antiparallel solutions. Never use absolute dot products or independent sign flips.
- Retain the 5% nominal magnitude-drift criterion against a same-definition, same-`RWIGS` reference. Compare weighted and unweighted magnitudes only to their corresponding references.
- Check agreement of normalized `M_int` and `MW_int` within the declared direction budget (nominally 1 degree unless explicitly configured otherwise). Report disagreements; do not choose whichever readout passes.

Where existing family policy allows it, geometry may be compared after **one common rotation about z**, applied to all target sites. Use the same rotation for full-vector and transverse checks. This adjustment is for validation only: keep raw measured directions unchanged for the fit. A single common rotation cannot hide relative-site errors. Preserve signed axial polarity.

### 5.2 Constraint alignment uses MW_int and absolute targets

No common-rotation adjustment is allowed for alignment against the actual `M_CONSTR` vectors. For a constrained ion with unit target `u` and weighted moment `MW`:

```text
MW_perp = MW - u*dot(u, MW)
B_c     = 2*lambda*MW_perp
E_p     = lambda*sum_over_constrained_ions(dot(MW_perp, MW_perp))
```

The zero-target ions must be excluded, not normalized. Preserve the nominal recorded `E_p < 1e-3 eV` requirement for constrained production rows. At lambda zero, the penalty vanishes; geometry still requires checking.

Both parallel and antiparallel moments have zero penalty, and a perpendicular moment has zero first-order angular push from this term. A small penalty does not certify the requested signed state.

The supplied Fe build printed `2*lambda*MW_perp` under the label `lambda*MW_perp`. Validate the numerical factor using the printed field and penalty; do not assume the label defines it for every build. Moment rounding limits the recomputed precision. Missing field data must yield an explicit unavailable diagnostic, not an invented field-validation PASS.

### 5.3 Pair checks

Require compatible structures/site maps, the same family/F2 assignment and measurement axis, opposite q modulo reciprocal translations, and accepted individual states. Compare the mirrored positive geometry with the negative geometry using the declared pair tolerances and the common-z-rotation policy where appropriate.

Small accepted geometric differences are handled by evaluating each side’s own kernel. Wrong signs, moment collapse, missing convergence, or failed individual checks cannot be repaired by “use realized geometry.” Preserve separate statuses for geometry, trace parity and unavailable evidence.

## 6. Replace the angular bond kernel

The native DMI Hamiltonian is the **plus-sign** sum of `d_b · (S_i × S_j)` over canonical bonds, counting each undirected bond once. `d_b` has energy units and `S` is a unit spin. The existing symmetry basis expresses `d_b = sum_j p[bond,j]*x[j]`.

For a canonical bond from site `a` in the reference cell to site `b` in integer cell translation `R`, use:

```text
neighbor = rotate_z(S[b], 2*pi*dot(q_frac, R))
g        = cross(S[a], neighbor)[2]
A[j]    += g * dot(n_hat, p[bond,j])
```

`S` contains the measured unit vectors for one state. `n_hat` is the selected x, y or z measurement axis. `p[bond,j]` is the existing symmetry-propagated vector multiplying DMI parameter `x[j]`.

Requirements:

- Use integer cell translation `R`, **not** `R + tau[b] - tau[a]`. The measured vectors already contain intracell orientation.
- Do not multiply by a separate reference-sign product. Those signs are already in `S`.
- Do not multiply by moment magnitudes: the Hamiltonian uses unit spins.
- Keep existing canonical bond counting, symmetry propagation `det(Q)*Q`, bond-reversal signs, parameter order and energy units.
- Obtain `N_m` from the explicit magnetic-site count; do not infer it from a site index.
- Use the same kernel for target-based planning and measured-state assembly, supplying different vector arrays. Do not retain a second angular production kernel.

Taking the z component already performs the lattice average for a generic nonzero spiral: transverse cross-product components cancel over translated cells. Rotating–axial bonds therefore contribute zero; flat and conical rotating–rotating bonds use the same expression. Do not add a numerical lattice sum to production.

The generic-q reduction is not a general energy expression at q equal to a reciprocal lattice vector. Preserve the production q exclusions and the separate in-plane-collinear q=0 electronic null test.

Form the paired observable and model row as:

```text
y       = (T_plus - T_minus) / N_m
row[j]  = (A_plus[j] - A_minus[j]) / N_m
```

Each side uses its own measured vectors and actual q. There is no extra factor of one-half, and no production shortcut `2*A_plus/N_m`. Preserve the raw pair-sum test; subtraction does not excuse an excessive common background.

Do not fabricate uncertainty to make the solver run. Existing valid supplied uncertainties may be used; otherwise report missing noise evidence. Preserve weighting/covariance semantics and distinguish an assembled diagnostic row from an accepted weighted fit.

## 7. Preserve the electronic trace boundary

This migration changes magnetic geometry, not the frozen-state electronic inputs:

- Keep Patch B indexed `CPROJ`, matching `FERWE` and `COCC` provenance.
- Do not apply moment rotations to `CPROJ` or `COCC`.
- Keep full SOC spin blocks when constructing x/y/z operators; select diagonal blocks only after operator rotation. Do not reinstate a “spin-flip blocks must vanish” condition.
- Preserve `COCC[i,j] = rho[j,i]` and its elementwise contraction with the matching SOC matrix entries.
- Keep the SOC operator axis equal to the design-row axis. No second axis rotation of targets or measured moments.
- Do not add or subtract the constraint penalty from the SOC trace.
- Retain genuine-dump axis validation and existing acceptance evidence. Synthetic matrix tests do not grant a new T3 pass.

If the current checkout contains an unrelated trace or dump blocker, report it distinctly. Fix a directly required integration defect when its intended behavior is established; do not expand this task into rebuilding the full campaign.

## 8. Likely edit locations and migration behavior

Historical names below must be checked against the actual repository:

| Location | Expected change |
|---|---|
| `targets.py`, relevant `materialize.py` callers | Direct vector recipes and writers; no pre-unwind or measurement-axis spin rotation; explicit lambda/readback inputs |
| `conventions.py`, `frames.py` | Remove obsolete switches from the live path; reuse ordinary z rotation where useful |
| `realized.py`, `realized_state_gate.py`, probe reader | Shared OSZICAR reader, measured-vector record, signed checks and weighted-field diagnostics |
| `model.py`, `design.py` | One vector kernel, using bond cell translations and both measured sides |
| `planner.py` | Evaluate that kernel on requested vectors; preserve physical targets when pairing/wrapping q |
| `manifest.py` | Explicit vector/readback convention version and migration rejection/rebuild path |
| `cli.py`, `solve.py`, `report.py` | Wire shared data through actual commands; axis identity and evidence-bearing acceptance |
| Existing tests and usage/probe docs | Replace stale assumptions; retain historical records as historical |

Do not delete all of `frames.py` or rewrite symmetry enumeration solely because their names look old. Remove obsolete live calls and redundant APIs where safe; keep legacy forensic handling explicitly separate.

Old angle-only or OUTCAR-derived records must not silently acquire the new meaning. Add a schema/convention marker using existing versioning machinery. Rebuild new records from original OSZICAR plus matching inputs when available, preserving the original records. Otherwise reject production use with an actionable message. Target-only old configurations may be migrated only when their complete recipe, structure and sign convention are known.

An old manifest must not re-enable unwound production behavior through global convention overrides. Do not preserve legacy field names in a way that silently routes the new writer back through the old adapters.

Update affected local documentation, especially the constraint-probe table that still labels most production targets “unwound.” Keep any deliberately wrong-frame discriminator clearly labeled as a diagnostic comparison. Do not silently delete all later probe controls or claim the simplified conventions are production-validated.

## 9. Required regression evidence

Use focused tests of these failure modes. Existing implementation aliases are not independent reference oracles.

### 9.1 Target and bond checks

Use `tau1=(0,0,0)`, `tau2=(0.5,0.5,0.5)`, `q=(0.25,0,0)`:

| Case | Expected physical target |
|---|---|
| G-type F0, Fe2 | `(-0.7071067812,-0.7071067812,0)` |
| G-type F1, psi=+30°, Fe2 | `(-0.2588190451,-0.9659258263,0)` |
| G-type F2b, theta=30°, Fe2 | `(-0.3535533906,-0.3535533906,-0.8660254038)` |

Verify both INCAR writers preserve those directions, partner targets flip y, and measurement-axis changes do not alter SCF inputs. Also test a ferromagnetic reference and stable POSCAR ion mapping.

For an intracell canonical bond, set `S1=(1,0,0)`, `S2=(-sqrt(3)/2,-1/2,0)`, `n_hat·d=1 meV`, `N_m=2`. The positive and negative model traces are −0.5 and +0.5 meV per cell; the paired result is **−0.5 meV per magnetic site**.

Check:

- Intracell `R=0` needs no extra rotation, even at finite q.
- Translating the neighbor changes the result with the correct sign; reversing a directed bond reverses its cross-product coefficient.
- No extra antiferromagnetic sign or magnitude factor appears.
- An exactly axial endpoint contributes zero; near-axis vectors remain numerically usable without `atan2`.
- A common z rotation leaves the kernel invariant; mirrored partners with opposite q reverse it.
- A complete commensurate real-space average of conical bond cross products agrees with the vector kernel. Keep this as a test oracle only.
- Perturb an otherwise valid negative state slightly: paired assembly must use its new vector rather than double the positive result.
- Integer reciprocal shifts preserve the kernel for fixed cell vectors. A wrapping test must catch accidental target regeneration.
- Preserve expected rank/parameter results for the unchanged BFO fixture (nine parameters at `R_max = 6 Å`; F0 alone rank four), if that exact fixture is present. Do not assert these counts for another structure.

### 9.2 Fe readback fixtures from the user’s runs

The following are **excerpt-level evidence**, not complete convergence or executable-provenance records. Preserve numeric precision and source labels. They are not BFO-family realization tests.

Unconstrained finite-q sphere block:

```text
 ion        MW_int                 M_int
  1  1.668 -0.696  0.000    2.073 -0.866  0.000
  2  1.668  0.696  0.000    2.073  0.866  0.000
   1 F= -.16440894E+02 E0= -.16439259E+02 d E =-.326940E-02 mag= 4.0418 -1.6742 0.0000
 E_p = 0.00000E+00 lambda = 0.000E+00
 ion             lambda*MW_perp
  1   0.00000E+00  -0.00000E+00   0.00000E+00
  2   0.00000E+00   0.00000E+00   0.00000E+00
```

Normalize the two `M_int` vectors without any site rotation. Their y components have opposite signs. The corresponding OUTCAR projected vectors were `(2.087,-0.872,0)` and `(2.092,-0.860,0)`; deliberately include them in a companion test file and verify they cannot replace the sphere readback.

Constrained finite-q block, both targets +x:

```text
 ion        MW_int                 M_int
  1  1.812 -0.044  0.000    2.259 -0.033  0.000
  2  1.812  0.044  0.000    2.259  0.033  0.000
   1 F= -.16380878E+02 E0= -.16379693E+02 d E =-.237054E-02 mag= 3.7810 -1.5662 0.0000
 E_p = 0.39240E-02 lambda = 0.100E+01
 ion             lambda*MW_perp
  1   0.00000E+00  -0.88590E-01   0.00000E+00
  2   0.00000E+00   0.88589E-01   0.00000E+00
```

Expected: `lambda=1`, `E_p=0.003924 eV`; weighted direction errors approximately 1.39°, unweighted errors approximately 0.84°. The printed field supports the factor two. Its summed squared norm divided by `4*lambda` is approximately `0.00392405 eV`. Account for printed rounding when recomputing from moments.

This record **fails** nominal absolute weighted alignment and penalty thresholds, even though the unweighted directional error is below 1°. Do not label it an overall production PASS.

### 9.3 Failure and integration cases

Cover incomplete trailing blocks, multiple records/segments, `D` exponents, duplicate/missing ions, zero magnetic moments, absent convergence, and missing OSZICAR despite a plausible OUTCAR. Test antiparallel zero-penalty states and nonaxial targets with unresolved transverse moments.

Demonstrate that one permitted common rotation can remove a global offset but cannot remove site-dependent errors, and cannot be used to pass absolute MW alignment. Demonstrate the near-axis case where the 3D test passes but the transverse-direction test fails.

Run at least one integration test through the real public entry points: target writing → fixture readback → signed validation → two-sided model row → solver input. Use explicitly synthetic trace/uncertainty/convergence fixtures where necessary and label them as such. Verify missing partner, wrong axis, old convention records and missing uncertainty do not produce accepted fits. Do not monkeypatch the old frame switches merely to keep the integration test green.

## 10. Implementation sequence and definition of done

1. Record the actual code paths, baseline test results and relevant existing instructions. Preserve unrelated edits.
2. Implement the shared vector representation and target/partner generation.
3. Implement the shared reader and signed checks; validate against the excerpt and failure fixtures.
4. Replace and wire the bond kernel through planning and paired assembly.
5. Add explicit record migration/rejection, update affected instructions, and run targeted integration plus the relevant existing regression suite.

Finish with a concise report containing changed paths, commands/results, any pre-existing failures, migration instructions, and remaining production-only checks. Identify substantive deviations from this spec with reasons. Do not claim that a spec change, unit test, parser success or numerical equivalence test is a new VASP validation result.

Done means the live writer → reader → gate → row path satisfies this contract without hidden winding adapters or angle reconstruction. No code is submitted to the cluster as part of Step 1.

## 11. Handoff to Codex in VS Code

Save this file as `docs/dmi_step1_implementation_spec.md` in the actual repository. Keeping the Revision 2.4 LaTeX source alongside it is useful for derivations, but the implementation contract above does not require access to this chat.

Start a new Codex task with:

> Implement Step 1 from `docs/dmi_step1_implementation_spec.md`. Read the repository’s applicable instructions, inspect the current code and baseline tests, then implement the scoped migration and its regression tests. The historical inventory is only a navigation aid. Preserve unrelated work and existing physical conventions except where the spec explicitly supersedes them. Do not submit VASP jobs or invent production acceptance results. Complete the work with a report of changed files, test results, migration behavior and remaining production checks.

For recurring tasks, append a short pointer to an existing applicable `AGENTS.md`; do not replace its other instructions:

```markdown
For DMI Step 1 work, read docs/dmi_step1_implementation_spec.md before editing.
It implements mathematics Revision 2.4 and supersedes older unwound-target
and OUTCAR-based realization assumptions within that scope.
Keep production validation evidence distinct from local software tests.
```

The spec is the durable handoff. Do not assume another Codex session has this conversation, the attachments, or access to the same filesystem.

## Source basis

This specification implements Revision 2.4 of `heide_math_v2.tex` and the user-supplied Fe outputs/source excerpts reproduced or summarized above. Repository navigation comes from the September 15 `pipeline-v2-inventory.md`; staging boundaries and retained campaign policy come from `next_steps.md`, `preflight_review.md`, `constraint_probe_v2_protocol.md`, `perlmutter_test_runner_spec.md` and `full_test_data_requirements.md`. No current repository or production executable was inspected while writing this spec. It describes work to implement, not work already completed.
