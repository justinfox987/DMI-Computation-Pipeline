"""Acceptance checks through N0. Gate results contain evidence, not global pins."""

from dataclasses import asdict, dataclass
from typing import Any, Sequence

import numpy as np

from . import conventions
from .dumpio import CprojData, MatrixDump, Occupations
from .trace import TraceResult, assert_state_inputs


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


def gate_i0(trace: TraceResult, tol: float = 1e-6) -> GateResult:
    components = [trace.imag_total, *trace.imag_per_ion.values()]
    finite = bool(np.all(np.isfinite(components)))
    value = float(np.max(np.abs(components))) if finite else None
    return GateResult("I0", finite and value <= tol, value, tol,
                      "Maximum absolute imaginary trace, total and per ion")


def gate_n0(trace: TraceResult, species: Sequence[str], sigma_restart: float | None = None) -> GateResult:
    """Null for an independently verified in-plane collinear q=psi=0 state.

    Spin-only C2x leaves its occupied projector invariant and reverses the
    diagonal SOC operator. No Patch A noise measurement is inherited.
    """
    if trace.axis != "z":
        raise ValueError("N0 must use the z trace")
    if sigma_restart is not None and (not np.isfinite(sigma_restart) or sigma_restart < 0):
        raise ValueError("sigma_restart must be finite and nonnegative")
    if set(trace.per_ion) != set(range(len(species))) or not species:
        raise ValueError("N0 needs a species label and real trace for every ion")
    threshold = max(conventions.N0_FLOOR_EV, 3 * sigma_restart if sigma_restart is not None else 0)
    parts = [trace.delta_E1, *trace.per_ion.values()]
    finite = bool(np.all(np.isfinite(parts)))
    worst = float(np.max(np.abs(parts))) if finite else None
    bi = {str(i + 1): trace.per_ion[i] for i, symbol in enumerate(species) if symbol == "Bi"}
    bi_warning = any(abs(v) >= 0.8 * threshold for v in bi.values())
    value = {"total_eV": trace.delta_E1, "per_ion_eV": {str(i + 1): v for i, v in trace.per_ion.items()},
             "Bi_eV": bi, "Bi_near_threshold": bi_warning, "sigma_restart_eV": sigma_restart}
    passed = finite and worst < threshold and not bi_warning
    detail = "Frozen-state null: total and every ion must pass"
    if bi_warning:
        detail += "; Bi near threshold: review required, acceptance withheld"
    return GateResult("N0", bool(passed), value, threshold, detail)
