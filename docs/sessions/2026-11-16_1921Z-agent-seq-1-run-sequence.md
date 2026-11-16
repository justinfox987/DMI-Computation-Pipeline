# Session: SEQ-1 sequential run scripts

- Session ID / UTC date: 2026-11-16
- Agent or human / platform: Claude Code (Opus 5.5), WSL2
- Task ID and scope: SEQ-1, `run.sh` and `run_dumps.sh` beside the array scripts
- Branch: `seq-1-run-sequence`, from `main`
- Base commit at session start: `e514eed`
- Working-tree changes already present: untracked `Claude outputs/` and `materials/fe/job.sh` (not this task's; left untouched)
- Related spec / prior session: [plans/seq-1-run-sequence.md](../../plans/seq-1-run-sequence.md); [SIM-1b log](2026-11-11_2255Z-agent-sim-1b-incar-fit.md)
- Status: complete, awaiting review

## Work performed

- `pipeline v3/dmi_pipeline/spiral.py`: `write_sequence` next to `write_array`,
  called from `prepare` (`run.sh` over `runs.txt`) and `prepare_dumps`
  (`run_dumps.sh` over `dumps.txt`) with the same job parts. The OUTCAR footer
  string is now the constant `FINISHED`, shared by `read_static` and the skip test.
- `pipeline v3/dmi_pipeline/__main__.py`: help and the closing line name both scripts.
- `pipeline v3/tests/test_spiral.py`: the prepare test checks `run.sh` (header
  without `--array`, the list file, the job body and the skip test) and runs
  `write_sequence`'s output with bash on a four-directory tree.
- `pipeline v3/tests/test_tensors.py`: the command-chain test checks `run_dumps.sh`.
- `docs/seed_file.md`, `STATUS.md`, `CHANGELOG.md`, `plans/seq-1-run-sequence.md`.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `cd "pipeline v3" && .venv/bin/python -m pytest -q` at `e514eed` | PASS, 15 | Baseline |
| `cd "pipeline v3" && .venv/bin/python -m pytest -q` | PASS, 15 | Software only |
| Fault injection: list read on stdin instead of fd 3; no `continue` after skip; no `||` after the subshell | Each makes `test_prepare_writes_paired_f0_inputs` fail | Shows the run test sees these faults |

No Slurm, `salloc` or VASP run. `sbatch run.sh` is not tested on a cluster.

## Decisions or deviations

Not covered by the spec, decided here:

- The list is read on fd 3 (`while read -r name <&3 ... done 3< list`). `srun`
  forwards stdin to task 0, so with a plain `done < list` the first VASP launch
  could swallow the rest of the list. The test's job body runs `cat > /dev/null`
  to check this.
- A failed run prints `failed <name>: exit <code>`, and the script exits 1 if any
  run failed (0 otherwise). VASP often exits 0 after a bad SCF, so `collect`
  remains the judge of a run.
- The job body is inserted verbatim, not indented, so heredocs in it still work.
- The test runs bash unconditionally, as the existing `bash -n` checks already do.

No DECISIONS entry.

## Handoff

- Completed work: SEQ-1 as specified.
- Remaining work / blockers: review and merge; first real use on Perlmutter by the user.
- Next concrete command or action: review the PR from `seq-1-run-sequence`.
- Files another session should read: the spec, `spiral.write_sequence`.
- Last tested commit, if available: the SEQ-1 commit on `seq-1-run-sequence`.
- Uncommitted/unpushed work and where it exists: none of this task's after the push.
