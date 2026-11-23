"""Prototype evaluation: random-forest conditionals vs. the copula generator.

Same held-out protocol, seeds, sample sizes and baselines as gcda/experiments/rq6.py
(library and forests fitted once on the training draw, seed 10,000; evaluation seeds
0..n-1), plus the source ``learned_rf``: every non-root node is sampled from a
ForestConditional fitted on the training draw, roots keep their marginal. For each
seed and source it records

* discovery: SHD / edges found / skeleton F1 of PC and (optionally) GES,
* fidelity (discrete graphs): mean category TVD and mean |Cramer's V error| over
  the true edges, as in RQ4; (continuous graph): mean |tau error| over the edges.

Writes to outputs/experiments/rf/ only. Because the non-forest sources use exactly
the code and seeds of the RQ6 cluster runs, their rows must be identical to
outputs/experiments/hpc/rq6_*/merged (checked by scripts/check_rf_consistency.py).
"""

import time
import warnings

import pandas as pd
from scipy.stats import kendalltau

from gcda.data.preprocessing import to_pseudo_observations_mixed
from gcda.data.registry import load_dataset
from gcda.dependency.forest import ForestConditional
from gcda.evaluation.causal_discovery import encode_categorical, run_ges, run_pc, structural_hamming_distance
from gcda.evaluation.discrete import compare_category_frequencies, compare_discrete_dependence
from gcda.experiments.common import (
    baseline_specs, cpt_refit_sample, fit_graph_library, learned_specs, paired_comparison, sample,
    skeleton_scores, summarize,
)
from gcda.experiments.rq6 import GRAPHS, TRAIN_SEED
from gcda.generation.graph_sampler import EdgeModel, NodeSpec


def forest_specs(train_df, dag, orders, library, dataset, **forest_kw) -> dict:
    """NodeSpecs whose non-root nodes are sampled by ForestConditional (fitted on the training draw)."""
    u_df, marginals = to_pseudo_observations_mixed(train_df, category_orders=orders, seed=0)
    specs = {}
    for node in dag.nodes:
        parents = list(dag.predecessors(node))
        marginal = library.get_marginal(dataset, node)
        if not parents:
            specs[node] = NodeSpec(marginal=marginal)
            continue
        fc = ForestConditional(child=node, parents=parents, marginal=marginals[node], **forest_kw).fit(u_df)
        specs[node] = NodeSpec(marginal=marginal,
                               edge_model=EdgeModel(conditional_sampler=fc, parent_order=parents, source="forest"))
    return specs


def run_graph(name: str, seeds: list[int], algorithms: list[str], alpha: float = 0.05) -> pd.DataFrame:
    cfg = GRAPHS[name]
    train_df, dag, orders = load_dataset(name, n=cfg["n"], seed=TRAIN_SEED)
    lib = fit_graph_library(train_df, dag, orders, name)
    t0 = time.time()
    rf_specs = forest_specs(train_df, dag, orders, lib, name)
    rf_fit_seconds = time.time() - t0
    nodes = list(dag.nodes)
    discrete_edges = [e for e in dag.edges] if cfg["discrete"] else []
    rows = []
    for seed in seeds:
        true_df, _, _ = load_dataset(name, n=cfg["n"], seed=seed)
        true_df = true_df[nodes]
        sources = {"true_data": true_df}
        sources["baseline_fixed_rho"], _ = sample(dag, baseline_specs(lib, name, dag), cfg["n"], seed)
        sources["learned"], _ = sample(dag, learned_specs(lib, name, dag), cfg["n"], seed)
        sources["learned_rf"], rf_sampler = sample(dag, rf_specs, cfg["n"], seed)
        if cfg["discrete"]:
            sources["cpt_refit"] = cpt_refit_sample(train_df, dag, cfg["n"], seed)
        for label, df in sources.items():
            row = {"graph": name, "seed": seed, "source": label, "rf_fit_seconds": rf_fit_seconds,
                   "fallback_draws": rf_sampler.total_fallback_draws if label == "learned_rf" else 0}
            data = encode_categorical(df[nodes], orders) if cfg["discrete"] else df[nodes]
            for alg in algorithms:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    cg = run_pc(data, indep_test=cfg["test"], alpha=alpha) if alg == "pc" else run_ges(data, discrete=cfg["discrete"])
                sk = skeleton_scores(dag, cg.G, nodes)
                row[f"shd_{alg}"] = structural_hamming_distance(dag, cg.G, nodes)
                row[f"n_edges_found_{alg}"] = sk["n_edges_found"]
                row[f"skeleton_f1_{alg}"] = sk["skeleton_f1"]
            if cfg["discrete"]:
                row["mean_tvd"] = compare_category_frequencies(true_df, df[nodes])["total_variation_distance"].mean()
                row["mean_cramers_v_abs_err"] = compare_discrete_dependence(true_df, df[nodes], pairs=discrete_edges)["cramers_v_abs_error"].mean()
            else:
                row["mean_edge_tau_abs_err"] = float(pd.Series(
                    [abs(kendalltau(df[a], df[b])[0] - kendalltau(true_df[a], true_df[b])[0]) for a, b in dag.edges]).mean())
            rows.append(row)
        print(f"  rf {name} seed {seed} done")
    return pd.DataFrame(rows)


def analyse(res: pd.DataFrame, algorithms: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics = [f"shd_{a}" for a in algorithms] + [f"n_edges_found_{a}" for a in algorithms] + \
        [m for m in ("mean_tvd", "mean_cramers_v_abs_err", "mean_edge_tau_abs_err") if m in res]
    summ = pd.concat([summarize(res.dropna(subset=[m]), ["graph", "source"], m).assign(metric=m)
                      for m in metrics if res[m].notna().any()], ignore_index=True)
    tests = []
    for g, d in res.groupby("graph"):
        for m in [f"shd_{a}" for a in algorithms] + [x for x in ("mean_cramers_v_abs_err", "mean_edge_tau_abs_err") if x in d and d[x].notna().any()]:
            w = d.pivot(index="seed", columns="source", values=m)
            for other in [c for c in w.columns if c != "learned_rf"]:
                tests.append({"graph": g, "metric": m, "comparison": f"learned_rf - {other}",
                              **paired_comparison(w["learned_rf"], w[other])})
    return summ, pd.DataFrame(tests)


def write_outputs(res: pd.DataFrame, out_dir, **meta) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write per-seed rows, summary and paired tests (also used by scripts/merge_results.py rf)."""
    from pathlib import Path

    from gcda.provenance import write_metadata

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    algorithms = [a for a in ("pc", "ges") if f"shd_{a}" in res and res[f"shd_{a}"].notna().any()]
    summ, tests = analyse(res, algorithms)
    for fname, frame in [("rf_per_seed.csv", res), ("rf_summary.csv", summ), ("rf_tests.csv", tests)]:
        frame.to_csv(out_dir / fname, index=False)
        write_metadata(out_dir / fname, algorithms=algorithms, train_seed=TRAIN_SEED, **meta)
    return summ, tests


def main(graphs: list[str], n_seeds: int, out_dir, algorithms: list[str], seed_start: int = 0) -> None:
    seeds = list(range(seed_start, seed_start + n_seeds))
    res = pd.concat([run_graph(g, seeds, algorithms) for g in graphs], ignore_index=True)
    summ, tests = write_outputs(res, out_dir, graphs=graphs, seeds=seeds)
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(summ.round(4).to_string(index=False))
        print(tests[tests.comparison.isin(["learned_rf - learned", "learned_rf - true_data", "learned_rf - cpt_refit"])]
              .round(4).to_string(index=False))
