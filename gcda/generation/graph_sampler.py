"""T5: sample an n x p dataset for a user-specified DAG.

Building blocks come from the T4 dependency library:
  - indegree 0 (root): draw U(0,1) and map through a marginal (a learned
    marginal, or a standard-normal baseline if none is supplied).
  - indegree 1: sample the child conditional on its parent using a fitted
    `pv.Bicop` (from the T4 pairwise library, or a baseline Gaussian copula)
    via its h-function inverse.
  - indegree >= 2: sample via a T4 `ConditionalSampler` vine fitted for that
    exact parent set, or via a `PairwiseProductConditional` composed from the
    per-edge pairwise copulas, or a baseline Gaussian vine if neither is given.

Every node's sampling step is wrapped in a try/except: on failure (or any
non-finite output) it emits a `FallbackWarning` and falls back to an
independent U(0,1) draw. Fallback draws are counted per node in
``GraphSampler.fallback_counts_`` and summarized in ``diagnostics_``.
"""

import warnings
from dataclasses import dataclass, field

import networkx as nx
import numpy as np
import pandas as pd
import pyvinecopulib as pv
from scipy.stats import kstest, norm, rankdata

from gcda.data.preprocessing import EmpiricalMarginal
from gcda.dependency.composed import PairwiseProductConditional
from gcda.dependency.conditional import EPS, ConditionalSampler, FallbackWarning
from gcda.dependency.library import DependencyLibrary

CORE_MAX_INDEGREE = 2
DEFAULT_BASELINE_RHO = 0.5


class MarginalDriftWarning(UserWarning):
    """A node's generated U-values are far from uniform, so mapping them through
    the stored marginal will NOT reproduce that marginal. Typical cause: a
    multi-parent model whose implied parent dependence differs from the
    dependence of the parents actually generated in this graph."""


@dataclass
class EdgeModel:
    """How to sample a node given its parent(s)."""

    bicop: pv.Bicop | None = None  # used when the node has exactly 1 parent
    bicop_parent_is_first: bool = True  # column convention of `bicop` (see hinv1/hinv2 below)
    conditional_sampler: ConditionalSampler | PairwiseProductConditional | None = None  # >= 2 parents
    # graph-node names of the parents, in the column order `conditional_sampler` expects;
    # None -> use the sampler's own `parents` attribute if it matches, else the DAG's order
    parent_order: list[str] | None = None
    source: str = "learned"


@dataclass
class NodeSpec:
    marginal: EmpiricalMarginal | None = None  # None -> standard-normal baseline marginal
    edge_model: EdgeModel | None = None  # None -> baseline Gaussian dependence
    notes: list[str] = field(default_factory=list)


def baseline_marginal() -> EmpiricalMarginal:
    """Standard normal marginal, used when no learned marginal is supplied."""
    grid = np.linspace(1e-4, 1 - 1e-4, 2000)
    marginal = EmpiricalMarginal()
    marginal.plotting_positions_ = grid
    marginal.sorted_values_ = norm.ppf(grid)
    return marginal


def baseline_bicop(rho: float = DEFAULT_BASELINE_RHO) -> pv.Bicop:
    """Simple baseline dependence for a 1-parent edge: fixed-correlation Gaussian copula (T5c.i)."""
    return pv.Bicop(family=pv.BicopFamily.gaussian, parameters=np.array([[rho]]))


def valid_baseline_rho(n_parents: int, rho: float = DEFAULT_BASELINE_RHO) -> float:
    """Largest per-parent correlation <= `rho` that keeps the baseline valid.

    The baseline puts correlation rho between the child and each of k mutually
    independent parents; that correlation matrix is positive definite only if
    k * rho^2 < 1. With rho = 0.5 this fails at k = 4 (singular: the child
    becomes a deterministic function of its parents) and k >= 5 (not PSD).
    We cap k * rho^2 at 0.9. For k <= 3 and rho = 0.5 the value is unchanged,
    so every result produced before this guard was added is unaffected.
    """
    return float(min(rho, np.sqrt(0.9 / max(n_parents, 1))))


