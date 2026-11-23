"""T7d: evaluation for discrete/categorical data.

i.   category frequencies and joint contingency sanity checks.
ii.  dependence measures suitable for discrete variables: (bias-corrected)
     Cramer's V and normalized mutual information.
iii. stability and runtime: `measure_generation_stability` records wall-clock
     time and how many fallback events (T4d/T5c.iv) were triggered. The
     pipeline uses immediate fallback rather than retries (a broken model
     logs a warning and falls back to an independent draw once, rather than
     re-attempting the same fit), so "failure rate" here means the fraction
     of fallback events raised during a sampling run.
"""

import time
import warnings
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency


def compare_category_frequencies(true_df: pd.DataFrame, sim_df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Per-column category-frequency realism: max absolute proportion difference
    and total variation distance between true and simulated frequency tables."""
    columns = columns or list(true_df.columns)
    rows = []
    for col in columns:
        true_freq = true_df[col].value_counts(normalize=True)
        sim_freq = sim_df[col].value_counts(normalize=True)
        categories = sorted(set(true_freq.index) | set(sim_freq.index), key=str)
        true_p = np.array([true_freq.get(c, 0.0) for c in categories])
        sim_p = np.array([sim_freq.get(c, 0.0) for c in categories])
        rows.append({
            "column": col,
            "n_categories": len(categories),
            "max_abs_diff": float(np.max(np.abs(true_p - sim_p))),
            "total_variation_distance": float(0.5 * np.sum(np.abs(true_p - sim_p))),
        })
    return pd.DataFrame(rows)


def joint_contingency_distance(true_df: pd.DataFrame, sim_df: pd.DataFrame, col_a: str, col_b: str) -> dict:
    """Total variation distance between the true and simulated joint (col_a, col_b) contingency tables."""
    true_ct = pd.crosstab(true_df[col_a], true_df[col_b], normalize=True)
    sim_ct = pd.crosstab(sim_df[col_a], sim_df[col_b], normalize=True)
    all_idx = sorted(set(true_ct.index) | set(sim_ct.index), key=str)
    all_cols = sorted(set(true_ct.columns) | set(sim_ct.columns), key=str)
    true_aligned = true_ct.reindex(index=all_idx, columns=all_cols, fill_value=0.0)
    sim_aligned = sim_ct.reindex(index=all_idx, columns=all_cols, fill_value=0.0)
    tvd = float(0.5 * np.abs(true_aligned.to_numpy() - sim_aligned.to_numpy()).sum())
    return {"var_a": col_a, "var_b": col_b, "total_variation_distance": tvd}


def cramers_v(x: np.ndarray, y: np.ndarray) -> float:
    """Bias-corrected Cramer's V (Bergsma, 2013) for two categorical arrays."""
    table = pd.crosstab(pd.Series(x), pd.Series(y))
    n = table.to_numpy().sum()
    if n == 0 or min(table.shape) < 2:
        return 0.0
    chi2 = chi2_contingency(table, correction=False)[0]
    phi2 = chi2 / n
    r, k = table.shape
    phi2_corr = max(0.0, phi2 - (k - 1) * (r - 1) / (n - 1))
    r_corr = r - (r - 1) ** 2 / (n - 1)
    k_corr = k - (k - 1) ** 2 / (n - 1)
    denom = min(k_corr - 1, r_corr - 1)
    return float(np.sqrt(phi2_corr / denom)) if denom > 0 else 0.0


def normalized_mutual_information(x: np.ndarray, y: np.ndarray) -> float:
    from sklearn.metrics import normalized_mutual_info_score

    return float(normalized_mutual_info_score(x, y))


def compare_discrete_dependence(
    true_df: pd.DataFrame, sim_df: pd.DataFrame, pairs: list[tuple[str, str]] | None = None
) -> pd.DataFrame:
    """Per-pair discrete dependence realism: true vs. simulated Cramer's V and normalized MI."""
    pairs = pairs or list(combinations(true_df.columns, 2))
    rows = []
    for a, b in pairs:
        v_true = cramers_v(true_df[a], true_df[b])
        v_sim = cramers_v(sim_df[a], sim_df[b])
        mi_true = normalized_mutual_information(true_df[a], true_df[b])
        mi_sim = normalized_mutual_information(sim_df[a], sim_df[b])
        rows.append({
            "var_i": a, "var_j": b,
            "cramers_v_true": v_true, "cramers_v_sim": v_sim, "cramers_v_abs_error": abs(v_true - v_sim),
            "nmi_true": mi_true, "nmi_sim": mi_sim, "nmi_abs_error": abs(mi_true - mi_sim),
        })
    return pd.DataFrame(rows)


def measure_generation_stability(sampler, n: int, seed: int = 0) -> tuple[pd.DataFrame, dict]:
    """Sample from `sampler` (a GraphSampler) once, recording wall-clock time,
    fallback events and fallback draws.

    `n_fallback_events` counts `FallbackWarning`s only (an earlier version
    counted every UserWarning, so unrelated library deprecation warnings could
    inflate it). `n_fallback_draws` comes from the sampler's own per-node
    counters, and `n_marginal_drift_nodes` counts nodes flagged by a
    `MarginalDriftWarning`.
    """
    from gcda.dependency.conditional import FallbackWarning
    from gcda.generation.graph_sampler import MarginalDriftWarning

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        t0 = time.time()
        df = sampler.sample(n=n, seed=seed)
        elapsed = time.time() - t0

    fallback_events = [w for w in caught if issubclass(w.category, FallbackWarning)]
    drift_events = [w for w in caught if issubclass(w.category, MarginalDriftWarning)]
    n_draws = int(sum(getattr(sampler, "fallback_counts_", {}).values()))
    n_nodes = len(sampler.dag.nodes)
    metrics = {
        "n": n,
        "elapsed_sec": elapsed,
        "n_fallback_events": len(fallback_events),
        "fallback_event_rate": len(fallback_events) / n_nodes,
        "n_fallback_draws": n_draws,
        "fallback_draw_rate": n_draws / (n * n_nodes),
        "n_marginal_drift_nodes": len(drift_events),
    }
    return df, metrics
