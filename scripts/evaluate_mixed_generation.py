"""T7a: a genuinely mixed continuous+discrete graph, built and evaluated end to end.

Asia (all binary) and Insurance (all categorical) each stress-test the
discrete pipeline, but neither has a node with a continuous parent feeding a
discrete child, or a 2-parent node with one continuous and one discrete
parent - the two edge shapes T7a's "mixed continuous+discrete" scope
actually calls for. `make_mixed_synthetic_scm` has both, with a known DAG:

  x1 (continuous) -> x2 (3-level ordinal)         [continuous parent -> discrete child]
  x1, x3 (continuous) -> x4 (continuous)          [ordinary 2-parent continuous]
  x2 (discrete), x4 (continuous) -> x5 (binary)   [mixed-type 2-parent node]

Run: python scripts/evaluate_mixed_generation.py

Builds the dependency library and samples the graph in one script (it's
small enough that a separate build step isn't needed), then evaluates:
  - T6a.i marginals for the continuous columns,
  - T7d.i category frequencies for the discrete columns,
  - dependence for every edge uniformly via Kendall's tau on an "ordinal
    numeric view" (discrete categories mapped to their rank via
    category_orders, continuous columns left as-is) - this is what makes a
    single dependence check meaningful across continuous-continuous,
    continuous-discrete and discrete-discrete edges alike.
"""

from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

from gcda.data.datasets import make_mixed_synthetic_scm
from gcda.data.preprocessing import to_pseudo_observations_mixed
from gcda.dependency.conditional import ConditionalSampler
from gcda.dependency.library import DependencyLibrary
from gcda.dependency.pairwise import build_pairwise_library
from gcda.evaluation.discrete import compare_category_frequencies, cramers_v
from gcda.evaluation.realism import compare_marginals, compare_pairwise_dependence
from gcda.provenance import write_metadata
from gcda.generation.graph_sampler import GraphSampler, node_spec_from_library


def to_ordinal_numeric(df: pd.DataFrame, category_orders: dict[str, list]) -> pd.DataFrame:
    """Numeric view of a mixed DataFrame: discrete columns -> rank index in
    their category order, continuous columns unchanged. Lets Kendall's
    tau/Spearman's rho be computed uniformly across continuous-continuous,
    continuous-discrete and discrete-discrete pairs.
    """
    out = {}
    for col in df.columns:
        if col in category_orders:
            index = {c: i for i, c in enumerate(category_orders[col])}
            out[col] = df[col].map(index)
        else:
            out[col] = df[col]
    return pd.DataFrame(out)


def main() -> None:
    true_df, dag, category_orders = make_mixed_synthetic_scm(n=5000, seed=1)
    continuous_cols = [c for c in dag.nodes if c not in category_orders]
    discrete_cols = [c for c in dag.nodes if c in category_orders]
    print(f"DAG edges: {list(dag.edges)}")
    print(f"continuous columns: {continuous_cols}, discrete columns: {discrete_cols}")

    u_df, marginals = to_pseudo_observations_mixed(true_df, category_orders=category_orders, seed=0)

    library = DependencyLibrary()
    library.add_marginals("mixed_scm", marginals)
    library.add_pairwise(build_pairwise_library(u_df, dataset_name="mixed_scm"))
    for node in dag.nodes:
        parents = list(dag.predecessors(node))
        if len(parents) >= 2:
            sampler = ConditionalSampler(child=node, parents=parents).fit(u_df)
            library.add_conditional("mixed_scm", sampler)

    node_specs = {
        node: node_spec_from_library(library, "mixed_scm", node, list(dag.predecessors(node)))
        for node in dag.nodes
    }
    sim_df = GraphSampler(dag, node_specs=node_specs, max_indegree=2).sample(n=5000, seed=2)

    print("\n=== continuous marginals (T6a.i) ===")
    marg = compare_marginals(true_df, sim_df, columns=continuous_cols)
    print(marg[["column", "quantile_l1", "ks_stat"]].to_string(index=False))

    print("\n=== discrete category frequencies (T7d.i) ===")
    freq = compare_category_frequencies(true_df, sim_df, columns=discrete_cols)
    print(freq[["column", "max_abs_diff", "total_variation_distance"]].to_string(index=False))

    print("\n=== dependence per edge, Kendall's tau on the ordinal-numeric view (T6a.ii/T7d.ii) ===")
    true_numeric = to_ordinal_numeric(true_df, category_orders)
    sim_numeric = to_ordinal_numeric(sim_df, category_orders)
    dep = compare_pairwise_dependence(true_numeric, sim_numeric, pairs=list(dag.edges))
    out = Path(__file__).parent.parent / "outputs" / "mixed_generation_edges.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    dep.to_csv(out, index=False)
    write_metadata(out)
    for _, row in dep.iterrows():
        edge_type = "discrete-discrete" if {row.var_i, row.var_j} <= set(discrete_cols) else (
            "continuous-continuous" if {row.var_i, row.var_j} <= set(continuous_cols) else "mixed"
        )
        print(f"  {row.var_i}->{row.var_j} ({edge_type}): tau_true={row.tau_true:.3f} "
              f"tau_sim={row.tau_sim:.3f} abs_error={row.tau_abs_error:.3f}")

    print("\n=== Cramer's V on the one genuinely discrete-discrete-adjacent pair (x2, x5) ===")
    print(f"  true={cramers_v(true_df['x2'], true_df['x5']):.3f} sim={cramers_v(sim_df['x2'], sim_df['x5']):.3f}")


if __name__ == "__main__":
    main()
