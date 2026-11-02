"""Lab-vector Step 1 input, sphere readback and canonical-bond rows.

No job submission or BFO symmetry generation occurs here. N0 keeps its historical
OUTCAR diagnostic path; Step 1 records never inherit its frame convention.
"""

from pathlib import Path
import re

import numpy as np

from . import manifest
from .realized import incar, logical, numbers, poscar_species
from .workflow import INCAR_TAGS, _echo_check

CONVENTION = "lab-oszicar-sphere-v1"
DIRECTION_DEG = 1.0
MOMENT_DRIFT = 0.05
RESOLUTION = 1e-8
PENALTY_EV = 1e-3
FLOAT = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[EeDd][+-]?\d+)?"
PENALTY = re.compile(r"\bE_p\s*=\s*(" + FLOAT + r")\s+lambda\s*=\s*(" + FLOAT + r")", re.I)
ELECTRONIC = re.compile(r"^\s*(?:DAV|RMM|CG|DMP|SDA|CGA):\s*(\d+)\b", re.I)
SUMMARY = re.compile(r"^\s*(\d+)\s+F=")
ITERATION = re.compile(r"Iteration\s+(\d+)\(\s*(\d+)\)")
BANNER = re.compile(r"^[ \t]*vasp\.\S+", re.I | re.M)


def printed_step(token):
    """Unit of the last printed decimal place, including Fortran exponents."""
    mantissa, *exponent = re.split(r"[EeDd]", token)
    decimals = len(mantissa.split(".")[1]) if "." in mantissa else 0
    return 10.0 ** (int(exponent[0]) - decimals if exponent else -decimals)


