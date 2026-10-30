# Plan: Perlmutter Fe pilot workflow (campaign, reference, runner, report)

Governing handoff: [`docs/next_steps.md`](../docs/next_steps.md) (revised 2026-10-30).
Physics contract: [`docs/dmi_step1_implementation_spec.md`](../docs/dmi_step1_implementation_spec.md), decisions D-001..D-006 in [`docs/DECISIONS.md`](../docs/DECISIONS.md).
Branch: `feat/dmi-step1-vectors`. One writer at a time; tasks run strictly in order T0..T6.

This file fixes the interfaces between tasks. A task may refine a detail but must
record the change here (edit this file) and in its session log. Do not add
dependencies beyond NumPy and the standard library. No VASP or cluster contact.

## Ground rules for every task

- Start-of-session steps in root `AGENTS.md` (STATUS, DECISIONS, `git status`, recent session logs).
- Follow `.roo` code-directions: plain loops, inline bodies, early `continue`/`return`, uppercase constants block, fail fast, one path for side effects, match surrounding style (`pipeline v3/dmi_pipeline/step1.py`).
- Reuse before adding: `step1.prepare`, `step1.write_inputs`, `step1.read_state`, `step1.validate`, `step1.paired`, `manifest.save/load/file_hash/fingerprints/check_files`, `realized.incar/numbers/logical/poscar_species`, `workflow.INCAR_TAGS/_echo_check`.
- Never relax a threshold, never edit original VASP files, never label synthetic or submitted work as physical evidence.
- Each task: focused tests, run full suite, commit only its own files (staged diff inspected), one session log from `docs/sessions/TEMPLATE.md`, STATUS handoff line. Do not push.
- Test command (cwd `pipeline v3`): `C:/Users/finny/miniconda3/envs/research/python.exe -B -m pytest -q -p no:cacheprovider --tb=short`.

## Module and CLI layout (new files in `pipeline v3/dmi_pipeline/`)

| Module | Owner task | Purpose |
|---|---|---|
| `step1.py` (edit) | T1 | extract shared convergence/association check |
| `campaign.py` | T2 | schema, merge, expansion, plan validation, `plan.json` |
| `reference.py` | T3 | q0 reference prep, extraction, provenance, compatibility |
| `runner.py` | T4 | submit/status/resume, ledger, lock, fake-sbatch seam, readback release |
| `provenance.py` | T5 | code snapshot, input hash verification, in-job executable record, report, `return_files.txt` |

CLI additions in `__main__.py`, all under the existing argparse layout, names prefixed `campaign-`:
`campaign-prepare`, `campaign-plan`, `campaign-reference`, `campaign-submit`, `campaign-status`, `campaign-resume`, `campaign-report`.
Preparation commands never submit. Only `campaign-submit` and `campaign-resume` call sbatch.

## T1 contract: shared convergence check

Extract from `step1.read_state` into `step1.check_run(directory, nions) -> dict` the logic that:
single completed OUTCAR segment, final EDIFF after last iteration, ionic/electronic iteration indexing, `_echo_check` (run INCAR versus its OUTCAR echo), `sphere()` parse, final OUTCAR/OSZICAR (ionic, electronic) association. Return `{"sphere": <sphere() dict>, "outcar": {"final_step": [i, e], "build_banner": str, "ionic_steps": [...]}}`.
`read_state` calls it and keeps config-specific checks (q including the OUTCAR QSPIRAL echo, targets, tags, lambda, POSCAR hash and species/order). Behavior and error messages unchanged; all existing tests pass unmodified. No signature change to public functions used by tests.

## T2 contract: campaign file and plan.json

`campaign.json` (input; new schema, `"schema": "dmi-campaign-1"`):

```json
{
  "schema": "dmi-campaign-1",
  "run_root": "ABS/PATH/new-run-root",
  "material": "ABS/PATH/shared-inputs-dir",
  "job_template": "ABS/PATH/working-job.sh",
  "reference": {"mode": "import", "path": "ABS/PATH/reference-run-or-references.json"},
  "defaults": {"family": "F0", "axis": "z", "magnetic_indices": [0,1], "signs": [1,1],
               "seed_magnitudes": [2.2,2.2], "rwigs": [1.5], "lambda": 1.0, "lzeroz": true},
  "cases": [
    {"id": "fe-f0-q025-plus",  "side": "+", "q_frac": [0.25,0,0], "purpose": "pair member",  "pair": "fe-f0-q025"},
    {"id": "fe-f0-q025-minus", "side": "-", "q_frac": [0.25,0,0], "purpose": "pair member",  "pair": "fe-f0-q025"}
  ]
}
```

