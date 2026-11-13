"""Tensors, fits and predictions: math Sections 6, 9 and 10 and plans/ten-05-tensors.md.

The spin model of Section 6 is the oracle: its D and A come from Eq (6.3), its
y and g from Eq (6.2), independent of the fit code.
"""

import os
import subprocess

import numpy as np
import pytest

from dmi_pipeline import manifest, spiral, symmetry, tensors
from dmi_pipeline.__main__ import main
from dmi_pipeline.dumpio import load_cso
from dmi_pipeline.gates import gate_forbidden
from dmi_pipeline.realized import incar
from dmi_pipeline.trace import split_operator
from tests.fixtures import bfo, make_clean_cso, write_cocc, write_cso
from tests.test_spiral import SEED, finish, material
from tests.test_symmetry import fege


def spin_model(rotations, seeds, n_m):
    """Bonds closed under the kept operations (r -> R r, d -> det(R) R d); Eqs (6.2) and (6.3)."""
    bonds = [(R @ r, np.linalg.det(R) * R @ d, j, eps) for r, d, j, eps in seeds for R in rotations]
    r, d, coupling, eps = (np.array(column, float) for column in zip(*bonds))
    big_d = np.einsum("b,bi,bj->ij", eps, d, r) / n_m
    big_a = np.einsum("b,b,bi,bj->ij", eps, coupling, r, r) / (2 * n_m)

    def per_cell(q):
        """T(q) per cell (odd) and E(q) - E(0) per cell (even), so that Eqs (1.3)-(1.4) give Eq (6.2)."""
        phase = r @ q
        y = 2 / n_m * np.einsum("b,bi,b->i", eps, d, np.sin(phase))
        return n_m * y / 2, np.sum(eps * coupling * (1 - np.cos(phase)))
    return big_d, big_a, per_cell


MODELS = {  # structure, magnetic sites, signs, seed bonds (r in Å, d and J in eV, eps)
    "FeGe": (fege(), list(range(4)), [1] * 4,
             [((2.0, 0.7, -1.1), (3e-4, -2e-4, 5e-4), 0.01, 1)]),
    "BFO": (bfo(), [2, 3], [1, -1],
            [((1.9, -0.6, 1.2), (2e-4, 4e-4, -1e-4), 0.008, 1), ((3.1, 1.4, -0.3), (-1e-4, 3e-4, 2e-4), -0.004, -1)]),
}


def model_fit(name, t, noise=0.0, rng=None):
    """Spin-model pairs along the default directions, fitted by tensors.fit_pairs."""
    structure, sites, signs, seeds = MODELS[name]
    ops = symmetry.operations(*structure, sites, signs)
    d_basis, a_basis = symmetry.spiralization_basis(ops["rotations"]), symmetry.stiffness_basis(ops["rotations"])
    big_d, big_a, per_cell = spin_model(ops["rotations"], seeds, len(sites))
    lattice, species = structure[0], structure[1]
    s = spiral.unit_directions(lattice, spiral.choose_directions(lattice, d_basis, a_basis))
    share = np.linspace(1, 2, len(species)) / np.linspace(1, 2, len(species)).sum()   # T split over ions
    pairs = []
    for i, s_i in enumerate(s):
        for t_j in t:
            (t_plus, e_plus), (t_minus, e_minus) = per_cell(t_j * s_i), per_cell(-t_j * s_i)
            if noise:
                t_plus, t_minus = t_plus + rng.normal(0, noise, 3), t_minus + rng.normal(0, noise, 3)
                e_plus, e_minus = e_plus + rng.normal(0, noise), e_minus + rng.normal(0, noise)
            pairs.append({"i": i, "t": t_j, "E_plus": e_plus, "E_minus": e_minus, "T_plus": t_plus,
                          "T_minus": t_minus, "per_ion": share[:, None] * (t_plus - t_minus)})
    fit = lambda p: tensors.fit_pairs(s, p, len(sites), 0.0, d_basis, a_basis, species)   # noqa: E731
    return big_d, big_a, fit(pairs), fit, pairs, s


