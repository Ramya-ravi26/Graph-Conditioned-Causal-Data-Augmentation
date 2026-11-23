#!/usr/bin/env bash
# Re-run every local experiment at the CURRENT commit into outputs/verify/ and compare
# with the committed results. Usage (from the repo root, venv active):
#   bash scripts/verify_all_local.sh                 # everything (~2-3 h on 4 cores)
#   bash scripts/verify_all_local.sh sweep rq1 rq5   # only the named steps
# Step names: sweep rq1 rq5 discrete rq2 rq4_small rq6_small composition indegree rq4_ins rq6_ins rq6_alarm compare
set -uo pipefail
V=outputs/verify; mkdir -p "$V/experiments" logs
git rev-parse HEAD > "$V/COMMIT"; git status --porcelain > "$V/DIRTY_FILES"
STEPS="${*:-sweep rq1 rq5 discrete rq2 rq4_small rq6_small composition indegree rq4_ins rq6_ins rq6_alarm compare}"
want() { [[ " $STEPS " == *" $1 "* ]]; }
FAILED=0
run() {
  local name=$1; shift; want "$name" || return 0
  echo "[$(date +%T)] start $name"; local t0=$SECONDS
  if "$@" > "logs/verify_$name.log" 2>&1; then
    echo "$name $((SECONDS - t0)) s" >> "$V/timings.txt"; echo "[$(date +%T)] done $name ($((SECONDS - t0)) s)"
  else
    echo "[$(date +%T)] FAILED $name (see logs/verify_$name.log)"; FAILED=1
  fi
}
E=scripts/run_experiments.py
run sweep          python scripts/sweep_hyperparameters.py --output-dir "$V"
run rq1            python $E rq1 --out "$V/experiments"
run rq5            python $E rq5 --seeds 30 --out "$V/experiments"
run discrete       python $E discrete-native --out "$V/experiments"
run rq2          python $E rq2 --seeds 30 --out "$V/experiments"
run rq4_small    python $E rq4 --graphs asia mixed_scm --seeds 10 --out "$V/experiments/rq4_small"
run rq6_small    python $E rq6 --graphs synthetic_scm asia --seeds 30 --out "$V/experiments/rq6_small"
run composition  python $E composition --n-dags 20 --seeds 10 --out "$V/experiments"
run indegree     python $E learned-indegree --seeds 5 --out "$V/experiments/learned_indegree_v2"
run rq4_ins      python $E rq4 --graphs insurance --seeds 5 --out "$V/experiments/rq4_insurance"
run rq6_ins      python $E rq6 --graphs insurance --seeds 5 --out "$V/experiments/rq6_insurance"
run rq6_alarm    python $E rq6 --graphs alarm --seeds 5 --out "$V/experiments/rq6_alarm"
want compare || exit $FAILED
echo "== comparison: sweep tables"
python scripts/compare_outputs.py outputs "$V" 2>&1 | grep -E "^(OK|DIFF|MISSING) +sweep_"
echo "== comparison: experiments"
python scripts/compare_outputs.py outputs/experiments "$V/experiments"
exit $(( FAILED || $? ))