def _fit_baseline_conditional_sampler(
    child: str, parents: list[str], rng: np.random.Generator,
    rho: float = DEFAULT_BASELINE_RHO, n_fit: int = 4000, clip_eps: float = EPS,
) -> ConditionalSampler:
    """Simple baseline dependence for a multi-parent edge: a Gaussian vine
    with each parent correlated `rho` with the child (T5c.i)."""
    dim = len(parents) + 1
    rho = valid_baseline_rho(len(parents), rho)
    corr = np.eye(dim)
    for i in range(len(parents)):
        corr[0, i + 1] = corr[i + 1, 0] = rho
    z = rng.multivariate_normal(np.zeros(dim), corr, size=n_fit)
    u = pd.DataFrame(norm.cdf(z), columns=[child, *parents])
    return ConditionalSampler(
        child=child, parents=parents, family_set=[pv.BicopFamily.gaussian], clip_eps=clip_eps
    ).fit(u)


class GraphSampler:
    """Samples an n x p dataset for a DAG, using pairwise/conditional copula models as edge building blocks.

    Parameters beyond the DAG and node specs:
      max_indegree      reject DAGs with more parents per node than this.
      baseline_rho      correlation used by the Gaussian baseline (capped per
                        `valid_baseline_rho` for many parents).
      clip_eps          U-values are kept inside [clip_eps, 1 - clip_eps].
      calibrate_margins if True, each non-root node's U column is replaced by
                        its normalized ranks before it is used downstream and
                        mapped through its marginal. Ranks (and hence the
                        generated copula) are unchanged, but the node's
                        marginal is reproduced exactly even when its
                        conditional model is not "compatible" with the parent
                        distribution generated in this graph.
      drift_tolerance   KS distance of a node's U column from U(0,1) above which
                        a MarginalDriftWarning is emitted (uncalibrated mode).
    """

    def __init__(
        self,
        dag: nx.DiGraph,
        node_specs: dict[str, NodeSpec] | None = None,
        max_indegree: int = CORE_MAX_INDEGREE,
        baseline_rho: float = DEFAULT_BASELINE_RHO,
        clip_eps: float = EPS,
        calibrate_margins: bool = False,
        drift_tolerance: float = 0.05,
    ):
        if not nx.is_directed_acyclic_graph(dag):
            raise ValueError("graph must be a DAG")
        too_many = {node: d for node, d in dag.in_degree() if d > max_indegree}
        if too_many:
            raise ValueError(f"nodes exceed max indegree {max_indegree}: {too_many}")
        if not 0 < clip_eps < 0.5:
            raise ValueError("clip_eps must be in (0, 0.5)")

        self.dag = dag
        self.max_indegree = max_indegree
        self.baseline_rho = baseline_rho
        self.clip_eps = clip_eps
        self.calibrate_margins = calibrate_margins
        self.drift_tolerance = drift_tolerance
        self.node_specs = {node: NodeSpec() for node in dag.nodes}
        if node_specs:
            unknown = set(node_specs) - set(dag.nodes)
            if unknown:
                raise ValueError(f"node_specs given for nodes not in the DAG: {sorted(unknown)}")
            self.node_specs.update(node_specs)
        self.fallback_counts_: dict[str, int] = {}
        self.diagnostics_: dict[str, dict] = {}

    def sample(self, n: int, seed: int | None = None) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        eps = self.clip_eps
        u_values: dict[str, np.ndarray] = {}
        self.fallback_counts_ = {node: 0 for node in self.dag.nodes}
        self.diagnostics_ = {}

        for node in nx.topological_sort(self.dag):
            parents = list(self.dag.predecessors(node))
            spec = self.node_specs[node]
            kind = "root" if not parents else (spec.edge_model.source if spec.edge_model else "baseline")
            try:
                if not parents:
                    u_node = rng.uniform(eps, 1 - eps, size=n)
                elif len(parents) == 1:
                    u_node = self._sample_indegree1(parents[0], u_values, spec, rng, n)
                    self.fallback_counts_[node] += int(getattr(self._last_sampler, "last_fallback_count_", 0))
                else:
                    u_node = self._sample_indegree_k(node, parents, u_values, spec, rng, n)
                    sampler_fallbacks = getattr(self._last_sampler, "last_fallback_count_", 0)
                    self.fallback_counts_[node] += int(sampler_fallbacks)
            except Exception as exc:  # noqa: BLE001 - one bad node must not break the whole graph
                warnings.warn(f"sampling node {node!r} failed ({exc!r}); falling back to an independent draw", FallbackWarning)
                u_node = rng.uniform(eps, 1 - eps, size=n)
                self.fallback_counts_[node] = n

            u_node = np.asarray(u_node, dtype=float)
            bad = ~np.isfinite(u_node)
            if bad.any():
                warnings.warn(f"node {node!r}: {int(bad.sum())} non-finite draws; using independent fallback for those", FallbackWarning)
                u_node = np.where(bad, rng.uniform(eps, 1 - eps, size=n), u_node)
                self.fallback_counts_[node] = max(self.fallback_counts_[node], int(bad.sum()))
            u_node = np.clip(u_node, eps, 1 - eps)

            ks = float(kstest(u_node, "uniform").statistic) if parents else 0.0
            if parents and self.calibrate_margins:
                u_node = np.clip(rankdata(u_node) / (n + 1), eps, 1 - eps)
            # flag only drift that is both practically large and beyond
            # sampling noise (0.1% KS critical value ~ 1.95 / sqrt(n))
            elif parents and ks > max(self.drift_tolerance, 1.95 / np.sqrt(n)):
                warnings.warn(
                    f"node {node!r}: generated U deviates from uniform (KS={ks:.3f}); its marginal will not be "
                    "reproduced. Consider calibrate_margins=True.",
                    MarginalDriftWarning,
                )
            u_values[node] = u_node
            self.diagnostics_[node] = {
                "model": kind,
                "n_parents": len(parents),
                "fallback_draws": self.fallback_counts_[node],
                "u_uniformity_ks": ks,
                "calibrated": bool(parents and self.calibrate_margins),
            }

        # latent (copula-scale) values of the last run, e.g. to check that a
        # transplanted copula is reproduced before discretization by a marginal
        self.u_values_ = pd.DataFrame(u_values)[list(self.dag.nodes)]
        data = {}
        for node in self.dag.nodes:
            marginal = self.node_specs[node].marginal or baseline_marginal()
            data[node] = marginal.inverse_transform(u_values[node])
        return pd.DataFrame(data, columns=list(self.dag.nodes))

    @property
    def total_fallback_draws(self) -> int:
        return int(sum(self.fallback_counts_.values()))

    def _sample_indegree1(self, parent: str, u_values: dict, spec: NodeSpec, rng: np.random.Generator, n: int) -> np.ndarray:
        self._last_sampler = None
        edge_model = spec.edge_model
        if edge_model is not None and edge_model.bicop is None and edge_model.conditional_sampler is not None:
            # e.g. a ForestConditional fitted for this single parent
            sampler = edge_model.conditional_sampler
            self._last_sampler = sampler
            return sampler.sample(u_values[parent].reshape(-1, 1), seed=int(rng.integers(0, 2**31 - 1)))
        has_bicop = edge_model is not None and edge_model.bicop is not None
        bicop = edge_model.bicop if has_bicop else baseline_bicop(self.baseline_rho)
        parent_is_first = edge_model.bicop_parent_is_first if has_bicop else True
        w = rng.uniform(self.clip_eps, 1 - self.clip_eps, size=n)
        u_parent = u_values[parent]
        # h1(u1,u2) = P(U2<=u2|U1=u1): hinv1([u1, w]) samples u2|u1.
        # h2(u1,u2) = P(U1<=u1|U2=u2): hinv2([w, u2]) samples u1|u2.
        if parent_is_first:
            return bicop.hinv1(np.column_stack([u_parent, w]))
        return bicop.hinv2(np.column_stack([w, u_parent]))

    def _resolve_parent_order(self, parents: list[str], edge_model: EdgeModel | None, sampler) -> list[str]:
        if edge_model is not None and edge_model.parent_order is not None:
            if set(edge_model.parent_order) != set(parents):
                raise ValueError(f"parent_order {edge_model.parent_order} does not match DAG parents {parents}")
            return list(edge_model.parent_order)
        sampler_parents = list(getattr(sampler, "parents", []))
        if set(sampler_parents) == set(parents):
            return sampler_parents
        return parents

    def _sample_indegree_k(self, node: str, parents: list[str], u_values: dict, spec: NodeSpec, rng: np.random.Generator, n: int) -> np.ndarray:
        edge_model = spec.edge_model
        sampler = edge_model.conditional_sampler if edge_model and edge_model.conditional_sampler else None
        if sampler is None:
            sampler = _fit_baseline_conditional_sampler(node, parents, rng, rho=self.baseline_rho, clip_eps=self.clip_eps)
            order = parents
        else:
            order = self._resolve_parent_order(parents, edge_model, sampler)
        self._last_sampler = sampler
        u_parents = np.column_stack([u_values[p] for p in order])
        return sampler.sample(u_parents, seed=int(rng.integers(0, 2**31 - 1)))


