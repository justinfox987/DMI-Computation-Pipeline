"""Readback for the in-plane collinear N0 acceptance run only.

The final-table parser is adapted from v2 realized.py. General F1/F2
realization and frame generation stay deferred until N0 passes.
"""

from pathlib import Path
import re

import numpy as np

from . import conventions


def incar(path: str | Path) -> dict[str, str]:
    text = Path(path).read_text(encoding="utf-8").replace("\\\n", " ")
    tags = {}
    for line in text.splitlines():
        for part in re.split(r"[#!]", line, maxsplit=1)[0].split(";"):
            if "=" in part:
                key, value = part.split("=", 1)
                key = key.strip().upper()
                if key in tags:
                    raise ValueError(f"Duplicate INCAR tag {key}")
                tags[key] = value.strip()
    if "I_CONSTRAINTED_M" in tags:
        raise ValueError("Misspelled I_CONSTRAINTED_M; use I_CONSTRAINED_M")
    return tags


def numbers(value: str) -> np.ndarray:
    result = []
    for token in value.replace(",", " ").split():
        count, number = token.split("*", 1) if "*" in token else ("1", token)
        result.extend([float(number.replace("D", "E").replace("d", "e"))] * int(count))
    result = np.asarray(result, dtype=float)
    if not np.all(np.isfinite(result)):
        raise ValueError("Non-finite INCAR vector")
    return result


def logical(tags: dict, key: str, default: bool = False) -> bool:
    value = tags.get(key, "T" if default else "F").strip(".").upper()
    if value not in {"T", "TRUE", "F", "FALSE"}:
        raise ValueError(f"Invalid logical {key}={value}")
    return value in {"T", "TRUE"}


def poscar_species(path: str | Path) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    symbols, counts = lines[5].split(), [int(n) for n in lines[6].split()]
    if len(symbols) != len(counts) or any(n <= 0 for n in counts):
        raise ValueError("N0 registration requires a VASP 5/6 POSCAR with species names")
    return [symbol for symbol, count in zip(symbols, counts) for _ in range(count)]


def _parse_magnetization_block(lines: list[str], start: int, n_ions: int) -> tuple[np.ndarray, int]:
    i = start + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or not lines[i].strip().startswith("# of ion"):
        raise ValueError("Missing magnetization table header")
    i += 2  # header and separator
    values = []
    for ion in range(n_ions):
        if i >= len(lines):
            raise ValueError("Truncated final magnetization table")
        parts = lines[i].split()
        if len(parts) < 3 or parts[0] != str(ion + 1):
            raise ValueError(f"Invalid final magnetization row for ion {ion + 1}")
        values.append(float(parts[-1]))
        i += 1
    return np.asarray(values), i


def read_outcar_moments(directory: str | Path, n_ions: int) -> np.ndarray:
    lines = (Path(directory) / "OUTCAR").read_text(encoding="utf-8", errors="replace").splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == "magnetization (x)"]
    if not starts:
        raise ValueError("No final noncollinear magnetization tables")
    position = starts[-1]
    values = []
    for axis in "xyz":
        while position < len(lines) and lines[position].strip() != f"magnetization ({axis})":
            position += 1
        if position == len(lines):
            raise ValueError(f"Missing final magnetization ({axis})")
        component, position = _parse_magnetization_block(lines, position, n_ions)
        values.append(component)
    result = np.stack(values, axis=1)
    if not np.all(np.isfinite(result)):
        raise ValueError("Non-finite final magnetic moments")
    return result


def null_state(directory: str | Path, config: dict) -> dict:
    """Gauge-invariant R0: q=0, collinear planar moments, recorded eps and magnitudes."""
    directory = Path(directory)
    tags = incar(directory / "INCAR")
    if logical(tags, "LSORBIT") or not logical(tags, "LNONCOLLINEAR"):
        raise ValueError("N0 needs a SOC-free noncollinear run")
    q = numbers(tags.get("QSPIRAL", "0 0 0"))
    if q.shape != (3,) or np.any(q != 0):
        raise ValueError("N0 requires QSPIRAL=0")
    if not np.array_equal(numbers(tags.get("SAXIS", "0 0 1")), [0, 0, 1]):
        raise ValueError("N0 requires SAXIS=0 0 1")
    if int(tags.get("I_CONSTRAINED_M", "0")) != 0:
        raise ValueError("This N0 bootstrap supports the unconstrained F0 null only")
    species = config["species"]
    if poscar_species(directory / "POSCAR") != species:
        raise ValueError("POSCAR species/order changed since registration")
    indices = np.asarray(config["magnetic_indices"], dtype=int)
    expected = np.asarray(config["moment_ref"], dtype=float)
    eps = np.asarray(config["eps"], dtype=float)
    all_moments = read_outcar_moments(directory, len(species))
    m = all_moments[indices]
    mag = np.linalg.norm(m, axis=1)
    if np.any(mag <= 1e-12):
        raise ValueError("Collapsed magnetic moment in N0 reference")
    # Remove AFM signs, then measure relative azimuths; global phase is free.
    alpha = np.angle((m[:, 0] + 1j * m[:, 1]) * eps)
    phase = np.angle(np.mean(np.exp(1j * alpha)))
    residual = np.angle(np.exp(1j * (alpha - phase)))
    theta_error = np.abs(np.arcsin(np.clip(m[:, 2] / mag, -1, 1)))
    relative_moment = np.abs(mag - expected) / expected
    # Include induced nonmagnetic moments in the collinearity prerequisite.
    axis = np.array([np.cos(phase), np.sin(phase), 0.0])
    perpendicular = all_moments - np.outer(all_moments @ axis, axis)
    transverse = float(np.max(np.linalg.norm(perpendicular, axis=1)))
    passed = (np.max(np.abs(residual)) < np.deg2rad(conventions.TOL_PHI_DEG)
              and np.max(theta_error) < np.deg2rad(conventions.TOL_THETA_DEG)
              and np.max(relative_moment) < conventions.TOL_MOMENT_REL
              and transverse < float(np.max(mag)) * np.sin(np.deg2rad(conventions.TOL_PHI_DEG)))
    return {"name": "R0", "passed": bool(passed), "frame": conventions.FRAME_MINT,
            "global_phase_deg": float(np.rad2deg(phase)),
            "phase_error_deg": np.rad2deg(residual).tolist(),
            "theta_error_deg": np.rad2deg(theta_error).tolist(),
            "moment_relative_error": relative_moment.tolist(),
            "transverse_max_muB": transverse, "moments_muB": all_moments.tolist()}
