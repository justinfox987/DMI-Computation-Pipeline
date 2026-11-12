# Session: SIM-1b, INCAR overrides and the single-solve fit (D-022, D-023)

- Session ID / UTC date: 2026-11-11, 22:55Z
- Agent or human / platform: Claude (Opus 5.5) in Claude Code, WSL
- Task ID and scope: SIM-1b. Covers `plans/simplify-1.md` items 2.5, 2.7, 2.9 (the exchange seed keys) and 2.10, plus three follow-ups from the SIM-1a review.
- Branch: `sim-1b-incar-fit`
- Base commit at session start: `22a0110` (`main`, PR #19 merge)
- Working-tree changes already present: untracked `Claude outputs/` and `materials/fe/{INCAR,KPOINTS,POSCAR,job.sh}`; left alone and not added.
- Related spec / prior session: `plans/simplify-1.md`; [SIM-1a](2026-11-11_2109Z-agent-sim-1a-recompute.md)
- Status: complete

## Work performed

Package: 1,590 -> 1,590 lines. The removals are balanced by the shared design builders, the energies-only path, explicit fewer-direction handling and the override lines. Tests: 14 -> 15, and 973 -> 1,007 lines.

**A. INCAR (D-022).** `spiral.material_incar` returns the user's tags and one `override` line for each owned tag that the INCAR sets differently. The owned tags are the eight fixed tags plus QSPIRAL, MAGMOM and M_CONSTR. `plan` and `prepare` print these lines and continue. `ISMEAR = -4` or `-5` is refused, with the reason.
- Removed: `INCAR_TAGS` and the unseen-tag warning, `SMEARING`, `MIN_SIGMA` and `min_sigma`, the required ENCUT, ENINI, RWIGS, ISMEAR and SIGMA, and the KSPACING rejection.
- `plan` prints ENCUT, ENINI, ISMEAR and SIGMA only when they are set.
- The check that the dumps need the parent's WAVECAR and CHGCAR stays.

**B. Fit (D-023).**
- **Design builders.** `spiral.spiralization_design` and `spiral.stiffness_design` build the single-solve designs: tensor columns plus a cubic nuisance per (direction, axis) for D, and a quartic nuisance per direction for A. `spiral.rank_value` is the smallest singular value of the column-normalized design. `spiral.plan_ranks` replaces `spiral.conditions`.
- **Plan.** `plan` refuses when the constrained-D or A design falls below `RANK_FLOOR`, and reports the D_free value.
- **Chooser.** `choose_directions` scores the tensor columns of the same designs at one magnitude. The full designs would not work as a score: their nuisance columns cap every value (0.266 for D and 0.169 for A with t in ratio 1:2:3), whatever the geometry. With that change, the default BFO set becomes (1-10), (10-1), (111); it was (01-1), (1-1-1), (111). FeGe stays (001), (010), (100).
- **Solve.** `tensors.tensor_fit` is one pseudoinverse solve, with Cov = sigma^2 X^+ X^+T. `tensors.fit_pairs` turns the complete pairs into A, D, D_free and F, the element-resolved D, and the noise. sigma_y is the RMS of [T(q) + T(-q)]/N_m and sigma_g that of [E(q) - E(-q)]/2N_m; both are written to `tensors.json` with their sample counts.
- **Removed:** `fit_directions`, `least_squares`, `propagate`, the closures, `slope_row`, `projector`, the pooled `sigma2`, `MIN_PAIRS`, `POOR_PITCH` and `poorly_determined`.
- **Fewer than three directions:** allowed when the seed gives them explicitly and both designs have full rank. D_free, F and the Forbidden check are then reported as not evaluated.
- **Energies-only:** with no `dump_C` directory, `check_tree` evaluates only E0, and `fit` reports A, its eigenvalues, D_sw and sigma_g, with every trace quantity not evaluated.

**C.** The `exchange_grid` and `rmax` seed keys and the plan's exchange-classes line are removed. `symmetry.exchange_classes`, its test, the twist count and its gate stay.

**D. Follow-ups from the SIM-1a review.**
1. A refused fit writes `tensors.json` as `{"passed": false, "failures": [...]}`, including when it raises.
2. `read_static` refuses a run whose last printed `lambda =` is not 0.
3. `plans/ten-06-fe-pilot.md`: only the status paragraph and the one "After SIM-1" sentence were corrected.

**Tests.**
- `test_seed_and_plan`: rank values, two explicit directions, the exchange keys rejected.
- `test_prepare_writes_paired_f0_inputs`: overrides of MAGMOM and LSPIRAL with printed lines; KSPACING and a missing ENINI accepted; ISMEAR = -5 refused.
- `test_readback`: a nonzero lambda.
- `test_fits_recover_spin_model_tensors`: single solve, sigma_y within a factor of two, coverage, the Forbidden check passing on noisy data, and a 40-draw noise calibration.
- `test_predictions`: the flag assertions are removed.
- `test_command_chain`: smaller t and the default chooser; a refused fit overwrites `tensors.json`; MIN_PAIRS is gone.
- New `test_energies_only_tree`: FeGe, one direction, no dumps.
- `material` and `finish` now take any structure.
- The layout test and the symmetry tests are unchanged.

**Documents:** `docs/seed_file.md`, `README.md`, the `heide_math_v3.md` module map and rules, `plans/simplify-1.md`, `plans/ten-06-fe-pilot.md` (status only), STATUS, CHANGELOG.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `cd "pipeline v3" && .venv/bin/python -m pytest -q` at `22a0110` | PASS, 14 | Baseline |
| Same on this branch | PASS, 15 | Software only |
| B: two-step fit at `22a0110` against `fit_pairs`, same directions and data | max relative difference (to max \|tensor\|): FeGe D_free 2.9e-14, D 4.5e-16, F 2.9e-14, A 2.4e-16; BFO 2.3e-15, 1.9e-16, 2.3e-15, 4.7e-16; noisy BFO 6.7e-15, 3.7e-16, 6.7e-15, 1.5e-15 | Spin models of the fit test; old default directions pinned |
| B: new `dmi fit` on the old command-chain tree (t = 0.005, 0.01, 0.015; old directions) | D_free 9.9e-16, D 1.9e-16, F 9.9e-16, A 8.5e-16 relative; pitch 258.07358254273583 -> 258.07358254273566 nm | Rebuilt in scratch |
| B: sigmas, old pooled -> new parity | FeGe sigma_y 4.9e-15 -> 0, sigma_g 3.2e-16 -> 0; BFO 6.0e-14 -> 0, 2.4e-15 -> 0; noisy BFO (true 1.414e-6) sigma_y 1.592e-6 -> 1.316e-6 (27 samples), sigma_g 4.215e-7 -> 5.870e-7 (9); chain tree 6.0e-14 -> 0, 1.8e-15 -> 0; noisy max sigma(D) 1.37e-5 -> 1.13e-5, max sigma(A) 1.99e-4 -> 2.77e-4 eV units | Noise-free data have exactly zero parity residual |
| Fault injections, each reverted | 9 of 9 caught: tetrahedron rule off; a per-run tag stopping again; lambda check off; no cubic nuisance; sigma_y from the odd part; a refused fit keeping the old `tensors.json`; no energies-only path; sigma instead of sigma^2 in Cov (caught only after adding the calibration check); quartic nuisance as cubic | Scratch edits |
| F: `python -m dmi_pipeline plan materials/fe/seed.toml` | exit 0; group 229 (Im-3m), 96 ops kept; p_D 0, p_A 1, n_twist 0; `ENCUT 550  ISMEAR 0  SIGMA 0.05`; one MAGMOM override line; rank D 1.000, A 0.169, D_free 0.266; directions (001), (010), (100); 19 runs | The user's untracked files, not edited or committed |
| `python -m pyflakes dmi_pipeline tests ../acceptance/m1.py` | No findings | |

Not run: any VASP job.

## Decisions or deviations

No DECISIONS entry. Findings for the user:

- **Forbidden check against truncation.** With D-023, sigma comes from the parity residuals, which are blind to the t^5 truncation that leaks into the linear slopes. The old pooled fit residual included it. On noise-free data the Forbidden check now fails: on the old chain tree, F = 1.03e-8 meV Å with sigma 0, so `dmi fit` exits 1 where it passed before. The test chain uses t = 0.001 to 0.003 for that reason. On real data parity noise usually dominates, but at BFO-scale t the truncation can be comparable. Listed as an unresolved input in STATUS.
- **Effective strictness of `RANK_FLOOR`.** With normalized single-solve designs the largest achievable value is about 0.169 for A with three magnitudes in ratio 1:2:3. A floor of 0.1 therefore asks for roughly 0.6 of the ideal geometry, stricter than before. The planned BFO and Fe sets pass.
- **Math Section 8.2** still says "use at least max(3, p_A) directions". The code now allows fewer explicit directions (item 2.7). The TeX was not edited.
- **RWIGS.** With RWIGS no longer required, a run without it prints no sphere moments. `collect` then reports "OSZICAR has no ion MW_int M_int block".
- **`plans/ten-06-fe-pilot.md`** line 46 still says `plan` requires ENCUT and ENINI. It was left alone, because only the status paragraph and the SIM-1 sentence were in scope.

## Handoff

- Completed work: SIM-1b; SIM-1 is complete pending review.
- Remaining work / blockers: the Forbidden truncation question above; TEN-06 spec approval.
- Next concrete command or action: review and merge `sim-1b-incar-fit`.
- Files another session should read: this log, `STATUS.md`, `plans/ten-06-fe-pilot.md`.
- Last tested commit, if available: the commit carrying this log.
- Uncommitted/unpushed work and where it exists: see the final response of this session.

## Amendment after review, 2026-11-12

The user's review amended D-023. The work is on the same branch, for the same PR #20.

- **Forbidden bound.** `gates.FORBIDDEN_FLOOR = 0.01`. The bound is `3 sigma + 0.01 max|D_free|`, replacing the 1e-9 roundoff floor. The gate reports `ratio_to_D_free`, and `tensors.json` records it under `F`, together with the bound text "sigma covers noise only, the floor covers series truncation".
- **Rank test.**
  - `spiral.geometry_ranks` replaces `plan_ranks`. It uses the tensor columns of the constrained-D, D_free and A designs, one row block per direction with t set aside. `plan`, `fit` and the chooser all use it.
  - `fit_pairs` requires two or more distinct magnitudes in every direction used, and `observables` drops a direction with fewer. The full-design test and its 0.17 cap are gone.
  - `plan` prints "-" for a design with no tensor columns (p_D = 0).
- **Tests (still 15).**
  - The "Forbidden passes" assertions are back on the noise-free models.
  - The command chain is back at t = 0.005, 0.01 and 0.015, with the Forbidden check passing.
  - The injected forbidden part is now 0.05 |D|, which fails; a new 0.005 |D| case passes.
  - The chain test also drops d1 when it is left with one magnitude, and then reports D_free and F as not evaluated, a path that was untested.
- **Documents.** The D-023 amendment, math Sections 9.4 and 11 (an unnumbered display, so no equation number moves), a dated note in the Revision 3.2 paragraph, the agent notes, `seed_file.md`, STATUS (the open item is removed), and CHANGELOG.

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `cd "pipeline v3" && .venv/bin/python -m pytest -q` | PASS, 15 | Software only |
| max\|F\| / max\|D_free\|, noise-free spin models | BFO: 7.2e-8 at t = 0.005-0.015 and 9.34e-5 at t = 0.03-0.09; FeGe: 2.9e-14 and 1.9e-15. All pass | `tests.test_tensors.model_fit` |
| Fault injections, each reverted | 5 of 5 caught: floor back to 1e-9; floor 0.1; a one-magnitude direction kept; D rank on the full design; D_free always evaluated | Scratch edits |
| `python -m dmi_pipeline plan materials/fe/seed.toml` | exit 0; rank D -, A 1.000, D_free 1.000; directions (001), (010), (100); one MAGMOM override line | The user's untracked files |
| Rebuild the math PDF | NOT RUN: no LaTeX engine on this machine (no pdflatex, latexmk, xelatex, lualatex or tectonic in WSL or Windows) | Braces, environments and display delimiters checked by script; not compiled |
