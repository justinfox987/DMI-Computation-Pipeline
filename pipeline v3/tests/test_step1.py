"""Offline software regression oracles; none represent production BFO acceptance."""

import subprocess
import sys

import numpy as np
import pytest

from dmi_pipeline import manifest, step1


FE_FREE = """ ion        MW_int                 M_int
  1  1.668 -0.696  0.000    2.073 -0.866  0.000
  2  1.668  0.696  0.000    2.073  0.866  0.000
  1 F= -.16440894E+02 E0= -.16439259E+02 d E =-.326940E-02 mag= 4.0418 -1.6742 0.0000
 E_p = 0.00000E+00 lambda = 0.000E+00
 ion             lambda*MW_perp
  1   0.00000E+00  -0.00000E+00   0.00000E+00
  2   0.00000E+00   0.00000E+00   0.00000E+00
"""
FE_CONSTRAINED = """ ion        MW_int                 M_int
  1  1.812 -0.044  0.000    2.259 -0.033  0.000
  2  1.812  0.044  0.000    2.259  0.033  0.000
  1 F= -.16380878E+02 E0= -.16379693E+02 d E =-.237054E-02 mag= 3.7810 -1.5662 0.0000
 E_p = 0.39240E-02 lambda = 0.100E+01
 ion             lambda*MW_perp
  1   0.00000E+00  -0.88590E-01   0.00000E+00
  2   0.00000E+00   0.88589E-01   0.00000E+00
"""


def poscar(path):
    path.write_text("test\n1\n1 0 0\n0 1 0\n0 0 1\nFe O\n2 1\nDirect\n0 0 0\n.5 .5 .5\n.2 .2 .2\n")
    return path


def recipe(family="F1", side="+", axis="z"):
    return {"id": "synthetic-" + side, "family": family, "side": side,
            "q_frac": [0.25, 0, 0], "axis": axis, "magnetic_indices": [0, 1],
            "signs": [1, -1], "angle_deg": None if family == "F0" else 30,
            "seed_magnitudes": [4, 4], "rwigs": [1.3, 0.8], "lambda": 0,
            "lzeroz": family == "F0", "f1_policy": "diagnostic"}


def run_cli(*arguments):
    return subprocess.run([sys.executable, "-B", "-m", "dmi_pipeline", *map(str, arguments)],
                          capture_output=True, text=True)


def test_target_numeric_and_partner_wrap(tmp_path):
    path = poscar(tmp_path / "POSCAR")
    expected = {"F0": [-0.7071067812, -0.7071067812, 0],
                "F1": [-0.2588190451, -0.9659258263, 0],
                "F2b": [-0.3535533906, -0.3535533906, -0.8660254038]}
    for family, direction in expected.items():
        plus = step1.prepare(recipe(family), path)
        assert plus["targets"][1] == pytest.approx(direction, abs=1e-9)
        minus = step1.prepare(recipe(family, "-"), path)
        assert minus["targets"] == pytest.approx(np.asarray(plus["targets"]) * [1, -1, 1])
        assert minus["tags"]["SAXIS"] == "0 0 1"
        assert minus["tags"]["M_CONSTR"] != plus["tags"]["M_CONSTR"]
    ferromagnetic = recipe("F0")
    ferromagnetic["signs"] = [1, 1]
    assert step1.prepare(ferromagnetic, path)["targets"][1] == pytest.approx([.7071067812, .7071067812, 0], abs=1e-9)
    x = step1.prepare(recipe(axis="x"), path)
    z = step1.prepare(recipe(), path)
    assert x["tags"] == z["tags"]
    q, reflected = step1.partner([.25, 0, 0], np.asarray(z["targets"]))
    assert q == pytest.approx([-.25, 0, 0])
    assert step1.coefficients(reflected, q + [1, 0, 0], "z", [{"a": 0, "b": 1, "R": [0, 0, 0], "p": [[0, 0, 1]]}], [0, 1]) == pytest.approx(step1.coefficients(reflected, q, "z", [{"a": 0, "b": 1, "R": [0, 0, 0], "p": [[0, 0, 1]]}], [0, 1]))
    assert step1.targets(path, [0, 1], [1, -1], q + [1, 0, 0], "F1", -30)[1] != pytest.approx(reflected[1])


