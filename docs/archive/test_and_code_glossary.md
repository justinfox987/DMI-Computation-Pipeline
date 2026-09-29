# Glossary: tests, gates, codes and acronyms

Current production rerun: [CP0–CP9 protocol](constraint_probe_v2_protocol.md).
Final execution/initialization decisions: [next_steps.md](next_steps.md).
Historical V-suite and frame status entries below do not certify the new binary.

Reference for the codes used in `decorated_spiral_implementation_rev2.md`
("Rev 2"), `full_test_data_requirements.md` ("REQ"),
`perlmutter_test_runner_spec.md` ("RUN") and
`full_test_preflight_confirmations.md` ("PRE").

Definitions follow Rev 2 unless noted. Status entries reflect what is recorded
in project history as of September 2026; they are not a substitute for the run
records.

---

## 0. Name collisions (read first)

Several labels have been reused for different things. When a document says
one of these, check which meaning applies.

| Label | Meaning 1 | Meaning 2 | Recommendation |
|---|---|---|---|
| **W0** | Rev 2 §2.1 work item: *constraint compatibility under `LSPIRAL`* (validated by the V-suite, ladder rung T0) | Rev 2 §5.4 gate: *CPROJ index completeness* (the `dumpio` loader contract) | Reserve **W0** for the loader gate, as REQ and RUN do. Call the constraint question **T0** or "the V-suite". PRE §A1 uses W0 in the constraint sense. |
| **Patch B** | July 2026: a proposed patch for Sandratskii's qSO masked-SOC method | September 2026: the current dump architecture (three flags, `PRE_LOOP`, self-indexed CPROJ, `FERWE.dat`) | "Patch B" now means the September dump patch only. |
| **T0–T13** | July 2026: agent *task* IDs for the old `dmi.py` build (e.g. "T4 implementation") | Rev 1/Rev 2 *validation ladder* rungs T0–T9 | Only the ladder meaning is current. |
| **T2** | Rev 1 ladder: "M0 + M1 re-run on patched build" | Rev 2 ladder: split into T2a–T2d | Use the Rev 2 split. Rev 1's T2 could not detect contamination. |
| **T4** | Rev 1: F2 spot-check with origin-shift + Im gates | Rev 2: F2 spot-check with I0 + per-ion decomposition | Rev 2 meaning. |
| **T8** | Rev 1: parity + null checks across the production set | Rev 2 / REQ §4: two-trace stability across replicated pairs (restart noise) | Rev 2 meaning. |
| **P0 vs Pin** | **P0**: the parity gate | **Pin 1–5**: numbered conventions from the derivation (§7 below) | Unrelated. |
| **A1–E3** | PRE checklist item IDs | — | Not tests. They only label confirmation tasks. |
| **Set A, B, …** | RUN submission sets | PRE sections A–E | Unrelated; context tells which. |
| **Stage 3** | Rev 1: per-configuration SOC dump run | — | **Retired.** Replaced by `dump_C` (material-level) + `dump_P` (per configuration). |

---

## 1. Data and acceptance gates

These run on real VASP output. Each has an explicit condition that makes it
fire (Rev 2 §5.4).

