from dataclasses import replace

import numpy as np
import pytest

from dmi_pipeline.dumpio import load_cocc, load_cproj, load_cso, load_ferwe
from dmi_pipeline.gates import gate_c0, gate_e0, gate_i0, gate_m1, gate_n0, gate_p0, gate_t3
from dmi_pipeline.trace import split_operator, trace_vector
from tests.fixtures import cproj_trace as compute_delta_E1, make_clean_cso, write_cocc, write_cso, write_fake_dump


def inputs(tmp_path, *, collinear=False):
    files = write_fake_dump(tmp_path, nk=2, nb=4, nions=2, lmdim=3,
                            n_kgrp=1, n_bgrp=1, nelect=2, collinear=collinear)
    cso = load_cso(write_cso(tmp_path / "CSO.dat", make_clean_cso(2, 3), nelect=2))
    return load_cproj(tmp_path), load_ferwe(tmp_path), cso, files


def test_cproj_trace_matches_density_oracle(tmp_path):
    cp, occ, cso, _ = inputs(tmp_path)
    result = compute_delta_E1(cp, occ, cso)
    # Independent density-matrix route: rho = |c><c|, then Tr(C rho) with C = file.T (ket first).
    oracle = np.zeros((2, 2), complex)
    for ion in range(2):
        for k in range(2):
            for spin, block in ((0, 0), (1, 3)):
                states = cp.c[0, k, ion, spin]
                rho = (states * occ.occupations[0, k]) @ states.conj().T
                oracle[ion, k] += occ.weights[k] * np.trace(cso.matrix[block, ion].T @ rho)
    assert result.delta_E1 == pytest.approx(oracle.sum().real, abs=1e-12)
    assert result.per_ion == pytest.approx(dict(enumerate(oracle.sum(axis=1).real)), abs=1e-12)
    assert result.per_k == pytest.approx(oracle.sum(axis=0), abs=1e-12)
    assert gate_i0([result.imag_total, *result.imag_per_ion.values()]).passed


def test_spin_swap_sign_origin_phase_and_flip_independence(tmp_path):
    cp, occ, cso, _ = inputs(tmp_path)
    baseline = compute_delta_E1(cp, occ, cso).delta_E1
    assert abs(baseline) > 1e-3  # Ensure these invariance tests can discriminate.
    swapped = replace(cp, c=cp.c[:, :, :, [1, 0]].copy())
    assert compute_delta_E1(swapped, occ, cso).delta_E1 == pytest.approx(-baseline, abs=1e-12)
    phases = np.exp(1j * np.array([[0.17, -0.17], [0.31, -0.31]]))
    shifted = replace(cp, c=cp.c * phases[None, None, :, :, None, None])
    assert compute_delta_E1(shifted, occ, cso).delta_E1 == pytest.approx(baseline, abs=1e-12)
    matrix = cso.matrix.copy()
    matrix[1:3] *= 1e6
    assert compute_delta_E1(cp, occ, replace(cso, matrix=matrix)).delta_E1 == baseline


def test_collinear_null_and_same_capture_checks(tmp_path):
    cp, occ, cso, files = inputs(tmp_path, collinear=True)
    assert gate_n0(trace_vector(load_cocc(files.cocc_path), split_operator(cso)).real).passed
    wrong = replace(occ, occupations=occ.occupations[:, :, ::-1].copy())
    with pytest.raises(ValueError, match="occupations"):
        compute_delta_E1(cp, wrong, cso)
    with pytest.raises(ValueError, match="RSPIN"):
        compute_delta_E1(cp, replace(occ, spin_factor=2.0), cso)


def test_c0_rejects_operator_defects():
    assert gate_c0(make_clean_cso(2, 3)).passed
    same_sign, broken_flip, empty_flip, not_finite = (make_clean_cso(2, 3) for _ in range(4))
    same_sign[3] = same_sign[0]
    broken_flip[1, 0, 1, 0] += 1
    empty_flip[1:3] = 0
    not_finite[0, 0, 0, 0] = np.nan
    for matrix in (same_sign, broken_flip, empty_flip, not_finite):
        assert not gate_c0(matrix).passed


def test_m1_observes_off_diagonal_order_and_corruption(tmp_path):
    cp, occ, _, files = inputs(tmp_path)
    co = load_cocc(files.cocc_path)
    assert gate_m1(cp, occ, co).passed
    matrix = co.matrix.copy()
    matrix[[1, 2]] = matrix[[2, 1]]
    assert not gate_m1(cp, occ, replace(co, matrix=matrix)).passed
    matrix = co.matrix.copy()
    matrix[0, 0, 0, 0] += 1e-5
    assert not gate_m1(cp, occ, replace(co, matrix=matrix)).passed


def test_trace_vector_and_t3(tmp_path):
    """Eqs (4.3), (4.4) and (4.8) against the independent CPROJ route of Eq (4.7)."""
    cp, occ, cso, files = inputs(tmp_path)
    cocc = load_cocc(files.cocc_path)
    rng = np.random.default_rng(3)
    lam = rng.normal(size=(3, 2, 3, 3)) + 1j * rng.normal(size=(3, 2, 3, 3))
    lam = lam + lam.conj().swapaxes(-1, -2)                       # Hermitian Lambda per axis and ion
    z = replace(cso, matrix=np.array([lam[2], lam[0] - 1j * lam[1], lam[0] + 1j * lam[1], -lam[2]]))
    assert np.allclose(split_operator(z), lam, atol=1e-14)
    t = trace_vector(cocc, split_operator(z))
    for axis in range(3):
        diagonal = np.zeros_like(z.matrix)
        diagonal[0], diagonal[3] = lam[axis], -lam[axis]           # sum_s s c^dagger Lambda c
        reference = compute_delta_E1(cp, occ, replace(cso, matrix=diagonal))
        assert t[:, axis].real == pytest.approx(list(reference.per_ion.values()), abs=1e-12)
        assert t[:, axis].real.sum() == pytest.approx(reference.delta_E1, abs=1e-12)
    assert gate_i0(t.imag).passed
    bad = cocc.matrix.copy()
    bad[0, 0, 0, 1] += 1e-3j                                       # breaks Hermiticity of rho
    assert not gate_i0(trace_vector(replace(cocc, matrix=bad), lam).imag).passed

    # T3 (Section 11): C_uu at SAXIS = x, y equals Lambda_x, Lambda_y of the z dump.
    def genuine(a):
        return replace(cso, matrix=np.array([lam[a], 0 * lam[a], 0 * lam[a], -lam[a]]))
    assert gate_t3(z, genuine(0), "x").passed and gate_t3(z, genuine(1), "y").passed
    swapped = gate_t3(replace(z, matrix=z.matrix[[0, 2, 1, 3]]), genuine(1), "y")
    assert not swapped.passed and "stored du, ud" in swapped.detail


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


def test_parity_checks():
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
