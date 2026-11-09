"""Seed, q plan, F0 inputs and readback (math Sections 3, 8 and 12).

Spec: plans/ten-03-spiral.md. Lattices are POSCAR row matrices in Å, positions
are fractional rows exactly as written in POSCAR, and sites are 0-based except
in seed.toml. No job is submitted here.
"""

from itertools import combinations, groupby, product
import os
from pathlib import Path
import re
import tomllib

import numpy as np

from . import manifest, symmetry
from .realized import INCAR_TAGS, echo_check, incar, logical, numbers, poscar

RANK_FLOOR = 0.1       # smallest singular value accepted in either rank condition
COLLAPSED = 0.1        # μB; a shorter M_int has no usable direction
PAIR_DEG = 90.0        # a relative site phase at or above this means another sign pattern
# Section 11 SCF-and-state checks, applied by collect.
TWIST_FREE_DEG = 1.0   # |delta_a| bound when n_twist = 0
MOMENT_DRIFT = 0.05    # |M_a / M_a(q0) - 1| bound
MZ_MAX = 0.05          # μB; |M_int z| bound for a flat spiral
REQUIRED = ("sites", "signs", "moments", "t")
OPTIONAL = ("spacegroup", "symprec", "directions", "exchange_grid", "rmax", "min_sigma")
# D-018 and math Section 3.2: finite smearing, so free energy TOTEN is variational
# and the force theorem holds. Fermi-Dirac, Gaussian, Methfessel-Paxton order 1.
SMEARING = {-1: "Fermi-Dirac", 0: "Gaussian", 1: "Methfessel-Paxton 1"}
MIN_SIGMA = 0.05       # eV; a seed may lower it for a convergence series
# Section 3.2 tags with one value for every run, and the tags set per run.
FIXED = {"LNONCOLLINEAR": "T", "LSPIRAL": "T", "LSORBIT": "F", "LZEROZ": "T",
         "SAXIS": "0 0 1", "ISYM": "-1", "I_CONSTRAINED_M": "1", "LAMBDA": "0"}
PER_RUN = ("QSPIRAL", "MAGMOM", "M_CONSTR")
LOGICAL = {"LNONCOLLINEAR", "LSPIRAL", "LSORBIT", "LZEROZ"}
TOTEN = re.compile(r"free\s+energy\s+TOTEN\s*=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[EeDd][+-]?\d+)?)")
CD = re.compile(r"(?:^|[;&|])\s*cd(?:\s|$)")
# Section 5 dump decks. A dump writes no WAVECAR or CHGCAR, so the linked parent
# files stay untouched.
DUMP_P = {"ISTART": "1", "ICHARG": "11", "ALGO": "Normal", "NELM": "1",
          "LDUMPCOCC": "T", "LWAVE": "F", "LCHARG": "F"}
# CSO depends only on the potential: read q0's CHGCAR (ICHARG = 11) and no WAVECAR.
DUMP_C = {"LNONCOLLINEAR": "T", "LSORBIT": "T", "ISYM": "-1", "ISTART": "0", "ICHARG": "11",
          "ALGO": "Normal", "NELM": "1", "LDUMPCSO": "T", "LWAVE": "F", "LCHARG": "F"}
CSO_DUMPS = {"dump_C": "0 0 1", "dump_C_x": "1 0 0", "dump_C_y": "0 1 0"}
SPIRAL_ONLY = ("LSPIRAL", "QSPIRAL", "LZEROZ", "I_CONSTRAINED_M", "LAMBDA", "M_CONSTR")

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
    echo_check(directory)
    result = sphere(directory / "OSZICAR", nions)
    ionic, electronic = (int(x) for x in iterations[-1].groups())
    if (result["ionic_steps"] != outcar_steps or
            (result["ionic_step"], result["electronic_step"]) != (ionic, electronic)):
        raise ValueError("Final OSZICAR ionic/electronic step cannot be associated with final OUTCAR EDIFF loop")
    return {"sphere": result, "outcar": {"final_step": [ionic, electronic],
            "build_banner": outcar.splitlines()[0].strip(), "ionic_steps": outcar_steps}}



