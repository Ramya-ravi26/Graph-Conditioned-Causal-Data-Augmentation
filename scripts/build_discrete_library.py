"""T7: build a dependency library for discrete/mixed datasets, reusing T4 unchanged.

Run: python scripts/build_discrete_library.py
Writes the library to outputs/discrete_dependency_library.json.

Unlike scripts/build_dependency_library.py (which fits one example 2-parent
conditional model per dataset), this fits a conditional model for *every*
multi-parent node so the whole DAG can be reconstructed later (T7 wants to
regenerate a full discrete network, not just illustrate one edge).
"""

from pathlib import Path

import networkx as nx
import pandas as pd

from gcda.data.datasets import load_asia, load_insurance, make_discretized_sachs
from gcda.data.preprocessing import to_pseudo_observations_mixed
from gcda.dependency.conditional import ConditionalSampler
from gcda.dependency.library import DependencyLibrary
from gcda.dependency.pairwise import build_pairwise_library, top_k_partners
from gcda.provenance import run_metadata

OUTPUT_PATH = Path(__file__).parent.parent / "outputs" / "discrete_dependency_library.json"

# discretized_sachs has no ground-truth DAG (like the real continuous Sachs
# data), so there's no full network to reconstruct - but we still fit one
# example 2-parent conditional model, picking the two variables most
# dependent on the target by |tau|, so it gets exercised past "pairwise only".
DISCRETIZED_SACHS_TARGET = "pmek"


def build_graph_library(
    library: DependencyLibrary, name: str, df: pd.DataFrame, dag: nx.DiGraph, category_orders: dict[str, list]
) -> None:
    print(f"\n=== {name} ({df.shape[0]} rows, {df.shape[1]} vars, "
          f"max indegree {max(dict(dag.in_degree()).values())}) ===")

    u_df, marginals = to_pseudo_observations_mixed(df, category_orders=category_orders, seed=0)
    library.add_marginals(name, marginals)

    pairwise_entries = build_pairwise_library(u_df, dataset_name=name)
    library.add_pairwise(pairwise_entries)
    n_ok = sum(1 for e in pairwise_entries if "error" not in e)
    print(f"  fit {n_ok}/{len(pairwise_entries)} pairwise models")

    n_conditional = 0
    for node in dag.nodes:
        parents = list(dag.predecessors(node))
        if len(parents) < 2:
            continue
        sampler = ConditionalSampler(child=node, parents=parents).fit(u_df)
        library.add_conditional(name, sampler)
        n_conditional += 1
    print(f"  fit {n_conditional} multi-parent conditional models")


def main() -> None:
    library = DependencyLibrary()

    asia_df, asia_dag, asia_orders = load_asia(n_samples=10000, seed=0)
    build_graph_library(library, "asia", asia_df, asia_dag, asia_orders)

    insurance_df, insurance_dag, insurance_orders = load_insurance(n_samples=10000, seed=0)
    build_graph_library(library, "insurance", insurance_df, insurance_dag, insurance_orders)

    print("\n=== discretized_sachs (stress test, no ground-truth DAG) ===")
    disc_sachs, sachs_orders = make_discretized_sachs()
    u_df, marginals = to_pseudo_observations_mixed(disc_sachs, category_orders=sachs_orders, seed=0)
    library.add_marginals("discretized_sachs", marginals)
    pairwise_entries = build_pairwise_library(u_df, dataset_name="discretized_sachs")
    library.add_pairwise(pairwise_entries)
    print(f"  fit {sum(1 for e in pairwise_entries if 'error' not in e)}/{len(pairwise_entries)} pairwise models")

    parents = top_k_partners(pairwise_entries, DISCRETIZED_SACHS_TARGET, k=2)
    print(f"  fitting conditional model: {DISCRETIZED_SACHS_TARGET} | {parents}")
    sampler = ConditionalSampler(child=DISCRETIZED_SACHS_TARGET, parents=parents).fit(u_df)
    library.add_conditional("discretized_sachs", sampler)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    library.metadata = run_metadata(script='build_discrete_library.py')
    library.save(OUTPUT_PATH)
    print(f"\nSaved discrete dependency library ({len(library.pairwise)} pairwise, "
          f"{len(library.conditional)} conditional models) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
