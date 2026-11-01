"""Small, explicitly gated Slurm runner for prepared Step 1 campaigns.

The template checker is heuristic: it recognizes ordinary one-line srun/mpirun/mpiexec
launches, not shell expansion, aliases, functions or a complete Bash control-flow graph.
A reviewed compute-node smoke test is still required before real submission.
"""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess

from . import campaign, manifest, reference, step1
from .realized import incar

RESTART_FILES = ("WAVECAR", "CHGCAR")
LIVE = {"PENDING", "CONFIGURING", "RUNNING", "COMPLETING", "SUSPENDED", "RESIZING"}
FAILURES = {"execution_failed", "readback_failed", "rejected", "blocked"}
LAUNCH = re.compile(r"(?:^|[;&|\s])(?:srun|mpirun|mpiexec|aprun|ibrun|vasp(?:_[A-Za-z0-9]+)?|\"\$VASP_EXECUTABLE\"|\$VASP_EXECUTABLE)(?=\s|$)")


class Slurm:
    """Only the scheduling boundary; tests can supply an object with the same methods."""

    def submit(self, argv, cwd):
        # SBATCH_* and SLURM_* can silently override explicit sbatch options.
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(("SBATCH_", "SLURM_"))}
        result = subprocess.run(argv, cwd=cwd, env=environment, text=True,
                                capture_output=True, check=True)
        return parse_job_id(result.stdout)

    def states(self, job_ids):
        if not job_ids:
            return {}
        ids = ",".join(job_ids)
        queue = subprocess.run(["squeue", "-h", "-j", ids, "-o", "%i|%T"],
                               text=True, capture_output=True, check=True)
        accounting = subprocess.run(["sacct", "-X", "-n", "-P", "-j", ids,
                                     "-o", "JobIDRaw,State,ExitCode"],
                                    text=True, capture_output=True, check=True)
        states = {}
        for line in accounting.stdout.splitlines():
            parts = line.split("|")
            if len(parts) >= 3 and parts[0] in job_ids:
                states[parts[0]] = {"state": parts[1].split()[0].upper(), "exit_code": parts[2]}
        for line in queue.stdout.splitlines():
            parts = line.split("|")
            if len(parts) == 2 and parts[0] in job_ids:
                states[parts[0]] = {"state": parts[1].upper(), "exit_code": None}
        return states

    def find(self, name, comment):
        """Match both job name and attempt directory; ambiguity must not release a job."""
        # %i|%j|%k and JobIDRaw,JobName,Comment are printed in that order by
        # squeue and sacct respectively; empty comments never match an attempt.
        queue = subprocess.run(["squeue", "-h", "-o", "%i|%j|%k"],
                               text=True, capture_output=True, check=True)
        history = subprocess.run(["sacct", "-X", "-n", "-P", "--name", name,
                                  "-o", "JobIDRaw,JobName,Comment"],
                                 text=True, capture_output=True, check=True)
        matches = set()
        for text in (queue.stdout, history.stdout):
            for line in text.splitlines():
                parts = line.split("|")
                if len(parts) >= 3 and parts[1] == name and parts[2] == comment:
                    matches.add(parse_job_id(parts[0]))
        return sorted(matches)


def parse_job_id(text):
    match = re.fullmatch(r"\s*([0-9]+)(?:;[A-Za-z0-9_.-]+)?\s*", text)
    if not match:
        raise ValueError(f"Invalid sbatch --parsable job ID: {text!r}")
    return match.group(1)


@contextmanager
def locked(root, clear_stale=False):
    path = Path(root) / "submission.lock"
    if clear_stale and path.exists():
        # This is an operator assertion, not automatic PID/hostname guessing.
        path.unlink()
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise ValueError(f"Submission lock held at {path}; inspect owner and use --clear-stale-lock only after verifying no writer is active") from error
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "host": socket.gethostname()}, handle)
        yield
    finally:
        path.unlink()


