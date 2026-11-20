# TEN-07 spec: BFO production tree with LSDA+U (Gate 3)

**Status: Approved by the user 2026-11-19.** Drafted 2026-11-18 on branch
`bfo-ev1`; approved with the Gate 3 tolerance set to 5%. No code in this task.

Physics authority: `docs/math/heide_math_v3.tex` (Revision 3.2, amended
18 November 2026), Sections 3, 4, 8, 9, 10 and 11. Functional: D-028 (LSDA+U
throughout). Inputs: D-019. Checks: D-023 (Forbidden), D-026 (Fit). Prior
evidence: [BFO LDA+U diagnostic](../evidence/2026-11-18-bfo-lda-diagnostic/README.md).

## Why

The diagnostic of 2026-11-18 passed Fit A and Fit D on two directions, but its
inputs carried over the PBE+U choices, and it could not test Forbidden or mesh
convergence. TEN-07 runs the production set and closes those gaps. The sign of
D is not part of TEN-07: the sign anchor is TEN-07b (below).

## Inputs

The user's LSDA+U production set, committed under `materials/bfo/` as given:
`POSCAR`, `INCAR`, `KPOINTS`, `seed.toml`, and a `POTCAR.spec` with each
dataset's name, TITEL and SHA-256. The POTCARs are never committed. The code and
this spec choose none of the inputs: the potpaw_LDA datasets, U, J and
`LDAUTYPE`, the structure, the cutoffs and the mesh are open until the user
supplies them (D-028). `plan` must report group 161 with 6 of 6 operations kept;
set `spacegroup = 161` in the seed.

## Stage A: production tree

- Seed: `directions = [[1, 1, 1], [1, -1, 0], [1, 0, 0]]`, `t = [0.03, 0.06, 0.09]`.
- 19 SCFs (q0 and nine pairs) and 20 dumps (19 `dump_P` and `dump_C`).
- Pass: C0, N0, I0, P0, E0, Fit A, Fit D and Forbidden, as `dmi fit` reports
  them, with `passed = true`.
- Report, not pass/fail: A, D, D_free, max|F| / max|D_free|, the species split
  and the prediction, each compared with the diagnostic.

Checked in this session with `dmi plan` on a scratch seed (the September BFO
POSCAR from `pipeline v3/noq/ref/`, `signs = [1, -1]`, `spacegroup = 161`):
group 161, 6 of 6 kept, `p_D 1  p_A 2  n_twist 0`; rank D 1.000, A 0.964,
D_free 0.535, all above `RANK_FLOOR = 0.1`; 19 runs including q0. In Cartesian
terms, [1 0 0] is (0, -0.945, -0.327), out of the basal plane, so the three
directions are not coplanar. The production POSCAR must give the same result.

## Stage B: mesh check of D

- q0 and the basal t = 0.06 pair (`d2_t2_plus`, `d2_t2_minus`), with dumps,
  at one denser mesh than Stage A. The mesh is the user's.
- Report the change in y (per axis) and in g at that pair against Stage A.

## Stage C: U sensitivity

- The Stage B set at one other U, chosen by the user.
- A report of the change in y and g, not a pass/fail check.

## Gate 3

Stage A passes, and Stage B changes D by less than 5% (the user's tolerance,
2026-11-19).

## TEN-07b: sign anchor (separate task)

The strained CrSb supercell control confirms the overall sign of D (D-020) and
its magnitude. It gets its own spec.

## Known limit (not a task)

The code writes whole trees only:

- `dmi dumps` writes a `dump_P` for every ok run and cannot write a subset.
- `dmi plan` and `dmi prepare` refuse a seed with fewer than three distinct `t`
  (checked: "Seed t needs at least 3 distinct positive magnitudes"), so the
  three-SCF set of Stages B and C cannot come from a seed either.
- `dmi fit` needs pairs at two or more magnitudes per direction, so it cannot
  fit a single pair.

So Stages B and C need either hand-made decks copied from Stage A's run
directories, with y and g compared outside `fit`, or a full tree at the
denser mesh or other U. **Open for the user:** which of the two (not settled
by the approval of 2026-11-19).

## Evidence record

`evidence/<date>-bfo-ten07/README.md`, with `plan.json`, `collected.json`,
`traces.json`, `tensors.json`, `fit.log`, `POTCAR.spec` and the build identity.
Numbers come from `tensors.json`, not typed in by hand.
