"""Synthetic scheduler, electronic files and material only; no Slurm/VASP job runs."""

import json
import os
import subprocess
import sys

import numpy as np
import pytest

from dmi_pipeline import campaign, manifest, runner
from dmi_pipeline.__main__ import main
from tests.test_campaign import synthetic_campaign
from tests.test_step1 import run_cli

TEMPLATE = '#!/bin/bash\n#SBATCH -N 1\nset -e\nsrun "$VASP_EXECUTABLE"\n'


class FakeScheduler:
    def __init__(self):
        self.calls = []
        self.jobs = {}
        self.matches = {}

    def submit(self, argv, cwd):
        self.calls.append((argv, cwd))
        job = str(10000 + len(self.calls))
        self.jobs[job] = {"state": "PENDING", "exit_code": None}
        return job + ";cluster"

    def states(self, job_ids):
        return {job: self.jobs[job] for job in job_ids if job in self.jobs}

    def find(self, name, comment):
        return self.matches.get((name, comment), [])


def prepared(tmp_path, generated=False):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    job.write_text(TEMPLATE)
    if generated:
        data["reference"] = {"mode": "generate"}
        manifest.save(data, source)
    campaign.prepare(source)
    return root, data


def synthetic_finish(root, scheduler, case, valid=True, gate=True, failed=False):
    """Supply indexed synthetic readback files, never invoke the copied template."""
    record = manifest.load(root / "submissions.json")["cases"][case]["attempts"][-1]
    attempt = root / "runs" / case / record["directory"]
    scheduler.jobs[record["job_id"]] = {"state": "FAILED" if failed else "COMPLETED",
                                         "exit_code": "1:0" if failed else "0:0"}
    config = manifest.load(attempt / "config.json")
    (attempt / "OUTCAR").write_text("vasp.test synthetic\n" + (attempt / "INCAR").read_text() +
             "Iteration 1( 1)\naborting loop because EDIFF is reached\nGeneral timing and accounting\n")
    moments = np.asarray(config["targets"])
    if not gate:
        moments[0] = -moments[0]
    rows = [f" {i + 1} " + " ".join(f"{v:.9f}" for v in [*(1.8 * m), *(2 * m)])
            for i, m in enumerate(moments)]
    (attempt / "OSZICAR").write_text(" DAV: 1 -1\n ion MW_int M_int\n" + "\n".join(rows) +
            f"\n 1 F= -1 E0= -1\n E_p = 0.0E+00 lambda = {float(config['tags']['LAMBDA']):.8E}\n"
            if valid else "bad synthetic OSZICAR\n")
    return attempt


def test_dry_run_submission_and_exact_argv_cwd(tmp_path, capsys):
    root, data = prepared(tmp_path)
    fake = FakeScheduler()
    runner.submit(root, fake, max_concurrent=2)
    assert fake.calls == [] and not (root / "submissions.json").exists()
    assert "DRY RUN plus" in capsys.readouterr().out
    runner.submit(root, fake, max_concurrent=2, yes=True)
    ledger = manifest.load(root / "submissions.json")
    assert len(fake.calls) == 2
    for argv, cwd in fake.calls:
        case_id = cwd.parent.name
        assert argv == ["sbatch", "--parsable", f"--chdir={cwd}", "--export=ALL",
                        f"--output={cwd / 'slurm-%j.out'}", f"--error={cwd / 'slurm-%j.err'}",
                        f"--job-name={root.name}-{case_id}-attempt001", f"--comment={cwd}",
                        "--kill-on-invalid-dep=yes", str(cwd / "job.sh")]
        assert ledger["cases"][case_id]["attempts"][0]["job_id"].isdigit()
        assert not any((cwd / name).exists() for name in ("WAVECAR", "CHGCAR", "CHG"))
    assert runner.parse_job_id("12345;cluster\n") == "12345"
    assert set(ledger) == {"schema", "max_concurrent", "code_identity", "plan_inputs", "cases", "lanes"}
    assert "SUBMIT" in capsys.readouterr().out


def test_generated_reference_runs_independently_and_blocks_acceptance(tmp_path):
    root, data = prepared(tmp_path, generated=True)
    fake = FakeScheduler()
    runner.submit(root, fake, max_concurrent=3, yes=True)
    assert [cwd.parent.name for _, cwd in fake.calls] == ["reference-q0", "plus", "minus"]
    assert len(fake.calls) == 3
    assert all(not any(arg.startswith("--dependency=") for arg in argv) for argv, _ in fake.calls)
    synthetic_finish(root, fake, "plus")
    synthetic_finish(root, fake, "minus")
    report = runner.status(root, fake)
    assert {row["status"] for row in report["cases"] if row["case_id"] != "reference-q0"} == {"submitted"}
    assert all(manifest.load(root / "runs" / case / "result.json")["pending_reference"] for case in ("plus", "minus"))
    synthetic_finish(root, fake, "reference-q0")
    report = runner.status(root, fake)
    assert {row["status"] for row in report["cases"]} == {"accepted"}
    assert manifest.load(root / "reference" / "references.json") == {"M_int": [2.0, 2.0], "MW_int": [1.8, 1.8]}


