# Decorated Spin Spirals in VASP: Implementation Specification

**Companion to** *Bond-Resolved DMI from Decorated Spin Spirals* (the derivation), *From Heide's Force Theorem to the VASP Trace* (the trace companion), and *Two-Trace Generalized Parity* (`new_direction.md`).
**Status:** engineering specification. Revision 2, September 2026 — rewritten for the Patch B dump architecture after the even-background diagnosis.
**Supersedes:** Revision 1 (July 2026). Sections marked **[CHANGED]** differ materially from Rev 1; **[DONE]** records work that has since been completed; **[OPEN]** marks what is still unresolved.

---

## 0. Scope, assumptions, inventory

### 0.1 What changed since Revision 1, in one paragraph

Rev 1 assumed the trace could be evaluated on projections dumped from a per-configuration SOC run (`ICHARG=11, NELM=1, LSORBIT=.TRUE.`). It cannot. That run performs a subspace rotation in the **full SOC Hamiltonian** before the dump hook fired, so the projections described SOC-perturbed orbitals rather than the frozen SOC-free eigenstates the force theorem requires. The symptom was a reproducible, Bi-dominated, q-**even** background of ~0.6 eV against a ~10⁻⁴ eV signal, and a q = 0 trace of 0.69 eV where a spin-only $C_{2x}$ argument forces exactly zero. The fix is architectural: **projections now come from the Stage-2 SOC-free run itself**, captured at a single named point (`PRE_LOOP`) before any eigensolver touches the orbitals, and the SOC operator comes from a separate, material-level dump. Everything in the derivation, the orbit machinery, the design map, and the solver is untouched. What changed is *which run produces which file*, and the addition of one acceptance gate (N0) that would have caught the original failure in an afternoon.

### 0.2 What exists and is frozen **[CHANGED]**

**Frozen and validated:** the derivation and its companions; `orbits.py` (bonds, space-group orbits, Moriya projectors, propagation); `model.py`/`design.py` (design map, configuration kernel); `planner.py` (Stage 0, pivoted-QR selection); `solve.py` (stacked SVD, covariance). None of this reads a VASP file, and none of it was touched by the contamination.

**Replaced:** the Patch A `LDUMPCSO` patch, `read_cproj.py`, per-configuration SOC dumps, `CPROJ_BAND_ORDER`, and EIGENVAL-based occupations. See §4.

**New:** the Patch B patch (three independent dump flags, one `PRE_LOOP` capture point, self-indexed CPROJ records, `FERWE.dat`); `dumpio.py`; the C0/W0/N0/P0 gates.

**Void:** every number produced by the Patch A trace path, including the −0.018/+0.014 meV $E_{\rm DM}$ estimates and the σ_restart = 1.5×10⁻⁵ eV noise floor. They were computed from contaminated projections and are not reference values.

### 0.3 What this document specifies

1. VASP-side work: the completed pinning campaigns (W0–W2), the Patch B dump architecture, and the k/q co-design rules (W5).
2. The configuration generator: `MAGMOM`/`M_CONSTR` construction, the two orthogonal frame conventions, INCAR deltas, λ ramp, chaining, realization gate.
3. The four-run protocol (`ref`, `dump_C`, `stage2`, `dump_P`) and the single-CSO economy.
4. The `dmi_pipeline` package layout and its gate inventory.
5. Stage 0 planner and the manifest.
6. The ordered test ladder T0–T9 with pass criteria, and the risk register.

**Assumptions.** VASP 6.4.2 GPU build with Patch B applied (build id pinned by C0; the toolchain must match the module set used at compile time — a mismatch produces `SEGV_ACCERR` at first GPU touch). PAW PBE+U as in the baseline. BiFeO₃ R3c, $N_m = 2$, $N_{\rm par} = 9$ within $R_{\max} = 6$ Å, insulating.

**Design philosophy, amended.** Every convention is determined empirically by a gate, never assumed. Rev 1 said this and still meant "gate the conventions." The amendment from the failure: **a gate must be able to fail for the reason you are testing.** W1b (below) was a correctly-executed test that could not discriminate the thing it was pinning, and the campaign paid for that in weeks. Every gate in §5.4 now carries an explicit statement of what would make it fire.

---

## 1. Architecture overview **[CHANGED]**

```
Stage 0   planner.py           orbits, Moriya projectors, design map, QR row
          (pure Python, sec)   selection, exclusions, parity pairs → manifest.json

Stage 1   materialize.py       one directory per configuration and per run type:
                               POSCAR, KPOINTS, INCAR, MAGMOM, M_CONSTR, job.sh

Stage 2   VASP (SOC-free)      LSPIRAL SCF; F1/F2 constrained (I_CONSTRAINED_M,
                               LAMBDA ramp, WAVECAR chaining); realization gate
                               (UNWOUND frame) → realized decorations into manifest

Stage 2b  VASP (dump_P)        SOC-FREE one-shot chained from Stage 2:
                               LDUMPCPROJ + LDUMPCOCC → CPROJ.*.bin, FERWE.dat, COCC.dat
                               captured at PRE_LOOP, before any orbital update

Material  VASP (ref, dump_C)   once per material: in-plane collinear SCF, then
                               LSORBIT dump → CSO_z.dat (+ CSO_x, CSO_y for T3 only)

Stage 4   dmi_pipeline         trace per configuration per axis → gates → two-trace
                               observable y = (T₊ − T₋)/N_m → design matrix from
                               REALIZED decorations → single SVD solve → d_b, covariance

Stage 5   validation ladder    λ-scan, ψ-independence, F0/F2 consistency,
                               qSO-on-F0, supercell anchor, TB2J comparison
```

