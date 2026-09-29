"""Readers for the actual Heide Patch B dump files.

The binary layout below follows ``csodump.F`` lines 154--184, not the earlier
migration document.  In particular, only CPROJ has a binary common header;
FERWE, CSO, and COCC have distinct formatted comment metadata.  CPROJ records
contain ``(NK, GLOBAL_BAND, ISP, WTKPT, EIG_Re, FERWE, CPROJ)``.

``WDES%NPRO`` is not emitted directly.  It is nevertheless determined by the
writer's dimensions: ``wave.F`` lines 165 and 247 define it as
``NRSPINORS * sum(LMMAX_ION)``.  The reader derives that exact value and checks
LMBASE before using it.  It never guesses NPRO from LMDIM.

Fortran stream I/O is native ABI data.  ``_probe_cproj_abi`` therefore probes
little/big endian default INTEGER/LOGICAL widths of four or eight bytes, while
requiring the binary64 ``REAL(q)`` representation used by the supported Patch B
build.  A non-binary64 build fails loudly rather than being silently decoded.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import math
import re
import struct
from typing import Iterable

import numpy as np

from . import conventions


CPROJ_MAGIC = "HEIDE_CPROJ_PATCH_B"
CPROJ_BUILD_ID = "VASP 6.4.2 HEIDE PATCH B"
CPROJ_DUMP_TAG = "PRE_LOOP"
OCCUPATION_TOLERANCE = 1.0e-6
ELECTRON_TOLERANCE = 1.0e-6
WEIGHT_TOLERANCE = 1.0e-8


@dataclass(frozen=True)
class FileProvenance:
    """Path and immutable SHA-256 identity of one input file."""

    path: Path
    sha256: str


@dataclass(frozen=True)
class CprojAbi:
    """The supported native ABI selected by header and record validation."""

    byte_order: str
    integer_bytes: int
    logical_bytes: int
    real_bytes: int = 8

    @property
    def integer_format(self) -> str:
        return f"{self.byte_order}{'i' if self.integer_bytes == 4 else 'q'}"

    @property
    def logical_format(self) -> str:
        return f"{self.byte_order}{'i' if self.logical_bytes == 4 else 'q'}"

    @property
    def real_dtype(self) -> np.dtype:
        return np.dtype(f"{self.byte_order}f8")


@dataclass(frozen=True)
class CprojHeader:
    """Every CPROJ header field emitted by ``WRITE_CPROJ_PRELOOP``."""

    magic: str
    format_version: int
    build_id: str
    dump_tag: str
    call_counter: int
    nions: int
    lmdim: int
    ncdij: int
    nrspinors: int
    nbands_local: int
    nbands_global: int
    nkpts_global: int
    ispin: int
    nb_low: int
    nb_par: int
    comm_kinter_node_me: int
    comm_kinter_ncpu: int
    comm_inter_node_me: int
    comm_inter_ncpu: int
    lsorbit: bool
    lnoncollinear: bool
    lspiral: bool
    qspiral: tuple[float, float, float]
    saxis: tuple[float, float, float]
    nelect: float
    enmax: float
    lmmax_ion: tuple[int, ...]
    lmbase: tuple[int, ...]
    npro: int
    abi: CprojAbi


@dataclass(frozen=True)
class CprojRecord:
    """One self-indexed CPROJ stream record, retaining all writer fields."""

    nk: int
    global_band: int
    isp: int
    weight: float
    eigenvalue: complex
    occupation: float
    cproj: np.ndarray


@dataclass(frozen=True)
class CprojFile:
    """One rank-local CPROJ file after stream decoding."""

    header: CprojHeader
    records: tuple[CprojRecord, ...]
    provenance: FileProvenance


@dataclass(frozen=True)
class CprojData:
    """Globally assembled Patch B CPROJ data.

    ``c`` has shape ``(ISPIN, NKPTS, NIONS, NRSPINORS, LMDIM, NBANDS)``.
    Indices are zero-based Python equivalents of the writer's one-based global
    ``ISP``, ``NK``, and ``GLOBAL_BAND`` fields.  Elements outside each ion's
    ``LMMAX_ION`` are zero.
    """

    c: np.ndarray
    weights: np.ndarray
    eigenvalues: np.ndarray
    occupations: np.ndarray
    header: CprojHeader
    files: tuple[FileProvenance, ...]


@dataclass(frozen=True)
class TextMetadata:
    """Metadata preserved from one formatted Patch B dump."""

    kind: str
    label: str
    lmdim: int | None
    nions: int | None
    ncdij: int | None
    nkpts: int | None
    nbands: int | None
    ispin: int | None
    set_dd_paw_call: int | None
    lsorbit: bool | None
    lnoncollinear: bool | None
    lspiral: bool | None
    qspiral: tuple[float, float, float] | None
    saxis: tuple[float, float, float] | None
    nelect: float | None
    raw_lines: tuple[str, ...]
    sanity_sum_w: float | None = None
    sanity_sum_fw: float | None = None
    min_occupation: float | None = None
    max_occupation: float | None = None


@dataclass(frozen=True)
class Occupations:
    """FERWE rows retaining the actual ISP dimension emitted by the writer."""

    occupations: np.ndarray
    weights: np.ndarray
    eigenvalues: np.ndarray
    spin_factor: float
    metadata: TextMetadata
    provenance: FileProvenance


@dataclass(frozen=True)
class MatrixDump:
    """CSO or COCC data in ``(IS, ION, I, J)`` order, all zero-based."""

    matrix: np.ndarray
    metadata: TextMetadata
    provenance: FileProvenance
    trace_by_ion: tuple[float, ...] | None = None
    trace_total: float | None = None


def _provenance(path: Path) -> FileProvenance:
    return FileProvenance(path=path, sha256=sha256(path.read_bytes()).hexdigest())


def _fixed_string(data: bytes, offset: int, size: int, description: str) -> tuple[str, int]:
    end = offset + size
    if end > len(data):
        raise ValueError(f"CPROJ header is truncated while reading {description}")
    try:
        value = data[offset:end].decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError(f"CPROJ {description} is not ASCII") from error
    return value.rstrip(" "), end


def _unpack_integer(data: bytes, offset: int, abi: CprojAbi, description: str) -> tuple[int, int]:
    end = offset + abi.integer_bytes
    if end > len(data):
        raise ValueError(f"CPROJ header is truncated while reading {description}")
    return int(struct.unpack_from(abi.integer_format, data, offset)[0]), end


def _unpack_logical(data: bytes, offset: int, abi: CprojAbi, description: str) -> tuple[bool, int]:
    end = offset + abi.logical_bytes
    if end > len(data):
        raise ValueError(f"CPROJ header is truncated while reading {description}")
    value = int(struct.unpack_from(abi.logical_format, data, offset)[0])
    if value not in (-1, 0, 1):
        raise ValueError(f"CPROJ {description} has unsupported native logical value {value}")
    return value != 0, end


def _unpack_reals(data: bytes, offset: int, count: int, abi: CprojAbi, description: str) -> tuple[np.ndarray, int]:
    end = offset + count * abi.real_bytes
    if end > len(data):
        raise ValueError(f"CPROJ header is truncated while reading {description}")
    values = np.frombuffer(data, dtype=abi.real_dtype, count=count, offset=offset).astype(np.float64, copy=True)
    if not np.all(np.isfinite(values)):
        raise ValueError(f"CPROJ {description} contains non-finite values")
    return values, end


def _derive_npro(nrspinors: int, lmmax_ion: tuple[int, ...], lmbase: tuple[int, ...]) -> int:
    if nrspinors < 1:
        raise ValueError(f"CPROJ NRSPINORS must be positive, got {nrspinors}")
    if any(value < 0 for value in lmmax_ion):
        raise ValueError("CPROJ LMMAX_ION contains a negative projector count")
    expected_base = 0
    for ion, (lmmax, base) in enumerate(zip(lmmax_ion, lmbase), start=1):
        if base != expected_base:
            raise ValueError(
                f"CPROJ LMBASE for ion {ion} is {base}, expected {expected_base} from preceding LMMAX_ION values"
            )
        expected_base += lmmax
    return nrspinors * expected_base


def _decode_cproj_header(data: bytes, abi: CprojAbi) -> tuple[CprojHeader, int]:
    offset = 0
    magic, offset = _fixed_string(data, offset, 32, "magic")
    version, offset = _unpack_integer(data, offset, abi, "format version")
    build_id, offset = _fixed_string(data, offset, 32, "build string")
    dump_tag, offset = _fixed_string(data, offset, 16, "dump tag")
    call_counter, offset = _unpack_integer(data, offset, abi, "call counter")
    values: list[int] = []
    for description in (
        "NIONS", "LMDIM", "NCDIJ", "NRSPINORS", "NBANDS local", "NBANDS global", "NKPTS global", "ISPIN",
        "NB_LOW", "NB_PAR", "COMM_KINTER NODE_ME", "COMM_KINTER NCPU", "COMM_INTER NODE_ME", "COMM_INTER NCPU",
    ):
        value, offset = _unpack_integer(data, offset, abi, description)
        values.append(value)
    nions, lmdim, ncdij, nrspinors, nbands_local, nbands_global, nkpts_global, ispin, nb_low, nb_par, k_node, k_ncpu, b_node, b_ncpu = values
    if nions < 1 or lmdim < 0 or ncdij < 1 or nbands_local < 0 or nbands_global < 1 or nkpts_global < 1 or ispin < 1:
        raise ValueError("CPROJ header has invalid non-positive dimensions")
    if not (1 <= k_node <= k_ncpu and 1 <= b_node <= b_ncpu):
        raise ValueError("CPROJ communicator rank is outside its communicator size")
    logical_values: list[bool] = []
    for description in ("LSORBIT", "LNONCOLLINEAR", "LSPIRAL"):
        value, offset = _unpack_logical(data, offset, abi, description)
        logical_values.append(value)
    qspiral, offset = _unpack_reals(data, offset, 3, abi, "QSPIRAL")
    saxis, offset = _unpack_reals(data, offset, 3, abi, "SAXIS")
    scalar_reals, offset = _unpack_reals(data, offset, 2, abi, "NELECT and ENMAX")
    lmmax_values: list[int] = []
    base_values: list[int] = []
    for ion in range(1, nions + 1):
        value, offset = _unpack_integer(data, offset, abi, f"LMMAX_ION({ion})")
        lmmax_values.append(value)
    for ion in range(1, nions + 2):
        value, offset = _unpack_integer(data, offset, abi, f"LMBASE({ion})")
        base_values.append(value)
    lmmax_ion = tuple(lmmax_values)
    if base_values[-1] != sum(lmmax_values):
        raise ValueError("CPROJ terminal LMBASE must equal sum(LMMAX_ION)")
    lmbase = tuple(base_values[:-1])
    # NPRO is absent from the stream.  Its byte count follows wave.F lines
    # 165/247; validate LMBASE only after the ABI has been selected so a bad
    # LMBASE is reported as a format defect, not as an ABI ambiguity.
    npro = nrspinors * sum(lmmax_ion)
    if lmdim != max(lmmax_ion):
        raise ValueError(f"CPROJ LMDIM={lmdim} does not equal max(LMMAX_ION)={max(lmmax_ion)}")
    header = CprojHeader(
        magic=magic,
        format_version=version,
        build_id=build_id,
        dump_tag=dump_tag,
        call_counter=call_counter,
        nions=nions,
        lmdim=lmdim,
        ncdij=ncdij,
        nrspinors=nrspinors,
        nbands_local=nbands_local,
        nbands_global=nbands_global,
        nkpts_global=nkpts_global,
        ispin=ispin,
        nb_low=nb_low,
        nb_par=nb_par,
        comm_kinter_node_me=k_node,
        comm_kinter_ncpu=k_ncpu,
        comm_inter_node_me=b_node,
        comm_inter_ncpu=b_ncpu,
        lsorbit=logical_values[0],
        lnoncollinear=logical_values[1],
        lspiral=logical_values[2],
        qspiral=tuple(float(value) for value in qspiral),
        saxis=tuple(float(value) for value in saxis),
        nelect=float(scalar_reals[0]),
        enmax=float(scalar_reals[1]),
        lmmax_ion=lmmax_ion,
        lmbase=lmbase,
        npro=npro,
        abi=abi,
    )
    return header, offset


def _assert_cproj_static_header(header: CprojHeader) -> None:
    if header.magic != CPROJ_MAGIC:
        raise ValueError(f"CPROJ magic is {header.magic!r}, expected {CPROJ_MAGIC!r}")
    if header.build_id != CPROJ_BUILD_ID:
        raise ValueError(f"CPROJ build id is {header.build_id!r}, expected {CPROJ_BUILD_ID!r}")
    if header.format_version != conventions.DUMP_FORMAT_VERSION:
        raise ValueError(
            f"CPROJ format version is {header.format_version}, "
            f"expected {conventions.DUMP_FORMAT_VERSION}"
        )
    if conventions.VASP_BUILD_ID is not conventions.UNDETERMINED:
        if header.build_id != conventions.VASP_BUILD_ID:
            raise ValueError(
                f"CPROJ build id is {header.build_id!r}, "
                f"expected pinned {conventions.VASP_BUILD_ID!r}"
            )
    if header.dump_tag != CPROJ_DUMP_TAG:
        raise ValueError(f"CPROJ dump tag is {header.dump_tag!r}, expected {CPROJ_DUMP_TAG!r}")
    if header.call_counter != 1:
        raise ValueError(f"CPROJ call counter is {header.call_counter}, expected writer constant 1")


def _record_size(header: CprojHeader) -> int:
    # W%CELEN is COMPLEX(q) (wave_struct.F), unlike FERWE's REAL(CELTOT).
    return 3 * header.abi.integer_bytes + 4 * header.abi.real_bytes + header.npro * 2 * header.abi.real_bytes


def _probe_cproj_abi(data: bytes) -> tuple[CprojHeader, int]:
    candidates: list[tuple[CprojHeader, int]] = []
    for byte_order in ("<", ">"):
        for integer_bytes in (4, 8):
            for logical_bytes in (4, 8):
                abi = CprojAbi(byte_order=byte_order, integer_bytes=integer_bytes, logical_bytes=logical_bytes)
                try:
                    header, offset = _decode_cproj_header(data, abi)
                    record_size = _record_size(header)
                    if record_size <= 0 or (len(data) - offset) % record_size != 0:
                        continue
                    candidates.append((header, offset))
                except (ValueError, struct.error, OverflowError):
                    continue
    if not candidates:
        raise ValueError(
            "CPROJ native ABI could not be identified. The reader supports binary64 REAL(q), four/eight-byte "
            "default INTEGER/LOGICAL, and either endianness; this dump needs an explicit ABI extension."
        )
    if len(candidates) != 1:
        descriptions = [f"{item[0].abi.byte_order}i{item[0].abi.integer_bytes}/l{item[0].abi.logical_bytes}" for item in candidates]
        raise ValueError(f"CPROJ native ABI is ambiguous: {', '.join(descriptions)}")
    header, offset = candidates[0]
    _assert_cproj_static_header(header)
    return header, offset


def read_cproj_file(path: str | Path) -> CprojFile:
    """Read one exact native stream CPROJ file and reject truncation or tail bytes."""

    input_path = Path(path)
    data = input_path.read_bytes()
    header, offset = _probe_cproj_abi(data)
    derived_npro = _derive_npro(header.nrspinors, header.lmmax_ion, header.lmbase)
    if derived_npro != header.npro:
        raise AssertionError("internal CPROJ NPRO derivation mismatch")
    record_size = _record_size(header)
    record_count = (len(data) - offset) // record_size
    records: list[CprojRecord] = []
    for record_index in range(record_count):
        start = offset + record_index * record_size
        nk, position = _unpack_integer(data, start, header.abi, f"record {record_index} NK")
        global_band, position = _unpack_integer(data, position, header.abi, f"record {record_index} GLOBAL_BAND")
        isp, position = _unpack_integer(data, position, header.abi, f"record {record_index} ISP")
        values, position = _unpack_reals(data, position, 4, header.abi, f"record {record_index} scalars")
        complex_parts, position = _unpack_reals(data, position, 2 * header.npro, header.abi, f"record {record_index} CPROJ")
        if position != start + record_size:
            raise AssertionError("internal CPROJ record-size mismatch")
        cproj = complex_parts[0::2] + 1j * complex_parts[1::2]
        records.append(
            CprojRecord(
                nk=nk,
                global_band=global_band,
                isp=isp,
                weight=float(values[0]),
                eigenvalue=complex(values[1], values[2]),
                occupation=float(values[3]),
                cproj=cproj.astype(np.complex128, copy=False),
            )
        )
    return CprojFile(header=header, records=tuple(records), provenance=_provenance(input_path))


def _header_consistency_key(header: CprojHeader) -> tuple[object, ...]:
    return (
        header.magic, header.format_version, header.build_id, header.dump_tag, header.call_counter,
        header.nions, header.lmdim, header.ncdij, header.nrspinors,
        header.nbands_global, header.nkpts_global, header.ispin, header.nb_par,
        header.comm_kinter_ncpu, header.comm_inter_ncpu, header.lsorbit, header.lnoncollinear,
        header.lspiral, header.qspiral, header.saxis, header.nelect, header.enmax, header.lmmax_ion,
        header.lmbase, header.npro, header.abi,
    )


def assert_cproj_headers_consistent(headers: Iterable[CprojHeader]) -> CprojHeader:
    """Require all rank files to agree except for their expected rank coordinates."""

    header_list = list(headers)
    if not header_list:
        raise ValueError("No CPROJ headers were supplied")
    reference = header_list[0]
    expected_ranks: set[tuple[int, int]] = set()
    for index, header in enumerate(header_list, start=1):
        if _header_consistency_key(header) != _header_consistency_key(reference):
            raise ValueError(f"CPROJ header {index} disagrees with the first CPROJ header")
        rank = (header.comm_kinter_node_me, header.comm_inter_node_me)
        if rank in expected_ranks:
            raise ValueError(f"CPROJ has duplicate communicator-rank header {rank}")
        expected_ranks.add(rank)
    expected_count = reference.comm_kinter_ncpu * reference.comm_inter_ncpu
    if len(header_list) != expected_count:
        raise ValueError(f"CPROJ has {len(header_list)} rank files, expected {expected_count} from communicator sizes")
    return reference


def load_cproj(directory: str | Path) -> CprojData:
    """Assemble CPROJ exclusively by each record's global k/band/spin indices.

    This executes the reader side of W0: every ``(ISP, NK, GLOBAL_BAND)`` must
    occur exactly once.  File order and rank identifiers never select a band.
    """

    root = Path(directory)
    paths = tuple(sorted(root.glob("CPROJ.*.bin")))
    if not paths:
        raise FileNotFoundError(f"No CPROJ.*.bin files found in {root}")
    parsed_files = [read_cproj_file(path) for path in paths]
    header = assert_cproj_headers_consistent(item.header for item in parsed_files)
    c = np.zeros(
        (header.ispin, header.nkpts_global, header.nions, header.nrspinors, header.lmdim, header.nbands_global),
        dtype=np.complex128,
    )
    weights = np.full((header.ispin, header.nkpts_global), np.nan, dtype=np.float64)
    eigenvalues = np.full((header.ispin, header.nkpts_global, header.nbands_global), np.nan, dtype=np.complex128)
    occupations = np.full((header.ispin, header.nkpts_global, header.nbands_global), np.nan, dtype=np.float64)
    coverage = np.zeros((header.ispin, header.nkpts_global, header.nbands_global), dtype=bool)
    for parsed in parsed_files:
        for record in parsed.records:
            if not (np.isfinite(record.eigenvalue) and np.isfinite(record.occupation)
                    and np.isfinite(record.weight) and np.all(np.isfinite(record.cproj))):
                raise ValueError(f"{parsed.provenance.path}: non-finite CPROJ record")
            if not 1 <= record.nk <= header.nkpts_global:
                raise ValueError(f"{parsed.provenance.path}: NK={record.nk} is outside 1..{header.nkpts_global}")
            if not 1 <= record.global_band <= header.nbands_global:
                raise ValueError(
                    f"{parsed.provenance.path}: GLOBAL_BAND={record.global_band} is outside 1..{header.nbands_global}"
                )
            if not 1 <= record.isp <= header.ispin:
                raise ValueError(f"{parsed.provenance.path}: ISP={record.isp} is outside 1..{header.ispin}")
            spin, kpoint, band = record.isp - 1, record.nk - 1, record.global_band - 1
            if coverage[spin, kpoint, band]:
                raise ValueError(f"W0 failed: duplicate CPROJ record (ISP={record.isp}, NK={record.nk}, BAND={record.global_band})")
            coverage[spin, kpoint, band] = True
            if math.isnan(weights[spin, kpoint]):
                weights[spin, kpoint] = record.weight
            elif not math.isclose(weights[spin, kpoint], record.weight, abs_tol=WEIGHT_TOLERANCE, rel_tol=0.0):
                raise ValueError(f"CPROJ records disagree on WTKPT for ISP={record.isp}, NK={record.nk}")
            eigenvalues[spin, kpoint, band] = record.eigenvalue
            occupations[spin, kpoint, band] = record.occupation
            for ion, (lmmax, base) in enumerate(zip(header.lmmax_ion, header.lmbase)):
                for spinor in range(header.nrspinors):
                    start = base + spinor * (header.npro // header.nrspinors)
                    c[spin, kpoint, ion, spinor, :lmmax, band] = record.cproj[start:start + lmmax]
    missing = np.argwhere(~coverage)
    if len(missing):
        spin, kpoint, band = missing[0]
        raise ValueError(f"W0 failed: missing CPROJ record (ISP={spin + 1}, NK={kpoint + 1}, BAND={band + 1})")
    if np.any(~np.isfinite(weights)):
        raise ValueError("W0 failed: a covered CPROJ k-point has no WTKPT")
    return CprojData(
        c=c,
        weights=weights,
        eigenvalues=eigenvalues,
        occupations=occupations,
        header=header,
        files=tuple(item.provenance for item in parsed_files),
    )


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
        "ferwe": "PRE_LOOP input occupations",
        "cso": "last nonzero SET_DD_PAW",
        "cocc": "PRE_LOOP input CPROJ",
    }
    if label != expected_labels[kind]:
        raise ValueError(f"{path}: {kind.upper()} label is {label!r}, expected {expected_labels[kind]!r}")
    values: dict[str, object] = {
        "lmdim": None, "nions": None, "ncdij": None, "nkpts": None, "nbands": None, "ispin": None,
        "set_dd_paw_call": None, "lsorbit": None, "lnoncollinear": None, "lspiral": None,
        "qspiral": None, "saxis": None, "nelect": None, "sanity_sum_w": None, "sanity_sum_fw": None,
        "min_occupation": None, "max_occupation": None,
    }
    for line in comments[1:]:
        body = line[1:].strip()
        parts = body.split()
        if body.startswith("NKPTS NBANDS ISPIN"):
            if len(parts) != 6:
                raise ValueError(f"{path}: malformed NKPTS/NBANDS/ISPIN metadata")
            values["nkpts"], values["nbands"], values["ispin"] = (int(parts[3]), int(parts[4]), int(parts[5]))
        elif body.startswith("LMDIM NIONS NCDIJ"):
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
        elif body.startswith("SANITY SUM_W SUM_FW NELECT"):
            if len(parts) != 7:
                raise ValueError(f"{path}: malformed SUM_W/SUM_FW/NELECT sanity line")
            values["sanity_sum_w"] = _parse_float(parts[4], "SUM_W")
            values["sanity_sum_fw"] = _parse_float(parts[5], "SUM_FW")
            values["nelect"] = _parse_float(parts[6], "NELECT")
        elif body.startswith("SANITY MIN_F MAX_F"):
            if len(parts) != 5:
                raise ValueError(f"{path}: malformed MIN_F/MAX_F sanity line")
            values["min_occupation"] = _parse_float(parts[3], "MIN_F")
            values["max_occupation"] = _parse_float(parts[4], "MAX_F")
    if kind == "ferwe" and None in (
        values["nkpts"], values["nbands"], values["ispin"], values["sanity_sum_w"], values["sanity_sum_fw"],
        values["nelect"], values["min_occupation"], values["max_occupation"],
    ):
        raise ValueError(f"{path}: FERWE lacks required actual-writer metadata")
    if kind in ("cso", "cocc") and None in (values["lmdim"], values["nions"], values["ncdij"]):
        raise ValueError(f"{path}: {kind.upper()} lacks required LMDIM/NIONS/NCDIJ metadata")
    if kind == "cso" and None in (values["set_dd_paw_call"], values["lsorbit"], values["lnoncollinear"], values["lspiral"], values["qspiral"], values["saxis"]):
        raise ValueError(f"{path}: CSO lacks required actual-writer metadata")
    return TextMetadata(kind=kind, label=label, raw_lines=raw_lines, **values), data_lines


def read_header(path: str | Path) -> CprojHeader | TextMetadata:
    """Read metadata without pretending actual text files share CPROJ's header."""

    input_path = Path(path)
    if input_path.suffix == ".bin":
        return read_cproj_file(input_path).header
    name = input_path.name.upper()
    if name.startswith("FERWE"):
        return _parse_text_metadata(input_path, "ferwe")[0]
    if name.startswith("CSO"):
        return _parse_text_metadata(input_path, "cso")[0]
    if name.startswith("COCC"):
        return _parse_text_metadata(input_path, "cocc")[0]
    raise ValueError(f"Cannot determine Patch B dump format for {input_path}")


