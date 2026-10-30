"""Synthetic material and template only; campaign preparation never executes VASP."""

import json

import numpy as np
import pytest

from dmi_pipeline import campaign, manifest, reference, step1
from dmi_pipeline.realized import incar, numbers
from tests.test_step1 import poscar, recipe, run_cli


def synthetic_campaign(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir()
    poscar(shared / "POSCAR")
    (shared / "INCAR").write_text("ENCUT = 550\nENINI = 500\nISTART = 0\nICHARG = 2\n"
                                  "MAGMOM = 9 9 9\nM_CONSTR = 0 0 0\nLSPIRAL = False\n")
    (shared / "KPOINTS").write_bytes(b"synthetic\n0\nGamma\n5 5 5\n0 0 0\n")
    (shared / "POTCAR").write_bytes(b"synthetic potential; not VASP data\n")
    job = tmp_path / "job.sh"
    job.write_bytes(b"#!/bin/bash\n# synthetic template only; never submitted\n")
    defaults = recipe("F0")
    defaults.pop("id")
    defaults.pop("side")
    defaults.pop("q_frac")
    defaults.pop("angle_deg")
    defaults.pop("f1_policy")
    defaults["signs"] = [1, 1]
    defaults["seed_magnitudes"] = [2.2, 2.2]
    defaults["rwigs"] = [1.5, 0.8]
    defaults["lambda"] = 1.0
    source = tmp_path / "campaign-source.json"
    data = {"schema": "dmi-campaign-1", "run_root": str(tmp_path / "campaign-run"),
            "material": str(shared), "job_template": str(job),
            "reference": {"mode": "import", "path": str(tmp_path / "independent-q0-reference")},
            "defaults": defaults,
            "cases": [{"id": "plus", "side": "+", "q_frac": [0.25, 0, 0], "purpose": "pair member",
                       "pair": "fe", "seed_magnitudes": [2.2, 2.2]},
                      {"id": "minus", "side": "-", "q_frac": [0.25, 0, 0], "purpose": "pair member",
                       "pair": "fe"}]}
    manifest.save(data, source)
    run = tmp_path / "q0-completed"
    config = reference.prepare_q0(dict(defaults, id="reference-q0"), shared / "POSCAR")
    step1.write_inputs(config, run, shared, job)
    (run / "OUTCAR").write_text("vasp.test synthetic\n" + (run / "INCAR").read_text() +
                                  "Iteration 1( 1)\naborting loop because EDIFF is reached\nGeneral timing and accounting\n")
    (run / "OSZICAR").write_text(" DAV: 1 -1\n ion MW_int M_int\n"
         " 1 1.800 0.000 0.000 2.000 0.000 0.000\n"
         " 2 1.800 0.000 0.000 2.000 0.000 0.000\n"
         " 3 0.000 0.000 0.000 0.000 0.000 0.000\n"
         " 1 F= -1 E0= -1\n E_p = 0.0E+00 lambda = 0.0E+00\n")
    reference.extract(run, run / "config.json", tmp_path / "independent-q0-reference")
    return source, data, shared, job, tmp_path / "campaign-run"


def test_synthetic_pair_expansion_matches_single_recipe_cli(tmp_path):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    original = source.read_bytes()
    plan = campaign.prepare(source)
    assert (root / "campaign.json").read_bytes() == original
    assert plan == manifest.load(root / "plan.json")
    for case in data["cases"]:
        case_id = case["id"]
        resolved = dict(data["defaults"])
        resolved.update({key: value for key, value in case.items() if key in campaign.RECIPE_FIELDS})
        resolved["id"] = case_id
        assert manifest.load(root / "cases" / case_id / "recipe.json") == resolved
        recipe_file = tmp_path / f"{case_id}-recipe.json"
        manifest.save(resolved, recipe_file)
        single = tmp_path / f"{case_id}-single"
        result = run_cli("step1-prepare", "--recipe", recipe_file, "--inputs", shared,
                         "--job-template", job, "--output", single)
        assert result.returncode == 0, result.stderr
        batch = root / "runs" / case_id
        for name in ("config.json", "INCAR.step1", "INCAR", "POSCAR", "KPOINTS", "POTCAR", "job.sh"):
            assert (batch / name).read_bytes() == (single / name).read_bytes()
        config = manifest.load(batch / "config.json")
        assert config == step1.prepare(resolved, shared / "POSCAR")
        tags = incar(batch / "INCAR")
        assert tags["ENCUT"] == "550" and tags["ENINI"] == "500"
        assert tags["ISTART"] == "0" and tags["ICHARG"] == "2"
        assert tags["MAGMOM"] == config["tags"]["MAGMOM"]
        assert tags["M_CONSTR"] == config["tags"]["M_CONSTR"]
        assert tags["LSPIRAL"] == "T"
        assert numbers(tags["M_CONSTR"]).reshape(-1, 3) == pytest.approx(np.asarray(config["targets"]))
        assert (batch / "INCAR").read_text().count("MAGMOM =") == 1
        assert (batch / "INCAR").read_text().count("M_CONSTR =") == 1
    plus = manifest.load(root / "runs" / "plus" / "config.json")
    minus = manifest.load(root / "runs" / "minus" / "config.json")
    assert plus["q_frac"] == [0.25, 0, 0]
    assert minus["q_frac"] == [-0.25, -0.0, -0.0]
    assert np.asarray(minus["targets"]) == pytest.approx(np.asarray(plus["targets"]) * [1, -1, 1])
    assert minus["tags"]["QSPIRAL"].split()[0] == "-0.25"


def test_synthetic_plan_dependencies_and_hashes(tmp_path):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    plan = campaign.prepare(source)
    assert plan["schema"] == "dmi-plan-1" and plan["run_count"] == 2
    assert plan["pairs"] == [{"id": "fe", "plus": "plus", "minus": "minus"}]
    assert plan["reference"] == {"mode": "import", "path": data["reference"]["path"],
                                 "status": "verified-import",
                                 "records": "reference/references.json and reference/reference-provenance.json"}
    for entry in plan["cases"]:
        assert entry["purpose"] == "pair member" and entry["pair"] == "fe"
        assert entry["side"] in ("+", "-")
        assert entry["initialization"] == "cold (ISTART=0, ICHARG=2)"
        assert entry["run_dir"] == "runs/" + entry["id"]
        assert entry["execution_parents"] == []
        assert entry["acceptance_requires"] == ["import:reference-q0"]
        assert entry["reference"] == "import:reference-q0"
    assert plan["inputs"] == {"campaign_sha256": manifest.file_hash(source),
                              "material": {name: manifest.file_hash(shared / name)
                                           for name in ("POSCAR", "INCAR", "KPOINTS", "POTCAR")},
                              "job_template_sha256": manifest.file_hash(job)}
    assert all(not (root / name).exists() for name in ("submissions.json", "jobsall.sh", "submission.lock"))
    assert not any(root.rglob("submission-id.txt"))


@pytest.mark.parametrize("label,change,expected", [
    ("duplicate", lambda d: d["cases"][1].update(id="plus"), "Duplicate"),
    ("collision", lambda d: d["cases"][1].update(id="PLUS"), "collision"),
    ("trailing_dot", lambda d: d["cases"][1].update(id="plus."), "Unsafe"),
    ("reserved", lambda d: d["cases"][1].update(id="reference-q0"), "collision"),
    ("unsafe_parent", lambda d: d["cases"][1].update(id="../x"), "Unsafe"),
    ("unsafe_separator", lambda d: d["cases"][1].update(id="a/b"), "Unsafe"),
    ("empty_id", lambda d: d["cases"][1].update(id=""), "Unsafe"),
    ("unknown", lambda d: d["cases"][0].update(resource="gpu"), "Unknown"),
    ("unknown_defaults", lambda d: d["defaults"].update(executable="vasp"), "Unknown"),
    ("unknown_campaign", lambda d: d.update(resources="gpu"), "Unknown"),
    ("unknown_reference", lambda d: d["reference"].update(typo="x"), "Unknown"),
    ("invalid_recipe", lambda d: d["defaults"].pop("seed_magnitudes"), "Invalid recipe"),
    ("missing_parent", lambda d: d["cases"][0].update(execution_parents=["absent"]), "Missing execution parent"),
    ("cycle", lambda d: (d["cases"][0].update(execution_parents=["minus"]),
                         d["cases"][1].update(execution_parents=["plus"])), "cycle"),
    ("two_plus", lambda d: d["cases"][1].update(side="+"), "exactly one"),
    ("mismatched_q", lambda d: d["cases"][1].update(q_frac=[0.3, 0, 0]), "mismatched"),
    ("mismatched_family", lambda d: d["cases"][1].update(family="F1", angle_deg=30, f1_policy="diagnostic"), "mismatched"),
    ("mismatched_axis", lambda d: d["cases"][1].update(axis="x"), "mismatched"),
    ("mismatched_seeds", lambda d: d["cases"][1].update(seed_magnitudes=[3, 3]), "mismatched"),
    ("missing_acceptance", lambda d: d["cases"][0].update(acceptance_requires=["absent"]), "Missing acceptance"),
    ("unsafe_pair", lambda d: d["cases"][1].update(pair="../bad"), "Unsafe"),
    ("reserved_windows_id", lambda d: d["cases"][1].update(id="CON.txt"), "Unsafe"),
    ("invalid_q", lambda d: d["cases"][1].update(q_frac=[0, 0, 0]), "unwrapped positive"),
    ("negative_q_double_flip", lambda d: d["cases"][1].update(q_frac=[-0.25, 0, 0]), "unwrapped positive"),
    ("wrong_reference_mode", lambda d: d["reference"].update(mode="other"), "reference.mode"),
])
def test_synthetic_invalid_campaign_leaves_root_uncreated(tmp_path, label, change, expected):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    change(data)
    manifest.save(data, source)
    with pytest.raises(ValueError, match=expected):
        campaign.prepare(source)
    assert not root.exists(), label


@pytest.mark.parametrize("missing,expected", [
    ("job", "job_template"), ("POSCAR", "POSCAR"), ("INCAR", "INCAR"),
    ("KPOINTS", "KPOINTS"), ("POTCAR", "POTCAR"),
])
def test_synthetic_missing_input_is_pre_write_failure(tmp_path, missing, expected):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    path = job if missing == "job" else shared / missing
    path.unlink()
    with pytest.raises(ValueError, match=expected):
        campaign.prepare(source)
    assert not root.exists()


def test_synthetic_restart_requires_real_declared_parent(tmp_path):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    (shared / "INCAR").write_text("ISTART = 1\nICHARG = 0\n")
    with pytest.raises(ValueError, match="ISTART=0 and ICHARG=2"):
        campaign.prepare(source)
    assert not root.exists()
    data["cases"][1]["execution_parents"] = ["plus"]
    manifest.save(data, source)
    with pytest.raises(ValueError, match="ISTART=0 and ICHARG=2"):
        campaign.prepare(source)
    assert not root.exists()
    data["cases"][0]["execution_parents"] = ["minus"]
    manifest.save(data, source)
    with pytest.raises(ValueError, match="cycle"):
        campaign.prepare(source)
    assert not root.exists()


def test_synthetic_existing_root_not_overwritten(tmp_path):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    root.mkdir()
    marker = root / "do-not-touch"
    marker.write_bytes(b"prior run")
    with pytest.raises(ValueError, match="must be empty"):
        campaign.prepare(source)
    assert list(root.iterdir()) == [marker] and marker.read_bytes() == b"prior run"


def test_synthetic_cli_prepare_and_plan_round_trip(tmp_path):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    preview = run_cli("campaign-plan", "--campaign", source)
    assert preview.returncode == 0, preview.stderr
    assert not root.exists()
    assert json.loads(preview.stdout)["run_count"] == 2
    prepared = run_cli("campaign-prepare", "--campaign", source)
    assert prepared.returncode == 0, prepared.stderr
    assert "Prepared 2 runs" in prepared.stdout
    shown = run_cli("campaign-plan", "--root", root)
    assert shown.returncode == 0, shown.stderr
    assert json.loads(preview.stdout)["reference"]["status"] == "unverified-import"
    assert json.loads(shown.stdout)["reference"]["status"] == "verified-import"
    for key in ("run_count", "cases", "pairs"):
        assert json.loads(preview.stdout)[key] == json.loads(shown.stdout)[key]
    assert '"execution_parents": []' in shown.stdout
    assert '"acceptance_requires": [' in shown.stdout
    assert "import:reference-q0" in shown.stdout and "fe" in shown.stdout
    assert "runtime" not in shown.stdout.lower()
    assert not (root / "submissions.json").exists()
    assert not any(root.rglob("slurm-*")) and not any(root.rglob("submission-id.txt"))
    repeated = run_cli("campaign-prepare", "--campaign", source)
    assert repeated.returncode == 1 and repeated.stderr.startswith("ERROR:")
    assert "must be empty" in repeated.stderr


def test_synthetic_reference_generate_plan_only(tmp_path):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    data["reference"] = {"mode": "generate"}
    manifest.save(data, source)
    result = run_cli("campaign-plan", "--campaign", source)
    assert result.returncode == 0, result.stderr
    preview = json.loads(result.stdout)
    assert preview["run_count"] == 3
    assert preview["cases"][0]["id"] == "reference-q0"
    assert preview["cases"][0]["status"] == "reference-producing"
    assert preview["reference"]["status"] == "pending-generate"
    for entry in preview["cases"][1:]:
        assert entry["execution_parents"] == []
        assert entry["acceptance_requires"] == ["reference-q0"]
    assert not root.exists()
    prepare_result = run_cli("campaign-prepare", "--campaign", source)
    assert prepare_result.returncode == 0, prepare_result.stderr
    assert manifest.load(root / "runs" / "reference-q0" / "config.json")["q_frac"] == [0, 0, 0]
    assert manifest.load(root / "plan.json")["reference"]["status"] == "pending-generate"


@pytest.mark.parametrize("collision", ["source", "material", "template", "reference"])
def test_synthetic_output_collision_preserves_inputs(tmp_path, collision):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    if collision == "source":
        data["run_root"] = str(tmp_path)
    if collision == "material":
        data["run_root"] = str(shared)
    if collision == "template":
        data["run_root"] = str(job.parent)
    if collision == "reference":
        data["reference"]["path"] = str(root / "q0")
    manifest.save(data, source)
    with pytest.raises(ValueError, match="collision"):
        campaign.prepare(source)
    assert not root.exists()
    assert source.is_file() and (shared / "POSCAR").is_file() and job.is_file()


def test_synthetic_explicit_parent_is_not_a_reference_requirement(tmp_path):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    data["cases"][1]["execution_parents"] = ["plus"]
    manifest.save(data, source)
    plan = campaign.prepare(source)
    minus = plan["cases"][1]
    assert minus["execution_parents"] == ["plus"]
    assert minus["acceptance_requires"] == ["import:reference-q0"]
    assert minus["initialization"] == "declared execution parent; shared INCAR: ISTART=0, ICHARG=2"
    assert (root / "runs" / "minus" / "config.json").is_file()


@pytest.mark.parametrize("missing", ["job", "POTCAR"])
def test_synthetic_empty_input_is_pre_write_failure(tmp_path, missing):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    (job if missing == "job" else shared / missing).write_bytes(b" \n")
    with pytest.raises(ValueError, match="nonempty"):
        campaign.prepare(source)
    assert not root.exists()
