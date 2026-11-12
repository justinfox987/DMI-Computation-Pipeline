"""Spiralization and stiffness tensors from paired spirals (math Sections 1, 9 and 10).

Spec: plans/ten-05-tensors.md, with D-023. Energies are eV per calculation cell on
input and per magnetic site after Eqs (1.3)-(1.4); q is Cartesian in 1/Å, so D
is eV Å and A is eV Å^2 per magnetic site. Reported values are converted to meV once.
"""

from pathlib import Path
import tomllib

import numpy as np

from . import manifest, spiral, symmetry
from .gates import NOT_EVALUATED, check_tree, gate_forbidden
from .realized import poscar
from .spiral import FREE_BASIS, RANK_FLOOR, geometry_ranks, spiralization_design, stiffness_design

MEV = 1e3
# Section 10.4: a meV value divided by V_m in Å^3, times these, gives SI units.
PJ_PER_M_FROM_MEV_PER_A = 1.602      # A: meV Å^-1 -> pJ m^-1
MJ_PER_M2_FROM_MEV_PER_A2 = 16.02    # D: meV Å^-2 -> mJ m^-2
DEGENERATE = 1e-9      # relative eigenvalue gap that counts as a degenerate n*
SIGN = "follows VASP's SOC energy (D-020); not yet confirmed by a VASP run"


def pair_observables(t_plus, t_minus, e_plus, e_minus, e_zero, n_m):
    """y of Eq (1.3) and g of Eq (1.4), per magnetic site; no extra factor of one half."""
    y = (np.asarray(t_plus, float) - np.asarray(t_minus, float)) / n_m
    g = (e_plus + e_minus - 2 * e_zero) / (2 * n_m)
    return y, g


# ---- single solves, Section 9.4 ------------------------------------------------

def tensor_fit(design, data, sigma, basis):
    """One least-squares solve x = X^+ d with Cov(x) = sigma^2 (X^T X)^+ (Eq 9.9).

    The first len(basis) unknowns are the basis coefficients; the rest are nuisances.
    "solver" maps any data of the same row layout to coefficients (Section 9.5).
    """
    nb = len(basis)
    solver = np.linalg.pinv(design)
    x, cov = solver @ data, sigma ** 2 * solver @ solver.T
    flat = np.reshape(basis, (nb, 9)).T                      # vec(tensor) = flat @ coefficients
    return {"coef": x[:nb], "cov_coef": cov[:nb, :nb], "nuisance": x[nb:],
            "tensor": (flat @ x[:nb]).reshape(3, 3), "cov": flat @ cov[:nb, :nb] @ flat.T,
            "solver": solver[:nb], "flat": flat}