| Gate | Tests | Fires on | When | Pass criterion |
|---|---|---|---|---|
| **C0** | Structure of `CSO.dat`: C_dd = −C_uu elementwise; C_uu purely imaginary, antisymmetric, zero diagonal; C_ud = C_du†; flip blocks nonzero and Hermitian; magnitudes Bi > Fe > O | Missing σ_z sign; wrong block map; wrong dump | Once per build (per CSO dump) | Exact structure, to numerical precision |
| **W0** (gate) | CPROJ index completeness: every (k, band) present exactly once; headers agree | Lost rank file, duplicate record, changed parallel layout | Every `dump_P` load (built into `dumpio`) | No gaps or duplicates |
| **M1** | COCC rebuilt from CPROJ + FERWE equals `COCC.dat` | Reader/writer indexing bug (both come from the same `PRE_LOOP` capture, so failure is never physics) | Every configuration | < 1e-10 |
| **M0** | Contraction CSO × COCC reproduces VASP's per-site SOC energy | Contraction or ordering error | **Demoted**: build validation only (needs same-state CSO and COCC, available only under a debug flag) | 1e-6 eV |
| **I0** | Imaginary part of ΔE⁽¹⁾ | Block-map or Hermiticity errors | Every trace | Im ΔE⁽¹⁾ < 1e-6 eV |
| **R0** | Realized state (Pin 5) vs target, read in the unwound frame: Δψ, θ per sublattice, \|M\|, phase uniformity, E_p | A state that left its family, or a wrong target | Every Stage-2 SCF (each λ step) | \|Δψ\| < 1°, \|Δθ\| < 1°, \|M\| within 5% of M_ref, α_rms < 1°, E_p present and < 1e-3 eV (constrained runs) |
| **N0** | Trace of the q = 0, in-plane collinear state vanishes (spin-only C₂ₓ forces it exactly) | SOC-contaminated projections (Patch A gave 0.69 eV) | Once, before the campaign; blocks everything | Rev 2: \|ΔE⁽¹⁾\| < max(5e-5, 3σ) eV, total and per ion, Bi reported separately. Earlier drafts used 5e-4 and 1e-4; check which value was applied. |
| **P0** | ΔE⁽¹⁾(q,ψ) + ΔE⁽¹⁾(−q,−ψ) at the noise floor | Residual even background; a ratio near 2 is the original failure signature | Every parity pair | Within the measured paired noise |

**Status.** REQ states that C0, W0, M1, R0, I0 and N0 evidence exists. C0
passed on the first Patch B `CSO.dat`. P0 has not yet run on Patch B data; the
q1/F0 pair in RUN Set A is its first nonzero-q instance.

---

## 2. Validation ladder T0–T9 (Rev 2 §7)

Strict order; each rung gates the next.

| Rung | Name | What it checks | Cost | Pass | Where it lives now | Status |
|---|---|---|---|---|---|---|
| **T0** | Constraint compatibility (work item W0) | `I_CONSTRAINED_M = 1` works together with `LSPIRAL` | small probe suite | V-suite GREEN (§3) | — | Ran on **LRC, vasp.6.3.2 complex**, not the production binary. **Must be re-established on production.** |
| **T1** | Frame pinning (work item W1) | Which frame MAGMOM, M_CONSTR and M_int use | few SCFs | Per-ion M_CONSTR-vs-realized residuals uniformly small | `conventions.py` | Done: MAGMOM lab, M_CONSTR unwound, M_INT unwound (azimuth only). The V2 no-op test was frame-degenerate and is invalid. |
| **T2a** | C0 on `CSO_z.dat` | CSO structure | free | See C0 | RUN Set 0 | Passed |
| **T2b** | W0 gate + M1 on first `dump_P` | Dump file handling | free | See W0, M1 | RUN Set 0 | Evidence exists per REQ |
| **T2c** | N0 | Frozen-state premise | 1 SCF + 1 dump | See N0 | RUN Set 0 | Evidence exists per REQ; check the value and threshold (PRE A3) |
| **T3** | Offline CSO rotation | Rotated z CSO equals genuine x/y dumps; pins the Euler convention. This is the measurement-axis mechanism (`LZEROZ` fixes the spin plane, so the operator rotates instead). | 2 dumps | Machine precision, all blocks and ions | REQ §1; RUN Set A | Pending (x/y dumps not yet produced on Patch B) |
| **T2d** | P0 on one ±q pair | No residual even background at finite q | 2 SCF + 2 dumps | See P0; each \|T±\| ≈ 1e-4 eV | REQ §3 (q1/F0 first); RUN Set A gate | Pending |
| **T4** | F2 spot-check | I0 and per-ion decomposition on one F2 configuration, before F2 production | 1 SCF + dump | Gates at baseline levels | RUN Set D names "T4–T8" but **no dedicated pre-production run is scheduled** | Gap: add an explicit check on the first q1/F2a pair before releasing F2 at q2/q3 |
| **T5** | λ-scan | Extracted row flat in λ (penalty field not perturbing d at first order) | 3 SCF (×2 sides) | Flat within noise | REQ §5; RUN fixed-λ branches | Pending; see PRE B3/E1 for the proposed ramp-chain design |
| **T6** | ψ-independence | Fitted d_A − d_B flat across ψ = 30°, 60°, 90° | 3 SCF per q (×2 sides) | Flat within σ | REQ §6 | Pending |
| **T7** | Cross-family consistency | Rev 2: D_intra[R] from F0 vs d^Fe1 + d^Fe2 from F2. REQ extends it to shared F0/F2 controls across the ψ fits. | free | Agreement within propagated σ (with shared-data covariance) | REQ §6 | Pending |
| **T8** | Two-trace stability | y reproducible across independently reconverged replicated pairs; common mode stable | replicate pairs | Within paired uncertainty | REQ §4; RUN Sets A/C1 | Pending; replica protocol undefined (PRE E2) |
| **T9** | External anchors | qSO ±q energies on F0; commensurate supercell SOC energies; TB2J per-bond D | heavy | Consistent within the Approximation-2 budget | REQ §8 | Protocols not specified |

