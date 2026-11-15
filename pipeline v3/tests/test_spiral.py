"""Seed, q plan, F0 inputs and readback: math Sections 3, 8 and plans/ten-03-spiral.md.

Synthetic files only. The BFO geometry is a test structure, not a relaxed one.
"""

from itertools import groupby
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


def material(tmp_path, seed=SEED, incar_text=INCAR, structure=None):
    """A material folder; BFO unless another (lattice, species, tau) is given."""
    folder = tmp_path / "bfo"
    folder.mkdir(exist_ok=True)
    lattice, species, tau = bfo() if structure is None else structure
    types = [(symbol, len(list(group))) for symbol, group in groupby(species)]
    text = "test\n1.0\n" + "".join(" ".join(f"{x:.12f}" for x in row) + "\n" for row in lattice)
    text += " ".join(s for s, _ in types) + "\n" + " ".join(str(n) for _, n in types) + "\nDirect\n"
    text += "".join(" ".join(f"{x:.6f}" for x in row) + "\n" for row in tau)
    (folder / "POSCAR").write_text(text)
    (folder / "INCAR").write_text(incar_text)
    (folder / "KPOINTS").write_text("mesh\n0\nGamma\n4 4 4\n0 0 0\n")
    (folder / "POTCAR").write_text("".join(f" VRHFIN ={s}: synthetic\n" for s, _ in types))
    (folder / "seed.toml").write_text(seed)
    (tmp_path / "job.sh").write_text(JOB)
    return folder / "seed.toml"