- `reference.mode` is `import` (a caller-supplied path to a completed q0 run or `references.json` + provenance, **not checked or extracted until T3**) or `generate` (T3 builds a q0 case, included in the plan as case `reference-q0`). The two-case example above imports a reference; generation reserves a third plan case with `status: "preparation deferred to T3"`, and T2 `campaign-prepare` fails explicitly without writing. `campaign-plan --campaign FILE` previews that three-case plan without writing. Plan top-level `reference` records mode/path/status for imports or mode/id/status for generation.
- Merge: case recipe fields override `defaults` key by key; no deep merge of lists. Cases additionally require `id`, `side`, `q_frac`, `purpose`, and may declare `pair`, `execution_parents` and additional `acceptance_requires` (case IDs). `id` is inserted into each resolved recipe. Unknown keys rejected. Executable and resources are NOT in the campaign (owned by `job_template`). Paths may be absolute or relative to the campaign file; the copied campaign preserves the original bytes.
- Negative member is given the same unwrapped positive `q_frac` with `side: "-"`; `step1.prepare` reflects it. Test must show q and targets equal single-recipe output and the sign applied exactly once.
- Expansion writes, under `run_root`: `campaign.json` (original copy), `cases/<id>/recipe.json` (fully resolved), `runs/<id>/` via `step1.write_inputs` (config.json, INCAR.step1, INCAR, POSCAR, KPOINTS, POTCAR, job.sh), `plan.json`. Finite-q cases pass through the same `step1.prepare` and `step1.write_inputs` as the single CLI; a generated q0 reference uses T3's explicit `reference.prepare_q0` and reuses `step1.write_inputs` without weakening the finite-q exclusion.
- Case and pair IDs: `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`, unique case IDs, no path separators, `..`, trailing dots or Windows reserved names. Reject case-insensitive output collisions, reserved `reference-q0`, input/output path overlaps and nonempty destinations. Inputs must exist and be nonempty before writing; `job_template` is always explicit. Shared POTCAR stays copied unchanged and is ignored by Git. The Python `CASE_ID` regex includes a single trailing dot, which is rejected separately as unsafe on Windows.

`plan.json` schema `"dmi-plan-1"`:

```json
{
  "schema": "dmi-plan-1",
  "run_count": 2,
  "cases": [{
    "id": "fe-f0-q025-plus", "purpose": "pair member", "pair": "fe-f0-q025", "side": "+",
    "initialization": "cold (ISTART=0, ICHARG=2)",
    "run_dir": "runs/fe-f0-q025-plus",
    "execution_parents": [],
    "acceptance_requires": ["import:reference-q0"],
    "reference": "import:reference-q0"
  }],
  "pairs": [{"id": "fe-f0-q025", "plus": "...", "minus": "..."}],
  "reference": {"mode": "import", "path": "ABS/PATH/reference", "status": "unverified; T3 extraction and compatibility pending"},
  "inputs": {"campaign_sha256": "...", "material": {"POSCAR": "sha", "INCAR": "sha", "KPOINTS": "sha", "POTCAR": "sha"}, "job_template_sha256": "..."}
}
```

- `execution_parents`: restart or ordering dependencies only. Cold-start pair members have none.
- `acceptance_requires`: reference and any accepted-state prerequisites. These do not create execution dependencies. Keep the two fields distinct everywhere.
- Initialization is checked via the shared INCAR parser: a case without a declared execution parent requires `ISTART=0`, `ICHARG=2`; a case with an existing in-plan parent records that parent separately even if the shared INCAR is cold. T2 does **not** stage or verify restart files; T4 must resolve restart ownership/consistency before any execution. Referenced parents must be finite-q cases in the same plan (the import q0 reference is an acceptance prerequisite, not a restart parent).
- Plan validation before any run-root write: duplicate/unsafe IDs, output collisions, invalid recipe via `step1.prepare`, missing parents/prerequisites, parent cycles, a pair with other than one `+` and one `-` member, pair members with differing family/axis/unwrapped positive q/material or other resolved recipe settings. T2 requires the first nonzero component of the input q to be positive to reject already-negated negative partners; this is a campaign input convention, not a change to single-recipe physics. `campaign-plan --root ROOT` reads a prepared plan; `--campaign FILE` validates and previews without writing. Both print run count, pairs and the two dependency kinds, never runtime estimates.
- Fe example lives at `evidence/` is NOT correct for runnable inputs; place the example at `examples/fe-f0-pilot/campaign.json` (paths are placeholders the user edits) and a synthetic test fixture under `pipeline v3/tests/`.

