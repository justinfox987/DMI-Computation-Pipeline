# Changelog

Record meaningful delivered changes, newest first. Include a session log or
commit reference when available. Do not use this as a command transcript.

## Unreleased

- TEN-04: added `dmi dumps` (Section 5 decks: `dump_P` under each ok run, `dump_C`/`dump_C_x`/`dump_C_y` from `q0`'s `CHGCAR` with `ISTART = 0`, `ICHARG = 11` and no `LSPIRAL` in any SOC deck; `parent.json` records parent hashes and linked-file size/mtime) and `dmi trace` (`gates.finish` writes each dump's `provenance.json` with C0, M1 or T3; `trace.split_operator`/`trace_vector` give the Eq (4.4)/(4.8) trace vector from COCC; N0 on all axes and ions, I0, P0 and E0 at 10%; `traces.json`). `collect` now applies the Section 11 SCF-and-state checks (`|delta_a| < 1°` when `n_twist = 0`, `M_a` within 5% of `q0`, `|M_z| < 0.05 μB`). T3 rewritten to the Section 11 form; deleted the Euler search, `rotate_saxis`, `cso.py`, `trace_config`, the `DONE`/`FAILED` markers and the `Bi` check in `gate_n0` (D-009 amended). Tests 15 -> 18. No VASP or cluster jobs. See the [TEN-04 handoff](docs/sessions/2026-11-08_2245Z-agent-ten04-trace.md).

- TEN-03: added `dmi_pipeline/spiral.py` with the seed loader, the q plan (both Section 8.2 rank conditions at `RANK_FLOOR = 0.1`, default low-index directions), F0 inputs at every ±q and q = 0 from unwrapped POSCAR positions, a Slurm-array `submit.sh` spliced from the user's `job.sh`, and `collect` readback of E and `M_int` with the Eq (3.3) phases. Commands `plan`, `prepare` and `collect` replace the five `step1-*` commands. Deleted `step1.py` (bond rows, F1/F2, λ>0 penalty checks) and `test_step1.py`; `sphere` and `check_run` moved unchanged. The readback rejects a reversed site by pair phase instead of the approved `|delta_a| < 90°`, which cannot see a reversal in a 2-site cell. Dropped `dmi status` (D-013 amended). Tests 16 -> 15. No VASP or cluster jobs. See the [TEN-03 handoff](docs/sessions/2026-11-08_2010Z-agent-ten03-spiral.md).

- TEN-02 follow-up: `test_section_7_4_table` now requires the inversion group's stiffness basis to span all 6 symmetric matrices, and `test_exchange_classes` adds FeGe (5 classes of 12, each closed under the kept R and r -> -r). Both catch an injected fault (dropped symmetrizer; dropped `-orbit`). Corrected three background notes in `plans/ten-02-symmetry.md`. No code change; 16 tests. See the [follow-up log](docs/sessions/2026-11-08_1829Z-agent-ten02-followup.md).

- TEN-02: added `dmi_pipeline/symmetry.py` (kept operations with the space-group, orthogonality and site-map guards; spiralization and stiffness bases; twist count; exchange classes) and the `spglib>=2.6` dependency. Replaced `step1.positions` and `realized.poscar_species` with one reader, `realized.poscar(path) -> (lattice, species, tau)`, which applies the scale factor and rejects Cartesian positions and negative or three-value scales. Added three tests (13 -> 16). Reproduced the spec's expected-results table; 9 of 9 injected faults caught. No VASP or cluster jobs. See the [TEN-02 handoff](docs/sessions/2026-11-08_1735Z-agent-ten02-symmetry.md).

- Prepared the repository for coding in Claude Code: added `CLAUDE.md` importing `AGENTS.md`, the TEN-02 spec (`plans/ten-02-symmetry.md`), the seed file format (`docs/seed_file.md`, D-016) and the symmetry detection rules (D-017). Added `materials/fe/seed.toml`, removed the obsolete `examples/fe-f0-pilot/` campaign example, moved the old runner plan to `docs/archive/`, marked TEN-01 done and set one branch per task. No code change. See the [handoff log](docs/sessions/2026-11-08_1710Z-agent-claude-code-handoff.md).

- TEN-01: removed `runner`, `campaign`, `reference` and `workflow` with their tests, about 3,300 lines. Moved `INCAR_TAGS` and `echo_check` to `realized`, gave T3 a small wrapper in `cso`, and ignored `vasp files/` and `pipeline v4/`. There is no N0 command until TEN-04. Cut the test suite from 210 cases to 13 (D-015). No VASP or cluster jobs. See the [TEN-01 handoff](docs/sessions/2026-11-04_1845Z-agent-ten01-remove-orchestration.md).

- Pivoted the project from bond-resolved DMI vectors to the spiralization tensor, stiffness tensor and exchange classes. Added math Revision 3.0 with a Markdown agent edition, recorded D-007 to D-014, updated AGENTS, STATUS and README, and moved bond-era documents to `docs/archive/`. No code or VASP change; the pre-pivot state is at tag `archive/bond-dmi-v3`.

