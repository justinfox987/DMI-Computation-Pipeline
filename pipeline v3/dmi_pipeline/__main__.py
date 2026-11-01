"""Command line for historical N0 and offline Step 1 diagnostics."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

from . import campaign, manifest, runner
from .dumpio import load_cocc, load_cproj, load_cso, load_ferwe
from . import step1
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
    prepare = commands.add_parser("step1-prepare", help="Prepare lab targets and optional shared VASP inputs (no VASP jobs)")
    prepare.add_argument("--recipe", type=Path, required=True)
    material = prepare.add_mutually_exclusive_group(required=True)
    material.add_argument("--poscar", type=Path)
    material.add_argument("--inputs", type=Path, help="Shared directory with POSCAR, INCAR, KPOINTS and POTCAR")
    prepare.add_argument("--job-template", type=Path, help="Explicit launch script for --inputs; copied unchanged as job.sh")
    prepare.add_argument("--output", type=Path, required=True)
    campaign_prepare = commands.add_parser("campaign-prepare", help="Expand and validate a campaign without submitting jobs")
    campaign_prepare.add_argument("--campaign", type=Path, required=True)
    campaign_plan = commands.add_parser("campaign-plan", help="Inspect a prepared root or validate a campaign without writing")
    plan_source = campaign_plan.add_mutually_exclusive_group(required=True)
    plan_source.add_argument("--root", type=Path)
    plan_source.add_argument("--campaign", type=Path)
    campaign_reference = commands.add_parser("campaign-reference", help="Verify a completed independent q0 reference against campaign cases")
    campaign_reference.add_argument("--root", type=Path, required=True)
    campaign_reference.add_argument("--run", type=Path, help="Completed q0 run; defaults to prepared generated reference")
    campaign_reference.add_argument("--config", type=Path, help="Explicit q0 config or magnetic_indices mapping for an imported run")
    campaign_reference.add_argument("--output", type=Path, help="Must be ROOT/reference when provided")
    submit = commands.add_parser("campaign-submit", help="Preview or confirm ordinary Slurm submission")
    submit.add_argument("--root", type=Path, required=True)
    submit.add_argument("--max-concurrent", type=int)
    submit.add_argument("--yes", action="store_true", help="Explicitly allow input staging and sbatch")
    submit.add_argument("--clear-stale-lock", action="store_true", help="Only after verifying no other writer is active")
    resume = commands.add_parser("campaign-resume", help="Reconcile jobs; optionally confirm new submissions")
    resume.add_argument("--root", type=Path, required=True)
    resume.add_argument("--retry", action="store_true", help="Permit new attempt after a recorded failure")
    resume.add_argument("--yes", action="store_true", help="Explicitly allow staging and sbatch")
    resume.add_argument("--clear-stale-lock", action="store_true")
    campaign_status = commands.add_parser("campaign-status", help="Reconcile and show individual case results")
    campaign_status.add_argument("--root", type=Path, required=True)
    campaign_status.add_argument("--json", action="store_true")
    campaign_status.add_argument("--clear-stale-lock", action="store_true")
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
        if args.command == "campaign-prepare":
            plan = campaign.prepare(args.campaign)
            print(f"Prepared {plan['run_count']} runs")
            return 0
        if args.command == "campaign-plan":
            if args.root is not None:
                plan = manifest.load(args.root / "plan.json")
                if plan.get("schema") != campaign.PLAN_SCHEMA:
                    raise ValueError("Expected dmi-plan-1 in prepared root")
            else:
                plan = campaign.build_plan(args.campaign)[0]
            print(json.dumps({key: plan[key] for key in ("run_count", "cases", "pairs", "reference")}, indent=2))
            return 0
        if args.command == "campaign-reference":
            differences = campaign.check_reference(args.root, args.run, args.config, args.output)
            if differences:
                for difference in differences:
                    print(f"BLOCK: {difference}")
                return 1
            print("PASS: independent q0 reference compatible with every consuming case")
            return 0
        if args.command == "campaign-submit":
            runner.submit(args.root, max_concurrent=args.max_concurrent, yes=args.yes,
                          clear_stale_lock=args.clear_stale_lock)
            return 0
        if args.command == "campaign-resume":
            runner.resume(args.root, retry=args.retry, yes=args.yes, clear_stale_lock=args.clear_stale_lock)
            return 0
        if args.command == "campaign-status":
            runner.status(args.root, json_output=args.json, clear_stale_lock=args.clear_stale_lock)
            return 0
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
            null_manifest = manifest.load(args.manifest)
            result = {"acceptance": null_manifest["acceptance"], "runs": {}}
            for kind, record in null_manifest["runs"].items():
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
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