@pytest.mark.parametrize("kind, expected", [("failed", "execution_failed"), ("corrupt", "readback_failed"),
                                           ("reject", "rejected"), ("pass", "accepted")])
def test_synthetic_outcomes_keep_separate_evidence(tmp_path, kind, expected):
    root, data = prepared(tmp_path)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    synthetic_finish(root, fake, "plus", valid=kind != "corrupt", gate=kind != "reject", failed=kind == "failed")
    report = runner.status(root, fake)
    result = manifest.load(root / "runs" / "plus" / "result.json")
    assert result["status"] == expected
    assert result["execution"]["state"] == ("FAILED" if kind == "failed" else "COMPLETED")
    assert result["gate"] is None if kind in ("failed", "corrupt") else result["gate"] is not None
    assert report["cases"][0]["status"] == expected
    if expected == "accepted":
        assert manifest.load(root / "runs" / "plus" / "attempt-001" / "readback" / "state.json")["gate"]["passed"]


def test_resume_cached_and_live_and_changed_hash(tmp_path):
    root, _ = prepared(tmp_path)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    synthetic_finish(root, fake, "plus")
    runner.status(root, fake)
    assert len(fake.calls) == 2
    runner.resume(root, fake, yes=True)
    assert len(fake.calls) == 2
    result = manifest.load(root / "runs" / "plus" / "result.json")
    plan = manifest.load(root / "plan.json")
    ledger = manifest.load(root / "submissions.json")
    assert runner.cache_valid(root, plan["cases"][0], result, ledger, plan)
    (root / "runs" / "plus" / "attempt-001" / "INCAR").write_text("changed\n")
    assert not runner.cache_valid(root, plan["cases"][0], result, ledger, plan)


def test_failure_retry_preserves_old_attempt(tmp_path):
    root, _ = prepared(tmp_path)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    old = synthetic_finish(root, fake, "plus", failed=True)
    runner.status(root, fake)
    original = {p.name: p.read_bytes() for p in old.iterdir() if p.is_file()}
    runner.resume(root, fake, yes=True)
    assert len(fake.calls) == 2
    runner.resume(root, fake, retry=True, yes=True)
    assert len(fake.calls) == 3
    assert {p.name: p.read_bytes() for p in old.iterdir() if p.is_file()} == original
    assert (old.parent / "attempt-002" / "job.sh").is_file()


def test_interrupted_submission_never_resubmits_and_lock(tmp_path):
    root, _ = prepared(tmp_path)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    ledger = manifest.load(root / "submissions.json")
    item = ledger["cases"]["plus"]["attempts"][0]
    job = item.pop("job_id")
    item["status"] = "submitting"
    manifest.save(ledger, root / "submissions.json")
    runner.resume(root, fake, yes=True)
    assert manifest.load(root / "submissions.json")["cases"]["plus"]["status"] == "unresolved"
    assert len(fake.calls) == 2
    fake.matches[(item["job_name"], str(root / "runs" / "plus" / item["directory"]))] = [job]
    runner.status(root, fake)
    assert manifest.load(root / "submissions.json")["cases"]["plus"]["attempts"][0]["job_id"] == job
    (root / "submission.lock").write_text('{"pid": 0, "host": "synthetic"}')
    with pytest.raises(ValueError, match="lock held"):
        runner.status(root, fake)
    runner.status(root, fake, clear_stale_lock=True)


@pytest.mark.parametrize("script, reason", [
    ('cd /other\n', "hardcoded absolute cd"),
    ('srun "$VASP_EXECUTABLE" &\n', "background launch"),
    ('srun "$VASP_EXECUTABLE" || true\n', "failure suppression"),
    ('srun "$VASP_EXECUTABLE"\nsrun "$VASP_EXECUTABLE"\n', "exactly one"),
    ('set +e\nsrun "$VASP_EXECUTABLE"\n', "failure suppression"),
    ('srun "$VASP_EXECUTABLE"\nif (\n', "bash -n"),
])
def test_template_checker_reports_line(tmp_path, script, reason):
    path = tmp_path / "job.sh"
    path.write_text('#!/bin/bash\n' + script)
    with pytest.raises(ValueError, match="line [0-9]+:.*" + reason):
        runner.check_template(path)


