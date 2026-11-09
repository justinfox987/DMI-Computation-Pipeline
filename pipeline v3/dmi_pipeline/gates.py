"""Section 11 checks, dump provenance and the dmi trace run. Results carry evidence, not global pins."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from . import conventions, manifest, spiral
from .dumpio import CprojData, MatrixDump, Occupations, load_cocc, load_cproj, load_cso, load_ferwe
from .realized import echo_check
from .trace import assert_state_inputs, split_operator, trace_run

AXES = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    value: Any
    threshold: Any
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


def gate_c0(cso: MatrixDump | np.ndarray, tol: float = 1e-12) -> GateResult:
    """Check the full z-axis SOC operator; flip blocks are never forced to zero.

    Nonzero flip blocks are required for this material's later T3 validation.
    Species-dependent magnitudes are reported separately, not hardcoded into
    a structural Hermiticity test.
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
    value = {"errors": errors, "max_abs_per_ion": magnitudes.tolist(),
             "max_ud_per_ion": flips.tolist()}
    passed = max(errors.values()) <= tol and bool(np.all(magnitudes > tol)) and bool(np.max(flips) > tol)
    detail = "Full CSO Hermiticity and z-axis structure checked"
    if not np.max(flips) > tol:
        detail += "; all flip blocks are zero: incomplete operator for T3"
    if not np.all(magnitudes > tol):
        detail += "; empty ion operator"
    return GateResult("C0", passed, value, tol, detail)


def rebuild_cocc(cproj: CprojData, ferwe: Occupations) -> np.ndarray:
    """Vectorized transcription of COCC_FROM_INPUT, including its block order.

    Fortran stores conj(c_bra[LP])*c_ket[L] at IS=1+bra+2*ket.
    No CSO off-diagonal packing assumption enters this calculation.
    """
    assert_state_inputs(cproj, ferwe)
    h = cproj.header
    if h.ncdij != 4:
        raise ValueError("M1 requires four noncollinear COCC blocks")
    result = np.zeros((4, h.nions, h.lmdim, h.lmdim), complex)
    weights = ferwe.spin_factor * ferwe.weights[:, None] * ferwe.occupations[0]
    for ion, lmmax in enumerate(h.lmmax_ion):
        for block, (bra, ket) in enumerate(conventions.COCC_SPIN_BLOCKS):
            result[block, ion, :lmmax, :lmmax] = np.einsum(
                "kib,kjb,kb->ij", cproj.c[0, :, ion, bra, :lmmax].conj(),
                cproj.c[0, :, ion, ket, :lmmax], weights, optimize=True,
            )
    return result


def gate_m1(cproj: CprojData, ferwe: Occupations, cocc: MatrixDump, tol: float = 1e-10) -> GateResult:
    rebuilt = rebuild_cocc(cproj, ferwe)
    if cocc.matrix.shape != rebuilt.shape or not np.all(np.isfinite(cocc.matrix)):
        return GateResult("M1", False, None, tol, "COCC dimensions or values invalid")
    if cocc.metadata.nelect is None or not np.isclose(cocc.metadata.nelect, cproj.header.nelect, atol=1e-6, rtol=0):
        return GateResult("M1", False, None, tol, "COCC NELECT disagrees with CPROJ")
    diff = np.abs(rebuilt - cocc.matrix)
    where = tuple(int(i) + 1 for i in np.unravel_index(np.argmax(diff), diff.shape))
    deviation = float(diff.max())
    return GateResult("M1", deviation <= tol, deviation, tol,
                      f"Maximum mismatch at (IS, ION, I, J)={where}")


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


