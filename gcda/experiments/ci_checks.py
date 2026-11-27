"""Do generated discrete/mixed data preserve the conditional independences of the supplied graph?

For every induced chain (A -> B -> C), fork (A <- B -> C) and collider (A -> B <- C) of the
true DAG of Asia, Insurance, Alarm and the mixed SCM (A and C non-adjacent), the three-node
graph is supplied to the generator, which learns its building blocks from the training draw
(seed 10,000) of these three columns and samples n rows per evaluation seed. On every sample:

* chain, fork:  the implied independence A _||_ C | B is tested, and the dependence A - C
  (which the graph implies as well) is tested marginally;
* collider:     the implied independence A _||_ C is tested, and the dependence A - C | B.

In copula space the chain/fork independence holds by construction (the child's U depends only
on the parent's U), but the observed data are not the U-values: a discrete B only reveals the
category slice of U_B, while A and C both still depend on where U_B lies inside the slice. The
implied independence of the *observed* variables therefore does not follow from the
construction and has to be checked.

Tests (alpha = 0.05 throughout):
  conditioning set empty or discrete: likelihood-ratio G-test of (conditional) independence
      on the contingency table (continuous A or C binned into 5 quantile bins, which keeps
      the null hypothesis valid);
  continuous B: generalised covariance measure (Shah & Peters, 2020) with k-nearest-neighbour
      regressions of A's and C's (ordinal) codes on B; exact-value means with a cluster-robust
      variance when most values of B repeat, as in random-forest data (see gcm_test).
Effect size: conditional mutual information (nats, plug-in) for the implied independence.
Under a true independence about 5% of tests reject.

Sources: the generator with jittered copulas (``learned``), with native discrete copulas
(``learned_native``), with random-forest conditionals (``learned_rf``), the fixed-rho baseline,
and a CPT refit on the three-node graph (discrete triples only; its data satisfy the implied
independences exactly, so its rejection rate calibrates the tests). Real data are included
where the full network implies the same statement (d-separation), as a second reference.
"""

import itertools
import warnings

import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import chi2, norm
from sklearn.neighbors import KNeighborsRegressor

from gcda.data.registry import load_dataset
from gcda.experiments.common import (
    baseline_specs,
    cpt_refit_sample,
    fit_graph_library,
    learned_specs,
    sample,
)
from gcda.experiments.rf_eval import forest_specs

NETWORKS = {"asia": 8000, "insurance": 8000, "alarm": 8000, "mixed_scm": 5000}
TRAIN_SEED = 10_000
MAX_PER_TYPE = 10


# --------------------------------------------------------------------------- structures
def triples(dag: nx.DiGraph, max_per_type: int = MAX_PER_TYPE, seed: int = 0) -> list[tuple[str, str, str, str]]:
    """Induced chains, forks and colliders (type, A, B, C) of the DAG; A and C non-adjacent."""
    found = {"chain": [], "fork": [], "collider": []}
    for b in sorted(dag.nodes):
        nbrs = sorted(set(dag.predecessors(b)) | set(dag.successors(b)))
        for a, c in itertools.combinations(nbrs, 2):
            if dag.has_edge(a, c) or dag.has_edge(c, a):
                continue
            a_par, c_par = dag.has_edge(a, b), dag.has_edge(c, b)
            if a_par and c_par:
                found["collider"].append(("collider", a, b, c))
            elif not a_par and not c_par:
                found["fork"].append(("fork", a, b, c))
            elif a_par:
                found["chain"].append(("chain", a, b, c))
            else:
                found["chain"].append(("chain", c, b, a))
    rng = np.random.default_rng(seed)
    out = []
    for items in found.values():
        if len(items) > max_per_type:
            items = [items[i] for i in sorted(rng.choice(len(items), max_per_type, replace=False))]
        out += items
    return out


def three_node_dag(kind: str, a: str, b: str, c: str) -> nx.DiGraph:
    edges = {"chain": [(a, b), (b, c)], "fork": [(b, a), (b, c)], "collider": [(a, b), (c, b)]}[kind]
    g = nx.DiGraph()
    g.add_nodes_from([a, b, c])
    g.add_edges_from(edges)
    return g


