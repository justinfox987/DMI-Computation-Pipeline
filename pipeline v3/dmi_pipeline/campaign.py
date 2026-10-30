"""Prepare a small Step 1 campaign without scheduling or reference extraction."""

import json
from pathlib import Path
import re

from . import manifest, step1
from .realized import incar
from .workflow import INCAR_TAGS

SCHEMA = "dmi-campaign-1"
PLAN_SCHEMA = "dmi-plan-1"
CASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
RECIPE_FIELDS = {"family", "side", "q_frac", "axis", "magnetic_indices", "signs",
                 "seed_magnitudes", "rwigs", "lambda", "lzeroz", "angle_deg",
                 "f1_policy", "nonmag_seed"}
CASE_FIELDS = RECIPE_FIELDS | {"id", "purpose", "pair", "execution_parents", "acceptance_requires"}
CAMPAIGN_FIELDS = {"schema", "run_root", "material", "job_template", "reference", "defaults", "cases"}
MATERIAL_FILES = ("POSCAR", "INCAR", "KPOINTS", "POTCAR")
RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}


def _keys(value, allowed, required, name):
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"Unknown {name} keys: {sorted(unknown)}")
    missing = required - set(value)
    if missing:
        raise ValueError(f"Missing {name} keys: {sorted(missing)}")


def _id(value, name):
    if (not isinstance(value, str) or not CASE_ID.fullmatch(value) or ".." in value
            or value.endswith(".") or value.split(".", 1)[0].upper() in RESERVED_NAMES):
        raise ValueError(f"Unsafe {name}: {value!r}")


def _list(value, name):
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value) or len(value) != len(set(value)):
        raise ValueError(f"{name} must be a list of unique names")
    for item in value:
        _id(item, name)


