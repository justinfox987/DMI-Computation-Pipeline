# TEN-06 spec: bcc Fe pilot at lambda 0 (Gate 2)

Physics authority: `docs/math/heide_math_v3.tex` (Revision 3.2), Sections 3, 4,
8, 9, 11 and 12. Workflow: `plans/ten-03-spiral.md`, `plans/ten-04-trace.md` and
`plans/ten-05-tensors.md`, as merged with cleanup 1 (`b082893`). Seed format:
`docs/seed_file.md`. Input ownership: D-019 (pending on `incar-user-settings`).

Status: draft for user review, 2026-11-09, revised with the user's answers, and
revised again on 2026-11-11 for D-020 to D-023 (`plans/simplify-1.md`). **This
pilot needs FIX-1 and SIM-1 merged first:** as the code stands at `454afa2`, the
FERWE reader rejects a smeared metal and `dmi trace` cannot pass.
Nothing has run. When it is approved, and the user has added their inputs to
`materials/fe/`, work on `ten-06-fe-pilot` from `main`. The user submits every job
(D-006). No agent contacts the cluster.

## Purpose

bcc Fe keeps inversion, so `D = 0` and `y_a(q) = 0` at every `q` (Sections 7.3
and 11). That makes it the null test: it is the first time `collect`, `dumps`,
`fit` read VASP output. It also settles two VASP facts left open by TEN-04:

1. whether `LDUMPCOCC` works without `LDUMPCPROJ`;
2. whether the `LSORBIT = T` CSO dump accepts `q0`'s `LSPIRAL = T` `CHGCAR`
   with `ICHARG = 11`.

The two facts about `dump_C_x` and `dump_C_y` are gone with those dumps
(D-021). The flip-block order is fixed by the handedness check in C0.

It gives the first wall times and a spin-wave stiffness to compare with
experiment.

## Material folder `materials/fe/`

The user supplies `POSCAR`, `INCAR`, `KPOINTS` and `POTCAR`. They are committed
as given, except the `POTCAR`, which is never committed. A `POTCAR.spec` with the
dataset name, TITEL and SHA-256 is committed in its place; `.gitignore` already
allows it. The structure, functional, potential, cutoffs, smearing, spheres, SCF
settings and parallel tags are the user's choices (D-019). This spec does not
set them.

Factual notes for those choices:

- In the bcc cell, spheres with `RWIGS` above `sqrt(3) a / 4` overlap. That is
  1.2397 Å for `a = 2.86304 Å`. Overlap enters `M_int`, and so `4A/M_int`. The
  comparison with experiment below uses `M_total` for that reason.
- Section 3.2: `ENCUT` about 100 eV above `ENINI`, as the VASP wiki advises.
  `plan` requires both, prints them and does not check the gap (TEN-03).
- VASP advises `LMAXMIX = 4` for d-electron systems when a run reads `CHGCAR`
  with `ICHARG = 11`. Every dump reads it that way (TEN-04).
- After SIM-1 the code does two things with the INCAR, and nothing else
  (D-022): it overrides the eleven tags it owns, printing one line per
  override, and it refuses tetrahedron smearing. The dumps need `LWAVE` and
  `LCHARG` left `T` (their default).

### seed.toml

Committed by this task. Only `t` changes from the current file:

```toml
# bcc Fe, 2-site conventional cell: the Gate 2 null test (TEN-06).
sites = [1, 2]
signs = [1, 1]
moments = [2.2, 2.2]
t = [0.05, 0.10, 0.15]   # 1/Å; see the convergence plan

spacegroup = 229
symprec = 1e-3
```

`sites = [1, 2]` assumes the user's POSCAR is the 2-site conventional cell,
with Fe on both sites. If it is the 1-site primitive cell, `sites`, `signs` and
`moments` become one value each, and nothing else changes. `directions` is
left to the code: for `Im-3m` with `p_A = 1`, the chooser takes
`(001), (010), (100)`. That gives 19 SCFs and 20 dumps (19 `dump_P` and one
`dump_C`) for the full tree.

## Convergence plan

Fe is a metal with long-range RKKY exchange. Section 8.4 asks for a k-mesh
series, and Section 8.3 bounds `t` from both sides. The table estimates the
stiffness signal per site as `A t^2`, with `A ≈ 154 meV Å²` (from
`D_sw ≈ 280 meV Å²` and `M = 2.2`). It is an estimate, not a result.

| `t` (1/Å) | 0.03 | 0.05 | 0.06 | 0.09 | 0.10 | 0.15 |
|---|---|---|---|---|---|---|
| `q_frac` along (001), `a = 2.863 Å` | 0.014 | 0.023 | 0.027 | 0.041 | 0.046 | 0.068 |
| `A t^2` (meV per site) | 0.14 | 0.39 | 0.55 | 1.25 | 1.54 | 3.47 |

