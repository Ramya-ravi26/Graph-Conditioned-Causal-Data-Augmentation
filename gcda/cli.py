"""GCDA command-line interface (T8b.ii).

    gcda build-library --dataset sachs --output lib_sachs.json [--dag graph.json]
    gcda generate --dag graph.json --library lib_sachs.json [--library lib_asia.json ...]
                  [--dataset sachs] --n 5000 --output data.csv [--calibrate-margins] [--strict]
    gcda evaluate --true-csv true.csv --sim-csv data.csv [--distances]
    gcda sweep [--wandb] [--config configs/sweep.yaml]

`generate` accepts several libraries (merged; dataset namespaces must not
collide) and a graph spec that can map each node to a (dataset, variable) and
bind any learned pair copula to any edge, so one graph can combine building
blocks learned on different datasets (see gcda/generation/spec.py). A JSON
report of every modelling decision, fallback and per-node diagnostic is
written next to the output CSV.
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from gcda.data.preprocessing import (
    discrete_cdf_pairs,
    handle_missing_values,
    to_pseudo_observations,
    to_pseudo_observations_mixed,
)
from gcda.data.registry import DATASET_NAMES, load_dataset
from gcda.dependency.conditional import ConditionalSampler
from gcda.dependency.library import DependencyLibrary
from gcda.dependency.pairwise import build_pairwise_library
from gcda.evaluation.realism import (
    compare_marginals,
    compare_pairwise_dependence,
    energy_distance,
    gaussian_mmd,
    permutation_test,
)
from gcda.generation.graph_sampler import GraphSampler
from gcda.generation.spec import StrictModeError, build_node_specs, load_graph_spec, parse_graph_spec
from gcda.provenance import run_metadata


def cmd_build_library(args: argparse.Namespace) -> None:
    df, dag, category_orders = load_dataset(args.dataset, n=args.n, seed=args.seed)
    df, _ = handle_missing_values(df, strategy="drop")
    u_df, marginals = to_pseudo_observations_mixed(df, category_orders=category_orders, seed=0)
    u_minus, var_types = None, None
    if args.discrete_mode == "native":
        u_df, u_minus, var_types = discrete_cdf_pairs(df, marginals)

    library = DependencyLibrary()
    library.metadata = run_metadata(dataset=args.dataset, n_rows=len(df), criterion=args.criterion,
                                    discrete_mode=args.discrete_mode)
    library.add_marginals(args.dataset, marginals, max_points=args.max_marginal_points)
    pairwise_entries = build_pairwise_library(
        u_df, dataset_name=args.dataset, selection_criterion=args.criterion, n_jobs=args.n_jobs,
        u_minus_df=u_minus, var_types=var_types,
    )
    library.add_pairwise(pairwise_entries)
    n_ok = sum(1 for e in pairwise_entries if "error" not in e)
    print(f"fit {n_ok}/{len(pairwise_entries)} pairwise models")

    # multi-parent targets: the dataset's own DAG (if it has one) plus any user graphs
    targets: dict[tuple[str, frozenset], list[str]] = {}
    graphs = [dag] if dag is not None and not args.no_dataset_dag else []
    for path in args.dag or []:
        graphs.append(parse_graph_spec(load_graph_spec(path))[0])
    for graph in graphs:
        for node in graph.nodes:
            parents = [p for p in graph.predecessors(node)]
            if len(parents) >= 2 and node in u_df.columns and all(p in u_df.columns for p in parents):
                targets[(node, frozenset(parents))] = parents
    for (node, _), parents in targets.items():
        sampler = ConditionalSampler(child=node, parents=parents, selection_criterion=args.criterion)
        sampler.fit(u_df, u_minus, var_types)
        library.add_conditional(args.dataset, sampler)
    print(f"fit {len(targets)} multi-parent conditional models")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    library.save(args.output)
    print(f"saved library to {args.output}")


def cmd_generate(args: argparse.Namespace) -> None:
    spec = load_graph_spec(args.dag)
    library = DependencyLibrary.load_many(args.library)
    try:
        dag, node_specs, report = build_node_specs(
            library, spec, default_dataset=args.dataset, compose=not args.no_compose, strict=args.strict,
        )
    except StrictModeError as exc:
        raise SystemExit(f"error: {exc}") from None
    fallbacks = [r for r in report if "baseline" in r["decision"]]
    if fallbacks:
        nodes = sorted({r["node"] for r in fallbacks})
        print(f"warning: baseline fallback for {nodes} ({len(fallbacks)} decision(s)); see the report file",
              file=sys.stderr)

    sampler = GraphSampler(dag, node_specs=node_specs, max_indegree=args.max_indegree,
                           calibrate_margins=args.calibrate_margins)
    df = sampler.sample(n=args.n, seed=args.seed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    report_path = args.output.with_name(args.output.name + ".report.json")
    report_path.write_text(json.dumps({
        "metadata": run_metadata(n=args.n, seed=args.seed, libraries=[str(p) for p in args.library]),
        "decisions": report,
        "diagnostics": sampler.diagnostics_,
    }, indent=2, default=str))
    print(f"generated {len(df)} rows x {len(df.columns)} columns -> {args.output} (report: {report_path.name})")


def cmd_evaluate(args: argparse.Namespace) -> None:
    true_df = pd.read_csv(args.true_csv)
    sim_df = pd.read_csv(args.sim_csv)
    common = [c for c in true_df.columns if c in sim_df.columns]
    if len(common) < len(true_df.columns):
        print(f"warning: comparing only shared columns {common}", file=sys.stderr)

    print("=== marginals ===")
    print(compare_marginals(true_df[common], sim_df[common]).to_string(index=False))
    print("\n=== pairwise dependence ===")
    print(compare_pairwise_dependence(true_df[common], sim_df[common]).to_string(index=False))
    if args.distances:
        numeric = [c for c in common if pd.api.types.is_numeric_dtype(true_df[c])]
        tu, _ = to_pseudo_observations(true_df[numeric])
        su, _ = to_pseudo_observations(sim_df[numeric])
        print("\n=== U-space distribution distances (unbiased, permutation p-value) ===")
        for name, stat in [("energy_distance", energy_distance), ("gaussian_mmd", gaussian_mmd)]:
            res = permutation_test(stat, tu.to_numpy(), su.to_numpy(), n_permutations=args.permutations)
            print(f"{name}: {res['statistic']:.5f}  p={res['p_value']:.3f}")


def cmd_sweep(args: argparse.Namespace) -> None:
    from gcda.experiments.sweep import DEFAULT_CONFIG_PATH, main

    main(config_path=args.config or DEFAULT_CONFIG_PATH, use_wandb=args.wandb)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gcda", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_p = subparsers.add_parser("build-library", help="fit a dependency library from one dataset")
    build_p.add_argument("--dataset", required=True, choices=DATASET_NAMES)
    build_p.add_argument("--output", type=Path, required=True)
    build_p.add_argument("--dag", type=Path, action="append",
                         help="graph spec(s) whose multi-parent nodes should get fitted conditional vines (repeatable)")
    build_p.add_argument("--no-dataset-dag", action="store_true", help="do not fit vines for the dataset's own DAG")
    build_p.add_argument("--criterion", choices=["aic", "bic"], default="bic")
    build_p.add_argument("--discrete-mode", choices=["jitter", "native"], default="jitter",
                         help="discrete columns: jittered pseudo-observations (thesis default) or the native "
                              "discrete copula likelihood (recommended for skewed categorical data)")
    build_p.add_argument("--n", type=int, default=None, help="rows to simulate (synthetic/BN datasets)")
    build_p.add_argument("--seed", type=int, default=None)
    build_p.add_argument("--n-jobs", type=int, default=1)
    build_p.add_argument("--max-marginal-points", type=int, default=None,
                         help="compress stored empirical marginals to this many quantile knots")
    build_p.set_defaults(func=cmd_build_library)

    gen_p = subparsers.add_parser("generate", help="sample data for a user-specified graph")
    gen_p.add_argument("--dag", type=Path, required=True, help="graph spec JSON (see gcda/generation/spec.py)")
    gen_p.add_argument("--library", type=Path, required=True, action="append",
                       help="dependency library JSON (repeatable; libraries are merged)")
    gen_p.add_argument("--dataset", default=None, help="default dataset namespace for nodes without a mapping")
    gen_p.add_argument("--n", type=int, default=1000)
    gen_p.add_argument("--seed", type=int, default=0)
    gen_p.add_argument("--max-indegree", type=int, default=4)
    gen_p.add_argument("--no-compose", action="store_true",
                       help="do not compose multi-parent models from pairwise copulas (use the Gaussian baseline instead)")
    gen_p.add_argument("--calibrate-margins", action="store_true",
                       help="rank-calibrate each node so its stored marginal is reproduced exactly")
    gen_p.add_argument("--strict", action="store_true", help="fail instead of falling back to baseline models")
    gen_p.add_argument("--output", type=Path, required=True)
    gen_p.set_defaults(func=cmd_generate)

    eval_p = subparsers.add_parser("evaluate", help="compare a generated CSV against a true-data CSV")
    eval_p.add_argument("--true-csv", type=Path, required=True)
    eval_p.add_argument("--sim-csv", type=Path, required=True)
    eval_p.add_argument("--distances", action="store_true", help="also report U-space energy distance / MMD with permutation tests")
    eval_p.add_argument("--permutations", type=int, default=200)
    eval_p.set_defaults(func=cmd_evaluate)

    sweep_p = subparsers.add_parser("sweep", help="run the hyperparameter sweep (configs/sweep.yaml)")
    sweep_p.add_argument("--wandb", action="store_true", help="log to Weights & Biases (offline by default)")
    sweep_p.add_argument("--config", type=Path, default=None)
    sweep_p.set_defaults(func=cmd_sweep)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
