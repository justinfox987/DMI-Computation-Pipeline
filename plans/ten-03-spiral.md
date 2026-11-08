# TEN-03 spec: seed, q plan, F0 inputs and readback

Physics authority: `docs/math/heide_math_v3.md`, Sections 3, 8 and 12. The seed
format is `docs/seed_file.md` (D-016). This file fixes the interfaces, the guards
and the tests. It does not restate the equations.

Status: approved by the user on 2026-11-08, with the decisions listed at the end.
The numbers under "Measured while drafting" came from a scratch script that was
not committed. Work on a branch `ten-03-spiral` from `main`.

## Scope

Add `pipeline v3/dmi_pipeline/spiral.py`, about 250 lines. It covers Section 12,
steps 1, 3, 4 (SCF inputs only) and 5:

1. the seed loader;
2. `dmi plan`: symmetry summary first, then the q plan and both rank conditions;
3. `dmi prepare`: F0 inputs at every +q and -q and at q = 0, plus `submit.sh`;
4. `dmi collect`: E and `M_int` readback and the phase relaxation of Eq (3.3).

Delete `step1.py` and `tests/test_step1.py`. Move the two readers that carry
forward, `sphere` and `check_run` (with `printed_step` and the regexes they use),
into `spiral.py` unchanged except for the deletions listed below. Remove the
`step1-*` commands from `__main__.py`. Net change is about 400 lines removed.

Out of scope:

- `dump_P` and `dump_C` inputs, the trace and the gates: TEN-04.
- Fits and `dmi fit`: TEN-05.
- Exchange-grid runs: TEN-09. The loader validates `exchange_grid` and `rmax`, and
  `plan` prints the class count, but `prepare` writes no exchange runs.
- `dmi status` is dropped. `collect` prints one state per run. Update
  `docs/seed_file.md` and add a one-line D-013 amendment to `docs/DECISIONS.md`.

## Seed loader

```python
load_seed(path) -> dict
    # sites      (Nm,)  0-based ints        signs   (Nm,) +1/-1
    # moments    (Nm,)  μB, > 0             t       (Nt,) 1/Å
    # spacegroup int | None                 symprec float, default 1e-3
    # directions (Nd, 3) q_frac | None      exchange_grid (3,) | None, rmax | None
    # folder     Path of the material       lattice, species, tau  from realized.poscar
```

It reads `seed.toml` with `tomllib`, then `POSCAR` from the same folder with the
existing `realized.poscar`. There is still one POSCAR parser.

Guards, all `ValueError` and each naming the key:

| Rule | Failure it stops |
|---|---|
| Unknown key | A mistyped `spacegroups` silently ignored |
| Missing required key | — |
| `sites`, `signs`, `moments` have equal lengths | Misaligned per-site values |
| `sites` are distinct integers in `1..N_atoms` | An off-by-one site list |
| `signs` are `+1` or `-1`; `moments` are finite and `> 0` | — |
| `t` has at least 3 distinct, finite, positive values (Section 8.3) | A fit with no spare degree of freedom |
| `directions` rows are three finite numbers, not all zero | — |
| `exchange_grid` is 3 positive integers; `rmax > 0` if and only if `exchange_grid` is set | A grid with no bond cutoff |

TOML integers and floats differ. `sites`, `signs`, `spacegroup` and
`exchange_grid` must be integers. The other numeric keys accept either.

## The q plan

```python
plan(seed) -> dict
    # ops          symmetry.operations(...) output
    # p_D, p_A, n_twist
    # directions   (Nd, 3) q_frac directions, from the seed or chosen
    # sigma_D      smallest singular value of S                  Section 8.2
    # sigma_A      p_A-th singular value of M[i, l] = s_i^T C_l s_i
    # points       list of {"name", "q_frac"}, including the q = 0 reference
    # classes      exchange class count, or None without exchange_grid
```

### Conventions

- `L = lattice.T`, as in TEN-02. A direction `d` in `q_frac` has the Cartesian
  unit vector `s ∝ inv(lattice) @ d`, which is `L^{-T} d`. Using `inv(lattice.T)`
  instead is the easy mistake. In a cubic cell both give the same answer, but in
  rhombohedral BFO they do not.
- The point for direction `s` and magnitude `t` is `q = t s` in 1/Å, so
  `q_frac = lattice @ q / (2π)`, from Eq (8.1).
- Phases use the POSCAR positions exactly as written. They are never wrapped
  into `[0, 1)`: `phi_a = 2π q_frac · tau_a` with `tau_a` as `realized.poscar`
  returns it, which the reader does not wrap. Wrapping would change `phi_a` by
  `2π q_frac · n` for an integer `n`, which is not a multiple of `2π` at generic
  `q`. The test fixture writes one magnetic site outside `[0, 1)`.
