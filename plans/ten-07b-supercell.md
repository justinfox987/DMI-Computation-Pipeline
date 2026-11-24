# TEN-07b: BFO supercell sign control (record of what was done)

**Status: a record, not an approved spec.** The runs were made by the user
without a prior spec; this file, written on 2026-11-23 on branch `rec-1`,
records what was done. Evidence:
[`evidence/2026-11-23-bfo-supercell/README.md`](../evidence/2026-11-23-bfo-supercell/README.md).

## Why

TEN-07's D-020 sign anchor. The trace route takes its sign from VASP's own SOC
energy (D-020). An independent check is the self-consistent SOC energy of the
two rotation senses of a commensurate spiral. The control was planned as
strained CrSb; it was done on BFO itself, with the TEN-07 Stage A settings.

## What was run

1. **Supercell pair.** A 4x1x1 cell of the primitive BFO cell (40 atoms, 8 Fe).
   A spiral with q_frac = (1/4, 0, 0) (|q| = 0.342876 1/Å, 94.5% basal) and
   spins in the y-z plane (n = +x), with phases 2π q_frac · τ. Two senses,
   plus and minus.
   - Settings: `LSORBIT = T`, self-consistent; 2x8x8; NBANDS 384; Stage A's U,
     J and LDA datasets; ENCUT 700; EDIFF 1E-07.
   - Run constrained (`I_CONSTRAINED_M = 1`, `LAMBDA = 2`) and unconstrained.
2. **Pipeline pair at the same q.** `dmi prepare` with the Stage A seed and t =
   0.03, 0.07, 0.342876, of which only q0 and d3_t3 (the same q) were run at
   8x8x8. Dumps are to be traced with `dmi fit`.

## Pass criterion (as intended)

The sign of the supercell's E_plus - E_minus must match the sign the pipeline
gives for the same q and n, from the traced y at d3_t3 and from the small-q
tensor. The magnitude is not a pass criterion: this q is far outside the linear
range.

## Known differences between the routes

- **Cutoff.** ENCUT 700 in the supercell; the spirals' effective cutoff is
  ENINI 600.
- **Mesh.** 2x8x8 on the 4x1x1 cell against 8x8x8 on the primitive cell.
- **Order in SOC.** The supercell is self-consistent in SOC; the pipeline is
  first order.

## Result

- **Supercell:** E_plus - E_minus = +1.2659 meV per Fe (constrained); the
  unconstrained difference was +10.124 meV per cell, user-reported. The minus
  sense is lower.
- **Small-q tensor:** +1.40 meV per Fe, the same sign.
- **Pipeline pair:** g = 14.257 meV per Fe; y_x = [T_x(q) - T_x(-q)] / 2 =
  +1.266 meV per Fe (`dmi fit`, 2026-11-23).
- **Verdict (2026-11-23): D-020's sign is confirmed.** The first-order trace
  reproduces the full-SOC chirality energy at this q (+1.266 against +1.2659
  meV per Fe: the same sign, and agreement within the four printed digits).
  Limits:

- One q and one rotation axis.
- SOC is on-site in both calculations, so the on-site approximation itself is
  not tested.
- The cutoffs differ: 700 eV in the supercell against an effective 600 eV
  (ENINI) in the spirals.