def check_template(path, bash=None):
    """Reject obvious unsafe launch constructs; do not rewrite template semantics."""
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    errors = []
    if not lines or not re.match(r"^#!.*\bbash\b", lines[0]):
        errors.append("line 1: a bash shebang is required")
    launches = []
    last_command = 0
    for number, line in enumerate(lines, 1):
        code = line.strip()
        if not code or code.startswith("#"):
            continue
        last_command = number
        if re.search(r"\bcd\s+['\"]?(?:/|[A-Za-z]:[/\\])", code):
            errors.append(f"line {number}: hardcoded absolute cd")
        if re.search(r"\bset\s+\+e(?:\s|$)|\bset\s+\+o\s+(?:errexit|pipefail)\b", code):
            errors.append(f"line {number}: failure suppression")
        if re.search(r"\|\|\s*(?:true|:)(?:\s|$)", code):
            errors.append(f"line {number}: failure suppression")
        if re.search(r"\brm\s+[^\n]*(?:WAVECAR|CHGCAR)", code) and re.search(r"(?:\.\./|/|\$HOME|\$SCRATCH)", code):
            errors.append(f"line {number}: shared restart cleanup")
        if re.search(r"\bsbatch\b", code):
            errors.append(f"line {number}: embedded submission")
        if re.search(r"\b(?:exit\s+0|trap\b.*(?:EXIT|ERR)|set\s+\+e(?:\s|$))", code):
            errors.append(f"line {number}: failure suppression or exit-code override")
        if LAUNCH.search(code):
            launches.append(number)
            if not re.match(r"^(?:srun|mpirun|mpiexec|aprun|ibrun|vasp(?:_[A-Za-z0-9]+)?|\"\$VASP_EXECUTABLE\"|\$VASP_EXECUTABLE)(?:\s|$)", code):
                errors.append(f"line {number}: launch must be a direct foreground command")
            if re.search(r"(?:^|[^&])&\s*(?:#.*)?$", code):
                errors.append(f"line {number}: background launch")
            if "||" in code or re.search(r"\|\s*(?:tee|cat)\b", code):
                errors.append(f"line {number}: launch exit status may be swallowed")
            if re.search(r"\b(?:if|while|until|eval|bash|sh)\b.*(?:srun|vasp|VASP_EXECUTABLE)", code):
                errors.append(f"line {number}: wrapped launch exit status cannot be verified")
    if len(launches) != 1:
        errors.append(f"line {launches[1] if len(launches) > 1 else 1}: expected exactly one foreground VASP launch, found {len(launches)}")
    if launches and last_command != launches[-1]:
        errors.append(f"line {last_command}: commands after launch may swallow its exit status")
    if bash is None:
        bash = shutil.which("bash")
        if bash is None and Path("C:/Program Files/Git/bin/bash.exe").is_file():
            bash = "C:/Program Files/Git/bin/bash.exe"
    if bash is None:
        raise ValueError("Bash unavailable: install Bash or provide its path to check_template; syntax cannot be skipped for submission")
    # stdin avoids MSYS Bash misinterpreting Windows drive-letter paths.
    syntax = subprocess.run([str(bash), "-n"], input=path.read_text(encoding="utf-8"),
                            text=True, capture_output=True)
    if syntax.returncode:
        match = re.search(r"line (\d+)", syntax.stderr)
        errors.append(f"line {match.group(1) if match else len(lines)}: bash -n: {syntax.stderr.strip()}")
    if errors:
        raise ValueError(f"Unsafe template {path}: " + "; ".join(errors))