def test_parser_excerpts_are_not_convergence_evidence(tmp_path):
    file = tmp_path / "OSZICAR"
    file.write_text(FE_FREE)
    free = step1.sphere(file, 2)
    assert free["M_int"][1] == [2.073, .866, 0]
    assert free["MW_int"][1] == [1.668, .696, 0]
    assert free["field_check"] == "available"
    file.write_text(FE_CONSTRAINED.replace("E+", "D+"))
    constrained = step1.sphere(file, 2)
    assert constrained["E_p_eV"] == pytest.approx(.003924)
    assert constrained["lambda"] == 1
    assert constrained["printed_field"][0][1] == pytest.approx(-.088590)
    assert sum(np.sum(np.square(ion)) for ion in constrained["printed_field"]) / 4 == pytest.approx(.00392405, rel=1e-4)
    with pytest.raises(ValueError, match="convergence"):
        step1.validate({"schema_version": 3, "convention": step1.CONVENTION}, free)
    for text, error in ((FE_FREE + "ion MW_int M_int\n1 0 0 0 0 0 0\n", "count mismatch"),
                        (FE_FREE.replace("  2  1.668", "  1  1.668"), "Duplicate"),
                        (FE_FREE.replace("2.073  0.866", "NaN  0.866"), "Nonfinite"),
                        (FE_FREE.replace("  2  1.668", "  2  1.668").replace("2.073  0.866  0.000", "2.073  0.866"), "Incomplete"),
                        (FE_FREE + "2 F= -1\n", "Ambiguous")):
        file.write_text(text)
        with pytest.raises(ValueError, match=error):
            step1.sphere(file, 2)
    file.write_text(FE_FREE + FE_CONSTRAINED)
    assert step1.sphere(file, 2)["lambda"] == 1
    for text in (FE_FREE + "ion MW_int M_int\n1 0 0 0 0 0 0\n",
                 FE_FREE + "2 F= -1\n"):
        file.write_text(text)
        with pytest.raises(ValueError):
            step1.sphere(file, 2)


def test_signed_gates_and_weighted_distinction(tmp_path):
    path = poscar(tmp_path / "POSCAR")
    config = step1.prepare(recipe("F0"), path)
    config["targets"] = [[1, 0, 0], [-1, 0, 0], [0, 0, 0]]
    read = {"M_int": [[2, 0, 0], [-2, 0, 0], [0, 0, 0]],
            "MW_int": [[1.8, 0, 0], [-1.8, 0, 0], [0, 0, 0]],
            "E_p_eV": 0, "lambda": 0, "source": "OSZICAR",
            "provenance": {"outcar_final_ediff": True}, "printed_field": None}
    assert step1.validate(config, read, [2, 2], [1.8, 1.8])["passed"]
    anti = dict(read, M_int=[[-2, 0, 0], [-2, 0, 0], [0, 0, 0]])
    assert not step1.validate(config, anti, [2, 2], [1.8, 1.8])["passed"]
    assert "missing" in str(step1.validate(config, read)["reasons"])
    rotated = dict(read, M_int=[[2 * np.cos(.2), 2 * np.sin(.2), 0], [-2 * np.cos(.2), -2 * np.sin(.2), 0], [0, 0, 0]],
                   MW_int=[[1.8 * np.cos(.2), 1.8 * np.sin(.2), 0], [-1.8 * np.cos(.2), -1.8 * np.sin(.2), 0], [0, 0, 0]])
    assert not step1.validate(config, rotated, [2, 2], [1.8, 1.8])["passed"]
    allowed = step1.validate(config, rotated, [2, 2], [1.8, 1.8], True)
    assert "full geometry" not in str(allowed["reasons"])
    assert "absolute weighted" in str(allowed["reasons"])
    scattered = dict(rotated, M_int=[rotated["M_int"][0], [-2 * np.cos(.3), -2 * np.sin(.3), 0], [0, 0, 0]])
    assert not step1.validate(config, scattered, [2, 2], [1.8, 1.8], True)["passed"]
    near = dict(read, M_int=[[2, 0, 0], [0, 0, -2], [0, 0, 0]])
    assert not step1.validate(config, near, [2, 2], [1.8, 1.8])["passed"]
    tiny = dict(read, M_int=[[0, 0, 0], [-2, 0, 0], [0, 0, 0]])
    assert not step1.validate(config, tiny, [2, 2], [1.8, 1.8])["passed"]
    weighted_bad = dict(read, MW_int=[[1.8, .06, 0], [-1.8, 0, 0], [0, 0, 0]])
    assert "weighted" in str(step1.validate(config, weighted_bad, [2, 2], [1.8, 1.8])["reasons"])
    nonaxial = dict(read, M_int=[[2, 0, 0], [0, .002, -2], [0, 0, 0]],
                    MW_int=[[1.8, 0, 0], [0, .002, -1.8], [0, 0, 0]])
    config["targets"][1] = [0, -.001, -np.sqrt(1 - .000001)]
    gated = step1.validate(config, nonaxial, [2, 2], [1.8, 1.8])
    assert "transverse phase" in str(gated["reasons"])
    assert "ion 2 signed full geometry" not in gated["reasons"]
    (tmp_path / "FE").write_text(FE_CONSTRAINED)
    fe = step1.sphere(tmp_path / "FE", 2)
    fe["provenance"] = {"outcar_final_ediff": True}
    fe_config = dict(config, targets=[[1, 0, 0], [1, 0, 0]])
    fe_gate = step1.validate(fe_config, fe, fe["M_norm"], fe["MW_norm"])
    assert not fe_gate["passed"]
    assert fe_gate["field_check"]["printed_factor"] == pytest.approx(2, abs=.02)
    assert "printed constraint penalty exceeds threshold" in fe_gate["reasons"]
    assert "ion 1 absolute weighted alignment" in fe_gate["reasons"]


