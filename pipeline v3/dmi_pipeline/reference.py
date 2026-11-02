"""Independent q0 sphere reference for the Step 1 Fe pilot; no VASP execution."""

from datetime import datetime, timezone
from pathlib import Path
import re
import socket

import numpy as np

from . import manifest, step1
from .realized import incar, logical, numbers, poscar_species
from .workflow import INCAR_TAGS

SCHEMA = "dmi-reference-provenance-1"
SOURCE_FILES = ("INCAR", "OUTCAR", "OSZICAR", "POSCAR", "KPOINTS", "POTCAR")
MATERIAL_FILES = ("POSCAR", "KPOINTS", "POTCAR")
RELEVANT_TAGS = ("ENCUT", "ENINI", "NBANDS", "ISMEAR", "SIGMA", "EDIFF", "PREC",
                 "LASPH", "ALGO", "LMAXMIX", "GGA", "ISPIN", "NELECT")
# These vary by design between an independently converged q0 and a finite-q SCF.
ALLOWED_TAGS = frozenset({"QSPIRAL", "LAMBDA", "MAGMOM", "M_CONSTR", "LZEROZ",
                          "ISTART", "ICHARG", "LWAVE", "LCHARG", "LORBIT", "NCORE",
                          "KPAR", "NPAR", "NSIM", "LSCALAPACK", "LPLANE",
                          "LDUMPCOCC", "LDUMPCPROJ", "LDUMPCSO", "NWRITE", "LVTOT",
                          "LVHAR", "LAECHG", "LELF"})
LOGICAL_TAGS = frozenset({"LNONCOLLINEAR", "LSORBIT", "LSPIRAL", "LASPH",
                          "LREAL", "ADDGRID", "LDAU", "GGA_COMPAT"})
# All tags not listed here (including the shared SCF settings) are blocking.
BLOCKING_TAGS = frozenset(INCAR_TAGS - ALLOWED_TAGS)


def prepare_q0(recipe, poscar):
    """Prepare a separate, explicitly unconstrained planar F0 sphere run."""
    if recipe.get("family") != "F0":
        raise ValueError("q0 reference requires a planar F0 recipe")
    if recipe.get("side") not in (None, "+"):
        raise ValueError("q0 reference must use the positive F0 side")
    # No production prepare() flag: reciprocal-q exclusion remains in that path.
    reference_recipe = dict(recipe, id="reference-q0", family="F0", side="+",
                            q_frac=[0, 0, 0], **{"lambda": 0, "lzeroz": True})
    reference_recipe.pop("angle_deg", None)
    reference_recipe.pop("f1_policy", None)
    species, _ = step1.positions(poscar)
    record = step1._prepare_record(reference_recipe, poscar, step1.vector([0, 0, 0], "q0"), species)
    record["tags"]["QSPIRAL"] = "0 0 0"
    if record["tags"]["LSPIRAL"] != "T" or record["tags"]["LZEROZ"] != "T":
        raise ValueError("Planar q0 sphere reference requires LSPIRAL=T and LZEROZ=T")
    return record


def _indices(config, species):
    indices = config.get("magnetic_indices") if isinstance(config, dict) else None
    if (not isinstance(indices, list) or len(indices) != 2 or
            any(type(i) is not int or i < 0 or i >= len(species) for i in indices) or
            len(set(indices)) != 2):
        raise ValueError("Reference needs explicit two distinct magnetic_indices in POSCAR order")
    if "species" in config and config["species"] != species:
        raise ValueError("Reference config species/order differs from POSCAR")
    if "q_frac" in config and not np.array_equal(step1.vector(config["q_frac"], "reference config q_frac"), [0, 0, 0]):
        raise ValueError("Reference config must identify a q0 run, not a finite-q case")
    return indices


def _q0_tags(tags):
    for key in ("QSPIRAL", "LAMBDA", "I_CONSTRAINED_M", "RWIGS"):
        if key not in tags:
            raise ValueError(f"Reference INCAR needs explicit {key}")
    q = numbers(tags["QSPIRAL"])
    if q.shape != (3,) or np.any(q != 0):
        raise ValueError("Reference INCAR QSPIRAL must be exactly 0 0 0")
    lam = numbers(tags["LAMBDA"])
    if lam.shape != (1,) or lam[0] != 0:
        raise ValueError("Reference INCAR LAMBDA must be zero")
    mode = numbers(tags["I_CONSTRAINED_M"])
    if mode.shape != (1,) or mode[0] != 1:
        raise ValueError("Reference requires I_CONSTRAINED_M=1 sphere output")
    rwigs = numbers(tags["RWIGS"])
    if not len(rwigs) or np.any(rwigs <= 0):
        raise ValueError("Reference needs positive explicit RWIGS")
    return rwigs.tolist()


