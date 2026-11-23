#!/bin/bash
#SBATCH -J gcda_rq2
#SBATCH --mail-type=END,FAIL
#SBATCH -A l0003501            # Lichtenberg project the thesis runs were charged to; others: use your own (`csreport`)
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#SBATCH -n 1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=2000
#SBATCH -t 03:00:00
# Held-out RQ2 (Sec. 6.2): synthetic SCM, 100 evaluation seeds (permutation tests on the first 10).
source slurm/env_lichtenberg.sh
python scripts/run_experiments.py rq2 --seeds 100 --out "$GCDA_OUT/rq2_100"