`A` needs no dump, and `p_A = 1`, so one direction determines it. Each
convergence step is therefore an energies-only tree with
`directions = [[0, 0, 1]]`: 7 SCFs, no dumps, and `fit` prints `A` alone
(`plans/simplify-1.md` item 2.10). The full tree runs once, at the chosen mesh
and `t`:

1. **k series** at `t = 0.05, 0.10, 0.15`: Γ-centred meshes `N = 12, 16, 20, 24`,
   built from the user's KPOINTS by changing only `N`. Converged when `A`
   changes by less than 5% between the last two meshes. Gate 2.3 is then
   evaluated on the full tree at the chosen mesh. If `N = 24` is still moving, add 28.
2. **t series** at the chosen `N`: `t = 0.03, 0.06, 0.09` against
   `0.05, 0.10, 0.15`. Consistent when `A` agrees within `2 sigma + 5%`.

Variants differ only in `KPOINTS` or `t`. On the cluster, each variant is an
uncommitted copy of the material folder (`fe-k12/`, `fe-t03/`, ...) next to the
run trees. Only the chosen `t` is committed to `materials/fe/seed.toml`. If the
user's chosen mesh differs from the committed `KPOINTS`, that is the user's file
to replace.

## Command sequence

These run on Perlmutter, from a checkout of `main` with the package installed in
a virtual environment. `$FE`, `$JOBS` and `$RUNS` are the user's paths and appear
in no committed file.

```bash
dmi plan    $FE/seed.toml
dmi prepare $FE/seed.toml --job $JOBS/scf.sh --out $RUNS/fe-k20
cd $RUNS/fe-k20 && sbatch submit.sh                 # 19 SCFs
dmi collect $RUNS/fe-k20                             # all 19 must print ok
dmi dumps   $RUNS/fe-k20 --job $JOBS/patchb.sh
cd $RUNS/fe-k20 && sbatch submit_dumps.sh            # 20 dumps
dmi fit     $RUNS/fe-k20                             # reads everything: C0, N0, I0, P0, E0, D, F, A, D_sw, the null check
```

For the 2-site cell, the first two lines `plan` prints must be:

```text
space group 229 (Im-3m) at symprec 0.001: 96 operations, 96 kept, 0 dropped
p_D 0  p_A 1  n_twist 0
```

That is the TEN-02 table, and it was checked by running `plan` on a 2-site
test folder. For the primitive cell, it is 48 operations. Any other group stops
the pilot.

`scf.sh` and `patchb.sh` each run `vasp_ncl` in their working directory and
contain no `cd`. Both use the same Patch B executable (decision 11), so one build
identity covers the SCFs and the dumps. Wait for each array to finish before the
next command. `collect` and `fit` read the VASP files again each time, so
they are safe to rerun.

**M1 for this build.** M1 runs once per build (D-021). If the executable is not
the 14 September build that already passed, add `LDUMPCPROJ = T` to
`q0/dump_P/INCAR` by hand before submitting, and run `acceptance/m1.py` on
that directory afterwards.

## Code in this task

Two small additions, with no new test, on top of the SIM-1 code.

1. **Centrosymmetric null** (decision 13). When the operations `dmi fit`
   rebuilds contain `-I`, every `abs(T_a)` over every run, axis and ion must be
   below `N0_FLOOR_EV`. Otherwise `fit` exits 1. This is about 10 lines in
   `tensors.py` and `gates.py`, plus one assertion in `test_fit_command`.
2. **Total moment for `D_sw`** (decision 7).
   - `collect` also reads the `mag=` vector on `q0`'s final OSZICAR `F=` line
     and stores `M_total = |mag| / N_m` per site.
   - `fit` reports `4A/M_int` and `4A/M_total` side by side.
   - This is a few lines in the OSZICAR reader and `tensors.fit`, plus one
     assertion added to the readback test and one to the fit test.
   - The synthetic OSZICAR fixture gains a `mag=` field.
   - The `mag=` line is a VASP format fact that the first real `q0` OSZICAR
     confirms. Until then the reader is tested on the fixture only.

## Gate 2

Each item is evaluated on the tree at the converged settings. The evidence record
says which ones pass, which fail, and which were not evaluated.

