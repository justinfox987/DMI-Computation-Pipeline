"""Synthetic q0 runs only; historical Fe values are excerpt-level, not run evidence."""

import numpy as np
import pytest

from dmi_pipeline import campaign, manifest, reference, step1
from dmi_pipeline.realized import incar, numbers
from tests.test_campaign import synthetic_campaign
from tests.test_step1 import poscar, recipe, run_cli, synthetic_readback


def q0_run(tmp_path):
    source, data, shared, job, root = synthetic_campaign(tmp_path)
    return tmp_path / "q0-completed", shared, source, data, root


def test_prepare_q0_preserves_production_q_rejection_and_signs(tmp_path):
    path = poscar(tmp_path / "POSCAR")
    for signs in ([1, 1], [1, -1]):
        settings = recipe("F0")
        settings["signs"] = signs
        settings["q_frac"] = [0, 0, 0]
        record = reference.prepare_q0(settings, path)
        assert record["schema_version"] == 3 and record["convention"] == step1.CONVENTION
        assert record["q_frac"] == [0, 0, 0]
        assert record["targets"] == [[1, 0, 0], [signs[1], 0, 0], [0, 0, 0]]
        assert record["tags"]["QSPIRAL"] == "0 0 0"
        assert record["tags"]["LAMBDA"] == "0.0"
        for key, expected in {"I_CONSTRAINED_M": "1", "LSPIRAL": "T", "LZEROZ": "T",
                              "LNONCOLLINEAR": "T", "LSORBIT": "F", "SAXIS": "0 0 1",
                              "RWIGS": "1.3 0.8"}.items():
            assert record["tags"][key] == expected
        assert numbers(record["tags"]["MAGMOM"]).reshape(-1, 3).tolist() == [
            [4, 0, 0], [4 * signs[1], 0, 0], [0, 0, 0]]
        with pytest.raises(ValueError, match="reciprocal-lattice q"):
            step1.prepare(settings, path)
    with pytest.raises(ValueError, match="reciprocal-lattice q"):
        step1.coefficients([[1, 0, 0], [1, 0, 0]], [0, 0, 0], "z",
                           [{"a": 0, "b": 1, "R": [0, 0, 0], "p": [[0, 0, 1]]}], [0, 1])
    with pytest.raises(ValueError, match="planar F0"):
        reference.prepare_q0(recipe("F1"), path)


def test_extract_final_multitable_order_and_provenance(tmp_path):
    run, shared, source, data, root = q0_run(tmp_path)
    config = manifest.load(run / "config.json")
    config["magnetic_indices"] = [1, 0]
    manifest.save(config, run / "config.json")
    oszicar = run / "OSZICAR"
    first = oszicar.read_text()
    second = first.replace("DAV: 1 -1", "DAV: 1 -1\n DAV: 2 -1")
    second = second.replace(" 2 1.800 0.000 0.000 2.000 0.000 0.000",
                            " 2 1.758 0.000 0.000 2.131 0.000 0.000")
    second = second.replace(" 1 F=", " 2 F=")
    oszicar.write_text(first + second)
    outcar = run / "OUTCAR"
    outcar.write_text(outcar.read_text().replace("General timing and accounting",
                           "Iteration 2( 1)\nIteration 2( 2)\naborting loop because EDIFF is reached\nGeneral timing and accounting"))
    output = tmp_path / "extracted"
    refs, provenance = reference.extract(run, run / "config.json", output)
    assert refs == {"M_int": [2.131, 2.0], "MW_int": [1.758, 1.8]}
    assert manifest.load(output / "references.json") == refs
    assert reference.verify_files(output / "references.json")[0] == refs
    assert provenance["schema"] == reference.SCHEMA
    assert provenance["magnetic_indices"] == [1, 0]
    assert provenance["rwigs"] == [1.5, 0.8]
    assert provenance["final_step"] == [2, 2]
    assert provenance["oszicar_lines"] == step1.check_run(run, 3)["sphere"]["lines"]
    assert provenance["outcar_final_ediff"] and provenance["incar_echo"]
    assert provenance["build_banner"] == "vasp.test synthetic"
    assert provenance["extraction_host"] and provenance["extracted_at_utc"].endswith("+00:00")
    assert set(provenance["sha256"]) == set(reference.SOURCE_FILES)
    for name in reference.SOURCE_FILES:
        assert provenance["source_paths"][name] == str((run / name).resolve())
        assert provenance["sha256"][name] == manifest.file_hash(run / name)
    assert all(key in provenance["input_tags"] for key in ("QSPIRAL", "LAMBDA", "RWIGS", "I_CONSTRAINED_M"))
    assert set(provenance["relevant_input_tags"]) == set(reference.RELEVANT_TAGS)
    assert provenance["references_sha256"] == manifest.file_hash(output / "references.json")
    state = synthetic_readback(tmp_path / "finite-q", step1.prepare(recipe("F0"), shared / "POSCAR"),
                               2 * np.array([[1, 0, 0], [1, 0, 0], [0, 0, 0]]),
                               1.8 * np.array([[1, 0, 0], [1, 0, 0], [0, 0, 0]]))
    assert "M_int" in step1.validate(manifest.load(tmp_path / "finite-q" / "config.json"), state,
                                      refs["M_int"], refs["MW_int"])["references"]


