"""Command line: plan, prepare, collect, dumps and fit (math Section 12).

Every command reads the VASP files again; JSON files other than plan.json and
config.json are reports, never inputs (D-021).
"""

import argparse
from pathlib import Path
import sys

from . import spiral, tensors

COMMANDS = {
    "plan": "Print the symmetry summary and the checked q plan; writes nothing",
    "prepare": "Write every F0 run, runs.txt and submit.sh; submits nothing",
    "collect": "Print one status line per run; writes collected.json as a report",
    "dumps": "Write dump_C and every ok run's dump_P; submits nothing",
    "fit": "Trace every ok run, apply C0, N0, I0, P0 and E0, fit D and A, check the forbidden "
           "part and predict the spiral; writes traces.json and tensors.json",
}


def plan_lines(summary) -> list[str]:
    """Plan report; the space-group line comes first (D-017)."""
    ops, tags, ranks = summary["ops"], summary["incar"], summary["ranks"]
    lines = [f"space group {ops['number']} ({ops['symbol']}) at symprec {summary['symprec']:g}: "
             f"{ops['total']} operations, "
             f"{ops['total'] - ops['dropped']} kept, {ops['dropped']} dropped",
             f"p_D {summary['p_D']}  p_A {summary['p_A']}  n_twist {summary['n_twist']}"]
    shown = [f"{key} {tags[key]}" for key in ("ENCUT", "ENINI", "ISMEAR", "SIGMA") if key in tags]
    if shown:
        lines.append("  ".join(shown))
    lines += summary["overrides"]
    lines.append(f"directions (q_frac)  rank D {ranks['D']:.3f}  A {ranks['A']:.3f}  D_free {ranks['D_free']:.3f}")
    lines += [f"  d{i}  " + " ".join(f"{x:g}" for x in d) for i, d in enumerate(summary["directions"], 1)]
    if ranks["D_free"] < spiral.RANK_FLOOR:
        lines.append("D_free is not determined: the forbidden part will not be evaluated")
    lines.append(f"{len(summary['points'])} runs including q0")
    return lines


def run(args) -> int:
    """Run one command; the exit code is 1 when any run or check fails."""
    if args.command in ("plan", "prepare"):
        seed = spiral.load_seed(args.seed)
        print("\n".join(plan_lines(spiral.plan(seed))))
        if args.command == "prepare":
            runs = spiral.prepare(seed, args.out, args.job)
            print(f"wrote {len(runs)} runs; submit from {args.out} with: sbatch submit.sh")
        return 0
    if args.command == "collect":
        results = spiral.collect(args.out)
        for name, value in results.items():
            print(f"{name:16} {value.get('error', 'ok')}")
        return 0 if all("error" not in value for value in results.values()) else 1
    if args.command == "dumps":
        dumps, skipped = spiral.prepare_dumps(args.out, args.job)
        for name, error in skipped.items():
            print(f"{name:16} no dump: {error}")
        print(f"wrote {len(dumps)} dumps; submit from {args.out} with: sbatch submit_dumps.sh")
        return 0
    report = tensors.fit(args.out)
    print("\n".join(report["lines"]))
    return 0 if report["passed"] else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Spin-spiral workflow for the spiralization and stiffness tensors")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in COMMANDS.items():
        sub = commands.add_parser(name, help=text)
        sub.add_argument("seed" if name in ("plan", "prepare") else "out", type=Path)
        if name in ("prepare", "dumps"):
            sub.add_argument("--job", type=Path, required=True,
                             help="Slurm template that runs VASP in its directory (Patch B build for dumps)")
        if name == "prepare":
            sub.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
