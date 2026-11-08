# TEN-04 spec: dumps, the trace vector and the Section 11 checks

Physics authority: `docs/math/heide_math_v3.md`, Sections 4, 5 and 11. Run layout
and readback: `plans/ten-03-spiral.md`. This file fixes the interfaces, the guards
and the tests. It does not restate the equations.

Status: approved by the user on 2026-11-08, with the decisions at the end. Work
on `ten-04-trace` from `main` (`dba823d`, TEN-03 merged).

## Scope

1. `dmi collect` gains the Section 11 SCF-and-state checks. A run that fails them
   is not `ok`, so it gets no dump.
2. `dmi dumps DIR --job job.sh` writes a `dump_P` under every `ok` run, plus
   `dump_C`, `dump_C_x` and `dump_C_y` from `q0`'s `CHGCAR`, with their own Slurm
   array (Section 5).
3. `gates.finish(dump_dir, kind)` writes each dump's `provenance.json`. It runs
   C0, M1 and T3, and it rejects a dump whose linked parent files changed.
4. `trace.split_operator` and `trace.trace_vector` implement Eqs (4.4) and (4.8)
   from COCC. `trace.trace_run` replaces `trace.trace_config`.
5. `dmi trace DIR` runs `finish`, then traces every `ok` run and applies N0, I0,
   P0 and E0. It writes `DIR/traces.json`.
6. T3 is rewritten to the Section 11 form. The Euler search goes, and so does
   `cso.py`.
7. `gate_n0` loses its species argument and the hard-coded `Bi` check.
8. STATUS is reconciled for the TEN-03 merge.

Out of scope: `y`, `g`, fits and units (TEN-05). Nothing here divides by `N_m`.
Exchange-grid runs are TEN-09.

## TEN-01 leftovers, all three

STATUS lists two. Reading `trace.py` turned up a third:

1. `trace_config` reads `<cso_dir>/provenance.json` with a passing C0, and nothing
   writes that file.
2. `trace_config` calls `manifest.require_done(dump_P, "dump_P")`, which reads a
   `DONE` marker. Its writer, `finish`, was deleted with the runner in TEN-01
   (`f57c366`). Nothing writes `DONE` or the `FAILED` marker it also checks.
3. `gate_n0` withholds acceptance on species `Bi`.

The fix is one evidence file per dump directory, `provenance.json`. One function
writes it (`gates.finish`) and one reads it (`manifest.require_done`, which now
reads `provenance.json` instead of `DONE`). The `FAILED` marker is dropped: a
failed check writes `"passed": false`.

## Collect: Section 11 SCF-and-state checks

`spiral.collect` applies these checks after reading every run, using `q0`
(always first in `runs.txt`) and `n_twist` from `plan.json`:

| Rule | Applies to |
|---|---|
| `abs(delta_a) < 1°` on every magnetic site | Runs at nonzero `q`, when `n_twist = 0`. Otherwise `delta_a` is recorded only, because Section 11 expects it to be linear in `q` |
| `abs(M_a / M_a(q0) - 1) < 0.05` on every magnetic site | Every run except `q0`. If `q0` is not `ok`, every other run fails with `"q0 not ok"` |
| `abs(M_int z) < 0.05 μB` on every magnetic site | Every run |

These checks join the TEN-03 per-run guards (convergence, `lambda = 0`, the
collapse floor and the pair phase). A failing run gets `"error"` in
`collected.json`, so `collect` exits 1 and `dumps` skips it. The constants live
in `spiral.py` with the others: `TWIST_FREE_DEG = 1.0`, `MOMENT_DRIFT = 0.05`
and `MZ_MAX = 0.05`.

## Dump inputs

```python
spiral.prepare_dumps(out, job) -> list[Path]   # dump directories, in submit order
```

`dmi dumps DIR --job job.sh` runs after `dmi collect`. `job.sh` is the Patch B
launch script and may differ from the SCF one. It is spliced into
`DIR/submit_dumps.sh` over `DIR/dumps.txt`, by the same function TEN-03 uses
for `submit.sh`. `prepare_dumps` writes:

