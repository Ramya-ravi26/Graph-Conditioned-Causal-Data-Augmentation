"""T4c: fit pairwise dependence models (AIC/BIC family selection) and store diagnostics."""

from concurrent.futures import ThreadPoolExecutor
from itertools import combinations

import numpy as np
import pandas as pd
import pyvinecopulib as pv

from gcda.dependency.families import DEFAULT_BICOP_FAMILIES


def fit_bicop(
    u_i: np.ndarray,
    u_j: np.ndarray,
    family_set: list[pv.BicopFamily] = DEFAULT_BICOP_FAMILIES,
    selection_criterion: str = "bic",
    u_i_minus: np.ndarray | None = None,
    u_j_minus: np.ndarray | None = None,
    var_types: tuple[str, str] = ("c", "c"),
) -> tuple[pv.Bicop, dict]:
    """Fit a single bivariate copula on two U(0,1) columns, selecting the family via AIC/BIC.

    With `var_types` containing "d", the native discrete likelihood is used:
    `u_*` must then be F(x) and `u_*_minus` F(x-) (see
    `preprocessing.discrete_cdf_pairs`). The returned copula is the latent
    (continuous) copula, which is what the samplers need.
    """
    controls = pv.FitControlsBicop(family_set=family_set, selection_criterion=selection_criterion)
    if "d" in var_types:
        u = np.column_stack([u_i, u_j, u_i_minus, u_j_minus])
        fitted = pv.Bicop(var_types=list(var_types))
        fitted.select(u, controls)
        cop = pv.Bicop(family=fitted.family, rotation=fitted.rotation, parameters=fitted.parameters)
        aic, bic = fitted.aic(u), fitted.bic(u)
    else:
        u = np.column_stack([u_i, u_j])
        cop = pv.Bicop()
        cop.select(u, controls)
        aic, bic = cop.aic(u), cop.bic(u)

    diagnostics = {
        "family": cop.family.name,
        "rotation": cop.rotation,
        "parameters": cop.parameters.tolist(),
        "tau": cop.tau,
        "aic": aic,
        "bic": bic,
        "n": len(u_i),
        "var_types": list(var_types),
    }
    return cop, diagnostics


def build_pairwise_library(
    u_df: pd.DataFrame,
    dataset_name: str,
    pairs: list[tuple[str, str]] | None = None,
    family_set: list[pv.BicopFamily] = DEFAULT_BICOP_FAMILIES,
    selection_criterion: str = "bic",
    n_jobs: int = 1,
    u_minus_df: pd.DataFrame | None = None,
    var_types: dict[str, str] | None = None,
) -> list[dict]:
    """Fit pairwise dependence models for many variable pairs and collect metadata.

    Defaults to every unordered pair of columns in `u_df` (O(p^2) fits); pass
    `pairs` (e.g. only a graph's edges) to restrict it for large p. Pairs are
    independent, so `n_jobs > 1` fits them in a thread pool; results are
    identical to the sequential run and returned in the same order. Failures
    on a given pair are recorded (with an `error` field) rather than aborting
    the whole run.
    """
    if pairs is None:
        pairs = list(combinations(u_df.columns, 2))

    def fit_one(pair: tuple[str, str]) -> dict:
        var_i, var_j = pair
        entry = {"dataset": dataset_name, "var_i": var_i, "var_j": var_j}
        try:
            vt = (var_types or {}).get(var_i, "c"), (var_types or {}).get(var_j, "c")
            native = u_minus_df is not None and "d" in vt
            _, diagnostics = fit_bicop(
                u_df[var_i].to_numpy(),
                u_df[var_j].to_numpy(),
                family_set=family_set,
                selection_criterion=selection_criterion,
                u_i_minus=u_minus_df[var_i].to_numpy() if native else None,
                u_j_minus=u_minus_df[var_j].to_numpy() if native else None,
                var_types=vt if native else ("c", "c"),
            )
            entry.update(diagnostics)
        except Exception as exc:  # noqa: BLE001 - keep building the library on a bad pair
            entry["error"] = str(exc)
        return entry

    if n_jobs > 1:
        with ThreadPoolExecutor(max_workers=n_jobs) as pool:
            return list(pool.map(fit_one, pairs))
    return [fit_one(pair) for pair in pairs]


def top_k_partners(pairwise_entries: list[dict], target: str, k: int = 2) -> list[str]:
    """Rank a target variable's pairwise partners by |Kendall's tau| and return the top k."""
    scored = []
    for entry in pairwise_entries:
        if "error" in entry:
            continue
        if entry["var_i"] == target:
            scored.append((abs(entry["tau"]), entry["var_j"]))
        elif entry["var_j"] == target:
            scored.append((abs(entry["tau"]), entry["var_i"]))
    scored.sort(reverse=True)
    return [name for _, name in scored[:k]]
