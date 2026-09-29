# dmi_pipeline codebase inventory (pipeline v2)

Inventory of every file under `vasp patch/pipeline v2/`, read on 2026-09-15, to support trimming the codebase. For each file: what it does, what calls it, and whether it works today.

## 0. How to read this document

- Paths are relative to `pipeline v2/`. `dmi_pipeline/gates.py:205` means the definition starts on line 205.
- Status labels:
  - `LIVE`: on the working path and covered by passing tests.
  - `ISSUES`: tested, but fails or is mis-wired with the shipped conventions or with real inputs.
  - `LEGACY`: Patch A code kept for one or two callers.
  - `BROKEN`: fails at import.
  - `STALE`: documentation or data that no longer matches the code.
  - `UNREFERENCED`: nothing references it (not the package, not the root scripts, not the tests).
  - `TESTS-ONLY`: referenced only from `tests/`.
  - `HUB`: widely reused; changing or removing it affects many callers.
- Dump formats:
  - Patch A: the original `LDUMPCSO` VASP patch. CPROJ rank files are placed by `block` or `cyclic` band order, occupations come from `EIGENVAL`, and every configuration gets its own SOC dump (`CSO_*.dat`, `COCC.dat`, `CPROJ.*.*.bin`).
  - Patch B: the newer patch. CPROJ records carry their own global k, band, and spin indices; occupations ship as `FERWE.dat`; CSO is one material-level file; each configuration has a SOC-free `dump_P` directory.
  - Format-free: code that never reads dump files (geometry, model, planner, solver).
- "Verified" means confirmed by running code (pytest, import checks, direct function calls), not only by reading it.
- Line counts come from `wc -l`. "Last modified" is the file timestamp.

## 1. Summary

### 1.1 Size and test status (verified)

| Item | Value |
|---|---|
| `dmi_pipeline/` | 23 modules, 6,947 lines |
| `tests/` | 21 test files plus `tests/fixtures.py`, 3,516 lines, 180 tests |
| Root scripts | 5 files, 1,486 lines |
| `constrsint probe/constraint_probe/` | 8 Python modules (2,070 lines) plus a shell template; its tests: 4 files, 890 lines, 56 tests |
| Markdown docs and specs | 12 files, 5,000 lines |
| `vasp_sample/` | 247 MB of VASP output, referenced by nothing |
| `dmi_pipeline` test run | 180 passed in 41.3 s (Python 3.11.15, conda env `research`) |
| `constraint_probe` test run | 56 passed in 1.4 s (must run from inside `constrsint probe/`) |
| Files that fail at import | 4: `dmi_pipeline/ta_td.py`, `single_trace.py`, `ta_td_extract.py`, `noisefloor.py` |
| Unreferenced top-level definitions in `dmi_pipeline` | 17, plus 12 referenced only by tests (section 9) |

### 1.2 Key findings (all verified)

1. Two dump formats coexist. `dumpio.py`, `trace.py`, and the C0/M1/N0/P0/I0/R0 gate functions are Patch B. `cproj.py`, `cso.py` (reader), and the `dmi gate m0` / `dmi gate t3` commands read Patch A files. `materialize.py` and `execution.py` still use the older `stage2`/`stage3` layout and a Patch A Stage-3 file list. The physics core (orbits, model, design, planner, solve) is format-free. The migration spec (`pipeline_migration_patch_b.md`) is only partly implemented.
2. Four files fail at import. The 2026-09-14 rewrite of `dmi_pipeline/trace.py` removed `read_eigenval`, `read_kpoint_coordinates`, and `match_negative_kpoints`. `dmi_pipeline/ta_td.py`, `ta_td_extract.py`, `single_trace.py`, and `noisefloor.py` still import them and raise `ImportError`. `single_trace.py` and `noisefloor.py` also call the old six-argument `compute_delta_E1(cproj_data, cso_uu, cso_dd, f_occ, w_k, ions)`. None of the four has tests.
3. `dmi materialize` cannot run with the shipped conventions. `conventions.py` pins `FRAME_MAGMOM = "lab"` and `FRAME_MCONSTR = "unwound"`, but `targets.to_frame` (`dmi_pipeline/targets.py:85`) accepts only `"internal_z_cone"` and `"lab_cartesian"`. `magmom_string` and `mconstr_string` therefore raise `RuntimeError: frame convention 'lab' is not pinned`. F1 configurations additionally require `F1_USES_LZEROZ`, which is still `UNDETERMINED`. `tests/test_materialize.py`, `tests/test_targets.py`, and `tests/test_cli_pipeline.py` pass only because autouse fixtures monkeypatch the frames to `"internal_z_cone"` and set `F1_USES_LZEROZ = True`.
4. The generated run script and `dmi trace` expect different Stage-3 contents. `write-run-script` marks Stage 3 complete when `stage3/` contains `CSO_z.dat`, `COCC.dat`, `EIGENVAL`, and `CPROJ.*.*.bin` (Patch A). `dmi trace` reads `stage3/dump_P/` (Patch B `CPROJ.*.bin`, `FERWE.dat`, and a `DONE` marker) plus `CSO_x.dat`, `CSO_y.dat`, `CSO_z.dat` from a separate `--cso-dir`. Nothing in the repo writes `dump_P`, `DONE`, or rotated CSO files. `dumpio.load_cso` also requires the CSO header to say `SAXIS = 0 0 1`, so a genuine x-axis or y-axis CSO dump is rejected.
5. `dmi form-pairs` has no upstream source of uncertainties. Each pair row needs `sigma_y`, taken from `TraceData.sigma_eV` or from `manifest.noise_model`. `trace_config` never sets `sigma_eV`. `dmi estimate-pair-noise` reads measurements with `role == "noise"`, and the planner never creates any. On a planner-generated campaign, `form-pairs` stops unless the manifest is edited by hand.
6. Dead code. 17 top-level definitions in `dmi_pipeline` are never referenced, and 12 more are referenced only by tests. Examples: `gates.gate_m1` (Patch A M1), `gates.gate_imag`, `gates.gate_origin_shift`, `gates.gate_pair_realization`, `gates.gate_pair_repeatability`, `realized.lambda_ramp`, `model.y_from_delta_E1`, `targets.from_frame`, `frames.from_unwound`, `manifest.RowData`, `planner.CandidateMeasurement`, and the CLI helpers `_row_object` and `_build_cso_source`. Full lists in section 9.
7. Most data on disk is unused. `vasp_sample/` (247 MB, real VASP 6.4.2 Patch A output) is referenced by no code or test, and `dumpio` rejects both its CPROJ binaries and its CSO file. The root `manifest.json` (988 KB) is schema version 1, which `manifest.load` rejects; `report.md` was rendered from it. The root `POSCAR` is required: 12 test files read it.
8. Several docs are stale or describe unbuilt work. `jiso_extension_spec.md` was never implemented. `USAGE.md` documents the broken scripts, the removed `CPROJ_BAND_ORDER`, the old `gate m1 --cproj-glob` syntax, and planner partner / lambda-scan / null-check behavior that no longer exists. Details in section 8.

### 1.3 Command status

Commands of the click group in `dmi_pipeline/cli.py` (run as `python -m dmi_pipeline.cli <command>` or `python run_dmi.py <command>`). Main-sequence steps are listed in the order the data requires: `form-pairs` reads the noise model, so `estimate-pair-noise` must run before it (`USAGE.md` lists them the other way round).

| Step | Command | Status | Reads -> writes | What blocks it today |
|---|---|---|---|---|
| 1 | `plan` | LIVE | campaign JSON -> manifest | Nothing. |
| 2 | `materialize` | ISSUES | manifest -> `measurements/<id>/plus/stage2`, `.../minus/stage2`, and matching `stage3` dirs | Finding 3: frame strings rejected by `targets.to_frame`; F1 needs `F1_USES_LZEROZ`. |
| 3 | `write-run-script` | ISSUES | manifest + user Stage-3 INCAR template -> `run_all.sh`, `execution_plan.json` | Generates correctly, but its Stage-3 completion check lists Patch A files that `trace` does not read (finding 4). |
| 4 | `realize` | ISSUES | `stage2/OUTCAR` -> realized psi/theta, per-config gate, pair gate | Passes `tol.phi` (radians) as the q tolerance and `TOL_MOMENT_REL` (a relative fraction) as an absolute moment tolerance in mu_B to `validate_realized_pair` (`cli.py:214-220`). |
| 5 | `trace` | ISSUES | `stage3/dump_P/` + `--cso-dir/CSO_{x,y,z}.dat` -> raw traces | Always traces all three axes; non-z CSO headers fail the SAXIS check; no producer for `dump_P`, `DONE`, or rotated CSO. Records `trace_gate = "PASS"` without running any gate. |
| 6 | `estimate-pair-noise` | ISSUES | `role == "noise"` measurements -> `noise_model` | Planner creates no noise measurements (finding 5). |
| 7 | `form-pairs` | ISSUES | traces + realized states -> pair rows with design rows | Needs `sigma_eV` or `noise_model`; nothing supplies either (finding 5). |
| 8 | `solve` | LIVE | pair rows -> solution + LOO-CV, holdout, class-sum gates | Works on complete manifests. `failing = [g for g in gates if not g.passed]` (`cli.py:489`) treats a recorded NOT_APPLICABLE gate (`passed = None`) as failed, so it then demands `--force`. |
| side | `report` | LIVE | manifest -> Markdown | Nothing. |
| side | `trace-one` | LIVE | one config dir + CSO dir -> printed trace and per-k values | Same input contract as `trace`. |
| side | `gate w0`, `gate c0`, `gate m1` | LIVE | Patch B `dump_P` files, `CSO.dat` | Print only: no `--manifest` option, so results and the `CSO_SIGN_VALIDATED` side effect are lost when the process exits. |
| side | `gate n0`, `gate p0`, `gate i0`, `gate r0` | LIVE | numbers typed on the command line | Print only. |
| side | `gate m0`, `gate t3` | LEGACY | Patch A CSO/COCC text via `cso.read_cso` and `cproj.load_cocc_dat` | Work and persist pins to `meta.conventions`; not connected to `dumpio` data. |

## 2. Architecture

### 2.1 Layers

Every import inside `dmi_pipeline` points to the same layer or a lower one (verified against all import statements). Lines in parentheses.

| Layer (top depends on bottom) | Modules |
|---|---|
| Root scripts (outside package) | `run_dmi.py` LIVE (25), `realized_state_gate.py` LIVE (669), `single_trace.py` BROKEN (245), `ta_td_extract.py` BROKEN (94), `noisefloor.py` BROKEN (453) |
| Orchestration and diagnostics | `cli` LIVE (728), `materialize` ISSUES (232), `execution` ISSUES (435), `ta_td` BROKEN (338) |
| Readback and analysis | `trace` LIVE (222), `realized` LIVE (371), `gates` LIVE, mixed eras (619), `solve` LIVE (205), `report` LIVE (133) |
| Dump readers | `dumpio` LIVE, Patch B (816), `cso` LEGACY (150), `cproj` LEGACY (253) |
| Planning and records | `planner` LIVE (623), `manifest` LIVE (387) |
| Geometry and model | `orbits` LIVE (399), `model` LIVE (125), `design` LIVE (95), `observables` LIVE (166), `frames` LIVE (86), `targets` ISSUES (186) |
| Foundation | `conventions` LIVE (243), `structures` LIVE (132), `__init__` (3) |

### 2.2 Import map

"Imports" lists `dmi_pipeline` modules only (third-party: numpy everywhere; scipy in `planner`; pymatgen in `structures`, `orbits`; pydantic in `manifest`; click in `cli`).

