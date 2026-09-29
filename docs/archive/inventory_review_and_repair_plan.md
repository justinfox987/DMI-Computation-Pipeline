# Review of `CODEBASE_INVENTORY.md` — Physics Corrections and Repair Plan

The inventory is accurate where I can check it against the project history, and its findings 1–8 match what I'd expect. Two of its observations (the `LSPIRAL = T` requirement in `trace_config`, and the `SAXIS = 0 0 1` assertion in `load_cso`) are more serious than their placement suggests — they block the acceptance test outright. Below: what the inventory has right, the physics errors it does not flag, and a repair order aimed at getting N0 measured this week.

---

## Part 1 — Physics errors not flagged in the inventory

### P1. `gate_c0` requires the spin-flip blocks to vanish. This is wrong, and will fail on your real dump.

`gates.gate_c0` (:84) checks "spin-flip blocks zero." The SOC operator is

$$\xi\,\boldsymbol\sigma\cdot\mathbf L = \xi\left[\sigma_z \ell_z + \tfrac12(\sigma_+\ell_- + \sigma_-\ell_+)\right]$$

The second term lives **entirely** in the `ud`/`du` blocks. A correct SOC dump has nonzero flip blocks. Your own Patch A data confirms this — the phase test measured the flip blocks contributing ~4.2 eV, concentrated on Bi. Requiring them to be zero is a physics error, and `gate_c0` would reject a correct `CSO.dat`.

The standalone `gate_c0.py` I sent you did **not** check the flip blocks, which is why C0 passed today. Those are two different gates with the same name.

**Fix:** delete the flip-block-zero assertion. Replace it with the correct structural check on the full 2×2 operator:

- `C_ud = C_du†` (Hermiticity of the full operator, not just per-block)
- `C_dd = -C_uu`, `C_uu` purely imaginary, antisymmetric, zero diagonal (keep these — they passed)
- report `max|C_ud|` per ion as **diagnostic output**, not a pass condition

Then re-run C0 on your real `CSO.dat` and look at `max|C_ud|`. If it's nonzero and Bi-dominated, that is correct and expected. If it really is zero, that is itself a finding — it would mean the dump captures only the $\sigma_z\ell_z$ component, which changes what the trace can measure, and I'd want to see the numbers before you build on it.

Note the separate, already-established fact: the flip blocks are correctly **excluded from the trace** (the origin-shift test proved their single-cell contribution is a gauge artifact). Excluding them from the contraction and requiring them to be zero in the dump are different statements; the code currently conflates them.

### P2. The N0 threshold is too loose — looser than the signal it must protect.

`gate_n0` uses `1e-4`; my migration spec said `5e-4`. Both are wrong, and the spec value is mine to correct.

The expected $E_{\rm DM}$ scale for BFO is 1–2×10⁻⁴ eV. A null threshold of 5×10⁻⁴ would let a contamination **larger than the entire signal** pass. The threshold has to sit below the signal, not above it.

The right scale is the per-trace reproducibility: σ_restart ≈ 1.5×10⁻⁵ eV (measured, but on Patch A traces, so treat it as an order of magnitude until re-measured).

**Fix:** `N0_TOL = max(5e-5, 3σ_restart)` on the total, and the same per ion. Also record the **per-ion Bi value separately** — Bi is where contamination concentrates, and a total that passes while Bi alone sits at 4×10⁻⁵ is a warning, not a pass.

### P3. `realized_state_gate.py` defaults to the frame that caused the original failure.

`run(directory, realized_frame="lab")` (:424), while `conventions.FRAME_MINT = "unwound"`. This is the exact discrepancy that produced the phantom "spiral collapsed to collinear" result and sent the project into the constraint campaign. Anyone running the script without the flag gets the wrong azimuth at any q where $2\pi\mathbf q\cdot(\boldsymbol\tau_2-\boldsymbol\tau_1)\notin 2\pi\mathbb Z$.

**Fix:** default to `conventions.FRAME_MINT`, don't hardcode. Keep `--realized-frame` as an override for forensics on old runs, and have the script print which frame it used in every report. `USAGE.md`'s "lab is the historical default" line should be deleted, not softened.

### P4. `FRAME_MAGMOM`/`FRAME_MCONSTR` and `targets.to_frame` are two orthogonal transformations, not a vocabulary mismatch.

The inventory (finding 3) reads this as a naming problem. It isn't. There are two independent rotations, and the code has one constant where it needs two:

| Transformation | What it does | Where it lives | Convention |
|---|---|---|---|
| **Spiral phase** | include or drop the per-site $2\pi\mathbf q\cdot\boldsymbol\tau_\mu$ in the azimuth | `frames.lab_to_unwound` | `FRAME_MAGMOM = "lab"`, `FRAME_MCONSTR = "unwound"` |
| **Cone axis** | rotate the configuration so its rotation plane normal is $\hat n$ instead of $\hat z$ | `targets.to_frame` | `"internal_z_cone"` vs `"lab_cartesian"` |

Renaming either one to match the other would silently apply the wrong rotation. `magmom_string` and `mconstr_string` must apply **both**, in order: build with `spin_targets` (which already includes $2\pi\mathbf q\cdot\boldsymbol\tau$), apply the spiral-phase choice via `frames`, then apply the cone-axis rotation via `to_frame`. Two arguments, two constants.

The three-frame round-trip test in `test_migration_spec.md` §5 must therefore be a **four**-way test: {lab, unwound} × {z-cone, n̂}.

### P5. The axis mechanism is ambiguous, and the two available paths would double-count.

This is the one I'd resolve before anything else in the campaign, because it decides whether T3 and rotated CSO files are needed at all.

There are two ways the code can select which component of $\mathbf d$ a measurement probes:

- **(a) Rotate the spins.** `targets.to_frame(..., "lab_cartesian", n_hat)` puts the spiral plane normal along $\hat n$; SAXIS stays $\hat z$; one `CSO_z.dat` forever. This is Heide's formulation.
- **(b) Rotate the operator.** Spins stay in the $xy$ plane (`LZEROZ`); `cso.rotate_saxis` produces `CSO_x/y`; `trace_config(axis=...)` picks one.

The repo currently contains both paths, and `design.configuration_kernel` takes an `axis` argument that is consumed by neither. **Applying both is a double rotation and gives a wrong design row.** Exactly one must be live.

I'd choose **(a)**: it matches the formalism, needs a single material-level CSO dump, makes the `SAXIS = 0 0 1` assertion in `load_cso` correct rather than an obstacle, and retires T3, `CSO_x/y.dat`, `rotate_saxis`, and `CSO_ROTATION_VALIDATED` from the production path entirely. That also resolves the inventory's finding 4 ("nothing writes rotated CSO files") by removing the requirement.

But this is checkable rather than arguable, and cheaply: take one configuration and compute its trace both ways — spins rotated to $\hat n = \hat x$ with `CSO_z`, versus spins in $xy$ with CSO rotated to $x$. The two differ by a global rotation of the whole problem, so they must agree. **If they don't, one path has a bug and the campaign would have inherited it.** Run this once, before materializing anything.

There is a caveat either way, and it's worth stating plainly: the trace uses only the spin-diagonal blocks, so it is a partial SOC sum, not $\langle\xi\boldsymbol\sigma\cdot\mathbf L\rangle$. Whether that partial sum tracks $\mathbf d\cdot\hat n$ correctly is not something the code can assert — it's what P0 (parity) measures empirically, on top of N0.

### P6. The noise model must be re-derived, not inherited.

Finding 5 correctly notes nothing supplies `sigma_y`. The physics point the inventory doesn't make: **σ_restart = 1.5×10⁻⁵ eV was measured on contaminated Patch A traces** and is not a Patch B quantity. Every number in the old manifest and in `noisefloor.py`'s outputs is void for the same reason.

`new_direction.md` §9's observation that TRIM- and parity-based noise estimators are invalid while an even background exists is *why* `noisefloor.py`'s `process()` is not merely broken but computing the wrong thing. If N0 passes, the background is gone and those estimators become valid again — so re-measure with restart replicates, and have the planner emit them (`role = "noise"`) rather than expecting hand-editing.

### P7. Minor physics-adjacent items

- `model._n_m_from_orbits` (:109) guesses $N_m$ by "2 if any bond touches site index 1" while `Orbit.n_m` is populated by `build_orbits`. Use the field. The guess is right for BFO and wrong for anything else.
- `realized._read_penalty_and_lambda` (:150) can pick up `LAMBDA` from the OUTCAR INCAR echo instead of the SCF trace, so `lambda_final` may report the input value. Anchor the parse to the OSZICAR/SCF block.
- `cli.realize` (:214-220) passes `tol.phi` (radians) as a q tolerance and `TOL_MOMENT_REL` (a fraction) as an absolute μ_B tolerance. Both are unit errors; the inventory has this right and it belongs on the critical path since R0 gates every Stage-2 run.

---

## Part 2 — What blocks N0 this week

These are the only items on the critical path. Everything else can wait.

