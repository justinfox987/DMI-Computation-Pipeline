"""Patch B first-order SOC trace contraction.

Production tracing consumes only the self-indexed ``dump_P`` artifacts emitted
for one configuration and a material-level, axis-specific ``CSO_<axis>.dat``.
The production contraction uses einsum per ion to bound temporary memory;
the copied v2 loops remain an independent numerical reference.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import numpy as np

from . import conventions, manifest
from .cso import rotate_saxis
from .dumpio import CprojData, MatrixDump, Occupations, assert_header, load_cproj, load_cso, load_ferwe


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


def _load_config_q_frac(cfg_dir: Path) -> tuple[float, float, float]:
    """Read the declared configuration q vector from its self-description."""

    config_path = cfg_dir / "config.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"Patch B trace requires configuration metadata at {config_path}")
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Configuration metadata is not valid JSON: {config_path}") from error
    q_frac = payload.get("q_frac")
    if not isinstance(q_frac, list) or len(q_frac) != 3:
        raise ValueError(f"Configuration metadata has no three-component q_frac: {config_path}")
    try:
        q = tuple(float(value) for value in q_frac)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Configuration q_frac is not numeric: {config_path}") from error
    if not np.all(np.isfinite(q)):
        raise ValueError(f"Configuration q_frac contains a non-finite value: {config_path}")
    return q


def _assert_done_marker(directory: Path, label: str) -> None:
    """Enforce the completed-artifact boundary required by Patch B readers."""

    manifest.require_done(directory, label)


def _trace_provenance(cproj: CprojData, ferwe: Occupations, cso: MatrixDump, axis: str, q_frac: tuple[float, float, float]) -> dict[str, Any]:
    """Return JSON-safe immutable identities for every input artifact."""

    return {
        "axis": axis,
        "q_frac": list(q_frac),
        "build_id": cproj.header.build_id,
        "cproj": [
            {"path": str(file.path), "sha256": file.sha256}
            for file in cproj.files
        ],
        "ferwe": {"path": str(ferwe.provenance.path), "sha256": ferwe.provenance.sha256},
        "cso": {"path": str(cso.provenance.path), "sha256": cso.provenance.sha256},
    }


def trace_config(cfg_dir: Path, cso_dir: Path, axis: str) -> TraceResult:
    """Trace one completed Patch B configuration against one material CSO axis.

    ``cfg_dir`` must be the configuration directory containing ``config.json``
    and its completed ``dump_P`` child. ``cso_dir`` contains the material-level
    ``CSO_x.dat``, ``CSO_y.dat``, or ``CSO_z.dat`` artifact. Gate execution is
    intentionally outside this reader; this function enforces only the input
    contracts that make its result meaningful.
    """

    config_directory = Path(cfg_dir)
    material_cso_directory = Path(cso_dir)
    if axis not in {"x", "y", "z"}:
        raise ValueError("axis must be x, y, or z")
    config = manifest.load(config_directory / "config.json")
    dump_directory = Path(config.get("dirs", {}).get("dump_P", config_directory / "dump_P"))
    _assert_done_marker(dump_directory, "dump_P")
    q_frac = _load_config_q_frac(config_directory)

    cproj = load_cproj(dump_directory)
    ferwe = load_ferwe(dump_directory)
    cso = load_cso(material_cso_directory / "CSO_z.dat")
    evidence = manifest.load(material_cso_directory / "provenance.json")
    if evidence.get("passed") is not True or not evidence["checks"]["C0"]["passed"]:
        raise ValueError("CSO has no passing C0 evidence")
    manifest.check_files(evidence["files"])
    rotation_path = material_cso_directory / "rotation.json"
    rotation = manifest.load(rotation_path) if axis != "z" and rotation_path.exists() else None
    cso = rotate_saxis(cso, axis, rotation)
    assert_header(cproj.header, expect_lsorbit=False,
                  expect_lspiral=True if any(q_frac) else None, q_frac=q_frac)
    if conventions.VASP_BUILD_ID is not conventions.UNDETERMINED:
        if cproj.header.build_id != conventions.VASP_BUILD_ID:
            raise ValueError(
                f"CPROJ build id is {cproj.header.build_id!r}, expected pinned "
                f"{conventions.VASP_BUILD_ID!r}"
            )

    result = compute_delta_E1(cproj, ferwe, cso)
    provenance = _trace_provenance(cproj, ferwe, cso, axis, q_frac)
    if rotation is not None:
        provenance["rotation"] = rotation
    return TraceResult(
        delta_E1=result.delta_E1,
        imag_total=result.imag_total,
        imag_per_ion=result.imag_per_ion,
        per_ion=result.per_ion,
        sigma_eV=result.sigma_eV,
        per_k=result.per_k,
        provenance=provenance,
        axis=axis,
    )
