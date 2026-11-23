import networkx as nx
import pytest

from gcda.evaluation.graph_conditioning import (
    dependence_strength_sweep,
    edge_removal_effect,
    is_monotonic,
)


def test_edge_removal_collapses_dependence():
    dag = nx.DiGraph([("P", "X"), ("P", "C")])
    result = edge_removal_effect(dag, "P", "X", n=8000, seed=0)

    assert result["expected_direction_confirmed"]
    assert abs(result["tau_with_edge"]) > 0.2
    assert abs(result["tau_without_edge"]) < 0.05


def test_dependence_strength_sweep_is_monotonic_in_rho():
    dag = nx.DiGraph([("P", "X")])
    results = dependence_strength_sweep(dag, "P", "X", rhos=[0.0, 0.3, 0.6, 0.9], n=8000, seed=1)

    taus = [r["tau"] for r in results]
    assert is_monotonic(taus)
    assert taus[-1] > taus[0] + 0.3


def test_dependence_strength_sweep_rejects_multi_parent_child():
    dag = nx.DiGraph([("P1", "X"), ("P2", "X")])
    with pytest.raises(ValueError, match="one parent"):
        dependence_strength_sweep(dag, "P1", "X", rhos=[0.0, 0.5], n=1000, seed=0)