def _plan(root):
    root = Path(root).resolve()
    plan = manifest.load(root / "plan.json")
    cases = plan.get("cases")
    if (plan.get("schema") != campaign.PLAN_SCHEMA or not isinstance(cases, list)
            or plan.get("run_count") != len(cases) or not isinstance(plan.get("inputs"), dict)
            or not isinstance(plan.get("reference"), dict)):
        raise ValueError("Invalid prepared campaign plan")
    ids = [entry.get("id") for entry in cases]
    if any(not isinstance(case_id, str) for case_id in ids) or len(set(ids)) != len(ids):
        raise ValueError("Duplicate or invalid plan case IDs")
    for entry in cases:
        campaign.validate_id(entry["id"], "plan case id")
        if entry.get("run_dir") != f"runs/{entry['id']}":
            raise ValueError("Unsafe plan run directory")
        for key in ("execution_parents", "acceptance_requires"):
            if not isinstance(entry.get(key), list):
                raise ValueError(f"Missing plan {key}")
        for parent in entry["execution_parents"]:
            if parent not in ids or parent == entry["id"]:
                raise ValueError(f"Invalid execution parent {parent}")
        for required in entry["acceptance_requires"]:
            if required not in ids and required != "import:reference-q0":
                raise ValueError(f"Invalid acceptance prerequisite {required}")
    for pair in plan.get("pairs", []):
        if pair.get("plus") not in ids or pair.get("minus") not in ids or pair["plus"] == pair["minus"]:
            raise ValueError("Invalid planned pair")
    mode = plan["reference"].get("mode")
    status = plan["reference"].get("status")
    if (mode == "import" and status != "verified-import") or (mode == "generate" and status not in
            ("pending-generate", "verified-generate", "failed-generate")) or mode not in ("import", "generate"):
        raise ValueError("Invalid planned reference status")
    inputs = plan["inputs"]
    paths = inputs.get("source_paths", {})
    if (set(paths) != {"campaign", "material", "job_template"} or
            set(inputs.get("prepared", {})) != set(ids) or not inputs.get("jobsall_sha256")):
        raise ValueError("Plan lacks recorded source/prepared/jobsall hashes; prepare this campaign again")
    if not (root / "jobsall.sh").is_file() or manifest.file_hash(root / "jobsall.sh") != inputs["jobsall_sha256"]:
        raise ValueError("jobsall.sh changed since preparation; prepare a new campaign rather than submitting an edited script")
    expected = {paths["campaign"]: inputs["campaign_sha256"],
                paths["job_template"]: inputs["job_template_sha256"]}
    expected.update({str(Path(paths["material"]) / name): digest
                     for name, digest in inputs["material"].items()})
    manifest.check_files(expected)
    if manifest.file_hash(root / "campaign.json") != inputs["campaign_sha256"]:
        raise ValueError("Prepared campaign differs from plan")
    ordered = []
    while len(ordered) < len(cases):
        ready = [entry for entry in cases if entry not in ordered and
                 all(parent in [item["id"] for item in ordered] for parent in entry["execution_parents"])]
        if not ready:
            raise ValueError("Execution parent cycle in prepared plan")
        ordered.extend(ready)
    for entry in ordered:
        directory = root / entry["run_dir"]
        if set(inputs["prepared"][entry["id"]]) != set(campaign.INPUT_FILES):
            raise ValueError(f"Prepared hashes missing for {entry['id']}")
        manifest.check_files({str(directory / name): inputs["prepared"][entry["id"]][name]
                               for name in campaign.INPUT_FILES})
        check_template(directory / "job.sh")
    return plan, ordered


def _ledger(root, plan, bound):
    path = root / "submissions.json"
    if path.exists():
        ledger = manifest.load(path)
        if (ledger.get("schema") != "dmi-submissions-1" or
                set(ledger.get("cases", {})) != {e["id"] for e in plan["cases"]} or
                len(ledger.get("lanes", [])) != ledger.get("max_concurrent")):
            raise ValueError("Submission ledger does not match plan")
        if bound is not None and bound != ledger["max_concurrent"]:
            raise ValueError("Concurrency bound is already pinned in submissions.json")
        return ledger
    return {"schema": "dmi-submissions-1", "max_concurrent": bound or 2,
            "lanes": [[] for _ in range(bound or 2)],
            "code_identity": None,  # TODO(T5): bind a verified frozen code snapshot here.
            "cases": {entry["id"]: {"status": "prepared", "attempts": [], "planned": True,
                                    "submitted": False, "blocked_reason": None} for entry in plan["cases"]}}