def test_seed_and_plan(tmp_path, capsys):
    path = material(tmp_path)
    assert main(["plan", str(path)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "space group 161 (R3c) at symprec 0.001: 6 operations, 6 kept, 0 dropped"
    assert lines[2] == "ENCUT 600  ENINI 500  ISMEAR 0  SIGMA 0.05"
    assert not any(line.startswith("override") for line in lines)

    # Section 8.2: the threefold relates BFO's three axes, so A has rank 1 of 2.
    def with_directions(rows):
        return spiral.load_seed(material(tmp_path, SEED + f"directions = {rows}\n"))
    with pytest.raises(ValueError, match="stiffness: rank value .* p_A = 2"):
        spiral.plan(with_directions([[1, 0, 0], [0, 1, 0], [0, 0, 1]]))
    good = spiral.plan(with_directions([[1, 1, 1], [1, -1, 0], [1, 0, 0]]))
    assert min(good["ranks"].values()) > spiral.RANK_FLOOR
    chosen = spiral.plan(spiral.load_seed(material(tmp_path)))
    assert min(chosen["ranks"].values()) > spiral.RANK_FLOOR and len(chosen["points"]) == 19
    # Two explicit directions: both designs have full rank, D_free does not (Section 9.4).
    two = spiral.plan(with_directions([[1, 1, 1], [1, -1, 0]]))
    assert two["ranks"]["D_free"] < spiral.RANK_FLOOR <= min(two["ranks"]["D"], two["ranks"]["A"])
    # An unsorted t list still names the smallest magnitude t1, where P0 and E0 gate.
    shuffled = spiral.plan(spiral.load_seed(material(tmp_path, SEED.replace("0.03, 0.06, 0.09", "0.09, 0.03, 0.06"))))
    lengths = {p["name"]: np.linalg.norm(2 * np.pi * np.linalg.solve(bfo()[0], p["q_frac"])) for p in shuffled["points"]}
    assert [lengths[f"d1_t{j}_plus"] for j in (1, 2, 3)] == pytest.approx([.03, .06, .09], rel=1e-10)

    for bad, message in [(SEED + "spacegroups = 161\n", "Unknown seed keys"),
                         (SEED + "exchange_grid = [2, 2, 2]\nrmax = 6.0\n", "Unknown seed keys"),
                         (SEED.replace("0.03, ", ""), "at least 3 distinct")]:
        with pytest.raises(ValueError, match=message):
            spiral.load_seed(material(tmp_path, bad))


def test_prepare_writes_paired_f0_inputs(tmp_path, capsys):
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

    # D-022: the code owns eleven tags and overrides the user's value with one line each.
    capsys.readouterr()
    material(tmp_path, incar_text="ISMEAR = 1\nMAGMOM = 10*0\nLSPIRAL = F\nKSPACING = 0.2\n")
    assert main(["prepare", str(path), "--job", str(tmp_path / "job.sh"), "--out", str(tmp_path / "over")]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert "override LSPIRAL: INCAR has F; using T" in lines and "ISMEAR 1" in lines
    assert "override MAGMOM: INCAR has 10*0; using the per-run value from the seed" in lines
    tags = incar(tmp_path / "over" / "d1_t1_plus" / "INCAR")
    assert tags["LSPIRAL"] == "T" and tags["KSPACING"] == "0.2" and tags["MAGMOM"] == incar(out / "d1_t1_plus" / "INCAR")["MAGMOM"]

    def rejected(message, incar_text=INCAR, job=JOB, potcar=None, target=None):
        material(tmp_path, incar_text=incar_text)
        (tmp_path / "job.sh").write_text(job)
        if potcar:
            (tmp_path / "bfo" / "POTCAR").write_text(potcar)
        with pytest.raises(ValueError, match=message):
            spiral.prepare(spiral.load_seed(path), target or tmp_path / "new", tmp_path / "job.sh")
    rejected("not empty", target=out)
    rejected(r"ISMEAR = -5 \(tetrahedron\) is refused: its energy is not variational", INCAR.replace("ISMEAR = 0", "ISMEAR = -5"))
    rejected("POTCAR elements", potcar=" VRHFIN =Fe:\n VRHFIN =Bi:\n VRHFIN =O:\n")
    rejected("must not cd", job=JOB + "cd scratch && srun vasp_ncl\n")
    rejected("already sets --array", job=JOB.replace("#SBATCH -N 1", "#SBATCH --array=1-4"))


def rot_z(degrees):
    turn = np.radians(degrees)
    return np.array([(np.cos(turn), -np.sin(turn), 0), (np.sin(turn), np.cos(turn), 0), (0, 0, 1)])


def finish(run, energy=-12.25, rotate_deg=37.0, reversed_site=False, twist_deg=0.0, scale=1.0, mz=0.0, mag=None):
    """A finished static run: two OSZICAR sphere tables, the last one final, and two TOTEN lines.

    The F= line carries mag= as VASP prints it; by default 1.1 times the summed M_int,
    standing in for the interstitial moment the spheres miss.
    """
    config = manifest.load(run / "config.json")
    moments = np.zeros((len(poscar(run / "POSCAR")[1]), 3))
    moments[config["sites"]] = 3.9 * scale * np.asarray(config["targets"]) @ rot_z(rotate_deg).T
    second = config["sites"][1]
    moments[second] = moments[second] @ rot_z(twist_deg).T * (-1 if reversed_site else 1)
    moments[config["sites"], 2] += mz
    def table(m):
        return "ion MW_int M_int\n" + "".join(
            f" {i + 1} " + " ".join(f"{v:.6f}" for v in (*0.9 * row, *row)) + "\n" for i, row in enumerate(m))
    mag = 1.1 * moments.sum(axis=0) if mag is None else np.asarray(mag)
    summary = "   1 F= -.12250000E+02 E0= -.12240000E+02  d E =-.282564E-02  mag=" + "".join(f"{x:11.4f}" for x in mag)
    (run / "OSZICAR").write_text(table(-moments) + "DAV: 1 -1\nRMM: 2 -1\n" + table(moments) + summary + "\n")
    (run / "OUTCAR").write_text("vasp.test synthetic\n" + (run / "INCAR").read_text() +
                                "  free  energy   TOTEN  =       -11.000000 eV\n"
                                f" free energy    TOTEN  =  {float(energy)!r} eV\n"
                                "aborting loop because EDIFF is reached\nGeneral timing and accounting\n")


def test_readback(tmp_path, capsys):
    path, out = material(tmp_path), tmp_path / "runs"
    spiral.prepare(spiral.load_seed(path), out, tmp_path / "job.sh")
    names = (out / "runs.txt").read_text().split()
    for name in names:
        finish(out / name, mag=(0.3, 0.4, 0.0) if name == "q0" else None)
    oszicar = out / "q0" / "OSZICAR"                       # an earlier F= line: mag= comes from the last one
    oszicar.write_text("   1 F= -.1E+02 E0= -.1E+02  d E =-.1E-02  mag=     9.0000     9.0000     9.0000\n"
                       + oszicar.read_text())
    assert main(["collect", str(out)]) == 0
    collected = manifest.load(out / "collected.json")      # M_total = |mag| / N_m, at q0 only
    assert collected["q0"]["M_total"] == pytest.approx(0.25) and collected["d1_t1_plus"]["M_total"] is None
    state = manifest.load(out / "collected.json")["d3_t1_minus"]           # the last sphere table, not the first
    assert state["E_eV"] == -12.25 and state["theta_deg"] == pytest.approx(37, abs=1e-4)
    assert state["delta_deg"] == pytest.approx([0, 0], abs=1e-4) and state["M"] == pytest.approx([3.9, 3.9])

    finish(out / names[1], reversed_site=True)
    for index, cut in ((3, "aborting loop because EDIFF is reached"), (4, "General timing and accounting")):
        outcar = out / names[index] / "OUTCAR"
        outcar.write_text(outcar.read_text().replace(cut, ""))
    (out / names[5] / "OSZICAR").write_text("ion MW_int M_int\n 1 0 0 0 1 0 0\n")
    (out / names[6] / "OUTCAR").unlink()
    oszicar = out / names[2] / "OSZICAR"                     # a constrained run: its energy holds a penalty
    oszicar.write_text(oszicar.read_text() + " E_p = 0.1E-02 lambda = 0.1E+02\n")
    finish(out / names[7], twist_deg=4.0)            # delta = +-2 deg with n_twist = 0
    finish(out / names[8], scale=1.1)                # M 10% above q0
    finish(out / names[9], mz=0.1)
    capsys.readouterr()
    assert main(["collect", str(out)]) == 1
    report = dict(line.split(None, 1) for line in capsys.readouterr().out.splitlines())
    assert "Site reversed: relative site phase 180.0" in report[names[1]]
    assert "did not reach EDIFF" in report[names[3]] and "no timing footer" in report[names[4]]
    assert "one row for each of the 10 ions" in report[names[5]]
    assert report[names[6]] == "missing" and report[names[0]] == "ok"
    assert "OSZICAR prints lambda = 0.1E+02, not 0" in report[names[2]]
    assert "|delta| = 2.00 deg >= 1.0 with n_twist = 0" in report[names[7]]
    assert "|M_a / M_a(q0) - 1| = 0.100" in report[names[8]] and "|M_z|" in report[names[9]]
