"""Spiralization and stiffness tensors from paired spirals (math Sections 1, 9 and 10).

Spec: plans/ten-05-tensors.md. Energies are eV per calculation cell on input and
per magnetic site after Eqs (1.3)-(1.4); q is Cartesian in 1/Å, so D is eV Å and
A is eV Å^2 per magnetic site. Reported values are converted to meV once.
"""

from pathlib import Path
import tomllib

import numpy as np

from . import manifest, spiral, symmetry
from .gates import check_tree, gate_forbidden
from .realized import poscar

MEV = 1e3
# Section 10.4: a meV value divided by V_m in Å^3, times these, gives SI units.
PJ_PER_M_FROM_MEV_PER_A = 1.602      # A: meV Å^-1 -> pJ m^-1
MJ_PER_M2_FROM_MEV_PER_A2 = 16.02    # D: meV Å^-2 -> mJ m^-2
MIN_PAIRS = 3          # complete +-q pairs per direction, so every Eq (9.1) fit has dof >= 1
POOR_PITCH = 0.3       # sigma(gamma_max) / gamma_max above which first order is unreliable
DEGENERATE = 1e-9      # relative eigenvalue gap that counts as a degenerate n*


def least_squares(X, y):
    """The one linear fit of Section 9: (x, unscaled covariance (X^T X)^-1, rss, dof)."""
    X, y = np.asarray(X, float), np.asarray(y, float)
    x = np.linalg.lstsq(X, y, rcond=None)[0]
    return x, np.linalg.pinv(X.T @ X), float(np.sum((y - X @ x) ** 2)), len(y) - X.shape[1]


def propagate(linear, cov):
    """Covariance of linear(v) for input covariance cov, Eq (9.9) carried forward."""
    jacobian = np.column_stack([np.ravel(linear(column)) for column in np.eye(len(cov))])
    return jacobian @ cov @ jacobian.T


def pair_observables(t_plus, t_minus, e_plus, e_minus, e_zero, n_m):
    """y of Eq (1.3) and g of Eq (1.4), per magnetic site; no extra factor of one half."""
    y = (np.asarray(t_plus, float) - np.asarray(t_minus, float)) / n_m
    g = (e_plus + e_minus - 2 * e_zero) / (2 * n_m)
    return y, g


# ---- per-direction fits, Eqs (9.1) and (9.9) --------------------------------

def fit_directions(directions):
    """Fit y = v t + c t^3 per axis and g = kappa t^2 + b t^4 per direction, pooling sigma2.

    directions: list of {"t": (Nt,), "y": (Nt, 3), "g": (Nt,)}; returns slopes,
    their covariances from the pooled variances, and the slope row of each fit,
    which applied to any y-like data gives its slope (Section 9.5 reuses it).
    """
    rss_y = rss_g = 0.0
    dof_y = dof_g = 0
    fits = []
    for d in directions:
        t = np.asarray(d["t"], float)
        x_y, x_g = np.column_stack([t, t ** 3]), np.column_stack([t ** 2, t ** 4])
        axes = [least_squares(x_y, d["y"][:, a]) for a in range(3)]
        energy = least_squares(x_g, d["g"])
        rss_y += sum(fit[2] for fit in axes)
        dof_y += sum(fit[3] for fit in axes)
        rss_g, dof_g = rss_g + energy[2], dof_g + energy[3]
        fits.append({"v": np.array([fit[0][0] for fit in axes]), "c": np.array([fit[0][1] for fit in axes]),
                     "kappa": energy[0][0], "b": energy[0][1], "unit_v": axes[0][1][0, 0],
                     "unit_kappa": energy[1][0, 0], "slope_row": np.linalg.pinv(x_y)[0]})
    sigma2_y, sigma2_g = rss_y / dof_y, rss_g / dof_g
    return {"fits": fits, "v": np.array([f["v"] for f in fits]), "kappa": np.array([f["kappa"] for f in fits]),
            # No cross-axis covariance (decision 3): axes from one state share noise.
            "cov_v": np.diag(np.repeat([sigma2_y * f["unit_v"] for f in fits], 3)),
            "cov_kappa": np.diag([sigma2_g * f["unit_kappa"] for f in fits]),
            "sigma2": {"y": sigma2_y, "g": sigma2_g, "dof_y": dof_y, "dof_g": dof_g}}


# ---- tensors, Eqs (9.3)-(9.6) ------------------------------------------------

