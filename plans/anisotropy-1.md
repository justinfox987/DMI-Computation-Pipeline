# Anisotropy 1 spec: `dmi aniso` and `dmi aniso-fit`

Status: design approved by the user on 2026-11-11, with the decisions at the
end. **Deferred:** build this after the spiralization tensor calculation works on
VASP output. No code is written.

Physics authority: math Revision 3.2, Section 13, with Section 10.3 for the
spiral criterion. Decision record: D-024. This module
shares no VASP state with the spiral workflow. It reuses the seed, the symmetry
module, the POSCAR/INCAR readers, the job-array writer and the `M_int` reader.

## What it computes

The energy of the uniform order parameter as a function of its direction
$\hat m$, with site moments $\varepsilon_a m_a\hat m$:

$$E(\hat m)=E_0+\sum_{\ell=1}^{p}k_\ell\,f_\ell(\hat m).$$

The $f_\ell$ are the polynomials in $\hat m$ of even degree up to `order` that
the kept operations leave unchanged, with constants removed. Even degree is
time reversal, $E(-\hat m)=E(\hat m)$. At `order = 2` this is the traceless
tensor $\hat m^T\mathcal K\hat m$. Energies are per magnetic site.

The basis is built numerically, for any group: average each monomial over the
kept rotations, evaluate on random unit vectors, subtract the mean, and keep the
independent columns by singular values. A prototype gives (run):

| Structure | Kept operations | `p` at order 2 | `p` at order 4 |
|---|---|---|---|
| bcc Fe | 96 | 0 | 1 |
| FeGe | 12 | 0 | 1 |
| BFO | 6 | 1 | 3 |
| Tetragonal FM | 16 | 1 | 3 |
| Orthorhombic FM | 8 | 2 | 5 |
| Triclinic FM | 2 | 5 | 14 |

These match the known counts, and they become the regression table.

## Which runs it chooses

1. **Fit directions:** `p + 1` directions that determine $E_0$ and the $k_\ell$.
   Candidates are the Cartesian axes, every rotation axis and mirror normal of
   the kept operations, their pairwise sums and differences, and 40 fixed
   generic points. A greedy choice maximizes the smallest singular value of the
   design matrix, which must exceed 0.1 (the `RANK_FLOOR` already used for `q`).
2. **One spare direction:** generic, not used to size the fit. Its residual
   exposes terms beyond `order`. In the prototype, an order-2 fit of a 3m
   surface with a $\cos^4\theta$ term misses the spare by exactly that term.
3. **Noise pairs** on the spare $\hat g$, both exactly equal in the ideal case:
   $-\hat g$ (time reversal) and $R\hat g$ for one kept operation with
   $R\hat g\neq\pm\hat g$ (omitted when no such operation exists).

BFO at order 2: $\hat c$, one in-plane axis, the spare and two noise runs, so
5 runs. A cubic magnet needs `order = 4` and also gets 5. `p = 0` at the
requested order writes nothing and says so.

## Inputs written

One directory per run, named `m1` ... `mN`, with the user's POSCAR, KPOINTS and
POTCAR copied unchanged. The INCAR is the material INCAR (D-019) with:

- set by the code: `LNONCOLLINEAR = T`, `LSORBIT = T`, `SAXIS = 0 0 1`,
  `ISYM = -1`, `I_CONSTRAINED_M = 1`, `LAMBDA = 0`, and `MAGMOM` and `M_CONSTR`
  as lab vectors $\varepsilon_a m_a\hat m$;
- removed, with one printed line each: `LSPIRAL`, `QSPIRAL`, `LZEROZ`, `ENINI`
  and any `MAGMOM` in the material INCAR.

`LAMBDA = 0` applies no constraint, so the moments are free to cant. The tags
exist only so that OSZICAR prints `M_int`. Every run starts from scratch, with
no shared CHGCAR or WAVECAR. All other settings, including the mesh and the
convergence, are the user's and are not checked.

`aniso.json` records the seed text, the group, `order`, `p`, the basis as
monomial coefficients, and each run's direction and role. `submit.sh` is the
same Slurm array as `prepare` writes. Nothing is submitted.

## Readback, checks and the fit (`dmi aniso-fit DIR`)

Every run is read fresh each time; no intermediate file is trusted. Per run:
the final `free energy TOTEN`, the last `M_int` block, "EDIFF is reached" and
the timing footer. Then:

