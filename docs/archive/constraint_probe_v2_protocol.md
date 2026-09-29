# Constraint probe v2 (CP suite): run protocol

Replaces the V0–V8 probe, which ran on LRC with vasp.6.3.2 and therefore does
not validate the production build. Terms follow
[test_and_code_glossary.md](test_and_code_glossary.md). Test IDs use the prefix
**CP** so they cannot be confused with the gates (C0, P0, R0) or the old V-suite.

Final execution decisions: [next_steps.md](next_steps.md). This updated protocol
specifies proposed runs, not production validation results.

**Goal.** Re-establish on the production Perlmutter binary:

- that the moment constraint works under `LSPIRAL` (ladder rung T0);
- the three frame conventions (W1);
- the λ behaviour;
- Bi/O constraint handling;
- F2 viability and its best starting state;
- the F1 `LZEROZ` policy (W2).

**Scope.** Every run is SOC-free with `SAXIS = 0 0 1`. The probe needs no
`dump_C`, no `dump_P`, and does not test N0 or T3.

## 1. Starting point and prerequisites

The physical seed is one converged collinear calculation, called **`ref`** below.
Also supply the production executable/source provenance and working Perlmutter
job template. Check the seed before anything else.

| Check | Required | If not |
|---|---|---|
| Code path | `LNONCOLLINEAR = T`, `LSORBIT = F` | Using `ref` only as a source of settings and moment magnitudes, run a new noncollinear `ref` from a cold start (`ISTART = 0`, `ICHARG = 2`). |
| Moment direction | In-plane (e.g. `MAGMOM = M 0 0  -M 0 0  0 …`) | Rerun `ref` in-plane. A z-collinear parent sits 90° from every flat spiral, and `LZEROZ = T` would remove its moments on the first step. The SOC-free energy is identical either way, so this costs one SCF. |
| Executable | Production binary (SHA-256 and build banner) | Reconverge a separate production ref; a compatible old restart may seed it after compatibility checks, otherwise start cold. Preserve old acceptance data. |
| Settings | Production ENCUT, EDIFF, +U, Γ-centered 8×8×8 mesh, `ISYM = -1`, NBANDS, mixer | Rerun. Results must transfer to the campaign unchanged. |

Before any submission, also settle the following:

1. **RWIGS pinned** (PRE B2). Use one set for every run. The LRC values
   (1.91 / 1.86 / 0.83) are only a starting candidate.
2. **Source-to-binary identity established** (PRE B1). The checked-in source
   skips zero-target ions in both field and penalty loops. Confirm that code
   produced the Perlmutter executable, then keep Bi/O `M_CONSTR = 0 0 0`.
   CP5 diagnoses indirect induced-moment changes, not a presumed direct penalty.
3. **Frame discriminator is nonzero.** Compute Δφ_τ = 2π q1·(τ_Fe2 − τ_Fe1)
   mod 2π from the production POSCAR. It must be far from 0 (about 45° was
   recorded). If it is not, choose another commensurate q for the probe.
4. **Environment fixed.** Pinned modules, the tag whitelist, and an OUTCAR
   INCAR-echo check after every run.

## 2. Runs

q1 = (1/4, 0, 0). The ψ values are targets in the unwound frame.

Common to all runs except `ref`:

- `LSPIRAL = T`, `QSPIRAL = ±q1`, `LSORBIT = F`, `SAXIS = 0 0 1`, `RWIGS` set;
- `I_CONSTRAINED_M = 1` always (readback-only runs use `LAMBDA = 0`);
- `MAGMOM` in the lab frame; `M_CONSTR` in the frame named below;
- chained runs use `ISTART = 1`, `ICHARG = 0`.

