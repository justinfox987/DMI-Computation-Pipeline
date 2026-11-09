# Session: TEN-05 tensors, fits and the spiral prediction

- Session ID / UTC date: 2026-11-09
- Agent or human / platform: Claude Code (Opus 5.5)
- Task ID and scope: TEN-05 per [plans/ten-05-tensors.md](../../plans/ten-05-tensors.md)
- Branch: `ten-05-tensors`
- Base commit at session start: `main` at `6aceeea` (TEN-04 merged in PR #13)
- Working-tree changes already present: none; the approved spec was committed first (`3729c91`)
- Related spec / prior session: [TEN-04 log](2026-11-08_2245Z-agent-ten04-trace.md)
- Status: complete, pending review

## Work performed

- `dmi_pipeline/tensors.py` (new):
  - `least_squares` (the one Section 9 routine) and `propagate` (every linear
    covariance).
  - `pair_observables` (Eqs 1.3, 1.4) and `fit_directions` (Eqs 9.1, 9.9).
  - `spiralization` (Eqs 9.3–9.5, plus `F_flipped_norm`) and `stiffness`
    (Eq 9.6).
  - `by_species` (Section 9.5).
  - `predict` (Eq 10.1) and `prediction_uncertainty` (first order, with the
    poorly-determined flag).
  - `spin_wave_stiffness` (Eq 10.2), `y_flip_visible` and `observables`
    (every input guard).
  - `fit`, which writes `tensors.json`.
- `gates.py`: `gate_forbidden` (Section 11). `check_tree` uses the new helper.
- `spiral.py`: `unchanged(directory, sha256, since)` replaces the two inline
  hash rechecks (in `check_tree` and `prepare_dumps`), and `fit` uses it too.
- `__main__.py`: added the `dmi fit DIR` command.
- `tests/test_tensors.py` (new, 3 tests): the spin-model recovery (Gate 1),
  predictions, and the end-to-end `dmi fit`.
- Docs: STATUS reconciled (TEN-04 merged, TEN-05 in review, TEN-06 next),
  CHANGELOG, and the `fit` line in `seed_file.md`.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `cd "pipeline v3" && .venv/bin/python -m pytest -q` | PASS, 21 passed | Whole suite; only spglib's DeprecationWarning |
| Gate 1: Eq (6.3) spin models for FeGe (23) and BFO (3m) at `t = 0.005–0.015` | `D_free`, `D` and `A` recovered to 1e-6 of max, `F` below 1e-6, the per-species sum equals `D` to 1e-15 | Spin-model data, not VASP |
| Noise check at `t = 0.03–0.09`, sigma 2e-6 eV, fixed seed | pooled `sigma2_y` within a factor of 2; `D` and `A` within 3 sigma | `sigma2_g` has 3 dof, too few for a band; its sigma is checked through `A` coverage instead |
| Fault injection, one at a time, `pytest -x tests/test_tensors.py` | 16 of 16 caught | Every fault in the spec list; `tensors.py` compared with the good copy afterwards |

No VASP or cluster jobs.

## Decisions or deviations

- User decisions 1–7 and rules (a)–(c) are recorded at the end of the spec.
- Test-side corrections during implementation:
  - The expected pitch sigma first left out the 1% error on `A_perp`. The code
    was right: `hypot(0.05, 0.01) λ`.
  - A `sigma2_g` assertion with an escape clause that never ran was removed,
    with the reason noted in the test.
- The `pitch_poorly_determined` flag moved into `prediction_uncertainty`, so a
  test can drive it both ways. Otherwise "threshold removed" could not be
  caught.
- The Forbidden check adds a relative floor of 1e-9 times `max|D_free|`, so
  noise-free data (sigma exactly 0) do not fail on roundoff.
- No new decision record.

## Handoff

- Completed work: everything in the spec's "Done when" except the merge.
- Remaining work / blockers: the TEN-06 spec and the Fe inputs (POSCAR, an INCAR
  with `ISMEAR`, `SIGMA`, `ENINI` and `RWIGS`, and KPOINTS).
- Next concrete command or action: review and merge the TEN-05 PR.
- Files another session should read: `plans/ten-05-tensors.md`, `dmi_pipeline/tensors.py`, `STATUS.md`.
- Last tested commit, if available: the `ten-05-tensors` commit containing this log.
- Uncommitted/unpushed work and where it exists: none after push.

## Addendum: the Forbidden check must still detect a real forbidden part

`test_fits_recover_spin_model_tensors` now also:

- asserts that the Forbidden check passes on every noise-free spin model;
- adds a forbidden component of 1e-3 |D| (`diag(1, 0, 0)`, which is entirely
  outside the 3m form) to noise-free BFO slopes, recovers it as `F`, and asserts
  that the check fails.

Loosening the floor in `gate_forbidden` from `1e-9` to `1e-2 * max|D_free|`
makes that assertion fail (`assert not True`). With the floor restored, the
suite passes (21 passed).
