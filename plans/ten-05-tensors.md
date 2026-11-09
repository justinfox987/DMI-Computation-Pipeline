# TEN-05 spec: tensors, fits and the spiral prediction

Physics authority: `docs/math/heide_math_v3.md` (Revision 3.1), Sections 1, 6,
7, 9 and 10. Run tree and checks: `plans/ten-03-spiral.md` and
`plans/ten-04-trace.md`. This file fixes the interfaces, the guards and the
tests. It does not restate the equations.

Status: approved by the user on 2026-11-09, with the decisions at the end. Work
on `ten-05-tensors` from `main` (`6aceeea`, TEN-04 merged).

## Scope

Add `pipeline v3/dmi_pipeline/tensors.py` (about 200 lines) and `dmi fit DIR`.
The command writes `DIR/tensors.json` and covers:

1. `y` and `g` from `traces.json` and `collected.json` (Eqs 1.3, 1.4), per
   magnetic site;
2. the per-direction fits of Eq (9.1), with the pooled uncertainties of Eq (9.9);
3. `D_free` (Eq 9.3), its forbidden part `F` (Eq 9.4), the constrained `D`
   (Eq 9.5) and `A` (Eq 9.6) in the TEN-02 bases, each with a covariance;
4. the Section 10.1 prediction: `Gamma`, `n*`, `q*`, `e*` and the pitch
   `lambda`, with the units of Section 10.4;
5. the Section 11 Forbidden check and the positive-`A` check;
6. what a provisional `T_y` means for `D`, reported in the output;
7. element-resolved `D` by species (Section 9.5);
8. the spin-wave stiffness `D_sw = 4A/M` (Eq 10.2), for ferromagnets only.

Out of scope:

- Exchange classes and Eqs (9.7)–(9.8), the second stiffness route: TEN-09.
- The rest of Sections 10.2–10.3 (the magnon dispersion, `T_MF`, `B_D`, walls
  and `K`): TEN-09, because they need `K` or exchange runs.
- The texture-class label. The form of `D` is in the output; naming the class
  waits until a material needs it.

## Inputs, normalization and units

`dmi fit` reads only the run tree. It uses `plan.json` (the seed text, the
directions, the group and the `runs` list), `collected.json`, `traces.json`, each
run's `config.json`, and `q0/POSCAR`.

- `N_m = len(config["sites"])`, the number of magnetic sites in the calculation
  cell. It must be the same in every run and must equal the number of `sites`
  in the seed text stored in `plan.json`.
- `y_a(q) = [T_a(q) - T_a(-q)] / N_m` from `traces.json` `T_eV`, and
  `g(q) = [E(q) + E(-q) - 2 E(0)] / (2 N_m)` from `collected.json` `E_eV`. Both
  are in eV per magnetic site. These are Eqs (1.3) and (1.4) with no extra
  factor of one half.
- Directions: the Cartesian unit `s_i = spiral.unit_directions(lattice, d_i)`,
  which is the same function `plan` used. `t` for each pair is
  `|spiral.cartesian(lattice, q_frac)|` of the `+q` run, checked against
  `plan.json` to `1e-9` relative.
- Units: `q` in 1/Å, so `D` comes out in eV Å and `A` in eV Å² per magnetic site.
  The output gives meV Å and meV Å² per site, and the Section 10.4
  micromagnetic values: `V_m = V_cell / N_m` from `q0/POSCAR`, `A` in pJ/m and
  `D` in mJ/m². The factors 1.602 and 16.02 apply to meV values divided by
  `V_m` in Å³, as in the Section 10.4 table, not to eV values. They are written
  once, as constants next to that table.
- Symmetry: `symmetry.operations` is rebuilt from `q0/POSCAR`, `config.json`
  sites and signs, and the seed's `symprec` and `spacegroup` (parsed from
  `plan.json["seed"]` with `tomllib`). That gives `B_l`, `C_l` and `P_D`. The
  same function and the same inputs mean the same bases as `plan`.

## Fits

```python
tensors.least_squares(X, y) -> (x, cov, rss, dof)       # the one routine of Section 9
tensors.observables(out) -> dict                        # per direction: s, t (Nt,), y (Nt, 3), g (Nt,)
tensors.fit_directions(obs) -> dict                     # v (Nd, 3), kappa (Nd,), cov_v, var_kappa, pooled sigma2
tensors.spiralization(s, v, cov_v, B) -> dict           # D_free, F, D, d, and their covariances
tensors.stiffness(s, kappa, var_kappa, C) -> dict       # A, a, covariance, eigenvalues
```