| Run | State | Parent | LZEROZ | M_CONSTR frame | λ | SCF steps |
|---|---|---|---|---|---|---|
| `f0_p`, `f0_m` | F0 at ±q1 | `ref` | T | (targets F0) | 0 (readback only) | 2 |
| `f1_T` | F1, ψ = +30°, +q1 | `f0_p` | T | unwound | chain 1 → 3 → 10 → 30, **all rungs run** | 4 |
| `f1_F` | same as `f1_T` | `f0_p` | F | unwound | same chain, all rungs | 4 |
| `f1_lab` | same as `f1_T` | `f0_p` | T | **lab** | 1 → 3 → 10, stop once CP1 discriminates | ≤ 3 |
| `f1_free` | F1, ψ = +30°, +q1 | cold MAGMOM (`ISTART = 0`, `ICHARG = 2`) | T | (targets F1) | 0 | 1 |
| `f1_m` | F1, ψ = −30°, −q1 | `f0_m` | CP7 winner | unwound | ramp up to `f1_*`'s selected λ | ≤ 4 |
| `f2_chain` | F2a: Fe1 cone 30°, Fe2 along signed axis, +q1 | `f0_p` | F | unwound | 1 only; dead-point diagnostic control | 1 |
| `f2_cold` | same target as `f2_chain` | near-target cold MAGMOM (`ISTART=0`, `ICHARG=2`) | F | unwound | 1 → 3 → 10 → 30, stop at first signed R0 pass | ≤ 4 |
| `f2b_cold` | F2b: Fe2 cone 30°, Fe1 along signed axis, +q1 | separate near-target cold MAGMOM | F | unwound | same | ≤ 4 |
| `f1_p60`, `f1_p90` | F1, ψ=+60°, +90°, +q1 | accepted selected-policy +30° → +60° | CP7 winner | unwound | each ramps 1 → 3 → 10 → 30, stop at first signed R0 pass | ≤ 8 |
| `f1_m60`, `f1_m90` | F1, ψ=−60°, −90°, −q1 | accepted `f1_m` → −60° | CP7 winner | unwound | same | ≤ 8 |

This list permits up to 43 SCF steps, excluding a new reference, optional
readback-mode controls and recovery jobs. This is a bound, not a runtime estimate.
Reuse accepted probe states later only when settings and provenance match.

**Mode-1 initialization.** At exactly 90° to the target, the penalty has zero
angular derivative; at 180° its energy is also zero. Do not start ψ=90°
directly from F0 or use flat F0 as a frozen-axis F2 production seed. Other
forces or numerical perturbations can move a full SCF away from the dead point:
`f2_chain` is a diagnostic, not a test required to fail. Production uses the
signed ψ chain and near-target F2 cold starts. R0 rejects wrong relative signs
and frozen-axis polarity, including antiparallel zero-penalty solutions.

**Chaining note.** A chained run reads its starting orbitals from the parent's
WAVECAR, so `MAGMOM` has no effect on its initial state. This is why
`f1_free` must be a cold start to test "unconstrained relaxation", and why the
`f1_*` chains starting from ψ = 0 test whether the constraint actually moves
the state.

Optionally, add a `dump_P` at every rung of `f1_T`, `f1_F` and `f1_m`. The
chains then double as the T5 λ-scan and the preflight E1 pilot. In that mode,
`f1_m` must continue through λ=30 even if an earlier rung passes. Only the
CP7-selected policy forms T5 pairs. This is an explicit projection-pilot
extension with the required dump gates; the stand-alone CP suite needs no dumps.

**Dependency order.**

1. `ref` → `f0_p`, `f0_m`.
2. `f1_T`, `f1_F`, `f1_lab`, `f1_free`, `f2_chain`, `f2_cold`, `f2b_cold`
   are independent branches once their prerequisites are ready. Cold branches
   need the settings/readback reference, not F0 wavefunctions.
3. After CP1 and CP7 pass, `f1_m` and +60° → +90° can run in parallel.
   The −60° → −90° chain follows accepted `f1_m`; parity sides stay separate.

## 3. Tests

