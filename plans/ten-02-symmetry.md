# TEN-02 spec: symmetry module

Physics authority: `docs/math/heide_math_v3.md`, Section 7. This file fixes the
interfaces, the guards and the tests. It does not restate the equations.

Status: design agreed with the user on 2026-11-04. Nothing here is implemented
yet. The results below came from a scratch prototype that was not committed.

## Scope

Add `pipeline v3/dmi_pipeline/symmetry.py`, about 110 lines, and add
`spglib>=2.6` to `pyproject.toml`. Versions 2.6, 2.7 and 2.8 were checked; 2.5
had no wheel to test.

Move `step1.positions` into `realized.py` as one reader:

```python
poscar(path) -> (lattice, species, tau)   # lattice rows as in POSCAR, in Å
```

It applies the scale factor and accepts Direct positions, with or without
Selective dynamics. It rejects Cartesian positions, a negative scale and a
three-value scale. Update the `step1.py` callers and remove `positions`, so there
is one parser.

Out of scope: any CLI command, the seed loader, and the `q` rank conditions. All
three are TEN-03. See `docs/seed_file.md` for the seed format.

## Interfaces

All functions are array-based and read no files. `sites` here are 0-based. The
seed loader in TEN-03 converts from the 1-based numbers in the seed.

```python
operations(lattice, species, tau, sites, signs, symprec=1e-3, spacegroup=None) -> dict
    # rotations    (g, 3, 3)  kept Cartesian R_g        Eqs (7.1), (7.3)
    # permutations (g, Nm)    pi_g on magnetic sites    Eq (7.2)
    # number, symbol          spglib's group for the crystal
    # total, dropped          operation counts

spiralization_basis(rotations) -> (p_D, 3, 3)   # Eqs (7.6)-(7.7)
stiffness_basis(rotations)     -> (p_A, 3, 3)   # Eqs (7.6)-(7.7)
twist_count(rotations, permutations) -> int     # Eq (7.9)
exchange_classes(lattice, tau, signs, rotations, rmax, tol) -> list[dict]
    # each class: {"sign": e_b, "vectors": (n_b, 3)}, for Eq (7.11)
```

The bases are orthonormal in the Frobenius inner product. TEN-07 gets the
forbidden part from them, so no separate projector is exported.

## Conventions that are easy to get wrong

- `L = lattice.T`, so `R = L @ W @ inv(L)`. spglib takes the POSCAR row matrix.
- Species map to integers with `np.unique(species, return_inverse=True)[1]`.
- Use `spglib.get_symmetry_dataset(cell, symprec=symprec)` and attribute access
  (`.rotations`, `.translations`, `.number`, `.international`). It returned
  `None` on overlapping atoms in spglib 2.8, so raise `ValueError` on `None`. 2.7
  and later emit a harmless `DeprecationWarning` about error handling.
- Site map, with fractional row vectors and `pi[a]` the target of source `a`:

  ```python
  d = tau[sites][:, None] - (tau[sites] @ W.T + t)[None, :]   # [target, source]
  d -= np.rint(d)
  dist = np.linalg.norm(d @ lattice, axis=2)
  pi = dist.argmin(0)
  ```

- Keep test: `abs((signs[pi] * signs).sum()) == len(sites)`. This is Eq (7.3) for
  one global sign.
- Use `kron(R, R)` on row-major vectorized matrices. Include the `det(R)` factor
  for the spiralization basis and omit it for stiffness.
- For the stiffness basis, multiply the projector by the symmetrizer before the
  SVD, so that it acts on symmetric matrices only.
- Rank cutoff is singular value `> 1e-8`. Each `R_g` is an exact matrix conjugate
  of an integer group, so the averages stay exact projectors even on a rounded
  lattice. BFO rounded to 4, 5 and 6 decimals gave zero singular values near
  `1e-16` while `|R^T R - I|` reached `2e-5`.
- Report the reconstructed full matrices only. Basis order and sign are
  arbitrary, so the individual coefficients have no meaning.
- List each undirected bond once: for `a == b`, keep one of `T` and `-T`; for
  `a < b`, keep every `T`. Use `signs[a] * signs[b]` as `e_b`. Bonds with the same
  `r` on inequivalent sublattices share a class by design, as in Section 7.6.

## Guards

All raise `ValueError`.

| Guard | Rule | Failure it stops |
|---|---|---|
| Space group | If `spacegroup` is given, stop when spglib finds another number; report both | Too tight or too loose `symprec`, which otherwise pass silently |
| Orthogonality | `|R^T R - I| < 1e-4` for every operation | Lattice strain hidden by a loose tolerance |
| Site map | `pi` is a bijection and the largest site distance is under `2 * symprec` | A wrong magnetic site list |

`spacegroup` is an optional check, not an override: it cannot force spglib to use
a group. Always return `number`, `symbol`, `total` and `dropped`. `plan` in TEN-03
prints them first, because that line is the only protection from a wrong group
when `spacegroup` is left out.

The cases that motivate the guards, all observed in the prototype:

- Strained zincblende at `c/a = 1.001` with `symprec = 0.01` reads as `F-43m`, with
  `D = 0` instead of `I-4m2`, and `|R^T R - I| = 2e-3`. At `c/a = 1.01` the same
  happens at `symprec = 0.1`.
- BFO with fractional position noise `sigma = 2e-4` reads as `P1` at
  `symprec = 1e-3`, with `p_D = 9`, `p_A = 6`, `n_twist = 3`. It recovers `R3c` at
  `1e-2`. With `sigma = 1e-3` it stays `P1` at `1e-2` and recovers at `3e-2`.
- Marking only one BFO Fe as magnetic passes as `R3c` with 6 operations, and the
  site distance is 6.8 Å. The largest site distance on any accepted noisy
  structure was `0.99 * symprec`.

A `symprec` sensitivity report was tried and dropped. It trips on correct settings
and cannot say which answer is right.

## Test structures

These are test geometries, not relaxed structures.

- bcc Fe: `a = 2.863`. Primitive, and 2-site conventional at `(0,0,0)`,
  `(.5,.5,.5)`.
- fcc: `a = 3.6`, 4-site conventional.
- FeGe B20: `a = 4.70`; Fe `u = .135`, Ge `v = .842`, on
  `(x,x,x)`, `(.5+x,.5-x,-x)`, `(-x,.5+x,.5-x)`, `(.5-x,-x,.5+x)`.
- BFO: rhombohedral `a = 5.54`, `alpha = 59.71 deg`. Bi at `(0,0,0)`, `(.5,.5,.5)`;
  Fe at `(x,x,x)`, `(x+.5,x+.5,x+.5)` with `x = .225`; O at
  `(o1,o2,o3)`, `(o3,o1,o2)`, `(o2,o3,o1)`, and each of
  `(o2,o1,o3)`, `(o3,o2,o1)`, `(o1,o3,o2)` shifted by `.5`, with
  `(o1,o2,o3) = (.541,.939,.394)`.
- Zincblende: `a = 6.0`, `c = 6.3`, conventional with Cr on the fcc sites and Sb
  shifted by `(.25,.25,.25)`, and the 2-atom primitive cell.

## Expected results

These counts all came out of the prototype.

| System | Pattern | Group | Total | Kept | `p_D` | `p_A` | `n_twist` |
|---|---|---|---:|---:|---:|---:|---:|
| bcc Fe primitive | FM | `Im-3m` | 48 | 48 | 0 | 1 | 0 |
| bcc Fe 2-site | FM | `Im-3m` | 96 | 96 | 0 | 1 | 0 |
| bcc Fe 2-site | G-type | `Im-3m` | 96 | 96 | 0 | 1 | 0 |
| fcc 4-site | FM | `Fm-3m` | 192 | 192 | 0 | 1 | 0 |
| fcc 4-site | `+ + - -` | `Fm-3m` | 192 | 64 | 0 | 2 | 0 |
| fcc 4-site | `+ - - -` | `Fm-3m` | 192 | 48 | 0 | 1 | 0 |
| FeGe B20 | FM | `P2_13` | 12 | 12 | 1 | 1 | 1 |
| BFO | G-type | `R3c` | 6 | 6 | 1 | 2 | 0 |
| Strained zincblende | FM | `I-4m2` | see below | all | 1 | 2 | 0 |

The conventional zincblende cell and the primitive cell both give
`D diag(1, -1, 0)` up to sign. The primitive cell has 8 operations. Rotating the
lattice by `Q` rotates the basis projector exactly, to `3e-16`.

BFO keeps all 6 operations because the glide that swaps the Fe sublattices has
`eta = -1`, which Eq (7.3) allows.

## Tests

Add three tests, for a total of 16. Do not add more.

1. **`test_section_7_4_table`.** Build each point group from generators and check
   the table's exact tensor forms: inversion, 23, -43m, 3m, 4mm, 6mm, 622, and
   -42m with 2-fold axes on x and y. Then run strained zincblende end to end from a
   POSCAR written to `tmp_path`, which also covers `poscar`.
2. **`test_patterns_and_twist`.** The fcc patterns, FeGe, BFO, and one case each
   for the three guards.
3. **`test_exchange_classes`.** At `q = (.31, .17, -.09)` with `rmax = 4.1`, bcc Fe
   `Phi_c` per site matches between the primitive and 2-site cells, and G-type
   flips the sign of the nearest-neighbor class only. Shell multiplicities in the
   2-site cell are 8, 6, 12.

## Done when

- All tests pass and the Section 7.4 table is reproduced.
- Injected faults are each caught by a test: drop `det(R)`, invert the
  permutation, use `R` in place of `R.T` in the map, skip the keep test, remove
  each guard, reverse `L`.
- `STATUS.md`, `CHANGELOG.md` and a session log are updated.
- The user merges the pull request.

These tests show the symmetry code is correct. They say nothing about VASP. The
spin-model recovery check is TEN-05, Gate 1.
