# PACK-1 spec: one batch job that keeps several runs going at once

Design approved by the user on 2026-11-20. Branch `pack-1` from `main` at
`a1735be`. Workflow context: `plans/seq-1-run-sequence.md` (`run.sh`).

## Why

`submit.sh` (an array) queues each run separately; `run.sh` runs one at a time
in one allocation. A tree of 19 to 31 small runs is cheaper to queue as one job
that runs several of them side by side, each on a slice of the allocation.

## Interface

```text
dmi prepare seed.toml --job scf.sh --out TREE --slots 4 [--max-time HH:MM:SS]
dmi dumps   TREE --job patchb.sh --slots 4 [--max-time HH:MM:SS]
```

Without `--slots` nothing changes. With it, the command also writes `pack.sh`
(`prepare`) or `pack_dumps.sh` (`dumps`), next to the array and sequence scripts.

## The job script

It describes **one** run. Its header must set `--nodes` and `--time`, and may set
`--gpus`. With `--slots`, its body must mention `DMI_RUN_NODES` and `--exact`,
or the command refuses it and shows this example:

```bash
gpus=$((4 * DMI_RUN_NODES))
srun --nodes="$DMI_RUN_NODES" --gpus="$gpus" --ntasks="$gpus" --exact ... "$vasp" &> output.log
```

A body that sizes `srun` from `SLURM_JOB_NUM_NODES` would take the whole
allocation.

## Generated header

These lines of the user's header are rewritten; all others are copied:

- `--nodes` = slots × nodes (accepting `--nodes=N`, `--nodes N`, `-N N`, `-N=N`);
- `--gpus` = slots × gpus, only if present;
- `--time` = time × ceil(n_runs / slots), accepting `MM`, `MM:SS`, `HH:MM:SS` and
  `D-HH:MM:SS`, and written as `HH:MM:SS` or `D-HH:MM:SS`.

If `--max-time` is given and the computed time exceeds it, the command stops with
an error that states both. It refuses slots < 1. If slots > n_runs, it uses n_runs.
Two comment lines, as in `run.sh`: the generator, the job's SHA-256, the slots and
the nodes per run; and "Run from this directory: sbatch pack.sh".

## Generated body

- `root="$PWD"`; exit 1 with a clear message if the list file is missing.
- `export DMI_RUN_NODES=<nodes per run>`.
- For each listed name, in order: skip it if its OUTCAR has the `FINISHED`
  footer (the same rule and constant as `run.sh`). Otherwise start the user's
  job body in a background subshell after `cd`, with stdin from `/dev/null`.
  When `<slots>` runs are going, wait for one to finish (`wait -n`) before
  starting the next. Sleep 1 s between launches. Print `run`, `skip`, `done`
  and `failed <name> (exit N)` lines.
- After the loop, wait for all; exit 1 if any run failed.
- Slurm places each step; no node names are passed. A resubmission skips
  finished runs and redoes unfinished ones.
- `pack_dumps.sh` does the same over `dumps.txt`. `dump_C` is one entry like any
  other.

## Implementation

`write_pack` beside `write_sequence` in `spiral.py`, sharing the skip test and
the job parts. The header is rewritten by a small pure function. No change to
`collect`, `fit` or any reader.

## Tests (stay at 15; extend existing tests)

- **Header.** For a header like the user's (`--nodes=4`, `--gpus=16`,
  `--time=00:30:00`, 31 runs, 4 slots), the result is 16, 64 and `04:00:00`;
  other lines are untouched. A `--max-time` violation is refused. A body
  without `DMI_RUN_NODES` or `--exact` is refused.
- **Execution.** Run `pack.sh` with bash on a fake tree, with a fake job body
  that records start and end times. Check that:
  - no more than `<slots>` runs are going at once;
  - finished runs are skipped;
  - a failing run does not stop the others, and the script exits 1;
  - every unfinished run ran exactly once;
  - `DMI_RUN_NODES` is visible to the body.
- **Mutations.** Before reporting, remove the slot limit and then the skip; a
  test must fail each time.

## Docs

- `docs/seed_file.md`:
  - the `--slots` option;
  - the job-script contract, with the `srun` example;
  - the three ways to run a tree (array, sequence, pack) and when each suits;
  - the limits: the time is rounds × the per-run limit; idle slots in the last
    round are still charged; a run cut off by the limit is redone.
- STATUS, CHANGELOG and the session log. Concurrent GPU steps with `--exact`
  inside one allocation stay untested until the user runs them on Perlmutter.

## Implementation choices the design left open (recorded at implementation)

- **Failure accounting.** The body is portable across bash 4.4 and 5.x:
  - `wait -n` is used only to throttle, against the live count from `jobs -rp`;
  - each failed run appends its name to a temporary file, and the final status
    comes from that file after a plain `wait`.

  This does not rely on `wait -n` returning the status of a job that ended
  before the call, which depends on the bash version.
- **Short forms.** `-t` and `-G` are accepted alongside `--time` and `--gpus`,
  like `-N`.
- **`--gpus=type:N`.** The `type:` prefix is kept, and N is scaled.
- **Refusals.** A header that sets one of the three options twice, or a
  non-integer node or GPU count, is refused.
- **`--max-time`.** It is refused without `--slots`.
- **Header lines not rewritten.** Other per-allocation totals in the header,
  such as `--ntasks` or `--mem`, are copied unchanged, as the design says. The
  docs warn that a total of this kind must be per-node or removed.
