# TEN-07: BFO with LSDA+U, Stages A to C (Gate 3)

Production VASP evidence from the user's Perlmutter runs, collected on
2026-11-23 (`provenance.txt`) and recorded on branch `rec-1`. Spec:
[plans/ten-07-bfo.md](../../plans/ten-07-bfo.md). The numbers below are read
from the JSON reports in this folder, or recomputed from them, and were checked
by the reviewer. The reviewer's estimates are labelled as such.

## Contents

| Folder | Contents |
|---|---|
| `stageA/` | `inputs/` (INCAR, KPOINTS, POSCAR, `POTCAR.info`, `seed.toml`), `plan.json`, `runs.txt`, `dumps.txt`, `collected.json`, `traces.json`, `tensors.json`, `fit.log`, `job_resources.txt`, `walltimes.txt` |
| `stageB/`, `stageC/` | `inputs/INCAR`, `inputs/KPOINTS`, `runs.txt`, the reports and the wall times. The POSCAR, `POTCAR.info`, `seed.toml`, `plan.json` and `job_resources.txt` were byte-identical to Stage A's and were removed |
| `provenance.txt` | pipeline commit and collection time |

`stageA/dumps.txt` came from a second copy of the Stage A tree
(`evidence/BFO-initial-tree/`, deleted in this change because it duplicated
stageA and had held a POTCAR).

**KPOINTS correction.** As collected, `stageA/inputs/KPOINTS` read `9 9 9`: the
input folder's KPOINTS had been edited for Stage B before it was copied. Stage A
ran at **8x8x8**, which the user confirmed from the Perlmutter run directories.
The q0 energies agree: Stage A's q0 is -29.31863775 eV, equal to the 8x8x8
supercell pair's q0 (-29.31863777 eV), while Stage B's q0 at 9x9x9 is
-29.31859537 eV. The deleted second copy also had `8 8 8`, and that file is the
one now in `stageA/inputs/KPOINTS`.

## Settings

| Item | Value |
|---|---|
| Functional | LSDA (`GGA = CA`) on the LDA PAW datasets: `PAW Fe 03Mar1998`, `PAW Bi_d 09Feb1998`, `PAW O 31May2000`; SHA-256 `0f9551c6c43f50c1ba5126d4855bf984586a45b79dae0bd32ed2311b9343d0fd` |
| DFT+U | `LDAUTYPE = 1`; U = 5.03, 0.97, 10.15 eV and J = 0.29, 0.30, 1.11 eV (Fe d, Bi p, O p), from the user's linear response with the LDA datasets |
| Cutoffs, smearing, SCF | ENINI 600, ENCUT 700; ISMEAR 0, SIGMA 0.08; EDIFF 5E-07; NBANDS 96 |
| Structure | `materials/bfo/POSCAR` (R3c, 10 atoms, V_m = 63.329 Å³ per Fe) |
| Meshes | Stage A 8x8x8, Stage B 9x9x9, Stage C 8x8x8 (Gamma-centred) |
| Resources | 4 nodes, 16 GPUs per run; about 400 s per SCF, 155 s per `dump_P`, 126 s for `dump_C` (Stage A) |
| Pipeline commit | `138c3c08c431a829be67b251592576a515675379` |
| Build | vasp.6.4.2, 14 September 2026 |

## Stage A: production tree (8x8x8)

Directions d1 = [1 1 1] (axis), d2 = [1 -1 0] (basal), d3 = [1 0 0] (oblique);
t = 0.03, 0.05, 0.07, 0.09, 0.12 1/Å. 31 SCFs and 32 dumps.

**Every check passes:** C0, N0, P0 (15 pairs), E0 (15 pairs), Forbidden, Fit A,
Fit D and Fit D_free. The null at every q is not applicable (no inversion).

| Quantity | Value |
|---|---|
| A eigenvalues (meV Å² per Fe) | 131.19, 131.19 (basal), 151.41 (axis) |
| A / V_m (pJ/m) | 3.319, 3.319, 3.830 |
| D | antisymmetric, D_yx = -D_xy = 2.1623 meV Å per Fe; 0.547 mJ/m² |
| Forbidden | max\|F\| / max\|D_free\| = 0.0032 (pass) |
| Prediction | cycloid, n* degeneracy 2; pitch 76.24 nm; e* = -8.91e-3 meV per Fe |
| D by species (D_yx, meV Å) | Fe 2.4428, Bi -0.1996, O -0.0810 |
| Noise | sigma_g 8.97e-9 eV (15 pairs), sigma_y 1.12e-7 eV (45 samples) |

