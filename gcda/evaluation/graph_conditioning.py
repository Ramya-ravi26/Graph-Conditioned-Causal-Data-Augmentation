"""T6b: does changing the graph change conditional dependencies in the expected direction?

Two checks: (1) removing an edge should collapse the corresponding pairwise
dependence towards zero relative to having it present, and (2) strengthening
an edge's copula parameter should monotonically increase the resulting
dependence (Kendall's tau) between that parent and child.
"""

import networkx as nx
import numpy as np
from scipy.stats import kendalltau

from gcda.generation.graph_sampler import EdgeModel, GraphSampler, NodeSpec, baseline_bicop


def edge_removal_effect(
    dag_with_edge: nx.DiGraph, parent: str, child: str, n: int = 5000, seed: int = 0
) -> dict:
    """Compare tau(parent, child) between the given DAG and the same DAG with that edge removed."""
    df_with = GraphSampler(dag_with_edge).sample(n=n, seed=seed)
    tau_with = kendalltau(df_with[parent], df_with[child])[0]

    dag_without = dag_with_edge.copy()
    dag_without.remove_edge(parent, child)
    df_without = GraphSampler(dag_without).sample(n=n, seed=seed)
    tau_without = kendalltau(df_without[parent], df_without[child])[0]

    return {
        "parent": parent, "child": child,
        "tau_with_edge": tau_with, "tau_without_edge": tau_without,
        "expected_direction_confirmed": abs(tau_with) > abs(tau_without),
    }


def dependence_strength_sweep(
    dag: nx.DiGraph, parent: str, child: str, rhos: list[float], n: int = 5000, seed: int = 0
) -> list[dict]:
    """Sample the same DAG with a 1-parent baseline Gaussian copula of varying strength
    on the (parent, child) edge; returns the resulting tau for each rho so monotonicity
    (stronger rho -> stronger |tau|) can be checked.

    `child` must have exactly one parent in `dag` (equal to `parent`): the varying-rho
    override is only wired up for the indegree-1 sampling path, so a multi-parent child
    would silently ignore it and ues the baseline conditional sampler for every rho.
    """
    parents_in_dag = list(dag.predecessors(child))
    if parents_in_dag != [parent]:
        raise ValueError(
            f"dependence_strength_sweep requires {child!r} to have exactly one parent "
            f"({parent!r}) in the DAG, found {parents_in_dag}"
        )

    results = []
    for rho in rhos:
        node_specs = {child: NodeSpec(edge_model=EdgeModel(bicop=baseline_bicop(rho)))}
        df = GraphSampler(dag, node_specs=node_specs).sample(n=n, seed=seed)
        tau = kendalltau(df[parent], df[child])[0]
        results.append({"rho": rho, "tau": tau})
    return results


def is_monotonic(values: list[float]) -> bool:
    diffs = np.diff(values)
    return bool(np.all(diffs >= -1e-9)) or bool(np.all(diffs <= 1e-9))
