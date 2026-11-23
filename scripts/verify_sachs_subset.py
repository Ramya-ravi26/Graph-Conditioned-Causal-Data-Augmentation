"""Verify that the first 853 rows of the bundled Sachs file are the CD3/CD28
(observational) condition, by comparing with an independent copy of that
condition, e.g. bnlearn's continuous observational data:

    wget https://www.bnlearn.com/book-crc/code/sachs.data.txt.gz && gunzip sachs.data.txt.gz
    python scripts/verify_sachs_subset.py sachs.data.txt

The reference is read as whitespace-separated with a header; columns are
matched by order (Raf, Mek, Plcg, PIP2, PIP3, Erk, Akt, PKA, PKC, P38, Jnk).
Exit status 0 if all 853 rows match (relative tolerance 1e-3), 1 otherwise.
"""

import sys

import numpy as np
import pandas as pd

from gcda.data.datasets import SACHS_OBSERVATIONAL_ROWS, load_sachs

ref = pd.read_csv(sys.argv[1], sep=r"\s+")
ours = load_sachs(observational_only=True)
if len(ref) != SACHS_OBSERVATIONAL_ROWS:
    print(f"reference has {len(ref)} rows, expected {SACHS_OBSERVATIONAL_ROWS}")
same_rows = np.isclose(ref.to_numpy()[:len(ours)], ours.to_numpy(), rtol=1e-3).all(axis=1)
print(f"{same_rows.sum()}/{len(ours)} rows match row-by-row")
if not same_rows.all():
    # order-insensitive check (the reference may be sorted differently)
    a = np.sort(np.round(ref.to_numpy(), 2), axis=0)
    b = np.sort(np.round(ours.to_numpy(), 2), axis=0)
    print("column-wise multiset match:", bool(np.allclose(a[:len(b)], b, rtol=1e-3)))
sys.exit(0 if same_rows.all() else 1)
