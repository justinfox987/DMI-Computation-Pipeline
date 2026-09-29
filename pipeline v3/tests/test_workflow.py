from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from dmi_pipeline import manifest
from dmi_pipeline.realized import null_state
from dmi_pipeline.workflow import finish, initialize, trace_null
from tests.fixtures import make_clean_cso, write_cso, write_fake_dump


def moments_text(moments):
    lines = []
    for axis, values in zip("xyz", np.asarray(moments).T):
        lines += [f"magnetization ({axis})", "", "# of ion s p d tot", "---------"]
        lines += [f"{i + 1} 0 0 0 {value:.9f}" for i, value in enumerate(values)]
        lines += ["---------", ""]
    return "\n".join(lines)


@pytest.fixture
def campaign(tmp_path):
    base = ("LNONCOLLINEAR=T\nLSORBIT=F\nLSPIRAL=F\nSAXIS=0 0 1\n"
            "MAGMOM=4 0 0 -4 0 0 0 0 0\nISYM=-1\n")
    ref, dc, dp = (tmp_path / name for name in ("ref", "dump_C", "dump_P"))
    for directory in (ref, dc, dp):
        directory.mkdir()
        (directory / "POSCAR").write_text("test\n1\n1 0 0\n0 1 0\n0 0 1\nFe Bi\n2 1\nDirect\n0 0 0\n.5 .5 .5\n.2 .2 .2\n")
        for name, data in (("KPOINTS", "gamma mesh"), ("POTCAR", "fake PAW"), ("WAVECAR", "restart orbitals"), ("CHGCAR", "restart density")):
            (directory / name).write_text(data)
        text = base + ("ISTART=0\nICHARG=2\n" if directory == ref else "ISTART=1\nICHARG=11\nLWAVE=F\nLCHARG=F\n")
        if directory == dc:
            text = text.replace("LSORBIT=F", "LSORBIT=T") + "LDUMPCSO=T\n"
        if directory == dp:
            text += "LDUMPCPROJ=T\nLDUMPCOCC=T\n"
        (directory / "INCAR").write_text(text)
        (directory / "OUTCAR").write_text("vasp.6.4.2 test build\nINCAR:\n" + text +
            "Iteration 1( 1)\naborting loop because EDIFF is reached\n" +
            moments_text([[4, 0, 0], [-4, 0, 0], [0, 0, 0]]) +
            "\nGeneral timing and accounting informations for this job:\n")
    write_fake_dump(dp, nk=2, nb=4, nions=3, lmdim=3, n_kgrp=1, n_bgrp=1,
                    nelect=2, q=(0, 0, 0), lspiral=False, collinear=True)
    write_cso(dc / "CSO.dat", make_clean_cso(3, 3), nelect=2)
    path = initialize(tmp_path / "acceptance", ref, dc, dp)
    return path, ref, dc, dp


def complete(path):
    for kind in ("ref", "dump_C", "dump_P"):
        record = finish(path, kind)
        assert record["passed"], record.get("error")
    return trace_null(path)


def test_n0_end_to_end_without_patched_conventions(campaign):
    path, ref, dc, dp = campaign
    result = complete(path)
    assert result["gates"]["N0"]["passed"]
    assert result["delta_E1_eV"] == pytest.approx(0, abs=1e-12)
    assert manifest.load(path)["acceptance"] == "PASS"
    assert "3" in result["gates"]["N0"]["value"]["Bi_eV"]
    # A separate interpreter must observe persisted state, not global booleans.
    proc = subprocess.run([sys.executable, "-B", "-m", "dmi_pipeline", "status", "--manifest", str(path)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert '"acceptance": "PASS"' in proc.stdout


def test_missing_prerequisite_and_changed_bytes_invalidate_acceptance(campaign):
    path, ref, dc, dp = campaign
    with pytest.raises(FileNotFoundError):
        trace_null(path)
    complete(path)
    with (dp / "COCC.dat").open("a") as handle:
        handle.write("# changed after M1\n")
    with pytest.raises(ValueError, match="changed since validation"):
        trace_null(path)
    assert manifest.load(path)["acceptance"] == "PENDING"
    assert "N0" not in manifest.load(path)["gates"]


def test_failure_cannot_leave_a_stale_done_marker(campaign):
    path, ref, dc, dp = campaign
    complete(path)
    outcar = ref / "OUTCAR"
    clean = outcar.read_text()
    outcar.write_text(clean.replace("aborting loop because EDIFF is reached", "NELM exhausted"))
    result = finish(path, "ref")
    assert not result["passed"]
    assert not (ref / "DONE").exists()
    assert (ref / "FAILED").is_file()
    outcar.write_text(clean)
    assert finish(path, "ref")["passed"]
    assert not (ref / "FAILED").exists()


def test_global_gauge_is_free_but_nonplanar_reference_fails(campaign):
    path, ref, dc, dp = campaign
    config = manifest.load(path)["configs"][0]
    phase = np.deg2rad(51)
    m = np.array([[4 * np.cos(phase), 4 * np.sin(phase), 0],
                  [-4 * np.cos(phase), -4 * np.sin(phase), 0], [0, 0, 0]])
    original = (ref / "OUTCAR").read_text()
    (ref / "OUTCAR").write_text(original + moments_text(m))
    assert null_state(ref, config)["passed"]
    m[0, 2] = 1
    (ref / "OUTCAR").write_text(original + moments_text(m))
    assert not null_state(ref, config)["passed"]


def test_restart_identity_is_required_for_dump_p(campaign):
    path, ref, dc, dp = campaign
    assert finish(path, "ref")["passed"]
    (dp / "WAVECAR").write_text("different eigenstates")
    result = finish(path, "dump_P")
    assert not result["passed"] and "WAVECAR differs" in result["error"]


def test_added_rank_file_and_edited_configuration_are_not_silent(campaign):
    path, ref, dc, dp = campaign
    complete(path)
    (dp / "CPROJ.extra.bin").write_bytes(b"rogue rank")
    with pytest.raises(ValueError, match="rank-file set changed"):
        trace_null(path)
    value = manifest.load(path)
    value["configs"][0]["species"][2] = "Fe"
    manifest.save(value, path)
    with pytest.raises(ValueError, match="configuration differs"):
        trace_null(path)