## T3 contract: reference preparation and extraction

- `generate`: q0 case via a small `reference.prepare_q0(recipe, poscar)` that reuses `step1.write_inputs` with mode-1, `LAMBDA = 0`, `QSPIRAL = 0 0 0`, same `RWIGS`, planar target `signs` along +x, schema-3 record. It must not weaken `step1.prepare`'s reciprocal-q rejection; the q0 path is a separate, explicit function with its own test.
- `extract(run_dir, config_or_poscar) -> references.json + reference-provenance.json`: use `step1.check_run` (T1). `references.json` keeps the existing format `{"M_int": [...], "MW_int": [...]}` (norms in magnetic-site order, printed precision). Provenance record: source paths and SHA-256 of INCAR/OUTCAR/OSZICAR/POSCAR/KPOINTS/POTCAR, selected final ionic/electronic step and OSZICAR line range, magnetic-site order, RWIGS, relevant tags (ENCUT, ENINI, NBANDS, ISMEAR, SIGMA, EDIFF, LASPH, ALGO, KPOINTS hash, PREC...), build banner, convergence flags, schema marker. Hosts: paths are host-bound; record the host that read it.
- `compatible(reference_provenance, case_config, case_inputs) -> list[str]` returning blocking differences. Allowed intentional differences: `QSPIRAL`, `LAMBDA`, `MAGMOM`, `M_CONSTR`, `LZEROZ` (document the list as a constant), restart/initial-charge tags only if the reference declares them. Everything else (POSCAR hash, POTCAR hash/species order, KPOINTS hash, ENCUT, ENINI, NBANDS, ISMEAR/SIGMA, EDIFF, PREC, LASPH, ALGO, RWIGS, magnetic-site order) must match or the case is not accepted. Never derive a reference from a finite-q case; reject a reference whose `QSPIRAL` is nonzero or whose run lacks convergence.
- Plan integration: reference appears as a plan case (`generate`) or as `import:<id>` metadata. Cases list it in `acceptance_requires`.

## T4 contract: runner

State under `run_root/` (all JSON via `manifest.save`, atomic):

```
submissions.json         # ledger: attempts, job ids, status, concurrency bound
submission.lock          # exclusive lock held during submit/resume
runs/<id>/attempt-NNN/   # one directory per attempt; inputs copied/linked from runs/<id>/ prepared inputs
runs/<id>/attempt-NNN/slurm-%j.{out,err}
runs/<id>/attempt-NNN/readback/state.json
runs/<id>/result.json    # per-case: execution status, readback status, gate, evidence hashes
jobsall.sh               # the single user-facing submission wrapper
```

- Case status vocabulary (separate, never merged): `prepared`, `submitted`, `running`, `execution_failed`, `readback_failed`, `rejected` (gate failed physically), `accepted`, `blocked` (prerequisite not accepted), `unresolved` (live job or interrupted submission not reconciled).
- `campaign-submit --root R [--max-concurrent N]`: take lock; verify plan and input hashes; validate template contract (below); write each attempt directory by copying the prepared case inputs (private WAVECAR/CHGCAR only if the INCAR enables restarts; never symlinked writable); submit with `sbatch --parsable --chdir=<attempt> --export=ALL --output/--error` from inside the attempt directory using argument lists (no shell `eval`), record the job ID (handle `;cluster` suffix) atomically.
- Scheduler seam: a single `scheduler` object with `submit(argv, cwd) -> job_id`, `states(job_ids) -> dict`. Production implementation shells out to `sbatch`/`squeue`/`sacct`; tests inject a fake. Concurrency: bounded lanes using `afterany` chaining as in the archived runner spec section 4.
- Readback release: a short post-job step runs `step1-read` equivalents through `step1.read_state`/`step1.validate` using the verified reference. Exit status of the job, gate result and reader errors are recorded as separate fields. A rejected or failed case never releases cases whose `acceptance_requires` contains it; those become `blocked`.
- Resume: under the lock, reconcile `submissions.json` with `squeue`/`sacct` and on-disk results. Reuse only completed evidence whose recorded code snapshot hash, input hashes, reference hash and parents match. Jobs found live are left alone. A submission that was interrupted (command issued, ID not recorded) is `unresolved`: look for a matching job by name/comment/attempt-dir; if still unknown, stop and report instead of resubmitting. Failed attempts are preserved; a retry uses a new `attempt-NNN`.
- Template contract check (static, on `job_template`): one foreground VASP launch, no hardcoded `cd`, no background `&` launch, no `|| true`/`set +e`-style error suppression, no shared-file cleanup, bash syntax passes (`bash -n`). Report each violation with its line; do not rewrite the script. Preserve `#SBATCH` resource directives; do not guess account, queue or GPU arguments.
- `jobsall.sh` is a thin wrapper that calls `python -m dmi_pipeline campaign-submit --root <R>`; nothing else.

