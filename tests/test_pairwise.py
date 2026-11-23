import numpy as np
import pandas as pd
import pyvinecopulib as pv

from gcda.dependency.pairwise import build_pairwise_library, fit_bicop
from gcda.compat import bicop_sample


def test_fit_bicop_recovers_known_gaussian_dependence():
    true_cop = pv.Bicop(family=pv.BicopFamily.gaussian, parameters=np.array([[0.6]]))
    u = bicop_sample(true_cop, 3000, seeds=[1, 2, 3])

    fitted_cop, diagnostics = fit_bicop(u[:, 0], u[:, 1])

    assert diagnostics["family"] == "gaussian"
    assert abs(diagnostics["tau"] - true_cop.tau) < 0.03


def test_build_pairwise_library_flags_independence():
    rng = np.random.default_rng(0)
    u_df = pd.DataFrame(
        {"a": rng.uniform(size=3000), "b": rng.uniform(size=3000)}
    )
    entries = build_pairwise_library(u_df, dataset_name="toy")

    assert len(entries) == 1
    entry = entries[0]
    assert entry["dataset"] == "toy"
    assert {entry["var_i"], entry["var_j"]} == {"a", "b"}
    assert abs(entry["tau"]) < 0.05
