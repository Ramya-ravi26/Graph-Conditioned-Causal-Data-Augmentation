"""RQ6 (held-out, multi-seed): is the generated data usable by a structure-learning algorithm?

Changes relative to the thesis' original protocol (scripts/evaluate_causal_discovery.py):
  * held-out: the dependency library is fitted ONCE on a training draw
    (seed TRAIN_SEED) that is disjoint from every evaluation seed; the
    original protocol re-used the library's own training data for seed 1;
  * more seeds (default 30) and four graphs (synthetic SCM, Asia, Insurance, Alarm);
  * stronger baselines: besides the fixed rho=0.5 Gaussian baseline, a
    *fitted* Gaussian copula (same pipeline, Gaussian/independence families
    only) and, for discrete networks, CPT refitting by maximum likelihood;
  * learned_native: discrete columns fitted with the native discrete copula
    likelihood instead of jittering (discrete graphs only);
  * statistics: bootstrap 95% CIs and paired Wilcoxon / t-tests per pair of
    sources, plus skeleton precision/recall/F1 and number of edges found.
"""

import time
import warnings

import numpy as np
import pandas as pd

from gcda.data.registry import load_dataset
from gcda.evaluation.causal_discovery import encode_categorical, run_ges, run_pc, structural_hamming_distance
from gcda.experiments.common import (
    GAUSSIAN_ONLY,
    baseline_specs,
    cpt_refit_sample,
    fit_graph_library,
    learned_specs,
    paired_comparison,
    sample,
    skeleton_scores,
    summarize,
)

TRAIN_SEED = 10_000
GRAPHS = {
    "synthetic_scm": {"n": 5000, "test": "fisherz", "discrete": False},
    "asia": {"n": 8000, "test": "chisq", "discrete": True},
    "insurance": {"n": 8000, "test": "chisq", "discrete": True},
    "alarm": {"n": 8000, "test": "chisq", "discrete": True},
}


def run_graph(name: str, seeds: list[int], alpha: float = 0.05, n_jobs: int = 4, algorithm: str = "pc") -> pd.DataFrame:
    cfg = GRAPHS[name]
    train_df, dag, orders = load_dataset(name, n=cfg["n"], seed=TRAIN_SEED)
    t0 = time.time()
    lib_full = fit_graph_library(train_df, dag, orders, name, n_jobs=n_jobs)
    lib_gauss = fit_graph_library(train_df, dag, orders, name, family_set=GAUSSIAN_ONLY, n_jobs=n_jobs)
    lib_native = fit_graph_library(train_df, dag, orders, name, n_jobs=n_jobs, discrete_mode="native") if cfg["discrete"] else None
    fit_seconds = time.time() - t0
    nodes = list(dag.nodes)
    rows = []
    for seed in seeds:
        true_df, _, _ = load_dataset(name, n=cfg["n"], seed=seed)
        true_df = true_df[nodes]
        sources = {"true_data": true_df}
        sources["baseline_fixed_rho"], _ = sample(dag, baseline_specs(lib_full, name, dag), cfg["n"], seed)
        sources["gaussian_copula_fitted"], _ = sample(dag, learned_specs(lib_gauss, name, dag), cfg["n"], seed)
        sources["learned"], learned_sampler = sample(dag, learned_specs(lib_full, name, dag), cfg["n"], seed)
        if cfg["discrete"]:
            sources["learned_native"], _ = sample(dag, learned_specs(lib_native, name, dag), cfg["n"], seed)
            sources["cpt_refit"] = cpt_refit_sample(train_df, dag, cfg["n"], seed)
        for label, df in sources.items():
            data = encode_categorical(df[nodes], orders) if cfg["discrete"] else df[nodes]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if algorithm == "pc":
                    cg = run_pc(data, indep_test=cfg["test"], alpha=alpha)
                else:
                    cg = run_ges(data, discrete=cfg["discrete"])
            rows.append({
                "graph": name, "seed": seed, "source": label, "alpha": alpha, "algorithm": algorithm,
                "shd": structural_hamming_distance(dag, cg.G, nodes),
                **skeleton_scores(dag, cg.G, nodes),
                "true_edges": dag.number_of_edges(),
                "fallback_draws": learned_sampler.total_fallback_draws if label == "learned" else 0,
                "library_fit_seconds": fit_seconds,
            })
        print(f"  {name} seed {seed} done")
    return pd.DataFrame(rows)


def analyse(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary = []
    for metric in ["shd", "n_edges_found", "skeleton_f1"]:
        s = summarize(results, ["graph", "source"], metric)
        s.insert(2, "metric", metric)
        summary.append(s)
    summary = pd.concat(summary, ignore_index=True)

    tests = []
    for graph, g in results.groupby("graph"):
        wide = g.pivot(index="seed", columns="source", values="shd")
        for other in [c for c in wide.columns if c != "learned"]:
            res = paired_comparison(wide["learned"], wide[other])
            tests.append({"graph": graph, "comparison": f"learned - {other}", "metric": "shd", **res})
    return summary, pd.DataFrame(tests)


def write_outputs(results: pd.DataFrame, out_dir, **meta) -> None:
    from pathlib import Path

    from gcda.provenance import write_metadata

    out_dir = Path(out_dir)
    summary, tests = analyse(results)
    for fname, frame in [("rq6_heldout_per_seed.csv", results), ("rq6_heldout_summary.csv", summary),
                         ("rq6_heldout_tests.csv", tests)]:
        frame.to_csv(out_dir / fname, index=False)
        write_metadata(out_dir / fname, **meta)
    with pd.option_context("display.width", 200):
        print(summary[summary.metric == "shd"].round(3).to_string(index=False))
        print(tests.round(4).to_string(index=False))


def main(graphs: list[str], n_seeds: int, out_dir, alpha: float = 0.05, seed_start: int = 0,
         algorithm: str = "pc") -> None:
    from pathlib import Path

    from gcda.provenance import write_metadata

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seeds = list(range(seed_start, seed_start + n_seeds))
    results = pd.concat([run_graph(g, seeds, alpha=alpha, algorithm=algorithm) for g in graphs], ignore_index=True)
    write_outputs(results, out_dir, graphs=graphs, seeds=seeds, train_seed=TRAIN_SEED, alpha=alpha, algorithm=algorithm)
