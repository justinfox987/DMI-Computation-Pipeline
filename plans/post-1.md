# POST-1 spec: dump COCC at the end of the SCF, and close the patch's open faults

Approved by the user on 2026-11-24, by the instruction to implement it,
including the three decisions under "Decisions to confirm". Repository branch
`post-1` from `main` at `0a4d67c`. Supersedes item 2.11 of
`plans/simplify-1.md`. New decision: D-030.

**As implemented** (2026-11-24, [log](../docs/sessions/2026-11-24_1740Z-agent-post-1.md)):

- Step 0 was not done before the edits: no Perlmutter hashes were available.
  The pre-edit SHA-256 of the six local files are in the session log, so the
  comparison can still be made. On a mismatch, restore the local tree from its
  backup before building.
- Section 2.2 puts the missing-`COCC.dat` error in `gates.py`. It is raised in
  `trace.trace_run`, where the file is read; `gates.check_tree` already reports
  a `trace_run` error against the run's name, so `gates.py` did not change.
- Section 1.4: the no-op validator also checks that the reader's echo lines sit
  inside the any-flag guard.
- The patch's "COCC trace is pathologically small" message no longer names
  `CSODUMP_PRELOOP`, because the post-loop dump reaches it too.

Source audit behind this spec: the patched tree `vasp-heide-patch-NEW`
(`csodump.F` last modified 2026-09-14), read against `main.F`, `paw.F`,
`reader.F`, `relativistic.F`, `electron.F`, `wave.F` and `main_mpi.F`, and the
TEN-07 Stage A record.

## Why

1. **Each spiral state costs two jobs.** The SCF converges the state, then
   `dump_P` rereads its WAVECAR and dumps `COCC.dat` before its first iteration.
   In TEN-07 Stage A the 31 `dump_P` runs took about 155 s each against about
   400 s per SCF: 28% of the tree. The spiral SCF is SOC-free, so the same
   routine can run on the orbitals in memory when the SCF ends.
2. **The patch has four faults that no production run has hit**, because the
   GPU build and the pipeline's decks avoid them. They should stop a run
   instead of depending on that.

| # | Fault | Today | After |
|---|---|---|---|
| F1 | With `NCORE > 1`, `CSO.dat` and `COCC.dat` miss ions and `CPROJ` files overwrite each other | Silent | Run stops |
| F2 | `LDUMPONLY` rewrites `CHGCAR` with a density that is not the converged one | Silent | Tag removed |
| F3 | `LDUMPONLY` with `LDUMPCSO` is accepted and always fails at the end | Late error | Tag removed |
| F4 | `COCC` is not symmetrized and nothing checks `ISYM` | Silent | Run stops |

## Decisions to confirm before coding

1. **Remove `LDUMPONLY`** instead of repairing it. Its one use was a cheap
   `dump_P`, which this spec removes. Removing it deletes F2, F3 and the two
   `GOTO` paths in `main.F`. The alternative is to keep it and force
   `LCHARG = F` and reject `LDUMPCSO`.
2. **Tag name `LDUMPCOCC_POST`.**
3. **Drop the stale-COCC guard in `trace_run`** (D-021). `COCC.dat` is now
   written by the run itself, before its OUTCAR closes, so "COCC older than
   OUTCAR" is always true and the guard has no replacement that is simple.

## Scope and rules

- **Two code bases.** Part 1 edits the VASP tree, which is licensed source and
  is **never added to this repository**, in whole or in part, including in
  tests, fixtures, logs and this spec's follow-ups. Part 2 edits `pipeline v3/`.
- **Local VASP tree:**
  `/mnt/c/Users/finny/Desktop/LBL 2026/vasp patch/vasp files/vasp-heide-patch-NEW`.
  The Perlmutter tree is the one that gets built.
