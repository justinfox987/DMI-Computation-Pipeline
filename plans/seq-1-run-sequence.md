# SEQ-1: sequential run scripts

Approved by the user on 2026-11-16. Branch `seq-1-run-sequence` from `main`.

## Goal

`dmi prepare` and `dmi dumps` keep writing the Slurm array scripts as now, and
each also writes a script that runs the same list one directory at a time
inside one allocation:

- `prepare` -> `run.sh` (loops over `runs.txt`)
- `dumps` -> `run_dumps.sh` (loops over `dumps.txt`)

Both scripts are always written; there is no new command-line option.

## Generated script

1. The job script's shebang and `#SBATCH` header, with no `--array` line, so
   `sbatch run.sh` and `bash run.sh` inside `salloc` both work.
2. Two comment lines: the generating command and job script sha256, and
   "Run from this directory: bash run.sh (inside an allocation) or sbatch run.sh".
3. `root="$PWD"`; exit 1 with a clear message if `$root/<list file>` is missing.
   Not `SLURM_SUBMIT_DIR`: under `salloc` it is where `salloc` was called.
4. For each listed name, in order: if `$root/$name/OUTCAR` contains
   "General timing and accounting", print `skip <name>: finished` and continue;
   otherwise print `run <name>` and run the job body in a subshell after
   `cd "$root/$name"`. A failed run does not stop the loop.
5. One run at a time; no background steps, no node packing.

## Implementation

`write_sequence` next to `write_array` in `spiral.py`, called from `prepare`
and `prepare_dumps` with the same job parts. The job.sh rules (no `cd`, no
`--array`) are unchanged. No change to `collect`, `fit` or any reader.

## Tests (stay at 15)

Extend the prepare test and the command-chain test: both scripts exist, the
header has no `--array`, the loop reads the right list, and the script holds the
job body and the skip test. If bash is available, run `run.sh` on a small tree
with a job body that writes a marker: a directory with the timing footer is
skipped and the others run in `runs.txt` order.

## Limits (documented)

The time limit covers the whole sequence; a run cut off mid-SCF is redone from
scratch on the next start; one slow run delays the rest.