| Check | Requirement | What it catches |
|---|---|---|
| A1 Converged | Each run finished and reached `EDIFF` | Unfinished runs |
| A2 Direction held | $\hat L=\sum_a\varepsilon_aM_a/|\cdot|$ within 2° of $\hat m$ | Moments that rotated away |
| A3 Pattern held | Every $\varepsilon_aM_a\cdot\hat m>0$ and $|M_a|$ within 2% across runs | Flipped sites, collapsed moments, another electronic branch |
| A4 Noise floor | Each noise-pair difference below 10% of the energy span; warning above 5% | Branch differences, loose convergence, symmetry-breaking settings |
| A5 Order | Spare residual below 3 times the noise floor; warning above 2 times | Terms beyond `order` |

The fit is one least-squares solve over all passing runs. The noise floor
$\sigma$ is the RMS of the noise-pair differences divided by $\sqrt2$, and the
coefficient errors follow from the same pseudoinverse. A failed A1 to A3 drops
that run; if the rest no longer determine the fit, the command stops. A failed
A4 or A5 still writes the result, marked failed, and exits 1. A warning is
printed and recorded in `anisotropy.json`, and does not change the exit code.

`anisotropy.json` holds, per magnetic site in meV:

- each run: direction, role, `E`, `M_int`, the angle of $\hat L$ from $\hat m$,
  and the net moment (the canting);
- $k_\ell\pm\sigma$ with the basis; at order 2 also $\mathcal K$, its
  eigenvalues and axes;
- the easy and hard directions and the span, from the fitted surface on a
  fine grid;
- for a uniaxial group, $K_c=E_\parallel-E_\perp$ in the document's convention
  ($K_c>0$ easy-plane);
- every check with its value, its threshold and any warning.

## Use by `dmi fit`

`dmi fit DIR --anisotropy ADIR` reads `anisotropy.json`, refuses it unless A1
to A5 passed, and evaluates the fitted surface on the circle normal to $\hat n^*$.
$K_s$ is its maximum minus its minimum, and

$$r^2=\frac{\pi^2}{4}\,\frac{|e^*|}{K_s}.$$

When $\hat n^*$ is degenerate, it reports the range of $r$ over the degenerate
set. Without the flag, `fit` is unchanged.

## Seed

One new optional key, `anisotropy_order`, 2 (default) or 4. `sites`, `signs`,
`moments`, `spacegroup` and `symprec` are reused; `t` is ignored.

## Code and tests

One module, `anisotropy.py`, estimated at 200 lines, plus about 25 in
`__main__.py` and `tensors.py`. Two tests, for a total of 23:

1. the table above, and exact recovery of a known order-4 3m surface from the
   chosen directions;
2. a synthetic tree end to end: a known $\mathcal K$ comes back; then one fault
   each for A2 (rotated moment), A3 (flipped site), A4 (shifted pair) and A5
   (added quartic term) must fail its own check, and a pair shifted by 7% and a
   spare off by 2.5 sigma must each warn and still pass.

## VASP facts the first real tree settles

1. Whether OSZICAR prints `M_int` with `LSORBIT = T`, `I_CONSTRAINED_M = 1`
   and `LAMBDA = 0`, in Cartesian components at `SAXIS = 0 0 1`.
2. Whether moments seeded along $\hat m$ stay within 2° through the SCF.
3. The size of the noise floor against the span, which decides whether the
   user's convergence settings are enough.

Until then every statement here is algebra or a synthetic test.

## Limits

- The force-theorem value, which is what Xu et al. report, is not computed.
  The result includes canting, so the two are not expected to agree.
- From-scratch runs can land on different electronic branches. A3 and A4
  detect that; they do not prevent it.
- The thresholds (2°, 2%, 10% with a warning at 5%, 3 sigma with a warning at
  2 sigma) are first values, to be revised from the first real tree.

## Decisions (user, 2026-11-11)

1. Self-consistent SOC total energies are the one route.
2. The code writes `submit.sh`; the user submits (D-006).
3. Keep five runs for a uniaxial magnet: the fit directions, the spare and both
   noise runs.
4. The thresholds are accepted as starting values, with two warnings added: a
   noise-pair difference above 5% of the span, and a spare residual above
   2 sigma.
5. Build after the spiralization tensor calculation.

## Open when the build starts

1. Whether `dmi fit --anisotropy` is part of this task.
2. Whether the module uses the current readers or the leaner ones of
   `plans/simplify-1.md` items 2.5 and 2.6, depending on what is merged by then.
