"""RQ1 (quantitative): do strong fitted pairwise dependencies coincide with known causal edges?

Ranks all 55 Sachs variable pairs by |tau| of the fitted pairwise copula and
scores the ranking against the skeleton of the Sachs consensus network
(bnlearn/pgmpy, 17 edges): AUROC (with the Mann-Whitney p-value),
precision@k, and the rank of praf-pmek. Run on the pooled 7,466 rows and on
the 853-row observational (CD3/CD28) condition.
"""

from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from sklearn.metrics import roc_auc_score

from gcda.data.datasets import load_sachs, sachs_consensus_dag
from gcda.data.preprocessing import to_pseudo_observations
from gcda.dependency.pairwise import build_pairwise_library


def score(observational_only: bool) -> tuple[dict, pd.DataFrame]:
    df = load_sachs(observational_only=observational_only)
    u, _ = to_pseudo_observations(df)
    entries = build_pairwise_library(u, "sachs", n_jobs=4)
    skeleton = {frozenset(e) for e in sachs_consensus_dag().edges}
    rows = [{"var_i": e["var_i"], "var_j": e["var_j"], "family": e["family"], "tau": e["tau"],
             "abs_tau": abs(e["tau"]), "consensus_edge": frozenset((e["var_i"], e["var_j"])) in skeleton}
            for e in entries if "error" not in e]
    pairs = pd.DataFrame(rows).sort_values("abs_tau", ascending=False).reset_index(drop=True)
    y, s = pairs["consensus_edge"].to_numpy(), pairs["abs_tau"].to_numpy()
    k_true = int(y.sum())
    res = {
        "rows": len(df), "n_pairs": len(pairs), "n_consensus_edges": k_true,
        "auroc": roc_auc_score(y, s),
        "mannwhitney_p": mannwhitneyu(s[y], s[~y], alternative="greater").pvalue,
        **{f"precision_at_{k}": float(y[:k].mean()) for k in (3, 5, 10, k_true)},
        "random_precision": k_true / len(pairs),
        "rank_praf_pmek": int(pairs.index[(pairs.var_i.isin(["praf", "pmek"])) & (pairs.var_j.isin(["praf", "pmek"]))][0]) + 1,
    }
    return res, pairs


def main(out_dir) -> None:
    from pathlib import Path

    from gcda.provenance import write_metadata

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for obs in (False, True):
        tag = "observational" if obs else "pooled"
        res, pairs = score(obs)
        summary.append({"data": tag, **res})
        pairs.to_csv(out_dir / f"rq1_sachs_pairs_{tag}.csv", index=False)
        print(f"--- {tag} ---")
        print(pairs.head(10).to_string(index=False))
    s = pd.DataFrame(summary)
    s.to_csv(out_dir / "rq1_summary.csv", index=False)
    write_metadata(out_dir / "rq1_summary.csv")
    print(s.round(4).T.to_string())