# ---- seed ----------------------------------------------------------------

def _list(raw, key, kind, values=None):
    """A nonempty TOML list of integers (kind int) or of finite numbers."""
    values = raw[key] if values is None else values
    allowed = (int,) if kind is int else (int, float)   # type(), so bool is refused
    if not (isinstance(values, list) and values and all(type(v) in allowed for v in values)):
        raise ValueError(f"Seed {key} must be a nonempty list of "
                         f"{'integers' if kind is int else 'numbers'}")
    result = np.asarray(values, dtype=kind)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"Seed {key} has a non-finite value")
    return result


def load_seed(path):
    """seed.toml and the POSCAR beside it (docs/seed_file.md)."""
    path = Path(path)
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    unknown = sorted(set(raw) - set(REQUIRED) - set(OPTIONAL))
    if unknown:
        raise ValueError(f"Unknown seed keys: {unknown}")
    missing = [key for key in REQUIRED if key not in raw]
    if missing:
        raise ValueError(f"Missing seed keys: {missing}")
    lattice, species, tau = poscar(path.parent / "POSCAR")
    sites, signs = _list(raw, "sites", int), _list(raw, "signs", int)
    moments, t = _list(raw, "moments", float), _list(raw, "t", float)
    if not len(sites) == len(signs) == len(moments):
        raise ValueError("Seed sites, signs and moments need equal lengths")
    if len(set(sites)) != len(sites) or sites.min() < 1 or sites.max() > len(species):
        raise ValueError(f"Seed sites must be distinct atoms numbered 1 to {len(species)}")
    if not np.all(np.abs(signs) == 1) or not np.all(moments > 0):
        raise ValueError("Seed signs must be +1 or -1 and moments positive")
    if len(set(t)) < 3 or not np.all(t > 0):
        raise ValueError("Seed t needs at least 3 distinct positive magnitudes (Section 8.3)")
    seed = {"folder": path.parent, "text": path.read_text(encoding="utf-8"),
            "lattice": lattice, "species": species, "tau": tau,
            "sites": sites - 1, "signs": signs, "moments": moments, "t": t,
            "spacegroup": None, "symprec": 1e-3, "directions": None, "min_sigma": MIN_SIGMA,
            "exchange_grid": None, "rmax": None}
    if "spacegroup" in raw:
        if type(raw["spacegroup"]) is not int:
            raise ValueError("Seed spacegroup must be an integer")
        seed["spacegroup"] = raw["spacegroup"]
    if "min_sigma" in raw:
        seed["min_sigma"] = float(_list(raw, "min_sigma", float, [raw["min_sigma"]])[0])
        if seed["min_sigma"] <= 0:
            raise ValueError("Seed min_sigma must be positive")
    if "symprec" in raw:
        seed["symprec"] = float(_list(raw, "symprec", float, [raw["symprec"]])[0])
        if seed["symprec"] <= 0:
            raise ValueError("Seed symprec must be positive")
    if "directions" in raw:
        rows = raw["directions"]
        if not isinstance(rows, list) or not rows:
            raise ValueError("Seed directions must be a list of three-number rows")
        d = [_list(raw, "directions", float, row) for row in rows]
        if any(len(row) != 3 or not np.any(row) for row in d):
            raise ValueError("Each seed direction needs three numbers, not all zero")
        seed["directions"] = np.array(d)
    if ("exchange_grid" in raw) != ("rmax" in raw):
        raise ValueError("Seed exchange_grid and rmax go together")
    if "exchange_grid" in raw:
        grid = _list(raw, "exchange_grid", int)
        rmax = _list(raw, "rmax", float, [raw["rmax"]])[0]
        if len(grid) != 3 or np.any(grid < 1) or rmax <= 0:
            raise ValueError("Seed exchange_grid needs 3 positive integers and rmax > 0")
        seed["exchange_grid"], seed["rmax"] = grid, float(rmax)
    return seed