| Item | Requirement | Source |
|---|---|---|
| 2.1 Tree health | Every run `ok` in `collect`: converged, pair phase, `abs(delta_a) < 1°` (`n_twist = 0`), `M_a` within 5% of `q0`, `abs(M_z) < 0.05 μB` | `collected.json` |
| 2.2 Dumps | COCC exists in every `dump_P` without `LDUMPCPROJ`, and is newer than its parent's OUTCAR, which settles fact 1. C0 passes on `dump_C`, including `h < 0` on every ion, which settles fact 2. M1 has passed for this build | `traces.json`, the M1 record |
| 2.3 Null at every `q` | The centrosymmetric null check passes | `tensors.json` |
| 2.4 N0, P0, E0, I0 | All pass in `dmi fit` | `traces.json` |
| 2.5 Noise | `sigma_y` and `sigma_g` from the parity residuals (D-023) are recorded | `tensors.json` |
| 2.6 `D = 0` | `p_D = 0`, so `F = D_free`, and the Forbidden check passes: every `abs(D_free_ij) <= 3 sigma`, with that `sigma_y` | `tensors.json` |
| 2.7 `A` and `D_sw` | `A` is positive and isotropic (`p_A = 1`) and converged per the plan. `4A/M_total` lies in the plausible window 200–400 meV Å². Its deviation from the experimental range is recorded, not gated. `4A/M_int` is reported alongside | `tensors.json` |
| 2.8 Wall times | Recorded per SCF and per dump | `OUTCAR` `Elapsed time` |

**Experimental reference for 2.7.** bcc Fe spin-wave stiffness from experiment
is 270–350 meV Å². Examples are Stringfellow, J. Phys. C 1, 950 (1968), 314 meV Å²,
and Loong et al., J. Appl. Phys. 55, 1895 (1984), 307 meV Å², as compiled by
Šipr et al., arXiv:2001.02558. These citations come from the user and have not
been checked here. `4A/M_total` is the one compared, because it does not depend
on `RWIGS`.

A failure in 2.2 caused by VASP rejecting the CSO deck means using the
fallback agreed in TEN-04 (a separate `LSPIRAL`-free reference SCF). That is a
new decision, not a silent change.

## Evidence record

One directory per converged tree, `evidence/2026-11-DD-fe-ten06-pilot/`, under
the `evidence/README.md` rules. It holds:

- `README.md` with:
  - the commit hash;
  - the build banner of the Patch B executable, and its SHA-256 if the user can
    supply it (otherwise "unknown");
  - the POTCAR TITEL and SHA-256;
  - the run-tree path on the cluster;
  - the k- and t-series tables (`A`, both `D_sw`, `sigma`);
  - each Gate 2 item as pass, fail or not evaluated, with its threshold;
  - wall times;
  - the two VASP facts as found;
  - the job scripts' resources.
- Copied unchanged: `plan.json`, `collected.json`, `traces.json`,
  `tensors.json`, and the `submit.sh` and `submit_dumps.sh` as run.
- `q0/dump_P/COCC.dat` and `dump_C/CSO.dat` (decision 14), the first real dump
  files in the repository. They are about 1 MB together.
- `hashes.txt`: `sha256sum` of every `OUTCAR`, `OSZICAR`, `COCC.dat` and
  `CSO.dat` that stays on the cluster, taken when the record is made.

`WAVECAR`, `CHGCAR`, `CPROJ` and the other dumps stay on the cluster. The
convergence trees are summarized in the README tables, with their paths and the
hashes of their JSON files. Their JSON files are not committed.

No number in the record is typed in by hand. Every value comes from the copied
JSON files or from a command the README shows.

## STATUS and docs (in this branch)

- STATUS: Gate 2 outcome per item and the two VASP facts, moved from Unresolved
  inputs to Established or to a blocker. Next action: TEN-07 if Gate 2 passes,
  or the named failure if it does not.
- CHANGELOG and a session log.
- `materials/fe/seed.toml`: the chosen `t`, and the comment updated.

## Done when

- The converged tree's Gate 2 items are recorded as pass, fail or not evaluated,
  in `evidence/`.
- `materials/fe/` holds the user's inputs and the chosen `t`.
- The two code additions pass their assertions.
- STATUS reflects the two VASP facts.
- The user merges the pull request.

Gate 2 is VASP evidence for one centrosymmetric metal. It says nothing about the
sign or size of a nonzero `D`; that is TEN-07.

## Decisions (user, 2026-11-09)

The structure, potential, functional, cutoffs, smearing, `RWIGS`, SCF settings
and parallel tags are the user's (D-019). They are not part of this spec.

7. Report `4A/M_int` and `4A/M_total`, with `M_total` per site from OUTCAR or
   OSZICAR. Compare `4A/M_total` with experiment.
10. Convergence variants are uncommitted copies of the material folder on the
    cluster.
11. The SCFs and the dumps use the same Patch B executable.
12. The plausible window is 200–400 meV Å², with the deviation from the
    270–350 meV Å² experimental range recorded and not gated. Citations are as
    above.
13. Add the centrosymmetric null check to `dmi fit`.
14. Commit `q0`'s `COCC.dat` and `dump_C`'s `CSO.dat` with the evidence record.
15. `t = 0.05, 0.10, 0.15` is the primary set, with `0.03, 0.06, 0.09` as the
    comparison.
16. The k series is `N = 12, 16, 20, 24`, extended to 28 if needed, and
    converged at 5% in `A`.
