# TEN-06 bcc Fe pilot: convergence trees and Gate 2 on fe-k12

Production VASP evidence from the user's Perlmutter runs, recorded 2026-11-17
on branch `fit-1-model-check` (spec: [plans/ten-06-fe-pilot.md](../../plans/ten-06-fe-pilot.md),
"Evidence record"). The diagnostics run after FIT-1, the open question and the
final verdict were added the same day on branch `ten-06-evidence`.

**This record is partial.** Every number below was reported by the user or by the
reviewer's hand check and transcribed here. None was copied from a JSON file in
this directory. That departs from the spec's rule that no number is typed in by
hand: `plan.json`, `collected.json`, `traces.json`, `tensors.json`, the launch
scripts, `q0/dump_P/COCC.dat`, `dump_C/CSO.dat` and `hashes.txt` are not yet in
the record. Items marked "not supplied" are unknown, not passed.

## Identity

| Item | Value |
|---|---|
| Code commit of the runs | not supplied. The Gate 2 fit ran after FIX-2 (PR #23, `2ceb27f` on `main`) |
| Patch B executable: build banner, SHA-256 | not supplied; the user is to confirm the build (M1, below) |
| POTCAR TITEL and SHA-256 | not supplied for the runs; the committed inputs name `PAW_PBE Fe_pv 02Aug2007` ([POTCAR.spec](../../materials/fe/POTCAR.spec)) |
| Run-tree path on the cluster | not supplied |
| Structure | `materials/fe/POSCAR`: cubic, a = 2.8630354989499160 Å, 2 Fe, N_m = 2 |
| Settings common to every tree | energies-only trees (no dumps) unless stated; direction [001]; t = 0.05, 0.10, 0.15 1/Å; ISMEAR 0, SIGMA 0.05; NBANDS reduced by the user (stated as 40 for the diagnostics after Gate 2) |
| Job resources, wall times | not supplied |

## k series (energies only, A_xx in meV Å²)

Old cutoffs: ENCUT 550, no ENINI.

| Mesh | 5x5x5 | 6x6x6 | 7x7x7 | 8x8x8 |
|---|---|---|---|---|
| A_xx | 346.0 | 424.0 | 469.4 | 442.8 |

New cutoffs: ENINI 600, ENCUT 700. sigma_g from 2.4e-7 to 2.3e-6 eV across these trees.

| Mesh | 8x8x8 | 10x10x10 | 11x11x11 | 12x12x12 (fe-k12) |
|---|---|---|---|---|
| A_xx | 429.0 | 449.6 | 391.5 | 433.0 |

A is not converged: it moves by 5% to 13% between neighbouring meshes, with no
trend. The planned meshes 16, 20 and 24 were not run as full trees. The t series
(0.03, 0.06, 0.09) was not run. An 18x18x18 tree was run after FIT-1
(Diagnostics, below).

**24x24x24 diagnostic** (q0 and the plus side only): result not supplied. The
18x18x18 tree below tested k sampling instead.

## Hand check of fe-k12 (reviewer)

- `|q|` equals the seed t exactly.
- A = 433.04 meV Å² is reproduced from the OUTCAR energies.
- `g/t²` = 519, 355, 282 meV Å² at t = 0.05, 0.10, 0.15; `g ~ t^1.44`. The model
  `g = A t² + b t⁴` does not fit: it misses t = 0.05 by 0.26 meV, about 1000
  sigma_g. FIT-1 adds the check that catches this (D-026); on these energies
  `Fit A` fails with residual +0.258 meV against a bound of 0.064 meV (repository
  test `test_bcc_fe_pilot_tree`, software only).
- Experiment implies A ≈ 150 meV Å² (D_sw ≈ 280 meV Å², M ≈ 2.2 μB). fe-k12 gives
  D_sw = 755 meV Å² (4A/M_int) and 775 meV Å² (4A/M_total).
- Most likely cause at the time: k sampling of the Fermi surface at small q in
  a metal. The 18x18x18 tree (Diagnostics, below) shows it is not the main
  cause.

## Gate 2 on fe-k12 with dumps

`dmi fit` after FIX-2 exited 0. Its output as reported by the user:

```text
C0 pass; per-run |T| <= 2.06e-7 eV on all axes; N0 pass; Null pass (worst
|T| 2.02e-07 eV); P0 and E0 pass on d1_t1..t3; D = 0; F not evaluated (one
direction); sigma_y 6.5e-08 eV (9 samples), sigma_g 2.44e-07 eV (3 samples).
```

This fit ran before FIT-1, so it printed no Fit line.

| Item | Result | Basis |
|---|---|---|
| 2.1 Tree health | pass | `fit` used all three pairs, so `collect` passed every run; `collected.json` not in the record |
| 2.2 Dumps | pass, except M1 | every `dump_P` gave a `COCC.dat` that `fit` traced; C0 passed on the real `dump_C/CSO.dat`, including `h < 0` on every ion. M1 for this build: not evaluated (the user is to confirm the build) |
| 2.3 Null at every q | pass | worst \|T\| 2.02e-7 eV against `N0_FLOOR_EV` 5e-5 eV |
| 2.4 N0, P0, E0, I0 | pass | `fit` output above |
| 2.5 Noise | recorded | sigma_y 6.5e-8 eV (9 samples), sigma_g 2.44e-7 eV (3 samples) |
| 2.6 D = 0, Forbidden | D = 0 (`p_D = 0`); Forbidden not evaluated | one direction does not determine D_free; needs three |
| 2.7 A and D_sw | fail | the quadratic model does not fit (Fit A would fail, D-026; it fails on every tree run after FIT-1), and the mesh is not converged; 4A/M_total = 775 meV Å² is outside the 200–400 window |
| 2.8 Wall times | not supplied | |

**The two VASP facts (TEN-04).**
1. `LDUMPCOCC` without `LDUMPCPROJ`: `dmi dumps` writes no `LDUMPCPROJ`, and
   every `dump_P` produced a `COCC.dat` that `fit` read. Settled, if the decks
   ran as `dmi dumps` wrote them (the user did not report a hand edit).
2. The `LSORBIT = T` CSO dump accepted `q0`'s `LSPIRAL = T` `CHGCAR` with
   `ICHARG = 11`: `dump_C` produced a `CSO.dat` that passed C0. Settled.

## Diagnostics after Gate 2

Run by the user after FIT-1, so every `dmi fit` below printed a Fit line.
Settings unless stated: ENINI 600, ENCUT 700, NBANDS 40, PREC Normal, ISMEAR 0,
SIGMA 0.05, energies-only trees, t = 0.05, 0.10, 0.15 1/Å. The `dmi fit`
values are from the user's output, and the comparisons and model fits are the
reviewer's hand calculations from them. Compare fe-k12 (12x12x12, PREC Normal):
A 433.0 meV Å², Fit A residual +0.258 meV at d1_t1, bound 0.0641 meV,
sigma_g 2.44e-7 eV.

| Hypothesis | Run | Outcome |
|---|---|---|
| k mesh | 8x8x8 to 12x12x12 (k series, above); 18x18x18, PREC Normal | 18x18x18: A 410.2 meV Å²; Fit A FAIL at d1_t1, residual +0.225 meV, bound 0.0688 meV; sigma_g 1.95e-6 eV; M_int(q0) 2.288 μB. Against fe-k12, 3.4x the k points moved A by -5% and the residual by -13%. The misfit persists: **not mainly a k-sampling effect** |
| FFT precision | PREC Accurate, 12x12x12 | A 410.9 meV Å²; Fit A FAIL at d1_t1, residual +0.235 meV, bound 0.0683 meV; sigma_g 1.9e-6 eV. Against fe-k12 (PREC Normal): A -5%, residual -9%. **Misfit persists** |
| Spiral cutoffs | 8x8x8 at ENCUT 550 (no ENINI) and at ENINI 600, ENCUT 700 (k series, above) | A 442.8 and 429.0 meV Å² (-3%). The residuals at the old cutoffs are not supplied: those fits ran before FIT-1 |
| A jump at q = 0 | fe-k12 settings, QSPIRAL = 0 0 0.0001 (\|q\| ≈ 2.2e-4 1/Å) | free energy -16.53056495 eV against q0's -16.53056019 eV, a difference of -4.8 μeV. A jump at q = 0 would have given about +0.9 meV per cell. **No jump** |
| Empty bands | fe-k12 q0 and d1_t3_plus, NBANDS 40 | the largest top-band occupation is 0 at every k point. **Enough empty bands** |
| Smearing width and scheme | the seven-point t scan at 8x8x8 with ISMEAR 0, SIGMA 0.05 and with ISMEAR 1 (Methfessel-Paxton), SIGMA 0.2 (tables below) | a 4x wider smearing in a different scheme leaves the shape nearly unchanged: g/t² still rises from about 215 to 855 meV Å² as t falls, and only the smallest-t point moved (956 to 855). **The smearing does not set the crossover** |

The trees after FIT-1 report sigma_g of about 2e-6 eV, against 2.44e-7 eV on
fe-k12; the bounds are set by the 1% floor, not by sigma_g.

### Seven-point t scan, 8x8x8, ISMEAR 0, SIGMA 0.05

t = 0.02, 0.03, 0.05, 0.10, 0.15, 0.20, 0.30 1/Å (15 runs). g per magnetic site.

| t (1/Å) | g (meV) | g/t² (meV Å²) |
|---|---|---|
| 0.02 | 0.3823 | 955.7 |
| 0.03 | 0.6392 | 710.2 |
| 0.05 | 1.2931 | 517.2 |
| 0.10 | 3.5841 | 358.4 |
| 0.15 | 6.6196 | 294.2 |
| 0.20 | 10.3554 | 258.9 |
| 0.30 | 19.1003 | 212.2 |

Local exponent n in g ~ tⁿ between successive points: 1.27, 1.38, 1.47, 1.51,
1.56, 1.51 (2 for a quadratic dispersion).

`dmi fit`: A = 314.4 meV Å²; Fit A FAIL at d1_t4 (t = 0.10), residual
+0.555 meV, bound 0.197 meV; sigma_g 2.11e-6 eV; M_int(q0) 2.327 μB.

Reviewer's model comparison (least squares on g, worst residual):

| Model | Worst residual (meV) | A (meV Å²) |
|---|---|---|
| A t² + B t⁴ | 0.55 | 314 |
| c + A t² + B t⁴ | 0.31 | 288 |
| c\|t\| + A t² + B t⁴ | 0.04 | 192 (4A/M ≈ 330 meV Å²) |

The \|t\| model fits best, but it is an empirical description, not a result.

### Seven-point t scan, 8x8x8, ISMEAR 1 (Methfessel-Paxton), SIGMA 0.2

| t (1/Å) | g (meV) | g/t² (meV Å²) |
|---|---|---|
| 0.02 | 0.3421 | 855.3 |
| 0.03 | 0.6426 | 714.0 |
| 0.05 | 1.3660 | 546.4 |
| 0.10 | 3.6883 | 368.8 |
| 0.15 | 6.8092 | 302.6 |
| 0.20 | 10.6245 | 265.6 |
| 0.30 | 19.3721 | 215.2 |

Local exponents: 1.55, 1.48, 1.43, 1.51, 1.55, 1.48.

`dmi fit`: A = 324.5 meV Å²; Fit A FAIL at d1_t4 (t = 0.10), residual
+0.565 meV, bound 0.199 meV; sigma_g 1.9e-6 eV; M_int(q0) 2.306 μB,
M_total 2.239 μB.

Reviewer's model comparison (worst residual):

| Model | Worst residual (meV) | A (meV Å²) |
|---|---|---|
| A t² + B t⁴ | 0.57 | 325 |
| c + A t² + B t⁴ | 0.32 | 298 |
| c\|t\| + A t² + B t⁴ | 0.08 | 199 |

## Open question

g/t² rises without levelling off as t falls from 0.30 to 0.02 1/Å, and g grows
with an exponent near 1.3 at the smallest t. The excess over a quadratic is
independent of the k mesh, the FFT precision, the spiral cutoffs, the number
of bands and the smearing, and it is absent at 2.2e-4 1/Å (no jump at q = 0).
For the cutoffs the evidence is A only, at 8x8x8; the residuals at the old
cutoffs were not recorded.

The cause is not identified. One untested physical candidate is non-analytic
structure of E(q) at small q in a metal with exchange-split Fermi surfaces.
This has not been checked against the literature.

## Verdict

- **Gate 2 machinery: pass** (unchanged). The dumps, the readers, the trace,
  C0 handedness, N0, the null at every q, I0, P0 and E0 pass on real VASP files.
- **A for Fe: non-quadratic over the accessible q range; not understood; not
  usable.** The Fit check (D-026) flags it on every tree.
- The Fe investigation is closed by the user's decision of 2026-11-17. Next is
  TEN-07 (BFO, an insulator), where the Fit check shows directly whether E(q)
  is quadratic.

Not covered by this pilot:

- the trace sign, which needs D ≠ 0 (TEN-07);
- Forbidden, which needs three directions;
- M1 for this build, until the user confirms the build;
- A for Fe (above).

## Implication for metals

FeGe and Mn2RhSn (TEN-08, TEN-09) are metals, so the quadratic model may fail
there too. The Fit check is the guard, and the t range and the settings need
care.

## Bugs found by the pilot

- FIX-2: the real Patch B `CSO.dat` has no NELECT line, and `trace_run` crashed
  comparing it with COCC's (PR #23).
- FIT-1: `fit` reported a precise A from data that the series does not
  describe (D-026, this branch).