All readback goes through `read_realized`; OUTCAR tables are never read by
hand. For every step, record per ion:

- the target vector in both frames and the MAGMOM phase;
- OSZICAR `MW_int` and `M_int`, the OUTCAR magnetization vector, and the
  printed constraint field with its source-verified factor of two;
- \|M\|, θ, azimuth, E_p, λ;
- the iteration count and TOTEN;
- the EIGENVAL file (needed for CP8).

| Test | Replaces | Uses | Measures | Pass |
|---|---|---|---|---|
| **CP0** Tag and readback | V0 | every run | Echo of I_CONSTRAINED_M, LAMBDA, M_CONSTR, RWIGS, LZEROZ; E_p, MW_int and M_int present; λ=0 gives E_p=0 within output precision | Record separate magnitude references for each readback from `f0_p`/`f0_m`; R0 uses the matching definition and RWIGS. |
| **CP1** Frames | V2 (invalid) | `f0_*`, `f1_free` first iteration, `f1_T`, `f1_lab` | Per-ion azimuth residuals r_μ after removing one global phase | See §4 |
| **CP2** Holds vs relaxes | V1 | `f1_free` vs `f1_T` | Realized ψ with and without the constraint | Held state within 1° of target; free state differs from it by far more than 1°. If the free state also stays at 30°, F1 is metastable unconstrained: report it, since it changes the constraint rationale for F1. |
| **CP3** Constraint is active | V3 | `f1_T` rungs | Movement of ψ from 0° (the parent state) toward +30° | Reaches 30° ± 1° by the first passing rung; E_p finite and nonzero while moving |
| **CP4** λ response | V4 | `f1_T` rungs | Weighted moments; B^c=2λ[MW−mhat(mhat·MW)]; E_p and iterations | Vector field agrees with printed field within output precision. Report field variation, λ·E_p and angular scaling as diagnostics, not mandatory scaling laws. A passing λ applies to this configuration, not automatically a family. |
| **CP5** Bi/O response | new | `f1_T` vs `f0_p` | Weighted/unweighted induced moments; source-confirmed zero-target exclusion | Confirm no direct Bi/O penalty in matched source. Report indirect changes; significant changes need explanation, not automatic new targets or a forced no-change criterion. |
| **CP6** F2 viability | V6 | `f2_chain`, `f2_cold`, `f2b_cold` | Signed R0, terminal λ, magnitudes, iterations | Both near-target cold-start assignments pass signed R0. Flat-parent control is reported independently; its expected failure is not a gate. |
| **CP7** F1 LZEROZ policy | V8 | `f1_T` vs `f1_F` at common λ rungs | θ, circular ψ, α_rms, E_p and convergence; TOTEN separately | Both pass R0 and agree in θ and ψ within 1°: choose T. Choose F if T fails realization/convergence and F passes. Missing evidence, both failing or material disagreement: UNDETERMINED. No energy σ is used for angles. |
| **CP8** Constrained parity | new | selected-policy +30° and `f1_m` at common accepted λ | Signed ψ parity, TOTEN, E_p, spectra with explicit k→−k mapping modulo reciprocal vectors | Circular ψ sum below 1°; energies/spectra within recorded tolerances from tighter-convergence checks and output precision. A few × EDIFF is not an error bound. Mismatch can reflect writer/frame errors, incomplete convergence or different states. |
| **CP9** Decoration continuation | new | +30°→+60°→+90° and −30°→−60°→−90° | Signed R0 and parent provenance at every step | Both chains reach signed targets without moment collapse; validates the production path under the CP7 policy. |

## 4. CP1 in detail: pinning three frames with one set of runs

For ion μ, the two candidate targets are:

- lab frame: φ_μ^lab = 2π q·τ_μ + φ_ref,μ + ψ δ_μ,Fe2
- unwound frame: φ_μ^unw = φ_ref,μ + ψ δ_μ,Fe2

