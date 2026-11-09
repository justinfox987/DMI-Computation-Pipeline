"""Tensors, fits and predictions: math Sections 6, 9 and 10 and plans/ten-05-tensors.md.

The spin model of Section 6 is the oracle: its D and A come from Eq (6.3), its
y and g from Eq (6.2), independent of the fit code.
"""

import numpy as np
import pytest

from dmi_pipeline import manifest, spiral, symmetry, tensors
from dmi_pipeline.__main__ import main
from dmi_pipeline.gates import gate_forbidden
from tests.fixtures import bfo
from tests.test_spiral import SEED, material
from tests.test_symmetry import closure, fege, rot_z


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
    structure, sites, signs, seeds = MODELS[name]
    ops = symmetry.operations(*structure, sites, signs)
    d_basis, a_basis = symmetry.spiralization_basis(ops["rotations"]), symmetry.stiffness_basis(ops["rotations"])
    big_d, big_a, per_cell = spin_model(ops["rotations"], seeds, len(sites))
    lattice, species = structure[0], structure[1]
    directions = spiral.choose_directions(lattice, a_basis)
    s = spiral.unit_directions(lattice, directions)
    share = np.linspace(1, 2, len(species)) / np.linspace(1, 2, len(species)).sum()   # T split over ions
    data = []
    for s_i in s:
        rows = []
        for t_j in t:
            (t_plus, e_plus), (t_minus, e_minus) = per_cell(t_j * s_i), per_cell(-t_j * s_i)
            if noise:
                t_plus, t_minus = t_plus + rng.normal(0, noise, 3), t_minus + rng.normal(0, noise, 3)
                e_plus, e_minus = e_plus + rng.normal(0, noise), e_minus + rng.normal(0, noise)
            y, g = tensors.pair_observables(t_plus, t_minus, e_plus, e_minus, 0.0, len(sites))
            rows.append((y, g, share[:, None] * (t_plus - t_minus) / len(sites)))
        data.append({"t": np.asarray(t), "y": np.array([r[0] for r in rows]),
                     "g": np.array([r[1] for r in rows]), "y_ion": np.array([r[2] for r in rows])})
    slopes = tensors.fit_directions(data)
    part = tensors.spiralization(s, slopes["v"], slopes["cov_v"], d_basis)
    stiff = tensors.stiffness(s, slopes["kappa"], slopes["cov_kappa"], a_basis)
    return (big_d, big_a, slopes, part, stiff, tensors.by_species(slopes, data, species, part["linear"]),
            s, d_basis)


def test_fits_recover_spin_model_tensors():
    """Gate 1: Eq (6.3) tensors come back through Eqs (1.3), (1.4) and Section 9."""
    for name in MODELS:
        big_d, big_a, slopes, part, stiff, species, s, d_basis = model_fit(name, [0.005, 0.01, 0.015])
        assert np.abs(big_d).max() > 1e-5 and np.abs(big_a).max() > 1e-3
        assert part["D_free"] == pytest.approx(big_d, abs=1e-6 * np.abs(big_d).max())
        assert part["D"] == pytest.approx(big_d, abs=1e-6 * np.abs(big_d).max())
        assert stiff["A"] == pytest.approx(big_a, abs=1e-6 * np.abs(big_a).max())
        assert np.abs(part["F"]).max() < 1e-6 * np.abs(big_d).max()
        assert sum(v["D"] for v in species.values()) == pytest.approx(part["D"], abs=1e-15)
        assert sum(v["D_free"] for v in species.values()) == pytest.approx(part["D_free"], abs=1e-15)
        assert gate_forbidden(part["F"], np.sqrt(np.diag(part["cov_F"])).reshape(3, 3), part["D_free"]).passed

    # Noise-free BFO (3m) with a forbidden 1e-3 |D| component added to D_free: the check must fail.
    # diag(1, 0, 0) has no projection on the 3m form D [z]x, so all of it is forbidden.
    extra = 1e-3 * np.abs(big_d).max() * np.diag([1.0, 0, 0])
    tainted = tensors.spiralization(s, slopes["v"] + 2 * s @ extra.T, slopes["cov_v"], d_basis)
    assert tainted["F"] == pytest.approx(extra, abs=1e-6 * np.abs(big_d).max())
    assert not gate_forbidden(tainted["F"], np.sqrt(np.diag(tainted["cov_F"])).reshape(3, 3),
                              tainted["D_free"]).passed

    # Real magnitudes with noise of known sigma: pooled sigma2 and coverage (Eq 9.9).
    noise, n_m = 2e-6, 2
    big_d, big_a, slopes, part, stiff, *_ = model_fit("BFO", [0.03, 0.06, 0.09], noise, np.random.default_rng(5))
    # 9 degrees of freedom for y, so the factor-two band depends on the fixed seed. g has
    # only 3 (one per direction), too few for a band; its sigma is checked by A's coverage.
    assert 0.5 < slopes["sigma2"]["y"] / (2 * noise ** 2 / n_m ** 2) < 2
    sigma_d = np.sqrt(np.diag(part["cov_D"])).reshape(3, 3)
    assert np.all(np.abs(part["D"] - big_d) <= 3 * sigma_d + 1e-12)
    sigma_a = np.sqrt(np.diag(stiff["cov_A"])).reshape(3, 3)
    assert np.all(np.abs(stiff["A"] - big_a) <= 3 * sigma_a + 1e-12)


