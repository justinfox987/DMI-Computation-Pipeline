"""Patch B dump readers, on fake dumps written from the Fortran record layout."""

import pytest

from dmi_pipeline.dumpio import load_cocc, load_cproj, load_cso, read_cproj_file
from tests.fixtures import make_clean_cso, write_cso, write_fake_dump


def test_assembly_does_not_depend_on_the_rank_grid(tmp_path):
    for n_kgrp, n_bgrp in ((1, 1), (2, 2), (4, 1), (1, 4)):
        directory = tmp_path / f"{n_kgrp}-{n_bgrp}"
        directory.mkdir()
        expected = write_fake_dump(directory, nk=4, nb=8, n_kgrp=n_kgrp, n_bgrp=n_bgrp, seed=29)
        loaded = load_cproj(directory)
        assert loaded.c == pytest.approx(expected.cproj, abs=0.0)
        assert loaded.weights[0] == pytest.approx(expected.weights, abs=0.0)


def test_duplicate_record_is_rejected(tmp_path):
    paths = write_fake_dump(tmp_path, nk=2, nb=2, n_kgrp=1, n_bgrp=1, nelect=2).cproj_paths
    data = paths[0].read_bytes()
    record_size = 3 * 4 + 4 * 8 + read_cproj_file(paths[0]).header.npro * 16
    paths[0].write_bytes(data + data[-record_size:])
    with pytest.raises(ValueError, match="duplicate"):
        load_cproj(tmp_path)


def test_cocc_reader_returns_the_written_matrix(tmp_path):
    paths = write_fake_dump(tmp_path, nk=2, nb=4, n_kgrp=1, n_bgrp=1, nelect=4)
    assert load_cocc(paths.cocc_path).matrix == pytest.approx(paths.cocc)


def test_non_z_cso_needs_its_expected_axis(tmp_path):
    path = write_cso(tmp_path / "CSO.dat", make_clean_cso(1, 3))
    lines = path.read_text().splitlines()
    path.write_text("\n".join("# SAXIS 1 0 0" if line.startswith("# SAXIS") else line for line in lines) + "\n")
    with pytest.raises(ValueError, match="SAXIS"):
        load_cso(path)
    assert load_cso(path, expect_saxis=(1, 0, 0)).metadata.saxis == (1, 0, 0)