- **Step 0, before any edit.** The user runs `sha256sum` on `src/csodump.F`,
  `src/main.F`, `src/paw.F`, `src/reader.F`, `src/relativistic.F` and
  `src/.objects` in the Perlmutter tree that built
  `vasp.6.4.2 (build Sep 14 2026 08:43:24)`. The agent compares them with the
  local files. On any mismatch, stop and report; do not edit.
- The agent edits and runs the static validators. The user copies the files to
  Perlmutter, builds and runs. No agent submits a job.
- Do not change `paw.F`, `relativistic.F`, any file format, or
  `LDUMP_LEGACY_LAST`.
- Anchors below are given by text, not line number.

## Part 1: the patch

### 1.1 `csodump.F`

**New flag.** `LOGICAL, SAVE :: LDUMPCOCC_POST = .FALSE.` with the others, and
`LOGICAL, SAVE :: POSTLOOP_DONE = .FALSE.`. Delete the `LDUMPONLY` declaration.

**One contraction routine, two labels.** Rename `COCC_FROM_INPUT` to
`COCC_FROM_CPROJ` and give it one more argument, `LABEL`, passed through to
`WRITE_COCC_FILE`. Its loop, reductions and file name `COCC.dat` do not change.
`CSODUMP_PRELOOP` passes `'PRE_LOOP input CPROJ'`, as now.

**New routine.**

```fortran
SUBROUTINE CSODUMP_POSTLOOP(W, WDES, T_INFO, INFO)
   ! same argument types and intents as CSODUMP_PRELOOP
   IF (.NOT. LDUMPCOCC_POST) RETURN
   IF (POSTLOOP_DONE) RETURN
   POSTLOOP_DONE = .TRUE.
   CALL CSODUMP_CHECK_LAYOUT(WDES)
   CALL COCC_FROM_CPROJ(W, WDES, T_INFO, INFO, 'POST_LOOP final CPROJ')
END SUBROUTINE
```

It dumps once, after the first electronic minimization. Do not use VASP's
internal `CRHODE`: it is mixed, which is why Patch B contracts `CPROJ` itself.

**Layout guard (F1).**

```fortran
SUBROUTINE CSODUMP_CHECK_LAYOUT(WDES)
#ifdef MPI
   IF (WDES%COMM_INB%NCPU > 1) CALL VTUTOR%ERROR( &
      'csodump: dumps need NCORE = 1; ions are distributed over the NCORE group and are not gathered.')
#endif
END SUBROUTINE
```

Call it first in `CSODUMP_PRELOOP`, after the flag `RETURN` and before
`PRELOOP_DONE` is set, and in `CSODUMP_POSTLOOP`. `CSODUMP_PRELOOP` also runs
for an `LDUMPCSO`-only deck, so this covers `CSO.dat`.

### 1.2 `reader.F`

- Remove `LDUMPONLY`: the `USE` entry, the read, the echo line and its check.
- Read `LDUMPCOCC_POST` the same way as the other tags.
- Set `DUMP_IU0 = IU0` when any of the five remaining tags is set.
- Print the echo block only when at least one tag is set, so a flags-off run's
  stdout equals stock VASP's.
- New errors, each through `VTUTOR%ERROR`:
  - `LDUMPCOCC_POST` with `LSORBIT = T`. This is the Patch A contamination
    (SOC mixes the orbitals the dump reads), so it is an error and not a
    warning.
  - `LDUMPCOCC_POST` with `LDUMPCOCC`: both write `COCC.dat`.
  - `ISYM /= -1` with any of `LDUMPCPROJ`, `LDUMPCOCC`, `LDUMPCOCC_POST` (F4).
    `ISYM` is already read above this block.

### 1.3 `main.F`

- In the `USE csodump` list, drop `LDUMPONLY`; add `CSODUMP_POSTLOOP` and
  `LDUMPCOCC_POST`.
- Delete `IF (LDUMPONLY) GOTO 3056` and the block
  `IF (LDUMPONLY) THEN ... GOTO 3164 ... ENDIF`. Remove the statement labels
  `3056` and `3164`, restoring both lines to their stock form.