# ---- material INCAR ------------------------------------------------------

def _same(key, a, b):
    if key in LOGICAL:
        return logical({key: a}, key) == logical({key: b}, key)
    try:
        x, y = numbers(a), numbers(b)
        return x.shape == y.shape and np.allclose(x, y, rtol=0, atol=1e-9)
    except ValueError:
        return a.strip().upper() == b.strip().upper()


def species_types(species):
    """POSCAR line 6 entries, recovered from the per-atom list in order."""
    return [symbol for symbol, _ in groupby(species)]


def material_incar(seed):
    """Electronic settings from the material INCAR, checked against Section 3.2."""
    tags = incar(seed["folder"] / "INCAR")
    unknown = sorted(set(tags) - INCAR_TAGS)
    if unknown:
        raise ValueError(f"Unreviewed INCAR tags: {unknown}")
    for key in PER_RUN:
        if key in tags:
            raise ValueError(f"Material INCAR sets {key}; the code writes it per run")
    for key, value in FIXED.items():
        if key in tags and not _same(key, tags[key], value):
            raise ValueError(f"Material INCAR has {key} = {tags[key]}; Section 3.2 needs {value}")
    types = species_types(seed["species"])
    rwigs = numbers(tags["RWIGS"]) if "RWIGS" in tags else np.array([])
    if len(rwigs) != len(types) or not np.all(rwigs > 0):
        raise ValueError(f"Material INCAR needs RWIGS with one positive radius per species type {types}")
    for key in ("ENCUT", "ENINI", "ISMEAR", "SIGMA"):
        if key not in tags:
            raise ValueError(f"Material INCAR needs {key}")
    ismear, sigma = numbers(tags["ISMEAR"]), numbers(tags["SIGMA"])
    if ismear.shape != (1,) or sigma.shape != (1,):
        raise ValueError("Material INCAR ISMEAR and SIGMA need one value each")
    if ismear[0] not in SMEARING:
        allowed = ", ".join(f"{k} ({v})" for k, v in SMEARING.items())
        raise ValueError(f"ISMEAR = {ismear[0]:g} is not allowed; use {allowed} (D-018)")
    if sigma[0] < seed["min_sigma"]:
        raise ValueError(f"SIGMA = {sigma[0]:g} eV is below {seed['min_sigma']:g}; set min_sigma in the seed "
                         "for a convergence series (D-018)")
    return tags


# ---- q plan --------------------------------------------------------------

def cartesian(lattice, q_frac):
    """Eq (8.1), q = 2π L^{-T} q_frac with L = lattice.T: rows of 2π inv(lattice) @ q_frac."""
    return 2 * np.pi * np.linalg.solve(lattice, np.atleast_2d(np.asarray(q_frac, float)).T).T


def unit_directions(lattice, directions):
    """Cartesian unit vectors of q_frac directions."""
    s = cartesian(lattice, directions)
    return s / np.linalg.norm(s, axis=1)[:, None]


def conditions(lattice, directions, stiffness):
    """(sigma_D, sigma_A): rank-3 value of S and rank-p_A value of M[i, l] = s_i^T C_l s_i."""
    s = unit_directions(lattice, directions)
    sigma_d = np.linalg.svd(s.T, compute_uv=False)
    sigma_a = np.linalg.svd(np.einsum("ij,ljk,ik->il", s, stiffness, s), compute_uv=False)
    p_a = len(stiffness)
    return (float(sigma_d[2]) if len(sigma_d) == 3 else 0.0,
            float(sigma_a[p_a - 1]) if len(sigma_a) >= p_a else 0.0)