Structural changes relative to Rev 1, one sentence each:

- **Stage 3 no longer exists as a per-configuration SOC run.** It splits into a material-level CSO dump (once, ever) and a per-configuration SOC-free projection dump chained from Stage 2.
- **The observable is a difference, not a trace.** $y = [\Delta E^{(1)}(q,\psi) - \Delta E^{(1)}(-q,-\psi)]/N_m$, per `new_direction.md`. Both members of every parity pair are measured; neither is solved from alone.
- **Occupations ship with the projections** (`FERWE.dat` from the same `PRE_LOOP` capture), not from a separately-matched EIGENVAL.
- **One acceptance gate (N0) precedes the campaign.** Nothing is materialized until the q = 0 null passes.

---

## 2. VASP-side work

### 2.1 W0 — constraint compatibility under LSPIRAL **[DONE]**

**Result: GREEN.** `I_CONSTRAINED_M = 1` composes with `LSPIRAL` on this build. The standalone probe suite (V0–V8) confirmed: the tag is recognized, the constraint holds and relaxes correctly, frames are self-consistent, the state is stationary to 0.044° at λ = 20, F2 is viable, and `LZEROZ` is compatible. The W3 longitudinal fallback patch is **not needed** and should not be built.

**Two corrections to Rev 1's W0 section, both earned the hard way:**

- Rev 1's no-op discriminator ("double λ and confirm `E_p` changes") is necessary but not sufficient. A silently *misspelled* tag (`I_CONSTRAINTED_M`) produces the identical signature to a dead constraint, because VASP ignores unknown tags without comment. **Every run must grep its own OUTCAR INCAR echo for the tags it wrote**; an absent echo is a failure, not a formatting quirk. This is now a hard check in `dmi finish`.
- `E_p → 10⁻⁹` does not mean "the constraint is satisfied as intended." It means VASP reached *its* target, which may not be yours. The state can sit 46.5° from the target you believe you wrote while `E_p` reports success — that is what happens when the target is written in the wrong frame. Always compare the realized unit vectors against `M_CONSTR` directly, per ion.

**Withdrawn:** Rev 1 and the interim notes implied F0 needs constraints. It does not. F0 spirals converge unconstrained, as originally derived; the apparent failure was the frame artifact in §2.2.

### 2.2 W1 — Frame pinning **[CHANGED — the Rev 1 test was invalid]**

There are **two independent frame conventions**, and Rev 1 conflated them into one family of `FRAME_*` switches. They are orthogonal and both must be applied:

| Convention | What it selects | Implemented in | Pinned value |
|---|---|---|---|
| **Spiral phase** | whether the per-site azimuth carries $2\pi\mathbf q\cdot\boldsymbol\tau_\mu$ | `frames.lab_to_unwound` | `FRAME_MAGMOM = "lab"`, `FRAME_MCONSTR = "unwound"`, `FRAME_MINT = "unwound"` |
| **Cone axis / SAXIS interpretation** | whether `MAGMOM`/`M_CONSTR` are given in the ẑ-cone frame (VASP rotates by SAXIS) or directly in lab Cartesian | `targets.to_frame` | `"internal_z_cone"` with SAXIS = ẑ everywhere in Stages 2/2b |

Writing a `frames`-vocabulary value into `targets.to_frame` (or vice versa) applies the wrong rotation. The generator must take **two** convention arguments, and the round-trip test is four-way: {lab, unwound} × {z-cone, n̂}.

**W1a — MAGMOM convention. [DONE]** Confirmed: `MAGMOM` is lab-frame input, carrying the intracell spiral phase explicitly.

**W1b — M_CONSTR frame. [INVALID AS SPECIFIED — replaced]** Rev 1 proposed a no-op constrained F0 run and read the frame off `E_p → 0`. **This test cannot discriminate the frames.** The lab and unwound frames differ by exactly $2\pi\mathbf q\cdot(\boldsymbol\tau_2 - \boldsymbol\tau_1)$; on a no-op constraint the target equals the realized state in *both* frames, so both pass. The constraint probe ran this test correctly, returned "lab," and was wrong — not through error but because the observable was degenerate.

**Replacement test:** use a **spiral-phase-dependent** configuration — a constrained F1 run at a q where $2\pi\mathbf q\cdot(\boldsymbol\tau_2-\boldsymbol\tau_1)\notin 2\pi\mathbb Z$ (q = ¼ works; q = 0 never will) — and compare `M_CONSTR` against the realized unit vectors **per ion**. The correct frame is the one whose per-ion residuals are uniformly small. The wrong frame leaves each ion off by precisely its own $2\pi\mathbf q\cdot\boldsymbol\tau_\mu$: the measured signature was 1.50° on ion 1 and 46.50° on ion 2, which is what identified the frame.

**W1c — M_int frame. [DONE, corrected]** `FRAME_MINT = "unwound"`: OUTCAR magnetization tables are written in the generalized-Bloch internal frame, in which a correct spiral reads as collinear. **This applies to the azimuth only.** The unwinding is a rotation about $\hat z$ by $2\pi\mathbf q\cdot\boldsymbol\tau_\mu$, so $|M|$ and the cone angle $\theta$ are frame-independent and must not be converted. Misreading this cost the project several weeks: the realized-state gate subtracted a spiral phase the data never contained, reported "collapse to collinear," and triggered an entire constraint campaign against a state that had been correct from the start.

