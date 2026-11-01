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

- `reference.mode` is `import` (a completed q0 run with `config.json` or explicit `reference.config` supplying `magnetic_indices`, or `references.json` with adjacent provenance) or `generate` (a real prepared q0 run included as `reference-q0`). `campaign-plan --campaign FILE` previews without writing; import preview status is `unverified-import`, and preparation verifies/extracts/compares before writing and records `verified-import`. Generation previews and prepares three runs, with `reference.status: "pending-generate"` until `campaign-reference` verifies the completed q0 run. Import provenance is copied under `run_root/reference/`; a bare references.json is rejected.
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
  "reference": {"mode": "import", "path": "ABS/PATH/reference", "status": "verified-import", "records": "reference/references.json and reference/reference-provenance.json"},
  "inputs": {"campaign_sha256": "...", "material": {"POSCAR": "sha", "INCAR": "sha", "KPOINTS": "sha", "POTCAR": "sha"}, "job_template_sha256": "...", "source_paths": {"campaign": "ABS/PATH/campaign.json", "material": "ABS/PATH/shared-inputs", "job_template": "ABS/PATH/working-job.sh"}, "prepared": {"fe-f0-q025-plus": {"config.json": "sha", "POSCAR": "sha", "INCAR": "sha", "KPOINTS": "sha", "POTCAR": "sha", "job.sh": "sha"}}, "jobsall_sha256": "..."}
}
```

- `inputs` is completed by `campaign-prepare` (preview from `campaign-plan --campaign` has only `campaign_sha256`, `material`, `job_template_sha256`, `source_paths`). `source_paths` contains absolute original input paths; `prepared` hashes the six prepared run files for each case; `jobsall_sha256` hashes the generated root-level submission script. Submit checks all of them, including the original sources; a missing or modified jobsall script fails before scheduling. Regenerate into a fresh run root rather than editing the pinned script.
- `execution_parents`: restart or ordering dependencies only. Cold-start pair members have none.
- `acceptance_requires`: reference and any accepted-state prerequisites. These do not create execution dependencies. Keep the two fields distinct everywhere.
- Initialization is checked via the shared INCAR parser: a case without a declared execution parent requires `ISTART=0`, `ICHARG=2`; a case with an existing in-plan parent records that parent separately even if the shared INCAR is cold. T2 does **not** stage or verify restart files; T4 must resolve restart ownership/consistency before any execution. Referenced parents must be finite-q cases in the same plan (the import q0 reference is an acceptance prerequisite, not a restart parent).
- Plan validation before any run-root write: duplicate/unsafe IDs, output collisions, invalid recipe via `step1.prepare`, missing parents/prerequisites, parent cycles, a pair with other than one `+` and one `-` member, pair members with differing family/axis/unwrapped positive q/material or other resolved recipe settings. T2 requires the first nonzero component of the input q to be positive to reject already-negated negative partners; this is a campaign input convention, not a change to single-recipe physics. `campaign-plan --root ROOT` reads a prepared plan; `--campaign FILE` validates and previews without writing. Both print run count, pairs and the two dependency kinds, never runtime estimates.
- Fe example lives at `evidence/` is NOT correct for runnable inputs; place the example at `examples/fe-f0-pilot/campaign.json` (paths are placeholders the user edits) and a synthetic test fixture under `pipeline v3/tests/`.

## T3 contract: reference preparation and extraction

- `generate`: `reference.prepare_q0(recipe, poscar)` shares Step 1's target/tag builder and `step1.write_inputs` without relaxing production q exclusion. It writes mode 1, explicit zero lambda/q, positive seeds, zero nonmagnetic entries, same RWIGS and planar signed +x F0. `LSPIRAL=T` and explicit `LZEROZ=T` retain the historical spiral q0/readback convention and current F0 planar requirement. A generated case is `status: "reference-producing"`, cold start, zero execution parents; pair acceptance requires `reference-q0` but execution does not.
- `reference.extract(run_dir, config, output=None) -> (references, provenance)` uses `step1.check_run`; config is a path or mapping with explicit two magnetic indices. Its optional output directory receives `references.json` in existing reader format and companion `reference-provenance.json` (schema `dmi-reference-provenance-1`), with the six run-file hashes/paths, references hash, magnetic-site order, species/RWIGS, all run INCAR tags and selected relevant tags (including ENCUT, ENINI, NBANDS, ISMEAR, SIGMA, EDIFF, PREC, LASPH, ALGO, LMAXMIX, GGA, ISPIN, NELECT), q/lambda/mode, final step and OSZICAR line range, build banner, convergence flags, UTC extraction time and host. `reference.verify_files(references_path)` rehashes and re-extracts source files; a bare JSON or finite-q run cannot qualify.
- `reference.compatible(provenance, case_config, case_run_dir_or_inputs) -> list[str]` lists blocking differences; `ALLOWED_TAGS` documents q/lambda/targets, LZEROZ, initial/restart, projection, parallel and dump differences; `BLOCKING_TAGS` is the remaining reviewed INCAR whitelist (plus mandatory mode 1 and RWIGS). Missing tags block instead of silently assuming VASP defaults. Both modes must be 1. POSCAR, KPOINTS, POTCAR hashes, species and magnetic-site order must agree. A prepared case's INCAR is compared to its config even for otherwise allowed tags.
- `campaign-reference --root ROOT [--run RUN_DIR --config CONFIG] [--output ROOT/reference]` verifies generated q0 (default `runs/reference-q0`) or an explicitly provided imported q0 run. It checks compatibility against every prepared case, prints PASS/BLOCK, returns 0/1; it does not overwrite prior evidence. Preparation import runs may specify `reference.config` for historical runs without a local config. `reference.status` is `unverified-import` (preview), `verified-import`, `pending-generate`, or `verified-generate`; plan's `records` points to the two files when verified. Generated extraction/compatibility happen after the run finishes. T4 must respect the status and verify evidence before releasing acceptance.

## T4 contract: runner

State under `run_root/` (all JSON via `manifest.save`, atomic):

```
submissions.json         # ledger: attempts, job ids, status, concurrency bound
submission.lock          # exclusive lock held during submit/resume
runs/<id>/attempt-NNN/   # one directory per attempt; inputs copied/linked from runs/<id>/ prepared inputs
runs/<id>/attempt-NNN/slurm-%j.{out,err}
runs/<id>/attempt-NNN/readback/state.json
runs/<id>/result.json    # per-case: execution status, readback status, gate, evidence hashes
jobsall.sh               # the short Slurm submission job, generated by campaign-prepare
```

- Case status vocabulary (separate, never merged): `prepared`, `submitted`, `running`, `execution_failed`, `readback_failed`, `rejected` (gate failed physically), `accepted`, `blocked` (prerequisite not accepted), `unresolved` (live job or interrupted submission not reconciled).
- `campaign-submit --root R [--max-concurrent N] [--yes] [--clear-stale-lock]`: without `--yes` print dry-run commands and perform no submission/staging; with `--yes` take lock, verify plan and source/prepared/jobsall hashes, validate template contract (below), copy each case's prepared inputs into a private attempt directory (private WAVECAR/CHGCAR only for declared verified restarts; never writable links), and submit via `sbatch --parsable --chdir=<attempt> --export=ALL --output/--error --job-name --comment --kill-on-invalid-dep=yes` from that attempt directory using argument lists (no shell `eval`). Record the job ID (`;cluster` suffix handled) atomically. The default concurrency bound is 2 and is pinned in the ledger. A second `--yes` submit skips recorded live/submitted/accepted attempts; without `--retry`, a failed attempt is not automatically resubmitted. `--clear-stale-lock` is an explicit operator assertion after verifying no other writer is active.
- Scheduler seam: a single `scheduler` object with `submit(argv, cwd) -> job_id`, `states(job_ids) -> dict`. Production implementation shells out to `sbatch`/`squeue`/`sacct`; tests inject a fake. Concurrency: bounded lanes using `afterany` chaining as in the archived runner spec section 4.
- Readback release: a short post-job step runs `step1-read` equivalents through `step1.read_state`/`step1.validate` using the verified reference. Exit status of the job, gate result and reader errors are recorded as separate fields. A rejected or failed case never releases cases whose `acceptance_requires` contains it; those become `blocked`.
- Resume: under the lock, reconcile `submissions.json` with `squeue`/`sacct` and on-disk results. Reuse only completed evidence whose recorded code snapshot hash, input hashes, reference hash and parents match. Jobs found live are left alone. A submission that was interrupted (command issued, ID not recorded) is `unresolved`: look for a matching job by name/comment/attempt-dir; if still unknown, stop and report instead of resubmitting. Failed attempts are preserved; a retry uses a new `attempt-NNN`.
- Template contract check (static, on `job_template`): one foreground VASP launch, no hardcoded `cd`, no background `&` launch, no `|| true`/`set +e`-style error suppression, no shared-file cleanup, bash syntax passes (`bash -n`). Report each violation with its line; do not rewrite the script. Preserve `#SBATCH` resource directives; do not guess account, queue or GPU arguments.
- `campaign-resume --root R [--retry] [--yes] [--clear-stale-lock]` and `campaign-status --root R [--json] [--clear-stale-lock]` use the same ledger/lock; reconciliation/readback/resume hardening is deferred to T4b.
- `campaign-prepare` writes `run_root/jobsall.sh` as a *real Slurm batch job*: `#!/bin/bash`, leading `#SBATCH` directives copied in their template order for account, partition/queue, QOS, constraint and resources, excluding all `--job-name`/`-J`, `--output`/`-o`, `--error`/`-e`, `--time`/`-t`, `--dependency`/`-d`, `--chdir`/`-D`, `--array`/`-a` and `--open-mode` forms. Its own directives set `<run-root-name>-jobsall`, absolute `jobsall-%j.out`/`.err` paths, and `JOBSALL_WALLTIME = "00:10:00"` (Python submission only, never VASP). A template without leading directives still produces the script, with a prepare-time warning and no invented account/queue. Body is only `set -euo pipefail`, `cd "<absolute root>"`, a `TODO(T5)` code-snapshot/PYTHONPATH comment and explicit-confirmation comment, then exactly one `"${PYTHON:-<sys.executable at prepare time>}" -B -m dmi_pipeline campaign-submit --root "<absolute root>" --yes`. The operator's `sbatch jobsall.sh` is explicit confirmation; the controller submits the calculation jobs then exits. A submit error propagates as the jobsall job's failure. T5 must bind a frozen code snapshot; this script does not yet do so.

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