---

## 3. The constraint probe suite V0–V8 (evidence for T0)

Ran on **LRC** with `vasp.6.3.2 27Jun22 (build Jul 27 2026) complex`,
between late July and mid-August 2026. None of it is valid for the production
Perlmutter GPU build until repeated there.

| Probe | Question | Recorded result | Keep for a rerun? |
|---|---|---|---|
| **V0** | Is the tag recognized? | Yes | Yes. Also grep the OUTCAR INCAR echo (catches `I_CONSTRAINTED_M`-type typos). |
| **V1** | Does the constraint hold, and does a free state relax? | Free: 30° → 0°. Held: stays at 29.91°. | Yes |
| **V2** | Frame consistency via a no-op constraint | E_p = 1.4e-10 eV, ΔE_tot = 1.8e-6 eV; pinned M_CONSTR = "lab" | **No.** The observable is frame-degenerate. Replace with the Rev 2 §2.2 per-ion test (constrained F1 at q = 1/4). |
| **V3** | Is the constraint active, not idle? | A mis-targeted state moved 19.97° of the requested 20° | Yes |
| **V4** | λ response | ψ stationary to 0.044° between λ = 10 and 20; E_p ∝ 1/λ | Yes, and record per-ion δ, \|M\|, E_p and iterations per λ (PRE B3) |
| **V5** | Drift | Recorded only as "drift confirmed" | Check the probe `report.md` for what was measured |
| **V6** | F2 viability | θ realized 29.91° (0.09° error) | Yes; record the parent state and ramp (PRE B4) |
| **V7** | — | Not in the recorded summary | Check the probe report |
| **V8** | `LZEROZ` compatibility with the constraint | Recorded in August as "realized states identical with and without". Rev 2 later ruled it did not decide the F1 policy. | Replace with the F1 LZEROZ policy comparison (REQ §2 / PRE E1) |

---

## 4. VASP-side work items W0–W5 (Rev 2 §2)

| Item | Subject | Status |
|---|---|---|
| **W0** | Constraint compatibility under `LSPIRAL` (see §0 collision) | GREEN on LRC 6.3.2 only; re-establish on production |
| **W1a** | MAGMOM frame | Done: lab (carries 2πq·τ) |
| **W1b** | M_CONSTR frame | Rev 1 test invalid; pinned: unwound |
| **W1c** | M_int (OUTCAR magnetization) frame | Done: unwound, azimuth only (\|M\| and θ are frame-free) |
| **W2** | `LZEROZ` semantics and family flag matrix | F0 = T, F2 = F, **F1 open** (`F1_USES_LZEROZ = UNDETERMINED`) |
| **W3** | Longitudinal-only constraint patch (fallback) | Cancelled. Would give only F0 ∪ F2 = rank 7. |
| **W4a** | Machine-readable M_int | Not implemented; OUTCAR parsed via `read_realized` |
| **W4b** | Dump provenance headers | Done (in Patch B) |
| **W5** | k/q co-design: Γ-centered mesh, q commensurate, exclude q ∈ G and \|q\| < q_min, no TRIM live rows, q = 0 is the mandatory N0 configuration | Policy |

