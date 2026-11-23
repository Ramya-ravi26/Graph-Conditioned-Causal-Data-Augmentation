"""Integrity and cross-machine checks for the Lichtenberg results in outputs/experiments/hpc/.

    python scripts/check_hpc_results.py

1. completeness: every (graph/network, source) has the expected number of seeds/DAGs, no duplicates;
2. merge integrity: each merged file equals the concatenation of its array-task files;
3. cross-machine identity: every seed/DAG that also exists in the workstation results
   (outputs/experiments/...) has identical values;
4. L1 Sachs validation and L2 sweep reproduction.
Exit code 1 if any check fails.
"""

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
L, H = ROOT / "outputs" / "experiments", ROOT / "outputs" / "experiments" / "hpc"
fail = 0


def report(ok, msg):
    global fail
    print(("OK    " if ok else "FAIL  ") + msg)
    fail += 0 if ok else 1


def complete(name, path, group, seed_col, n):
    d = pd.read_csv(H / path)
    counts = d.groupby(group)[seed_col].nunique()
    report(bool((counts == n).all()) and not d.duplicated([*group, seed_col]).any(),
           f"{name}: {len(counts)} groups x {n} {seed_col}s, no duplicates")
    return d


def merged_equals_tasks(name, merged, pattern, key):
    m = pd.read_csv(H / merged)
    t = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(str(H / pattern)))])
    a = t.sort_values(key).reset_index(drop=True)
    b = m.sort_values(key).reset_index(drop=True)[t.columns]
    num = a.select_dtypes("number").columns
    ok = len(a) == len(b) and np.allclose(a[num].to_numpy(float), b[num].to_numpy(float), equal_nan=True)
    report(ok, f"{name}: merged == concat(task files) ({len(t)} rows)")


def same_as_local(name, local, hpc, key, cols):
    a, b = pd.read_csv(L / local), pd.read_csv(H / hpc)
    m = a.merge(b, on=key, suffixes=("_l", "_h"))
    bad = sum(int((~np.isclose(m[c + "_l"].astype(float), m[c + "_h"].astype(float), equal_nan=True)).sum()) for c in cols)
    report(len(m) == len(a) and bad == 0, f"{name}: {len(m)}/{len(a)} workstation rows found, {bad} mismatched values")


complete("RQ6 PC", "rq6_pc/merged/rq6_heldout_per_seed.csv", ["graph", "source"], "seed", 100)
complete("RQ6 GES", "rq6_ges/merged/rq6_heldout_per_seed.csv", ["graph", "source"], "seed", 100)
complete("RQ4", "rq4/merged/rq4_heldout_per_seed.csv", ["network", "source"], "seed", 50)
complete("RQ2", "rq2_100/rq2_heldout_per_seed.csv", ["source"], "seed", 100)
for tag in ("pooled", "observational"):
    complete(f"novel {tag}", f"novel_dags/merged/novel_dags_{tag}_per_dag.csv", ["generator", "calibrated"], "dag", 200)
complete("learned indegree", "learned_indegree/learned_indegree_per_edge.csv", ["network", "mode", "child", "parent"], "seed", 10)

merged_equals_tasks("RQ6 PC", "rq6_pc/merged/rq6_heldout_per_seed.csv", "rq6_pc/task_*/rq6_heldout_per_seed.csv", ["graph", "source", "seed"])
merged_equals_tasks("RQ6 GES", "rq6_ges/merged/rq6_heldout_per_seed.csv", "rq6_ges/task_*/rq6_heldout_per_seed.csv", ["graph", "source", "seed"])
merged_equals_tasks("RQ4", "rq4/merged/rq4_heldout_per_seed.csv", "rq4/task_*/rq4_heldout_per_seed.csv", ["network", "source", "seed"])
for tag in ("pooled", "observational"):
    merged_equals_tasks(f"novel {tag}", f"novel_dags/merged/novel_dags_{tag}_per_dag.csv",
                        f"novel_dags/task_*/novel_dags_{tag}_per_dag.csv", ["generator", "calibrated", "dag"])

k6, c6 = ["graph", "seed", "source"], ["shd", "n_edges_found", "skeleton_f1"]
same_as_local("RQ6 SCM+Asia", "rq6_small/rq6_heldout_per_seed.csv", "rq6_pc/merged/rq6_heldout_per_seed.csv", k6, c6)
same_as_local("RQ6 Insurance", "rq6_insurance/rq6_heldout_per_seed.csv", "rq6_pc/merged/rq6_heldout_per_seed.csv", k6, c6)
same_as_local("RQ6 Alarm", "rq6_alarm/rq6_heldout_per_seed.csv", "rq6_pc/merged/rq6_heldout_per_seed.csv", k6, c6)
k4, c4 = ["network", "seed", "source"], ["mean_tvd", "mean_cramers_v_abs_err", "mean_nmi_abs_err"]
same_as_local("RQ4 Asia+mixed", "rq4_small/rq4_heldout_per_seed.csv", "rq4/merged/rq4_heldout_per_seed.csv", k4, c4)
same_as_local("RQ4 Insurance", "rq4_insurance/rq4_heldout_per_seed.csv", "rq4/merged/rq4_heldout_per_seed.csv", k4, c4)
same_as_local("RQ2", "rq2_heldout_per_seed.csv", "rq2_100/rq2_heldout_per_seed.csv", ["seed", "source"],
              ["mean_edge_tau_abs_error", "mean_marginal_ks", "energy_distance", "gaussian_mmd"])
for tag in ("pooled", "observational"):
    same_as_local(f"novel {tag}", f"novel_dags_{tag}_per_dag.csv", f"novel_dags/merged/novel_dags_{tag}_per_dag.csv",
                  ["dag", "generator", "calibrated"], ["shd", "skeleton_f1", "mean_marginal_ks", "varsortability"])
same_as_local("learned indegree", "learned_indegree_v2/learned_indegree_per_edge.csv",
              "learned_indegree/learned_indegree_per_edge.csv", ["network", "seed", "mode", "child", "parent"],
              ["cramers_v_sim", "tau_sim"])

sachs = (H / "sachs_validation.txt").read_text().strip()
report(sachs.startswith("853/853"), f"L1 Sachs validation: '{sachs}'")
repro = sorted(H.glob("repro_*/sweep/sweep_dependency_models.csv"))
if repro:
    a, b = pd.read_csv(repro[0]), pd.read_csv(ROOT / "outputs" / "sweep_dependency_models.csv")
    ok = np.allclose(a.vine_aic, b.vine_aic, atol=1e-6) and (a.families_selected == b.families_selected).all()
    report(ok, f"L2 rebuild: sweep table reproduced ({repro[0].parent.parent.name})")
else:
    report(False, "L2 rebuild: no repro_*/sweep directory")
print(f"\n{fail} check(s) failed")
sys.exit(1 if fail else 0)
