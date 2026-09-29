from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import struct

import numpy as np
import pytest

from dmi_pipeline.dumpio import assert_header, load_cocc, load_cproj, load_cso, load_ferwe, read_cproj_file
from tests.fixtures import corrupt, make_clean_cso, write_cso, write_fake_dump


def test_fake_dump_round_trip_uses_recorded_global_indices(tmp_path: Path) -> None:
    expected = write_fake_dump(tmp_path, nk=4, nb=8, n_kgrp=2, n_bgrp=2, seed=11)
    loaded = load_cproj(tmp_path)

    assert loaded.c == pytest.approx(expected.cproj, abs=0.0)
    assert loaded.occupations == pytest.approx(expected.occupations, abs=0.0)
    assert loaded.weights[0] == pytest.approx(expected.weights, abs=0.0)


@pytest.mark.parametrize(("n_kgrp", "n_bgrp"), [(1, 1), (2, 2), (4, 1), (1, 4)])
def test_rank_grid_independence(n_kgrp: int, n_bgrp: int, tmp_path: Path) -> None:
    expected = write_fake_dump(tmp_path, nk=4, nb=8, n_kgrp=n_kgrp, n_bgrp=n_bgrp, seed=29)
    loaded = load_cproj(tmp_path)

    assert loaded.c == pytest.approx(expected.cproj, abs=0.0)
    for kpoint in range(4):
        for band in range(8):
            assert loaded.c[0, kpoint, 0, 0, 0, band] == expected.cproj[0, kpoint, 0, 0, 0, band]


def test_w0_names_missing_rank_file(tmp_path: Path) -> None:
    paths = write_fake_dump(tmp_path, nk=4, nb=8).cproj_paths
    corrupt(paths[-1], drop=True)
    with pytest.raises(ValueError, match="rank files"):
        load_cproj(tmp_path)


def test_w0_names_duplicate_record_index(tmp_path: Path) -> None:
    paths = write_fake_dump(tmp_path, nk=2, nb=2, n_kgrp=1, n_bgrp=1, nelect=2).cproj_paths
    data = paths[0].read_bytes()
    header = read_cproj_file(paths[0]).header
    record_size = 3 * 4 + 4 * 8 + header.npro * 16
    paths[0].write_bytes(data + data[-record_size:])
    with pytest.raises(ValueError, match=r"duplicate.*ISP=1.*NK=2.*BAND=2"):
        load_cproj(tmp_path)


def test_w0_rejects_dimension_mismatch_between_rank_files(tmp_path: Path) -> None:
    paths = write_fake_dump(tmp_path, nk=2, nb=2, n_kgrp=2, n_bgrp=1, nelect=2).cproj_paths
    data = bytearray(paths[1].read_bytes())
    data[96:100] = struct.pack("<i", 5)
    paths[1].write_bytes(data)
    with pytest.raises(ValueError, match="header 2 disagrees"):
        load_cproj(tmp_path)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"format_version": 2}, "format version"),
        ({"dump_point": "POST_LOOP"}, "dump tag"),
        ({"build_id": "wrong build"}, "build id"),
    ],
)
def test_static_header_failures(change: dict[str, object], message: str, tmp_path: Path) -> None:
    path = write_fake_dump(tmp_path, nk=2, nb=2, n_kgrp=1, n_bgrp=1, nelect=2).cproj_paths[0]
    corrupt(path, **change)
    with pytest.raises(ValueError, match=message):
        read_cproj_file(path)


def test_assert_header_checks_spin_spiral_q_and_axis(tmp_path: Path) -> None:
    header = load_cproj(write_fake_dump(tmp_path, nk=2, nb=2, n_kgrp=1, n_bgrp=1, nelect=2).directory).header
    with pytest.raises(ValueError, match="LSORBIT"):
        assert_header(replace(header, lsorbit=True), expect_lsorbit=False)
    with pytest.raises(ValueError, match="QSPIRAL"):
        assert_header(header, q_frac=(0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="SAXIS"):
        assert_header(replace(header, saxis=(1.0, 0.0, 0.0)))

    cso_path = write_cso(tmp_path / "CSO.dat", make_clean_cso(2, 3))
    assert load_cso(cso_path).metadata.lsorbit is True
    text = cso_path.read_text(encoding="utf-8").replace("LSORBIT= T", "LSORBIT= F")
    cso_path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="LSORBIT"):
        load_cso(cso_path)