**Deliverable:** five constants in `conventions.py` — `FRAME_MAGMOM`, `FRAME_MCONSTR`, `FRAME_MINT`, plus the cone-axis convention and `F1_USES_LZEROZ` — each annotated with the gate and the run that pinned it.

### 2.3 W2 — LZEROZ semantics and the family flag matrix **[OPEN for F1]**

`LZEROZ = .TRUE.` zeroes the axis component of the magnetization each iteration; it is the enforcer of $\theta = \pi/2$, which is why F0 needs no cone constraint. For F2 it would annihilate the frozen sublattice and must be `.FALSE.`

`F1_USES_LZEROZ` is **still `UNDETERMINED`**. The probe's V8 addressed compatibility, not the F1 policy question. Resolve before F1 production: one constrained F1 run each way, compare realized $\theta$ uniformity and convergence behaviour. Until then `materialize` must refuse to write F1 directories rather than guess.

Family flag matrix:

| Flag | F0 | F1 | F2 |
|---|---|---|---|
| `LSPIRAL` / `QSPIRAL` | on | on | on |
| `LZEROZ` | `.TRUE.` | **[OPEN]** | `.FALSE.` |
| `I_CONSTRAINED_M` | **off** | `1` | `1` |
| `LAMBDA` | — | ramped | ramped |
| `M_CONSTR` | — | all sites, flat, ψ-decorated | frozen ∥ n̂; winding at cone θ |
| `LSORBIT` | `.FALSE.` | `.FALSE.` | `.FALSE.` |
| `SAXIS` | `0 0 1` | `0 0 1` | `0 0 1` |
| `ISYM` | −1 | −1 | −1 |

`LSORBIT` is `.FALSE.` in **every** configuration run. It appears only in `dump_C`. `LSPIRAL` and `LSORBIT` never coexist in one INCAR — an invariant the tag whitelist enforces at write time.

### 2.4 W3 — longitudinal-only constraint patch **[CANCELLED]**

W0 returned GREEN, so the fallback is unnecessary. Rev 1 §2.4's Fortran sketch is retained only in the risk register as a contingency if F1 convergence later proves intractable.

### 2.5 W4 — dump conveniences **[SUPERSEDED by Patch B]**

- **W4a (machine-readable `M_int`)**: not implemented; OUTCAR parsing is used, behind `read_realized(rundir)`. Acceptable — but the parser must apply `FRAME_MINT` and must never be bypassed by hand-reading a table. Hand-reading OUTCAR magnetization blocks produced repeated false diagnoses (a gauge-free 51° global rotation mistaken for state error); all readback goes through the gated path.
- **W4b (dump provenance header)**: **[DONE]**, and expanded well past the original scope. Every Patch B file carries format version, build id, dump point, dimensions, and an echo of `LSORBIT`/`LSPIRAL`/`QSPIRAL`/`SAXIS`/`NELECT`. Readers assert against these; the "which dump is this" class of error is closed by construction.

### 2.6 W5 — k/q co-design and exclusions **[CHANGED]**

- **Γ-centered k-mesh**, identical across the campaign, with every selected q commensurate with it.
- **Hard exclusions from the live pool:** $\mathbf q \in \{\mathbf G\}$ (including $\mathbf q = 0$); $|\mathbf q| < q_{\min}$ (half the smallest k-mesh increment).

  *Rev 1 justified the q ∈ G exclusion by "the spin-flip selection rule fails there." That rationale is obsolete* — the spin-flip blocks are excluded from the trace entirely (§4.3), so no selection rule is being relied upon. The correct reason is simpler and stronger: at $\mathbf q \in \mathbf G$ the configuration has no chirality, so there is no DM signal to measure.
- **q = 0 is now a required diagnostic configuration, not merely an exclusion. [NEW]** Precisely because the trace must vanish there by symmetry, q = 0 is the campaign's acceptance gate (N0, §5.4). The planner must always emit it.
- **TRIM handling:** a TRIM point with ψ = 0 is self-paired; under the two-trace observable it yields $y \equiv 0$ by construction and cannot be a live row. Keep TRIM points out of the live pool entirely.
- **BZ-reduction assertion:** rows at $\mathbf q$ and $\mathbf q + \mathbf G$ are identical; if pivoted QR selects both, the reduction code is buggy.

---

## 3. Configuration generator (Stages 1–2)

### 3.1 MAGMOM and M_CONSTR construction **[CHANGED — two frame adapters]**

Single source: `spin_targets(structure, q, psi, family, theta, n_hat, eps, M_mag)` returns per-atom Cartesian target spins. The formula is the derivation's Eq. (3):

```
alpha_i = 2π q̃·τ̃_i + phi_ref(a_i) + psi·delta(a_i,2)
S_i     = ( s_a cos(alpha_i),  s_a sin(alpha_i),  eps_a c_a )
```

with $(s_a, c_a) = (1, 0)$ for F0/F1, and $(\sin\theta, \cos\theta)$ / $(0,1)$ on the winding / frozen sublattices for F2.

**Then two adapters, in this order:**

```
MAGMOM_i   = M_mag(a_i) · cone_adapt( S_i )                      # spiral phase KEPT (lab)
M_CONSTR_i = cone_adapt( unwind( S_i ) )                         # spiral phase REMOVED
```

where `unwind` drops the $2\pi\mathbf q\cdot\boldsymbol\tau_\mu$ term (azimuth only) and `cone_adapt` is the identity while SAXIS = ẑ. Mode 2 writes moment-scaled vectors instead of unit directions.

