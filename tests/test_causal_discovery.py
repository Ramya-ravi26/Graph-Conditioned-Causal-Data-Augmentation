import networkx as nx
import numpy as np
import pandas as pd

from gcda.evaluation.causal_discovery import (
    compare_causal_discovery,
    encode_categorical,
    run_pc,
    structural_hamming_distance,
)


def _v_structure_data(n=4000, seed=0):
    # A -> C <- B, A and B independent: a collider, the one local structure
    # PC can always fully orient from observational data (unlike an
    # unshielded chain A->B->C, which is Markov-equivalent to A<-B->C and
    # A<-B<-C and so is *correctly* left fully undirected by PC).
    rng = np.random.default_rng(seed)
    a = rng.normal(size=n)
    b = rng.normal(size=n)
    c = 0.7 * a + 0.7 * b + rng.normal(scale=0.3, size=n)
    df = pd.DataFrame({"A": a, "B": b, "C": c})
    dag = nx.DiGraph([("A", "C"), ("B", "C")])
    return df, dag


def test_run_pc_recovers_identifiable_v_structure_exactly():
    df, dag = _v_structure_data()
    cg = run_pc(df, indep_test="fisherz")
    assert structural_hamming_distance(dag, cg.G, list(df.columns)) == 0


def test_structural_hamming_distance_is_deterministic_given_the_same_data():
    df, dag = _v_structure_data()
    cg = run_pc(df, indep_test="fisherz")
    shd_self = structural_hamming_distance(dag, cg.G, list(df.columns))
    # running PC again on the same data must give the same graph and SHD
    cg2 = run_pc(df, indep_test="fisherz")
    assert structural_hamming_distance(dag, cg2.G, list(df.columns)) == shd_self


def test_encode_categorical_maps_to_expected_integer_codes():
    df = pd.DataFrame({"x": ["low", "high", "medium", "low"]})
    encoded = encode_categorical(df, {"x": ["low", "medium", "high"]})
    assert list(encoded["x"]) == [0, 2, 1, 0]


def test_compare_causal_discovery_reports_all_sources():
    df, dag = _v_structure_data()
    sim_dfs = {"copy": df.copy()}
    result = compare_causal_discovery(df, sim_dfs, dag, indep_test="fisherz")
    assert set(result["source"]) == {"true_data", "copy"}
    assert (result["shd_to_true_dag"] >= 0).all()