def choose_directions(lattice, stiffness):
    """Best-conditioned set of low-index q_frac directions, Section 8.2."""
    candidates = [c for c in product((-1, 0, 1), repeat=3) if c > (0, 0, 0)]
    n = max(3, len(stiffness))
    # Symmetry-equivalent sets tie to ~1e-15; round so the first set in
    # combinations order wins on every machine.
    best = max(combinations(candidates, n),
               key=lambda d: round(min(conditions(lattice, d, stiffness)), 9))
    return np.array(best, dtype=float)


def qspiral(q_frac):
    """The string written to QSPIRAL; phases are computed from its parsed value."""
    return " ".join(f"{x + 0.0:.12g}" for x in q_frac)


def targets(seed, q_frac):
    """Eq (3.1) lab targets for the magnetic sites.

    q_frac is the parsed QSPIRAL string (plan rounds it once), and the positions
    are the POSCAR values as written, never wrapped into [0, 1).
    """
    phi = 2 * np.pi * seed["tau"][seed["sites"]] @ np.asarray(q_frac, float)
    return seed["signs"][:, None] * np.column_stack([np.cos(phi), np.sin(phi), 0 * phi])


def plan(seed):
    """Symmetry summary, checked q directions and the run list. Writes nothing."""
    lattice, sites = seed["lattice"], seed["sites"]
    ops = symmetry.operations(lattice, seed["species"], seed["tau"], sites, seed["signs"],
                              seed["symprec"], seed["spacegroup"])
    rotations = ops["rotations"]
    stiffness = symmetry.stiffness_basis(rotations)
    tags = material_incar(seed)
    directions = seed["directions"]
    if directions is None:
        directions = choose_directions(lattice, stiffness)
    if len(directions) < max(3, len(stiffness)):
        raise ValueError(f"Need at least {max(3, len(stiffness))} q directions for p_A = {len(stiffness)}")
    sigma_d, sigma_a = conditions(lattice, directions, stiffness)
    if sigma_d < RANK_FLOOR:
        raise ValueError(f"q directions do not determine D: sigma_D = {sigma_d:.3g} < {RANK_FLOOR}")
    if sigma_a < RANK_FLOOR:
        raise ValueError(f"q directions do not determine the stiffness: sigma_A = {sigma_a:.3g} "
                         f"< {RANK_FLOOR} for p_A = {len(stiffness)}")
    points = [{"name": "q0", "q_frac": [0.0, 0.0, 0.0]}]
    for i, d in enumerate(directions, 1):
        # q = t s and Eq (8.1) give q_frac parallel to d, so scale d directly;
        # this keeps exact zeros instead of 1e-18 noise in QSPIRAL.
        length = np.linalg.norm(cartesian(lattice, d))
        for j, t in enumerate(seed["t"], 1):
            q_frac = t * d / length
            for side, sign in (("plus", 1), ("minus", -1)):
                points.append({"name": f"d{i}_t{j}_{side}",
                               "q_frac": numbers(qspiral(sign * q_frac)).tolist()})
    classes = None
    if seed["exchange_grid"] is not None:
        classes = len(symmetry.exchange_classes(lattice, seed["tau"][sites], seed["signs"], rotations,
                                                seed["rmax"], tol=2 * seed["symprec"]))
    return {"ops": ops, "p_D": len(symmetry.spiralization_basis(rotations)), "p_A": len(stiffness),
            "n_twist": symmetry.twist_count(rotations, ops["permutations"]),
            "directions": directions, "sigma_D": sigma_d, "sigma_A": sigma_a,
            "points": points, "classes": classes, "incar": tags, "symprec": seed["symprec"]}


# ---- inputs --------------------------------------------------------------

def split_job(text):
    """(shebang, #SBATCH header, body) of the user's launch script."""
    lines = text.splitlines()
    shebang = lines.pop(0) if lines and lines[0].startswith("#!") else "#!/bin/bash"
    last = -1
    for i, line in enumerate(lines):
        if line.strip() and not line.lstrip().startswith("#"):
            break
        if line.lstrip().startswith("#SBATCH"):
            last = i
    header, body = lines[:last + 1], lines[last + 1:]
    if any(re.match(r"\s*#SBATCH\s+(--array\b|-a\b)", line) for line in header):
        raise ValueError("job.sh already sets --array; prepare writes it")
    if any(CD.search(line.split("#", 1)[0]) for line in body):
        raise ValueError("job.sh must not cd; submit.sh enters each run directory")
    return shebang, header, body


