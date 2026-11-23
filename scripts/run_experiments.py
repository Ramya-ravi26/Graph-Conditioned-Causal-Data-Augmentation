"""Entry point for the extended (remediation) experiments.

    python scripts/run_experiments.py rq4 --graphs asia insurance alarm mixed_scm --seeds 10
    python scripts/run_experiments.py rq6 --graphs synthetic_scm asia insurance alarm --seeds 30
    python scripts/run_experiments.py composition --n-dags 20
    python scripts/run_experiments.py rq1
    python scripts/run_experiments.py discrete-native
    python scripts/run_experiments.py learned-indegree
    python scripts/run_experiments.py rq2

Every experiment writes CSV/JSON results plus a `.meta.json` provenance file to
--out (default outputs/experiments/). The same commands are wrapped in
slurm/*.slurm for larger seed counts on the Lichtenberg cluster.
"""

import argparse
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "outputs" / "experiments"

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("experiment", choices=["rf", "rq4", "rq6", "composition", "rq5", "rq1", "discrete-native", "learned-indegree", "rq2"])
    p.add_argument("--graphs", nargs="+", default=["synthetic_scm", "asia", "insurance", "alarm"])
    p.add_argument("--seeds", type=int, default=30, help="number of evaluation seeds")
    p.add_argument("--seed-start", type=int, default=0, help="first evaluation seed (for Slurm array splits)")
    p.add_argument("--n-dags", type=int, default=20)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--algorithm", choices=["pc", "ges"], default="pc", help="discovery algorithm for rq6")
    p.add_argument("--rf-algorithms", nargs="+", default=["pc", "ges"], choices=["pc", "ges"],
                   help="discovery algorithms for the random-forest prototype (experiment rf)")
    p.add_argument("--dag-start", type=int, default=0, help="first random-DAG index for composition (array splits)")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = p.parse_args()
    if a.experiment == "rf":
        from gcda.experiments.rf_eval import main
        main(a.graphs, a.seeds, a.out, algorithms=a.rf_algorithms, seed_start=a.seed_start)
    elif a.experiment == "rq4":
        from gcda.experiments.rq4 import main
        main(a.out, a.graphs, a.seeds, seed_start=a.seed_start)
    elif a.experiment == "rq6":
        from gcda.experiments.rq6 import main
        main(a.graphs, a.seeds, a.out, alpha=a.alpha, seed_start=a.seed_start, algorithm=a.algorithm)
    elif a.experiment == "composition":
        from gcda.experiments.composition import main
        main(a.n_dags, a.seeds, a.out, dag_start=a.dag_start)
    elif a.experiment == "rq5":
        from gcda.experiments.composition import main_rq5_only
        main_rq5_only(a.out, a.seeds)
    elif a.experiment == "rq1":
        from gcda.experiments.rq1 import main
        main(a.out)
    elif a.experiment == "discrete-native":
        from gcda.experiments.discrete_native import main
        main(a.out)
    elif a.experiment == "learned-indegree":
        from gcda.experiments.learned_indegree import main
        main(a.out, a.seeds)
    elif a.experiment == "rq2":
        from gcda.experiments.rq2 import main
        main(a.out, a.seeds)
