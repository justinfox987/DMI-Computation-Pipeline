# TEN-07b: BFO supercell sign control

Production VASP evidence from the user's Perlmutter runs, collected on
2026-11-23 and recorded on branch `rec-1`. Record of what was done:
[plans/ten-07b-supercell.md](../../plans/ten-07b-supercell.md). The runs were
made without a prior spec. Pipeline commit and collection time:
[`../2026-11-20-bfo-ten07/provenance.txt`](../2026-11-20-bfo-ten07/provenance.txt).

**Purpose.** To check the overall sign of D (D-020) with an independent route:
self-consistent SOC energies of the two rotation senses of a commensurate spiral.

**Status: D-020's sign confirmed** (2026-11-23, recorded on branch `sign-1`).
The first-order trace of the pipeline pair at this q gives y_x = +1.266 meV per
Fe. The self-consistent SOC supercell gives +1.2659 meV per Fe: the same sign,
and agreement within the four printed digits (below).

## Contents

| Folder | Contents |
|---|---|
| `supercell/plus/`, `supercell/minus/` | INCAR, KPOINTS, POSCAR, `POTCAR.info`, the full OSZICAR, and `OUTCAR.summary` (energy, build line, k points and bands, wall time) |
| `supercell_pair/` | the pipeline pair at the same q: `inputs/` (INCAR, KPOINTS, POSCAR, `POTCAR.info`, `seed.toml`), `plan.json`, `runs.txt`, `collected.json`, `job_resources.txt`, `walltimes.txt`; `traces.json` and `fit.log` are to be added by the user |

## The supercell runs

| Item | Value |
|---|---|
| Cell | 4x1x1 of the primitive cell (4 a1, a2, a3), 40 atoms, 8 Fe; 506.63 Å³, 63.329 Å³ per Fe |
| Spiral | q_frac = (1/4, 0, 0) of the primitive cell, \|q\| = 0.342876 1/Å along (0, -0.945, -0.327), so 94.5% basal |
| Spins | in the y-z plane, rotation axis n = +x; phase 2π q_frac · τ per Fe |
| Plus and minus | differ only in the sense of rotation (MAGMOM and M_CONSTR mirrored in z; the same POSCAR) |
| Settings | `LSORBIT = T`, self-consistent; 2x8x8 k points; NBANDS 384; the U, J and LDA datasets of TEN-07 Stage A; ENCUT 700, EDIFF 1E-07; restarted with `ISTART = 1`, `ICHARG = 1` |
| Constraint | `I_CONSTRAINED_M = 1`, `LAMBDA = 2` |
| Build line | `vasp.6.4.2 20Jul23 (build Sep 14 2026 08:43:24)` |
| Wall time | 597 s (plus), 584 s (minus) |

**Cutoff mismatch.** The supercell ran at ENCUT 700, while the spirals'
effective cutoff is ENINI 600. The two routes therefore differ in cutoff as
well as in method.

## Result

| | E_plus (eV) | E_minus (eV) | E_plus - E_minus |
|---|---|---|---|
| Constrained (LAMBDA = 2) | -121.18019908 | -121.19032603 | +10.127 meV = +1.2659 meV per Fe |
| Unconstrained | — | — | +10.124 meV (user-reported; files not in this record) |

The penalty energies are E_p = 1.1e-7 eV (plus) and 0.8e-7 eV (minus), from the
OSZICARs. **The minus sense is lower.**

## Comparison

- **Small-q tensor (TEN-07 Stage A).** For this q and n, Stage A gives
  E_plus - E_minus = 2 |n · D · q| = +1.40 meV per Fe, with
  q_y = -0.324 1/Å and D_yx = 2.1623 meV Å. That is the same sign as the
  supercell's +1.2659 meV per Fe. This q is far outside the linear range, so
  the magnitudes are not expected to agree.
- **The pipeline pair at the same q** (`supercell_pair/`): 8x8x8,
  `QSPIRAL = 0.249999965 0 0` (run d3_t3, seed t = 0.03, 0.07, 0.342876;
  EDIFF 1E-07). Energies: g = 14.257 meV per Fe, M_int 4.297 μB.
  - **Traces** (`dmi fit` on the pair, the user's run of 2026-11-23; the
    same U, J and datasets as the supercell):

    ```text
    q0          T = +4.638e-09 +9.134e-09 -2.145e-07 eV
    d3_t3_plus  T = +1.266e-03 -1.809e-08 -6.389e-07 eV
    d3_t3_minus T = -1.266e-03 +1.651e-08 +2.923e-07 eV
    ```

  - **y_x = [T_x(q) - T_x(-q)] / 2 = +1.266 meV per Fe**, from the printed
    four-digit values. The pair's `traces.json` and `fit.log` will be added to
    `supercell_pair/` by the user; they were not present when this was
    recorded, so the unrounded value is not yet in the record.
- **Verdict: D-020's sign is confirmed.** The first-order trace reproduces the
  full-SOC chirality energy at this q:

  | Route | Value (meV per Fe) |
  |---|---|
  | Pipeline pair, y_x | +1.266 |
  | Supercell, (E_plus - E_minus) / 8 | +1.2659 |

  Same sign, and agreement within the four printed digits.

  Limits:

  - One q and one rotation axis.
  - SOC is on-site in both calculations, so the on-site approximation itself is
    not tested.
  - The cutoffs differ: 700 eV in the supercell against an effective 600 eV
    (ENINI) in the spirals.
