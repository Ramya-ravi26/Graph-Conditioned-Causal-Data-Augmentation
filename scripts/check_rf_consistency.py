"""Check that the non-forest rows of the RF prototype equal the RQ6 cluster runs.

The RF experiment re-generates true_data, baseline_fixed_rho, learned and cpt_refit with
the RQ6 code and seeds, so for every (graph, seed, source) present in both, SHD /
edges found / skeleton F1 must be identical. Any difference means the comparison
learned_rf vs. the rest is not like-for-like.

    python scripts/check_rf_consistency.py outputs/experiments/rf/<run>/rf_per_seed.csv
"""

import sys
from pathlib import Path

import pandas as pd

HPC = Path("outputs/experiments/hpc")


def main(path: str) -> int:
    rf = pd.read_csv(path)
    bad = checked = 0
    for alg in ("pc", "ges"):
        if f"shd_{alg}" not in rf:
            continue
        ref = pd.read_csv(HPC / f"rq6_{alg}" / "merged" / "rq6_heldout_per_seed.csv")
        m = rf.merge(ref, on=["graph", "seed", "source"], how="inner")
        for col in ("shd", "n_edges_found", "skeleton_f1"):
            diff = m[~((m[f"{col}_{alg}"] - m[col]).abs() < 1e-9)]
            checked += len(m)
            bad += len(diff)
            if len(diff):
                print(f"MISMATCH {alg} {col}:\n", diff[["graph", "seed", "source", f"{col}_{alg}", col]].to_string(index=False))
        print(f"{alg}: {len(m)} (graph, seed, source) rows compared against the cluster run")
    print("OK: identical to the RQ6 cluster runs" if bad == 0 and checked else "FAILED" if bad else "nothing to compare")
    return 1 if bad or not checked else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