def projector(basis):
    """P_D or P_A of Eq (7.6) through the orthonormal basis of Eq (7.7)."""
    return lambda m: sum((np.sum(b * m) * b for b in basis), np.zeros((3, 3)))


def spiralization(s, v, cov_v, basis):
    """D_free (9.3), F (9.4) and the constrained D (9.5), with covariances; v is (Nd, 3)."""
    s, v = np.asarray(s, float), np.asarray(v, float)
    nd, project = len(s), projector(basis)
    s_plus = np.linalg.pinv(s.T)                          # S has the unit s_i as columns

    def free(flat):
        return np.reshape(flat, (nd, 3)).T @ s_plus / 2
    def forbidden(flat):
        d = free(flat)
        return d - project(d)
    # Rows (i, alpha) of Eq (9.5): 2 e_alpha^T B_l s_i, in the order of v.ravel().
    design = np.array([[2 * (b @ s_i)[a] for b in basis] for s_i in s for a in range(3)]).reshape(3 * nd, len(basis))
    solve = np.linalg.pinv(design) if len(basis) else np.zeros((0, 3 * nd))
    def coefficients(flat):
        return solve @ np.ravel(flat)
    def constrained(flat):
        return sum((c * b for c, b in zip(coefficients(flat), basis)), np.zeros((3, 3)))

    flat = v.ravel()
    result = {"D_free": free(flat), "F": forbidden(flat), "D": constrained(flat), "d": coefficients(flat)}
    for name, linear in (("D_free", free), ("F", forbidden), ("D", constrained), ("d", coefficients)):
        result["cov_" + name] = propagate(linear, cov_v)
    result["linear"] = {"free": free, "constrained": constrained}
    return result


def stiffness(s, kappa, cov_kappa, basis):
    """A of Eq (9.6) in the stiffness basis, with covariance and eigenvalues."""
    design = np.einsum("ij,ljk,ik->il", np.asarray(s, float), np.asarray(basis), np.asarray(s, float))
    solve = np.linalg.pinv(design)
    def coefficients(k):
        return solve @ k
    def matrix(k):
        return np.einsum("l,ljk->jk", coefficients(k), np.asarray(basis))
    a_matrix = matrix(kappa)
    return {"A": a_matrix, "a": coefficients(kappa), "cov_A": propagate(matrix, cov_kappa),
            "cov_a": propagate(coefficients, cov_kappa), "eigenvalues": np.linalg.eigvalsh(a_matrix)}


# ---- predictions, Eq (10.1) and Eq (10.2) ------------------------------------

def by_species(slopes, directions, species, linear):
    """Section 9.5: the same linear maps on per-ion slopes, summed over the ions of each species."""
    result = {}
    for ion, symbol in enumerate(species):
        v_ion = np.array([f["slope_row"] @ d["y_ion"][:, ion, :] for f, d in zip(slopes["fits"], directions)])
        entry = result.setdefault(symbol, {"D_free": np.zeros((3, 3)), "D": np.zeros((3, 3))})
        entry["D_free"] += linear["free"](v_ion.ravel())
        entry["D"] += linear["constrained"](v_ion.ravel())
    return result


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
    result = dict(zip(("gamma_max", "e_star", "q_star", "pitch_A"), sigma.tolist()))
    # Decision 4: beyond this the first-order propagation itself is unreliable.
    result["poorly_determined"] = bool(sigma[0] > POOR_PITCH * scalars(params)[0])
    return result


def spin_wave_stiffness(a_matrix, cov_a_matrix, moment, signs):
    """D_sw = 4A/M of Eq (10.2), ferromagnets only; M in μB per site."""
    if any(sign != 1 for sign in signs):
        return None, "not a ferromagnet: Eq (10.2) applies when every sign is +1"
    return 4 * a_matrix / moment, (4 / moment) ** 2 * cov_a_matrix


# ---- the run tree --------------------------------------------------------------

