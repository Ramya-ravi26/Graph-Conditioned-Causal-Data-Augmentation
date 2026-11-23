"""Conditional sampling for multi-parent nodes composed from *pairwise* building blocks.

``ConditionalSampler`` (conditional.py) fits a dedicated vine for one specific
``child | parents`` triple on one dataset, so it only exists for parent sets
that were present when the library was built. To reuse learned *pairwise*
dependencies for a multi-parent node that never existed in any source dataset
(or whose edges come from different datasets), this module composes the
conditional density of the child from one bivariate copula per incoming edge:

    c(u_C | u_P1, ..., u_Pk)  ∝  prod_j c_j(u_C, u_Pj)

This is exact when the parents are conditionally independent given the child
in copula space (a star-shaped vine truncated after the first tree, the
"copula Bayesian network" local density of Elidan, 2010) and an approximation
otherwise. It deliberately does NOT encode any parent-parent dependence: the
parents' joint distribution is whatever the surrounding graph generates, which
is what a transplanted causal mechanism should do.

Sampling inverts the normalized conditional CDF numerically on a fixed grid
that is uniform in normal-score space (dense in both tails).
"""

import warnings

import numpy as np
import pyvinecopulib as pv
from scipy.stats import norm

from gcda.dependency.conditional import EPS, FallbackWarning

_Z_GRID = np.linspace(-5.5, 5.5, 801)


class PairwiseProductConditional:
    """Sample ``child | parents`` from a product of per-edge bivariate copulas.

    ``edges`` is a list of ``(bicop, child_is_first)`` in the same order as
    ``parents``: ``child_is_first`` says whether the child occupies the
    copula's first column (asymmetric/rotated families care about this).
    """

    def __init__(self, child: str, parents: list[str], edges: list[tuple[pv.Bicop, bool]], clip_eps: float = EPS):
        if len(edges) != len(parents):
            raise ValueError("need exactly one bivariate copula per parent")
        self.child = child
        self.parents = list(parents)
        self.edges = edges
        self.clip_eps = clip_eps
        self.last_fallback_count_ = 0
        grid = norm.cdf(_Z_GRID)
        self.grid_ = np.clip(grid, clip_eps, 1 - clip_eps)

    def _log_density_on_grid(self, u_parents: np.ndarray) -> np.ndarray:
        n, m = u_parents.shape[0], len(self.grid_)
        log_dens = np.zeros((n, m))
        g = np.broadcast_to(self.grid_, (n, m)).ravel()
        for j, (bicop, child_is_first) in enumerate(self.edges):
            p = np.repeat(u_parents[:, j], m)
            pts = np.column_stack([g, p]) if child_is_first else np.column_stack([p, g])
            dens = bicop.pdf(pts).reshape(n, m)
            log_dens += np.log(np.maximum(dens, 1e-300))
        return log_dens

    def sample(self, u_parents: np.ndarray, seed: int | None = None) -> np.ndarray:
        rng = np.random.default_rng(seed)
        u_parents = np.clip(np.atleast_2d(np.asarray(u_parents, dtype=float)), self.clip_eps, 1 - self.clip_eps)
        n = u_parents.shape[0]
        self.last_fallback_count_ = 0
        w = rng.uniform(self.clip_eps, 1 - self.clip_eps, size=n)
        out = np.empty(n)
        # chunk to bound memory (n x grid)
        for start in range(0, n, 2000):
            sl = slice(start, start + 2000)
            log_dens = self._log_density_on_grid(u_parents[sl])
            log_dens -= log_dens.max(axis=1, keepdims=True)
            dens = np.exp(log_dens)
            # trapezoid CDF over the u-grid (density is w.r.t. u)
            du = np.diff(self.grid_)
            seg = 0.5 * (dens[:, 1:] + dens[:, :-1]) * du
            cdf = np.concatenate([np.zeros((dens.shape[0], 1)), np.cumsum(seg, axis=1)], axis=1)
            total = cdf[:, -1:]
            ok = np.isfinite(total[:, 0]) & (total[:, 0] > 0)
            cdf = np.where(ok[:, None], cdf / np.where(total > 0, total, 1.0), 0.0)
            draws = np.array([np.interp(wi, ci, self.grid_) for wi, ci in zip(w[sl], cdf)])
            draws[~ok] = rng.uniform(self.clip_eps, 1 - self.clip_eps, size=int((~ok).sum()))
            self.last_fallback_count_ += int((~ok).sum())
            out[sl] = draws
        if self.last_fallback_count_:
            warnings.warn(
                f"PairwiseProductConditional({self.child}|{self.parents}): "
                f"{self.last_fallback_count_}/{n} degenerate rows, independent fallback used",
                FallbackWarning,
            )
        return np.clip(out, self.clip_eps, 1 - self.clip_eps)