def test_load_ferwe_clean_and_targeted_failures(tmp_path: Path) -> None:
    paths = write_fake_dump(tmp_path, nk=2, nb=4, n_kgrp=1, n_bgrp=1, nelect=4)
    assert load_ferwe(paths.ferwe_path).occupations.shape == (1, 2, 4)

    clean = paths.ferwe_path.read_text(encoding="utf-8")
    paths.ferwe_path.write_text(clean.replace("1.0000000000000000E+00", "5.0000000000000000E-01", 1), encoding="utf-8")
    with pytest.raises(ValueError, match=r"fractional.*ISP=1.*NK=1.*BAND=1"):
        load_ferwe(paths.ferwe_path)

    paths.ferwe_path.write_text(clean.replace("5.0000000000000000E-01", "4.0000000000000002E-01"), encoding="utf-8")
    with pytest.raises(ValueError, match=r"sum\(WTKPT\)"):
        load_ferwe(paths.ferwe_path)

    paths.ferwe_path.write_text(clean.replace("4.0000000000000000E+00", "5.0000000000000000E+00", 1), encoding="utf-8")
    with pytest.raises(ValueError, match="SUM_FW"):
        load_ferwe(paths.ferwe_path)


def test_load_cocc_parses_rows_and_treats_trace_check_as_diagnostic(tmp_path: Path) -> None:
    paths = write_fake_dump(tmp_path, nk=2, nb=4, n_kgrp=1, n_bgrp=1, nelect=4)
    text = paths.cocc_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    lines.insert(1, "# extra comment")
    paths.cocc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    loaded = load_cocc(paths.cocc_path)

    assert loaded.matrix == pytest.approx(paths.cocc)
    assert loaded.trace_total is not None
    assert loaded.trace_total != pytest.approx(4.0)


def test_complex_eigenvalue_terminal_lmbase_and_rank_local_offsets(tmp_path):
    paths = write_fake_dump(tmp_path, nk=2, nb=4, nions=2, lmdim=3,
                            n_kgrp=1, n_bgrp=2, nelect=2).cproj_paths
    first, second = [read_cproj_file(path) for path in paths]
    assert first.header.nb_low == 1 and second.header.nb_low == 2
    assert first.header.nb_par == second.header.nb_par == 2
    assert first.records[0].eigenvalue == 0.125j
    assert first.records[0].occupation == 1.0
    assert len(first.records[0].cproj) == 12
    # 88 fixed bytes + 56 integer metadata + 12 logical bytes + 64 reals
    # + NIONS LMMAX + (NIONS+1) LMBASE, followed by the first record.
    data = bytearray(paths[0].read_bytes())
    terminal_offset = 220 + 2 * 4 + 2 * 4
    data[terminal_offset:terminal_offset + 4] = struct.pack("<i", 999)
    paths[0].write_bytes(data)
    with pytest.raises(ValueError):
        read_cproj_file(paths[0])


def test_genuine_non_z_cso_requires_explicit_expected_axis(tmp_path):
    path = write_cso(tmp_path / "CSO.dat", make_clean_cso(1, 3))
    text = path.read_text().splitlines()
    text = ["# SAXIS 1 0 0" if line.startswith("# SAXIS") else line for line in text]
    path.write_text("\n".join(text) + "\n")
    with pytest.raises(ValueError, match="SAXIS"):
        load_cso(path)
    assert load_cso(path, expect_saxis=(1, 0, 0)).metadata.saxis == (1, 0, 0)


@pytest.mark.parametrize("delta", [-1, 1])
def test_truncated_record_or_trailing_byte_rejected(tmp_path, delta):
    path = write_fake_dump(tmp_path, nk=2, nb=4, n_kgrp=1, n_bgrp=1).cproj_paths[0]
    data = path.read_bytes()
    path.write_bytes(data[:-1] if delta < 0 else data + b"x")
    with pytest.raises(ValueError):
        read_cproj_file(path)
