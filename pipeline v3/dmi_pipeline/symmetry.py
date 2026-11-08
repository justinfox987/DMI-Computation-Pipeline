"""Kept operations, tensor bases, twist count and exchange classes (math Section 7).

Everything is array-based and reads no files. Lattices are POSCAR row matrices in
Å, positions are fractional rows, and magnetic sites are 0-based.
"""

from itertools import product

import numpy as np
import spglib

ORTHOGONALITY = 1e-4   # largest |R^T R - I| accepted
RANK = 1e-8            # singular-value cutoff for bases and the twist count


def operations(lattice, species, tau, sites, signs, symprec=1e-3, spacegroup=None):
    """spglib operations that keep the sign pattern, Eqs (7.1)-(7.3)."""
    lattice, tau = np.asarray(lattice, float), np.asarray(tau, float)
    sites, signs = np.asarray(sites, int), np.asarray(signs, int)
    if len(sites) == 0 or signs.shape != sites.shape or not np.all(np.abs(signs) == 1):
        raise ValueError("Need one sign of +1 or -1 for each magnetic site")
    numbers = np.unique(species, return_inverse=True)[1]
    data = spglib.get_symmetry_dataset((lattice, tau, numbers), symprec=symprec)
    if data is None:
        raise ValueError("spglib found no symmetry; check for overlapping atoms")
    if spacegroup is not None and data.number != spacegroup:
        raise ValueError(f"spglib finds space group {data.number} ({data.international}) "
                         f"at symprec {symprec}, not the expected {spacegroup}")
    L = lattice.T                      # columns are lattice vectors
    frac = tau[sites]
    rotations, permutations = [], []
    for W, t in zip(data.rotations, data.translations):
        R = L @ W @ np.linalg.inv(L)
        if np.abs(R.T @ R - np.eye(3)).max() >= ORTHOGONALITY:
            raise ValueError("Non-orthogonal operation: the lattice is strained beyond symprec")
        # d[target, source]; pi[a] is the site that source a lands on, Eq (7.2).
        d = frac[:, None] - (frac @ W.T + t)[None, :]
        d -= np.rint(d)
        dist = np.linalg.norm(d @ lattice, axis=2)
        pi = dist.argmin(0)
        if len(set(pi)) != len(sites) or dist[pi, np.arange(len(sites))].max() >= 2 * symprec:
            raise ValueError("An operation does not map the magnetic sites onto each other")
        if abs((signs[pi] * signs).sum()) == len(sites):   # one global eta, Eq (7.3)
            rotations.append(R)
            permutations.append(pi)
    total = len(data.rotations)
    return {"rotations": np.array(rotations), "permutations": np.array(permutations),
            "number": data.number, "symbol": data.international,
            "total": total, "dropped": total - len(rotations)}


def _basis(projector):
    """Orthonormal 3x3 matrices spanning the projector's range."""
    u, s, _ = np.linalg.svd(projector)
    return u[:, s > RANK].T.reshape(-1, 3, 3)


def spiralization_basis(rotations):
    """Basis of allowed D, Eqs (7.6)-(7.7). det(R): D is a pseudotensor."""
    # kron(R, R) acts on row-major vec(M) as M -> R M R^T.
    return _basis(np.mean([np.linalg.det(R) * np.kron(R, R) for R in rotations], axis=0))


def stiffness_basis(rotations):
    """Basis of allowed symmetric A, Eqs (7.6)-(7.7)."""
    swap = np.eye(9).reshape(3, 3, 3, 3).transpose(0, 1, 3, 2).reshape(9, 9)
    projector = np.mean([np.kron(R, R) for R in rotations], axis=0)
    return _basis(projector @ (np.eye(9) + swap) / 2)


def twist_count(rotations, permutations):
    """Number of allowed intracell twist parameters, Eq (7.9)."""
    n = permutations.shape[1]
    average = np.zeros((3 * n, 3 * n))
    for R, pi in zip(rotations, permutations):
        for a, target in enumerate(pi):
            average[3 * target:3 * target + 3, 3 * a:3 * a + 3] += R
    Q = np.kron(np.eye(n) - 1.0 / n, np.eye(3))
    return int(np.linalg.matrix_rank(average @ Q / len(rotations), tol=RANK))


def exchange_classes(lattice, tau, signs, rotations, rmax, tol):
    """Bond classes within rmax for Eq (7.11), shortest first.

    tau holds the magnetic sites only. Each undirected bond appears once. Bonds
    with equal sign and r' = +-R r share a class, even across sublattices.
    """
    lattice, tau, signs = np.asarray(lattice, float), np.asarray(tau, float), np.asarray(signs)
    reach = np.ceil(rmax * np.linalg.norm(np.linalg.inv(lattice), axis=0)).astype(int) + 1
    T = np.array(list(product(*(range(-k, k + 1) for k in reach))))
    positive = np.sign(T) @ (4, 2, 1) > 0   # first nonzero component of T is positive
    bonds = []
    for a in range(len(tau)):
        for b in range(a, len(tau)):
            r = (tau[b] - tau[a] + T) @ lattice
            length = np.linalg.norm(r, axis=1)
            keep = (length > tol) & (length <= rmax + tol) & (positive if a == b else True)
            bonds += [(n, signs[a] * signs[b], v) for n, v in zip(length[keep], r[keep])]
    classes = []
    for _, sign, r in sorted(bonds, key=lambda bond: bond[0]):
        for c in classes:
            if c["sign"] == sign and np.linalg.norm(c["orbit"] - r, axis=1).min() < tol:
                c["vectors"].append(r)
                break
        else:
            orbit = np.asarray(rotations) @ r
            classes.append({"sign": sign, "orbit": np.vstack([orbit, -orbit]), "vectors": [r]})
    return [{"sign": int(c["sign"]), "vectors": np.array(c["vectors"])} for c in classes]