def test_fits_recover_spin_model_tensors():
    """Gate 1: Eq (6.3) tensors come back through Eqs (1.3), (1.4) and the single solves of Section 9.4."""
    def forbidden(r):
        return gate_forbidden(r["F"]["tensor"], np.sqrt(np.diag(r["F"]["cov"])).reshape(3, 3), r["D_free"]["tensor"])
    for name in MODELS:
        big_d, big_a, r, fit, pairs, s = model_fit(name, [0.005, 0.01, 0.015])
        assert np.abs(big_d).max() > 1e-5 and np.abs(big_a).max() > 1e-3
        for tensor, exact in ((r["D_free"], big_d), (r["D"], big_d), (r["A"], big_a)):
            assert tensor["tensor"] == pytest.approx(exact, abs=1e-6 * np.abs(exact).max())
        # Noise-free pairs give sigma = 0; the 1% floor covers the t^5 truncation (D-023).
        assert np.abs(r["F"]["tensor"]).max() < 1e-6 * np.abs(big_d).max() and forbidden(r).passed
        for key in ("D", "D_free"):
            assert sum(v[key] for v in r["by_species"].values()) == pytest.approx(r[key]["tensor"], abs=1e-15)

    # Noise-free BFO (3m) with a forbidden part added to y: 0.05 |D| is an error the check must
    # catch; 0.005 |D| is within the truncation floor. diag(1, 0, 0) has no projection on the
    # 3m form D [z]x, so all of it is forbidden.
    for size, caught in ((0.05, True), (0.005, False)):
        extra = size * np.abs(big_d).max() * np.diag([1.0, 0, 0])
        # Odd in q like a real term, so the parity residuals stay zero: y += 2 t F s with N_m = 2.
        tainted = [dict(p, T_plus=p["T_plus"] + 2 * p["t"] * extra @ s[p["i"]],
                        T_minus=p["T_minus"] - 2 * p["t"] * extra @ s[p["i"]]) for p in pairs]
        bad = fit(tainted)
        assert bad["F"]["tensor"] == pytest.approx(extra, abs=1e-6 * np.abs(big_d).max())
        assert forbidden(bad).passed is not caught

    # Real magnitudes with noise of known sigma: the parity residuals measure it (Eq 9.9), the
    # covariances cover the truth, and the forbidden part is within 3 sigma.
    noise, n_m = 2e-6, 2
    big_d, big_a, r, *_ = model_fit("BFO", [0.03, 0.06, 0.09], noise, np.random.default_rng(5))
    assert r["noise"]["n_y"] == 27 and 0.5 < r["noise"]["sigma_y"] / (np.sqrt(2) * noise / n_m) < 2
    for tensor, exact in ((r["D"], big_d), (r["A"], big_a)):
        assert np.all(np.abs(tensor["tensor"] - exact) <= 3 * np.sqrt(np.diag(tensor["cov"])).reshape(3, 3) + 1e-12)
    assert forbidden(r).passed
    # Calibration of Eq (9.9): over repeated noise draws the spread of D and A matches the reported sigma.
    _, _, _, fit, exact, _ = model_fit("BFO", [0.03, 0.06, 0.09])
    rng, draws = np.random.default_rng(7), []
    for _ in range(40):
        noisy = [dict(p, T_plus=p["T_plus"] + rng.normal(0, noise, 3), T_minus=p["T_minus"] + rng.normal(0, noise, 3),
                      E_plus=p["E_plus"] + rng.normal(0, noise), E_minus=p["E_minus"] + rng.normal(0, noise)) for p in exact]
        result = fit(noisy)
        draws.append([result["D"]["coef"][0], result["A"]["coef"][0], np.sqrt(result["D"]["cov_coef"][0, 0]),
                      np.sqrt(result["A"]["cov_coef"][0, 0])])
    draws = np.array(draws)
    assert 0.6 < draws[:, 0].std() / draws[:, 2].mean() < 1.6 and 0.6 < draws[:, 1].std() / draws[:, 3].mean() < 1.6


