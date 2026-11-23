#!/usr/bin/env bash
# Shared environment for all gcda Slurm jobs on the TU Darmstadt Lichtenberg cluster.
# Source this from the job scripts. Adjust the module names once to whatever
# `module avail python` / `module avail gcc` list on the cluster (they change
# between software stacks); everything else is self-contained.
set -euo pipefail

: "${GCDA_REPO:=$HOME/Graph-Conditioned-Causal-Data-Augmentation}"        # clone of this repository
: "${GCDA_VENV:=$HOME/venvs/gcda}"              # virtual environment (created by slurm/setup_env.sh)
: "${GCDA_OUT:=$GCDA_REPO/outputs/hpc}"         # results root (consider /work/scratch/$USER for large runs)

module purge
module load gcc python 2>/dev/null || module load python   # e.g. "module load gcc/11.2.0 python/3.11.4"

source "$GCDA_VENV/bin/activate"
cd "$GCDA_REPO"
export WANDB_MODE=offline
# one numerical thread per process; parallelism comes from Slurm tasks / arrays
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p "$GCDA_OUT" logs
python -c "import gcda, sys; print('python', sys.version.split()[0], 'gcda at', gcda.__file__)"
git rev-parse HEAD
