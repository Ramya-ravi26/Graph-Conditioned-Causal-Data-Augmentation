"""T6a: does the generated data look realistic?

i.   compare_marginals: do quantiles/histograms match per variable?
ii.  compare_pairwise_dependence: do Kendall/Spearman dependencies match per pair?
iii. energy_distance / gaussian_mmd: do simple distribution distances improve vs a baseline?

Distances in (iii) are computed on rank-transformed U(0,1) data (pseudo-observations)
rather than raw units, since marginal realism is already covered by (i) and the
whole point of this project is dependence-structure realism, which is what U-space
distances isolate; U-space also keeps every variable on the same [0,1] scale so a
multivariate distance isn't dominated by whichever column happens to have large units.
"""

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from scipy.stats import kendalltau, ks_2samp, spearmanr


def compare_marginals(true_df: pd.DataFrame, sim_df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Per-column marginal realism: KS statistic, decile quantile L1 distance, mean/std."""
    columns = columns or list(true_df.columns)
    quantile_levels = np.linspace(0.1, 0.9, 9)
    rows = []
    for col in columns:
        true_x = true_df[col].to_numpy()
        sim_x = sim_df[col].to_numpy()
        ks_stat, ks_pvalue = ks_2samp(true_x, sim_x)
        quantile_l1 = float(np.mean(np.abs(np.quantile(true_x, quantile_levels) - np.quantile(sim_x, quantile_levels))))
        rows.append({
            "column": col,
            "ks_stat": ks_stat,
            "ks_pvalue": ks_pvalue,
            "quantile_l1": quantile_l1,
            "mean_true": true_x.mean(), "mean_sim": sim_x.mean(),
            "std_true": true_x.std(), "std_sim": sim_x.std(),
        })
    return pd.DataFrame(rows)


def plot_marginals(true_df: pd.DataFrame, sim_df: pd.DataFrame, columns: list[str], out_dir: str | Path) -> None:
    """Overlaid true-vs-simulated histograms, one PNG per column."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for col in columns:
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.hist(true_df[col], bins=30, alpha=0.5, density=True, label="true")
        ax.hist(sim_df[col], bins=30, alpha=0.5, density=True, label="simulated")
        ax.set_title(f"marginal: {col}")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_dir / f"marginal_{col}.png", dpi=120)
        plt.close(fig)


def compare_pairwise_dependence(
    true_df: pd.DataFrame, sim_df: pd.DataFrame, pairs: list[tuple[str, str]] | None = None
) -> pd.DataFrame:
    """Per-pair dependence realism: true vs. simulated Kendall's tau and Spearman's rho."""
    pairs = pairs or list(combinations(true_df.columns, 2))
    rows = []
    for a, b in pairs:
        tau_true = kendalltau(true_df[a], true_df[b])[0]
        tau_sim = kendalltau(sim_df[a], sim_df[b])[0]
        rho_true = spearmanr(true_df[a], true_df[b])[0]
        rho_sim = spearmanr(sim_df[a], sim_df[b])[0]
        rows.append({
            "var_i": a, "var_j": b,
            "tau_true": tau_true, "tau_sim": tau_sim, "tau_abs_error": abs(tau_true - tau_sim),
            "rho_true": rho_true, "rho_sim": rho_sim, "rho_abs_error": abs(rho_true - rho_sim),
        })
    return pd.DataFrame(rows)