def _reference(root, plan):
    status = plan["reference"]["status"]
    if status not in ("verified-import", "verified-generate"):
        return None
    refs, provenance = reference.verify_files(root / "reference" / "references.json")
    for entry in plan["cases"]:
        if entry["id"] == "reference-q0":
            continue
        directory = root / entry["run_dir"]
        differences = reference.compatible(provenance, manifest.load(directory / "config.json"), directory)
        if differences:
            raise ValueError(f"Reference incompatible with {entry['id']}: {'; '.join(differences)}")
    return refs


def cache_valid(root, entry, result, ledger, plan):
    """Single cache boundary; T5 must verify code_identity and executable record here."""
    try:
        if (result.get("status") not in ("accepted", "rejected") or
                not isinstance(result.get("execution"), dict) or
                result["execution"].get("state") != "COMPLETED" or
                result["execution"].get("exit_code") not in ("0:0", "0", 0) or
                result.get("readback") != "passed" or result.get("gate", {}).get("passed") is not (result["status"] == "accepted") or
                result.get("code_identity") != ledger["code_identity"]):
            return False
        attempt = root / entry["run_dir"] / result["attempt"]
        # VASP may write restart outputs after a cold attempt was staged; those
        # outputs are not input files and must not invalidate its accepted gate.
        staged = campaign.INPUT_FILES + (RESTART_FILES if campaign.restart_enabled(incar(attempt / "INCAR")) else ())
        if set(result["input_hashes"]) != {str(attempt / name) for name in staged}:
            return False
        manifest.check_files(result["input_hashes"])
        expected_outputs = {str(attempt / name) for name in ("OUTCAR", "OSZICAR")}
        if entry["id"] != "reference-q0":
            expected_outputs.add(str(attempt / "readback" / "state.json"))
        if set(result["output_hashes"]) != expected_outputs:
            return False
        manifest.check_files(result["output_hashes"])
        if entry["id"] == "reference-q0" and plan["reference"]["status"] != "verified-generate":
            return False
        if entry["reference"]:
            if plan["reference"]["status"] not in ("verified-import", "verified-generate"):
                return False
            if result.get("reference_hash") != manifest.file_hash(root / "reference" / "references.json"):
                return False
            _reference(root, plan)
        if result["status"] == "accepted":
            for parent in campaign.case_parents(entry):
                parent_result = manifest.load(root / "runs" / parent / "result.json")
                if parent_result.get("status") != "accepted" or result["parent_hashes"].get(parent) != manifest.file_hash(root / "runs" / parent / "result.json"):
                    return False
        state = manifest.load(root / entry["run_dir"] / result["attempt"] / "readback" / "state.json") if entry["id"] != "reference-q0" else None
        if state is not None and state["gate"]["passed"] is not (result["status"] == "accepted"):
            return False
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False


def _script(attempt):
    """T5 substitution point for a reviewed in-job executable-identity instrument."""
    return attempt / "job.sh"


def _submit_job(scheduler, argv, attempt, confirmed):
    """The single gated side-effecting scheduler call for submit and resume."""
    if not confirmed:
        raise ValueError("Job submission needs explicit --yes")
    return parse_job_id(str(scheduler.submit(argv, attempt)))


