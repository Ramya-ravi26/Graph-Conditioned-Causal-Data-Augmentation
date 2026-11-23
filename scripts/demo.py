"""End-to-end live demo (T8b.iv): the whole pipeline, narrated, in ~1-2 minutes.

Run: python scripts/demo.py

Deliberately scoped to fast pieces (synthetic SCM + Asia, not the ~10-minute
Insurance build) so it's usable in front of an audience. Walks through:
  1. fit a dependency library from real/synthetic data (T4),
  2. sample a graph with it vs. a naive baseline (T5),
  3. evaluate realism, baseline vs. learned (T6a),
  4. do the same for a discrete network (T7),
  5. compose a novel graph from TWO different datasets' building blocks -
     the literal "reuse learned dependencies for any user-specified graph"
     claim, not just replaying a dataset's own structure,
  6. close the loop: run a real causal discovery algorithm on the result.
"""

import warnings

import networkx as nx
import pandas as pd
from scipy.stats import kendalltau

from gcda.data.datasets import load_asia, load_sachs, make_synthetic_scm
from gcda.data.preprocessing import to_pseudo_observations, to_pseudo_observations_mixed
from gcda.dependency.conditional import ConditionalSampler
from gcda.dependency.library import DependencyLibrary
from gcda.dependency.pairwise import build_pairwise_library
from gcda.evaluation.causal_discovery import compare_causal_discovery, encode_categorical
from gcda.evaluation.realism import compare_marginals, compare_pairwise_dependence
from gcda.generation.graph_sampler import GraphSampler, NodeSpec, node_spec_from_library
from gcda.generation.spec import build_node_specs