def test_predictions():
    """Section 10.1's three cases and the propagated pitch uncertainty."""
    d0, a0 = 2e-3, 0.05
    scalar = tensors.predict(d0 * np.eye(3), a0 * np.eye(3))
    assert scalar["pitch_A"] == pytest.approx(4 * np.pi * a0 / d0) and scalar["e_star"] == pytest.approx(-d0 ** 2 / (4 * a0))
    assert scalar["degeneracy"] == 3
    q_hat = scalar["q_star"] / np.linalg.norm(scalar["q_star"])
    assert abs(q_hat @ np.linalg.eigh(scalar["Gamma"])[1][:, -1]) == pytest.approx(1)   # Bloch helix: q* || n*

    z_cross = np.array([(0, -1, 0), (1, 0, 0), (0, 0, 0)], float)
    polar = tensors.predict(d0 * z_cross, np.diag([a0, a0, 3 * a0]))
    assert polar["degeneracy"] == 2 and np.allclose(polar["n_star"][:, 2], 0)
    assert polar["pitch_A"] == pytest.approx(4 * np.pi * a0 / d0)

    j, d, a = 0.010, 0.001, 3.0                                   # the Section 6 chain
    chain_d = np.zeros((3, 3))
    chain_d[2, 0] = d * a
    chain = tensors.predict(chain_d, np.diag([j * a * a / 2, 1, 1]))
    assert chain["pitch_A"] / 10 == pytest.approx(18.85, abs=0.005)
    assert chain["q_star"][0] == pytest.approx(-d / (j * a))

    basis = [z_cross / np.sqrt(2)]
    a_basis = [np.diag([1., 1, 0]) / np.sqrt(2), np.diag([0., 0, 1])]
    d_coeff, a_coeff = np.array([d0 * np.sqrt(2)]), np.array([a0 * np.sqrt(2), 3 * a0])
    small = tensors.prediction_uncertainty(d_coeff, np.diag([(0.05 * d_coeff[0]) ** 2]), basis,
                                           a_coeff, np.diag((0.01 * a_coeff) ** 2), a_basis)
    # pitch = 4 pi A_perp / |D|: 5% on D and 1% on A_perp add in quadrature.
    assert small["pitch_A"] == pytest.approx(np.hypot(0.05, 0.01) * 4 * np.pi * a0 / d0, rel=1e-6)

    a_matrix = np.diag([a0, a0, 3 * a0])
    assert tensors.spin_wave_stiffness(a_matrix, np.zeros((9, 9)), 2.2, [1, 1])[0] == pytest.approx(4 * a_matrix / 2.2)
    assert tensors.spin_wave_stiffness(a_matrix, np.zeros((9, 9)), 2.2, [1, -1])[0] is None


