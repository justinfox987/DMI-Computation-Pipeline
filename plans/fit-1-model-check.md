# FIT-1: model check in `dmi fit`, and the TEN-06 Fe evidence record

Approved by the user on 2026-11-17. Branch `fit-1-model-check` from `main`
after PR #23.

## Why

The Fe pilot at 12x12x12 (fe-k12: direction [001], t = 0.05, 0.10, 0.15 1/Å)
gave `A = 433 +- 0.04 meV Å²` while `g/t²` was 519, 355 and 282 meV Å². The
fit `g = A t² + b t⁴` misses t = 0.05 by 0.26 meV, about 1000 sigma_g
(2.4e-7 eV). The parity sigma sees SCF noise only, never model error, and
nothing in `fit` flagged the misfit.

## The check ("Fit", math Section 11; D-026)

For each tensor solve (A always; D and D_free when traced), after the solve:

- residual `r = data - design @ x`, in the units of the data;
- bound `3 sigma + 0.01 max|data|`, with that solve's parity sigma (sigma_g for
  A, sigma_y for D and D_free). This has the same form as the Forbidden bound
  (D-023): sigma covers noise, and the 1% floor covers series truncation so that
  noise-free spin-model data pass;
- pass when every `|r_i| <= bound`; on failure name the worst row (the pair,
  and the axis for D), its residual and the bound;
- rows <= columns: "not evaluated: exactly determined", never a pass.

On fe-k12: worst `|r|` = 0.258 meV, bound = 0.001 + 0.063 meV, so it fails by
about 4x.

## Behaviour

As for Forbidden, the solve and the report still happen. `tensors.json` gets a
`fit_check` entry per tensor (worst residual, bound, row, passed, and the residual
vector), and `report["passed"]` is false when any evaluated Fit check fails, so
`dmi fit` exits 1. The printed lines are `Fit A  FAIL: ...` or
`Fit A  pass, worst residual ... of bound ...`. An energies-only tree still gets
the A check.

## Tests (stay at 15)

- The spin-model fits pass the Fit check (existing tensors test).
- `test_bcc_fe_pilot_tree` with the real fe-k12 energies: Fit A fails and names
  d1_t1, A = 433.04 meV Å², and `dmi fit` exits 1.
- Mutation check: disable the failure, and a test must fail.

## Docs

Math Sections 9.4 (parity sigma does not measure model error) and 11 (the Fit
check, unnumbered display), with a Revision 3.2 amendment note; D-026;
`heide_math_v3.md`; `docs/seed_file.md`; CHANGELOG, STATUS, session log.

## TEN-06 evidence record

`evidence/2026-11-17-fe-ten06-pilot/README.md`, as the TEN-06 spec's "Evidence
record" section says, holding the user's convergence trees, the fe-k12 Gate 2
results and verdict, and the pilot's bugs. The TEN-06 convergence plan is
amended to what was run. A 24x24x24 diagnostic is running; its result is a
placeholder.
