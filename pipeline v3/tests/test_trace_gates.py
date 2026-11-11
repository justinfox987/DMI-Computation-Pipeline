"""Section 11 checks and the trace vector of math Section 4."""

import numpy as np
import pytest

from dmi_pipeline.dumpio import load_cocc, load_cso
from dmi_pipeline.gates import gate_c0, gate_e0, gate_i0, gate_n0, gate_p0
from dmi_pipeline.trace import split_operator, trace_vector
from tests.fixtures import make_clean_cso, write_cocc, write_cso, write_fake_dump


def test_c0_rejects_operator_defects():
    assert gate_c0(make_clean_cso(2, 3)).passed
    same_sign, broken_flip, empty_flip, not_finite, exchanged = (make_clean_cso(2, 3) for _ in range(5))
    same_sign[3] = same_sign[0]
    broken_flip[1, 0, 1, 0] += 1
    empty_flip[1:3] = 0
    not_finite[0, 0, 0, 0] = np.nan
    exchanged = exchanged[[0, 2, 1, 3]]                            # Hermitian still; right-handed now
    for matrix in (same_sign, broken_flip, empty_flip, not_finite, exchanged):
        assert not gate_c0(matrix).passed
    assert "handedness h >= 0 on ions [1, 2]" in gate_c0(exchanged).detail


def test_vasp_file_layout_fixes_the_trace_sign(tmp_path):
    """Math Section 4.4 layout test (D-020): both files written as VASP writes them.

    relativistic.F stores CSO(lm, l'm', 1 + a + 2a') = <a'|<l'm'|C|lm>|a>; DEPSUM and
    COCC_FROM_INPUT store COCC(LP, L, 1 + s_ + 2s) = sum w f c(L, s) conj(c(LP, s_)).
    """
    xi = 0.3
    eps = np.zeros((3, 3, 3))
    eps[0, 1, 2] = eps[1, 2, 0] = eps[2, 0, 1] = 1
    eps[0, 2, 1] = eps[2, 1, 0] = eps[1, 0, 2] = -1
    lam = xi / 2 * -1j * eps                                       # xi L.S on a real p shell, (L_k)_ij = -i eps_kij
    pauli = np.array([[[0, 1], [1, 0]], [[0, -1j], [1j, 0]], [[1, 0], [0, -1]]])
    h_soc = sum(np.kron(pauli[a], lam[a]) for a in range(3))       # spin-major: index = 3 * spin + orbital
    rng = np.random.default_rng(11)
    psi = rng.normal(size=(5, 2, 3)) + 1j * rng.normal(size=(5, 2, 3))
    wf = np.array([0.4, 0.3, 0.2, 0.07, -0.01])                    # fractional and MP-negative occupations
    flat = psi.reshape(5, 6)
    exact_e = np.einsum("n,ni,ij,nj->", wf, flat.conj(), h_soc, flat).real
    exact_t = [np.einsum("n,ni,ij,nj->", wf, flat.conj(), np.kron(pauli[2], lam[a]), flat).real for a in range(3)]

    cso, cocc = np.zeros((4, 1, 3, 3), complex), np.zeros((4, 1, 3, 3), complex)
    for a in range(2):
        for b in range(2):
            cso[a + 2 * b, 0] = h_soc[3 * b:3 * b + 3, 3 * a:3 * a + 3].T
            cocc[a + 2 * b, 0] = np.einsum("n,nl,np->pl", wf, psi[:, b], psi[:, a].conj())
    cso = load_cso(write_cso(tmp_path / "CSO.dat", cso))
    cocc = load_cocc(write_cocc(tmp_path / "COCC.dat", cocc, nelect=8.0))

    assert np.sum(cso.matrix * cocc.matrix.conj()).real == pytest.approx(exact_e, abs=1e-12)
    assert gate_c0(cso).passed
    lx, ly, lz = split_operator(cso)[:, 0]
    handedness = np.trace((lx @ ly - ly @ lx) @ lz).imag / np.trace(lz @ lz).real ** 1.5
    assert handedness == pytest.approx(-1 / np.sqrt(2))            # left-handed in file arrays
    assert min(map(abs, exact_t)) > 1e-2
    assert trace_vector(cocc, split_operator(cso))[0].real == pytest.approx(exact_t, abs=1e-12)


def test_parity_checks(tmp_path):
    """N0 on a collinear state's trace vector, I0 on a non-Hermitian COCC, then P0 and E0."""
    files = write_fake_dump(tmp_path, nk=2, nb=4, nions=2, lmdim=3, n_kgrp=1, n_bgrp=1, nelect=2, collinear=True)
    cocc, lam = load_cocc(files.cocc_path), split_operator(make_clean_cso(2, 3))
    t = trace_vector(cocc, lam)
    assert gate_n0(t.real).passed and gate_i0(t.imag).passed
    files = write_fake_dump(tmp_path / "spiral", nk=2, nb=4, nions=2, lmdim=3, n_kgrp=1, n_bgrp=1, nelect=2)
    assert not gate_n0(trace_vector(load_cocc(files.cocc_path), lam).real).passed
    bad = cocc.matrix.copy()
    bad[0, 0, 0, 1] += 1e-3j                                       # breaks Hermiticity of rho
    assert not gate_i0(trace_vector(type(cocc)(bad, cocc.metadata), lam).imag).passed

    floor = 5e-5
    per_ion = np.zeros((3, 3))
    per_ion[1, 0], per_ion[2, 0] = 2 * floor, -2 * floor          # zero total, one ion over the floor
    assert not gate_n0(per_ion).passed and gate_n0(per_ion / 10).passed

    odd = np.array([1e-3, -2e-3, 5e-4])
    assert gate_p0(odd, -odd).passed
    background = 0.2 * odd                                         # a 20% even part
    assert not gate_p0(odd + background, -odd + background).passed
    assert gate_p0([1e-6, 0, 0], [1e-6, 0, 0]).passed              # inversion: both parts at the floor

    assert gate_e0(-9.99, -9.99 + 1e-4, -10.0).passed
    assert not gate_e0(-9.99, -9.985, -10.0).passed
