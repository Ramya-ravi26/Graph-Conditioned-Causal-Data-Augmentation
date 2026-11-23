import networkx as nx
import numpy as np
import pandas as pd
import pytest
from scipy.stats import kendalltau

from gcda.data.datasets import make_synthetic_scm
from gcda.data.preprocessing import to_pseudo_observations
from gcda.dependency.library import DependencyLibrary
from gcda.dependency.pairwise import build_pairwise_library
from gcda.dependency.conditional import ConditionalSampler
from gcda.generation.graph_sampler import (
    EdgeModel,
    GraphSampler,
    NodeSpec,
    _bicop_from_pairwise_entry,
    node_spec_from_library,
)


def test_rejects_cyclic_graph():
    with pytest.raises(ValueError, match="DAG"):
        GraphSampler(nx.DiGraph([("A", "B"), ("B", "A")]))


def test_rejects_graph_exceeding_max_indegree():
    dag = nx.DiGraph([("A", "X"), ("B", "X"), ("C", "X")])
    with pytest.raises(ValueError, match="indegree"):
        GraphSampler(dag, max_indegree=2)


def test_baseline_chain_reproduces_target_correlation():
    dag = nx.DiGraph([("A", "B"), ("B", "C")])
    df = GraphSampler(dag).sample(n=20000, seed=0)

    expected_tau = (2 / np.pi) * np.arcsin(0.5)  # baseline rho=0.5 Gaussian copula
    assert abs(kendalltau(df["A"], df["B"])[0] - expected_tau) < 0.02
    assert abs(kendalltau(df["B"], df["C"])[0] - expected_tau) < 0.02


def test_baseline_two_parent_node():
    dag = nx.DiGraph()
    dag.add_nodes_from(["P1", "P2", "X"])
    dag.add_edges_from([("P1", "X"), ("P2", "X")])
    df = GraphSampler(dag).sample(n=20000, seed=1)

    assert abs(kendalltau(df["P1"], df["P2"])[0]) < 0.03
    expected_tau = (2 / np.pi) * np.arcsin(0.5)
    assert abs(kendalltau(df["P1"], df["X"])[0] - expected_tau) < 0.03
    assert abs(kendalltau(df["P2"], df["X"])[0] - expected_tau) < 0.03


def test_three_parent_extension_beyond_core_indegree():
    dag = nx.DiGraph([("A", "X"), ("B", "X"), ("C", "X")])
    df = GraphSampler(dag, max_indegree=3).sample(n=1000, seed=0)
    assert df.shape == (1000, 4)


def _build_synthetic_scm_library():
    df, dag = make_synthetic_scm(n=5000, seed=1)
    u_df, marginals = to_pseudo_observations(df)
    library = DependencyLibrary()
    library.add_marginals("scm", marginals)
    library.add_pairwise(build_pairwise_library(u_df, dataset_name="scm"))
    sampler = ConditionalSampler(child="x4", parents=["x1", "x2"]).fit(u_df)
    library.add_conditional("scm", sampler)
    return library, df, dag


def test_graph_sampler_reproduces_synthetic_scm_dependence_structure():
    library, true_df, dag = _build_synthetic_scm_library()

    node_specs = {
        node: node_spec_from_library(library, "scm", node, list(dag.predecessors(node)))
        for node in dag.nodes
    }
    sim_df = GraphSampler(dag, node_specs=node_specs).sample(n=5000, seed=99)

    for a, b in [("x1", "x3"), ("x1", "x4"), ("x2", "x4"), ("x4", "x5")]:
        tau_true = kendalltau(true_df[a], true_df[b])[0]
        tau_sim = kendalltau(sim_df[a], sim_df[b])[0]
        assert abs(tau_true - tau_sim) < 0.05


def test_node_spec_from_library_raises_on_missing_pair():
    library, _, dag = _build_synthetic_scm_library()
    with pytest.raises(KeyError):
        node_spec_from_library(library, "scm", "x1", ["nonexistent"])


class _BrokenBicop:
    def hinv1(self, u):
        raise RuntimeError("boom")


def test_indegree1_falls_back_on_bicop_failure():
    dag = nx.DiGraph([("A", "B")])
    node_specs = {"B": NodeSpec(edge_model=EdgeModel(bicop=_BrokenBicop()))}
    sampler = GraphSampler(dag, node_specs=node_specs)

    with pytest.warns(UserWarning, match="failed"):
        df = sampler.sample(n=500, seed=0)
    assert df.shape == (500, 2)
    assert np.all(np.isfinite(df.to_numpy()))


class _NonFiniteBicop:
    def hinv1(self, u):
        out = np.full(len(u), 0.5)
        out[0] = np.nan
        return out


def test_indegree1_falls_back_on_non_finite_output():
    dag = nx.DiGraph([("A", "B")])
    node_specs = {"B": NodeSpec(edge_model=EdgeModel(bicop=_NonFiniteBicop()))}
    sampler = GraphSampler(dag, node_specs=node_specs)

    with pytest.warns(UserWarning, match="non-finite"):
        df = sampler.sample(n=500, seed=0)
    assert np.all(np.isfinite(df.to_numpy()))


def test_bicop_from_pairwise_entry_handles_independence():
    # "indep" family has no parameters; a pairwise entry's .tolist() collapses
    # pv.Bicop's required (0, 0)-shaped array to a bare [], which used to crash
    # reconstruction (hit for real when reconstructing the Asia network, T7).
    entry = {"family": "indep", "rotation": 0, "parameters": []}
    bicop = _bicop_from_pairwise_entry(entry)
    assert bicop.family.name == "indep"


def test_hinv1_direction_matches_empirical_conditional_quantiles_of_clayton():
    # thesis Sec. 3.4: which argument of h1/hinv1 is the conditioning value was
    # checked by binning a large Clayton sample near a fixed conditioning value
    import pyvinecopulib as pv

    from gcda.compat import bicop_sample

    cop = pv.Bicop(family=pv.BicopFamily.clayton, parameters=np.array([[3.0]]))
    u = bicop_sample(cop, 600000, seeds=[1, 2, 3])
    u1 = 0.2
    near = u[np.abs(u[:, 0] - u1) < 0.002, 1]
    for q in (0.1, 0.5, 0.9):
        model_q = cop.hinv1(np.array([[u1, q]]))[0]
        wrong_q = cop.hinv1(np.array([[q, u1]]))[0]  # arguments swapped
        empirical = np.quantile(near, q)
        assert abs(empirical - model_q) < 0.025
        assert abs(empirical - wrong_q) > 4 * abs(empirical - model_q) or abs(empirical - wrong_q) > 0.1
