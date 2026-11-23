"""Compare two result directories file-by-file (all CSVs with the same relative path).

    python scripts/compare_outputs.py REFERENCE_DIR NEW_DIR [--rtol 1e-9] [--atol 1e-12]

Numeric columns must agree within tolerance; timing columns (elapsed*, *seconds*)
are ignored. Prints one line per file (OK / DIFF / MISSING) and exits 1 on any DIFF/MISSING.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

IGNORE = ("elapsed", "seconds", "time")

p = argparse.ArgumentParser()
p.add_argument("reference", type=Path)
p.add_argument("new", type=Path)
p.add_argument("--rtol", type=float, default=1e-9)
p.add_argument("--atol", type=float, default=1e-12)
a = p.parse_args()

bad = 0
for ref in sorted(a.reference.rglob("*.csv")):
    rel = ref.relative_to(a.reference)
    new = a.new / rel
    if not new.exists():
        print(f"MISSING {rel}")
        bad += 1
        continue
    r, n = pd.read_csv(ref), pd.read_csv(new)
    cols = [c for c in r.columns if not any(k in c.lower() for k in IGNORE)]
    if list(r.shape) != list(n.shape) or not set(cols) <= set(n.columns):
        print(f"DIFF    {rel}: shape/columns {r.shape} vs {n.shape}")
        bad += 1
        continue
    worst, where = 0.0, ""
    for c in cols:
        if pd.api.types.is_numeric_dtype(r[c]):
            x, y = r[c].to_numpy(float), n[c].to_numpy(float)
            same_nan = np.isnan(x) == np.isnan(y)
            close = np.isclose(x, y, rtol=a.rtol, atol=a.atol, equal_nan=True)
            if not (same_nan.all() and close.all()):
                d = np.nanmax(np.abs(x - y))
                if d > worst:
                    worst, where = d, c
        elif not (r[c].astype(object).fillna("<NA>").astype(str) == n[c].astype(object).fillna("<NA>").astype(str)).all():
            # (pandas >= 3 keeps missing values in string columns as NaN, and NaN != NaN)
            worst, where = float("inf"), c
    if where:
        print(f"DIFF    {rel}: max |diff| {worst:.3g} in column '{where}'")
        bad += 1
    else:
        print(f"OK      {rel}")
print(f"\n{bad} file(s) differ or are missing")
sys.exit(1 if bad else 0)