def test_command_chain(tmp_path, capsys):
    """prepare, collect, dumps and fit on a BFO tree whose VASP files hold spin-model values.

    OUTCAR energies and COCC traces reproduce Eq (6.2), so fit must return the Eq (6.3)
    tensors; fit reads only these files (D-021).
    """
    path, out, job = material(tmp_path, SEED.replace("0.03, 0.06, 0.09", "0.005, 0.01, 0.015")), tmp_path / "runs", tmp_path / "job.sh"
    assert main(["prepare", str(path), "--job", str(job), "--out", str(out)]) == 0
    structure, sites, signs, seeds = MODELS["BFO"]
    big_d, big_a, per_cell = spin_model(symmetry.operations(*structure, sites, signs)["rotations"], seeds, 2)
    lattice, names = bfo()[0], spiral.run_names(out)
    cells = {name: per_cell(spiral.cartesian(lattice, manifest.load(out / name / "config.json")["q_frac"])[0])
             for name in names}
    for name in names:
        finish(out / name, energy=-50.0 + cells[name][1])
        for big in ("WAVECAR", "CHGCAR"):
            (out / name / big).write_bytes(b"synthetic " + name.encode())
    assert main(["collect", str(out)]) == 0
    assert main(["dumps", str(out), "--job", str(job)]) == 0

    # Section 5 decks: one z-axis CSO dump from q0's CHGCAR, and a COCC-only dump_P per run.
    assert (out / "dumps.txt").read_text().split() == ["dump_C"] + [f"{n}/dump_P" for n in names]
    assert subprocess.run(["bash", "-n", str(out / "submit_dumps.sh")]).returncode == 0
    tags = incar(out / "dump_C" / "INCAR")
    assert (tags["LSORBIT"], tags["ISTART"], tags["ICHARG"], tags["SAXIS"]) == ("T", "0", "11", "0 0 1")
    assert not set(tags) & set(spiral.SPIRAL_ONLY) and tags["MAGMOM"] == incar(out / "q0" / "INCAR")["MAGMOM"]
    assert os.readlink(out / "dump_C" / "CHGCAR") == "../q0/CHGCAR" and not (out / "dump_C" / "WAVECAR").exists()
    for name in ("q0", "d2_t1_minus"):
        tags = incar(out / name / "dump_P" / "INCAR")
        assert (tags["ISTART"], tags["ICHARG"], tags["LDUMPCOCC"]) == ("1", "11", "T") and "LDUMPCPROJ" not in tags
        assert tags["QSPIRAL"] == incar(out / name / "INCAR")["QSPIRAL"]
        assert os.readlink(out / name / "dump_P" / "WAVECAR") == "../WAVECAR"

    # Dump outputs. Per ion, COCC_uu - COCC_dd = sum_b c_b Lambda_b, with c chosen so
    # that the trace gives 0.7 and 0.3 of the spin-model T(q) on the two Fe ions.
    cso = make_clean_cso(10, 3)
    write_cso(out / "dump_C" / "CSO.dat", cso)
    lam = split_operator(load_cso(out / "dump_C" / "CSO.dat"))
    for name in names:
        cocc = np.zeros((4, 10, 3, 3), complex)
        for ion, share in ((2, 0.7), (3, 0.3)):
            gram = np.einsum("aij,bij->ab", lam[:, ion], lam[:, ion].conj()).real
            m = np.einsum("b,bij->ij", np.linalg.solve(gram, share * cells[name][0]), lam[:, ion])
            cocc[0, ion], cocc[3, ion] = m / 2, -m / 2
        write_cocc(out / name / "dump_P" / "COCC.dat", cocc, nelect=8.0)

    capsys.readouterr()
    assert main(["fit", str(out)]) == 0
    report = manifest.load(out / "tensors.json")
    assert report["N_m"] == 2 and np.allclose(report["D"]["value"], 1e3 * big_d, atol=1e-6 * 1e3 * np.abs(big_d).max())
    assert np.allclose(report["A"]["value"], 1e3 * big_a, atol=1e-6 * 1e3 * np.abs(big_a).max())
    volume = abs(np.linalg.det(lattice)) / 2
    assert report["V_m_A3"] == pytest.approx(volume)
    assert np.allclose(report["micromagnetic"]["D_mJ_per_m2"], 1e3 * big_d / volume * 16.02, rtol=1e-6, atol=1e-12)
    assert np.allclose(report["micromagnetic"]["A_pJ_per_m"], 1e3 * big_a / volume * 1.602, rtol=1e-6, atol=1e-12)
    assert np.allclose(report["D_by_species"]["Fe"]["D"], report["D"]["value"], atol=1e-12)
    assert report["sign"] == "follows VASP's SOC energy (D-020); not yet confirmed by a VASP run"
    assert report["D_sw"]["M_int"]["value"] is None and report["D_sw"]["M_total"]["value"] is None   # not a ferromagnet
    assert report["noise"]["sigma_y"] == 0 and report["noise"]["n_g"] == 9
    assert report["null"]["passed"] is None and "not applicable" in report["null"]["detail"]           # R3c: no inversion
    assert report["F"]["passed"] and report["F"]["ratio_to_D_free"] < 1e-6 and "noise only" in report["F"]["bound"]
    assert report["prediction"]["pitch_nm"] > 0 and report["prediction"]["degeneracy"] == 2
    traces = manifest.load(out / "traces.json")
    assert traces["passed"] and traces["checks"]["C0"]["passed"] and traces["checks"]["N0"]["passed"]
    assert all(g["passed"] for name in ("P0", "E0") for g in traces["checks"][name].values())

    def refused(*messages):
        capsys.readouterr()
        assert main(["fit", str(out)]) == 1
        output = capsys.readouterr().out
        assert all(message in output for message in messages), output

    # The one guard: a COCC.dat older than its parent OUTCAR belongs to an earlier state.
    cocc_path, outcar = out / "d2_t3_minus" / "dump_P" / "COCC.dat", out / "d2_t3_minus" / "OUTCAR"
    stamp = os.stat(outcar).st_mtime_ns
    os.utime(cocc_path, ns=(stamp - 10**9, stamp - 10**9))
    refused("d2_t3_minus", "older than the run's OUTCAR", "fit refused")
    os.utime(cocc_path, ns=(stamp + 10**9, stamp + 10**9))
    # Exchanged flip blocks keep C0's Hermiticity but reverse the handedness (Section 4.2).
    write_cso(out / "dump_C" / "CSO.dat", cso[[0, 2, 1, 3]])
    refused("C0  FAIL", "handedness h >= 0", "fit refused: failed C0")
    assert manifest.load(out / "tensors.json") == {"passed": False, "failures": ["C0"]}   # no stale result
    write_cso(out / "dump_C" / "CSO.dat", cso)
    # A run that collect rejects leaves d1 with 2 complete pairs; the single solve still uses them.
    finish(out / "d1_t2_plus", energy=-50.0 + cells["d1_t2_plus"][1], reversed_site=True)
    assert main(["fit", str(out)]) == 0
    report = manifest.load(out / "tensors.json")
    assert report["directions"][0]["t"] == [0.005, 0.015]
    assert np.allclose(report["D"]["value"], 1e3 * big_d, atol=1e-6 * 1e3 * np.abs(big_d).max())
    # d1 left with one magnitude is dropped; the remaining two directions still determine D and
    # A, but not D_free, so F is not evaluated rather than passed (Section 9.4).
    finish(out / "d1_t3_plus", energy=-50.0 + cells["d1_t3_plus"][1], reversed_site=True)
    capsys.readouterr()
    assert main(["fit", str(out)]) == 0
    report = manifest.load(out / "tensors.json")
    assert report["dropped_directions"] == ["d1"] and report["F"]["passed"] is None
    assert report["D_free"].startswith("not evaluated")
    assert np.allclose(report["D"]["value"], 1e3 * big_d, atol=1e-6 * 1e3 * np.abs(big_d).max())