def gate_forbidden(forbidden, sigma, d_free, sigmas: float = 3.0) -> GateResult:
    """Section 11: the forbidden part of D_free vanishes within 3 sigma, element by element.

    A relative floor of 1e-9 of D_free absorbs roundoff where sigma is exactly zero.
    """
    forbidden, sigma = np.asarray(forbidden, float), np.asarray(sigma, float)
    bound = sigmas * sigma + 1e-9 * float(np.max(np.abs(d_free)))
    return GateResult("Forbidden", bool(np.all(np.abs(forbidden) <= bound)),
                      {"norm": float(np.linalg.norm(forbidden)), "worst_ratio": float(np.max(np.abs(forbidden) / np.maximum(bound, 1e-300)))},
                      sigmas, "|F_ij| <= 3 sigma(F_ij) for every element")


def gate_t3(z: MatrixDump, dump: MatrixDump, axis: str, tol: float = 1e-10) -> GateResult:
    """Section 11 T3: C_uu of a genuine SAXIS = axis dump equals Lambda_axis from the z dump."""
    lam = split_operator(z)["xyz".index(axis)]
    uu = dump.matrix[conventions.UU_IDX]
    if uu.shape != lam.shape:
        return GateResult("T3", False, None, tol, f"{axis} dump dimensions differ from the z dump")
    error, reversed_ = float(np.max(np.abs(uu - lam))), float(np.max(np.abs(uu + lam)))
    detail = f"C_uu at SAXIS = {axis} against Lambda_{axis} of Eq (4.4)"
    if error > tol and axis == "y" and reversed_ <= tol:
        detail = "C_uu matches -Lambda_y: the CSO flip blocks are stored du, ud; correct conventions.py"
    return GateResult("T3", error <= tol, {"axis": axis, "error": error}, tol, detail)


def t3(z_path, x_path, y_path) -> dict:
    """Validate genuine x/y dumps against the z operator from one build (dmi t3)."""
    paths = [Path(path) for path in (z_path, x_path, y_path)]
    outcars = [path.parent / "OUTCAR" for path in paths]
    banners = {outcar.read_text(encoding="utf-8", errors="replace").splitlines()[0].strip()
               for outcar in outcars}
    if len(banners) != 1:
        raise ValueError("T3 dumps must come from one build")
    z = load_cso(paths[0])
    checks = {axis: gate_t3(z, load_cso(path, expect_saxis=AXES[axis]), axis).to_dict()
              for axis, path in (("x", paths[1]), ("y", paths[2]))}
    return {"name": "T3", "passed": all(c["passed"] for c in checks.values()), "checks": checks,
            "build_banner": banners.pop(), "files": manifest.fingerprints(paths + outcars)}


# ---- dump provenance and the run tree -------------------------------------

def completed(directory: Path) -> bool:
    outcar = directory / "OUTCAR"
    return outcar.exists() and "General timing and accounting" in outcar.read_text(encoding="utf-8", errors="replace")


def finish(dump_dir, kind: str, out) -> dict:
    """Check one finished dump and write its provenance.json; failures are recorded too."""
    dump_dir, out = Path(dump_dir), Path(out)
    record = {"kind": kind, "passed": False, "checks": {}, "files": {}, "parent": None,
              "build_banner": None, "error": None}
    try:
        record["parent"] = manifest.load(dump_dir / "parent.json")["parent"]
        spiral.parent_unchanged(dump_dir)
        record["checks"]["incar_echo"] = echo_check(dump_dir)
        record["build_banner"] = (dump_dir / "OUTCAR").read_text(errors="replace").splitlines()[0].strip()
        names, result = ["INCAR", "OUTCAR"], None
        if kind == "dump_P":
            cocc = load_cocc(dump_dir / "COCC.dat")
            names.append("COCC.dat")
            if record["parent"] == "q0":                  # M1 on the first state (D-011)
                cproj = load_cproj(dump_dir)
                result = gate_m1(cproj, load_ferwe(dump_dir), cocc)
                names += [str(f.path.relative_to(dump_dir)) for f in cproj.files] + ["FERWE.dat"]
        else:
            axis = {"dump_C": "z", "dump_C_x": "x", "dump_C_y": "y"}[kind]
            cso = load_cso(dump_dir / "CSO.dat", expect_saxis=AXES[axis])
            names.append("CSO.dat")
            if axis == "z":
                result = gate_c0(cso)
            else:
                manifest.require_done(out / "dump_C", "dump_C", out)
                result = gate_t3(load_cso(out / "dump_C" / "CSO.dat"), cso, axis)
        if result is not None:
            record["checks"][result.name] = result.to_dict()
        record["files"] = {str((dump_dir / n).relative_to(out)): manifest.file_hash(dump_dir / n) for n in names}
        record["passed"] = all(check["passed"] for check in record["checks"].values())
        if not record["passed"]:
            record["error"] = "failed " + ", ".join(k for k, c in record["checks"].items() if not c["passed"])
    except (OSError, ValueError, KeyError) as error:
        record["error"] = str(error)
    manifest.save(record, dump_dir / "provenance.json")
    return record