def build_plan(source):
    """Validate the entire campaign and return a plan and resolved recipes; no writes."""
    source = Path(source).resolve()
    data = manifest.load(source)
    _keys(data, CAMPAIGN_FIELDS, CAMPAIGN_FIELDS, "campaign")
    if data["schema"] != SCHEMA:
        raise ValueError(f"Campaign schema must be {SCHEMA}")
    for name in ("run_root", "material", "job_template"):
        if not isinstance(data[name], str) or not data[name].strip():
            raise ValueError(f"{name} must be an explicit path")
    root = (source.parent / data["run_root"]).resolve()
    material = (source.parent / data["material"]).resolve()
    job = (source.parent / data["job_template"]).resolve()
    if (source == root or root in source.parents or root == material or root in material.parents
            or material in root.parents or root == job or root in job.parents):
        raise ValueError("Output collision: run_root overlaps a campaign input")
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError("Campaign run_root must be empty; do not overwrite a VASP run")

    ref = data["reference"]
    _keys(ref, {"mode", "path"}, {"mode"}, "reference")
    if ref["mode"] == "import":
        if not isinstance(ref.get("path"), str) or not ref["path"].strip():
            raise ValueError("Imported reference needs an explicit path")
        reference_path = (source.parent / ref["path"]).resolve()
        if reference_path == root or root in reference_path.parents or reference_path in root.parents:
            raise ValueError("Output collision: imported reference overlaps run_root")
        reference = {"mode": "import", "path": ref["path"], "status": "unverified; T3 extraction and compatibility pending"}
        reference_id = "import:reference-q0"
    elif ref["mode"] == "generate":
        if "path" in ref:
            raise ValueError("Generated reference must not have an import path")
        reference = {"mode": "generate", "id": "reference-q0", "status": "preparation deferred to T3"}
        reference_id = "reference-q0"
    else:
        raise ValueError("reference.mode must be import or generate")

    _keys(data["defaults"], RECIPE_FIELDS, set(), "defaults")
    if not isinstance(data["cases"], list) or not data["cases"]:
        raise ValueError("Campaign requires a nonempty cases list")
    for name in MATERIAL_FILES:
        path = material / name
        if not path.is_file() or not path.read_bytes().strip():
            raise ValueError(f"Shared {name} must exist and be nonempty: {path}")
    if not job.is_file() or not job.read_bytes().strip():
        raise ValueError(f"job_template must exist and be nonempty: {job}")
    tags = incar(material / "INCAR")
    if not tags:
        raise ValueError("Shared INCAR is empty")
    unknown = set(tags) - INCAR_TAGS
    if unknown:
        raise ValueError(f"Unreviewed INCAR tags: {sorted(unknown)}")
    cold = tags.get("ISTART") == "0" and tags.get("ICHARG") == "2"

    recipes, records, entries, pair_members = {}, {}, [], {}
    seen_paths = set()
    for case in data["cases"]:
        _keys(case, CASE_FIELDS, {"id", "side", "q_frac", "purpose"}, "case")
        case_id = case["id"]
        _id(case_id, "case id")
        # Windows paths can alias by case or a trailing dot; reject them before writing.
        path_key = case_id.rstrip(".").casefold()
        if path_key in seen_paths or case_id == "reference-q0":
            raise ValueError(f"Duplicate case id or output collision: {case_id}")
        seen_paths.add(path_key)
        if not isinstance(case["purpose"], str) or not case["purpose"].strip():
            raise ValueError(f"Case {case_id} needs a purpose")
        parents = case.get("execution_parents", [])
        requires = case.get("acceptance_requires", [])
        _list(parents, "execution_parents")
        _list(requires, "acceptance_requires")
        if reference_id in requires:
            raise ValueError(f"Case {case_id} duplicates its reference acceptance prerequisite")
        if not cold and not parents:
            raise ValueError(f"Case {case_id} needs ISTART=0 and ICHARG=2 or an explicit execution parent")
        recipe = dict(data["defaults"])
        recipe.update({key: value for key, value in case.items() if key in RECIPE_FIELDS})
        recipe["id"] = case_id
        # prepare() reflects the negative side itself; input q must not be negated first.
        try:
            q = step1.vector(recipe["q_frac"], "q_frac")
            first = next((float(component) for component in q if component != 0), 0)
            if first <= 0:
                raise ValueError("needs an unwrapped positive q_frac even for side '-'")
            record = step1.prepare(recipe, material / "POSCAR")
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid recipe for {case_id}: {error}") from error
        recipes[case_id] = recipe
        records[case_id] = record
        pair = case.get("pair")
        if pair is not None:
            _id(pair, "pair id")
            pair_members.setdefault(pair, []).append(case_id)
        if parents:
            initialization = "declared execution parent; shared INCAR: ISTART=0, ICHARG=2" if cold else "restart (declared execution parent)"
        else:
            initialization = "cold (ISTART=0, ICHARG=2)"
        entry = {"id": case_id, "purpose": case["purpose"], "pair": pair, "side": record["side"],
                 "initialization": initialization,
                 "run_dir": f"runs/{case_id}", "execution_parents": parents,
                 "acceptance_requires": [reference_id, *requires], "reference": reference_id}
        entries.append(entry)

    for entry in entries:
        for parent in entry["execution_parents"]:
            if parent not in recipes:
                raise ValueError(f"Missing execution parent {parent} for {entry['id']}")
        for required in entry["acceptance_requires"][1:]:
            if required not in recipes:
                raise ValueError(f"Missing acceptance prerequisite {required} for {entry['id']}")
    graph = {entry["id"]: entry["execution_parents"] for entry in entries}
    visiting, visited = set(), set()

    def visit(case_id):
        if case_id in visiting:
            raise ValueError(f"Execution parent cycle at {case_id}")
        if case_id in visited:
            return
        visiting.add(case_id)
        for parent in graph[case_id]:
            visit(parent)
        visiting.remove(case_id)
        visited.add(case_id)

    for case_id in graph:
        visit(case_id)

    pairs = []
    seen_pairs = set()
    for pair, members in pair_members.items():
        if pair.casefold() in seen_pairs:
            raise ValueError(f"Pair id output collision: {pair}")
        seen_pairs.add(pair.casefold())
        if len(members) != 2 or {records[name]["side"] for name in members} != {"+", "-"}:
            raise ValueError(f"Pair {pair} needs exactly one '+' and one '-' member")
        plus = next(name for name in members if records[name]["side"] == "+")
        minus = next(name for name in members if records[name]["side"] == "-")
        a, b = records[plus], records[minus]
        if (a["family"] != b["family"] or a["axis"] != b["axis"]
                or a["poscar_sha256"] != b["poscar_sha256"]
                or a["q_frac"] != [-component for component in b["q_frac"]]
                or {key: value for key, value in recipes[plus].items() if key not in ("id", "side")}
                != {key: value for key, value in recipes[minus].items() if key not in ("id", "side")}):
            raise ValueError(f"Pair {pair} has mismatched family, axis, material, recipe or unwrapped positive q")
        pairs.append({"id": pair, "plus": plus, "minus": minus})

    if ref["mode"] == "generate":
        entries.insert(0, {"id": "reference-q0", "purpose": "q0 reference", "pair": None,
                           "side": None, "initialization": "preparation deferred to T3", "run_dir": "runs/reference-q0",
                           "execution_parents": [], "acceptance_requires": [], "reference": None,
                           "status": "preparation deferred to T3"})
    plan = {"schema": PLAN_SCHEMA, "run_count": len(entries), "cases": entries, "pairs": pairs,
            "reference": reference,
            "inputs": {"campaign_sha256": manifest.file_hash(source),
                       "material": {name: manifest.file_hash(material / name) for name in MATERIAL_FILES},
                       "job_template_sha256": manifest.file_hash(job)}}
    try:
        json.dumps(plan, allow_nan=False)
        json.dumps(recipes, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid campaign JSON values: {error}") from error
    return plan, recipes, records, root, material, job


def prepare(source):
    """Validate first; then copy the original campaign and expand every finite-q run."""
    plan, recipes, records, root, material, job = build_plan(source)
    if plan["reference"]["mode"] == "generate":
        raise ValueError("reference.mode generate preparation not yet implemented (T3); reference-q0 is reserved in the plan")
    root.mkdir(parents=True, exist_ok=True)
    (root / "campaign.json").write_bytes(Path(source).read_bytes())
    for case_id, recipe in recipes.items():
        manifest.save(recipe, root / "cases" / case_id / "recipe.json")
        step1.write_inputs(records[case_id], root / "runs" / case_id, material, job)
    manifest.save(plan, root / "plan.json")
    return plan