- Fe pilot T4b-2: expose completed jobs waiting on reference verification in the status table and additive JSON fields/counts; consolidate scheduler-state reconciliation in one table. Synthetic local tests only; no VASP or cluster jobs. No handoff log was committed for T4b-2.

- Added the Fe pilot T4 runner baseline and hardened the submit path: prepared, hashed Slurm `jobsall.sh`, locked and explicitly confirmed fake-tested submission, private restart staging and exact scheduler options. Local 153 -> 160 tests and generated-script Bash syntax pass; reconcile/readback/resume are still being hardened in T4b. No VASP or cluster jobs. See the [T4a handoff](docs/sessions/2026-10-30_2124Z-agent-pilot-runner-t4a-submit-path.md).

- Added independent q0 sphere-reference preparation/extraction with hashed provenance and strict per-case compatibility; campaign import/generate and `campaign-reference` now verify before acceptance. 106 -> 136 local tests pass; no VASP or cluster run. See the [T3 handoff](docs/sessions/2026-10-30_1559Z-agent-pilot-runner-t3-reference.md).

### Fe F0 pilot campaign preparation (2026-10-30)

- Added `campaign-prepare` and `campaign-plan` with pre-write plan validation, two-kind dependencies, explicit imported-reference provenance pending T3, SHA-256 input inventory, and per-case expansion through the unchanged Step 1 generator/writer. Added a two-run Fe example and 44 synthetic tests; 106 total local tests pass. Generated q0 preparation, submission and reference checks remain for T3/T4. See the [T2 handoff](docs/sessions/2026-10-30_1538Z-agent-pilot-runner-t2-campaign.md).

### Shared Step 1 run convergence check (2026-10-30)

- Extracted `step1.check_run(directory, nions)` for independent OUTCAR convergence, run INCAR echo and terminal OSZICAR sphere/step association; `read_state` retains config-specific comparisons and unchanged provenance/readback. Seven synthetic boundary cases added; 62 local tests pass. No physical validation or cluster execution. See the [T1 handoff](docs/sessions/2026-10-30_1526Z-agent-pilot-runner-t1-check-run.md).

### Explicit Perlmutter pilot interfaces (2026-10-21)

- Removed current-directory job.sh discovery: include a launch script only through `--job-template`. Material/recipe/run/readback paths stay caller supplied, with executable configuration in the existing working launch script. Added ENINI to the shared input whitelist so cutoff settings can be supplied and echoed without selecting new values. Added the [Perlmutter sequence](docs/archive/PERLMUTTER_F0_PILOT.md), portable installation instructions and regression coverage through synthetic shared-input preparation/readback. Local pilot directories are generator tests; no local cluster assets are required. No calculation submitted. See the [handoff](docs/sessions/2026-10-21_1815Z-agent-perlmutter-pilot-portability.md).

### Single-directory Step 1 pilot preparation (2026-10-19)

- Extended existing `step1-prepare`/`write_inputs` with shared material assembly: generated tags override the base INCAR once, while POSCAR/KPOINTS/POTCAR and a supplied launch template are copied unchanged. The default launch template is current-directory job.sh; its absence is explicitly reported as review-only. Existing fragment-only preparation remains available. A local ferromagnetic Fe F0 candidate is prepared with consistent targets/config/INCAR, with launch availability and inherited cutoff/resource choices recorded for review. See the [preparation handoff](docs/sessions/2026-10-19_1627Z-agent-fe-f0-preparation.md). No scheduler, VASP execution or physical acceptance change.

### Step 1 logical INCAR equivalence (2026-10-19)

- Reused the shared strict logical parser for the four Step 1 run/config boolean tags. A prepared T/F config now reads the original Fe True/False INCAR without a config edit; invalid or opposite boolean values still fail. The full real-file CLI readback reproduces the same failed physical gate and field/penalty diagnostics with unchanged thresholds. See the [follow-up session](docs/sessions/2026-10-19_1556Z-agent-step1-logical-readback.md). No VASP rerun.

### Historical Fe q0 reference and full Step 1 readback (2026-10-05)

- Recorded a converged q0 Fe sphere reference, a diagnostic F1 reconstruction of the historical +x/+x lambda=1 inputs, and the full CLI readback. The physical gate fails absolute weighted alignment, M_int norm drift and penalty limits; signed factor evidence passes, while the field/penalty same-update identity remains unavailable with a recorded interval gap. The generated config's T/F tokens fail literal comparison with historical True/False inputs, so the evidence includes a clearly labelled spelling-only historical config. No validator/tolerance or VASP change. See the [readback session](docs/sessions/2026-10-05_2030Z-agent-step1-q0-readback.md) and [evidence record](evidence/2026-10-05-fe-q0-step1-readback/README.md).