def check_tree(out) -> dict:
    """dmi trace: finish new dumps, trace every ok run, then N0, I0, P0, E0 and T3."""
    out = Path(out)
    names = (out / "runs.txt").read_text(encoding="utf-8").split()
    collected = manifest.load(out / "collected.json")
    lines, failures = [], []

    dumps = [(out / d, d) for d in spiral.CSO_DUMPS] + [(out / n / "dump_P", "dump_P") for n in names]
    status = {}
    for directory, kind in dumps:                         # dump_C first: T3 needs it
        label = str(directory.relative_to(out))
        if not directory.exists():
            continue
        if not (directory / "provenance.json").exists():
            if not completed(directory):
                status[label] = "missing"
                lines.append(f"{label:24} missing")
                continue
            finish(directory, kind, out)
        record = manifest.load(directory / "provenance.json")
        status[label] = "ok" if record["passed"] else record["error"]
        lines.append(f"{label:24} {status[label]}")

    runs, energies = {}, {}
    for name in names:
        result = collected.get(name, {"error": "missing"})
        if "error" in result:
            lines.append(f"{name:24} skipped: not ok in collect")
            continue
        try:
            spiral.unchanged(out / name, result["sha256"], "dmi collect")
            energies[name] = result["E_eV"]            # E0 needs no dump
            runs[name] = trace_run(out / name, out)
            runs[name]["I0"] = gate_i0(runs[name]["imag_eV"]).to_dict()
            if not runs[name]["I0"]["passed"]:
                failures.append(f"I0 {name}")
            lines.append(f"{name:24} T = " + " ".join(f"{x:+.3e}" for x in runs[name]["T_eV"]) + " eV")
        except (OSError, ValueError, KeyError) as error:
            runs[name] = {"error": str(error)}
            failures.append(name)
            lines.append(f"{name:24} {error}")

    checks = {}
    if "q0" in runs and "error" not in runs["q0"]:
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
    for name in ("P0", "E0"):
        for direction in sorted({n.split("_t")[0] for n in names if n.endswith("_plus")}):
            entry = checks[name].get(f"{direction}_t1")
            if entry is None or not entry["passed"]:
                failures.append(f"{name} {direction}")
    if not checks["N0"]["passed"]:
        failures.append("N0")
    t3 = {axis: status.get(f"dump_C_{axis}", "not run") for axis in "xy"}
    for axis, state in t3.items():
        if state not in ("ok", "not run", "missing"):
            failures.append(f"T3 {axis}")
    checks["T3"] = t3
    report = {"runs": runs, "checks": checks, "dumps": status,
              "T_y": "confirmed by T3" if t3["y"] == "ok" else "provisional: CSO flip-block order unpinned until T3",
              "passed": not failures, "failures": failures}
    manifest.save(report, out / "traces.json")
    lines += [f"N0  {'pass' if checks['N0']['passed'] else 'FAIL'}",
              *(f"{name}  {pair:12} {'pass' if g['passed'] else 'FAIL'}" for name in ("P0", "E0")
                for pair, g in checks[name].items()),
              f"T3  x {t3['x']}, y {t3['y']}", f"T_y {report['T_y']}"]
    report["lines"] = lines
    return report
