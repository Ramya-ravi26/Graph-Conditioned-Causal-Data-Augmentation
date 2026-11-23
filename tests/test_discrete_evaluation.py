import networkx as nx
import numpy as np
import pandas as pd
import pytest

from gcda.evaluation.discrete import (
    compare_category_frequencies,
    compare_discrete_dependence,
    cramers_v,
    joint_contingency_distance,
    measure_generation_stability,
    normalized_mutual_information,
)
from gcda.generation.graph_sampler import GraphSampler


def test_compare_category_frequencies_zero_for_identical_data():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"a": rng.choice(["x", "y", "z"], size=1000, p=[0.5, 0.3, 0.2])})
    result = compare_category_frequencies(df, df)
    assert result.loc[0, "max_abs_diff"] == 0.0
    assert result.loc[0, "total_variation_distance"] == 0.0


def test_compare_category_frequencies_detects_shift():
    rng = np.random.default_rng(0)
    true_df = pd.DataFrame({"a": rng.choice(["x", "y"], size=2000, p=[0.9, 0.1])})
    sim_df = pd.DataFrame({"a": rng.choice(["x", "y"], size=2000, p=[0.5, 0.5])})
    result = compare_category_frequencies(true_df, sim_df)
    assert result.loc[0, "max_abs_diff"] > 0.3


def test_joint_contingency_distance_zero_for_identical_data():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"a": rng.choice(["x", "y"], size=1000), "b": rng.choice(["p", "q"], size=1000)})
    result = joint_contingency_distance(df, df, "a", "b")
    assert result["total_variation_distance"] == 0.0


def test_cramers_v_detects_dependence():
    rng = np.random.default_rng(0)
    n = 5000
    x = rng.choice(["a", "b"], size=n)
    y_dependent = x  # perfectly dependent
    y_independent = rng.choice(["a", "b"], size=n)

    assert cramers_v(x, y_dependent) > 0.9
    assert cramers_v(x, y_independent) < 0.1


def test_normalized_mutual_information_detects_dependence():
    rng = np.random.default_rng(0)
    n = 5000
    x = rng.choice(["a", "b"], size=n)
    y_dependent = x
    y_independent = rng.choice(["a", "b"], size=n)

    assert normalized_mutual_information(x, y_dependent) > 0.9
    assert normalized_mutual_information(x, y_independent) < 0.05


def test_compare_discrete_dependence_reports_both_measures():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"a": rng.choice(["x", "y"], size=2000), "b": rng.choice(["p", "q"], size=2000)})
    result = compare_discrete_dependence(df, df, pairs=[("a", "b")])
    assert result.loc[0, "cramers_v_abs_error"] == 0.0
    assert result.loc[0, "nmi_abs_error"] == pytest.approx(0.0, abs=1e-9)


def test_measure_generation_stability_reports_no_fallback_on_clean_baseline():
    dag = nx.DiGraph([("A", "B")])
    sampler = GraphSampler(dag)
    df, metrics = measure_generation_stability(sampler, n=500, seed=0)

    assert df.shape == (500, 2)
    assert metrics["n_fallback_events"] == 0
    assert metrics["elapsed_sec"] >= 0


class _BrokenBicop:
    def hinv1(self, u):
        raise RuntimeError("boom")


def test_measure_generation_stability_counts_fallback_events():
    from gcda.generation.graph_sampler import EdgeModel, NodeSpec

    dag = nx.DiGraph([("A", "B")])
    node_specs = {"B": NodeSpec(edge_model=EdgeModel(bicop=_BrokenBicop()))}
    sampler = GraphSampler(dag, node_specs=node_specs)

    _, metrics = measure_generation_stability(sampler, n=500, seed=0)
    assert metrics["n_fallback_events"] >= 1