def implied_in_full_dag(dag: nx.DiGraph, kind: str, a: str, b: str, c: str) -> bool:
    cond = set() if kind == "collider" else {b}
    return nx.is_d_separator(dag, {a}, {c}, cond)


# --------------------------------------------------------------------------- tests
def _codes(x: pd.Series, order: list | None, bins: int = 5) -> np.ndarray:
    """Integer codes: categories in their order, continuous values in quantile bins."""
    if order is not None:
        return pd.Categorical(x, categories=order).codes.astype(int)
    return pd.qcut(x.rank(method="first"), bins, labels=False).astype(int)


def g_test(a: np.ndarray, c: np.ndarray, b: np.ndarray | None = None) -> tuple[float, float]:
    """(p-value, conditional mutual information in nats) of A _||_ C | B for integer codes."""
    strata = [np.ones(len(a), bool)] if b is None else [b == v for v in np.unique(b)]
    g, dof, cmi, n = 0.0, 0, 0.0, len(a)
    for m in strata:
        tab = pd.crosstab(a[m], c[m]).to_numpy().astype(float)
        if tab.shape[0] < 2 or tab.shape[1] < 2:
            continue
        exp = tab.sum(1, keepdims=True) * tab.sum(0, keepdims=True) / tab.sum()
        nz = tab > 0
        gi = 2 * (tab[nz] * np.log(tab[nz] / exp[nz])).sum()
        g += gi
        dof += (tab.shape[0] - 1) * (tab.shape[1] - 1)
        cmi += gi / (2 * n)
    p = float(chi2.sf(g, dof)) if dof > 0 else 1.0
    return p, cmi


