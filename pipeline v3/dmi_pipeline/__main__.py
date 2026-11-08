"""Command line: the spiral workflow, dump gates and T3."""

import argparse
import json
from pathlib import Path
import sys

from . import manifest
from .cso import t3
from .dumpio import load_cocc, load_cproj, load_cso, load_ferwe
from . import spiral
from .gates import gate_c0, gate_m1


def plan_lines(summary) -> list[str]:
    """Plan report; the space-group line comes first (D-017)."""
    ops, tags = summary["ops"], summary["incar"]
    lines = [f"space group {ops['number']} ({ops['symbol']}) at symprec {summary['symprec']:g}: "
             f"{ops['total']} operations, "
             f"{ops['total'] - ops['dropped']} kept, {ops['dropped']} dropped",
             f"p_D {summary['p_D']}  p_A {summary['p_A']}  n_twist {summary['n_twist']}",
             f"ENCUT {tags['ENCUT']}  ENINI {tags['ENINI']}",
             f"directions (q_frac)  sigma_D {summary['sigma_D']:.3f}  sigma_A {summary['sigma_A']:.3f}"]
    lines += [f"  d{i}  " + " ".join(f"{x:g}" for x in d) for i, d in enumerate(summary["directions"], 1)]
    lines.append(f"{len(summary['points'])} runs including q0")
    if summary["classes"] is not None:
        lines.append(f"exchange classes: {summary['classes']}")
    return lines


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Spin-spiral workflow and Patch B dump checks")
    commands = parser.add_subparsers(dest="command", required=True)
    gate = commands.add_parser("gate", help="Inspect one dump")
    gate.add_argument("name", choices=("c0", "w0", "m1"))
    gate.add_argument("path", type=Path)
    gate.add_argument("--output", type=Path)
    rotation = commands.add_parser("t3", help="Validate genuine x/y dumps for offline CSO rotation")
    for name in ("z", "x", "y", "output"):
        rotation.add_argument("--" + name, type=Path, required=True)
    for name, text in (("plan", "Print the symmetry summary and the checked q plan; writes nothing"),
                       ("prepare", "Write every F0 run, runs.txt and submit.sh; submits nothing"),
                       ("collect", "Read E and M_int from every finished run into collected.json")):
        sub = commands.add_parser(name, help=text)
        sub.add_argument("seed" if name != "collect" else "out", type=Path)
        if name == "prepare":
            sub.add_argument("--job", type=Path, required=True, help="Slurm template that runs VASP in its directory")
            sub.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            print("\n".join(plan_lines(spiral.plan(spiral.load_seed(args.seed)))))
            return 0
        if args.command == "prepare":
            seed = spiral.load_seed(args.seed)
            print("\n".join(plan_lines(spiral.plan(seed))))
            runs = spiral.prepare(seed, args.out, args.job)
            print(f"wrote {len(runs)} runs; submit from {args.out} with: sbatch submit.sh")
            return 0
        if args.command == "collect":
            results = spiral.collect(args.out)
            for name, value in results.items():
                print(f"{name:16} {value.get('error', 'ok')}")
            return 0 if all("error" not in value for value in results.values()) else 1
        if args.command == "t3":
            result = t3(args.z, args.x, args.y)
            manifest.save(result, args.output)
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] else 1
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