def test_canonical_kernel_oracles():
    basis = [{"a": 0, "b": 1, "R": [0, 0, 0], "p": [[0, 0, .001]]}]
    plus = [[1, 0, 0], [-np.sqrt(3) / 2, -.5, 0]]
    minus = [[1, 0, 0], [-np.sqrt(3) / 2, .5, 0]]
    assert step1.coefficients(plus, [.25, 0, 0], "z", basis, [0, 1])[0] == pytest.approx(-.0005)
    assert (step1.coefficients(plus, [.25, 0, 0], "z", basis, [0, 1])[0] -
            step1.coefficients(minus, [-.25, 0, 0], "z", basis, [0, 1])[0]) / 2 == pytest.approx(-.0005)
    basis[0]["R"] = [1, 0, 0]
    assert step1.coefficients(plus, [.25, 0, 0], "z", basis, [0, 1])[0] == pytest.approx(-np.sqrt(3) * .0005)
    basis[0]["a"], basis[0]["b"], basis[0]["R"] = 1, 0, [-1, 0, 0]
    assert step1.coefficients(plus, [.25, 0, 0], "z", basis, [0, 1])[0] == pytest.approx(np.sqrt(3) * .0005)
    basis[0]["R"] = [0, 0, 0]
    assert step1.coefficients([[0, 0, 1], plus[1]], [.25, 0, 0], "z", basis, [0, 1])[0] == 0
    with pytest.raises(ValueError, match="integer"):
        step1.coefficients(plus, [.25, 0, 0], "z", [dict(basis[0], R=[.5, 0, 0])], [0, 1])
    basis[0].update(a=0, b=1, R=[1, 0, 0])
    assert step1.coefficients(plus, [1.25, 0, 0], "z", basis, [0, 1]) == pytest.approx(
        step1.coefficients(plus, [.25, 0, 0], "z", basis, [0, 1]))
    angle = .39
    spun = [step1.rotate_z(s, angle) for s in plus]
    assert step1.coefficients(spun, [.25, 0, 0], "z", basis, [0, 1]) == pytest.approx(
        step1.coefficients(plus, [.25, 0, 0], "z", basis, [0, 1]))
    cone = [[.6, 0, .8], [-.6, 0, -.8]]
    average = 0
    for cell in range(4):
        left = step1.rotate_z(cone[0], 2 * np.pi * cell / 4)
        right = step1.rotate_z(cone[1], 2 * np.pi * (cell + 1) / 4)
        average += np.cross(left, right)[2] / 4
    assert step1.coefficients(cone, [.25, 0, 0], "z", basis, [0, 1])[0] == pytest.approx(
        average * .001)