def gcm_test(a: np.ndarray, c: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Generalised covariance measure of A _||_ C | B (continuous B): p-value, |residual corr|.

    E[A | B] and E[C | B] are estimated by k-nearest-neighbour regression (k = sqrt(n)).
    Random-forest data need a different estimate: leaf sampling re-uses training values, so most
    values of B occur several times and the conditional means jump between neighbouring values,
    which a smoothing regression misses (its leftover residuals make the test reject a true
    independence). When at least half of the rows share their value of B, the conditional
    means are therefore taken within each exact value, and the variance of the statistic is
    computed per value group (cluster-robust), because residuals within a group are dependent.
    """
    groups = pd.Series(b).factorize()[0]
    repeated = np.bincount(groups)[groups] > 1
    if repeated.mean() >= 0.5:
        ra = a - pd.Series(a).groupby(groups).transform("mean").to_numpy()
        rc = c - pd.Series(c).groupby(groups).transform("mean").to_numpy()
        r = ra * rc
        t = r.sum() / np.sqrt((np.bincount(groups, weights=r) ** 2).sum())
    else:
        k = int(np.sqrt(len(b)))
        reg = lambda y: KNeighborsRegressor(n_neighbors=k).fit(b.reshape(-1, 1), y).predict(b.reshape(-1, 1))
        ra, rc = a - reg(a), c - reg(c)
        r = ra * rc
        t = np.sqrt(len(r)) * r.mean() / r.std(ddof=1)
    corr = abs(np.corrcoef(ra, rc)[0, 1])
    return float(2 * norm.sf(abs(t))), float(corr)


def ci_test(df: pd.DataFrame, a: str, c: str, b: str | None, orders: dict) -> tuple[float, float, str]:
    if b is not None and b not in orders:                         # continuous conditioning variable
        code = lambda x: (pd.Categorical(df[x], categories=orders[x]).codes.astype(float)
                          if x in orders else df[x].to_numpy(float))
        p, eff = gcm_test(code(a), code(c), df[b].to_numpy(float))
        return p, eff, "gcm"
    p, eff = g_test(_codes(df[a], orders.get(a)), _codes(df[c], orders.get(c)),
                    None if b is None else _codes(df[b], orders.get(b)))
    return p, eff, "g"


# --------------------------------------------------------------------------- experiment
def run_network(name: str, seeds: list[int], max_per_type: int = MAX_PER_TYPE) -> pd.DataFrame:
    n = NETWORKS[name]
    train, dag, orders = load_dataset(name, n=n, seed=TRAIN_SEED)
    real = {s: load_dataset(name, n=n, seed=s)[0] for s in seeds}
    rows = []
    for kind, a, b, c in triples(dag, max_per_type):
        g3 = three_node_dag(kind, a, b, c)
        cols = [a, b, c]
        o3 = {k: v for k, v in orders.items() if k in cols}
        discrete = all(x in o3 for x in cols)
        tr = train[cols]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            lib = fit_graph_library(tr, g3, o3, name, n_jobs=1)
            specs = {"baseline_fixed_rho": baseline_specs(lib, name, g3), "learned": learned_specs(lib, name, g3)}
            if any(x in o3 for x in cols):
                lib_nat = fit_graph_library(tr, g3, o3, name, n_jobs=1, discrete_mode="native")
                specs["learned_native"] = learned_specs(lib_nat, name, g3)
            specs["learned_rf"] = forest_specs(tr, g3, o3, lib, name)
        real_ok = implied_in_full_dag(dag, kind, a, b, c)
        indep_cond = None if kind == "collider" else b          # the implied independence
        dep_cond = b if kind == "collider" else None             # the implied dependence
        for seed in seeds:
            data = {}
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                for label, sp in specs.items():
                    data[label], _ = sample(g3, sp, n, seed)
                if discrete:
                    data["cpt_refit"] = cpt_refit_sample(tr, g3, n, seed)
            if real_ok:
                data["true_data"] = real[seed][cols]
            for label, df in data.items():
                p_ind, eff_ind, test = ci_test(df, a, c, indep_cond, o3)
                p_dep, _, _ = ci_test(df, a, c, dep_cond, o3)
                rows.append({"network": name, "structure": kind, "a": a, "b": b, "c": c,
                             "b_type": "discrete" if b in o3 else "continuous", "test": test,
                             "seed": seed, "source": label,
                             "p_implied_independence": p_ind, "effect_implied_independence": eff_ind,
                             "reject_implied_independence": p_ind < 0.05,
                             "p_implied_dependence": p_dep, "detect_implied_dependence": p_dep < 0.05})
        print(f"  ci {name} {kind} {a}-{b}-{c} done")
    return pd.DataFrame(rows)


def summarize_ci(res: pd.DataFrame) -> pd.DataFrame:
    keys = ["network", "structure", "source"]
    summ = res.groupby(keys).agg(tests=("reject_implied_independence", "size"),
                                 rejection_rate=("reject_implied_independence", "mean"),
                                 mean_effect=("effect_implied_independence", "mean"),
                                 dependence_detected=("detect_implied_dependence", "mean")).reset_index()
    n_triples = res.drop_duplicates(keys + ["a", "b", "c"]).groupby(keys).size().rename("triples").reset_index()
    return summ.merge(n_triples, on=keys)[keys + ["triples", "tests", "rejection_rate", "mean_effect",
                                                   "dependence_detected"]]


def main(networks: list[str], n_seeds: int, out_dir, seed_start: int = 0) -> None:
    from pathlib import Path

    from gcda.provenance import write_metadata

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seeds = list(range(seed_start, seed_start + n_seeds))
    res = pd.concat([run_network(nw, seeds) for nw in networks], ignore_index=True)
    summ = summarize_ci(res)
    for fname, frame in [("ci_checks_per_test.csv", res), ("ci_checks_summary.csv", summ)]:
        frame.to_csv(out_dir / fname, index=False)
        write_metadata(out_dir / fname, networks=networks, seeds=seeds, train_seed=TRAIN_SEED,
                       max_per_type=MAX_PER_TYPE)
    with pd.option_context("display.width", 250, "display.max_rows", 300):
        print(summ.round(3).to_string(index=False))