---

## 5. Patch A-era diagnostics (historical)

Still referenced in explanations. Their numbers are **void** as reference
values.

| Name | What it showed |
|---|---|
| **T-A** | The CSO operator is purely imaginary-antisymmetric, exactly. This ruled out operator contamination. C0 extends it with the C_dd = −C_uu sign check. |
| **T-D** | The trace flips sign under state conjugation (ratio −1 to 1e-17), and the ±q states are genuine conjugates |
| **Origin-shift test** | Translating all atoms moved the all-blocks trace (4.506 → 4.019 eV) but left the spin-diagonal trace unchanged. Hence flip blocks are excluded from the contraction (they must still be present in the dump for T3). |
| **Parity ratio ≈ 2** | Signature of the Patch A failure: +q and −q traces equal rather than opposite, from a ~0.6 eV even background |
| **Patch A σ_restart = 1.5e-5 eV** | Void; do not reuse (REQ §4) |

---

## 6. Fit diagnostics (`dmi_pipeline` gates on the solve)

| Name | Checks |
|---|---|
| **Rank / κ** | Design matrix reaches N_par = 9; condition number below κ_max. The worst-determined direction is reported by parameter name. |
| **predict_holdout** | Fit without a subset, predict it |
| **gate_holdout_family** | Hold out one configuration family and predict it |
| **gate_class_sum_agreement** | Displacement-class sums agree between families |
| **gate_loo_cv** | Leave-one-out cross-validation residuals. A leave-one-q-out variant would also test bond-range truncation (PRE C2). |
| **Realized / noise-weighted conditioning** | Rank and κ recomputed from realized rows with 1/σ² weights before fitting (REQ §3) |

---

## 7. Configurations, observables and pinned conventions

### Families (REQ §3)

| Code | Definition | Constraint | LZEROZ |
|---|---|---|---|
| **F0** | Flat spiral, both sublattices winding, ψ = 0, θ = 90° | none | T |
| **F1** | Flat spiral with sublattice phase decoration ±ψ (30°; T6 adds 60°, 90°) | `I_CONSTRAINED_M = 1` | open (W2) |
| **F2a** | Fe1 winds on a θ = 30° cone; Fe2 frozen along the axis | constrained | F |
| **F2b** | Fe2 winds on a θ = 30° cone; Fe1 frozen | constrained | F |

Neither F0 ∪ F1 nor F0 ∪ F2 reaches rank 9; F1 ∪ F2 does, and F0 alone has
rank 4.

### Other symbols

- **q1, q2, q3.** The campaign spiral vectors (1/4,0,0), (1/4,1/8,0) and
  (1/4,1/8,1/8), in fractional reciprocal coordinates, each with its negative
  partner.
- **Magnetic signs ε.** Fe1 = +1, Fe2 = −1. Inter-sublattice bonds carry
  ε_aε_k = −1 in the design matrix.
- **Generalized parity.** (q, ψ, θ) → (−q, −ψ, θ). It is realized in the
  SOC-free problem by the antiunitary spin mirror T∘C₂y.
- **y (two-trace observable).** [ΔE⁽¹⁾(q,ψ) − ΔE⁽¹⁾(−q,−ψ)]/N_m, with N_m = 2.
  Both sides are always measured.
- **E_DM.** [E(q) − E(−q)]/N_m, with no factor of ½.
- **Pin 2.** The old single-trace economy. Retired in favour of y.
- **Pin 3.** Sublattice labels are fixed by POSCAR order; a silent relabeling
  flips every ψ.
