# Random-forest conditionals: supporting files

- `nonmonotone_edges.csv`: per true edge of Asia, Insurance and Alarm (training draw), Cramer's V and
  |Spearman rho| of the category indices; produced by `python scripts/nonmonotone_edges.py` (thesis Sec. 3.9).

The evaluation results (100 seeds, PC and GES) are in `outputs/experiments/hpc/rf_pc/merged/` and
`outputs/experiments/hpc/rf_ges/merged/` (thesis Table 6.11). Check and summarise them with

    python scripts/check_rf_consistency.py outputs/experiments/hpc/rf_pc/merged/rf_per_seed.csv
    python scripts/rf_gap_table.py outputs/experiments/hpc/rf_pc/merged/rf_per_seed.csv outputs/experiments/hpc/rf_ges/merged/rf_per_seed.csv
