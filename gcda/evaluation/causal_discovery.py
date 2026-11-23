"""Closing the loop on the project's actual goal: is the generated data usable
as training data for a real causal discovery algorithm?

T1-T7 validate statistical realism (marginals, dependence, distribution
distance) but never checked the motivating use case itself - "many ML
methods for graph discovery need lots of training data." This module runs
the PC algorithm (causal-learn) on both the true data and our generated
data for a *known* DAG, and compares each recovered graph to the ground
truth via Structural Hamming Distance (SHD): the number of edge
insertions/deletions/reversals needed to turn one graph into the other,
lower is better.
"""

import networkx as nx
import numpy as np
import pandas as pd
from causallearn.graph.Dag import Dag
from causallearn.graph.GraphNode import GraphNode
from causallearn.graph.SHD import SHD
from causallearn.search.ConstraintBased.PC import pc


def _to_causal_learn_dag(true_dag: nx.DiGraph, node_names: list[str]) -> Dag:
    nodes = [GraphNode(name) for name in node_names]
    node_by_name = {node.get_name(): node for node in nodes}
    dag = Dag(nodes)
    for a, b in true_dag.edges:
        dag.add_directed_edge(node_by_name[a], node_by_name[b])
    return dag


def run_pc(df: pd.DataFrame, indep_test: str = "fisherz", alpha: float = 0.05):
    """Run the PC algorithm and return causal-learn's CausalGraph (a CPDAG estimate).

    indep_test="fisherz" for continuous data, "chisq" or "gsq" for discrete
    (categorical) data encoded as integer codes.
    """
    node_names = list(df.columns)
    data = df.to_numpy().astype(float)
    return pc(data, alpha=alpha, indep_test=indep_test, node_names=node_names, show_progress=False)


def run_ges(df: pd.DataFrame, discrete: bool = False):
    """Greedy Equivalence Search (causal-learn) with BIC (continuous) or BDeu (discrete) score.

    Returns an object with a `.G` attribute (the estimated CPDAG), like `run_pc`.
    """
    from types import SimpleNamespace

    from causallearn.search.ScoreBased.GES import ges

    score = "local_score_BDeu" if discrete else "local_score_BIC"
    record = ges(df.to_numpy().astype(float), score_func=score, node_names=list(df.columns))
    return SimpleNamespace(G=record["G"])


def encode_categorical(df: pd.DataFrame, category_orders: dict[str, list]) -> pd.DataFrame:
    """Map categorical columns to integer codes (0..K-1) for chisq/gsq independence tests."""
    out = {}
    for col in df.columns:
        if col in category_orders:
            index = {c: i for i, c in enumerate(category_orders[col])}
            out[col] = df[col].map(index)
        else:
            out[col] = df[col]
    return pd.DataFrame(out)


def structural_hamming_distance(true_dag: nx.DiGraph, estimated_graph, node_names: list[str]) -> int:
    """SHD between a known DAG and a causal-learn CausalGraph/Dag estimate."""
    truth = _to_causal_learn_dag(true_dag, node_names)
    return SHD(truth, estimated_graph).get_shd()


def compare_causal_discovery(
    true_df: pd.DataFrame,
    sim_dfs: dict[str, pd.DataFrame],
    true_dag: nx.DiGraph,
    indep_test: str = "fisherz",
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Run PC on the true data and each named simulated dataset, report SHD to the true DAG.

    `sim_dfs` maps a label (e.g. "baseline", "learned") to a DataFrame with
    the same columns as `true_df`, already encoded numerically (use
    `encode_categorical` first for discrete data).
    """
    node_names = list(true_df.columns)
    rows = []
    for label, df in {"true_data": true_df, **sim_dfs}.items():
        cg = run_pc(df, indep_test=indep_test, alpha=alpha)
        rows.append({
            "source": label,
            "shd_to_true_dag": structural_hamming_distance(true_dag, cg.G, node_names),
            "n_edges_found": int((cg.G.graph != 0).sum() / 2),
        })
    return pd.DataFrame(rows)
