"""POST-1 acceptance check A2 (plans/post-1.md; D-030).

Compares the COCC.dat an SCF wrote when it ended (LDUMPCOCC_POST) with the
COCC.dat an old-style dump_P wrote from that run's WAVECAR, and the trace
vector each gives with the material CSO. Usage:

    python acceptance/compare_cocc.py RUN dump_C/CSO.dat

Prints the largest |difference| with its index, and T from each file. It
applies no threshold: the bounds are in the spec. The WAVECAR is single
precision, so the two files are expected to differ near 1e-7.
"""

from pathlib import Path
import sys

import numpy as np

from dmi_pipeline.dumpio import POST_LOOP, load_cocc, load_cso
from dmi_pipeline.trace import split_operator, trace_vector


def compare(run, cso_path):
    """(largest |difference|, its 1-based (IS, ION, I, J), T from the SCF file, T from dump_P), T in eV."""
    run = Path(run)
    post, pre = load_cocc(run / "COCC.dat"), load_cocc(run / "dump_P" / "COCC.dat")
    if post.metadata.label != POST_LOOP or pre.metadata.label == POST_LOOP:
        raise ValueError(f"need an SCF dump in {run} and a PRE_LOOP dump in {run / 'dump_P'}; "
                         f"found {post.metadata.label!r} and {pre.metadata.label!r}")
    if post.matrix.shape != pre.matrix.shape:
        raise ValueError(f"the two COCC files differ in shape: {post.matrix.shape} and {pre.matrix.shape}")
    diff = np.abs(post.matrix - pre.matrix)
    where = tuple(int(i) + 1 for i in np.unravel_index(np.argmax(diff), diff.shape))
    lam = split_operator(load_cso(cso_path))
    t_post, t_pre = (trace_vector(cocc, lam).real.sum(axis=0) for cocc in (post, pre))
    return float(diff.max()), where, t_post, t_pre


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python acceptance/compare_cocc.py RUN CSO.dat")
    worst, where, t_post, t_pre = compare(*sys.argv[1:])
    print(f"max |COCC(SCF) - COCC(dump_P)| = {worst:.3e} at (IS, ION, I, J) = {where}")
    for label, t in (("T from the SCF dump", t_post), ("T from dump_P     ", t_pre), ("difference        ", t_post - t_pre)):
        print(f"{label} " + " ".join(f"{x:+.9e}" for x in t) + " eV")
