# HPC runbook: Lichtenberg (TU Darmstadt)

This runbook covers the experiments that need more statistical power than a
4-core machine provides: 100-seed downstream evaluations (PC and GES), 50-seed
discrete reconstruction, 200 random DAGs, learned vines at higher indegree, the
random-forest conditionals, and the from-scratch reproduction. Their results are
in `outputs/experiments/hpc/`, and they are what the thesis reports.

All scripts are in `slurm/`. They share `slurm/env_lichtenberg.sh`.

## 0. One-time setup (login node)

```bash
git clone https://github.com/ramya-ravi26/Graph-Conditioned-Causal-Data-Augmentation.git ~/Graph-Conditioned-Causal-Data-Augmentation
```
```bash
cd ~/Graph-Conditioned-Causal-Data-Augmentation && git log -1 --oneline
```
```bash
module avail python
```
Pick a Python ≥ 3.10 module, then edit the two `module load` lines in
`slurm/env_lichtenberg.sh` and `slurm/setup_env.sh`.

```bash
bash slurm/setup_env.sh
```
This creates `~/venvs/gcda`, installs `requirements-lock.txt` and runs the test suite (expected: all tests pass).

```bash
mkdir -p logs
```
Slurm needs this directory to exist for `--output`/`--error`.

**Before the first submission:**
- The job scripts are set to project `l0003501`, under which the thesis runs were made. If you run them under another project, replace it in every `slurm/*.slurm` (`csreport` shows your projects).
- Optionally set `GCDA_OUT=/work/scratch/$USER/gcda` so large outputs land on scratch.

```bash
sed -i 's/l0003501/<your project>/' slurm/*.slurm
```

**Lichtenberg specifics:**
- Partitions are chosen automatically from the requested time and resources.
- `-t` must not exceed the project's limit.
- Memory is requested per CPU (`--mem-per-cpu`, in MB).
- Compute nodes have no internet access. Run every download step (pip, reference datasets) on the login node.

## 1. Jobs

| Job | What it runs | Resources (per array task) | Merged output (`outputs/experiments/hpc/`) | Thesis |
|---|---|---|---|---|
| `rq6_heldout.slurm` | Downstream usefulness with PC, 100 seeds, on SCM, Asia, Insurance, Alarm | 10 tasks × (4 CPU, 8 GB, ≤ 6 h) | `rq6_pc/merged/` | Sec. 6.6 |
| `rq6_heldout.slurm` with `ALGO=ges` | The same with GES (BIC / BDeu) | 10 tasks × (4 CPU, 8 GB, ≤ 12 h) | `rq6_ges/merged/` | Sec. 6.6 |
| `rf_heldout.slurm` (`ALGO=pc` / `ges`) | RQ6 protocol plus random-forest conditionals | 10 tasks × (4 CPU, 8 GB, ≤ 8 h PC / 14 h GES) | `rf_pc/merged/`, `rf_ges/merged/` | Sec. 6.6.1 |
| `rq2_heldout.slurm` | Per-edge dependence reproduction, 100 seeds | 1 task (4 CPU, 8 GB, ≤ 3 h) | `rq2_100/` | Sec. 6.2 |
| `rq4_heldout.slurm` | Discrete/mixed reconstruction (jitter, native, CPT refit), 50 seeds | 5 tasks × (4 CPU, 8 GB, ≤ 4 h) | `rq4/merged/` | Sec. 6.4 |
| `novel_dags.slurm` | 200 random DAGs over the Sachs variables | 10 tasks × (4 CPU, 8 GB, ≤ 4 h) | `novel_dags/merged/` | Sec. 6.5 |
| `learned_indegree.slurm` | Learned vines at indegree 2–4, jitter vs native, 10 seeds | 1 task (4 CPU, 8 GB, ≤ 3 h) | `learned_indegree/` | Sec. 6.3.1 |
| `sweep_and_rebuild.slurm` | Rebuild both libraries, rerun the sweep and every evaluation script, compare with `outputs/` | 1 task (8 CPU, 12 GB, ≤ 2 h) | `repro_<jobid>/` | Sec. 7.3 |
| `sachs_validate.slurm` (or login node) | Checks that the first 853 Sachs rows are the observational condition | login node | `sachs_validation.txt` | Sec. 5.1 |

