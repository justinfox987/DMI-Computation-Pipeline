# BFO LDA+U diagnostic: two directions, energies and dumps

Production VASP evidence from the user's Perlmutter run of 2026-11-18, recorded
on branch `bfo-ev1`. It tests whether the PBE |q| artifact (D-027) explains the
BFO Fit A failure. It is a diagnostic, not the TEN-07 production tree: the
setup carries over the PBE+U choices and swaps only the functional (below).

**Source of the numbers.** The user will add the tree's reports to this folder:

| File | In the record |
|---|---|
| `tensors.json` | not yet |
| `traces.json` | not yet |
| `collected.json` | not yet |
| `plan.json` | not yet |
| `fit.log` | not yet |

Until they arrive, every number below is from the user's report of the run, or
the reviewer's hand check and conversions, transcribed by hand. When
`tensors.json` is added, it is the authority, and any number here that differs
is corrected from it.

## Setup

| Item | Value |
|---|---|
| Structure | BFO R3c, 10-atom rhombohedral cell, G-type; the PBE+U structure. V_m = 63.329 Å³ per Fe |
| Functional | LDA, set by `GGA = CA` on the PBE POTCARs (confirmed by the user, 2026-11-23) |
| DFT+U | `LDAUTYPE = 1` (Liechtenstein), `LDAUL = 2 1 1`, `LDAUU = 5.2 0.8 9.7`, `LDAUJ = 0.4 0.8 1.9`, in POSCAR species order Fe, Bi, O (confirmed by the user, 2026-11-23). Carried over unchanged from the PBE+U setup |
| Mesh, cutoffs, smearing | 7x7x7 Gamma-centred; ENINI 600, ENCUT 700; ISMEAR 0, SIGMA 0.08 |
| Directions (q_frac) | d1 = [1 1 1] (Cartesian -z, the polar axis); d2 = [1 -1 0] (basal) |
| t | 0.03, 0.06, 0.09 1/Å |
| Runs | 13 SCFs (q0 and six pairs), 14 dumps (13 `dump_P` and `dump_C`) |
| Code commit, Patch B build, POTCAR TITEL and SHA-256, run paths, wall times | not supplied. The user confirmed on 2026-11-17 that the build is the 14 September build |

A note on the species order (not a confirmation): the September BFO inputs in
`pipeline v3/noq/ref/` list `Fe Bi O` in the POSCAR, set the same three LDAU
lines in the INCAR, and give 63.329 Å³ per Fe. Their POTCARs are
`PAW_PBE Fe 06Sep2000`, `PAW_PBE Bi_d 06Sep2000` and `PAW_PBE O 08Apr2002`. Whether
this tree used the same files is not recorded.

## Results

`dmi fit` exited 0 with `passed = true`.

**Checks.** C0 pass; N0 pass; P0 and E0 pass on all six pairs; the null at
every q is not applicable (R3c has no inversion).

**Stiffness A** (per Fe):

| | Basal | Basal | Axis |
|---|---|---|---|
| A eigenvalue (meV Å²) | 141.02 | 141.02 | 155.04 |
| A / V_m (pJ/m) | 3.567 | 3.567 | 3.922 |

Fit A pass, worst residual 0.00513 meV (d1_t1) of bound 0.01315 meV;
sigma_g 3.23e-9 eV (6 pairs).

The same tree with PBE+U ([Fe pilot record](../2026-11-17-fe-ten06-pilot/README.md),
run 3): 337.7, 337.7, 390.7 meV Å²; Fit A FAIL, 0.0928 meV against a bound of
0.0234 meV; sigma_g 2.66e-7 eV. LDA+U removes the misfit, and sigma_g falls by
a factor of about 80.

**Spiralization D** (per Fe): antisymmetric, D_yx = -D_xy = 2.3446 ± 0.0010
meV Å, every other component zero; D / V_m = 0.5931 mJ/m². Fit D pass, worst
residual 2.2e-4 meV (d1_t2, z) of bound 3.85e-3 meV; sigma_y 8.12e-8 eV
(18 samples).

**Traces.** Along the axis direction, |T| ≤ 3.0e-7 eV on every axis. Along the
basal direction, |T| is 1.2e-4 to 3.6e-4 eV, odd in q to four digits, with
magnitudes in the ratio 1 : 1.99 : 2.96 for t = 0.03 : 0.06 : 0.09.

**D by species** (on-site approximation):

| Species | D_yx (meV Å) | Share |
|---|---|---|
| Fe | 2.5425 | 108.4% |
| Bi | -0.1248 | -5.3% |
| O | -0.0731 | -3.1% |
| Sum | 2.3446 | 100% |

**Prediction.** A cycloid: n* perpendicular to q and to the polar axis, with a
basal degeneracy of 2. Pitch 75.58 nm (experiment 62 to 64 nm), |q*| =
0.008313 1/Å, e* = -9.745e-3 meV per Fe. The ±0.03 nm on the pitch is SCF noise
only.

**Not evaluated.** D_free and the forbidden part F: two directions do not
determine D_free.

## Reviewer's hand check

d2_t1 gives |y| = 0.1405 meV, so D = |y| / 2t = 2.34 meV Å, as `fit` reports.

Arithmetic checked in this session from the numbers above: A / V_m and D / V_m
reproduce the SI values; |q*| = D / 2A_basal, e* = -D² / 4A_basal and the pitch
2π/|q*| reproduce the prediction; the species shares sum to D.

## What this run does not establish

- **The overall sign of D.** The Forbidden check cannot see it, and the sign
  anchor is the supercell control (TEN-07b).
- **The Forbidden check.** It needs three directions (TEN-07 Stage A).
- **Mesh convergence of D** (and of A). One mesh was run (TEN-07 Stage B).
- **Production values.** This is a diagnostic setup: PBE POTCARs with the LDA
  functional, and U and the structure carried over from PBE+U. The production
  inputs are the user's (D-028).

What it does establish: the BFO Fit A failure under PBE+U is the D-027 artifact
(the same tree passes Fit A under LDA+U), and D under LDA+U fits the series
cleanly (Fit D pass). Whether D under PBE is affected stays open.

## Literature comparison (reviewer's conversions)

These are the reviewer's conversions to A per Fe. The neutron and
Landau-Ginzburg figures are quoted from the reviewer's recollection and have
not been checked.

| Source | Reported | A (meV Å² per Fe) |
|---|---|---|
| Xu et al., PRB 103, 214423 (2021), FLEUR, R3c | J_eff = -16.16 meV; A = \|J_eff\| a² / 2 with a = 3.96 Å | about 127 |
| Neutron scattering | J = 4.38 meV, J' = 0.15 meV, S = 5/2 | about 185 |
| Landau-Ginzburg | 3e-7 erg/cm | about 117 |

This diagnostic gives 141.02 (basal) and 155.04 (axis) meV Å².
