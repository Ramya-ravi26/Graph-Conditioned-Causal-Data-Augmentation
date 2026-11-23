"""How many strong edges of the discrete benchmark networks are non-monotone?

For every true edge of Asia, Insurance and Alarm (training draw, seed 10,000, n = 8000)
compare Cramer's V (any dependence) with |Spearman rho| on the category indices
(monotone dependence along the category order, the only kind a copula on jittered
pseudo-observations can represent). An edge counts as strong if V > 0.2 and as
non-monotone if |rho_s| < V / 2.

    python scripts/nonmonotone_edges.py [--out outputs/experiments/rf/nonmonotone_edges.csv]
"""

import argparse
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

from gcda.data.registry import load_dataset
from gcda.evaluation.discrete import cramers_v
from gcda.experiments.rq6 import GRAPHS, TRAIN_SEED

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("outputs/experiments/rf/nonmonotone_edges.csv"))
    a = p.parse_args()
    rows = []
    for g in ("asia", "insurance", "alarm"):
        df, dag, orders = load_dataset(g, n=GRAPHS[g]["n"], seed=TRAIN_SEED)
        for u, v in dag.edges:
            codes = {c: pd.Categorical(df[c], categories=orders[c]).codes for c in (u, v)}
            rho = spearmanr(codes[u], codes[v])[0]
            V = cramers_v(df[u], df[v])
            rows.append({"graph": g, "parent": u, "child": v, "cramers_v": V, "abs_spearman": abs(rho),
                         "strong": V > 0.2, "non_monotone": V > 0.2 and abs(rho) < V / 2})
    res = pd.DataFrame(rows)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(a.out, index=False)
    s = res.groupby("graph").agg(edges=("child", "size"), strong=("strong", "sum"), non_monotone=("non_monotone", "sum"))
    s["share_of_strong_%"] = (100 * s.non_monotone / s.strong).round(0)
    print(s.loc[["asia", "insurance", "alarm"]].to_string())
