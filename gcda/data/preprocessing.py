"""T4b/T7c: missing-value handling, rank transform to U in (0, 1), and the inverse map back.

T7c extends this to discrete/categorical columns via `CategoricalMarginal` and
`to_pseudo_observations_mixed`: once continuized to U(0,1), discrete columns
plug into the exact same pairwise/conditional/graph-sampling machinery built
for continuous data in T4/T5, unchanged.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

_EPS = 1e-6


def handle_missing_values(df: pd.DataFrame, strategy: str = "drop") -> tuple[pd.DataFrame, dict]:
    """Handle missing values with a documented, simple strategy.

    strategy="drop": drop rows with any missing value.
    strategy="median": fill missing values with the column median.
    """
    if strategy not in ("drop", "median"):
        raise ValueError(f"Unknown strategy: {strategy!r}")

    missing_counts = df.isna().sum()
    if strategy == "drop":
        clean = df.dropna().reset_index(drop=True)
    else:
        clean = df.fillna(df.median(numeric_only=True))

    report = {
        "strategy": strategy,
        "n_rows_total": len(df),
        "n_rows_dropped": len(df) - len(clean) if strategy == "drop" else 0,
        "missing_counts": {c: int(v) for c, v in missing_counts.items() if v > 0},
    }
    return clean, report


@dataclass
class EmpiricalMarginal:
    """Empirical marginal distribution: rank-transform to U(0,1) and back.

    Fitted on a 1-D sample. `transform` maps original-scale values to
    pseudo-observations in (0, 1) via the empirical CDF; `inverse_transform`
    maps pseudo-observations back to original units via the empirical
    quantile function. The two are (approximate) inverses of each other,
    which is what T4b.iii asks for.
    """

    sorted_values_: np.ndarray = field(default=None, repr=False)
    plotting_positions_: np.ndarray = field(default=None, repr=False)

    def fit(self, x: np.ndarray) -> "EmpiricalMarginal":
        x = np.asarray(x, dtype=float)
        n = len(x)
        self.sorted_values_ = np.sort(x)
        # standard (n + 1) plotting positions avoid pseudo-observations at
        # exactly 0 or 1, which would blow up under e.g. a Gaussian ppf.
        self.plotting_positions_ = np.arange(1, n + 1) / (n + 1)
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        """Map original-scale values to U(0,1) pseudo-observations.

        Uses linear interpolation on the fitted empirical CDF, so it also
        works for values not seen during `fit` (they get clamped to the
        smallest/largest fitted plotting position).
        """
        x = np.asarray(x, dtype=float)
        return np.interp(x, self.sorted_values_, self.plotting_positions_)

    def inverse_transform(self, u: np.ndarray) -> np.ndarray:
        """Map U(0,1) pseudo-observations back to original units."""
        u = np.asarray(u, dtype=float)
        return np.interp(u, self.plotting_positions_, self.sorted_values_)


def to_pseudo_observations(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, EmpiricalMarginal]]:
    """Rank-transform every column of `df` to U(0,1), removing marginal effects.

    Returns the U-space DataFrame and a fitted `EmpiricalMarginal` per column
    so the mapping back to original units is available later (T4b.iii).
    """
    marginals: dict[str, EmpiricalMarginal] = {}
    u_data = {}
    for col in df.columns:
        values = df[col].to_numpy()
        marginal = EmpiricalMarginal().fit(values)
        marginals[col] = marginal
        u_data[col] = marginal.transform(values)
    return pd.DataFrame(u_data, index=df.index), marginals


@dataclass
class CategoricalMarginal:
    """Categorical/discrete marginal, continuized via jittering (T7c.i/ii).

    Discrete variables cause ties in ranks: many rows share the same
    category, so a plain rank transform can't separate them. The documented
    rule used here is the standard "continuization" trick for ordinal data:
    each observation of category k gets its own independent draw, uniform on
    the slice of (0, 1) that category's empirical probability mass occupies,
    rather than one shared rank. `inverse_transform` reverses this exactly by
    mapping U back to whichever category's slice it falls in (the discrete
    quantile map) - jittering only spreads out the within-category
    randomness needed to make the transform well-defined per observation, it
    does not lose information about which category was observed.

    Category order is fixed at fit time (sorted by string representation
    unless `categories` is given explicitly); for genuinely ordinal
    variables, pass `categories` in their natural order.
    """

    categories_: list = field(default=None, repr=False)
    cum_probs_: np.ndarray = field(default=None, repr=False)

    def fit(self, x: np.ndarray, categories: list | None = None) -> "CategoricalMarginal":
        counts = pd.Series(x).value_counts()
        self.categories_ = list(categories) if categories is not None else sorted(counts.index.tolist(), key=str)
        probs = np.array([counts.get(c, 0) for c in self.categories_], dtype=float)
        self.cum_probs_ = np.cumsum(probs / probs.sum())
        return self

    def transform(self, x: np.ndarray, rng: np.random.Generator | None = None) -> np.ndarray:
        """Jitter each observed category into its empirical-CDF slice of U(0,1)."""
        rng = rng if rng is not None else np.random.default_rng()
        index = {category: i for i, category in enumerate(self.categories_)}
        idx = np.array([index[v] for v in x])
        lower = np.where(idx == 0, 0.0, self.cum_probs_[idx - 1])
        upper = self.cum_probs_[idx]
        return lower + rng.uniform(size=len(x)) * (upper - lower)

    def inverse_transform(self, u: np.ndarray) -> np.ndarray:
        """Map U(0,1) back to categories via the discrete quantile map."""
        u = np.clip(np.asarray(u, dtype=float), _EPS, 1 - _EPS)
        idx = np.clip(np.searchsorted(self.cum_probs_, u, side="right"), 0, len(self.categories_) - 1)
        return np.array([self.categories_[i] for i in idx], dtype=object)


def to_pseudo_observations_mixed(
    df: pd.DataFrame,
    discrete_columns: list[str] | None = None,
    category_orders: dict[str, list] | None = None,
    seed: int | None = None,
) -> tuple[pd.DataFrame, dict[str, "EmpiricalMarginal | CategoricalMarginal"]]:
    """Like `to_pseudo_observations`, but for mixed continuous/discrete data (T7).

    Continuous columns use `EmpiricalMarginal`; discrete/categorical columns
    use the jittered `CategoricalMarginal`. Columns are auto-detected as
    discrete when their dtype isn't numeric (covers object/string/category/
    bool dtypes); pass `discrete_columns` explicitly for numerically-coded
    categoricals (e.g. integer category codes).

    `category_orders` (column -> ordered list of categories) fixes the
    category order used by `CategoricalMarginal` for the given columns,
    which matters for genuinely ordinal variables - without it, categories
    default to alphabetical order, which is wrong for e.g. a "low"/"medium"/
    "high" column (alphabetically "high" < "low" < "medium").
    """
    rng = np.random.default_rng(seed)
    if discrete_columns is None:
        discrete_columns = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
    discrete_columns = set(discrete_columns)
    category_orders = category_orders or {}

    marginals: dict[str, "EmpiricalMarginal | CategoricalMarginal"] = {}
    u_data = {}
    for col in df.columns:
        values = df[col].to_numpy()
        if col in discrete_columns:
            marginal = CategoricalMarginal().fit(values, categories=category_orders.get(col))
            u_data[col] = marginal.transform(values, rng=rng)
        else:
            marginal = EmpiricalMarginal().fit(values)
            u_data[col] = marginal.transform(values)
        marginals[col] = marginal
    return pd.DataFrame(u_data, index=df.index), marginals


def discrete_cdf_pairs(
    df: pd.DataFrame, marginals: dict[str, "EmpiricalMarginal | CategoricalMarginal"]
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    """Inputs for pyvinecopulib's *native* discrete copula likelihood.

    For every column returns F(x) (`upper`) and F(x-) (`lower`, the CDF just
    below the observed value) plus its variable type ("c"/"d"). For discrete
    columns the copula likelihood of an observation is the rectangle
    probability C(F(x), F(y)) - C(F(x-), F(y)) - ..., so no jittering is
    needed and no concordance is lost to ties (Genest & Neslehova, 2007).
    Continuous columns use their pseudo-observations for both.
    """
    upper, lower, var_types = {}, {}, {}
    for col in df.columns:
        m = marginals[col]
        if isinstance(m, CategoricalMarginal):
            index = {category: i for i, category in enumerate(m.categories_)}
            idx = np.array([index[v] for v in df[col].to_numpy()])
            upper[col] = m.cum_probs_[idx]
            lower[col] = np.where(idx == 0, 0.0, m.cum_probs_[idx - 1])
            var_types[col] = "d"
        else:
            u = m.transform(df[col].to_numpy())
            upper[col] = u
            lower[col] = u
            var_types[col] = "c"
    clip = lambda a: np.clip(a, _EPS, 1 - _EPS)  # noqa: E731
    return (pd.DataFrame({k: clip(v) for k, v in upper.items()}, index=df.index),
            pd.DataFrame({k: clip(v) for k, v in lower.items()}, index=df.index), var_types)
