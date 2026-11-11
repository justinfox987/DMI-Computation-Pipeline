"""Readers for the two Patch B dump files the pipeline uses: CSO.dat and COCC.dat.

Both are formatted text with comment metadata from csodump.F, and both store the
ket index first (math Section 4.2). The CPROJ and FERWE readers serve check M1,
which runs once per build from acceptance/m1.py (D-021).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re

import numpy as np

ELECTRON_TOLERANCE = 1.0e-6


@dataclass(frozen=True)
class TextMetadata:
    """Metadata preserved from one formatted Patch B dump."""

    kind: str
    label: str
    lmdim: int | None
    nions: int | None
    ncdij: int | None
    set_dd_paw_call: int | None
    lsorbit: bool | None
    lnoncollinear: bool | None
    lspiral: bool | None
    qspiral: tuple[float, float, float] | None
    saxis: tuple[float, float, float] | None
    nelect: float | None
    raw_lines: tuple[str, ...]


@dataclass(frozen=True)
class MatrixDump:
    """CSO or COCC data in ``(IS, ION, I, J)`` order, all zero-based."""

    matrix: np.ndarray
    metadata: TextMetadata
    trace_by_ion: tuple[float, ...] | None = None
    trace_total: float | None = None


def _parse_fortran_bool(value: str, description: str) -> bool:
    normal = value.strip().upper()
    if normal in ("T", ".TRUE."):
        return True
    if normal in ("F", ".FALSE."):
        return False
    raise ValueError(f"{description} has invalid Fortran logical value {value!r}")


def _parse_float(value: str, description: str) -> float:
    try:
        result = float(value.replace("D", "E").replace("d", "e"))
    except ValueError as error:
        raise ValueError(f"{description} is not a floating-point value: {value!r}") from error
    if not math.isfinite(result):
        raise ValueError(f"{description} is not finite")
    return result


def _read_text_lines(path: Path) -> tuple[tuple[str, ...], list[str]]:
    raw_lines = tuple(path.read_text(encoding="utf-8").splitlines())
    data_lines = [line for line in raw_lines if line.strip() and not line.lstrip().startswith("#")]
    return raw_lines, data_lines


def _parse_text_metadata(path: Path, kind: str) -> tuple[TextMetadata, list[str]]:
    raw_lines, data_lines = _read_text_lines(path)
    comments = [line.strip() for line in raw_lines if line.strip().startswith("#")]
    if not comments or not comments[0].startswith("# HEIDE_PATCH_B "):
        raise ValueError(f"{path}: missing exact '# HEIDE_PATCH_B <label>' first metadata line")
    label = comments[0][len("# HEIDE_PATCH_B "):].strip()
    expected_labels = {
        "cso": "last nonzero SET_DD_PAW",
        "cocc": "PRE_LOOP input CPROJ",
    }
    if label != expected_labels[kind]:
        raise ValueError(f"{path}: {kind.upper()} label is {label!r}, expected {expected_labels[kind]!r}")
    values: dict[str, object] = {
        "lmdim": None, "nions": None, "ncdij": None, "set_dd_paw_call": None, "lsorbit": None,
        "lnoncollinear": None, "lspiral": None, "qspiral": None, "saxis": None, "nelect": None,
    }
    for line in comments[1:]:
        body = line[1:].strip()
        parts = body.split()
        if body.startswith("LMDIM NIONS NCDIJ"):
            if len(parts) != 6:
                raise ValueError(f"{path}: malformed LMDIM/NIONS/NCDIJ metadata")
            values["lmdim"], values["nions"], values["ncdij"] = (int(parts[3]), int(parts[4]), int(parts[5]))
        elif body.startswith("SET_DD_PAW_CALL"):
            if len(parts) != 2:
                raise ValueError(f"{path}: malformed SET_DD_PAW_CALL metadata")
            values["set_dd_paw_call"] = int(parts[1])
        elif body.startswith("LSORBIT="):
            fields = re.fullmatch(r"LSORBIT=\s*(\S+)\s+LNONCOLLINEAR=\s*(\S+)\s+LSPIRAL=\s*(\S+)", body)
            if fields is None:
                raise ValueError(f"{path}: malformed logical metadata")
            for key, value in zip(("lsorbit", "lnoncollinear", "lspiral"), fields.groups()):
                values[key] = _parse_fortran_bool(value, key)
        elif body.startswith("QSPIRAL"):
            if len(parts) != 4:
                raise ValueError(f"{path}: malformed QSPIRAL metadata")
            values["qspiral"] = tuple(_parse_float(value, "QSPIRAL") for value in parts[1:])
        elif body.startswith("SAXIS"):
            if len(parts) != 4:
                raise ValueError(f"{path}: malformed SAXIS metadata")
            values["saxis"] = tuple(_parse_float(value, "SAXIS") for value in parts[1:])
        elif body.startswith("NELECT"):
            if len(parts) != 2:
                raise ValueError(f"{path}: malformed NELECT metadata")
            values["nelect"] = _parse_float(parts[1], "NELECT")
    if None in (values["lmdim"], values["nions"], values["ncdij"]):
        raise ValueError(f"{path}: {kind.upper()} lacks required LMDIM/NIONS/NCDIJ metadata")
    if kind == "cso" and None in (values["set_dd_paw_call"], values["lsorbit"], values["lnoncollinear"], values["lspiral"], values["qspiral"], values["saxis"]):
        raise ValueError(f"{path}: CSO lacks required actual-writer metadata")
    return TextMetadata(kind=kind, label=label, raw_lines=raw_lines, **values), data_lines


def _load_matrix(path: str | Path, kind: str) -> MatrixDump:
    input_path = Path(path)
    metadata, data_lines = _parse_text_metadata(input_path, kind)
    assert metadata.lmdim is not None and metadata.nions is not None and metadata.ncdij is not None
    matrix = np.zeros((metadata.ncdij, metadata.nions, metadata.lmdim, metadata.lmdim), dtype=np.complex128)
    seen = np.zeros(matrix.shape, dtype=bool)
    trace_by_ion: list[float | None] = [None] * metadata.nions
    trace_total: float | None = None
    for raw_line in metadata.raw_lines:
        stripped = raw_line.strip()
        if stripped.startswith("# TRACE_CHECK ION"):
            parts = stripped.split()
            if len(parts) != 5:
                raise ValueError(f"{input_path}: malformed TRACE_CHECK ION line")
            ion = int(parts[3])
            if not 1 <= ion <= metadata.nions:
                raise ValueError(f"{input_path}: TRACE_CHECK ion {ion} is out of range")
            if trace_by_ion[ion - 1] is not None:
                raise ValueError(f"{input_path}: duplicate TRACE_CHECK for ion {ion}")
            trace_by_ion[ion - 1] = _parse_float(parts[4], "TRACE_CHECK ION")
        elif stripped.startswith("# TRACE_CHECK TOTAL"):
            parts = stripped.split()
            if len(parts) != 4:
                raise ValueError(f"{input_path}: malformed TRACE_CHECK TOTAL line")
            trace_total = _parse_float(parts[3], "TRACE_CHECK TOTAL")
    for line in data_lines:
        parts = line.split()
        if len(parts) != 6:
            raise ValueError(f"{input_path}: malformed {kind.upper()} row {line!r}")
        ion, is_index, i, j = (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))
        if not (1 <= ion <= metadata.nions and 1 <= is_index <= metadata.ncdij and 1 <= i <= metadata.lmdim and 1 <= j <= metadata.lmdim):
            raise ValueError(f"{input_path}: {kind.upper()} row index {(ion, is_index, i, j)} is outside metadata dimensions")
        index = (is_index - 1, ion - 1, i - 1, j - 1)
        if seen[index]:
            raise ValueError(f"{input_path}: duplicate {kind.upper()} matrix row {(ion, is_index, i, j)}")
        seen[index] = True
        matrix[index] = _parse_float(parts[4], "Re") + 1j * _parse_float(parts[5], "Im")
    missing = np.argwhere(~seen)
    if len(missing):
        is_index, ion, i, j = missing[0]
        raise ValueError(f"{input_path}: missing {kind.upper()} matrix row {(ion + 1, is_index + 1, i + 1, j + 1)}")
    if kind == "cocc":
        if any(value is None for value in trace_by_ion) or trace_total is None:
            raise ValueError(f"{input_path}: COCC lacks required TRACE_CHECK diagnostics")
        trace_values = tuple(float(value) for value in trace_by_ion if value is not None)
        if not math.isclose(sum(trace_values), trace_total, abs_tol=ELECTRON_TOLERANCE, rel_tol=0.0):
            raise ValueError(f"{input_path}: COCC per-ion TRACE_CHECK values do not sum to TRACE_CHECK TOTAL")
    else:
        trace_values = None
    return MatrixDump(
        matrix=matrix,
        metadata=metadata,
        trace_by_ion=trace_values,
        trace_total=trace_total,
    )


def load_cso(path: str | Path) -> MatrixDump:
    """Load the dump_C CSO and require its deck: SOC on, no spiral, SAXIS = z (Section 5)."""

    result = _load_matrix(path, "cso")
    m = result.metadata
    if (m.lsorbit, m.lnoncollinear, m.lspiral) != (True, True, False):
        raise ValueError(f"{path}: CSO needs LSORBIT = T, LNONCOLLINEAR = T and LSPIRAL = F")
    if not (np.allclose(m.qspiral, 0, atol=1e-12, rtol=0) and np.allclose(m.saxis, (0, 0, 1), atol=1e-12, rtol=0)):
        raise ValueError(f"{path}: CSO has QSPIRAL = {m.qspiral} and SAXIS = {m.saxis}; needs 0 and (0, 0, 1)")
    return result


def load_cocc(path: str | Path) -> MatrixDump:
    """Load a dump_P COCC. The writer emits no LSORBIT or LSPIRAL metadata; the
    PRE_LOOP label and the file type are all the format provides."""

    return _load_matrix(path, "cocc")
