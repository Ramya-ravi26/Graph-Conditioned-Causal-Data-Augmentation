"""RQ4 (held-out, multi-seed): reconstruct discrete / mixed networks.

Library fitted once on a training draw (seed 10,000); each evaluation seed
draws independent true data. Sources: fixed-rho baseline (real marginals),
learned with jittered discrete columns (thesis method), learned with the
native discrete likelihood, the same two with margin calibration, and CPT
refitting. Metrics: mean category-frequency TVD over nodes, mean |Cramer's V
error| and |NMI error| over the true edges, fallback draws.
"""

import pandas as pd

from gcda.data.registry import load_dataset
from gcda.evaluation.discrete import compare_category_frequencies, compare_discrete_dependence
from gcda.experiments.common import (
    baseline_specs, cpt_refit_sample, fit_graph_library, learned_specs, paired_comparison, sample, summarize,
)

TRAIN_SEED = 10_000


def run_network(name: str, seeds: list[int], n: int = 10000) -> pd.DataFrame:
    train, dag, orders = load_dataset(name, n=n, seed=TRAIN_SEED)
    lib_j = fit_graph_library(train, dag, orders, name, discrete_mode="jitter")
    lib_n = fit_graph_library(train, dag, orders, name, discrete_mode="native")
    discrete_cols = [c for c in dag.nodes if orders and c in orders]
    rows = []
    for seed in seeds:
        true, _, _ = load_dataset(name, n=n, seed=seed)
        sources = {
            "baseline_fixed_rho": sample(dag, baseline_specs(lib_j, name, dag), n, seed)[0],
            "learned_jitter": sample(dag, learned_specs(lib_j, name, dag), n, seed)[0],
            "learned_native": sample(dag, learned_specs(lib_n, name, dag), n, seed)[0],
            "learned_native_calibrated": sample(dag, learned_specs(lib_n, name, dag), n, seed, calibrate=True)[0],
            "baseline_calibrated": sample(dag, baseline_specs(lib_j, name, dag), n, seed, calibrate=True)[0],
        }
        if len(discrete_cols) == len(dag.nodes):
            sources["cpt_refit"] = cpt_refit_sample(train, dag, n, seed)
        edges = [e for e in dag.edges if e[0] in discrete_cols and e[1] in discrete_cols]
        for label, sim in sources.items():
            freq = compare_category_frequencies(true[discrete_cols], sim[discrete_cols])
            dep = compare_discrete_dependence(true, sim, pairs=edges) if edges else pd.DataFrame()
            rows.append({
                "network": name, "seed": seed, "source": label,
                "mean_tvd": freq["total_variation_distance"].mean(),
                "mean_cramers_v_abs_err": dep["cramers_v_abs_error"].mean() if len(dep) else float("nan"),
                "mean_nmi_abs_err": dep["nmi_abs_error"].mean() if len(dep) else float("nan"),
            })
        print(f"  rq4 {name} seed {seed} done")
    return pd.DataFrame(rows)


def main(out_dir, networks: list[str], n_seeds: int, seed_start: int = 0) -> None:
    from pathlib import Path

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seeds = list(range(seed_start, seed_start + n_seeds))
    res = pd.concat([run_network(nw, seeds) for nw in networks], ignore_index=True)
    write_outputs(res, out_dir, networks=networks, seeds=seeds, train_seed=TRAIN_SEED)


def write_outputs(res: pd.DataFrame, out_dir, **meta) -> None:
    from pathlib import Path

    from gcda.provenance import write_metadata

    out_dir = Path(out_dir)
    summ = pd.concat([summarize(res, ["network", "source"], m).assign(metric=m)
                      for m in ["mean_tvd", "mean_cramers_v_abs_err", "mean_nmi_abs_err"]])
    tests = []
    for nw, g in res.groupby("network"):
        for m in ["mean_tvd", "mean_cramers_v_abs_err"]:
            w = g.pivot(index="seed", columns="source", values=m)
            for other in ["learned_jitter", "baseline_fixed_rho", "cpt_refit"]:
                if other in w and "learned_native" in w:
                    tests.append({"network": nw, "metric": m, "comparison": f"learned_native - {other}",
                                  **paired_comparison(w["learned_native"], w[other])})
    tests = pd.DataFrame(tests)
    for fname, frame in [("rq4_heldout_per_seed.csv", res), ("rq4_heldout_summary.csv", summ), ("rq4_heldout_tests.csv", tests)]:
        frame.to_csv(out_dir / fname, index=False)
        write_metadata(out_dir / fname, **meta)
    with pd.option_context("display.width", 220):
        print(summ.round(4).to_string(index=False))
        print(tests.round(4).to_string(index=False))