Sublattice labels are fixed by POSCAR order (Pin 3); the generator asserts the ε assignment against the recorded reference and refuses on mismatch, since a silent relabeling flips the sign of every ψ. `RWIGS` is mandatory whenever `M_CONSTR` is present.

**Round-trip assertion (mandatory, runs at write time):** generate a seed at ψ = 0, convert to each of the four frame combinations, invert each back, and require ψ = 0 to 10⁻⁹ in all four. This is the check that would have caught the frame error in one second rather than one month.

### 3.2 INCAR deltas **[CHANGED]**

Four templates, one base. The base contains `LNONCOLLINEAR`, `ISYM = -1`, `SAXIS = 0 0 1`, ENCUT, EDIFF, +U, mixer settings, and **must not** contain `LSORBIT` or `LSPIRAL` — those are set only by deltas. Tag names are validated against a hardcoded whitelist before writing (this is the `I_CONSTRAINTED_M` guard).

| Directory | Delta |
|---|---|
| `material/ref` | `LSORBIT=.F. ISTART=0 ICHARG=2` + in-plane collinear G-type MAGMOM, `EDIFF=1e-7` |
| `material/dump_C` | `LSORBIT=.T. ISTART=1 ICHARG=11 ALGO=Normal NELM=1 LDUMPCSO=.T. LWAVE=.F. LCHARG=.F.` |
| `configs/<id>/stage2` | `LSORBIT=.F. LSPIRAL=.T. QSPIRAL=<q> ISTART=1 ICHARG=0` + MAGMOM (+ constraint block for F1/F2) |
| `configs/<id>/dump_P` | as its stage2, plus `ISTART=1 ICHARG=11 ALGO=Normal NELM=1 LDUMPCPROJ=.T. LDUMPCOCC=.T. LWAVE=.F. LCHARG=.F.` |