```text
DIR/dump_C/  dump_C_x/  dump_C_y/   INCAR POSCAR KPOINTS POTCAR parent.json, CHGCAR -> ../q0/CHGCAR
DIR/<run>/dump_P/                   INCAR POSCAR KPOINTS POTCAR parent.json, CHGCAR and WAVECAR -> ../
DIR/dumps.txt                       dump_C, dump_C_x, dump_C_y, then <run>/dump_P in runs.txt order
DIR/submit_dumps.sh
```

Parent files are relative symlinks. `parent.json` records the parent run name,
its `OUTCAR` and `OSZICAR` hashes from `collected.json`, and the `size` and
`mtime_ns` of each linked file. `finish` rejects the dump if any of these changed.
That catches a parent rerun or overwritten between `dumps` and the dump job.
With `LWAVE = F` and `LCHARG = F`, a dump writes neither file.

| Directory | INCAR |
|---|---|
| `dump_P` | The parent run's `INCAR` unchanged, plus `ISTART = 1`, `ICHARG = 11`, `ALGO = Normal`, `NELM = 1`, `LDUMPCOCC = T`, `LWAVE = F`, `LCHARG = F`. The `q0` dump also sets `LDUMPCPROJ = T` for M1 (D-011). |
| `dump_C` | The material `INCAR` plus `LNONCOLLINEAR = T`, `LSORBIT = T`, `SAXIS = 0 0 1`, `ISYM = -1`, the `q0` `MAGMOM`, `ISTART = 0`, `ICHARG = 11`, `ALGO = Normal`, `NELM = 1`, `LDUMPCSO = T`, `LWAVE = F`, `LCHARG = F`. |
| `dump_C_x`, `dump_C_y` | The `dump_C` deck with `SAXIS = 1 0 0` and `0 1 0` respectively. |

No INCAR with `LSORBIT = T` contains `LSPIRAL`, `QSPIRAL`, `LZEROZ`,
`I_CONSTRAINED_M`, `LAMBDA` or `M_CONSTR`. `prepare_dumps` checks this rule on
the decks it writes. `ISTART = 0` with `ICHARG = 11` reads only `CHGCAR`. CSO
depends only on the potential, so no `LSPIRAL` `WAVECAR` is read into an SOC run.
`ALGO = Normal, NELM = 1` is the historical N0 recipe
(`docs/archive/decorated_spiral_implementation_rev2.md`, Section 3).

Guards (`ValueError`, naming the run):

| Rule | Failure it stops |
|---|---|
| `DIR/collected.json` exists, and the parent is `ok` in it with `OUTCAR` and `OSZICAR` hashes that still match | A dump from an unconverged or changed parent (Section 5) |
| The parent has nonempty `CHGCAR`, and `WAVECAR` for `dump_P` | A material `INCAR` with `LWAVE = F` or `LCHARG = F` |
| `q0` is `ok` | No in-plane reference for the CSO dumps |
| No dump directory exists yet | Overwriting a dump |
| The `job.sh` rules of TEN-03 | — |

Runs that are not `ok` get no dump. `dmi dumps` prints them and writes the rest.

Two things only TEN-06 can show:

- Whether VASP accepts `ICHARG = 11` from an `LSPIRAL = T` `CHGCAR` in an
  `LSORBIT = T` run. If it does not, the fallback is a separate `LSPIRAL`-free
  reference SCF.
- Whether `dump_C_x` and `dump_C_y` read that `CHGCAR`'s magnetization relative
  to their own `SAXIS`. Only the orbital `uu` block enters T3, and that block
  depends on the potential.

## provenance.json

```python
gates.finish(dump_dir, kind) -> dict    # kind: dump_C, dump_C_x, dump_C_y, dump_P
```

`dmi trace` calls it for every dump directory that has no `provenance.json` yet.
Each check is an existing or rewritten function:

| Kind | Checks | Files hashed (paths relative to `DIR`) |
|---|---|---|
| `dump_C` | `parent.json` unchanged, `realized.echo_check`, `load_cso`, `gate_c0` | `INCAR`, `OUTCAR`, `CSO.dat` |
| `dump_C_x`, `dump_C_y` | `parent.json` unchanged, `echo_check`, `load_cso(expect_saxis=...)`, `gate_t3` against `dump_C`, which must have passed | `INCAR`, `OUTCAR`, `CSO.dat` |
| `dump_P` | `parent.json` unchanged, `echo_check`, `load_cocc`; on `q0`, also `load_cproj`, `load_ferwe` and `gate_m1` | `INCAR`, `OUTCAR`, `COCC.dat`; on `q0`, also `CPROJ.*.bin` and `FERWE.dat` |