def fit_pairs(s, pairs, n_m, e_zero, d_basis, a_basis, species=None):
    """Every Section 9 result from the complete pairs.

    pairs: dicts with i (row of s), t, E_plus, E_minus, and T_plus, T_minus and
    per_ion = per-ion T(q) - T(-q) (all None in an energies-only tree). Noise comes from the parity
    residuals (Eq 9.9): sigma_y from [T(q) + T(-q)]/N_m, sigma_g from [E(q) - E(-q)]/2N_m.
    """
    points = [(p["i"], p["t"]) for p in pairs]
    traced = pairs[0]["T_plus"] is not None
    if any(len({p["t"] for p in pairs if p["i"] == i}) < 2 for i in range(len(s))):
        raise ValueError("Every direction used needs complete pairs at two or more distinct magnitudes")
    ranks = geometry_ranks(s, d_basis, a_basis)
    observed = [pair_observables(p["T_plus"] if traced else 0, p["T_minus"] if traced else 0,
                                 p["E_plus"], p["E_minus"], e_zero, n_m) for p in pairs]
    y, g = np.array([o[0] for o in observed]), np.array([o[1] for o in observed])
    odd_g = np.array([(p["E_plus"] - p["E_minus"]) / (2 * n_m) for p in pairs])
    a_design = stiffness_design(s, points, a_basis)
    if ranks["A"] < RANK_FLOOR:
        raise ValueError(f"The directions used do not determine A: rank value {ranks['A']:.3g} < {RANK_FLOOR}")
    noise = {"sigma_g": float(np.sqrt(np.mean(odd_g ** 2))), "n_g": len(odd_g)}
    result = {"A": tensor_fit(a_design, g, noise["sigma_g"], a_basis), "noise": noise}
    result["A"]["eigenvalues"] = np.linalg.eigvalsh(result["A"]["tensor"])
    if not traced:
        return result
    even_y = np.array([(np.asarray(p["T_plus"]) + p["T_minus"]) / n_m for p in pairs])
    noise.update(sigma_y=float(np.sqrt(np.mean(even_y ** 2))), n_y=even_y.size)
    if ranks["D"] < RANK_FLOOR:
        raise ValueError(f"The directions used do not determine D: rank value {ranks['D']:.3g} < {RANK_FLOOR}")
    result["D"] = tensor_fit(spiralization_design(s, points, d_basis), y.ravel(), noise["sigma_y"], d_basis)
    if ranks["D_free"] >= RANK_FLOOR:                      # fewer than three directions: not evaluated
        free = result["D_free"] = tensor_fit(spiralization_design(s, points, FREE_BASIS), y.ravel(),
                                             noise["sigma_y"], FREE_BASIS)
        rest = np.eye(9) - result["D"]["flat"] @ result["D"]["flat"].T       # 1 - P_D, Eq (9.4)
        result["F"] = {"tensor": (rest @ free["tensor"].ravel()).reshape(3, 3), "cov": rest @ free["cov"] @ rest.T}
    if species is not None:
        result["by_species"] = by_species(result, np.array([p["per_ion"] for p in pairs]) / n_m, species)
    return result


def by_species(result, y_ion, species):
    """Section 9.5: the same solves applied to per-ion y, summed over the ions of each species."""
    fits = {name: result[name] for name in ("D", "D_free") if name in result}
    out = {}
    for ion, symbol in enumerate(species):
        entry = out.setdefault(symbol, {name: np.zeros((3, 3)) for name in fits})
        for name, f in fits.items():
            entry[name] += (f["flat"] @ (f["solver"] @ y_ion[:, ion, :].ravel())).reshape(3, 3)
    return out


# ---- predictions, Eq (10.1) and Eq (10.2) ------------------------------------

def predict(d_matrix, a_matrix):
    """Gamma, n*, q*, e* and the pitch; n* is a subspace when gamma_max is degenerate."""
    if not np.any(d_matrix):
        return {"Gamma": np.zeros((3, 3)), "eigenvalues": np.zeros(3), "gamma_max": 0.0, "n_star": None,
                "degeneracy": 0, "q_star": np.zeros(3), "e_star": 0.0, "pitch_A": None}
    a_inv = np.linalg.inv(a_matrix)
    gamma = d_matrix @ a_inv @ d_matrix.T
    eigenvalues, vectors = np.linalg.eigh(gamma)
    top = eigenvalues[-1]
    degeneracy = int(np.sum(eigenvalues >= top * (1 - DEGENERATE)))
    q_star = -a_inv @ d_matrix.T @ vectors[:, -1] / 2
    return {"Gamma": gamma, "eigenvalues": eigenvalues, "gamma_max": float(top),
            "n_star": vectors[:, -degeneracy:].T, "degeneracy": degeneracy, "q_star": q_star,
            "e_star": float(-top / 4), "pitch_A": float(2 * np.pi / np.linalg.norm(q_star))}