def _stage(root, entry, attempt, ledger, plan):
    source = root / entry["run_dir"]
    tags = incar(source / "INCAR")
    restart = campaign.restart_enabled(tags)
    if restart and len(entry["execution_parents"]) != 1:
        raise ValueError(f"{entry['id']} restart requires one declared, verified execution parent")
    if not restart and (tags.get("ISTART") != "0" or tags.get("ICHARG") != "2"):
        raise ValueError(f"{entry['id']} requires cold ISTART=0 ICHARG=2 or declared restart")
    parent_paths = []
    if restart:
        parent = entry["execution_parents"][0]
        result = manifest.load(root / "runs" / parent / "result.json")
        parent_entry = next(item for item in plan["cases"] if item["id"] == parent)
        if (not cache_valid(root, parent_entry, result, ledger, plan) or
                set(result.get("restart_hashes", {})) != set(RESTART_FILES)):
            raise ValueError(f"{entry['id']} restart parent {parent} lacks accepted, verified WAVECAR/CHGCAR evidence")
        for name in RESTART_FILES:
            path = root / "runs" / parent / result["attempt"] / name
            manifest.check_files({str(path): result["restart_hashes"][name]})
            parent_paths.append(path)
    attempt.mkdir()
    for name in campaign.INPUT_FILES:
        shutil.copy2(source / name, attempt / name)
    check_template(_script(attempt))
    for path in parent_paths:
        shutil.copy2(path, attempt / path.name)
        manifest.check_files({str(attempt / path.name): result["restart_hashes"][path.name]})
    return manifest.fingerprints([attempt / name for name in campaign.INPUT_FILES] +
                                 [attempt / name for name in RESTART_FILES if (attempt / name).exists()])


def _write_result(root, entry, ledger, record, **values):
    result = {"schema": "dmi-case-result-1", "case_id": entry["id"],
              "status": record["status"], "job_id": record.get("job_id"),
              "attempt": record["directory"], "execution": record.get("execution"),
              "readback": record.get("readback"), "gate": record.get("gate"),
              "blocked_reason": ledger["cases"][entry["id"]].get("blocked_reason"),
              "input_hashes": record.get("input_hashes", {}), "code_identity": ledger["code_identity"]}
    result.update(values)
    manifest.save(result, root / entry["run_dir"] / "result.json")