```json
{"kind": "dump_P", "passed": true, "checks": {"incar_echo": {}, "M1": {}},
 "files": {"d1_t1_plus/dump_P/COCC.dat": "<sha256>"},
 "parent": "d1_t1_plus", "build_banner": "vasp.6.4.2 ...", "error": null}
```

`manifest.check_files(files, root)` gains a `root` argument, so relative paths
resolve against `DIR`. `require_done` keeps its `CPROJ` rank-file check and loses
the `FAILED` marker. COCC has no `QSPIRAL` header, so a dump is tied to its run by
the `INCAR` echo (which includes `QSPIRAL`), `parent.json` and the hashes.

## T3, Section 11 form

```python
gates.gate_t3(z, dump, axis, tol=1e-10) -> GateResult   # axis "x" or "y"
```

`dump.matrix[UU]` must equal `split_operator(z)[axis]` on every ion, to `tol`.
`load_cso` already checks `SAXIS` against `expect_saxis`. A `Lambda_y` match with
the opposite sign means the CSO flip blocks are stored as `du, ud`. In that case
T3 fails with that message, and `conventions.py` must be corrected rather than
worked around.

T3 runs from `finish` on `dump_C_x` and `dump_C_y`. `traces.json` labels `T_y`
`"provisional"` unless `dump_C_y` passed T3. `T_x` and `T_z` do not depend on
the flip-block order. If the x or y dump has not run yet, T3 is reported as
`not run`, which is not a failure. A failed T3 is a failure.

`dmi t3 --z --x --y --output` stays as a command and calls `gate_t3` twice. It is
the cluster check for a build, independent of a run tree. These are deleted: the
Euler search (`EULER_CONVENTIONS`, `spin_rotation`, `validate_rotation`),
`_rotate`, `rotate_saxis`, and with them `cso.py` itself. Its wrapper `t3`
moves to `gates.py`.

## Trace vector

```python
trace.split_operator(cso) -> np.ndarray      # (3, nions, lm, lm): Lambda_x, Lambda_y, Lambda_z, Eq (4.4)
trace.trace_vector(cocc, lam) -> np.ndarray  # (nions, 3) complex per-ion T, Eq (4.8)
trace.trace_run(run, out) -> dict            # replaces trace_config
    # T_eV (3,)  per_ion_eV (nions, 3)  imag_eV (nions, 3)  q_frac  sha256 {COCC, CSO}
```

- Eq (4.4) uses the CSO block order of `gate_c0`: `0 = uu`, `1 = ud`, `2 = du`,
  `3 = dd`. T3 tests that order.
- Eq (4.8) contracts elementwise over the `lmmax` block:
  `T[ion, a] = sum(lam[a, ion] * (cocc[UU, ion] - cocc[DD, ion]))`. Here
  `COCC[i, j] = rho[j, i]`, and a matrix trace would insert the wrong transpose
  (Section 4.4). `conventions.UU_IDX` and `DD_IDX` give the blocks.
- The real part is `T` and the imaginary part is the I0 residual. Both are kept
  per ion, for the element-resolved `D` in TEN-05.
- `trace_run` needs passing `provenance.json` in `dump_C` and `<run>/dump_P`,
  with unchanged hashes. It also needs equal `NIONS`, `LMDIM` and `NELECT` in
  COCC and CSO, with `NIONS` equal to the POSCAR atom count. It takes `q_frac`
  from the run's `config.json`.

`trace_config`, `_load_config_q_frac`, `_assert_done_marker` and
`_trace_provenance` are deleted; nothing calls them. `compute_delta_E1` and its
reference loop stay as the independent CPROJ route, which the tests use as the
oracle.

## Checks