| Module | Imports | Imported by (package) | Imported by (root scripts) | Imported by (tests) |
|---|---|---|---|---|
| `conventions` | none | cli, cso, dumpio, gates, manifest, materialize, orbits, planner, realized, report, solve, targets, trace | single_trace | test_cli_pipeline, test_conventions, test_cso_rotation, test_frames, test_materialize, test_realized, test_targets |
| `structures` | none | cli, cso, frames, materialize, orbits, planner, realized, targets | realized_state_gate | test_cli_pipeline, test_frames, test_model, test_orbits, test_realized, test_realized_state_gate, test_solve, test_structures, test_targets, test_two_trace |
| `orbits` | conventions, structures | cli, design, gates, model, planner, solve | none | test_cli_pipeline, test_gates, test_model, test_orbits, test_solve, test_two_trace |
| `model` | orbits | cli, design, planner | none | test_cli_pipeline, test_model, test_planner_cli, test_solve, test_two_trace |
| `design` | model, orbits | cli, planner | none | test_cli_pipeline, test_solve, test_two_trace |
| `observables` | none | cli, gates | none | test_gates, test_observables, test_two_trace |
| `frames` | structures | realized | none | test_cli_pipeline, test_frames, test_realized |
| `targets` | conventions, structures | materialize | realized_state_gate | test_frames, test_realized_state_gate, test_targets |
| `planner` | conventions, design, manifest, model, orbits, structures | cli, materialize | none | test_planner_cli, test_two_trace |
| `manifest` | conventions | cli, execution, gates, materialize, planner, realized, report | realized_state_gate | test_cli_pipeline, test_conventions, test_execution, test_gates, test_manifest, test_materialize, test_realized, test_report, test_solve, test_two_trace |
| `dumpio` | conventions | cli, gates, trace | none | fixtures.py, test_dumpio, test_gates, test_trace |
| `cso` | conventions, structures | cli, ta_td | single_trace, noisefloor | test_cli_pipeline, test_cso_rotation |
| `cproj` | none | cli, gates, ta_td | single_trace, noisefloor | none |
| `trace` | conventions, dumpio | cli, gates, ta_td | single_trace, noisefloor | test_cli_pipeline, test_gates, test_trace |
| `realized` | conventions, frames, manifest, structures | cli, gates | realized_state_gate | test_realized, test_realized_state_gate, test_two_trace |
| `gates` | conventions, cproj, dumpio, manifest, observables, orbits, realized, solve, trace | cli | none | test_gates |
| `solve` | conventions, orbits | cli, gates | none | test_gates, test_solve, test_two_trace |
| `report` | conventions (unused), manifest | cli | none | test_planner_cli, test_report |
| `materialize` | conventions, manifest, planner, structures, targets | cli | none | test_materialize |
| `execution` | manifest | cli | none | test_execution |
| `cli` | conventions, cproj, cso, design, dumpio, execution, gates, manifest, materialize, model, observables, orbits, planner, realized, report, solve, structures, trace | none | run_dmi | test_cli_pipeline, test_execution, test_planner_cli |
| `ta_td` | cproj, cso, trace | none | ta_td_extract | none |

### 2.3 Most-reused definitions (HUB)

| Definition | Location | Role | Used by |
|---|---|---|---|
| `load`, `save`, `validate` | `manifest.py:355`, `:362`, `:271` | Read, atomically write, and cross-validate `manifest.json` | Every CLI command; `report.write_report`; `validate` also runs on every `Manifest` construction |
| `Manifest`, `Meta`, `ConfigData`, `MeasurementData`, `TraceData`, `RealizedData`, `PairRowData`, `PairRealizationGateData` | `manifest.py:243`, `:51`, `:202`, `:177`, `:137`, `:114`, `:159`, `:150` | Data contract between all stages | planner, materialize, execution, realized, gates, cli, realized_state_gate, 10 test files; `solve` reads the same fields by name |
| `MagneticStructure`, `load_magnetic_structure` | `structures.py:17`, `:51` | Structure plus magnetic metadata | orbits, frames, targets, realized, planner, materialize, cli; realized_state_gate builds `MagneticStructure` directly |
| `enumerate_bonds` -> `canonicalize` -> `build_orbits` | `orbits.py:85`, `:136`, `:260` | Geometry chain: bonds, symmetry orbits, Moriya-allowed bases | `planner.plan`, `cli._rebuild_orbits` (used by `form-pairs` and `solve`), most physics tests |
| `param_labels`, `all_bond_vectors`, `propagate` | `orbits.py:372`, `:394`, `:359` | Parameter names; parameter vector -> per-bond DM vectors | planner, `solve.solve`, gates (rank-failure messages) |
| `Row`, `dpsi`, `weight`, `phase` | `model.py:13`, `:38`, `:42`, `:46` | Row descriptor and per-bond physics primitives | `design.configuration_kernel`, `model.design_row`, planner pool rows |
| `configuration_kernel`, `paired_design_row` | `design.py:13`, `:83` | Production design row `[A(c_plus) - A(c_minus)] / N_m` | `planner._target_pair_row`, `cli form-pairs`; test_two_trace, test_solve, test_cli_pipeline |
| `assemble`, `solve` | `solve.py:42`, `:102` | Pair rows -> weighted least squares via SVD | `cli solve`; `gates.predict_holdout`, `gate_loo_cv`, `gate_holdout_family`, `gate_class_sum_agreement` |
| `spin_targets` | `targets.py:33` | Target spin vectors for a (q, psi, theta) state | `materialize`, `realized_state_gate` (seed calibration), test_frames, test_targets, test_realized_state_gate |
| `load_cproj`, `load_ferwe`, `load_cso`, `load_cocc`, `assert_header` | `dumpio.py:453`, `:664`, `:802`, `:810`, `:631` | Patch B readers | `trace.trace_config`, `cli gate w0/c0/m1`, tests via `tests/fixtures.py` |
| `compute_delta_E1`, `trace_config` | `trace.py:82`, `:173` | First-order SOC trace of one configuration | `cli trace`, `cli trace-one` |
| `read_realized`, `realization_gate`, `validate_realized_pair`, `wrap_to_pi` | `realized.py:188`, `:273`, `:294`, `:90` | Stage-2 readback and gates | `cli realize`; `realized_state_gate.py` (uses `wrap_to_pi` 10 times) |
| `pair_observable` | `observables.py:96` | Two-trace observable arithmetic | `cli form-pairs`, `cli estimate-pair-noise` |
| `set_from_manifest` and the module-level constants | `conventions.py:204` | Carries pinned conventions between CLI processes | `cli._load_manifest_with_conventions` (materialize, realize, trace); constants read by most modules and overwritten at runtime by `gate_m0`, `gate_c0`, `gate_m1`, and `cli gate t3` |
| `GateResult`, `run_gate`, `to_gate_data` | `gates.py:51`, `:60`, `:76` | Common gate record | Every gate function; cli |
| `read_cso` | `cso.py:19` | Legacy CSO text reader | `cli gate m0`, `cli gate t3`, `ta_td`, `single_trace`, `noisefloor`, test_cso_rotation |

## 3. dmi_pipeline modules

Ordered from the foundation layer upward. Each entry has a status line, purpose, definitions (line numbers, flags), and notes. `HUB`, `UNREFERENCED`, and `TESTS-ONLY` flags are defined in section 0.

### 3.1 `dmi_pipeline/conventions.py`

- Status: LIVE. Format-free; holds the Patch B pins. 243 lines. Modified 2026-09-12.
- Purpose: module-level constants consulted by readers, writers, and gates: empirically pinned VASP conventions, fixed tolerances, and the observable mode. They are plain globals, and some gates and CLI commands overwrite them at runtime.
- Definitions:
  - `ObservableMode` (:20), `DEFAULT_OBSERVABLE_MODE` (:27): enum with `single_trace` and `two_trace_generalized_parity`; default is two-trace.
  - `require_single_trace_validation(manifest)` (:30): raises unless `meta.single_trace_validation_status == "PASS"`. Called by `manifest.validate`. Single-trace mode exists only to be refused.
  - `UNDETERMINED` (:43): sentinel for unpinned values.
  - `SPIN_BLOCK_MAP = {1: (0,0), 2: (0,1), 3: (1,0), 4: (1,1)}` (:66), `UU_IDX = 0` (:72), `DD_IDX = 3` (:73): NCDIJ spin-block packing (1-based IS keys, 0-based indices).
  - `FRAME_MAGMOM = "lab"` (:77), `FRAME_MCONSTR = "unwound"` (:84), `FRAME_MINT = "unwound"` (:91): Patch B frame pins with provenance docstrings. The vocabulary matches `frames.py`, not `targets.py`.
  - `EULER_CONVENTION = "a+b+U"` (:99), `CSO_ROTATION_VALIDATED = False` (:100): T3 pin. The value is set but the flag is not, so `cso.rotate_saxis` refuses to run.
  - `F1_USES_LZEROZ = UNDETERMINED` (:103), `VASP_BUILD_ID = UNDETERMINED` (:108), `DUMP_FORMAT_VERSION = 1` (:109), `CSO_SIGN_VALIDATED = False` (:110).
  - Fixed tolerances (:113-128): `TOL_PHI_DEG = 1.0`, `TOL_THETA_DEG = 1.0`, `TOL_MOMENT_REL = 0.05`, `KAPPA_MAX = 1e3`, `SPACEGROUP_SYMPREC = 1e-4`, `GATE_AGREEMENT_FLOOR_EV = 1e-9`, `BOND_TOL = 1e-5`.
  - `validate(require_empirical=True)` (:182) with `_check_spin_block_consistency()` (:142): strict check that every name in `_EMPIRICAL_NAMES` is pinned, that the M0 and M1 packings agree, and that CSO rotation is validated. Its only caller is `tests/test_conventions.py`, with `require_empirical=False`, which returns immediately. With the current pins the strict form would always raise.
  - `set_from_manifest(manifest)` (:204) HUB: copies non-null values from `meta.conventions` into the globals (whitelisted names only; converts `spin_block_map` keys to int; rejects a mismatched `dump_format_version`).
- Notes:
  - Runtime mutation: `gates.gate_m0` sets `UU_IDX`/`DD_IDX`, `gates.gate_m1` sets `SPIN_BLOCK_MAP`, `gates.gate_c0` sets `CSO_SIGN_VALIDATED`, and `cli gate t3` sets `EULER_CONVENTION`/`CSO_ROTATION_VALIDATED`. Tests isolate this with `monkeypatch`.
  - `CPROJ_BAND_ORDER` has been removed, as the migration spec requires. The constraint probe's `PENALTY_SIGN` and `LAMBDA_RECOMMENDED` do not exist here, and nothing in the package references them.

### 3.2 `dmi_pipeline/structures.py`

- Status: LIVE. Format-free. 132 lines. Modified 2026-07-27.
- Purpose: loads a POSCAR with pymatgen and attaches explicit magnetic metadata.
- Definitions:
  - `MagneticStructure` (:17) HUB: frozen dataclass with `struct`, `mag_indices`, `sublattice`, `eps`, `moment`; helpers `n_m`, `frac(k)`, `cart(k)`, `lattice_matrix`.
  - `load_magnetic_structure(poscar_path, spec)` (:51) HUB: validates the spec (`magnetic_species`; `sublattice_assignment` must be `"by_poscar_order"`; `eps` entries +1 or -1; one positive `moment` per magnetic site), selects sites by species, and assigns sublattice k+1 to the k-th magnetic site. Every magnetic site is its own sublattice, so the model supports exactly `len(eps)` magnetic atoms per cell (2 for the BFO fixture).
  - `phi_ref(sublattice, eps_by_sublattice)` (:120): 0 for eps = +1, pi for eps = -1.
  - `_required` (:45): helper.
- Notes:
  - `Poscar.from_file(..., check_for_POTCAR=False)` raises a pymatgen DeprecationWarning; these make up a large share of the 164 warnings in the test run.

### 3.3 `dmi_pipeline/orbits.py`