# ---------------------------------------------------------------------- library helpers

def _bicop_from_pairwise_entry(entry: dict) -> pv.Bicop:
    name = entry["family"]
    if not isinstance(name, str) or not hasattr(pv.BicopFamily, name) or name.startswith("_"):
        raise ValueError(f"unknown copula family {name!r} in library entry")
    family = getattr(pv.BicopFamily, name)
    params = np.array(entry["parameters"], dtype=float)
    if params.size == 0:
        # e.g. the "indep" family has no parameters; .tolist() loses the (0, 0)
        # shape pv.Bicop's constructor requires, collapsing it to a bare [].
        params = params.reshape(0, 0)
    return pv.Bicop(family=family, rotation=int(entry["rotation"]), parameters=params)


def bind_pairwise_copula(library: DependencyLibrary, dataset: str, source_parent: str, source_child: str) -> EdgeModel:
    """Re-use the copula learned for the pair (source_parent, source_child) in
    `dataset` on ANY edge parent -> child of a new graph.

    The source parent's column of the stored copula is mapped to the new
    edge's parent, so asymmetric families keep their orientation. This is the
    building-block reuse mechanism: the edge's dependence pattern (family,
    rotation, parameters, hence tau and tail behaviour) is transplanted, while
    the endpoints keep their own marginals.
    """
    entry = library.get_pairwise_entry(dataset, source_parent, source_child)
    return EdgeModel(
        bicop=_bicop_from_pairwise_entry(entry),
        bicop_parent_is_first=entry["var_i"] == source_parent,
        source=f"bound:{dataset}:{source_parent}->{source_child}",
    )


