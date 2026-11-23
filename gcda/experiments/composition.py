"""RQ5: are learned dependencies reusable as building blocks for graphs that never existed?

Two experiments:

(a) The thesis' cross-dataset graph praf -> pmek, praf -> dysp, built from a
    merged Sachs + Asia library. praf/pmek keep their Sachs marginals and the
    learned praf-pmek copula; dysp keeps its Asia marginal; the cross-dataset
    edge praf -> dysp re-uses (binds) the copula Asia learned for
    bronc -> dysp. Reported: marginal fidelity of every node, and whether
    each edge reproduces the dependence of the copula it was built from.

(b) Novel random DAGs over the 11 Sachs variables (max indegree 2): none of
    these graphs exists in the data. For each DAG and each generator
    (learned pairwise copulas + fitted vines; learned pairwise copulas +
    pairwise-composed multi-parent models; fitted Gaussian copula; fixed
    rho=0.5 baseline) we report: PC's SHD/skeleton-F1 to the *specified* DAG
    (does the generator produce data faithful to the requested graph?),
    per-edge tau fidelity to the library copula, marginal drift with and
    without calibration, and varsortability (Reisach et al., 2021).
"""

import warnings

import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import kendalltau, ks_2samp

from gcda.data.datasets import load_asia, load_sachs
from gcda.data.preprocessing import to_pseudo_observations, to_pseudo_observations_mixed
from gcda.dependency.conditional import ConditionalSampler
from gcda.dependency.library import DependencyLibrary
from gcda.dependency.pairwise import build_pairwise_library
from gcda.evaluation.causal_discovery import run_pc, structural_hamming_distance
from gcda.evaluation.discrete import compare_category_frequencies
from gcda.experiments.common import GAUSSIAN_ONLY, bootstrap_ci, paired_comparison, skeleton_scores
from gcda.generation.graph_sampler import GraphSampler, NodeSpec
from gcda.generation.spec import build_node_specs


def kendall_tau_a(x, y) -> float:
    """Kendall's tau-a via tau_b and tie fractions (exact identity, O(n log n))."""
    x, y = np.asarray(x), np.asarray(y)
    tb = kendalltau(x, y, variant="b")[0]
    n = len(x)
    n0 = n * (n - 1) / 2

    def tied_pairs(v):
        _, c = np.unique(v, return_counts=True)
        return float((c * (c - 1) / 2).sum())

    return float(tb * np.sqrt((n0 - tied_pairs(x)) * (n0 - tied_pairs(y))) / n0)


def varsortability(df: pd.DataFrame, dag: nx.DiGraph) -> float:
    """Fraction of directed paths (here: edges) along which marginal variance increases."""
    var = df.var()
    edges = list(dag.edges)
    if not edges:
        return float("nan")
    return float(np.mean([1.0 if var[b] > var[a] else 0.5 if var[b] == var[a] else 0.0 for a, b in edges]))


# --------------------------------------------------------------------------- (a)
def cross_dataset_rq5(seeds: list[int], n: int = 10000) -> tuple[pd.DataFrame, dict]:
    sachs = load_sachs()
    asia, asia_dag, orders = load_asia(n_samples=10000, seed=0)
    lib = DependencyLibrary()
    u_s, m_s = to_pseudo_observations(sachs)
    lib.add_marginals("sachs", m_s)
    lib.add_pairwise(build_pairwise_library(u_s, "sachs", pairs=[("praf", "pmek")]))
    lib_a = DependencyLibrary()
    u_a, m_a = to_pseudo_observations_mixed(asia, category_orders=orders, seed=0)
    lib_a.add_marginals("asia", m_a)
    lib_a.add_pairwise(build_pairwise_library(u_a, "asia", pairs=[("bronc", "dysp")]))
    merged = lib.merge(lib_a)
    spec = {
        "nodes": {"praf": {"dataset": "sachs"}, "pmek": {"dataset": "sachs"}, "dysp": {"dataset": "asia"}},
        "edges": [["praf", "pmek"], {"from": "praf", "to": "dysp", "copula": {"dataset": "asia", "pair": ["bronc", "dysp"]}}],
    }
    dag, specs, report = build_node_specs(merged, spec, strict=True)
    tau_cop_sachs = merged.get_pairwise_entry("sachs", "praf", "pmek")["tau"]
    tau_cop_asia = merged.get_pairwise_entry("asia", "bronc", "dysp")["tau"]
    dysp_codes = asia["dysp"].map({s: i for i, s in enumerate(orders["dysp"])})
    bronc_codes = asia["bronc"].map({s: i for i, s in enumerate(orders["bronc"])})
    rows = []
    for seed in seeds:
        sampler = GraphSampler(dag, node_specs=specs)
        gen = sampler.sample(n=n, seed=seed)
        lat = sampler.u_values_
        gen_dysp = gen["dysp"].map({s: i for i, s in enumerate(orders["dysp"])})
        rows.append({
            "seed": seed,
            "ks_praf": ks_2samp(gen["praf"], sachs["praf"]).statistic,
            "ks_pmek": ks_2samp(gen["pmek"], sachs["pmek"]).statistic,
            "tvd_dysp": compare_category_frequencies(asia[["dysp"]], gen[["dysp"]])["total_variation_distance"][0],
            "tau_praf_pmek_generated": kendalltau(gen["praf"], gen["pmek"])[0],
            "tau_praf_pmek_sachs_data": kendalltau(sachs["praf"], sachs["pmek"])[0],
            "tau_praf_pmek_copula": tau_cop_sachs,
            "tau_latent_praf_dysp_generated": kendalltau(lat["praf"], lat["dysp"])[0],
            "tau_a_praf_dysp_generated": kendall_tau_a(gen["praf"], gen_dysp),
            "tau_a_bronc_dysp_asia_data": kendall_tau_a(bronc_codes, dysp_codes),
            "tau_bronc_dysp_copula": tau_cop_asia,
        })
    return pd.DataFrame(rows), {"decisions": report}