def prediction_uncertainty(d, cov_d, d_basis, a, cov_a, a_basis):
    """First-order sigma of gamma_max, e*, |q*| and the pitch by central differences in (d_l, a_l)."""
    params = np.concatenate([d, a])
    cov = np.zeros((len(params), len(params)))
    cov[:len(d), :len(d)], cov[len(d):, len(d):] = cov_d, cov_a      # T and E are independent data
    def scalars(p):
        out = predict(np.einsum("l,ljk->jk", p[:len(d)], np.asarray(d_basis)),
                      np.einsum("l,ljk->jk", p[len(d):], np.asarray(a_basis)))
        return np.array([out["gamma_max"], out["e_star"], np.linalg.norm(out["q_star"]), out["pitch_A"]])
    steps = np.maximum(np.sqrt(np.diag(cov)), 1e-12 * np.abs(params)) * 1e-3
    jacobian = np.column_stack([(scalars(params + h * e) - scalars(params - h * e)) / (2 * h)
                                if h > 0 else np.zeros(4) for h, e in zip(steps, np.eye(len(params)))])
    sigma = np.sqrt(np.diag(jacobian @ cov @ jacobian.T))
    return dict(zip(("gamma_max", "e_star", "q_star", "pitch_A"), sigma.tolist()))


def spin_wave_stiffness(a_matrix, cov_a_matrix, moment, signs):
    """D_sw = 4A/M of Eq (10.2), ferromagnets only; M in μB per site."""
    if any(sign != 1 for sign in signs):
        return None, "not a ferromagnet: Eq (10.2) applies when every sign is +1"
    return 4 * a_matrix / moment, (4 / moment) ** 2 * cov_a_matrix


# ---- the run tree --------------------------------------------------------------

def observables(out, states, traces):
    """Complete pairs of the tree, from read_runs and check_tree of this call."""
    out = Path(out)
    plan = manifest.load(out / "plan.json")
    seed = tomllib.loads(plan["seed"])
    lattice, species, tau = poscar(out / "q0" / "POSCAR")
    config = manifest.load(out / "q0" / "config.json")
    sites, signs = config["sites"], config["signs"]
    n_m = len(sites)
    if n_m != len(seed["sites"]):
        raise ValueError(f"N_m = {n_m} from config.json, but the seed in plan.json has {len(seed['sites'])} sites")
    ops = symmetry.operations(lattice, species, tau, sites, signs, seed.get("symprec", 1e-3), seed.get("spacegroup"))
    traced = traces["traced"]

    def run(name):
        """E, T, per-ion T and q_frac of one run, or None when it is not complete."""
        result, trace = states.get(name, {"error": "missing"}), traces["runs"].get(name, {})
        if "error" in result or (traced and ("error" in trace or not trace)):
            return None
        q_frac = manifest.load(out / name / "config.json")["q_frac"]
        if not traced:
            return result["E_eV"], None, None, q_frac
        return result["E_eV"], np.asarray(trace["T_eV"]), np.asarray(trace["per_ion_eV"]), q_frac

    zero = run("q0")
    if zero is None:
        raise ValueError("q0 has no state" + (" or no trace" if traced else ""))
    used, dropped, pairs = [], [], []
    for i, direction in enumerate(plan["directions"], 1):
        rows = []
        for j, t in enumerate(np.sort(seed["t"]), 1):
            plus, minus = run(f"d{i}_t{j}_plus"), run(f"d{i}_t{j}_minus")
            if plus is None or minus is None:
                continue
            length = np.linalg.norm(spiral.cartesian(lattice, plus[3]))
            if not np.isclose(length, t, rtol=1e-9, atol=0):
                raise ValueError(f"d{i}_t{j}: |q| = {length:.6g} 1/Å differs from the seed t = {t:g}")
            rows.append({"i": len(used), "t": t, "E_plus": plus[0], "E_minus": minus[0], "T_plus": plus[1],
                         "T_minus": minus[1], "per_ion": None if plus[2] is None else plus[2] - minus[2]})
        if len({r["t"] for r in rows}) < 2:              # slope and cubic nuisance need two magnitudes
            dropped.append(f"d{i}")
            continue
        used.append({"name": f"d{i}", "q_frac": direction, "t": [r["t"] for r in rows]})
        pairs += rows
    if not pairs:
        raise ValueError("No complete +-q pair")
    return {"lattice": lattice, "species": species, "n_m": n_m, "signs": signs, "traced": traced,
            "s": spiral.unit_directions(lattice, [d["q_frac"] for d in used]), "directions": used,
            "dropped": dropped, "pairs": pairs, "e_zero": zero[0],
            "d_basis": symmetry.spiralization_basis(ops["rotations"]),
            "a_basis": symmetry.stiffness_basis(ops["rotations"]), "M_q0": float(np.mean(states["q0"]["M"]))}


