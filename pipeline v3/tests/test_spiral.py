"""Seed, q plan, F0 inputs and readback: math Sections 3, 8 and plans/ten-03-spiral.md.

Synthetic files only. The BFO geometry is a test structure, not a relaxed one.
"""

import subprocess

import numpy as np
import pytest

from dmi_pipeline import manifest, spiral
from dmi_pipeline.__main__ import main
from dmi_pipeline.realized import incar, numbers, poscar
from tests.fixtures import bfo

INCAR = "ENCUT = 600\nENINI = 500\nISMEAR = 0\nSIGMA = 0.05\nRWIGS = 1.6 1.2 0.8\n"
JOB = "#!/bin/bash\n#SBATCH -N 1\n#SBATCH -t 00:30:00\n\nmodule load vasp\nsrun vasp_ncl\n"
SEED = "sites = [3, 4]\nsigns = [1, -1]\nmoments = [4.0, 4.0]\nt = [0.03, 0.06, 0.09]\nspacegroup = 161\n"


def material(tmp_path, seed=SEED, incar_text=INCAR):
    folder = tmp_path / "bfo"
    folder.mkdir(exist_ok=True)
    lattice, species, tau = bfo()
    text = "BFO\n1.0\n" + "".join(" ".join(f"{x:.12f}" for x in row) + "\n" for row in lattice)
    text += "Bi Fe O\n2 2 6\nDirect\n" + "".join(" ".join(f"{x:.6f}" for x in row) + "\n" for row in tau)
    (folder / "POSCAR").write_text(text)
    (folder / "INCAR").write_text(incar_text)
    (folder / "KPOINTS").write_text("mesh\n0\nGamma\n4 4 4\n0 0 0\n")
    (folder / "POTCAR").write_text("".join(f" VRHFIN ={x}: synthetic\n" for x in ("Bi", "Fe", "O")))
    (folder / "seed.toml").write_text(seed)
    (tmp_path / "job.sh").write_text(JOB)
    return folder / "seed.toml"


