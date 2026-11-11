from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct

import numpy as np

# Literal writer constants: do not import the implementation being tested.
CPROJ_MAGIC = "HEIDE_CPROJ_PATCH_B"
CPROJ_BUILD_ID = "VASP 6.4.2 HEIDE PATCH B"
CPROJ_DUMP_TAG = "PRE_LOOP"


@dataclass(frozen=True)
class DumpPaths:
    directory: Path
    cproj_paths: tuple[Path, ...]
    ferwe_path: Path
    cocc_path: Path
    cproj: np.ndarray
    occupations: np.ndarray
    weights: np.ndarray
    cocc: np.ndarray


def _fixed(value: str, width: int) -> bytes:
    encoded = value.encode("ascii")
    if len(encoded) > width:
        raise ValueError(f"{value!r} exceeds fixed width {width}")
    return encoded.ljust(width, b" ")


def _write_matrix(path: Path, matrix: np.ndarray, kind: str, *, nelect: float,
                  saxis: tuple[float, float, float] = (0.0, 0.0, 1.0)) -> None:
    ncdij, nions, lmdim, second_lmdim = matrix.shape
    if lmdim != second_lmdim:
        raise ValueError("matrix orbital dimensions must be square")
    label = "last nonzero SET_DD_PAW" if kind == "cso" else "PRE_LOOP input CPROJ"
    lines = [f"# HEIDE_PATCH_B {label}"]
    if kind == "cso":
        lines.extend(
            [
                "# SET_DD_PAW_CALL         1",
                f"# LMDIM NIONS NCDIJ{lmdim:10d}{nions:10d}{ncdij:10d}",
                "# LSORBIT= T LNONCOLLINEAR= T LSPIRAL= F",
                "# QSPIRAL  0.0000000000000000E+00  0.0000000000000000E+00  0.0000000000000000E+00",
                "# SAXIS " + "".join(f"{x:24.16E}" for x in saxis),
                f"# NELECT {nelect:24.16E}",
            ]
        )
    else:
        lines.extend(
            [
                f"# LMDIM NIONS NCDIJ{lmdim:10d}{nions:10d}{ncdij:10d}",
                f"# NELECT {nelect:24.16E}",
            ]
        )
    lines.append("# columns: ION IS I J Re Im")
    for ion in range(nions):
        for is_index in range(ncdij):
            for i in range(lmdim):
                for j in range(lmdim):
                    value = matrix[is_index, ion, i, j]
                    lines.append(
                        f"{ion + 1:8d}{is_index + 1:8d}{i + 1:8d}{j + 1:8d}"
                        f"{value.real:24.16E}{value.imag:24.16E}"
                    )
    if kind == "cocc":
        trace_values = []
        for ion in range(nions):
            trace_value = float(np.trace(matrix[0, ion]).real + np.trace(matrix[3, ion]).real)
            trace_values.append(trace_value)
            lines.append(f"# TRACE_CHECK ION{ion + 1:8d}{trace_value:24.16E}")
        lines.append(f"# TRACE_CHECK TOTAL{sum(trace_values):24.16E}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_fake_dump(
    tmpdir: str | Path,
    *,
    nk: int = 4,
    nb: int = 6,
    nions: int = 3,
    lmdim: int = 8,
    ncdij: int = 4,
    n_kgrp: int = 2,
    n_bgrp: int = 2,
    lsorbit: bool = False,
    lspiral: bool = True,
    q: tuple[float, float, float] = (0.25, 0.0, 0.0),
    nelect: int = 4,
    seed: int = 0,
    collinear: bool = False,
) -> DumpPaths:
    """Write the native stream layout from csodump.F lines 141--184."""

    directory = Path(tmpdir)
    directory.mkdir(parents=True, exist_ok=True)
    if nk < 1 or nb < 1 or nions < 1 or lmdim < 1:
        raise ValueError("fake dump dimensions must be positive")
    if ncdij != 4:
        raise ValueError("the synthetic noncollinear fixture requires NCDIJ=4")
    if nk % n_kgrp or nb % n_bgrp:
        raise ValueError("nk and nb must be divisible by their synthetic rank-group counts")
    if not 0 < nelect <= nb:
        raise ValueError("nelect must fit the noncollinear band count (RSPIN=1)")

    rng = np.random.default_rng(seed)
    cproj = (
        rng.normal(size=(1, nk, nions, 2, lmdim, nb))
        + 1j * rng.normal(size=(1, nk, nions, 2, lmdim, nb))
    ).astype(np.complex128)
    weights = np.full(nk, 1.0 / nk, dtype=np.float64)
    occupations = np.zeros((1, nk, nb), dtype=np.float64)
    if collinear:
        cproj[:, :, :, 1] = cproj[:, :, :, 0]
    occupations[:, :, :nelect] = 1.0
    if nelect < nb:  # Smeared edge: fractional on even k, Methfessel-Paxton overshoot on odd k.
        occupations[:, 0::2, nelect - 1:nelect + 1] = (0.7, 0.3)
        occupations[:, 1::2, nelect - 1:nelect + 1] = (1.04, -0.04)

    lmmax = tuple(lmdim for _ in range(nions))
    lmbase = tuple(ion * lmdim for ion in range(nions))
    cproj_paths: list[Path] = []
    for k_group in range(n_kgrp):
        for band_group in range(n_bgrp):
            path = directory / f"CPROJ.{k_group:04d}.{band_group:04d}.bin"
            cproj_paths.append(path)
            local_kpoints = [index for index in range(nk) if index % n_kgrp == k_group]
            local_bands = [index for index in range(nb) if index % n_bgrp == band_group]
            pieces = [
                _fixed(CPROJ_MAGIC, 32),
                struct.pack("<i", 1),
                _fixed(CPROJ_BUILD_ID, 32),
                _fixed(CPROJ_DUMP_TAG, 16),
                struct.pack("<i", 1),
                struct.pack("<4i", nions, lmdim, ncdij, 2),
                struct.pack("<4i", len(local_bands), nb, nk, 1),
                struct.pack("<2i", band_group + 1, n_bgrp),
                struct.pack("<4i", k_group + 1, n_kgrp, band_group + 1, n_bgrp),
                struct.pack("<3i", int(lsorbit), 1, int(lspiral)),
                struct.pack("<3d", *q),
                struct.pack("<3d", 0.0, 0.0, 1.0),
                struct.pack("<2d", float(nelect), 400.0),
                struct.pack(f"<{nions}i", *lmmax),
                struct.pack(f"<{nions + 1}i", *lmbase, sum(lmmax)),
            ]
            for kpoint in local_kpoints:
                for band in local_bands:
                    pieces.append(
                        struct.pack(
                            "<3i4d",
                            kpoint + 1,
                            band + 1,
                            1,
                            weights[kpoint],
                            float(band),
                            0.125,  # CELEN imaginary component must not shift CPROJ.
                            occupations[0, kpoint, band],
                        )
                    )
                    for spinor in range(2):
                        for ion in range(nions):
                            for lm in range(lmdim):
                                value = cproj[0, kpoint, ion, spinor, lm, band]
                                pieces.append(struct.pack("<2d", value.real, value.imag))
            path.write_bytes(b"".join(pieces))

    ferwe_path = directory / "FERWE.dat"
    ferwe_lines = [
        "# HEIDE_PATCH_B PRE_LOOP input occupations",
        f"# NKPTS NBANDS ISPIN{nk:10d}{nb:10d}{1:10d}",
        "# columns: NK NB ISP WTKPT EIG_Re FERWE",
    ]
    for kpoint in range(nk):
        for band in range(nb):
            ferwe_lines.append(
                f"{kpoint + 1:8d}{band + 1:8d}{1:8d}{weights[kpoint]:24.16E}"
                f"{float(band):24.16E}{occupations[0, kpoint, band]:24.16E}"
            )
    ferwe_lines.extend(
        [
            f"# SANITY SUM_W SUM_FW NELECT{np.sum(weights):24.16E}{float(nelect):24.16E}{float(nelect):24.16E}",
            f"# SANITY MIN_F MAX_F{np.min(occupations):24.16E}{np.max(occupations):24.16E}",
        ]
    )
    ferwe_path.write_text("\n".join(ferwe_lines) + "\n", encoding="utf-8")

    cocc = np.zeros((ncdij, nions, lmdim, lmdim), dtype=np.complex128)
    spin_pairs = ((0, 0), (1, 0), (0, 1), (1, 1))
    for is_index, (bra_spin, ket_spin) in enumerate(spin_pairs):
        for ion in range(nions):
            for kpoint in range(nk):
                for band in range(nb):
                    weight = weights[kpoint] * occupations[0, kpoint, band]
                    if weight == 0.0:
                        continue
                    for i in range(lmdim):
                        for j in range(lmdim):
                            cocc[is_index, ion, i, j] += (
                                np.conj(cproj[0, kpoint, ion, bra_spin, i, band])
                                * cproj[0, kpoint, ion, ket_spin, j, band]
                                * weight
                            )
    cocc_path = directory / "COCC.dat"
    _write_matrix(cocc_path, cocc, "cocc", nelect=float(nelect))
    return DumpPaths(
        directory=directory,
        cproj_paths=tuple(cproj_paths),
        ferwe_path=ferwe_path,
        cocc_path=cocc_path,
        cproj=cproj,
        occupations=occupations,
        weights=weights,
        cocc=cocc,
    )