def extract(run_dir, config, output=None):
    """Verify a completed independent q0 run and optionally write both reference records.

    config is an explicit mapping or a path to config.json (or a minimal imported
    JSON mapping of magnetic_indices). No magnetic sites are inferred from moments.
    """
    run = Path(run_dir).resolve()
    config = manifest.load(config) if isinstance(config, (str, Path)) else config
    for name in SOURCE_FILES:
        if not (run / name).is_file() or not (run / name).stat().st_size:
            raise ValueError(f"Reference needs nonempty {name}: {run / name}")
    species = poscar_species(run / "POSCAR")
    indices = _indices(config, species)
    if "poscar_sha256" in config and config["poscar_sha256"] != manifest.file_hash(run / "POSCAR"):
        raise ValueError("Reference POSCAR differs from supplied config")
    tags = incar(run / "INCAR")
    unknown = set(tags) - INCAR_TAGS
    if unknown:
        raise ValueError(f"Unreviewed reference INCAR tags: {sorted(unknown)}")
    rwigs = _q0_tags(tags)
    if len(rwigs) != len(dict.fromkeys(species)):
        raise ValueError("Reference RWIGS must have one radius per POSCAR species")
    if "tags" in config:
        for key, value in config["tags"].items():
            if key not in tags:
                raise ValueError(f"Reference run INCAR missing requested {key}")
            if key in {"LNONCOLLINEAR", "LSORBIT", "LSPIRAL", "LZEROZ"}:
                equal = logical(tags, key) == logical(config["tags"], key)
            else:
                try:
                    a, b = numbers(tags[key]), numbers(value)
                    equal = a.shape == b.shape and len(a) > 0 and np.array_equal(a, b)
                except ValueError:
                    equal = tags[key].strip().upper() == value.strip().upper()
            if not equal:
                raise ValueError(f"Reference run INCAR {key} differs from supplied config")
    checked = step1.check_run(run, len(species))
    sphere = checked["sphere"]
    if sphere["lambda"] != 0:
        raise ValueError("Reference final OSZICAR lambda must be zero")
    outcar = (run / "OUTCAR").read_text(encoding="utf-8", errors="replace")
    for echoed in re.findall(r"^\s*QSPIRAL\s*=\s*(.*)$", outcar, re.M):
        q = numbers(echoed)
        if q.shape != (3,) or np.any(q != 0):
            raise ValueError("Reference OUTCAR QSPIRAL must be zero")
    paths = {name: str((run / name).resolve()) for name in SOURCE_FILES}
    hashes = {name: manifest.file_hash(path) for name, path in paths.items()}
    references = {"M_int": [sphere["M_norm"][ion] for ion in indices],
                  "MW_int": [sphere["MW_norm"][ion] for ion in indices]}
    if any(not np.isfinite(value) or value <= 0 for values in references.values() for value in values):
        raise ValueError("Reference magnetic sphere norms must be positive and finite")
    provenance = {"schema": SCHEMA, "source_paths": paths, "sha256": hashes,
                  "magnetic_indices": indices, "species": species, "rwigs": rwigs,
                  "input_tags": tags, "relevant_input_tags": {key: tags.get(key) for key in RELEVANT_TAGS},
                  "qspiral": [0.0, 0.0, 0.0], "lambda": 0.0, "i_constrained_m": 1,
                  "final_step": checked["outcar"]["final_step"], "oszicar_lines": sphere["lines"],
                  "segment": "single completed OUTCAR run; matched terminal ionic/electronic step",
                  "outcar_final_ediff": True, "incar_echo": True,
                  "build_banner": checked["outcar"]["build_banner"],
                  "extracted_at_utc": datetime.now(timezone.utc).isoformat(), "extraction_host": socket.gethostname()}
    if output is not None:
        output = Path(output)
        if (output / "references.json").exists() or (output / "reference-provenance.json").exists():
            raise ValueError("Reference output exists; do not overwrite verification evidence")
        manifest.save(references, output / "references.json")
        provenance["references_sha256"] = manifest.file_hash(output / "references.json")
        manifest.save(provenance, output / "reference-provenance.json")
    return references, provenance


