# Session: FIX-1, trace sign and smeared FERWE

- Session ID / UTC date: 2026-11-11, 19:46Z
- Agent or human / platform: Claude (Opus 5.5) in Claude Code, WSL
- Task ID and scope: FIX-1, `plans/simplify-1.md` Part 1 (items 1.1 and 1.2; D-020). Also reconciled the stale STATUS lines.
- Branch: `fix-1-trace-sign`
- Base commit at session start: `cf5f9da` (`main`, PR #17 merge)
- Working-tree changes already present: untracked `Claude outputs/` and `materials/fe/{INCAR,KPOINTS,POSCAR,job.sh}`. Left untouched and not added to the branch.
- Related spec / prior session: `plans/simplify-1.md`; [simplify decisions](2026-11-11_1600Z-agent-simplify-decisions.md)
- Status: complete

## Work performed

- `pipeline v3/dmi_pipeline/trace.py`: `trace_vector` now uses `Re sum Lambda_file * conj(COCC_uu - COCC_dd)`, VASP's own SOC energy form. Updated the docstring.
- `pipeline v3/dmi_pipeline/dumpio.py`: `load_ferwe` no longer rejects fractional occupations or occupations outside [0, 1]. Updated the docstring. `OCCUPATION_TOLERANCE` stays because the MIN_F/MAX_F sanity comparison uses it.
- `pipeline v3/tests/fixtures.py`: the CPROJ oracle reads the CSO file as ket-first (`file[i, j] = C_ji`). The fake dump's band edge is now smeared, 0.7/0.3 on even k and 1.04/-0.04 (Methfessel-Paxton) on odd k, so every dump test runs on a smeared state.
- `pipeline v3/tests/test_trace_gates.py`: the density-matrix oracle in `test_cproj_trace_matches_density_oracle` uses the same layout. New `test_vasp_file_layout_fixes_the_trace_sign` is the math Section 4.4 layout test. It writes `xi L.S` on a real p shell and random spinors with fractional and negative weights into both files in exactly the `relativistic.F` and `COCC_FROM_INPUT` layouts, then requires that:
  - VASP's `Re sum CSO * conj(COCC)` equals `<H_SOC>`;
  - C0 passes;
  - handedness is -1/sqrt(2);
  - `trace_vector` equals the exact `<sigma_z x Lambda_a>` on all three axes.
- STATUS, CHANGELOG: FIX-1 recorded; stale merge lines reconciled.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `cd "pipeline v3" && .venv/bin/python -m pytest -q`, before the edits | PASS, 21 passed | Baseline at `cf5f9da` |
| Same, after the edits | PASS, 22 passed | Software only |
| Fault: drop the conjugate in `trace_vector` | Caught: `test_trace_vector_and_t3`, `test_vasp_file_layout_fixes_the_trace_sign` | Scratch injection, reverted |
| Fault: oracle back to bra-first (`kib,ij,kjb`) | Caught: `test_cproj_trace_matches_density_oracle`, `test_trace_vector_and_t3` | Scratch injection, reverted |
| Fault: restore the fractional FERWE check | Caught by 5 tests (`ValueError` on the smeared fixture) | Scratch injection, reverted |
| Fault: swap the flip blocks in `split_operator` | Caught: `test_dumps_provenance_and_trace`, `test_trace_vector_and_t3`, layout test | Scratch injection, reverted |
| `load_cso("noq/dump-C/CSO.dat")`, `load_cocc("noq/dump-P0/COCC.dat")`, `gate_c0`, `gate_n0`, handedness | C0 and N0 pass; total T = (+2.1e-8, +4.3e-8, +5.2e-8) eV, the recorded values with the sign reversed; max imaginary part 2e-19 eV; handedness -0.523 (x2), -0.440 (x2), -0.707 (x6) | Real BFO q = 0 dumps, one collinear state. Says nothing about finite q or the sign on VASP |

Not run: any VASP job, M1 on the real dump, `dmi trace` on a real tree.

## Decisions or deviations

None new. This implements D-020 and the FERWE part of D-021. DECISIONS and the math are not edited; an early edit of the D-020 status line was reverted, because the task brief excludes DECISIONS.

Existing tests tied to the old convention: two, both oracles rather than sign assertions. They were changed together with the code:

- `cproj_trace` in `tests/fixtures.py` read the CSO file as bra-first;
- the inline density-matrix route in `test_cproj_trace_matches_density_oracle` used `Tr(file @ rho)`.

No test asserts the sign of a dump-derived `T` or `D`. The `D` assertions in `test_tensors.py` feed spin-model traces to the fit and never call `trace_vector`. All 21 tests passed unchanged in their assertions.

Expected effect: every `T` changes sign, so `D` and the predicted rotation sense change sign. Magnitudes, the forbidden part `F`, the pitch, N0, P0, E0 and M1 are unchanged. The `tensors.json` sign label still says "unanchored until the TEN-07 supercell control". That is still true for VASP confirmation, so it was left for SIM-1 to reword, together with the `T_y`/T3 report fields it sits beside.

## Handoff

- Completed work: FIX-1 code and tests; STATUS reconciled with PRs #15, #16 and #17.
- Remaining work / blockers: SIM-1 (D-021 to D-023), then TEN-06. The sign still needs the TEN-07 supercell confirmation on VASP.
- Next concrete command or action: review and merge `fix-1-trace-sign`; write the SIM-1 branch from `main`.
- Files another session should read: `plans/simplify-1.md` Part 2, `STATUS.md`.
- Last tested commit, if available: the commit carrying this log, on `fix-1-trace-sign`.
- Uncommitted/unpushed work and where it exists: see the final response of this session.
