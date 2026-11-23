import numpy as np
import pandas as pd

from gcda.data.preprocessing import (
    CategoricalMarginal,
    EmpiricalMarginal,
    handle_missing_values,
    to_pseudo_observations,
    to_pseudo_observations_mixed,
)


def test_handle_missing_values_drop():
    df = pd.DataFrame({"a": [1.0, 2.0, np.nan, 4.0], "b": [1, 2, 3, 4]})
    clean, report = handle_missing_values(df, strategy="drop")
    assert len(clean) == 3
    assert report["n_rows_dropped"] == 1
    assert report["missing_counts"] == {"a": 1}


def test_handle_missing_values_median():
    df = pd.DataFrame({"a": [1.0, 2.0, np.nan, 4.0], "b": [1, 2, 3, 4]})
    clean, report = handle_missing_values(df, strategy="median")
    assert len(clean) == 4
    assert clean["a"].isna().sum() == 0
    assert clean.loc[2, "a"] == 2.0  # median of [1,2,4]


def test_empirical_marginal_roundtrip():
    rng = np.random.default_rng(0)
    x = rng.normal(5, 2, size=1000)
    marginal = EmpiricalMarginal().fit(x)
    u = marginal.transform(x)
    assert np.all(u > 0) and np.all(u < 1)
    x_back = marginal.inverse_transform(u)
    assert np.allclose(x, x_back)


def test_to_pseudo_observations_is_uniform_and_preserves_row_order():
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"a": rng.normal(0, 1, 2000), "b": rng.exponential(2, 2000)})
    u_df, marginals = to_pseudo_observations(df)

    # roughly uniform marginals
    assert abs(u_df["a"].mean() - 0.5) < 0.02
    assert abs(u_df["b"].mean() - 0.5) < 0.02

    # row order preserved: largest raw value -> (near) largest U value
    assert u_df["a"].to_numpy().argmax() == df["a"].to_numpy().argmax()

    # marginals map back to (approximately) the original data
    x_back = marginals["a"].inverse_transform(u_df["a"].to_numpy())
    assert np.allclose(df["a"].to_numpy(), x_back)


def test_categorical_marginal_roundtrip_is_exact():
    rng = np.random.default_rng(0)
    x = rng.choice(["a", "b", "c"], size=2000, p=[0.5, 0.3, 0.2])
    marginal = CategoricalMarginal().fit(x)
    u = marginal.transform(x, rng=rng)

    assert np.all(u > 0) and np.all(u < 1)
    assert np.array_equal(marginal.inverse_transform(u), x)


def test_categorical_marginal_jitter_breaks_ties_within_category():
    rng = np.random.default_rng(0)
    x = np.array(["a"] * 100)
    marginal = CategoricalMarginal().fit(x)
    u = marginal.transform(x, rng=rng)
    # a single category still spans (0, 1) fully; jittering must not collapse
    # every observation onto one shared rank (the tie problem T7c.i solves).
    assert len(np.unique(u)) == 100


def test_to_pseudo_observations_mixed_uses_categorical_for_non_numeric_columns():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({
        "cont": rng.normal(size=1000),
        "cat": rng.choice(["x", "y"], size=1000),
    })
    u_df, marginals = to_pseudo_observations_mixed(df, seed=0)

    assert isinstance(marginals["cont"], EmpiricalMarginal)
    assert isinstance(marginals["cat"], CategoricalMarginal)
    assert u_df["cont"].between(0, 1).all()
    assert u_df["cat"].between(0, 1).all()

    decoded = marginals["cat"].inverse_transform(u_df["cat"].to_numpy())
    assert np.array_equal(decoded, df["cat"].to_numpy())


def test_to_pseudo_observations_mixed_preserves_dependence():
    rng = np.random.default_rng(0)
    n = 5000
    cont = rng.normal(size=n)
    # categorical variable whose value is driven by `cont`, so dependence should survive continuization
    cat = np.where(cont > 0, "high", "low")
    df = pd.DataFrame({"cont": cont, "cat": cat})

    u_df, _ = to_pseudo_observations_mixed(df, seed=0)
    from scipy.stats import kendalltau

    tau = kendalltau(u_df["cont"], u_df["cat"])[0]
    # sign depends on the (here alphabetical) default category order for
    # nominal categories - only the dependence *strength* is meaningful here.
    # (a continuous variable vs. its own median-split binary indicator has a
    # population tau of exactly 0.5; use a margin to absorb sampling noise.)
    assert abs(tau) > 0.45


def test_jitter_dilutes_tau_for_skewed_binary_variables_by_the_expected_factor():
    # Not a bug: jittering ties apart necessarily dilutes measured dependence
    # relative to tau-b (which excludes tied pairs from its denominator), and
    # the dilution is severe when either variable is a skewed binary split
    # (found while auditing why a naive Gaussian baseline sometimes beat the
    # "learned" model on ordinary Asia-network edges like smoke->lung: the
    # copula was correctly fitting the *diluted* jittered dependence, not
    # failing to fit the true one). The dilution factor is
    # sqrt((1 - tie_x) * (1 - tie_y)), tie_v = P(two random draws of v match).
    rng = np.random.default_rng(0)
    n = 20000
    p_x, p_y = 0.5, 0.06  # y mimics a rare binary indicator, e.g. Asia's "lung"
    latent = rng.multivariate_normal([0, 0], [[1, 0.6], [0.6, 1]], size=n)
    x = np.where(latent[:, 0] > np.quantile(latent[:, 0], 1 - p_x), "yes", "no")
    y = np.where(latent[:, 1] > np.quantile(latent[:, 1], 1 - p_y), "yes", "no")
    df = pd.DataFrame({"x": x, "y": y})

    from scipy.stats import kendalltau

    tau_b = kendalltau(df["x"] == "yes", df["y"] == "yes")[0]
    u_df, _ = to_pseudo_observations_mixed(df, seed=1)
    tau_jittered = kendalltau(u_df["x"], u_df["y"])[0]

    def tie_fraction(col):
        p = col.value_counts(normalize=True).to_numpy()
        return (p**2).sum()

    predicted = tau_b * np.sqrt((1 - tie_fraction(df["x"])) * (1 - tie_fraction(df["y"])))
    assert abs(tau_jittered - predicted) < 0.02
    assert tau_jittered < 0.5 * tau_b  # the dilution is substantial for this skew


def test_pseudo_observations_of_a_permuted_column_invert_to_the_same_permutation():
    # regression test for the scrambled-pseudo-observation bug (thesis Sec. 3.2/4.2):
    # transforming a permuted copy must give the permuted pseudo-observations, and
    # inverting must recover the permuted original values in that same order
    rng = np.random.default_rng(7)
    x = rng.gamma(2.0, size=1500)
    perm = rng.permutation(len(x))
    u_df, marginals = to_pseudo_observations(pd.DataFrame({"x": x}))
    u_perm, marginals_perm = to_pseudo_observations(pd.DataFrame({"x": x[perm]}))
    assert np.allclose(u_perm["x"].to_numpy(), u_df["x"].to_numpy()[perm])
    assert np.allclose(marginals_perm["x"].inverse_transform(u_perm["x"].to_numpy()), x[perm])
