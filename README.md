# Graph-Conditioned Causal Data Augmentation (GCDA)

A synthetic data generator that learns pairwise/local dependencies from
real data (via copulas) and reuses them as building blocks to sample data
for a user-specified graph, so causal-discovery/structure-learning methods
have more training data to work with (see `Master Thesis Task Plan`).

## Setup

Requires Python >= 3.10 (the codebase uses `X | Y` union type hints,
which don't parse on 3.9). Check with `python3 --version` before
installing, especially on a shared/HPC environment where the default
`python3` may be older - use `module avail python`/`module avail
anaconda` to find a newer one if needed.

```bash
conda env create -f environment.yml
conda activate gcda
pip install -e .   # installs the gcda package + the `gcda` CLI

# or, without conda:
pip install -e ".[test]"   # pyproject.toml's own dependency list + pytest
```

`pyproject.toml` gives lower bounds (and `pgmpy<1.3`, because pgmpy 1.3
removes the bundled-network loader). `requirements-lock.txt` pins the exact
environment in which every thesis table was reproduced bit-for-bit:

```bash
pip install -r requirements-lock.txt && pip install -e . --no-deps
```

Every output file gets a `<name>.meta.json` next to it with package
versions, git commit and arguments (`gcda/provenance.py`).
The git commits recorded in the result files of `outputs/` refer to the
development repository in which the experiments were run.

## Repository structure

```
gcda/                   the installable package
  data/                 dataset loaders (T4a/T7b) + preprocessing (T4b/T7c)
  dependency/            pairwise (T4c) + conditional (T4d) copula fitting, DependencyLibrary
  generation/            GraphSampler (T5)
  evaluation/            realism (T6a), graph-conditioning (T6b), discrete (T7d), causal_discovery
  cli.py                 `gcda` command (build-library / generate / evaluate / sweep)
scripts/                narrated, single-purpose entry points (see each T-section below);
                        the CLI is the composable interface, these are the detailed reports/demos
configs/                sweep.yaml - what scripts/sweep_hyperparameters.py sweeps
  experiments/           sweep + held-out multi-seed experiments (RQ1-RQ6, ablations)
  provenance.py          run metadata attached to every output
data/raw/               provenance notes for the bundled Sachs data (the CSV is package data in gcda/data/resources/)
tests/                  pytest suite (mirrors the package layout; `pytest` runs it)
outputs/                versioned result artifacts the thesis tables come from (+ .meta.json provenance)
slurm/, docs/HPC_RUNBOOK.md  Lichtenberg job scripts for the large-seed runs
thesis/                 thesis LaTeX source + bibliography (`thesis/build.sh` builds the PDF)
thesis_audit/           record of the corrections made after the audit (thesis text and code)
LAB_NOTEBOOK.md         T8a - chronological decisions, bugs found/fixed, and results
```

## CLI

Installed as the `gcda` command (see `gcda/cli.py`):

```bash
gcda build-library --dataset sachs --output lib_sachs.json
gcda build-library --dataset asia --discrete-mode native --output lib_asia.json
gcda generate --dag graph.json --library lib_sachs.json --library lib_asia.json --n 5000 --output data.csv
gcda evaluate --true-csv true.csv --sim-csv data.csv --distances
gcda sweep [--wandb]
```

`graph.json` is any DAG, not necessarily a dataset's own structure. Simplest
form: `{"edges": [["a", "b"], ["a", "c"]]}` (nodes looked up in `--dataset`).
Full form (several libraries are merged; namespaces must not collide):

```json
{"nodes": {"praf": {"dataset": "sachs"}, "pmek": {"dataset": "sachs"}, "dysp": {"dataset": "asia"}},
 "edges": [["praf", "pmek"],
           {"from": "praf", "to": "dysp", "copula": {"dataset": "asia", "pair": ["bronc", "dysp"]}}]}
```

- each node's marginal comes from its (dataset, variable);
- an edge uses an explicit `copula` binding (any learned pair from any
  dataset; the first variable of `pair` plays the parent role), else the
  learned pair copula of its endpoints if both come from one dataset;
- a multi-parent node uses a fitted vine for that parent *set* (edge order
  does not matter), else a model composed from its edges' pairwise copulas
  (`gcda/dependency/composed.py`), else the Gaussian baseline;
- every decision and every baseline fallback is written to
  `data.csv.report.json`; `--strict` turns fallbacks into errors;
  `--calibrate-margins` reproduces every node's marginal exactly (see
  "compatibility" in `gcda/generation/graph_sampler.py`).

