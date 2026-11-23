"""Ablation: jitter continuization vs. pyvinecopulib's native discrete copula likelihood.

For every edge of Asia and Insurance, fit a bivariate copula on a training
draw (a) to jittered pseudo-observations (the thesis' method) and (b) with
var_types=("d","d"), i.e. the likelihood of the discrete data itself using
F(x) and F(x-). Simulate from each fitted copula, map both coordinates back
through the empirical discrete quantile function, and compare the
dependence of the simulated pair to a held-out test draw (Cramer's V,
Kendall's tau-b). This isolates the effect of jitter dilution.
"""

import warnings

import numpy as np
import pandas as pd
import pyvinecopulib as pv
from scipy.stats import kendalltau

from gcda.data.datasets import load_asia, load_insurance
from gcda.data.preprocessing import CategoricalMarginal, to_pseudo_observations_mixed
from gcda.dependency.families import DEFAULT_BICOP_FAMILIES
from gcda.evaluation.discrete import cramers_v
from gcda.compat import bicop_sample


def _cdf_pair(values, states):
    m = CategoricalMarginal().fit(values, categories=states)
    idx = np.array([states.index(v) for v in values])
    upper = m.cum_probs_[idx]
    lower = np.where(idx == 0, 0.0, m.cum_probs_[idx - 1])
    return upper, lower, m


def run(name, loader, n=10000, n_sim=10000):
    train, dag, orders = loader(n, 0)
    test, _, _ = loader(n, 1)
    u_jit, _ = to_pseudo_observations_mixed(train, category_orders=orders, seed=0)
    controls = pv.FitControlsBicop(family_set=DEFAULT_BICOP_FAMILIES, selection_criterion="bic")
    rows = []
    for a, b in dag.edges:
        ua, la, ma = _cdf_pair(train[a].to_numpy(), list(orders[a]))
        ub, lb, mb = _cdf_pair(train[b].to_numpy(), list(orders[b]))
        jit = pv.Bicop()
        jit.select(np.column_stack([u_jit[a], u_jit[b]]), controls)
        nat = pv.Bicop(var_types=["d", "d"])
        nat.select(np.column_stack([ua, ub, la, lb]), controls)
        code_a = {s: i for i, s in enumerate(orders[a])}
        code_b = {s: i for i, s in enumerate(orders[b])}
        true_v = cramers_v(test[a], test[b])
        true_t = kendalltau(test[a].map(code_a), test[b].map(code_b))[0]
        row = {"network": name, "edge": f"{a}->{b}", "cramers_v_test": true_v, "tau_b_test": true_t}
        for label, cop in [("jitter", jit), ("native", nat)]:
            sim_cop = pv.Bicop(family=cop.family, rotation=cop.rotation, parameters=cop.parameters)
            s = bicop_sample(sim_cop, n_sim, seeds=[11, 12, 13])
            xa, xb = ma.inverse_transform(s[:, 0]), mb.inverse_transform(s[:, 1])
            row[f"family_{label}"] = cop.family.name
            row[f"cramers_v_{label}"] = cramers_v(xa, xb)
            row[f"tau_b_{label}"] = kendalltau(pd.Series(xa).map(code_a), pd.Series(xb).map(code_b))[0]
            row[f"cramers_v_abs_err_{label}"] = abs(row[f"cramers_v_{label}"] - true_v)
            row[f"tau_b_abs_err_{label}"] = abs(row[f"tau_b_{label}"] - true_t)
        rows.append(row)
    return pd.DataFrame(rows)


def main(out_dir) -> None:
    from pathlib import Path

    from gcda.experiments.common import paired_comparison
    from gcda.provenance import write_metadata

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = pd.concat([run("asia", lambda n, s: load_asia(n, s)), run("insurance", lambda n, s: load_insurance(n, s))])
    res.to_csv(out_dir / "discrete_native_vs_jitter.csv", index=False)
    write_metadata(out_dir / "discrete_native_vs_jitter.csv")
    summ = []
    for net, g in res.groupby("network"):
        for m in ("cramers_v", "tau_b"):
            summ.append({"network": net, "metric": m, "mean_abs_err_jitter": g[f"{m}_abs_err_jitter"].mean(),
                         "mean_abs_err_native": g[f"{m}_abs_err_native"].mean(),
                         **paired_comparison(g[f"{m}_abs_err_native"], g[f"{m}_abs_err_jitter"])})
    s = pd.DataFrame(summ)
    s.to_csv(out_dir / "discrete_native_vs_jitter_summary.csv", index=False)
    print(res[res.network == "asia"].round(3).to_string(index=False))
    print(s.round(4).to_string(index=False))
