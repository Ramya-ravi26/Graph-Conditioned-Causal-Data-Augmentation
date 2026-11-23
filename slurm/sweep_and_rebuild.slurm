#!/bin/bash
#SBATCH -J gcda_repro
#SBATCH --mail-type=END,FAIL
#SBATCH -A l0003501            # Lichtenberg project the thesis runs were charged to; others: use your own (`csreport`)
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err
#SBATCH --array=0
#SBATCH -n 1
#SBATCH --cpus-per-task=8
#SBATCH --mem-per-cpu=1500
#SBATCH -t 02:00:00
# Full from-scratch reproduction: rebuild both dependency libraries, rerun every
# thesis script and compare with the committed outputs (never done end-to-end
# locally: the local audit reused the committed library JSON files).
source slurm/env_lichtenberg.sh
D="$GCDA_OUT/repro_$SLURM_JOB_ID"; mkdir -p "$D"
cp -r outputs "$D/committed_outputs"
python t3_validation.py
python scripts/build_dependency_library.py
python scripts/build_discrete_library.py
python scripts/sweep_hyperparameters.py --output-dir "$D/sweep"
python scripts/check_reproduction.py "$D/sweep/sweep_dependency_models.csv" "$D/committed_outputs/sweep_dependency_models.csv"
python scripts/evaluate_generation.py         > "$D/evaluate_generation.txt"
python scripts/evaluate_discrete_generation.py > "$D/evaluate_discrete_generation.txt"
python scripts/evaluate_mixed_generation.py    > "$D/evaluate_mixed_generation.txt"
python scripts/evaluate_causal_discovery.py    > "$D/evaluate_causal_discovery.txt"
python - <<'PY'
import json, hashlib, pathlib
for f in ["outputs/dependency_library.json", "outputs/discrete_dependency_library.json"]:
    new = json.loads(pathlib.Path(f).read_text())
    print(f, "pairwise:", len(new["pairwise"]), "conditional:", len(new["conditional"]))
PY
git diff --stat -- outputs/   # any change vs the committed artifacts is a reproducibility finding
