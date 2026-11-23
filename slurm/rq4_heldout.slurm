#!/bin/bash
#SBATCH -J gcda_rq4
#SBATCH --mail-type=END,FAIL
#SBATCH -A l0003501            # Lichtenberg project the thesis runs were charged to; others: use your own (`csreport`)
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err
#SBATCH --array=0-4                 # 5 tasks x 10 seeds = 50 seeds
#SBATCH -n 1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=2000
#SBATCH -t 04:00:00
# Held-out RQ4 (Table 6.4): discrete/mixed network reconstruction, jitter vs native vs CPT refit.
source slurm/env_lichtenberg.sh
START=$((SLURM_ARRAY_TASK_ID * 10))
python scripts/run_experiments.py rq4 --graphs asia insurance alarm mixed_scm --seeds 10 --seed-start $START \
    --out "$GCDA_OUT/rq4/task_$SLURM_ARRAY_TASK_ID"
# after all tasks:  python scripts/merge_results.py rq4 $GCDA_OUT/rq4/task_* --out $GCDA_OUT/rq4/merged