def observables(out, states, traces):
    """y, g and per-ion y per kept direction, from read_runs and check_tree of this call."""
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
    t_seed = np.sort(seed["t"])

    def run(name):
        """E, T and per-ion T of one run, or None when it is not complete."""
        result, trace = states.get(name, {"error": "missing"}), traces["runs"].get(name, {"error": "missing"})
        if "error" in result or "error" in trace:
            return None
        return result["E_eV"], np.asarray(trace["T_eV"]), np.asarray(trace["per_ion_eV"]), trace["q_frac"]

    zero = run("q0")
    if zero is None:
        raise ValueError("q0 has no state or no trace")
    kept, dropped = [], []
    for i, direction in enumerate(plan["directions"], 1):
        rows = []
        for j, t in enumerate(t_seed, 1):
            plus, minus = run(f"d{i}_t{j}_plus"), run(f"d{i}_t{j}_minus")
            if plus is None or minus is None:
                continue
            length = np.linalg.norm(spiral.cartesian(lattice, plus[3]))
            if not np.isclose(length, t, rtol=1e-9, atol=0):
                raise ValueError(f"d{i}_t{j}: |q| = {length:.6g} 1/Å differs from the seed t = {t:g}")
            y, g = pair_observables(plus[1], minus[1], plus[0], minus[0], zero[0], n_m)
            rows.append((t, y, g, (plus[2] - minus[2]) / n_m))
        if len(rows) < MIN_PAIRS:
            dropped.append(f"d{i}")
            continue
        kept.append({"name": f"d{i}", "q_frac": direction, "t": np.array([r[0] for r in rows]),
                     "y": np.array([r[1] for r in rows]), "g": np.array([r[2] for r in rows]),
                     "y_ion": np.array([r[3] for r in rows])})
    d_basis, a_basis = (symmetry.spiralization_basis(ops["rotations"]), symmetry.stiffness_basis(ops["rotations"]))
    s = spiral.unit_directions(lattice, [d["q_frac"] for d in kept]) if kept else np.zeros((0, 3))
    sigma_d, sigma_a = spiral.conditions(lattice, [d["q_frac"] for d in kept], a_basis) if kept else (0.0, 0.0)
    if len(kept) < max(3, len(a_basis)) or min(sigma_d, sigma_a) < spiral.RANK_FLOOR:
        raise ValueError(f"After dropping {dropped or 'none'} (fewer than {MIN_PAIRS} complete pairs), the kept "
                         f"directions fail the Section 8.2 rank conditions (sigma_D {sigma_d:.3g}, sigma_A {sigma_a:.3g})")
    return {"lattice": lattice, "species": species, "n_m": n_m, "signs": signs, "s": s, "directions": kept,
            "dropped": dropped, "d_basis": d_basis, "a_basis": a_basis,
            "M_q0": float(np.mean(states["q0"]["M"])),
            "parity_residual_eV": {k: v["value"]["even_eV"] for k, v in traces["checks"]["P0"].items()}}


def _value(matrix, cov, scale=MEV):
    return {"value": (scale * matrix).tolist(), "sigma": (scale * np.sqrt(np.diag(cov)).reshape(3, 3)).tolist()}


