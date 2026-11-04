"""Command line for dump gates, T3 and offline Step 1 diagnostics."""

import argparse
import json
from pathlib import Path
import sys

from . import manifest
from .cso import t3
from .dumpio import load_cocc, load_cproj, load_cso, load_ferwe
from . import step1
from .gates import gate_c0, gate_m1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Patch B dump checks and Step 1 diagnostics")
    commands = parser.add_subparsers(dest="command", required=True)
    gate = commands.add_parser("gate", help="Inspect one dump")
    gate.add_argument("name", choices=("c0", "w0", "m1"))
    gate.add_argument("path", type=Path)
    gate.add_argument("--output", type=Path)
    rotation = commands.add_parser("t3", help="Validate genuine x/y dumps for offline CSO rotation")
    for name in ("z", "x", "y", "output"):
        rotation.add_argument("--" + name, type=Path, required=True)
    prepare = commands.add_parser("step1-prepare", help="Prepare lab targets and optional shared VASP inputs (no VASP jobs)")
    prepare.add_argument("--recipe", type=Path, required=True)
    material = prepare.add_mutually_exclusive_group(required=True)
    material.add_argument("--poscar", type=Path)
    material.add_argument("--inputs", type=Path, help="Shared directory with POSCAR, INCAR, KPOINTS and POTCAR")
    prepare.add_argument("--job-template", type=Path, help="Explicit launch script for --inputs; copied unchanged as job.sh")
    prepare.add_argument("--output", type=Path, required=True)
    wrap = commands.add_parser("step1-wrap-partner", help="Shift prepared negative q without regenerating targets")
    wrap.add_argument("--config", type=Path, required=True)
    wrap.add_argument("--q-frac", type=float, nargs=3, required=True)
    wrap.add_argument("--output", type=Path, required=True)
    state = commands.add_parser("step1-read", help="Read converged sphere moments and gate realization")
    state.add_argument("--config", type=Path, required=True)
    state.add_argument("--run", type=Path, required=True)
    state.add_argument("--references", type=Path, required=True,
                       help="JSON: M_int and MW_int reference norms in magnetic-site order")
    state.add_argument("--common-z", action="store_true")
    state.add_argument("--output", type=Path, required=True)
    row = commands.add_parser("step1-row", help="Two measured sides and supplied canonical bond basis")
    for name in ("plus", "minus", "basis", "traces", "output"):
        row.add_argument("--" + name, type=Path, required=True)
    solver = commands.add_parser("step1-fit", help="Diagnostic weighted solve; not production acceptance")
    solver.add_argument("--rows", type=Path, required=True)
    solver.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "step1-prepare":
            record = step1.prepare(manifest.load(args.recipe), args.inputs / "POSCAR" if args.inputs else args.poscar)
            step1.write_inputs(record, args.output, args.inputs, args.job_template)
            print(args.output / "config.json")
            if args.inputs and args.job_template is None:
                print("No --job-template supplied; inputs prepared for review only.", file=sys.stderr)
            return 0
        if args.command == "step1-wrap-partner":
            record = step1.wrap_partner(manifest.load(args.config), args.q_frac)
            step1.write_inputs(record, args.output)
            print(args.output / "config.json")
            return 0
        if args.command == "step1-read":
            value = step1.read_and_gate(args.config, args.run, args.references, args.output, args.common_z)
            gate = value["gate"]
            print(json.dumps({"passed": gate["passed"], "reasons": gate["reasons"]}, indent=2))
            return 0 if gate["passed"] else 1
        if args.command == "step1-row":
            traces = manifest.load(args.traces)
            if traces.get("axis") != manifest.load(args.plus)["config"]["axis"]:
                raise ValueError("Trace operator axis must match design-row axis")
            result = step1.paired(manifest.load(args.plus), manifest.load(args.minus),
                                  manifest.load(args.basis)["bonds"], traces["plus_eV"],
                                  traces["minus_eV"], traces.get("sigma_y_eV_per_site"))
            result["trace_source"] = traces.get("source", "unverified")
            manifest.save(result, args.output)
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "step1-fit":
            result = step1.fit(manifest.load(args.rows)["rows"])
            manifest.save(result, args.output)
            print(json.dumps(result, indent=2))
            return 0
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
