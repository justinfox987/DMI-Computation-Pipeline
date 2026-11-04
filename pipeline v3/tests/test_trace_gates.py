from dataclasses import replace

import numpy as np
import pytest

from dmi_pipeline.dumpio import load_cocc, load_cproj, load_cso, load_ferwe
from dmi_pipeline.gates import gate_c0, gate_i0, gate_m1, gate_n0
from dmi_pipeline.trace import compute_delta_E1, compute_delta_E1_reference
from tests.fixtures import make_clean_cso, write_cso, write_fake_dump


def inputs(tmp_path, *, collinear=False):
    files = write_fake_dump(tmp_path, nk=2, nb=4, nions=2, lmdim=3,
                            n_kgrp=1, n_bgrp=1, nelect=2, collinear=collinear)
    cso = load_cso(write_cso(tmp_path / "CSO.dat", make_clean_cso(2, 3), nelect=2))
    return load_cproj(tmp_path), load_ferwe(tmp_path), cso, files


def test_vectorized_trace_matches_copied_loop_and_density_oracle(tmp_path):
    cp, occ, cso, _ = inputs(tmp_path)
    result = compute_delta_E1(cp, occ, cso)
    loop = compute_delta_E1_reference(cp, occ, cso)
    # Independent density-matrix route: rho = |c><c|, followed by Tr(C rho).
    oracle = np.zeros((2, 2), complex)
    for ion in range(2):
        for k in range(2):
            for spin, block in ((0, 0), (1, 3)):
                states = cp.c[0, k, ion, spin]
                rho = (states * occ.occupations[0, k]) @ states.conj().T
                oracle[ion, k] += occ.weights[k] * np.trace(cso.matrix[block, ion] @ rho)
    assert result.delta_E1 == pytest.approx(oracle.sum().real, abs=1e-12)
    assert result.delta_E1 == pytest.approx(loop.delta_E1, abs=1e-12)
    assert result.per_ion == pytest.approx(dict(enumerate(oracle.sum(axis=1).real)), abs=1e-12)
    assert result.per_k == pytest.approx(oracle.sum(axis=0), abs=1e-12)
    assert gate_i0(result).passed


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
    cp, occ, cso, _ = inputs(tmp_path, collinear=True)
    t = compute_delta_E1(cp, occ, cso)
    assert gate_n0(t, ["Fe", "Bi"]).passed
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
