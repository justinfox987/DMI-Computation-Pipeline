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
from .realized import incar, logical, numbers, poscar

RANK_FLOOR = 0.1       # smallest singular value of the column-normalized tensor columns (Section 9.4)
COLLAPSED = 0.1        # μB; a shorter M_int has no usable direction
PAIR_DEG = 90.0        # a relative site phase at or above this means another sign pattern
# Section 11 SCF-and-state checks, applied by collect.
TWIST_FREE_DEG = 1.0   # |delta_a| bound when n_twist = 0
MOMENT_DRIFT = 0.05    # |M_a / M_a(q0) - 1| bound
MZ_MAX = 0.05          # μB; |M_int z| bound for a flat spiral
REQUIRED = ("sites", "signs", "moments", "t")
OPTIONAL = ("spacegroup", "symprec", "directions")
# D-022 and math Section 3.2: tetrahedron modes give no variational energy, so the
# force theorem does not hold. This is the one check on the user's settings.
TETRAHEDRON = (-4, -5)
# The eleven tags the code owns (Section 3.2): one value for every run, and the tags set per run.
FIXED = {"LNONCOLLINEAR": "T", "LSPIRAL": "T", "LSORBIT": "F", "LZEROZ": "T",
         "SAXIS": "0 0 1", "ISYM": "-1", "I_CONSTRAINED_M": "1", "LAMBDA": "0"}
PER_RUN = ("QSPIRAL", "MAGMOM", "M_CONSTR")
LOGICAL = {"LNONCOLLINEAR", "LSPIRAL", "LSORBIT", "LZEROZ"}
FLOAT = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[EeDd][+-]?\d+)?"
TOTEN = re.compile(r"free\s+energy\s+TOTEN\s*=\s*(" + FLOAT + ")")
PENALTY = re.compile(r"\blambda\s*=\s*(" + FLOAT + ")", re.I)
SUMMARY = re.compile(r"^\s*\d+\s+F=")       # the OSZICAR line closing an ionic step
CD = re.compile(r"(?:^|[;&|])\s*cd(?:\s|$)")
# Section 5 dump decks. A dump writes no WAVECAR or CHGCAR, so the linked parent
# files stay untouched.
DUMP_P = {"ISTART": "1", "ICHARG": "11", "ALGO": "Normal", "NELM": "1",
          "LDUMPCOCC": "T", "LWAVE": "F", "LCHARG": "F"}
# CSO depends only on the potential: read q0's CHGCAR (ICHARG = 11) and no WAVECAR.
DUMP_C = {"LNONCOLLINEAR": "T", "LSORBIT": "T", "ISYM": "-1", "ISTART": "0", "ICHARG": "11",
          "ALGO": "Normal", "NELM": "1", "LDUMPCSO": "T", "LWAVE": "F", "LCHARG": "F", "SAXIS": "0 0 1"}
SPIRAL_ONLY = ("LSPIRAL", "QSPIRAL", "LZEROZ", "I_CONSTRAINED_M", "LAMBDA", "M_CONSTR")

SPHERE = re.compile(r"^\s*ion\s+MW_int\s+M_int\s*$", re.I)