def composed_conditional(
    library: DependencyLibrary, child: str, parents: list[str], edge_sources: dict[str, tuple[str, str, str]],
    clip_eps: float = EPS,
) -> EdgeModel:
    """Build a multi-parent model from per-edge pairwise copulas.

    `edge_sources[parent] = (dataset, source_parent, source_child)` names the
    library pair whose copula is used for the edge parent -> child.
    """
    edges = []
    for p in parents:
        dataset, sp, sc = edge_sources[p]
        entry = library.get_pairwise_entry(dataset, sp, sc)
        edges.append((_bicop_from_pairwise_entry(entry), entry["var_i"] == sc))
    sampler = PairwiseProductConditional(child=child, parents=parents, edges=edges, clip_eps=clip_eps)
    return EdgeModel(conditional_sampler=sampler, parent_order=list(parents), source="composed")


def node_spec_from_library(
    library: DependencyLibrary, dataset: str, node: str, parents: list[str], compose: bool = False,
) -> NodeSpec:
    """Build a NodeSpec for `node` (as it appeared in `dataset`) with the given parents,
    using the T4 pairwise/conditional models and marginal already fit on that dataset.

    For >= 2 parents a fitted ConditionalSampler for that parent *set* is used
    if one exists; otherwise, with `compose=True`, a PairwiseProductConditional
    is assembled from the pairwise models of each (parent, node) pair, and with
    `compose=False` a KeyError is raised (the historical behaviour).
    """
    marginal = library.get_marginal(dataset, node)

    if not parents:
        edge_model = None
    elif len(parents) == 1:
        parent = parents[0]
        try:
            entry = library.get_pairwise_entry(dataset, node, parent)
        except KeyError:
            raise KeyError(f"no pairwise model for {dataset}: {node} | {parent}") from None
        edge_model = EdgeModel(bicop=_bicop_from_pairwise_entry(entry), bicop_parent_is_first=entry["var_i"] == parent)
    else:
        try:
            sampler = library.get_conditional_sampler(dataset, node, parents)
            edge_model = EdgeModel(conditional_sampler=sampler)
        except KeyError:
            if not compose:
                raise
            edge_model = composed_conditional(library, node, parents, {p: (dataset, p, node) for p in parents})

    return NodeSpec(marginal=marginal, edge_model=edge_model)