def test_template_checker_accepts_reviewed_synthetic_template(tmp_path, monkeypatch):
    path = tmp_path / "job.sh"
    path.write_text(TEMPLATE)
    runner.check_template(path)
    monkeypatch.setattr(runner.shutil, "which", lambda name: None)
    original = runner.Path.is_file
    monkeypatch.setattr(runner.Path, "is_file", lambda self: False if "Program Files" in str(self) and self.name == "bash.exe" else original(self))
    with pytest.raises(ValueError, match="Bash unavailable"):
        runner.check_template(path)


def test_cli_status_dry_run_and_jobsall_syntax(tmp_path):
    root, _ = prepared(tmp_path)
    dry = run_cli("campaign-submit", "--root", root)
    assert dry.returncode == 0 and "DRY RUN" in dry.stdout and not (root / "submissions.json").exists()
    report = run_cli("campaign-status", "--root", root, "--json")
    assert report.returncode == 0, report.stderr
    data = json.loads(report.stdout)
    assert data["schema"] == "dmi-runner-status-1" and {r["case_id"] for r in data["cases"]} == {"plus", "minus"}
    assert {r["status"] for r in data["cases"]} == {"prepared"}
    text = (root / "jobsall.sh").read_text()
    assert text.count("campaign-submit") == 1 and "--yes" in text
    bash = runner.shutil.which("bash") or "C:/Program Files/Git/bin/bash.exe"
    assert subprocess.run([bash, "-n"], input=text, text=True, capture_output=True).returncode == 0


def test_synthetic_submit_dependencies_keep_science_and_lane_ancestors(tmp_path):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    job.write_text(TEMPLATE)
    data["cases"][1]["execution_parents"] = ["plus"]
    data["cases"].append({"id": "other", "side": "+", "q_frac": [0.25, 0, 0],
                          "purpose": "synthetic independent case"})
    manifest.save(data, source)
    campaign.prepare(source)
    fake = FakeScheduler()
    runner.submit(root, fake, max_concurrent=1, yes=True)
    assert len(fake.calls) == 3
    for (argv, cwd), case in zip(fake.calls, ("plus", "other", "minus")):
        assert cwd == root / "runs" / case / "attempt-001"
        assert argv[:9] == ["sbatch", "--parsable", f"--chdir={cwd}", "--export=ALL",
                            f"--output={cwd / 'slurm-%j.out'}", f"--error={cwd / 'slurm-%j.err'}",
                            f"--job-name={root.name}-{case}-attempt001", f"--comment={cwd}",
                            "--kill-on-invalid-dep=yes"]
        assert argv[-1] == str(cwd / "job.sh")
    assert not any(arg.startswith("--dependency=") for arg in fake.calls[0][0])
    assert "--dependency=afterany:10001" in fake.calls[1][0]
    assert "--dependency=afterok:10001,afterany:10001:10002" in fake.calls[2][0]


def test_synthetic_slurm_submit_scrubs_inherited_scheduler_options(monkeypatch, tmp_path):
    monkeypatch.setenv("SBATCH_ACCOUNT", "wrong")
    monkeypatch.setenv("SBATCH_OPEN_MODE", "append")
    monkeypatch.setenv("SLURM_JOB_ID", "999")
    monkeypatch.setenv("DMI_SYNTHETIC_UNRELATED", "preserved")
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, "12345;cluster\n", "")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    argv = ["sbatch", "--parsable", "job.sh"]
    assert runner.Slurm().submit(argv, tmp_path) == "12345"
    actual, options = calls[0]
    assert actual == argv and isinstance(actual, list)
    assert options["cwd"] == tmp_path and options["check"] is True
    assert "shell" not in options and options["env"]["DMI_SYNTHETIC_UNRELATED"] == "preserved"
    assert all(not key.startswith(("SBATCH_", "SLURM_")) for key in options["env"])