# --------------------------------------------------------------------------- (b)
def random_dag(nodes: list[str], rng: np.random.Generator, max_parents: int = 2, edge_prob: float = 0.3) -> nx.DiGraph:
    order = list(rng.permutation(nodes))
    dag = nx.DiGraph()
    dag.add_nodes_from(order)
    for i, child in enumerate(order[1:], start=1):
        candidates = order[:i]
        k = min(max_parents, int(rng.binomial(len(candidates), edge_prob)) if candidates else 0)
        k = min(k, len(candidates))
        for parent in rng.choice(candidates, size=k, replace=False):
            dag.add_edge(parent, child)
    return dag


def _sachs_libraries(u_df, marginals):
    full, gauss = DependencyLibrary(), DependencyLibrary()
    for lib, fams in [(full, None), (gauss, GAUSSIAN_ONLY)]:
        lib.add_marginals("sachs", marginals)
        kwargs = {"family_set": fams} if fams else {}
        lib.add_pairwise(build_pairwise_library(u_df, "sachs", n_jobs=4, **kwargs))
    return full, gauss


def novel_graph_study(n_dags: int, n: int = 5000, observational_only: bool = False, dag_start: int = 0) -> pd.DataFrame:
    sachs = load_sachs(observational_only=observational_only)
    u_df, marginals = to_pseudo_observations(sachs)
    lib_full, lib_gauss = _sachs_libraries(u_df, marginals)
    nodes = list(sachs.columns)
    rows = []
    for d in range(dag_start, dag_start + n_dags):
        rng = np.random.default_rng(1000 + d)
        dag = random_dag(nodes, rng)
        spec = {"nodes": {v: {"dataset": "sachs"} for v in nodes}, "edges": [list(e) for e in dag.edges]}
        # fitted-vine variant: fit a conditional vine for every multi-parent node of THIS graph
        lib_vine = DependencyLibrary.from_payload({"pairwise": lib_full.pairwise, "conditional": [], "marginals": lib_full.marginals})
        for v in nodes:
            ps = list(dag.predecessors(v))
            if len(ps) >= 2:
                lib_vine.add_conditional("sachs", ConditionalSampler(child=v, parents=ps).fit(u_df))
        generators = {
            "learned_fitted_vine": build_node_specs(lib_vine, spec, compose=False)[1],
            "learned_composed": build_node_specs(lib_full, spec, compose=True)[1],
            "gaussian_copula_fitted": build_node_specs(lib_gauss, spec, compose=True)[1],
            "baseline_fixed_rho": {v: NodeSpec(marginal=lib_full.get_marginal("sachs", v)) for v in nodes},
        }
        for label, specs in generators.items():
            for calibrate in (False, True):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    sampler = GraphSampler(dag, node_specs=specs, calibrate_margins=calibrate)
                    gen = sampler.sample(n=n, seed=d)
                    cg = run_pc(gen[nodes], indep_test="fisherz")
                ks = [ks_2samp(gen[v], sachs[v]).statistic for v in nodes]
                tau_err = []
                for a, b in dag.edges:
                    if dag.in_degree(b) == 1:
                        lib = lib_gauss if label == "gaussian_copula_fitted" else lib_full
                        target = lib.get_pairwise_entry("sachs", a, b)["tau"] if label != "baseline_fixed_rho" else 2 / np.pi * np.arcsin(0.5)
                        tau_err.append(abs(kendalltau(gen[a], gen[b])[0] - target))
                rows.append({
                    "dag": d, "generator": label, "calibrated": calibrate, "n_edges": dag.number_of_edges(),
                    "max_indegree": max(dict(dag.in_degree()).values()),
                    "shd": structural_hamming_distance(dag, cg.G, nodes),
                    **skeleton_scores(dag, cg.G, nodes),
                    "mean_marginal_ks": float(np.mean(ks)), "max_marginal_ks": float(np.max(ks)),
                    "indeg1_tau_abs_error": float(np.mean(tau_err)) if tau_err else np.nan,
                    "n_drift_nodes": int(sum(1 for v in sampler.diagnostics_.values()
                                             if v["n_parents"] and v["u_uniformity_ks"] > max(0.05, 1.95 / np.sqrt(n)))),
                    "varsortability": varsortability(gen[nodes], dag),
                    "fallback_draws": sampler.total_fallback_draws,
                })
        # reference: a linear-Gaussian SCM on the same DAG (Reisach et al. varsortability check)
        w_rng = np.random.default_rng(5000 + d)
        x = pd.DataFrame(index=range(n), columns=nodes, dtype=float)
        for v in nx.topological_sort(dag):
            x[v] = w_rng.normal(size=n)
            for p in dag.predecessors(v):
                x[v] += w_rng.choice([-1, 1]) * w_rng.uniform(0.5, 2.0) * x[p]
        rows.append({"dag": d, "generator": "linear_gaussian_scm_reference", "calibrated": False,
                     "n_edges": dag.number_of_edges(), "varsortability": varsortability(x, dag)})
        print(f"  novel DAG {d} done ({dag.number_of_edges()} edges)")
    return pd.DataFrame(rows)