- **Eq (9.1).** For each direction, fit `y_a = v_a t + c_a t^3` on every axis
  and `g = kappa t^2 + b t^4`, each with `least_squares`. The noise variance is
  pooled as in Eq (9.9). For `y`, the sum of squared residuals over all
  directions and axes is divided by the total degrees of freedom. `g` gets its
  own pool. Axes from one state share noise, so the slope errors are estimates
  (Section 9.4). Cross-axis covariance is not modelled.
- **Eq (9.3).** `D_free = V S^+ / 2`, with `S` the unit `s_i` as columns and `V`
  the `v_i` as columns, in the same order.
- **Eq (9.4).** `F = D_free - P_D[D_free]`, with
  `P_D[M] = sum_l <B_l, M> B_l` (Frobenius). With `p_D = 0`, `P_D = 0` and
  `F = D_free`.
- **Eq (9.5).** The `d_l` minimize over the `3 Nd` rows
  `X[(i, a), l] = 2 e_a^T B_l s_i`, and `D = sum_l d_l B_l`.
- **Eq (9.6).** The `a_l` minimize `M[i, l] = s_i^T C_l s_i`, the matrix
  `spiral.conditions` already builds, and `A = sum_l a_l C_l`.
- **Uncertainties.** Every output of the last four items is linear in `v` or
  `kappa`. Their covariances come from one helper, which applies the linear map
  to the stacked `v` (or `kappa`) and propagates the block-diagonal input
  covariance: `J Sigma J^T`, with `J` built by applying the map to unit
  vectors. There is no second formula per quantity.
- **Element-resolved `D`** (Section 9.5): the same linear map applied to
  `traces.json` `per_ion_eV`, summed over the ions of each species. That gives
  `D_free` and the constrained `D` by species. Their sum over species equals the
  total, which a test checks.
- **Parity residuals** (Section 9.4): `norm(T(q) + T(-q))` per pair, copied from
  the `traces.json` P0 values. A common background cancels in `y`, so the fit
  cannot see it.

## Predictions (Section 10.1)

```python
tensors.predict(D, A) -> dict      # Gamma, eigenvalues, n_star, degeneracy, q_star, q_star_frac, e_star, pitch
```

- `Gamma = D A^-1 D^T`. `n*` is the top eigenvector. `q* = -A^-1 D^T n* / 2`,
  `e* = -gamma_max / 4` and `lambda = 2 pi / |q*|`, in Å and nm.
- **Degeneracy.** When the top eigenvalue is repeated to `1e-9` relative, as in
  the polar case, `n*` is a subspace. The output gives its dimension and an
  orthonormal basis. Within that subspace, `|q*|`, `e*` and `lambda` are the same,
  so they are still reported.
- **`D = 0`** (`p_D = 0`, or every `d_l` at zero): no spiral. `q* = 0` and
  `lambda` is `null`.
- **Uncertainty.** `gamma_max`, `e*`, `|q*|` and `lambda` are propagated to first
  order with a central-difference Jacobian in the parameters `(d_l, a_l)`. `D`
  and `A` come from independent data (`T` and `E`), so their covariance is block
  diagonal. A perturbation within the allowed basis keeps any symmetry
  degeneracy, so the derivatives exist. No uncertainty is given for `n*`.
- When `sigma(gamma_max) / gamma_max > 0.3`, the output carries
  `"pitch_poorly_determined": true`, and `dmi fit` prints a warning. That is
  where first-order propagation stops being reliable.
- Predictions use the constrained `D` and `A`, and only when `A` is positive
  definite.
- **`D_sw = 4A / M`** (Eq 10.2) applies to ferromagnets only, meaning every
  seed sign is `+1`. `M` is the mean `|M_int|` over the magnetic sites of `q0`,
  from `collected.json`, in μB. The output is a matrix in meV Å², with its
  uncertainty propagated from `A`. For any other pattern it is `null`, with the
  reason.

## T_y provisional

Until `dump_C_y` passes T3, the CSO flip-block order is unpinned (TEN-04). If it
is wrong, every `T_y` flips sign, and so does row `y` (the spin axis) of
`D_free`: `D_free -> M D_free` with `M = diag(1, -1, 1)`. `tensors.json` reports:

- `T_y`, copied from `traces.json`: `confirmed by T3` or `provisional`.
- `F_flipped_norm`: when `y_flip_visible_in_F` is true, the norm of `F` for
  the fit with every `T_y` reversed. If it is much smaller than `norm(F)`, the
  data favour the other flip-block order before T3 runs.
- `y_flip_visible_in_F`: true when the allowed form is not closed under the
  flip, which means `(I - P_D)[M B_l]` is nonzero for some `l`. A wrong order
  then shows up as a large `F`. This holds for every nonzero row of the
  Section 7.4 table: `D I`, `D [z]x`, `diag(D_perp, D_perp, D_par)` and
  `D diag(1, -1, 0)`. It is false when the flip maps the allowed space to itself,
  for example a diagonal `D` in a group like `222`. In that case `F` cannot see
  the error, and the sign of `D_yy` is unconfirmed.