def read_job(job):
    """Validated (shebang, header, body) of a launch script."""
    job = Path(job)
    text = job.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"{job} is empty")
    return (*split_job(text), manifest.file_hash(job))


def write_array(out, list_name, script_name, names, job_parts, command):
    """List file plus a Slurm array that enters one listed directory per task."""
    shebang, header, body, digest = job_parts
    (out / list_name).write_text("".join(n + "\n" for n in names), encoding="utf-8")
    lines = [shebang, *header, f"#SBATCH --array=1-{len(names)}",
             f"# Generated by {command} from a job script (sha256 {digest}).",
             f"# Submit from this directory with: sbatch {script_name}",
             f'cd "$SLURM_SUBMIT_DIR/$(sed -n "${{SLURM_ARRAY_TASK_ID}}p" "$SLURM_SUBMIT_DIR/{list_name}")" || exit 1',
             *body]
    (out / script_name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare(seed, out, job):
    """Write every F0 run, runs.txt, submit.sh and plan.json under out."""
    summary = plan(seed)
    out, folder = Path(out), seed["folder"]
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"{out} is not empty; do not overwrite a VASP run")
    shared = {}
    for name in ("POSCAR", "KPOINTS", "POTCAR"):
        shared[name] = (folder / name).read_bytes()
        if not shared[name].strip():
            raise ValueError(f"{folder / name} is empty")
    potcar = re.findall(r"VRHFIN\s*=\s*([A-Za-z]+)\s*:", shared["POTCAR"].decode("utf-8", "replace"))
    if potcar != species_types(seed["species"]):
        raise ValueError(f"POTCAR elements {potcar} differ from POSCAR species {species_types(seed['species'])}")
    job_parts = read_job(job)

    nions, sites = len(seed["species"]), seed["sites"]
    moments = np.zeros(nions)
    moments[sites] = seed["moments"]
    names = []
    for point in summary["points"]:
        u = targets(seed, point["q_frac"])
        lab = np.zeros((nions, 3))
        lab[sites] = u
        tags = dict(FIXED, QSPIRAL=qspiral(point["q_frac"]),
                    MAGMOM=" ".join(f"{x:.12g}" for x in (lab * moments[:, None]).flat),
                    M_CONSTR=" ".join(f"{x:.12g}" for x in lab.flat))
        run = out / point["name"]
        run.mkdir(parents=True)
        incar_tags = dict(summary["incar"], **tags)
        (run / "INCAR").write_text("".join(f"{k} = {v}\n" for k, v in incar_tags.items()), encoding="utf-8")
        for name, content in shared.items():
            (run / name).write_bytes(content)
        manifest.save({"q_frac": point["q_frac"], "sites": sites.tolist(), "signs": seed["signs"].tolist(),
                       "targets": u.tolist(), "tags": tags}, run / "config.json")
        names.append(point["name"])
    write_array(out, "runs.txt", "submit.sh", names, job_parts, "dmi prepare")
    hashes = {name: manifest.file_hash(folder / name) for name in ("seed.toml", "POSCAR", "INCAR", "KPOINTS", "POTCAR")}
    manifest.save({"seed": seed["text"], "sha256": hashes, "symbol": summary["ops"]["symbol"],
                   "number": summary["ops"]["number"], "total": summary["ops"]["total"],
                   "dropped": summary["ops"]["dropped"], "p_D": summary["p_D"], "p_A": summary["p_A"],
                   "n_twist": summary["n_twist"], "directions": summary["directions"].tolist(),
                   "sigma_D": summary["sigma_D"], "sigma_A": summary["sigma_A"],
                   "runs": summary["points"]}, out / "plan.json")
    return [out / name for name in names]


