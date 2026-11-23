"""RQ2 (held-out): does sampling the synthetic SCM's graph with learned models
reproduce its per-edge dependence, marginals and joint distribution?

The library is fitted on a training draw (seed 10,000) and every metric is
computed against independent test draws (seeds 0..n-1). Reports per-edge
|tau error|, marginal KS, and U-space energy distance / MMD (unbiased) with
permutation p-values, for the fixed-rho baseline, the fitted Gaussian copula
and the learned models.
"""

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, ks_2samp

from gcda.data.datasets import make_synthetic_scm
from gcda.data.preprocessing import to_pseudo_observations
from gcda.evaluation.realism import energy_distance, gaussian_mmd, permutation_test
from gcda.experiments.common import GAUSSIAN_ONLY, baseline_specs, fit_graph_library, learned_specs, sample, summarize


def main(out_dir, n_seeds: int = 30) -> None:
    from pathlib import Path

    from gcda.provenance import write_metadata

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    train, dag = make_synthetic_scm(n=5000, seed=10_000)
    lib = fit_graph_library(train, dag, None, "synthetic_scm", all_pairs=True)
    lib_g = fit_graph_library(train, dag, None, "synthetic_scm", family_set=GAUSSIAN_ONLY, all_pairs=True)
    rows, edge_rows = [], []
    for seed in range(n_seeds):
        test, _ = make_synthetic_scm(n=5000, seed=seed)
        tu, _ = to_pseudo_observations(test)
        for label, specs in [("baseline_fixed_rho", baseline_specs(lib, "synthetic_scm", dag)),
                             ("gaussian_copula_fitted", learned_specs(lib_g, "synthetic_scm", dag)),
                             ("learned", learned_specs(lib, "synthetic_scm", dag))]:
            gen, _ = sample(dag, specs, 5000, seed + 500)
            gu, _ = to_pseudo_observations(gen)
            errs = {f"{a}->{b}": abs(kendalltau(gen[a], gen[b])[0] - kendalltau(test[a], test[b])[0]) for a, b in dag.edges}
            for e, v in errs.items():
                edge_rows.append({"seed": seed, "source": label, "edge": e, "tau_abs_error": v})
            do_perm = seed < 10  # permutation tests are O(n_perm * max_n^2): first 10 seeds only
            row = {"seed": seed, "source": label, "mean_edge_tau_abs_error": np.mean(list(errs.values())),
                   "mean_marginal_ks": np.mean([ks_2samp(gen[c], test[c]).statistic for c in test.columns]),
                   "energy_distance": energy_distance(tu.to_numpy(), gu.to_numpy(), unbiased=True),
                   "gaussian_mmd": gaussian_mmd(tu.to_numpy(), gu.to_numpy(), unbiased=True)}
            if do_perm:
                row["energy_p"] = permutation_test(energy_distance, tu.to_numpy(), gu.to_numpy(), n_permutations=200)["p_value"]
                row["mmd_p"] = permutation_test(gaussian_mmd, tu.to_numpy(), gu.to_numpy(), n_permutations=200)["p_value"]
            rows.append(row)
        print(f"  rq2 seed {seed} done")
    res, edges = pd.DataFrame(rows), pd.DataFrame(edge_rows)
    res.to_csv(out_dir / "rq2_heldout_per_seed.csv", index=False)
    edges.to_csv(out_dir / "rq2_heldout_edges.csv", index=False)
    summ = pd.concat([summarize(res, ["source"], m).assign(metric=m) for m in
                      ["mean_edge_tau_abs_error", "mean_marginal_ks", "energy_distance", "gaussian_mmd"]])
    p = res.groupby("source")[["energy_p", "mmd_p"]].agg(lambda x: float((x.dropna() < 0.05).mean()))
    summ.to_csv(out_dir / "rq2_heldout_summary.csv", index=False)
    p.to_csv(out_dir / "rq2_heldout_rejection_rates.csv")
    write_metadata(out_dir / "rq2_heldout_summary.csv", n_seeds=n_seeds, train_seed=10_000)
    print(summ.round(4).to_string(index=False))
    print("fraction of seeds where the permutation test rejects equality at 5%:\n", p.round(3).to_string())
    print(edges.groupby(["edge", "source"]).tau_abs_error.mean().unstack().round(4).to_string())
