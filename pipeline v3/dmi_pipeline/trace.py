"""First-order SOC trace (math Section 4).

The trace vector of Eq (4.8) from a run's dump_P COCC and the material's z-axis
CSO from dump_C. Both files are read again on every call (D-021).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from . import conventions, manifest
from .dumpio import MatrixDump, load_cocc
from .realized import poscar


def split_operator(cso: MatrixDump | np.ndarray) -> np.ndarray:
    """(Lambda_x, Lambda_y, Lambda_z) per ion from the four CSO blocks, Eq (4.4).

    Block order uu, ud, du, dd. Lambda_y depends on the ud/du order, which the
    handedness condition of gate_c0 checks (math Section 4.2).
    """
    uu, ud, du, dd = cso.matrix if isinstance(cso, MatrixDump) else cso
    return np.array([(ud + du) / 2, (du - ud) / 2j, (uu - dd) / 2])


def trace_vector(cocc: MatrixDump, lam: np.ndarray) -> np.ndarray:
    """Per-ion T_alpha of Eq (4.8), shape (nions, 3), complex.

    CSO.dat and COCC.dat both store the ket index first, so this is VASP's own
    SOC energy form, Re sum CSO * conj(COCC) (math Section 4.4, D-020). Without
    the conjugate every T reverses sign.
    """
    magnetization = cocc.matrix[conventions.UU_IDX] - cocc.matrix[conventions.DD_IDX]
    return np.einsum("anij,nij->na", lam, magnetization.conj())


def trace_run(run: Path, cso: MatrixDump) -> dict:
    """Trace vector of one run from its dump_P/COCC.dat and the material CSO.

    The one guard of D-021: a COCC.dat older than its parent's OUTCAR belongs to
    an earlier state of that run.
    """
    run = Path(run)
    path = run / "dump_P" / "COCC.dat"
    if path.stat().st_mtime_ns < (run / "OUTCAR").stat().st_mtime_ns:
        raise ValueError("dump_P/COCC.dat is older than the run's OUTCAR; rerun its dump")
    cocc = load_cocc(path)
    nions = len(poscar(run / "POSCAR")[1])
    shapes = {(m.nions, m.lmdim, m.ncdij) for m in (cso.metadata, cocc.metadata)}
    if len(shapes) != 1 or cso.metadata.nions != nions:
        raise ValueError(f"CSO and COCC dimensions differ or do not match the {nions} POSCAR ions")
    if cocc.metadata.nelect is None or not np.isclose(cso.metadata.nelect, cocc.metadata.nelect, atol=1e-6, rtol=0):
        raise ValueError("CSO and COCC NELECT differ")
    t = trace_vector(cocc, split_operator(cso))
    return {"q_frac": manifest.load(run / "config.json")["q_frac"], "T_eV": t.real.sum(axis=0).tolist(),
            "per_ion_eV": t.real.tolist(), "imag_eV": t.imag.tolist()}
