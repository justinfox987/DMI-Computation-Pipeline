# Simplify 1 spec: fewer operations, checks and documents

Status: decided on 2026-11-11. The user chose the anisotropy route and asked
Claude to choose the rest; the choices are at the end and in D-020 to D-025.
The math and the project records are updated. FIX-1 (Part 1) is merged in PR
#18. SIM-1a (D-021: items 2.2, 2.3, 2.4 and 2.6) is merged in PR #19. SIM-1b
(D-022, D-023 and the exchange seed keys: items 2.5, 2.7, 2.9 and 2.10) is in
review on `sim-1b-incar-fit`, so SIM-1 is complete pending that review. Part 2 below is
kept as written on 2026-11-10; where a choice differs from it, the Decisions
section wins.

Scope read: `pipeline v3/` at `454afa2` (branch `incar-user-settings`), the
plans, DECISIONS, STATUS, both math editions, the patched VASP source under
`vasp files/vasp-heide-patch-NEW/src`, and the real BFO q = 0 dumps in
`pipeline v3/noq/`.

Evidence labels: **run** means executed in a scratch copy with the 21 tests
passing first; **source** means read from VASP source; **estimate** is a line
count from function spans, not a finished diff.

## Part 1. Two defects found on the way

These are not simplifications. Fix them whatever is decided below.

### 1.1 The trace has the opposite sign to VASP's own SOC energy (source, run)

- `relativistic.F`, `SPINORB_STRENGTH`: VASP stores the operator reverted,
  `D(lm, l'm', a + 2a') = <a'| <l'm'| D |lm> |a>`. The first orbital index is
  the ket. The flip blocks are `2 = ud`, `3 = du`.
- `us.F` `DEPSUM` and `csodump.F` `COCC_FROM_INPUT` use one layout:
  `COCC(LP, L, 1 + s_ + 2s) += w f c(L, s) conj(c(LP, s_))`.
- `relativistic.F`, `CALC_SPINORB_MATRIX_ELEMENTS`: VASP's energy is
  `Re sum CSO(i,j,IS) * CONJG(COCC(i,j,IS))`.
- `trace.py:56` contracts `Lambda * COCC` with no conjugate. Every `Lambda` is
  imaginary and antisymmetric and every spin-diagonal `COCC` block is
  Hermitian, so dropping the conjugate flips the sign on all three axes.
- A bookkeeping test with exactly these layouts (random spinors, `xi L.S` on a
  p shell): VASP's formula returns `<H>`; `split_operator` + `trace_vector`
  return minus the exact `<sigma_z x Lambda_a>` for a = x, y, z; adding
  `.conj()` returns the exact values.
- The real BFO `CSO.dat` agrees with the reverted layout. The handedness
  `Im Tr([Lx, Ly] Lz) / Tr(Lz^2)^1.5` of the split triple is -0.707 on all six
  O ions, -0.523 on Fe and -0.440 on Bi. The emulation gives -0.707. A
  bra-first file would give +0.707.

Consequence: every `T`, so `D` and the predicted rotation sense, has the wrong
overall sign. Magnitudes, `F`, the pitch, N0, P0 and M1 are unaffected, which
is why no existing check saw it. The CPROJ oracle in `tests/fixtures.py` makes
the same bra-first assumption, so agreement with it does not test the sign.

