#!/bin/bash
#SBATCH -J gcda_rf
#SBATCH --mail-type=END,FAIL
#SBATCH -A l0003501            # Lichtenberg project the thesis runs were charged to; others: use your own (`csreport`)
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err
#SBATCH --array=0-9                 # 10 tasks x 10 seeds = 100 evaluation seeds per graph
#SBATCH -n 1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=2000          # MB; forests add < 1 GB on Alarm
#SBATCH -t 08:00:00                 # PC; for GES submit with --time=14:00:00 (RQ6-GES + one more source)
# Random-forest conditionals (thesis Sec. 3.9/6.6.1): the RQ6 held-out protocol with the
# extra source learned_rf, on SCM, Asia, Insurance, Alarm; 100 seeds.
# ALGO=ges: sbatch --time=14:00:00 --export=ALL,ALGO=ges slurm/rf_heldout.slurm
source slurm/env_lichtenberg.sh
ALGO=${ALGO:-pc}
SEEDS_PER_TASK=10
START=$((SLURM_ARRAY_TASK_ID * SEEDS_PER_TASK))
python scripts/run_experiments.py rf --graphs synthetic_scm asia insurance alarm \
    --seeds $SEEDS_PER_TASK --seed-start $START --rf-algorithms $ALGO \
    --out "$GCDA_OUT/rf_$ALGO/task_$SLURM_ARRAY_TASK_ID"
# after all tasks:  python scripts/merge_results.py rf $GCDA_OUT/rf_$ALGO/task_* --out $GCDA_OUT/rf_$ALGO/merged