@pytest.mark.parametrize("fault, message", [
    ("not_converged", "EDIFF"), ("truncated", "count mismatch"),
    ("restarted", "ambiguous completed"), ("ambiguous_loop", "restart or missing"),
    ("missing_oszicar", "OSZICAR"), ("nonzero_q", "QSPIRAL"),
    ("nonzero_lambda", "LAMBDA"), ("wrong_mode", "I_CONSTRAINED_M"),
    ("missing_mode", "I_CONSTRAINED_M"), ("missing_site_map", "magnetic_indices"),
])
def test_extract_rejects_incomplete_or_finite_q_synthetic_run(tmp_path, fault, message):
    run, shared, source, data, root = q0_run(tmp_path)
    if fault == "not_converged":
        path = run / "OUTCAR"
        path.write_text(path.read_text().replace("aborting loop because EDIFF is reached", "NELM exhausted"))
    if fault == "truncated":
        path = run / "OSZICAR"
        path.write_text(path.read_text() + " DAV: 1 -1\n ion MW_int M_int\n 1 0 0 0 0 0 0\n")
    if fault == "restarted":
        path = run / "OUTCAR"
        path.write_text(path.read_text() + path.read_text())
    if fault == "ambiguous_loop":
        path = run / "OUTCAR"
        path.write_text(path.read_text().replace("General timing and accounting",
                        "Iteration 1( 1)\naborting loop because EDIFF is reached\nGeneral timing and accounting"))
    if fault == "missing_oszicar":
        (run / "OSZICAR").unlink()
    if fault == "missing_mode":
        path = run / "INCAR"
        path.write_text("\n".join(line for line in path.read_text().splitlines()
                                  if not line.startswith("I_CONSTRAINED_M =")) + "\n")
    if fault in {"nonzero_q", "nonzero_lambda", "wrong_mode"}:
        key, replacement = {"nonzero_q": ("QSPIRAL", "0.25 0 0"),
                            "nonzero_lambda": ("LAMBDA", "1"),
                            "wrong_mode": ("I_CONSTRAINED_M", "2")}[fault]
        path = run / "INCAR"
        path.write_text(path.read_text().replace(f"{key} = {incar(path)[key]}", f"{key} = {replacement}"))
    config = {} if fault == "missing_site_map" else {"magnetic_indices": [0, 1]}
    with pytest.raises((ValueError, OSError), match=message):
        reference.extract(run, config)


def test_excerpt_values_are_not_run_evidence(tmp_path):
    # Values from the historical Fe q0 excerpt, not a completed-run fixture.
    excerpt = {"M_int": [2.131, 2.131], "MW_int": [1.758, 1.758]}
    run, shared, source, data, root = q0_run(tmp_path)
    (run / "OSZICAR").write_text(" ion MW_int M_int\n"
                                   + "".join(f" {ion} {mw:.3f} 0 0 {m:.3f} 0 0\n"
                                             for ion, (m, mw) in enumerate(zip(excerpt["M_int"], excerpt["MW_int"]), 1))
                                   + " 3 0 0 0 0 0 0\n 1 F= -1\n E_p = 0 lambda = 0\n")
    with pytest.raises(ValueError, match="electronic loop"):
        reference.extract(run, run / "config.json")


@pytest.mark.parametrize("kind, name", [
    ("POSCAR", "POSCAR hash"), ("KPOINTS", "KPOINTS hash"), ("POTCAR", "POTCAR hash"),
    ("ENCUT", "ENCUT"), ("ENINI", "ENINI"), ("NBANDS", "NBANDS"),
    ("ISMEAR", "ISMEAR"), ("SIGMA", "SIGMA"), ("EDIFF", "EDIFF"),
    ("RWIGS", "RWIGS"), ("indices", "magnetic-site order"), ("missing", "missing on case"),
    ("missing_ref", "missing on reference"), ("unknown", "Unreviewed"),
])
def test_compatible_reports_each_blocking_difference(tmp_path, kind, name):
    run, shared, source, data, root = q0_run(tmp_path)
    _, provenance = reference.extract(run, run / "config.json")
    config = step1.prepare(dict(recipe("F0"), signs=[1, 1], rwigs=[1.5, 0.8]), shared / "POSCAR")
    if kind in reference.MATERIAL_FILES:
        path = shared / kind
        path.write_bytes(path.read_bytes() + b"\nchanged")
    elif kind == "indices":
        config["magnetic_indices"] = [1, 0]
    elif kind == "missing":
        (shared / "INCAR").write_text((shared / "INCAR").read_text().replace("ENCUT = 550\n", ""))
    elif kind == "missing_ref":
        provenance["input_tags"].pop("ENCUT")
    elif kind == "unknown":
        (shared / "INCAR").write_text((shared / "INCAR").read_text() + "UNKNOWN_TAG = 1\n")
    elif kind == "RWIGS":
        config["tags"]["RWIGS"] = "1.6 0.8"
    else:
        provenance["input_tags"][kind] = "1"
    if kind == "unknown":
        with pytest.raises(ValueError, match=name):
            reference.compatible(provenance, config, shared)
        return
    differences = reference.compatible(provenance, config, shared)
    assert any(name in diff for diff in differences), differences