| # | Blocker | Fix |
|---|---|---|
| **B1** | `trace_config` requires `LSPIRAL = T` (:347). The N0 configuration is q = 0, dumped **without** `LSPIRAL`. The acceptance gate cannot be evaluated. | Require `LSPIRAL = T` **iff** `q_frac ≠ 0`; when q = 0, accept either and assert `QSPIRAL = 0` if present. |
| **B2** | `gate_c0` flip-block assertion (P1) | Delete the assertion; report `max\|C_ud\|` as diagnostic. |
| **B3** | `gate c0`/`w0`/`m1` are print-only; `CSO_SIGN_VALIDATED` dies with the process (finding, §1.3) | Add `--manifest` to all three, using the existing `_report_and_maybe_append` path that `gate m0`/`gate t3` already use. |
| **B4** | `trace_config` requires `cfg_dir/dump_P/DONE` and `cfg_dir/config.json`; nothing writes either | Implement `dmi finish <dir>` from the migration spec §6.3 — it's ~50 lines and is also what unblocks `materialize`'s DONE-gating later. Interim: write both by hand for the N0 directory. |
| **B5** | `N0_TOL` (P2) | `max(5e-5, 3σ)`; add the per-ion Bi report. |
| **B6** | **Performance.** `compute_delta_E1` and `_rebuild_patch_b_cocc` are deliberately unvectorized Python loops. On your real dump — 512 k-points × 152 bands × 10 ions × 2 blocks × LMDIM² — that is 10⁸–10⁹ inner iterations. Minutes at best, hours if LMDIM is large. M1 is the same magnitude. | Vectorize with `np.einsum`, keep the loop version as `compute_delta_E1_reference`, and add an equivalence test on a small case. The existing density-matrix oracle in `test_trace.py` is the right guard. |
| **B7** | `cli trace` writes `trace_gate = "PASS"` without running I0 (:460) | Run I0; record the real result. A hardcoded PASS in a gate field is worse than no gate. |

**Also fix before trusting any N0 number:** `trace` traces all three axes unconditionally. Until P5 is resolved, run z only.

---

## Part 3 — Repair order after N0

**Tier 1 — campaign-blocking.** Resolve P5 (axis mechanism) with the equivalence test. Fix P4 (two frame transformations in `targets`), which unblocks `materialize` without the monkeypatch. Pin `F1_USES_LZEROZ` from the constraint probe. Fix the `cli.realize` unit errors (P7). Unify the directory layout: the migration spec says `configs/<id>/{stage2,dump_P}`, the code uses `measurements/<id>/{plus,minus}/stage{2,3}`, and `write-run-script` checks for Patch A Stage-3 files. Pick the spec layout and change `execution.py` to match.

**Tier 2 — make the campaign runnable end to end.** `finish`/`submit`/`status`; DONE-gated `materialize`; the INCAR tag whitelist (this is the `I_CONSTRAINTED_M` guard — high value for ~20 lines); manifest status and provenance fields; planner-generated noise replicates (P6); `solve` blocking on C0 and N0; the `passed is None` bug at `cli.py:489` that treats NOT_APPLICABLE as failure.

**Tier 3 — deletions.** These are safe and reduce the surface a lot: `single_trace.py`, `ta_td_extract.py`, `noisefloor.py`, `dmi_pipeline/ta_td.py` (all broken, no tests, no importers), `cproj.py` and `gates.gate_m1` together, the 17 unreferenced definitions in §9.1, `vasp_sample/` (247 MB, unreadable by `dumpio`), the stale root `manifest.json` and `report.md`. Keep `cso.py` only if P5 resolves toward option (b).

Keep the T-A/T-D material as **documentation**, not code — `TA_TD_extraction_reference.md` records why the two-trace method exists, and that history is worth preserving even though `ta_td.py` should go.

**Tier 4 — hygiene.** `model.design_row` vs `design.configuration_kernel` duplication (delete the former, re-point three test files at the latter); `design_row_reference` is currently an alias of `design_row`, so that test compares a function with itself and should be deleted or made a genuine second implementation; the three ψ/θ inversion implementations (`realized`, `realized_state_gate`, `constraint_probe`) should collapse to one with the probe's kept deliberately as an independent check.

---

## Part 4 — Two things the inventory gets right that deserve emphasis

**The physics core is intact.** `orbits`, `model`, `design`, `solve`, and the planner are format-free and untouched by all of this. `test_model.py::test_directed_bond_oracle_matches_canonical_design` remains the strongest check in the repo. None of the Patch A contamination reached this layer.

**Three test files monkeypatch the frames to make the suite pass** (finding 3, §5 notes). That is the single most dangerous thing in the inventory: 180 green tests while `materialize` cannot run with shipped conventions. When P4 lands, delete those autouse fixtures — if a test then fails, it is telling you something true.
