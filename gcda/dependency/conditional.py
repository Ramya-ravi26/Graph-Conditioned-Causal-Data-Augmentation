"""T4d: conditional sampler for X | parents, built on a small vine copula.

Sampling recipe (verified against the closed-form Gaussian conditional on
synthetic data before writing this module): put the child variable *first*
in the D-vine order. Empirically, `RVineStructure.from_order([v1, ..., vd])`
processes variables in the *reverse* of that list internally (v_d is
unconditional, v_1 is conditioned on everything else) — so listing the
child first makes it the fully-conditioned variable. To then draw
child | parents = observed values:

  1. Forward Rosenblatt-transform a row with the observed parent U-values
     and an arbitrary placeholder for the child column.
  2. Overwrite the (transformed) child column with fresh iid U(0,1) draws.
  3. Apply the inverse Rosenblatt transform; the child column of the result
     is the conditional sample, and the parent columns reconstruct exactly.
"""

import warnings

import numpy as np
import pandas as pd
import pyvinecopulib as pv

from gcda.dependency.families import DEFAULT_BICOP_FAMILIES

EPS = 1e-6


class FallbackWarning(UserWarning):
    """Emitted whenever a sampling step falls back to an independent U(0,1) draw.

    A dedicated subclass lets callers count genuine fallback events without
    also counting unrelated library deprecation warnings.
    """


class ConditionalSampler:
    """Sample a child variable conditional on 1-2 (core) or more parents."""

    def __init__(
        self,
        child: str,
        parents: list[str],
        family_set: list[pv.BicopFamily] = DEFAULT_BICOP_FAMILIES,
        selection_criterion: str = "bic",
        clip_eps: float = EPS,
    ):
        self.clip_eps = clip_eps
        self.child = child
        self.parents = list(parents)
        self.family_set = family_set
        self.selection_criterion = selection_criterion
        self.vine_: pv.Vinecop | None = None
        self.last_fallback_count_ = 0

    def fit(self, u_df: pd.DataFrame, u_minus_df: pd.DataFrame | None = None,
            var_types: dict[str, str] | None = None) -> "ConditionalSampler":
        """Fit the vine on pseudo-observations.

        With `u_minus_df` and `var_types` (see `preprocessing.discrete_cdf_pairs`)
        discrete columns use the native discrete likelihood instead of
        jittered pseudo-observations; the stored vine is the latent
        continuous vine with the selected pair-copulas, used for sampling.
        """
        columns = [self.child, *self.parents]
        data = u_df[columns].to_numpy()
        d = len(columns)
        # child listed first -> ends up last/fully-conditioned in the vine's
        # internal processing order (see module docstring).
        structure = pv.RVineStructure.from_order(list(range(1, d + 1)))
        controls = pv.FitControlsVinecop(
            family_set=self.family_set, selection_criterion=self.selection_criterion
        )
        types = [(var_types or {}).get(c, "c") for c in columns]
        if u_minus_df is not None and "d" in types:
            fitted = pv.Vinecop.from_structure(structure=structure, var_types=types)
            fitted.select(np.column_stack([data, u_minus_df[columns].to_numpy()]), controls)
            pair_copulas = [
                [pv.Bicop(family=b.family, rotation=b.rotation, parameters=b.parameters) for b in tree]
                for tree in fitted.pair_copulas
            ]
            self.vine_ = pv.Vinecop.from_structure(structure=structure, pair_copulas=pair_copulas)
            self.var_types_ = types
            return self
        self.vine_ = pv.Vinecop.from_structure(structure=structure)
        self.vine_.select(data, controls)
        self.var_types_ = ["c"] * d
        return self

    def sample(self, u_parents: np.ndarray, seed: int | None = None) -> np.ndarray:
        """Draw one child U-value per row of `u_parents` (shape (n, n_parents))."""
        if self.vine_ is None:
            raise RuntimeError("ConditionalSampler must be fit() before sampling")

        u_parents = np.atleast_2d(np.asarray(u_parents, dtype=float))
        n = u_parents.shape[0]
        rng = np.random.default_rng(seed)
        self.last_fallback_count_ = 0

        # Stability guard: clip to keep every U away from the 0/1 boundary,
        # where inverse-CDF-style computations can blow up.
        eps = self.clip_eps
        u_parents = np.clip(u_parents, eps, 1 - eps)

        try:
            u_obs = np.column_stack([np.full(n, 0.5), u_parents])
            u_rosen = self.vine_.rosenblatt(u_obs)
            u_final = u_rosen
            u_final[:, 0] = rng.uniform(eps, 1 - eps, size=n)
            v_final = self.vine_.inverse_rosenblatt(u_final)
            child_u = np.clip(v_final[:, 0], eps, 1 - eps)
        except Exception as exc:  # noqa: BLE001 - fall back rather than abort a sampling run
            warnings.warn(
                f"ConditionalSampler({self.child}|{self.parents}) failed ({exc!r}); "
                "falling back to independent sampling for this batch.",
                FallbackWarning,
            )
            self.last_fallback_count_ = n
            return rng.uniform(eps, 1 - eps, size=n)

        bad = ~np.isfinite(child_u)
        n_bad = int(bad.sum())
        if n_bad:
            warnings.warn(
                f"ConditionalSampler({self.child}|{self.parents}): {n_bad}/{n} "
                "non-finite draws, falling back to independent sampling for those rows.",
                FallbackWarning,
            )
            child_u[bad] = rng.uniform(eps, 1 - eps, size=n_bad)
            self.last_fallback_count_ = n_bad
        return child_u

    def to_dict(self) -> dict:
        if self.vine_ is None:
            raise RuntimeError("ConditionalSampler must be fit() before serializing")
        return {
            "child": self.child,
            "parents": self.parents,
            "selection_criterion": self.selection_criterion,
            "vine_json": self.vine_.to_json(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConditionalSampler":
        sampler = cls(child=data["child"], parents=data["parents"], selection_criterion=data["selection_criterion"])
        sampler.vine_ = pv.Vinecop.from_json(data["vine_json"])
        return sampler