- Format `q_frac` once to the string written in `QSPIRAL`, `%.12g` per component.
  Compute the Eq (3.1) phases from the parsed string, not the unrounded value,
  so that `MAGMOM` and `QSPIRAL` always agree.
- Run names are `q0`, then `d{i}_t{j}_plus` and `d{i}_t{j}_minus` with 1-based
  `i` and `j`. There are `2 Nd Nt + 1` runs.

### Rank conditions (both are guards, checked before any input is written)

- **D:** `S` has the unit `s_i` as columns. Require `sigma_D >= RANK_FLOOR`.
  This applies even when `p_D = 0`, because the free 9-component fit and its
  forbidden part need it.
- **A:** `M[i, l] = s_i^T C_l s_i`, with `C_l` from `symmetry.stiffness_basis`
  (Frobenius-orthonormal). Require `Nd >= max(3, p_A)` and
  `sigma_A >= RANK_FLOOR`.

`RANK_FLOOR = 0.1`. The rows of `S` and the basis are normalized, so the
singular values are O(1), and an exact rank deficiency shows up as 0. See open
question 2.

### Default directions

If the seed has no `directions`, take the 13 low-index candidates `q_frac` with
components in `{-1, 0, 1}`, one per `±` pair. Choose the `max(3, p_A)`-element
subset that maximizes `min(sigma_D, sigma_A)`, and break ties by the first
subset in `itertools.combinations` order. This is at most 1716 subsets for
`p_A = 6`. It applies Section 8.2's rule directly and adds no option.

### `dmi plan materials/x/seed.toml`

Writes no files. The output prints, in this order:

```text
space group 161 (R3c) at symprec 0.001: 6 operations, 6 kept, 0 dropped
p_D 1  p_A 2  n_twist 0
ENCUT 600  ENINI 500
directions (q_frac)   sigma_D 0.909  sigma_A 0.980
  d1  0 1 -1
  ...
t (1/Å) 0.03 0.06 0.09   ->  19 runs including q0
exchange classes within rmax 6.0: <n>      # only with exchange_grid
```

The first line comes straight from `symmetry.operations`, as D-017 requires.
`plan` also checks the material `INCAR` with the same function `prepare` uses
(the `INCAR` rows of the guard table below), so `plan` catches those errors
before any input is written.
`plan` exits 1 with the `ValueError` message if any guard fails, including the
TEN-02 guards. A nonzero `n_twist` is printed, not rejected: the spirals are
unconstrained (D-008), so the intracell phases are free to relax.

## F0 inputs

```python
prepare(seed, out, job) -> list[Path]   # run directories, in submit order
```

`dmi prepare materials/x/seed.toml --job job.sh --out DIR` runs `plan` first and
stops on the same guards. It then writes:

```text
DIR/
  plan.json        seed text, SHA-256 of seed/POSCAR/INCAR/KPOINTS/POTCAR, the plan summary
  submit.sh        Slurm array, see below
  runs.txt         run directories in submit order
  q0/  d1_t1_plus/  d1_t1_minus/  ...
     INCAR  KPOINTS  POSCAR  POTCAR  config.json
```

`config.json` per run holds `q_frac`, `sites`, `signs`, `targets` (Eq 3.1,
magnetic sites only) and the generated `tags`. `trace.trace_config` already reads
`q_frac` from `config.json` and finds `dump_P/` under the run, so TEN-04 needs no
new run record.

INCAR is the material `INCAR` plus the Section 3.2 tags, which the code writes:
`LNONCOLLINEAR = T`, `LSPIRAL = T` (also at q0), `LSORBIT = F`, `QSPIRAL`,
`LZEROZ = T`, `SAXIS = 0 0 1`, `ISYM = -1`, `I_CONSTRAINED_M = 1`, `LAMBDA = 0`,
`MAGMOM = m_a S_a^0` and `M_CONSTR = S_a^0`. Nonmagnetic ions get zero vectors.
Targets are physical lab vectors from Eq (3.1) at `+q`, `-q` and `0`, with no
pre-unwinding. The `-q` run evaluates the same formula at `-q`. There is no
separate partner reflection, which removes `step1.partner` and `wrap_partner`.

Guards:

| Rule | Failure it stops |
|---|---|
| `DIR` does not exist or is empty | Overwriting a VASP run |
| Material `INCAR` has only tags in `realized.INCAR_TAGS` | A typo treated as a setting |
| A generated tag in the material `INCAR` must have the same value, or the run stops and names the tag | An `ISYM = 2` or `LSORBIT = T` left in a template |
| `RWIGS` is in the material `INCAR` with one positive value per species type on POSCAR line 6, in that order | Missing sphere moments, or one radius per atom |
| `ENCUT` and `ENINI` are both in the material `INCAR`. There is no check on the gap between them | An `ENINI` default that differs between machines |
| `KPOINTS`, `POTCAR` and `job.sh` exist and are not empty | — |
| The body of `job.sh`, after its `#SBATCH` lines, contains no `cd` command | A template that leaves the run directory chosen by `submit.sh` |
| `POTCAR` `VRHFIN =X:` element order equals the POSCAR species order | A wrong POTCAR order, which otherwise runs and gives wrong physics |

## `submit.sh`

Generated from the user's `job.sh`, which owns the executable, modules and
resources (D-006). `job.sh` runs VASP in its working directory. `prepare` splits
it after its last leading `#SBATCH` line and writes:

```bash
#!/bin/bash
<job.sh's #SBATCH lines, unchanged>
#SBATCH --array=1-19
# Generated by dmi prepare from job.sh (sha256 ...). Submit with: sbatch submit.sh
cd "$SLURM_SUBMIT_DIR/$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$SLURM_SUBMIT_DIR/runs.txt")" || exit 1
<the rest of job.sh, unchanged>
```

`runs.txt` lists the run directories in submit order. `prepare` stops if
`job.sh` already sets `--array`, or if its body contains its own `cd` (a word
`cd` at the start of a command, after `;`, `&&`, `||` or `|`). The user submits
from `DIR`. The code never calls `sbatch`.

## Readback

```python
read_run(run) -> dict
    # E_eV        last OUTCAR match of r"free\s+energy\s+TOTEN\s*=\s*(FLOAT)"
    # M_int       (Nm, 3) lab vectors of the magnetic sites, final complete block
    # M           (Nm,) lengths
    # theta_deg   common angle, Eq (3.3)
    # delta_deg   (Nm,) phase relaxation, Eq (3.3)
collect(out) -> dict      # {run name: read_run(...) or {"error": message}}
```

`dmi collect DIR` reads every run in `runs.txt`, writes `DIR/collected.json`
with SHA-256 hashes of each run's `OUTCAR` and `OSZICAR`, prints one line per run
(`ok`, `missing` or the error), and exits 1 if any run is not `ok`. It is safe to
rerun, because the run directories are its only state (D-013).

`read_run` uses the moved `check_run`, which checks for one completed OUTCAR
segment, the final loop reaching EDIFF, the INCAR echo, and that the final
OSZICAR step matches the OUTCAR step. Directions come only from `M_int`.
`MW_int` is parsed but not used.

Guards. A failed guard marks that run as not `ok`; it does not stop the others:

| Rule | Failure it stops |
|---|---|
| `check_run` passes | Unconverged or restarted runs |
| Generated tags in the run `INCAR` equal `config.json` | An input edited after `prepare` |
| Printed final `lambda` is 0 | A penalty in E |
| `M_a >= 0.1 μB` on every magnetic site | A collapsed moment with an undefined direction |
| `abs(delta_a) < 90°` on every magnetic site | An SCF that fell into a different sign pattern |

Removed with `step1.py`, because they served `LAMBDA > 0` or the bond rows: the
penalty and field reconstruction in `validate`, the `M_int` and `MW_int`
reference-magnitude drift check, the 1° direction gate, the F1/F2 targets,
`coefficients`, `paired`, `fit` and `read_and_gate`. At `LAMBDA = 0` the measured
directions are the result, so a small `delta_a` is reported, not rejected
(Section 3.3).

## Removing the bond rows and constrained families

Delete these from `step1.py`, then delete the file once `sphere` and `check_run`
have moved: `targets` (F0/F1/F2), `partner`, `prepare`, `_prepare_record`,
`wrap_partner`, `write_inputs`, `require_vector`, `read_state`, `read_and_gate`,
`validate`, `coefficients`, `paired` and `fit`, along with the constants only they
use (`CONVENTION`, `DIRECTION_DEG`, `MOMENT_DRIFT`, `PENALTY_EV`). Remove the
`step1-prepare`, `step1-wrap-partner`, `step1-read`, `step1-row` and `step1-fit`
commands. Update `AGENTS.md`, `README.md` and `STATUS.md` where they describe
`step1.py`. `acceptance/`, `evidence/` and the archive are left untouched.

## TEN-01 leftovers

TEN-03 does not fix these. It keeps them visible and avoids blocking them:

1. `trace.trace_config` requires `<cso_dir>/provenance.json` with passing C0
   evidence, and nothing writes it. The writer belongs to the `dump_C` step in
   TEN-04. TEN-03 keeps the `config.json` `q_frac` contract that `trace_config`
   reads.