- Add the one hook. In the ionic loop, directly after
  `CALL ELECTRONIC_OPTIMIZATION` and before the `WVREAL_PRECISE` block:

```fortran
      IF (LDUMPCOCC_POST) CALL CSODUMP_POSTLOOP(W, WDES, T_INFO, INFO)
```

Why this point is safe, from the source:

- `ELMIN` ends by updating the host copies of the orbitals and projections,
  so on GPU the host projections are current.
- The WAVECAR is written later from this same `W`, so the dump is the state
  `dump_P` reconstructs, without the single-precision round trip.

Not established from the source: that host `W%FERWE` is current here on GPU.
Acceptance test A2 decides it.

### 1.4 Static validators (`tools/`, local tree only)

Update, do not add files.

- Remove the three `LDUMPONLY` checks and the stale check
  "legacy output guards unavailable INFO metadata" (it expects a
  `TRACE_TOTAL`/`NELECT` comparison that was removed on purpose).
- Replace `"LDUMPONLY"` in the no-op flag list with `"LDUMPCOCC_POST"`.
- Add: no `LDUMPONLY`, `3056` label or `3164` label left in `main.F`,
  `reader.F` or `csodump.F`; exactly one `CSODUMP_POSTLOOP` call in `main.F`,
  on a line guarded by `LDUMPCOCC_POST`; `CSODUMP_CHECK_LAYOUT` is called in
  both hook routines; the three new `reader.F` errors exist.

Both scripts must exit 0.

### 1.5 `README_HEIDE_PATCH.md` (local tree)

Update the tag table, the Runs section (SCF with `LDUMPCOCC_POST`, `dump_C`
unchanged, `dump_P` only for M1) and the Rules. Remove every `LDUMPONLY` line.

## Part 2: the pipeline

### 2.1 `spiral.py`

- `FIXED` gains `"LDUMPCOCC_POST": "T"`; add it to `LOGICAL`. Every spiral SCF
  now writes its own `COCC.dat`. The owned-tag count in the comment and in math
  Section 3.2 goes from eleven to twelve.
- Delete `DUMP_P`.
- `prepare_dumps` writes `dump_C` only: delete the per-run loop, the
  `WAVECAR` link and the `skipped` return value. `dumps.txt` then has one line.
  Keep `submit_dumps.sh` and `run_dumps.sh`; drop `pack_dumps.sh` and the
  `--slots` and `--max-time` options of `dmi dumps`, since one run needs no
  pack.
- `dump_C`'s deck must not inherit the tag: add `LDUMPCOCC_POST` to the keys
  stripped from q0's INCAR (it is an `LSORBIT = T` deck and would be refused).

### 2.2 `trace.py`, `dumpio.py`, `gates.py`, `__main__.py`

- `trace_run` reads `run / "COCC.dat"`. Delete the mtime guard (decision 3).
- `dumpio`: the COCC label may be `"PRE_LOOP input CPROJ"` or
  `"POST_LOOP final CPROJ"`. `trace_run` requires the second, so an old
  `dump_P` file copied into a run directory is refused by name.
- `gates.py`: a run that is ok but has no `COCC.dat`, in a tree that has
  `dump_C`, is an error naming the run and saying the SCF needs the POST-1
  build. The energies-only rule (no `dump_C`) is unchanged.
- `__main__.py`: command help and the `dumps` message.

### 2.3 Tests (stay at 15; change existing tests)

- Fixtures write `COCC.dat` in the run directory with the POST label.
- The command-chain test runs `prepare`, `dumps` (one deck) and `fit` on the
  new layout and checks that every SCF INCAR has `LDUMPCOCC_POST = T` and
  `dump_C`'s INCAR does not.
- One existing reader test also loads a PRE-label file through `load_cocc` and
  checks that `trace_run` refuses it.