## Smoke test

```bash
python smoke_test.py
```

Fits a Gaussian copula on random uniform data, samples from it, and logs
Kendall's tau (original vs. generated) to W&B.

## T3: tool choice + validation on toy data

`pyvinecopulib` is used as the main copula/vine library (see the module
docstring in `t3_validation.py` for the rationale).

```bash
python t3_validation.py
```

For each of Gaussian, Student-t and Clayton copulas with known parameters,
this script:
1. generates toy data from the known copula,
2. fits a copula back and checks that the recovered family, parameters and
   Kendall's tau match the ground truth,
3. samples new data from the *fitted* copula and checks that its dependence
   statistics (Kendall's tau, Spearman's rho) match the original data.

Diagnostic scatter/histogram plots are written to `outputs/t3_validation/`.
Exits with a non-zero status if any check fails.

## T4: dependency library from real continuous datasets

`gcda/` holds the reusable package code:

- `data/datasets.py` — the three Phase 1 datasets: `load_sachs()` (a real
  continuous causal-discovery benchmark, bundled in `data/raw/`),
  `load_uci_diabetes()` (UCI-style robustness dataset, via scikit-learn),
  and `make_synthetic_scm()` (a small synthetic SCM with a known DAG).
- `data/preprocessing.py` — missing-value handling, rank-transform to
  U(0,1) pseudo-observations (`to_pseudo_observations`), and the
  `EmpiricalMarginal` class that maps U back to original units.
- `dependency/pairwise.py` — fits a bivariate copula per variable pair,
  selecting the family via AIC/BIC (`build_pairwise_library`), storing
  family/parameters/tau/AIC/BIC metadata for each pair.
- `dependency/conditional.py` — `ConditionalSampler`, a small 3-variable
  vine copula that samples `child | parent1, parent2` (via a forward +
  inverse Rosenblatt transform), with clipping and a fallback to
  independent sampling if fitting/sampling becomes unstable.
- `dependency/library.py` — `DependencyLibrary`, a JSON-serializable
  container for the pairwise models, conditional models and marginals,
  used later (T5) to sample data for an arbitrary graph.

Build the library for all three datasets:

```bash
python scripts/build_dependency_library.py
```

This preprocesses each dataset, fits pairwise models for every variable
pair, fits one 2-parent conditional model per dataset, prints a
resampled-vs-true dependence sanity check, and saves everything to
`outputs/dependency_library.json`.

Run the test suite (preprocessing round-trips, pairwise family recovery,
conditional sampler vs. closed-form Gaussian theory, library
serialization):

```bash
pytest tests/
```

## T5: generate data for a given graph (continuous)

`gcda/generation/graph_sampler.py` implements `GraphSampler`:
given a DAG (a `networkx.DiGraph`, indegree <= 2 by default; raise
`max_indegree` for the 3-4 parent extension) it samples an n x p dataset in
topological order, node by node:

- indegree 0 (root): draws from a marginal (`EmpiricalMarginal` from the
  T4 library, or a standard-normal baseline if none is given).
- indegree 1: samples the child conditional on its parent via a fitted
  `pv.Bicop`'s h-function inverse (a T4 pairwise model, or — as a simple
  baseline — a fixed-correlation Gaussian copula).
- indegree >= 2: samples via a T4 `ConditionalSampler` vine (or a baseline
  Gaussian vine if none is given).

Every node's sampling step is wrapped in a try/except with a non-finite
check; on failure it logs a warning and falls back to an independent
U(0,1) draw for that node, so one bad edge/model cannot break the whole
generation run.

`node_spec_from_library(library, dataset, node, parents)` looks up the
right pairwise/conditional model and marginal for a node straight from a
T4 `DependencyLibrary`, so a graph mirroring (part of) a real dataset's
variables can be sampled using models learned from that dataset.

```bash
python scripts/generate_graph_data.py
```

