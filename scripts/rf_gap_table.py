"""Gap-closed table for the random-forest prototype.

gap closed = (SHD_baseline - SHD_source) / (SHD_baseline - SHD_real) in %; 100 = real-data level,
> 100 = overshoot (discovery easier than on real data). Also prints |SHD_source - SHD_real|.

    python scripts/rf_gap_table.py outputs/experiments/hpc/rf_pc/merged/rf_per_seed.csv [.../rf_ges/merged/rf_per_seed.csv]
"""

import sys

import pandas as pd

rows = []
for path in sys.argv[1:]:
    d = pd.read_csv(path)
    for alg in ("pc", "ges"):
        col = f"shd_{alg}"
        if col not in d or d[col].isna().all():
            continue
        m = d.pivot_table(index="graph", columns="source", values=col, aggfunc="mean")
        n = d.groupby("graph").seed.nunique()
        for g, r in m.iterrows():
            gap = r["baseline_fixed_rho"] - r["true_data"]
            row = {"graph": g, "alg": alg.upper(), "seeds": int(n[g]),
                   **{s: round(r[s], 2) for s in ("baseline_fixed_rho", "learned", "learned_rf", "cpt_refit", "true_data") if s in r and pd.notna(r[s])}}
            for s in ("learned", "learned_rf", "cpt_refit"):
                if s in r and pd.notna(r[s]):
                    row[f"{s}_gap_closed_%"] = round(100 * (r["baseline_fixed_rho"] - r[s]) / gap) if abs(gap) > 0.5 else None
                    row[f"{s}_abs_diff_to_real"] = round(abs(r[s] - r["true_data"]), 2)
            rows.append(row)
with pd.option_context("display.width", 300, "display.max_columns", 50):
    print(pd.DataFrame(rows).to_string(index=False))