### Step 1 field and penalty diagnostics (2026-09-30)

- Split signed factor-two evidence from the field/penalty identity in the existing Step 1 validator. The identity now records printed intervals and any gap at the requested coefficient matched to run inputs, with same-update interpretation unavailable until separately established. The lambda=1 Fe discrepancy remains visible; alignment and penalty acceptance limits are unchanged. Added a focused CGA-format regression and updated the spec/usage; 18 focused and 53 total local tests pass. See the [validator handoff](docs/sessions/2026-09-30_2011Z-agent-step1-field-penalty-validator.md). No VASP rerun or production acceptance.

### Step 1 field and penalty source audit (2026-09-30)

- Traced the original lambda=1 Fe sample against supplied VASP mode-1 source: the final printed penalty is cached before a later moment refresh, while signed fields use current moments; the source coefficient remains the requested 1.0. The field/penalty printed intervals are disjoint at exact lambda 1, while factor-two and sign remain supported at printed-moment precision. No code or tolerance change, VASP rerun, or production gate; see the [source audit](docs/sessions/2026-09-30_1933Z-agent-step1-field-penalty-source-audit.md).

### Step 1 original-file reader repair handoff (2026-09-30)

- Committed the reviewed reader repair for repeated OSZICAR sphere tables, SDA/CGA iterations, actual OUTCAR run banners and `Iteration I(E)` association, with distinct missing-summary and missing-OUTCAR-footer checks. The original Fe sample parses at ionic/electronic step 1/50 (95 sphere tables, one ionic summary); 17 focused and 52 total local software tests pass. No push.
- The sample's requested both-Fe +x directions do not establish physical F0 realization, and zero lambda/field cannot verify a nonzero-lambda convention. No versioned config/reference-bound read, production gate or VASP job; see [real-sample handoff](docs/sessions/2026-09-30_1610Z-agent-step1-reader-real-sample.md).

### Step 1 final review follow-up (2026-09-30)

- Rejected malformed or broadcastable QSPIRAL values at stored/requested/run/echo boundaries and mismatched per-species RWIGS between otherwise valid partners.
- Kept zero-field states valid without claiming factor-two evidence below printed resolution; retained separate zero-field consistency and positive-signal Fe excerpt checks. See [final review log](docs/sessions/2026-09-30_0024Z-agent-step1-final-review.md). No production VASP validation.

### Step 1 corrective review (2026-09-30)

- Bound readback and row gates to checked config/run file hashes and re-read sphere
  moments, checked stored q/target identity, and added safe CLI wrapped-partner
  representation without changing physical targets.
- Allowed one common-z pair-validation rotation while retaining raw model spins;
  checked printed penalty and signed field against MW_int within decimal rounding;
  required indexed terminal OSZICAR and final OUTCAR loop agreement or failed closed.
  Synthetic tests are not VASP validation. See [corrective session log](docs/sessions/2026-09-30_0005Z-agent-step1-review-fixes.md).

### Step 1 offline vector software path (2026-09-29)

- Added versioned lab-frame target recipes and INCAR fragments, strict OSZICAR
  sphere-moment readback with separate electronic convergence, signed realization
  checks, one canonical cell-translation bond kernel and two-sided diagnostic rows.
- Added offline CLI input/readback/row/weighted-solve entry points and synthetic
  regression coverage while preserving the historical N0 manifest and trace.
  Missing BFO symmetry basis, production trace/parity and noise evidence are
  explicit blockers, not new validation passes. See [local usage](docs/archive/STEP1_LOCAL_USAGE.md)
  and the [implementation handoff](docs/sessions/2026-09-29_2328Z-agent-dmi-step1-vectors.md).

### Local baseline handoff (2026-09-29)

- Audited the tracked N0-only baseline, recorded its local test result and
  outstanding Step 1 work in [the handoff](docs/sessions/2026-09-29_2024Z-agent-baseline-finalization.md).
- Excluded the two local full VASP distribution copies while leaving the small
  Patch B spec and other untracked patch/source candidates visible for review.
  No VASP assets, production results or Step 1 changes were committed.

### Documentation and coordination

- Prepared repository instructions, status/ownership tracking, a decision log,
  session-log template, evidence guidance and a Windows-friendly setup guide.
- Bundled the current Revision 2.4 LaTeX source and Step 1 implementation spec.
- Preserved the nine supplied older documents under docs/archive with a clear
  notice about superseded frame assumptions.
- Added starter ignore and line-ending rules for local Python/HPC work.

The documentation-and-coordination entries above describe the starter kit, not
Step 1 implementation or a new production validation result.

## Earlier document milestones

- **2026-09-29:** Step 1 implementation specification written.
- **2026-09-26:** Math Revision 2.4 replaced redundant angular bookkeeping with
  vector-based targets, readback, checks and fitting.

Software releases and production validation milestones remain to be recorded
from actual repository commits and evidence.