def make_clean_cso(nions: int, lmdim: int) -> np.ndarray:
    matrix = np.zeros((4, nions, lmdim, lmdim), dtype=np.complex128)
    for ion in range(nions):
        scale = float(ion + 1)
        for i in range(lmdim):
            for j in range(i + 1, lmdim):
                value = 1j * scale * float(1 + i + 2 * j)
                matrix[0, ion, i, j] = value
                matrix[0, ion, j, i] = -value
        matrix[3, ion] = -matrix[0, ion]
        flip = scale * (np.arange(lmdim * lmdim).reshape(lmdim, lmdim) + 1 + 0.3j)
        matrix[1, ion] = flip
        matrix[2, ion] = flip.conj().T
    return matrix


def write_cso(path: str | Path, matrix: np.ndarray, *, nelect: float = 8.0,
              saxis: tuple[float, float, float] = (0.0, 0.0, 1.0)) -> Path:
    output = Path(path)
    _write_matrix(output, matrix, "cso", nelect=nelect, saxis=saxis)
    return output


def write_cocc(path: str | Path, matrix: np.ndarray, *, nelect: float) -> Path:
    """A COCC.dat alone, as a production dump_P writes it without CPROJ."""
    output = Path(path)
    _write_matrix(output, matrix, "cocc", nelect=nelect)
    return output


def bfo():
    """Rhombohedral R3c BFO with the threefold axis on z: (lattice, species, tau).

    A test geometry, not a relaxed one. Positions are as a POSCAR may write them,
    not wrapped into [0, 1): the second Fe sits at x - 1/2, so wrapping it would
    change its spiral phase.
    """
    a, alpha = 5.54, np.radians(59.71)
    r = np.sqrt(2 * (1 - np.cos(alpha)) / 3)
    phi = 2 * np.pi * np.arange(3) / 3
    lattice = a * np.column_stack([r * np.cos(phi), r * np.sin(phi), np.full(3, np.sqrt(1 - r * r))])
    x, (o1, o2, o3) = .225, (.541, .939, .394)
    oxygen = [(o1, o2, o3), (o3, o1, o2), (o2, o3, o1)]
    oxygen += [(p + .5, q + .5, s + .5) for p, q, s in [(o2, o1, o3), (o3, o2, o1), (o1, o3, o2)]]
    tau = np.array([(0, 0, 0), (.5, .5, .5), (x, x, x), (x - .5, x - .5, x - .5)] + oxygen)
    return lattice, ["Bi"] * 2 + ["Fe"] * 2 + ["O"] * 6, tau