- Status: LIVE. Format-free. 399 lines. Modified 2026-07-27. The migration docs mark it frozen.
- Purpose: magnetic bond enumeration, space-group orbits, Moriya projectors, and DM-vector propagation. For the BFO fixture at r_max = 6 Angstrom: 3 orbits, 9 parameters (asserted by tests).
- Definitions:
  - `Bond` (:21), `OrbitMember` (:37), `Orbit` (:45), `BondKey`: frozen records. `Bond` holds (i, j, R), Cartesian and fractional displacement, the eps product, and both sublattices. `OrbitMember` holds a canonical bond plus the operation mapping the representative onto it (chi, R_mat, det). `Orbit` holds id, representative, members, stabilizer, projector, basis, dim, n_m.
  - `enumerate_bonds(ms, r_max)` (:85) HUB: every directed magnetic pair with BOND_TOL < |r| < r_max inside a metric-derived translation box (`_translation_bounds`, :56), deterministically sorted (`_bond_sort_key`, :118).
  - `canonicalize(bonds)` (:136) HUB: keeps one bond of each reverse pair (first nonzero Cartesian component positive; `_canonical_direction`, :128) and asserts exactly half survive.
  - `site_permutation(ms, op)` (:178), `_fractional_image` (:169), `_bond_from_image` (:200), `apply_op_to_bond` (:225), `_reverse` (:72), `_op_sort_key` (:160): map sites and bonds through symmetry operations; return the canonical image and the reversal sign chi.
  - `build_orbits(ms, canonical_bonds, ops=None)` (:260) HUB: gets Cartesian operations from pymatgen `SpacegroupAnalyzer`, unions bonds into classes, picks deterministic representatives, records members and stabilizers, builds the projector (`_make_projector`, :233: P = mean(chi * det(R) * R), asserted idempotent and symmetric, allowed basis = eigenvectors with eigenvalue 1, identity for trivial stabilizers), and runs `_propagation_self_test` (:342).
  - `propagate(orbit, member, d_rep)` (:359): chi * det * R_mat @ d_rep.
  - `param_labels(orbits)` (:372) HUB, with `_component_label` (:367): labels such as `orbit0[r=(...)]` plus an axis name; used in every rank-failure message and in reports.
  - `d_rep_from_x` (:381), `all_bond_vectors(orbits, x)` (:394): parameter vector -> representative vectors -> DM vector for every canonical bond.
- Notes:
  - No unreferenced definitions.
  - `manifest.orbits`, written by the planner, is never read back. `cli._rebuild_orbits` recomputes orbits from POSCAR for `form-pairs` and `solve`, so symmetry analysis and the self-tests run on each of those commands.

### 3.4 `dmi_pipeline/model.py`

- Status: LIVE for the primitives; the single-trace design-row functions have no production caller. Format-free. 125 lines. Modified 2026-08-10. The migration docs mark it frozen.
- Purpose: the row descriptor and per-bond physics, plus the original exact-parity design row that production no longer uses.
- Definitions:
  - `Row` (:13) HUB: validated descriptor (q_frac, psi, theta per sublattice, n_hat, family in F0/F1/F2).
  - `dpsi(bond, psi)` (:38), `weight(bond, theta)` (:42), `phase(bond, q_frac, psi)` (:46) HUB: psi offset for bonds touching sublattice 2, sin(theta_i)*sin(theta_j), and 2*pi*q.r + dpsi. Used by `design.configuration_kernel` and `design_row`.
  - `design_row(orbits, row)` (:50), `design_matrix(orbits, rows)` (:82): legacy row with the 2/N_m prefactor. No production caller; `planner` imports `design_matrix` but never calls it. Used by test_model, test_solve, test_two_trace.
  - `design_row_reference` (:77) TESTS-ONLY: an alias of `design_row`, so the "vectorized equals reference" test compares the function with itself.
  - `e_dm_oracle(ms, all_directed_bonds, d_by_bond, row)` (:95) TESTS-ONLY: independent reimplementation over all directed bonds. `tests/test_model.py::test_directed_bond_oracle_matches_canonical_design` is the strongest physics check in the suite.
  - `y_from_delta_E1` (:89) UNREFERENCED.
  - `_n_m_from_orbits` (:109): guesses N_m for `design_row` via `getattr` on the list (never set), then "2 if any bond touches site index 1, else 1". It ignores the `Orbit.n_m` field that `build_orbits` fills.
- Notes:
  - Unused import: `all_bond_vectors`.
  - Removing `design_row`/`design_matrix` means re-pointing test_model (oracle, rank progression 4/6/9, F2 zeroing), test_solve (round trip), and test_two_trace (exact-pair equivalence) at `design.configuration_kernel`.

### 3.5 `dmi_pipeline/design.py`

- Status: LIVE. Format-free. 95 lines. Modified 2026-08-10.
- Purpose: builds the production design row from both realized members of a parity pair.
- Definitions:
  - `configuration_kernel(*, q_frac, realized_psi, realized_theta_per_sublattice, family, winding_sublattice, axis, orbit_data)` (:13) HUB: unnormalized A(c). For each orbit basis vector e: sum over members of weight * eps * sin(phase) * dot(n_hat, chi * det * R_mat @ e). `winding_sublattice` is deleted on entry, and `family` only feeds `Row` validation. It is the same loop as `model.design_row` without the prefactor.
  - `paired_design_row(plus_realized, minus_realized, axis, orbit_data, n_magnetic)` (:83) HUB: `(A(c_plus) - A(c_minus)) / n_magnetic`, reading realized psi on sublattice 2 and realized theta from each `ConfigData` or dict.
  - `_value` (:54), `_realized_arguments` (:58): helpers.

### 3.6 `dmi_pipeline/observables.py`

- Status: LIVE. Format-free. 166 lines. Modified 2026-08-10.
- Purpose: arithmetic for the two-trace observable and paired-restart noise.
- Definitions:
  - `PairObservable` (:13), `PairObservableData` (:31), `NoiseModel` (:43): records.
  - `compute_generalized_parity_observable(trace_plus, trace_minus, n_magnetic, *, sigma_plus, sigma_minus, covariance)` (:58): difference, common mode 0.5*(T_plus + T_minus), y = Re(T_plus - T_minus)/N_m, imaginary residual, sigma_y = sqrt(max(0, (sigma_plus^2 + sigma_minus^2 - 2*cov) / N_m^2)). Called by `pair_observable`; tests also call it directly.
  - `pair_observable(...)` (:96) HUB: the same arithmetic plus ids and axis.
  - `estimate_paired_noise(replicates, *, n_magnetic, family)` (:134): sample variances and plus/minus covariance (ddof = 1) over at least two replicates.
- Notes:
  - `cli estimate-pair-noise` stores `NoiseModel.__dict__` as `manifest.noise_model`; `form-pairs` reads `sigma_trace_eV` and `trace_covariance_eV2` from it by string key, so renaming a `NoiseModel` field silently breaks `form-pairs`.

### 3.7 `dmi_pipeline/frames.py`

- Status: LIVE. Patch B. 86 lines. Modified 2026-09-12.
- Purpose: rotates vectors between Patch B's lab frame and the generalized-Bloch unwound frame by each magnetic site's 2*pi*q.tau.
- Definitions:
  - `spiral_phase` (:16), `spiral_phases(ms, q_frac)` (:26): per-site 2*pi*q.tau.
  - `rotate_z_per_site(vectors, phases)` (:48), `_vectors_and_phases` (:34): per-site rotation about z, with shape checks.
  - `lab_to_unwound` (:59): used by `to_unwound` and by tests. `unwound_to_lab` (:64): used only by `from_unwound` and by tests.
  - `to_unwound(vectors, frame, ms, q_frac)` (:69): called by `realized.read_realized` with `FRAME_MINT`.
  - `from_unwound` (:79) UNREFERENCED.
- Notes:
  - These adapters are what would let `materialize`/`targets` write M_CONSTR in the unwound frame, but `targets.py` does not use them (finding 3).

### 3.8 `dmi_pipeline/targets.py`

- Status: ISSUES. Format-free, but still uses the pre-Patch B frame vocabulary. 186 lines. Modified 2026-07-27. The migration docs mark it frozen.
- Purpose: target spin vectors and the MAGMOM, M_CONSTR, and RWIGS INCAR strings.
- Definitions:
  - `spin_targets(ms, q_frac, psi, theta_by_sublattice)` (:33) HUB: (n_m, 3) unit vectors with alpha = 2*pi*q.tau + phi_ref + (psi on sublattice 2) and S = (sin(theta)cos(alpha), sin(theta)sin(alpha), eps*cos(theta)).
  - `to_frame(vectors, frame, n_hat)` (:85), `_rotation_z_to(n_hat)` (:56): accepts only `"internal_z_cone"` (identity) and `"lab_cartesian"` (Rodrigues rotation taking z to n_hat). Any other value raises `RuntimeError`.
  - `from_frame` (:97) UNREFERENCED.
  - `magmom_string(ms, S, n_hat)` (:145), `mconstr_string(ms, S, n_hat, mode)` (:153), `rwigs_string(struct, radii)` (:175): INCAR lines. Mode 1 writes unit directions, mode 2 moment-scaled vectors, mode 3 one axis component per site (for the W3 longitudinal patch, which was never written). Both vector writers call `_assert_eps_consistent` (:110) and then `to_frame` with the pinned frame.
  - `_eps_by_sublattice` (:16), `_site_vectors` (:133): helpers.
- Notes:
  - Verified: with the shipped `FRAME_MAGMOM = "lab"` and `FRAME_MCONSTR = "unwound"`, both `magmom_string` and `mconstr_string` raise.
  - The Patch B migration spec requires M_CONSTR with alpha = phi_ref + psi (no 2*pi*q.tau term). Nothing implements this.

### 3.9 `dmi_pipeline/planner.py`

- Status: LIVE. Format-free. 623 lines. Modified 2026-08-10. The migration docs mark it frozen.
- Purpose: Stage 0, no VASP. Enumerates candidate rows, selects a well-conditioned set of parity-pair measurements, predicts uncertainties, and returns a schema-2 `Manifest`.
- Definitions:
  - `CampaignConfig` (:24) HUB, with `from_dict`, `from_file`, `validate`: campaign knobs with defaults. JSON only (YAML rejected), unknown keys rejected, `poscar` resolved relative to the config file. `n_partners`, `n_lambda_scan`, `n_null_checks`, and `schema_version` are accepted but never read.
  - `q_pool` (:170), `_nearest_bz` (:162), `is_reciprocal_lattice_vector` (:184), `is_trim` (:188), `commensurate_with_kmesh` (:192), `q_cart_norm` (:196), `is_excluded` (:200), `is_null_check_candidate` (:212), `_is_psi_degenerate` (:153): q grid reduced to the first Brillouin zone, and the exclusion rules (q in G, |q| < q_min, TRIM points, incommensurate with the k-mesh; F1 at psi in {0, pi}).
  - `_candidate_rows(config, reciprocal_lattice)` (:228): pool of F0 (psi = 0), F1 (non-degenerate psi), and F2 (theta values times winding 1 and 2) rows, times axes. TRIM psi = 0 F0 rows go to a null list that is only counted.
  - `generalized_parity_partner(row)` (:292), `canonical_pair_key` (:303), `reduce_to_bz` (:283), `wrap_angle` (:288), `_config_key` (:277), `_row_key` (:273): the (-q, -psi) partner and pair de-duplication. `materialize` also uses `reduce_to_bz` and `wrap_angle`.
  - `_target_pair_row(orbits, row, n_magnetic)` (:308): pool design row from `configuration_kernel` on the target pair.
  - `select_rows(M_pool, pool_rows, n_target, kappa_max, config)` (:330): pivoted-QR order, then the shared-q bias (adds F1 rows only), then the small-|q| F1 bias, then fills remaining slots in pool-index order; asserts full rank and kappa < kappa_max. The build spec's greedy condition-number extension is not implemented.
  - `_augment_for_holdout` (:403), `_rank_and_nullspace` (:391), `_augment_for_kappa` (:437): add rows until each `holdout_families` complement is full rank (raising with null-space labels if impossible), then repair kappa by seeded random sampling if needed.
  - `_expand_to_full_axis_configs` (:466): pulls in every axis row of each selected configuration.
  - `plan(config)` (:500) HUB: runs the chain; groups rows into measurements `meas_000`, `meas_001`, ... with `<config_id>_plus` and `<config_id>_minus` configs; stores rank progression, predicted sigma, parameter labels, worst direction, holdout rank, holdout-added ids, and pool statistics as extra `meta` keys (pydantic `extra="allow"`).
  - `CandidateConfig` (:122), `CandidateMeasurement` (:142): dataclasses from the two-trace spec. `CandidateMeasurement` is UNREFERENCED; `CandidateConfig` is referenced only by it.
  - `_rank` (:267), `_config_id` (:483), `_serialize_orbits` (:490): helpers.
