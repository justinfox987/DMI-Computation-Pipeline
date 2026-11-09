"""First-order SOC trace (math Section 4).

Production uses the trace vector of Eq (4.8): the run's COCC from dump_P and
the material's z-axis CSO from dump_C. The CPROJ contraction of Eq (4.7) is the
test oracle (tests/fixtures.py), and M1 compares the two inputs.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from . import conventions, manifest
from .dumpio import CprojData, MatrixDump, Occupations, load_cocc, load_cso
from .realized import poscar


def assert_state_inputs(cproj: CprojData, ferwe: Occupations) -> None:
    """Prove FERWE belongs to these indexed, noncollinear projections."""
    h = cproj.header
    if h.ispin != 1 or h.nrspinors != 2 or not h.lnoncollinear or h.lsorbit:
        raise ValueError("Trace requires SOC-free noncollinear ISPIN=1, NRSPINORS=2")
    if ferwe.spin_factor != 1.0:
        raise ValueError("Noncollinear spinors require RSPIN=1; do not double-count electrons")
    if not np.isclose(ferwe.metadata.nelect, h.nelect, atol=1e-6, rtol=0):
        raise ValueError("FERWE NELECT disagrees with CPROJ")
    for name, actual, expected, tol in (
        ("occupations", ferwe.occupations, cproj.occupations, 1e-8),
        ("weights", ferwe.weights[None, :], cproj.weights, 1e-12),
        ("eigenvalues", ferwe.eigenvalues, cproj.eigenvalues.real, 1e-10),
    ):
        if actual.shape != expected.shape or not np.allclose(actual, expected, atol=tol, rtol=0):
            raise ValueError(f"FERWE {name} disagree with CPROJ from the same capture")
    if not np.all(np.isfinite(cproj.c)):
        raise ValueError("Non-finite CPROJ coefficients")


def split_operator(cso: MatrixDump) -> np.ndarray:
    """(Lambda_x, Lambda_y, Lambda_z) per ion from the four CSO blocks, Eq (4.4).

    Block order uu, ud, du, dd as gate_c0 reads it. Lambda_y depends on the
    ud/du order, which T3 checks against a genuine SAXIS = y dump.
    """
    uu, ud, du, dd = cso.matrix
    return np.array([(ud + du) / 2, (du - ud) / 2j, (uu - dd) / 2])


def trace_vector(cocc: MatrixDump, lam: np.ndarray) -> np.ndarray:
    """Per-ion T_alpha of Eq (4.8), shape (nions, 3), complex.

    COCC[i, j] = rho[j, i], so Tr[Lambda rho] is the elementwise sum of
    Lambda * COCC; a matrix trace would insert the wrong transpose.
    """
    magnetization = cocc.matrix[conventions.UU_IDX] - cocc.matrix[conventions.DD_IDX]
    return np.einsum("anij,nij->na", lam, magnetization)


def trace_run(run: Path, out: Path) -> dict:
    """Trace vector of one collected run from its dump_P and the material dump_C."""
    run, out = Path(run), Path(out)
    manifest.require_done(out / "dump_C", "dump_C", out)
    manifest.require_done(run / "dump_P", "dump_P", out)
    cso, cocc = load_cso(out / "dump_C" / "CSO.dat"), load_cocc(run / "dump_P" / "COCC.dat")
    nions = len(poscar(run / "POSCAR")[1])
    shapes = {(m.nions, m.lmdim, m.ncdij) for m in (cso.metadata, cocc.metadata)}
    if len(shapes) != 1 or cso.metadata.nions != nions:
        raise ValueError(f"{run.name}: CSO and COCC dimensions differ or do not match the {nions} POSCAR ions")
    if cocc.metadata.nelect is None or not np.isclose(cso.metadata.nelect, cocc.metadata.nelect, atol=1e-6, rtol=0):
        raise ValueError(f"{run.name}: CSO and COCC NELECT differ")
    t = trace_vector(cocc, split_operator(cso))
    return {"q_frac": manifest.load(run / "config.json")["q_frac"], "T_eV": t.real.sum(axis=0).tolist(),
            "per_ion_eV": t.real.tolist(), "imag_eV": t.imag.tolist(),
            "sha256": {"COCC": cocc.provenance.sha256, "CSO": cso.provenance.sha256}}