def read_static(run, nions):
    """(E, M_int, mag) of one finished static run (Section 3.3, D-021).

    The OUTCAR must have reached EDIFF and printed its timing footer. M_int is the
    last OSZICAR sphere block, one row per ion; E is the last free energy TOTEN.
    mag is the cell moment on the last F= line (three components in a
    noncollinear run), or None when that line prints no mag=.
    A constrained run whose last printed lambda is not 0 is refused: its energy
    holds a penalty term.
    """
    run = Path(run)
    outcar = (run / "OUTCAR").read_text(encoding="utf-8", errors="replace")
    if "aborting loop because EDIFF is reached" not in outcar:
        raise ValueError("OUTCAR: the SCF did not reach EDIFF")
    if "General timing and accounting" not in outcar:
        raise ValueError("OUTCAR has no timing footer: the run did not finish")
    energies = TOTEN.findall(outcar)
    if not energies:
        raise ValueError("OUTCAR has no free energy TOTEN line")
    oszicar = (run / "OSZICAR").read_text(encoding="utf-8", errors="replace")
    penalty = PENALTY.findall(oszicar)
    if penalty and float(penalty[-1].replace("D", "E").replace("d", "e")) != 0:
        raise ValueError(f"OSZICAR prints lambda = {penalty[-1]}, not 0: the energy holds a penalty term")
    lines = oszicar.splitlines()
    headers = [i for i, line in enumerate(lines) if SPHERE.match(line)]
    if not headers:
        raise ValueError("OSZICAR has no ion MW_int M_int block")
    rows = [line.split() for line in lines[headers[-1] + 1:headers[-1] + 1 + nions]]
    if len(rows) != nions or any(len(row) != 7 or row[0] != str(ion) for ion, row in enumerate(rows, 1)):
        raise ValueError(f"Last OSZICAR sphere block does not have one row for each of the {nions} ions")
    m = np.array([[float(x.replace("D", "E").replace("d", "e")) for x in row[4:]] for row in rows])
    if not np.all(np.isfinite(m)):
        raise ValueError("Non-finite OSZICAR M_int")
    summary = [line for line in lines if SUMMARY.match(line)]
    mag = None
    if summary and "mag=" in summary[-1]:
        mag = np.array([float(x.replace("D", "E").replace("d", "e")) for x in summary[-1].split("mag=")[1].split()])
    return float(energies[-1].replace("D", "E").replace("d", "e")), m, mag


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
            # Ascending t, so run d{i}_t1 is the smallest t, where P0 and E0 gate.
            "sites": sites - 1, "signs": signs, "moments": moments, "t": np.sort(t),
            "spacegroup": None, "symprec": 1e-3, "directions": None}
    if "spacegroup" in raw:
        if type(raw["spacegroup"]) is not int:
            raise ValueError("Seed spacegroup must be an integer")
        seed["spacegroup"] = raw["spacegroup"]
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
    """The user's INCAR (D-019, D-022), and one line per owned tag it sets differently.

    The code writes its own value for each of the eleven tags it owns and refuses
    tetrahedron smearing. It checks nothing else.
    """
    tags = incar(seed["folder"] / "INCAR")
    if "ISMEAR" in tags and numbers(tags["ISMEAR"])[0] in TETRAHEDRON:
        raise ValueError(f"ISMEAR = {tags['ISMEAR']} (tetrahedron) is refused: its energy is not variational, "
                         "so the force theorem of Section 3.2 does not hold (D-022)")
    overrides = [f"override {key}: INCAR has {' '.join(tags[key].split())}; using {value}"
                 for key, value in FIXED.items() if key in tags and not _same(key, tags[key], value)]
    overrides += [f"override {key}: INCAR has {' '.join(tags[key].split())}; using the per-run value from the seed"
                  for key in PER_RUN if key in tags]
    return tags, overrides


# ---- q plan --------------------------------------------------------------

def cartesian(lattice, q_frac):
    """Eq (8.1), q = 2π L^{-T} q_frac with L = lattice.T: rows of 2π inv(lattice) @ q_frac."""
    return 2 * np.pi * np.linalg.solve(lattice, np.atleast_2d(np.asarray(q_frac, float)).T).T


def unit_directions(lattice, directions):
    """Cartesian unit vectors of q_frac directions."""
    s = cartesian(lattice, directions)
    return s / np.linalg.norm(s, axis=1)[:, None]


FREE_BASIS = np.eye(9).reshape(9, 3, 3)    # D_free: the nine components, row-major


def spiralization_design(s, points, basis):
    """Design of the single solve for D (Section 9.4): rows (point m, axis a) of
    y_a = 2 t (D s_i)_a + c_ia t^3; columns: the basis coefficients, then c_ia."""
    nb, nd = len(basis), len(s)
    design = np.zeros((3 * len(points), nb + 3 * nd))
    for m, (i, t) in enumerate(points):
        design[3 * m:3 * m + 3, :nb] = 2 * t * np.reshape([b @ s[i] for b in basis], (nb, 3)).T
        design[3 * m:3 * m + 3, nb + 3 * i:nb + 3 * i + 3] = t ** 3 * np.eye(3)
    return design


