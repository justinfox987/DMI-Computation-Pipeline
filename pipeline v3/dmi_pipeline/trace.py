"""First-order SOC trace (math Section 4).

Production uses the trace vector of Eq (4.8): the run's COCC from dump_P and
the material's z-axis CSO from dump_C. The CPROJ contraction and its copied v2
loops stay as the independent reference route, and M1 compares the two inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from . import conventions, manifest
from .dumpio import CprojData, MatrixDump, Occupations, load_cocc, load_cso
from .realized import poscar


@dataclass(frozen=True)
class TraceResult:
    """One raw per-configuration Patch B trace; pairing occurs elsewhere."""

    delta_E1: float
    imag_total: float
    imag_per_ion: dict[int, float]
    per_ion: dict[int, float]
    sigma_eV: float | None = None
    provenance: dict[str, Any] | None = None
    per_k: np.ndarray | None = None
    axis: str = "z"


def _assert_trace_inputs(cproj: CprojData, ferwe: Occupations, cso: MatrixDump) -> None:
    """Reject data outside the unambiguous Patch B noncollinear trace contract."""

    header = cproj.header
    assert_state_inputs(cproj, ferwe)
    if header.ispin != 1:
        raise ValueError(
            f"Patch B trace requires ISPIN=1 with spinors in CPROJ, got ISPIN={header.ispin}"
        )
    if header.nrspinors != 2:
        raise ValueError(f"Patch B trace requires NRSPINORS=2, got {header.nrspinors}")
    if header.ncdij <= max(int(conventions.UU_IDX), int(conventions.DD_IDX)):
        raise ValueError(
            f"CSO/CPROJ NCDIJ={header.ncdij} does not contain UU/DD blocks "
            f"{conventions.UU_IDX}/{conventions.DD_IDX}"
        )
    if ferwe.metadata.nkpts != header.nkpts_global:
        raise ValueError(
            f"FERWE NKPTS={ferwe.metadata.nkpts} disagrees with CPROJ NKPTS={header.nkpts_global}"
        )
    if ferwe.metadata.nbands != header.nbands_global:
        raise ValueError(
            f"FERWE NBANDS={ferwe.metadata.nbands} disagrees with CPROJ NBANDS={header.nbands_global}"
        )
    if ferwe.metadata.ispin != header.ispin:
        raise ValueError(f"FERWE ISPIN={ferwe.metadata.ispin} disagrees with CPROJ ISPIN={header.ispin}")
    if cso.metadata.nions != header.nions or cso.metadata.lmdim != header.lmdim:
        raise ValueError(
            "CSO dimensions disagree with CPROJ: "
            f"CSO NIONS/LMDIM={cso.metadata.nions}/{cso.metadata.lmdim}, "
            f"CPROJ NIONS/LMDIM={header.nions}/{header.lmdim}"
        )
    if cso.metadata.ncdij != header.ncdij:
        raise ValueError(f"CSO NCDIJ={cso.metadata.ncdij} disagrees with CPROJ NCDIJ={header.ncdij}")
    if ferwe.metadata.nelect is None or not np.isclose(ferwe.metadata.nelect, header.nelect, atol=1.0e-6, rtol=0.0):
        raise ValueError(f"FERWE NELECT={ferwe.metadata.nelect} disagrees with CPROJ NELECT={header.nelect}")
    if cso.metadata.nelect is not None and not np.isclose(cso.metadata.nelect, header.nelect, atol=1.0e-6, rtol=0.0):
        raise ValueError(f"CSO NELECT={cso.metadata.nelect} disagrees with CPROJ NELECT={header.nelect}")
    if ferwe.occupations.shape != (1, header.nkpts_global, header.nbands_global):
        raise ValueError(
            f"FERWE occupations have shape {ferwe.occupations.shape}, expected "
            f"{(1, header.nkpts_global, header.nbands_global)}"
        )
    if ferwe.weights.shape != (header.nkpts_global,):
        raise ValueError(
            f"FERWE weights have shape {ferwe.weights.shape}, expected {(header.nkpts_global,)}"
        )


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


def compute_delta_E1(cproj: CprojData, ferwe: Occupations, cso: MatrixDump) -> TraceResult:
    """Diagonal-block contraction, retaining real and imaginary decompositions."""
    _assert_trace_inputs(cproj, ferwe, cso)
    if not np.all(np.isfinite(cso.matrix)):
        raise ValueError("Non-finite CSO matrix")
    weights = ferwe.weights[:, None] * ferwe.occupations[0]
    by_ion_k = np.zeros((cproj.header.nions, cproj.header.nkpts_global), complex)
    for ion, lmmax in enumerate(cproj.header.lmmax_ion):
        for spin, block in ((0, conventions.UU_IDX), (1, conventions.DD_IDX)):
            c = cproj.c[0, :, ion, spin, :lmmax, :]
            by_ion_k[ion] += np.einsum(
                "kib,ij,kjb,kb->k", c.conj(), cso.matrix[block, ion, :lmmax, :lmmax],
                c, weights, optimize=True,
            )
    ion_totals = by_ion_k.sum(axis=1)
    total = ion_totals.sum()
    return TraceResult(float(total.real), float(total.imag),
                       dict(enumerate(ion_totals.imag.tolist())),
                       dict(enumerate(ion_totals.real.tolist())),
                       per_k=by_ion_k.sum(axis=0))


def compute_delta_E1_reference(cproj: CprojData, ferwe: Occupations, cso: MatrixDump) -> TraceResult:
    """Contract Patch B CPROJ, FERWE, and diagonal CSO blocks exactly.

    Only the spin-diagonal ``uu`` and ``dd`` blocks contribute.  The explicit
    loops are intentional: they expose the writer-aligned indices and preserve
    per-ion/per-k accumulators needed by trace diagnostics.
    """

    _assert_trace_inputs(cproj, ferwe, cso)
    header = cproj.header
    total = np.complex128(0.0)
    per_k = np.zeros(header.nkpts_global, dtype=np.complex128)
    imag_per_ion: dict[int, float] = {}
    per_ion: dict[int, float] = {}
    spin_blocks = ((0, int(conventions.UU_IDX)), (1, int(conventions.DD_IDX)))

    for ion in range(header.nions):
        lmmax = header.lmmax_ion[ion]
        trace_ion = np.complex128(0.0)
        for kpoint in range(header.nkpts_global):
            trace_k_ion = np.complex128(0.0)
            for band in range(header.nbands_global):
                weight = np.float64(ferwe.weights[kpoint] * ferwe.occupations[0, kpoint, band])
                if weight == 0.0:
                    continue
                for spinor, matrix_block in spin_blocks:
                    contribution = np.complex128(0.0)
                    for bra_lm in range(lmmax):
                        bra = np.conj(cproj.c[0, kpoint, ion, spinor, bra_lm, band])
                        for ket_lm in range(lmmax):
                            ket = cproj.c[0, kpoint, ion, spinor, ket_lm, band]
                            contribution += bra * cso.matrix[matrix_block, ion, bra_lm, ket_lm] * ket
                    trace_k_ion += contribution * weight
            trace_ion += trace_k_ion
            per_k[kpoint] += trace_k_ion
        imag_per_ion[ion] = float(trace_ion.imag)
        per_ion[ion] = float(trace_ion.real)
        total += trace_ion

    return TraceResult(
        delta_E1=float(total.real),
        imag_total=float(total.imag),
        imag_per_ion=imag_per_ion,
        per_ion=per_ion,
        per_k=per_k,
    )


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
