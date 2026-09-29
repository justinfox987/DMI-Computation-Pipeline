"""Register existing N0 runs, validate completion, and persist acceptance evidence.

No VASP jobs are launched here. This bootstrap is deliberately separate from
the later campaign planner and materializer.
"""

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
from time import perf_counter

import numpy as np

from . import manifest
from .cso import validate_rotation
from .dumpio import assert_header, load_cocc, load_cproj, load_cso, load_ferwe
from .gates import gate_c0, gate_i0, gate_m1, gate_n0
from .realized import incar, logical, null_state, numbers, poscar_species
from .trace import compute_delta_E1, _trace_provenance

# Input-only registration still rejects unknown tags instead of treating the
# verbatim INCAR echo as evidence VASP recognized a typo.
INCAR_TAGS = set("""
SYSTEM ENCUT ENAUG PREC NCORE NPAR KPAR NBANDS NEDOS ISTART ICHARG ISMEAR SIGMA
IBRION POTIM ISIF NSW NELM NELMIN NELMDL ISYM SYMPREC LMAXMIX LMAXPAW ALGO IALGO
ISEARCH EDIFF EDIFFG LREAL LORBIT GGA AMIX BMIX AMIX_MAG BMIX_MAG AMIN IMIX
ISPIN GGA_COMPAT LASPH MAGMOM LDAU LDAUPRINT LDAUTYPE LDAUL LDAUU LDAUJ
LNONCOLLINEAR LSORBIT LSPIRAL QSPIRAL SAXIS LZEROZ RWIGS I_CONSTRAINED_M LAMBDA
M_CONSTR LWAVE LCHARG LDUMPCOCC LDUMPCPROJ LDUMPCSO LPLANE LSCALAPACK NSIM
ADDGRID NELECT NWRITE LVTOT LVHAR LAECHG LELF LASPH LDAUTYPE
""".split())


def _echo_check(directory: Path) -> dict:
    tags = incar(directory / "INCAR")
    unknown = set(tags) - INCAR_TAGS
    if unknown:
        raise ValueError(f"Unreviewed INCAR tags: {sorted(unknown)}")
    text = (directory / "OUTCAR").read_text(encoding="utf-8", errors="replace")
    if "General timing and accounting" not in text:
        raise ValueError("OUTCAR has no completed-job timing footer")
    for key, expected in tags.items():
        # VASP's initial INCAR block retains every supplied value, including
        # vector tags and ALGO. Compare tokens, not substring matches.
        matches = re.findall(r"^\s*" + re.escape(key) + r"\s*=\s*(.*)$", text, re.M)
        def equal(actual):
            a, b = actual.split(), expected.split()
            if a[:len(b)] == b:
                return True
            try:
                x, y = numbers(" ".join(a[:len(b)])), numbers(expected)
                return x.shape == y.shape and np.allclose(x, y, atol=1e-12, rtol=1e-8)
            except ValueError:
                return " ".join(a[:len(b)]).strip(".").upper() == expected.strip(".").upper()
        if not any(equal(actual) for actual in matches):
            raise ValueError(f"OUTCAR does not echo the requested {key}={expected}")
    return {"passed": True, "checked_tags": sorted(tags)}


def initialize(root: str | Path, ref: str | Path, dump_c: str | Path, dump_p: str | Path) -> Path:
    """Record explicit MAGMOM targets from an existing q=0 reference run."""
    root = Path(root).resolve()
    path = root / "manifest.json"
    if path.exists():
        raise ValueError(f"Manifest already exists: {path}; reuse finish/trace/status")
    ref, dump_c, dump_p = (Path(p).resolve() for p in (ref, dump_c, dump_p))
    if len({ref, dump_c, dump_p}) != 3:
        raise ValueError("ref, dump_C, and dump_P must be distinct run directories")
    species = poscar_species(ref / "POSCAR")
    tags = incar(ref / "INCAR")
    moments = numbers(tags["MAGMOM"]).reshape(len(species), 3)
    magnitudes = np.linalg.norm(moments, axis=1)
    indices = np.flatnonzero(magnitudes > 1e-12)
    if not len(indices):
        raise ValueError("MAGMOM supplies no magnetic target")
    units = moments[indices] / magnitudes[indices, None]
    eps = np.sign(units @ units[0])
    if np.max(np.abs(units[:, 2])) > 1e-10 or not np.allclose(units, eps[:, None] * units[0], atol=1e-10):
        raise ValueError("N0 requires collinear in-plane MAGMOM targets")
    if np.any(numbers(tags.get("QSPIRAL", "0 0 0")) != 0):
        raise ValueError("N0 registration requires q=0")
    if logical(tags, "LSORBIT") or not logical(tags, "LNONCOLLINEAR"):
        raise ValueError("N0 reference must be SOC-free and noncollinear")
    cfg_dir = root / "configs" / "n0"
    config = {"id": "n0", "family": "F0", "q_frac": [0.0, 0.0, 0.0], "psi_target": 0.0,
              "species": species, "magnetic_indices": indices.tolist(),
              "moment_ref": magnitudes[indices].tolist(), "eps": eps.astype(int).tolist(),
              "dirs": {"stage2": str(ref), "dump_P": str(dump_p)}}
    manifest.save(config, cfg_dir / "config.json")
    value = {"schema_version": 2, "milestone": "N0", "meta": {"noise_model": None},
             "material": {"ref": str(ref), "dump_C": str(dump_c), "cso_dir": str(root / "cso")},
             "config_dir": str(cfg_dir), "configs": [config], "runs": {}, "gates": {},
             "acceptance": "PENDING"}
    manifest.save(value, path)
    return path


