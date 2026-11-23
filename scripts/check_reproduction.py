"""Compare a freshly produced sweep CSV with the committed reference (exit 1 on mismatch).

    python scripts/check_reproduction.py NEW.csv outputs/sweep_dependency_models.csv
"""

import sys

import numpy as np
import pandas as pd

new, ref = pd.read_csv(sys.argv[1]), pd.read_csv(sys.argv[2])
keys = ["dataset", "family_set", "selection_criterion"]
m = ref.merge(new, on=keys, suffixes=("_ref", "_new"))
ok = len(m) == len(ref)
for col in ["vine_aic", "vine_bic", "mean_tau_abs_error"]:
    diff = np.abs(m[f"{col}_ref"] - m[f"{col}_new"]).max()
    print(f"{col}: max |diff| = {diff:.3g}")
    ok &= diff < 1e-6
same = (m["families_selected_ref"] == m["families_selected_new"]).all()
print("families identical:", same)
sys.exit(0 if ok and same else 1)