def summarize_novel(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics = ["shd", "skeleton_f1", "mean_marginal_ks", "indeg1_tau_abs_error", "n_drift_nodes", "varsortability"]
    rows = []
    for (gen, cal), g in results.groupby(["generator", "calibrated"]):
        row = {"generator": gen, "calibrated": cal, "n_dags": g["dag"].nunique()}
        for m in metrics:
            if m in g and g[m].notna().any():
                lo, hi = bootstrap_ci(g[m].dropna())
                row[m] = g[m].mean()
                row[f"{m}_ci"] = f"[{lo:.3f}, {hi:.3f}]"
        rows.append(row)
    tests = []
    uncal = results[(results.calibrated == False) & results.shd.notna()]  # noqa: E712
    wide = uncal.pivot(index="dag", columns="generator", values="shd")
    for other in ["learned_composed", "gaussian_copula_fitted", "baseline_fixed_rho"]:
        if other in wide:
            tests.append({"comparison": f"learned_fitted_vine - {other}", "metric": "shd",
                          **paired_comparison(wide["learned_fitted_vine"], wide[other])})
    return pd.DataFrame(rows), pd.DataFrame(tests)


def main_rq5_only(out_dir, n_seeds: int = 30) -> None:
    import json
    from pathlib import Path

    from gcda.provenance import write_metadata

    out_dir = Path(out_dir)
    rq5, info = cross_dataset_rq5(list(range(n_seeds)))
    rq5.to_csv(out_dir / "rq5_cross_dataset.csv", index=False)
    (out_dir / "rq5_cross_dataset_decisions.json").write_text(json.dumps(info, indent=2))
    write_metadata(out_dir / "rq5_cross_dataset.csv")
    print(rq5.describe().T[["mean", "std"]].round(4).to_string())


def main(n_dags: int, n_seeds: int, out_dir, dag_start: int = 0) -> None:
    import json
    from pathlib import Path

    from gcda.provenance import write_metadata

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rq5, info = cross_dataset_rq5(list(range(min(n_seeds, 30))))
    rq5.to_csv(out_dir / "rq5_cross_dataset.csv", index=False)
    (out_dir / "rq5_cross_dataset_decisions.json").write_text(json.dumps(info, indent=2))
    write_metadata(out_dir / "rq5_cross_dataset.csv")
    print(rq5.describe().T[["mean", "std"]].round(4).to_string())

    for obs in (False, True):
        tag = "observational" if obs else "pooled"
        res = novel_graph_study(n_dags, observational_only=obs, dag_start=dag_start)
        summary, tests = summarize_novel(res)
        for fname, frame in [(f"novel_dags_{tag}_per_dag.csv", res), (f"novel_dags_{tag}_summary.csv", summary),
                             (f"novel_dags_{tag}_tests.csv", tests)]:
            frame.to_csv(out_dir / fname, index=False)
            write_metadata(out_dir / fname, n_dags=n_dags, sachs_rows=tag)
        with pd.option_context("display.width", 250, "display.max_columns", 30):
            print(f"--- novel DAGs ({tag}) ---")
            print(summary.round(3).to_string(index=False))
            print(tests.round(4).to_string(index=False))