@pytest.mark.parametrize("restart_tag", ["ISTART = 1", "ICHARG = 11"])
def test_synthetic_restart_needs_verified_parent_and_private_copies(tmp_path, restart_tag):
    root, _ = prepared(tmp_path)
    child = root / "runs" / "minus"
    old = "ISTART = 0" if restart_tag.startswith("ISTART") else "ICHARG = 2"
    (child / "INCAR").write_text((child / "INCAR").read_text().replace(old, restart_tag))
    plan = manifest.load(root / "plan.json")
    plan["inputs"]["prepared"]["minus"]["INCAR"] = manifest.file_hash(child / "INCAR")
    manifest.save(plan, root / "plan.json")
    fake = FakeScheduler()
    with pytest.raises(ValueError, match="restart requires a declared execution parent"):
        runner.submit(root, fake, yes=True)
    assert len(fake.calls) == 1
    assert not (child / "attempt-001").exists()
    plan["cases"][1]["execution_parents"] = ["plus"]
    manifest.save(plan, root / "plan.json")
    runner.submit(root, fake, yes=True)
    assert len(fake.calls) == 1
    parent_attempt = synthetic_finish(root, fake, "plus")
    for name in runner.RESTART_FILES:
        (parent_attempt / name).write_bytes((name + " synthetic parent").encode())
    runner.status(root, fake)
    ledger = manifest.load(root / "submissions.json")
    assert ledger["cases"]["plus"]["status"] == "accepted"
    child_attempt = child / "attempt-001"
    child_entry = plan["cases"][1]
    assert runner.cache_valid(root, plan["cases"][0], manifest.load(root / "runs" / "plus" / "result.json"),
                              ledger, plan)
    hashes = runner._stage(root, child_entry, child_attempt, ledger, plan)
    assert set(hashes) == {str(child_attempt / name) for name in campaign.INPUT_FILES + runner.RESTART_FILES}
    for name in runner.RESTART_FILES:
        original = (parent_attempt / name).read_bytes()
        copy = child_attempt / name
        assert copy.is_file() and not copy.is_symlink()
        assert os.stat(copy).st_ino != os.stat(parent_attempt / name).st_ino
        copy.write_bytes(b"synthetic child edit")
        assert (parent_attempt / name).read_bytes() == original


def test_synthetic_jobsall_batch_header_and_hash_contract(tmp_path):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    job.write_text('#!/bin/bash\n#SBATCH --account=synthetic\n#SBATCH -p debug\n'
                   '#SBATCH --constraint=gpu\n#SBATCH --qos=regular\n'
                   '#SBATCH --job-name=old\n#SBATCH -Jold2\n#SBATCH --output=old.out\n'
                   '#SBATCH -e old.err\n#SBATCH --time=12:00:00\n#SBATCH -t 9:00:00\n'
                   '#SBATCH --dependency=afterok:22\n#SBATCH -D /tmp\n'
                   '#SBATCH --array=1-3\n#SBATCH --open-mode=append\n'
                   'set -e\nsrun "$VASP_EXECUTABLE"\n')
    campaign.prepare(source)
    text = (root / "jobsall.sh").read_text()
    lines = text.splitlines()
    assert lines[0] == "#!/bin/bash"
    assert lines[1:5] == ["#SBATCH --account=synthetic", "#SBATCH -p debug",
                           "#SBATCH --constraint=gpu", "#SBATCH --qos=regular"]
    assert [line for line in lines if line.startswith("#SBATCH")][4:] == [
        f"#SBATCH --job-name={root.name}-jobsall",
        f'#SBATCH --output="{root.as_posix()}/jobsall-%j.out"',
        f'#SBATCH --error="{root.as_posix()}/jobsall-%j.err"',
        f"#SBATCH --time={campaign.JOBSALL_WALLTIME}"]
    assert lines[-4] == f'cd "{root.as_posix()}"'
    assert lines[-1] == (f'"${{PYTHON:-{sys.executable.replace(chr(92), "/")}}}" -B -m '
                         f'dmi_pipeline campaign-submit --root "{root.as_posix()}" --yes')
    assert "TODO(T5)" in text and "explicit confirmation" in text
    assert text.count("campaign-submit") == 1 and "srun" not in text and "old.out" not in text
    bash = runner.shutil.which("bash") or "C:/Program Files/Git/bin/bash.exe"
    assert subprocess.run([bash, "-n"], input=text, text=True, capture_output=True).returncode == 0
    assert manifest.load(root / "plan.json")["inputs"]["jobsall_sha256"] == manifest.file_hash(root / "jobsall.sh")
    (root / "jobsall.sh").write_text(text + "# synthetic edit\n")
    fake = FakeScheduler()
    with pytest.raises(ValueError, match="jobsall.sh changed since preparation"):
        runner.submit(root, fake, yes=True)
    assert fake.calls == [] and not (root / "submissions.json").exists()
    assert not (root / "submission.lock").exists()


def test_synthetic_jobsall_missing_header_warns_and_double_submit_is_idempotent(tmp_path, capsys):
    root, _ = prepared(tmp_path)
    assert "WARNING: job template has no leading #SBATCH directives" not in capsys.readouterr().out
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    ledger = manifest.load(root / "submissions.json")
    assert len(fake.calls) == 2
    runner.submit(root, fake, yes=True)
    assert len(fake.calls) == 2
    updated = manifest.load(root / "submissions.json")
    for name in ("plus", "minus"):
        assert len(updated["cases"][name]["attempts"]) == 1
        assert updated["cases"][name]["attempts"][0]["job_id"] == ledger["cases"][name]["attempts"][0]["job_id"]
    assert not any((root / "runs" / name / "attempt-002").exists() for name in ("plus", "minus"))
    other = tmp_path / "other"
    other.mkdir()
    source, data, shared, job, other_root = synthetic_campaign(other)
    campaign.prepare(source)
    assert "WARNING: job template has no leading #SBATCH directives" in capsys.readouterr().out