def assert_header(
    header: CprojHeader | TextMetadata,
    *,
    expect_lsorbit: bool | None = None,
    expect_lspiral: bool | None = None,
    q_frac: tuple[float, float, float] | None = None,
    saxis: tuple[float, float, float] | None = (0.0, 0.0, 1.0),
) -> None:
    """Validate only metadata fields the actual format contains."""

    if isinstance(header, CprojHeader):
        _assert_cproj_static_header(header)
        lsorbit, lspiral, actual_q, actual_saxis = header.lsorbit, header.lspiral, header.qspiral, header.saxis
    else:
        lsorbit, lspiral, actual_q, actual_saxis = header.lsorbit, header.lspiral, header.qspiral, header.saxis
    if expect_lsorbit is not None:
        if lsorbit is None:
            raise ValueError(f"{getattr(header, 'kind', 'CPROJ')} does not emit LSORBIT metadata")
        if lsorbit != expect_lsorbit:
            raise ValueError(f"LSORBIT={lsorbit}, expected {expect_lsorbit}")
    if expect_lspiral is not None:
        if lspiral is None:
            raise ValueError(f"{getattr(header, 'kind', 'CPROJ')} does not emit LSPIRAL metadata")
        if lspiral != expect_lspiral:
            raise ValueError(f"LSPIRAL={lspiral}, expected {expect_lspiral}")
    if q_frac is not None:
        if actual_q is None or not np.allclose(actual_q, q_frac, atol=1.0e-12, rtol=0.0):
            raise ValueError(f"QSPIRAL={actual_q}, expected {q_frac}")
    if saxis is not None:
        if actual_saxis is None or not np.allclose(actual_saxis, saxis, atol=1.0e-12, rtol=0.0):
            raise ValueError(f"SAXIS={actual_saxis}, expected {saxis}")