def test_seed_and_plan(tmp_path, capsys):
    path = material(tmp_path)
    assert main(["plan", str(path)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "space group 161 (R3c) at symprec 0.001: 6 operations, 6 kept, 0 dropped"
    assert lines[2] == "ENCUT 600  ENINI 500"

    # Section 8.2: the threefold relates BFO's three axes, so A has rank 1 of 2.
    def with_directions(rows):
        return spiral.load_seed(material(tmp_path, SEED + f"directions = {rows}\n"))
    with pytest.raises(ValueError, match="stiffness: sigma_A = .* p_A = 2"):
        spiral.plan(with_directions([[1, 0, 0], [0, 1, 0], [0, 0, 1]]))
    good = spiral.plan(with_directions([[1, 1, 1], [1, -1, 0], [1, 0, 0]]))
    assert (good["sigma_D"], good["sigma_A"]) == pytest.approx((.344, .929), abs=1e-3)
    chosen = spiral.plan(spiral.load_seed(material(tmp_path)))
    assert min(chosen["sigma_D"], chosen["sigma_A"]) >= .9 and len(chosen["points"]) == 19

    for bad, message in [(SEED + "spacegroups = 161\n", "Unknown seed keys"),
                         (SEED.replace("0.03, ", ""), "at least 3 distinct")]:
        with pytest.raises(ValueError, match=message):
            spiral.load_seed(material(tmp_path, bad))


def test_prepare_writes_paired_f0_inputs(tmp_path):
    path, out = material(tmp_path), tmp_path / "runs"
    assert main(["prepare", str(path), "--job", str(tmp_path / "job.sh"), "--out", str(out)]) == 0
    names = (out / "runs.txt").read_text().split()
    assert len(names) == 2 * 3 * 3 + 1 and names[0] == "q0"

    _, _, tau = poscar(path.parent / "POSCAR")          # as written: Fe 2 at x - 1/2
    assert tau[3, 0] < 0
    for name in names:
        tags, config = incar(out / name / "INCAR"), manifest.load(out / name / "config.json")
        q = numbers(tags["QSPIRAL"])
        t = 0 if name == "q0" else [.03, .06, .09][int(name.split("_t")[1][0]) - 1]
        assert np.linalg.norm(2 * np.pi * np.linalg.solve(bfo()[0], q)) == pytest.approx(t, rel=1e-10)
        phi = 2 * np.pi * tau[[2, 3]] @ q             # Eq (3.1) from the written QSPIRAL
        expected = np.array([1, -1])[:, None] * np.column_stack([np.cos(phi), np.sin(phi), 0 * phi])
        lab = numbers(tags["M_CONSTR"]).reshape(-1, 3)
        assert np.allclose(lab[[2, 3]], expected, atol=1e-11) and not lab[[0, 1, 4]].any()
        assert np.allclose(numbers(tags["MAGMOM"]).reshape(-1, 3), 4 * lab, atol=1e-10)
        assert tags["LSPIRAL"] == "T" and tags["LAMBDA"] == "0" and tags["ENCUT"] == "600"
        assert config["q_frac"] == pytest.approx(q.tolist(), abs=0)
    assert incar(out / "q0" / "INCAR")["QSPIRAL"] == "0 0 0"
    plus, minus = (manifest.load(out / f"d1_t2_{side}" / "config.json") for side in ("plus", "minus"))
    assert np.allclose(minus["q_frac"], -np.asarray(plus["q_frac"]), atol=0)
    assert np.allclose(minus["targets"], np.asarray(plus["targets"]) * [1, -1, 1], atol=1e-11)

    submit = (out / "submit.sh").read_text()
    assert f"#SBATCH --array=1-{len(names)}\n" in submit and submit.index("#SBATCH -t") < submit.index("cd ")
    assert subprocess.run(["bash", "-n", str(out / "submit.sh")]).returncode == 0

    def rejected(message, incar_text=INCAR, job=JOB, potcar=None, target=None):
        material(tmp_path, incar_text=incar_text)
        (tmp_path / "job.sh").write_text(job)
        if potcar:
            (tmp_path / "bfo" / "POTCAR").write_text(potcar)
        with pytest.raises(ValueError, match=message):
            spiral.prepare(spiral.load_seed(path), target or tmp_path / "new", tmp_path / "job.sh")
    rejected("not empty", target=out)
    rejected("ISYM = 2", INCAR + "ISYM = 2\n")
    rejected("sets MAGMOM", INCAR + "MAGMOM = 10*0\n")
    rejected("Unreviewed INCAR tags", INCAR + "LSORBT = F\n")
    rejected("RWIGS", INCAR.replace("RWIGS = 1.6 1.2 0.8", "RWIGS = 1.6 1.6 1.2 1.2 .8 .8 .8 .8 .8 .8"))
    rejected("needs ENINI", INCAR.replace("ENINI = 500\n", ""))
    rejected("POTCAR elements", potcar=" VRHFIN =Fe:\n VRHFIN =Bi:\n VRHFIN =O:\n")
    rejected("must not cd", job=JOB + "cd scratch && srun vasp_ncl\n")
    rejected("already sets --array", job=JOB.replace("#SBATCH -N 1", "#SBATCH --array=1-4"))


def finish(run, energy=-12.25, rotate_deg=37.0, reversed_site=False):
    """Converged OUTCAR and OSZICAR with repeated sphere tables and mixed solvers."""
    config = manifest.load(run / "config.json")
    turn = np.radians(rotate_deg)
    rotation = np.array([(np.cos(turn), -np.sin(turn), 0), (np.sin(turn), np.cos(turn), 0), (0, 0, 1)])
    moments = np.zeros((10, 3))
    moments[config["sites"]] = 3.9 * np.asarray(config["targets"]) @ rotation.T
    if reversed_site:
        moments[config["sites"][1]] *= -1
    table = "ion MW_int M_int\n" + "".join(
        f" {i + 1} " + " ".join(f"{v:.6f}" for v in (*0.9 * m, *m)) + "\n" for i, m in enumerate(moments))
    solvers = "DAV: 1 -1\nDAV: 2 -1\nSDA: 3 -1\n" + "".join(f"CGA: {i} -1\n" for i in range(4, 51))
    (run / "OSZICAR").write_text(table + " E_p = 0.0E+00 lambda = 0.0E+00\n" + solvers +
                                 table + " 1 F= -1 E0= -1\n E_p = 0.0E+00 lambda = 0.0E+00\n")
    iterations = "".join(f"Iteration 1( {i})\n" for i in range(1, 51))
    (run / "OUTCAR").write_text("vasp.test synthetic\n" + (run / "INCAR").read_text() + iterations +
                                "  free  energy   TOTEN  =       -11.000000 eV\n"
                                f" free energy    TOTEN  =  {energy:.6f} eV\n"
                                "aborting loop because EDIFF is reached\nGeneral timing and accounting\n")


def test_readback(tmp_path, capsys):
    path, out = material(tmp_path), tmp_path / "runs"
    spiral.prepare(spiral.load_seed(path), out, tmp_path / "job.sh")
    names = (out / "runs.txt").read_text().split()
    for name in names:
        finish(out / name)
    assert main(["collect", str(out)]) == 0
    state = manifest.load(out / "collected.json")["d3_t1_minus"]
    assert state["E_eV"] == -12.25 and state["theta_deg"] == pytest.approx(37, abs=1e-4)
    assert state["delta_deg"] == pytest.approx([0, 0], abs=1e-4) and state["M"] == pytest.approx([3.9, 3.9])

    finish(out / names[1], reversed_site=True)
    bad = {3: lambda text: text.replace("aborting loop because EDIFF is reached", "NELM"),
           4: lambda text: text.replace("General timing",
                                        "Iteration 2( 1)\naborting loop because EDIFF is reached\nGeneral timing"),
           5: lambda text: text + text}
    for index, change in bad.items():
        outcar = out / names[index] / "OUTCAR"
        outcar.write_text(change(outcar.read_text()))
    (out / names[6] / "OUTCAR").unlink()
    capsys.readouterr()
    assert main(["collect", str(out)]) == 1
    report = dict(line.split(None, 1) for line in capsys.readouterr().out.splitlines())
    assert "Site reversed: relative site phase 180.0" in report[names[1]]
    assert "did not reach EDIFF" in report[names[3]]
    assert "cannot be associated" in report[names[4]] and "ambiguous completed OUTCAR" in report[names[5]]
    assert report[names[6]] == "missing" and report[names[0]] == "ok"
