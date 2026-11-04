"""F0 targets, the command line and the OSZICAR/OUTCAR readers. Synthetic files only."""

import numpy as np
import pytest

from dmi_pipeline import manifest, step1
from dmi_pipeline.__main__ import main
from dmi_pipeline.realized import incar


def poscar(path):
    path.write_text("test\n1\n1 0 0\n0 1 0\n0 0 1\nFe O\n2 1\nDirect\n0 0 0\n.5 .5 .5\n.2 .2 .2\n")
    return path


def recipe(side="+"):
    return {"id": "synthetic-" + side, "family": "F0", "side": side, "q_frac": [0.25, 0, 0],
            "axis": "z", "magnetic_indices": [0, 1], "signs": [1, -1], "seed_magnitudes": [4, 4],
            "rwigs": [1.3, 0.8], "lambda": 0, "lzeroz": True}


def complete_run(directory, config):
    """Write the OUTCAR and OSZICAR of a converged run with moments on target."""
    (directory / "OUTCAR").write_text("vasp.test synthetic\n" + (directory / "INCAR").read_text() +
        "Iteration 1( 1)\naborting loop because EDIFF is reached\nGeneral timing and accounting\n")
    rows = [f" {i + 1} " + " ".join(f"{v:.10f}" for v in [*(1.8 * np.array(u)), *(2 * np.array(u))])
            for i, u in enumerate(config["targets"])]
    (directory / "OSZICAR").write_text(" DAV: 1 -1\n ion MW_int M_int\n" + "\n".join(rows) +
        "\n 1 F= -1 E0= -1\n E_p = 0.0E+00 lambda = 0.0E+00\n")


def prepared_run(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir()
    poscar(shared / "POSCAR")
    (shared / "INCAR").write_text("ENCUT = 550\nISTART = 0\nMAGMOM = 9 9 9\nLSPIRAL = False\n")
    (shared / "KPOINTS").write_bytes(b"test\n0\nGamma\n5 5 5\n0 0 0\n")
    (shared / "POTCAR").write_bytes(b"synthetic potential; not VASP data\n")
    recipe_path = tmp_path / "recipe.json"
    manifest.save(recipe(), recipe_path)
    run = tmp_path / "run"
    assert main(["step1-prepare", "--recipe", str(recipe_path), "--inputs", str(shared),
                 "--output", str(run)]) == 0
    return run


def test_f0_targets_and_partner(tmp_path):
    path = poscar(tmp_path / "POSCAR")
    plus = step1.prepare(recipe(), path)
    assert plus["targets"][1] == pytest.approx([-0.7071067812, -0.7071067812, 0], abs=1e-9)
    minus = step1.prepare(recipe("-"), path)
    assert minus["q_frac"] == pytest.approx([-.25, 0, 0])
    assert minus["targets"] == pytest.approx(np.asarray(plus["targets"]) * [1, -1, 1])


def test_prepare_and_read_through_the_command_line(tmp_path):
    run = prepared_run(tmp_path)
    config = manifest.load(run / "config.json")
    tags = incar(run / "INCAR")
    assert all(tags[key] == value for key, value in config["tags"].items())
    assert tags["ENCUT"] == "550" and tags["LSPIRAL"] == "T"
    complete_run(run, config)
    references = tmp_path / "references.json"
    manifest.save({"M_int": [2, 2], "MW_int": [1.8, 1.8]}, references)
    state = tmp_path / "state.json"
    assert main(["step1-read", "--config", str(run / "config.json"), "--run", str(run),
                 "--references", str(references), "--output", str(state)]) == 0
    assert manifest.load(state)["gate"]["passed"]


def test_real_oszicar_format_uses_the_terminal_table(tmp_path):
    """VASP repeats sphere tables and mixes solvers; the last table belongs to the final step."""
    run = prepared_run(tmp_path)
    config = manifest.load(run / "config.json")
    complete_run(run, config)
    original = (run / "OSZICAR").read_text()
    table = original.split(" ion MW_int M_int\n")[1].split("\n 1 F=")[0]
    earlier = " E_p = 0.0E+00 lambda = 0.0E+00\n DBL = 0\n ion MW_int M_int\n" + table + "\n"
    solvers = "DAV: 1 -1\nDAV: 2 -1\nSDA: 3 -1\n" + "".join(f"CGA: {i} -1\n" for i in range(4, 51))
    (run / "OSZICAR").write_text(earlier + solvers + "ion MW_int M_int\n" + table + "\n" +
                                 original[original.index(" 1 F="):])
    outcar = (run / "OUTCAR").read_text()
    (run / "OUTCAR").write_text(outcar.replace(
        "Iteration 1( 1)", "".join(f"Iteration 1( {i})\n" for i in range(1, 51))))
    checked = step1.check_run(run, 3)
    assert checked["outcar"]["final_step"] == [1, 50]
    assert checked["sphere"]["M_int"] == pytest.approx(2 * np.asarray(config["targets"]))


def test_unconverged_or_mismatched_runs_are_rejected(tmp_path):
    run = prepared_run(tmp_path)
    complete_run(run, manifest.load(run / "config.json"))
    outcar, oszicar = (run / "OUTCAR").read_text(), (run / "OSZICAR").read_text()
    bad_runs = {
        "did not reach EDIFF": (outcar.replace("aborting loop because EDIFF is reached", "NELM"), oszicar),
        "cannot be associated": (outcar.replace("General timing",
            "Iteration 2( 1)\naborting loop because EDIFF is reached\nGeneral timing"), oszicar),
        "count mismatch": (outcar, oszicar + " DAV: 1 -1\n ion MW_int M_int\n 1 0 0 0 0 0 0\n"),
        "ambiguous completed OUTCAR": (outcar + outcar, oszicar),
    }
    for message, (bad_outcar, bad_oszicar) in bad_runs.items():
        (run / "OUTCAR").write_text(bad_outcar)
        (run / "OSZICAR").write_text(bad_oszicar)
        with pytest.raises(ValueError, match=message):
            step1.check_run(run, 3)