- Notes:
  - Emits no noise, scan, or lambda-scan measurements, no `lambda_schedule`, and no `chain_from`.
  - Unused: the `design_matrix` import and the local `holdout_added_config_keys` (:545).

### 3.10 `dmi_pipeline/manifest.py`

- Status: LIVE. Format-free (pair schema version 2). 387 lines. Modified 2026-09-12.
- Purpose: pydantic schema for `manifest.json`, cross-reference validation, and atomic persistence.
- Definitions:
  - `StrictModel` (:20): base model with `extra="allow"` and `validate_assignment=True`.
  - `Meta` (:51), `ConventionValues` (:24), `ExecutionPlanRecord` (:39): campaign metadata, persisted convention pins, run-script records.
  - `ConfigData` (:202) HUB, `ConfigExecutionData` (:188), `RealizedData` (:114), `TraceData` (:137): one physical VASP configuration with execution paths, realized state, and raw per-axis traces.
  - `MeasurementData` (:177) HUB, `PairRealizationGateData` (:150), `PairRowData` (:159): a plus/minus pair, its pair gate, and per-axis pair rows (y, sigma_y, design row).
  - `OrbitData` (:105), `OrbitMemberData` (:98), `BondData` (:87): serialized orbits; written by the planner, never read.
  - `GateData` (:220), `SolutionData` (:229), `Manifest` (:243): gate record, solution, and the root model, whose model validator calls `validate`.
  - `RowData` (:125) UNREFERENCED: deprecated single-trace row.
  - `validate(manifest)` (:271) HUB: rejects schema version 1 with an explicit message; enforces unique ids, valid references, parity labels, family and winding agreement, and allowed measurement roles. Once a measurement has rows, it requires realized data on both configs, a non-FAIL pair gate, both raw traces for every PASS row, y, sigma_y > 0, and a design row.
  - `load(path)` (:355), `save(manifest, path)` (:362) HUB: `save` writes a temp file, fsyncs, then calls `os.replace`.
  - `append_gates` (:386): used by cli. `append_configs` (:382) UNREFERENCED. `_as_manifest` (:259), `_axis_key` (:267): helpers.
- Notes:
  - `load` validates twice (model validator plus the explicit call).
  - The Patch B schema additions from the migration spec (per-stage status, dump provenance, material-level artifacts) are not present.

### 3.11 `dmi_pipeline/dumpio.py`

- Status: LIVE. Patch B. 816 lines. Modified 2026-09-12.
- Purpose: strict readers for the four Patch B dump files, written against the Fortran writer `csodump.F` as documented in `patch_b_audit.md`. Tested only against the synthetic writer in `tests/fixtures.py`; the repo contains no real Patch B output.
- Definitions:
  - Constants (:34-40): `CPROJ_MAGIC = "HEIDE_CPROJ_PATCH_B"`, `CPROJ_BUILD_ID = "VASP 6.4.2 HEIDE PATCH B"`, `CPROJ_DUMP_TAG = "PRE_LOOP"`, `CPROJ_FORMAT_VERSION = 1` (UNREFERENCED; the code checks `conventions.DUMP_FORMAT_VERSION` instead), `OCCUPATION_TOLERANCE`, `ELECTRON_TOLERANCE`, `WEIGHT_TOLERANCE`.
  - Records: `FileProvenance` (:44, path + sha256), `CprojAbi` (:52), `CprojHeader` (:74), `CprojRecord` (:110), `CprojFile` (:123), `CprojData` (:132; array `c` shaped (ISPIN, NKPTS, NIONS, NRSPINORS, LMDIM, NBANDS)), `TextMetadata` (:150), `Occupations` (:176), `MatrixDump` (:188; array `matrix` shaped (NCDIJ, NIONS, LMDIM, LMDIM)).
  - `read_cproj_file(path)` (:385): decodes one native-stream CPROJ file. `_probe_cproj_abi` (:358) tries 8 ABIs (byte order x 4/8-byte INTEGER x 4/8-byte LOGICAL) and requires exactly one whose record size divides the payload. `_decode_cproj_header` (:255) and `_assert_cproj_static_header` (:332) check magic, build string, format version, the pinned `VASP_BUILD_ID` if set, dump tag, and call counter. Helpers: `_fixed_string` (:202), `_unpack_integer` (:213), `_unpack_logical` (:220), `_unpack_reals` (:230), `_derive_npro` (:240), `_record_size` (:354), `_provenance` (:198).
  - `load_cproj(directory)` (:453) HUB: globs `CPROJ.*.bin`; requires all rank headers to agree and the file count to equal k-groups x band-groups (`assert_cproj_headers_consistent`, :432; `_header_consistency_key`, :421); places each record by its own (ISP, NK, GLOBAL_BAND). Missing or duplicate records raise "W0 failed".
  - `load_ferwe(path_or_directory)` (:664) HUB: full coverage; occupations exactly 0 or 1 (insulator); spin-independent k-weights summing to 1; SANITY lines must match the rows; infers the RSPIN factor (1 or 2) from `SUM_FW`.
  - `load_cso(path)` (:802), `load_cocc(path)` (:810), `_load_matrix` (:744) HUB: dense matrices with complete element coverage; COCC `TRACE_CHECK` lines must sum consistently. `load_cso` requires `LSORBIT = T`, `LSPIRAL = F`, and, through the default of `assert_header`, `SAXIS = (0, 0, 1)`.
  - `assert_header(header, *, expect_lsorbit, expect_lspiral, q_frac, saxis=(0, 0, 1))` (:631) HUB: flag, QSPIRAL, and SAXIS checks for either header type.
  - `_parse_text_metadata(path, kind)` (:539), `_read_text_lines` (:533), `_parse_fortran_bool` (:514), `_parse_float` (:523): comment-header parser; requires the exact first comment line `# HEIDE_PATCH_B <label>`.
  - `read_header(path)` (:615) UNREFERENCED.
- Notes:
  - Verified: rejects `vasp_sample/CSO.dat` (no `# HEIDE_PATCH_B` line) and `vasp_sample/CPROJ.0000.0000.bin` (no ABI matches the Patch A layout).
  - Verified: a CSO file whose header says `SAXIS = 1 0 0` is rejected by `load_cso`.
  - No adapter converts a `MatrixDump` into `cso.py`'s per-ion dict, so T3 rotation cannot run on Patch B data.

### 3.12 `dmi_pipeline/cso.py`

- Status: LEGACY reader; the rotation math itself is format-free. 150 lines. Modified 2026-07-29.
- Purpose: legacy CSO text reader plus the offline SAXIS rotation used by gate T3.
- Definitions:
  - `read_cso(path)` (:19) HUB: six-column `ION IS I J Re Im` rows -> `{ion: array (4, lmmax, lmmax)}`. Comment lines are skipped, so it parses Patch A text (verified on `vasp_sample/CSO.dat`: 10 ions) and would parse Patch B text too.
  - `as_spin_matrix(cso_ion)` (:59), `_spin_matrix_to_cso_ion` (:72): (4, lm, lm) <-> (2, 2, lm, lm) through `SPIN_BLOCK_MAP`.
  - `EULER_CONVENTIONS` (8 strings), `_parse_convention` (:80), `spin_rotation(n_hat, convention)` (:89): the eight sign/dagger candidates and the 2x2 spin rotation.
  - `_rotate_with_convention` (:111), `rotate_saxis(cso_z, n_hat)` (:124): U^dagger C U per ion; `rotate_saxis` refuses unless `CSO_ROTATION_VALIDATED`.
  - `find_euler_convention(cso_z, cso_x, cso_y, x_hat, y_hat)` (:130): T3 search at 1e-10; the error message lists every candidate's deviation.
- Notes:
  - Live callers: `cli gate m0` (`read_cso`) and `cli gate t3` (`read_cso`, `find_euler_convention`). Inside the package, `as_spin_matrix` and `rotate_saxis` are used only by the unreferenced `cli._build_cso_source`; otherwise only the broken root scripts and tests use them.
  - Nothing writes rotated `CSO_x.dat` / `CSO_y.dat`, which `dmi trace` requires.
  - `read_cso` duplicates `dumpio.load_cso` with a different array shape.

### 3.13 `dmi_pipeline/cproj.py`

- Status: LEGACY. Patch A. 253 lines. Modified 2026-07-27.
- Purpose: frozen verbatim copy of the Patch A `read_cproj.py`. Assembles rank files by `block` or `cyclic` band placement and rebuilds COCC. The migration spec says to delete it.
- Definitions:
  - `load_all_cproj(pattern, order)` (:85), `_read_one_file` (:49), `_place` (:74): read the Patch A binary (7 int32 header fields, RSPIN, LMMAXC, LMBASE, then per-k records).
  - `get_ion_cproj(data, NK, ion)` (:139): (NRSPINORS, lm, NBANDS) slice; used only by `ta_td.py` (broken).
  - `rebuild_cocc(data)` (:164): DEPSUM contraction; used only by the unreferenced `gates.gate_m1`.
  - `load_cocc_dat` (alias of `_load_cocc_dat`, :205): Patch A COCC text -> array (lm, lm, ions, ncdij). Its only live use is `cli gate m0`.
  - `if __name__ == "__main__":` block: standalone COCC cross-check script.
- Notes:
  - Deleting it requires replacing `load_cocc_dat` in `cli gate m0` (or retiring M0, which the migration spec calls build-validation only), deleting `gates.gate_m1`, and removing or rewriting `ta_td.py`, `single_trace.py`, and `noisefloor.py`.

### 3.14 `dmi_pipeline/trace.py`

- Status: LIVE. Patch B. 222 lines. Modified 2026-09-14.
- Purpose: first-order SOC trace Delta E(1) for one configuration and one CSO axis.
- Definitions:
  - `compute_delta_E1(cproj, ferwe, cso)` (:82) HUB: sum over k of w_k, over bands of f_kn, over ions and the uu/dd blocks, of conj(c) C c. Written as explicit Python loops over ion, k-point, band, block, and both orbital indices (deliberately unvectorized, per its docstring). Returns the real total, imaginary total, per-ion imaginary parts, and per-k complex contributions.
  - `_assert_trace_inputs(cproj, ferwe, cso)` (:34): requires ISPIN = 1 and NRSPINORS = 2, NCDIJ covering `UU_IDX`/`DD_IDX`, and FERWE/CSO dimensions and NELECT agreeing with CPROJ.
  - `trace_config(cfg_dir, cso_dir, axis)` (:173) HUB: requires `cfg_dir/dump_P/DONE` and `cfg_dir/config.json`; loads CPROJ and FERWE from `dump_P` and CSO from `cso_dir/CSO_<axis>.dat`; asserts LSORBIT = F, LSPIRAL = T, QSPIRAL equal to the config's q, SAXIS = z, and the pinned build id if set; attaches SHA-256 provenance.
  - `_load_config_q_frac` (:127), `_assert_done_marker` (:149), `_trace_provenance` (:157): helpers.
  - `trace_row(*args, **kwargs)` (:213): stub that always raises; imported by `cli.py`, never called.
  - `TraceResult` (:23): record; its `sigma_eV` field is never set anywhere in the repo.
