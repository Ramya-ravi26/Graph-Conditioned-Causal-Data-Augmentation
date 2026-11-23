"""Random-forest conditional prototype (gcda/dependency/forest.py)."""

import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

from gcda.data.preprocessing import to_pseudo_observations, to_pseudo_observations_mixed
from gcda.dependency.forest import ForestConditional
from gcda.evaluation.discrete import cramers_v
from gcda.generation.graph_sampler import EdgeModel, GraphSampler, NodeSpec


def test_forest_reproduces_logical_or_interaction_that_copulas_miss():
    rng = np.random.default_rng(0)
    n = 6000
    a = rng.uniform(size=n) < 0.3
    b = rng.uniform(size=n) < 0.3
    c = np.where(a | b, "yes", "no")
    df = pd.DataFrame({"a": np.where(a, "yes", "no"), "b": np.where(b, "yes", "no"), "c": c})
    orders = {k: ["no", "yes"] for k in df}
    u, m = to_pseudo_observations_mixed(df, category_orders=orders, seed=0)
    fc = ForestConditional("c", ["a", "b"], marginal=m["c"]).fit(u)
    child = m["c"].inverse_transform(fc.sample(u[["a", "b"]].to_numpy(), seed=1))
    # OR is deterministic: the sampled child must equal a OR b almost everywhere
    assert (child == c).mean() > 0.99


def test_forest_reproduces_non_monotone_continuous_dependence():
    rng = np.random.default_rng(1)
    x = rng.normal(size=5000)
    y = x ** 2 + 0.3 * rng.normal(size=5000)        # rank correlation ~0, strong dependence
    u, m = to_pseudo_observations(pd.DataFrame({"x": x, "y": y}))
    fc = ForestConditional("y", ["x"], marginal=m["y"]).fit(u)
    y_sim = m["y"].inverse_transform(fc.sample(u[["x"]].to_numpy(), seed=2))
    assert abs(spearmanr(x, y)[0]) < 0.1
    # |x| vs y captures the U-shape: simulated data must reproduce it
    assert abs(kendalltau(np.abs(x), y_sim)[0] - kendalltau(np.abs(x), y)[0]) < 0.05


def test_forest_in_graph_sampler_single_and_multi_parent():
    rng = np.random.default_rng(2)
    n = 4000
    a = rng.normal(size=n)
    b = np.sin(2 * a) + 0.2 * rng.normal(size=n)
    c = np.where(a * b > 0, "pos", "neg")
    df = pd.DataFrame({"a": a, "b": b, "c": c})
    u, m = to_pseudo_observations_mixed(df, category_orders={"c": ["neg", "pos"]}, seed=0)
    dag = nx.DiGraph([("a", "b"), ("a", "c"), ("b", "c")])
    specs = {"a": NodeSpec(marginal=m["a"])}
    for node, ps in [("b", ["a"]), ("c", ["a", "b"])]:
        fc = ForestConditional(node, ps, marginal=m[node]).fit(u)
        specs[node] = NodeSpec(marginal=m[node], edge_model=EdgeModel(conditional_sampler=fc, parent_order=ps))
    sampler = GraphSampler(dag, node_specs=specs)
    gen = sampler.sample(n, seed=0)
    assert sampler.total_fallback_draws == 0
    assert set(gen["c"]) <= {"neg", "pos"}
    assert abs(cramers_v(gen["c"], np.sign(gen["a"] * gen["b"])) - cramers_v(df["c"], np.sign(df["a"] * df["b"]))) < 0.05


def test_forest_does_not_replay_training_rows():
    rng = np.random.default_rng(3)
    x = rng.normal(size=3000)
    y = x + rng.normal(size=3000)
    u, m = to_pseudo_observations(pd.DataFrame({"x": x, "y": y}))
    fc = ForestConditional("y", ["x"], marginal=m["y"]).fit(u)
    draws = fc.sample(u[["x"]].to_numpy(), seed=4)
    # leaf sampling returns training U-values, but not the row's own value most of the time
    assert (np.isclose(draws, u["y"].to_numpy())).mean() < 0.15