def test_cli_synthetic_chain_and_rejections(tmp_path):
    pos = poscar(tmp_path / "POSCAR")
    configs = []
    states = []
    for side in ("+", "-"):
        recipe_path = tmp_path / (side + "-recipe.json")
        manifest.save(recipe(side=side), recipe_path)
        dest = tmp_path / (side + "-targets")
        result = run_cli("step1-prepare", "--recipe", recipe_path, "--poscar", pos, "--output", dest)
        assert result.returncode == 0, result.stderr
        cfg = manifest.load(dest / "config.json")
        configs.append(cfg)
        run = tmp_path / (side + "-run")
        run.mkdir()
        (run / "POSCAR").write_bytes(pos.read_bytes())
        (run / "INCAR").write_bytes((dest / "INCAR.step1").read_bytes())
        (run / "OUTCAR").write_text("vasp.test synthetic\n" + (run / "INCAR").read_text() +
                                    "Iteration 1( 1)\naborting loop because EDIFF is reached\nGeneral timing and accounting\n")
        if side == "+":
            with pytest.raises(FileNotFoundError):
                step1.read_state(run, cfg)  # OUTCAR never replaces missing sphere evidence.
        ion_lines = []
        for i, u in enumerate(cfg["targets"]):
            mw = np.asarray(u) * (1.8 if i < 2 else 0)
            m = np.asarray(u) * (2 if i < 2 else 0)
            ion_lines.append(f" {i + 1} " + " ".join(f"{v:.10f}" for v in [*mw, *m]))
        (run / "OSZICAR").write_text(" ion MW_int M_int\n" + "\n".join(ion_lines) + "\n 1 F= -1 E0= -1\n E_p = 0.0E+00 lambda = 0.0E+00\n")
        if side == "+":
            outcar = run / "OUTCAR"
            original = outcar.read_text()
            outcar.write_text(original.replace("aborting loop because EDIFF is reached", "NELM exhausted"))
            with pytest.raises(ValueError, match="EDIFF"):
                step1.read_state(run, cfg)
            outcar.write_text(original.replace("M_CONSTR = ", "M_CONSTR = 0 "))
            with pytest.raises(ValueError, match="echo|M_CONSTR"):
                step1.read_state(run, cfg)
            outcar.write_text(original)
        reference = tmp_path / "reference.json"
        manifest.save({"M_int": [2, 2], "MW_int": [1.8, 1.8]}, reference)
        state = tmp_path / (side + "-state.json")
        result = run_cli("step1-read", "--config", dest / "config.json", "--run", run,
                         "--references", reference, "--output", state)
        assert result.returncode == 0, result.stderr
        states.append(state)
    bonds = tmp_path / "basis.json"
    manifest.save({"source": "synthetic supplied basis; not BFO", "bonds": [{"a": 0, "b": 1, "R": [0, 0, 0], "p": [[0, 0, 1]]}]}, bonds)
    trace = tmp_path / "trace.json"
    manifest.save({"source": "synthetic independent trace and uncertainty", "axis": "z",
                   "plus_eV": -.0005, "minus_eV": .0005, "sigma_y_eV_per_site": 1e-5}, trace)
    output = tmp_path / "row.json"
    result = run_cli("step1-row", "--plus", states[0], "--minus", states[1], "--basis", bonds,
                     "--traces", trace, "--output", output)
    assert result.returncode == 0, result.stderr
    row = manifest.load(output)
    assert row["status"].startswith("diagnostic")
    assert row["y_eV_per_site"] == pytest.approx(-.0005)
    neg = manifest.load(states[1])
    neg["gate"]["spins"][1] = step1.rotate_z(neg["gate"]["spins"][1], np.deg2rad(.2)).tolist()
    altered = step1.paired(manifest.load(states[0]), neg, manifest.load(bonds)["bonds"], -.0005, .0005, 1e-5)
    assert altered["row"] != pytest.approx(row["row"])
    rows = tmp_path / "rows.json"
    manifest.save({"rows": [row]}, rows)
    fit = tmp_path / "fit.json"
    assert run_cli("step1-fit", "--rows", rows, "--output", fit).returncode == 0
    assert "numerical diagnostic only" in manifest.load(fit)["status"]
    assert run_cli("step1-row", "--plus", states[0], "--minus", states[0], "--basis", bonds,
                   "--traces", trace, "--output", output).returncode != 0
    wrong = dict(manifest.load(trace), axis="x")
    manifest.save(wrong, trace)
    assert run_cli("step1-row", "--plus", states[0], "--minus", states[1], "--basis", bonds,
                   "--traces", trace, "--output", output).returncode != 0
    row["sigma_y_eV_per_site"] = None
    manifest.save({"rows": [row]}, rows)
    assert run_cli("step1-fit", "--rows", rows, "--output", fit).returncode != 0
    legacy = manifest.load(states[0]); legacy["config"]["schema_version"] = 2
    manifest.save(legacy, states[0])
    assert run_cli("step1-row", "--plus", states[0], "--minus", states[1], "--basis", bonds,
                   "--traces", trace, "--output", output).returncode != 0