## 2. Commands

### rq6 (PC, then GES)

```bash
sbatch slurm/rq6_heldout.slurm
```
```bash
ALGO=ges sbatch --time=12:00:00 slurm/rq6_heldout.slurm
```
Once all array tasks are finished:
```bash
source slurm/env_lichtenberg.sh && python scripts/merge_results.py rq6 $GCDA_OUT/rq6_pc/task_* --out $GCDA_OUT/rq6_pc/merged
```
```bash
source slurm/env_lichtenberg.sh && python scripts/merge_results.py rq6 $GCDA_OUT/rq6_ges/task_* --out $GCDA_OUT/rq6_ges/merged
```

### rq4

```bash
sbatch slurm/rq4_heldout.slurm
```
```bash
source slurm/env_lichtenberg.sh && python scripts/merge_results.py rq4 $GCDA_OUT/rq4/task_* --out $GCDA_OUT/rq4/merged
```

### novel-dags

```bash
sbatch slurm/novel_dags.slurm
```
Merge:
```bash
source slurm/env_lichtenberg.sh && python - <<'PY'
import glob, os, pandas as pd
from gcda.experiments.composition import summarize_novel
out = os.environ["GCDA_OUT"] + "/novel_dags/merged"; os.makedirs(out, exist_ok=True)
for tag in ("pooled", "observational"):
    res = pd.concat(pd.read_csv(f) for f in glob.glob(os.environ["GCDA_OUT"] + f"/novel_dags/task_*/novel_dags_{tag}_per_dag.csv"))
    summary, tests = summarize_novel(res)
    res.to_csv(f"{out}/novel_dags_{tag}_per_dag.csv", index=False)
    summary.to_csv(f"{out}/novel_dags_{tag}_summary.csv", index=False)
    tests.to_csv(f"{out}/novel_dags_{tag}_tests.csv", index=False)
    print(tag, res.dag.nunique(), "DAGs"); print(summary.round(3).to_string(index=False))
PY
```

### rf (random-forest conditionals)

```bash
sbatch slurm/rf_heldout.slurm
```
```bash
sbatch --time=14:00:00 --export=ALL,ALGO=ges slurm/rf_heldout.slurm
```
```bash
source slurm/env_lichtenberg.sh && python scripts/merge_results.py rf $GCDA_OUT/rf_pc/task_* --out $GCDA_OUT/rf_pc/merged
```
```bash
source slurm/env_lichtenberg.sh && python scripts/merge_results.py rf $GCDA_OUT/rf_ges/task_* --out $GCDA_OUT/rf_ges/merged
```
The shared sources must equal the RQ6 runs (run once both are in `outputs/experiments/hpc/`):
```bash
python scripts/check_rf_consistency.py $GCDA_OUT/rf_pc/merged/rf_per_seed.csv
```

### rq2

```bash
sbatch slurm/rq2_heldout.slurm
```

### learned-indegree and the from-scratch reproduction

```bash
sbatch slurm/learned_indegree.slurm
```
```bash
sbatch slurm/sweep_and_rebuild.slurm
```

### sachs-verify (login node)

```bash
wget https://www.bnlearn.com/book-crc/code/sachs.data.txt.gz && gunzip sachs.data.txt.gz
```
```bash
python scripts/verify_sachs_subset.py sachs.data.txt
```

## 3. Checking and storing results

1. Check every job with `sacct -j <JOBID> --format=JobID,State,ExitCode,Elapsed,MaxRSS` (all `COMPLETED`, `0:0`); `merge_results.py` refuses duplicated rows and prints the number of seeds merged.
2. Copy each `merged/` directory into `outputs/experiments/hpc/<job>/` and commit it together with its `.meta.json` provenance files.
3. `python scripts/check_hpc_results.py` runs the integrity and cross-machine checks on `outputs/experiments/hpc/`.
