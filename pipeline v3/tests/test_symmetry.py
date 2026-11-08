"""Symmetry module: math Section 7 and plans/ten-02-symmetry.md.

The structures are test geometries, not relaxed ones.
"""

import numpy as np
import pytest

from dmi_pipeline import symmetry
from dmi_pipeline.realized import poscar

FCC = [(0, 0, 0), (0, .5, .5), (.5, 0, .5), (.5, .5, 0)]


def bcc(two_site):
    a = 2.863
    if two_site:
        return a * np.eye(3), ["Fe"] * 2, np.array([(0, 0, 0), (.5, .5, .5)])
    return a / 2 * (np.ones((3, 3)) - 2 * np.eye(3)), ["Fe"], np.zeros((1, 3))


def fcc():
    return 3.6 * np.eye(3), ["Ni"] * 4, np.array(FCC, float)


def fege():
    def b20(x):
        return [(x, x, x), (.5 + x, .5 - x, -x), (-x, .5 + x, .5 - x), (.5 - x, -x, .5 + x)]
    return 4.70 * np.eye(3), ["Fe"] * 4 + ["Ge"] * 4, np.array(b20(.135) + b20(.842)) % 1


def bfo():
    """Rhombohedral R3c with the threefold axis on z."""
    a, alpha = 5.54, np.radians(59.71)
    r = np.sqrt(2 * (1 - np.cos(alpha)) / 3)
    phi = 2 * np.pi * np.arange(3) / 3
    lattice = a * np.column_stack([r * np.cos(phi), r * np.sin(phi), np.full(3, np.sqrt(1 - r * r))])
    x, (o1, o2, o3) = .225, (.541, .939, .394)
    oxygen = [(o1, o2, o3), (o3, o1, o2), (o2, o3, o1)]
    oxygen += [(p + .5, q + .5, s + .5) for p, q, s in [(o2, o1, o3), (o3, o2, o1), (o1, o3, o2)]]
    tau = np.array([(0, 0, 0), (.5, .5, .5), (x, x, x), (x + .5, x + .5, x + .5)] + oxygen) % 1
    return lattice, ["Bi"] * 2 + ["Fe"] * 2 + ["O"] * 6, tau


def zincblende(primitive, c=6.3):
    a = 6.0
    if primitive:
        lattice = np.array([(0, a / 2, c / 2), (a / 2, 0, c / 2), (a / 2, a / 2, 0)])
        return lattice, ["Cr", "Sb"], np.array([(0, 0, 0), (.25, .25, .25)])
    tau = np.array(FCC + [np.add(f, .25) for f in FCC]) % 1
    return np.diag([a, a, c]), ["Cr"] * 4 + ["Sb"] * 4, tau


def counts(structure, sites, signs, **kwargs):
    ops = symmetry.operations(*structure, sites, signs, **kwargs)
    R = ops["rotations"]
    return ops, symmetry.spiralization_basis(R), symmetry.stiffness_basis(R)


def same_span(basis, expected):
    """Bases agree up to order, sign and mixing: compare their projectors."""
    def projector(matrices):
        q = np.linalg.qr(np.reshape(matrices, (len(matrices), 9)).T)[0]
        return q @ q.T
    if len(basis) != len(expected):
        return False
    return len(basis) == 0 or np.allclose(projector(basis), projector(expected), atol=1e-10)


def closure(generators):
    group = [np.eye(3)]
    while True:
        new = [g @ h for g in group for h in generators
               if not any(np.allclose(g @ h, k) for k in group)]
        if not new:
            return np.array(group)
        for g in new:
            if not any(np.allclose(g, k) for k in group):
                group.append(g)


def rot_z(n):
    c, s = np.cos(2 * np.pi / n), np.sin(2 * np.pi / n)
    return np.array([(c, -s, 0), (s, c, 0), (0, 0, 1)])


Z = np.array([(0, -1, 0), (1, 0, 0), (0, 0, 0)])           # [z]_x
PERP, PARA = np.diag([1, 1, 0]), np.diag([0, 0, 1])
I3, ZERO = np.eye(3), np.zeros((0, 3, 3))