def test_bcc_fe_pilot_tree(tmp_path, capsys):
    """The TEN-06 shape on bcc Fe (Im-3m, p_A = 1, inversion kept), one explicit direction.

    Before any dump the tree is energies-only (item 2.10): A and both D_sw values, D_free
    not determined, every trace quantity not evaluated. With dumps, the centrosymmetric
    null (Sections 7.3 and 11) passes at T = 0 and fails when one run's T exceeds the floor.
    """
    a = 2.86304
    structure = (a * np.eye(3), ["Fe", "Fe"], np.array([(0, 0, 0), (0.5, 0.5, 0.5)]))
    rotations = symmetry.operations(*structure, [0, 1], [1, 1])["rotations"]
    _, big_a, per_cell = spin_model(rotations, [((a / 2, a / 2, a / 2), (0, 0, 0), 0.02, 1)], 2)
    seed = "sites = [1, 2]\nsigns = [1, 1]\nmoments = [2.2, 2.2]\nt = [0.05, 0.10, 0.15]\nspacegroup = 229\n" \
           "directions = [[0, 0, 1]]\n"
    path, out, job = material(tmp_path, seed, "ISMEAR = 0\nSIGMA = 0.05\n", structure), tmp_path / "runs", tmp_path / "job.sh"
    assert main(["prepare", str(path), "--job", str(job), "--out", str(out)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[:2] == ["space group 229 (Im-3m) at symprec 0.001: 96 operations, 96 kept, 0 dropped",
                         "p_D 0  p_A 1  n_twist 0"]
    assert "D_free is not determined: the forbidden part will not be evaluated" in lines
    for name in spiral.run_names(out):
        q = spiral.cartesian(structure[0], manifest.load(out / name / "config.json")["q_frac"])[0]
        finish(out / name, energy=-50.0 + per_cell(q)[1])
        for big in ("WAVECAR", "CHGCAR"):
            (out / name / big).write_bytes(b"synthetic")
    assert main(["fit", str(out)]) == 0
    report = manifest.load(out / "tensors.json")
    assert np.allclose(report["A"]["value"], 1e3 * big_a, atol=1e-6 * 1e3 * np.abs(big_a).max())
    a_xx = report["A"]["value"][0][0]
    # 4A/M side by side: M_int = 3.9 from the sphere rows, M_total = 1.1 x 3.9 from mag= (fixture);
    # tolerances are the fixture's printed precision (6 and 4 decimals).
    assert report["D_sw"]["M_int"]["value"][0][0] == pytest.approx(4 * a_xx / 3.9, rel=1e-5)
    assert report["D_sw"]["M_total"]["value"][0][0] == pytest.approx(4 * a_xx / 4.29, rel=1e-4)
    assert "RWIGS" in report["D_sw"]["M_int"]["moment"] and report["D_sw"]["M_total"]["sigma"][0][0] == 0
    assert report["D"].startswith("not evaluated") and report["noise"]["n_g"] == 3 and "sigma_y" not in report["noise"]
    assert report["null"]["passed"] is None and report["null"]["detail"].startswith("not evaluated")
    traces = manifest.load(out / "traces.json")
    assert traces["checks"]["C0"]["passed"] is None and traces["checks"]["E0"]["d1_t1"]["passed"]

    # Dumps: zero spin density gives T = 0 on every run, so the null passes ...
    assert main(["dumps", str(out), "--job", str(job)]) == 0
    write_cso(out / "dump_C" / "CSO.dat", make_clean_cso(2, 3))
    for name in spiral.run_names(out):
        write_cocc(out / name / "dump_P" / "COCC.dat", np.zeros((4, 2, 3, 3), complex), nelect=8.0)
    capsys.readouterr()
    assert main(["fit", str(out)]) == 0
    report = manifest.load(out / "tensors.json")
    assert report["null"]["passed"] and report["null"]["threshold"] == 5e-5 and report["F"]["passed"] is None
    # ... and one run whose COCC gives |T| = 1e-4 eV on ion 2 makes fit exit 1, naming it.
    lam = split_operator(load_cso(out / "dump_C" / "CSO.dat"))[:, 1]
    gram = np.einsum("aij,bij->ab", lam, lam.conj()).real
    m = np.einsum("b,bij->ij", np.linalg.solve(gram, [0.0, 1e-4, 0.0]), lam)
    cocc = np.zeros((4, 2, 3, 3), complex)
    cocc[0, 1], cocc[3, 1] = m / 2, -m / 2
    write_cocc(out / "d1_t2_minus" / "dump_P" / "COCC.dat", cocc, nelect=8.0)
    capsys.readouterr()
    assert main(["fit", str(out)]) == 1
    assert "Null  FAIL: |T_y| = 1.000e-04 eV on d1_t2_minus, ion 2" in capsys.readouterr().out
    assert manifest.load(out / "tensors.json")["failures"][-1].startswith("Null (|T_y| = 1.000e-04 eV on d1_t2_minus")