def verify_files(references_path):
    """Validate a previously extracted pair and rehash its original run files."""
    path = Path(references_path)
    if path.name != "references.json":
        raise ValueError("Imported reference must be named references.json")
    provenance_path = path.with_name("reference-provenance.json")
    if not provenance_path.is_file():
        raise ValueError("Reference requires adjacent reference-provenance.json; bare references.json cannot be accepted")
    refs, provenance = manifest.load(path), manifest.load(provenance_path)
    if set(refs) != {"M_int", "MW_int"} or provenance.get("schema") != SCHEMA:
        raise ValueError("Invalid reference or provenance schema")
    indices = provenance.get("magnetic_indices")
    if (not isinstance(indices, list) or len(indices) != 2 or
            any(type(i) is not int or i < 0 for i in indices) or len(set(indices)) != 2 or
            any(not isinstance(refs[key], list) or len(refs[key]) != len(indices) or
                any(type(x) not in (int, float) or not np.isfinite(x) or x <= 0 for x in refs[key])
                for key in refs)):
        raise ValueError("Invalid magnetic-site reference norms")
    paths, hashes = provenance.get("source_paths"), provenance.get("sha256")
    if (not isinstance(paths, dict) or not isinstance(hashes, dict) or
            set(paths) != set(SOURCE_FILES) or set(hashes) != set(SOURCE_FILES) or
            any(not isinstance(paths[name], str) or not isinstance(hashes[name], str)
                for name in SOURCE_FILES) or
            manifest.file_hash(path) != provenance.get("references_sha256")):
        raise ValueError("Reference file hashes or source paths are missing or changed")
    directories = {Path(paths[name]).resolve().parent for name in SOURCE_FILES}
    if len(directories) != 1 or any(Path(paths[name]).name != name for name in SOURCE_FILES):
        raise ValueError("Reference source paths must describe one completed run directory")
    manifest.check_files({paths[name]: hashes[name] for name in SOURCE_FILES})
    # A copied JSON pair must still describe this q0 run, not a finite-q run or an edited tag set.
    actual, fresh = extract(Path(paths["INCAR"]).parent, {"magnetic_indices": indices})
    if (actual != refs or any(fresh[key] != provenance.get(key) for key in
                              ("sha256", "source_paths", "input_tags", "relevant_input_tags",
                               "final_step", "oszicar_lines", "magnetic_indices", "species", "rwigs",
                               "build_banner", "segment", "outcar_final_ediff", "incar_echo",
                               "qspiral", "lambda", "i_constrained_m"))):
        raise ValueError("Reference records differ from rechecked q0 source files")
    return refs, provenance


def compatible(provenance, case_config, case_run_dir_or_inputs):
    """Return all blocking physical-input differences; never supply implicit defaults."""
    case_dir = Path(case_run_dir_or_inputs)
    ref_tags = provenance.get("input_tags")
    if provenance.get("schema") != SCHEMA or not isinstance(ref_tags, dict):
        raise ValueError("Reference provenance schema or input tags missing")
    tags = incar(case_dir / "INCAR")
    if set(tags) - INCAR_TAGS:
        raise ValueError(f"Unreviewed case INCAR tags: {sorted(set(tags) - INCAR_TAGS)}")
    # A material directory has inherited tags, whereas a prepared run already has merged tags.
    if not (case_dir / "config.json").is_file():
        tags.update(case_config["tags"])
    differences = []
    if provenance.get("magnetic_indices") != case_config.get("magnetic_indices"):
        differences.append("magnetic-site order differs")
    species = poscar_species(case_dir / "POSCAR")
    if provenance.get("species") != species or case_config.get("species") != species:
        differences.append("POSCAR species order differs")
    hashes = provenance.get("sha256", {})
    if (case_dir / "config.json").is_file():
        if manifest.file_hash(case_dir / "POSCAR") != case_config.get("poscar_sha256"):
            differences.append("case POSCAR differs from its prepared config")
        for key, value in case_config.get("tags", {}).items():
            if key not in tags:
                differences.append(f"case INCAR missing prepared {key}")
                continue
            try:
                a, b = numbers(value), numbers(tags[key])
                equal = a.shape == b.shape and len(a) > 0 and np.array_equal(a, b)
            except ValueError:
                equal = (logical(case_config["tags"], key) == logical(tags, key) if key in LOGICAL_TAGS | {"LZEROZ"}
                         else value.strip().upper() == tags[key].strip().upper())
            if not equal:
                differences.append(f"case INCAR {key} differs from its prepared config")
    for name in MATERIAL_FILES:
        if hashes.get(name) != manifest.file_hash(case_dir / name):
            differences.append(f"{name} hash differs")
    for key in sorted(set(ref_tags) | set(tags) | {"I_CONSTRAINED_M", "RWIGS"}):
        if key in ALLOWED_TAGS:
            continue
        if key not in ref_tags or key not in tags:
            differences.append(f"{key} missing on {'reference' if key not in ref_tags else 'case'} INCAR")
            continue
        if key == "I_CONSTRAINED_M":
            try:
                a, b = numbers(ref_tags[key]), numbers(tags[key])
                if a.shape == b.shape == (1,) and a[0] == b[0] == 1:
                    continue
            except ValueError:
                pass
            differences.append("I_CONSTRAINED_M differs; both runs must use mode 1")
            continue
        if key == "RWIGS":
            try:
                a, b = numbers(ref_tags[key]), numbers(tags[key])
                if a.shape != b.shape or not np.array_equal(a, b):
                    differences.append("RWIGS differs")
            except ValueError:
                differences.append("RWIGS invalid")
            continue
        if key in LOGICAL_TAGS:
            if logical(ref_tags, key) != logical(tags, key):
                differences.append(f"{key} differs")
            continue
        try:
            a, b = numbers(ref_tags[key]), numbers(tags[key])
            equal = a.shape == b.shape and len(a) > 0 and np.array_equal(a, b)
        except ValueError:
            equal = ref_tags[key].strip().upper() == tags[key].strip().upper()
        if not equal:
            differences.append(f"{key} differs")
    return differences
