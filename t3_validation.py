"""T3: Choose tools and validate them on toy data.

T3a. Tool choice: pyvinecopulib is used as the main copula/vine library.
     Rationale (documented here instead of only in the thesis notes):
       - C++ backend (via pybind11) -> fast fitting/simulation, which matters
         once we scale to many pairwise fits and large sampled graphs.
       - Native support for the families we actually need (Gaussian, Student-t,
         Clayton, Gumbel, Frank, Joe, BB1/6/7/8, ...) plus automatic family
         selection via AIC/BIC (`Bicop.select`), which is exactly what T4c asks
         for ("try multiple families and pick one using AIC/BIC").
       - First-class vine copula support, needed later for the multi-parent
         conditional sampler (T4d/T5), so we are not locked into pairwise-only
         tooling.
       - Actively maintained Python bindings for the well-established R
         `vinecopulib`/`VineCopula` methodology.
     No strong reason was found to prefer the alternative `copulas` package
     (pure Python, fewer families, no vine support), so pyvinecopulib is kept
     as the main library per the task recommendation.

T3b. Validation tests (must pass before building anything on top of this):
       i.   Generate synthetic data from a *known* bivariate copula
            (Gaussian / Student-t / Clayton) with known parameters.
       ii.  Fit a copula back with `Bicop.select` and check that the
            recovered family, parameters and Kendall's tau match the truth.
       iii. Simulate new data from the *fitted* copula and check that its
            dependence statistics (Kendall's tau, Spearman's rho) match the
            original data's dependence statistics.

Run directly: `python t3_validation.py`. Exits non-zero if any check fails.
Diagnostic scatter/histogram plots are written to `outputs/t3_validation/`.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyvinecopulib as pv
from scipy.stats import kendalltau, spearmanr
from gcda.compat import bicop_sample

N_SAMPLES = 3000
SEED = 42
# Tolerances account for Monte Carlo sampling noise at N_SAMPLES=3000.
# Correlation-type parameters (Gaussian rho, Student rho) are well identified
# by ~3000 samples, so a small absolute tolerance is enough. Degrees-of-freedom
# (Student nu) is a shape parameter that converges much more slowly and lives
# on a different scale, so it additionally gets a relative tolerance.
PARAM_ATOL = 0.08
PARAM_RTOL = 0.15
TAU_TOL = 0.04
OUTPUT_DIR = Path(__file__).parent / "outputs" / "t3_validation"

# Candidate family set for `select` (AIC/BIC based, as in T4c).
CANDIDATE_FAMILIES = [
    pv.BicopFamily.gaussian,
    pv.BicopFamily.student,
    pv.BicopFamily.clayton,
    pv.BicopFamily.gumbel,
    pv.BicopFamily.frank,
    pv.BicopFamily.joe,
]


@dataclass
class ToyCase:
    name: str
    family: pv.BicopFamily
    true_params: np.ndarray  # shape (n_params, 1), pyvinecopulib convention


TOY_CASES = [
    ToyCase("gaussian", pv.BicopFamily.gaussian, np.array([[0.7]])),
    ToyCase("student_t", pv.BicopFamily.student, np.array([[0.6], [4.0]])),
    ToyCase("clayton", pv.BicopFamily.clayton, np.array([[2.0]])),
]


def validate_case(case: ToyCase, seed: int) -> dict:
    """Run the three T3b validation steps for one toy copula family."""
    checks = {}

    # i. Generate synthetic data with known dependence.
    true_cop = pv.Bicop(family=case.family, parameters=case.true_params)
    u_true = bicop_sample(true_cop, N_SAMPLES, seeds=[seed, seed + 1, seed + 2])
    tau_true_theoretical = true_cop.tau
    tau_true_empirical = kendalltau(u_true[:, 0], u_true[:, 1])[0]
    rho_true_empirical = spearmanr(u_true[:, 0], u_true[:, 1])[0]

    # ii. Fit the copula back and check family/parameters/correlation.
    fitted_cop = pv.Bicop()
    controls = pv.FitControlsBicop(family_set=CANDIDATE_FAMILIES)
    fitted_cop.select(u_true, controls)

    family_ok = fitted_cop.family == case.family
    params_true = case.true_params.ravel()
    params_fit = fitted_cop.parameters.ravel()
    params_ok = family_ok and params_true.shape == params_fit.shape and np.allclose(
        params_true, params_fit, atol=PARAM_ATOL, rtol=PARAM_RTOL
    )
    tau_fit_ok = abs(fitted_cop.tau - tau_true_theoretical) < TAU_TOL

    # iii. Sample new data from the fitted copula and compare dependence stats.
    u_sim = bicop_sample(fitted_cop, N_SAMPLES, seeds=[seed + 10, seed + 11, seed + 12])
    tau_sim = kendalltau(u_sim[:, 0], u_sim[:, 1])[0]
    rho_sim = spearmanr(u_sim[:, 0], u_sim[:, 1])[0]
    tau_sim_ok = abs(tau_sim - tau_true_empirical) < TAU_TOL
    rho_sim_ok = abs(rho_sim - rho_true_empirical) < TAU_TOL

    _save_plots(case.name, u_true, u_sim)

    return {
        "name": case.name,
        "true_family": case.family,
        "fitted_family": fitted_cop.family,
        "family_ok": family_ok,
        "true_params": params_true,
        "fitted_params": params_fit,
        "params_ok": params_ok,
        "tau_true_theoretical": tau_true_theoretical,
        "tau_fitted": fitted_cop.tau,
        "tau_fit_ok": tau_fit_ok,
        "tau_true_empirical": tau_true_empirical,
        "tau_sim": tau_sim,
        "tau_sim_ok": tau_sim_ok,
        "rho_true_empirical": rho_true_empirical,
        "rho_sim": rho_sim,
        "rho_sim_ok": rho_sim_ok,
        "all_ok": family_ok and params_ok and tau_fit_ok and tau_sim_ok and rho_sim_ok,
    }


def _save_plots(name: str, u_true: np.ndarray, u_sim: np.ndarray) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    axes[0].scatter(u_true[:, 0], u_true[:, 1], alpha=0.3, s=8)
    axes[0].set_title(f"{name}: original data (U-space)")
    axes[1].scatter(u_sim[:, 0], u_sim[:, 1], alpha=0.3, s=8)
    axes[1].set_title(f"{name}: sampled from fitted copula")
    axes[2].hist(u_sim[:, 0], bins=30)
    axes[2].set_title(f"{name}: marginal of simulated U (should be ~uniform)")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / f"{name}.png", dpi=120)
    plt.close(fig)


def main() -> int:
    np.random.seed(SEED)
    results = [validate_case(case, SEED) for case in TOY_CASES]

    print(f"{'family':<10} {'fam.match':<10} {'params_ok':<10} "
          f"{'tau_true':>9} {'tau_fit':>9} {'tau_sim':>9} {'PASS':>6}")
    for r in results:
        print(
            f"{r['name']:<10} "
            f"{str(r['family_ok']):<10} "
            f"{str(r['params_ok']):<10} "
            f"{r['tau_true_theoretical']:>9.4f} "
            f"{r['tau_fitted']:>9.4f} "
            f"{r['tau_sim']:>9.4f} "
            f"{str(r['all_ok']):>6}"
        )
        print(
            f"    true params={r['true_params']} fitted params={r['fitted_params']} "
            f"rho_true={r['rho_true_empirical']:.4f} rho_sim={r['rho_sim']:.4f}"
        )

    all_passed = all(r["all_ok"] for r in results)
    print("\nOverall:", "PASS" if all_passed else "FAIL")
    print(f"Diagnostic plots written to {OUTPUT_DIR}/")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