def _reconcile(root, plan, ordered, ledger, scheduler):
    ids = [item["job_id"] for case in ledger["cases"].values() for item in case["attempts"] if item.get("job_id")]
    states = scheduler.states(ids) if ids else {}
    for entry in ordered:
        case = ledger["cases"][entry["id"]]
        if not case["attempts"]:
            continue
        record = case["attempts"][-1]
        if case["status"] == "blocked" and record["status"] in ("submitted", "running"):
            case["status"] = record["status"]
            case["blocked_reason"] = None
        attempt = root / entry["run_dir"] / record["directory"]
        if record["status"] == "submitting" and not record.get("job_id"):
            matches = scheduler.find(record["job_name"], str(attempt))
            if len(matches) == 1:
                record["job_id"] = matches[0]
                record["status"] = "submitted"
                manifest.save(ledger, root / "submissions.json")
            else:
                case["status"] = "unresolved"
                case["blocked_reason"] = "interrupted submission: inspect Slurm name/comment before retry"
                continue
        if not record.get("job_id"):
            continue
        evidence = states.get(record["job_id"])
        if evidence is None:
            evidence = scheduler.states([record["job_id"]]).get(record["job_id"])
        if evidence is None:
            if record["status"] in ("accepted", "rejected") and (root / entry["run_dir"] / "result.json").is_file():
                if cache_valid(root, entry, manifest.load(root / entry["run_dir"] / "result.json"), ledger, plan):
                    case["status"] = record["status"]
                    continue
            case["status"] = "unresolved"
            case["blocked_reason"] = "scheduler job state unavailable"
            continue
        state = evidence["state"] if isinstance(evidence, dict) else evidence
        exit_code = evidence.get("exit_code") if isinstance(evidence, dict) else None
        record["execution"] = {"state": state, "exit_code": exit_code}
        if state in LIVE:
            case["status"] = "running" if state == "RUNNING" else "submitted"
            record["status"] = case["status"]
            continue
        if state != "COMPLETED" or exit_code not in ("0:0", "0", 0):
            if entry["id"] == "reference-q0" and plan["reference"]["status"] != "failed-generate":
                plan["reference"]["status"] = "failed-generate"
                manifest.save(plan, root / "plan.json")
            if record["status"] != "execution_failed":
                case["status"] = record["status"] = "execution_failed"
                record["readback"] = None
                record["gate"] = None
                _write_result(root, entry, ledger, record)
            case["status"] = "execution_failed"
            continue
        if record["status"] in ("accepted", "rejected", "blocked") and (root / entry["run_dir"] / "result.json").is_file():
            previous = manifest.load(root / entry["run_dir"] / "result.json")
            if cache_valid(root, entry, previous, ledger, plan):
                case["status"] = record["status"]
                continue
            if record["status"] == "blocked" and (previous.get("gate") or {}).get("passed") is True:
                parents = campaign.case_parents(entry)
                if all(ledger["cases"][parent]["status"] == "accepted" for parent in parents):
                    parent_hashes = {parent: manifest.file_hash(root / "runs" / parent / "result.json")
                                     for parent in parents}
                    candidate = dict(previous, status="accepted", blocked_reason=None,
                                     readback="passed", parent_hashes=parent_hashes)
                    if cache_valid(root, entry, candidate, ledger, plan):
                        record["status"] = case["status"] = "accepted"
                        record["readback"] = "passed"
                        case["blocked_reason"] = None
                        manifest.save(candidate, root / entry["run_dir"] / "result.json")
                        continue
            if record["status"] != "readback_failed":
                case["status"] = record["status"] = "readback_failed"
                record["readback"] = "cached evidence changed"
                record["gate"] = None
                _write_result(root, entry, ledger, record)
            else:
                case["status"] = "readback_failed"
            continue
        if not (attempt / "OUTCAR").is_file() or not (attempt / "OSZICAR").is_file():
            if entry["id"] == "reference-q0" and plan["reference"]["status"] != "failed-generate":
                plan["reference"]["status"] = "failed-generate"
                manifest.save(plan, root / "plan.json")
            case["status"] = record["status"] = "execution_failed"
            record["readback"] = "missing OUTCAR or OSZICAR"
            _write_result(root, entry, ledger, record)
            continue
        if record["status"] == "readback_failed":
            continue
        try:
            manifest.check_files(record["input_hashes"])
            if entry["id"] == "reference-q0":
                if plan["reference"]["status"] == "failed-generate":
                    raise ValueError("Generated reference previously failed; explicit new attempt required")
                differences = campaign.check_reference(root, run=attempt, config=attempt / "config.json")
                plan = manifest.load(root / "plan.json")
                if differences:
                    raise ValueError("; ".join(differences))
                ref_hash = manifest.file_hash(root / "reference" / "references.json")
                record["gate"] = {"passed": True, "reasons": []}
            else:
                if not plan["reference"]["status"].startswith("verified"):
                    case["status"] = "blocked"
                    case["blocked_reason"] = "reference not verified"
                    continue
                try:
                    _reference(root, plan)
                except (OSError, ValueError, KeyError) as error:
                    case["status"] = "blocked"
                    case["blocked_reason"] = f"reference verification failed: {error}"
                    continue
                case["blocked_reason"] = None
                state_path = attempt / "readback" / "state.json"
                if state_path.exists():
                    raise ValueError("Existing state cannot be overwritten without verified cache")
                value = step1.read_and_gate(attempt / "config.json", attempt,
                                            root / "reference" / "references.json", state_path)
                record["gate"] = value["gate"]
                ref_hash = manifest.file_hash(root / "reference" / "references.json")
            record["readback"] = "passed"
            case["status"] = record["status"] = "accepted" if record["gate"]["passed"] else "rejected"
            parent_hashes = {}
            if case["status"] == "accepted":
                for parent in campaign.case_parents(entry):
                    if ledger["cases"][parent]["status"] != "accepted":
                        case["status"] = record["status"] = "blocked"
                        case["blocked_reason"] = f"prerequisite {parent} is not accepted"
                        break
                    parent_hashes[parent] = manifest.file_hash(root / "runs" / parent / "result.json")
            output_hashes = manifest.fingerprints([attempt / name for name in ("OUTCAR", "OSZICAR")])
            if entry["id"] != "reference-q0":
                output_hashes.update(manifest.fingerprints([attempt / "readback" / "state.json"]))
            restart_hashes = {name: manifest.file_hash(attempt / name) for name in RESTART_FILES if (attempt / name).is_file()}
            _write_result(root, entry, ledger, record, reference_hash=ref_hash,
                          parent_hashes=parent_hashes, output_hashes=output_hashes,
                          restart_hashes=restart_hashes)
        except (OSError, ValueError, KeyError, TypeError) as error:
            if entry["id"] == "reference-q0":
                plan["reference"]["status"] = "failed-generate"
                manifest.save(plan, root / "plan.json")
            case["status"] = record["status"] = "readback_failed"
            record["readback"] = str(error)
            record["gate"] = None
            _write_result(root, entry, ledger, record)
    manifest.save(ledger, root / "submissions.json")


