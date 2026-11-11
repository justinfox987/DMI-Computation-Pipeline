"""M1, once per production build (D-021; math Section 11).

Compares the dump_P COCC.dat with the density matrix rebuilt from CPROJ and
FERWE of the same capture. It tests the Fortran routine COCC_FROM_INPUT, a
property of the build, so it runs on one state whose dump_P the user gave
LDUMPCPROJ = T. Usage:

    python acceptance/m1.py DUMP_P_DIR

Prints the largest deviation and exits 1 above 1e-10.

CPROJ.*.bin is the Fortran stream of WRITE_CPROJ_PRELOOP (csodump.F lines
141-184), read with a fixed layout: little-endian, 4-byte INTEGER and LOGICAL,
8-byte REAL. A build with another layout fails on the magic string or the
record size, never silently.
"""

from pathlib import Path
import struct
import sys

import numpy as np

from dmi_pipeline.dumpio import load_cocc

MAGIC = "HEIDE_CPROJ_PATCH_B"
TOL = 1e-10
# magic, version, build id, dump tag, call counter, 14 dimensions and ranks,
# LSORBIT LNONCOLLINEAR LSPIRAL, QSPIRAL, SAXIS, NELECT, ENMAX.
HEADER = struct.Struct("<32si32s16si14i3i8d")
# COCC_FROM_INPUT: COCC(LP, L, 1 + s_ + 2s) += w f conj(c(LP, s_)) c(L, s);
# block index -> (bra spin s_, ket spin s).
COCC_SPIN_BLOCKS = ((0, 0), (1, 0), (0, 1), (1, 1))


def read_cproj(directory):
    """Every rank file assembled by global index; each (spin, k, band) exactly once.

    Returns (c[k, ion, spinor, lm, band], weights[k], occupations[k, band], nelect, lmmax).
    """
    paths = sorted(Path(directory).glob("CPROJ.*.bin"))
    if not paths:
        raise ValueError(f"No CPROJ.*.bin in {directory}; the dump_P needs LDUMPCPROJ = T")
    c = weights = occupations = coverage = None
    for path in paths:
        data = path.read_bytes()
        fields = HEADER.unpack_from(data)
        magic = fields[0].decode("ascii", "replace").rstrip()
        if magic != MAGIC:
            raise ValueError(f"{path.name}: magic {magic!r}, expected {MAGIC!r}; not a little-endian i4 Patch B dump")
        nions, lmdim, ncdij, nrspinors, _, nbands, nkpts, ispin = fields[5:13]
        lsorbit, lnoncollinear = fields[19:21]
        nelect = fields[28]
        offset = HEADER.size
        lmmax = struct.unpack_from(f"<{nions}i", data, offset)
        lmbase = struct.unpack_from(f"<{nions + 1}i", data, offset + 4 * nions)
        offset += 4 * (2 * nions + 1)
        if (ispin, nrspinors, ncdij, bool(lsorbit), bool(lnoncollinear)) != (1, 2, 4, False, True):  # .TRUE. may be -1
            raise ValueError(f"{path.name}: M1 needs a SOC-free noncollinear state (ISPIN 1, 2 spinors, NCDIJ 4)")
        if list(lmbase) != list(np.cumsum((0,) + lmmax)) or lmdim != max(lmmax):
            raise ValueError(f"{path.name}: LMBASE or LMDIM disagrees with LMMAX_ION")
        npro = nrspinors * lmbase[-1]          # wave.F: NPRO = NRSPINORS * sum(LMMAX_ION)
        record = np.dtype([("nk", "<i4"), ("band", "<i4"), ("isp", "<i4"), ("w", "<f8"),
                           ("eig", "<f8", 2), ("f", "<f8"), ("c", "<f8", (npro, 2))])
        if (len(data) - offset) % record.itemsize:
            raise ValueError(f"{path.name}: record size does not divide the file")
        if c is None:
            c = np.zeros((nkpts, nions, nrspinors, lmdim, nbands), complex)
            weights, occupations = np.zeros(nkpts), np.zeros((nkpts, nbands))
            coverage = np.zeros((nkpts, nbands), int)
        for rec in np.frombuffer(data, record, offset=offset):
            k, b = rec["nk"] - 1, rec["band"] - 1
            if rec["isp"] != 1 or not (0 <= k < nkpts and 0 <= b < nbands):
                raise ValueError(f"{path.name}: record index (ISP, NK, BAND) = {rec['isp'], k + 1, b + 1} out of range")
            coverage[k, b] += 1
            weights[k], occupations[k, b] = rec["w"], rec["f"]
            values = rec["c"][:, 0] + 1j * rec["c"][:, 1]
            for ion, (n, base) in enumerate(zip(lmmax, lmbase)):
                for spinor in range(nrspinors):
                    start = base + spinor * lmbase[-1]
                    c[k, ion, spinor, :n, b] = values[start:start + n]
    if np.any(coverage != 1):
        k, b = np.argwhere(coverage != 1)[0]
        raise ValueError(f"CPROJ record (NK, BAND) = ({k + 1}, {b + 1}) occurs {coverage[k, b]} times, not once")
    return c, weights, occupations, nelect, lmmax


