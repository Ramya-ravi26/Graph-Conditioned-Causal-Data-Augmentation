"""Merge per-seed results of Slurm array tasks and recompute summaries/tests.

    python scripts/merge_results.py rq6 outputs/hpc/rq6/task_* --out outputs/hpc/rq6/merged
    python scripts/merge_results.py rq4 outputs/hpc/rq4/task_* --out outputs/hpc/rq4/merged
    python scripts/merge_results.py rf outputs/hpc/rf_pc/task_* --out outputs/hpc/rf_pc/merged
"""

import argparse
from pathlib import Path

import pandas as pd

FILES = {"rq6": "rq6_heldout_per_seed.csv", "rq4": "rq4_heldout_per_seed.csv", "rf": "rf_per_seed.csv"}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("experiment", choices=sorted(FILES))
    p.add_argument("dirs", nargs="+", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    frames = [pd.read_csv(d / FILES[a.experiment]) for d in a.dirs if (d / FILES[a.experiment]).exists()]
    res = pd.concat(frames, ignore_index=True).drop_duplicates()
    key = ["graph", "seed", "source"] if a.experiment in ("rq6", "rf") else ["network", "seed", "source"]
    dup = res.duplicated(key).sum()
    if dup:
        raise SystemExit(f"{dup} duplicated (graph/network, seed, source) rows across tasks")
    a.out.mkdir(parents=True, exist_ok=True)
    if a.experiment == "rf":
        from gcda.experiments.rf_eval import write_outputs
    elif a.experiment == "rq6":
        from gcda.experiments.rq6 import write_outputs
    else:
        from gcda.experiments.rq4 import write_outputs
    write_outputs(res, a.out, merged_from=[str(d) for d in a.dirs])
    print(f"merged {len(frames)} task directories, {res['seed'].nunique()} seeds")
