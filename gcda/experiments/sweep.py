"""T6c/T7: sweep key hyperparameters and log metrics (optionally to W&B).

Sweeps (all read from configs/sweep.yaml):
  1. dependency-model sweep: copula family set x AIC/BIC x dataset, for one
     multi-parent conditional target per dataset (Table 6.1);
  2. indegree-cap sweep: GraphSampler's Gaussian baseline at 2..K parents,
     repeated over several seeds, with the theoretical tau as reference
     (Table 6.2);
  3. clipping-epsilon sweep: the stability guard's epsilon (task T6c
     "clipping/fallback settings"), recording fallback draws and accuracy.
"""

import os
import time
from itertools import chain, product
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import pyvinecopulib as pv
import yaml
from scipy.stats import kendalltau

from gcda.data.preprocessing import handle_missing_values, to_pseudo_observations_mixed
from gcda.data.registry import load_dataset
from gcda.dependency.conditional import EPS, ConditionalSampler
from gcda.evaluation.realism import compare_pairwise_dependence, energy_distance, gaussian_mmd
from gcda.generation.graph_sampler import GraphSampler, valid_baseline_rho

WANDB_PROJECT = "graph-conditioned-augmentation"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "configs" / "sweep.yaml"
OUTPUT_DIR = REPO_ROOT / "outputs"

# sample sizes used by the sweep (kept from the thesis runs for exact reproducibility)
SWEEP_N = {"synthetic_scm": 5000, "asia": 8000, "insurance": 8000}
SWEEP_SEED = {"synthetic_scm": 1, "asia": 0, "insurance": 0}


def load_config(path: Path) -> dict:
    config = yaml.safe_load(Path(path).read_text())
    config["family_sets"] = {
        name: [getattr(pv.BicopFamily, family) for family in families]
        for name, families in config["family_sets"].items()
    }
    return config


def _prepare(dataset_name: str) -> pd.DataFrame:
    df, _dag, category_orders = load_dataset(dataset_name, n=SWEEP_N.get(dataset_name), seed=SWEEP_SEED.get(dataset_name))
    clean, _ = handle_missing_values(df, strategy="drop")
    u_df, _ = to_pseudo_observations_mixed(clean, category_orders=category_orders, seed=0)
    return u_df


def _evaluate_sampler(sampler: ConditionalSampler, u_df: pd.DataFrame, child: str, parents: list[str]) -> dict:
    columns = [child, *parents]
    u_sim = sampler.sample(u_df[parents].to_numpy(), seed=0)
    sim_u_df = u_df[parents].copy()
    sim_u_df[child] = u_sim
    dep = compare_pairwise_dependence(u_df[columns], sim_u_df[columns], pairs=[(child, p) for p in parents])
    data_np, sim_np = u_df[columns].to_numpy(), sim_u_df[columns].to_numpy()
    return {
        "mean_tau_abs_error": dep["tau_abs_error"].mean(),
        "energy_distance": energy_distance(data_np, sim_np),
        "gaussian_mmd": gaussian_mmd(data_np, sim_np),
        "n_fallback": sampler.last_fallback_count_,
    }


def run_dependency_sweep(config: dict, use_wandb: bool = False) -> pd.DataFrame:
    targets = config["targets"]
    family_sets = config["family_sets"]
    rows = []
    for dataset_name, family_set_name, criterion in product(targets, family_sets, config["selection_criteria"]):
        print(f"  {dataset_name} / {family_set_name} / {criterion}")
        u_df = _prepare(dataset_name)
        child, parents = targets[dataset_name]["child"], targets[dataset_name]["parents"]
        sampler = ConditionalSampler(
            child=child, parents=parents, family_set=family_sets[family_set_name], selection_criterion=criterion,
        ).fit(u_df)
        data_np = u_df[[child, *parents]].to_numpy()
        vine = sampler.vine_
        metrics = {
            "dataset": dataset_name,
            "family_set": family_set_name,
            "selection_criterion": criterion,
            "child": child,
            "parents": ",".join(parents),
            "n": len(u_df),
            "vine_aic": vine.aic(data_np),
            "vine_bic": vine.bic(data_np),
            "families_selected": ",".join(f.name for f in chain.from_iterable(vine.families)),
            **_evaluate_sampler(sampler, u_df, child, parents),
            "clip_eps": EPS,
        }
        rows.append(metrics)
        if use_wandb:
            import wandb
            wandb.log(metrics)
    return pd.DataFrame(rows)


