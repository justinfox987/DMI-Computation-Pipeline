# TEN-06 bcc Fe pilot: convergence trees and Gate 2 on fe-k12

Production VASP evidence from the user's Perlmutter runs, recorded 2026-11-17
on branch `fit-1-model-check` (spec: [plans/ten-06-fe-pilot.md](../../plans/ten-06-fe-pilot.md),
"Evidence record"). The diagnostics run after FIT-1, the open question and the
final verdict were added the same day on branch `ten-06-evidence`. The runs of
18 November (a 10x10x10 PBE scan, an LDA control and a BFO scan), the
reviewer's analysis of the cause, the revised open question and the revised
verdict were added on 2026-11-18 on the same branch. The BFO LDA+U result, the
M1 build confirmation and the user's functional decision (D-028) were added on
2026-11-18 on branch `bfo-ev1`.

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
| Patch B executable: build banner, SHA-256 | banner and SHA-256 not supplied; the user confirmed on 2026-11-17 that the build is the 14 September build, so M1 is covered (below) |
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
| 2.2 Dumps | pass | every `dump_P` gave a `COCC.dat` that `fit` traced; C0 passed on the real `dump_C/CSO.dat`, including `h < 0` on every ion. M1: covered; the user confirmed on 2026-11-17 that the build is the 14 September build, on which M1 passed at 5.3e-15 |
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
| Functional: PBE vs LDA | 10x10x10, ENINI 900, ENCUT 1000, t = 0.02, 0.03, 0.05, 0.10, with PBE and with LDA (18 November, below) | PBE: Fit A FAIL, residual +0.0764 meV, bound 0.0419 meV. LDA: Fit A PASS, worst residual 0.00249 meV, bound 0.0173 meV. **LDA removes the misfit** |

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

## 18 November: the cause

Three energies-only trees run by the user on 2026-11-18. The `dmi fit` values
are from the user's output; g is per magnetic site. Identity items (commit,
build, POTCAR hashes, run paths, wall times) are not supplied, as above.

### Run 1: Fe, PBE, 10x10x10

PBE, 10x10x10, ENINI 900, ENCUT 1000, ISMEAR 0, SIGMA 0.05, direction [001].

| t (1/Å) | g (meV) | g/t² (meV Å²) |
|---|---|---|
| 0.02 | 0.3081 | 770.3 |
| 0.03 | 0.5958 | 662.0 |
| 0.05 | 1.3115 | 524.6 |
| 0.10 | 3.8884 | 388.8 |

`dmi fit`: A = 595.7 meV Å²; Fit A FAIL at d1_t2 (t = 0.03), residual
+0.0764 meV, bound 0.0419 meV; sigma_g 1.0e-6 eV; M_int(q0) 2.313 μB,
M_total 2.251 μB.

Both the mesh and the cutoffs differ from the 8x8x8 scan, so the effect of the
higher cutoffs is not separated from that of the mesh. The shape persists: g/t²
still rises as t falls.

### Run 2: Fe, LDA, 10x10x10

The same mesh, cutoffs, smearing and direction as run 1; t = 0.02, 0.03, 0.05,
0.10 1/Å (from the g table). LDA was set by `GGA = CA` on the `PAW_PBE Fe_pv`
POTCAR, at the PBE lattice constant of `materials/fe/POSCAR` (**to confirm**:
the INCAR and POTCAR of this run are not in the record).

| t (1/Å) | g (meV) | g/t² (meV Å²) |
|---|---|---|
| 0.02 | 0.0707 | 176.9 |
| 0.03 | 0.1610 | 178.9 |
| 0.05 | 0.4519 | 180.8 |
| 0.10 | 1.7315 | 173.2 |

`dmi fit`: A = 182.5 meV Å²; Fit A PASS, worst residual 0.00249 meV, bound
0.0173 meV; sigma_g 1.25e-9 eV (4 pairs); M_int(q0) 2.174 μB, M_total
2.144 μB; D_sw = 335.8 meV Å² (4A/M_int) and 340.4 meV Å² (4A/M_total).

Against run 1, the Fit residual is 30 times smaller and the parity noise 800
times smaller. g/t² is flat within 4% from t = 0.02 to 0.10.

### Run 3: BFO, PBE+U, 7x7x7

R3c, 10-atom cell, G-type, PBE+U (**to confirm**: the U values were not
supplied); 7x7x7, ENINI 600, ENCUT 700, ISMEAR 0, SIGMA 0.08. Directions
d1 = [1 1 1] (the polar axis) and d2 = [1 -1 0] (basal). `dmi plan`: group 161,
6 of 6 operations kept, `p_D 1  p_A 2  n_twist 0`.

| Direction | t (1/Å) | g (meV per Fe) | g/t² (meV Å²) |
|---|---|---|---|
| d1 | 0.03 | 0.4332 | 481.4 |
| d1 | 0.06 | 1.1901 | 330.6 |
| d1 | 0.09 | 2.2628 | 279.4 |
| d2 | 0.03 | 0.3653 | 405.9 |
| d2 | 0.06 | 1.0246 | 284.6 |
| d2 | 0.09 | 1.9177 | 236.8 |

