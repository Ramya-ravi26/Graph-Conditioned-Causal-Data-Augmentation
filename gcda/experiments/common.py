"""Shared helpers for the remediation experiments (held-out libraries, baselines, statistics)."""

import warnings

import networkx as nx
import numpy as np
import pandas as pd
import pyvinecopulib as pv
from scipy import stats

from gcda.data.preprocessing import discrete_cdf_pairs, to_pseudo_observations_mixed
from gcda.dependency.conditional import ConditionalSampler
from gcda.dependency.families import DEFAULT_BICOP_FAMILIES
from gcda.dependency.library import DependencyLibrary
from gcda.dependency.pairwise import build_pairwise_library
from gcda.generation.graph_sampler import GraphSampler, NodeSpec, node_spec_from_library

GAUSSIAN_ONLY = [pv.BicopFamily.indep, pv.BicopFamily.gaussian]


def fit_graph_library(df: pd.DataFrame, dag: nx.DiGraph, category_orders: dict | None, dataset: str,
                      family_set=DEFAULT_BICOP_FAMILIES, n_jobs: int = 4, all_pairs: bool = False,
                      discrete_mode: str = "jitter") -> DependencyLibrary:
    """Fit marginals, pairwise copulas (graph edges only unless all_pairs) and one
    conditional vine per multi-parent node, on a *training* draw.

    discrete_mode="jitter": discrete columns are continuized by jittering (thesis method);
    discrete_mode="native": pyvinecopulib's discrete likelihood on F(x), F(x-).
    """
    u_df, marginals = to_pseudo_observations_mixed(df, category_orders=category_orders, seed=0)
    u_minus, var_types = None, None
    if discrete_mode == "native":
        u_df, u_minus, var_types = discrete_cdf_pairs(df, marginals)
    elif discrete_mode != "jitter":
        raise ValueError(f"unknown discrete_mode {discrete_mode!r}")
    library = DependencyLibrary()
    library.add_marginals(dataset, marginals)
    pairs = None if all_pairs else [tuple(e) for e in dag.edges]
    library.add_pairwise(build_pairwise_library(u_df, dataset, pairs=pairs, family_set=family_set, n_jobs=n_jobs,
                                                u_minus_df=u_minus, var_types=var_types))
    for node in dag.nodes:
        parents = list(dag.predecessors(node))
        if len(parents) >= 2:
            sampler = ConditionalSampler(child=node, parents=parents, family_set=family_set)
            library.add_conditional(dataset, sampler.fit(u_df, u_minus, var_types))
    return library


def learned_specs(library: DependencyLibrary, dataset: str, dag: nx.DiGraph, compose: bool = False) -> dict[str, NodeSpec]:
    return {n: node_spec_from_library(library, dataset, n, list(dag.predecessors(n)), compose=compose) for n in dag.nodes}


def baseline_specs(library: DependencyLibrary, dataset: str, dag: nx.DiGraph) -> dict[str, NodeSpec]:
    """Real marginals, fixed-correlation Gaussian dependence everywhere (the thesis baseline)."""
    return {n: NodeSpec(marginal=library.get_marginal(dataset, n)) for n in dag.nodes}


def sample(dag, specs, n, seed, calibrate=False):
    max_indeg = max([d for _, d in dag.in_degree()] + [1])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sampler = GraphSampler(dag, node_specs=specs, max_indegree=max(max_indeg, 2), calibrate_margins=calibrate)
        return sampler.sample(n=n, seed=seed), sampler


def cpt_refit_sample(train_df: pd.DataFrame, dag: nx.DiGraph, n: int, seed: int) -> pd.DataFrame:
    """Natural discrete baseline: refit the network's CPTs by maximum likelihood on
    the training draw, then forward-sample. Uses the TRUE DAG, like every generator here."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            from pgmpy.models import DiscreteBayesianNetwork as BN
        except ImportError:  # pragma: no cover - older pgmpy
            from pgmpy.models import BayesianNetwork as BN
        model = BN(list(dag.edges))
        model.add_nodes_from(dag.nodes)
        model.fit(train_df[list(dag.nodes)])  # default estimator = maximum likelihood (all pgmpy versions)
        out = model.simulate(n_samples=n, seed=seed, show_progress=False)
    return out[list(dag.nodes)].reset_index(drop=True)


def skeleton_scores(true_dag: nx.DiGraph, est_graph, node_names: list[str]) -> dict:
    """Adjacency precision/recall/F1 of a causal-learn graph against the true DAG."""
    adj = est_graph.graph
    est = {frozenset((node_names[i], node_names[j])) for i in range(len(node_names)) for j in range(i + 1, len(node_names))
           if adj[i, j] != 0 or adj[j, i] != 0}
    true = {frozenset(e) for e in true_dag.edges}
    tp = len(est & true)
    precision = tp / len(est) if est else 1.0
    recall = tp / len(true) if true else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"n_edges_found": len(est), "skeleton_precision": precision, "skeleton_recall": recall, "skeleton_f1": f1}


def bootstrap_ci(values, n_boot: int = 5000, seed: int = 0, level: float = 0.95) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if len(values) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    means = rng.choice(values, size=(n_boot, len(values)), replace=True).mean(axis=1)
    lo, hi = np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(lo), float(hi)


def paired_comparison(a, b) -> dict:
    """Paired comparison of two per-seed metric vectors (a - b): mean difference,
    bootstrap 95% CI, Wilcoxon signed-rank and paired t-test p-values."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = a - b
    lo, hi = bootstrap_ci(d)
    try:
        w = stats.wilcoxon(a, b, zero_method="zsplit").pvalue if np.any(d != 0) else 1.0
    except ValueError:
        w = float("nan")
    t = stats.ttest_rel(a, b).pvalue if np.std(d) > 0 else (1.0 if np.mean(d) == 0 else 0.0)
    return {"mean_diff": float(d.mean()), "ci_low": lo, "ci_high": hi, "wilcoxon_p": float(w), "ttest_p": float(t), "n": len(d)}


def summarize(df: pd.DataFrame, group: list[str], metric: str) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(group):
        lo, hi = bootstrap_ci(g[metric])
        key = key if isinstance(key, tuple) else (key,)
        rows.append({**dict(zip(group, key)), "mean": g[metric].mean(), "std": g[metric].std(ddof=1),
                     "ci_low": lo, "ci_high": hi, "n": len(g)})
    return pd.DataFrame(rows)
