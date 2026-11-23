"""Close the loop on the project's actual goal: run a real causal discovery
algorithm (PC, via causal-learn) on our generated data and check whether it
recovers the true graph about as well as it does from real data.

T1-T7 validate statistical realism but never tested this - the whole
motivation stated in the task plan is "graph discovery methods need lots
of training data," so this is the actual bar the generator needs to clear.

Run: python scripts/build_dependency_library.py     (once)
     python scripts/build_discrete_library.py        (once, ~10 min)
     python scripts/evaluate_causal_discovery.py

For both a continuous DAG (synthetic SCM) and a discrete one (Asia),
compares PC's Structural Hamming Distance (SHD) to the true DAG when run
on: the true data itself, our baseline (Gaussian-copula-everywhere)
generated data, and our learned-model generated data. Lower SHD is
better; 0 means PC recovered exactly the same CPDAG as it does from real
data. Averaged over several data-generation seeds rather than a single
draw - PC's result is deterministic given its input, so seed-to-seed
variation here comes entirely from sampling noise in the underlying data,
and a single seed can look artificially good or bad (an earlier one-seed
run of the Asia case made "learned" look like it beat real data outright,
which didn't hold up once averaged over more seeds).
"""

from pathlib import Path

import pandas as pd

from gcda.data.datasets import load_asia, make_synthetic_scm
from gcda.dependency.library import DependencyLibrary
from gcda.evaluation.causal_discovery import compare_causal_discovery, encode_categorical
from gcda.provenance import write_metadata
from gcda.generation.graph_sampler import GraphSampler, NodeSpec, node_spec_from_library

CONTINUOUS_LIBRARY_PATH = Path(__file__).parent.parent / "outputs" / "dependency_library.json"
DISCRETE_LIBRARY_PATH = Path(__file__).parent.parent / "outputs" / "discrete_dependency_library.json"
SEEDS = [0, 1, 2, 3]


def evaluate_continuous(seeds: list[int] = SEEDS) -> pd.DataFrame:
    if not CONTINUOUS_LIBRARY_PATH.exists():
        raise SystemExit(f"{CONTINUOUS_LIBRARY_PATH} not found; run scripts/build_dependency_library.py first")
    library = DependencyLibrary.load(CONTINUOUS_LIBRARY_PATH)

    all_results = []
    for seed in seeds:
        true_df, dag = make_synthetic_scm(n=5000, seed=seed)
        n = len(true_df)

        baseline_specs = {node: NodeSpec(marginal=library.get_marginal("synthetic_scm", node)) for node in dag.nodes}
        baseline_df = GraphSampler(dag, node_specs=baseline_specs).sample(n=n, seed=seed)

        learned_specs = {
            node: node_spec_from_library(library, "synthetic_scm", node, list(dag.predecessors(node)))
            for node in dag.nodes
        }
        learned_df = GraphSampler(dag, node_specs=learned_specs).sample(n=n, seed=seed)

        result = compare_causal_discovery(
            true_df, {"baseline": baseline_df, "learned": learned_df}, dag, indep_test="fisherz",
        )
        result["seed"] = seed
        all_results.append(result)
    return pd.concat(all_results, ignore_index=True)


def evaluate_discrete(seeds: list[int] = SEEDS) -> pd.DataFrame:
    if not DISCRETE_LIBRARY_PATH.exists():
        raise SystemExit(f"{DISCRETE_LIBRARY_PATH} not found; run scripts/build_discrete_library.py first")
    library = DependencyLibrary.load(DISCRETE_LIBRARY_PATH)

    all_results = []
    for seed in seeds:
        true_df, dag, category_orders = load_asia(n_samples=8000, seed=seed)
        n = len(true_df)

        baseline_specs = {node: NodeSpec(marginal=library.get_marginal("asia", node)) for node in dag.nodes}
        baseline_df = GraphSampler(dag, node_specs=baseline_specs, max_indegree=2).sample(n=n, seed=seed)

        learned_specs = {
            node: node_spec_from_library(library, "asia", node, list(dag.predecessors(node)))
            for node in dag.nodes
        }
        learned_df = GraphSampler(dag, node_specs=learned_specs, max_indegree=2).sample(n=n, seed=seed)

        true_encoded = encode_categorical(true_df, category_orders)
        baseline_encoded = encode_categorical(baseline_df, category_orders)
        learned_encoded = encode_categorical(learned_df, category_orders)

        result = compare_causal_discovery(
            true_encoded, {"baseline": baseline_encoded, "learned": learned_encoded}, dag, indep_test="chisq",
        )
        result["seed"] = seed
        all_results.append(result)
    return pd.concat(all_results, ignore_index=True)


def summarize(results: pd.DataFrame) -> pd.DataFrame:
    return results.groupby("source")["shd_to_true_dag"].agg(["mean", "std", "min", "max"])


if __name__ == "__main__":
    print("=== continuous: synthetic SCM, PC with Fisher-Z test ===")
    cont = evaluate_continuous()
    print(cont.pivot(index="seed", columns="source", values="shd_to_true_dag").to_string())
    print("\nmean SHD across seeds (lower is better):")
    print(summarize(cont).to_string())

    print("\n=== discrete: Asia, PC with chi-square test ===")
    disc = evaluate_discrete()
    print(disc.pivot(index="seed", columns="source", values="shd_to_true_dag").to_string())
    print("\nmean SHD across seeds (lower is better):")
    print(summarize(disc).to_string())

    out = Path(__file__).parent.parent / "outputs" / "causal_discovery_results.csv"
    pd.concat([cont.assign(graph="synthetic_scm"), disc.assign(graph="asia")]).to_csv(out, index=False)
    write_metadata(out, seeds=SEEDS)
    print(f"\nSaved per-seed results to {out}")