**Note on `ALGO`.** Rev 1 and the Patch B spec both suggested `ALGO = None` for dump runs. In practice `ALGO = None` suppresses code paths the patch depends on and interacts badly with the GPU build. Use `ALGO = Normal, NELM = 1`: the dump fires at `PRE_LOOP`, before that single step does anything, so the captured state is identical and the run terminates cleanly. `LDUMPONLY` is likewise **not** used until its clean-stop path is fixed (it currently calls into VASP's finalization, which tries to close an XML tag the electronic loop never opened).

The in-plane reference matters physically: the N0 null relies on a spin-only $C_{2x}$ rotation about the common moment axis, which exists only for moments in the plane perpendicular to the SOC quantization axis. A ẑ-collinear reference gives no constraint at all. Since Stage 2 is SOC-free, ẑ- and x̂-collinear states are exactly degenerate, so this costs nothing — and in R3c BFO the Fe moments physically lie in the basal plane anyway.

### 3.3 λ ramp and WAVECAR chaining

Unchanged from Rev 1: chain from the nearest converged neighbor in q; ramp λ geometrically {1, 3, 10, 30} restarting each step, stopping at the **smallest** λ that passes the realization gate. Larger λ is not safer — it stiffens the penalty field that perturbs the density (T5 quantifies this). Record terminal λ per configuration. F0 runs unconstrained and chains normally.

### 3.4 The realization gate (Pin 5) **[CHANGED — frame]**

After each Stage-2 convergence, `read_realized(rundir)` parses the final OUTCAR moments **in the unwound frame** and compares against the target:

```
|Δψ_2 − Δψ_1| < tol_phi   (1°)      ← gauge-invariant; the global phase is reported and ignored
|Δtheta_a|    < tol_theta (1°)      ← frame-free, no conversion
||M_i| − M_ref|/M_ref < tol_M (5%)  ← frame-free
alpha_residual_rms < tol_phi        ← family-membership (uniformity) assertion
E_p present and < 1e-3 eV           ← constrained rows only
PASS → realized decorations into manifest; Stage 4 builds the row from them
FAIL → next λ; ramp exhausted → ACCEPTED if still a valid decorated spiral, else DEAD
```

The uniformity assertion remains the important subtlety: Pin 5 licenses substituting the *realized* decoration for the *target* only if the realized state is still in the family (one ψ and one θ per sublattice). A state with site-scattered phases is not a decorated spiral and must be discarded, not corrected.

Terminal `E_p` is recorded as an early-warning diagnostic, with the §2.1 caveat: a small `E_p` proves VASP hit its own target, not yours. The per-ion `M_CONSTR`-vs-realized comparison is what proves the target was right.

---

## 4. The dump protocol **[REWRITTEN]**

### 4.1 Why the protocol changed

The force theorem evaluates $\Delta E^{(1)} = \sum_{nk} f^{(0)}_{nk} w_k \langle\psi^{(0)}|H_{\rm SO}|\psi^{(0)}\rangle$ on the **frozen SOC-free** eigenstates. Patch A dumped projections from a SOC run whose single electronic step began with a subspace rotation in the full Hamiltonian. Occupied–occupied mixing is harmless (the trace depends only on the occupied-subspace projector), but occupied–unoccupied mixing enters at $O(\xi/\Delta)$ — with $\xi_{\rm Bi} \approx 2.1$ eV against eV-scale gaps, that is not small. Patch A's stated invariant ("the dump is consistent with OUTCAR's final SOC energy") was the wrong invariant; the right one is "the dump is consistent with the *input* orbitals."

### 4.2 The four runs

**`material/ref` — once per material.** In-plane collinear SOC-free SCF. Produces the CHGCAR/WAVECAR that `dump_C` reads and that the first configuration of each family chains from. Converge tightly.

**`material/dump_C` — once per material.** The only run in the campaign with `LSORBIT = .TRUE.` Produces `CSO_z.dat`. CSO depends only on the converged potential, never on the orbitals, so the contamination mechanism does not apply and the SOC-free density's potential is exactly what the force theorem wants. Measured configuration-independence: 1.2×10⁻⁹ between ±q runs.

*Patch note:* the CSO buffer is populated by `CALC_SPINORB_MATRIX_ELEMENTS` inside the electronic loop, not during setup, so the CSO flush must happen at the in-loop `SET_DD_PAW` call (Patch A behaviour) rather than at `PRE_LOOP`. The empty-buffer abort moves to program exit.

**`configs/<id>/stage2` — per configuration.** The SOC-free spiral SCF described in §3. Unchanged in physics from Rev 1.

**`configs/<id>/dump_P` — per configuration.** A one-shot chained from its own Stage 2, SOC-free, capturing `CPROJ.*.bin`, `FERWE.dat`, `COCC.dat` at `PRE_LOOP` — after `PROALL` has formed the projections, before any eigensolver or charge update touches them. Because the orbitals are read from a converged SOC-free WAVECAR and nothing rotates them, the frozen-state premise holds **by construction** rather than by assumption.

### 4.3 What the trace uses, and what it does not

The contraction uses the **spin-diagonal blocks only**:

$$\Delta E^{(1)} = \sum_k w_k \sum_n f_{kn} \sum_\mu \left[ c_\uparrow^\dagger C^\mu_{uu} c_\uparrow + c_\downarrow^\dagger C^\mu_{dd} c_\downarrow \right]$$

The spin-flip blocks are excluded, and this is settled rather than conventional: in a single-cell evaluation they carry one term of the lattice sum $\sum_R e^{i\mathbf q\cdot\mathbf R}$ with a spurious site phase, and the origin-shift test confirmed it empirically — the all-blocks value moved from 4.506 to 4.019 eV under a pure coordinate-origin translation, while the diagonal-only value was invariant to all digits. A physical energy cannot depend on where you put the origin.

**But the flip blocks must be present in the dump and must be nonzero.** Two reasons. Physically, $\xi\boldsymbol\sigma\cdot\mathbf L = \xi[\sigma_z\ell_z + \tfrac12(\sigma_+\ell_-+\sigma_-\ell_+)]$, and the second term lives entirely there; Patch A measured them contributing ~4.2 eV, concentrated on Bi. Operationally, §4.4's offline axis rotation **requires** them: rotating the quantization axis mixes diagonal and flip blocks, so $C(\hat x)$'s diagonal blocks are built partly from $C(\hat z)$'s flip blocks. A dump with zero flip blocks could not be rotated at all.

Any gate that asserts the flip blocks vanish is therefore wrong on both counts and must not be written.

### 4.4 Single-axis CSO with offline SAXIS rotation (T3) **[RETAINED — and it is the axis mechanism]**

The radial integrals $\bar\xi$ are axis-independent; SAXIS enters only through the spin rotation $U$. Since the dump contains all four spin blocks, the axis rotation is a pure spin-space conjugation done offline:

$$C(\hat n)^{ss'} = \sum_{tt'} U^\dagger(\hat n)_{st}\, C(\hat z)^{tt'}\, U(\hat n)_{t's'}$$

with $U$ built from SAXIS via VASP's EULER call, **up to sign and ordering conventions pinned by T3, not assumed**. T3 compares the offline-rotated ẑ dump against genuine x̂ and ŷ dumps for one configuration; agreement to machine precision on every block, ion, and $(i,j)$ validates the module. If it fails, enumerate the eight candidates (α sign, β sign, $U$ vs $U^\dagger$) — one matches exactly or the module is wrong. The real-harmonics transformation is axis-independent and commutes with the spin conjugation, so it cancels.

**This is the mechanism by which a measurement selects which component of $\mathbf d$ it probes**, and there is no alternative: `LZEROZ` pins the spin plane to $xy$, so the spiral's rotation axis cannot be reoriented by rotating the spins. Rotating the operator is also far cheaper — three axes come free from one `dump_P`, whereas rotating the configuration would need three Stage-2 SCFs per $(q,\psi)$.

Consequences for the code: `targets.to_frame`'s $\hat n$ argument is the **SAXIS-interpretation adapter** (W1c), *not* the design-matrix axis; with SAXIS = ẑ everywhere it is the identity. Applying both it and the CSO rotation as if they were the same thing would double-rotate. And `dumpio.load_cso` must accept `SAXIS ≠ z` headers for the two T3 validation dumps, while production reads only `CSO_z.dat`.

### 4.5 Occupations **[CHANGED — the Rev 1 rule is inverted]**

Rev 1 required occupations from each row's own Stage-2 EIGENVAL and explicitly forbade "the FERWE weights in the CPROJ binaries." That prohibition was correct for Patch A, where the CPROJ binaries came from a SOC run and carried SOC-perturbed occupations.

Under Patch B it inverts: `FERWE.dat` is written at the same `PRE_LOOP` capture, from the same SOC-free state as the projections, so it is the **primary and preferred** source. It eliminates the cross-file k-ordering assumption entirely. EIGENVAL is retained only as an optional cross-check that warns on mismatch.

The underlying rule is unchanged and still strict: the frozen $f^{(0)}$ for a row comes from that row's own SOC-free state, never from a partner. Checks at load: $\sum_k w_k = 1$, $\sum_{kn} w_k f_{kn} = N_{\rm elect}$, every $f \in \{0,1\}$ (a fractional occupation is an error for this insulator, not a warning).

The free consistency check for parity partners survives: their SOC-free spectra must agree to SCF tolerance, being antiunitarily related.

---

## 5. The `dmi_pipeline` package

### 5.1 Layout **[CHANGED]**

```
dmi_pipeline/
├── conventions.py     # FRAME_* (two families!), (uu_idx, dd_idx) (M0), EULER (T3),
│                      #   VASP_BUILD_ID (C0), tolerances — each annotated with its gate
├── orbits.py          # FROZEN  bonds, orbits, Moriya projectors, propagation
├── model.py           # FROZEN  row descriptor, per-bond primitives
├── design.py          # FROZEN  paired design row from REALIZED decorations
├── planner.py         # FROZEN  Stage 0: selection, exclusions, parity pairs
├── solve.py           # FROZEN  stacked SVD, rank assertion, covariance, TB2J
├── targets.py         # spin_targets(); MAGMOM/M_CONSTR writers — TWO frame adapters
├── frames.py          # spiral-phase adapters (lab ↔ unwound)
├── materialize.py     # Stage 1: four INCAR templates, tag whitelist, DONE-gating
├── execution.py       # job scripts, chain order, submission
├── realized.py        # OUTCAR readback (unwound), realization gate, writeback
├── dumpio.py          # NEW  Patch B readers; W0 index-completeness is its contract
├── cso.py             # rotate_saxis() (T3) — reader consolidated into dumpio
├── trace.py           # compute_delta_E1 (vectorized) + reference loop version
├── observables.py     # two-trace observable, paired noise
├── gates.py           # W0, C0, M1, N0, P0, I0, R0 + fit diagnostics
└── manifest.py        # schema v2, validation, single source of truth
```

**Deleted:** `cproj.py` (Patch A reader), `ta_td.py`, `single_trace.py`, `ta_td_extract.py`, `noisefloor.py`, `CPROJ_BAND_ORDER`. The T-A/T-D *documentation* is kept — it records why the two-trace method exists — but the code is retired.

### 5.2 The core, and what is no longer untouched **[CHANGED]**

Rev 1 claimed `compute_delta_E1` would not be edited. Two changes are unavoidable:

1. **Signature.** It now takes `(cproj, ferwe, cso)` from the Patch B readers. No `eigenval_path`, no `cproj_order`, no `cso_source` callable — the three arguments that generated the most confusion are gone.
2. **Vectorization.** On real data the contraction is 512 k-points × 152 bands × 10 ions × 2 blocks × LMDIM², i.e. 10⁸–10⁹ inner operations. A literal Python loop is minutes to hours per trace, and M1's COCC rebuild is the same magnitude. Vectorize with `einsum`; keep the loop as `compute_delta_E1_reference` and assert equivalence on a small case. The density-matrix oracle in `test_trace.py` is the guard.

The *mathematics* is unchanged, and the derivation's §9.1 licence still holds: the trace depends only on the gBT spinor structure and the block selection, both decoration-blind.

### 5.3 New numerics worth flagging

- **`orbits.py`** is imported identically by planner and solver, so the design map that promised rank 9 is definitionally the map that gets inverted.
- **`design.py`** implements the paired row $[A(c_+) - A(c_-)]/N_m$ with three strict rules: all inputs are **realized** decorations (Pin 5); F2 rows carry the realized $\sin^2\theta$ weight read back per sublattice; axes never get independent solves (one stacked matrix, one solve).
- **`solve.py`**: assert rank $= N_{\rm par}$ with a stated singular-value floor; weights $1/\sigma_y^2$; report the worst-determined direction **by name** — "d_A − d_B on the NN inter orbit, ẑ component" is actionable, a condition number is not.
- **`trace.py`**: record per-ion and per-k decompositions alongside the total. They cost nothing and were the diagnostics that localized the contamination to Bi.

### 5.4 Gate inventory (final) **[CHANGED]**

| Gate | Tests | What makes it fire | When |
|---|---|---|---|
| **C0** | CSO structure: $C_{dd} = -C_{uu}$ elementwise; $C_{uu}$ purely imaginary, antisymmetric, zero diagonal; $C_{ud} = C_{du}^\dagger$; magnitudes ordered Bi > Fe > O | a missing $\sigma_z$ sign (which would make the trace a spin-independent $\sum\langle\xi\ell_z\rangle$ — even by construction and Bi-dominated) | once per build |
| **W0** | CPROJ index completeness: every (k, band) present exactly once; headers agree | a lost rank file, a duplicated record, a changed parallel layout | every dump load (it is the loader's contract) |
| **M1** | COCC rebuilt from CPROJ + FERWE matches `COCC.dat` at 1e-10 | a writer/reader indexing bug. Both sides now come from the same `PRE_LOOP` capture, so any failure is a code bug, never physics | every configuration |
| **N0** | q = 0 trace $\approx 0$ | SOC-contaminated projections. For an in-plane collinear state, spin-only $C_{2x}$ maps $\sigma_z\ell_z \to -\sigma_z\ell_z$ while leaving the occupied projector invariant, so the trace vanishes identically. **Zero free parameters; no parity partner needed.** | **before the campaign; blocks everything** |
| **I0** | $\text{Im}\,\Delta E^{(1)} < 10^{-6}$ eV | block-map or Hermiticity errors | every trace |
| **P0** | $\Delta E^{(1)}(q,\psi) + \Delta E^{(1)}(-q,-\psi)$ at the noise floor | residual even background; a ratio near 2 is the original failure signature and must be reported by name | every parity pair |
| **T3** | offline-rotated CSO vs genuine x̂/ŷ dumps | wrong Euler convention | once per build |
| **R0** | realized ψ, θ, moment, uniformity, $E_p$ (unwound frame) | a state that left its family | every Stage-2 run |
| **λ-scan** | extracted row flat in λ | penalty field perturbing $\mathbf d$ at first order | T5, once |
| **ψ-independence** | fitted $d_A - d_B$ flat in ψ | model validity across F1 | T6, once |
| **F0/F2 consistency** | $D_{\rm intra}[R]$ vs $d^{\rm Fe1} + d^{\rm Fe2}$ | cross-family transferability | free, from production rows |
| **Rank / κ** | design-matrix health | — | every solve |

**M0** is demoted to build-validation only: it needs CSO and COCC of the *same SOC state*, which Patch B produces only under a debug flag. It is no longer a campaign gate.

**N0 threshold.** The expected $E_{\rm DM}$ is 1–2×10⁻⁴ eV, so the null threshold must sit *below* the signal, not above it: `N0_TOL = max(5e-5, 3σ_restart)` on the total and per ion, with the Bi contribution reported separately. Earlier drafts proposed 5×10⁻⁴ and 1×10⁻⁴; both would permit a contamination larger than the entire signal to pass.

---

## 6. Stage-0 planner and the manifest

### 6.1 Planner algorithm **[CHANGED — pairs, and the mandatory null]**

```
inputs:  POSCAR, {ε_a}, R_max, k-mesh, knob ranges, κ_max, oversampling
1. orbits.py → N_par, orbit data;  assert N_par == 9 for R3c BFO @ 6 Å
2. candidate pool: commensurate q × ψ × fam × axis, minus exclusions (§2.6)
3. design map over the pool; assert achievable rank == N_par BEFORE any DFT
4. column-pivoted QR on Mᵀ → rows to oversampling × N_par under κ < κ_max, with
   two deliberate biases QR would not choose:
     – cross-family overlap at shared q (transferability needs redundancy)
     – small-|q| F1 rows (the d_A−d_B channel rides cos(q·r), maximal there)
5. every selected row becomes a PAIR: (q,ψ) and (−q,−ψ), both measured        [NEW]
6. emit the mandatory q=0 N0 configuration                                    [NEW]
7. emit restart replicates (role="noise") for the noise model                 [NEW]
8. predicted per-parameter σ from (MᵀWM)⁻¹ — the go/no-go table before any DFT
9. emit manifest.json + campaign report
```

Steps 5–7 are new. Step 7 matters because σ_restart must be **re-measured on Patch B** — the Patch A value is void, and TRIM/parity-based noise estimators were invalid while the even background existed. Without planner-emitted replicates, `form-pairs` has no σ source and stalls.

### 6.2 Manifest schema **[CHANGED — v2 + provenance]**

```json
{ "meta": { "build_hash", "vasp_build_id",
            "conventions": { "frames_spiral", "frames_cone", "blocks", "euler",
                             "eps_assignment", "dump_format_version" },
            "kmesh", "Rmax", "kappa_max", "noise_model" },
  "material": { "ref", "dump_C", "cso_provenance": { "gates": {"C0","T3"}, "sha256" } },
  "configs": [ { "id", "family", "q_frac", "psi_target", "theta_target",
                 "dirs": { "stage2", "dump_P" }, "chain_from",
                 "status": { "stage2", "dump_P" },
                 "dump_provenance": { "build_id", "header", "files": {"sha256"} },
                 "realized": { "psi", "theta_per_sublattice", "alpha_rms_err",
                               "E_p", "lambda_final", "gate" },
                 "traces": [ { "axis", "delta_E1", "im_max", "per_ion" } ],
                 "gates": { "R0", "W0", "M1", "I0" } } ],
  "measurements": [ { "id", "plus_id", "minus_id", "pair_gate",
                      "rows": [ { "axis", "y", "sigma_y", "design_row" } ],
                      "gates": { "P0" } } ],
  "solution": { "x", "cov", "rank", "kappa", "sv", "per_bond_d", "tb2j" } }
```

Stages read and append to this file and nothing else. Every "which convention was that" question has its answer recorded next to the number it produced — and now every "which binary, which dump, which bytes" question does too.

---

## 7. The test ladder **[CHANGED — N0 is the new first rung]**

| # | Test | Cost | Pass criterion | On fail |
|---|---|---|---|---|
| T0 | W0 constraint probe | — | **DONE: GREEN** | — |
| T1 | W1 frame pinning, spiral-phase-dependent | — | **DONE**, with `FRAME_MINT = "unwound"`; W1b replaced (§2.2) | — |
| **T2a** | **C0 on `CSO_z.dat`** | free | structure + $C_{dd}=-C_{uu}$ + flip blocks nonzero and Hermitian | wrong dump or wrong block map; do not proceed |
| **T2b** | **W0 + M1 on the first `dump_P`** | free | index completeness; COCC rebuild at 1e-10 | reader or writer bug |
| **T2c** | **N0 — q = 0 null** | 1 SCF + 1 dump | $\|\Delta E^{(1)}\| < \max(5\times10^{-5}, 3\sigma)$, total and per ion | **the frozen-state premise is still violated.** Report the per-ion breakdown; the distribution across Bi/Fe/O discriminates the remaining hypotheses. **Blocks the entire campaign.** |
| T3 | Offline CSO rotation vs genuine x̂/ŷ dumps | 2 extra dumps | machine-precision match, all blocks, all ions | pin among the 8 Euler candidates; fall back to 3 CSO dumps per material (cheap — they are material-level) |
| **T2d** | **P0 on one ±q pair** | 2 SCF + 2 dumps | $\|T_+ + T_-\|$ at the noise floor; each $\|T_\pm\| \sim 10^{-4}$ eV | ratio ≈ 2 means residual even background — return to N0 |
| T4 | F2 spot-check: I0 + per-ion decomposition | 1 SCF + dump | gates at baseline levels | wrong-block contamination hunt before F2 production |
| T5 | λ-scan (one F1, 3 λ) | 3 SCF | row value flat in λ within noise | reduce λ; if never flat, penalty is first-order — escalate |
| T6 | ψ-independence (one q; ψ = 30°, 60°, 90°) | 3 SCF | fitted $d_A - d_B$ flat in ψ | model-validity failure; decide via realization data |
| T7 | F0/F2 consistency | free | agreement within propagated σ | transferability failure |
| T8 | Two-trace stability across replicated pairs | repeated paired runs | $y$ restart-reproducible within paired uncertainty; common mode recorded and stable | investigate pair realization; replace the pair — never solve from one side |
| T9 | External anchors: qSO on F0; supercell; TB2J | heavy, end | consistent within the Approximation-2 budget | physics discussion, not pipeline debugging |

T2a–T2d are the new plumbing ladder and cost **four SCFs and five dumps total**. They exist because the Rev 1 ladder had no rung that could detect contaminated projections — T2 as written ("M0 + M1 unchanged from baseline") passed throughout the failure, since both gates validate file handling rather than physics.

---

## 8. Risk register **[CHANGED]**

| Risk | Likelihood | Blast radius | Mitigation / fallback |
|---|---|---|---|
| **Projections not frozen SOC-free eigenstates** | **realized once; diagnosed** | every trace | `PRE_LOOP` capture in a SOC-free run makes it structural; **N0 detects it in one run** |
| Toolchain mismatch between build and runtime | moderate (bitten once) | everything | pin `module list` at build time into the repo; use the same set in every job script |
| `I_CONSTRAINED_M` dead under `LSPIRAL` | **resolved GREEN** | — | W3 cancelled |
| Frame convention mis-pinned | **realized once** | silent sign errors in every ψ | four-way round-trip assertion at write time; never hand-read OUTCAR |
| Silent VASP tag failure (typo, unknown tag) | **realized once** | a wasted cycle each time | tag whitelist at write; OUTCAR echo check in `dmi finish` |
| F1/F2 parity partners realize asymmetrically | moderate | common-mode contamination survives the difference | build the row from both realized states; pair-realization tolerances; monitor paired restarts |
| Penalty field perturbs d at first order | low | T5 fails | smaller λ + tighter chaining; λ→0 extrapolation |
| Converged F1/F2 leaves the family | moderate at large ψ, θ | rows invalid | R0 uniformity assertion; shrink ψ/θ (rank 9 is achievable at ψ = 30°, θ = 30°) |
| Transferability fails (T7) | low for insulating BFO | single-solve premise | per-family solves + cross-family reporting; interesting rather than fatal |
| CSO rotation unresolvable (T3) | very low | axis economy only | three CSO dumps per material — material-level, so nearly free |
| N0 fails after the rewrite | **unknown until measured** | the method itself | fall back to Sandratskii qSO: masked-SOC self-consistent total-energy differences, evaluated in the physical frame, never unwound. Costs the first-order economy and re-opens the noise floor, but the planner, orbits, design map, and solver all survive unchanged |

**Every fallback path still terminates in a publishable result.** The worst realistic case is now the last row, and even there the multi-sublattice no-go theorem, the decorated-spiral construction, the rank-9 result, and the design/solve machinery are independent of how $E_{\rm DM}$ is measured.

---

## 9. Cost recap **[CHANGED]**

Per material: 1 reference SCF + 1 CSO dump (+2 dumps for T3, once). Per configuration: 1 Stage-2 SCF (1.5–3× baseline when constrained, less with chaining) + 1 `dump_P` one-shot (negligible — it does no electronic work). With the two-trace observable, every live row is a pair, so a campaign of ~16 measurements is ~32 Stage-2 SCFs plus the q = 0 null and a few restart replicates.

Total ≈ 40–70 baseline-SCF units, embarrassingly parallel across configurations. The per-configuration SOC dump that Rev 1 budgeted is **gone entirely** — and with it the `LSORBIT` + `LSPIRAL` incompatibility, the three-CSO bookkeeping, and the contamination channel.

---

## 10. Build order **[CHANGED]**

Patch B fixes (CSO flush point, COCC trace check) → `dumpio.py` + fixtures → **T2a (C0)** → `dmi finish` + DONE markers → **T2b (W0/M1)** → vectorize the trace → **T2c (N0) — stop here if it fails** → T3 → **T2d (P0)** → fix the two frame families in `targets.py` and delete the monkeypatch fixtures → pin `F1_USES_LZEROZ` (W2) → `materialize` with the four templates and the tag whitelist → planner pairs + null + replicates → production Stage 2 with chaining → T4–T8 interleaved with production → solve → T9 anchors → write the validation section directly from the manifest.

The single most important property of this order: **nothing downstream of T2c is built until the q = 0 null passes.** The previous ladder's first physics-sensitive rung was T5, by which point the entire pipeline had been written against a measurement that did not work.
