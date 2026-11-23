#!/bin/bash
#SBATCH -J gcda_rq6
#SBATCH --mail-type=END,FAIL
#SBATCH -A l0003501            # Lichtenberg project the thesis runs were charged to; others: use your own (`csreport`)
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err
#SBATCH --array=0-9                 # 10 tasks x 10 seeds = 100 evaluation seeds per graph
#SBATCH -n 1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=2000          # MB; peak ~3 GB (Alarm, 5 sources)
#SBATCH -t 06:00:00                 # measured locally: ~4 min/seed Insurance, ~3 min/seed Alarm (4 cores)
# Held-out RQ6 (Table 6.6/Fig. 6.10): PC + SHD on SCM, Asia, Insurance, Alarm; 100 seeds.
# ALGO=ges sbatch slurm/rq6_heldout.slurm   runs the same with GES instead of PC.
source slurm/env_lichtenberg.sh
ALGO=${ALGO:-pc}
SEEDS_PER_TASK=10
START=$((SLURM_ARRAY_TASK_ID * SEEDS_PER_TASK))
python scripts/run_experiments.py rq6 --graphs synthetic_scm asia insurance alarm \
    --seeds $SEEDS_PER_TASK --seed-start $START --algorithm $ALGO \
    --out "$GCDA_OUT/rq6_$ALGO/task_$SLURM_ARRAY_TASK_ID"
# after all tasks:  python scripts/merge_results.py rq6 $GCDA_OUT/rq6_$ALGO/task_* --out $GCDA_OUT/rq6_$ALGO/merged