The residual is r_μ = φ_μ^read − φ_μ^target − Φ, where Φ is one fitted global
phase (the SOC-free problem is gauge-free about z). Use wrapped differences.
The **correct frame gives \|r_μ\| < 1° on each Fe with resolved transverse
moment**. Zero/near-zero Bi/O moments and frozen axial moments have no usable
azimuth. The wrong frame gives a relative residual
r_2 − r_1 = ±Δφ_τ.

| Convention | Evidence | Decides |
|---|---|---|
| `FRAME_MINT` (OSZICAR `M_int`) | `f0_p`, `f0_m`: F0 relaxes to its natural state, so compare readbacks against both candidate forms of that state | Frame of `M_int` |
| OUTCAR magnetization table | Same runs, compared against `M_int` | Whether the two readouts share a frame. The VASP wiki suggests the constraint-sphere `M_int` handles spirals differently from the standard site tables, so the two may **not** agree. `read_realized` must use one pinned source. |
| `FRAME_MAGMOM` | Matched-source initialization path and a verified pre-update capture if available; first printed `f1_free` moments support but do not alone establish the seed | MAGMOM input frame; an SCF iteration may already have evolved the state |
| `FRAME_MCONSTR` | `f1_T` vs `f1_lab`: one reaches its target with uniform residuals, the other shows the ±Δφ_τ signature | M_CONSTR frame |

Expected (from the Rev 2 pins): MAGMOM lab, M_CONSTR unwound, OUTCAR table
unwound. Pin `MW_int` and `M_int` frames independently of the OUTCAR table.
Absolute weighted-moment alignment to M_CONSTR is needed for field diagnostics;
do not gauge-fit away that misalignment. Family R0 may remove one common
azimuthal gauge, never independent per-ion signs. Retain POSCAR Fe signs when
mapping physical vectors to family cone angles, especially on the frozen ion.

## 5. Outputs and what they set

| Result | Sets | Where it lands |
|---|---|---|
| CP0–CP3 | Readback, frames, hold/free and activity evidence for T0/T1; source-specific magnitude references | Glossary and R0; tag echo alone is insufficient |
| CP1 | `FRAME_MAGMOM`, `FRAME_MCONSTR`, `FRAME_MINT`, readout source | `conventions.py`, each with this run ID |
| CP2–CP4 | Per-configuration ramp evidence; proposed later optimizations | Keep Rev 2 policy unless explicitly amended; no automatic family λ |
| CP5 | Confirmed zero targets and induced-moment diagnostics | Materializer/provenance; no automatic target changes |
| CP6 | F2 parent rule; F2 viability on production | RUN §3 |
| CP7 | `F1_USES_LZEROZ` | `conventions.py`; replaces the REQ §2 probe and the RUN Set B gate |
| CP8 | Parity-consistent constrained writer | Materializer tests; unblocks F1 pairs |
| CP9 | Signed decoration-chain viability | RUN §3; releases ψ=60°/90° branches |

**Return, per run:** INCAR, POSCAR, KPOINTS, OUTCAR, OSZICAR, EIGENVAL,
stdout/stderr, job script, executable SHA-256 and build banner, `module list`,
and parent run ID with restart hashes. Keep WAVECAR/CHGCAR on Perlmutter:
`f0_p` and `f0_m` can seed the campaign's q1/F0 baseline if their provenance
matches. Probe F0 uses mode 1 with λ=0 for readback, whereas production F0
is unconstrained. Verify equivalence from matched source and a controlled
check before reusing these states; otherwise retain probe-only states and run
production F0 with its specified tags.

**Stop conditions.**

- CP0 or CP3 fails (constraint inactive on this build): stop. This is the
  Rev 2 risk-register case, and F1/F2 are blocked.
- CP1 is ambiguous: do not pin any frame, and do not proceed to F1 pairs.
- Every other failure is reported and blocks only the decision it feeds.
