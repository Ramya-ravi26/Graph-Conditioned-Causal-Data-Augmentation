import numpy as np
import pandas as pd
from scipy.stats import norm

from gcda.dependency.conditional import ConditionalSampler


def _fit_gaussian_sampler(sigma, parent_names, n=15000, seed=0):
    """Fit a ConditionalSampler on data drawn from a known multivariate Gaussian
    copula with correlation matrix `sigma` (child is the last row/column)."""
    rng = np.random.default_rng(seed)
    d = sigma.shape[0]
    z = rng.multivariate_normal(np.zeros(d), sigma, size=n)
    u = norm.cdf(z)
    u_df = pd.DataFrame(u, columns=[*parent_names, "x"])

    sampler = ConditionalSampler(child="x", parents=parent_names)
    sampler.fit(u_df)
    return sampler


def _fit_trivariate_gaussian_sampler(n=15000, seed=0):
    sigma = np.array([[1.0, 0.3, 0.5], [0.3, 1.0, 0.4], [0.5, 0.4, 1.0]])
    return _fit_gaussian_sampler(sigma, ["p1", "p2"], n=n, seed=seed), sigma


def _gaussian_conditional_mean_var(sigma, parent_z):
    """Closed-form conditional mean/variance of the last variable given the others."""
    k = len(parent_z)
    s11 = sigma[:k, :k]
    s12 = sigma[:k, k]
    s22 = sigma[k, k]
    s11_inv = np.linalg.inv(s11)
    mean = s12 @ s11_inv @ np.asarray(parent_z)
    var = s22 - s12 @ s11_inv @ s12
    return mean, var


def test_conditional_sampler_matches_gaussian_theory():
    sampler, sigma = _fit_trivariate_gaussian_sampler()

    m = 8000
    for p1_u, p2_u in [(0.8, 0.2), (0.2, 0.8), (0.5, 0.5)]:
        mean, var = _gaussian_conditional_mean_var(sigma, norm.ppf([p1_u, p2_u]))
        u_parents = np.column_stack([np.full(m, p1_u), np.full(m, p2_u)])
        x_u_sim = sampler.sample(u_parents, seed=42)
        x_z_sim = norm.ppf(x_u_sim)

        assert abs(x_z_sim.mean() - mean) < 0.05
        assert abs(x_z_sim.var() - var) < 0.05
        assert sampler.last_fallback_count_ == 0


def test_conditional_sampler_matches_gaussian_theory_with_three_parents():
    # T5/T6/T7 all sample real data at indegree 3 (Insurance) and claim the
    # underlying "child listed first in the vine order" trick generalizes
    # beyond 2 parents (verified ad hoc during development, never committed
    # as a test) - this pins that claim down against closed-form Gaussian
    # conditionals for a genuine 4-variable (3-parent) vine.
    rng = np.random.default_rng(1)
    a = rng.normal(size=(4, 4))
    sigma = a @ a.T
    sigma /= np.outer(np.sqrt(np.diag(sigma)), np.sqrt(np.diag(sigma)))
    sampler = _fit_gaussian_sampler(sigma, ["p1", "p2", "p3"], n=30000, seed=2)

    m = 15000
    for p_u in [[0.8, 0.2, 0.5], [0.2, 0.8, 0.9], [0.5, 0.5, 0.5]]:
        mean, var = _gaussian_conditional_mean_var(sigma, norm.ppf(p_u))
        u_parents = np.tile(p_u, (m, 1))
        x_u_sim = sampler.sample(u_parents, seed=42)
        x_z_sim = norm.ppf(np.clip(x_u_sim, 1e-6, 1 - 1e-6))

        assert abs(x_z_sim.mean() - mean) < 0.05
        assert abs(x_z_sim.var() - var) < 0.05
        assert sampler.last_fallback_count_ == 0


def test_conditional_sampler_handles_boundary_inputs_without_crashing():
    sampler, _ = _fit_trivariate_gaussian_sampler()
    edge_cases = np.array([[0.0, 1.0], [1.0, 0.0], [0.0, 0.0], [1.0, 1.0]])

    out = sampler.sample(edge_cases, seed=1)

    assert out.shape == (4,)
    assert np.all(np.isfinite(out))
    assert np.all((out > 0) & (out < 1))


def test_conditional_sampler_serialization_roundtrip():
    sampler, _ = _fit_trivariate_gaussian_sampler(n=2000)
    restored = ConditionalSampler.from_dict(sampler.to_dict())

    u_parents = np.column_stack([np.full(500, 0.7), np.full(500, 0.3)])
    original = sampler.sample(u_parents, seed=5)
    reloaded = restored.sample(u_parents, seed=5)

    assert np.allclose(original, reloaded)