def _source_files(directory: Path) -> list[Path]:
    names = ("INCAR", "OUTCAR", "POSCAR", "KPOINTS", "POTCAR")
    return [directory / name for name in names]


def _same_restart(source: Path, target: Path, source_record: dict) -> dict:
    files = {}
    for name in ("WAVECAR", "CHGCAR", "POSCAR", "KPOINTS", "POTCAR"):
        path = target / name
        expected = source_record["files"][str((source / name).resolve())]
        actual = manifest.file_hash(path)
        if actual != expected:
            raise ValueError(f"{target}/{name} differs from the validated reference")
        files[str(path.resolve())] = actual
    return files


def finish(path: str | Path, kind: str) -> dict:
    """Validate one existing run; failures invalidate previous acceptance."""
    path = Path(path)
    campaign = manifest.load(path)
    config = campaign["configs"][0]
    directories = {"ref": campaign["material"]["ref"], "dump_C": campaign["material"]["dump_C"],
                   "dump_P": config["dirs"]["dump_P"]}
    if kind not in directories:
        raise ValueError("kind must be ref, dump_C, or dump_P")
    directory = Path(directories[kind])
    start = perf_counter()
    campaign["acceptance"] = "PENDING"
    campaign["gates"].pop("N0", None)
    record = {"kind": kind, "passed": False, "when": datetime.now(timezone.utc).isoformat(),
              "files": {}, "checks": {}}
    try:
        record["checks"]["incar_echo"] = _echo_check(directory)
        config_path = Path(campaign["config_dir"]) / "config.json"
        if manifest.load(config_path) != config:
            raise ValueError("Manifest configuration differs from config.json")
        tags = incar(directory / "INCAR")
        record["files"] = manifest.fingerprints(_source_files(directory))
        record["files"].update(manifest.fingerprints([config_path]))
        # OUTCAR's build banner is the available executable identity; the
        # binary dump's fixed text identifies the format, not a unique build.
        banner = (directory / "OUTCAR").read_text(encoding="utf-8", errors="replace").splitlines()[0].strip()
        record["build_banner"] = banner
        if kind == "ref":
            text = (directory / "OUTCAR").read_text(encoding="utf-8", errors="replace")
            converged = text.rfind("aborting loop because EDIFF is reached")
            iterations = [m.start() for m in re.finditer(r"Iteration\s+\d+\(\s*\d+\)", text)]
            if converged < 0 or (iterations and converged < iterations[-1]):
                raise ValueError("Final electronic loop did not reach EDIFF")
            record["checks"]["R0"] = null_state(directory, config)
            if not record["checks"]["R0"]["passed"]:
                raise ValueError("R0 failed: reference is not the requested planar collinear state")
            record["files"].update(manifest.fingerprints([directory / "WAVECAR", directory / "CHGCAR"]))
        else:
            source = Path(directories["ref"])
            source_record = manifest.require_done(source, "ref")
            record["reference_build_banner"] = source_record["build_banner"]
            record["same_build_as_reference"] = banner == source_record["build_banner"]
            if int(tags.get("ISTART", "0")) != 1 or int(tags.get("ICHARG", "0")) != 11:
                raise ValueError("Dump needs ISTART=1, ICHARG=11")
            if kind == "dump_C":
                # CSO depends on the potential, not the final SOC eigenstates.
                # A historical dump may overwrite WAVECAR. Never compare that
                # output to the SOC-free reference as a C0 pass condition.
                record["potential_source"] = {"declared_reference": str(source),
                                               "input_hash_verified": False}
                cso = load_cso(directory / "CSO.dat")
                result = gate_c0(cso).to_dict()
                record["checks"]["C0"] = result
                if not result["passed"]:
                    raise ValueError("C0 failed")
                if cso.metadata.nions != len(config["species"]):
                    raise ValueError("CSO ion count disagrees with POSCAR")
                record["files"].update(manifest.fingerprints([directory / "CSO.dat"]))
                destination = Path(campaign["material"]["cso_dir"])
                destination.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(directory / "CSO.dat", destination / "CSO_z.dat")
                record["files"].update(manifest.fingerprints([destination / "CSO_z.dat"]))
                campaign["material"]["cso_provenance"] = record
                campaign["gates"]["C0"] = result
            else:
                record["files"].update(_same_restart(source, directory, source_record))
                if logical(tags, "LWAVE", True) or logical(tags, "LCHARG", True):
                    raise ValueError("dump_P must preserve input files: LWAVE=F and LCHARG=F")
                cp, occ, co = load_cproj(directory), load_ferwe(directory), load_cocc(directory / "COCC.dat")
                assert_header(cp.header, expect_lsorbit=False, q_frac=(0, 0, 0))
                result = gate_m1(cp, occ, co).to_dict()
                record["checks"].update({"W0": {"passed": True}, "M1": result})
                if not result["passed"]:
                    raise ValueError("M1 failed")
                if cp.header.nions != len(config["species"]):
                    raise ValueError("CPROJ ion count disagrees with POSCAR")
                record["format_build_id"] = cp.header.build_id
                record["header"] = asdict(cp.header)
                record["files"].update({str(f.path.resolve()): f.sha256 for f in cp.files})
                record["files"].update(manifest.fingerprints([directory / "FERWE.dat", directory / "COCC.dat"]))
                campaign["gates"].update({"W0": {"passed": True}, "M1": result})
        record["passed"] = True
    except (ValueError, OSError, KeyError) as error:
        record["error"] = str(error)
    record["wall_seconds"] = perf_counter() - start
    campaign["runs"][kind] = record
    marker, obsolete = ("DONE", "FAILED") if record["passed"] else ("FAILED", "DONE")
    manifest.save(record, directory / marker)
    (directory / obsolete).unlink(missing_ok=True)
    manifest.save(campaign, path)
    if kind == "dump_C" and record["passed"]:
        manifest.save(record, Path(campaign["material"]["cso_dir"]) / "provenance.json")
    return record


