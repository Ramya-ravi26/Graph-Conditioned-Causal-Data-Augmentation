#!/usr/bin/env bash
# One-time setup on a Lichtenberg login node (has internet access):
#   bash slurm/setup_env.sh
set -euo pipefail
: "${GCDA_REPO:=$HOME/Graph-Conditioned-Causal-Data-Augmentation}"
: "${GCDA_VENV:=$HOME/venvs/gcda}"
module purge
module load gcc python 2>/dev/null || module load python
python3 -c 'import sys; assert sys.version_info >= (3, 10), "need Python >= 3.10: pick a newer python module"'
python3 -m venv "$GCDA_VENV"
source "$GCDA_VENV/bin/activate"
pip install --upgrade pip
cd "$GCDA_REPO"
# exact versions that reproduced every thesis table; fall back to the unpinned
# requirements if a pinned wheel is unavailable for the cluster's Python
pip install -r requirements-lock.txt || pip install -r requirements.txt
pip install -e . --no-deps
pytest -q