def fit(out):
    """dmi fit: trace and check the tree from its files, then every Section 9 and
    10.1 result, written to DIR/tensors.json. Refuses when a Section 11 check fails."""
    out = Path(out)
    states = spiral.read_runs(out)
    traces = check_tree(out, states)
    if not traces["passed"]:
        return {"passed": False, "lines": traces["lines"] + [f"fit refused: failed {', '.join(traces['failures'])}"]}
    obs = observables(out, states, traces)
    slopes = fit_directions(obs["directions"])
    spiral_part = spiralization(obs["s"], slopes["v"], slopes["cov_v"], obs["d_basis"])
    stiff = stiffness(obs["s"], slopes["kappa"], slopes["cov_kappa"], obs["a_basis"])
    forbidden = gate_forbidden(spiral_part["F"], np.sqrt(np.diag(spiral_part["cov_F"])).reshape(3, 3),
                               spiral_part["D_free"])
    positive = bool(np.all(stiff["eigenvalues"] > 0))

    species_d = by_species(slopes, obs["directions"], obs["species"], spiral_part["linear"])

    volume = abs(np.linalg.det(obs["lattice"])) / obs["n_m"]               # V_m, Å^3
    report = {"N_m": obs["n_m"], "V_m_A3": volume,
              "units": {"D": "meV A per magnetic site", "A": "meV A^2 per magnetic site", "pitch": "nm"},
              "directions": [{"name": d["name"], "q_frac": d["q_frac"], "s": s.tolist(), "t": d["t"].tolist(),
                              "v": f["v"].tolist(), "c": f["c"].tolist(), "kappa": f["kappa"], "b": f["b"]}
                             for d, f, s in zip(obs["directions"], slopes["fits"], obs["s"])],
              "dropped_directions": obs["dropped"], "sigma2": slopes["sigma2"],
              "D_free": _value(spiral_part["D_free"], spiral_part["cov_D_free"]),
              "F": dict(_value(spiral_part["F"], spiral_part["cov_F"]), norm=MEV * float(np.linalg.norm(spiral_part["F"])),
                        passed=forbidden.passed),
              "D": dict(_value(spiral_part["D"], spiral_part["cov_D"]), d=spiral_part["d"].tolist(),
                        cov_d=spiral_part["cov_d"].tolist()),
              "A": dict(_value(stiff["A"], stiff["cov_A"]), a=stiff["a"].tolist(), cov_a=stiff["cov_a"].tolist(),
                        eigenvalues=(MEV * stiff["eigenvalues"]).tolist(), positive=positive),
              "D_by_species": {k: {"D_free": (MEV * v["D_free"]).tolist(), "D": (MEV * v["D"]).tolist()}
                               for k, v in species_d.items()},
              "micromagnetic": {"A_pJ_per_m": (MEV * stiff["A"] / volume * PJ_PER_M_FROM_MEV_PER_A).tolist(),
                                "D_mJ_per_m2": (MEV * spiral_part["D"] / volume * MJ_PER_M2_FROM_MEV_PER_A2).tolist()},
              "parity_residual_eV": obs["parity_residual_eV"],
              "sign": "follows VASP's SOC energy (D-020); not yet confirmed by a VASP run"}
    if positive:
        result = predict(spiral_part["D"], stiff["A"])
        prediction = {"Gamma": result["Gamma"].tolist(), "eigenvalues": result["eigenvalues"].tolist(),
                      "n_star": None if result["n_star"] is None else result["n_star"].tolist(),
                      "degeneracy": result["degeneracy"], "q_star": result["q_star"].tolist(),
                      "q_star_frac": (obs["lattice"] @ result["q_star"] / (2 * np.pi)).tolist(),
                      "e_star_meV": MEV * result["e_star"], "pitch_nm": None, "sigma_pitch_nm": None,
                      "pitch_poorly_determined": None}
        if result["pitch_A"] is not None:
            sigma = prediction_uncertainty(spiral_part["d"], spiral_part["cov_d"], obs["d_basis"],
                                           stiff["a"], stiff["cov_a"], obs["a_basis"])
            prediction.update(pitch_nm=result["pitch_A"] / 10, sigma_pitch_nm=sigma["pitch_A"] / 10,
                              sigma_e_star_meV=MEV * sigma["e_star"],
                              pitch_poorly_determined=sigma["poorly_determined"])
        report["prediction"] = prediction
        d_sw, cov_sw = spin_wave_stiffness(stiff["A"], stiff["cov_A"], obs["M_q0"], obs["signs"])
        report["D_sw"] = ({"value": None, "reason": cov_sw} if d_sw is None else
                          dict(_value(d_sw, cov_sw), units="meV A^2", M_muB=obs["M_q0"]))
    else:
        report["prediction"] = None
        report["D_sw"] = {"value": None, "reason": "A is not positive definite"}
    report["passed"] = forbidden.passed and positive
    manifest.save(report, out / "tensors.json")
    report["lines"] = traces["lines"] + _lines(report)
    return report


def _lines(report):
    def matrix(m):
        return "[" + "; ".join(" ".join(f"{x:+.4g}" for x in row) for row in m) + "]"
    lines = [f"D (meV A per site)  {matrix(report['D']['value'])}",
             f"F norm {report['F']['norm']:.3g} meV A: {'pass' if report['F']['passed'] else 'FAIL'}",
             f"A (meV A^2 per site) {matrix(report['A']['value'])}  eigenvalues "
             + " ".join(f"{x:.4g}" for x in report["A"]["eigenvalues"])]
    p = report["prediction"]
    if p is None:
        lines.append("no prediction: A is not positive definite")
    elif p["pitch_nm"] is None:
        lines.append("D = 0: no spiral")
    else:
        lines.append(f"pitch {p['pitch_nm']:.4g} +- {p['sigma_pitch_nm']:.2g} nm, n* degeneracy {p['degeneracy']}")
        if p["pitch_poorly_determined"]:
            lines.append("WARNING: pitch poorly determined (sigma(gamma_max)/gamma_max > 0.3)")
    if report["dropped_directions"]:
        lines.append(f"dropped directions: {', '.join(report['dropped_directions'])}")
    lines.append(f"sign {report['sign']}")
    return lines