## T5 contract: provenance, report, return bundle

- Code snapshot: at preparation, copy the package source tree (`dmi_pipeline/*.py`, `pyproject.toml`) into `run_root/code/` with a manifest of file hashes and `git rev-parse HEAD` plus a flag/diff hash if the tree is dirty. Submit/read/resume execute from and verify against this snapshot (`PYTHONPATH=run_root/code`). Editable install plus commit hash is not sufficient.
- Hash verification: input hashes (campaign, material, template, recipes, reference) are verified before submit and before readback; mismatch invalidates cached acceptance.
- In-job executable record: capture `executable.json` (resolved path via `readlink -f`, sha256, `module list`/env summary, host, job ID, start time) after the template's environment setup and before the actual launch. An outer attempt wrapper cannot see modules or executable paths established inside an unchanged job script: require a reviewed instrumentation point in the working template or an equivalent verified launch contract; if neither is available, record "unavailable" and do not claim launch identity or release acceptance. For module/container launchers, record the resolved executable or image identity if determinable. Executable identity is not source/build provenance.
- Report: `report.json` and `report.md` with separate sections: execution failures, readback failures, rejected states (with reasons, MW_int alignment/penalty/drift retained), accepted states, blocked/unresolved. A pair section shows both members and each member's result; do not label a pair SOC/parity validated. Reporting runs even if cases failed. Synthetic fixtures are labelled synthetic.
- `return_files.txt`: small inputs, resolved recipes/configs, reference records, state records, job scripts, job IDs, logs, hashes, OUTCAR/OSZICAR; exclude WAVECAR/CHGCAR/large dumps.

## T6 contract: documentation and handoff

- Rewrite `docs/PERLMUTTER_F0_PILOT.md` with copyable commands for env setup, campaign prepare, plan review, submit, status/resume, reference extraction, readback, report and return files. Mark each command as implemented only if it is. Cluster-only choices listed separately (paths/template, resources, ENCUT/ENINI, compatible reference, executable/build evidence, compute-node smoke test).
- Update `docs/STEP1_LOCAL_USAGE.md` pointer, `STATUS.md` (DMI-02 row, next action), `CHANGELOG.md`, session log, and `docs/DECISIONS.md` (D-007: runner design: no new scheduler service, ledger+lock+fake seam, reference vs restart dependency split) if warranted.
- Final handoff reports baseline inspected, reused functions, interfaces, changed files, exact test commands/results, minimal Fe campaign example, cluster-only decisions vs unimplemented software, commit/uncommitted status. No claim of readiness for the broader DMI campaign.

## Required tests (map to `docs/next_steps.md` section 5)

1. Campaign expansion equals single-case generator, +q/-q targets, overrides, IDs; invalid plans rejected (T2).
2. Reference extraction picks the converged final table and site order; incompatible or incomplete references cannot pass (T3).
3. Launcher failure, readback failure and physical rejection are distinguishable; blocked descendants not released (T4).
4. Execution vs reference dependencies allow only intended concurrency; no shared writable restart files (T2, T4).
5. Resume skips verified work and live jobs, preserves failed attempts, handles interruption without duplicate submission (T4).
6. Changed code, inputs, references or parents invalidate cached acceptance (T4, T5).
7. Reports include failed and blocked cases and never upgrade synthetic or submitted work to physical evidence (T5).
8. `bash -n` on generated shell scripts; full existing regression suite green at every task.