```python
gates.gate_n0(per_ion, sigma=None) -> GateResult        # per_ion (nions, 3) real T at q0
gates.gate_i0(imag, tol=1e-6) -> GateResult             # imag (nions, 3)
gates.gate_p0(plus, minus, tol=0.1) -> GateResult       # T vectors (3,) at +q and -q
gates.gate_e0(e_plus, e_minus, e_zero, tol=0.1) -> GateResult
```

| Check | Rule | Evaluated on |
|---|---|---|
| N0 | Every `T_a(0)`, total and per ion, has magnitude `< max(N0_FLOOR_EV, 3 sigma)` on all three axes | `q0` |
| I0 | `max abs(Im T)` per ion and axis `<= 1e-6` eV | Every run |
| P0 | `norm(T(q) + T(-q)) <= 0.1 norm(T(q) - T(-q))`, or `norm(T(q) + T(-q)) < N0_FLOOR_EV` | Gates at each direction's smallest `t`; reported at every `t` |
| E0 | `abs(E(q) - E(-q)) <= 0.1 abs(E(q) + E(-q) - 2 E(0))`, with no floor | Gates at each direction's smallest `t`; reported at every `t` |
| C0, M1, T3 | Read from `provenance.json` | `dump_C`; `q0`'s `dump_P`; `dump_C_x` and `dump_C_y` |

Notes on the rules:

- **N0 per ion.** The spin-only `C2x` argument of Section 4.5 maps the collinear
  state onto itself atom by atom, so every atom's term vanishes, not only the
  sum. `sigma` stays `None` until restart replicates exist.
- **P0 floor.** With inversion kept, `T(q) - T(-q)` vanishes at every `q`
  (Section 11, bcc Fe), so a ratio alone would compare noise with noise.
- **Norms.** P0 uses the 3-vector norm, so it does not depend on the frame, and
  the provisional sign of `T_y` cannot change it.

`dmi trace DIR`:

1. Runs `finish` on any dump without `provenance.json`.
2. Traces every `ok` run whose `dump_P` passed.
3. Rechecks the `collected.json` hashes and reads `E` from it.
4. Applies the checks and writes `DIR/traces.json`.
5. Prints one line per run and per check, and exits 1 if any check fails or any
   `ok` run has no passing trace. A T3 that has not run does not count as a
   failure.

Rerunning `dmi trace` is safe, because it never rewrites a `provenance.json`. To
redo a dump, delete its directory.

## gate_n0

`gate_n0(trace, species, sigma_restart)` becomes `gate_n0(per_ion, sigma=None)`.
The `Bi_eV`, `Bi_near_threshold` and species arguments go. The `acceptance/`
record stays as it is, as a historical record.

## STATUS reconciliation (in this branch)

- Header: reconciled at TEN-04, base `main` at `dba823d`.
- TEN-03: Done, merged in PR #12 (`dba823d`). Its Established row drops "Not yet merged".
- TEN-04: this owner and branch; the next action is the TEN-05 spec.
- Remove from Unresolved inputs: OUTCAR energy-line spacing (now read with
  flexible whitespace) and the TEN-01 leftovers.
- Add to Unresolved inputs, for TEN-06: whether VASP accepts the `q0` `CHGCAR`
  for the CSO dumps, and how `dump_C_x` and `dump_C_y` read its magnetization.
- Keep "whether `LDUMPCOCC` works without `LDUMPCPROJ`".
- Update the local software row with the test count.

## Tests

Three new tests, for a total of 18. One existing test is extended, and one
existing call changes:

1. **`test_trace_vector_and_t3`** (`test_trace_gates.py`). On the existing fake
   dump, build a CSO from known `Lambda` through Eq (4.3), and check that
   `split_operator` recovers it.
   - For each axis, `trace_vector` equals `compute_delta_E1` on a CSO whose
     diagonal blocks are `+Lambda_a` and `-Lambda_a` (Eq 4.7 by the CPROJ
     route), to `1e-12`.
   - The per-ion values sum to the total.
   - An imaginary part injected into COCC fails I0.
   - `gate_t3` passes for x and y dumps whose `uu` block is `Lambda_x` or
     `Lambda_y`, and fails with the flip-block message when the z dump's `ud`
     and `du` are swapped.