def _value(matrix, cov, scale=MEV):
    return {"value": (scale * matrix).tolist(), "sigma": (scale * np.sqrt(np.diag(cov)).reshape(3, 3)).tolist()}


def report_tree(out, states, traces):
    """Every Section 9 and 10.1 result of a tree whose Section 11 checks passed."""
    obs = observables(out, states, traces)
    result = fit_pairs(obs["s"], obs["pairs"], obs["n_m"], obs["e_zero"], obs["d_basis"], obs["a_basis"],
                       obs["species"] if obs["traced"] else None)
    stiff, traced = result["A"], obs["traced"]
    positive = bool(np.all(stiff["eigenvalues"] > 0))
    volume = abs(np.linalg.det(obs["lattice"])) / obs["n_m"]               # V_m, Å^3
    report = {"N_m": obs["n_m"], "V_m_A3": volume,
              "units": {"D": "meV A per magnetic site", "A": "meV A^2 per magnetic site", "pitch": "nm"},
              "directions": [dict(d, s=s.tolist(), b=float(stiff["nuisance"][k]),
                                  c=result["D"]["nuisance"][3 * k:3 * k + 3].tolist() if traced else None)
                             for k, (d, s) in enumerate(zip(obs["directions"], obs["s"]))],
              "dropped_directions": obs["dropped"], "noise": result["noise"],
              "A": dict(_value(stiff["tensor"], stiff["cov"]), a=stiff["coef"].tolist(),
                        cov_a=stiff["cov_coef"].tolist(), eigenvalues=(MEV * stiff["eigenvalues"]).tolist(),
                        positive=positive),
              "micromagnetic": {"A_pJ_per_m": (MEV * stiff["tensor"] / volume * PJ_PER_M_FROM_MEV_PER_A).tolist()},
              "sign": SIGN}
    forbidden_passed = True
    if not traced:
        for name in ("D", "D_free", "F", "D_by_species", "prediction"):
            report[name] = NOT_EVALUATED
    else:
        d = result["D"]
        report["D"] = dict(_value(d["tensor"], d["cov"]), d=d["coef"].tolist(), cov_d=d["cov_coef"].tolist())
        report["micromagnetic"]["D_mJ_per_m2"] = (MEV * d["tensor"] / volume * MJ_PER_M2_FROM_MEV_PER_A2).tolist()
        report["D_by_species"] = {k: {n: (MEV * m).tolist() for n, m in v.items()} for k, v in result["by_species"].items()}
        if "D_free" in result:
            f = result["F"]
            forbidden = gate_forbidden(f["tensor"], np.sqrt(np.diag(f["cov"])).reshape(3, 3), result["D_free"]["tensor"])
            forbidden_passed = forbidden.passed
            report["D_free"] = _value(result["D_free"]["tensor"], result["D_free"]["cov"])
            report["F"] = dict(_value(f["tensor"], f["cov"]), norm=MEV * float(np.linalg.norm(f["tensor"])),
                               ratio_to_D_free=forbidden.value["ratio_to_D_free"], passed=forbidden.passed,
                               bound=forbidden.detail)
        else:
            reason = "not evaluated: the directions do not determine D_free"
            report["D_free"], report["F"] = reason, {"passed": None, "reason": reason}
        report["prediction"] = None
        if positive:
            p = predict(d["tensor"], stiff["tensor"])
            prediction = {"Gamma": p["Gamma"].tolist(), "eigenvalues": p["eigenvalues"].tolist(),
                          "n_star": None if p["n_star"] is None else p["n_star"].tolist(),
                          "degeneracy": p["degeneracy"], "q_star": p["q_star"].tolist(),
                          "q_star_frac": (obs["lattice"] @ p["q_star"] / (2 * np.pi)).tolist(),
                          "e_star_meV": MEV * p["e_star"], "pitch_nm": None, "sigma_pitch_nm": None}
            if p["pitch_A"] is not None:
                sigma = prediction_uncertainty(d["coef"], d["cov_coef"], obs["d_basis"],
                                               stiff["coef"], stiff["cov_coef"], obs["a_basis"])
                prediction.update(pitch_nm=p["pitch_A"] / 10, sigma_pitch_nm=sigma["pitch_A"] / 10,
                                  sigma_e_star_meV=MEV * sigma["e_star"])
            report["prediction"] = prediction
    if positive:
        d_sw, cov_sw = spin_wave_stiffness(stiff["tensor"], stiff["cov"], obs["M_q0"], obs["signs"])
        report["D_sw"] = ({"value": None, "reason": cov_sw} if d_sw is None else
                          dict(_value(d_sw, cov_sw), units="meV A^2", M_muB=obs["M_q0"]))
    else:
        report["D_sw"] = {"value": None, "reason": "A is not positive definite"}
    report["passed"] = forbidden_passed and positive
    return report