def read_ferwe(path, nkpts, nbands):
    """Rows NK NB ISP WTKPT EIG FERWE; every (k, band) exactly once."""
    rows = np.array([line.split() for line in Path(path).read_text().splitlines()
                     if line.strip() and not line.lstrip().startswith("#")], float)
    if rows.shape != (nkpts * nbands, 6) or np.any(rows[:, 2] != 1):
        raise ValueError(f"{path}: expected {nkpts * nbands} ISP = 1 rows of 6 columns")
    k, b = rows[:, 0].astype(int) - 1, rows[:, 1].astype(int) - 1
    occupations, seen = np.zeros((nkpts, nbands)), np.zeros((nkpts, nbands), int)
    np.add.at(seen, (k, b), 1)
    if np.any(seen != 1):
        raise ValueError(f"{path}: a (k, band) row is missing or repeated")
    occupations[k, b] = rows[:, 5]
    return occupations


def m1(directory):
    """(deviation, (IS, ION, I, J) of the largest mismatch, 1-based) for one dump_P directory."""
    directory = Path(directory)
    c, weights, occupations, nelect, lmmax = read_cproj(directory)
    if not np.allclose(read_ferwe(directory / "FERWE.dat", *occupations.shape), occupations, atol=1e-8, rtol=0):
        raise ValueError("FERWE occupations disagree with the CPROJ records of the same capture")
    if not np.isclose(weights @ occupations.sum(axis=1), nelect, atol=1e-6, rtol=0):
        raise ValueError("sum w f differs from NELECT: noncollinear spinors need RSPIN = 1")
    cocc = load_cocc(directory / "COCC.dat")
    if not np.isclose(cocc.metadata.nelect, nelect, atol=1e-6, rtol=0):
        raise ValueError("COCC NELECT disagrees with CPROJ")
    rebuilt = np.zeros_like(cocc.matrix)
    wf = weights[:, None] * occupations
    for ion, n in enumerate(lmmax):
        for block, (bra, ket) in enumerate(COCC_SPIN_BLOCKS):
            rebuilt[block, ion, :n, :n] = np.einsum("kib,kjb,kb->ij", c[:, ion, bra, :n].conj(),
                                                    c[:, ion, ket, :n], wf, optimize=True)
    diff = np.abs(rebuilt - cocc.matrix)
    where = tuple(int(i) + 1 for i in np.unravel_index(np.argmax(diff), diff.shape))
    return float(diff.max()), where


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python acceptance/m1.py DUMP_P_DIR")
    deviation, where = m1(sys.argv[1])
    passed = deviation <= TOL
    print(f"M1 {'pass' if passed else 'FAIL'}: max |COCC - rebuild| = {deviation:.3e} "
          f"at (IS, ION, I, J) = {where}; tolerance {TOL:g}")
    raise SystemExit(0 if passed else 1)
