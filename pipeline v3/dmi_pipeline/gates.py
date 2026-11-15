"""Section 11 checks and the tree trace that dmi fit runs. Results carry evidence, not global pins."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from . import conventions, manifest
from .dumpio import MatrixDump, load_cso
from .trace import split_operator, trace_run


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    value: Any
    threshold: Any
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


def handedness(cso: MatrixDump | np.ndarray) -> np.ndarray:
    """h = Im Tr([Lambda_x, Lambda_y] Lambda_z) / Tr(Lambda_z^2)^1.5 per ion, math Section 4.2.

    Ket-first file arrays give h < 0 for xi > 0; a bra-first file or exchanged
    flip blocks give h > 0.
    """
    lx, ly, lz = split_operator(cso)
    commutator = lx @ ly - ly @ lx
    norm = np.einsum("nij,nji->n", lz, lz).real
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.einsum("nij,nji->n", commutator, lz).imag / norm ** 1.5


def gate_c0(cso: MatrixDump | np.ndarray, tol: float = 1e-12) -> GateResult:
    """Check the full z-axis SOC operator and its storage layout (Section 11).

    Structure: dd = -uu, uu imaginary antisymmetric with zero diagonal, flip-block
    Hermiticity, no empty ion. Layout: h < 0 on every ion (Section 4.2).
    """
    m = cso.matrix if isinstance(cso, MatrixDump) else np.asarray(cso)
    if (m.ndim != 4 or m.shape[0] != 4 or m.shape[-1] != m.shape[-2]
            or not m.size or not np.all(np.isfinite(m))):
        return GateResult("C0", False, None, tol, "Invalid/non-finite four-block CSO")
    uu, ud, du, dd = m
    errors = {
        "dd_plus_uu": float(np.max(np.abs(dd + uu))),
        "uu_real": float(np.max(np.abs(uu.real))),
        "uu_antisymmetry": float(np.max(np.abs(uu + uu.swapaxes(-1, -2)))),
        "uu_diagonal": float(np.max(np.abs(np.diagonal(uu, axis1=-2, axis2=-1)))) ,
        "flip_hermiticity": float(np.max(np.abs(ud - du.conj().swapaxes(-1, -2)))),
    }
    magnitudes = np.max(np.abs(m), axis=(0, 2, 3))
    flips = np.max(np.abs(ud), axis=(1, 2))
    h = handedness(m)
    value = {"errors": errors, "max_abs_per_ion": magnitudes.tolist(),
             "max_ud_per_ion": flips.tolist(), "handedness_per_ion": h.tolist()}
    left = bool(np.all(h < 0))
    passed = (max(errors.values()) <= tol and bool(np.all(magnitudes > tol))
              and bool(np.max(flips) > tol) and left)
    detail = "Full CSO Hermiticity, z-axis structure and handedness checked"
    if not np.max(flips) > tol:
        detail += "; all flip blocks are zero: Lambda_x and Lambda_y are missing"
    if not np.all(magnitudes > tol):
        detail += "; empty ion operator"
    if not left:
        detail += (f"; handedness h >= 0 on ions {(np.flatnonzero(~(h < 0)) + 1).tolist()}: "
                   "flip blocks exchanged or the file is not ket-first")
    return GateResult("C0", passed, value, tol, detail)


def gate_i0(imag, tol: float = 1e-6) -> GateResult:
    """Imaginary residual of the trace, every ion and axis (Section 11)."""
    values = np.asarray(imag, dtype=float)
    finite = bool(values.size) and bool(np.all(np.isfinite(values)))
    value = float(np.max(np.abs(values))) if finite else None
    return GateResult("I0", finite and value <= tol, value, tol,
                      "Maximum absolute imaginary trace per ion and axis")


def gate_n0(per_ion, sigma: float | None = None) -> GateResult:
    """Null at q = 0 on all three axes, total and per ion (Sections 4.5 and 11).

    The spin-only C2 rotation about the collinear axis maps the state onto
    itself atom by atom, so every atom's term vanishes, not only the sum.
    """
    t = np.asarray(per_ion, dtype=float)
    if t.ndim != 2 or t.shape[1] != 3 or not len(t):
        raise ValueError("N0 needs the real trace of every ion on all three axes")
    if sigma is not None and (not np.isfinite(sigma) or sigma < 0):
        raise ValueError("sigma must be finite and nonnegative")
    threshold = max(conventions.N0_FLOOR_EV, 3 * sigma if sigma is not None else 0)
    parts = np.vstack([t.sum(axis=0), t])
    finite = bool(np.all(np.isfinite(parts)))
    worst = float(np.max(np.abs(parts))) if finite else None
    value = {"total_eV": t.sum(axis=0).tolist(), "worst_eV": worst, "sigma_eV": sigma}
    return GateResult("N0", finite and worst < threshold, value, threshold,
                      "Frozen-state null: total and every ion, all three axes")


def gate_p0(plus, minus, tol: float = 0.1) -> GateResult:
    """Parity, Eq (4.9): the even part of T is at most tol of the odd part, or at the N0 floor."""
    plus, minus = np.asarray(plus, dtype=float), np.asarray(minus, dtype=float)
    even, odd = float(np.linalg.norm(plus + minus)), float(np.linalg.norm(plus - minus))
    # With inversion the odd part vanishes too; then the even part must sit at the floor.
    passed = even <= tol * odd or even < conventions.N0_FLOOR_EV
    return GateResult("P0", bool(passed), {"even_eV": even, "odd_eV": odd}, tol,
                      "|T(q) + T(-q)| <= tol |T(q) - T(-q)|, or below the N0 floor")


def gate_e0(e_plus: float, e_minus: float, e_zero: float, tol: float = 0.1) -> GateResult:
    """E(q) = E(-q), Eq (4.9), measured against the curvature numerator; no floor."""
    difference, curvature = abs(e_plus - e_minus), abs(e_plus + e_minus - 2 * e_zero)
    return GateResult("E0", difference <= tol * curvature,
                      {"difference_eV": difference, "curvature_eV": curvature}, tol,
                      "|E(q) - E(-q)| <= tol |E(q) + E(-q) - 2 E(0)|")


def gate_null(runs) -> GateResult:
    """Centrosymmetric null (Sections 7.3 and 11): with inversion kept, D = 0 and
    y_a(q) = 0 at every q, so every |T_a| of every traced run and ion is below
    N0_FLOOR_EV, not only the slope. runs: name -> per-ion T, shape (nions, 3)."""
    worst = (0.0, None, None, None)
    for name, per_ion in runs.items():
        t = np.abs(np.asarray(per_ion, float))
        ion, axis = np.unravel_index(np.argmax(t), t.shape)
        if t[ion, axis] >= worst[0]:
            worst = (float(t[ion, axis]), name, int(ion) + 1, "xyz"[axis])
    value = {"worst_eV": worst[0], "run": worst[1], "ion": worst[2], "axis": worst[3]}
    passed = worst[0] < conventions.N0_FLOOR_EV
    detail = "|T_a| of every traced run, ion and axis below the N0 floor"
    if not passed:
        detail = f"|T_{worst[3]}| = {worst[0]:.3e} eV on {worst[1]}, ion {worst[2]}, at or above the N0 floor"
    return GateResult("Null", passed, value, conventions.N0_FLOOR_EV, detail)


# Series truncation leaves a forbidden part of order 1e-4 to 1e-3 |D| at realistic t,
# which the parity sigma (noise only) cannot see; an axis, frame or transpose error is
# of order |D|. The Forbidden bound therefore adds this fraction of max|D_free| (D-023).
FORBIDDEN_FLOOR = 0.01


def gate_forbidden(forbidden, sigma, d_free, sigmas: float = 3.0) -> GateResult:
    """Section 11: |F_ij| <= 3 sigma(F_ij) + FORBIDDEN_FLOOR max|D_free| for every element.

    sigma covers noise only. With D = 0 the floor is zero and sigma alone decides.
    """
    forbidden, sigma = np.asarray(forbidden, float), np.asarray(sigma, float)
    scale = float(np.max(np.abs(d_free)))
    bound = sigmas * sigma + FORBIDDEN_FLOOR * scale
    passed = bool(np.all(np.abs(forbidden) <= bound))
    return GateResult("Forbidden", passed,
                      {"norm": float(np.linalg.norm(forbidden)),
                       "ratio_to_D_free": float(np.max(np.abs(forbidden)) / scale) if scale else None,
                       "worst_ratio": float(np.max(np.abs(forbidden) / np.maximum(bound, 1e-300)))},
                      sigmas, f"|F_ij| <= 3 sigma(F_ij) + {FORBIDDEN_FLOOR} max|D_free|; "
                              "sigma covers noise only, the floor covers series truncation")


NOT_EVALUATED = "not evaluated: no dump_C, an energies-only tree"


def check_tree(out, states, inversion=False) -> dict:
    """Trace every ok run from its files, then C0, N0, I0, P0, E0 and, when the kept
    operations contain inversion, the centrosymmetric null (Section 11).

    states is spiral.read_runs(out), q0 first. A tree with no dump_C directory is
    energies-only (item 2.10): only E0 applies and every trace check is not
    evaluated. A dump_C that exists but fails is an error. Writes traces.json as
    a report; no command reads it back (D-021).
    """
    out = Path(out)
    names = list(states)
    traced = (out / "dump_C").is_dir()
    lines, failures, runs, energies = [], [], {}, {}
    checks, cso = {}, None
    if traced:
        try:
            cso = load_cso(out / "dump_C" / "CSO.dat")
            checks["C0"] = gate_c0(cso).to_dict()
        except (OSError, ValueError) as error:
            checks["C0"] = {"name": "C0", "passed": False, "detail": str(error)}
        if not checks["C0"]["passed"]:
            failures.append("C0")
        lines.append(f"C0  {'pass' if checks['C0']['passed'] else 'FAIL: ' + checks['C0']['detail']}")
    else:
        checks["C0"] = {"name": "C0", "passed": None, "detail": NOT_EVALUATED}
        lines.append(f"C0, N0, I0 and P0 {NOT_EVALUATED}")

    for name in names:
        if "error" in states[name]:
            lines.append(f"{name:24} skipped: not ok in collect")
            continue
        energies[name] = states[name]["E_eV"]           # E0 needs no dump
        if cso is None:
            continue
        try:
            runs[name] = trace_run(out / name, cso)
            runs[name]["I0"] = gate_i0(runs[name]["imag_eV"]).to_dict()
            if not runs[name]["I0"]["passed"]:
                failures.append(f"I0 {name}")
            lines.append(f"{name:24} T = " + " ".join(f"{x:+.3e}" for x in runs[name]["T_eV"]) + " eV")
        except (OSError, ValueError, KeyError) as error:
            runs[name] = {"error": str(error)}
            failures.append(name)
            lines.append(f"{name:24} {error}")

    if not traced:
        checks["N0"] = {"name": "N0", "passed": None, "detail": NOT_EVALUATED}
    elif "q0" in runs and "error" not in runs["q0"]:
        checks["N0"] = gate_n0(runs["q0"]["per_ion_eV"]).to_dict()
    else:
        checks["N0"] = {"name": "N0", "passed": False, "detail": "q0 has no trace"}
    for name in ("P0", "E0"):
        checks[name] = {}
    for plus in [n for n in names if n.endswith("_plus")]:
        pair, minus = plus[:-len("_plus")], plus[:-len("_plus")] + "_minus"
        if plus in runs and minus in runs and "error" not in runs[plus] and "error" not in runs[minus]:
            checks["P0"][pair] = gate_p0(runs[plus]["T_eV"], runs[minus]["T_eV"]).to_dict()
        if plus in energies and minus in energies and "q0" in energies:
            checks["E0"][pair] = gate_e0(energies[plus], energies[minus], energies["q0"]).to_dict()
    # Gate at each direction's smallest t; every t is reported.
    for name in ("P0", "E0") if traced else ("E0",):
        for direction in sorted({n.split("_t")[0] for n in names if n.endswith("_plus")}):
            entry = checks[name].get(f"{direction}_t1")
            if entry is None or not entry["passed"]:
                failures.append(f"{name} {direction}")
    if checks["N0"]["passed"] is False:
        failures.append("N0")
    if not traced:
        checks["Null"] = {"name": "Null", "passed": None, "detail": NOT_EVALUATED}
    elif not inversion:
        checks["Null"] = {"name": "Null", "passed": None, "detail": "not applicable: inversion is not kept"}
    else:
        checks["Null"] = gate_null({n: r["per_ion_eV"] for n, r in runs.items() if "error" not in r}).to_dict()
        if not checks["Null"]["passed"]:
            failures.append(f"Null ({checks['Null']['detail']})")
    report = {"traced": traced, "runs": runs, "checks": checks, "passed": not failures, "failures": failures}
    manifest.save(report, out / "traces.json")
    if traced:
        lines.append(f"N0  {'pass' if checks['N0']['passed'] else 'FAIL'}")
        null = checks["Null"]
        lines.append(f"Null  {null['detail'] if null['passed'] is None else ('pass' if null['passed'] else 'FAIL: ' + null['detail'])}")
    lines += [f"{name}  {pair:12} {'pass' if g['passed'] else 'FAIL'}" for name in ("P0", "E0")
              for pair, g in checks[name].items()]
    report["lines"] = lines
    return report
