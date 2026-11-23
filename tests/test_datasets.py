import networkx as nx

from gcda.data.datasets import (
    load_asia,
    load_insurance,
    make_discretized_sachs,
    make_mixed_synthetic_scm,
)


def test_load_asia_returns_valid_dag_and_binary_data():
    df, dag, category_orders = load_asia(n_samples=500, seed=0)
    assert nx.is_directed_acyclic_graph(dag)
    assert max(dict(dag.in_degree()).values()) == 2
    assert list(df.columns) == list(dag.nodes)
    assert df.shape == (500, 8)
    for col in df.columns:
        assert df[col].nunique() == 2
        assert set(df[col].unique()) <= set(category_orders[col])


def test_load_insurance_returns_valid_dag_with_categorical_data():
    df, dag, category_orders = load_insurance(n_samples=300, seed=0)
    assert nx.is_directed_acyclic_graph(dag)
    assert max(dict(dag.in_degree()).values()) <= 4  # within GraphSampler's stated extension range
    assert list(df.columns) == list(dag.nodes)
    assert df.shape[0] == 300


def test_load_insurance_category_orders_match_true_ordinal_order():
    # regression test: these must NOT be alphabetically sorted (e.g. alphabetical
    # RiskAversion would be Adventurous/Cautious/Normal/Psychopath, which has no
    # relation to the true order below and would corrupt concordance for any
    # copula fit involving it).
    _, _, category_orders = load_insurance(n_samples=10, seed=0)
    assert category_orders["SocioEcon"] == ["Prole", "Middle", "UpperMiddle", "Wealthy"]
    assert category_orders["RiskAversion"] == ["Psychopath", "Adventurous", "Normal", "Cautious"]
    assert category_orders["CarValue"] == ["FiveThou", "TenThou", "TwentyThou", "FiftyThou", "Million"]


def test_make_discretized_sachs_bins_into_requested_categories():
    df, category_orders = make_discretized_sachs(n_bins=3)
    assert set(df["praf"].unique()) <= {"low", "medium", "high"}
    assert category_orders["praf"] == ["low", "medium", "high"]
    # roughly balanced tercile bins
    counts = df["praf"].value_counts(normalize=True)
    assert (counts > 0.25).all()


def test_make_mixed_synthetic_scm_has_continuous_and_discrete_columns():
    df, dag, category_orders = make_mixed_synthetic_scm(n=2000, seed=0)
    assert nx.is_directed_acyclic_graph(dag)
    assert set(category_orders) == {"x2", "x5"}
    assert df["x1"].dtype.kind == "f"
    assert set(df["x2"].unique()) <= {"low", "medium", "high"}
    assert set(df["x5"].unique()) <= {"no", "yes"}
    # x5 has one discrete parent (x2) and one continuous parent (x4) - the
    # mixed-type 2-parent edge this dataset exists to exercise.
    assert set(dag.predecessors("x5")) == {"x2", "x4"}


def test_sachs_observational_subset_and_condition_boundaries():
    import numpy as np

    from gcda.data.datasets import SACHS_OBSERVATIONAL_ROWS, load_sachs

    full = load_sachs()
    obs = load_sachs(observational_only=True)
    assert len(full) == 7466 and len(obs) == SACHS_OBSERVATIONAL_ROWS == 853
    # the file concatenates the nine Sachs et al. conditions (853, 902, 911, 723,
    # 810, 799, 848, 913, 707 rows); every boundary shows a clear distribution
    # shift, which is what justifies taking the first 853 rows as one condition.
    x = np.log1p(full.to_numpy())
    bounds = np.cumsum([853, 902, 911, 723, 810, 799, 848, 913])

    def jump(i, w=200):
        return np.abs(x[i - w:i].mean(0) - x[i:i + w].mean(0)).sum()

    inside = [jump(i) for i in (400, 1300, 2200, 3000, 3800, 4600, 5400, 6300, 7100)]
    assert min(jump(int(b)) for b in bounds) > np.median(inside)


def test_sachs_consensus_dag_has_mek_with_three_parents():
    from gcda.data.datasets import sachs_consensus_dag

    dag = sachs_consensus_dag()
    assert dag.number_of_edges() == 17
    assert dag.in_degree("pmek") == 3


def test_registry_loads_every_dataset_name():
    from gcda.data.registry import DATASET_NAMES, load_dataset

    for name in DATASET_NAMES:
        df, dag, orders = load_dataset(name, n=200, seed=0) if name not in ("sachs", "sachs_observational", "uci_diabetes", "discretized_sachs") else load_dataset(name)
        assert len(df) > 0