Fix: `np.einsum("anij,nij->na", lam, magnetization.conj())`, the same change
in the oracle, and the rule text in AGENTS and the math ("contract elementwise,
not with a matrix trace") becomes "use VASP's form, `Re sum CSO * conj(COCC)`".
This is source reading plus a bookkeeping test, not a VASP run. The TEN-07
supercell control still confirms it, as a confirmation and not a calibration.

The same evidence settles the open "CSO flip-block order" input: handedness
is negative, the source says the orbital indices are reverted, so the flip
blocks are `ud, du` as `conventions.py` assumes.

### 1.2 The FERWE reader rejects every smeared state (run)

`dumpio.py:687-690` raises on any occupation that is not 0 or 1 within 1e-6,
and on any outside [0, 1]. D-018 now requires finite smearing, and bcc Fe is a
metal. Chain: `load_ferwe` raises, M1 fails on `q0/dump_P`, `trace_run("q0")`
has no passing provenance, N0 fails, `fit` refuses. Reproduced on the fixture:
0.7/0.3 gives "fractional FERWE", 1.04/-0.04 (Methfessel-Paxton) gives
"outside [0, 1]". TEN-06 cannot pass `dmi trace` as the code stands. Minimal
fix: delete those two checks. Item 2.3 removes the whole path.

### 1.3 Not a defect: the user's Fe INCAR stops `plan` twice (run)

`dmi plan materials/fe/seed.toml` stops on "Material INCAR sets MAGMOM", then
on "needs ENINI". With both edited in a scratch copy, `plan` and `prepare`
work and write 19 runs. Item 2.5 removes both stops.

## Part 2. Simplifications, largest first

| # | Change | Removes | Costs |
|---|---|---|---|
| 2.1 | One math document | 2 of 4 copies, about 1,700 lines | None |
| 2.2 | Recompute; trust no intermediate file | About 110 lines; 5 guard layers | One mtime check replaces them |
| 2.3 | M1 once per build, outside the package | About 600 lines + 150 fixture lines | Reverses part of D-011 |
| 2.4 | Handedness check replaces T3 | 2 VASP runs per tree, about 40 lines | T3 becomes optional, once |
| 2.5 | Code overrides its own tags, checks nothing else | About 60 lines, seed key `min_sigma` | Narrows D-018 |
| 2.6 | Read the last `M_int` block only | About 140 lines | Restart detection goes |
| 2.7 | One linear solve per tensor; measured noise | About 85 lines | Changes TEN-05 decisions 3, 4 |
| 2.8 | One anisotropy route, two directions | 12-17 runs, 2 math pages | Bare `K` not computed |
| 2.9 | Cut what no material uses | About 55 lines, 3 math subsections | Re-add on demand |
| 2.10 | Converge `A` from energies alone | About 4 of 5 Fe trees | None |
| 2.11 | Optional: dump at the end of the SCF | One job and one WAVECAR per state | Patch rebuild |

Estimate: package 2,537 lines to roughly 1,200-1,400; tests 1,080 to roughly
600; the 22-page project math copy toward 14 pages.

### 2.1 One math document

There are two different documents called Revision 3.1:

- `docs/math/heide_math_v3.tex`, 9 November: adds the smearing row. Keeps the
  3.0 numbering. The code and every spec cite this numbering.
- Project `claude/heide_math_v3.tex`, 6 November: adds Section 1.1 and a
  Section 10 on anisotropy. It moves Eqs (1.2)-(1.4) to (1.3)-(1.5) and
  Sections 10-12 to 11-13, so every citation in the code would be off by one.

Proposal: the repository TeX is the only source. Anisotropy enters as a new
last section, so no number moves, in the short form of 2.8. The project copy is
replaced by the repository file. `heide_math_v3.md` (709 lines kept in step by
hand) shrinks to its agent notes, moved into AGENTS.md. `heide_math_v2.tex`
leaves the tree; the tag keeps it.

Related drift, for the user's process choice: README's status paragraph says
`trace` and `fit` are not implemented and the suite has 16 tests; STATUS says
cleanup 1 is pending, and it is merged. Five records per change (spec, session
log, STATUS, CHANGELOG, DECISIONS) is where that comes from. Minimum fix: README
carries no status.

### 2.2 Recompute instead of guarding

A file can change between two commands, and the code guards that five ways:
`config.json` against INCAR, the OUTCAR echo, SHA-256 in `collected.json`
rechecked by `dumps`, `trace` and `fit`, `parent.json` with link size and mtime,
and `provenance.json` with `require_done`. `fit` also rebuilds the symmetry and
compares it with `plan.json`.

Loading one real 1 MB dump takes 0.05 s (run). So `fit` can read every OUTCAR,
OSZICAR, COCC and CSO each time. `collected.json` and `traces.json` remain as
reports and are never inputs. Nothing is stale by construction. Commands:
`plan`, `prepare`, `collect` (prints status only), `dumps`, `fit`. Keep one
guard, because a parent rerun after its dump is a real mistake: `COCC.dat`
must be newer than its parent's OUTCAR. Hashes for an evidence record come from
`sha256sum` when archiving.

### 2.3 M1 once per build

M1 compares `COCC.dat` with a Python rebuild from CPROJ and FERWE. It tests
the Fortran routine `COCC_FROM_INPUT`, which is a line-for-line copy of VASP's
`DEPSUM` (source). That is a property of the build, not of a material.
`acceptance/manifest.json` already records M1 passing at 5.3e-15 on the real
BFO dump. Yet `dmi dumps` sets `LDUMPCPROJ` on `q0` of every tree (0.3 GB at
BFO size), and the readers for it are 600 of the package's lines: nine
dataclasses, a probe over 8 ABI combinations, rank-file assembly and the FERWE
cross-checks.

Proposal: a standalone `acceptance/m1.py` with a fixed little-endian
`i4`/`f8` layout that fails on a bad magic string. Run it once per production
build. The package keeps `load_cso` and `load_cocc` (about 150 lines).

### 2.4 Handedness replaces T3

`prepare_dumps` writes `dump_C_x` and `dump_C_y` for every tree, including each
convergence tree, to pin one bit: the flip-block order. Around it sit
`gate_t3`, the "provisional `T_y`" strings, `y_flip_visible` and
`F_flipped_norm`. Item 1.1 pins the same bit from one z dump with no VASP run.
Proposal: one check in C0, "the split triple is left-handed on every ion", and
delete the rest. The x and y decks can be written by hand once if an
independent confirmation is wanted.

This also removes two open inputs: whether the x and y decks accept `q0`'s
CHGCAR, and how they read its magnetization.

### 2.5 The code owns eleven tags and checks nothing else

The code writes `LNONCOLLINEAR`, `LSPIRAL`, `LSORBIT`, `LZEROZ`, `SAXIS`,
`ISYM`, `I_CONSTRAINED_M`, `LAMBDA`, `QSPIRAL`, `MAGMOM` and `M_CONSTR`.
Proposal: it overrides those and prints one line per override. It stops
requiring `ENCUT`, `ENINI` and `RWIGS`, stops rejecting `KSPACING`, and drops
the `INCAR_TAGS` list, the unseen-tag warning, the `SIGMA` floor and
`min_sigma`. One physics rule stays: tetrahedron smearing is refused, because
its energy is not variational. This is D-019 taken to its end, and it narrows
D-018 to that one rule.

### 2.6 Read the last `M_int` block

`sphere` and `check_run` are 129 lines. They parse ionic steps, restarts, the
`E_p`/`lambda` line and the `lambda*MW_perp` field block, which served
constrained and relaxing runs. Every run is now static at `LAMBDA = 0`. A
12-line reader (last `ion MW_int M_int` block, "EDIFF is reached", the timing
footer, last `TOTEN`) returns the same `M_int` as the current code on both real
sample runs, `Fe_q0_test/q0` and `reader_test_2` (run). `echo_check` (21
lines) goes too: the dump file existing with the right header is the proof that
VASP read a dump flag.

`M_int` no longer enters any fit. It is a check that the state is the intended
spiral. Keep three tests: no collapsed moment, no reversed site (pair phase,
which also fixes the sense of rotation), and `|M_z|` small.

### 2.7 One solve per tensor, with measured noise

The fit is linear end to end. One design matrix with the tensor components
and one cubic nuisance per direction and axis reproduces the current
`D_free`, `D`, `F` and `A` to 1e-12 relative on the FeGe and BFO spin models
(run; about 30 lines against about 85). It replaces `fit_directions`, `propagate`,
the four closures, `slope_row` and the pooling.

Noise: the current sigma is pooled from fits with one degree of freedom each
(9 in total for `y`, 3 for `g`). The pairs already measure it directly: the
even part `[T(q) + T(-q)]/N_m` and `[E(q) - E(-q)]/2N_m`. On the noisy BFO
model, with true sigma 1.41e-6, the parity value is 1.32e-6 from 27 samples
and the pooled value is 1.59e-6 from 9 (run). Proposal: sigma is the RMS
parity residual, one number for `y` and one for `g`. Drop the
`poorly_determined` flag and `MIN_PAIRS` logic.

The rank test becomes "the design matrix has full column rank", which also
allows fewer than three directions when `p_D` is small.

### 2.8 Anisotropy: one route, two directions

Revision 3.1 (project copy) plans two routes, five directions, a fourth-order
form, a canting closure test and a k series: 15-20 runs. The functional needs
one number for a uniaxial magnet, `K_c = E_par - E_perp`.

Proposal: self-consistent SOC total energies along the axis and one in-plane
direction, plus one `-m` repeat as the noise floor. Three runs, no pipeline
code: the user runs them and gives `K_c` to `fit`, which reports
`r^2 = (pi^2/4) |e*| / |K_c|`. This route has no force-theorem step and
includes the canting, so it is the `K` the functional uses and needs no
canting estimate. The cost is that the bare value, which is what Xu computed,
is not produced; add two `ICHARG = 11` runs only if that comparison is wanted.
Cubic groups have no quadratic term and skip this. The judgment here is the
user's: which `K` the paper reports.

### 2.9 Cut what no current material uses

- Exchange classes: `exchange_grid` and `rmax` are parsed, validated and
  counted, but `prepare` writes no grid run and `fit` fits no `J_c`. Remove
  the keys, `exchange_classes`, and math Sections 7.6 and 9.3 with the
  mean-field temperature.
- Twist count: the SCF is unconstrained, so twist is handled without it.
  `twist_count` only switches a 1 degree gate. Report `delta_a` and drop the
  gate and math Section 7.5; Section 2.3 already states the reason.
- Math Section 10.2's linear magnon term and Section 10.3's cone field: no
  code uses them. `D_sw = 4A/M` stays, for the Fe comparison.
- `conventions.UNDETERMINED` and the `VASP_BUILD_ID` pin (never set),
  `GateResult`, the atomic `manifest.save`, and the Slurm header splicing
  (copy `job.sh` into each run and list the directories instead).

### 2.10 Converge `A` from energies alone

TEN-06 plans four to five full trees for the k and t series, each 19 SCFs and
22 dumps. `A` needs no dump, and bcc Fe has `p_A = 1`, so one direction
determines it: 7 SCFs per mesh. Run the full tree once, at the chosen mesh.
With 2.7, `fit` prints `A` when a tree has no dumps.

### 2.11 Optional: dump at the end of the SCF

`dump_P` rereads the parent WAVECAR and dumps before the first iteration. The
same routine called after the loop of the SCF itself gives the same density
matrix in double precision. That removes one job and one WAVECAR per state
(6 GB each at the BFO sample size), and the `DUMP_P` deck and parent tracking.
It needs one more hook in `main.F`, a rebuild, and one comparison of the two
dumps on one state. Given the open executable question in STATUS, this waits
for the user.

## What stays

First-order SOC on frozen SOC-free states; unconstrained F0 at `LAMBDA = 0`;
both signs of `q`; three magnitudes; the free fit and its forbidden part; N0,
I0, P0, E0 and C0; the symmetry module; the seed file; the direction chooser.

## Decisions (2026-11-11)

| Item | Choice | Record |
|---|---|---|
| 1.1 Trace sign | Fix now, on its own branch with 1.2 (FIX-1) | D-020 |
| 1.2 FERWE reader | Fix now: delete the two occupation checks; the reader then leaves the package in SIM-1 | D-021 |
| 2.1 One math document | Yes. Repository TeX only, now Revision 3.2; the Markdown file holds agent notes; anisotropy is Section 13 | D-025 |
| 2.2 Recompute | Yes, with the one mtime guard | D-021 |
| 2.3 M1 once per build | Yes, as `acceptance/m1.py` | D-021 |
| 2.4 Handedness replaces T3 | Yes; T3 optional by hand | D-021 |
| 2.5 INCAR | Yes: override eleven tags, refuse tetrahedron smearing, check nothing else | D-022 |
| 2.6 Last `M_int` block | Yes | D-021 |
| 2.7 One solve, parity noise | Yes | D-023 |
| 2.8 Anisotropy | The user's choice: self-consistent route, five runs, a coded module, built later (`plans/anisotropy-1.md`) | D-024 |
| 2.9 Exchange classes | **Changed from the proposal.** Exchange is a project goal, so the math keeps Sections 7.6 and 9.3 for a later task. Only the half-built seed keys and the plan count leave the code | D-025 |
| 2.9 Twist count and gate | **Changed from the proposal: kept.** When symmetry forbids twist, a nonzero phase means a wrong or unconverged state, and the check costs 15 lines | D-025 |
| 2.9 Small dead code | Remove: the build-id pin, `GateResult`, the atomic save, the Slurm header splicing stays (one array job is worth its 34 lines) | SIM-1 |
| 2.10 Converge `A` from energies | Yes; TEN-06 is revised | TEN-06 |
| 2.11 Dump at the end of the SCF | **No, not now.** The executable question in STATUS is open, and a patch change before the first pilot adds risk. Revisit after Gate 2 | none |

## Order of work

1. **FIX-1**, done (PR #18): the conjugate in `trace_vector` and in the test
   oracle, the layout test of math Section 4.4 as a new test, and the two FERWE
   checks deleted.
2. **SIM-1**, done pending review: SIM-1a (D-021, PR #19), then SIM-1b (D-022,
   D-023, the exchange seed keys and item 2.10, on `sim-1b-incar-fit`). The
   suite is 15 tests, not the 12 estimated. `docs/seed_file.md` lost
   `min_sigma`, `exchange_grid` and `rmax` in SIM-1b.
3. **TEN-06**, the Fe pilot, as revised.
4. **ANI-1**, the anisotropy module, after the spiralization tensor works.