`dmi fit`: A eigenvalues 337.7, 337.7, 390.7 meV Å² (the form symmetry
requires); Fit A FAIL at d1_t1, residual +0.0928 meV, bound 0.0234 meV;
sigma_g 2.66e-7 eV (6 pairs). An insulator shows the same misfit as Fe, so it
is not a metal effect.

### Reviewer's analysis

**Model fits.** Least squares of g = c t + A t² (+ B t⁴):

| Data | c (meV Å) | A (meV Å²) | B (meV Å⁴) | Worst residual (meV) |
|---|---|---|---|---|
| Fe 8x8x8, Gaussian 0.05 (7 points) | 16.7 | 192 | -388 | 0.04 |
| Fe 8x8x8, Methfessel-Paxton 0.2 (7 points) | 17.0 | 199 | -451 | 0.08 |
| BFO d1, from t = 0.03 and 0.06 | 9.0 | 180 | — | predicts g(0.09) = 2.268 meV against 2.2628 measured |
| BFO d2 | about 7 | about 165 | — | about 0.06 |

So every PBE scan is a physically sensible quadratic term plus a spurious term
linear in |q|. Fe: 4A/M ≈ 335 meV Å² (experiment about 280 to 314). BFO: the
experimental J = 4.4 meV with S = 5/2 gives about 215 meV Å² (the reviewer's
estimate).

**Explanation.** Confirmed for Fe by run 2, and for BFO by the LDA+U tree of
2026-11-18 ([BFO LDA+U diagnostic](../2026-11-18-bfo-lda-diagnostic/README.md)). The
mechanism is the reviewer's inference: no paper was found that reports this |q|
artifact in spiral energies.

VASP's noncollinear GGA is locally collinear: n_up/down = (n ± |m|)/2, with
gradients of |m| only. Where m changes sign in space (the interstitial of Fe;
between the sublattices of an antiferromagnet), a spiral adds a transverse
component m_perp proportional to q, and grad|m| collapses in a thin layer. With
m_x = γz, the integral of [γ² - (d|m|/dz)²] dz is π γ |m_perp|, linear in |q|.
LDA depends on |m|², which is smooth, and has no such term.

It accounts for:

- the same misfit in a metal and an insulator;
- independence of the k mesh, the smearing and the number of bands;
- small shifts with PREC and the cutoffs, largest at the smallest t, where the
  layer is thinner than the FFT grid spacing;
- no excess at 2.2e-4 1/Å;
- E(q) = E(-q);
- the direction dependence in BFO.

**Literature** (as supplied by the reviewer; not checked in this session):

- arXiv 2608.22464: VASP's locally collinear GGA does "not capture the
  transverse spin gradients".
- arXiv 2110.09897: the direction of m at m = 0 is "ill-defined, causing
  numerical singularities"; "a general cure within the locally collinear
  approach is unknown".
- arXiv cond-mat/0612604 (Peralta, Scuseria, Frisch).
- arXiv 2510.11603: VASP spirals for Fe use LDA, D = 220, smallest q about
  0.2 1/Å.

**Two side findings.**

1. The parity sigma cannot detect SCF non-convergence, because the +q and -q
   runs follow mirror-image iteration paths. The September sample OSZICARs stop
   while the energy still drifts by about 1e-7 eV per step.
2. The VASP wiki's spiral recipe restarts every q from one converged density
   (`ICHARG = 1`); this pipeline starts each run from scratch.

## Open question

Resolved for Fe: the non-quadratic term is an artifact of PBE in VASP's locally
collinear treatment. Confirmed for BFO: the LDA+U two-direction tree passes
Fit A, and its D is clean (Fit D pass) ([BFO LDA+U diagnostic](../2026-11-18-bfo-lda-diagnostic/README.md)). Open: whether D under PBE is
affected (the artifact is even in q). The user has chosen LSDA+U for production
(D-028).

## Verdict

- **Gate 2 machinery: pass** (unchanged). The dumps, the readers, the trace,
  C0 handedness, N0, the null at every q, I0, P0 and E0 pass on real VASP files.
- **A for Fe with LDA at 10x10x10: 182.5 meV Å², Fit A pass.** The absolute
  value is not final: the mesh is not converged, the functional is LDA on a PBE
  POTCAR, and the lattice constant is PBE's.
- **A for Fe with PBE: not usable**, for the reason above (D-027). The Fit
  check (D-026) flags it on every PBE tree.

Not covered by this pilot:

- the trace sign, which needs D ≠ 0 (TEN-07);
- Forbidden, which needs three directions;
- a converged A for Fe.

## Implication for other materials

The 18 November BFO scan shows the misfit in an insulator, so it is not limited
to metals. By the mechanism above, any material where m changes sign in space
can show it under PBE, so FeGe and Mn2RhSn (TEN-08, TEN-09) may be affected
too; this is untested. The Fit check is the guard. The user has chosen LSDA+U
for production (D-028).

## Bugs found by the pilot

- FIX-2: the real Patch B `CSO.dat` has no NELECT line, and `trace_run` crashed
  comparing it with COCC's (PR #23).
- FIT-1: `fit` reported a precise A from data that the series does not
  describe (D-026, this branch).
