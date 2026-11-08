"""INCAR and POSCAR helpers shared by the readers."""

from pathlib import Path
import re

import numpy as np

# Input-only registration still rejects unknown tags instead of treating the
# verbatim INCAR echo as evidence VASP recognized a typo.
INCAR_TAGS = set("""
SYSTEM ENCUT ENINI ENAUG PREC NCORE NPAR KPAR NBANDS NEDOS ISTART ICHARG ISMEAR SIGMA
IBRION POTIM ISIF NSW NELM NELMIN NELMDL ISYM SYMPREC LMAXMIX LMAXPAW ALGO IALGO
ISEARCH EDIFF EDIFFG LREAL LORBIT GGA AMIX BMIX AMIX_MAG BMIX_MAG AMIN IMIX
ISPIN GGA_COMPAT LASPH MAGMOM LDAU LDAUPRINT LDAUTYPE LDAUL LDAUU LDAUJ
LNONCOLLINEAR LSORBIT LSPIRAL QSPIRAL SAXIS LZEROZ RWIGS I_CONSTRAINED_M LAMBDA
M_CONSTR LWAVE LCHARG LDUMPCOCC LDUMPCPROJ LDUMPCSO LPLANE LSCALAPACK NSIM
ADDGRID NELECT NWRITE LVTOT LVHAR LAECHG LELF LASPH LDAUTYPE
""".split())


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


def poscar(path: str | Path) -> tuple[np.ndarray, list[str], np.ndarray]:
    """VASP 5/6 POSCAR: (lattice rows in Å, species per atom, Direct positions)."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if len(lines) < 8:
        raise ValueError("Incomplete POSCAR")
    scale = lines[1].split()
    if len(scale) != 1:
        raise ValueError("POSCAR needs one scale factor; three-value scales are not supported")
    # A negative scale means a target volume in VASP; refuse rather than guess.
    if not float(scale[0]) > 0:
        raise ValueError("POSCAR scale factor must be positive")
    lattice = float(scale[0]) * np.array([line.split()[:3] for line in lines[2:5]], dtype=float)
    symbols, counts = lines[5].split(), [int(n) for n in lines[6].split()]
    if len(symbols) != len(counts) or any(n <= 0 for n in counts):
        raise ValueError("POSCAR needs VASP 5/6 species names and positive counts")
    species = [symbol for symbol, count in zip(symbols, counts) for _ in range(count)]
    start = 8 if lines[7].strip().lower().startswith("s") else 7
    if start >= len(lines) or not lines[start].strip().lower().startswith("d"):
        raise ValueError("POSCAR positions must be Direct, not Cartesian")
    rows = [line.split()[:3] for line in lines[start + 1:start + 1 + len(species)]]
    if len(rows) != len(species) or any(len(row) != 3 for row in rows):
        raise ValueError("POSCAR position count mismatch")
    tau = np.array(rows, dtype=float)
    if not (np.all(np.isfinite(lattice)) and np.all(np.isfinite(tau))):
        raise ValueError("Non-finite POSCAR value")
    return lattice, species, tau


def echo_check(directory: Path) -> dict:
    tags = incar(directory / "INCAR")
    unknown = set(tags) - INCAR_TAGS
    if unknown:
        raise ValueError(f"Unreviewed INCAR tags: {sorted(unknown)}")
    text = (directory / "OUTCAR").read_text(encoding="utf-8", errors="replace")
    if "General timing and accounting" not in text:
        raise ValueError("OUTCAR has no completed-job timing footer")
    for key, expected in tags.items():
        # VASP's initial INCAR block retains every supplied value, including
        # vector tags and ALGO. Compare tokens, not substring matches.
        matches = re.findall(r"^\s*" + re.escape(key) + r"\s*=\s*(.*)$", text, re.M)
        def equal(actual):
            a, b = actual.split(), expected.split()
            if a[:len(b)] == b:
                return True
            try:
                x, y = numbers(" ".join(a[:len(b)])), numbers(expected)
                return x.shape == y.shape and np.allclose(x, y, atol=1e-12, rtol=1e-8)
            except ValueError:
                return " ".join(a[:len(b)]).strip(".").upper() == expected.strip(".").upper()
        if not any(equal(actual) for actual in matches):
            raise ValueError(f"OUTCAR does not echo the requested {key}={expected}")
    return {"passed": True, "checked_tags": sorted(tags)}
