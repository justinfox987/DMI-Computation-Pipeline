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
    wrapped = step1.wrap_partner(step1.prepare(recipe(side="-"), path), [.75, 0, 0])
    assert wrapped["targets"] == pytest.approx(reflected)
    assert wrapped["q_frac"] == pytest.approx([.75, 0, 0])
    assert wrapped["tags"]["M_CONSTR"] == step1.prepare(recipe(side="-"), path)["tags"]["M_CONSTR"]
    with pytest.raises(ValueError, match="integer"):
        step1.wrap_partner(wrapped, [.76, 0, 0])
    bad_recipe = recipe(side="-")
    bad_recipe["partner_q_frac"] = [.75, 0, 0]
    with pytest.raises(ValueError, match="cannot regenerate"):
        step1.prepare(bad_recipe, path)


def synthetic_readback(tmp_path, config, moments, weighted, ep=0, lam=0, field=None,
                       electronic=1, ionic=1, mw_digits=9):
    """Synthetic, explicitly indexed SCF files for readback/gate tests only."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = poscar(tmp_path / "POSCAR")
    config["poscar_sha256"] = manifest.file_hash(source)
    config["tags"]["M_CONSTR"] = " ".join(str(x) for row in config["targets"] for x in row)
    config["tags"]["LAMBDA"] = str(lam)
    config_path = tmp_path / "config.json"
    manifest.save(config, config_path)
    (tmp_path / "INCAR").write_text("".join(f"{k} = {v}\n" for k, v in config["tags"].items()))
    (tmp_path / "OUTCAR").write_text("vasp.test synthetic\n" + (tmp_path / "INCAR").read_text() +
        f"Iteration {electronic}( {ionic})\naborting loop because EDIFF is reached\nGeneral timing and accounting\n")
    rows = [f" {i + 1} " + " ".join(f"{v:.{mw_digits}f}" for v in w) +
            " " + " ".join(f"{v:.9f}" for v in m)
            for i, (w, m) in enumerate(zip(weighted, moments))]
    text = "".join(f" DAV: {i}  -1\n" for i in range(1, electronic + 1))
    text += " ion MW_int M_int\n" + "\n".join(rows) + f"\n {ionic} F= -1 E0= -1\n"
    text += f" E_p = {ep:.8E} lambda = {lam:.8E}\n"
    if field is not None:
        text += " ion lambda*MW_perp\n"
        text += "".join(f" {i + 1} " + " ".join(f"{v:.9E}" for v in values) + "\n"
                        for i, values in enumerate(field))
    (tmp_path / "OSZICAR").write_text(text)
    return step1.read_state(tmp_path, config, config_path)


def test_parser_excerpts_are_not_convergence_evidence(tmp_path):
    file = tmp_path / "OSZICAR"
    file.write_text(FE_FREE)
    with pytest.raises(ValueError, match="electronic loop"):
        step1.sphere(file, 2)  # The supplied excerpt has no electronic iteration IDs.
    file.write_text(" DAV: 1 -1\n" + FE_FREE)
    free = step1.sphere(file, 2)
    assert free["M_int"][1] == [2.073, .866, 0]
    assert free["MW_int"][1] == [1.668, .696, 0]
    assert free["printed_field"] is not None
    file.write_text(" DAV: 1 -1\n" + FE_CONSTRAINED.replace("E+", "D+"))
    constrained = step1.sphere(file, 2)
    assert constrained["E_p_eV"] == pytest.approx(.003924)
    assert constrained["lambda"] == 1
    assert constrained["printed_field"][0][1] == pytest.approx(-.088590)
    assert sum(np.sum(np.square(ion)) for ion in constrained["printed_field"]) / 4 == pytest.approx(.00392405, rel=1e-4)
    with pytest.raises(ValueError, match="provenance"):
        step1.validate({"schema_version": 3, "convention": step1.CONVENTION}, free)
    for text, error in ((FE_FREE + "ion MW_int M_int\n1 0 0 0 0 0 0\n", "count mismatch"),
                        (FE_FREE.replace("  2  1.668", "  1  1.668"), "Duplicate"),
                        (FE_FREE.replace("2.073  0.866", "NaN  0.866"), "Nonfinite"),
                        (FE_FREE.replace("2.073  0.866  0.000", "2.073  0.866"), "Incomplete"),
                        (FE_FREE + "2 F= -1\n", "Ambiguous")):
        file.write_text(text)
        with pytest.raises(ValueError, match=error):
            step1.sphere(file, 2)
    file.write_text(" DAV: 1 -1\n" + FE_FREE + " DAV: 1 -1\n" + FE_CONSTRAINED)
    with pytest.raises(ValueError, match="restart|missing|ambiguous"):
        step1.sphere(file, 2)
    for text in (FE_FREE + "ion MW_int M_int\n1 0 0 0 0 0 0\n",
                 FE_FREE + "2 F= -1\n"):
        file.write_text(text)
        with pytest.raises(ValueError):
            step1.sphere(file, 2)


def test_signed_gates_and_weighted_distinction(tmp_path):
    path = poscar(tmp_path / "POSCAR")
    config = step1.prepare(recipe("F0"), path)
    config["targets"] = [[1, 0, 0], [-1, 0, 0], [0, 0, 0]]
    m = [[2, 0, 0], [-2, 0, 0], [0, 0, 0]]
    mw = [[1.8, 0, 0], [-1.8, 0, 0], [0, 0, 0]]
    read = synthetic_readback(tmp_path / "base", config, m, mw)
    assert step1.validate(config, read, [2, 2], [1.8, 1.8])["passed"]
    anti = synthetic_readback(tmp_path / "anti", config, [[-2, 0, 0], m[1], m[2]], mw)
    assert not step1.validate(config, anti, [2, 2], [1.8, 1.8])["passed"]
    assert "missing" in str(step1.validate(config, read)["reasons"])
    rotated_m = [[2 * np.cos(.2), 2 * np.sin(.2), 0], [-2 * np.cos(.2), -2 * np.sin(.2), 0], [0, 0, 0]]
    rotated_w = [[1.8 * np.cos(.2), 1.8 * np.sin(.2), 0], [-1.8 * np.cos(.2), -1.8 * np.sin(.2), 0], [0, 0, 0]]
    rotated = synthetic_readback(tmp_path / "rotated", config, rotated_m, rotated_w)
    assert not step1.validate(config, rotated, [2, 2], [1.8, 1.8])["passed"]
    allowed = step1.validate(config, rotated, [2, 2], [1.8, 1.8], True)
    assert "full geometry" not in str(allowed["reasons"])
    assert "absolute weighted" in str(allowed["reasons"])
    scattered = synthetic_readback(tmp_path / "scattered", config,
                                   [rotated_m[0], [-2 * np.cos(.3), -2 * np.sin(.3), 0], m[2]], rotated_w)
    assert not step1.validate(config, scattered, [2, 2], [1.8, 1.8], True)["passed"]
    near = synthetic_readback(tmp_path / "near", config, [m[0], [0, 0, -2], m[2]], mw)
    assert not step1.validate(config, near, [2, 2], [1.8, 1.8])["passed"]
    tiny = synthetic_readback(tmp_path / "tiny", config, [[0, 0, 0], m[1], m[2]], mw)
    assert not step1.validate(config, tiny, [2, 2], [1.8, 1.8])["passed"]
    weighted_bad = synthetic_readback(tmp_path / "weighted", config, m, [[1.8, .06, 0], mw[1], mw[2]])
    assert "weighted" in str(step1.validate(config, weighted_bad, [2, 2], [1.8, 1.8])["reasons"])
    config["targets"][1] = [0, -.001, -np.sqrt(1 - .000001)]
    nonaxial = synthetic_readback(tmp_path / "nonaxial", config,
        [[2, 0, 0], [0, .002, -2], [0, 0, 0]], [[1.8, 0, 0], [0, .002, -1.8], [0, 0, 0]])
    gated = step1.validate(config, nonaxial, [2, 2], [1.8, 1.8])
    assert "transverse phase" in str(gated["reasons"])
    assert "ion 2 signed full geometry" not in gated["reasons"]
    fe_config = dict(config, targets=[[1, 0, 0], [1, 0, 0], [0, 0, 0]])
    fe = synthetic_readback(tmp_path / "fe", fe_config,
        [[2.259, -.033, 0], [2.259, .033, 0], [0, 0, 0]],
        [[1.812, -.044, 0], [1.812, .044, 0], [0, 0, 0]], .003924, 1,
        [[0, -.088590, 0], [0, .088589, 0], [0, 0, 0]], mw_digits=3)
    fe_oszicar = tmp_path / "fe" / "OSZICAR"
    fe_oszicar.write_text(fe_oszicar.read_text().replace(
        "E_p = 3.92400000E-03 lambda = 1.00000000E+00",
        "E_p = 0.39240E-02 lambda = 0.100E+01"))
    fe = step1.read_state(tmp_path / "fe", fe_config, tmp_path / "fe" / "config.json")
    fe_gate = step1.validate(fe_config, fe, fe["M_norm"][:2], fe["MW_norm"][:2])
    assert not fe_gate["passed"]
    assert fe_gate["field_check"]["printed_factor"] == pytest.approx(2, abs=.02)
    assert "printed constraint penalty exceeds threshold" in fe_gate["reasons"]
    assert "ion 1 absolute weighted alignment" in fe_gate["reasons"]
    assert fe_gate["penalty_check"].startswith("pass")
    assert fe_gate["field_check"]["status"].startswith("pass")


def test_penalty_field_precision_and_absent_field(tmp_path):
    config = step1.prepare(recipe("F0"), poscar(tmp_path / "POSCAR"))
    targets = np.asarray(config["targets"])
    m = 2 * targets
    mw = 1.8 * targets
    good = synthetic_readback(tmp_path / "good", config, m, mw, lam=1, field=np.zeros_like(mw))
    gate = step1.validate(config, good, [2, 2], [1.8, 1.8])
    assert gate["passed"] and gate["penalty_check"].startswith("pass")
    assert gate["field_check"]["status"].startswith("pass")
    no_field = synthetic_readback(tmp_path / "absent", config, m, mw, lam=1)
    assert step1.validate(config, no_field, [2, 2], [1.8, 1.8])["field_check"]["status"].startswith("unavailable")
    bad_penalty = synthetic_readback(tmp_path / "penalty", config, m, mw, ep=.0005, lam=1)
    penalty_gate = step1.validate(config, bad_penalty, [2, 2], [1.8, 1.8])
    assert not penalty_gate["passed"] and penalty_gate["penalty_check"].startswith("fail")
    bad_field = synthetic_readback(tmp_path / "field", config, m, mw, lam=1,
                                   field=[[0, .02, 0], [0, 0, 0], [0, 0, 0]])
    field_gate = step1.validate(config, bad_field, [2, 2], [1.8, 1.8])
    assert not field_gate["passed"] and field_gate["field_check"]["status"].startswith("fail")
    negative = synthetic_readback(tmp_path / "negative", config, m, mw, lam=1,
                                  field=[[0, -.02, 0], [0, 0, 0], [0, 0, 0]])
    assert not step1.validate(config, negative, [2, 2], [1.8, 1.8])["passed"]
    small_mw = 1.8 * targets
    small_mw[0, 1] = .004
    small = synthetic_readback(tmp_path / "small", config, m, small_mw, ep=.000016, lam=1,
                               field=[[0, .008, 0], [0, 0, 0], [0, 0, 0]])
    assert step1.validate(config, small, [2, 2], [1.8, 1.8])["passed"]


def test_final_loop_association_and_stale_evidence(tmp_path):
    config = step1.prepare(recipe("F0"), poscar(tmp_path / "POSCAR"))
    m = 2 * np.asarray(config["targets"])
    mw = .9 * m
    run = tmp_path / "run"
    synthetic_readback(run, config, m, mw)
    outcar, oszicar = run / "OUTCAR", run / "OSZICAR"
    clean_outcar, clean_oszicar = outcar.read_text(), oszicar.read_text()
    # Two electronic loops with the same terminal ionic ID are not a proven match.
    outcar.write_text(clean_outcar.replace("aborting loop because EDIFF is reached",
                     "aborting loop because EDIFF is reached\nIteration 1( 1)\naborting loop because EDIFF is reached"))
    with pytest.raises(ValueError, match="restart|association|loop"):
        step1.read_state(run, config, run / "config.json")
    outcar.write_text(clean_outcar.replace("aborting loop because EDIFF is reached",
                                  "aborting loop because EDIFF is reached\nIteration 1( 2)"))
    with pytest.raises(ValueError, match="EDIFF"):
        step1.read_state(run, config, run / "config.json")
    outcar.write_text(clean_outcar)
    oszicar.write_text(clean_oszicar + " DAV: 1 -1\n ion MW_int M_int\n 1 0 0 0 0 0 0\n")
    with pytest.raises(ValueError, match="count mismatch"):
        step1.read_state(run, config, run / "config.json")
    oszicar.write_text(clean_oszicar.replace(" 1 F=", " 2 F="))
    with pytest.raises(ValueError, match="restart|missing|associate"):
        step1.read_state(run, config, run / "config.json")
    oszicar.write_text(clean_oszicar)
    outcar.write_text(clean_outcar.replace("General timing and accounting",
                      "Iteration 1( 2)\naborting loop because EDIFF is reached\nGeneral timing and accounting"))
    oszicar.write_text(clean_oszicar.replace(" 1 F=", " 2 F="))
    with pytest.raises(ValueError, match="restart|missing|associate"):
        step1.read_state(run, config, run / "config.json")
    outcar.write_text(clean_outcar.replace("General timing and accounting",
                     "Iteration 1( 2)\naborting loop because EDIFF is reached\nGeneral timing and accounting"))
    oszicar.write_text(clean_oszicar + clean_oszicar.replace(" 1 F=", " 2 F="))
    # A complete ordered two-step record is distinguishable by the ionic IDs.
    assert step1.read_state(run, config, run / "config.json")["ionic_steps"] == [1, 2]
    oszicar.write_text(clean_oszicar + clean_oszicar)
    with pytest.raises(ValueError, match="restart|missing|associate"):
        step1.read_state(run, config, run / "config.json")


def test_pair_common_rotation_only_in_validation(tmp_path):
    basis = [{"a": 0, "b": 1, "R": [0, 0, 0], "p": [[0, 0, 1]]}]
    states = []
    for side in ("+", "-"):
        folder = tmp_path / side
        config = step1.prepare(recipe(side=side), poscar(tmp_path / "POSCAR"))
        raw = np.asarray(config["targets"])
        spins = np.asarray([step1.rotate_z(s, .008 if side == "+" else .012) for s in raw])
        m, mw = 2 * spins, 1.8 * spins
        read = synthetic_readback(folder, config, m, mw)
        gate = step1.validate(config, read, [2, 2], [1.8, 1.8], common_z=True)
        assert gate["passed"], gate["reasons"]
        states.append({"config": config, "readback": read, "gate": gate})
    row = step1.paired(*states, basis, -.0005, .0005)
    # A relative-site or antiparallel solution cannot be absorbed by one offset.
    raw_minus = np.asarray(states[1]["readback"]["M_int"])
    for index, replacement in ((1, step1.rotate_z(raw_minus[1], .08)),
                               (0, -raw_minus[0])):
        folder = tmp_path / ("wrong-" + str(index))
        modified = raw_minus.copy()
        modified[index] = replacement
        read = synthetic_readback(folder, dict(states[1]["config"]), modified,
                                  states[1]["readback"]["MW_int"])
        gate = step1.validate(states[1]["config"], read, [2, 2], [1.8, 1.8], common_z=True)
        assert not gate["passed"]
    assert row["row"] == pytest.approx(((step1.coefficients(states[0]["gate"]["spins"],
        states[0]["config"]["q_frac"], "z", basis, [0, 1]) -
        step1.coefficients(states[1]["gate"]["spins"], states[1]["config"]["q_frac"], "z", basis, [0, 1])) / 2))
    bad = states[1]["readback"]["M_int"]
    bad[1] = step1.rotate_z(bad[1], .08).tolist()
    with pytest.raises(ValueError, match="readback"):
        step1.paired(*states, basis, -.0005, .0005)
    assert row["status"].startswith("diagnostic")


def test_pair_rejects_relative_phase_even_if_each_state_passes(tmp_path):
    states = []
    for side in ("+", "-"):
        cfg = step1.prepare(recipe(side=side), poscar(tmp_path / "POSCAR"))
        degrees = [0.8, -0.8] if side == "+" else [0.8, -0.8]
        spins = np.asarray(cfg["targets"]).copy()
        for ion, angle in enumerate(degrees):
            spins[ion] = step1.rotate_z(spins[ion], np.deg2rad(angle))
        read = synthetic_readback(tmp_path / ("pair-" + side), cfg, 2 * spins, 1.8 * spins)
        gate = step1.validate(cfg, read, [2, 2], [1.8, 1.8], common_z=True)
        assert gate["passed"], gate["reasons"]
        states.append({"config": cfg, "readback": read, "gate": gate})
    with pytest.raises(ValueError, match="Partner measured"):
        step1.paired(*states, [{"a": 0, "b": 1, "R": [0, 0, 0], "p": [[0, 0, 1]]}], 0, 0)


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
        if side == "-":
            wrapped = tmp_path / "wrapped-targets"
            wrap = run_cli("step1-wrap-partner", "--config", dest / "config.json",
                           "--q-frac", .75, 0, 0, "--output", wrapped)
            assert wrap.returncode == 0, wrap.stderr
            wrapped_cfg = manifest.load(wrapped / "config.json")
            assert np.asarray(wrapped_cfg["targets"]) == pytest.approx(np.asarray(cfg["targets"]))
            assert wrapped_cfg["tags"]["M_CONSTR"] == cfg["tags"]["M_CONSTR"]
            assert wrapped_cfg["q_frac"] == pytest.approx([.75, 0, 0])
            dest, cfg = wrapped, wrapped_cfg
        configs.append(cfg)
        run = tmp_path / (side + "-run")
        run.mkdir()
        (run / "POSCAR").write_bytes(pos.read_bytes())
        (run / "INCAR").write_bytes((dest / "INCAR.step1").read_bytes())
        (run / "OUTCAR").write_text("vasp.test synthetic\n" + (run / "INCAR").read_text() +
                                    "Iteration 1( 1)\naborting loop because EDIFF is reached\nGeneral timing and accounting\n")
        if side == "+":
            with pytest.raises(FileNotFoundError):
                step1.read_state(run, cfg, dest / "config.json")  # OUTCAR never replaces missing sphere evidence.
        ion_lines = []
        for i, u in enumerate(cfg["targets"]):
            mw = np.asarray(u) * (1.8 if i < 2 else 0)
            m = np.asarray(u) * (2 if i < 2 else 0)
            ion_lines.append(f" {i + 1} " + " ".join(f"{v:.10f}" for v in [*mw, *m]))
        (run / "OSZICAR").write_text(" DAV: 1 -1\n ion MW_int M_int\n" + "\n".join(ion_lines) + "\n 1 F= -1 E0= -1\n E_p = 0.0E+00 lambda = 0.0E+00\n")
        if side == "+":
            outcar = run / "OUTCAR"
            original = outcar.read_text()
            outcar.write_text(original.replace("aborting loop because EDIFF is reached", "NELM exhausted"))
            with pytest.raises(ValueError, match="EDIFF"):
                step1.read_state(run, cfg, dest / "config.json")
            outcar.write_text(original.replace("M_CONSTR = ", "M_CONSTR = 0 "))
            with pytest.raises(ValueError, match="echo|M_CONSTR"):
                step1.read_state(run, cfg, dest / "config.json")
            outcar.write_text(original)
        if side == "+":
            changed = dict(cfg, q_frac=[.26, 0, 0])
            manifest.save(changed, dest / "config.json")
            q_mismatch = run_cli("step1-read", "--config", dest / "config.json", "--run", run,
                                 "--references", tmp_path / "missing.json", "--output", tmp_path / "invalid.json")
            assert q_mismatch.returncode != 0 and "QSPIRAL" in q_mismatch.stderr
            manifest.save(cfg, dest / "config.json")
            changed = dict(cfg, tags=dict(cfg["tags"], QSPIRAL="0.26 0 0"))
            manifest.save(changed, dest / "config.json")
            q_mismatch = run_cli("step1-read", "--config", dest / "config.json", "--run", run,
                                 "--references", tmp_path / "missing.json", "--output", tmp_path / "invalid.json")
            assert q_mismatch.returncode != 0 and "QSPIRAL" in q_mismatch.stderr
            manifest.save(cfg, dest / "config.json")
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
    plus_original = manifest.load(states[0])
    forged = dict(plus_original, gate=dict(plus_original["gate"], passed=True))
    forged["gate"]["spins"] = [[-1, 0, 0], [-1, 0, 0], [0, 0, 0]]
    manifest.save(forged, states[0])
    assert run_cli("step1-row", "--plus", states[0], "--minus", states[1], "--basis", bonds,
                   "--traces", trace, "--output", output).returncode != 0
    manifest.save(plus_original, states[0])
    neg = manifest.load(states[1])
    neg["gate"]["spins"][1] = step1.rotate_z(neg["gate"]["spins"][1], np.deg2rad(.2)).tolist()
    manifest.save(neg, states[1])
    assert run_cli("step1-row", "--plus", states[0], "--minus", states[1], "--basis", bonds,
                   "--traces", trace, "--output", output).returncode != 0
    original_state = manifest.load(states[1])
    original_state["gate"] = step1.validate(configs[1], original_state["readback"], [2, 2], [1.8, 1.8])
    manifest.save(original_state, states[1])
    original_oszicar = (tmp_path / "+-run" / "OSZICAR").read_text()
    (tmp_path / "+-run" / "OSZICAR").write_text(original_oszicar.replace("2.0000000000", "1.0000000000"))
    assert run_cli("step1-row", "--plus", states[0], "--minus", states[1], "--basis", bonds,
                   "--traces", trace, "--output", output).returncode != 0
    (tmp_path / "+-run" / "OSZICAR").write_text(original_oszicar)
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
