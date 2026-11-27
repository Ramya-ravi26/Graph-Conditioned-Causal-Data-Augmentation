"""Chain / fork / collider conditional-independence checks (gcda/experiments/ci_checks.py)."""

import networkx as nx
import numpy as np

from gcda.experiments.ci_checks import (
    g_test,
    gcm_test,
    implied_in_full_dag,
    three_node_dag,
    triples,
)


def test_triples_finds_induced_chain_fork_collider_only():
    dag = nx.DiGraph([("a", "b"), ("b", "c"), ("b", "d"), ("e", "d"), ("a", "c")])
    found = set(triples(dag, max_per_type=100))
    assert ("chain", "a", "b", "d") in found          # a -> b -> d, a and d non-adjacent
    assert ("collider", "b", "d", "e") in found       # b -> d <- e
    assert ("fork", "c", "b", "d") in found           # c <- b -> d
    assert not any({x[1], x[3]} == {"a", "c"} for x in found)   # a - c adjacent: excluded
    assert set(three_node_dag("collider", "x", "y", "z").edges) == {("x", "y"), ("z", "y")}


def test_implied_statement_uses_d_separation_in_the_full_graph():
    dag = nx.DiGraph([("a", "b"), ("b", "c"), ("a", "d"), ("d", "c")])
    assert not implied_in_full_dag(dag, "chain", "a", "b", "c")   # a -> d -> c stays open
    assert implied_in_full_dag(nx.DiGraph([("a", "b"), ("b", "c")]), "chain", "a", "b", "c")


def test_g_test_keeps_level_under_conditional_independence_and_detects_dependence():
    rng = np.random.default_rng(0)
    rejections = 0
    for r in range(500):
        b = rng.integers(0, 3, 2000)
        a = (rng.uniform(size=2000) < 0.2 + 0.2 * b).astype(int)    # a depends on b
        c = (rng.uniform(size=2000) < 0.7 - 0.2 * b).astype(int)    # c depends on b only
        rejections += g_test(a, c, b)[0] < 0.05
    assert rejections / 500 < 0.08
    assert g_test(a, c)[0] < 0.05                                    # marginally dependent via b


def test_gcm_keeps_level_for_step_shaped_conditional_means():
    rng = np.random.default_rng(1)
    rejections = 0
    for r in range(100):
        b = rng.normal(size=3000)
        a = np.floor(3 * b) + rng.normal(size=3000)                  # step function of b
        c = (rng.uniform(size=3000) < 1 / (1 + np.exp(-np.round(2 * b)))).astype(float)
        rejections += gcm_test(a, c, b)[0] < 0.05
    assert rejections / 100 < 0.12


def test_gcm_keeps_level_when_b_repeats_values_like_leaf_sampling():
    rng = np.random.default_rng(2)
    pool = rng.normal(size=800)                                       # "training values" of b
    rejections = 0
    for r in range(100):
        idx = rng.integers(0, 800, 3000)
        b = pool[idx]                                                 # b re-uses pool values
        jag = rng.normal(size=800)                                    # jagged function of the value
        a = jag[idx] + rng.normal(size=3000)
        c = (rng.uniform(size=3000) < 1 / (1 + np.exp(-2 * jag[idx]))).astype(float)
        rejections += gcm_test(a, c, b)[0] < 0.05
    assert rejections / 100 < 0.12
