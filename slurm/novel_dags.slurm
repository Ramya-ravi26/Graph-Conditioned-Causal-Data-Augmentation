#!/bin/bash
#SBATCH -J gcda_novel
#SBATCH --mail-type=END,FAIL
#SBATCH -A l0003501            # Lichtenberg project the thesis runs were charged to; others: use your own (`csreport`)
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err
#SBATCH --array=0-9                 # 10 tasks x 20 random DAGs = 200 novel graphs
#SBATCH -n 1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=2000
#SBATCH -t 04:00:00                 # ~1.5 min per DAG (pooled + observational, 4 generators x 2 calibration modes)
# RQ5 novel-graph study (Table 6.5): random DAGs over the Sachs variables.
source slurm/env_lichtenberg.sh
python scripts/run_experiments.py composition --n-dags 20 --dag-start $((SLURM_ARRAY_TASK_ID * 20)) --seeds 30 \
    --out "$GCDA_OUT/novel_dags/task_$SLURM_ARRAY_TASK_ID"
# merge: concatenate novel_dags_*_per_dag.csv over tasks, then
#   python -c "import pandas as pd, glob; from gcda.experiments.composition import summarize_novel; ..."
# (see docs/HPC_RUNBOOK.md, section 'novel-dags')