**Fit residuals of A.** Fit A passes; its worst residual is 0.0184 meV (d1_t1)
against a bound of 0.0214 meV. The residuals, in 1e-3 meV:

| | t = 0.03 | 0.05 | 0.07 | 0.09 | 0.12 |
|---|---|---|---|---|---|
| d1 | 18.4 | 5.9 | -13.9 | 4.8 | -0.1 |
| d2 | 2.5 | 2.8 | -0.2 | -3.2 | 0.9 |
| d3 | 0.1 | -4.9 | 4.7 | -0.2 | -0.3 |

The scatter is 0.0066 meV rms. That is about 700 times the parity sigma_g
(about 740 from these numbers). The parity sigma therefore understates the
energy noise. The realistic uncertainty on A is 1 to 2%, not the quoted
±0.002 meV Å². The same holds for the pitch: its ±0.019 nm is the SCF parity
noise only.

The sign of D follows VASP's SOC energy (D-020). It is supported by the
supercell control, but not yet confirmed
([supercell record](../2026-11-23-bfo-supercell/README.md)).

## Stage B: mesh check of D (9x9x9)

q0 and the basal pair d2_t3 (t = 0.07, not 0.06 as first written in the spec),
with dumps.

| | Stage A (8x8x8) | Stage B (9x9x9) | Change |
|---|---|---|---|
| \|y\| (meV) | 0.30030 | 0.30026 | -0.015% |
| g (meV per Fe) | 0.63692 | 0.62513 | -1.85% |
| Direction of y | | | 0.04° |

These values are recomputed from `traces.json` and `collected.json`. The
reviewer's -0.04% for |y| comes from the four-digit values in `fit.log`.

**Gate 3 (Stage B changes D by less than 5%): PASS.**

`dmi fit` on this trimmed tree prints "fit refused: failed P0 d2, E0 d2", and
`tensors.json` says `passed: false`, although the `fit.log` lines show P0 and
E0 passing on d2_t3. `gates.py` gates P0 and E0 at each direction's `_t1`
pair, and a trimmed tree that has only `d2_t3` has no `d2_t1` entry, which is
counted as a failure. This is a known wart in the message, not a failed check.

## Stage C: U sensitivity (8x8x8)

The Stage B set at 8x8x8, with only Fe U changed (5.03 to 4.00 eV).

| | Stage A (U = 5.03) | Stage C (U = 4.00) | Change |
|---|---|---|---|
| \|y\| (meV) | 0.30030 | 0.43480 | +44.79% |
| g (meV per Fe) | 0.63692 | 0.75743 | +18.92% |
| Direction of y | | | 0.04° |
| M_int (μB) | 4.23 | 4.155 | |

The reviewer's estimate scales Stage A by these two ratios: D about 3.1 meV Å,
A_perp about 156 meV Å², pitch about 62.6 nm. Experiment gives 62 nm.

The limits of this estimate:

- It rests on one pair at one t.
- U = 4 was chosen after seeing the 76 nm pitch.
- The user is re-converging the linear response; the production U is that
  value, not a fit to the pitch (D-029).

## Literature comparison (reviewer's conversions)

| Source | Reported | Converted |
|---|---|---|
| Neutron-fitted spin model | J = 4.38, J' = 0.15, D_u = 0.11 meV | A about 185 meV Å², D about 3.8 meV Å |
| Xu et al. 2021 (FLEUR) | | pitch about 80 nm |
| Four-state DFT | | pitch 83 nm |

This record gives A 131.19 / 151.41 meV Å², D 2.1623 meV Å and a pitch of
76.24 nm at U = 5.03 eV.

## What this record establishes, and what it does not

**Established:**

- On real VASP files, the full Gate 3 check set passes for BFO with LSDA+U.
- D_free obeys the R3c form to 0.3%.
- D changes by less than 0.1% from 8x8x8 to 9x9x9.

**Not established:**

- The overall sign of D: the supercell control is pending its dumps.
- Convergence in t beyond the five magnitudes run.
- The final U (D-029).
- Energy noise at the parity-sigma level: the residual scatter is about 700
  times larger. EDIFF is to be tightened.