def run_indegree_sweep(config: dict, use_wandb: bool = False) -> pd.DataFrame:
    """Baseline Gaussian sampler at increasing indegree caps.

    The per-parent correlation is capped by `valid_baseline_rho` so the
    baseline stays a valid (positive-definite) model at every cap; the
    theoretical tau = 2/pi * arcsin(rho_eff) is reported alongside. Each cap is
    repeated `repeats` times with seeds seed, seed+1, ... (repeat 0 uses the
    original seed, so its row equals the thesis' single run for caps 2-3).
    """
    spec = config["indegree_sweep"]
    rho, n, seed, repeats = spec["baseline_rho"], spec["n"], spec["seed"], spec.get("repeats", 1)
    rows = []
    for cap in spec["caps"]:
        parents = [f"P{i}" for i in range(cap)]
        dag = nx.DiGraph()
        dag.add_nodes_from([*parents, "X"])
        dag.add_edges_from([(p, "X") for p in parents])
        rho_eff = valid_baseline_rho(cap, rho)
        for r in range(repeats):
            print(f"  indegree_cap={cap} repeat={r}")
            t0 = time.perf_counter()
            sampler = GraphSampler(dag, max_indegree=cap, baseline_rho=rho)
            df = sampler.sample(n=n, seed=seed + r)
            elapsed = time.perf_counter() - t0
            taus = [kendalltau(df[p], df["X"])[0] for p in parents]
            metrics = {
                "indegree_cap": cap,
                "repeat": r,
                "seed": seed + r,
                "baseline_rho": rho,
                "rho_effective": rho_eff,
                "tau_theoretical": float(2 / np.pi * np.arcsin(rho_eff)),
                "mean_tau": float(np.mean(taus)),
                "min_tau": float(np.min(taus)),
                "max_tau": float(np.max(taus)),
                "elapsed_sec": elapsed,
                "fallback_draws": sampler.total_fallback_draws,
                "clip_eps": EPS,
            }
            rows.append(metrics)
            if use_wandb:
                import wandb
                wandb.log(metrics)
    return pd.DataFrame(rows)


def run_clip_sweep(config: dict, use_wandb: bool = False) -> pd.DataFrame:
    """Vary the clipping epsilon of the conditional sampler (T6c)."""
    spec = config.get("clip_sweep")
    if not spec:
        return pd.DataFrame()
    targets = config["targets"]
    rows = []
    for dataset_name in spec["datasets"]:
        u_df = _prepare(dataset_name)
        child, parents = targets[dataset_name]["child"], targets[dataset_name]["parents"]
        for eps in spec["eps_values"]:
            print(f"  clip sweep {dataset_name} eps={eps}")
            sampler = ConditionalSampler(child=child, parents=parents, clip_eps=float(eps)).fit(u_df)
            metrics = {"dataset": dataset_name, "clip_eps": float(eps), **_evaluate_sampler(sampler, u_df, child, parents)}
            rows.append(metrics)
            if use_wandb:
                import wandb
                wandb.log(metrics)
    return pd.DataFrame(rows)


def main(config_path: Path = DEFAULT_CONFIG_PATH, use_wandb: bool = False, output_dir: Path = OUTPUT_DIR) -> None:
    from gcda.provenance import write_metadata

    config = load_config(config_path)
    if use_wandb:
        import wandb
        wandb.init(
            project=WANDB_PROJECT, name="hyperparameter-sweep",
            mode=os.environ.get("WANDB_MODE", "offline"),
            config={"config_file": str(config_path), **yaml.safe_load(Path(config_path).read_text())},
        )

    print("Dependency-model sweep (family set x AIC/BIC x dataset):")
    dep_results = run_dependency_sweep(config, use_wandb=use_wandb)
    print("\nIndegree-cap sweep:")
    indegree_results = run_indegree_sweep(config, use_wandb=use_wandb)
    print("\nClipping-epsilon sweep:")
    clip_results = run_clip_sweep(config, use_wandb=use_wandb)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in [("sweep_dependency_models.csv", dep_results), ("sweep_indegree_cap.csv", indegree_results),
                        ("sweep_clip_eps.csv", clip_results)]:
        frame.to_csv(output_dir / name, index=False)
        write_metadata(output_dir / name, config_file=str(config_path))

    print("\n=== dependency-model sweep results ===")
    print(dep_results.drop(columns=["parents", "families_selected"]).to_string(index=False))
    print("\n=== indegree-cap sweep results (mean over repeats) ===")
    print(indegree_results.groupby("indegree_cap")[["rho_effective", "tau_theoretical", "mean_tau", "elapsed_sec"]].mean().to_string())
    if not clip_results.empty:
        print("\n=== clipping-epsilon sweep ===")
        print(clip_results.to_string(index=False))
    print(f"\nSaved results to {output_dir}/")

    if use_wandb:
        import wandb
        wandb.finish()
