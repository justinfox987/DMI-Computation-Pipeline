"""Command line for the N0 acceptance milestone."""

import argparse
import json
from pathlib import Path
import sys

from . import manifest
from .dumpio import load_cocc, load_cproj, load_cso, load_ferwe
from .gates import gate_c0, gate_m1
from .workflow import finish, initialize, t3, trace_null


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Patch B N0 acceptance workflow")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init-null", help="Register existing reference and dump runs")
    for name in ("root", "ref", "dump-c", "dump-p"):
        init.add_argument("--" + name, type=Path, required=True)
    finish_parser = commands.add_parser("finish", help="Check a registered run and write DONE/FAILED")
    finish_parser.add_argument("kind", choices=("ref", "dump_C", "dump_P"))
    finish_parser.add_argument("--manifest", type=Path, required=True)
    for name in ("trace", "status"):
        sub = commands.add_parser(name)
        sub.add_argument("--manifest", type=Path, required=True)
    gate = commands.add_parser("gate", help="Inspect a dump; results never certify N0 alone")
    gate.add_argument("name", choices=("c0", "w0", "m1"))
    gate.add_argument("path", type=Path)
    gate.add_argument("--output", type=Path)
    rotation = commands.add_parser("t3", help="Validate genuine x/y dumps for offline CSO rotation")
    rotation.add_argument("--manifest", type=Path, required=True)
    rotation.add_argument("--x", type=Path, required=True)
    rotation.add_argument("--y", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init-null":
            print(initialize(args.root, args.ref, args.dump_c, args.dump_p))
            return 0
        if args.command == "finish":
            result = finish(args.manifest, args.kind)
            print(json.dumps({k: v for k, v in result.items() if k != "files"}, indent=2))
            return 0 if result["passed"] else 1
        if args.command == "trace":
            result = trace_null(args.manifest)
            print(json.dumps({k: v for k, v in result.items() if k != "per_k_eV"}, indent=2))
            return 0 if all(g["passed"] for g in result["gates"].values()) else 1
        if args.command == "t3":
            result = t3(args.manifest, args.x, args.y)
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] else 1
        if args.command == "status":
            campaign = manifest.load(args.manifest)
            result = {"acceptance": campaign["acceptance"], "runs": {}}
            for kind, record in campaign["runs"].items():
                result["runs"][kind] = "DONE" if record["passed"] else record.get("error", "FAILED")
            print(json.dumps(result, indent=2))
            return 0
        if args.name == "c0":
            result = gate_c0(load_cso(args.path)).to_dict()
        else:
            cp = load_cproj(args.path)
            result = {"name": "W0", "passed": True, "records": cp.header.nkpts_global * cp.header.nbands_global}
            if args.name == "m1":
                result = gate_m1(cp, load_ferwe(args.path), load_cocc(args.path / "COCC.dat")).to_dict()
        if args.output:
            manifest.save(result, args.output)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    except (OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