Compares, on the synthetic SCM's known DAG, the baseline (Gaussian
copula everywhere) against the run using T4's learned models: the
baseline reproduces one fixed dependence strength for every edge, while
the learned-model run recovers each edge's true (very different)
dependence strength almost exactly.

## T6: evaluation + hyperparameter sweeps (continuous)

`gcda/evaluation/` holds the evaluation code:

- `realism.py` (T6a) — `compare_marginals` (KS statistic, decile quantile
  L1 distance) and `compare_pairwise_dependence` (Kendall's tau,
  Spearman's rho) between true and simulated data, plus `plot_marginals` /
  `plot_pairwise_scatter` for visual checks. `energy_distance` and
  `gaussian_mmd` give a single multivariate distribution-distance number
  (computed on rank-transformed U-space data, since marginal realism is
  already covered separately and U-space keeps every variable on the
  same scale), used to check that the learned models actually improve on
  the Gaussian-everywhere baseline.
- `graph_conditioning.py` (T6b) — `edge_removal_effect` checks that
  deleting an edge collapses the corresponding dependence towards zero;
  `dependence_strength_sweep` checks that strengthening an edge's copula
  parameter increases the resulting Kendall's tau monotonically.

```bash
python scripts/evaluate_generation.py
```

Runs both T6a and T6b on the synthetic SCM, comparing the baseline against
the learned-model run against the true data, and writes marginal/pairwise
diagnostic plots to `outputs/t6_evaluation/`. The baseline keeps each
node's *real* marginal (from the library) and only swaps in baseline
Gaussian dependence, so the comparison isolates what the learned
dependence model contributes rather than conflating it with marginal
mismatch (an earlier version of this script always used a standard-normal
baseline marginal regardless of the node's actual distribution).

```bash
python scripts/sweep_hyperparameters.py [--wandb] [--config configs/sweep.yaml]
```

T6c/T7: sweeps copula family set (`gaussian_only` vs. the full
`parametric` set) x AIC-vs-BIC selection x dataset choice for the
2-parent conditional model — across *both* continuous (Sachs, UCI
diabetes, synthetic SCM) and discrete (Asia, Insurance) datasets — plus a
separate indegree-cap sweep (2/3/4 parents) for `GraphSampler`. What gets
swept lives in `configs/sweep.yaml` (T8b.i), not hardcoded in the script,
so a run is reproducible from a versioned config file. Every row also
records the clipping epsilon and the number of fallback draws used.
Results are saved to `outputs/sweep_dependency_models.csv` and
`outputs/sweep_indegree_cap.csv`. Pass `--wandb` to also log each run to
Weights & Biases; it defaults to offline mode (no credentials required) —
set `WANDB_MODE=online` and log in beforehand to sync for real.

## T7 (extension): mixed/discrete variables

The key idea: continuize discrete/categorical columns to U(0,1) via
jittering, then reuse every piece of T4/T5/T6 unchanged - pairwise fitting,
the conditional sampler, `GraphSampler`, the evaluation metrics never need
to know a column was ever discrete.

- `data/datasets.py` (T7b) — `load_asia()` (8 binary variables, the small
  sanity-check network), `load_insurance()` (27 categorical variables,
  max indegree 3, the larger benchmark), `make_discretized_sachs()`
  (quantile-binned real continuous data as a stress test), and
  `make_mixed_synthetic_scm()` (a small DAG that genuinely mixes
  continuous and discrete nodes, including a continuous-parent ->
  discrete-child edge and a 2-parent edge with one continuous and one
  discrete parent - neither Asia nor Insurance exercises that shape).
  Asia/Insurance are sampled from their known CPTs, bundled with `pgmpy` -
  no network access needed - and all three DAG-based loaders also return
  each variable's true category order (`category_orders`), since several
  Insurance variables are genuinely ordinal (e.g. `SocioEcon`:
  Prole < Middle < UpperMiddle < Wealthy) and alphabetical order would
  silently scramble that, corrupting concordance for any copula fit
  involving them.
- `data/preprocessing.py` (T7c) — `CategoricalMarginal` handles the tie
  problem documented in the task plan: instead of a shared rank for every
  row in a category, each observation gets an independent draw uniform on
  that category's slice of (0, 1) (the empirical-CDF slice), so ties
  disappear and the transform is invertible per observation.
  `inverse_transform` maps U back to a category via that same slice (the
  discrete quantile map). `to_pseudo_observations_mixed` auto-detects
  discrete (non-numeric) columns and continuizes only those (continuous
  columns still go through the original `EmpiricalMarginal`), and accepts
  `category_orders` to fix the order for ordinal columns.

  **Known limitation, found while auditing this pipeline:** jittering
  necessarily dilutes measured dependence relative to Kendall's tau-b
  (which excludes tied pairs from its denominator), and the dilution is
  severe for skewed/rare binary variables. For two variables with tie
  probabilities `t_x, t_y` (chance two random draws share a category), the
  tau on the jittered data comes out close to
  `tau_b(raw) * sqrt((1 - t_x) * (1 - t_y))` — verified empirically against
  several Asia edges (`tests/test_preprocessing.py`). A copula fit on
  jittered data faithfully reproduces that *diluted* dependence, which is
  why a naive baseline sometimes lands closer to the true value than the
  "learned" model on individual edges (see `evaluate_discrete_generation.py`
  below) - the near-deterministic case (Asia's `either` = tub OR lung) is
  an extreme instance of the same mechanism, not a separate issue. This is
  a genuine limitation of the simple jittering approach for skewed/binary
  discrete data, not a bug: the jittered tau equals Kendall's tau-a of the
  raw data in expectation (tied pairs contribute zero concordance).
  **Fix, now implemented:** `discrete_mode="native"` (CLI
  `--discrete-mode native`) fits pairwise copulas and conditional vines with
  pyvinecopulib's native discrete likelihood on F(x) and F(x-) instead of
  jittered pseudo-observations; on held-out data it cuts the Cramer's V
  error of reproduced edges by roughly an order of magnitude
  (`scripts/run_experiments.py discrete-native`, `rq4`).
- `evaluation/discrete.py` (T7d) — `compare_category_frequencies` /
  `joint_contingency_distance` (sanity checks), `cramers_v` (bias-corrected)
  and `normalized_mutual_information` (dependence measures for categorical
  data), and `measure_generation_stability` (wall-clock time + how many
  T4d/T5c.iv fallback events fired - the pipeline uses immediate fallback
  rather than retries).

```bash
python scripts/build_discrete_library.py      # ~10 min: fits Asia + Insurance + discretized Sachs
python scripts/evaluate_discrete_generation.py
python scripts/evaluate_mixed_generation.py   # genuinely mixed continuous+discrete DAG, no build step needed
```

`evaluate_discrete_generation.py` reconstructs the full Asia and Insurance
networks from scratch with the unmodified `GraphSampler`, comparing a
baseline (real marginals, baseline Gaussian dependence) against the
learned-model run, and reports category frequencies matching closely for
both. Edge dependence is where the jittering-dilution limitation above
shows up: the learned model is not uniformly better than baseline on a
per-edge Cramer's V/MI basis, precisely because it faithfully reproduces
the diluted dependence rather than the raw one.

`evaluate_mixed_generation.py` runs the same kind of check on
`make_mixed_synthetic_scm`'s genuinely mixed DAG: continuous-continuous
edges match almost exactly (consistent with T4-T6's continuous results),
while edges into the discrete/binary node show the same attenuation
pattern as Asia/Insurance.

## Closing the loop: is the generated data actually usable for causal discovery?

Every check above (T6a, T7d) validates *statistical realism* - marginals,
pairwise dependence, distribution distance. None of them test the
project's actual stated goal: "many ML methods for graph discovery need
lots of training data." `gcda/evaluation/causal_discovery.py`
closes that gap by running the PC algorithm (`causal-learn`) on our
generated data and checking whether it recovers the true DAG about as
well as it does from real data, via Structural Hamming Distance (SHD) -
the number of edge insertions/deletions/reversals to turn one graph into
the other (0 = identical CPDAG).

```bash
python scripts/evaluate_causal_discovery.py
```

Averaged over several data-generation seeds (a single seed can look
artificially good or bad purely from sampling noise - an earlier one-seed
run made the discrete "learned" case look like it beat real data outright,
which didn't hold up once averaged):

| source | continuous (synthetic SCM) mean SHD | discrete (Asia) mean SHD |
|---|---|---|
| true data | 1.25 | 6.50 |
| baseline (Gaussian everywhere) | 1.00 | 8.25 |
| learned (T4 models) | 1.00 | 6.75 |

These are the original four-seed numbers. The held-out, multi-seed
re-evaluation with stronger baselines (fitted Gaussian copula, CPT refitting,
native discrete fitting), confidence intervals and paired tests is
`python scripts/run_experiments.py rq6` (results in
`outputs/experiments/rq6_*`); the 100-seed PC and GES runs from the
Lichtenberg cluster that the thesis reports are in `outputs/experiments/hpc/`
(Sec. 6.6).

For the continuous DAG, all three are essentially tied at the theoretical
floor (the one edge PC can never orient from observational data alone
regardless of data source). For Asia, the learned model's data supports
causal discovery almost as well as real data (6.75 vs. 6.50), while the
naive baseline is measurably worse (8.25) - it generates spurious extra
edges because a single fixed correlation strength on every edge doesn't
respect the graph's true conditional-independence structure. This is the
result that actually validates the objective: reusing learned dependencies
as building blocks produces data a real structure-learning algorithm can
use about as well as the original data, and does so *because* it learned
the dependencies rather than assuming a fixed generic one.

## Random-forest conditionals (thesis Sec. 3.9 and 6.6.1)

Copula conditionals can only represent dependence that is monotone along each
variable's order, and they approximate parent interactions. On Insurance and Alarm
that is why the copula generator falls short of real data for discovery
(`python scripts/nonmonotone_edges.py` counts the non-monotone edges).
`gcda/dependency/forest.py` (`ForestConditional`) replaces a node's conditional by a
random forest in the same U-space: a classifier for discrete children, leaf sampling
from a regression forest for continuous ones. It plugs into `GraphSampler` as an
`EdgeModel(conditional_sampler=...)`.

```bash
python scripts/run_experiments.py rf --graphs asia insurance alarm --seeds 10
```

The 100-seed cluster runs (`slurm/rf_heldout.slurm`) are in
`outputs/experiments/hpc/rf_{pc,ges}/merged/`; `scripts/check_rf_consistency.py`
verifies that their shared sources equal the RQ6 runs and `scripts/rf_gap_table.py`
prints the gap-closed table. A forest is fitted per node, parent set and dataset, so
unlike the copula library it is not a reusable building block for new graphs.

## T8: writing + final deliverables

- **T8a**, lab notebook: `LAB_NOTEBOOK.md` - a chronological record of
  every decision, what was verified before being trusted, results, and
  every bug found (with root cause and fix).
- **T8b.i**, clean repo + install + configs: this README, `pyproject.toml`
  / `environment.yml` / `requirements.txt`, and `configs/sweep.yaml` (what
  `scripts/sweep_hyperparameters.py` sweeps, versioned rather than
  hardcoded).
- **T8b.ii**, library artifacts + generator CLI: the `gcda` package
  (dependency-library JSON artifacts under `outputs/`, versioned so the
  thesis numbers can be checked against them) plus the `gcda` CLI (`build-library` / `generate` /
  `evaluate` / `sweep`, see the CLI section above) and the narrated
  `scripts/*.py` equivalents.
- **T8b.iii**, W&B: `smoke_test.py` and `scripts/sweep_hyperparameters.py`
  log to the `graph-conditioned-augmentation` W&B project (offline mode by
  default in this environment - no credentials required; set
  `WANDB_MODE=online` and log in to sync a real project). Every sweep run
  logs its full config (`configs/sweep.yaml`'s contents) alongside the
  metrics, so a run is reproducible from the logged config, not just the
  numbers.
- **T8b.iv**, thesis + demo: the thesis source in `thesis/`
  (`thesis/build.sh` builds the PDF) and `scripts/demo.py` (a live, ~1-minute run through the whole
  pipeline: fit a library, generate data two ways, extend to discrete
  data, compose building blocks from two different datasets into a graph
  that never existed in either, then close the loop with a real causal
  discovery check).
