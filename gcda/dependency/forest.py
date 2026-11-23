"""Random-forest conditional models: sample a child given its parents without copula assumptions.

Copula conditionals (pairwise h-inverse, vines) can only represent monotone
dependence along each variable's (category) order and approximate parent
interactions through the vine's simplifying assumption. On Insurance and Alarm
a sizeable share of strong edges is non-monotone and several CPTs are logical
interactions (e.g. OR), which is the main reason the copula generator falls
short of real data there (thesis Sec. 6.6). A forest has neither restriction.

Both models work in the same U-space as the rest of the pipeline, so they
plug into GraphSampler unchanged: parents enter as their U-values, the child's
U-value is returned and mapped through its stored marginal as usual.

* discrete child: RandomForestClassifier on the child's category index;
  a category is drawn from the predicted class probabilities and turned into
  a U-value uniform on that category's CDF slice (so inverse_transform
  returns exactly that category).
* continuous child: RandomForestRegressor on the child's U-value with
  *leaf sampling*: pick a random tree, find the leaf the parent values fall
  into, and return the U-value of a random training observation from that
  leaf (a quantile-regression-forest style conditional sampler, cf. the
  distributional random forests used by causalAssembly).

min_samples_leaf keeps leaves from collapsing onto single training rows, so
the sampler does not simply replay the training data.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

from gcda.data.preprocessing import CategoricalMarginal
from gcda.dependency.conditional import EPS


class ForestConditional:
    def __init__(self, child: str, parents: list[str], marginal=None, n_estimators: int = 100,
                 min_samples_leaf: int | None = None, max_features: float | str | None = 1.0,
                 random_state: int = 0, clip_eps: float = EPS):
        self.child = child
        self.parents = list(parents)
        self.marginal = marginal
        self.discrete = isinstance(marginal, CategoricalMarginal)
        self.n_estimators = n_estimators
        self.min_samples_leaf = min_samples_leaf if min_samples_leaf is not None else (10 if self.discrete else 20)
        self.max_features = max_features
        self.random_state = random_state
        self.clip_eps = clip_eps
        self.last_fallback_count_ = 0
        self.model_ = None

    # ------------------------------------------------------------------ fit
    def fit(self, u_df: pd.DataFrame) -> "ForestConditional":
        X = u_df[self.parents].to_numpy(float)
        y_u = u_df[self.child].to_numpy(float)
        kw = dict(n_estimators=self.n_estimators, min_samples_leaf=self.min_samples_leaf,
                  max_features=self.max_features, random_state=self.random_state, n_jobs=1)
        if self.discrete:
            y = self._category_index(y_u)
            self.model_ = RandomForestClassifier(**kw).fit(X, y)
        else:
            self.model_ = RandomForestRegressor(**kw).fit(X, y_u)
            self.train_y_ = y_u
            # per tree: training rows grouped by leaf (CSR layout) for O(1) leaf sampling
            self.leaf_index_ = []
            for est in self.model_.estimators_:
                leaves = est.apply(X)
                order = np.argsort(leaves, kind="stable")
                n_nodes = est.tree_.node_count
                counts = np.bincount(leaves, minlength=n_nodes)
                starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
                self.leaf_index_.append((order, starts, counts))
        return self

    def _category_index(self, u: np.ndarray) -> np.ndarray:
        cum = self.marginal.cum_probs_
        return np.clip(np.searchsorted(cum, np.clip(u, self.clip_eps, 1 - self.clip_eps), side="right"),
                       0, len(cum) - 1)

    # ------------------------------------------------------------------ sample
    def sample(self, u_parents: np.ndarray, seed: int | None = None) -> np.ndarray:
        if self.model_ is None:
            raise RuntimeError("ForestConditional must be fit() before sampling")
        rng = np.random.default_rng(seed)
        X = np.atleast_2d(np.asarray(u_parents, dtype=float))
        n = X.shape[0]
        self.last_fallback_count_ = 0
        if self.discrete:
            proba = self.model_.predict_proba(X)
            classes = self.model_.classes_
            cum = np.cumsum(proba, axis=1)
            draw = rng.uniform(size=(n, 1))
            k = classes[np.minimum((draw > cum).sum(axis=1), len(classes) - 1)]
            cp = self.marginal.cum_probs_
            lower = np.where(k == 0, 0.0, cp[np.maximum(k - 1, 0)])
            upper = cp[k]
            u = lower + rng.uniform(size=n) * (upper - lower)
        else:
            trees = rng.integers(0, len(self.model_.estimators_), size=n)
            u = np.empty(n)
            for t in np.unique(trees):
                rows = np.where(trees == t)[0]
                leaves = self.model_.estimators_[t].apply(X[rows])
                order, starts, counts = self.leaf_index_[t]
                pick = starts[leaves] + (rng.uniform(size=len(rows)) * counts[leaves]).astype(int)
                u[rows] = self.train_y_[order[pick]]
        return np.clip(u, self.clip_eps, 1 - self.clip_eps)
