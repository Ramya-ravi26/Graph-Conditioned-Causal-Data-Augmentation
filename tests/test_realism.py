import numpy as np
import pandas as pd

from gcda.evaluation.realism import (
    compare_marginals,
    compare_pairwise_dependence,
    energy_distance,
    gaussian_mmd,
    plot_marginals,
    plot_pairwise_scatter,
)


def _gaussian_df(rng, n, rho=0.0, loc=0.0, scale=1.0, cols=("a", "b")):
    cov = np.array([[1.0, rho], [rho, 1.0]])
    z = rng.multivariate_normal([0, 0], cov, size=n) * scale + loc
    return pd.DataFrame(z, columns=list(cols))


def test_compare_marginals_small_error_for_same_distribution():
    rng = np.random.default_rng(0)
    true_df = _gaussian_df(rng, 3000)
    sim_df = _gaussian_df(rng, 3000)

    result = compare_marginals(true_df, sim_df)
    assert set(result["column"]) == {"a", "b"}
    assert (result["quantile_l1"] < 0.15).all()
    assert (result["ks_pvalue"] > 0.01).all()


def test_compare_pairwise_dependence_detects_mismatch():
    rng = np.random.default_rng(0)
    true_df = _gaussian_df(rng, 5000, rho=0.8)
    sim_df = _gaussian_df(rng, 5000, rho=0.0)

    result = compare_pairwise_dependence(true_df, sim_df)
    assert len(result) == 1
    assert result.iloc[0]["tau_abs_error"] > 0.3


def test_energy_distance_and_mmd_grow_with_distributional_difference():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(1000, 3))
    y_same = rng.normal(size=(1000, 3))
    y_shifted = rng.normal(loc=3.0, size=(1000, 3))

    e_same = energy_distance(x, y_same)
    e_shifted = energy_distance(x, y_shifted)
    assert 0 <= e_same < 0.2
    assert e_shifted > e_same

    m_same = gaussian_mmd(x, y_same)
    m_shifted = gaussian_mmd(x, y_shifted)
    assert 0 <= m_same < 0.05
    assert m_shifted > m_same


def test_plot_helpers_write_expected_files(tmp_path):
    rng = np.random.default_rng(0)
    true_df = _gaussian_df(rng, 500, rho=0.5)
    sim_df = _gaussian_df(rng, 500, rho=0.5)

    plot_marginals(true_df, sim_df, ["a", "b"], tmp_path / "marginals")
    assert (tmp_path / "marginals" / "marginal_a.png").exists()
    assert (tmp_path / "marginals" / "marginal_b.png").exists()

    plot_pairwise_scatter(true_df, sim_df, [("a", "b")], tmp_path / "pairs")
    assert (tmp_path / "pairs" / "pair_a_b.png").exists()
