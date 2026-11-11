"""Patch B dump files: the package's CSO and COCC readers, and acceptance/m1.py.

Fake dumps are written from the Fortran record layout of csodump.F.
"""

import importlib.util
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from dmi_pipeline.dumpio import load_cocc, load_cso
from tests.fixtures import make_clean_cso, write_cocc, write_cso, write_fake_dump

M1 = Path(__file__).resolve().parents[2] / "acceptance" / "m1.py"
_spec = importlib.util.spec_from_file_location("m1", M1)
m1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m1)


def test_cso_and_cocc_readers(tmp_path):
    paths = write_fake_dump(tmp_path, nk=2, nb=4, n_kgrp=1, n_bgrp=1, nelect=2)
    assert load_cocc(paths.cocc_path).matrix == pytest.approx(paths.cocc, abs=0)
    cso = make_clean_cso(2, 3)
    assert load_cso(write_cso(tmp_path / "CSO.dat", cso)).matrix == pytest.approx(cso, abs=0)
    with pytest.raises(ValueError, match="SAXIS"):            # dump_C is the z dump only
        load_cso(write_cso(tmp_path / "CSO_x.dat", cso, saxis=(1.0, 0.0, 0.0)))


def test_m1_script(tmp_path):
    """M1 passes on a smeared 2 x 2 rank grid and fails on corrupted COCC or a repeated record."""
    paths = write_fake_dump(tmp_path, nk=4, nb=8, nions=2, lmdim=3, n_kgrp=2, n_bgrp=2, nelect=4, seed=29)
    result = subprocess.run([sys.executable, str(M1), str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0 and "M1 pass" in result.stdout, result.stdout + result.stderr

    matrix = paths.cocc.copy()
    matrix[[1, 2]] = matrix[[2, 1]]                          # flip blocks in the wrong order
    write_cocc(paths.cocc_path, matrix, nelect=4.0)
    assert m1.m1(tmp_path)[0] > m1.TOL

    write_cocc(paths.cocc_path, paths.cocc, nelect=4.0)
    data = paths.cproj_paths[0].read_bytes()
    record = 3 * 4 + 4 * 8 + 2 * 2 * 3 * 16                  # (NK, BAND, ISP), W, EIG (complex), F, CPROJ
    paths.cproj_paths[0].write_bytes(data + data[-record:])
    with pytest.raises(ValueError, match="not once"):
        m1.m1(tmp_path)
    assert np.any(paths.occupations % 1)                       # the fixture is smeared