def banner(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def step_1_build_continuous_library() -> DependencyLibrary:
    banner("1. Fit a dependency library from the synthetic SCM (T4)")
    df, dag = make_synthetic_scm(n=5000, seed=1)
    print(f"DAG: {list(dag.edges)}")

    u_df, marginals = to_pseudo_observations(df)
    library = DependencyLibrary()
    library.add_marginals("synthetic_scm", marginals)
    library.add_pairwise(build_pairwise_library(u_df, dataset_name="synthetic_scm"))
    for node in dag.nodes:
        parents = list(dag.predecessors(node))
        if len(parents) >= 2:
            library.add_conditional("synthetic_scm", ConditionalSampler(child=node, parents=parents).fit(u_df))
    print(f"library: {len(library.pairwise)} pairwise models, {len(library.conditional)} conditional models")
    return library, df, dag


def step_2_generate_and_compare(library: DependencyLibrary, true_df: pd.DataFrame, dag: nx.DiGraph) -> pd.DataFrame:
    banner("2-3. Sample the same graph: baseline vs. learned models (T5, T6a)")
    baseline_specs = {n: NodeSpec(marginal=library.get_marginal("synthetic_scm", n)) for n in dag.nodes}
    baseline_df = GraphSampler(dag, node_specs=baseline_specs).sample(n=5000, seed=0)

    learned_specs = {n: node_spec_from_library(library, "synthetic_scm", n, list(dag.predecessors(n))) for n in dag.nodes}
    learned_df = GraphSampler(dag, node_specs=learned_specs).sample(n=5000, seed=0)

    print(f"{'edge':<10} {'true_tau':>9} {'baseline_tau':>13} {'learned_tau':>12}")
    for a, b in dag.edges:
        print(f"{a}->{b:<7} {kendalltau(true_df[a], true_df[b])[0]:>9.3f} "
              f"{kendalltau(baseline_df[a], baseline_df[b])[0]:>13.3f} "
              f"{kendalltau(learned_df[a], learned_df[b])[0]:>12.3f}")

    marg = compare_marginals(true_df, learned_df)
    print(f"\nlearned-run mean marginal quantile L1 error: {marg['quantile_l1'].mean():.4f}")
    return learned_df


def step_4_discrete_network() -> DependencyLibrary:
    banner("4. Same pipeline, unchanged, on a discrete network: Asia (T7)")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df, dag, category_orders = load_asia(n_samples=8000, seed=0)

    u_df, marginals = to_pseudo_observations_mixed(df, category_orders=category_orders, seed=0)
    library = DependencyLibrary()
    library.add_marginals("asia", marginals)
    library.add_pairwise(build_pairwise_library(u_df, dataset_name="asia"))
    for node in dag.nodes:
        parents = list(dag.predecessors(node))
        if len(parents) >= 2:
            library.add_conditional("asia", ConditionalSampler(child=node, parents=parents).fit(u_df))

    specs = {n: node_spec_from_library(library, "asia", n, list(dag.predecessors(n))) for n in dag.nodes}
    sim_df = GraphSampler(dag, node_specs=specs, max_indegree=2).sample(n=8000, seed=1)

    print("category frequencies, true vs. simulated (should match closely):")
    for col in ["smoke", "either"]:
        print(f"  {col}: true={df[col].value_counts(normalize=True).round(3).to_dict()} "
              f"sim={sim_df[col].value_counts(normalize=True).round(3).to_dict()}")
    return library


def step_5_cross_dataset_composition(continuous_library: DependencyLibrary, discrete_library: DependencyLibrary) -> None:
    banner("5. Compose a NOVEL graph from two different datasets' building blocks")
    # Sachs building blocks (marginals + the learned praf-pmek copula)
    sachs = load_sachs()
    u_s, m_s = to_pseudo_observations(sachs)
    sachs_library = DependencyLibrary()
    sachs_library.add_marginals("sachs", m_s)
    sachs_library.add_pairwise(build_pairwise_library(u_s, "sachs", pairs=[("praf", "pmek")]))
    merged = sachs_library.merge(discrete_library)

    # praf -> pmek uses the copula learned on Sachs; the cross-dataset edge
    # praf -> dysp RE-USES the copula Asia learned for bronc -> dysp
    # (graph that never existed in either dataset; strict = no baseline fallback)
    spec = {
        "nodes": {"praf": {"dataset": "sachs"}, "pmek": {"dataset": "sachs"}, "dysp": {"dataset": "asia"}},
        "edges": [["praf", "pmek"],
                  {"from": "praf", "to": "dysp", "copula": {"dataset": "asia", "pair": ["bronc", "dysp"]}}],
    }
    dag, node_specs, report = build_node_specs(merged, spec, strict=True)
    for item in report:
        print(f"  {item['node']}: {item['what']} <- {item['decision']}")
    df = GraphSampler(dag, node_specs=node_specs).sample(n=5000, seed=0)
    print(f"tau(praf, pmek): generated={kendalltau(df['praf'], df['pmek'])[0]:.3f} "
          f"real Sachs={kendalltau(sachs['praf'], sachs['pmek'])[0]:.3f}")
    print(f"P(dysp=yes): generated={(df['dysp'] == 'yes').mean():.3f} "
          f"(Asia marginal re-used)")
    print(df.head())


def step_6_close_the_loop(library: DependencyLibrary, true_df: pd.DataFrame, dag: nx.DiGraph, learned_df: pd.DataFrame) -> None:
    banner("6. Close the loop: does a real causal discovery algorithm agree?")
    baseline_specs = {n: NodeSpec(marginal=library.get_marginal("synthetic_scm", n)) for n in dag.nodes}
    baseline_df = GraphSampler(dag, node_specs=baseline_specs).sample(n=5000, seed=0)

    result = compare_causal_discovery(
        true_df, {"baseline": baseline_df, "learned": learned_df}, dag, indep_test="fisherz",
    )
    print("PC algorithm's Structural Hamming Distance to the true DAG (lower is better):")
    print(result.to_string(index=False))


def main() -> None:
    continuous_library, true_df, dag = step_1_build_continuous_library()
    learned_df = step_2_generate_and_compare(continuous_library, true_df, dag)
    discrete_library = step_4_discrete_network()
    step_5_cross_dataset_composition(continuous_library, discrete_library)
    step_6_close_the_loop(continuous_library, true_df, dag, learned_df)
    banner("Done.")


if __name__ == "__main__":
    main()