def stiffness_design(s, points, basis):
    """Design of the single solve for A: rows m of g = t^2 s_i^T A s_i + b_i t^4."""
    nb, nd = len(basis), len(s)
    design = np.zeros((len(points), nb + nd))
    for m, (i, t) in enumerate(points):
        design[m, :nb] = [t * t * s[i] @ c @ s[i] for c in basis]
        design[m, nb + i] = t ** 4
    return design


def rank_value(design):
    """Smallest singular value after scaling each column to unit norm; 0 when the
    matrix has fewer rows than columns or a zero column; None with no columns
    (p_D = 0: nothing to determine)."""
    if not design.shape[1]:
        return None
    norms = np.linalg.norm(design, axis=0)
    if design.shape[0] < design.shape[1] or np.any(norms == 0):
        return 0.0
    return float(np.linalg.svd(design / norms, compute_uv=False)[-1])


def undetermined(value):
    """True when a rank value fails RANK_FLOOR; None (no tensor columns) never fails."""
    return value is not None and value < RANK_FLOOR


def geometry_ranks(s, d_basis, a_basis):
    """rank_value of the tensor columns of the constrained-D, D_free and A designs,
    one row block per direction with t set aside (Section 9.4).

    These test the geometry alone. The nuisance columns are separate: they are
    determined when every direction has at least two distinct magnitudes, which
    plan and fit require. The full design would cap these values through the
    t-t^3 correlation of the grid, whatever the directions.
    """
    points = [(i, 1.0) for i in range(len(s))]
    return {"D": rank_value(spiralization_design(s, points, d_basis)[:, :len(d_basis)]),
            "A": rank_value(stiffness_design(s, points, a_basis)[:, :len(a_basis)]),
            "D_free": rank_value(spiralization_design(s, points, FREE_BASIS)[:, :9])}


def choose_directions(lattice, d_basis, a_basis):
    """Best-conditioned set of max(3, p_A) low-index q_frac directions, Section 8.2."""
    candidates = [c for c in product((-1, 0, 1), repeat=3) if c > (0, 0, 0)]
    # Symmetry-equivalent sets tie to ~1e-15; round so the first set in
    # combinations order wins on every machine.
    best = max(combinations(candidates, max(3, len(a_basis))),
               key=lambda d: round(min(v for v in geometry_ranks(unit_directions(lattice, d), d_basis, a_basis).values()
                                       if v is not None), 9))
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
    d_basis, a_basis = symmetry.spiralization_basis(rotations), symmetry.stiffness_basis(rotations)
    tags, overrides = material_incar(seed)
    directions = seed["directions"]
    if directions is None:
        directions = choose_directions(lattice, d_basis, a_basis)
    # Explicit directions may be fewer than three when both designs have full rank.
    # load_seed already requires three distinct magnitudes, so every direction has two.
    ranks = geometry_ranks(unit_directions(lattice, directions), d_basis, a_basis)
    if undetermined(ranks["D"]):
        raise ValueError(f"q directions do not determine D: rank value {ranks['D']:.3g} < {RANK_FLOOR}")
    if undetermined(ranks["A"]):
        raise ValueError(f"q directions do not determine the stiffness: rank value {ranks['A']:.3g} "
                         f"< {RANK_FLOOR} for p_A = {len(a_basis)}")
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
    return {"ops": ops, "p_D": len(d_basis), "p_A": len(a_basis),
            "n_twist": symmetry.twist_count(rotations, ops["permutations"]),
            "directions": directions, "ranks": ranks, "points": points, "incar": tags,
            "overrides": overrides, "symprec": seed["symprec"]}


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
    manifest.save({"seed": seed["text"], "symbol": summary["ops"]["symbol"],
                   "number": summary["ops"]["number"], "total": summary["ops"]["total"],
                   "dropped": summary["ops"]["dropped"], "p_D": summary["p_D"], "p_A": summary["p_A"],
                   "n_twist": summary["n_twist"], "directions": summary["directions"].tolist(),
                   "ranks": summary["ranks"],
                   "runs": summary["points"]}, out / "plan.json")
    return [out / name for name in names]