def fit(out):
    """dmi fit: trace and check the tree from its files, then every Section 9 and
    10.1 result, written to DIR/tensors.json. A refused fit also writes
    tensors.json, with passed false and its failures, so no older result survives."""
    out = Path(out)
    try:
        states = spiral.read_runs(out)
        traces = check_tree(out, states)
        failures = traces["failures"]
        if not failures:
            report = report_tree(out, states, traces)
            manifest.save(report, out / "tensors.json")
            report["lines"] = traces["lines"] + _lines(report)
            return report
    except (OSError, ValueError, KeyError) as error:
        if out.is_dir():
            manifest.save({"passed": False, "failures": [str(error)]}, out / "tensors.json")
        raise
    manifest.save({"passed": False, "failures": failures}, out / "tensors.json")
    return {"passed": False, "lines": traces["lines"] + [f"fit refused: failed {', '.join(failures)}"]}


def _lines(report):
    def matrix(m):
        return "[" + "; ".join(" ".join(f"{x:+.4g}" for x in row) for row in m) + "]"
    noise = report["noise"]
    lines = [f"A (meV A^2 per site) {matrix(report['A']['value'])}  eigenvalues "
             + " ".join(f"{x:.4g}" for x in report["A"]["eigenvalues"])]
    if isinstance(report["D"], str):
        lines.append(f"D, F and the prediction {report['D']}")
        lines.append(f"sigma_g {noise['sigma_g']:.3g} eV from {noise['n_g']} pairs")
    else:
        lines.insert(0, f"D (meV A per site)  {matrix(report['D']['value'])}")
        f = report["F"]
        lines.insert(1, f"F norm {f['norm']:.3g} meV A, max|F|/max|D_free| {f['ratio_to_D_free']:.2g}: "
                        f"{'pass' if f['passed'] else 'FAIL'}" if f["passed"] is not None
                     else f"F {f['reason']}")
        lines.append(f"sigma_y {noise['sigma_y']:.3g} eV ({noise['n_y']} samples)  "
                     f"sigma_g {noise['sigma_g']:.3g} eV ({noise['n_g']} samples)")
        p = report["prediction"]
        if p is None:
            lines.append("no prediction: A is not positive definite")
        elif p["pitch_nm"] is None:
            lines.append("D = 0: no spiral")
        else:
            lines.append(f"pitch {p['pitch_nm']:.4g} +- {p['sigma_pitch_nm']:.2g} nm, n* degeneracy {p['degeneracy']}")
    if report["dropped_directions"]:
        lines.append(f"dropped directions (fewer than two magnitudes): {', '.join(report['dropped_directions'])}")
    lines.append(f"sign {report['sign']}")
    return lines