def trace_null(path: str | Path) -> dict:
    path = Path(path)
    campaign = manifest.load(path)
    campaign["acceptance"] = "PENDING"
    campaign["gates"].pop("N0", None)
    manifest.save(campaign, path)
    config = campaign["configs"][0]
    if manifest.load(Path(campaign["config_dir"]) / "config.json") != config:
        raise ValueError("Manifest configuration differs from config.json")
    ref = manifest.require_done(campaign["material"]["ref"], "ref")
    material = manifest.require_done(campaign["material"]["dump_C"], "dump_C")
    state = manifest.require_done(config["dirs"]["dump_P"], "dump_P")
    if not ref["checks"]["R0"]["passed"] or not material["checks"]["C0"]["passed"] or not state["checks"]["M1"]["passed"]:
        raise ValueError("N0 prerequisites R0/C0/M1 are not passing")
    directory = Path(config["dirs"]["dump_P"])
    cp, occ = load_cproj(directory), load_ferwe(directory)
    assert_header(cp.header, expect_lsorbit=False, q_frac=(0, 0, 0))
    cso = load_cso(Path(campaign["material"]["cso_dir"]) / "CSO_z.dat")
    trace = compute_delta_E1(cp, occ, cso)
    i0 = gate_i0(trace).to_dict()
    n0 = gate_n0(trace, config["species"]).to_dict()
    result = {"axis": "z", "delta_E1_eV": trace.delta_E1, "imag_total_eV": trace.imag_total,
              "per_ion_eV": {str(i + 1): value for i, value in trace.per_ion.items()},
              "imag_per_ion_eV": {str(i + 1): value for i, value in trace.imag_per_ion.items()},
              "per_k_eV": [[float(z.real), float(z.imag)] for z in trace.per_k],
              "species": config["species"], "gates": {"I0": i0, "N0": n0},
              "provenance": _trace_provenance(cp, occ, cso, "z", (0, 0, 0))}
    campaign["gates"].update(result["gates"])
    campaign["acceptance"] = "PASS" if i0["passed"] and n0["passed"] else "FAIL"
    manifest.save(result, Path(campaign["config_dir"]) / "trace.json")
    manifest.save(campaign, path)
    return result


def t3(path: str | Path, x_path: str | Path, y_path: str | Path) -> dict:
    """Validate genuine x/y dumps against the single production z operator."""
    campaign = manifest.load(path)
    if campaign.get("acceptance") != "PASS":
        raise ValueError("T3 requires N0 acceptance first")
    source = manifest.require_done(campaign["material"]["dump_C"], "dump_C")
    cso_dir = Path(campaign["material"]["cso_dir"])
    # Withdraw the old pin before attempting new validation.
    manifest.save({"name": "T3", "passed": False}, cso_dir / "rotation.json")
    campaign["gates"].pop("T3", None)
    manifest.save(campaign, path)
    x_path, y_path = Path(x_path), Path(y_path)
    for operator in (x_path, y_path):
        banner = (operator.parent / "OUTCAR").read_text(encoding="utf-8", errors="replace").splitlines()[0].strip()
        if banner != source["build_banner"]:
            raise ValueError("T3 genuine dumps must use the same CSO build as the z dump")
    result = validate_rotation(load_cso(cso_dir / "CSO_z.dat"),
                               load_cso(x_path, expect_saxis=(1, 0, 0)),
                               load_cso(y_path, expect_saxis=(0, 1, 0)))
    result["build_banner"] = source["build_banner"]
    result["files"].update(manifest.fingerprints([x_path.parent / "OUTCAR", y_path.parent / "OUTCAR"]))
    manifest.save(result, cso_dir / "rotation.json")
    campaign["gates"]["T3"] = result
    manifest.save(campaign, path)
    return result