def _advance(root, scheduler, bound=None, yes=False, retry=False, clear_stale_lock=False, resume=False):
    root = Path(root).resolve()
    if bound is not None and (type(bound) is not int or bound < 1):
        raise ValueError("--max-concurrent must be a positive integer")
    with locked(root, clear_stale_lock):
        plan, ordered = _plan(root)
        ledger = _ledger(root, plan, bound)
        # A failed/changed reference must be recorded as blocked evidence, not
        # turned into a silent substitute for accepted pair readback.
        if resume or (root / "submissions.json").exists():
            _reconcile(root, plan, ordered, ledger, scheduler)
        if any(case["status"] == "unresolved" for case in ledger["cases"].values()):
            raise ValueError("Unresolved submission/job: inspect Slurm and do not resubmit blindly")
        lanes = [list(lane) for lane in ledger["lanes"]]
        submitted = 0
        for entry in ordered:
            case = ledger["cases"][entry["id"]]
            name = entry["id"]
            if case["status"] == "accepted":
                print(f"SKIP {name}: accepted")
                continue
            if case["status"] in ("submitted", "running"):
                print(f"SKIP {name}: live job")
                continue
            if case["attempts"] and not retry:
                print(f"SKIP {name}: {case['status']}; --retry required for a new attempt")
                continue
            dependencies = []
            blocked = None
            tags = incar(root / entry["run_dir"] / "INCAR")
            restart = campaign.restart_enabled(tags)
            for parent in entry["execution_parents"]:
                parent_case = ledger["cases"][parent]
                if parent_case["status"] in FAILURES:
                    blocked = f"execution parent {parent} is not accepted"
                    break
                if parent_case["status"] != "accepted" and restart:
                    blocked = f"restart parent {parent} needs accepted evidence before staging"
                    break
                if parent_case["status"] != "accepted":
                    if not parent_case["attempts"] or not parent_case["attempts"][-1].get("job_id"):
                        blocked = f"execution parent {parent} has no submitted job"
                        break
                    dependencies.append(parent_case["attempts"][-1]["job_id"])
                # A verified parent may have aged out of Slurm accounting; its
                # accepted result, not its old job ID, releases this child.
            if blocked:
                case["status"] = "blocked"
                case["blocked_reason"] = blocked
                print(f"BLOCK {name}: {blocked}")
                continue
            for required in entry["acceptance_requires"]:
                if required == "import:reference-q0":
                    continue
                required_case = ledger["cases"][required]
                if required_case["status"] in FAILURES:
                    blocked = f"prerequisite {required} is not accepted"
                    break
            if blocked:
                case["status"] = "blocked"
                case["blocked_reason"] = blocked
                print(f"BLOCK {name}: {blocked}")
                continue
            attempt_number = len(case["attempts"]) + 1
            attempt = root / entry["run_dir"] / f"attempt-{attempt_number:03d}"
            if attempt.exists():
                raise ValueError(f"Attempt already exists: {attempt}; preserve existing output")
            if restart and len(entry["execution_parents"]) != 1:
                raise ValueError(f"{name} restart requires a declared execution parent")
            lane_index = min(range(len(lanes)), key=lambda index: len(lanes[index]))
            lane = lanes[lane_index]
            dependent = []
            if dependencies:
                dependent.append("afterok:" + ":".join(dependencies))
            if lane:
                dependent.append("afterany:" + ":".join(lane))
            job_name = f"{root.name}-{name}-attempt{attempt_number:03d}"
            argv = ["sbatch", "--parsable", f"--chdir={attempt}", "--export=ALL",
                    f"--output={attempt / 'slurm-%j.out'}", f"--error={attempt / 'slurm-%j.err'}",
                    f"--job-name={job_name}", f"--comment={attempt}", "--kill-on-invalid-dep=yes"]
            if dependent:
                argv.append("--dependency=" + ",".join(dependent))
            argv.append(str(_script(attempt)))
            if not yes:
                print(f"DRY RUN {name}: cwd={attempt} argv={json.dumps(argv)}")
                lane.append(f"planned-{name}")
                continue
            input_hashes = _stage(root, entry, attempt, ledger, plan)
            record = {"directory": attempt.name, "status": "submitting", "job_id": None,
                      "job_name": job_name, "lane": lane_index, "input_hashes": input_hashes,
                      "execution": None, "readback": None, "gate": None}
            case["attempts"].append(record)
            case["status"] = "unresolved"
            manifest.save(ledger, root / "submissions.json")
            # All real submissions flow through this one confirmed, locked call.
            record["job_id"] = _submit_job(scheduler, argv, attempt, yes)
            record["status"] = case["status"] = "submitted"
            case["submitted"] = True
            case["blocked_reason"] = None
            ledger["lanes"][lane_index].append(record["job_id"])
            manifest.save(ledger, root / "submissions.json")
            lane.append(record["job_id"])
            submitted += 1
            print(f"SUBMIT {name}: {record['job_id']} {attempt.name}")
        if yes:
            manifest.save(ledger, root / "submissions.json")
        print(f"SUMMARY: {submitted} submitted; {len(ordered)} planned; max concurrent {ledger['max_concurrent']}")
        return ledger


