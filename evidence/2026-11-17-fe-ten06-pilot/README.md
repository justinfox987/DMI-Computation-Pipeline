# TEN-06 bcc Fe pilot: convergence trees and Gate 2 on fe-k12

Production VASP evidence from the user's Perlmutter runs, recorded 2026-11-17
on branch `fit-1-model-check` (spec: [plans/ten-06-fe-pilot.md](../../plans/ten-06-fe-pilot.md),
"Evidence record").

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
| Settings common to every tree | energies-only trees (no dumps) unless stated; direction [001]; t = 0.05, 0.10, 0.15 1/Å; ISMEAR 0, SIGMA 0.05; NBANDS reduced by the user |
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
(0.03, 0.06, 0.09) was not run.

**24x24x24 diagnostic** (q0 and the plus side only): running. Result: _placeholder,
to be filled from the user's output._

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
- Most likely cause: k sampling of the Fermi surface at small q in a metal.
  **Not established.** The 24x24x24 diagnostic tests it.

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
| 2.7 A and D_sw | fail | the quadratic model does not fit (Fit A would fail, D-026), and the mesh is not converged; 4A/M_total = 775 meV Å² is outside the 200–400 window |
| 2.8 Wall times | not supplied | |

**The two VASP facts (TEN-04).**
1. `LDUMPCOCC` without `LDUMPCPROJ`: `dmi dumps` writes no `LDUMPCPROJ`, and
   every `dump_P` produced a `COCC.dat` that `fit` read. Settled, if the decks
   ran as `dmi dumps` wrote them (the user did not report a hand edit).
2. The `LSORBIT = T` CSO dump accepted `q0`'s `LSPIRAL = T` `CHGCAR` with
   `ICHARG = 11`: `dump_C` produced a `CSO.dat` that passed C0. Settled.

## Verdict

The machinery passes on real VASP files: the dumps, the readers, the trace,
C0 handedness, N0, the null at every q, I0, P0 and E0.

Not covered by this pilot:

- the trace sign, which needs D ≠ 0 (TEN-07);
- Forbidden, which needs three directions;
- M1 for this build, until the user confirms the build;
- the accuracy of A: the model does not fit and the mesh is not converged.

## Bugs found by the pilot

- FIX-2: the real Patch B `CSO.dat` has no NELECT line, and `trace_run` crashed
  comparing it with COCC's (PR #23).
- FIT-1: `fit` reported a precise A from data that the series does not
  describe (D-026, this branch).