def test_predictions():
    """Section 10.1's three cases, the y-row flip, and the uncertainty flags."""
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

    rng = np.random.default_rng(2)
    generic_d, base = rng.normal(size=(3, 3)) * 1e-3, rng.normal(size=(3, 3))
    generic_a = base @ base.T * 0.01 + 0.02 * np.eye(3)
    plain, flipped = tensors.predict(generic_d, generic_a), tensors.predict(tensors.FLIP @ generic_d, generic_a)
    assert flipped["pitch_A"] == pytest.approx(plain["pitch_A"]) and flipped["e_star"] == pytest.approx(plain["e_star"])
    assert flipped["q_star"] == pytest.approx(plain["q_star"])
    assert flipped["n_star"][0] == pytest.approx(plain["n_star"][0] * [1, -1, 1]) or \
        flipped["n_star"][0] == pytest.approx(-plain["n_star"][0] * [1, -1, 1])

    mirror_x, c2x = np.diag([-1., 1, 1]), np.diag([1., -1, -1])
    s4z = np.array([(0, -1, 0), (1, 0, 0), (0, 0, -1)], float)
    for generators, visible in (([rot_z(3), mirror_x], True), ([s4z, c2x], True), ([rot_z(2), c2x], False)):
        assert tensors.y_flip_visible(symmetry.spiralization_basis(closure(generators))) is visible

    basis = [z_cross / np.sqrt(2)]
    a_basis = [np.diag([1., 1, 0]) / np.sqrt(2), np.diag([0., 0, 1])]
    d_coeff, a_coeff = np.array([d0 * np.sqrt(2)]), np.array([a0 * np.sqrt(2), 3 * a0])
    small = tensors.prediction_uncertainty(d_coeff, np.diag([(0.05 * d_coeff[0]) ** 2]), basis,
                                           a_coeff, np.diag((0.01 * a_coeff) ** 2), a_basis)
    large = tensors.prediction_uncertainty(d_coeff, np.diag([(0.5 * d_coeff[0]) ** 2]), basis,
                                           a_coeff, np.diag((0.01 * a_coeff) ** 2), a_basis)
    gamma = tensors.predict(d0 * z_cross, np.diag([a0, a0, 3 * a0]))["gamma_max"]
    assert small["gamma_max"] / gamma < tensors.POOR_PITCH < large["gamma_max"] / gamma
    assert not small["poorly_determined"] and large["poorly_determined"]
    # pitch = 4 pi A_perp / |D|: 5% on D and 1% on A_perp add in quadrature.
    assert small["pitch_A"] == pytest.approx(np.hypot(0.05, 0.01) * 4 * np.pi * a0 / d0, rel=1e-6)

    a_matrix = np.diag([a0, a0, 3 * a0])
    assert tensors.spin_wave_stiffness(a_matrix, np.zeros((9, 9)), 2.2, [1, 1])[0] == pytest.approx(4 * a_matrix / 2.2)
    assert tensors.spin_wave_stiffness(a_matrix, np.zeros((9, 9)), 2.2, [1, -1])[0] is None