def submit(root, scheduler=None, max_concurrent=None, yes=False, clear_stale_lock=False):
    return _advance(root, scheduler or Slurm(), max_concurrent, yes,
                    clear_stale_lock=clear_stale_lock)


def resume(root, scheduler=None, retry=False, yes=False, clear_stale_lock=False):
    return _advance(root, scheduler or Slurm(), yes=yes, retry=retry,
                    clear_stale_lock=clear_stale_lock, resume=True)


def status(root, scheduler=None, json_output=False, clear_stale_lock=False):
    root = Path(root).resolve()
    with locked(root, clear_stale_lock):
        plan, ordered = _plan(root)
        ledger = _ledger(root, plan, None)
        if (root / "submissions.json").exists():
            _reconcile(root, plan, ordered, ledger, scheduler or Slurm())
        rows = []
        for entry in ordered:
            case = ledger["cases"][entry["id"]]
            latest = case["attempts"][-1] if case["attempts"] else {}
            rows.append({"case_id": entry["id"], "pair": entry.get("pair"),
                         "status": case["status"], "job_id": latest.get("job_id"),
                         "attempt": latest.get("directory"), "execution": latest.get("execution"),
                         "readback": latest.get("readback"), "gate": latest.get("gate"),
                         "blocked_reason": case.get("blocked_reason")})
        report = {"schema": "dmi-runner-status-1", "pairs": plan.get("pairs", []), "cases": rows}
        if json_output:
            print(json.dumps(report, indent=2))
        else:
            print("case id | status | job id | attempt | execution | readback | gate | blocked reason")
            for row in rows:
                print(" | ".join(str(row[key] if row[key] is not None else "-") for key in
                                 ("case_id", "status", "job_id", "attempt", "execution", "readback", "gate", "blocked_reason")))
            for pair in report["pairs"]:
                print(f"pair {pair['id']}: {pair['plus']} / {pair['minus']} (individual states above; no parity/SOC claim)")
        return report