- What does not change. If the allowed space is closed under the flip, then
  `D -> M D` and `Gamma -> M Gamma M`. The eigenvalues, `e*`, `q*` and `lambda`
  are unchanged, and only the `y` component of `n*` flips. So the pitch does not
  depend on the flip-block order. When the space is not closed, the flip shows
  up as a failed Forbidden check before any prediction.

The overall sign of `D` is a separate question that no symmetry check sees
(Section 9.2). `tensors.json` carries `"sign": "unanchored until the TEN-07
supercell control"`.

## Checks

| Check | Rule | On failure |
|---|---|---|
| Forbidden (Section 11) | Every `abs(F_ij) <= 3 sigma(F_ij)`; `norm(F)` is reported too | Reported, and `dmi fit` exits 1. `D` and the predictions are still written, marked `forbidden check failed` |
| A positive | Every eigenvalue of `A` `> 0` (Section 9.2) | No predictions. Exits 1. "The pattern is not a local minimum of the exchange energy" |
| Degrees of freedom | Each kept direction has at least 3 complete pairs, so every Eq (9.1) fit has `dof >= 1` | That direction is dropped. See the next row |
| Rank after drops | `spiral.conditions` on the kept directions still has `sigma_D` and `sigma_A >= RANK_FLOOR`, and `Nd >= max(3, p_A)` | Stop with `ValueError` naming the dropped directions |

Guards before any fit (`ValueError`):

| Rule | Failure it stops |
|---|---|
| `traces.json` has `"passed": true`. A T3 that has not run is allowed (TEN-04). There is no override | Fitting traces that failed N0, I0, P0 or E0 |
| The `collected.json` and `traces.json` hashes still match each used run's `OUTCAR`, `OSZICAR` and `COCC.dat` | A tree changed after `collect` or `trace` |
| The rebuilt operations give the `plan.json` group number and kept/dropped counts | Bases from a different symmetry than the plan |
| `N_m`, the lattice and `t` agree across runs and with `plan.json`, and `N_m` equals the seed's site count | Mixed trees |

The hash recheck already exists inline in `gates.check_tree`. It moves into one
helper, `spiral.unchanged(out, name, sha256)`, which `check_tree`,
`prepare_dumps` and `fit` all call. That removes the two existing copies rather
than adding a third.

## dmi fit and tensors.json

`dmi fit DIR` prints `D` (meV Å), `F` and its check, `A` (meV Å²) and its
eigenvalues, `lambda` ± sigma (nm), `n*` (or the degenerate subspace), the `T_y`
status and the sign status. It writes `DIR/tensors.json`:

```json
{"N_m": 2, "V_m_A3": 63.4, "units": {"D": "meV A per magnetic site", "A": "meV A^2 per magnetic site"},
 "directions": [{"q_frac": [...], "s": [...], "t": [...], "v": [...], "c": [...], "kappa": 0.0, "b": 0.0}],
 "sigma2": {"y": 0.0, "g": 0.0, "dof_y": 9, "dof_g": 3},
 "D_free": {"value": [[...]], "sigma": [[...]]}, "F": {"value": [[...]], "sigma": [[...]], "norm": 0.0, "passed": true},
 "D": {"value": [[...]], "sigma": [[...]], "d": [...], "cov_d": [[...]]},
 "A": {"value": [[...]], "sigma": [[...]], "a": [...], "cov_a": [[...]], "eigenvalues": [...], "positive": true},
 "micromagnetic": {"A_pJ_per_m": [[...]], "D_mJ_per_m2": [[...]]},
 "prediction": {"Gamma": [[...]], "eigenvalues": [...], "n_star": [[...]], "degeneracy": 2,
                "q_star": [...], "q_star_frac": [...], "e_star_meV": 0.0, "pitch_nm": 0.0, "sigma_pitch_nm": 0.0},
 "parity_residual_eV": {"d1_t1": 0.0},
 "T_y": "provisional ...", "y_flip_visible_in_F": true, "sign": "unanchored until the TEN-07 supercell control",
 "dropped_directions": [], "passed": true}
```

Rerunning `dmi fit` is safe; it overwrites only `tensors.json`.

## Tests

Three new tests in `tests/test_tensors.py`, for a total of 21:

1. **`test_fits_recover_spin_model_tensors`** (Gate 1, the Section 6 oracle).
   - Bonds are generated by applying each kept operation to seed bonds
     (`r -> R r`, `d -> det(R) R d`). That gives a spin model with the
     crystal's symmetry. Its `D` and `A` come from Eq (6.3), independent of the
     fit code.
   - `y` and `g` come from Eq (6.2) at the plan's directions.
   - For FeGe (`23`) and BFO (`3m`), with `t = 0.005, 0.01, 0.015`, the fits
     recover `D` and `A`, with `F` at roundoff. The `t^5` term is still large
     at `t = 0.09`, so exact recovery uses these small values.
   - The 1/`N_m` and the `/2` of Eq (9.3) are both exercised, because BFO has
     `N_m = 2`.
   - With the real `t = 0.03, 0.06, 0.09` and added noise of known sigma, the
     pooled `sigma2` is within a factor of two and the reported sigmas cover the
     error.
   - Per ion, the per-species `D` sums to the total `D`.
2. **`test_predictions`.** The three Section 10.1 cases:
   - Scalar: `lambda = 4 pi A / |D|`, `e* = -D^2 / 4A`, `q*` parallel to `n*`.
   - Polar: `n*` perpendicular to `p`, a 2-dimensional degeneracy, and
     `lambda = 4 pi A_perp / |D|`.
   - The chain: 18.85 nm for `J = 10` meV, `d = 1` meV, `a = 3` Å.
   - Flipping row `y` of `D` leaves `lambda`, `e*` and `q*` unchanged and flips
     `n*_y`.
   - `y_flip_visible_in_F` is true for `3m` and `-42m` and false for `222`.
3. **`test_fit_command`.** A prepared BFO tree, as in TEN-04. Synthetic
   `collected.json` and `traces.json` hold spin-model `E` and `T`, and the files
   they hash are written so the hash recheck passes.
   - `dmi fit` exits 0, and `tensors.json` has the Eq (6.3) tensors in meV, the
     micromagnetic units from `V_m`, `T_y` copied over, and the sign note.
   - It refuses a failed `traces.json` and a changed `COCC.dat`.
   - Removing one `+q` run's trace drops that direction. The fit then refuses,
     because BFO's two remaining default directions fail the rank conditions.

Injected faults the tests must catch:

- `1/N_m` dropped from `y`;
- the `/2` dropped from `g` or from Eq (9.3);
- `S` built from `q_frac` instead of the unit Cartesian `s`;
- `F` computed with the stiffness projector;
- `q*` with the sign reversed;
- `lambda = pi / |q*|`;
- an unpooled sigma;
- the 1.602 and 16.02 factors swapped;
- the 1.602 and 16.02 factors applied to eV values;
- `N_m` not checked against the seed;
- the `pitch_poorly_determined` threshold removed;
- `D_sw` reported for a non-ferromagnetic pattern;
- `y_flip_visible_in_F` inverted;
- the hash recheck removed;
- the dropped-direction rank recheck removed.

## STATUS reconciliation (in this branch)

- TEN-04: Done, merged in PR #13 (`6aceeea`). Its Established row drops "Not
  yet merged".
- TEN-05: this owner and branch. Next action: TEN-06, the bcc Fe pilot. That is
  the first time `collect`, `dumps`, `trace` and `fit` read VASP output.
- Local software row: 21 tests.

## Done when

- All 21 tests pass, the spin-model tensors are recovered (Gate 1), and every
  injected fault is caught.
- STATUS, CHANGELOG, `docs/seed_file.md` (the `fit` line) and a session log are
  updated.
- The user merges the pull request.

These tests show that the fits and predictions follow Sections 6, 9 and 10 on
spin-model data. Gate 2, the bcc Fe pilot, is the first VASP evidence.

## Decisions (user, 2026-11-09)

1. Refuse unless `traces.json` passed. A T3 that has not run is allowed. There is
   no override.
2. Drop directions with fewer than 3 complete pairs, and recheck the rank.
3. One pooled `sigma2` for `y` and one for `g`, with no cross-axis covariance,
   for now.
4. First-order propagation, with a `pitch_poorly_determined` flag when
   `sigma(gamma_max) / gamma_max > 0.3`.
5. Element-resolved `D` by species from `per_ion_eV`, added now. The
   per-species sum is checked inside an existing test.
6. Report the `F` norm of the fit with every `T_y` reversed whenever
   `y_flip_visible_in_F` is true.
7. Add `D_sw = 4A / M` (Eq 10.2) for ferromagnets only (every sign `+1`), with
   `M` from `q0`'s `M_int`. The rest of Sections 10.2–10.3 waits for TEN-09.

The user also added three rules:

- the 1.602 and 16.02 factors apply to meV values, and applying them to eV
  values is an injected fault;
- exact recovery uses `t = 0.005` to `0.015`, and the noise check uses the
  real `t`;
- `N_m` is checked against the seed's site count in `plan.json`.

The total stays at 21 tests.