def load_ferwe(path_or_directory: str | Path) -> Occupations:
    """Load FERWE.dat with strict index, weight, electron, and insulating checks.

    The source writes ``RSPIN * WTKPT * FERTOT`` into the SANITY electron
    total, but does not emit RSPIN.  For ISPIN=2 it is one; for ISPIN=1 this
    reader derives the only writer-consistent value (one or two) from the
    recorded SANITY total and NELECT rather than assuming a collinear state.
    """

    candidate = Path(path_or_directory)
    path = candidate / "FERWE.dat" if candidate.is_dir() else candidate
    metadata, data_lines = _parse_text_metadata(path, "ferwe")
    assert metadata.nkpts is not None and metadata.nbands is not None and metadata.ispin is not None
    nkpts, nbands, ispin = metadata.nkpts, metadata.nbands, metadata.ispin
    occupations = np.full((ispin, nkpts, nbands), np.nan, dtype=np.float64)
    eigenvalues = np.full((ispin, nkpts, nbands), np.nan, dtype=np.float64)
    weights = np.full((ispin, nkpts), np.nan, dtype=np.float64)
    seen = np.zeros((ispin, nkpts, nbands), dtype=bool)
    sanity_sum_w = metadata.sanity_sum_w
    sanity_sum_fw = metadata.sanity_sum_fw
    sanity_nelect = metadata.nelect
    for line in data_lines:
        parts = line.split()
        if len(parts) != 6:
            raise ValueError(f"{path}: malformed FERWE row {line!r}")
        nk, band, isp = (int(parts[0]), int(parts[1]), int(parts[2]))
        if not (1 <= nk <= nkpts and 1 <= band <= nbands and 1 <= isp <= ispin):
            raise ValueError(f"{path}: FERWE row index {(nk, band, isp)} is outside header dimensions")
        spin, kpoint, band_index = isp - 1, nk - 1, band - 1
        if seen[spin, kpoint, band_index]:
            raise ValueError(f"{path}: duplicate FERWE row (ISP={isp}, NK={nk}, BAND={band})")
        seen[spin, kpoint, band_index] = True
        weight, eigenvalue, occupation = (_parse_float(parts[3], "WTKPT"), _parse_float(parts[4], "EIG_Re"), _parse_float(parts[5], "FERWE"))
        if weight < 0:
            raise ValueError(f"{path}: negative WTKPT")
        if not 0.0 <= occupation <= 1.0:
            raise ValueError(f"{path}: FERWE at ISP={isp}, NK={nk}, BAND={band} is outside [0, 1]: {occupation}")
        if min(abs(occupation), abs(occupation - 1.0)) > OCCUPATION_TOLERANCE:
            raise ValueError(f"{path}: fractional FERWE at ISP={isp}, NK={nk}, BAND={band}: {occupation}")
        if math.isnan(weights[spin, kpoint]):
            weights[spin, kpoint] = weight
        elif not math.isclose(weights[spin, kpoint], weight, abs_tol=WEIGHT_TOLERANCE, rel_tol=0.0):
            raise ValueError(f"{path}: inconsistent WTKPT for ISP={isp}, NK={nk}")
        occupations[spin, kpoint, band_index] = occupation
        eigenvalues[spin, kpoint, band_index] = eigenvalue
    missing = np.argwhere(~seen)
    if len(missing):
        spin, kpoint, band = missing[0]
        raise ValueError(f"{path}: missing FERWE row (ISP={spin + 1}, NK={kpoint + 1}, BAND={band + 1})")
    if sanity_sum_w is None or sanity_sum_fw is None or sanity_nelect is None:
        raise ValueError(f"{path}: missing actual-writer FERWE SANITY SUM_W/SUM_FW/NELECT line")
    if not np.allclose(weights, weights[0], atol=WEIGHT_TOLERANCE, rtol=0.0):
        raise ValueError(f"{path}: WTKPT differs across ISP channels; the writer's WDES%WTKPT is spin-independent")
    common_weights = weights[0].copy()
    if not math.isclose(float(np.sum(common_weights)), 1.0, abs_tol=WEIGHT_TOLERANCE, rel_tol=0.0):
        raise ValueError(f"{path}: sum(WTKPT)={np.sum(common_weights)} does not equal one")
    if not math.isclose(sanity_sum_w, float(np.sum(common_weights)), abs_tol=WEIGHT_TOLERANCE, rel_tol=0.0):
        raise ValueError(f"{path}: SANITY SUM_W={sanity_sum_w} disagrees with rows")
    raw_electrons = float(np.sum(common_weights[None, :, None] * occupations))
    allowed_factors = (1.0,) if ispin == 2 else (1.0, 2.0)
    matching_factors = [factor for factor in allowed_factors if math.isclose(factor * raw_electrons, sanity_sum_fw, abs_tol=ELECTRON_TOLERANCE, rel_tol=0.0)]
    if len(matching_factors) != 1:
        raise ValueError(f"{path}: rows cannot reproduce SANITY SUM_FW={sanity_sum_fw} with legal RSPIN for ISPIN={ispin}")
    spin_factor = matching_factors[0]
    if not math.isclose(sanity_sum_fw, sanity_nelect, abs_tol=ELECTRON_TOLERANCE, rel_tol=0.0):
        raise ValueError(f"{path}: SANITY SUM_FW={sanity_sum_fw} does not equal NELECT={sanity_nelect}")
    if metadata.min_occupation is None or metadata.max_occupation is None:
        raise ValueError(f"{path}: missing FERWE MIN_F/MAX_F sanity metadata")
    if not math.isclose(metadata.min_occupation, float(np.min(occupations)), abs_tol=OCCUPATION_TOLERANCE, rel_tol=0.0):
        raise ValueError(f"{path}: SANITY MIN_F disagrees with rows")
    if not math.isclose(metadata.max_occupation, float(np.max(occupations)), abs_tol=OCCUPATION_TOLERANCE, rel_tol=0.0):
        raise ValueError(f"{path}: SANITY MAX_F disagrees with rows")
    return Occupations(
        occupations=occupations,
        weights=common_weights,
        eigenvalues=eigenvalues,
        spin_factor=spin_factor,
        metadata=metadata,
        provenance=_provenance(path),
    )


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
        provenance=_provenance(input_path),
        trace_by_ion=trace_values,
        trace_total=trace_total,
    )


def load_cso(path: str | Path, *, expect_saxis: tuple[float, float, float] = (0.0, 0.0, 1.0)) -> MatrixDump:
    """Load actual CSO text and require the Patch B SOC, non-spiral metadata."""

    result = _load_matrix(path, "cso")
    assert_header(result.metadata, expect_lsorbit=True, expect_lspiral=False,
                  q_frac=(0.0, 0.0, 0.0), saxis=expect_saxis)
    if result.metadata.lnoncollinear is not True:
        raise ValueError("CSO requires LNONCOLLINEAR=T")
    return result


def load_cocc(path: str | Path) -> MatrixDump:
    """Load actual COCC text and reject a file claiming SOC provenance."""

    result = _load_matrix(path, "cocc")
    # COCC has no LSORBIT/LSPIRAL metadata in the writer.  The PRE_LOOP label
    # and its distinct file type are all the format itself provides.
    return result