2. **`test_dumps_provenance_and_trace`** (`test_spiral.py`). This uses the TEN-03
   material and its `finish` helper, with fake `WAVECAR` and `CHGCAR` files.
   - `dmi dumps` writes the four kinds with the tags above: `LDUMPCPROJ` only on
     `q0`, no `LSPIRAL` in any SOC deck, and only `CHGCAR` linked for the CSO
     dumps.
   - A run that is not `ok` gets no dump.
   - Synthetic dumps get the right sign at `-q`: COCC with `uu` and `dd`
     swapped, which gives `T(-q) = -T(q)`.
   - With those dumps, `dmi trace` exits 0, and `traces.json` has N0, P0, E0
     and T3 passing, with `T_y` not provisional.
   - Touching a parent `CHGCAR` (changing its `mtime`) makes `finish` reject
     that dump.
   - Editing `CSO.dat` after `finish` makes `trace_run` refuse the run.
3. **`test_parity_checks`** (`test_trace_gates.py`). Synthetic `T` and `E`:
   - N0 fails on one ion over the floor, even with a zero total.
   - P0 passes an odd pair, fails a 20% even background, and passes a
     centrosymmetric pair at the floor.
   - E0 passes and fails.

Changed:

- `test_readback` is extended for the collect checks: one run with `delta = 2°`,
  one with `M` 10% off `q0`, and one with `M_z = 0.1` are each not `ok`.
- `test_collinear_null_and_same_capture_checks` changes only its `gate_n0` call.

Injected faults the tests must catch:

- `trace(Lambda @ (uu - dd))` in place of the elementwise sum;
- `Lambda_y` with `ud` and `du` swapped;
- the `1/2` dropped in Eq (4.4);
- `dd` added instead of subtracted;
- T3 comparing the `dd` block;
- the per-ion N0 rule reduced to the total;
- the P0 floor removed;
- `E(0)` left out of E0;
- each of the three collect checks removed;
- the `parent.json` stat check removed;
- the hash recheck removed from `trace_run`;
- the `ok` guard removed from `prepare_dumps`.

## Done when

- All 18 tests pass, and every injected fault is caught.
- `trace_config`, the Euler code, `cso.py` and the `Bi` check are gone, and
  nothing reads `DONE`.
- STATUS, CHANGELOG, `docs/seed_file.md` (the `dumps` and `trace` commands) and
  a session log are updated.
- The user merges the pull request.

These tests show the dump inputs, the contraction and the checks follow
Sections 4, 5 and 11 on synthetic data. Four questions remain VASP facts for
TEN-06:

- whether `LDUMPCOCC` works on its own;
- whether the CSO dumps accept the `q0` `CHGCAR`;
- how the x and y dumps read its magnetization;
- the CSO flip-block order.

## Decisions (user, 2026-11-08)

1. `dump_C` reads `q0`'s `CHGCAR` only (`ISTART = 0`, `ICHARG = 11`), with no
   `WAVECAR` linked. No `LSORBIT = T` deck contains `LSPIRAL`. The fallback at
   TEN-06 is a separate `LSPIRAL`-free reference SCF.
2. P0 and E0 use 10% of the odd part and of the curvature. They gate at each
   direction's smallest `t` and are reported at every `t`. E0 has no floor.
3. `sigma = None` until restart replicates exist.
4. T3 takes the Section 11 form: `C_uu` at `SAXIS = x` equals `Lambda_x`, and
   at `SAXIS = y` equals `Lambda_y`, both from the z dump. The Euler search,
   `validate_rotation`, `rotate_saxis` and `_rotate` are deleted. `dmi dumps`
   also writes `dump_C_x` and `dump_C_y`, `finish` runs T3, and `T_y` stays
   provisional until T3 passes.
5. One `dmi trace`, which runs `finish`.
6. The Section 11 SCF-and-state checks go in `dmi collect`: `abs(delta_a) < 1°`
   when `n_twist = 0` (from `plan.json`), `M_a` within 5% of `q0`'s, and
   `abs(M_z) < 0.05 μB`.

The user also added a rule: `dmi dumps` records the size and `mtime` of each
parent's linked `WAVECAR` and `CHGCAR`, and `finish` rejects the dump if either
changed.