- **Mutations**, before reporting: `trace_run` reading `dump_P/COCC.dat`;
  `LDUMPCOCC_POST` left in the `dump_C` deck; the missing-COCC error removed.
  A test must fail each time.

### 2.4 `acceptance/compare_cocc.py` (new, about 40 lines)

`python acceptance/compare_cocc.py RUN CSO.dat` loads `RUN/COCC.dat` and
`RUN/dump_P/COCC.dat` with `load_cocc`, and prints the largest
`|difference|` with its `(IS, ION, I, J)`, and `T` from each with
`trace.trace_vector`. It reuses the package readers and adds no physics.

### 2.5 Docs

`docs/seed_file.md` (commands), math Section 5 run table and Section 12 steps,
`STATUS.md`, and D-030 in `docs/DECISIONS.md`: one SCF per state writes COCC;
`dump_P` survives only as the M1 run; `LDUMPONLY` removed; D-021's guard
dropped.

## Acceptance (the user's runs, new build, TEN-07 Stage A settings at 8x8x8)

Run in a fresh tree: `q0`, `d2_t3_plus`, `d2_t3_minus` (three SCFs) and
`dump_C`. Then, by hand in each of the three run directories, one old-style
`dump_P`: the run's INCAR with `LDUMPCOCC_POST` removed, plus `ISTART = 1`,
`ICHARG = 11`, `ALGO = Normal`, `NELM = 1`, `LDUMPCOCC = T`, `LWAVE = F`,
`LCHARG = F`, and links to `../WAVECAR` and `../CHGCAR`. Add
`LDUMPCPROJ = T` to q0's.

| ID | Check | Pass |
|---|---|---|
| A0 | Step 0 hashes match | All six |
| A1 | Static validators | Both exit 0 |
| A2 | `compare_cocc.py` on the three runs | Largest COCC difference below 1e-6; each `T` component differs by less than 5e-7 eV |
| A3 | `dmi fit` on the tree | C0, N0, P0 and E0 pass |
| A4 | Agreement with Stage A | q0 energy within 1e-6 eV of -29.31863775 eV; `|y|` of d2_t3 within 0.5% of 0.30030 meV |
| A5 | M1 on q0's `dump_P` (`acceptance/m1.py`) | Below 1e-10, as D-021 requires per build |
| A6 | Refusals, each a few seconds | `LDUMPCOCC_POST` with `LSORBIT = T`; with `LDUMPCOCC`; with `ISYM = 0`: each stops in the reader with its message |
| A7 | Flags off | q0 SCF with no dump tag: stdout has no `LDUMP` line, and no `COCC.dat` is written |

A2's bounds: the WAVECAR is single precision, so the two dumps should differ
near 1e-7, and Stage A's parity noise is sigma_y = 1.1e-7 eV. If A2 fails and
the difference is at the 1e-3 level or above, suspect stale host occupations
on GPU (Section 1.3) before anything else.

F1's guard cannot fire on the GPU build, which forces `NCORE = 1`. It is
covered by A1 only, unless the CPU build is rebuilt: there, `NCORE = 2` with
`LDUMPCOCC_POST = T` must stop.

**Record:** `evidence/<date>-post-1/` with the INCARs, `fit.log`,
`traces.json`, the `compare_cocc.py` output, the M1 output, the build line and
the new SHA-256 of the six files.

## Not in this spec

- A build stamp in the dump headers.
- Removing `LDUMP_LEGACY_LAST`.
- Computing `CSO` without the separate `dump_C` run.
- `-DWAVECAR_double`. No dump reads the WAVECAR after this change.

## Order of work

1. Step 0.
2. Part 1; A1. Hand the six files and the two validators' output to the user.
3. The user builds; the reviewer checks the diff against Section 1.
4. Part 2 on branch `post-1`; tests and mutations; pull request.
5. The user runs the acceptance set; A2 to A7; evidence record; D-030 accepted.
6. Only then is the Sep 14 binary retired from the job scripts.