2. `gates.gate_n0` withholds acceptance on a hard-coded `Bi` species. TEN-04
   removes that check, which its STATUS row already says.

Both go into the TEN-04 row and the next action in STATUS.

## Tests

`tests/test_spiral.py`, three tests, replacing the four in `test_step1.py`, for a
total of 15:

1. **`test_seed_and_plan`.** A BFO material folder in `tmp_path`, built from the
   `bfo()` geometry in `test_symmetry.py` and moved to a shared `tests/fixtures.py`
   helper. The POSCAR is unwrapped: the second Fe is written at
   `(x - .5, x - .5, x - .5)`. Check that the plan line reports `R3c`, 6, 6, 0. The seed directions
   `(100), (010), (001)` fail the A condition (rank 1 of 2). `(111), (1-10), (100)`
   pass. The default choice passes with `min(sigma_D, sigma_A) >= 0.9`. A seed
   with an unknown key, and one with 2 values of `t`, are both rejected.
2. **`test_prepare_writes_paired_f0_inputs`.** Using the same folder, check that
   `2 Nd Nt + 1` runs are written. At `±q` the targets are Eq (3.1) recomputed
   from the written `QSPIRAL`, and the `-q` targets equal the `+q` ones with `y`
   negated. `q0` has `QSPIRAL = 0 0 0` and `LSPIRAL = T`. A material `INCAR` with
   `ISYM = 2` is rejected and named. `submit.sh` has `--array=1-N` with
   `N = len(runs.txt)` and passes `bash -n`.
3. **`test_readback`.** Synthetic `OUTCAR` and `OSZICAR` in the prepared runs,
   reusing the old repeated-table and mixed-solver OSZICAR layout. The energy
   line has irregular spacing and two matches, and the last one is taken. Moments
   rotated by a common 37° give `theta = 37` and `delta = 0`. A reversed site and
   an unconverged OUTCAR are each reported as not `ok`, and `collect` exits 1.

Injected faults the tests must catch: `inv(lattice.T)` in place of `inv(lattice)`,
phases computed from wrapped positions (`tau % 1`), phases computed from the
unrounded `q_frac`, a `-q` target equal to the `+q`
target, the first instead of the last TOTEN match, `MW_int` in place of `M_int`,
`theta` left out of `delta`, and removal of each `prepare` guard listed above
except the empty-file checks.

## Measured while drafting

From a scratch script using the TEN-02 test geometries:

| System | `p_A` | `(100),(010),(001)` | `(111),(1-10),(100)` | Default choice |
|---|---:|---|---|---|
| BFO `R3c` | 2 | `sigma_D .574`, `sigma_A 0` | `.344`, `.929` | `(01-1),(1-1-1),(111)`: `.909`, `.980` |
| FeGe | 1 | `1`, `1` | — | `(001),(010),(100)` |
| bcc Fe 2-site | 1 | `1`, `1` | — | `(001),(010),(100)` |
| Strained CrSb | 2 | `1`, `1` | — | `(001),(010),(100)` |

The BFO default includes the threefold axis `(111)`, which Section 8.2 recommends.
My first run of the script used `inv(lattice.T)` and found BFO's three axes at
rank 2. That error is why the convention is written out above and is one of the
injected faults.

## Done when

- All tests pass, and `dmi plan` on BFO reproduces the rank-1 failure of math
  Section 8.2.
- Every injected fault above is caught.
- `step1.py` and the `step1-*` commands are gone, with no remaining callers.
- `STATUS.md`, `CHANGELOG.md`, `AGENTS.md`, `README.md`, `docs/seed_file.md`, the
  D-013 amendment and a session log are updated.
- The user merges the pull request.

These tests show that inputs and readback follow Sections 3 and 8. They say
nothing about VASP. The first real runs are TEN-06.

## Decisions (user, 2026-11-08)

1. Delete `step1.py`. `sphere` and `check_run` move to `spiral.py`.
2. `RANK_FLOOR = 0.1`.
3. Keep both readback rules, `M_a >= 0.1 μB` and `abs(delta_a) < 90°`, until TEN-06.
4. `submit.sh` is spliced into a copy of `job.sh`.
5. Drop `dmi status`. Update `seed_file.md` and amend D-013 in one line.
6. Leave the `Bi` check in `gate_n0` for TEN-04.
7. Require `ENCUT` and `ENINI` in the material `INCAR` and print both in `plan`,
   with no gap check.
8. `--out` is required.

The user also added three rules: phases use unwrapped POSCAR positions; `RWIGS`
has one value per species type on POSCAR line 6; and `prepare` rejects a `job.sh`
whose body has its own `cd`.