def test_fit_command(tmp_path, capsys):
    """dmi fit on a prepared BFO tree whose collected.json and traces.json hold spin-model values."""
    path, out = material(tmp_path, SEED.replace("0.03, 0.06, 0.09", "0.005, 0.01, 0.015")), tmp_path / "runs"
    spiral.prepare(spiral.load_seed(path), out, tmp_path / "job.sh")
    structure, sites, signs, seeds = MODELS["BFO"]
    ops = symmetry.operations(*structure, sites, signs)
    big_d, big_a, per_cell = spin_model(ops["rotations"], seeds, 2)
    lattice = bfo()[0]
    collected, runs = {}, {}
    for name in (out / "runs.txt").read_text().split():
        q_frac = manifest.load(out / name / "config.json")["q_frac"]
        t_cell, e_cell = per_cell(spiral.cartesian(lattice, q_frac)[0])
        for file, text in (("OUTCAR", "out " + name), ("OSZICAR", "osz " + name), ("dump_P/COCC.dat", "cocc " + name)):
            (out / name / file).parent.mkdir(exist_ok=True)
            (out / name / file).write_text(text)
        collected[name] = {"E_eV": -50.0 + e_cell, "M": [4.0, 4.0],
                           "sha256": {f: manifest.file_hash(out / name / f) for f in ("OUTCAR", "OSZICAR")}}
        per_ion = np.zeros((10, 3))
        per_ion[2], per_ion[3] = 0.7 * t_cell, 0.3 * t_cell
        runs[name] = {"T_eV": t_cell.tolist(), "per_ion_eV": per_ion.tolist(), "q_frac": q_frac,
                      "sha256": {"COCC": manifest.file_hash(out / name / "dump_P" / "COCC.dat")}}
    traces = {"passed": True, "failures": [], "runs": runs, "T_y": "provisional: CSO flip-block order unpinned until T3",
              "checks": {"P0": {f"d{i}_t{j}": {"value": {"even_eV": 0.0}} for i in (1, 2, 3) for j in (1, 2, 3)}}}
    manifest.save(collected, out / "collected.json")
    manifest.save(traces, out / "traces.json")

    assert main(["fit", str(out)]) == 0
    report = manifest.load(out / "tensors.json")
    assert report["N_m"] == 2 and np.allclose(report["D"]["value"], 1e3 * big_d, atol=1e-6 * 1e3 * np.abs(big_d).max())
    assert np.allclose(report["A"]["value"], 1e3 * big_a, atol=1e-6 * 1e3 * np.abs(big_a).max())
    volume = abs(np.linalg.det(lattice)) / 2
    assert report["V_m_A3"] == pytest.approx(volume)
    assert np.allclose(report["micromagnetic"]["D_mJ_per_m2"], 1e3 * big_d / volume * 16.02, rtol=1e-6, atol=1e-12)
    assert np.allclose(report["micromagnetic"]["A_pJ_per_m"], 1e3 * big_a / volume * 1.602, rtol=1e-6, atol=1e-12)
    assert np.allclose(report["D_by_species"]["Fe"]["D"], report["D"]["value"], atol=1e-12)
    assert report["T_y"].startswith("provisional") and report["y_flip_visible_in_F"] and "F_flipped_norm" in report
    assert report["sign"].startswith("unanchored") and report["D_sw"]["value"] is None
    assert report["prediction"]["pitch_nm"] > 0 and report["prediction"]["degeneracy"] == 2

    def refused(message, path, change):
        original = path.read_text()
        change(path)
        capsys.readouterr()
        assert main(["fit", str(out)]) == 1 and message in capsys.readouterr().err
        path.write_text(original)
    refused("traces.json did not pass", out / "traces.json",
            lambda p: manifest.save(dict(traces, passed=False), p))
    refused("COCC.dat changed since dmi trace", out / "d2_t3_minus" / "dump_P" / "COCC.dat", lambda p: p.write_text("x"))
    plan = manifest.load(out / "plan.json")
    refused("seed in plan.json has 1 sites", out / "plan.json",
            lambda p: manifest.save(dict(plan, seed=plan["seed"].replace("sites = [3, 4]", "sites = [3]")), p))
    runs_without = {k: v for k, v in runs.items() if k != "d1_t1_plus"}
    refused("fail the Section 8.2 rank conditions", out / "traces.json",
            lambda p: manifest.save(dict(traces, runs=runs_without), p))