def test_prepared_case_allowed_tag_tampering_cannot_pass(tmp_path):
    run, shared, source, data, root = q0_run(tmp_path)
    _, provenance = reference.extract(run, run / "config.json")
    config = step1.prepare(dict(recipe("F0"), signs=[1, 1], rwigs=[1.5, 0.8]), shared / "POSCAR")
    case = tmp_path / "case"
    step1.write_inputs(config, case, shared)
    path = case / "INCAR"
    path.write_text(path.read_text().replace("QSPIRAL = 0.25 0.0 0.0", "QSPIRAL = 0.3 0 0"))
    assert "prepared config" in " ".join(reference.compatible(provenance, config, case))
    path.write_text(path.read_text().replace("QSPIRAL = 0.3 0 0", "QSPIRAL = 0.25 0.0 0.0"))
    assert reference.compatible(provenance, config, case) == []


def test_compatible_historical_allowed_differences_and_case_mismatch(tmp_path):
    run, shared, source, data, root = q0_run(tmp_path)
    _, provenance = reference.extract(run, run / "config.json")
    config = step1.prepare(dict(recipe("F0"), signs=[1, 1], rwigs=[1.5, 0.8]), shared / "POSCAR")
    for key, value in {"ICHARG": "1", "LORBIT": "2", "NCORE": "8", "KPAR": "2",
                       "LZEROZ": "True", "LNONCOLLINEAR": "True", "LSORBIT": "False",
                       "LSPIRAL": "True"}.items():
        provenance["input_tags"][key] = value
    with (shared / "INCAR").open("a") as handle:
        handle.write("LORBIT = 11\nNCORE = 16\nKPAR = 4\n")
    assert reference.compatible(provenance, config, shared) == []
    provenance["input_tags"]["I_CONSTRAINED_M"] = "2"
    assert "I_CONSTRAINED_M" in " ".join(reference.compatible(provenance, config, shared))
    provenance["input_tags"]["I_CONSTRAINED_M"] = "1"
    config["tags"]["RWIGS"] = "1.6 0.8"
    assert "RWIGS" in " ".join(reference.compatible(provenance, config, shared))


def test_import_paths_and_prewrite_failure_synthetic(tmp_path):
    run, shared, source, data, root = q0_run(tmp_path)
    plan = campaign.prepare(source)
    assert plan["reference"]["status"] == "verified-import"
    assert plan["cases"][1]["acceptance_requires"] == ["import:reference-q0"]
    assert reference.verify_files(root / "reference" / "references.json")[0] == {"M_int": [2, 2], "MW_int": [1.8, 1.8]}
    bare = tmp_path / "bare"
    bare.mkdir()
    manifest.save({"M_int": [2, 2], "MW_int": [1.8, 1.8]}, bare / "references.json")
    data["run_root"] = str(tmp_path / "bare-root")
    data["reference"]["path"] = str(bare / "references.json")
    manifest.save(data, source)
    with pytest.raises(ValueError, match="adjacent reference-provenance"):
        campaign.prepare(source)
    assert not (tmp_path / "bare-root").exists()
    data["reference"]["path"] = str(run)
    data["run_root"] = str(tmp_path / "import-run-root")
    manifest.save(data, source)
    assert campaign.prepare(source)["reference"]["status"] == "verified-import"
    data["run_root"] = str(tmp_path / "bad-root")
    (shared / "INCAR").write_text((shared / "INCAR").read_text().replace("ENCUT = 550", "ENCUT = 600"))
    manifest.save(data, source)
    with pytest.raises(ValueError, match="ENCUT"):
        campaign.prepare(source)
    assert not (tmp_path / "bad-root").exists()


def test_generated_cli_round_trip_and_finite_q_rejection(tmp_path):
    run, shared, source, data, root = q0_run(tmp_path)
    data["reference"] = {"mode": "generate"}
    manifest.save(data, source)
    result = run_cli("campaign-prepare", "--campaign", source)
    assert result.returncode == 0, result.stderr
    generated = root / "runs" / "reference-q0"
    (generated / "OUTCAR").write_text("vasp.test synthetic\n" + (generated / "INCAR").read_text() +
                                       "Iteration 1( 1)\naborting loop because EDIFF is reached\nGeneral timing and accounting\n")
    (generated / "OSZICAR").write_bytes((run / "OSZICAR").read_bytes())
    failed = run_cli("campaign-reference", "--root", root, "--run", root / "runs" / "plus")
    assert failed.returncode == 1 and "finite-q" in failed.stderr
    passed = run_cli("campaign-reference", "--root", root, "--run", generated,
                     "--config", generated / "config.json", "--output", root / "reference")
    assert passed.returncode == 0, passed.stderr
    assert "PASS" in passed.stdout
    assert manifest.load(root / "plan.json")["reference"]["status"] == "verified-generate"
    assert reference.verify_files(root / "reference" / "references.json")[0]["M_int"] == [2, 2]