def test_section_7_4_table(tmp_path):
    c3 = np.array([(0, 0, 1), (1, 0, 0), (0, 1, 0)])          # threefold on [111]
    mirror_x, c2x = np.diag([-1, 1, 1]), np.diag([1, -1, -1])
    s4z = np.array([(0, -1, 0), (1, 0, 0), (0, 0, -1)])
    t23 = [rot_z(2), c3]
    table = [  # generators, D forms, A forms (None: not fixed by the table)
        ([-I3], ZERO, None),
        (t23, [I3], [I3]),
        (t23 + [np.array([(0, 1, 0), (1, 0, 0), (0, 0, 1)])], ZERO, [I3]),
        ([rot_z(3), mirror_x], [Z], [PERP, PARA]),
        ([rot_z(4), mirror_x], [Z], [PERP, PARA]),
        ([rot_z(6), mirror_x], [Z], [PERP, PARA]),
        ([rot_z(6), c2x], [PERP, PARA], [PERP, PARA]),
        ([s4z, c2x], [np.diag([1, -1, 0])], [PERP, PARA]),
    ]
    for generators, d_form, a_form in table:
        group = closure(generators)
        assert same_span(symmetry.spiralization_basis(group), d_form)
        assert a_form is None or same_span(symmetry.stiffness_basis(group), a_form)

    # Strained zincblende end to end from a POSCAR at scale 2: I-4m2, D diag(1, -1, 0).
    lattice, species, tau = zincblende(primitive=False)
    text = "CrSb\n2.0\n" + "".join(" ".join(map(str, row / 2)) + "\n" for row in lattice)
    text += "Cr Sb\n4 4\nSelective dynamics\nDirect\n"
    text += "".join(" ".join(map(str, row)) + " T T T\n" for row in tau)
    (tmp_path / "POSCAR").write_text(text)
    structure = poscar(tmp_path / "POSCAR")
    assert np.allclose(structure[0], lattice) and structure[1] == species
    for structure, sites, total in [(structure, range(4), 32), (zincblende(True), [0], 8)]:
        ops, d, a = counts(structure, list(sites), [1] * len(sites))
        assert (ops["symbol"], ops["total"], ops["dropped"]) == ("I-4m2", total, 0)
        assert same_span(d, [np.diag([1, -1, 0])]) and same_span(a, [PERP, PARA])
        assert symmetry.twist_count(ops["rotations"], ops["permutations"]) == 0


def test_patterns_and_twist():
    cases = [  # structure, sites, signs, symbol, total, kept, p_D, p_A, n_twist
        (fcc(), range(4), [1, 1, 1, 1], "Fm-3m", 192, 192, 0, 1, 0),
        (fcc(), range(4), [1, 1, -1, -1], "Fm-3m", 192, 64, 0, 2, 0),
        (fcc(), range(4), [1, -1, -1, -1], "Fm-3m", 192, 48, 0, 1, 0),
        (fege(), range(4), [1] * 4, "P2_13", 12, 12, 1, 1, 1),
        (bfo(), [2, 3], [1, -1], "R3c", 6, 6, 1, 2, 0),
    ]
    for structure, sites, signs, symbol, total, kept, p_d, p_a, n_twist in cases:
        ops, d, a = counts(structure, list(sites), signs)
        assert (ops["symbol"], ops["total"], total - ops["dropped"]) == (symbol, total, kept)
        assert (len(d), len(a)) == (p_d, p_a)
        assert symmetry.twist_count(ops["rotations"], ops["permutations"]) == n_twist
    assert same_span(counts(fege(), range(4), [1] * 4)[1], [I3])
    assert same_span(counts(bfo(), [2, 3], [1, -1])[1], [Z])

    # Guards. Noisy BFO reads as P1 at symprec 1e-3 and passes every other check.
    lattice, species, tau = bfo()
    noisy = (lattice, species, tau + np.random.default_rng(7).normal(0, 2e-4, tau.shape))
    assert symmetry.operations(*noisy, [2, 3], [1, -1])["symbol"] == "P1"
    with pytest.raises(ValueError, match="space group 1 "):
        symmetry.operations(*noisy, [2, 3], [1, -1], spacegroup=161)
    with pytest.raises(ValueError, match="Non-orthogonal"):
        symmetry.operations(*zincblende(False, c=6.006), range(4), [1] * 4, symprec=0.01)
    with pytest.raises(ValueError, match="magnetic sites"):
        symmetry.operations(*bfo(), [2], [1])


def test_exchange_classes():
    q = np.array([.31, .17, -.09])

    def phi(structure, signs):
        ops = symmetry.operations(*structure, range(len(signs)), signs)
        classes = symmetry.exchange_classes(structure[0], structure[2], signs,
                                            ops["rotations"], rmax=4.1, tol=1e-6)
        values = [c["sign"] * (1 - np.cos(c["vectors"] @ q)).sum() / len(signs) for c in classes]
        return np.array(values), [len(c["vectors"]) for c in classes]

    primitive, _ = phi(bcc(False), [1])
    ferro, multiplicity = phi(bcc(True), [1, 1])
    g_type, _ = phi(bcc(True), [1, -1])
    assert multiplicity == [8, 6, 12]
    assert np.allclose(primitive, ferro, atol=1e-12)
    assert np.allclose(g_type, ferro * [-1, 1, 1], atol=1e-12)