# ---- readback ------------------------------------------------------------

def read_run(run):
    """E and M_int of one finished run, with the Eq (3.3) phase relaxation."""
    run = Path(run)
    config = manifest.load(run / "config.json")
    tags = incar(run / "INCAR")
    for key, value in config["tags"].items():
        if key not in tags or not _same(key, tags[key], value):
            raise ValueError(f"Run INCAR {key} differs from config.json")
    checked = check_run(run, len(poscar(run / "POSCAR")[1]))
    state = checked["sphere"]
    if state["lambda"] != 0:
        raise ValueError(f"Printed final lambda is {state['lambda']}, not 0")
    energies = TOTEN.findall((run / "OUTCAR").read_text(encoding="utf-8", errors="replace"))
    if not energies:
        raise ValueError("OUTCAR has no free energy TOTEN line")
    m = np.asarray(state["M_int"])[config["sites"]]       # lab vectors; never the targets
    length = np.linalg.norm(m, axis=1)
    if np.any(length < COLLAPSED):
        raise ValueError(f"Collapsed moment: |M_int| = {length.min():.3g} μB < {COLLAPSED}")
    target = np.asarray(config["targets"])
    s = (m[:, 0] + 1j * m[:, 1]) / length                # Eq (3.2)
    u = target[:, 0] + 1j * target[:, 1]
    z = u.conj() * s
    # Judge the pattern by relative phases, which theta cannot absorb: in a
    # 2-site cell a reversed site gives |delta_a| = 90 on both sites but a
    # 180 deg pair. Every pair within 90 deg implies every |delta_a| < 90 deg.
    pair = np.degrees(np.abs(np.angle(z[:, None] * z[None, :].conj()))).max()
    if pair >= PAIR_DEG:
        raise ValueError(f"Site reversed: relative site phase {pair:.1f} deg; another sign pattern")
    theta = np.angle(np.sum(z))                           # Eq (3.3)
    delta = np.degrees(np.angle(z * np.exp(-1j * theta)))
    return {"E_eV": float(energies[-1].replace("D", "E").replace("d", "e")), "M_int": m.tolist(),
            "M": length.tolist(), "theta_deg": float(np.degrees(theta)), "delta_deg": delta.tolist(),
            "sha256": {name: manifest.file_hash(run / name) for name in ("OUTCAR", "OSZICAR")}}


def state_error(name, result, q0, twist_free):
    """Section 11 SCF-and-state checks against q0, or None when the run passes."""
    if np.abs(np.asarray(result["M_int"])[:, 2]).max() >= MZ_MAX:
        return f"|M_z| >= {MZ_MAX} μB: not a flat spiral"
    if name == "q0":
        return None
    if q0 is None:
        return "q0 not ok"
    drift = np.abs(np.asarray(result["M"]) / np.asarray(q0["M"]) - 1).max()
    if drift >= MOMENT_DRIFT:
        return f"|M_a / M_a(q0) - 1| = {drift:.3f} >= {MOMENT_DRIFT}"
    if twist_free and np.abs(result["delta_deg"]).max() >= TWIST_FREE_DEG:
        return f"|delta| = {np.abs(result['delta_deg']).max():.2f} deg >= {TWIST_FREE_DEG} with n_twist = 0"
    return None


def collect(out):
    """Read every run in runs.txt and write collected.json; rerunning is safe."""
    out = Path(out)
    twist_free = manifest.load(out / "plan.json")["n_twist"] == 0
    results = {}
    for name in (out / "runs.txt").read_text(encoding="utf-8").split():   # q0 first
        if not (out / name / "OUTCAR").exists():
            results[name] = {"error": "missing"}
            continue
        try:
            results[name] = read_run(out / name)
        except (OSError, ValueError, KeyError) as error:
            results[name] = {"error": str(error)}
            continue
        q0 = results.get("q0")
        error = state_error(name, results[name], None if q0 is None or "error" in q0 else q0, twist_free)
        if error:
            results[name] = {"error": error}
    manifest.save(results, out / "collected.json")
    return results