# ---- readback ------------------------------------------------------------

def read_run(run):
    """E and M_int of one finished run, with the Eq (3.3) phase relaxation."""
    run = Path(run)
    config = manifest.load(run / "config.json")
    energy, m_int, mag = read_static(run, len(poscar(run / "POSCAR")[1]))
    m = m_int[config["sites"]]                            # lab vectors; never the targets
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
    return {"E_eV": energy, "M_int": m.tolist(), "M": length.tolist(),
            # Total cell moment per magnetic site: meaningful at q0 only, where it enters D_sw.
            "M_total": None if mag is None or run.name != "q0" else float(np.linalg.norm(mag)) / len(m),
            "theta_deg": float(np.degrees(theta)), "delta_deg": delta.tolist()}


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


def read_runs(out):
    """E, M_int and the Section 11 state checks of every run in runs.txt, q0 first.

    Every command that needs a run's state calls this; nothing reads collected.json.
    """
    out = Path(out)
    twist_free = manifest.load(out / "plan.json")["n_twist"] == 0
    results = {}
    for name in run_names(out):   # q0 first
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
    return results


def collect(out):
    """dmi collect: read every run and write collected.json as a report."""
    results = read_runs(out)
    manifest.save(results, Path(out) / "collected.json")
    return results


def run_names(out):
    """Run directory names in submit order, q0 first (runs.txt written by prepare)."""
    return (Path(out) / "runs.txt").read_text(encoding="utf-8").split()


# ---- dump inputs ---------------------------------------------------------

def prepare_dumps(out, job):
    """Write dump_C from q0's CHGCAR and every ok run's dump_P (Section 5).

    Returns (dump directories in submit order, {name: error} of runs skipped).
    """
    out = Path(out)
    job_parts = read_job(job)
    states = read_runs(out)
    if "error" in states.get("q0", {"error": "missing"}):
        raise ValueError(f"q0 is not ok ({states.get('q0', {}).get('error', 'missing')}); dump_C needs its CHGCAR")
    q0_tags = incar(out / "q0" / "INCAR")
    cso_base = {k: v for k, v in q0_tags.items() if k not in SPIRAL_ONLY}   # keeps q0's MAGMOM
    decks = [(out / "dump_C", "q0", "../q0/", ("CHGCAR",), dict(cso_base, **DUMP_C))]
    skipped = {}
    for name, state in states.items():
        if "error" in state:
            skipped[name] = state["error"]
            continue
        decks.append((out / name / "dump_P", name, "../", ("CHGCAR", "WAVECAR"),
                      dict(incar(out / name / "INCAR"), **DUMP_P)))
    for directory, name, link, files, tags in decks:
        if directory.exists():
            raise ValueError(f"{directory} exists; do not overwrite a dump")
        for file in files:
            source = out / name / file
            if not source.is_file() or source.stat().st_size == 0:
                raise ValueError(f"{name}: no {file}; the parent INCAR must not set LWAVE or LCHARG to F")
        if logical(tags, "LSORBIT") and any(key in tags for key in SPIRAL_ONLY):
            raise ValueError(f"{directory}: an LSORBIT = T deck must not contain spiral tags")
    for directory, name, link, files, tags in decks:
        directory.mkdir()
        (directory / "INCAR").write_text("".join(f"{k} = {v}\n" for k, v in tags.items()), encoding="utf-8")
        for file in ("POSCAR", "KPOINTS", "POTCAR"):
            (directory / file).write_bytes((out / name / file).read_bytes())
        for file in files:
            os.symlink(link + file, directory / file)
    dirs = [d for d, *_ in decks]
    write_array(out, "dumps.txt", "submit_dumps.sh", [str(d.relative_to(out)) for d in dirs],
                job_parts, "dmi dumps")
    return dirs, skipped