- **Pin 5.** Realized decorations replace targets in the design row, only if
  R0 confirms the state is still in its family.
- **N0 symmetry.** Spin-only C₂ₓ leaves an x-collinear state invariant and maps
  σ_zℓ_z → −σ_zℓ_z. That is why the N0 reference must be in-plane.

### `conventions.py` constants

| Constant | Value | Pinned by |
|---|---|---|
| `FRAME_MAGMOM` | lab | W1a |
| `FRAME_MCONSTR` | unwound | W1b replacement (per-ion residuals 1.50° / 46.50°) |
| `FRAME_MINT` | unwound (azimuth only) | W1c |
| Cone-axis convention | `internal_z_cone`, SAXIS = z | W1 |
| `F1_USES_LZEROZ` | UNDETERMINED | W2 / REQ §2 |
| `EULER_CONVENTION` | a+b+U (Patch A-era T3 at 1e-10; re-confirm with genuine Patch B dumps) | T3 |
| `SPIN_BLOCK_MAP` | {1:(0,0), 2:(0,1), 3:(1,0), 4:(1,1)}; UU_IDX = 0, DD_IDX = 3 | M0 / Hermiticity |
| `VASP_BUILD_ID` | from the `CSO.dat` header | C0 |
| `CPROJ_BAND_ORDER` | **retired** (CPROJ files are self-indexed) | — |

---

## 8. Runs, files and dump flags

| Name | What it is |
|---|---|
| **`ref`** (`noq/ref`, `material/ref`) | Once-per-material in-plane collinear SOC-free SCF. Parent of `dump_C` and of the F0 q1 chains. |
| **`dump_C`** | Once-per-material SOC run (`LSORBIT = T`, `ICHARG = 11`, `NELM = 1`, `LDUMPCSO = T`) → `CSO.dat`. The only SOC run in the campaign. |
| **`stage2`** | Per-configuration SOC-free spiral SCF (`LSPIRAL`, constrained for F1/F2) |
| **`dump_P`** | Per-configuration SOC-free one-shot from its own `stage2` (`LDUMPCPROJ`, `LDUMPCOCC`) → `CPROJ.*.bin`, `COCC.dat`, `FERWE.dat` |
| **`dump_P0`** | The `dump_P` of the q = 0 N0 configuration |
| **`CSO.dat`** | SOC operator matrix ⟨p\|ξσ·L\|p⟩ per ion, all four spin blocks; SAXIS in header |
| **`CPROJ.*.bin`** | Self-indexed PAW projections ⟨p\|ψ_nk⟩, one file per MPI rank; assembled by placement |
| **`COCC.dat`** | On-site occupation (density) matrices; stored transposed, so the contraction is `np.sum(CSO*COCC)` |
| **`FERWE.dat`** | Occupations f_nk and weights w_k from the same capture. The primary occupation source (EIGENVAL is only a cross-check). |
| **`PRE_LOOP`** | Dump point in `main.F` before any eigensolver call, so projections are the frozen input orbitals |
| **`SET_DD_PAW`** | In-loop call where the CSO buffer is populated. The CSO flush happens there. |
| **`LDUMPONLY`** | Early-exit flag. Not used: its stop path hits an XML finalization error. |
| **`LDUMP_LEGACY_LAST`** | Debug flag enabling same-state CSO + COCC for M0 |

---

## 9. Physics and VASP acronyms