def test_synthetic_completed_submit_is_idempotent(tmp_path):
    root, _ = prepared(tmp_path)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    synthetic_finish(root, fake, "plus")
    synthetic_finish(root, fake, "minus")
    report = runner.status(root, fake)
    assert {row["status"] for row in report["cases"]} == {"accepted"}
    runner.submit(root, fake, yes=True)
    assert len(fake.calls) == 2
    assert all(len(manifest.load(root / "submissions.json")["cases"][name]["attempts"]) == 1
               for name in ("plus", "minus"))


def test_reference_verified_mid_pass_releases_both_synthetic_gates(tmp_path):
    root, _ = prepared(tmp_path, generated=True)
    fake = FakeScheduler()
    runner.submit(root, fake, max_concurrent=3, yes=True)
    synthetic_finish(root, fake, "plus")
    synthetic_finish(root, fake, "minus", gate=False)
    synthetic_finish(root, fake, "reference-q0")
    rows = {row["case_id"]: row for row in runner.status(root, fake)["cases"]}
    assert rows["reference-q0"]["status"] == "accepted"
    assert rows["plus"]["status"] == "accepted"
    assert rows["minus"]["status"] == "rejected"


@pytest.mark.parametrize("gate, expected", [(True, "accepted"), (False, "rejected")])
def test_synthetic_campaign_status_waits_for_reference_in_table_and_json(tmp_path, monkeypatch, capsys, gate, expected):
    root, _ = prepared(tmp_path, generated=True)
    fake = FakeScheduler()
    monkeypatch.setattr(runner, "Slurm", lambda: fake)
    runner.submit(root, fake, max_concurrent=3, yes=True)
    capsys.readouterr()
    synthetic_finish(root, fake, "plus", gate=gate)

    assert main(["campaign-status", "--root", str(root)]) == 0
    table = capsys.readouterr().out
    assert "plus | submitted (waiting: reference) |" in table
    assert "minus | submitted |" in table
    assert "reference-q0 | submitted |" in table
    assert "SUMMARY: submitted: 2; waiting_reference: 1" in table

    assert main(["campaign-status", "--root", str(root), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema"] == "dmi-runner-status-1"
    rows = {row["case_id"]: row for row in report["cases"]}
    assert report["summary"] == {"submitted": 2, "waiting_reference": 1}
    assert rows["plus"]["pending_reference"] is True
    assert rows["plus"]["execution"] == {"state": "COMPLETED", "exit_code": "0:0"}
    assert rows["minus"]["pending_reference"] is False
    assert rows["minus"]["execution"]["state"] == "PENDING"
    assert rows["reference-q0"]["pending_reference"] is False

    synthetic_finish(root, fake, "reference-q0")
    runner.resume(root, fake, yes=True)
    capsys.readouterr()
    assert main(["campaign-status", "--root", str(root), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    rows = {row["case_id"]: row for row in report["cases"]}
    assert rows["plus"]["status"] == expected
    assert rows["plus"]["pending_reference"] is False
    assert rows["plus"]["gate"]["passed"] is gate
    expected_summary = {"submitted": 1, "waiting_reference": 0, "accepted": 1}
    expected_summary[expected] = expected_summary.get(expected, 0) + 1
    assert report["summary"] == expected_summary
    assert not manifest.load(root / "runs" / "plus" / "result.json").get("pending_reference")
    assert len(fake.calls) == 3
    assert main(["campaign-status", "--root", str(root)]) == 0
    assert "waiting: reference" not in capsys.readouterr().out


def test_pending_reference_synthetic_resume_releases_without_duplicate_readback(tmp_path):
    root, _ = prepared(tmp_path, generated=True)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    synthetic_finish(root, fake, "plus")
    runner.status(root, fake)
    path = root / "runs" / "plus" / "result.json"
    assert manifest.load(path)["pending_reference"] is True
    assert not (root / "runs" / "plus" / "attempt-001" / "readback" / "state.json").exists()
    synthetic_finish(root, fake, "reference-q0")
    runner.resume(root, fake, yes=True)
    assert manifest.load(path)["status"] == "accepted"
    assert not manifest.load(path).get("pending_reference")
    assert len(fake.calls) == 3


def test_terminal_failures_remain_terminal_without_scheduler_history(tmp_path):
    root, _ = prepared(tmp_path)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    synthetic_finish(root, fake, "plus", failed=True)
    synthetic_finish(root, fake, "minus", gate=False)
    runner.status(root, fake)
    fake.jobs.clear()
    rows = {row["case_id"]: row["status"] for row in runner.status(root, fake)["cases"]}
    assert rows == {"plus": "execution_failed", "minus": "rejected"}
    runner.resume(root, fake, yes=True)
    assert len(fake.calls) == 2


def test_uncertain_job_is_not_retried(tmp_path):
    root, _ = prepared(tmp_path)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    fake.jobs.pop("10001")
    runner.resume(root, fake, retry=True, yes=True)
    ledger = manifest.load(root / "submissions.json")
    assert ledger["cases"]["plus"]["status"] == "unresolved"
    assert len(ledger["cases"]["plus"]["attempts"]) == 1
    assert len(fake.calls) == 2


def test_failed_parent_blocks_descendant_without_new_submission(tmp_path):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    job.write_text(TEMPLATE)
    data["cases"][1]["execution_parents"] = ["plus"]
    manifest.save(data, source)
    campaign.prepare(source)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    synthetic_finish(root, fake, "plus", failed=True)
    runner.resume(root, fake, yes=True)
    ledger = manifest.load(root / "submissions.json")
    assert ledger["cases"]["minus"]["status"] == "blocked"
    assert "prerequisite plus" in ledger["cases"]["minus"]["blocked_reason"]
    assert len(fake.calls) == 2
    assert not (root / "runs" / "minus" / "attempt-002").exists()


def test_blocked_restart_child_waits_for_new_accepted_parent(tmp_path):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    job.write_text(TEMPLATE)
    data["cases"][1]["execution_parents"] = ["plus"]
    manifest.save(data, source)
    campaign.prepare(source)
    child = root / "runs" / "minus"
    (child / "INCAR").write_text((child / "INCAR").read_text().replace("ISTART = 0", "ISTART = 1"))
    plan = manifest.load(root / "plan.json")
    plan["inputs"]["prepared"]["minus"]["INCAR"] = manifest.file_hash(child / "INCAR")
    manifest.save(plan, root / "plan.json")
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    assert len(fake.calls) == 1 and not (child / "attempt-001").exists()
    synthetic_finish(root, fake, "plus", failed=True)
    runner.resume(root, fake, yes=True)
    fake.jobs.clear()
    report = runner.status(root, fake)
    assert report["cases"][1]["status"] == "blocked"
    assert "execution parent plus" in report["cases"][1]["blocked_reason"]
    assert not (child / "attempt-001").exists()
    runner.resume(root, fake, retry=True, yes=True)
    parent = synthetic_finish(root, fake, "plus")
    for name in runner.RESTART_FILES:
        (parent / name).write_bytes((name + " synthetic restart").encode())
    runner.resume(root, fake, yes=True)
    assert (child / "attempt-001" / "WAVECAR").read_bytes() == (parent / "WAVECAR").read_bytes()
    assert len(fake.calls) == 3


def test_rejected_parent_blocks_accepted_child_without_releasing_it(tmp_path):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    job.write_text(TEMPLATE)
    data["cases"][1]["execution_parents"] = ["plus"]
    manifest.save(data, source)
    campaign.prepare(source)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    synthetic_finish(root, fake, "plus", gate=False)
    synthetic_finish(root, fake, "minus")
    report = runner.status(root, fake)
    assert {row["case_id"]: row["status"] for row in report["cases"]} == {
        "plus": "rejected", "minus": "blocked"}
    assert "prerequisite plus" in report["cases"][1]["blocked_reason"]
    assert not (root / "runs" / "minus" / "attempt-001" / "readback" / "state.json").exists()


@pytest.mark.parametrize("change", ["attempt INCAR", "reference", "provenance", "plan template"])
def test_cached_synthetic_acceptance_invalidates_without_mutating_attempt(tmp_path, change):
    root, _ = prepared(tmp_path)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    synthetic_finish(root, fake, "plus")
    runner.status(root, fake)
    attempt = root / "runs" / "plus" / "attempt-001"
    if change == "attempt INCAR":
        target = attempt / "INCAR"
    elif change == "reference":
        target = root / "reference" / "references.json"
    elif change == "provenance":
        target = root / "reference" / "reference-provenance.json"
    else:
        target = root / "plan.json"
    if change == "plan template":
        plan = manifest.load(target)
        plan["inputs"]["job_template_sha256"] = "0" * 64
        manifest.save(plan, target)
    else:
        target.write_bytes(target.read_bytes() + b" \n")
    snapshot = {str(path.relative_to(attempt)): path.read_bytes() for path in attempt.rglob("*") if path.is_file()}
    rows = runner.status(root, fake)["cases"]
    assert rows[0]["status"] == "prepared"
    assert "cached acceptance invalid" in rows[0]["blocked_reason"]
    assert {str(path.relative_to(attempt)): path.read_bytes() for path in attempt.rglob("*") if path.is_file()} == snapshot
    runner.resume(root, fake, yes=True)
    assert len(fake.calls) == 2


def test_reference_incompatibility_blocks_completed_case_without_readback(tmp_path):
    root, _ = prepared(tmp_path)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    synthetic_finish(root, fake, "plus")
    provenance = root / "reference" / "reference-provenance.json"
    record = manifest.load(provenance)
    record["magnetic_indices"] = [1, 0]
    manifest.save(record, provenance)
    rows = runner.status(root, fake)["cases"]
    assert rows[0]["status"] == "blocked"
    assert "reference verification failed" in rows[0]["blocked_reason"]
    assert not (root / "runs" / "plus" / "attempt-001" / "readback" / "state.json").exists()


def test_parent_restart_hash_change_invalidates_accepted_child(tmp_path):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    job.write_text(TEMPLATE)
    data["cases"][1]["execution_parents"] = ["plus"]
    manifest.save(data, source)
    campaign.prepare(source)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    parent = synthetic_finish(root, fake, "plus")
    for name in runner.RESTART_FILES:
        (parent / name).write_bytes((name + " synthetic parent").encode())
    synthetic_finish(root, fake, "minus")
    assert {row["status"] for row in runner.status(root, fake)["cases"]} == {"accepted"}
    child = root / "runs" / "minus" / "attempt-001"
    snapshot = {str(path.relative_to(child)): path.read_bytes() for path in child.rglob("*") if path.is_file()}
    (parent / "WAVECAR").write_bytes(b"synthetic changed wave")
    rows = runner.status(root, fake)["cases"]
    assert rows[0]["status"] == "prepared" and rows[1]["status"] != "accepted"
    assert "restart WAVECAR" in rows[0]["blocked_reason"]
    assert "parent plus" in rows[1]["blocked_reason"]
    assert {str(path.relative_to(child)): path.read_bytes() for path in child.rglob("*") if path.is_file()} == snapshot


def test_live_job_does_not_write_result_or_resubmit_and_readback_only_once(tmp_path, monkeypatch):
    root, _ = prepared(tmp_path)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    fake.jobs["10001"]["state"] = "RUNNING"
    runner.resume(root, fake, yes=True)
    result = root / "runs" / "plus" / "result.json"
    assert not result.exists() and len(fake.calls) == 2
    assert runner.status(root, fake)["cases"][0]["execution"]["state"] == "RUNNING"
    synthetic_finish(root, fake, "plus")
    original = runner.step1.read_and_gate
    calls = []

    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(runner.step1, "read_and_gate", counted)
    runner.status(root, fake)
    before = result.read_bytes()
    runner.resume(root, fake, yes=True)
    assert calls == [1] and result.read_bytes() == before


@pytest.mark.parametrize("parent_gate", [True, False])
def test_generated_reference_and_execution_parent_reconcile_in_one_pass(tmp_path, monkeypatch, parent_gate):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    job.write_text(TEMPLATE)
    data["reference"] = {"mode": "generate"}
    data["cases"][1]["execution_parents"] = ["plus"]
    manifest.save(data, source)
    campaign.prepare(source)
    plan = manifest.load(root / "plan.json")
    assert [entry["id"] for entry in plan["cases"]] == ["reference-q0", "plus", "minus"]
    assert plan["cases"][2]["execution_parents"] == ["plus"]
    fake = FakeScheduler()
    runner.submit(root, fake, max_concurrent=3, yes=True)
    synthetic_finish(root, fake, "reference-q0")
    synthetic_finish(root, fake, "plus", gate=parent_gate)
    synthetic_finish(root, fake, "minus")
    calls = []
    original_reference = campaign.check_reference
    original_readback = runner.step1.read_and_gate

    def checked_reference(*args, **kwargs):
        calls.append("reference-q0")
        return original_reference(*args, **kwargs)

    def checked_readback(config, directory, references, output):
        calls.append(directory.parent.name)
        return original_readback(config, directory, references, output)

    monkeypatch.setattr(campaign, "check_reference", checked_reference)
    monkeypatch.setattr(runner.step1, "read_and_gate", checked_readback)
    rows = {row["case_id"]: row for row in runner.status(root, fake)["cases"]}
    assert manifest.load(root / "plan.json")["reference"]["status"] == "verified-generate"
    assert rows["reference-q0"]["status"] == "accepted"
    assert rows["plus"]["status"] == ("accepted" if parent_gate else "rejected")
    assert rows["minus"]["status"] == ("accepted" if parent_gate else "blocked")
    assert calls == (["reference-q0", "plus", "minus"] if parent_gate else ["reference-q0", "plus"])
    assert rows["plus"]["readback"] == "passed"
    if parent_gate:
        assert rows["minus"]["readback"] == "passed"
        assert manifest.load(root / "runs" / "minus" / "result.json")["status"] == "accepted"
    else:
        assert "prerequisite plus" in rows["minus"]["blocked_reason"]
        assert not (root / "runs" / "minus" / "attempt-001" / "readback" / "state.json").exists()


@pytest.mark.parametrize("state, expected, live", [
    ("COMPLETED", "readback_failed", False),
    ("FAILED", "execution_failed", False),
    ("CANCELLED", "execution_failed", False),
    ("TIMEOUT", "execution_failed", False),
    ("NODE_FAIL", "execution_failed", False),
    ("OUT_OF_MEMORY", "execution_failed", False),
    ("DEADLINE", "execution_failed", False),
    ("BOOT_FAIL", "execution_failed", False),
    ("PREEMPTED", "execution_failed", False),
    ("PENDING", "submitted", True),
    ("RUNNING", "running", True),
    ("CONFIGURING", "submitted", True),
    ("COMPLETING", "submitted", True),
    ("REQUEUED", "submitted", True),
    ("REQUEUE_HOLD", "submitted", True),
    ("REQUEUE_FED", "submitted", True),
    ("RESIZING", "submitted", True),
    ("SIGNALING", "submitted", True),
    ("STAGE_OUT", "submitted", True),
    ("STOPPED", "submitted", True),
    ("SUSPENDED", "submitted", True),
    ("SPECIAL_EXIT", "submitted", True),
    ("RESV_DEL_HOLD", "submitted", True),
    ("REVOKED", "submitted", True),
    ("CANCELLED by 1234", "execution_failed", False),
    ("CANCELLED+", "execution_failed", False),
    ("running", "running", True),
    ("MYSTERY", "unresolved", False),
    ("", "unresolved", False),
    (None, "unresolved", False),
])
def test_synthetic_scheduler_state_reconciliation(tmp_path, monkeypatch, state, expected, live):
    root, _ = prepared(tmp_path)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    fake.jobs["10001"] = {"state": state, "exit_code": "0:0"}
    readbacks = []
    monkeypatch.setattr(runner.step1, "read_and_gate", lambda *args, **kwargs: readbacks.append(args))
    runner.resume(root, fake, yes=True)
    ledger = manifest.load(root / "submissions.json")
    case = ledger["cases"]["plus"]
    record = case["attempts"][-1]
    result_path = root / "runs" / "plus" / "result.json"
    assert case["status"] == expected
    assert record["execution"] == {"state": state, "exit_code": "0:0"}
    assert len(fake.calls) == 2 and len(case["attempts"]) == 1
    assert readbacks == []
    if live:
        assert record["status"] == expected
    elif expected in ("execution_failed", "readback_failed"):
        assert record["status"] == expected
    else:
        assert record["status"] == "submitted"  # Unknown states cannot close an attempt.
    assert result_path.exists() is (expected in ("execution_failed", "readback_failed"))
    if result_path.exists():
        assert manifest.load(result_path)["status"] == expected


def test_completed_missing_outputs_is_readback_failed_and_nonzero_does_not_read(tmp_path):
    root, _ = prepared(tmp_path)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    fake.jobs["10001"] = {"state": "COMPLETED", "exit_code": "0:0"}
    synthetic_finish(root, fake, "minus", failed=True)
    runner.status(root, fake)
    assert manifest.load(root / "runs" / "plus" / "result.json")["status"] == "readback_failed"
    result = manifest.load(root / "runs" / "minus" / "result.json")
    assert result["status"] == "execution_failed" and result["readback"] is None
    assert not (root / "runs" / "minus" / "attempt-001" / "readback" / "state.json").exists()


def test_crash_on_second_scheduler_lookup_keeps_atomic_ledger_and_releases_lock(tmp_path):
    root, _ = prepared(tmp_path)
    fake = FakeScheduler()
    runner.submit(root, fake, yes=True)
    synthetic_finish(root, fake, "plus")
    synthetic_finish(root, fake, "minus")
    original = fake.states
    seen = []

    def crash(ids):
        seen.append(ids)
        if len(seen) == 2:
            raise RuntimeError("synthetic scheduler crash")
        return {"10001": fake.jobs["10001"]}  # Missing second job forces a second lookup.

    fake.states = crash
    with pytest.raises(RuntimeError, match="synthetic scheduler crash"):
        runner.resume(root, fake, yes=True)
    assert not (root / "submission.lock").exists()
    ledger = manifest.load(root / "submissions.json")
    assert ledger["schema"] == "dmi-submissions-1"
    assert ledger["cases"]["plus"]["status"] == "accepted"
    fake.states = original
    runner.resume(root, fake, yes=True)
    assert {case["status"] for case in manifest.load(root / "submissions.json")["cases"].values()} == {"accepted"}