- Notes:
  - The rewrite removed `read_eigenval`, `read_kpoint_coordinates`, and `match_negative_kpoints`, breaking four importers (finding 2).
  - LSPIRAL = T is required, so a q = 0 dump written without LSPIRAL (the migration spec's N0 null configuration) would be rejected.

### 3.15 `dmi_pipeline/realized.py`

- Status: LIVE. Patch B frame handling. 371 lines. Modified 2026-09-12.
- Purpose: Stage-2 readback. Parses final OUTCAR moments, recovers realized psi and theta per sublattice, and gates single configurations and pairs.
- Definitions:
  - `read_realized(rundir, ms, target=None)` (:188) HUB: reads `config.json` unless a target is passed; raises `NotImplementedError` if `MINT.dat` exists; takes the last x/y/z magnetization tables and converts them with `frames.to_unwound(FRAME_MINT)`; computes theta = arccos(eps * m_z / |m|), psi_k = wrap(alpha - phi_ref) with no q.tau term, per-sublattice circular means, alpha residual RMS, theta spread, and relative moment deviation.
  - `_read_outcar_magnetization` (:128), `_parse_magnetization_block` (:103), `read_outcar_moments(rundir, n_ions)` (:180): strict parser for the `# of ion ... tot` tables.
  - `_read_penalty_and_lambda` (:150): best effort, using the last lines starting with `E_PENALTY` or `LAMBDA`. The OUTCAR INCAR echo line `LAMBDA = ...` also matches, so `lambda_final` can come from the input echo.
  - `realization_gate(realized, target, tol)` (:273) HUB: DEAD for non-uniform phases, non-uniform cone, or moment collapse; otherwise PASS if within tolerance of the target, else ACCEPTED.
  - `validate_realized_pair(plus_config, minus_config, *, tol_q, tol_psi, tol_theta, tol_magnitude)` (:294) HUB: both members in family; family and winding match; q_minus = -q_plus mod G; psi_minus = -psi_plus; theta and magnitude agreement. Returns PASS, WARN_USE_REALIZED_PAIR_ROW, or FAIL.
  - `Tolerances` (:57) with `from_conventions`, `wrap_to_pi` (:90), `angle_difference` (:94), `_circular_mean` (:99). `realized_state_gate.py` uses `wrap_to_pi` 10 times.
  - `RealizedState` (:38), `RealizationGateResult` (:72), `PairRealizationResult` (:78): records.
  - `lambda_ramp(...)` (:347) UNREFERENCED: lambda-schedule driver that takes a `run_vasp` callable.
- Notes:
  - Sublattice 2 is hard-coded as the psi sublattice here and in `design.py`, matching the two-sublattice model.

### 3.16 `dmi_pipeline/gates.py`

- Status: LIVE, mixed eras: Patch B dump gates, Patch A M0/M1 gates, and fit-level cross-validation. 619 lines. Modified 2026-09-15.
- Purpose: all validation checks, sharing one `GateResult` record. 12 of its 25 public functions have no production caller.
- Framework:
  - `GateResult` (:51), `run_gate` (:60), `to_gate_data` (:76), `RankDeficientFitError` (:64) HUB: `passed` is True, False, or None (NOT_APPLICABLE).
- Patch B gates (called by `cli gate` commands):
  - `gate_c0(cso, tol)` (:84): CSO structure check (C_dd = -C_uu; C_uu purely imaginary, antisymmetric, zero diagonal; spin-flip blocks zero). Side effect: sets `conventions.CSO_SIGN_VALIDATED = True` in-process.
  - `gate_m1_patch_b(cproj, ferwe, cocc, tol)` (:136) with `_rebuild_patch_b_cocc` (:114): rebuilds COCC with literal DEPSUM loops (six nested Python loops) and compares at 1e-10.
  - `gate_n0(trace_value_eV, threshold=1e-4)` (:150): null-trace check. The migration spec specifies 5e-4.
  - `gate_p0(trace_plus_eV, trace_minus_eV, floor_eV)` (:156): even-background ratio. `gate_i0(trace_result, tol)` (:164): imaginary part <= 1e-6 eV. `gate_r0(psi_error_deg, theta_error_deg, penalty_eV, ...)` (:169): checks pre-computed realized-state errors.
- Patch A gates:
  - `gate_m0(cso, cocc, spinorb_energy_per_site, tol)` (:235): called by `cli gate m0`. Checks that the diagonal blocks named by `SPIN_BLOCK_MAP` reproduce the per-site SOC energy; pins `UU_IDX`/`DD_IDX`.
  - `gate_m1(cproj_pattern, cocc_dat, tol)` (:205) with `SPIN_BLOCK_MAP_CANDIDATES`: UNREFERENCED. Uses `cproj.load_all_cproj` and `cproj.rebuild_cocc`.
- Trace and pair gates with no CLI wiring:
  - UNREFERENCED: `gate_imag` (:282), `gate_origin_shift` (:288), `gate_pair_realization` (:311), `gate_pair_repeatability` (:325).
  - TESTS-ONLY: `gate_parity` (:293; always passes, diagnostic only) and `gate_pair_observable` (:315). `PairTraceGateResult` (:301) is their record.
- Scan and model checks, all TESTS-ONLY: `noise_floor` (:334), `gate_lambda_scan` (:343), `gate_psi_independence` (:369) with `_orbit_slice` (:360), `class_sums` (:394), `gate_rank` (:610).
- Fit diagnostics (run automatically by `cli solve` through `cli._diagnostic_gates`):
  - `predict_holdout(manifest, orbits, fit_mask, predict_mask)` (:411): fits one row mask and predicts another; reduced chi^2; raises `RankDeficientFitError` naming the null-space parameters.
  - `gate_loo_cv(manifest, orbits)` (:465): leaves one measurement out at a time.
  - `gate_holdout_family(manifest, orbits, held_out)` (:448) with `_families_by_row` (:442): fits without one family and predicts it; NOT_APPLICABLE when the complement is rank-deficient.
  - `gate_class_sum_agreement(manifest, orbits)` (:531) with `_class_sum_matrix` (:502): F0-only fit in class-sum space versus the non-F0 fit projected through class sums.
- Notes:
  - Each fit diagnostic calls `solve.assemble` again, and `gate_loo_cv` re-assembles once per measurement (quadratic in measurement count).
  - `load_all_cproj` and `rebuild_cocc` are imported only for the unreferenced `gate_m1`.

### 3.17 `dmi_pipeline/solve.py`

- Status: LIVE. Format-free. 205 lines. Modified 2026-08-10. The migration docs mark it frozen.
- Purpose: assembles pair rows into a weighted least-squares system and solves it.
- Definitions:
  - `assemble(manifest, orbits)` (:42) HUB: one row per live measurement per axis. Fails closed on a missing partner, missing realization, unusable pair gate, missing raw trace, non-PASS row, sigma_y <= 0, or wrong design-row length. Weights are 1/sigma_y^2. Accepts objects or dicts via `_get_field` (:37).
  - `solve(M, y, w, orbits, kappa_max)` (:102) HUB: SVD of sqrt(W) M; rank threshold sigma_max / kappa_max, with a null-space error message built from parameter labels; covariance inv(M^T W M), sigma, residuals, worst direction, and every bond's DM vector.
  - `write_native_table` (:163), `write_tb2j_table` (:178; D = -0.5 * d in meV, both bond directions), `write_orbit_report` (:194), `_bond_line` (:156): TESTS-ONLY output writers; no CLI command calls them.
  - `Solution` (:24), `RowMeta` (:16): records.

### 3.18 `dmi_pipeline/report.py`

- Status: LIVE. Format-free. 133 lines. Modified 2026-08-10.
- Purpose: renders a Markdown report from a manifest.
- Definitions:
  - `render_report(manifest)` (:27): conventions table, orbits, rank progression, holdout viability, two-trace measurement inventory with common-mode diagnostics, predicted sigma (eV), solution, and gates (LOO-CV first, then holdout, then the rest).
  - `write_report(manifest_or_path, path)` (:128): used by `cli report`.
  - `_gate_status` (:18), `_value` (:12): three-way PASS / FAIL / NOT_APPLICABLE rendering, and a dict-or-attribute getter.
- Notes:
  - Unused import: `from . import conventions`.

### 3.19 `dmi_pipeline/materialize.py`

- Status: ISSUES. Pre-Patch B layout. 232 lines. Modified 2026-08-10.
- Purpose: Stage 1. Writes Stage-2 VASP inputs for both sides of every measurement, plus Stage-3 provenance directories.
- Definitions:
  - `materialize(manifest, base_dir, base_incar, kpoints, potcar_spec)` (:140) HUB: loads the structure; checks POTCAR species; assigns `chain_from`; validates every pair (minus q = reduce_to_bz(-plus q), psi values sum to 0 mod 2*pi, same theta and winding) before writing anything; then writes `measurements/<measurement_id>/<side>/stage2/` (INCAR, POSCAR, POTCAR, KPOINTS, config.json) and `.../stage3/` (config.json, provenance.json). Returns the manifest with execution paths and config digests.
  - `_materialize_one(...)` (:52): INCAR = base_incar, then `COMMON_INCAR` (LNONCOLLINEAR, LSORBIT = F, LSPIRAL = T, ISYM = -1), then family tags, dropping None values; MAGMOM from `spin_targets`; M_CONSTR (mode 1) for F1 and F2.
  - `_family_incar_tags(family)` (:23): F0 LZEROZ = T; F1 LZEROZ = `F1_USES_LZEROZ` and I_CONSTRAINED_M = 1; F2 LZEROZ = F and I_CONSTRAINED_M = 1. `LAMBDA = None` is dropped, so no LAMBDA line is ever written.
  - `_chain_from(config, all_configs)` (:92): same-side restart parent. F1 chains from F1 at psi/2, else from F0, at the same q. F2 chains from the next smaller theta with the same winding, else from F0.
  - `_config_digest` (:133), `_incar_value` (:35), `_ordered_species` (:41): helpers.
- Notes:
  - Raises with the shipped conventions (finding 3).
  - Layout differs from the migration spec (`material/ref`, `material/dump_C`, `configs/<id>/stage2`, `configs/<id>/dump_P`, DONE-gated creation, INCAR tag whitelist).

### 3.20 `dmi_pipeline/execution.py`

- Status: ISSUES. Patch A Stage-3 contract. 435 lines. Modified 2026-08-11.
- Purpose: writes a reviewable bash runner plus `execution_plan.json` for Stage 2 and Stage 3. Never runs VASP.
- Definitions:
  - `write_run_script(manifest, base_dir, out_path, stage3_template, settings)` (:412) HUB: requires `out_path` directly inside `base_dir` and an existing Stage-3 INCAR template; validates and orders jobs; writes both files atomically; sets the executable bit.
  - `RunScriptConfig` (:29): mode `scheduler` or `inline`, scheduler command, runners, required-artifact lists. Defaults: Stage 2 requires `OUTCAR`, `WAVECAR`, `CHGCAR`; Stage 3 requires `CSO_z.dat`, `COCC.dat`, `EIGENVAL`, and a match for `CPROJ.*.*.bin`.
  - `_plan_configs` (:87), `_ordered_stage2_configs` (:121): select non-excluded pair members; depth-first ordering that rejects missing, self, cross-parity, excluded, q-mismatched, family-incompatible, and cyclic restart chains.
  - `_plan_payload` (:162), `_script_text` (:219): JSON job list, and the bash script (completion sentinels, WAVECAR/CHGCAR symlinks, per-lambda attempts rewritten with `awk`, Stage-3 template copy, `sbatch --dependency=afterok`).
  - `_shell` (:62), `_shell_array` (:66), `_atomic_write` (:70): helpers.
- Notes:
  - Its Stage-3 required artifacts are Patch A, while `dmi trace` reads Patch B `dump_P` files (finding 4).
  - Supports per-configuration `lambda_schedule`, but nothing in the repo sets one.

### 3.21 `dmi_pipeline/cli.py`

- Status: LIVE entry point; several commands have issues (section 1.3). Mixed eras. 728 lines. Modified 2026-09-15.
- Purpose: the click group `cli`.
- Commands (line of the function definition): `plan` (:41), `report` (:52), `materialize` (:61), `write-run-script` (:94), `realize` (:173), `trace` (:290), `form-pairs` (:334), `estimate-pair-noise` (:389), `solve` (:483), `trace-one` (:533), and the `gate` group (:508) with `m0` (:593), `w0` (:610), `c0` (:623), `m1` (:635), `n0` (:652), `p0` (:661), `i0` (:670), `r0` (:682), `t3` (:707).
- Helpers:
  - `_load_manifest_with_conventions` (:567), `_report_and_maybe_append` (:547) HUB: load a manifest and apply its pins; append a gate result and persist pins. Only `gate m0` and `gate t3` use the persisting path.
  - `_rebuild_orbits(manifest)` (:412): recomputes orbits from `meta.poscar_path`, `magnetic_spec`, and `r_max`.
  - `_solution_data` (:426), `_diagnostic_gates` (:455): solution serialization (per-bond d and sigma), and the three fit diagnostics after each solve; `ValueError` and `AssertionError` from those gates are swallowed.
  - `_config_run_directory` (:150), `_config_stage3_directory` (:159), `_build_ms` (:75), `_existing_gate` (:512), `_print_gate_result` (:519), `_read_spinorb_energies` (:576).
  - UNREFERENCED: `_row_object` (:234) and `_build_cso_source` (:248) with its constant `_AXES`: legacy three-dump / rotated-single-dump CSO selection.
- Notes:
  - Unused import `trace_row`. `as_spin_matrix`, `rotate_saxis`, and `Row` are imported only for the unreferenced helpers.
  - `trace` writes `trace_gate = "PASS"` for every trace without running I0.

### 3.22 `dmi_pipeline/ta_td.py`

- Status: BROKEN. Patch A. 338 lines. Modified 2026-08-13.
- Purpose: T-A/T-D diagnostics from `TA_TD_extraction_reference.md`. Decomposes the CSO uu block into real/imaginary symmetric/antisymmetric parts, and compares plain, component-filtered, and conjugated traces between +q and -q run directories.
- Definitions:
  - `load_ta_td_report(plus_directory, minus_directory, *, cproj_order, ...)` (:293): loads two Patch A directories with `load_all_cproj`, `read_cso`, and `read_eigenval`, then builds the report.
  - `build_ta_td_report(...)` (:179): JSON-safe evidence and verdicts (trace partition, operator conjugation, state pairing, CSO agreement, spectrum agreement).
  - `contract_trace(...)` (:85): einsum contraction with optional CPROJ conjugation or block transform.
  - `decompose_operator` (:33), `clean_imaginary_antisymmetric` (:48), `real_symmetric_contaminant` (:53), `_operator_summary` (:125), `_trace_dict` (:141), `_outcar_evidence` (:150), `_sanity_summary` (:159), `_validate_inputs` (:58), `DiagnosticTrace` (:26).
- Notes:
  - Verified: `from .trace import read_eigenval` raises `ImportError`.
  - Only importer: `ta_td_extract.py`. Its test file was deleted; only stale bytecode remains in `tests/__pycache__/`.

### 3.23 `dmi_pipeline/__init__.py`

- Status: LIVE. 3 lines.
- Contents: a docstring and `__version__ = "0.1.0"` (UNREFERENCED). There is no `pyproject.toml` or `setup.py`; the package runs from the `pipeline v2/` directory.

## 4. Root scripts

### 4.1 `run_dmi.py`

- Status: LIVE. 25 lines. Modified 2026-09-15.
- Adds the repo root to `sys.path` and calls `dmi_pipeline.cli.cli()`. Its docstring examples use the current command syntax (`gate w0`, `gate m1 dump_P`, `gate c0`, `trace-one`).

### 4.2 `realized_state_gate.py`

- Status: LIVE. Format-free (reads OUTCAR, INCAR, POSCAR, OSZICAR). 669 lines. Modified 2026-08-13. Covered by `tests/test_realized_state_gate.py` (14 tests).
- Purpose: answers, for one run directory, whether the SCF realized the requested spin state. Reads QSPIRAL and the vector M_CONSTR (or MAGMOM) from INCAR, the final OUTCAR moments, POSCAR, and the last `E_p` line of OSZICAR. Edits nothing.
- Definitions:
  - `run(directory=".", realized_frame="lab")` (:424) HUB: finds magnetic ions by |M| > 0.5 mu_B; groups them into exactly two geometric sublattices; takes eps from the target z components, or assumes the BFO signs (+1, -1) for planar seeds; checks that a psi = 0 seed from `spin_targets` inverts to 0; inverts psi per site (with the 2*pi*q.tau term for `lab`, without it for `unwound`); compares the gauge-invariant psi_2 - psi_1, theta, |M|, and alpha RMS with the target (2 deg phase, 2 deg theta, |M| > 0.5 mu_B, 2 deg alpha RMS). Returns a result dict with a PASS/FAIL verdict.
  - `print_report(result)` (:557): human-readable report, including per-ion M_CONSTR versus realized unit directions, the OUTCAR echo of I_CONSTRAINED_M / LAMBDA / LSPIRAL / LZEROZ, and the OSZICAR E_p line.
  - `write_m_constr(rundir, psi_target, theta_target)` (:486): prints a unit-vector M_CONSTR that keeps the realized gauge psi_1 and sets psi_2 - psi_1 = psi_target; asserts its own round trip.
  - `main(argv)` (:621): hand-written argument loop for `--realized-frame lab|unwound` and `--write-mconstr [degrees]`.
  - INCAR, OUTCAR, OSZICAR scraping: `_read_incar` (:51), `_read_incar_text` (:337; joins backslash continuations), `_numbers` (:57), `_qspiral` (:67), `_parse_vector_tag` (:76), `_target_moments` (:85), `_outcar_echo_tags` (:329), `_last_penalty` (:373), `TargetMoments` (:46).
  - Structure and inversion helpers: `_build_magnetic_structure` (:138), `_subgroups` (:95), `_eps_from_target` (:110), `_eps_by_sublattice` (:175), `_psi_from_vectors` (:188), `_psi_summary` (:213), `_fallback_realized` (:226), `_phase_difference_from_magnetic_vectors` (:248), `_phase_difference_from_full_vectors` (:268), `_target_phase_difference` (:276), `_seed_phase_calibration` (:285), `_phase_rms_by_sublattice` (:301), `_target_theta` (:316), `_constraint_direction_comparison` (:384), `_format_tags` (:552), `_deg` (:380).
- Notes:
  - Default `realized_frame = "lab"` differs from the pinned `conventions.FRAME_MINT = "unwound"`; `USAGE.md` calls lab the historical default.
  - Keeps a `try/except ImportError` fallback (lines 23-34) for an older `realized.py` without `read_outcar_moments`; that function now exists.
  - `run()` also calls `realized.read_realized` but uses only its theta and magnitudes; psi always comes from the script's own inversion.
  - `MOMENT_RELATIVE_TOLERANCE = 0.10` is defined but not used.

### 4.3 `single_trace.py`

- Status: BROKEN. Patch A. 245 lines. Modified 2026-08-14.
- Purpose: one raw trace for one Patch A directory: EIGENVAL occupations, explicit `--cproj-order`, `CSO_z.dat` with optional offline rotation, and a k / -k pairing printout.
- Definitions: `run_single_trace` (:74), `main` (:224), `_print_result` (:189), `_build_parser` (:162), `_cso_diagonal_blocks` (:46), `_check_cso_channel_counts` (:65), `_parse_axis` (:32), `_require_file` (:41).
- Notes:
  - Verified `ImportError`: imports `match_negative_kpoints`, `read_eigenval`, and `read_kpoint_coordinates` from `dmi_pipeline.trace`. Also calls the old six-argument `compute_delta_E1`.
  - `dmi trace-one` is the Patch B equivalent. The migration spec lists this file for deletion, but `USAGE.md` still documents it.

### 4.4 `ta_td_extract.py`

- Status: BROKEN. Patch A. 94 lines. Modified 2026-08-13.
- Purpose: argparse wrapper around `dmi_pipeline.ta_td.load_ta_td_report`; writes JSON evidence and prints verdicts.
- Definitions: `main` (:69), `_build_parser` (:18), `_print_summary` (:39).
- Notes: broken through `dmi_pipeline/ta_td.py`. `USAGE.md` still documents it.

### 4.5 `noisefloor.py`

- Status: BROKEN. Patch A. 453 lines. Modified 2026-08-06.
- Purpose: single-file noise-floor workflow with the commands `gen2`, `gen3`, `process`, and `selftest`.
- Definitions:
  - Editable config block (lines 15-32): `TEMPLATE`, `ROOT`, `LAUNCH`, `LINKMODE`, `CPROJ_BAND_ORDER = "cyclic"`, `N_M`, `MAG_SPECIES`, `MOMENT`, `EPS`, `TRIM_QS`, `PARITY_QS`, `RESTART_Q`, `AXES`; then `OWNED_KEYS`.
  - `cases()` (:38): 3 TRIM cases, 2 plus/minus parity pairs, and 2 restart seeds (0 and 30 deg).
  - `gen2()` (:219): Stage-2 directories from a template. INCARs are edited with pymatgen `Incar` through `edit_incar` (:173, with a MAGMOM round-trip check), `stage2_overrides` (:207), `magmom_values` (:111), `magmom_line` (:123), `explicit_magmom_vectors` (:129), `incar_magmom_values` (:157), `incar_magmom_vectors` (:168), `qspiral_string` (:127), and `parse_poscar` (:69).
  - `gen3()` (:253): per-axis `soc_x`, `soc_y`, `soc_z` dump directories with linked WAVECAR/CHGCAR (`link_or_copy`, :242).
  - `run_trace(soc_dir, scf_dir)` (:296): Patch A trace (`load_all_cproj`, `read_eigenval`, old `compute_delta_E1`).
  - `process()` (:344): sigma_trim, sigma_parity / sqrt(2), sigma_restart / sqrt(2); writes `samples.csv` and `report.txt` with warnings.
  - `selftest()` (:420), `rms` (:342), `main` (:438); file helpers `require_file` (:47), `require_dir` (:50), `make_dir` (:53), `copy_created` (:58), `write_created` (:64), `run_script` (:215).
- Notes:
  - Verified `ImportError` at module import, so even `selftest` cannot run.
  - Diverged from its own spec (`noisefloor_simple_spec.md` requires stdlib + numpy only and roughly 350 lines at most).
  - `new_direction.md` section 9 states that TRIM and parity-sum noise estimates are invalid while the even background exists; `process` computes exactly those.
  - The pytest cache still lists deleted `tests/noisefloor/test_*.py` files that once covered this script.

## 5. Test suite (`tests/`)

Run from `pipeline v2/`. 180 tests, all passing in 41.3 s (verified). `tests/fixtures.py` is a helper module, not a test file.

| File | Tests | What it covers | Depends on |
|---|---|---|---|
| `tests/fixtures.py` | helper | Synthetic Patch B writer: `write_fake_dump` (CPROJ binaries across a rank grid, FERWE.dat, COCC.dat computed by DEPSUM from the same CPROJ), `make_clean_cso`, `make_broken_cso`, `write_cso`, `corrupt` | dumpio constants |
| `tests/fixtures/bfo_magnetic.json` | data | Magnetic spec (Fe, by_poscar_order, eps [1, -1], moment [4.1, 4.1]) for the root `POSCAR` | none |
| `test_cli_pipeline.py` | 13 | CLI `materialize`, `realize`, `gate m0`, `gate t3`, the Patch B gate commands, `gate n0` failure exit code, `trace` (with `trace_config` monkeypatched), `form-pairs` and `solve` refusals, `solve` recovering a known x, idempotence, `--force` | cli, fixtures.py, root POSCAR; autouse fixture forces frames to `internal_z_cone` |
| `test_conventions.py` | 3 | Pinned values, `set_from_manifest`, dump-format-version rejection | conventions, manifest |
| `test_cso_rotation.py` | 11 | `read_cso` parsing, `as_spin_matrix`, rotation unitarity, T3 recovery and failure message, `rotate_saxis` identity, Hermiticity, and guard | cso |
| `test_dumpio.py` | 14 | Round trip, rank-grid independence (4 grids), W0 missing file / duplicate record / header mismatch, header tampering, `assert_header`, FERWE failures, COCC parsing | dumpio, fixtures.py |
| `test_execution.py` | 6 | Script content and job ordering, invalid chain parents, cycles, F0 lambda schedule rejection, CLI records `ExecutionPlanRecord`; runs `bash -n` when bash is available | execution, cli |
| `test_frames.py` | 2 | Lab versus unwound meaning of a `spin_targets` seed; unwound readback recovers psi = 0 | frames, targets |
| `test_gates.py` | 23 | C0 clean and 5 broken kinds, Patch B M1 corruption, N0/P0/I0, raw common mode, noise floor, lambda scan, psi independence, class sums, gate_rank, `to_gate_data`, `predict_holdout`, pair observable | gates, dumpio, fixtures.py |
| `test_manifest.py` | 12 | Round trip, missing references, atomic save, duplicate ids, schema v1 rejection, 7 fail-closed pair-completeness violations | manifest |
| `test_materialize.py` | 8 | Stage directories per side, identical POSCARs, INCAR family tags, F1 LZEROZ guard, QSPIRAL and config.json round trip, invalid pair rejected before writing, `chain_from` persisted, missing POTCAR species | materialize; autouse fixture forces frames to `internal_z_cone` |
| `test_model.py` | 4 | Directed-bond oracle equivalence, BFO rank progression 4 / 6 / 9, F2 zeroing of sublattice-2 orbits, design_matrix versus reference | model, orbits |
| `test_observables.py` | 5 | Normalization, common-mode cancellation, covariance propagation and clamp, side provenance, paired noise estimate | observables |
| `test_orbits.py` | 6 | Simple-cubic bond counts, canonicalization coverage, BFO 3 orbits / 9 parameters, projector properties and determinism, propagation, bond-vector coverage | orbits |
| `test_planner_cli.py` | 15 | Rank progression, CLI plan plus report, YAML rejection, holdout augmentation and unreachable-family error, F1 psi exclusion, obsolete knobs ignored, pair-key de-duplication, axis labels, two `select_rows` regressions | planner, cli, report |
| `test_realized.py` | 7 | psi/theta recovery, PASS, ACCEPTED, DEAD (non-uniform phase, moment collapse), config.json requirement, pair statuses | realized, frames |
| `test_realized_state_gate.py` | 14 | The root script `realized_state_gate.py` (imported directly, so pytest must run from `pipeline v2/`) | realized_state_gate, realized, targets |
| `test_report.py` | 2 | NOT_APPLICABLE rendered distinctly from PASS | report |
| `test_solve.py` | 4 | Round trip plus output writers, rank-failure message, realized values in assembly, non-PASS rows fail closed | solve, design, model |
| `test_structures.py` | 3 | BFO metadata, moment count check, assignment mode check | structures |
| `test_targets.py` | 18 | `spin_targets` oracle and norms, rotations, `to_frame` (old vocabulary), MAGMOM / M_CONSTR / RWIGS strings, eps bookkeeping | targets; autouse fixture forces frames to `internal_z_cone` |
| `test_trace.py` | 5 | Density-matrix oracle, spinor-swap sign flip, zero imaginary part for Hermitian CSO, QSPIRAL mismatch rejection, unrelated EIGENVAL ignored | trace, dumpio, fixtures.py |
| `test_two_trace.py` | 5 | Exact pair row equals legacy row, realized mismatch uses both kernels, F2 partner keeps winding, synthetic solve cancels common mode, planner emits unique pairs | design, model, planner, realized, solve |

Notes:
- Three test files force pre-Patch B frame strings with autouse fixtures, which is why the suite passes while `materialize` fails with the shipped conventions (finding 3).
- CLI commands with no success-path test: `form-pairs`, `estimate-pair-noise`, `trace-one`.
- Stale caches: `.pytest_cache/v/cache/nodeids` and `lastfailed` list deleted tests (`tests/noisefloor/*`, `tests/test_single_trace.py`, `tests/test_ta_td.py`, `phase_test.py`). `tests/__pycache__/` holds bytecode for `test_phase_test`, `test_single_trace`, and `test_ta_td`; the root `__pycache__/` holds `phase_test` bytecode.

## 6. `constrsint probe/` (constraint_probe)

- Status: LIVE as a standalone suite. 56 tests pass in 1.4 s when run from inside `constrsint probe/` (verified). The directory name is misspelled.
- Contents: package `constraint_probe/`, `pyproject.toml` (console script `probe = constraint_probe.cli:cli`; dependencies numpy, pymatgen, pyyaml, click), `constraint_probe.egg-info/` (build metadata), `constraint_probe_spec.md`, `tests/` (4 test files and 13 fixture files), `.pytest_cache/`.
- Independence: it does not import `dmi_pipeline`, and `dmi_pipeline` does not import it.
- Purpose: decides whether VASP's `I_CONSTRAINED_M` works under `LSPIRAL` on a given build, and prints values to copy by hand into `conventions.py`: `FRAME_MCONSTR` (verdict V2), `PENALTY_SIGN` (V7), `LAMBDA_RECOMMENDED` (V4), `F1_USES_LZEROZ` (V8).

| File | Lines | Contents |
|---|---|---|
| `constraint_probe/config.py` | 166 | `ProbeConfig`; `load_config` reads YAML; `OWNED_INCAR_KEYS`; `_validate` checks RWIGS coverage, exactly two sublattices, commensurate q values, a non-TRIM `q_large`, seed files, and no suite-owned keys in `base_incar` |
| `constraint_probe/geometry.py` | 203 | `MagGeom`, `load_geometry` (alternating sublattices), `species_order`, `phi_ref`, `spin_targets` (intentional copy of the dmi_pipeline formula), `decompose` (psi including the q.tau term), `frame_identity`, `frame_unwind_spiral`, `frame_wind_spiral`, `wrap_to_pi`, `wrap_to_2pi` |
| `constraint_probe/incar.py` | 194 | `CaseSpec`, `case_to_dict`, `case_from_dict`, `build_targets`, `build_incar` (sets LORBIT = 2 on purpose rather than the spec's 11), `write_case` (POSCAR and POTCAR copies, KPOINTS, optional job.sh and seed CHGCAR, INCAR, case.json) |
| `constraint_probe/outcar.py` | 366 | `parse_outcar` (INCAR echo, final magnetization tables, TOTEN, penalty patterns, electronic step count versus NELM, OSZICAR cross-check and E_p fallback, RWIGS echo check, build banner), `parse_oszicar`, `oszicar_converged` |
| `constraint_probe/tests.py` | 652 | Not a pytest file. `build_cases` (cases T1-T5 including the lambda ladder and T4_lzeroz), decision tables `v0_tag_recognized` through `v8_lzeroz`, `overall_verdict` (GREEN, AMBER, RED, FRAME, INCONCLUSIVE), `CaseObservation` |
| `constraint_probe/analyze.py` | 403 | `analyze` (parses every case, rotates OUTCAR moments with `frame_wind_spiral`, applies V0-V8, writes `results.json` and `report.md` with a transcription block), `results_from_json`, `render_report`, `write_generation_meta`, `write_run_script` |
| `constraint_probe/cli.py` | 82 | `probe generate`, `probe analyze`, `probe report` |
| `constraint_probe/__init__.py` | 4 | Docstring |
| `constraint_probe/templates/run_all.sh` | 56 | sbatch dependency-chain template; runs `eval "$RUNNER"` when a case has no job.sh |

Tests: `test_analyze.py` 25, `test_geometry.py` 7, `test_incar.py` 13, `test_outcar.py` 11. Fixtures: 5 OUTCAR texts, 2 OSZICAR texts, 3 POSCARs, and dummy POTCAR, CHGCAR, and job script files.

Relationship to `dmi_pipeline` now:
- Its V2 frame answer ("lab") was later overturned. `pipeline_migration_patch_b.md` section 3 explains that the no-op constraint cannot distinguish the frames; `FRAME_MCONSTR` is now pinned to "unwound" from a later run.
- Of its four outputs, only `F1_USES_LZEROZ` exists in `conventions.py`, and it is still unpinned. `PENALTY_SIGN` and `LAMBDA_RECOMMENDED` are not defined or used anywhere in `dmi_pipeline`.
- `analyze` treats OUTCAR moments as co-rotating and winds them into the lab frame before `decompose` subtracts q.tau; `dmi_pipeline/realized.py` reaches the same psi by skipping the q.tau term. Both assume OUTCAR reports unwound moments.

## 7. Duplicated logic

| Logic | Copies | Comment |
|---|---|---|
| Target spin vectors | `targets.spin_targets`; `constraint_probe/geometry.spin_targets`; `noisefloor.magmom_values`; inline in `realized_state_gate.write_m_constr`; test oracles in `test_targets.py`, `test_realized.py`, `test_cli_pipeline.py` | The probe copy is intentional (independent check) |
| psi/theta inversion from moments | `realized.read_realized`; `realized_state_gate._psi_from_vectors`, `_psi_summary`, `_fallback_realized`; `constraint_probe/geometry.decompose` | Three implementations with different frame handling |
| OUTCAR magnetization table parsing | `realized._read_outcar_magnetization`; `constraint_probe/outcar._parse_magnetization` | Synthetic OUTCAR writers are also repeated in `test_cli_pipeline.py`, `test_realized.py`, `test_realized_state_gate.py` |
| INCAR parsing and editing | `realized_state_gate._read_incar_text`; `realized_state_gate._outcar_echo_tags`; `constraint_probe/outcar._parse_incar_echo`; `noisefloor.edit_incar` (pymatgen) | |
| Design-row loop | `model.design_row`; `design.configuration_kernel` | Same loop, different prefactor |
| CSO text reading | `cso.read_cso` (dict of (4, lm, lm)); `dumpio.load_cso` (array (NCDIJ, NIONS, LMDIM, LMDIM)) | Different shapes: M0/T3 use one, C0/trace the other |
| CPROJ reading | `cproj.load_all_cproj` (Patch A); `dumpio.load_cproj` (Patch B) | |
| COCC rebuild (DEPSUM) | `cproj.rebuild_cocc`; `gates._rebuild_patch_b_cocc`; inline in `tests/fixtures.write_fake_dump` | |
| Trace contraction | `trace.compute_delta_E1`; `ta_td.contract_trace`; `test_trace._density_oracle` | The test oracle is intentional |
| Run-script generation | `execution._script_text`; `constraint_probe/templates/run_all.sh`; `noisefloor.run_script` | |
| Atomic file write | `manifest.save`; `execution._atomic_write` | |
| Dict-or-attribute getter | `design._value`; `solve._get_field`; `report._value` | |
| Angle wrapping | `realized.wrap_to_pi`; `planner.wrap_angle`; `constraint_probe/geometry.wrap_to_pi` | |
| Species order | `materialize._ordered_species`; inline in `targets.rwigs_string`; `constraint_probe/geometry.species_order` | |

## 8. Docs and data files

### 8.1 Markdown documents

| File | Lines | Modified | Status | What it is, and how it relates to the code now |
|---|---|---|---|---|
| `USAGE.md` | 470 | 2026-08-14 | STALE (partly current) | User guide. Current for the plan-to-solve outline and `realized_state_gate.py`. Stale for `single_trace.py` and `ta_td_extract.py` (broken), `CPROJ_BAND_ORDER` (removed), `gate m1 --cproj-glob ... --cocc` (now `gate m1 DUMP_DIR`), planner partners / lambda scans / null checks (removed), and per-configuration SOC Stage-3 dumps (Patch A). |
| `dmi_pipeline_build_spec.md` | 935 | 2026-08-11 | STALE (architecture reference) | Original module-by-module build spec with a prepended two-trace update. Still describes orbits, model, planner, and solve accurately; its reader, trace, gate, and manifest sections are Patch A / schema v1. |
| `decorated_spiral_implementation.md` | 403 | 2026-08-10 | Background | Physics and VASP engineering plan: W0-W5 probes, lambda ramp, realization gate, T0-T9 test ladder, risk register. Its Stage-3 protocol is superseded by Patch B. |
| `new_direction.md` | 1,310 | 2026-08-11 | Mostly implemented | One-trace to two-trace change spec. Implemented: `observables.py`, `design.py`, the measurement schema, the pair realization gate, `form-pairs`, `estimate-pair-noise`. Not wired: pair repeatability and common-mode stability gates, spectrum parity gate. |
| `pipeline_migration_patch_b.md` | 226 | 2026-09-12 | Partly implemented | Patch B migration spec. Implemented: `dumpio.py`, frame pins, `trace_config`, C0/M1/N0/P0/I0/R0 gate functions. Not implemented: `material/ref` and `dump_C` layout, INCAR templates and tag whitelist, `finish`/`submit`/`status` commands, DONE-gated materialize, manifest status fields, rotated CSO files, solve blocking on C0/N0, deletion of `cproj.py` and `single_trace.py`. |
| `patch_b_audit.md` | 174 | 2026-09-12 | Reference | Audit of the migration spec against the Fortran writer (`csodump.F`); the source of `dumpio`'s separate parsers and ABI probe. Its "current package" findings predate the rewrite, and it cites Fortran files under `vasp patch/vasp files/` outside this directory. |
| `test_migration_spec.md` | 137 | 2026-09-15 | Partly implemented | Test migration plan. Implemented: `tests/fixtures.py`, `test_dumpio.py`, `test_trace.py` (including the spinor-swap oracle), Patch B parts of `test_gates.py`. Not implemented: EIGENVAL-mismatch warning, three-frame M_CONSTR round trip, blocking-relationship tests, Patch B `test_materialize.py`, manifest schema extensions. |
| `jiso_extension_spec.md` | 396 | 2026-07-27 | Not implemented | Isotropic exchange J extraction from Stage-2 energies. No `energies.py`, `design_row_J`, `solve_exchange`, or related gates exist. |
| `noisefloor_simple_spec.md` | 196 | 2026-08-04 | STALE | Spec for `noisefloor.py`, which diverged from it and is now broken. |
| `TA_TD_extraction_reference.md` | 269 | 2026-08-13 | Historical | T-A/T-D diagnostic recipe on Patch A +q/-q data; records the ~0.63 eV even background that motivated the two-trace method. Implemented by the broken `ta_td.py`. |
| `constrsint probe/constraint_probe_spec.md` | 395 | 2026-07-28 | Reference | Spec for the probe suite; matches its code apart from deliberate deviations (LORBIT = 2, OSZICAR penalty fallback, `frame_wind_spiral`). |
| `report.md` | 89 | 2026-07-27 | STALE | Generated from the schema v1 manifest; shows old partner, lambda_scan, and psi_scan roles. |

### 8.2 Data, config, and cache files

| Path | Size | Status | Notes |
|---|---|---|---|
| `POSCAR` | 17 lines | Required | BFO R3c cell (Fe2 Bi2 O6). Read by 12 test files. |
| `tests/fixtures/bfo_magnetic.json` | 6 lines | Required | Magnetic spec for the root POSCAR. |
| `campaign.json` | 11 lines | Example | Minimal `plan` config; no test uses it. |
| `manifest.json` | 988 KB | STALE | Schema version 1 (configs carry `partner_id` and `rows`; no `measurements`). `manifest.load` rejects it (verified). |
| `vasp_sample/` | 247 MB | Unused | Real VASP 6.4.2 Patch A run (BFO, 216 k-points, 152 bands): 16 CPROJ binaries (7.5 MB each), `vasprun.xml` (121 MB), OUTCAR, EIGENVAL, CSO.dat, COCC.dat, INCAR, POSCAR, and a stale `__pycache__/`. No code or test refers to it. `dumpio` cannot read it; legacy `cproj`/`cso` can. |
| `.pytest_cache/`, `__pycache__/`, `tests/__pycache__/`, `dmi_pipeline/__pycache__/`, `vasp_sample/__pycache__/` | small | STALE | Regenerated automatically; several entries refer to deleted files (`phase_test.py`, `test_single_trace`, `test_ta_td`, `tests/noisefloor/`, old `read_cproj` and `trace` modules). |
| `.claude/settings.local.json` | 10 lines | Tooling | Claude Code permission allowlist for pytest commands. |
| `.vscode/settings.json` | 3 lines | Tooling | Selects the conda environment manager. |

## 9. Unreferenced code in `dmi_pipeline`

### 9.1 Zero references anywhere (17)

- `dmi_pipeline/__init__.py:3` `__version__`
- `dmi_pipeline/cli.py:234` `_row_object`
- `dmi_pipeline/cli.py:248` `_build_cso_source`
- `dmi_pipeline/dumpio.py:37` `CPROJ_FORMAT_VERSION`
- `dmi_pipeline/dumpio.py:615` `read_header`
- `dmi_pipeline/frames.py:79` `from_unwound`
- `dmi_pipeline/gates.py:205` `gate_m1`
- `dmi_pipeline/gates.py:282` `gate_imag`
- `dmi_pipeline/gates.py:288` `gate_origin_shift`
- `dmi_pipeline/gates.py:311` `gate_pair_realization`
- `dmi_pipeline/gates.py:325` `gate_pair_repeatability`
- `dmi_pipeline/manifest.py:125` `RowData`
- `dmi_pipeline/manifest.py:382` `append_configs`
- `dmi_pipeline/model.py:89` `y_from_delta_E1`
- `dmi_pipeline/planner.py:142` `CandidateMeasurement`
- `dmi_pipeline/realized.py:347` `lambda_ramp`
- `dmi_pipeline/targets.py:97` `from_frame`

### 9.2 Referenced only by tests (12)

- `dmi_pipeline/gates.py:293` `gate_parity`
- `dmi_pipeline/gates.py:315` `gate_pair_observable`
- `dmi_pipeline/gates.py:334` `noise_floor` (a local variable in `gate_class_sum_agreement` shares the name; grep confirms only tests call the function)
- `dmi_pipeline/gates.py:343` `gate_lambda_scan`
- `dmi_pipeline/gates.py:369` `gate_psi_independence`
- `dmi_pipeline/gates.py:394` `class_sums`
- `dmi_pipeline/gates.py:610` `gate_rank`
- `dmi_pipeline/model.py:77` `design_row_reference`
- `dmi_pipeline/model.py:95` `e_dm_oracle`
- `dmi_pipeline/solve.py:163` `write_native_table`
- `dmi_pipeline/solve.py:178` `write_tb2j_table`
- `dmi_pipeline/solve.py:194` `write_orbit_report`

### 9.3 Reachable only through dead, test-only, or broken code

- `planner.CandidateConfig` (:122): only inside `CandidateMeasurement`.
- `cli._AXES`: only inside `_build_cso_source`.
- `frames.unwound_to_lab` (:64): only via `from_unwound` and tests.
- `model.design_row` (:50), `model.design_matrix` (:82), `model._n_m_from_orbits` (:109): only via tests; `planner.py` imports `design_matrix` without calling it.
- `gates.SPIN_BLOCK_MAP_CANDIDATES`: only via `gate_m1`. `gates._orbit_slice` (:360): only via `gate_psi_independence`. `gates.PairTraceGateResult` (:301): only via the dead or test-only pair gates.
- `cproj.rebuild_cocc` (:164): only via `gates.gate_m1`. `cproj.get_ion_cproj` (:139) and `cproj.load_all_cproj` (:85): only via `gates.gate_m1`, `ta_td.py`, `single_trace.py`, `noisefloor.py`.
- `cso.as_spin_matrix` (:59) and `cso.rotate_saxis` (:124): in production only via `cli._build_cso_source` and the broken scripts (tests use them).
- `trace.trace_row` (:213): imported by `cli.py`, never called.
- `solve._bond_line` (:156): only via the test-only writers.
- All of `dmi_pipeline/ta_td.py`: its only importer is the broken `ta_td_extract.py`.

### 9.4 Unused imports, parameters, and fields

- `planner.py`: import `design_matrix`; local `holdout_added_config_keys` (:545); `CampaignConfig` fields `n_partners`, `n_lambda_scan`, `n_null_checks`, `schema_version`.
- `model.py`: import `all_bond_vectors`. `report.py`: import `conventions`. `cli.py`: import `trace_row`. `gates.py`: imports `load_all_cproj`, `rebuild_cocc` (used only by the unreferenced `gate_m1`).
- `design.configuration_kernel`: parameter `winding_sublattice` is deleted on entry.
- Fields nothing writes: `TraceData.sigma_eV`, `ConfigData.lambda_schedule`, `MeasurementData.role` values other than `live` (the planner never produces `noise`, `scan`, `validation`, or `excluded`).
- Written but never read: `Manifest.orbits`.
- `realized_state_gate.py`: `MOMENT_RELATIVE_TOLERANCE`.

## 10. Removal dependencies

What else must change if a piece is removed. Derived from the import map (2.2) and reference counts (section 9).

- `single_trace.py`, `ta_td_extract.py`, `noisefloor.py`, `dmi_pipeline/ta_td.py`: already broken; nothing in the package or tests imports them. Removing them leaves `cproj.load_all_cproj`/`get_ion_cproj` used only by `gates.gate_m1`, and `cso.as_spin_matrix`/`rotate_saxis` used only by the unreferenced `cli._build_cso_source` and tests. `USAGE.md` sections describing them would need updating.
- `dmi_pipeline/cproj.py`: live use is only `load_cocc_dat` in `cli gate m0` (`cli.py:13`, `:601`). `gates.py:39` imports `load_all_cproj` and `rebuild_cocc` for the unreferenced `gate_m1`. No test imports `cproj` directly, but `test_cli_pipeline.py::test_gate_m0_command_pins_convention_and_appends_to_manifest` exercises `gate m0`.
- `dmi_pipeline/cso.py`: `cli gate m0` and `cli gate t3` depend on `read_cso` and `find_euler_convention`. Tests: `test_cso_rotation.py` (11), plus `test_gate_t3_command_recovers_convention` and the `gate m0` test in `test_cli_pipeline.py`.
- `model.design_row`, `design_matrix`, `design_row_reference`, `e_dm_oracle`: only tests (`test_model.py`, `test_solve.py`, `test_two_trace.py`) and the unused planner import.
- Test-only and unreferenced gates in `gates.py`: only `test_gates.py`; no production dependency.
- `solve` output writers: only `test_solve.py::test_round_trip_and_covariance`.
- `dmi_pipeline/execution.py`: only `cli write-run-script` and `test_execution.py`.
- `realized_state_gate.py`: standalone; only `tests/test_realized_state_gate.py`.
- `constrsint probe/`: independent of `dmi_pipeline` and its tests. `F1_USES_LZEROZ` would still need another source.
- `vasp_sample/`, root `manifest.json`, `report.md`, `campaign.json`: no code or test references. Keep the root `POSCAR` and `tests/fixtures/bfo_magnetic.json`.
- Cache directories: safe to delete; regenerated.

## 11. How this was checked

- Read every source, test, fixture, spec, and config file in `pipeline v2/`, including `constrsint probe/`. For large data files, read headers only.
- Ran both test suites with `-p no:cacheprovider` and `PYTHONDONTWRITEBYTECODE=1`, so no cache or bytecode was written to the repo: 180 passed in 41.3 s; 56 passed in 1.4 s (conda env `research`, Python 3.11.15, numpy 2.4.6, scipy 1.17.1, pydantic 2.13.4, click 8.4.1, pytest 9.1.1).
- Imported each entry point to confirm the four `ImportError`s. Called `targets.magmom_string` and `targets.mconstr_string` with the shipped pins. Loaded a CSO file whose header says `SAXIS = 1 0 0` with `dumpio.load_cso`. Loaded the root `manifest.json` with `manifest.load`. Opened `vasp_sample/` files with `dumpio` and with `cso.read_cso`.
- Reference counts: an AST walk over `dmi_pipeline/`, the root scripts, and `tests/`, counting names, attributes, imports, and string literals (to catch monkeypatch targets). Click-decorated command functions were excluded. Name-based counting can be fooled by same-named local variables (it missed `gates.noise_floor`, corrected with grep) and cannot see `getattr` or `globals()` access; the package uses those only in `conventions.set_from_manifest` and the dict-or-attribute field getters.
- Line numbers come from `grep -n` on 2026-09-15 and will drift after edits.
