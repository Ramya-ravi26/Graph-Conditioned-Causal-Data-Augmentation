"""Learned (not baseline) multi-parent conditional vines at indegree 2-4 on held-out data.

For every multi-parent node of Insurance (indegree 2-3) and Alarm (indegree
2-4), a conditional vine is fitted on a training draw; the child is then
sampled given the parents of an independent test draw, and the child-parent
dependence (Cramer's V, tau) and the child's category frequencies are compared
with the test data. Repeated over seeds for the test draw.
"""

import warnings

import pandas as pd
from scipy.stats import kendalltau

from gcda.data.preprocessing import discrete_cdf_pairs, to_pseudo_observations_mixed
from gcda.data.registry import load_dataset
from gcda.dependency.conditional import ConditionalSampler
from gcda.evaluation.discrete import cramers_v


def main(out_dir, n_seeds: int = 10) -> None:
    from pathlib import Path

    from gcda.provenance import write_metadata

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in ("insurance", "alarm"):
        train, dag, orders = load_dataset(name, n=10000, seed=10_000)
        u_train, marg = to_pseudo_observations_mixed(train, category_orders=orders, seed=0)
        up, lo, vt = discrete_cdf_pairs(train, marg)
        fitted = {
            "jitter": {v: ConditionalSampler(child=v, parents=list(dag.predecessors(v))).fit(u_train)
                       for v in dag.nodes if dag.in_degree(v) >= 2},
            "native": {v: ConditionalSampler(child=v, parents=list(dag.predecessors(v))).fit(up, lo, vt)
                       for v in dag.nodes if dag.in_degree(v) >= 2},
        }
        for seed in range(min(n_seeds, 10)):
          test, _, _ = load_dataset(name, n=10000, seed=seed)
          u_test, _ = to_pseudo_observations_mixed(test, category_orders=orders, seed=seed)
          # native mode conditions on the parents' latent uniforms: draw them from
          # the parents' CDF rectangles [F(x-), F(x)] (randomized PIT)
          import numpy as np
          rng = np.random.default_rng(seed)
          t_up, t_lo, _ = discrete_cdf_pairs(test, marg)
          u_latent = t_lo + rng.uniform(size=t_lo.shape) * (t_up - t_lo)
          for mode, samplers in fitted.items():
            parents_u = u_test if mode == "jitter" else u_latent
            for v, s in samplers.items():
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    u_child = s.sample(parents_u[s.parents].to_numpy(), seed=seed)
                child = marg[v].inverse_transform(u_child)
                codes = {c: i for i, c in enumerate(orders[v])}
                for p in s.parents:
                    pc = {c: i for i, c in enumerate(orders[p])}
                    rows.append({
                        "network": name, "seed": seed, "mode": mode, "child": v, "parent": p, "indegree": len(s.parents),
                        "cramers_v_test": cramers_v(test[v], test[p]), "cramers_v_sim": cramers_v(child, test[p]),
                        "tau_test": kendalltau(test[v].map(codes), test[p].map(pc))[0],
                        "tau_sim": kendalltau(pd.Series(child).map(codes), test[p].map(pc))[0],
                        "fallback_draws": s.last_fallback_count_,
                    })
        print(f"  {name} done")
    res = pd.DataFrame(rows)
    res["cramers_v_abs_err"] = (res.cramers_v_sim - res.cramers_v_test).abs()
    res["tau_abs_err"] = (res.tau_sim - res.tau_test).abs()
    res.to_csv(out_dir / "learned_indegree_per_edge.csv", index=False)
    summ = res.groupby(["network", "mode", "indegree"]).agg(
        n_edges=("parent", "size"), cramers_v_test=("cramers_v_test", "mean"),
        cramers_v_abs_err=("cramers_v_abs_err", "mean"), tau_abs_err=("tau_abs_err", "mean"),
        fallback_draws=("fallback_draws", "sum")).reset_index()
    summ.to_csv(out_dir / "learned_indegree_summary.csv", index=False)
    write_metadata(out_dir / "learned_indegree_summary.csv")
    print(summ.round(4).to_string(index=False))
