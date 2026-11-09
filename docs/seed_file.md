# Seed file format

One seed file describes one material and drives the whole workflow from D-013.
The format was agreed with the user on 2026-11-04 (D-016). The loader is built in
TEN-03. A real example is `materials/fe/seed.toml`.

## Folder layout

```text
materials/fe/
  seed.toml   what the pipeline needs to know
  POSCAR      structure, the main input
  INCAR       electronic settings only (ENCUT, ENINI, ISMEAR, SIGMA, RWIGS, U)
  KPOINTS     one mesh for every q
  POTCAR      never committed
```

The seed holds no machine paths, so it works on any machine and is safe to commit
to the public repo. The Slurm template is passed on the command line:

```bash
dmi plan    materials/fe/seed.toml
dmi prepare materials/fe/seed.toml --job job.sh --out RUNS
cd RUNS && sbatch submit.sh          # the user submits, as D-006 requires
dmi collect RUNS                     # one state per run; safe to rerun
dmi dumps   RUNS --job patchb.sh     # dump_C, dump_C_x, dump_C_y and each ok run's dump_P
cd RUNS && sbatch submit_dumps.sh    # the user submits
dmi trace   RUNS                     # provenance, trace vector, N0 I0 P0 E0 T3
dmi fit     ...                      # TEN-05
```

`--out` is required because the seed holds no paths. There is no `status`
command: `collect` prints one line per run (D-013).

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
exchange_grid = [4, 4, 4]                        # default: no exchange runs
rmax = 6.0               # exchange bond cutoff in Å
min_sigma = 0.05         # lowest SIGMA accepted, eV; lower only for a convergence series
```

## Fields

| Key | Required | Meaning |
|---|---|---|
| `sites` | Yes | Magnetic atoms, numbered from 1 in POSCAR order |
| `signs` | Yes | $\varepsilon_a=\pm1$, one per site |
| `moments` | Yes | Seed magnitude $m_a>0$ in $\mu_B$, one per site |
| `t` | Yes | Magnitudes in Å$^{-1}$; Section 8.3 asks for three per direction |
| `spacegroup` | No | Check on spglib's result, not an override |
| `symprec` | No | spglib tolerance in Å, default `1e-3` |
| `directions` | No | $\boldsymbol q_{\rm frac}$ directions; both rank conditions of Section 8.2 still apply |
| `exchange_grid` | No | Coarse $\Gamma$-centered grid of Section 8.4 |
| `rmax` | With `exchange_grid` | Bond cutoff in Å for Section 7.6 |
| `min_sigma` | No | Lowest `SIGMA` in eV that `plan` accepts, default `0.05`; lower it only for a smearing convergence series (D-018) |

The material `INCAR` must set `ISMEAR` to `-1`, `0` or `1` (Fermi-Dirac, Gaussian,
Methfessel-Paxton order 1) and `SIGMA` explicitly; `plan` prints both (D-018,
math Section 3.2).

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
- The code writes the run tags of math Section 3.2 itself. If the `INCAR` in the
  material folder contradicts one, stop and report the tag.
- Check the rank conditions on `directions` before writing any input.
