#!/bin/bash
#SBATCH -J gcda_indeg
#SBATCH --mail-type=END,FAIL
#SBATCH -A l0003501            # Lichtenberg project the thesis runs were charged to; others: use your own (`csreport`)
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err
#SBATCH --array=0
#SBATCH -n 1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=2000
#SBATCH -t 03:00:00
# Learned conditional vines at indegree 2-4 (Insurance, Alarm), jitter vs native, 10 held-out seeds.
source slurm/env_lichtenberg.sh
python scripts/run_experiments.py learned-indegree --seeds 10 --out "$GCDA_OUT/learned_indegree"