def plot_pairwise_scatter(true_df: pd.DataFrame, sim_df: pd.DataFrame, pairs: list[tuple[str, str]], out_dir: str | Path) -> None:
    """Side-by-side true-vs-simulated scatter plots, one PNG per pair."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for a, b in pairs:
        fig, axes = plt.subplots(1, 2, figsize=(9, 4))
        axes[0].scatter(true_df[a], true_df[b], alpha=0.3, s=8)
        axes[0].set_title(f"true: {a} vs {b}")
        axes[1].scatter(sim_df[a], sim_df[b], alpha=0.3, s=8)
        axes[1].set_title(f"simulated: {a} vs {b}")
        fig.tight_layout()
        fig.savefig(out_dir / f"pair_{a}_{b}.png", dpi=120)
        plt.close(fig)


def _subsample(x: np.ndarray, max_n: int, rng: np.random.Generator) -> np.ndarray:
    if len(x) <= max_n:
        return x
    idx = rng.choice(len(x), size=max_n, replace=False)
    return x[idx]


def energy_distance(x: np.ndarray, y: np.ndarray, max_n: int = 500, seed: int = 0, unbiased: bool = False) -> float:
    """Energy distance between two multivariate samples (Szekely & Rizzo, 2013).

    E = 2*E|X-Y| - E|X-X'| - E|Y-Y'|, using Euclidean distance. O(n^2), so both
    samples are subsampled to `max_n` points. The default (`unbiased=False`) is
    the V-statistic that includes the zero diagonal of the within-sample
    distance matrices (the values reported in the thesis sweep table);
    `unbiased=True` excludes the diagonal (U-statistic), which is centred at
    0 when both samples come from the same distribution.
    """
    rng = np.random.default_rng(seed)
    x = _subsample(np.atleast_2d(x), max_n, rng)
    y = _subsample(np.atleast_2d(y), max_n, rng)
    return _energy(x, y, unbiased)


def _within_mean(d: np.ndarray, unbiased: bool) -> float:
    if not unbiased:
        return float(d.mean())
    n = d.shape[0]
    return float((d.sum() - np.trace(d)) / (n * (n - 1)))


def _energy(x: np.ndarray, y: np.ndarray, unbiased: bool) -> float:
    return float(2 * cdist(x, y).mean() - _within_mean(cdist(x, x), unbiased) - _within_mean(cdist(y, y), unbiased))


def gaussian_mmd(x: np.ndarray, y: np.ndarray, max_n: int = 500, seed: int = 0, unbiased: bool = False,
                 bandwidth: float | None = None) -> float:
    """Squared MMD (Gretton et al., 2012) with an RBF kernel (median-distance bandwidth).

    `unbiased=True` gives the unbiased U-statistic estimator (diagonal terms
    excluded); the default biased V-statistic matches the thesis sweep table.
    """
    rng = np.random.default_rng(seed)
    x = _subsample(np.atleast_2d(x), max_n, rng)
    y = _subsample(np.atleast_2d(y), max_n, rng)
    if bandwidth is None:
        bandwidth = _median_bandwidth(x, y)
    return _mmd(x, y, bandwidth, unbiased)


def _median_bandwidth(x: np.ndarray, y: np.ndarray) -> float:
    combined = np.vstack([x, y])
    pairwise = cdist(combined, combined)
    median_dist = np.median(pairwise[pairwise > 0])
    return float(median_dist) if median_dist > 0 else 1.0


def _mmd(x: np.ndarray, y: np.ndarray, bandwidth: float, unbiased: bool) -> float:
    def kernel(a, b):
        return np.exp(-cdist(a, b) ** 2 / (2 * bandwidth ** 2))

    return float(_within_mean(kernel(x, x), unbiased) + _within_mean(kernel(y, y), unbiased) - 2 * kernel(x, y).mean())


def permutation_test(statistic, x: np.ndarray, y: np.ndarray, n_permutations: int = 200, max_n: int = 500,
                     seed: int = 0) -> dict:
    """Two-sample permutation test for `energy_distance` or `gaussian_mmd`.

    Both samples are subsampled to `max_n` once, the unbiased statistic is
    computed, and the pooled sample is re-split `n_permutations` times.
    Returns the observed statistic and the permutation p-value (with the +1
    correction, so it is never exactly 0).
    """
    rng = np.random.default_rng(seed)
    x = _subsample(np.atleast_2d(x), max_n, rng)
    y = _subsample(np.atleast_2d(y), max_n, rng)
    if statistic is gaussian_mmd:
        bw = _median_bandwidth(x, y)

        def stat(a, b):
            return _mmd(a, b, bw, True)
    elif statistic is energy_distance:
        def stat(a, b):
            return _energy(a, b, True)
    else:
        stat = statistic
    observed = stat(x, y)
    pooled = np.vstack([x, y])
    nx_ = len(x)
    exceed = 0
    for _ in range(n_permutations):
        idx = rng.permutation(len(pooled))
        if stat(pooled[idx[:nx_]], pooled[idx[nx_:]]) >= observed:
            exceed += 1
    return {"statistic": observed, "p_value": (exceed + 1) / (n_permutations + 1), "n_permutations": n_permutations}