# ---- dump inputs ---------------------------------------------------------

def _stat(path):
    info = os.stat(path)
    return {"size": info.st_size, "mtime_ns": info.st_mtime_ns}


def parent_unchanged(dump_dir):
    """Raise unless the parent recorded by prepare_dumps is byte- and stat-identical."""
    dump_dir = Path(dump_dir)
    record = manifest.load(dump_dir / "parent.json")
    parent = dump_dir.parent / "q0" if dump_dir.name in CSO_DUMPS else dump_dir.parent
    for name, digest in record["sha256"].items():
        if manifest.file_hash(parent / name) != digest:
            raise ValueError(f"{dump_dir}: parent {name} changed since dmi dumps")
    for name, recorded in record["links"].items():
        if _stat(dump_dir / name) != recorded:
            raise ValueError(f"{dump_dir}: linked parent {name} changed size or mtime since dmi dumps")


def prepare_dumps(out, job):
    """Write dump_C, dump_C_x, dump_C_y and every ok run's dump_P (Section 5).

    Returns (dump directories in submit order, names of runs skipped as not ok).
    """
    out = Path(out)
    job_parts = read_job(job)
    collected = manifest.load(out / "collected.json")
    names = (out / "runs.txt").read_text(encoding="utf-8").split()
    if "error" in collected.get("q0", {"error": "missing"}):
        raise ValueError("q0 is not ok in collected.json; the CSO dumps need its CHGCAR")
    q0_tags = incar(out / "q0" / "INCAR")
    cso_base = {k: v for k, v in q0_tags.items() if k not in SPIRAL_ONLY}   # keeps q0's MAGMOM
    decks, skipped = [], []
    for name in names:
        result = collected.get(name, {"error": "missing"})
        if "error" in result:
            skipped.append(name)
            continue
        parent = out / name
        for file, digest in result["sha256"].items():
            if manifest.file_hash(parent / file) != digest:
                raise ValueError(f"{name}: {file} changed since dmi collect; rerun collect")
        tags = dict(incar(parent / "INCAR"), **DUMP_P)
        if name == "q0":
            tags["LDUMPCPROJ"] = "T"                       # M1 on the first state (D-011)
            for dump, saxis in CSO_DUMPS.items():
                decks.append((out / dump, name, "../q0/", ("CHGCAR",),
                              dict(cso_base, **DUMP_C, SAXIS=saxis), result["sha256"]))
        decks.append((parent / "dump_P", name, "../", ("CHGCAR", "WAVECAR"), tags, result["sha256"]))
    for directory, name, link, files, tags, _ in decks:
        if directory.exists():
            raise ValueError(f"{directory} exists; do not overwrite a dump")
        for file in files:
            source = out / name / file
            if not source.is_file() or source.stat().st_size == 0:
                raise ValueError(f"{name}: no {file}; the parent INCAR must not set LWAVE or LCHARG to F")
        if logical(tags, "LSORBIT") and any(key in tags for key in SPIRAL_ONLY):
            raise ValueError(f"{directory}: an LSORBIT = T deck must not contain spiral tags")
    for directory, name, link, files, tags, digests in decks:
        directory.mkdir()
        (directory / "INCAR").write_text("".join(f"{k} = {v}\n" for k, v in tags.items()), encoding="utf-8")
        for file in ("POSCAR", "KPOINTS", "POTCAR"):
            (directory / file).write_bytes((out / name / file).read_bytes())
        for file in files:
            os.symlink(link + file, directory / file)
        manifest.save({"parent": name, "sha256": digests,
                       "links": {file: _stat(directory / file) for file in files}}, directory / "parent.json")
    dirs = [d for d, *_ in decks]
    write_array(out, "dumps.txt", "submit_dumps.sh", [str(d.relative_to(out)) for d in dirs],
                job_parts, "dmi dumps")
    return dirs, skipped
