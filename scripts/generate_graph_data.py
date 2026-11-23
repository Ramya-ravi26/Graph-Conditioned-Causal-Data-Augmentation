"""T5: generate a synthetic dataset for a given graph, reusing the T4 dependency library.

Run: python scripts/build_dependency_library.py   (once, to build the library)
     python scripts/generate_graph_data.py

Demonstrates all three T5c stages on the synthetic SCM's known ground-truth
DAG: a pure baseline run (Gaussian copula everywhere), a run using the real
fitted pairwise/conditional models from the library, and a comparison of
the resulting dependence structure against the true data.
"""

from pathlib import Path

import networkx as nx
from scipy.stats import kendalltau

from gcda.data.datasets import make_synthetic_scm
from gcda.dependency.library import DependencyLibrary
from gcda.generation.graph_sampler import GraphSampler, node_spec_from_library

LIBRARY_PATH = Path(__file__).parent.parent / "outputs" / "dependency_library.json"


def main() -> None:
    true_df, dag = make_synthetic_scm(n=5000, seed=1)
    print(f"Ground-truth DAG edges: {list(dag.edges)}")

    print("\n=== baseline (Gaussian copula everywhere, no library) ===")
    baseline_df = GraphSampler(dag).sample(n=5000, seed=0)
    print(baseline_df.describe().loc[["mean", "std"]])

    if not LIBRARY_PATH.exists():
        print(f"\n{LIBRARY_PATH} not found; run scripts/build_dependency_library.py first "
              "to also see the learned-model comparison.")
        return

    library = DependencyLibrary.load(LIBRARY_PATH)
    node_specs = {
        node: node_spec_from_library(library, "synthetic_scm", node, list(dag.predecessors(node)))
        for node in dag.nodes
    }
    learned_df = GraphSampler(dag, node_specs=node_specs).sample(n=5000, seed=0)

    print("\n=== using T4's learned pairwise/conditional models ===")
    print("pair       true_tau  baseline_tau  learned_tau")
    for a, b in nx.to_undirected(dag).edges:
        t_true = kendalltau(true_df[a], true_df[b])[0]
        t_baseline = kendalltau(baseline_df[a], baseline_df[b])[0]
        t_learned = kendalltau(learned_df[a], learned_df[b])[0]
        print(f"{a}-{b:<8} {t_true:8.3f}  {t_baseline:12.3f}  {t_learned:11.3f}")


if __name__ == "__main__":
    main()
