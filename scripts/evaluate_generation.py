"""T6a+b: evaluate a generated graph dataset against the true data it should resemble.

Run: python scripts/build_dependency_library.py   (once, to build the library)
     python scripts/evaluate_generation.py

Uses the synthetic SCM (known ground-truth DAG) to compare:
  - baseline generation (Gaussian copula everywhere) vs.
  - generation using T4's learned pairwise/conditional models
against the true data, on marginals (T6a.i), pairwise dependence (T6a.ii)
and a multivariate distribution distance (T6a.iii). Also runs the T6b
graph-conditioning checks (edge removal, dependence-strength monotonicity).
"""

from pathlib import Path

import networkx as nx

from gcda.data.datasets import make_synthetic_scm
from gcda.data.preprocessing import to_pseudo_observations
from gcda.dependency.library import DependencyLibrary
from gcda.evaluation.graph_conditioning import dependence_strength_sweep, edge_removal_effect, is_monotonic
from gcda.evaluation.realism import (
    compare_marginals,
    compare_pairwise_dependence,
    energy_distance,
    gaussian_mmd,
    plot_marginals,
    plot_pairwise_scatter,
)
from gcda.generation.graph_sampler import GraphSampler, NodeSpec, node_spec_from_library

LIBRARY_PATH = Path(__file__).parent.parent / "outputs" / "dependency_library.json"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "t6_evaluation"


def main() -> None:
    if not LIBRARY_PATH.exists():
        raise SystemExit(f"{LIBRARY_PATH} not found; run scripts/build_dependency_library.py first")

    library = DependencyLibrary.load(LIBRARY_PATH)
    true_df, dag = make_synthetic_scm(n=5000, seed=1)
    edges = list(dag.edges)

    # Baseline keeps each node's *real* marginal (from the library) and only
    # swaps in baseline Gaussian dependence, so the comparison below isolates
    # what the learned dependence model contributes rather than conflating it
    # with marginal mismatch (synthetic_scm's marginals are close to, but not
    # exactly, standard normal - e.g. x4 = 0.6*x1 + 0.5*x2 + noise has
    # variance 0.86, not 1 - so using the library's real marginal here rather
    # than always falling back to a standard-normal baseline marginal matters).
    baseline_specs = {node: NodeSpec(marginal=library.get_marginal("synthetic_scm", node)) for node in dag.nodes}
    baseline_df = GraphSampler(dag, node_specs=baseline_specs).sample(n=5000, seed=0)
    node_specs = {
        node: node_spec_from_library(library, "synthetic_scm", node, list(dag.predecessors(node)))
        for node in dag.nodes
    }
    learned_df = GraphSampler(dag, node_specs=node_specs).sample(n=5000, seed=0)

    print("=== T6a.i marginals (quantile L1 distance, lower is better) ===")
    for name, sim_df in [("baseline", baseline_df), ("learned", learned_df)]:
        result = compare_marginals(true_df, sim_df)
        print(f"{name}: mean quantile_l1={result['quantile_l1'].mean():.4f}, "
              f"mean ks_stat={result['ks_stat'].mean():.4f}")

    print("\n=== T6a.ii pairwise dependence (mean |tau error|, lower is better) ===")
    for name, sim_df in [("baseline", baseline_df), ("learned", learned_df)]:
        result = compare_pairwise_dependence(true_df, sim_df, pairs=edges)
        print(f"{name}: mean_tau_abs_error={result['tau_abs_error'].mean():.4f}")

    print("\n=== T6a.iii distribution distance in U-space (lower is better) ===")
    true_u, _ = to_pseudo_observations(true_df)
    cols = list(dag.nodes)
    for name, sim_df in [("baseline", baseline_df), ("learned", learned_df)]:
        sim_u, _ = to_pseudo_observations(sim_df)
        e = energy_distance(true_u[cols].to_numpy(), sim_u[cols].to_numpy())
        m = gaussian_mmd(true_u[cols].to_numpy(), sim_u[cols].to_numpy())
        print(f"{name}: energy_distance={e:.5f}, gaussian_mmd={m:.5f}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plot_marginals(true_df, learned_df, list(dag.nodes), OUTPUT_DIR / "marginals")
    plot_pairwise_scatter(true_df, learned_df, edges, OUTPUT_DIR / "pairs")
    print(f"\nDiagnostic plots written to {OUTPUT_DIR}/")

    print("\n=== T6b graph-conditioning: removing an edge should collapse its dependence ===")
    removal = edge_removal_effect(dag, "x1", "x4", n=5000, seed=0)
    print(removal)

    print("\n=== T6b graph-conditioning: dependence strength should increase monotonically with rho ===")
    # x3 has a single parent (x1) in this DAG - dependence_strength_sweep requires that,
    # since the rho override only applies to the indegree-1 sampling path.
    sweep = dependence_strength_sweep(dag, "x1", "x3", rhos=[0.0, 0.3, 0.6, 0.9], n=5000, seed=0)
    print(sweep)
    print("monotonic:", is_monotonic([r["tau"] for r in sweep]))


if __name__ == "__main__":
    main()