| Term | Meaning |
|---|---|
| **DMI / DM** | Dzyaloshinskii–Moriya interaction; **d** is the pipeline's native DM vector, and the TB2J convention is D = −d/2 |
| **SOC** | Spin–orbit coupling, ξ L·σ (ξ_Bi ≈ 2.1 eV, ξ_Fe ≈ 0.14 eV, ξ_O ≈ 0.03 eV) |
| **ΔE⁽¹⁾** | First-order (force-theorem) SOC energy: Σ_nk f_nk w_k ⟨ψ⁽⁰⁾\|H_SO\|ψ⁽⁰⁾⟩, spin-diagonal blocks only |
| **Heide method** | Force-theorem trace method for DMI from spin spirals |
| **qSO** | Sandratskii's self-consistent approach: SOC included with its spin-flip parts masked so the generalized Bloch theorem survives; ±q total-energy differences. T9 anchor. |
| **gBT** | Generalized Bloch theorem (Sandratskii): spirals in the primitive cell via `LSPIRAL`/`QSPIRAL` |
| **Unwound frame** | gBT internal frame with the 2πq·τ phase removed; a correct spiral reads as collinear there |
| **PAW** | Projector augmented-wave method |
| **TB2J** | Green's-function (Liechtenstein-type) exchange/DMI code; T9 per-bond comparison |
| **R3c** | Space group 161; BFO = BiFeO₃, a G-type AFM with N_m = 2 Fe per magnetic cell |
| **N_par** | Number of fit parameters: 9 (3 orbits × 3 components within Rmax = 6 Å) |
| **Orbit / Moriya projector** | Symmetry-equivalent bond set / symmetry restriction and propagation of d across an orbit |
| **TRIM** | Time-reversal-invariant momentum; q ≡ −q, so no live row |
| **κ** | Design-matrix condition number |
| **λ (`LAMBDA`)** | Constraint penalty weight |
| **E_p** | Penalty energy λΣ\|M⊥\|². It scales as 1/λ at fixed torque. |
| **B^c** | Constraining field 2λM⊥; it equals the torque of the realized state |
| **`I_CONSTRAINED_M = 1`** | Direction-only moment constraint (VASP) |
| **`M_CONSTR`** | Constraint targets (unwound frame) |
| **`MAGMOM`** | Initial moments (lab frame) |
| **`M_int`** | Sphere-integrated moments written by VASP (unwound frame) |
| **`RWIGS`** | Integration and constraint sphere radii per species (Å) |
| **`LZEROZ`** | Zeroes the magnetization component along the spiral axis each iteration (enforces flat spirals) |
| **`SAXIS`** | Spin quantization axis; z in every configuration run |
| **SCF** | Self-consistent field run |
| **EDIFF** | Electronic convergence tolerance. Trace error scales roughly as √EDIFF (first-order, non-variational). |
| **LRC** | Lawrencium (LBNL cluster). Ran the V-suite. |
| **Perlmutter** | NERSC GPU/CPU system. Production target. |

---

## 10. Campaign structure codes

| Code | Meaning |
|---|---|
| **REQ §1–§8** | Data requirements: axis dumps (§1), F1 LZEROZ policy (§2), baseline 12 pairs (§3), replicas/T8 (§4), λ/T5 (§5), decorations/T6–T7 (§6), return files (§7), external anchors/T9 (§8) |
| **RUN Set 0** | Import and verify reference, z CSO and N0 evidence |
| **RUN Set A** | x/y CSO dumps; q1/F0 baseline ± and replicas 2/3 |
| **RUN A gates** | T3 and z-only P0 with fresh paired F0 noise |
| **RUN Set B / B gate** | F1 LZEROZ comparison and policy resolution |
| **RUN C1 / C2 / C3** | Dependency levels: q1 constrained work and scans; then q2; then q3 (chained q1 → q2 → q3 within each branch) |
| **RUN Set D** | Analysis: pairs, noise, T4–T8, nine-parameter fits |
| **PRE A1–A3** | Provenance checks (V-suite build and cluster, z CSO build, N0 record) |
| **PRE B1–B5** | Constraint machinery (zero targets, RWIGS, λ behaviour, F2 start, V8 content) |
| **PRE C1–C3** | Pipeline code (pair rows, leave-one-q-out rank, old ±q readbacks) |
| **PRE D1–D3** | Cost, quota and purge, `job.sh` contract |
| **PRE E1–E3** | Pilots on the production build (combined constraint pilot, replica determinism, EDIFF sensitivity) |
