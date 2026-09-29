"""Offline CSO rotation. Euler math reused from v2; Patch A reader removed.

The full operator is rotated before selecting diagonal blocks. Validation is
persisted against the source bytes, never enabled by a process-global flag.
"""

from dataclasses import replace

import numpy as np

from . import manifest
from .dumpio import MatrixDump

EULER_CONVENTIONS = tuple(f"a{sa}b{sb}U{d}" for sa in ("+", "-")
                          for sb in ("+", "-") for d in ("", "d"))
AXES = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}


def spin_rotation(n_hat: np.ndarray, convention: str) -> np.ndarray:
    """v2's eight sign/dagger candidates, with explicit unit-vector validation."""
    n = np.asarray(n_hat, dtype=np.float64)
    if n.shape != (3,) or not np.isclose(np.linalg.norm(n), 1.0, atol=1e-8, rtol=0):
        raise ValueError("n_hat must be a finite three-component unit vector")
    if convention not in EULER_CONVENTIONS:
        raise ValueError(f"Unknown Euler convention {convention!r}")
    s_alpha = 1.0 if convention[1] == "+" else -1.0
    s_beta = 1.0 if convention[3] == "+" else -1.0
    alpha = s_alpha * np.arctan2(n[1], n[0])
    beta = s_beta * np.arctan2(np.hypot(n[0], n[1]), n[2])
    U = np.array(
        [[np.cos(beta / 2) * np.exp(-1j * alpha / 2), -np.sin(beta / 2) * np.exp(-1j * alpha / 2)],
         [np.sin(beta / 2) * np.exp(+1j * alpha / 2), np.cos(beta / 2) * np.exp(+1j * alpha / 2)]],
        dtype=np.complex128,
    )
    return U.conj().T if convention.endswith("Ud") else U


def _rotate(matrix: np.ndarray, axis: str, convention: str) -> np.ndarray:
    if matrix.ndim != 4 or matrix.shape[0] != 4 or matrix.shape[-1] != matrix.shape[-2]:
        raise ValueError("CSO must have shape (4, nions, lm, lm)")
    U = spin_rotation(np.asarray(AXES[axis]), convention)
    spin = matrix.reshape(2, 2, *matrix.shape[1:])
    return np.einsum("st,tunij,uv->svnij", U.conj().T, spin, U, optimize=True).reshape(matrix.shape)


def validate_rotation(z: MatrixDump, x: MatrixDump, y: MatrixDump, tol: float = 1e-10) -> dict:
    if x.matrix.shape != z.matrix.shape or y.matrix.shape != z.matrix.shape:
        raise ValueError("T3 needs matching dimensions on all three dumps")
    for axis, dump in (("z", z), ("x", x), ("y", y)):
        if dump.metadata.saxis != AXES[axis]:
            raise ValueError(f"T3 {axis} dump has the wrong SAXIS header")
    errors = {c: max(float(np.max(np.abs(_rotate(z.matrix, "x", c) - x.matrix))),
                     float(np.max(np.abs(_rotate(z.matrix, "y", c) - y.matrix))))
              for c in EULER_CONVENTIONS}
    matches = [c for c, error in errors.items() if error <= tol]
    passed = len(matches) == 1
    return {"name": "T3", "passed": passed, "threshold": tol, "errors": errors,
            "euler_convention": matches[0] if passed else None,
            "detail": "All blocks and ions compared; one unique Euler convention required",
            "source_sha256": z.provenance.sha256,
            "files": {str(d.provenance.path.resolve()): d.provenance.sha256 for d in (z, x, y)}}


def rotate_saxis(z: MatrixDump, axis: str, validation: dict | None = None) -> MatrixDump:
    if axis not in AXES:
        raise ValueError("axis must be x, y, or z")
    if axis == "z":
        return z
    if not validation or validation.get("passed") is not True:
        raise ValueError("CSO rotation is not validated; run T3 before requesting x/y")
    if validation.get("source_sha256") != z.provenance.sha256:
        raise ValueError("T3 validated a different CSO source")
    manifest.check_files(validation["files"])
    return replace(z, matrix=_rotate(z.matrix, axis, validation["euler_convention"]),
                   metadata=replace(z.metadata, saxis=AXES[axis]))