def vector(value, name):
    result = np.asarray(value, dtype=float)
    if result.shape != (3,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite three-vector")
    return result


def rotate_z(value, angle):
    x, y, z = value
    return np.array((x * np.cos(angle) - y * np.sin(angle),
                     x * np.sin(angle) + y * np.cos(angle), z))


def positions(path):
    """VASP 5/6 direct positions, with no Cartesian-coordinate ambiguity."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if len(lines) < 8:
        raise ValueError("Incomplete POSCAR")
    species = poscar_species(path)
    start = 7
    if lines[start].strip().lower().startswith("s"):
        start += 1
    if start >= len(lines) or lines[start].strip().lower() != "direct":
        raise ValueError("Step 1 requires POSCAR Direct positions")
    result = []
    for line in lines[start + 1:start + 1 + len(species)]:
        result.append(vector(line.split()[:3], "POSCAR position"))
    if len(result) != len(species):
        raise ValueError("POSCAR position count mismatch")
    return species, np.asarray(result)


def targets(poscar, magnetic_indices, signs, q_frac, family, angle_deg=None):
    """Return physical target vectors for the explicitly mapped two-site reference."""
    species, tau = positions(poscar)
    q = vector(q_frac, "q_frac")
    if family not in {"F0", "F1", "F2a", "F2b"}:
        raise ValueError("family must be F0, F1, F2a or F2b")
    if (len(magnetic_indices) != 2 or any(type(i) is not int or i < 0 or i >= len(species) for i in magnetic_indices)
            or len(set(magnetic_indices)) != 2):
        raise ValueError("Two distinct zero-based magnetic ion indices required")
    if (len(signs) != 2 or any(type(sign) is not int or sign not in (-1, 1) for sign in signs)):
        raise ValueError("Explicit reference signs must each be +1 or -1")
    if (family == "F0" and angle_deg is not None) or (family != "F0" and angle_deg is None):
        raise ValueError("F1/F2 need an angle_deg; F0 has no angle")
    angle = 0.0 if angle_deg is None else float(angle_deg)
    if not np.isfinite(angle):
        raise ValueError("Non-finite recipe angle")
    s, c = np.sin(np.deg2rad(angle)), np.cos(np.deg2rad(angle))
    base = {"F0": ((1, 0, 0), (1, 0, 0)),
            "F1": ((1, 0, 0), (c, s, 0)),
            "F2a": ((s, 0, c), (0, 0, 1)),
            "F2b": ((0, 0, 1), (s, 0, c))}[family]
    out = np.zeros((len(species), 3))
    for site, ion in enumerate(magnetic_indices):
        out[ion] = rotate_z(np.asarray(base[site]) * signs[site], 2 * np.pi * np.dot(q, tau[ion]))
    return out


def partner(q, target):
    q = vector(q, "q_frac")
    reflected = np.asarray(target, dtype=float).copy()
    if reflected.ndim != 2 or reflected.shape[1] != 3 or not np.all(np.isfinite(reflected)):
        raise ValueError("Invalid partner targets")
    reflected[:, 1] *= -1
    return -q, reflected


def prepare(recipe, poscar):
    """Make a versioned input record; caller must supply radii and F1 policy."""
    if "partner_q_frac" in recipe:
        raise ValueError("Prepare cannot regenerate a wrapped partner; use step1-wrap-partner on a prepared negative record")
    species, _ = positions(poscar)
    q = vector(recipe["q_frac"], "q_frac")
    if np.allclose(q, np.rint(q), atol=1e-12):
        raise ValueError("Generic-q model excludes reciprocal-lattice q")
    return _prepare_record(recipe, poscar, q, species)


def _prepare_record(recipe, poscar, q, species):
    """Shared target/tag construction after the production q check or explicit q0 selection."""
    indices = recipe["magnetic_indices"]
    rwigs = np.asarray(recipe["rwigs"], dtype=float)
    if rwigs.shape != (len(dict.fromkeys(species)),) or not np.all(np.isfinite(rwigs)) or np.any(rwigs <= 0):
        raise ValueError("Supply one positive RWIGS radius per POSCAR species")
    seeds = np.asarray(recipe["seed_magnitudes"], dtype=float)
    if seeds.shape != (len(indices),) or not np.all(np.isfinite(seeds)) or np.any(seeds <= 0):
        raise ValueError("Supply a positive seed magnitude per magnetic ion")
    lam = float(recipe["lambda"])
    if not np.isfinite(lam) or lam < 0:
        raise ValueError("LAMBDA must be finite and nonnegative")
    family = recipe["family"]
    if recipe["axis"] not in ("x", "y", "z"):
        raise ValueError("Measurement axis must be x, y or z; SCF tags stay fixed")
    lzeroz = recipe["lzeroz"]
    if type(lzeroz) is not bool or (family.startswith("F2") and lzeroz) or (family == "F0" and not lzeroz):
        raise ValueError("Explicit LZEROZ boolean required; F0 requires T and F2 requires F")
    if family == "F1" and recipe.get("f1_policy") != "diagnostic":
        raise ValueError("F1 LZEROZ is unvalidated: label an explicit diagnostic candidate")
    nonmag_seed = float(recipe.get("nonmag_seed", 0))
    if not np.isfinite(nonmag_seed) or nonmag_seed != 0:
        raise ValueError("Step 1 nonmagnetic seed policy is zero")
    u = targets(poscar, indices, recipe["signs"], q, family, recipe.get("angle_deg"))
    mag = np.zeros_like(u)
    for site, ion in enumerate(indices):
        mag[ion] = u[ion] * seeds[site]
    side = recipe.get("side", "+")
    if side not in ("+", "-"):
        raise ValueError("side must be + or -")
    if side == "-":
        q, u = partner(q, u)
        _, mag = partner(q, mag)
    tags = {"LNONCOLLINEAR": "T", "LSORBIT": "F", "LSPIRAL": "T",
            "SAXIS": "0 0 1", "I_CONSTRAINED_M": "1", "LAMBDA": str(lam),
            "LZEROZ": "T" if lzeroz else "F", "QSPIRAL": " ".join(map(str, q)),
            "RWIGS": " ".join(map(str, rwigs)),
            "MAGMOM": " ".join(f"{x:.12g}" for x in mag.flat),
            "M_CONSTR": " ".join(f"{x:.12g}" for x in u.flat)}
    return {"schema_version": 3, "convention": CONVENTION, "id": recipe["id"],
            "family": family, "side": side, "q_frac": q.tolist(), "axis": recipe["axis"],
            "magnetic_indices": list(indices), "signs": list(recipe["signs"]),
            "species": species, "poscar_sha256": manifest.file_hash(poscar),
            "targets": u.tolist(), "seed_magnitudes": seeds.tolist(),
            "recipe": {"angle_deg": (-float(recipe["angle_deg"]) if family == "F1" and side == "-" else recipe.get("angle_deg")),
                       "f1_policy": recipe.get("f1_policy")},
            "tags": tags}


def wrap_partner(record, q_frac):
    """Represent an existing reflected partner at q plus an integer reciprocal shift."""
    require_vector(record)
    if record["side"] != "-":
        raise ValueError("Only a prepared negative partner can be wrapped")
    q = vector(q_frac, "partner q_frac")
    delta = q - vector(record["q_frac"], "original q_frac")
    if not np.allclose(delta, np.rint(delta), atol=1e-10, rtol=0):
        raise ValueError("Partner q must differ by an integer reciprocal shift")
    if np.allclose(q, np.rint(q), atol=1e-12):
        raise ValueError("Generic-q model excludes reciprocal-lattice q")
    updated = dict(record, q_frac=q.tolist(), tags=dict(record["tags"]))
    updated["tags"]["QSPIRAL"] = " ".join(map(str, q))
    return updated


def write_inputs(record, directory, inputs=None, job_template=None):
    """Write generated tags, optionally assembling shared VASP material inputs."""
    require_vector(record)
    directory = Path(directory)
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("Input destination must be empty; do not overwrite a VASP run")
    files, tags = {}, None
    if inputs is not None:
        inputs = Path(inputs)
        tags = incar(inputs / "INCAR")
        if not tags:
            raise ValueError("Shared INCAR is empty")
        unknown = set(tags) - INCAR_TAGS
        if unknown:
            raise ValueError(f"Unreviewed INCAR tags: {sorted(unknown)}")
        tags.update(record["tags"])
        for name in ("POSCAR", "KPOINTS", "POTCAR"):
            files[name] = (inputs / name).read_bytes()
            if not files[name].strip():
                raise ValueError(f"Shared {name} is empty")
        if manifest.file_hash(inputs / "POSCAR") != record["poscar_sha256"]:
            raise ValueError("Shared POSCAR differs from the requested target")
    if job_template is not None:
        if inputs is None:
            raise ValueError("A job template requires shared material inputs")
        files["job.sh"] = Path(job_template).read_bytes()
        if not files["job.sh"].strip():
            raise ValueError("Job template is empty")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "INCAR.step1").write_text("".join(f"{k} = {v}\n" for k, v in record["tags"].items()), encoding="utf-8")
    manifest.save(record, directory / "config.json")
    if tags is not None:
        (directory / "INCAR").write_text("".join(f"{k} = {v}\n" for k, v in tags.items()), encoding="utf-8")
    for name, content in files.items():
        (directory / name).write_bytes(content)


def require_vector(record):
    if record.get("schema_version") != 3 or record.get("convention") != CONVENTION:
        raise ValueError("Step 1 requires schema 3 lab OSZICAR vectors; rebuild from original POSCAR/INCAR/OSZICAR, preserve legacy N0")


def sphere(path, nions):
    """Parse terminal OSZICAR ionic record; segment convergence is checked by check_run.

    Fail closed for incomplete or ambiguous restarts rather than taking the last
    earlier complete table. Convergence is checked independently in OUTCAR.
    """
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    headers = [i for i, line in enumerate(lines) if re.match(r"^\s*ion\s+MW_int\s+M_int\s*$", line, re.I)]
    if not headers:
        raise ValueError("OSZICAR has no sphere moment block")
    if any(re.match(r"^\s*ion\s+MW_int\b", line, re.I) and i not in headers for i, line in enumerate(lines)):
        raise ValueError("Malformed OSZICAR sphere header")
    start = headers[-1]
    mw, m, mw_step, seen = [], [], [], set()
    end = start + 1
    for i in range(start + 1, len(lines)):
        parts = lines[i].split()
        if not parts or not parts[0].isdigit() or (len(parts) > 1 and parts[1] == "F="):
            end = i
            break
        if len(parts) != 7:
            raise ValueError("Incomplete OSZICAR sphere row")
        ion = int(parts[0])
        if ion in seen or ion != len(seen) + 1:
            raise ValueError("Duplicate or out-of-order OSZICAR ion")
        seen.add(ion)
        try:
            values = np.array([float(x.replace("D", "E").replace("d", "e")) for x in parts[1:]])
        except ValueError as error:
            raise ValueError("Invalid OSZICAR sphere number") from error
        if not np.all(np.isfinite(values)):
            raise ValueError("Nonfinite OSZICAR sphere moment")
        mw.append(values[:3].tolist())
        mw_step.append([printed_step(x) for x in parts[1:4]])
        m.append(values[3:].tolist())
        end = i + 1
    if len(seen) != nions:
        raise ValueError("Terminal OSZICAR sphere block ion count mismatch")
    summary = [i for i in range(end, len(lines)) if SUMMARY.match(lines[i])]
    if not summary:
        raise ValueError("Terminal sphere block has no final F= record")
    f = summary[0]
    if any(line.strip() for line in lines[end:f]):
        raise ValueError("Unexpected data before OSZICAR final F= record")
    tail = lines[f + 1:]
    penalties = [(i + f + 1, PENALTY.search(line)) for i, line in enumerate(tail)]
    penalties = [(i, match) for i, match in penalties if match]
    if len(penalties) != 1 or any(re.search(r"\bE_p\s*=", line, re.I) and not PENALTY.search(line) for line in tail):
        raise ValueError("Terminal OSZICAR record needs one printed E_p and lambda")
    p, match = penalties[0]
    ep, lam = (float(x.replace("D", "E").replace("d", "e")) for x in match.groups())
    ep_step, lam_step = (printed_step(x) for x in match.groups())
    if not np.all(np.isfinite([ep, lam])) or lam < 0 or ep < 0:
        raise ValueError("Invalid OSZICAR penalty or lambda")
    field, field_step = None, None
    field_headers = [i for i in range(p + 1, len(lines)) if re.match(r"^\s*ion\s+lambda\*MW_perp\s*$", lines[i], re.I)]
    if len(field_headers) > 1:
        raise ValueError("Ambiguous terminal OSZICAR field blocks")
    if field_headers:
        field, field_step = [], []
        for ion in range(nions):
            row = lines[field_headers[0] + 1 + ion].split() if field_headers[0] + 1 + ion < len(lines) else []
            if len(row) != 4 or row[0] != str(ion + 1):
                raise ValueError("Incomplete/duplicate terminal OSZICAR field")
            field.append([float(x.replace("D", "E").replace("d", "e")) for x in row[1:]])
            field_step.append([printed_step(x) for x in row[1:]])
        if not np.all(np.isfinite(field)):
            raise ValueError("Nonfinite OSZICAR field")
    # A preceding complete ionic step is allowed; no later electronic work is.
    if len(summary) != 1 or any(SUMMARY.match(line) for line in lines[p + 1:]):
        raise ValueError("Ambiguous terminal OSZICAR record")
    if field_headers and any(line.strip() for line in lines[field_headers[0] + 1 + nions:]):
        raise ValueError("Trailing data after terminal OSZICAR field")
    if not field_headers and any(line.strip() for line in lines[p + 1:]):
        raise ValueError("Trailing data after terminal OSZICAR penalty")
    previous = [i for i, line in enumerate(lines[:start]) if SUMMARY.match(line)]
    # VASP may print several sphere tables per electronic iteration; require
    # complete tables and an indexed loop within each ionic step.
    boundary = -1
    for summary_line in previous + [f]:
        step_headers = [i for i in headers if boundary < i < summary_line]
        if not step_headers:
            raise ValueError("OSZICAR ionic steps missing sphere blocks or contain restarts")
        for header in step_headers:
            for ion in range(nions):
                row = lines[header + 1 + ion].split() if header + 1 + ion < summary_line else []
                if len(row) != 7 or row[0] != str(ion + 1):
                    raise ValueError("Incomplete OSZICAR ionic sphere block")
                try:
                    values = [float(x.replace("D", "E").replace("d", "e")) for x in row[1:]]
                except ValueError as error:
                    raise ValueError("Invalid OSZICAR sphere number") from error
                if not np.all(np.isfinite(values)):
                    raise ValueError("Nonfinite OSZICAR sphere moment")
            if header + 1 + nions < summary_line and re.match(r"^\s*\d+\s+", lines[header + 1 + nions]):
                raise ValueError("Duplicate or extra OSZICAR ionic sphere ion")
        electronic = [int(match.group(1)) for line in lines[boundary + 1:summary_line]
                      if (match := ELECTRONIC.match(line))]
        if not electronic or electronic != list(range(1, electronic[-1] + 1)):
            raise ValueError("OSZICAR electronic loop missing or ambiguous")
        boundary = summary_line
    steps = [int(SUMMARY.match(lines[i]).group(1)) for i in previous + [f]]
    if steps != list(range(1, steps[-1] + 1)):
        raise ValueError("OSZICAR ionic summaries contain a restart or missing step")
    return {"MW_int": mw, "M_int": m, "MW_norm": np.linalg.norm(mw, axis=1).tolist(),
            "M_norm": np.linalg.norm(m, axis=1).tolist(), "E_p_eV": ep, "lambda": lam,
            "printed_field": field, "precision": {"MW_int": mw_step, "E_p_eV": ep_step,
            "lambda": lam_step, "printed_field": field_step},
            "source": "OSZICAR", "ionic_step": steps[-1], "ionic_steps": steps,
            "electronic_step": electronic[-1],
            "lines": [start + 1, max(p + 1, (field_headers[0] + 1 + nions) if field_headers else p + 1)]}


def check_run(directory, nions) -> dict:
    """Check one converged OUTCAR segment against the terminal OSZICAR sphere."""
    directory = Path(directory)
    outcar = (directory / "OUTCAR").read_text(encoding="utf-8", errors="replace")
    # Count actual run banners, not compatibility prose mentioning vasp.4.x.
    if outcar.count("General timing and accounting") != 1 or len(BANNER.findall(outcar)) != 1:
        raise ValueError("Missing or ambiguous completed OUTCAR run segment")
    converged = outcar.rfind("aborting loop because EDIFF is reached")
    iterations = list(ITERATION.finditer(outcar))
    footer = outcar.rfind("General timing and accounting")
    if (not iterations or converged < iterations[-1].end() or converged > footer or
            ITERATION.search(outcar[footer:]) or BANNER.search(outcar[footer:])):
        raise ValueError("Final electronic loop did not reach EDIFF after its last iteration")
    # OUTCAR Iteration I(E) prints ionic I first and electronic E second.
    outcar_steps = [int(match.group(1)) for match in iterations if int(match.group(2)) == 1]
    if not outcar_steps or outcar_steps != list(range(1, outcar_steps[-1] + 1)):
        raise ValueError("OUTCAR ionic loop contains a restart or missing first iteration")
    for step in outcar_steps:
        count = [int(match.group(2)) for match in iterations if int(match.group(1)) == step]
        if count != list(range(1, count[-1] + 1)):
            raise ValueError("OUTCAR electronic loop contains a restart or missing iteration")
    _echo_check(directory)
    result = sphere(directory / "OSZICAR", nions)
    ionic, electronic = (int(x) for x in iterations[-1].groups())
    if (result["ionic_steps"] != outcar_steps or
            (result["ionic_step"], result["electronic_step"]) != (ionic, electronic)):
        raise ValueError("Final OSZICAR ionic/electronic step cannot be associated with final OUTCAR EDIFF loop")
    return {"sphere": result, "outcar": {"final_step": [ionic, electronic],
            "build_banner": outcar.splitlines()[0].strip(), "ionic_steps": outcar_steps}}


def read_state(directory, record, config_path):
    """Check matching run inputs and independent final electronic convergence."""
    require_vector(record)
    directory = Path(directory)
    config_path = Path(config_path)
    if manifest.load(config_path) != record:
        raise ValueError("Config file differs from requested record")
    stored_q = vector(record["q_frac"], "stored q_frac")
    requested_q = vector(numbers(record["tags"]["QSPIRAL"]), "Requested QSPIRAL")
    if not np.allclose(requested_q, stored_q, atol=1e-9, rtol=0):
        raise ValueError("Requested QSPIRAL differs from stored model q_frac")
    if not np.allclose(numbers(record["tags"]["M_CONSTR"]).reshape(-1, 3), record["targets"], atol=1e-9, rtol=0):
        raise ValueError("Requested M_CONSTR differs from stored targets")
    if manifest.file_hash(directory / "POSCAR") != record["poscar_sha256"]:
        raise ValueError("POSCAR differs from the requested target")
    tags = incar(directory / "INCAR")
    for key, value in record["tags"].items():
        if key not in tags:
            raise ValueError(f"Run INCAR missing requested {key}")
        if key == "QSPIRAL":
            actual_q = vector(numbers(tags[key]), "Run QSPIRAL")
            if not np.allclose(actual_q, requested_q, atol=1e-9, rtol=0):
                raise ValueError("Run INCAR QSPIRAL differs from requested input")
        elif key in {"MAGMOM", "M_CONSTR", "RWIGS", "LAMBDA", "SAXIS"}:
            if not np.allclose(numbers(tags[key]), numbers(value), atol=1e-9, rtol=0):
                raise ValueError(f"Run INCAR {key} differs from requested input")
        elif key in {"LNONCOLLINEAR", "LSORBIT", "LSPIRAL", "LZEROZ"}:
            if logical(tags, key) != logical(record["tags"], key):
                raise ValueError(f"Run INCAR {key} differs from requested input")
        elif tags[key].strip().upper() != value.upper():
            raise ValueError(f"Run INCAR {key} differs from requested input")
    if not np.allclose(actual_q, stored_q, atol=1e-9, rtol=0):
        raise ValueError("Run QSPIRAL differs from stored model q_frac")
    if poscar_species(directory / "POSCAR") != record["species"]:
        raise ValueError("Run species/order mismatch")
    if not np.allclose(numbers(tags["M_CONSTR"]).reshape(-1, 3), record["targets"], atol=1e-9, rtol=0):
        raise ValueError("Requested M_CONSTR differs from versioned target vectors")
    outcar = (directory / "OUTCAR").read_text(encoding="utf-8", errors="replace")
    for echoed in re.findall(r"^\s*QSPIRAL\s*=\s*(.*)$", outcar, re.M):
        echoed_q = vector(numbers(echoed), "OUTCAR QSPIRAL")
        if not np.allclose(echoed_q, stored_q, atol=1e-9, rtol=0):
            raise ValueError("OUTCAR QSPIRAL differs from stored model q_frac")
    checked = check_run(directory, len(record["species"]))
    result = checked["sphere"]
    if not np.isclose(result["lambda"], numbers(tags["LAMBDA"])[0], atol=1e-10, rtol=1e-6):
        raise ValueError("Printed final lambda differs from requested LAMBDA")
    result["provenance"] = {"files": manifest.fingerprints(
        [config_path] + [directory / name for name in ("POSCAR", "INCAR", "OUTCAR", "OSZICAR")]),
        "config_path": str(config_path.resolve()), "run_path": str(directory.resolve()),
        "outcar_final_ediff": True, "final_step": checked["outcar"]["final_step"],
        "segment": "single completed OUTCAR run; matched terminal ionic/electronic step",
        "build_banner": checked["outcar"]["build_banner"], "input_tags": record["tags"],
        "incar_echo": True}
    return result


def read_and_gate(config_path, directory, references_path, output, common_z=False):
    """Use the same config-bound read, physical gate and atomic state write for both CLIs."""
    config = manifest.load(config_path)
    readback = read_state(directory, config, config_path)
    references = manifest.load(references_path)
    gate = validate(config, readback, references.get("M_int"), references.get("MW_int"), common_z)
    value = {"config": config, "readback": readback, "gate": gate}
    manifest.save(value, output)
    return value


def validate(record, readback, moment_ref=None, weighted_ref=None, common_z=False):
    require_vector(record)
    provenance = readback.get("provenance", {})
    if not provenance.get("outcar_final_ediff") or not provenance.get("config_path") or not provenance.get("run_path"):
        raise ValueError("Missing independently associated OSZICAR/OUTCAR readback provenance")
    manifest.check_files(provenance["files"])
    if read_state(provenance["run_path"], record, provenance["config_path"]) != readback:
        raise ValueError("Stored sphere readback differs from verified run files")
    indices = record["magnetic_indices"]
    u = np.asarray(record["targets"], dtype=float)
    m, mw = (np.asarray(readback[key], dtype=float) for key in ("M_int", "MW_int"))
    if m.shape != u.shape or mw.shape != u.shape or readback.get("source") != "OSZICAR":
        raise ValueError("OSZICAR moment count/source does not match targets")
    if not np.all(np.isfinite(m)) or not np.all(np.isfinite(mw)):
        raise ValueError("Nonfinite sphere readback")
    if any(abs(np.linalg.norm(u[ion]) - 1) > 1e-6 for ion in indices):
        raise ValueError("Magnetic targets must be unit vectors")
    reasons = []
    norms, weighted = np.linalg.norm(m, axis=1), np.linalg.norm(mw, axis=1)
    if any(norms[i] < RESOLUTION or weighted[i] < RESOLUTION for i in indices):
        reasons.append("collapsed magnetic sphere moment")
        return {"passed": False, "reasons": reasons, "spins": None,
                "references": {"M_int": moment_ref, "MW_int": weighted_ref},
                "allow_common_z": common_z}
    spins = np.zeros_like(m)
    spins[indices] = m[indices] / norms[indices, None]
    offset = 0.0
    if common_z:
        # A single best signed in-plane offset; never rotate actual constraints or fitted spins.
        z = sum(complex(u[i, 0], u[i, 1]).conjugate() * complex(spins[i, 0], spins[i, 1]) for i in indices)
        offset = np.angle(z) if abs(z) > RESOLUTION else 0.0
    threshold = np.cos(np.deg2rad(DIRECTION_DEG))
    phase_errors = []
    for ion in indices:
        expected = rotate_z(u[ion], offset)
        if np.dot(expected, spins[ion]) <= threshold:
            reasons.append(f"ion {ion + 1} signed full geometry")
        transverse = np.linalg.norm(expected[:2])
        if transverse > RESOLUTION:
            t = np.linalg.norm(spins[ion, :2])
            if t < RESOLUTION:
                reasons.append(f"ion {ion + 1} unresolved transverse")
            else:
                phase = float(np.rad2deg(np.arccos(np.clip(np.dot(expected[:2], spins[ion, :2]) / (transverse * t), -1, 1))))
                phase_errors.append(phase)
                if phase >= DIRECTION_DEG:
                    reasons.append(f"ion {ion + 1} transverse phase")
        if np.dot(spins[ion], mw[ion] / weighted[ion]) <= threshold:
            reasons.append(f"ion {ion + 1} M_int/MW_int disagreement")
        if np.dot(u[ion], mw[ion] / weighted[ion]) <= threshold:
            reasons.append(f"ion {ion + 1} absolute weighted alignment")
    for reference, actual, label in ((moment_ref, norms, "M_int"), (weighted_ref, weighted, "MW_int")):
        if reference is None:
            reasons.append(f"missing same-definition {label} magnitude reference")
            continue
        ref = np.asarray(reference, dtype=float)
        if ref.shape != (len(indices),) or not np.all(np.isfinite(ref)) or np.any(ref <= 0):
            raise ValueError(f"Invalid {label} magnitude reference")
        if any(abs(actual[ion] - ref[site]) / ref[site] >= MOMENT_DRIFT for site, ion in enumerate(indices)):
            reasons.append(f"{label} magnitude drift")
    ep, printed_lam = readback["E_p_eV"], readback["lambda"]
    if not np.all(np.isfinite([ep, printed_lam])) or ep < 0 or printed_lam < 0:
        raise ValueError("Invalid printed final penalty or lambda")
    # read_state has matched this requested coefficient to the run INCAR and
    # OUTCAR echo. Its use as the effective coefficient still needs build evidence.
    lam = float(numbers(record["tags"]["LAMBDA"])[0])
    if lam > 0 and ep >= PENALTY_EV:
        reasons.append("printed constraint penalty exceeds threshold")
    precision = readback["precision"]
    mw_error = np.asarray(precision["MW_int"], dtype=float) / 2
    if mw_error.shape != mw.shape or np.any(mw_error <= 0):
        raise ValueError("Missing printed MW_int precision")
    field = readback.get("printed_field")
    predicted = np.zeros_like(mw)
    perps = np.zeros_like(mw)
    penalty = 0.0
    for ion in indices:
        perp = mw[ion] - u[ion] * np.dot(u[ion], mw[ion])
        perps[ion] = perp
        predicted[ion] = 2 * lam * perp
        penalty += lam * np.dot(perp, perp)
    # Bound the penalty from the printed MW_int digits and requested coefficient.
    perp_error = np.zeros_like(mw_error)
    perp_error[indices] = mw_error[indices] + np.abs(u[indices]) * np.sum(np.abs(u[indices]) * mw_error[indices], axis=1)[:, None]
    low = np.maximum(np.abs(perps) - perp_error, 0)
    high = np.abs(perps) + perp_error
    ep_error = precision["E_p_eV"] / 2
    penalty_low = lam * np.sum(low[indices] ** 2)
    penalty_high = lam * np.sum(high[indices] ** 2)
    if ep + ep_error < penalty_low or ep - ep_error > penalty_high:
        reasons.append("printed penalty disagrees with MW_int recomputation")
    penalty_check = ("fail: MW_int/penalty contradiction" if "printed penalty disagrees with MW_int recomputation" in reasons
                     else "pass: MW_int/penalty consistent within printed precision")
    field_check = {"status": "unavailable: no printed field",
                   "identity": {"status": "unavailable: no printed field"}}
    if field is not None:
        printed = np.asarray(field, dtype=float)
        field_error = np.asarray(precision["printed_field"], dtype=float) / 2
        if printed.shape != mw.shape or field_error.shape != mw.shape or not np.all(np.isfinite(printed)):
            raise ValueError("Invalid printed field ion count or values")
        field_check = {"status": "unavailable: factor-two unresolved at printed precision",
                       "coefficient": lam,
                       "coefficient_source": "requested LAMBDA matched to run INCAR and OUTCAR echo"}
        # Compare signed Cartesian components; magnitudes alone miss a reversed field.
        field_tolerance = 2 * lam * perp_error
        if np.any(np.abs(printed - predicted) > field_tolerance + field_error):
            field_check["status"] = "fail: printed field disagrees with MW_int"
            reasons.append("printed field disagrees with factor-two convention")
        field_penalty = float(np.sum(np.square(printed[indices])) / (4 * lam)) if lam > 0 else None
        field_check["field_E_p_eV"] = field_penalty
        if lam > 0:
            fp_low = np.sum(np.maximum(np.abs(printed[indices]) - field_error[indices], 0) ** 2) / (4 * lam)
            fp_high = np.sum((np.abs(printed[indices]) + field_error[indices]) ** 2) / (4 * lam)
            gap = max(float(fp_low - (ep + ep_error)), float((ep - ep_error) - fp_high), 0.0)
            field_check["identity"] = {
                "status": "unavailable: same-update association not established",
                "observed": "disjoint" if gap > 0 else "overlap",
                "gap_eV": gap, "field_E_p_interval_eV": [float(fp_low), float(fp_high)],
                "printed_E_p_interval_eV": [float(ep - ep_error), float(ep + ep_error)]}
        else:
            field_check["identity"] = {"status": "unavailable: zero coefficient"}
            if field_check["status"].startswith("fail"):
                field_check["status"] = "fail: nonzero zero-lambda field"
        # Resolve both the measured signal and the difference from a factor-one field.
        if lam > 0 and not field_check["status"].startswith("fail"):
            resolved = (np.linalg.norm(printed[indices]) > np.linalg.norm(field_error[indices]) and
                        np.any(lam * np.abs(perps[indices]) > (field_tolerance + field_error)[indices]))
            if resolved:
                field_check["status"] = "pass: factor-two signed field"
                field_check["printed_factor"] = float(np.sum(printed[indices] * perps[indices]) /
                                                       (lam * np.sum(perps[indices] ** 2)))
            else:
                field_check["consistency"] = "pass: zero/small field agrees with MW_int within printed precision"
    return {"passed": not reasons, "reasons": reasons, "spins": spins.tolist(),
            "phase_rms_deg": float(np.sqrt(np.mean(np.square(phase_errors)))) if phase_errors else None,
            "common_z_deg": float(np.rad2deg(offset)), "recomputed_E_p_eV": float(penalty),
            "recomputed_field": predicted.tolist(), "penalty_check": penalty_check,
            "field_check": field_check, "references": {"M_int": moment_ref, "MW_int": weighted_ref},
            "allow_common_z": common_z}


def coefficients(spins, q_frac, axis, basis, magnetic_indices):
    """One canonical bond kernel, for requested or measured unit vectors."""
    s = np.asarray(spins, dtype=float)
    q = vector(q_frac, "q_frac")
    if axis not in ("x", "y", "z") or s.ndim != 2 or s.shape[1] != 3 or not np.all(np.isfinite(s)):
        raise ValueError("Invalid axis or spins")
    if np.allclose(q, np.rint(q), atol=1e-12):
        raise ValueError("Generic-q model excludes reciprocal-lattice q")
    if not basis or not magnetic_indices:
        raise ValueError("Explicit canonical bonds and magnetic sites required")
    width = len(basis[0]["p"])
    if not width:
        raise ValueError("Empty symmetry parameter basis")
    row = np.zeros(width)
    seen = set()
    for bond in basis:
        a, b, r = bond["a"], bond["b"], bond["R"]
        if (not isinstance(a, int) or not isinstance(b, int) or a not in magnetic_indices
                or b not in magnetic_indices or a >= len(s) or b >= len(s)
                or len(r) != 3 or any(type(x) is not int for x in r)):
            raise ValueError("Bond endpoints must be mapped magnetic ions; R must be integer")
        key = (a, b, *r)
        reverse = (b, a, *[-x for x in r])
        if key in seen or reverse in seen or (a == b and all(x == 0 for x in r)):
            raise ValueError("Duplicate, reversed or self canonical bond")
        seen.add(key)
        p = np.asarray(bond["p"], dtype=float)
        if p.shape != (width, 3) or not np.all(np.isfinite(p)):
            raise ValueError("Bond symmetry basis must be finite (parameters, 3)")
        if any(abs(np.linalg.norm(s[ion]) - 1) > 1e-6 for ion in (a, b)):
            raise ValueError("Bond spins must be unit vectors")
        neighbor = rotate_z(s[b], 2 * np.pi * np.dot(q, r))
        g = np.cross(s[a], neighbor)[2]
        row += g * p[:, "xyz".index(axis)]
    return row


def paired(plus, minus, basis, trace_plus, trace_minus, sigma_y=None):
    """Assemble a diagnostic row; missing uncertainty never gives an accepted fit."""
    require_vector(plus["config"])
    require_vector(minus["config"])
    a, b = plus["config"], minus["config"]
    if a["side"] != "+" or b["side"] != "-" or a["id"] == b["id"]:
        raise ValueError("Distinct + and - partner configurations required")
    for key in ("family", "axis", "magnetic_indices", "species", "poscar_sha256"):
        if a[key] != b[key]:
            raise ValueError(f"Partner {key} mismatch")
    qsum = np.asarray(a["q_frac"]) + np.asarray(b["q_frac"])
    if not np.allclose(qsum - np.rint(qsum), 0, atol=1e-10):
        raise ValueError("Partner q mismatch modulo reciprocal lattice")
    if not np.allclose(np.asarray(a["targets"]) * [1, -1, 1], b["targets"], atol=1e-10):
        raise ValueError("Partner target reflection mismatch")
    for state in (plus, minus):
        gate = state["gate"]
        if not gate.get("passed"):
            raise ValueError("Both sphere realization gates must pass")
        references = gate.get("references", {})
        verified = validate(state["config"], state["readback"], references.get("M_int"),
                            references.get("MW_int"), gate.get("allow_common_z", False))
        if gate != verified or not verified["passed"]:
            raise ValueError("Stored sphere gate differs from verified moments, inputs or references")
    radii = [numbers(config["tags"]["RWIGS"]) for config in (a, b)]
    if (any(r.shape != (len(dict.fromkeys(a["species"])),) or np.any(r <= 0) for r in radii)
            or not np.allclose(radii[0], radii[1], atol=1e-9, rtol=0)):
        raise ValueError("Partner RWIGS radii mismatch by species")
    if any(not np.isfinite(x) for x in (trace_plus, trace_minus)):
        raise ValueError("Nonfinite traces")
    n = len(a["magnetic_indices"])
    sp, sm = np.asarray(plus["gate"]["spins"]), np.asarray(minus["gate"]["spins"])
    threshold = np.cos(np.deg2rad(DIRECTION_DEG))
    mirror_spins = sp * [1, -1, 1]
    # Reflection reverses a z rotation: fit one common signed offset for the pair.
    z = sum(complex(mirror_spins[i, 0], mirror_spins[i, 1]).conjugate() *
            complex(sm[i, 0], sm[i, 1]) for i in a["magnetic_indices"])
    offset = np.angle(z) if abs(z) > RESOLUTION and all(
        state["gate"]["allow_common_z"] for state in (plus, minus)) else 0.0
    for ion in a["magnetic_indices"]:
        mirror = rotate_z(mirror_spins[ion], offset)
        if np.dot(mirror, sm[ion]) <= threshold:
            raise ValueError("Partner measured signed geometry mismatch")
        if np.linalg.norm(mirror[:2]) > RESOLUTION:
            if np.linalg.norm(sm[ion, :2]) < RESOLUTION or (np.dot(mirror[:2], sm[ion, :2]) /
                    (np.linalg.norm(mirror[:2]) * np.linalg.norm(sm[ion, :2]))) <= threshold:
                raise ValueError("Partner measured transverse geometry mismatch")
    ap = coefficients(sp, a["q_frac"], a["axis"], basis, a["magnetic_indices"])
    am = coefficients(minus["gate"]["spins"], b["q_frac"], b["axis"], basis, b["magnetic_indices"])
    sigma = None if sigma_y is None else float(sigma_y)
    if sigma is not None and (not np.isfinite(sigma) or sigma <= 0):
        raise ValueError("sigma_y must be positive, independently supplied in eV per site")
    return {"row": ((ap - am) / n).tolist(), "y_eV_per_site": (trace_plus - trace_minus) / n,
            "pair_sum_eV": trace_plus + trace_minus, "sigma_y_eV_per_site": sigma,
            "axis": a["axis"], "status": "diagnostic: P0/noise and trace provenance not verified"}


def fit(rows):
    """Numerical weighted solve; no result is labelled production-accepted."""
    if not rows or any(row.get("sigma_y_eV_per_site") is None for row in rows):
        raise ValueError("Missing independently supplied uncertainty; no accepted weighted fit")
    a = np.asarray([row["row"] for row in rows], dtype=float)
    y = np.asarray([row["y_eV_per_site"] for row in rows], dtype=float)
    sigma = np.asarray([row["sigma_y_eV_per_site"] for row in rows], dtype=float)
    if a.ndim != 2 or a.shape[0] < a.shape[1] or not np.all(np.isfinite(a)) or not np.all(np.isfinite(y)) or not np.all(np.isfinite(sigma)) or np.any(sigma <= 0):
        raise ValueError("Invalid weighted fit inputs")
    design = a / sigma[:, None]
    if np.linalg.matrix_rank(design) != design.shape[1]:
        raise ValueError("Rank-deficient bond design")
    x = np.linalg.lstsq(design, y / sigma, rcond=None)[0]
    return {"parameters_eV": x.tolist(), "residual_eV_per_site": (y - a @ x).tolist(),
            "status": "numerical diagnostic only; production trace/parity/basis/noise gates not certified"}
