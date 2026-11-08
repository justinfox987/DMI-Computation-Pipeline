# Session: TEN-03 seed, q plan, F0 inputs and readback

- Session ID / UTC date: 2026-11-08
- Agent or human / platform: Claude Code (Opus 5.5)
- Task ID and scope: TEN-03, `spiral.py` per [plans/ten-03-spiral.md](../../plans/ten-03-spiral.md); delete `step1.py`
- Branch: `ten-03-spiral`
- Base commit at session start: `main` at `8d50eb6` (TEN-02 and its follow-up merged)
- Working-tree changes already present: none (the spec draft was untracked and committed first as `f8a944b`)
- Related spec / prior session: [TEN-02 follow-up](2026-11-08_1829Z-agent-ten02-followup.md)
- Status: complete, pending review

## Work performed

- `pipeline v3/dmi_pipeline/spiral.py` (new, about 500 lines including 160 moved):
  `load_seed`, `material_incar`, `cartesian`/`unit_directions`/`conditions`/
  `choose_directions`, `plan`, `targets`, `split_job`, `prepare`, `read_run`,
  `collect`. `sphere`, `check_run`, `printed_step` and their regexes moved from
  `step1.py` unchanged.
- `pipeline v3/dmi_pipeline/__main__.py`: `plan`, `prepare`, `collect` replace
  `step1-prepare`, `step1-wrap-partner`, `step1-read`, `step1-row`, `step1-fit`.
- Deleted `step1.py` (662 lines) and `tests/test_step1.py` (4 tests).
- `tests/test_spiral.py` (new, 3 tests). `tests/fixtures.py` now holds `bfo()`,
  unwrapped (second Fe at x - 1/2); `test_symmetry.py` imports it.
- Docs: spec updated, `seed_file.md` (no `status`, `--out`, `collect RUNS`),
  D-013 amendment, AGENTS, README, STATUS, CHANGELOG.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `cd "pipeline v3" && .venv/bin/python -m pytest -q` | PASS, 15 passed | Whole suite; only spglib's DeprecationWarning |
| Fault injection, one at a time, `pytest -x tests/test_spiral.py tests/test_symmetry.py` | 19 of 19 caught | `inv(lattice.T)` in directions and in the q length, q magnitude not `t`, wrapped positions, unrounded `q_frac`, `-q` target = `+q`, first TOTEN, `MW_int` for `M_int`, `theta` left out, pair rule removed, and each of the 9 `prepare`/INCAR/job guards. `spiral.py` restored and compared byte-for-byte after each run |
| `bash -n` on the generated `submit.sh` | PASS | Inside `test_prepare_writes_paired_f0_inputs`; Slurm itself not run |

Software behavior only. No VASP or cluster jobs; `sbatch` was never called.

## Decisions or deviations

- User decisions 1-8 and rules (a)-(c) are recorded at the end of the spec.
- **Deviation, approved by the user mid-session:** the readback rule
  `|delta_a| < 90°` was replaced by a pair-phase rule,
  `max_ab |arg(z_a z_b*)| < 90°` with `z_a = u_a* s_a`. In a 2-site cell, theta
  absorbs half of a flip, so a reversal gives `delta = ±90.0000°` and noise
  decides. The pair rule implies the old one. Spec and guard table updated.
- Found during implementation:
  - The first wrapped-position fault went unnoticed because the test only checked
    a direction with `q_frac·(1,1,1) = 0`. The test now checks every run.
  - `lattice @ q / 2π` left `-2e-18` in `QSPIRAL`, so `q_frac` is now computed
    as `t d / |2π L^{-T} d|`.
  - Three symmetry-equivalent BFO direction sets tie to 1e-15, so the score is
    rounded to 1e-9 and the first set in order wins.
- `RWIGS` "per species type on line 6" is recovered by grouping consecutive
  species. A POSCAR that repeats a symbol in adjacent line-6 entries would merge
  them. Not seen in practice; noted, not handled.
- D-013 amended in one line (no `status` command). No new decision.

## Handoff

- Completed work: everything in the spec's "Done when", except the merge.
- Remaining work / blockers: TEN-04 spec (trace step; CSO `provenance.json`
  writer; remove the `Bi` check). `materials/fe` still lacks POSCAR, INCAR and
  KPOINTS until TEN-06.
- Next concrete command or action: review and merge the TEN-03 PR.
- Files another session should read: `plans/ten-03-spiral.md`, `dmi_pipeline/spiral.py`, `STATUS.md`.
- Last tested commit, if available: the `ten-03-spiral` commit containing this log.
- Uncommitted/unpushed work and where it exists: none after push.
