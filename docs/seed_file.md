# Seed file format

One seed file describes one material and drives the whole workflow from D-013.
The format was agreed with the user on 2026-11-04 (D-016). The loader is built in
TEN-03. A real example is `materials/fe/seed.toml`.

## Folder layout

```text
materials/fe/
  seed.toml   what the pipeline needs to know
  POSCAR      structure, the main input
  INCAR       the user's settings (D-019); see the INCAR rules below
  KPOINTS     one mesh for every q
  POTCAR      never committed
```

The seed holds no machine paths, so it works on any machine and is safe to commit
to the public repo. The Slurm template is passed on the command line:

```bash
dmi plan    materials/fe/seed.toml
dmi prepare materials/fe/seed.toml --job job.sh --out RUNS
cd RUNS && sbatch submit.sh          # the user submits, as D-006 requires (or run.sh, below)
dmi collect RUNS                     # one state per run; safe to rerun
dmi dumps   RUNS --job patchb.sh     # one z-axis dump_C and each ok run's dump_P
cd RUNS && sbatch submit_dumps.sh    # the user submits (or run_dumps.sh, below)
dmi fit     RUNS                     # trace, C0 N0 I0 P0 E0 and, with inversion, the null at every q;
                                     # then D, F, A, the pitch, 4A/M_int and 4A/M_total, and units,
                                     # and the Fit check of each solve
                                     # with no dump_C yet: A, D_sw, E0 and Fit A only (energies-only)
```

After the tensors, `fit` prints one Fit line per solve (`A`, and `D` and
`D_free` when traced; math Section 11, D-026). It tests whether the series in `t`
describes the data, which the parity sigma cannot see:

```text
Fit A  pass, worst residual 0.0012 meV of bound 0.063 meV
Fit A  FAIL: d1_t1 residual +0.258 meV, bound 0.0641 meV
Fit A  not evaluated: exactly determined
```

A FAIL names the worst pair (and the axis for `D`). The tensors are still
reported, but `fit` exits 1 and `tensors.json` has `passed` false. Each solve's
check and residual vector are under `fit_check` in `tensors.json`.

`prepare` writes two launch scripts over `runs.txt`, and `dumps` the same two
over `dumps.txt`. Both keep the job script's `#SBATCH` header and run its body
in each listed directory:

| Script | Runs | Start it from the run directory with |
|---|---|---|
| `submit.sh`, `submit_dumps.sh` | a Slurm array, one task per directory | `sbatch submit.sh` |
| `run.sh`, `run_dumps.sh` | one directory at a time in one allocation | `sbatch run.sh`, or `bash run.sh` inside `salloc` |

`run.sh` skips a directory whose OUTCAR has VASP's timing footer, so starting it
again resumes the list; a failed run does not stop the others, and the script
exits 1 if any run failed. Its limits: the time limit covers the whole sequence;
a run cut off mid-SCF is redone from scratch on the next start; and one slow run
delays the rest.

`--out` is required because the seed holds no paths. There is no `status`
command: `collect` prints one line per run (D-013). Every command reads the VASP
files again; `collected.json`, `traces.json` and `tensors.json` are reports that
no command reads back (D-021). M1 is not part of the workflow: it runs once per
build as `python acceptance/m1.py DUMP_P_DIR`.

## Example

The site, sign and moment values come from the old Fe pilot. The `t` values are
the math document's BFO-scale first guess, so they are placeholders for Fe.

```toml
# Required
sites = [1, 2]           # magnetic atoms, numbered as in POSCAR
signs = [1, 1]           # order parameter sign per site
moments = [2.2, 2.2]     # seed moment per site, in Bohr magnetons
t = [0.03, 0.06, 0.09]   # spiral magnitudes in 1/Å

# Optional
spacegroup = 229         # stop if spglib finds a different group
symprec = 1e-3           # symmetry tolerance in Å
directions = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]   # q_frac; default: code chooses
```

## Fields

| Key | Required | Meaning |
|---|---|---|
| `sites` | Yes | Magnetic atoms, numbered from 1 in POSCAR order |
| `signs` | Yes | $\varepsilon_a=\pm1$, one per site |
| `moments` | Yes | Seed magnitude $m_a>0$ in $\mu_B$, one per site |
| `t` | Yes | Magnitudes in Å$^{-1}$; Section 8.3 asks for three per direction. The loader sorts them ascending, so run `d{i}_t1` is always the smallest `t`, where P0 and E0 gate |
| `spacegroup` | No | Check on spglib's result, not an override |
| `symprec` | No | spglib tolerance in Å, default `1e-3` |
| `directions` | No | $\boldsymbol q_{\rm frac}$ directions. Fewer than three are allowed (see below) |

Without `directions`, the code chooses $\max(3,p_A)$ low-index directions, so
$\mathcal D_{\rm free}$ and its forbidden part are always evaluated. Explicit
`directions` may be fewer than three when the constrained-$\mathcal D$ and $A$
fit designs pass the rank test below (math Section 9.4). If the $\mathcal D_{\rm free}$
design then lacks full rank, `plan` says so, and `tensors.json` reports
$\mathcal D_{\rm free}$, $\mathcal F$ and the Forbidden check as not evaluated.
A cubic material ($p_A = 1$) can be converged from one direction this way.

## INCAR rules

The `INCAR` belongs to the user (D-019, D-022). The code owns eleven tags and
writes its own value for each: `LNONCOLLINEAR`, `LSPIRAL`, `LSORBIT`, `LZEROZ`,
`SAXIS`, `ISYM`, `I_CONSTRAINED_M`, `LAMBDA`, `QSPIRAL`, `MAGMOM` and
`M_CONSTR` (math Section 3.2). Where the material `INCAR` sets one of them
differently, `plan` and `prepare` print one `override` line with the user's
value and the value used, and continue. One rule is checked: `ISMEAR = -4` or
`-5` (tetrahedron) is refused, because its energy is not variational and the
force theorem does not hold. Every other tag, including its absence, is the
user's choice and is passed through unchanged. `plan` prints `ENCUT`, `ENINI`,
`ISMEAR` and `SIGMA` when the `INCAR` sets them. The dumps need the parent's
`WAVECAR` and `CHGCAR`, so leave `LWAVE` and `LCHARG` at `T`.

## Rules

- Parse with `tomllib` from the standard library; `pyproject.toml` requires
  Python 3.11 or later, so this adds no dependency.
- Reject unknown keys. A mistyped `spacegroups` must not be ignored silently.
- `sites`, `signs` and `moments` must have equal lengths.
- Sites are 1-based only in this file. The loader converts them to the 0-based
  indices used in the code.
- The `plan` output starts with the group spglib found and the kept and dropped
  operation counts. This is the only protection from a wrong group when
  `spacegroup` is left out, so set `spacegroup` for production runs.
- Check the rank conditions on `directions` before writing any input: the
  tensor columns of the constrained-$\mathcal D$ and $A$ fit designs, one row
  block per direction with `t` set aside and each column scaled to unit norm,
  need smallest singular value at least `RANK_FLOOR = 0.1`, and every direction
  needs two or more distinct magnitudes (math Section 9.4). `plan` prints the
  values. In `fit`, a direction with complete pairs at fewer than two
  magnitudes is dropped.
