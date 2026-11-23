# CODE_CHANGES

All code and configuration changes relative to the audited implementation (`origin/full-implementation` @ `3c4aa11`).
The complete diff is in `thesis_audit/code_changes.patch` (apply with `git apply`) and reproduced below.

## Changes by audit issue

| Audit ID | Change | Files | Rationale | Impact on existing results | Tests |
|---|---|---|---|---|---|
| I1 | Conditional models are looked up by parent **set**. The sampler feeds parent columns in the model's own order (`EdgeModel.parent_order`, `_resolve_parent_order`). The CLI keeps a node's real marginal when only its edge model is missing. | `dependency/library.py`, `generation/graph_sampler.py`, `generation/spec.py`, `cli.py` | The same DAG with its edges listed in another order silently lost its learned model and marginal: x4 std 0.94 → 1.00, τ 0.445 → 0.315. | None. Thesis runs always used the stored parent order. | `test_conditional_lookup_ignores_parent_order`, `test_same_dag_with_reordered_edges_gives_identical_samples`, `test_cli_generate_is_invariant_to_edge_order` |
| I2 | `DependencyLibrary.merge` (namespace collisions rejected) and `load_many`. `bind_pairwise_copula` re-uses any learned pair copula on any edge, preserving orientation. Graph-spec layer (`generation/spec.py`) supports node → (dataset, variable) mapping, per-edge `copula` binding, strict mode and a decision report. The CLI `generate` accepts repeated `--library`, `--strict`, `--calibrate-margins` and `--no-compose`. `demo.py` step 5 now runs the thesis' praf→pmek, praf→dysp graph with a learned, bound cross-dataset edge. | `dependency/library.py`, `generation/graph_sampler.py`, `generation/spec.py`, `cli.py`, `scripts/demo.py` | The cross-dataset composition claimed in the thesis did not exist: the demo's cross edge used the ρ = 0.5 baseline, and the CLI was single-dataset. | New capability; no change to existing numbers. | `test_merge_rejects_namespace_collisions_and_combines_libraries`, `test_bind_pairwise_copula_transplants_dependence_and_orientation`, `test_cli_generate_composes_two_libraries_with_cross_dataset_binding`, `test_strict_mode_rejects_baseline_fallbacks` |
| I2/I3 | `PairwiseProductConditional`: multi-parent conditional density ∝ ∏ c(u_C, u_Pj) over the incoming edges' copulas, sampled by grid inversion. Used when no vine was fitted for a parent set (`compose=True`). | `dependency/composed.py`, `generation/graph_sampler.py` | Makes learned pairwise building blocks usable for parent sets that never co-occurred. | New capability. | `test_pairwise_product_conditional_matches_gaussian_theory_for_star_model`, `test_compose_flag_builds_multi_parent_model_from_pairwise_blocks` |
| I3 | Per-node KS distance of the generated U-values from U(0,1). `MarginalDriftWarning` when it exceeds both 0.05 and 1.95/√n. Optional `calibrate_margins` (rank-normalize each non-root node). | `generation/graph_sampler.py` | A vine reused under a different parent distribution distorts the child's marginal without any warning. This was the real cause of the Insurance baseline's TVD. | Off by default, so existing numbers are unchanged. | `test_calibrate_margins_reproduces_marginal_and_drift_is_flagged` |
| I4 | `valid_baseline_rho(k) = min(ρ, √(0.9/k))` for the multi-parent baseline. | `generation/graph_sampler.py` | ρ = 0.5 with 4 independent parents gives a singular correlation matrix; with 5 or more it is not PSD. | Unchanged for k ≤ 3; Table 6.2 caps 2 and 3 reproduce exactly. | `test_valid_baseline_rho_unchanged_up_to_three_parents_and_valid_beyond`, `test_baseline_sampler_at_high_indegree_hits_theoretical_tau[4,5]` |
| I5 | All new experiments fit the library on seed 10 000 and evaluate on seeds 0..n−1. | `experiments/*.py` | The original RQ2 and RQ6 (seed 1) reused training data. | New results are reported next to the originals. | covered by experiment outputs |
| I7 | `FallbackWarning` class. `GraphSampler.fallback_counts_`, `diagnostics_` and `total_fallback_draws`. `measure_generation_stability` counts only fallback warnings and reports fallback draws and drift nodes. | `dependency/conditional.py`, `generation/graph_sampler.py`, `evaluation/discrete.py` | The thesis claimed a fallback counter that did not exist, and the metric counted every UserWarning. | Reported fallback counts were 0 before and remain 0. | `test_fallback_counter_counts_each_failed_draw_once`, `test_measure_generation_stability_ignores_unrelated_warnings` |
| I8 | Lower-bound pins plus `pgmpy<1.3` in `pyproject.toml`. `requirements-lock.txt` (the exact environment that reproduced the tables). `gcda/compat.bicop_sample` (pyvinecopulib `sample`/`simulate`). pgmpy loader falls back to `example_models.load_model`. `provenance.py` writes a `.meta.json` with versions, git SHA and argv next to every output; libraries also store metadata and a schema version. | `pyproject.toml`, `requirements*.txt`, `environment.yml`, `gcda/compat.py`, `gcda/provenance.py`, `data/datasets.py`, scripts | Unpinned dependencies, deprecated APIs and no provenance. | None (verified bit-identical sweep). | `test_run_metadata_records_versions_and_extra_fields`, `test_v1_libraries_without_schema_version_still_load` |
| I9 | `full-implementation` merged into the working branch, so it reaches `main` when the PR is merged. | git | The default branch had no implementation. | — | — |
| I10 | `wandb/` (personal e-mail, hostname, paths) removed from the tree and ignored. | `.gitignore` | PII in the repository. | History still contains it; removing it needs a history rewrite on `main` by the owner. | — |
| I11 | `outputs/` documented as versioned. Thesis-v1 sweep tables kept in `outputs/thesis_v1/`. `scripts/check_reproduction.py` compares a fresh sweep with the committed table. | `.gitignore`, `outputs/` | The README and thesis said "gitignored" while the files were committed. | — | used in CI |
| I12 | `[tool.pytest.ini_options] testpaths=["tests"]`. Smoke test is offline by default. CI workflow (Python 3.11/3.13: tests plus sweep reproduction check). | `pyproject.toml`, `smoke_test.py`, `.github/workflows/tests.yml` | Bare `pytest` failed on `smoke_test.py`. | — | CI |
| I13 | `top_k_partners` moved to `dependency/pairwise.py`. Single dataset registry (`data/registry.py`) with explicit n/seed. | `dependency/pairwise.py`, `data/registry.py`, scripts | Duplicated logic and silently different sample sizes. | Sizes kept as before (sweep n = 8000 for Asia/Insurance). | `test_parallel_pairwise_fitting_matches_sequential`, `test_registry_loads_every_dataset_name` |
| I14 | Sachs CSV moved to package data (`gcda/data/resources/`, `GCDA_DATA_DIR` override). Sweep moved into `gcda/experiments/sweep.py` (no `sys.path` hack). `clip_eps` is a parameter of `ConditionalSampler`/`GraphSampler`. | `data/datasets.py`, `experiments/sweep.py`, `cli.py`, `dependency/conditional.py` | Hard-coded paths broke non-editable installs; ε could not be swept (task plan T6c). | None. | `test_sachs_observational_subset_and_condition_boundaries` |
| I15 | Unbiased (U-statistic) energy distance and MMD (`unbiased=True`), plus `permutation_test`. Defaults unchanged. | `evaluation/realism.py` | Biased estimators without a test made small differences uninterpretable. | Defaults reproduce the thesis values. | `test_unbiased_distances_and_permutation_tests` |
| I16 | Every evaluation script writes CSV/JSON results with provenance to `outputs/`. Discretized Sachs and energy/MMD are now reported (RQ2, sweep). | `scripts/evaluate_*.py` | The appendix claimed this already. | — | — |
| I17 | `load_sachs(observational_only=True)` (first 853 rows = CD3/CD28 condition), `sachs_consensus_dag()`, Alarm loader. | `data/datasets.py` | Pooled interventional data were treated as observational. | — | `test_sachs_observational_subset_and_condition_boundaries`, `test_sachs_consensus_dag_has_mek_with_three_parents` |
| I18 | `build_pairwise_library(n_jobs=…, pairs=…)` (thread pool, identical results). Optional marginal compression (`max_points`). CLI `--n-jobs`, `--max-marginal-points`. | `dependency/pairwise.py`, `dependency/library.py`, `cli.py` | O(p²) fitting and large libraries. | None by default. | `test_parallel_pairwise_fitting_matches_sequential`, `test_marginal_compression_keeps_quantiles` |
| I19 | Library schema validation on load; copula family allow-list. | `dependency/library.py`, `generation/graph_sampler.py` | Untrusted JSON was used without checks. | — | `test_library_load_validates_structure_and_family_names` |
| I20 | `--strict` mode and a JSON decision/diagnostics report for every generation. | `cli.py`, `generation/spec.py` | Silent degradation. | — | `test_strict_mode_rejects_baseline_fallbacks` |
| R6/R10 | **Native discrete fitting** (`discrete_mode="native"`): pairwise copulas and conditional vines are fitted with pyvinecopulib's discrete likelihood on F(x), F(x−), and the latent continuous copula is used for sampling. CLI `--discrete-mode`. | `data/preprocessing.discrete_cdf_pairs`, `dependency/pairwise.py`, `dependency/conditional.py`, `cli.py` | Removes most of the jitter dilution (Cramér's V error 0.264 → 0.141 on Asia, 0.240 → 0.007 on the mixed SCM). | Off by default. | experiment outputs |
| R5/R10 | Experiment package: held-out RQ1, RQ2, RQ4, RQ5 (cross-dataset plus novel DAGs), RQ6 (PC or GES), native-vs-jitter ablation, learned indegree. Seed/DAG offsets for Slurm arrays. `merge_results.py`, `verify_sachs_subset.py`. | `gcda/experiments/*`, `scripts/run_experiments.py`, `scripts/merge_results.py`, `scripts/verify_sachs_subset.py`, `evaluation/causal_discovery.run_ges` | Weak evidence for the thesis claims. | — | smoke-tested; outputs committed |
| Thesis claims | Tests that make documented claims true: permuted-column round trip; h-function direction by binning. | `tests/test_preprocessing.py`, `tests/test_graph_sampler.py` | The thesis described checks that did not exist. | — | `test_pseudo_observations_of_a_permuted_column_invert_to_the_same_permutation`, `test_hinv1_direction_matches_empirical_conditional_quantiles_of_clayton` |
| Sweep | Indegree caps 2–6 × 10 repeats with the theoretical τ; clip-ε sweep. Seed-0 rows reproduce the old values. | `experiments/sweep.py`, `configs/sweep.yaml` | I4 and task plan T6c. | Table 6.2 replaced. | — |
| Demo | `GraphSampler.u_values_` exposes the latent copula-scale values of the last run. | `generation/graph_sampler.py` | Needed to verify copula-level transplant fidelity (RQ5). | — | — |

## Regression checks performed

| Check | Result |
|---|---|
| Full test suite | all tests pass (see "Test inventory"; count includes the new tests) |
| Sweep (Table 6.1) after refactor | `check_reproduction.py`: max \|ΔAIC\| = 1.4e-11, `mean_tau_abs_error` diff 0, identical families |
| Indegree sweep seed 0, caps 2–3 | identical to the thesis' Table 6.2 (0.334/0.315/0.352; 0.327/0.315/0.335) |
| Original RQ6 four-seed SHD table | reproduced exactly with the committed libraries (audit run) |
| Mixed-SCM table | reproduced exactly (audit run) |


## Test inventory

Test functions in `tests/`: **80** (54 before remediation).

Changed/added test files:

```
M	tests/test_datasets.py
M	tests/test_graph_sampler.py
M	tests/test_pairwise.py
M	tests/test_preprocessing.py
A	tests/test_provenance.py
A	tests/test_remediation.py
```

## Diffstat

```
.github/workflows/tests.yml              |   28 +
 .gitignore                               |    6 +-
 LAB_NOTEBOOK.md                          |   39 +
 README.md                                |   84 +-
 configs/sweep.yaml                       |   17 +-
 data/raw/README.md                       |   34 +-
 docs/HPC_RUNBOOK.md                      |  134 ++
 docs/presentation.md                     |    2 +
 docs/thesis_outline.md                   |    2 +
 environment.yml                          |    2 +-
 gcda/cli.py                              |  221 ++-
 gcda/compat.py                           |   13 +
 gcda/data/datasets.py                    |   81 +-
 gcda/data/preprocessing.py               |   31 +
 gcda/data/registry.py                    |   44 +
 gcda/data/resources/sachs_continuous.csv | 7467 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 gcda/dependency/composed.py              |   94 +
 gcda/dependency/conditional.py           |   51 +-
 gcda/dependency/library.py               |  124 +-
 gcda/dependency/pairwise.py              |   74 +-
 gcda/evaluation/causal_discovery.py      |   14 +
 gcda/evaluation/discrete.py              |   23 +-
 gcda/evaluation/realism.py               |   79 +-
 gcda/experiments/__init__.py             |    0
 gcda/experiments/common.py               |  126 ++
 gcda/experiments/composition.py          |  252 +++
 gcda/experiments/discrete_native.py      |   87 +
 gcda/experiments/learned_indegree.py     |   76 +
 gcda/experiments/rq1.py                  |   62 +
 gcda/experiments/rq2.py                  |   64 +
 gcda/experiments/rq4.py                  |   85 +
 gcda/experiments/rq6.py                  |  129 ++
 gcda/experiments/sweep.py                |  209 ++
 gcda/generation/graph_sampler.py         |  252 ++-
 gcda/generation/spec.py                  |  173 ++
 gcda/provenance.py                       |   53 +
 pyproject.toml                           |   37 +-
 requirements-lock.txt                    |   80 +
 requirements.txt                         |    2 +-
 scripts/build_dependency_library.py      |   18 +-
 scripts/build_discrete_library.py        |   17 +-
 scripts/check_reproduction.py            |   21 +
 scripts/demo.py                          |   39 +-
 scripts/evaluate_causal_discovery.py     |    6 +
 scripts/evaluate_discrete_generation.py  |   10 +
 scripts/evaluate_mixed_generation.py     |    7 +
 scripts/merge_results.py                 |   32 +
 scripts/run_experiments.py               |   56 +
 scripts/sweep_hyperparameters.py         |  189 +-
 scripts/verify_sachs_subset.py           |   31 +
 slurm/env_lichtenberg.sh                 |   22 +
 slurm/learned_indegree.slurm             |   14 +
 slurm/novel_dags.slurm                   |   18 +
 slurm/rq4_heldout.slurm                  |   17 +
 slurm/rq6_heldout.slurm                  |   21 +
 slurm/setup_env.sh                       |   18 +
 slurm/sweep_and_rebuild.slurm            |   33 +
 smoke_test.py                            |    6 +-
 t3_validation.py                         |    5 +-
 tests/test_datasets.py                   |   37 +
 tests/test_graph_sampler.py              |   19 +
 tests/test_pairwise.py                   |    3 +-
 tests/test_preprocessing.py              |   13 +
 tests/test_provenance.py                 |    8 +
 tests/test_remediation.py                |  281 +++
 65 files changed, 10800 insertions(+), 492 deletions(-)
```

## Full diff

```diff
diff --git a/.github/workflows/tests.yml b/.github/workflows/tests.yml
new file mode 100644
index 0000000..b13242e
--- /dev/null
+++ b/.github/workflows/tests.yml
@@ -0,0 +1,28 @@
+name: tests
+on:
+  push:
+  pull_request:
+jobs:
+  pytest:
+    runs-on: ubuntu-latest
+    strategy:
+      fail-fast: false
+      matrix:
+        python-version: ["3.11", "3.13"]
+    steps:
+      - uses: actions/checkout@v4
+      - uses: actions/setup-python@v5
+        with:
+          python-version: ${{ matrix.python-version }}
+      - name: Install
+        run: |
+          python -m pip install --upgrade pip
+          pip install -e ".[test]"
+      - name: Test
+        env:
+          WANDB_MODE: offline
+        run: pytest -q
+      - name: Reproduce thesis sweep table (regression check)
+        run: |
+          python scripts/sweep_hyperparameters.py --output-dir /tmp/sweep
+          python scripts/check_reproduction.py /tmp/sweep/sweep_dependency_models.csv outputs/sweep_dependency_models.csv
diff --git a/.gitignore b/.gitignore
index 4ade616..606a46e 100644
--- a/.gitignore
+++ b/.gitignore
@@ -1,6 +1,10 @@
 __pycache__/
 *.pyc
 *.egg-info/
-outputs/
 wandb/
 .pytest_cache/
+# outputs/ IS versioned: it holds the exact artifacts the thesis tables were
+# produced from (see outputs/SHA256SUMS). Scratch output goes to outputs/scratch/.
+outputs/scratch/
+outputs/t3_validation/
+thesis/build/
diff --git a/LAB_NOTEBOOK.md b/LAB_NOTEBOOK.md
index 1699c63..08d00fc 100644
--- a/LAB_NOTEBOOK.md
+++ b/LAB_NOTEBOOK.md
@@ -291,3 +291,42 @@ compared the generated `outputs/` against this environment's:
   set beats Gaussian-only on both Asia and Insurance; AIC and BIC select
   different models on discrete data) held in every run regardless of this
   bug - only the exact fitted numbers varied.
+
+## Post-audit remediation
+
+An external-style audit of thesis, LaTeX source and code
+(`thesis_audit/AUDIT_REPORT.md`) was turned into a backlog and worked off
+(`thesis_audit/MASTER_REMEDIATION_REPORT.md`). Decisions worth recording:
+
+- **Parent-order bug.** `get_conditional_sampler` matched the *ordered*
+  parent list, so the same DAG written with its edges in a different order
+  silently lost its fitted vine and (via the CLI fallback) its real
+  marginal. Now matched by parent *set*; the sampler feeds parent columns in
+  the vine's own order. Regression tests at library and CLI level.
+- **Composition was mostly marginals.** The demo's cross-dataset edge used
+  the ρ = 0.5 baseline. Added `DependencyLibrary.merge`, copula binding
+  (`bind_pairwise_copula`, CLI graph spec with per-edge `copula`), and a
+  pairwise-composed multi-parent model (`PairwiseProductConditional`,
+  product of per-edge copula densities, exact under conditional
+  independence of the parents given the child).
+- **Compatibility of transplanted multi-parent models.** A vine fitted under
+  one parent distribution does not reproduce the child's marginal under
+  another (this is what drove the Insurance baseline's TVD, concentrated at
+  multi-parent nodes - not "error propagation"). Added a per-node
+  uniformity diagnostic (`MarginalDriftWarning`) and optional rank
+  calibration (`calibrate_margins`).
+- **Baseline validity.** ρ = 0.5 with k = 4 independent parents gives a
+  singular correlation matrix (child deterministic), k ≥ 5 not PSD. Capped at
+  `sqrt(0.9 / k)`; unchanged for k ≤ 3, so the original results stand.
+- **Jitter dilution is the τ_a identity** (known in the discrete-copula
+  literature), and it is fixable: pyvinecopulib's native discrete likelihood
+  (`discrete_mode="native"`) removes most of the per-edge dependence loss.
+- **Sachs data are pooled over nine experimental conditions**; the first
+  853 rows are the CD3/CD28 condition (boundary evidence in
+  `tests/test_datasets.py`; byte-level confirmation listed as a cluster/login
+  task). 91% of `praf` values are ties (rounded measurements); the tie
+  method does not change the praf-pmek fit (Joe, τ = 0.666 under max-rank,
+  mid-rank and random tie-breaking), but the empirical τ_b of the raw data is
+  0.616 - the 0.666 in the thesis is the fitted copula's τ.
+- **Held-out evaluation.** Every new experiment fits on seed 10,000 and
+  evaluates on seeds 0..n-1; the original RQ6 seed 1 reused the training data.
diff --git a/README.md b/README.md
index fd52dd8..3e7e2ad 100644
--- a/README.md
+++ b/README.md
@@ -22,10 +22,16 @@ pip install -e .   # installs the gcda package + the `gcda` CLI
 pip install -e ".[test]"   # pyproject.toml's own dependency list + pytest
 ```
 
-No dependency in this repo is pinned to an exact version (only the
-package names are listed) - pip resolves whatever's compatible with your
-Python and platform, which is more robust across machines than a `pip
-freeze` snapshot from one specific environment.
+`pyproject.toml` gives lower bounds (and `pgmpy<1.3`, because pgmpy 1.3
+removes the bundled-network loader). `requirements-lock.txt` pins the exact
+environment in which every thesis table was reproduced bit-for-bit:
+
+```bash
+pip install -r requirements-lock.txt && pip install -e . --no-deps
+```
+
+Every output file gets a `<name>.meta.json` next to it with package
+versions, git commit and arguments (`gcda/provenance.py`).
 
 ## Repository structure
 
@@ -39,9 +45,14 @@ gcda/                   the installable package
 scripts/                narrated, single-purpose entry points (see each T-section below);
                         the CLI is the composable interface, these are the detailed reports/demos
 configs/                sweep.yaml - what scripts/sweep_hyperparameters.py sweeps
-data/raw/               bundled real datasets (Sachs) + provenance notes
-tests/                  pytest suite (mirrors the package layout)
-outputs/                generated artifacts (gitignored): libraries, sweep CSVs, plots
+  experiments/           sweep + held-out multi-seed experiments (RQ1-RQ6, ablations)
+  provenance.py          run metadata attached to every output
+data/raw/               provenance notes for the bundled Sachs data (the CSV is package data in gcda/data/resources/)
+tests/                  pytest suite (mirrors the package layout; `pytest` runs it)
+outputs/                versioned result artifacts the thesis tables come from (+ .meta.json provenance)
+slurm/, docs/HPC_RUNBOOK.md  Lichtenberg job scripts for the large-seed runs
+thesis/                 thesis LaTeX source + bibliography (`thesis/build.sh` builds the PDF)
+thesis_audit/           audit report, remediation reports, thesis edit records
 LAB_NOTEBOOK.md         T8a - chronological decisions, bugs found/fixed, and results
 docs/                   T8b.iv - thesis outline, demo script notes, presentation outline
 ```
@@ -51,20 +62,34 @@ docs/                   T8b.iv - thesis outline, demo script notes, presentation
 Installed as the `gcda` command (see `gcda/cli.py`):
 
 ```bash
-gcda build-library --dataset synthetic_scm --output outputs/lib.json
-gcda generate --dag my_graph.json --library outputs/lib.json --dataset synthetic_scm --n 5000 --output data.csv
-gcda evaluate --true-csv true.csv --sim-csv data.csv
+gcda build-library --dataset sachs --output lib_sachs.json
+gcda build-library --dataset asia --discrete-mode native --output lib_asia.json
+gcda generate --dag graph.json --library lib_sachs.json --library lib_asia.json --n 5000 --output data.csv
+gcda evaluate --true-csv true.csv --sim-csv data.csv --distances
 gcda sweep [--wandb]
 ```
 
-`my_graph.json` is any DAG you want, not necessarily the dataset's own
-structure: `{"edges": [["a", "b"], ["a", "c"]]}`. Nodes with no matching
-entry in the library fall back to baseline Gaussian dependence with a
-warning, rather than failing the whole run - this is the literal "reuse
-learned dependencies as building blocks for any user-specified graph"
-capability the project is about; see `LAB_NOTEBOOK.md` for how that was
-verified (composing building blocks from two different datasets into one
-novel graph that never existed in either original dataset).
+`graph.json` is any DAG, not necessarily a dataset's own structure. Simplest
+form: `{"edges": [["a", "b"], ["a", "c"]]}` (nodes looked up in `--dataset`).
+Full form (several libraries are merged; namespaces must not collide):
+
+```json
+{"nodes": {"praf": {"dataset": "sachs"}, "pmek": {"dataset": "sachs"}, "dysp": {"dataset": "asia"}},
+ "edges": [["praf", "pmek"],
+           {"from": "praf", "to": "dysp", "copula": {"dataset": "asia", "pair": ["bronc", "dysp"]}}]}
+```
+
+- each node's marginal comes from its (dataset, variable);
+- an edge uses an explicit `copula` binding (any learned pair from any
+  dataset; the first variable of `pair` plays the parent role), else the
+  learned pair copula of its endpoints if both come from one dataset;
+- a multi-parent node uses a fitted vine for that parent *set* (edge order
+  does not matter), else a model composed from its edges' pairwise copulas
+  (`gcda/dependency/composed.py`), else the Gaussian baseline;
+- every decision and every baseline fallback is written to
+  `data.csv.report.json`; `--strict` turns fallbacks into errors;
+  `--calibrate-margins` reproduces every node's marginal exactly (see
+  "compatibility" in `gcda/generation/graph_sampler.py`).
 
 ## Smoke test
 
@@ -266,10 +291,14 @@ to know a column was ever discrete.
   below) - the near-deterministic case (Asia's `either` = tub OR lung) is
   an extreme instance of the same mechanism, not a separate issue. This is
   a genuine limitation of the simple jittering approach for skewed/binary
-  discrete data, not a bug; a more faithful fix would use pyvinecopulib's
-  native discrete support (`var_types="d"`, fitting directly on category
-  probabilities) instead of continuizing first - noted as follow-up work,
-  out of scope here.
+  discrete data, not a bug: the jittered tau equals Kendall's tau-a of the
+  raw data in expectation (tied pairs contribute zero concordance).
+  **Fix, now implemented:** `discrete_mode="native"` (CLI
+  `--discrete-mode native`) fits pairwise copulas and conditional vines with
+  pyvinecopulib's native discrete likelihood on F(x) and F(x-) instead of
+  jittered pseudo-observations; on held-out data it cuts the Cramer's V
+  error of reproduced edges by roughly an order of magnitude
+  (`scripts/run_experiments.py discrete-native`, `rq4`).
 - `evaluation/discrete.py` (T7d) — `compare_category_frequencies` /
   `joint_contingency_distance` (sanity checks), `cramers_v` (bias-corrected)
   and `normalized_mutual_information` (dependence measures for categorical
@@ -325,6 +354,13 @@ which didn't hold up once averaged):
 | baseline (Gaussian everywhere) | 1.00 | 8.25 |
 | learned (T4 models) | 1.00 | 6.75 |
 
+These are the original four-seed numbers. The held-out, multi-seed
+re-evaluation with stronger baselines (fitted Gaussian copula, CPT refitting,
+native discrete fitting), confidence intervals and paired tests is
+`python scripts/run_experiments.py rq6` (results in
+`outputs/experiments/rq6_*`, discussed in thesis Sec. 6.6); the
+100-seed version runs on the cluster (`slurm/rq6_heldout.slurm`).
+
 For the continuous DAG, all three are essentially tied at the theoretical
 floor (the one edge PC can never orient from observational data alone
 regardless of data source). For Asia, the learned model's data supports
@@ -347,8 +383,8 @@ the dependencies rather than assuming a fixed generic one.
   `scripts/sweep_hyperparameters.py` sweeps, versioned rather than
   hardcoded).
 - **T8b.ii**, library artifacts + generator CLI: the `gcda` package
-  (dependency-library JSON artifacts under `outputs/`, gitignored since
-  they're generated) plus the `gcda` CLI (`build-library` / `generate` /
+  (dependency-library JSON artifacts under `outputs/`, versioned so the
+  thesis numbers can be checked against them) plus the `gcda` CLI (`build-library` / `generate` /
   `evaluate` / `sweep`, see the CLI section above) and the narrated
   `scripts/*.py` equivalents.
 - **T8b.iii**, W&B: `smoke_test.py` and `scripts/sweep_hyperparameters.py`
diff --git a/configs/sweep.yaml b/configs/sweep.yaml
index 78a4d7c..252cadb 100644
--- a/configs/sweep.yaml
+++ b/configs/sweep.yaml
@@ -10,9 +10,8 @@ family_sets:
 
 selection_criteria: [aic, bic]
 
-# One 2-parent (or 3-parent, for insurance) conditional-model target per
-# dataset: child | parents, all must already exist as columns in that
-# dataset's loader.
+# One 2-parent conditional-model target per dataset: child | parents, all
+# must already exist as columns in that dataset's loader.
 targets:
   sachs:
     child: pmek
@@ -30,8 +29,18 @@ targets:
     child: DrivQuality
     parents: [RiskAversion, DrivingSkill]
 
+# Baseline Gaussian sampler at increasing indegree. The per-parent
+# correlation is capped at sqrt(0.9 / k) so the baseline is a valid model at
+# every cap (rho = 0.5 with k = 4 independent parents is singular).
 indegree_sweep:
-  caps: [2, 3, 4]
+  caps: [2, 3, 4, 5, 6]
   baseline_rho: 0.5
   n: 5000
   seed: 0
+  repeats: 10
+
+# Stability guard (T6c "clipping/fallback settings"): epsilon used to keep
+# U-values inside [eps, 1 - eps] in the conditional sampler.
+clip_sweep:
+  datasets: [sachs, asia]
+  eps_values: [1.0e-10, 1.0e-6, 1.0e-3, 1.0e-2]
diff --git a/data/raw/README.md b/data/raw/README.md
index 5866cba..2a77972 100644
--- a/data/raw/README.md
+++ b/data/raw/README.md
@@ -1,21 +1,31 @@
 # Raw datasets
 
-`sachs_continuous.csv` — the Sachs et al. (2005) protein-signaling flow
-cytometry dataset (11 continuous variables, 7466 single-cell measurements),
-one of the standard continuous benchmarks used in the causal discovery
-literature. Mirrored from the `CausalDiscoveryToolbox` package:
+`gcda/data/resources/sachs_continuous.csv` (moved there so it is installed as
+package data) is the Sachs et al. (2005) protein-signaling flow cytometry
+dataset: 11 continuous variables, 7,466 single-cell measurements, mirrored from
+the `CausalDiscoveryToolbox` package:
 https://raw.githubusercontent.com/FenTechSolutions/CausalDiscoveryToolbox/master/cdt/data/resources/cyto_full_data.csv
 
-Bundled directly in the repo (rather than downloaded on demand) so
-experiments are reproducible on machines without internet access (e.g. the
-Lichtenberg HPC cluster).
+**The 7,466 rows pool all nine experimental conditions of the original study**
+(sizes 853, 902, 911, 723, 810, 799, 848, 913, 707), i.e. one general
+stimulation (CD3/CD28) plus eight interventions. They are therefore not i.i.d.
+observational data. `load_sachs(observational_only=True)` returns the first
+853 rows, the CD3/CD28 condition. Evidence that the file is the concatenation
+of the conditions in this order (checked in `tests/test_datasets.py`): every
+one of the eight boundaries shows a much larger distribution shift than
+offsets inside the blocks, and the blocks carry the expected intervention
+signatures (e.g. under the MEK inhibitor U0126 the median of `p44/42` (Erk)
+drops from about 15 to 2.7; under the PIP2 inhibitor psitectorigenin the
+median of `PIP2` drops to 2.1). A direct row-by-row comparison with the
+original observational file was not possible offline; see
+`docs/HPC_RUNBOOK.md` (task "sachs-verify") for the one-line check.
 
 Citation: Sachs, K., Perez, O., Pe'er, D., Lauffenburger, D. A., & Nolan,
 G. P. (2005). Causal protein-signaling networks derived from multiparameter
 single-cell data. Science, 308(5721), 523-529.
 
-The other two Phase 1 datasets are not stored as files:
-- the UCI-style robustness dataset uses `sklearn.datasets.load_diabetes`
-  (bundled with scikit-learn, no download needed),
-- the synthetic SCM dataset is generated on the fly with a known ground
-  truth (see `gcda/data/datasets.py::make_synthetic_scm`).
+The other datasets are not stored as files:
+- UCI-style robustness dataset: `sklearn.datasets.load_diabetes` (the
+  Efron et al., 2004 diabetes data);
+- synthetic SCMs are generated on the fly (`gcda/data/datasets.py`);
+- Asia, Insurance and Alarm are sampled from the CPTs bundled with pgmpy.
diff --git a/docs/HPC_RUNBOOK.md b/docs/HPC_RUNBOOK.md
new file mode 100644
index 0000000..d4b574a
--- /dev/null
+++ b/docs/HPC_RUNBOOK.md
@@ -0,0 +1,134 @@
+# HPC runbook: Lichtenberg (TU Darmstadt)
+
+This runbook covers the experiments that are too expensive to run at full
+statistical power on a 4-core machine. Each one also ran locally at reduced
+size: those results are what the thesis currently reports (marked "local" in
+`thesis_audit/MASTER_REMEDIATION_REPORT.md`). The cluster runs replace them
+with more seeds or graphs, and they add the from-scratch reproduction.
+
+All scripts are in `slurm/`. They share `slurm/env_lichtenberg.sh`.
+
+## 0. One-time setup (login node)
+
+```bash
+git clone https://github.com/ramya-ravi26/copula-simulator.git ~/copula-simulator
+```
+```bash
+cd ~/copula-simulator && git checkout <thesis commit or branch>
+```
+```bash
+module avail python
+```
+Pick a Python ≥ 3.10 module, then edit the two `module load` lines in
+`slurm/env_lichtenberg.sh` and `slurm/setup_env.sh`.
+
+```bash
+bash slurm/setup_env.sh
+```
+This creates `~/venvs/gcda`, installs `requirements-lock.txt` and runs the test suite (expected: all tests pass).
+
+```bash
+mkdir -p logs
+```
+Slurm needs this directory to exist for `--output`/`--error`.
+
+**Before the first submission:**
+- Replace `project_XXXXX` in every `slurm/*.slurm` with your project account.
+- Optionally set `GCDA_OUT=/work/scratch/$USER/gcda` so large outputs land on scratch.
+
+```bash
+sed -i 's/project_XXXXX/project01234/' slurm/*.slurm
+```
+
+**Lichtenberg specifics:**
+- Partitions are chosen automatically from the requested time and resources.
+- `-t` must not exceed the project's limit.
+- Memory is requested per CPU (`--mem-per-cpu`, in MB).
+- Compute nodes have no internet access. Run every download step (pip, reference datasets) on the login node.
+
+## 1. Experiment table
+
+| Job | Objective / why needed | Resources (per array task) | Expected outputs | Validation | Thesis sections to update |
+|---|---|---|---|---|---|
+| `rq6_heldout.slurm` (PC) | Held-out downstream usefulness with **100 seeds** on SCM, Asia, Insurance, Alarm. Local runs: SCM/Asia 30 seeds, Insurance/Alarm 10 seeds; the Insurance/Alarm confidence intervals are wide. | 10 tasks × (4 CPU, 8 GB, ≤ 6 h); ~40 core-h total | `rq6_pc/task_*/rq6_heldout_*.csv` → merged `rq6_pc/merged/` | merged per-seed file has 100 seeds × graphs × sources and no duplicates (enforced by `merge_results.py`); `true_data` SHD on Asia ≈ 6–7 as locally | Sec. 6.6 (Table 6.6, Fig. 6.10), Abstract, Sec. 8.1 |
+| `rq6_heldout.slurm` with `ALGO=ges` | Second discovery algorithm (score-based GES; BIC / BDeu). The audit's "single algorithm" limitation. | as above; GES on Alarm is slower, budget ≤ 12 h (raise `-t`) | `rq6_ges/merged/` | same checks; GES SHD on SCM true data ≈ 1 (smoke-tested locally) | Sec. 6.6 (new paragraph), Sec. 7.4 limitation removed |
+| `rq4_heldout.slurm` | Discrete/mixed reconstruction (jitter vs native vs CPT refit) with **50 seeds** (10 locally). | 5 tasks × (4 CPU, 8 GB, ≤ 4 h) | `rq4/merged/` | native < jitter Cramér's-V error on all networks, as locally | Sec. 6.4 (Table 6.4), Sec. 7.4 |
+| `novel_dags.slurm` | Composition study on **200** random DAGs over the Sachs variables (20 locally). | 10 tasks × (4 CPU, 8 GB, ≤ 4 h) | `novel_dags/task_*/novel_dags_{pooled,observational}_per_dag.csv` | per-generator means within the local 95% CIs | Sec. 6.5 (Table 6.5) |
+| `learned_indegree.slurm` | Learned vines at indegree 2–4, jitter vs native, 10 held-out seeds (local run: jitter only, then native added). | 1 task (4 CPU, 8 GB, ≤ 3 h) | `learned_indegree/learned_indegree_summary.csv` | 0 fallback draws at every indegree | Sec. 6.3.1 |
+| `sweep_and_rebuild.slurm` | **From-scratch reproduction.** Rebuild both libraries, rerun the sweep and every evaluation script, and compare with the committed outputs. The local audit reused the committed library files instead of rebuilding them. | 1 task (8 CPU, 12 GB, ≤ 2 h) | `repro_<jobid>/` and a `git diff --stat outputs/` | `check_reproduction.py` exits 0; `git diff outputs/` shows only metadata/timestamp changes | Sec. 7.3 (reproducibility statement), App. A.5 |
+| sachs-verify (login node, seconds) | Confirm that the first 853 rows of the bundled Sachs file are the CD3/CD28 observational condition. Locally this rests on distribution-shift evidence only. | login node | console output | `verify_sachs_subset.py` exits 0 | Sec. 5.1, `data/raw/README.md` |
+
+## 2. Commands
+
+### rq6 (PC, then GES)
+
+```bash
+sbatch slurm/rq6_heldout.slurm
+```
+```bash
+ALGO=ges sbatch --time=12:00:00 slurm/rq6_heldout.slurm
+```
+Once all array tasks are finished:
+```bash
+source slurm/env_lichtenberg.sh && python scripts/merge_results.py rq6 $GCDA_OUT/rq6_pc/task_* --out $GCDA_OUT/rq6_pc/merged
+```
+```bash
+source slurm/env_lichtenberg.sh && python scripts/merge_results.py rq6 $GCDA_OUT/rq6_ges/task_* --out $GCDA_OUT/rq6_ges/merged
+```
+
+### rq4
+
+```bash
+sbatch slurm/rq4_heldout.slurm
+```
+```bash
+source slurm/env_lichtenberg.sh && python scripts/merge_results.py rq4 $GCDA_OUT/rq4/task_* --out $GCDA_OUT/rq4/merged
+```
+
+### novel-dags
+
+```bash
+sbatch slurm/novel_dags.slurm
+```
+Merge:
+```bash
+source slurm/env_lichtenberg.sh && python - <<'PY'
+import glob, os, pandas as pd
+from gcda.experiments.composition import summarize_novel
+out = os.environ["GCDA_OUT"] + "/novel_dags/merged"; os.makedirs(out, exist_ok=True)
+for tag in ("pooled", "observational"):
+    res = pd.concat(pd.read_csv(f) for f in glob.glob(os.environ["GCDA_OUT"] + f"/novel_dags/task_*/novel_dags_{tag}_per_dag.csv"))
+    summary, tests = summarize_novel(res)
+    res.to_csv(f"{out}/novel_dags_{tag}_per_dag.csv", index=False)
+    summary.to_csv(f"{out}/novel_dags_{tag}_summary.csv", index=False)
+    tests.to_csv(f"{out}/novel_dags_{tag}_tests.csv", index=False)
+    print(tag, res.dag.nunique(), "DAGs"); print(summary.round(3).to_string(index=False))
+PY
+```
+
+### learned-indegree and the from-scratch reproduction
+
+```bash
+sbatch slurm/learned_indegree.slurm
+```
+```bash
+sbatch slurm/sweep_and_rebuild.slurm
+```
+
+### sachs-verify (login node)
+
+```bash
+wget https://www.bnlearn.com/book-crc/code/sachs.data.txt.gz && gunzip sachs.data.txt.gz
+```
+```bash
+python scripts/verify_sachs_subset.py sachs.data.txt
+```
+
+## 3. Bringing results back into the thesis
+
+1. Copy each `merged/` directory into `outputs/experiments/hpc/` in the repository and commit it, including the `.meta.json` provenance files.
+2. In `thesis_audit/thesis_edits_batch2.py`, every number that comes from a local run is marked with a `% LOCAL-RUN` LaTeX comment in the new text.
+3. Replace those numbers with the merged HPC values, and the seed counts in the table captions (`30`/`10` → `100`).
+4. Run `python thesis_audit/apply_thesis_edits.py && thesis/build.sh`.
+
+Expected changes are narrower confidence intervals. The qualitative conclusions should not change. If one does, the corresponding claim must be revised, not kept.
diff --git a/docs/presentation.md b/docs/presentation.md
index 7baed77..b86daf9 100644
--- a/docs/presentation.md
+++ b/docs/presentation.md
@@ -1,3 +1,5 @@
+> **Note (post-audit):** this outline predates the remediation in `thesis_audit/`. The authoritative text is `thesis/thesis.tex`; where numbers or claims differ (e.g. RQ5 composition, RQ6 held-out results, jitter vs native discrete fitting, the vine structure), the thesis source is correct.
+
 ---
 marp: true
 paginate: true
diff --git a/docs/thesis_outline.md b/docs/thesis_outline.md
index 8e5dc57..81eec4e 100644
--- a/docs/thesis_outline.md
+++ b/docs/thesis_outline.md
@@ -1,3 +1,5 @@
+> **Note (post-audit):** this outline predates the remediation in `thesis_audit/`. The authoritative text is `thesis/thesis.tex`; where numbers or claims differ (e.g. RQ5 composition, RQ6 held-out results, jitter vs native discrete fitting, the vine structure), the thesis source is correct.
+
 # Thesis outline — Graph-Conditioned Causal Data Augmentation
 
 A chapter-by-chapter skeleton with the project's actual results already
diff --git a/environment.yml b/environment.yml
index ec134f9..ecfd7e7 100644
--- a/environment.yml
+++ b/environment.yml
@@ -14,6 +14,6 @@ dependencies:
       - pyvinecopulib
       - pytest
       - wandb
-      - pgmpy
+      - pgmpy<1.3
       - causal-learn
       - pyyaml
diff --git a/gcda/cli.py b/gcda/cli.py
index 1985cf6..960f906 100644
--- a/gcda/cli.py
+++ b/gcda/cli.py
@@ -1,15 +1,17 @@
 """GCDA command-line interface (T8b.ii).
 
-Wraps the package's core operations - build a dependency library from a
-dataset, generate data for an arbitrary user-specified graph, evaluate a
-generated dataset against the truth, and run the hyperparameter sweep -
-behind a single `gcda` command, installed via `pip install -e .`.
-
-The `scripts/*.py` files remain the detailed, narrated versions of these
-same operations (with printed diagnostics, plots, multi-dataset demos);
-this CLI is the composable, scriptable entry point for actually using the
-package as a tool: pick a dataset, build a library, generate data for a
-graph you specify, done.
+    gcda build-library --dataset sachs --output lib_sachs.json [--dag graph.json]
+    gcda generate --dag graph.json --library lib_sachs.json [--library lib_asia.json ...]
+                  [--dataset sachs] --n 5000 --output data.csv [--calibrate-margins] [--strict]
+    gcda evaluate --true-csv true.csv --sim-csv data.csv [--distances]
+    gcda sweep [--wandb] [--config configs/sweep.yaml]
+
+`generate` accepts several libraries (merged; dataset namespaces must not
+collide) and a graph spec that can map each node to a (dataset, variable) and
+bind any learned pair copula to any edge, so one graph can combine building
+blocks learned on different datasets (see gcda/generation/spec.py). A JSON
+report of every modelling decision, fallback and per-node diagnostic is
+written next to the output CSV.
 """
 
 import argparse
@@ -17,108 +19,99 @@ import json
 import sys
 from pathlib import Path
 
-import networkx as nx
 import pandas as pd
 
-from gcda.data.datasets import (
-    load_asia,
-    load_insurance,
-    load_sachs,
-    load_uci_diabetes,
-    make_discretized_sachs,
-    make_mixed_synthetic_scm,
-    make_synthetic_scm,
+from gcda.data.preprocessing import (
+    discrete_cdf_pairs,
+    handle_missing_values,
+    to_pseudo_observations,
+    to_pseudo_observations_mixed,
 )
-from gcda.data.preprocessing import handle_missing_values, to_pseudo_observations_mixed
+from gcda.data.registry import DATASET_NAMES, load_dataset
 from gcda.dependency.conditional import ConditionalSampler
 from gcda.dependency.library import DependencyLibrary
 from gcda.dependency.pairwise import build_pairwise_library
-from gcda.evaluation.realism import compare_marginals, compare_pairwise_dependence
-from gcda.generation.graph_sampler import GraphSampler, node_spec_from_library
-
-def _load_discretized_sachs():
-    df, category_orders = make_discretized_sachs()
-    return df, None, category_orders
-
-
-def _load_synthetic_scm():
-    df, dag = make_synthetic_scm(n=5000, seed=1)
-    return df, dag, None
-
-
-# name -> loader returning (df, dag_or_None, category_orders_or_None)
-DATASETS = {
-    "sachs": lambda: (load_sachs(), None, None),
-    "uci_diabetes": lambda: (load_uci_diabetes(), None, None),
-    "discretized_sachs": _load_discretized_sachs,
-    "synthetic_scm": _load_synthetic_scm,
-    "mixed_scm": lambda: make_mixed_synthetic_scm(n=5000, seed=1),
-    "asia": lambda: load_asia(n_samples=10000, seed=0),
-    "insurance": lambda: load_insurance(n_samples=10000, seed=0),
-}
-
-
-def _load_dataset(name: str):
-    if name not in DATASETS:
-        raise SystemExit(f"unknown dataset {name!r}; choose from {sorted(DATASETS)}")
-    return DATASETS[name]()
+from gcda.evaluation.realism import (
+    compare_marginals,
+    compare_pairwise_dependence,
+    energy_distance,
+    gaussian_mmd,
+    permutation_test,
+)
+from gcda.generation.graph_sampler import GraphSampler
+from gcda.generation.spec import StrictModeError, build_node_specs, load_graph_spec, parse_graph_spec
+from gcda.provenance import run_metadata
 
 
 def cmd_build_library(args: argparse.Namespace) -> None:
-    df, dag, category_orders = _load_dataset(args.dataset)
+    df, dag, category_orders = load_dataset(args.dataset, n=args.n, seed=args.seed)
     df, _ = handle_missing_values(df, strategy="drop")
     u_df, marginals = to_pseudo_observations_mixed(df, category_orders=category_orders, seed=0)
+    u_minus, var_types = None, None
+    if args.discrete_mode == "native":
+        u_df, u_minus, var_types = discrete_cdf_pairs(df, marginals)
 
     library = DependencyLibrary()
-    library.add_marginals(args.dataset, marginals)
-    pairwise_entries = build_pairwise_library(u_df, dataset_name=args.dataset)
+    library.metadata = run_metadata(dataset=args.dataset, n_rows=len(df), criterion=args.criterion,
+                                    discrete_mode=args.discrete_mode)
+    library.add_marginals(args.dataset, marginals, max_points=args.max_marginal_points)
+    pairwise_entries = build_pairwise_library(
+        u_df, dataset_name=args.dataset, selection_criterion=args.criterion, n_jobs=args.n_jobs,
+        u_minus_df=u_minus, var_types=var_types,
+    )
     library.add_pairwise(pairwise_entries)
     n_ok = sum(1 for e in pairwise_entries if "error" not in e)
     print(f"fit {n_ok}/{len(pairwise_entries)} pairwise models")
 
-    n_conditional = 0
-    if dag is not None:
-        for node in dag.nodes:
-            parents = list(dag.predecessors(node))
-            if len(parents) >= 2:
-                sampler = ConditionalSampler(child=node, parents=parents).fit(u_df)
-                library.add_conditional(args.dataset, sampler)
-                n_conditional += 1
-    print(f"fit {n_conditional} multi-parent conditional models")
+    # multi-parent targets: the dataset's own DAG (if it has one) plus any user graphs
+    targets: dict[tuple[str, frozenset], list[str]] = {}
+    graphs = [dag] if dag is not None and not args.no_dataset_dag else []
+    for path in args.dag or []:
+        graphs.append(parse_graph_spec(load_graph_spec(path))[0])
+    for graph in graphs:
+        for node in graph.nodes:
+            parents = [p for p in graph.predecessors(node)]
+            if len(parents) >= 2 and node in u_df.columns and all(p in u_df.columns for p in parents):
+                targets[(node, frozenset(parents))] = parents
+    for (node, _), parents in targets.items():
+        sampler = ConditionalSampler(child=node, parents=parents, selection_criterion=args.criterion)
+        sampler.fit(u_df, u_minus, var_types)
+        library.add_conditional(args.dataset, sampler)
+    print(f"fit {len(targets)} multi-parent conditional models")
 
     args.output.parent.mkdir(parents=True, exist_ok=True)
     library.save(args.output)
     print(f"saved library to {args.output}")
 
 
-def _load_dag_spec(path: Path) -> nx.DiGraph:
-    spec = json.loads(path.read_text())
-    dag = nx.DiGraph()
-    dag.add_nodes_from(spec.get("nodes", []))
-    dag.add_edges_from(tuple(edge) for edge in spec["edges"])
-    return dag
-
-
 def cmd_generate(args: argparse.Namespace) -> None:
-    dag = _load_dag_spec(args.dag)
-    library = DependencyLibrary.load(args.library)
-
-    node_specs = {}
-    missing = []
-    for node in dag.nodes:
-        try:
-            node_specs[node] = node_spec_from_library(library, args.dataset, node, list(dag.predecessors(node)))
-        except KeyError:
-            missing.append(node)  # falls back to GraphSampler's baseline Gaussian mode
-    if missing:
-        print(f"warning: no library entry for {missing}; using baseline Gaussian dependence for them", file=sys.stderr)
-
-    sampler = GraphSampler(dag, node_specs=node_specs, max_indegree=args.max_indegree)
+    spec = load_graph_spec(args.dag)
+    library = DependencyLibrary.load_many(args.library)
+    try:
+        dag, node_specs, report = build_node_specs(
+            library, spec, default_dataset=args.dataset, compose=not args.no_compose, strict=args.strict,
+        )
+    except StrictModeError as exc:
+        raise SystemExit(f"error: {exc}") from None
+    fallbacks = [r for r in report if "baseline" in r["decision"]]
+    if fallbacks:
+        nodes = sorted({r["node"] for r in fallbacks})
+        print(f"warning: baseline fallback for {nodes} ({len(fallbacks)} decision(s)); see the report file",
+              file=sys.stderr)
+
+    sampler = GraphSampler(dag, node_specs=node_specs, max_indegree=args.max_indegree,
+                           calibrate_margins=args.calibrate_margins)
     df = sampler.sample(n=args.n, seed=args.seed)
 
     args.output.parent.mkdir(parents=True, exist_ok=True)
     df.to_csv(args.output, index=False)
-    print(f"generated {len(df)} rows x {len(df.columns)} columns -> {args.output}")
+    report_path = args.output.with_name(args.output.name + ".report.json")
+    report_path.write_text(json.dumps({
+        "metadata": run_metadata(n=args.n, seed=args.seed, libraries=[str(p) for p in args.library]),
+        "decisions": report,
+        "diagnostics": sampler.diagnostics_,
+    }, indent=2, default=str))
+    print(f"generated {len(df)} rows x {len(df.columns)} columns -> {args.output} (report: {report_path.name})")
 
 
 def cmd_evaluate(args: argparse.Namespace) -> None:
@@ -132,51 +125,69 @@ def cmd_evaluate(args: argparse.Namespace) -> None:
     print(compare_marginals(true_df[common], sim_df[common]).to_string(index=False))
     print("\n=== pairwise dependence ===")
     print(compare_pairwise_dependence(true_df[common], sim_df[common]).to_string(index=False))
+    if args.distances:
+        numeric = [c for c in common if pd.api.types.is_numeric_dtype(true_df[c])]
+        tu, _ = to_pseudo_observations(true_df[numeric])
+        su, _ = to_pseudo_observations(sim_df[numeric])
+        print("\n=== U-space distribution distances (unbiased, permutation p-value) ===")
+        for name, stat in [("energy_distance", energy_distance), ("gaussian_mmd", gaussian_mmd)]:
+            res = permutation_test(stat, tu.to_numpy(), su.to_numpy(), n_permutations=args.permutations)
+            print(f"{name}: {res['statistic']:.5f}  p={res['p_value']:.3f}")
 
 
 def cmd_sweep(args: argparse.Namespace) -> None:
-    # deferred import: sweep_hyperparameters.py lives in scripts/, not gcda/,
-    # since it produces printed reports rather than a reusable library API.
-    # It parses --wandb from sys.argv itself, so swap in a clean argv rather
-    # than let it see "sweep" (this subcommand's own name) as a stray arg.
-    scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
-    sys.path.insert(0, str(scripts_dir))
-    import sweep_hyperparameters
-
-    original_argv = sys.argv
-    sys.argv = ["sweep_hyperparameters.py", *(["--wandb"] if args.wandb else [])]
-    try:
-        sweep_hyperparameters.main()
-    finally:
-        sys.argv = original_argv
+    from gcda.experiments.sweep import DEFAULT_CONFIG_PATH, main
+
+    main(config_path=args.config or DEFAULT_CONFIG_PATH, use_wandb=args.wandb)
 
 
 def build_parser() -> argparse.ArgumentParser:
-    parser = argparse.ArgumentParser(prog="gcda", description=__doc__)
+    parser = argparse.ArgumentParser(prog="gcda", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
     subparsers = parser.add_subparsers(dest="command", required=True)
 
     build_p = subparsers.add_parser("build-library", help="fit a dependency library from one dataset")
-    build_p.add_argument("--dataset", required=True, choices=sorted(DATASETS))
+    build_p.add_argument("--dataset", required=True, choices=DATASET_NAMES)
     build_p.add_argument("--output", type=Path, required=True)
+    build_p.add_argument("--dag", type=Path, action="append",
+                         help="graph spec(s) whose multi-parent nodes should get fitted conditional vines (repeatable)")
+    build_p.add_argument("--no-dataset-dag", action="store_true", help="do not fit vines for the dataset's own DAG")
+    build_p.add_argument("--criterion", choices=["aic", "bic"], default="bic")
+    build_p.add_argument("--discrete-mode", choices=["jitter", "native"], default="jitter",
+                         help="discrete columns: jittered pseudo-observations (thesis default) or the native "
+                              "discrete copula likelihood (recommended for skewed categorical data)")
+    build_p.add_argument("--n", type=int, default=None, help="rows to simulate (synthetic/BN datasets)")
+    build_p.add_argument("--seed", type=int, default=None)
+    build_p.add_argument("--n-jobs", type=int, default=1)
+    build_p.add_argument("--max-marginal-points", type=int, default=None,
+                         help="compress stored empirical marginals to this many quantile knots")
     build_p.set_defaults(func=cmd_build_library)
 
     gen_p = subparsers.add_parser("generate", help="sample data for a user-specified graph")
-    gen_p.add_argument("--dag", type=Path, required=True, help='JSON file: {"edges": [["a","b"], ...]}')
-    gen_p.add_argument("--library", type=Path, required=True, help="dependency library JSON (from build-library)")
-    gen_p.add_argument("--dataset", required=True, help="namespace within the library to pull models from")
+    gen_p.add_argument("--dag", type=Path, required=True, help="graph spec JSON (see gcda/generation/spec.py)")
+    gen_p.add_argument("--library", type=Path, required=True, action="append",
+                       help="dependency library JSON (repeatable; libraries are merged)")
+    gen_p.add_argument("--dataset", default=None, help="default dataset namespace for nodes without a mapping")
     gen_p.add_argument("--n", type=int, default=1000)
     gen_p.add_argument("--seed", type=int, default=0)
-    gen_p.add_argument("--max-indegree", type=int, default=2)
+    gen_p.add_argument("--max-indegree", type=int, default=4)
+    gen_p.add_argument("--no-compose", action="store_true",
+                       help="do not compose multi-parent models from pairwise copulas (use the Gaussian baseline instead)")
+    gen_p.add_argument("--calibrate-margins", action="store_true",
+                       help="rank-calibrate each node so its stored marginal is reproduced exactly")
+    gen_p.add_argument("--strict", action="store_true", help="fail instead of falling back to baseline models")
     gen_p.add_argument("--output", type=Path, required=True)
     gen_p.set_defaults(func=cmd_generate)
 
     eval_p = subparsers.add_parser("evaluate", help="compare a generated CSV against a true-data CSV")
     eval_p.add_argument("--true-csv", type=Path, required=True)
     eval_p.add_argument("--sim-csv", type=Path, required=True)
+    eval_p.add_argument("--distances", action="store_true", help="also report U-space energy distance / MMD with permutation tests")
+    eval_p.add_argument("--permutations", type=int, default=200)
     eval_p.set_defaults(func=cmd_evaluate)
 
-    sweep_p = subparsers.add_parser("sweep", help="run the hyperparameter sweep (scripts/sweep_hyperparameters.py)")
+    sweep_p = subparsers.add_parser("sweep", help="run the hyperparameter sweep (configs/sweep.yaml)")
     sweep_p.add_argument("--wandb", action="store_true", help="log to Weights & Biases (offline by default)")
+    sweep_p.add_argument("--config", type=Path, default=None)
     sweep_p.set_defaults(func=cmd_sweep)
 
     return parser
diff --git a/gcda/compat.py b/gcda/compat.py
new file mode 100644
index 0000000..8fe3496
--- /dev/null
+++ b/gcda/compat.py
@@ -0,0 +1,13 @@
+"""Small compatibility shims for third-party API changes."""
+
+
+def bicop_sample(bicop, n: int, seeds: list[int] | None = None):
+    """Draw from a pv.Bicop: `sample` in pyvinecopulib >= 1.0, `simulate` before.
+
+    Both produce identical draws for the same seeds (checked in the audit with
+    pyvinecopulib 1.0.1); this avoids the deprecation warning on new versions
+    while keeping 0.7.x working.
+    """
+    seeds = seeds or []
+    method = getattr(bicop, "sample", None) or bicop.simulate
+    return method(n, seeds=seeds)
diff --git a/gcda/data/datasets.py b/gcda/data/datasets.py
index 644eb5a..e746007 100644
--- a/gcda/data/datasets.py
+++ b/gcda/data/datasets.py
@@ -1,22 +1,63 @@
 """T4a/T7b: the Phase 1 continuous datasets and the Phase 2 discrete/mixed datasets."""
 
+import os
 import warnings
+from importlib import resources
 from pathlib import Path
 
 import networkx as nx
 import numpy as np
 import pandas as pd
 
-RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
+# Bundled as package data (gcda/data/resources) so the loaders work from a
+# regular (non-editable) install too; GCDA_DATA_DIR overrides the location.
+SACHS_FILENAME = "sachs_continuous.csv"
 
+# The CDT "cyto_full_data" file is the concatenation of the nine Sachs et al.
+# (2005) experimental conditions; the first 853 rows are the CD3/CD28
+# condition, the general-stimulation (observational) data used in most
+# causal-discovery benchmarks.  See data/raw/README.md and
+# tests/test_datasets.py for the consistency check.
+SACHS_OBSERVATIONAL_ROWS = 853
 
-def load_sachs() -> pd.DataFrame:
+# Consensus network of Sachs et al. (2005) as distributed by bnlearn/pgmpy,
+# expressed in this dataset's column names.
+SACHS_NAME_MAP = {
+    "praf": "Raf", "pmek": "Mek", "plcg": "Plcg", "PIP2": "PIP2", "PIP3": "PIP3",
+    "p44/42": "Erk", "pakts473": "Akt", "PKA": "PKA", "PKC": "PKC", "P38": "P38", "pjnk": "Jnk",
+}
+
+
+def _sachs_path() -> Path:
+    override = os.environ.get("GCDA_DATA_DIR")
+    if override:
+        return Path(override) / SACHS_FILENAME
+    return Path(str(resources.files("gcda.data").joinpath("resources", SACHS_FILENAME)))
+
+
+def load_sachs(observational_only: bool = False) -> pd.DataFrame:
     """Sachs et al. (2005) protein-signaling dataset: 11 continuous variables.
 
-    A standard continuous benchmark in the causal discovery literature.
+    By default all 7,466 rows are returned. These pool the nine experimental
+    conditions of the original study (one general stimulation + eight
+    interventions), i.e. they are NOT i.i.d. observational data. Pass
+    ``observational_only=True`` for the 853-row CD3/CD28 condition only.
     See data/raw/README.md for provenance and citation.
     """
-    return pd.read_csv(RAW_DATA_DIR / "sachs_continuous.csv")
+    df = pd.read_csv(_sachs_path())
+    if observational_only:
+        df = df.iloc[:SACHS_OBSERVATIONAL_ROWS].reset_index(drop=True)
+    return df
+
+
+def sachs_consensus_dag() -> nx.DiGraph:
+    """The bnlearn/pgmpy Sachs consensus network, relabelled to this dataset's columns."""
+    model = _example_model("sachs")
+    inverse = {v: k for k, v in SACHS_NAME_MAP.items()}
+    dag = nx.DiGraph()
+    dag.add_nodes_from(SACHS_NAME_MAP)
+    dag.add_edges_from((inverse[a], inverse[b]) for a, b in model.edges())
+    return dag
 
 
 def load_uci_diabetes() -> pd.DataFrame:
@@ -55,6 +96,26 @@ def make_synthetic_scm(n: int = 2000, seed: int = 0) -> tuple[pd.DataFrame, nx.D
     return df, dag
 
 
+def _example_model(name: str):
+    """Load a bnlearn network bundled with pgmpy.
+
+    `pgmpy.utils.get_example_model` (bundled BIF files, no network access) is
+    deprecated and scheduled for removal in pgmpy 1.3, so pyproject pins
+    pgmpy<1.3; if it is unavailable we fall back to its successor
+    `pgmpy.example_models.load_model("bnlearn/<name>")`.
+    """
+    with warnings.catch_warnings():
+        warnings.simplefilter("ignore")  # pgmpy deprecation warnings
+        try:
+            from pgmpy.utils import get_example_model
+
+            return get_example_model(name)
+        except ImportError:  # pragma: no cover - pgmpy >= 1.3
+            from pgmpy.example_models import load_model
+
+            return load_model(f"bnlearn/{name}")
+
+
 def _load_bnlearn_model(name: str, n_samples: int, seed: int) -> tuple[pd.DataFrame, nx.DiGraph, dict[str, list]]:
     """Sample a discrete Bayesian network bundled with pgmpy (no network access needed).
 
@@ -67,11 +128,7 @@ def _load_bnlearn_model(name: str, n_samples: int, seed: int) -> tuple[pd.DataFr
     of observations count as concordant/discordant for every copula fit
     involving that variable.
     """
-    with warnings.catch_warnings():
-        warnings.simplefilter("ignore")  # pgmpy warns that get_example_model is deprecated
-        from pgmpy.utils import get_example_model
-
-        model = get_example_model(name)
+    model = _example_model(name)
 
     dag = nx.DiGraph()
     dag.add_nodes_from(model.nodes())
@@ -92,6 +149,12 @@ def load_asia(n_samples: int = 10000, seed: int = 0) -> tuple[pd.DataFrame, nx.D
     return _load_bnlearn_model("asia", n_samples=n_samples, seed=seed)
 
 
+def load_alarm(n_samples: int = 10000, seed: int = 0) -> tuple[pd.DataFrame, nx.DiGraph, dict[str, list]]:
+    """ALARM network (Beinlich et al., 1989): 37 discrete variables, max indegree 4.
+    The task plan's alternative larger discrete benchmark (T7b.ii)."""
+    return _load_bnlearn_model("alarm", n_samples=n_samples, seed=seed)
+
+
 def load_insurance(n_samples: int = 10000, seed: int = 0) -> tuple[pd.DataFrame, nx.DiGraph, dict[str, list]]:
     """Insurance network (Binder et al., 1997): 27 categorical variables (2-5
     categories each), several genuinely ordinal - the larger discrete
diff --git a/gcda/data/preprocessing.py b/gcda/data/preprocessing.py
index 2bfa8fa..bd2bb4d 100644
--- a/gcda/data/preprocessing.py
+++ b/gcda/data/preprocessing.py
@@ -177,3 +177,34 @@ def to_pseudo_observations_mixed(
             u_data[col] = marginal.transform(values)
         marginals[col] = marginal
     return pd.DataFrame(u_data, index=df.index), marginals
+
+
+def discrete_cdf_pairs(
+    df: pd.DataFrame, marginals: dict[str, "EmpiricalMarginal | CategoricalMarginal"]
+) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
+    """Inputs for pyvinecopulib's *native* discrete copula likelihood.
+
+    For every column returns F(x) (`upper`) and F(x-) (`lower`, the CDF just
+    below the observed value) plus its variable type ("c"/"d"). For discrete
+    columns the copula likelihood of an observation is the rectangle
+    probability C(F(x), F(y)) - C(F(x-), F(y)) - ..., so no jittering is
+    needed and no concordance is lost to ties (Genest & Neslehova, 2007).
+    Continuous columns use their pseudo-observations for both.
+    """
+    upper, lower, var_types = {}, {}, {}
+    for col in df.columns:
+        m = marginals[col]
+        if isinstance(m, CategoricalMarginal):
+            index = {category: i for i, category in enumerate(m.categories_)}
+            idx = np.array([index[v] for v in df[col].to_numpy()])
+            upper[col] = m.cum_probs_[idx]
+            lower[col] = np.where(idx == 0, 0.0, m.cum_probs_[idx - 1])
+            var_types[col] = "d"
+        else:
+            u = m.transform(df[col].to_numpy())
+            upper[col] = u
+            lower[col] = u
+            var_types[col] = "c"
+    clip = lambda a: np.clip(a, _EPS, 1 - _EPS)  # noqa: E731
+    return (pd.DataFrame({k: clip(v) for k, v in upper.items()}, index=df.index),
+            pd.DataFrame({k: clip(v) for k, v in lower.items()}, index=df.index), var_types)
diff --git a/gcda/data/registry.py b/gcda/data/registry.py
new file mode 100644
index 0000000..e4a85fe
--- /dev/null
+++ b/gcda/data/registry.py
@@ -0,0 +1,44 @@
+"""Single registry of dataset loaders used by the CLI, the sweep and the experiments.
+
+Each loader returns ``(df, dag_or_None, category_orders_or_None)``. Sample
+sizes and seeds are explicit arguments, so different entry points that need
+different sizes (the sweep historically used n=8000 for Asia/Insurance, the
+library builder n=10000) state it instead of silently diverging.
+"""
+
+from gcda.data import datasets as ds
+
+DEFAULT_N = {"synthetic_scm": 5000, "mixed_scm": 5000, "asia": 10000, "insurance": 10000, "alarm": 10000}
+DEFAULT_SEED = {"synthetic_scm": 1, "mixed_scm": 1, "asia": 0, "insurance": 0, "alarm": 0}
+
+
+def load_dataset(name: str, n: int | None = None, seed: int | None = None):
+    n = n if n is not None else DEFAULT_N.get(name)
+    seed = seed if seed is not None else DEFAULT_SEED.get(name)
+    if name == "sachs":
+        return ds.load_sachs(), ds.sachs_consensus_dag(), None
+    if name == "sachs_observational":
+        return ds.load_sachs(observational_only=True), ds.sachs_consensus_dag(), None
+    if name == "uci_diabetes":
+        return ds.load_uci_diabetes(), None, None
+    if name == "discretized_sachs":
+        df, orders = ds.make_discretized_sachs()
+        return df, None, orders
+    if name == "synthetic_scm":
+        df, dag = ds.make_synthetic_scm(n=n, seed=seed)
+        return df, dag, None
+    if name == "mixed_scm":
+        return ds.make_mixed_synthetic_scm(n=n, seed=seed)
+    if name == "asia":
+        return ds.load_asia(n_samples=n, seed=seed)
+    if name == "insurance":
+        return ds.load_insurance(n_samples=n, seed=seed)
+    if name == "alarm":
+        return ds.load_alarm(n_samples=n, seed=seed)
+    raise KeyError(f"unknown dataset {name!r}; choose from {sorted(DATASET_NAMES)}")
+
+
+DATASET_NAMES = [
+    "sachs", "sachs_observational", "uci_diabetes", "discretized_sachs",
+    "synthetic_scm", "mixed_scm", "asia", "insurance", "alarm",
+]
diff --git a/gcda/data/resources/sachs_continuous.csv b/gcda/data/resources/sachs_continuous.csv
new file mode 100644
index 0000000..2e04f2a
--- /dev/null
+++ b/gcda/data/resources/sachs_continuous.csv
@@ -0,0 +1,7467 @@
+praf,pmek,plcg,PIP2,PIP3,p44/42,pakts473,PKA,PKC,P38,pjnk
+26.4,13.2,8.82,18.3,58.8,6.61,17.0,414.0,17.0,44.9,40.0
+35.9,16.5,12.3,16.8,8.13,18.6,32.5,352.0,3.37,16.5,61.5
+59.4,44.1,14.6,10.2,13.0,14.9,32.5,403.0,11.4,31.9,19.5
+73.0,82.8,23.1,13.5,1.29,5.83,11.8,528.0,13.7,28.6,23.1
+33.7,19.8,5.19,9.73,24.8,21.1,46.1,305.0,4.66,25.7,81.3
+18.8,3.75,17.6,22.1,10.9,11.9,25.7,610.0,13.7,49.1,57.8
+44.9,36.5,10.4,132.0,16.3,8.66,17.9,835.0,15.0,35.9,18.1
+47.4,15.0,14.6,30.5,17.5,20.2,45.3,466.0,6.44,24.4,20.0
+104.0,61.5,10.6,21.1,41.8,11.5,23.5,445.0,29.2,61.0,25.3
+21.1,21.5,1.88,205.0,43.7,13.2,135.0,213.0,14.6,26.7,101.0
+16.4,16.4,14.5,17.0,11.2,21.9,34.6,449.0,20.4,44.9,24.1
+74.3,22.9,7.5,15.5,26.2,20.9,36.5,389.0,31.9,71.0,35.5
+85.1,39.6,8.9,64.9,11.7,6.67,12.2,528.0,17.9,44.1,118.0
+36.8,29.2,5.0,9.06,15.5,17.9,17.9,400.0,14.6,41.4,151.0
+29.2,24.1,10.2,16.0,46.6,8.82,7.23,500.0,9.73,19.1,7.91
+50.0,13.8,11.9,13.2,11.3,18.1,27.9,392.0,56.2,77.0,1.0
+26.2,26.7,21.3,10.9,14.7,9.06,37.9,89.0,40.0,65.5,1.42
+39.6,38.2,10.5,92.2,22.7,27.6,31.3,223.0,16.5,30.8,7.64
+30.5,19.8,7.5,133.0,15.7,19.1,36.2,319.0,24.1,37.2,17.2
+49.1,16.5,13.3,141.0,25.7,31.1,62.1,710.0,14.2,27.4,22.1
+38.5,8.9,11.3,85.8,17.9,12.1,35.9,843.0,12.0,28.4,20.9
+31.6,17.8,14.5,10.6,4.91,10.2,23.9,276.0,13.8,28.4,12.7
+41.0,27.9,1.0,137.0,23.9,30.2,50.0,965.0,1.0,84.3,4.61
+70.4,54.2,15.4,24.4,12.9,9.91,27.9,449.0,35.9,93.9,48.3
+70.4,42.2,17.6,20.9,10.5,59.4,98.2,1981.0,35.9,46.1,17.8
+21.5,1.0,8.28,181.0,43.7,18.8,38.5,644.0,13.6,29.2,7.04
+39.2,23.1,18.6,22.1,10.6,17.8,32.2,466.0,10.5,23.3,6.98
+69.8,20.4,19.8,18.4,6.26,10.4,25.0,500.0,22.7,48.3,59.4
+34.9,22.3,17.2,50.0,23.1,34.3,51.4,308.0,13.2,38.9,196.0
+40.7,24.8,13.0,62.6,38.2,5.14,14.7,673.0,28.1,41.8,23.1
+45.7,15.7,13.2,21.3,7.5,23.9,49.1,1382.0,19.5,38.5,20.9
+43.7,29.2,14.5,17.6,13.1,8.58,12.5,621.0,34.0,67.9,28.1
+79.9,80.6,4.41,209.0,19.5,10.5,35.5,422.0,26.9,40.3,15.3
+56.7,17.3,21.7,18.1,12.7,9.22,22.9,552.0,38.5,59.9,17.9
+58.8,19.5,2.57,41.4,2.21,19.1,33.7,325.0,22.9,31.9,20.7
+53.8,12.7,10.9,12.4,30.8,20.2,37.9,403.0,22.5,38.5,20.9
+58.3,23.1,18.9,79.1,24.4,36.2,48.7,429.0,14.7,28.9,12.6
+160.0,28.1,7.1,115.0,16.1,4.96,12.4,1241.0,2.46,31.3,83.5
+45.3,9.39,12.2,53.8,27.6,4.29,27.6,599.0,38.2,80.6,139.0
+54.7,28.4,8.35,9.39,20.7,38.5,59.9,898.0,12.7,23.7,13.5
+85.1,26.9,25.3,47.8,22.9,13.6,14.2,396.0,4.74,8.98,43.3
+109.0,43.7,9.47,343.0,60.4,27.1,42.6,319.0,14.9,37.9,17.8
+25.7,15.3,1.0,120.0,23.7,2.69,18.9,10.2,4.96,40.3,221.0
+50.5,28.1,27.6,28.9,13.8,14.7,24.8,382.0,15.3,20.0,7.7
+69.2,17.8,17.8,62.1,23.1,2.71,13.3,562.0,4.45,20.0,105.0
+62.6,19.3,8.51,20.9,39.2,4.49,24.8,474.0,23.5,48.7,22.5
+67.9,43.7,11.4,19.3,15.8,17.8,38.5,1433.0,31.9,66.7,40.0
+75.0,57.8,4.91,15.4,24.6,21.9,36.2,233.0,21.3,46.1,17.0
+50.9,42.2,7.57,122.0,48.3,6.26,36.2,1027.0,12.5,32.8,108.0
+79.9,20.4,24.1,22.5,20.0,8.82,24.1,466.0,19.1,34.9,6.15
+62.6,21.7,21.9,22.1,3.82,39.2,75.7,1310.0,8.74,22.7,11.7
+50.9,25.3,6.38,76.4,17.2,9.06,15.4,673.0,4.66,26.9,173.0
+75.0,30.5,13.6,51.4,42.2,25.3,35.5,466.0,20.4,43.7,10.1
+59.4,25.3,11.7,20.7,27.9,3.62,12.4,29.7,17.2,32.5,10.5
+181.0,37.9,1.0,292.0,49.6,6.38,13.1,573.0,20.9,38.2,17.6
+69.8,33.1,12.7,67.3,1.91,4.07,27.1,973.0,85.8,121.0,32.5
+57.3,19.1,11.1,42.2,6.61,5.83,13.5,547.0,44.9,80.6,71.7
+82.8,30.5,13.9,18.6,6.92,23.5,37.5,418.0,6.55,16.7,95.6
+35.5,24.6,15.7,35.5,11.9,21.9,45.7,322.0,6.79,23.3,11.9
+80.6,27.9,17.9,42.6,17.3,2.84,20.7,188.0,20.7,33.1,17.5
+113.0,45.7,10.8,154.0,58.3,13.1,21.5,337.0,5.47,20.0,9.39
+8.9,10.1,10.3,89.0,29.4,181.0,355.0,1731.0,24.1,42.2,20.7
+35.2,14.1,7.1,20.2,32.2,12.9,22.5,583.0,37.5,47.4,9.47
+24.1,12.3,12.7,62.6,26.7,9.14,16.5,547.0,25.7,59.9,80.6
+164.0,33.1,5.78,28.6,13.7,16.3,24.1,319.0,22.5,35.5,12.4
+57.8,27.1,15.5,57.3,19.5,25.9,34.6,382.0,3.05,27.1,78.4
+90.6,27.4,40.0,97.3,71.0,10.9,18.9,429.0,4.45,42.9,80.6
+38.5,12.7,4.37,22.7,23.7,4.22,10.8,578.0,1.86,7.37,3.43
+51.4,36.8,12.7,40.3,21.7,12.7,25.9,667.0,2.5,14.9,64.9
+26.9,15.1,18.6,20.5,8.43,20.4,38.5,437.0,11.7,24.4,15.4
+56.2,21.1,12.7,21.1,57.8,14.1,19.8,474.0,25.9,39.6,75.7
+70.4,35.5,18.4,45.7,47.8,18.8,31.6,418.0,10.0,22.3,6.67
+58.8,35.2,12.2,16.5,24.1,18.4,33.7,362.0,16.3,19.8,10.4
+69.2,35.5,17.3,50.0,19.8,8.51,18.6,151.0,12.0,31.1,27.6
+69.8,47.0,25.5,276.0,77.0,32.8,51.4,799.0,19.6,47.8,16.4
+105.0,59.9,20.0,19.6,15.1,6.85,23.1,1065.0,1.67,48.3,4.66
+62.1,51.9,13.6,30.2,10.6,14.3,37.9,692.0,6.49,25.0,91.4
+75.0,33.4,1.0,31.6,1.0,19.8,27.6,505.0,18.6,31.1,7.64
+20.4,15.1,7.99,101.0,35.9,9.14,22.9,400.0,11.7,22.7,6.85
+47.8,19.6,17.5,33.1,82.0,17.9,35.2,956.0,22.5,43.3,20.0
+59.9,53.3,11.8,77.7,12.9,11.1,37.9,1407.0,18.8,29.4,16.8
+46.6,27.1,12.4,109.0,21.9,21.5,38.2,207.0,11.0,31.3,12.0
+51.9,21.3,49.1,58.8,10.8,58.8,200.0,3051.0,15.3,39.2,15.7
+31.9,23.9,15.1,12.7,4.61,6.73,15.0,562.0,1.0,68.5,8.2
+93.9,27.4,67.3,138.0,30.8,28.1,46.1,906.0,2.69,6.98,71.0
+64.9,23.3,15.3,12.6,9.06,19.6,35.2,806.0,2.37,20.0,7.91
+153.0,123.0,12.0,34.6,63.8,8.58,26.2,470.0,1.0,12.0,9.91
+16.7,12.4,7.04,235.0,34.9,44.9,64.9,1843.0,23.5,36.2,30.5
+71.7,25.5,13.1,12.0,43.3,12.2,31.3,655.0,7.7,16.4,49.1
+35.5,23.7,2.89,4.26,12.9,13.0,22.7,470.0,7.77,33.4,16.3
+83.5,61.5,13.0,34.6,12.3,3.46,19.5,239.0,2.53,2.69,6.1
+31.9,8.82,12.9,154.0,56.7,16.8,16.0,433.0,9.56,48.7,54.2
+29.4,20.2,7.7,125.0,27.4,89.0,150.0,799.0,2.71,15.4,49.1
+302.0,325.0,17.6,25.7,10.7,29.2,38.2,313.0,10.8,36.5,17.2
+40.3,16.5,11.5,505.0,67.3,19.3,29.7,483.0,2.92,15.3,89.0
+29.2,15.4,9.73,23.1,71.0,6.38,47.0,557.0,20.0,24.6,7.7
+46.1,25.7,12.7,24.4,37.2,16.8,35.9,375.0,5.47,39.2,95.6
+52.3,21.5,27.1,155.0,67.9,7.23,23.9,820.0,3.59,25.0,93.1
+48.7,36.5,18.6,10.6,13.9,6.1,25.9,1009.0,10.2,22.7,15.3
+85.8,82.0,120.0,325.0,79.1,6.61,10.9,723.0,12.1,21.9,5.42
+75.7,25.9,21.5,64.4,45.3,8.28,28.4,583.0,15.7,36.8,13.7
+58.3,21.9,14.9,18.4,30.2,5.47,17.2,982.0,16.3,21.5,15.5
+58.8,34.9,13.3,82.8,38.2,22.5,27.9,379.0,6.55,18.4,48.7
+112.0,27.6,28.4,67.9,30.5,10.8,16.7,403.0,17.8,29.7,7.77
+66.7,29.2,2.39,10.9,32.2,22.9,32.2,379.0,14.3,30.8,17.6
+39.6,23.9,6.61,137.0,20.4,22.7,38.2,313.0,16.1,20.0,10.5
+36.5,15.5,2.55,8.35,40.0,15.8,34.6,281.0,21.3,28.6,13.9
+38.2,25.7,32.2,59.4,138.0,24.1,36.5,331.0,38.5,67.9,16.3
+41.8,21.3,9.39,7.91,32.5,13.3,61.0,858.0,2.81,17.3,64.4
+62.1,18.1,24.8,113.0,25.5,17.0,34.6,604.0,4.26,13.5,72.3
+167.0,79.1,9.65,111.0,20.2,28.4,89.0,1472.0,20.4,29.2,12.9
+55.7,28.6,25.9,51.9,64.9,7.5,17.6,271.0,2.21,4.45,9.73
+84.3,71.7,12.9,93.1,36.5,8.9,17.8,906.0,9.06,25.0,42.2
+60.4,25.3,19.1,27.4,44.5,44.5,64.9,1197.0,20.9,49.6,17.5
+57.3,21.9,38.2,38.5,81.3,5.83,12.9,274.0,16.0,21.5,14.9
+76.4,32.8,30.0,60.4,49.6,5.47,14.3,87.4,11.1,27.4,7.43
+96.5,119.0,15.5,71.0,13.9,19.5,32.2,500.0,50.9,75.0,26.9
+38.5,17.8,32.2,115.0,61.0,10.6,21.3,965.0,5.0,20.4,34.9
+66.1,46.6,7.7,19.6,75.7,15.7,17.8,519.0,12.0,13.8,14.9
+112.0,79.1,7.37,15.0,35.9,10.6,32.2,382.0,14.9,31.1,12.0
+47.0,22.3,12.2,73.0,24.1,3.49,11.4,340.0,5.62,13.9,93.9
+87.4,54.7,19.6,8.58,24.8,15.8,33.1,757.0,24.6,40.7,25.0
+57.8,19.1,22.9,19.1,11.3,18.8,57.3,743.0,8.66,8.35,24.4
+92.2,31.1,18.9,22.3,34.3,13.6,29.4,385.0,7.23,17.6,7.99
+93.1,28.9,9.56,11.4,23.1,20.4,24.8,319.0,4.14,20.2,122.0
+107.0,36.8,16.0,38.9,29.2,18.8,28.1,276.0,1.83,25.5,97.3
+80.6,56.7,16.1,27.6,4.03,5.28,5.88,491.0,3.52,5.57,24.4
+44.9,25.3,1.0,158.0,12.3,14.2,26.2,514.0,6.55,16.1,33.7
+27.4,18.8,9.65,13.2,9.73,18.6,54.7,286.0,1.88,19.8,88.2
+31.6,25.7,24.6,35.2,25.7,14.1,25.7,284.0,20.4,28.4,48.3
+52.3,33.4,8.13,25.5,5.73,30.5,42.9,305.0,34.9,68.5,20.4
+71.7,27.4,8.82,18.3,23.1,14.1,27.4,649.0,3.82,20.2,53.8
+44.5,26.9,15.5,87.4,12.5,4.53,16.0,379.0,3.68,32.5,77.0
+74.3,27.4,16.4,22.7,2.0,6.26,15.1,457.0,13.6,24.6,6.55
+44.1,20.2,13.9,17.8,39.2,22.3,30.2,487.0,30.5,40.0,23.7
+42.9,22.9,17.3,17.8,21.9,13.1,36.8,710.0,12.6,24.4,65.5
+79.1,26.4,1.19,3.96,41.4,8.06,20.4,509.0,3.68,16.0,63.2
+89.0,30.0,44.9,47.0,7.37,52.8,97.3,2288.0,69.8,94.7,8.28
+63.2,27.4,14.5,80.6,41.0,15.1,38.2,453.0,13.6,32.8,13.1
+27.9,20.7,25.3,70.4,42.2,6.98,21.3,313.0,24.8,44.5,23.1
+69.8,22.9,19.3,17.5,9.73,20.7,28.1,255.0,13.0,25.3,9.73
+28.9,15.7,22.7,37.9,49.1,13.0,23.5,509.0,22.1,53.8,35.9
+102.0,30.8,7.17,82.0,49.1,20.2,25.0,343.0,3.96,26.9,87.4
+59.4,25.3,14.9,61.5,26.2,22.5,36.5,239.0,2.74,14.5,77.7
+89.8,31.3,18.8,22.5,8.74,25.0,37.5,426.0,29.7,60.4,24.1
+200.0,33.1,19.5,56.2,16.1,21.7,35.5,305.0,4.26,14.2,95.6
+62.1,18.1,14.9,149.0,62.1,4.49,20.7,698.0,44.1,125.0,57.3
+46.1,23.7,17.9,276.0,41.4,15.0,19.5,334.0,16.7,31.6,11.8
+149.0,85.1,8.43,7.99,17.8,29.2,69.2,1208.0,26.4,46.6,30.0
+8.9,15.5,7.91,153.0,16.0,40.3,61.5,1582.0,12.2,25.7,12.0
+109.0,40.0,9.82,24.4,73.0,12.3,23.1,487.0,17.9,30.8,15.1
+71.7,42.9,31.1,23.9,10.5,8.13,34.9,2571.0,1.0,33.4,1.01
+68.5,24.4,16.3,47.8,13.9,5.94,17.2,649.0,18.6,38.5,17.8
+79.9,44.1,4.45,89.8,28.1,39.2,82.8,632.0,20.4,51.4,35.9
+85.1,34.9,1.0,325.0,23.5,44.1,86.6,799.0,23.9,41.8,16.7
+196.0,163.0,3.85,311.0,59.9,22.9,25.3,470.0,2.15,6.61,2.81
+38.5,17.3,25.7,26.4,10.9,29.4,42.6,322.0,23.3,37.5,19.3
+64.4,50.9,12.7,12.4,3.11,22.5,30.0,573.0,25.0,54.7,20.9
+97.3,22.7,17.5,101.0,31.3,19.6,25.3,352.0,13.9,36.2,9.82
+79.1,28.4,7.3,6.73,66.7,27.4,53.3,1655.0,40.0,66.1,20.4
+106.0,24.8,1.35,61.0,16.1,70.4,108.0,1018.0,15.4,31.9,14.2
+76.4,30.8,8.51,141.0,12.1,19.3,34.0,297.0,6.15,29.4,118.0
+108.0,30.8,21.5,41.0,30.8,6.61,27.4,1094.0,11.5,30.2,67.3
+53.3,34.6,18.3,41.0,56.2,3.79,30.8,965.0,3.43,16.4,70.4
+27.9,19.3,24.4,106.0,23.7,14.7,21.3,519.0,14.9,36.2,16.5
+69.8,26.2,21.9,20.4,17.0,18.9,45.3,533.0,2.41,9.47,74.3
+7.23,5.88,17.8,119.0,14.1,8.82,23.7,445.0,3.0,18.1,66.7
+49.1,18.8,14.9,29.4,15.0,17.6,28.1,470.0,1.88,21.9,59.4
+42.6,15.7,53.3,62.6,16.5,3.79,10.3,552.0,6.98,44.9,271.0
+16.5,22.9,9.22,10.9,46.1,3.59,13.6,874.0,12.5,28.1,2.89
+101.0,61.0,17.9,13.0,27.9,7.99,11.1,215.0,5.14,11.4,58.8
+59.9,21.9,11.5,17.2,13.3,8.82,24.8,965.0,9.22,44.9,3.85
+102.0,46.1,11.3,104.0,13.3,36.8,65.5,914.0,13.7,33.4,11.0
+142.0,101.0,26.9,422.0,101.0,11.3,19.5,649.0,8.43,29.2,138.0
+61.5,17.2,17.8,10.1,16.7,14.9,33.1,542.0,11.1,20.9,154.0
+54.7,20.4,15.5,35.2,32.5,11.7,18.1,599.0,1.63,17.5,67.9
+50.5,19.5,4.78,13.6,24.8,11.7,28.9,509.0,18.3,39.6,23.3
+34.0,13.3,26.7,38.2,98.2,34.0,59.4,704.0,32.8,63.2,50.9
+48.7,19.5,32.8,43.7,44.9,8.58,24.4,466.0,1.6,20.4,64.9
+70.4,25.3,12.3,145.0,21.1,4.53,24.6,255.0,4.83,18.8,51.9
+45.7,19.1,6.32,94.7,17.2,8.43,16.0,244.0,3.08,23.5,93.9
+78.4,33.1,25.3,27.4,46.6,66.7,164.0,3220.0,17.8,29.7,18.3
+17.6,11.4,32.5,94.7,117.0,23.7,36.5,355.0,9.82,23.1,18.9
+29.4,26.4,15.1,21.5,8.13,15.4,71.7,610.0,2.07,22.1,57.3
+63.8,21.1,7.64,38.2,50.0,4.41,13.9,461.0,20.5,31.3,13.2
+227.0,155.0,28.6,32.8,22.3,10.8,10.1,362.0,19.6,39.2,12.1
+64.4,29.7,13.7,33.4,8.58,7.7,23.1,1252.0,12.6,25.3,1.11
+57.8,15.3,19.5,71.0,31.6,14.3,17.9,505.0,18.9,38.9,33.1
+75.0,23.7,13.5,178.0,31.6,21.5,33.1,255.0,28.1,43.7,12.5
+48.7,25.0,52.3,109.0,16.3,6.85,17.8,445.0,3.85,16.0,63.8
+61.0,53.3,27.4,32.5,3.72,9.56,25.7,1346.0,1.42,19.6,79.9
+96.5,46.1,16.1,15.5,31.6,3.85,22.3,5.57,6.15,32.5,73.0
+54.7,26.2,12.5,93.9,14.9,11.5,18.6,474.0,16.4,24.1,7.3
+118.0,39.2,66.1,75.0,14.1,4.33,11.1,562.0,18.3,36.5,13.3
+96.5,56.2,29.7,39.2,16.1,12.2,37.9,1000.0,17.3,47.0,23.1
+89.0,52.8,24.4,18.9,3.85,23.1,42.9,710.0,21.1,37.9,18.6
+25.3,38.5,21.5,48.3,75.0,19.1,33.7,308.0,89.0,138.0,46.6
+96.5,46.1,20.9,51.4,14.5,53.3,118.0,882.0,3.34,12.9,30.5
+62.6,34.9,18.1,133.0,30.0,21.5,24.1,403.0,9.56,21.3,13.6
+18.3,20.0,47.4,75.7,63.2,13.3,19.3,400.0,19.3,31.9,29.4
+65.5,32.5,12.9,17.0,12.7,18.8,31.1,334.0,5.88,33.1,138.0
+85.1,41.0,14.9,32.2,27.4,38.5,47.0,777.0,6.38,23.1,56.2
+79.9,25.0,36.5,26.2,42.6,4.91,9.91,385.0,5.42,25.9,98.2
+42.2,20.2,8.2,26.9,23.9,19.1,40.3,422.0,22.9,32.5,24.4
+61.0,19.1,10.2,68.5,28.6,10.9,6.55,267.0,20.5,43.7,21.9
+17.5,10.9,6.1,155.0,21.3,17.2,26.4,389.0,17.3,47.0,23.7
+36.5,22.3,33.4,63.8,126.0,9.73,19.8,552.0,20.9,34.6,15.4
+14.6,14.9,21.7,167.0,31.3,19.1,32.8,286.0,5.19,15.5,108.0
+17.3,24.4,25.7,26.9,8.58,21.5,36.2,284.0,17.0,35.2,14.9
+63.2,10.9,65.5,127.0,29.7,26.9,53.8,337.0,25.9,38.9,20.5
+35.2,16.0,12.5,157.0,48.3,15.5,117.0,1499.0,28.9,46.1,10.7
+57.3,27.6,14.5,173.0,37.2,5.57,12.4,604.0,15.8,37.2,18.8
+24.4,15.5,15.0,114.0,15.8,16.7,30.0,1000.0,13.6,20.5,17.3
+69.8,40.7,14.6,135.0,27.9,29.2,42.9,385.0,14.3,24.1,9.06
+74.3,35.9,44.9,53.8,75.0,10.6,33.1,1382.0,10.6,28.9,4.26
+101.0,35.5,16.5,88.2,16.8,49.6,72.3,730.0,17.2,32.5,17.9
+41.4,17.2,22.1,21.1,12.7,23.9,34.3,379.0,1.0,13.2,8.66
+82.0,66.1,11.4,17.2,32.8,5.28,12.3,158.0,25.7,63.2,31.9
+86.6,38.2,18.8,10.3,2.48,19.5,31.3,382.0,18.8,30.5,3.49
+14.1,7.23,20.7,155.0,13.5,17.3,86.6,195.0,20.5,38.2,15.8
+89.8,52.3,2.81,14.5,49.1,38.2,83.5,750.0,25.5,41.0,15.0
+97.3,41.4,27.6,178.0,48.3,11.3,27.1,528.0,3.82,14.6,68.5
+26.9,13.7,11.0,34.9,35.5,17.5,39.2,505.0,13.9,30.2,10.2
+89.0,21.3,13.7,20.7,15.5,3.31,13.7,407.0,1.78,1.53,55.2
+66.1,23.9,17.6,12.6,20.0,21.7,35.9,269.0,24.4,36.5,11.3
+129.0,53.3,25.3,382.0,87.4,7.64,8.13,305.0,6.49,40.3,87.4
+39.2,19.3,37.5,85.8,46.1,7.23,12.1,599.0,21.9,47.0,17.8
+25.0,18.6,4.03,12.0,36.2,29.7,41.0,346.0,5.78,11.9,26.4
+45.7,19.3,7.17,98.2,29.7,5.33,22.9,365.0,23.3,40.0,21.1
+62.1,20.5,25.0,57.3,12.1,14.9,21.5,422.0,1.0,89.0,1.57
+71.0,32.5,20.2,83.5,131.0,4.83,20.5,25.3,23.9,37.5,17.8
+50.0,31.6,6.67,11.3,14.9,14.7,113.0,181.0,17.5,28.6,9.22
+102.0,31.6,4.41,12.9,21.7,8.58,18.3,523.0,10.1,33.4,104.0
+63.2,24.6,11.2,16.5,3.11,6.44,17.5,542.0,3.49,9.82,4.53
+233.0,66.1,14.5,87.4,20.4,13.3,18.4,359.0,1.0,18.9,58.8
+38.9,24.1,18.9,36.8,17.5,42.6,80.6,1075.0,11.8,35.9,11.3
+98.2,44.1,6.04,23.1,16.1,12.0,22.7,547.0,22.9,50.5,15.4
+38.9,24.6,8.66,6.49,26.2,22.7,26.7,219.0,10.7,39.6,71.7
+87.4,29.4,22.5,22.7,13.9,26.2,47.8,311.0,10.8,13.8,9.65
+75.7,21.5,1.0,71.7,2.27,6.26,15.5,418.0,14.7,28.9,12.7
+79.9,18.9,15.7,80.6,23.7,7.77,15.1,396.0,20.0,32.8,18.6
+52.8,19.5,19.3,54.7,47.4,43.7,57.3,661.0,11.2,38.9,98.2
+63.8,17.0,33.7,35.2,12.9,70.4,109.0,1358.0,9.73,25.9,91.4
+107.0,44.9,7.99,17.6,45.7,7.84,21.1,500.0,4.53,12.4,69.8
+59.4,18.4,17.0,76.4,16.3,31.1,59.4,667.0,18.4,51.9,18.4
+106.0,74.3,48.7,61.5,24.8,16.0,36.2,542.0,7.7,27.9,167.0
+71.0,40.7,11.7,16.8,14.5,7.99,16.7,655.0,24.8,43.3,14.3
+21.5,13.1,23.7,24.4,17.0,4.29,11.1,392.0,12.3,27.9,29.2
+149.0,51.4,33.7,120.0,31.6,29.4,54.2,1762.0,19.1,26.7,8.9
+25.9,12.3,17.8,112.0,18.1,17.9,36.5,346.0,5.0,21.1,57.3
+64.4,48.3,12.3,30.0,35.2,13.3,34.9,349.0,13.7,31.1,16.1
+36.2,11.3,15.5,16.4,37.9,15.3,22.9,414.0,4.14,10.4,68.5
+51.9,26.7,12.9,44.5,4.49,30.2,50.0,302.0,17.9,22.3,10.3
+21.7,7.57,9.65,308.0,38.2,11.8,29.4,355.0,8.13,17.2,89.8
+93.9,35.9,17.6,14.3,13.0,23.5,40.0,300.0,13.2,24.6,13.0
+56.7,20.5,13.6,88.2,30.0,24.4,32.5,414.0,25.3,41.4,16.4
+66.1,16.1,11.0,75.0,14.3,13.2,29.2,466.0,24.8,49.6,29.2
+27.6,17.0,11.2,99.1,50.0,29.7,50.5,1346.0,25.3,52.8,13.2
+49.1,33.4,21.7,19.8,10.1,25.3,39.2,400.0,25.7,33.7,20.9
+157.0,51.9,12.3,21.7,45.3,5.99,45.3,49.1,7.77,10.3,41.0
+124.0,33.4,13.5,16.3,17.5,16.1,25.0,466.0,9.47,24.1,262.0
+37.9,16.4,34.6,39.2,6.85,2.53,13.9,239.0,4.07,58.8,89.0
+45.3,25.5,22.1,15.1,13.3,12.3,22.9,474.0,2.05,23.5,106.0
+163.0,86.6,33.1,53.8,15.4,40.3,53.3,316.0,18.9,38.5,13.2
+62.6,33.7,8.58,37.2,44.9,5.0,4.29,400.0,24.6,45.3,28.6
+26.4,15.3,43.7,43.7,13.3,6.04,21.9,1037.0,30.8,61.0,14.2
+52.3,29.7,13.3,85.1,88.2,11.9,32.2,1446.0,19.5,43.7,20.7
+81.3,24.8,21.5,25.0,4.53,181.0,248.0,621.0,15.3,34.0,22.1
+95.6,38.2,5.0,281.0,64.4,26.4,45.3,496.0,26.2,48.7,10.4
+79.9,29.4,5.05,117.0,17.3,30.0,71.0,828.0,8.82,22.1,12.6
+17.3,14.6,15.1,121.0,30.8,10.4,14.7,717.0,16.0,26.4,8.35
+51.4,37.9,42.6,73.7,36.2,15.5,35.5,1219.0,1.98,17.6,77.0
+38.5,7.3,3.13,17.0,17.5,29.4,41.8,470.0,27.4,42.9,16.0
+52.8,53.3,3.65,13.6,42.6,36.8,62.6,1000.0,12.4,23.5,23.7
+91.4,40.3,17.0,38.2,1.49,10.5,27.1,1009.0,29.7,50.0,33.4
+37.9,14.2,13.3,32.8,12.1,17.9,42.9,487.0,2.11,24.8,66.7
+55.2,18.8,7.5,32.5,13.6,55.7,97.3,2618.0,10.1,30.8,58.3
+44.5,24.8,15.5,178.0,45.3,21.1,57.3,982.0,1.0,58.3,8.43
+70.4,30.0,20.4,17.3,13.7,19.1,36.8,349.0,17.0,53.3,22.3
+47.4,30.5,19.8,21.7,31.6,33.1,87.4,400.0,3.89,36.8,96.5
+63.8,21.7,22.7,184.0,36.2,20.5,26.2,359.0,3.96,19.8,80.6
+23.5,42.9,12.1,29.2,27.4,1.5,8.51,154.0,20.7,36.2,13.5
+5.23,15.1,22.1,93.9,7.7,133.0,297.0,1094.0,9.39,19.6,4.14
+14.5,15.4,1.0,117.0,3.49,16.0,29.4,457.0,20.4,48.3,16.0
+36.8,9.47,12.2,12.6,15.8,20.0,30.0,271.0,12.1,26.2,85.8
+97.3,25.3,17.6,12.9,17.3,6.98,9.22,352.0,12.6,23.3,20.9
+16.3,12.1,67.3,149.0,39.6,43.3,64.4,1027.0,9.56,15.4,67.3
+44.5,31.3,33.1,184.0,58.8,32.5,43.3,286.0,1.0,59.4,3.68
+67.9,53.3,17.5,97.3,37.5,22.1,36.8,331.0,5.42,15.1,94.7
+59.4,28.1,18.9,81.3,18.1,79.9,165.0,2129.0,8.58,17.0,7.57
+25.9,17.2,21.5,24.1,36.8,15.3,32.2,313.0,9.91,18.8,9.22
+40.0,32.8,11.3,98.2,19.5,40.0,75.7,365.0,19.3,33.7,14.7
+60.4,24.8,17.0,337.0,60.4,12.7,25.0,496.0,9.91,20.5,9.56
+50.5,24.6,17.0,136.0,30.0,57.8,91.4,1526.0,1.54,23.3,59.9
+31.1,18.8,6.15,191.0,13.0,10.6,21.9,466.0,13.7,26.7,15.0
+11.2,17.9,17.5,15.1,29.2,12.7,19.3,331.0,18.8,24.8,10.9
+39.2,28.4,23.1,14.2,24.4,92.2,235.0,1670.0,8.06,19.3,18.4
+72.3,27.1,18.4,37.2,25.7,7.3,23.3,1075.0,7.04,21.3,35.5
+62.1,16.1,25.0,379.0,78.4,31.3,50.0,343.0,14.1,20.2,9.65
+12.7,12.9,30.5,32.8,19.6,3.37,14.1,385.0,31.9,59.4,28.1
+49.6,17.9,7.5,11.1,3.02,67.3,129.0,737.0,17.0,31.6,7.77
+62.6,22.7,13.1,125.0,10.3,5.73,22.5,418.0,17.3,32.5,12.4
+10.8,5.33,23.9,49.1,12.9,11.0,22.9,483.0,2.35,21.1,85.8
+74.3,26.4,13.5,36.5,50.0,4.26,17.2,70.4,3.0,14.7,92.2
+73.0,21.7,6.79,213.0,23.5,16.5,19.1,429.0,1.67,44.9,3.0
+10.9,6.38,16.7,145.0,33.4,8.58,11.0,305.0,1.6,13.8,62.6
+55.2,18.9,11.0,123.0,11.9,11.5,23.9,422.0,11.2,25.3,14.2
+56.7,13.9,18.4,13.5,15.5,5.67,30.2,538.0,17.9,39.6,14.6
+97.3,61.5,11.8,165.0,34.6,24.6,31.9,433.0,19.5,35.2,21.5
+45.3,19.5,19.3,47.0,85.8,3.55,30.0,1124.0,17.5,44.5,157.0
+45.3,16.5,17.0,89.8,47.0,19.5,46.1,407.0,11.1,27.6,122.0
+248.0,271.0,17.8,34.0,38.9,21.5,38.5,449.0,2.59,35.5,3.75
+58.3,34.0,19.8,164.0,35.9,20.5,33.4,313.0,14.1,32.2,13.9
+112.0,46.1,10.8,133.0,9.22,4.1,10.8,552.0,26.9,53.8,25.9
+16.0,15.0,17.9,153.0,35.2,12.9,35.5,457.0,11.2,25.7,1.19
+67.3,31.6,26.7,13.5,17.2,31.1,50.5,294.0,16.1,35.9,1.0
+39.2,15.8,16.5,22.9,17.3,11.0,28.9,311.0,3.75,7.91,8.35
+68.5,24.4,20.7,63.8,26.2,27.1,33.1,392.0,2.97,13.6,57.8
+59.9,40.0,6.44,196.0,25.9,95.6,143.0,1700.0,16.8,47.4,16.7
+88.2,67.3,36.5,58.8,119.0,12.7,36.2,429.0,38.2,136.0,55.7
+13.1,11.2,42.2,154.0,64.4,21.1,34.9,239.0,5.38,17.2,73.7
+99.1,50.5,14.6,76.4,30.0,3.92,12.0,343.0,13.6,29.4,12.0
+53.3,18.6,22.7,55.7,21.1,17.6,17.2,449.0,29.2,44.1,21.9
+137.0,50.0,8.28,29.2,14.5,6.98,17.9,281.0,4.18,23.5,123.0
+44.5,19.8,19.8,89.8,47.8,3.92,18.9,661.0,4.29,21.7,126.0
+255.0,85.8,20.0,73.0,34.9,7.23,17.0,322.0,12.7,21.1,26.2
+55.2,25.0,31.3,98.2,35.2,3.0,6.04,27.6,5.57,18.1,7.43
+74.3,34.6,13.9,17.2,10.8,9.31,32.5,1286.0,36.5,73.0,33.7
+117.0,49.1,1.0,396.0,33.1,12.2,27.9,547.0,2.39,22.1,98.2
+44.5,26.4,13.2,69.8,13.0,15.8,19.3,231.0,35.5,54.7,27.4
+87.4,54.7,20.5,176.0,33.7,10.3,22.3,426.0,27.1,27.4,1.73
+32.2,14.9,13.7,12.9,15.5,9.06,21.5,528.0,9.91,23.3,95.6
+37.2,14.5,26.9,17.3,13.2,24.1,31.6,300.0,12.2,34.3,18.4
+50.9,24.4,68.5,137.0,50.9,22.7,40.3,496.0,42.6,74.3,200.0
+29.4,20.4,35.2,33.1,38.9,26.7,47.0,340.0,32.8,53.8,19.1
+48.3,7.43,15.5,110.0,48.7,3.79,17.0,483.0,7.04,31.3,92.2
+64.9,34.9,5.94,11.3,26.2,68.5,106.0,615.0,15.1,40.3,26.9
+32.8,23.9,23.7,18.8,5.83,33.4,55.2,806.0,15.3,37.2,21.5
+26.4,17.0,51.9,47.8,8.2,22.9,37.9,257.0,50.9,71.7,27.9
+69.8,34.0,24.1,71.7,17.6,13.2,24.6,264.0,18.1,41.4,23.5
+45.7,18.3,8.66,18.4,64.4,10.6,14.9,429.0,16.1,25.9,10.5
+131.0,37.2,19.1,97.3,30.2,24.1,29.4,313.0,16.0,19.1,18.4
+106.0,38.2,9.14,24.1,32.2,18.3,30.5,685.0,12.1,28.1,19.6
+68.5,28.1,16.4,145.0,16.5,10.7,23.7,573.0,4.18,30.8,59.9
+59.4,26.7,10.1,83.5,1.64,6.79,21.5,346.0,4.18,23.3,33.7
+47.0,17.0,42.2,71.0,44.5,10.8,57.3,538.0,26.9,50.0,15.3
+56.7,35.9,9.14,30.8,15.4,37.9,105.0,1625.0,21.7,30.5,19.8
+28.4,12.6,21.1,31.3,45.3,36.2,60.4,835.0,4.18,15.8,90.6
+35.2,19.1,28.6,66.1,60.4,2.71,21.1,599.0,3.19,14.3,90.6
+47.0,24.1,17.8,257.0,75.7,7.77,29.2,956.0,10.8,30.5,11.5
+63.2,18.9,20.5,15.4,9.31,21.1,113.0,1104.0,23.7,56.2,13.3
+62.6,21.1,6.04,209.0,24.8,5.05,18.4,583.0,2.79,12.4,8.28
+14.2,11.7,24.8,38.9,63.2,6.1,14.2,355.0,10.7,30.2,10.6
+53.8,20.7,16.4,15.3,1.43,12.1,18.4,509.0,9.65,53.3,217.0
+68.5,27.6,17.5,82.0,18.6,6.85,24.1,359.0,1.1,61.5,14.1
+119.0,64.4,10.5,53.8,28.6,8.66,33.4,2480.0,2.97,31.9,78.4
+41.8,11.1,14.9,18.6,66.7,6.79,34.0,698.0,13.3,22.3,11.1
+44.9,21.7,15.0,48.7,42.9,2.59,20.9,414.0,13.9,27.4,9.91
+72.3,38.9,1.0,547.0,11.2,3.68,13.7,343.0,15.3,40.0,18.3
+53.3,34.6,2.89,1.11,764.0,8.66,12.7,219.0,24.6,63.8,137.0
+31.9,18.9,87.4,130.0,31.3,7.57,24.6,523.0,9.47,23.7,16.3
+117.0,59.4,10.8,284.0,23.1,21.1,30.5,305.0,7.1,21.1,32.5
+45.3,32.8,26.9,137.0,37.5,3.08,11.5,649.0,2.33,31.6,57.3
+46.6,30.0,12.9,16.7,14.2,10.1,16.7,262.0,32.5,96.5,25.7
+30.5,8.9,163.0,379.0,75.0,13.2,16.5,514.0,19.5,26.4,17.8
+41.8,12.0,11.1,28.9,35.9,6.26,22.9,24.4,2.79,15.4,83.5
+102.0,38.2,37.5,244.0,73.7,14.9,15.3,466.0,5.28,30.5,122.0
+33.1,26.2,23.7,168.0,43.3,115.0,209.0,791.0,20.0,18.1,12.4
+44.1,33.4,15.7,21.3,15.5,7.77,19.1,441.0,2.35,17.5,82.8
+15.3,14.9,18.9,17.8,14.1,21.9,23.7,294.0,8.28,17.9,10.7
+85.8,31.3,9.65,73.7,10.8,5.94,17.9,441.0,22.3,46.6,32.8
+32.5,27.1,22.7,22.5,22.5,21.9,33.1,509.0,21.1,33.7,9.22
+54.7,19.3,36.2,50.0,28.4,12.1,28.9,294.0,16.1,27.6,15.0
+40.0,23.7,14.3,19.8,13.7,1.73,5.67,16.8,23.5,42.6,11.5
+36.5,16.5,15.5,32.2,9.47,3.34,5.42,257.0,26.9,47.0,66.1
+52.8,50.0,34.3,95.6,71.7,29.4,64.9,453.0,12.3,22.1,21.3
+81.3,61.5,20.4,25.9,13.7,40.7,50.0,422.0,11.2,28.4,14.5
+13.5,30.0,24.8,255.0,61.5,29.7,44.5,231.0,19.3,35.2,15.1
+17.5,29.4,27.4,22.9,24.1,22.5,29.2,422.0,26.9,44.1,4.26
+38.2,25.9,45.7,39.6,13.1,20.2,42.6,362.0,3.43,13.0,52.8
+104.0,26.2,11.4,11.9,22.1,9.56,15.0,349.0,1.36,31.9,1.0
+37.2,12.1,31.3,21.9,10.0,12.0,22.3,372.0,3.34,10.4,75.7
+52.3,41.0,25.0,53.8,19.3,9.91,20.0,610.0,1.0,52.8,8.9
+80.6,25.5,11.8,96.5,9.65,2.76,18.6,13.3,20.2,40.0,17.0
+227.0,42.2,16.3,62.6,11.7,2.39,26.2,562.0,2.27,28.1,20.5
+33.4,4.45,17.2,30.0,28.6,28.9,55.7,429.0,27.9,37.5,12.5
+31.9,16.0,7.77,24.1,85.8,5.73,7.04,292.0,10.6,30.2,12.1
+73.7,25.3,15.4,120.0,12.6,4.78,18.8,445.0,4.74,15.3,114.0
+55.2,55.7,9.56,514.0,53.8,7.99,15.3,685.0,14.3,26.7,11.5
+37.5,21.9,7.37,23.3,57.8,8.9,14.3,375.0,18.4,46.1,35.2
+25.0,16.5,9.31,19.5,3.52,106.0,172.0,1715.0,11.3,22.7,16.7
+70.4,33.1,8.2,500.0,93.1,47.8,88.2,1055.0,2.53,12.1,87.4
+31.1,20.2,23.9,400.0,110.0,9.14,13.2,567.0,31.3,80.6,106.0
+47.4,14.1,9.31,20.4,26.2,6.26,8.28,385.0,14.3,25.3,14.9
+86.6,49.1,17.9,4.91,15.3,10.8,17.0,284.0,21.3,37.2,11.2
+120.0,45.3,18.6,113.0,25.5,16.5,38.2,1114.0,16.0,31.3,6.55
+51.4,37.9,20.0,19.3,25.7,10.5,44.5,764.0,17.5,36.8,14.3
+27.6,26.2,18.3,64.9,44.1,21.5,30.8,1155.0,18.1,31.1,8.98
+42.2,16.8,16.5,163.0,8.74,12.7,30.5,441.0,9.91,17.6,17.6
+32.2,28.4,39.6,25.5,11.5,14.7,24.6,319.0,24.6,44.1,19.8
+38.2,24.1,28.1,22.1,30.0,25.5,47.8,1186.0,25.3,53.8,39.2
+55.7,26.9,28.6,9.47,50.0,25.0,43.3,437.0,3.85,19.6,38.2
+47.4,25.5,15.5,35.5,3.65,14.9,18.4,737.0,4.87,15.4,76.4
+40.7,17.2,15.1,15.5,3.62,11.7,21.1,514.0,24.4,50.0,119.0
+10.6,14.1,28.4,17.9,12.4,17.6,25.7,365.0,4.57,12.5,40.3
+92.2,30.2,16.7,77.0,55.7,7.91,26.9,562.0,2.69,13.3,61.5
+33.4,12.7,21.5,48.3,22.9,22.1,29.7,276.0,3.46,11.3,24.4
+25.7,7.84,41.4,29.4,25.5,17.6,28.6,331.0,14.5,27.6,13.8
+63.2,32.5,22.1,292.0,35.2,4.14,8.28,164.0,13.8,27.6,1.02
+65.5,28.9,11.9,104.0,28.6,13.6,21.9,337.0,13.3,33.4,17.5
+51.4,59.4,42.2,178.0,66.1,5.78,22.7,514.0,9.82,18.3,4.0
+65.5,48.3,17.9,93.1,25.3,9.31,11.9,491.0,2.86,15.7,57.3
+13.3,20.7,18.6,147.0,35.5,69.2,110.0,1275.0,5.73,16.5,16.8
+114.0,39.6,14.1,75.0,33.1,6.73,23.3,737.0,13.3,35.2,12.7
+141.0,65.5,46.6,276.0,112.0,40.0,56.2,743.0,15.0,26.7,20.7
+43.7,19.3,23.7,34.6,19.8,20.0,35.9,610.0,1.35,93.1,8.35
+3.82,14.6,15.8,8.9,10.3,12.6,26.9,308.0,46.6,77.7,44.9
+93.1,80.6,21.3,17.2,18.4,28.6,43.3,311.0,8.2,18.4,5.28
+50.0,28.1,22.3,28.6,19.3,9.73,39.2,1472.0,29.7,59.9,22.7
+89.8,17.0,20.9,85.8,29.7,1.0,3.16,248.0,16.3,28.9,19.6
+17.2,15.1,21.3,22.1,20.0,20.9,27.9,379.0,12.7,25.9,3.4
+43.7,26.7,23.3,78.4,43.7,11.5,12.6,483.0,11.1,31.1,9.06
+19.1,15.5,4.37,9.91,22.3,10.8,16.3,491.0,8.51,27.9,16.4
+195.0,60.4,32.2,11.4,44.5,4.53,13.3,28.4,15.8,25.9,20.7
+88.2,33.7,12.0,56.2,16.7,10.0,16.3,407.0,15.5,38.5,11.1
+92.2,37.2,22.3,146.0,19.3,19.1,37.2,325.0,14.1,27.6,16.1
+39.6,11.9,19.3,552.0,76.4,16.5,27.4,365.0,13.6,24.6,16.1
+93.1,36.5,9.31,349.0,38.9,11.5,19.3,355.0,8.58,12.6,23.5
+18.3,4.1,14.5,149.0,25.0,18.9,39.6,355.0,4.74,17.5,67.3
+63.2,22.7,10.8,106.0,36.5,57.3,93.1,1046.0,15.0,31.9,11.4
+43.7,13.8,2.21,316.0,24.6,15.0,31.3,828.0,12.3,23.1,11.8
+8.2,17.0,21.1,85.8,31.3,16.5,26.9,305.0,23.5,38.5,8.9
+26.7,17.0,1.35,365.0,17.8,14.1,52.8,1700.0,10.3,20.7,13.9
+50.5,28.1,49.1,60.4,41.8,31.6,51.9,1219.0,8.58,53.3,12.5
+84.3,34.6,5.14,15.8,14.3,13.5,21.5,349.0,3.46,12.1,62.1
+62.6,24.1,20.9,12.9,23.1,40.7,93.1,1794.0,4.18,12.6,93.1
+63.8,21.7,15.4,39.2,8.9,100.0,233.0,2458.0,14.1,32.5,14.5
+43.3,21.7,8.66,48.3,42.6,8.98,14.9,557.0,8.2,34.3,165.0
+79.1,25.5,7.57,93.1,22.1,8.9,19.8,478.0,20.5,32.8,14.2
+10.8,15.0,23.5,28.4,55.7,1.22,14.7,828.0,18.9,31.9,10.1
+78.4,22.1,30.0,328.0,35.2,12.3,22.9,253.0,16.7,25.9,10.6
+90.6,49.1,18.1,105.0,21.5,22.9,31.9,392.0,15.8,24.1,11.1
+552.0,389.0,12.9,161.0,44.5,17.8,25.9,770.0,4.03,13.5,26.7
+40.7,24.6,61.0,120.0,22.9,23.5,50.5,717.0,45.7,85.8,39.6
+60.4,12.7,17.3,175.0,22.3,12.7,31.1,319.0,3.65,23.3,55.7
+50.5,21.1,17.5,22.3,4.22,25.3,38.9,382.0,3.52,8.43,71.7
+117.0,38.9,26.7,14.3,10.3,15.1,29.2,843.0,23.1,36.8,15.1
+61.0,21.7,12.6,82.0,23.7,10.6,20.5,1346.0,21.7,36.2,16.4
+92.2,42.2,14.5,32.2,37.2,4.0,17.0,334.0,11.4,29.2,70.4
+11.0,9.31,7.43,126.0,24.1,15.5,26.2,594.0,18.9,44.1,22.7
+170.0,86.6,29.7,179.0,47.0,29.2,43.3,331.0,4.18,23.9,93.9
+54.2,21.9,11.7,229.0,36.5,36.2,127.0,939.0,16.8,40.0,14.9
+18.1,23.5,40.7,91.4,53.8,14.7,28.4,552.0,4.96,41.4,292.0
+34.9,21.7,41.4,215.0,83.5,7.23,17.6,538.0,27.6,57.3,20.4
+179.0,164.0,15.8,45.7,11.9,17.5,30.0,730.0,17.2,25.9,17.9
+83.5,48.7,34.0,107.0,67.9,17.6,31.1,316.0,2.05,15.0,71.7
+89.0,31.6,54.2,79.9,26.9,4.0,58.8,523.0,5.47,21.7,54.7
+58.8,37.9,5.67,22.3,11.2,34.9,63.8,1946.0,15.7,29.4,9.91
+31.9,11.4,14.1,12.2,6.04,14.9,28.9,470.0,24.8,39.6,30.8
+46.6,19.5,29.2,58.3,47.4,5.38,31.6,457.0,10.2,32.8,22.1
+37.9,10.6,17.6,32.2,14.7,14.6,28.4,244.0,6.79,14.6,66.1
+73.0,20.0,13.3,13.6,28.6,2.25,23.1,302.0,58.3,111.0,170.0
+42.2,17.9,31.9,75.7,77.0,24.1,106.0,1794.0,15.4,49.6,200.0
+87.4,57.3,24.8,110.0,40.7,24.4,27.4,359.0,12.0,20.4,6.98
+41.0,17.0,21.1,244.0,70.4,10.4,16.8,470.0,19.6,38.5,19.6
+50.9,35.2,22.1,22.9,3.19,3.96,12.4,115.0,32.2,49.6,18.8
+10.8,19.3,17.8,29.4,26.9,5.19,10.8,698.0,4.74,10.1,69.8
+77.7,48.7,20.7,21.7,18.6,11.0,33.1,400.0,13.5,22.7,14.6
+74.3,30.5,22.1,35.5,50.9,126.0,276.0,1625.0,17.6,27.9,17.9
+40.7,55.7,11.2,114.0,26.7,53.3,84.3,956.0,12.4,26.7,15.0
+77.0,20.4,12.6,25.7,37.5,3.55,12.4,562.0,10.1,25.5,26.7
+14.3,5.42,13.0,89.0,1.64,8.2,21.9,414.0,21.3,33.1,23.1
+51.9,33.7,15.0,43.3,12.5,20.9,35.9,403.0,93.9,170.0,40.0
+33.4,24.1,9.14,18.9,54.7,44.9,102.0,1334.0,28.9,69.2,47.0
+75.0,46.6,2.84,457.0,37.2,6.55,19.8,389.0,20.0,31.1,11.5
+1.61,11.4,34.3,31.3,7.04,49.6,81.3,791.0,8.51,30.8,155.0
+53.3,21.5,6.44,253.0,23.1,9.47,26.2,334.0,3.4,27.6,79.1
+85.1,32.2,16.8,32.5,64.4,3.02,27.9,207.0,26.4,38.9,11.8
+50.9,28.6,25.3,56.7,38.2,29.4,60.4,717.0,9.73,19.3,14.7
+25.9,22.9,33.4,93.9,26.7,5.57,14.9,615.0,16.1,33.7,17.5
+85.8,62.1,53.3,325.0,239.0,12.9,24.6,403.0,10.6,14.3,12.2
+94.7,37.5,72.3,96.5,33.1,25.5,46.6,588.0,4.7,17.2,28.4
+40.0,18.4,24.4,63.8,35.2,6.15,16.4,81.3,15.5,27.6,15.7
+77.0,46.1,35.2,90.6,41.0,16.1,25.9,396.0,2.0,76.4,14.3
+28.6,22.5,40.7,204.0,66.1,20.0,29.2,239.0,1.32,36.2,1.79
+92.2,56.2,15.3,19.1,12.7,9.14,9.39,322.0,11.1,20.0,18.9
+14.6,11.0,8.35,175.0,32.2,8.35,25.9,965.0,23.9,35.2,5.19
+54.2,17.9,19.8,22.1,18.8,27.1,41.8,319.0,10.9,23.9,13.2
+29.7,18.9,3.43,14.7,23.5,2.76,9.65,276.0,1.95,79.1,4.87
+31.1,23.9,1.0,843.0,82.8,16.4,30.2,474.0,8.06,21.7,6.61
+75.0,21.1,39.2,33.4,2.23,18.1,28.4,302.0,19.5,36.8,12.6
+42.9,23.1,4.14,200.0,16.7,19.1,45.3,1252.0,25.7,27.9,17.9
+82.8,26.9,7.84,142.0,3.85,17.6,25.3,297.0,34.0,71.7,33.7
+426.0,255.0,11.5,58.3,15.8,7.77,16.3,685.0,5.52,6.44,3.62
+54.2,33.4,20.4,20.5,22.3,20.9,33.1,269.0,18.9,46.6,18.3
+88.2,19.5,22.3,81.3,16.4,4.57,16.5,542.0,18.4,33.4,14.1
+12.4,21.1,14.2,14.1,61.5,16.0,33.7,835.0,10.4,21.5,8.06
+147.0,85.1,15.4,59.4,111.0,21.1,27.9,297.0,1.18,8.82,41.8
+58.8,24.1,18.3,16.7,9.47,2.21,10.6,1.95,1.6,5.38,5.38
+48.3,12.3,24.1,17.3,1.0,1.55,19.5,42.9,21.1,34.3,18.6
+107.0,50.0,13.6,67.9,23.1,20.9,27.1,331.0,3.11,12.1,33.7
+79.9,122.0,23.7,20.5,15.5,10.7,22.7,407.0,3.65,20.7,59.9
+77.0,36.2,23.9,29.4,10.9,15.0,27.9,375.0,22.3,35.9,11.7
+52.3,34.9,10.1,32.2,36.8,23.9,35.5,231.0,14.1,18.8,11.5
+69.8,23.1,17.6,445.0,109.0,24.8,38.5,179.0,21.1,47.8,22.7
+84.3,33.7,21.1,38.2,24.4,9.82,13.1,519.0,28.6,55.2,16.7
+59.9,30.5,8.51,6.55,8.74,10.4,22.3,368.0,13.7,25.0,14.3
+47.0,25.9,13.6,16.4,13.2,23.5,46.6,1241.0,18.4,35.2,22.9
+74.3,16.5,53.3,47.8,50.9,22.3,37.5,461.0,22.1,49.1,14.2
+8.28,19.3,18.9,161.0,35.5,26.2,44.1,191.0,17.6,38.2,20.9
+66.1,53.8,11.1,20.5,26.9,5.19,15.7,573.0,8.9,11.4,38.5
+47.0,23.1,18.6,28.1,18.4,11.3,30.0,743.0,28.4,47.8,19.3
+23.5,27.4,2.44,122.0,15.0,18.1,28.4,294.0,3.82,19.5,155.0
+12.3,6.38,7.37,111.0,18.6,3.11,18.8,496.0,14.2,34.0,13.5
+15.8,10.5,12.6,18.9,14.2,17.5,32.5,316.0,31.1,46.6,19.6
+21.1,25.3,11.4,109.0,22.3,20.2,31.9,385.0,17.2,29.4,11.7
+12.7,10.2,11.5,130.0,28.6,20.0,25.7,359.0,6.21,29.4,27.1
+15.0,13.2,26.2,28.1,13.5,11.2,44.1,2035.0,7.17,17.2,12.6
+69.2,28.6,4.57,389.0,45.3,1.81,14.5,204.0,22.7,38.2,10.4
+9.65,3.05,31.3,106.0,40.0,28.1,46.1,470.0,15.8,20.7,7.91
+43.7,21.5,12.2,53.3,59.9,6.79,15.3,362.0,29.4,52.8,38.9
+32.2,21.5,5.88,136.0,18.3,96.5,175.0,578.0,3.34,23.3,83.5
+37.9,12.3,11.2,57.3,10.6,16.7,46.6,1611.0,15.3,39.2,23.1
+48.3,33.7,15.7,11.3,28.1,7.5,32.5,1310.0,11.2,27.9,20.9
+33.1,17.3,5.99,93.9,26.4,11.5,41.8,692.0,4.57,18.4,3.02
+45.7,28.9,12.1,13.7,40.3,5.88,13.3,403.0,23.7,43.3,8.28
+22.1,5.78,30.5,17.3,7.3,7.1,19.5,418.0,28.4,57.8,20.2
+40.0,16.0,10.2,18.9,31.3,5.19,17.2,922.0,25.0,59.9,35.9
+31.1,20.2,8.74,11.3,67.9,42.6,54.2,343.0,2.44,6.92,73.7
+97.3,36.5,21.7,57.3,4.18,4.74,40.7,505.0,16.1,31.6,14.9
+31.9,23.9,7.57,40.3,19.1,56.2,93.9,1625.0,10.7,18.4,10.3
+38.2,13.9,30.8,211.0,92.2,14.1,17.5,547.0,17.5,39.6,16.7
+51.4,25.7,7.91,23.3,24.1,7.04,14.9,470.0,42.6,58.3,2.97
+56.2,19.8,9.14,17.2,10.6,16.8,71.7,1894.0,12.0,23.5,16.3
+75.0,26.4,25.0,163.0,35.5,19.6,30.0,250.0,15.8,28.9,12.4
+55.7,23.9,8.06,16.7,25.7,16.4,21.7,573.0,35.2,63.2,17.8
+50.9,31.6,11.1,8.28,21.3,1.22,14.2,604.0,1.19,63.8,7.5
+83.5,26.9,13.7,52.3,46.6,18.3,22.9,292.0,19.3,47.0,20.4
+67.9,28.4,18.4,255.0,40.7,119.0,173.0,621.0,6.44,13.1,77.0
+57.3,26.7,14.6,109.0,21.5,1.89,9.56,396.0,19.6,39.6,16.8
+34.9,54.7,11.8,105.0,18.4,19.6,77.0,163.0,8.9,31.9,33.7
+66.7,24.8,16.7,19.1,18.9,30.8,61.0,1252.0,18.8,36.5,25.9
+39.6,45.3,21.3,110.0,38.5,10.1,30.5,685.0,18.8,34.6,22.3
+47.4,27.9,7.04,25.7,39.6,5.0,16.7,319.0,10.3,27.1,5.78
+40.7,22.3,14.9,38.5,7.04,6.38,29.7,19.6,32.2,64.9,51.9
+52.3,25.0,15.3,29.4,9.31,17.6,17.9,316.0,15.4,41.0,146.0
+18.9,15.0,10.6,172.0,21.5,21.9,28.4,372.0,1.39,50.0,6.32
+41.0,23.1,20.9,11.8,8.9,21.3,37.2,784.0,3.19,21.9,65.5
+47.0,33.7,22.9,33.7,20.7,18.6,35.5,267.0,12.9,34.6,13.7
+33.1,19.3,9.39,18.4,33.1,27.6,30.2,407.0,9.56,16.0,9.91
+20.2,15.5,8.2,150.0,40.3,16.3,33.4,331.0,3.65,11.5,83.5
+75.0,32.2,24.6,20.5,16.0,21.3,25.5,284.0,27.6,47.8,30.2
+25.0,10.7,9.73,27.1,15.4,11.0,19.1,302.0,3.13,18.4,71.0
+5.57,13.0,14.6,112.0,32.8,16.4,27.4,528.0,2.21,24.1,69.2
+21.5,9.73,14.5,91.4,17.8,2.71,16.8,552.0,6.1,19.3,6.92
+53.3,22.5,17.6,15.5,9.91,21.3,34.3,313.0,23.1,38.9,16.7
+59.9,26.9,20.4,196.0,69.8,18.6,49.6,947.0,4.57,18.8,133.0
+54.2,23.3,9.22,26.7,49.1,17.5,33.4,478.0,10.9,25.0,5.28
+90.6,38.9,15.7,33.4,16.7,25.7,34.6,359.0,3.34,19.3,97.3
+73.0,30.2,44.9,349.0,130.0,13.8,22.9,359.0,11.0,29.7,114.0
+38.9,14.9,24.1,82.8,17.2,21.5,21.5,271.0,13.6,31.9,14.7
+21.5,12.7,27.6,53.3,53.3,25.3,44.9,325.0,19.3,25.3,9.65
+64.9,46.6,26.2,21.9,14.1,24.1,31.1,375.0,12.1,27.1,7.99
+27.1,18.1,15.7,40.7,16.1,21.3,39.6,264.0,15.8,28.9,11.1
+57.8,27.4,6.61,14.7,18.1,28.1,32.5,349.0,10.3,26.7,9.73
+39.2,13.2,35.2,26.4,59.4,45.3,72.3,813.0,12.1,27.6,10.2
+40.7,24.8,15.8,6.67,45.3,13.7,30.5,461.0,15.0,22.1,48.7
+31.6,17.5,8.9,196.0,20.5,6.61,13.2,365.0,17.5,23.1,20.5
+88.2,39.6,27.9,89.8,35.9,6.21,24.1,698.0,40.7,73.7,45.7
+99.1,53.3,17.2,101.0,26.7,38.5,70.4,552.0,2.48,7.91,89.0
+91.4,18.3,21.5,28.4,4.66,29.2,55.2,588.0,29.4,77.0,200.0
+50.0,28.1,12.3,117.0,16.3,27.6,40.0,223.0,5.94,24.4,103.0
+47.0,30.2,22.3,37.5,18.3,2.11,14.1,23.9,2.21,22.7,80.6
+53.8,22.1,15.8,11.4,10.8,11.7,34.9,193.0,3.34,14.5,77.0
+32.2,17.6,16.4,88.2,37.2,9.56,22.5,557.0,16.1,31.1,18.4
+66.7,44.1,14.5,15.4,8.13,15.4,34.0,392.0,22.7,37.9,17.9
+40.3,14.6,12.2,64.4,20.7,19.1,29.2,382.0,22.1,36.2,17.8
+14.3,8.43,11.2,15.4,55.2,9.47,33.4,1104.0,26.9,44.1,13.6
+57.3,35.5,15.3,21.7,20.2,19.5,38.5,396.0,2.62,27.9,8.9
+2.97,7.23,14.2,73.7,6.85,17.5,25.5,195.0,1.76,8.43,75.0
+13.1,1.53,34.0,66.7,11.1,12.6,24.6,355.0,1.53,19.3,75.7
+95.6,33.1,22.7,47.4,12.9,34.3,44.5,237.0,5.67,16.0,82.8
+36.5,19.3,18.4,16.3,33.7,13.2,106.0,400.0,17.0,35.9,13.5
+91.4,26.2,22.9,43.3,27.1,20.2,36.2,328.0,12.2,22.9,3.02
+70.4,41.4,18.3,83.5,14.5,43.7,77.7,1219.0,11.9,22.7,15.8
+73.7,29.4,27.1,188.0,74.3,13.2,32.2,259.0,20.9,35.9,9.14
+142.0,107.0,45.7,138.0,75.0,26.4,45.7,403.0,14.6,21.7,11.9
+34.0,13.3,33.7,271.0,71.0,4.41,39.2,982.0,20.7,28.9,9.65
+82.8,35.2,25.5,92.2,64.4,7.99,26.9,632.0,14.5,25.0,11.8
+53.8,23.9,14.1,70.4,4.07,9.22,10.5,334.0,6.04,12.9,75.7
+62.6,43.3,26.7,170.0,28.4,3.75,10.6,389.0,11.2,18.9,10.9
+42.6,22.7,14.3,204.0,33.7,56.2,87.4,578.0,5.62,22.3,102.0
+25.9,11.7,23.7,32.2,24.1,16.7,42.9,483.0,4.18,19.3,40.3
+50.5,32.2,42.2,47.4,28.4,27.4,46.1,470.0,5.28,13.2,36.2
+8.66,5.38,8.28,102.0,15.4,19.5,18.1,407.0,11.2,28.1,163.0
+31.9,22.1,20.9,145.0,26.2,12.7,20.7,334.0,15.7,35.2,12.0
+31.9,22.5,15.7,32.5,26.9,7.43,25.9,655.0,17.9,44.1,14.7
+43.3,21.7,21.7,16.0,22.5,2.81,12.3,757.0,8.35,26.4,13.0
+56.2,34.9,25.9,6.21,1.0,19.6,37.9,352.0,1.0,3.82,5.14
+47.8,34.9,13.5,21.7,13.9,9.56,19.1,483.0,1.55,25.3,87.4
+14.3,22.3,10.0,31.6,29.4,5.52,21.9,334.0,14.2,26.4,10.3
+31.6,23.5,31.3,14.5,14.1,10.3,16.8,478.0,5.09,12.1,50.5
+58.8,19.1,19.6,100.0,19.8,9.65,45.7,939.0,2.09,13.9,61.0
+34.0,20.2,16.0,37.9,16.3,16.3,25.0,264.0,11.0,27.4,36.8
+37.9,32.8,31.6,131.0,16.4,44.9,73.7,308.0,1.63,21.5,95.6
+31.6,21.7,26.7,51.4,18.6,14.7,49.6,1186.0,26.2,58.3,19.5
+102.0,50.0,42.2,78.4,32.8,17.0,57.3,1114.0,6.32,18.1,101.0
+25.3,14.5,28.9,65.5,37.9,47.4,66.1,264.0,18.3,35.9,5.14
+14.7,44.9,29.2,276.0,76.4,45.7,65.5,403.0,27.1,49.6,21.1
+41.4,20.7,12.1,18.3,14.9,7.84,21.5,1155.0,6.32,16.4,9.31
+20.7,8.98,19.1,39.6,26.9,14.6,23.5,368.0,19.5,38.5,14.3
+15.5,26.2,19.6,20.2,11.3,8.74,28.4,407.0,8.58,21.3,34.6
+56.2,34.9,17.0,20.0,15.0,7.3,22.7,973.0,3.08,15.3,60.4
+23.5,23.9,12.7,21.1,32.5,15.8,31.6,271.0,5.94,19.5,18.3
+73.7,14.1,50.5,82.0,23.9,25.3,47.4,1134.0,20.2,23.1,8.9
+55.2,20.7,21.7,27.4,12.5,14.5,41.4,1407.0,22.3,28.1,21.5
+32.2,21.3,17.9,89.8,27.1,4.14,17.8,372.0,43.7,59.9,19.5
+65.5,38.5,20.4,133.0,37.2,59.9,110.0,1358.0,2.74,13.9,98.2
+28.6,47.4,17.8,66.7,27.9,12.4,20.2,414.0,16.7,31.1,11.2
+28.9,16.5,20.2,23.7,4.14,4.7,18.9,7.43,1.68,91.4,3.55
+25.5,15.8,13.7,300.0,42.9,16.0,27.4,284.0,19.5,34.9,20.5
+37.2,25.3,17.5,82.0,24.6,7.77,16.8,426.0,16.5,26.7,6.79
+79.9,28.6,2.67,300.0,40.3,29.2,52.8,626.0,7.7,25.7,189.0
+43.3,15.5,1.06,202.0,24.6,20.2,30.5,379.0,12.1,24.6,16.3
+36.2,20.7,23.9,20.0,11.0,10.6,21.3,453.0,4.0,9.91,54.7
+77.7,40.0,18.9,22.7,14.2,10.9,39.2,362.0,4.07,21.5,136.0
+89.0,24.4,37.2,35.5,10.8,9.73,11.3,337.0,12.5,25.9,8.13
+114.0,26.7,9.47,124.0,24.4,13.0,20.5,284.0,3.4,13.9,1.0
+63.8,22.1,5.78,8.74,14.2,17.6,31.3,362.0,5.83,21.9,34.9
+37.2,11.1,23.5,100.0,26.7,15.7,73.7,519.0,30.5,82.8,19.1
+75.0,44.5,24.1,11.8,20.7,6.67,14.5,422.0,24.8,35.2,6.61
+68.5,21.9,12.7,95.6,32.2,8.51,15.8,343.0,25.7,56.7,21.5
+23.1,12.1,25.3,36.5,17.0,14.1,29.4,392.0,15.7,26.4,16.5
+55.2,32.8,16.3,16.4,25.7,24.1,49.1,806.0,6.32,11.7,54.7
+12.6,8.06,4.91,19.5,69.8,8.28,23.5,542.0,11.0,29.7,89.8
+102.0,79.9,15.4,17.0,5.23,5.33,11.1,422.0,7.57,42.2,149.0
+79.9,28.9,25.7,24.6,10.4,24.1,29.7,274.0,10.3,16.1,67.9
+83.5,31.1,22.5,67.3,28.6,12.0,25.3,178.0,33.1,66.1,34.9
+80.6,40.7,16.8,14.2,4.1,20.2,33.4,239.0,3.96,7.17,82.0
+58.3,46.1,19.6,153.0,18.6,4.57,1.7,113.0,106.0,153.0,34.3
+61.0,27.9,32.8,52.8,11.2,12.9,30.5,271.0,12.2,19.3,9.47
+50.9,15.0,16.5,17.5,5.42,44.1,82.8,1176.0,8.43,21.9,15.4
+15.3,16.7,21.9,106.0,40.0,9.47,22.5,429.0,33.1,51.4,17.8
+49.1,24.6,10.1,145.0,14.3,12.3,24.4,453.0,26.2,37.9,17.6
+42.9,24.6,24.8,59.4,20.7,22.5,41.8,407.0,21.1,44.9,18.8
+57.3,30.8,48.7,9.73,64.4,15.5,27.4,523.0,7.84,24.1,92.2
+14.5,40.7,19.6,426.0,73.0,15.3,33.1,334.0,3.02,20.0,79.1
+89.8,19.3,16.5,15.8,1.3,43.7,79.9,1731.0,12.1,24.6,8.74
+58.8,17.6,24.8,179.0,61.5,17.3,69.2,717.0,2.04,30.5,86.6
+139.0,110.0,23.5,496.0,84.3,20.7,40.7,410.0,20.2,40.0,19.3
+36.5,18.4,3.25,9.73,38.9,4.22,13.0,241.0,16.3,36.5,20.9
+18.8,19.5,25.9,322.0,51.9,10.5,23.1,365.0,3.79,10.9,73.7
+35.9,15.1,10.8,85.8,21.3,10.1,23.7,414.0,21.9,53.8,27.1
+36.8,19.6,22.3,106.0,27.1,11.5,21.5,294.0,2.02,11.1,86.6
+62.6,27.6,77.0,53.8,16.0,7.77,14.1,331.0,18.6,39.6,12.9
+52.8,28.4,16.3,108.0,44.9,16.4,30.8,213.0,18.9,32.2,19.5
+51.9,24.4,23.3,124.0,41.0,10.8,20.7,331.0,27.9,61.0,32.8
+8.43,19.8,18.9,139.0,49.6,15.7,26.7,294.0,1.0,101.0,6.21
+37.2,16.7,14.7,81.3,13.3,9.39,24.8,328.0,24.8,41.4,32.8
+69.2,37.2,21.3,40.0,21.5,13.6,28.1,359.0,12.2,26.4,59.4
+24.6,16.0,23.7,392.0,113.0,16.8,29.2,355.0,12.0,47.0,191.0
+42.9,20.5,18.4,64.9,42.9,4.03,11.1,400.0,29.2,37.9,15.4
+84.3,18.6,17.2,25.0,9.56,5.99,13.0,311.0,21.9,36.8,13.7
+48.3,36.8,28.9,36.2,12.7,29.7,44.1,257.0,16.3,27.4,10.8
+31.1,12.6,3.96,13.2,47.0,27.4,41.0,346.0,2.53,12.5,82.8
+37.5,31.1,22.1,27.9,27.9,18.8,37.2,573.0,1.88,33.1,54.7
+27.6,20.2,14.5,122.0,26.9,8.35,12.1,418.0,19.6,35.9,22.5
+37.9,13.7,6.32,12.7,48.3,54.2,78.4,1230.0,8.13,18.8,10.6
+150.0,55.7,39.6,70.4,85.1,51.9,88.2,649.0,23.1,42.2,20.4
+51.4,22.5,15.4,21.7,14.3,16.8,32.8,365.0,9.31,14.9,41.8
+38.5,19.1,22.1,23.1,5.94,29.4,33.7,271.0,30.5,58.8,59.4
+63.2,37.2,37.9,81.3,39.2,316.0,621.0,1472.0,18.1,30.8,9.73
+26.9,19.8,25.0,20.0,7.1,13.1,30.2,851.0,5.94,30.0,239.0
+26.9,14.7,8.9,85.8,8.58,9.39,19.8,505.0,20.5,39.2,25.7
+61.0,17.3,32.5,34.9,26.7,20.7,126.0,150.0,12.5,52.8,264.0
+51.9,23.5,37.2,54.7,2.5,22.5,37.2,300.0,33.7,55.2,38.2
+34.6,14.5,17.0,100.0,15.8,22.1,26.7,204.0,23.3,48.7,47.8
+97.3,28.4,30.5,44.9,12.5,15.5,26.4,267.0,7.84,54.7,343.0
+6.26,21.1,1.0,137.0,4.29,6.15,15.5,1446.0,11.3,18.9,9.91
+17.5,36.2,4.26,429.0,40.3,10.3,39.6,85.1,23.3,66.1,12.1
+2.74,3.96,38.2,37.9,9.56,47.0,71.7,1144.0,25.9,50.5,113.0
+48.3,28.6,26.7,84.3,29.7,5.67,16.5,491.0,5.38,38.5,121.0
+53.8,38.5,20.0,14.2,9.73,8.06,15.8,407.0,17.2,26.4,19.3
+62.1,20.7,14.7,14.5,8.13,9.31,24.8,414.0,3.49,33.7,204.0
+61.5,26.2,4.96,92.2,24.8,18.4,20.0,599.0,11.5,18.4,6.55
+62.6,37.5,61.0,155.0,21.7,12.9,14.1,375.0,23.1,47.0,26.2
+103.0,37.9,10.6,47.0,8.98,17.0,32.8,255.0,2.69,44.5,1.95
+40.7,9.39,23.1,18.6,2.44,6.44,19.5,331.0,8.58,20.0,7.99
+107.0,27.9,11.0,141.0,31.9,14.2,27.4,337.0,11.2,24.6,10.4
+106.0,55.2,18.4,16.5,10.4,19.1,30.0,286.0,4.26,15.7,71.7
+41.0,28.4,20.7,13.8,17.3,15.7,90.6,991.0,26.7,43.3,23.5
+18.9,11.0,14.2,8.66,34.6,153.0,239.0,704.0,32.5,41.4,13.9
+35.2,23.5,25.5,22.3,4.03,9.47,12.9,331.0,13.6,36.2,10.1
+39.6,17.3,13.8,111.0,51.4,12.2,18.1,400.0,2.15,93.9,3.37
+17.0,6.73,7.23,55.7,8.2,3.59,29.2,649.0,19.5,39.6,7.37
+92.2,31.3,9.82,36.2,88.2,5.88,12.1,382.0,8.06,20.5,7.3
+25.5,18.9,16.7,28.9,4.83,8.43,13.6,661.0,15.8,37.9,18.4
+63.8,28.6,20.5,19.3,6.98,20.9,26.7,382.0,11.1,22.7,30.0
+22.5,44.5,12.7,157.0,12.1,22.7,27.1,445.0,17.9,40.0,12.7
+38.9,14.3,18.9,167.0,36.5,5.23,5.19,519.0,15.7,24.6,23.5
+20.5,6.79,17.8,164.0,47.8,13.2,20.5,547.0,15.1,35.2,12.9
+89.8,40.7,21.9,16.0,24.1,23.3,51.9,1084.0,4.41,12.3,60.4
+109.0,69.2,13.6,77.0,5.52,75.7,107.0,562.0,19.3,35.9,30.2
+62.1,25.0,59.4,109.0,31.6,31.1,52.3,947.0,28.4,49.1,5.67
+37.5,19.5,21.9,93.9,31.9,15.8,25.7,352.0,27.4,34.3,17.8
+64.4,22.3,36.5,359.0,62.6,11.8,21.7,461.0,13.3,20.9,10.8
+30.0,24.8,16.7,79.1,42.2,16.8,33.1,1346.0,12.0,30.5,16.8
+35.2,16.1,36.8,47.4,10.5,10.3,14.3,1046.0,36.8,98.2,62.1
+60.4,15.5,13.6,70.4,40.3,8.43,21.3,250.0,23.7,40.0,29.7
+34.9,31.6,21.9,246.0,78.4,10.6,34.6,461.0,37.2,59.4,32.5
+47.4,34.6,7.04,33.7,37.5,7.37,10.9,407.0,31.3,50.9,33.1
+18.1,29.2,17.6,40.3,38.5,12.3,16.8,461.0,6.85,11.5,29.7
+52.3,32.5,12.4,50.9,22.3,18.1,32.8,352.0,8.06,28.9,4.83
+66.1,24.6,38.5,123.0,37.9,13.1,22.3,365.0,11.4,39.6,92.2
+18.6,29.2,13.5,17.0,13.7,17.9,21.1,346.0,11.0,23.5,15.3
+38.9,23.3,12.4,27.9,48.3,2.19,12.6,63.8,8.66,21.7,26.9
+92.2,16.7,5.62,7.43,27.6,55.2,76.4,784.0,16.0,28.6,8.2
+139.0,56.7,51.9,41.0,47.8,17.9,43.3,1155.0,11.4,31.1,34.3
+92.2,36.5,3.75,113.0,17.6,24.8,32.2,319.0,3.85,18.1,23.5
+78.4,30.5,19.3,89.8,33.4,4.22,31.9,813.0,1.58,18.8,54.7
+23.9,23.7,28.4,30.0,7.43,16.8,33.7,223.0,4.26,41.8,136.0
+92.2,30.8,20.2,21.5,6.1,26.9,51.9,1526.0,1.78,22.5,84.3
+35.9,28.1,12.1,135.0,25.9,6.26,12.6,429.0,17.6,27.6,11.2
+64.4,18.1,23.7,16.4,3.37,16.3,34.0,355.0,9.91,20.9,6.32
+82.0,28.1,13.2,79.9,33.4,8.43,17.8,594.0,29.7,47.8,83.5
+55.2,20.4,25.5,15.7,16.4,23.3,34.0,319.0,11.1,27.4,4.37
+39.2,26.2,22.5,105.0,22.7,15.4,24.8,382.0,33.1,89.8,30.0
+66.1,33.4,48.7,55.2,17.8,11.0,28.1,679.0,11.5,23.3,26.4
+62.6,23.9,24.8,35.5,8.28,9.82,27.1,441.0,9.73,27.4,53.8
+53.8,15.0,12.9,67.9,7.17,22.3,38.5,292.0,1.47,9.39,71.0
+17.5,15.5,25.9,26.4,14.6,15.4,36.5,217.0,35.5,77.0,20.0
+53.3,24.1,7.57,86.6,20.0,23.7,45.7,1027.0,10.7,20.7,10.2
+33.1,17.0,9.82,26.7,44.1,15.8,25.3,583.0,17.8,39.6,21.5
+71.7,25.9,24.8,104.0,37.5,20.5,35.5,308.0,23.3,46.1,31.6
+29.4,16.7,18.9,95.6,34.6,13.6,22.5,322.0,24.1,34.3,12.9
+62.1,24.4,8.43,7.5,15.5,8.43,21.3,429.0,24.6,37.5,24.1
+48.7,20.7,15.7,77.7,23.5,12.3,36.8,679.0,1.0,85.1,9.47
+50.9,18.4,49.6,52.8,23.5,8.9,18.1,491.0,18.4,39.2,12.5
+13.0,4.37,11.9,41.0,17.9,7.23,31.1,1486.0,18.8,46.1,20.0
+50.5,25.7,24.1,17.6,15.5,9.65,20.5,418.0,4.18,40.7,68.5
+38.5,15.8,15.3,47.8,61.5,20.2,25.5,274.0,10.0,32.8,14.2
+42.2,44.1,7.99,85.8,20.0,28.9,54.7,441.0,24.4,34.6,8.82
+104.0,32.8,30.5,97.3,25.9,21.5,35.5,349.0,15.3,27.1,15.1
+110.0,53.8,25.0,85.1,31.3,27.1,42.2,267.0,4.61,47.0,33.7
+34.0,26.9,17.8,80.6,18.6,24.6,31.9,269.0,18.6,40.7,14.6
+91.4,39.2,15.0,16.0,38.5,6.79,21.1,466.0,22.9,36.5,17.0
+35.5,37.5,4.03,21.9,13.7,4.87,17.3,523.0,3.55,16.5,69.8
+55.2,14.1,28.4,115.0,37.5,33.1,76.4,1346.0,14.5,26.9,9.22
+37.5,16.4,18.6,41.0,5.19,2571.0,3555.0,4491.0,14.6,36.2,24.4
+42.2,22.9,26.7,28.6,4.78,16.4,25.9,392.0,28.9,38.5,21.1
+49.1,35.2,24.6,115.0,10.8,42.2,71.0,704.0,2.41,19.1,105.0
+67.9,25.9,17.6,16.0,19.3,9.47,32.2,704.0,30.5,55.7,40.0
+59.4,39.6,18.9,14.1,16.0,7.3,23.3,168.0,31.3,50.5,20.2
+34.3,21.9,25.5,64.9,27.4,10.5,31.6,300.0,8.06,21.3,5.99
+164.0,41.0,70.4,193.0,65.5,41.4,49.6,331.0,24.4,41.0,12.3
+36.5,8.82,24.1,12.9,4.53,16.4,26.4,155.0,25.9,40.7,19.1
+48.7,32.8,1.0,118.0,10.3,1.54,14.3,610.0,2.69,35.5,58.8
+76.4,32.2,22.5,89.0,16.1,11.4,22.5,478.0,10.7,20.4,3.49
+25.7,20.5,28.4,85.8,26.4,47.0,86.6,470.0,21.9,36.8,14.5
+12.0,13.7,19.5,15.7,13.2,65.5,111.0,2091.0,1.0,98.2,4.74
+112.0,18.8,19.1,41.0,6.38,10.9,30.0,441.0,16.5,27.9,15.0
+82.0,55.7,26.9,96.5,13.3,5.42,12.5,449.0,5.99,15.8,1.0
+47.0,18.1,16.3,26.4,8.98,19.3,36.2,528.0,30.5,40.7,10.9
+59.9,21.7,26.2,79.1,20.5,19.6,31.1,250.0,20.7,26.4,12.4
+31.1,12.2,3.82,25.9,33.1,6.73,9.56,343.0,39.6,80.6,39.2
+37.5,20.0,3.89,7.57,14.3,20.9,39.2,302.0,10.8,28.1,7.57
+55.7,16.8,49.6,37.2,18.3,16.0,24.6,297.0,19.1,33.1,31.1
+8.43,17.8,27.9,103.0,35.5,8.51,19.6,289.0,11.1,28.6,16.3
+59.4,18.8,13.0,33.4,44.5,24.6,55.7,1512.0,34.3,76.4,34.0
+69.8,30.5,33.1,117.0,55.7,10.6,28.1,806.0,2.5,23.5,57.8
+40.3,15.5,15.0,63.8,29.4,26.4,43.7,649.0,11.2,26.2,10.4
+38.9,9.82,32.8,47.4,66.1,14.6,28.9,300.0,11.3,20.9,4.03
+31.3,23.5,31.3,155.0,41.4,6.49,14.2,449.0,15.4,25.9,16.1
+72.3,17.2,24.4,24.8,17.6,7.17,37.5,63.2,2.71,21.1,97.3
+48.3,15.5,16.8,167.0,36.2,11.5,18.6,414.0,12.4,14.9,13.8
+18.6,10.3,63.2,51.4,24.8,7.84,13.9,505.0,5.78,13.9,71.7
+54.2,13.7,20.0,14.2,25.9,5.28,14.5,34.0,10.2,25.5,9.06
+33.4,13.6,107.0,176.0,59.9,26.4,34.0,284.0,1.37,18.9,63.2
+37.2,16.4,6.1,7.99,12.6,26.4,59.4,1208.0,14.5,22.1,2.27
+43.3,16.4,17.6,24.6,7.3,22.5,25.0,319.0,4.1,24.1,5.33
+64.9,32.2,7.99,34.3,3.79,3.65,12.2,119.0,21.1,36.8,22.9
+78.4,38.2,11.7,149.0,21.9,17.5,32.5,286.0,24.4,45.7,34.6
+38.2,13.5,18.6,30.2,12.7,10.8,20.5,375.0,4.57,40.7,79.1
+20.5,15.0,13.9,135.0,34.9,2.71,27.6,638.0,18.6,38.2,13.9
+54.2,46.1,24.6,19.6,22.1,18.6,37.5,346.0,24.1,42.6,32.5
+45.3,18.8,16.4,30.8,4.37,18.3,32.2,316.0,8.2,23.3,24.6
+41.0,21.3,16.1,20.4,10.1,71.7,132.0,599.0,37.9,54.7,22.3
+46.1,27.9,13.9,17.0,15.5,17.5,39.6,311.0,8.66,24.4,1.64
+22.3,20.9,6.61,33.1,9.56,6.61,14.9,505.0,12.7,29.4,12.2
+14.2,12.3,18.1,73.7,28.4,6.61,13.6,322.0,2.79,8.82,39.2
+47.8,30.2,14.6,83.5,58.8,9.22,39.6,737.0,28.6,42.2,22.1
+33.7,11.1,23.9,17.8,8.13,9.65,21.5,519.0,43.7,89.0,22.9
+72.3,26.2,4.03,19.5,46.1,4.57,17.2,655.0,12.6,27.9,18.4
+50.9,22.7,17.5,118.0,24.4,21.7,32.2,319.0,7.43,24.4,66.7
+126.0,58.8,167.0,331.0,118.0,9.22,22.5,183.0,4.49,25.9,95.6
+35.2,17.2,26.7,59.4,13.2,4.83,43.7,777.0,34.3,45.3,16.3
+26.4,16.0,17.5,18.4,11.7,8.43,17.3,441.0,8.43,25.7,107.0
+69.8,44.5,16.4,188.0,34.9,42.9,66.7,1114.0,19.1,48.3,25.3
+24.1,17.2,17.6,88.2,15.0,12.6,29.4,284.0,18.3,38.9,12.7
+4.87,14.5,10.8,195.0,38.9,20.5,39.6,176.0,11.0,22.5,5.88
+56.7,24.1,8.35,20.5,31.6,7.5,21.9,461.0,4.29,13.2,62.1
+15.4,26.4,16.4,55.7,15.3,15.4,25.0,457.0,7.7,19.3,14.2
+46.1,23.5,10.4,73.7,12.5,5.42,14.2,519.0,17.0,26.4,18.4
+41.0,18.1,18.3,79.1,15.4,17.5,28.1,365.0,22.7,34.6,11.2
+41.4,30.5,14.2,126.0,27.6,20.4,43.7,300.0,14.2,24.8,22.9
+65.5,33.7,12.2,14.5,10.2,14.2,28.4,229.0,5.42,30.0,94.7
+60.4,34.0,1.0,491.0,42.9,41.4,71.0,638.0,28.4,42.6,17.6
+77.0,20.7,65.5,56.2,33.7,20.9,35.5,414.0,3.02,14.2,62.6
+63.8,23.7,1.0,118.0,10.9,51.4,100.0,1334.0,22.9,54.7,17.8
+104.0,38.2,28.1,27.6,86.6,14.3,23.5,474.0,24.8,27.6,9.73
+70.4,38.9,36.5,62.1,19.3,24.4,42.2,349.0,4.03,10.9,18.8
+77.7,79.1,24.1,21.3,17.0,14.9,25.3,279.0,18.8,42.2,20.7
+78.4,28.6,16.5,150.0,53.3,12.4,26.2,496.0,33.4,74.3,29.7
+19.8,36.5,21.1,28.1,14.3,18.6,39.6,274.0,27.1,38.2,6.61
+56.2,26.9,20.5,21.5,10.7,24.4,37.9,316.0,3.89,14.7,77.0
+322.0,231.0,15.0,441.0,63.2,46.6,72.3,269.0,51.9,92.2,79.1
+46.6,21.3,17.5,56.7,35.9,46.1,75.0,359.0,25.9,39.6,16.4
+33.4,20.5,24.8,18.8,20.0,18.8,45.3,743.0,14.9,26.2,14.2
+93.1,33.4,12.6,77.7,26.7,31.9,40.7,294.0,28.4,66.1,41.8
+111.0,49.1,15.7,11.9,25.3,12.7,25.3,259.0,3.43,12.3,62.6
+33.4,17.0,30.8,47.0,64.4,3.62,18.4,437.0,27.4,35.5,20.0
+33.1,28.9,26.7,22.9,4.66,18.9,41.8,509.0,13.3,21.3,11.4
+50.0,15.7,34.0,59.4,85.8,15.4,29.4,449.0,13.1,34.9,73.0
+52.8,20.7,18.8,20.4,13.2,1.29,8.58,334.0,20.7,38.2,17.6
+90.6,33.4,14.2,21.5,63.2,17.3,34.9,372.0,11.7,17.0,12.7
+86.6,15.8,20.7,104.0,19.5,21.1,31.9,229.0,7.43,38.2,89.0
+40.3,22.5,16.1,20.2,23.7,7.99,20.5,578.0,22.7,43.3,11.4
+18.8,10.3,29.2,262.0,61.5,36.5,52.3,305.0,23.1,36.2,15.1
+13.7,13.9,19.8,20.9,16.1,4.74,15.8,63.2,33.1,36.8,2.13
+60.4,83.5,17.5,16.5,7.91,5.67,18.8,35.9,1.1,19.1,51.9
+70.4,23.7,1.72,400.0,47.8,10.8,29.4,523.0,46.1,90.6,59.4
+27.9,3.62,19.5,25.3,16.4,24.1,39.6,334.0,6.92,15.7,127.0
+47.8,31.3,15.0,106.0,30.5,23.1,29.2,253.0,1.65,28.6,55.2
+29.4,25.9,26.4,35.5,6.15,21.3,41.4,626.0,23.3,52.8,29.2
+86.6,24.4,18.6,17.8,12.6,91.4,173.0,858.0,9.73,20.0,16.7
+126.0,105.0,23.5,64.4,36.2,7.1,18.4,422.0,16.8,25.7,18.4
+54.2,26.9,15.4,13.5,3.11,18.4,35.5,319.0,10.6,23.3,15.1
+34.6,13.8,9.56,200.0,25.3,8.28,17.0,542.0,9.31,10.6,34.0
+62.1,22.3,16.0,24.1,22.1,11.2,38.5,649.0,8.74,19.3,17.0
+60.4,22.1,27.6,21.9,10.1,5.47,20.2,939.0,18.4,48.7,168.0
+84.3,23.1,18.4,61.0,21.3,6.79,32.2,723.0,9.82,28.4,14.1
+43.3,22.1,10.8,106.0,16.1,7.04,13.2,757.0,5.05,10.7,41.4
+66.1,28.4,30.8,198.0,30.0,10.1,27.6,426.0,18.1,31.1,10.6
+25.5,13.2,22.3,12.7,32.5,7.91,31.3,385.0,15.5,30.0,84.3
+32.8,12.6,12.3,17.8,48.3,28.9,51.4,799.0,10.6,17.3,7.5
+19.5,49.6,6.1,16.1,28.1,17.3,31.6,649.0,20.9,44.9,16.8
+46.6,22.1,17.6,27.1,15.4,62.6,99.1,2072.0,19.3,38.2,25.3
+41.4,11.7,89.0,207.0,52.8,24.8,43.3,410.0,1.76,28.6,82.8
+42.2,27.6,21.5,67.9,12.3,8.28,15.8,562.0,21.9,29.7,8.28
+62.1,21.7,9.56,6.49,34.3,15.3,23.1,319.0,11.9,35.5,50.9
+103.0,32.2,10.2,13.2,50.9,5.28,5.62,239.0,14.5,22.9,5.23
+77.7,23.7,24.8,60.4,44.5,21.5,25.0,289.0,32.2,83.5,27.1
+46.6,15.0,8.51,120.0,22.3,6.1,20.0,478.0,20.9,36.8,9.65
+36.5,22.3,17.5,142.0,9.06,16.1,22.1,661.0,6.55,27.6,20.2
+47.8,31.9,34.0,426.0,41.0,2.07,3.79,27.1,13.9,26.9,74.3
+79.1,62.6,19.5,19.3,13.8,9.39,32.5,483.0,9.82,24.6,54.2
+17.0,10.1,41.4,284.0,49.1,23.3,33.7,621.0,12.5,25.5,77.7
+41.4,28.9,13.8,81.3,11.5,28.6,44.5,379.0,8.82,26.7,52.8
+29.2,10.7,12.5,15.4,15.8,14.2,29.2,626.0,6.73,54.2,6.38
+61.0,26.7,9.82,8.98,9.39,24.8,34.6,500.0,5.88,12.9,31.9
+33.1,32.8,87.4,403.0,64.4,7.1,14.1,1252.0,6.98,23.3,14.9
+106.0,102.0,69.8,359.0,68.5,10.9,25.5,828.0,4.78,15.1,5.78
+33.7,5.62,26.2,168.0,22.9,20.0,24.4,414.0,9.22,28.6,31.6
+52.8,26.9,25.5,106.0,19.8,7.43,67.3,352.0,8.06,25.7,40.0
+22.3,26.7,44.1,153.0,42.6,12.6,22.9,939.0,13.2,20.4,70.4
+41.4,29.4,13.9,23.9,1.79,9.91,23.9,1286.0,20.5,61.5,138.0
+76.4,50.9,20.5,22.9,3.59,2.33,4.74,50.9,15.8,29.7,82.0
+92.2,92.2,27.6,39.6,2.37,34.6,62.1,820.0,4.29,14.9,37.9
+73.7,41.0,75.0,217.0,58.3,21.7,41.8,1894.0,8.35,16.1,38.5
+49.6,30.8,51.9,276.0,51.4,5.52,11.3,737.0,4.41,10.7,10.7
+172.0,153.0,43.7,233.0,16.1,20.2,35.2,704.0,7.3,18.6,36.5
+50.0,32.2,97.3,392.0,89.0,13.2,20.7,673.0,10.2,22.9,30.8
+47.0,42.2,25.3,16.0,14.1,6.67,29.7,325.0,6.85,36.5,24.8
+42.9,35.5,22.5,24.6,15.0,14.6,32.2,661.0,28.1,76.4,117.0
+106.0,71.7,28.9,157.0,29.2,11.4,23.9,542.0,5.23,23.7,58.8
+57.3,38.2,27.1,26.9,10.9,9.14,19.3,207.0,13.6,35.5,44.5
+22.9,25.3,14.5,124.0,21.9,72.3,133.0,2548.0,5.05,6.15,25.9
+41.4,22.9,28.9,22.5,7.57,9.65,50.5,237.0,19.3,45.7,105.0
+48.3,18.4,13.9,132.0,12.5,12.5,33.1,882.0,49.1,107.0,211.0
+85.8,56.2,65.5,72.3,17.9,21.9,32.8,737.0,18.3,14.6,23.3
+73.0,54.7,20.0,151.0,30.5,28.1,38.5,723.0,16.5,32.2,33.4
+28.6,33.7,13.9,204.0,27.4,22.5,37.5,679.0,3.92,17.3,36.8
+86.6,79.9,16.0,136.0,13.8,18.4,28.9,626.0,10.0,18.3,23.3
+113.0,88.2,47.8,93.9,43.7,20.7,35.2,491.0,10.3,22.3,35.5
+28.9,21.1,17.6,19.1,6.49,9.56,20.9,973.0,2.71,20.7,3.13
+129.0,75.7,13.7,125.0,17.9,6.49,15.8,334.0,14.2,53.8,27.4
+26.4,29.4,17.6,81.3,16.7,17.8,36.5,1554.0,15.1,30.2,56.2
+41.4,23.9,44.9,426.0,49.1,19.1,34.0,956.0,2.0,75.0,11.9
+41.0,25.9,62.1,219.0,38.2,6.73,16.3,334.0,5.47,19.5,18.4
+29.7,30.0,17.3,80.6,9.65,11.1,24.4,457.0,18.8,47.4,73.0
+38.5,33.7,37.2,382.0,20.7,18.1,27.6,649.0,11.3,16.7,32.8
+35.9,26.7,18.8,41.8,11.0,98.2,231.0,1794.0,23.3,56.7,109.0
+39.2,23.1,12.0,160.0,23.1,11.3,21.9,1263.0,5.47,17.9,11.5
+48.7,28.6,62.1,302.0,94.7,35.5,60.4,717.0,11.2,34.3,44.9
+69.2,43.3,25.3,22.3,1.93,21.7,42.9,791.0,9.31,24.1,29.7
+147.0,87.4,26.9,20.4,20.7,32.8,47.4,777.0,20.0,56.2,103.0
+89.8,62.1,23.1,30.8,4.57,8.9,31.1,583.0,59.4,126.0,121.0
+39.6,36.8,29.4,40.0,12.6,9.22,10.2,231.0,8.82,26.2,37.5
+34.9,23.1,12.6,117.0,13.9,14.1,17.0,509.0,9.39,40.0,43.7
+142.0,94.7,28.9,13.8,5.67,11.3,24.6,644.0,8.28,6.55,7.7
+33.7,33.4,14.2,181.0,11.2,12.1,24.8,483.0,10.5,30.8,46.1
+25.7,35.2,46.1,92.2,20.0,33.4,50.9,599.0,3.75,48.7,50.0
+217.0,132.0,23.1,132.0,16.5,18.4,37.2,1155.0,7.3,17.5,22.7
+38.2,24.1,57.3,365.0,56.2,40.7,79.9,1230.0,33.1,77.7,168.0
+71.7,40.0,27.1,47.0,219.0,14.5,25.3,939.0,12.7,23.9,63.2
+155.0,106.0,96.5,426.0,58.8,24.4,44.1,604.0,33.7,66.7,66.1
+34.3,25.5,18.4,24.1,7.5,3.46,13.0,583.0,10.6,17.5,8.74
+121.0,84.3,27.1,21.9,5.33,8.82,30.5,717.0,4.83,18.9,31.6
+85.8,52.3,20.2,38.5,16.1,5.94,27.4,241.0,9.91,21.9,40.0
+157.0,97.3,28.4,25.5,6.04,13.0,21.9,414.0,7.77,19.5,41.0
+113.0,66.7,19.8,44.9,12.3,17.9,25.9,679.0,7.04,36.8,18.8
+41.0,29.4,15.4,15.7,15.0,6.55,9.39,1310.0,12.1,18.9,59.4
+146.0,97.3,49.1,69.2,16.7,15.4,29.2,547.0,5.94,9.06,20.4
+34.6,20.5,18.8,20.9,4.07,30.5,120.0,1382.0,10.7,19.3,37.2
+99.1,98.2,34.3,193.0,10.6,25.3,41.8,820.0,12.0,28.9,43.3
+46.6,24.4,33.4,13.7,31.1,21.5,36.8,890.0,10.0,27.4,2.23
+107.0,76.4,18.3,135.0,13.8,14.7,27.9,1018.0,39.2,110.0,126.0
+67.3,36.8,30.2,138.0,11.7,12.6,20.2,610.0,9.06,20.9,32.2
+97.3,73.7,55.2,379.0,82.8,16.0,28.4,764.0,31.9,79.9,75.0
+51.9,21.5,11.1,188.0,13.6,5.62,25.5,207.0,29.7,76.4,132.0
+39.2,29.2,40.3,302.0,72.3,7.43,18.8,698.0,1.53,1.45,7.64
+38.2,22.3,26.4,38.5,16.7,1.75,10.9,588.0,7.37,20.0,21.3
+103.0,78.4,20.5,16.8,1.45,15.7,33.7,679.0,30.5,64.9,69.8
+90.6,63.8,17.6,26.9,6.85,10.6,28.9,1104.0,32.8,88.2,151.0
+45.3,32.8,19.3,120.0,20.5,39.2,58.3,655.0,10.3,22.3,29.4
+14.9,21.3,22.3,16.5,10.6,5.99,3.43,161.0,13.2,26.7,16.7
+151.0,121.0,29.2,129.0,30.0,18.4,32.8,982.0,7.5,36.8,45.7
+44.1,33.7,41.0,325.0,31.6,10.6,36.8,470.0,1.03,59.4,6.38
+39.6,28.6,43.3,71.7,7.77,44.5,67.3,661.0,10.3,21.7,21.5
+96.5,69.8,32.5,64.9,8.2,13.2,25.3,770.0,56.2,141.0,205.0
+41.4,24.4,18.6,23.3,6.38,16.1,26.2,906.0,13.6,40.3,42.6
+53.3,34.9,19.3,47.8,10.1,3.49,17.2,173.0,18.9,53.3,55.2
+274.0,172.0,29.7,20.4,12.9,41.0,56.7,533.0,16.4,28.1,44.5
+113.0,36.5,40.0,246.0,40.7,20.9,28.4,379.0,8.06,30.0,25.5
+161.0,112.0,44.1,84.3,28.4,36.8,50.9,583.0,1.36,1.72,11.1
+225.0,163.0,82.8,112.0,23.5,24.4,36.5,717.0,40.7,72.3,202.0
+31.3,24.8,8.43,305.0,14.3,7.43,26.2,346.0,5.05,21.5,18.1
+60.4,42.2,23.9,31.3,1.96,9.22,15.0,1046.0,9.06,21.7,42.6
+176.0,97.3,24.4,145.0,15.7,14.7,21.3,820.0,7.77,19.6,20.9
+30.5,32.8,10.2,136.0,5.94,30.5,55.7,791.0,14.1,20.5,48.7
+57.8,31.6,11.5,157.0,36.5,11.2,27.1,626.0,10.3,32.2,29.4
+308.0,200.0,16.0,93.9,29.7,17.8,31.9,655.0,11.2,17.5,7.1
+31.3,40.3,20.7,163.0,17.6,11.5,31.3,866.0,36.2,76.4,79.1
+27.1,21.3,93.9,500.0,63.2,35.5,57.8,542.0,10.6,27.6,3.92
+47.4,21.1,44.1,179.0,23.5,11.2,20.2,478.0,10.3,37.5,34.6
+51.9,27.1,15.0,167.0,1.84,13.9,16.4,621.0,18.6,46.6,33.1
+48.3,20.9,20.5,64.9,13.7,29.7,47.0,1065.0,5.73,3.02,15.7
+112.0,83.5,21.3,23.3,9.31,33.7,51.4,835.0,7.91,23.7,18.4
+57.8,40.7,16.8,362.0,22.1,11.2,27.9,799.0,9.22,22.9,55.2
+38.9,28.1,35.5,24.4,1.0,12.5,15.1,1334.0,13.6,22.7,30.2
+117.0,78.4,19.3,17.9,6.85,33.4,48.3,947.0,12.5,17.5,1.0
+68.5,107.0,18.3,31.1,19.5,11.1,22.9,599.0,12.2,27.1,14.3
+36.8,24.8,21.7,98.2,18.3,7.91,19.8,403.0,8.74,25.9,38.5
+38.2,29.2,21.1,129.0,24.6,12.4,30.0,723.0,6.67,10.0,21.5
+47.0,26.2,15.4,84.3,18.3,9.06,27.1,965.0,11.0,18.4,26.7
+253.0,157.0,25.7,121.0,18.6,25.9,42.2,965.0,11.9,17.9,36.5
+96.5,46.1,13.6,136.0,3.43,16.0,32.5,505.0,13.5,20.5,46.1
+191.0,115.0,13.1,12.5,3.31,21.7,25.7,514.0,11.4,12.9,17.0
+59.9,29.2,12.2,76.4,21.9,18.6,24.8,583.0,9.73,15.1,8.35
+61.5,37.2,158.0,557.0,110.0,2.64,12.9,461.0,12.1,26.7,27.6
+34.9,25.0,34.0,26.7,2.71,1.45,6.1,34.3,27.1,61.0,90.6
+34.6,34.6,13.2,87.4,16.8,12.5,23.9,407.0,7.23,27.6,42.2
+170.0,123.0,16.5,8.35,1.73,20.2,29.2,757.0,32.8,78.4,186.0
+21.3,15.3,69.8,239.0,51.9,58.8,70.4,578.0,16.3,27.1,42.2
+44.9,28.1,21.1,142.0,13.1,16.8,20.7,692.0,17.0,38.5,41.0
+33.7,20.4,25.5,24.6,6.73,11.9,58.3,325.0,13.9,14.9,32.5
+200.0,125.0,16.5,308.0,15.1,37.2,38.2,777.0,24.8,43.3,100.0
+35.5,23.5,23.7,25.9,12.3,16.5,25.0,874.0,66.1,183.0,279.0
+26.4,23.3,120.0,514.0,117.0,23.5,43.3,799.0,10.8,30.0,58.3
+41.0,41.0,18.1,167.0,19.8,4.1,15.4,615.0,13.8,22.5,20.5
+157.0,79.1,20.4,33.7,25.7,4.37,19.3,858.0,49.1,106.0,155.0
+83.5,54.2,60.4,48.3,14.9,31.3,51.9,621.0,14.1,16.4,25.3
+109.0,143.0,22.1,108.0,22.5,15.3,35.5,649.0,20.9,58.8,53.3
+145.0,93.9,34.3,474.0,62.1,15.7,21.5,429.0,10.8,22.5,21.9
+41.0,11.8,15.4,75.0,13.9,25.0,30.8,626.0,8.06,26.4,15.7
+30.2,26.7,32.8,191.0,28.1,18.3,19.6,723.0,54.7,139.0,191.0
+40.7,13.1,25.3,22.7,1.17,11.4,25.7,685.0,14.6,24.6,20.7
+38.5,20.2,50.0,368.0,60.4,8.74,28.1,483.0,11.4,26.4,40.0
+37.2,56.7,18.4,21.3,10.8,14.1,31.1,621.0,13.1,23.5,36.2
+195.0,106.0,13.9,135.0,3.72,24.1,43.7,414.0,10.8,24.8,38.5
+29.4,31.1,45.7,52.8,8.82,26.7,47.8,523.0,10.0,23.3,29.4
+60.4,48.7,13.6,29.7,2.35,213.0,322.0,1554.0,8.35,20.9,23.7
+60.4,40.7,27.6,22.1,5.0,18.6,41.0,1124.0,7.7,23.3,17.9
+64.9,53.3,71.0,466.0,73.0,7.77,19.8,1114.0,12.4,20.2,12.6
+58.3,31.1,79.9,77.0,8.58,19.6,28.4,638.0,15.3,36.5,50.9
+36.5,25.7,22.5,76.4,13.5,17.0,27.9,730.0,12.2,36.2,30.5
+163.0,117.0,26.9,362.0,53.3,4.83,20.7,157.0,22.3,76.4,85.8
+41.8,23.1,22.1,101.0,26.2,36.5,44.1,750.0,11.4,36.5,33.4
+36.5,22.3,49.6,56.2,10.2,22.9,37.2,704.0,29.7,77.0,153.0
+142.0,85.1,25.3,33.1,26.9,12.0,24.1,939.0,80.6,101.0,12.2
+90.6,61.5,10.0,18.8,21.1,18.6,31.3,931.0,5.09,100.0,1.0
+73.0,46.1,15.5,113.0,8.2,13.3,22.3,621.0,13.5,21.9,30.0
+39.2,19.5,16.4,64.9,9.65,14.6,26.2,750.0,12.0,22.9,25.9
+86.6,55.2,23.3,22.7,4.91,4.87,9.65,136.0,36.5,86.6,118.0
+42.9,25.5,15.7,23.1,3.72,30.2,41.0,730.0,22.1,46.6,7.23
+55.2,42.9,17.5,95.6,6.98,5.62,21.3,610.0,10.2,23.7,26.2
+64.9,41.4,20.7,168.0,22.9,14.6,25.7,661.0,12.6,25.5,42.6
+36.2,18.6,34.9,34.9,11.3,13.2,20.4,791.0,1.11,10.5,18.4
+59.9,35.2,64.9,257.0,42.2,12.6,28.1,730.0,1.86,3.79,4.03
+51.9,30.2,22.3,136.0,16.8,14.1,23.7,835.0,10.7,20.5,13.5
+54.7,49.1,20.9,161.0,12.3,21.9,37.9,1155.0,13.5,32.2,35.5
+44.9,31.3,23.9,30.2,8.58,26.9,71.7,1094.0,10.3,23.1,25.3
+284.0,233.0,50.5,422.0,35.5,1.36,9.82,898.0,34.0,55.2,11.0
+35.5,28.4,13.2,191.0,13.8,9.14,24.1,500.0,12.5,27.9,35.2
+92.2,80.6,15.4,167.0,9.39,2.57,10.7,19.3,13.7,37.5,15.5
+112.0,67.3,17.0,90.6,10.4,39.6,58.3,588.0,8.28,26.2,40.7
+35.5,25.0,46.1,248.0,35.5,9.22,15.5,632.0,10.8,31.9,30.5
+44.9,27.6,18.6,117.0,16.8,12.5,14.6,679.0,6.21,14.9,9.39
+132.0,82.8,16.0,20.9,12.6,1.0,2.17,1.0,17.2,25.9,33.7
+23.9,10.3,18.8,21.3,1.0,4.18,10.9,219.0,8.98,19.6,29.2
+34.6,25.5,14.2,89.0,16.4,25.9,50.0,1298.0,10.8,51.4,7.77
+135.0,73.7,18.9,105.0,6.49,25.5,62.6,1911.0,6.21,17.3,15.5
+31.9,31.1,25.0,16.5,7.57,12.1,19.3,704.0,1.98,64.9,4.49
+30.8,20.2,21.1,23.5,14.5,30.8,55.7,1382.0,51.9,113.0,115.0
+33.7,15.1,49.6,453.0,49.1,27.9,45.3,523.0,49.6,92.2,209.0
+80.6,58.8,28.1,56.7,8.58,9.82,14.6,594.0,9.73,17.0,27.9
+34.9,19.8,14.7,94.7,4.91,51.9,89.0,1981.0,11.0,41.8,41.8
+176.0,91.4,15.7,149.0,12.3,45.7,72.3,1827.0,6.15,13.1,3.89
+15.4,3.02,20.0,17.2,21.7,20.4,31.3,567.0,7.37,23.3,25.0
+142.0,91.4,57.8,102.0,18.9,12.0,13.6,305.0,4.03,10.6,12.9
+41.8,24.1,18.4,18.3,8.66,19.8,38.5,422.0,39.6,83.5,158.0
+26.4,18.3,17.6,44.1,10.4,13.2,20.2,667.0,8.58,20.9,23.3
+72.3,47.4,16.5,79.9,9.22,8.06,24.6,710.0,7.77,25.3,32.2
+32.2,10.8,12.6,27.4,10.6,18.6,40.7,813.0,22.3,32.5,41.4
+225.0,125.0,14.6,11.1,1.54,11.5,31.1,407.0,3.37,66.7,9.22
+40.3,34.9,24.8,27.9,6.61,1.0,1.67,33.4,15.3,42.6,44.5
+122.0,89.8,9.22,173.0,3.72,23.5,28.6,1037.0,10.4,29.4,6.79
+53.3,38.9,18.3,22.1,6.85,35.5,80.6,2308.0,20.0,45.7,66.1
+36.2,23.7,36.8,328.0,51.9,9.22,13.3,679.0,42.2,92.2,122.0
+37.5,22.1,17.3,14.6,12.2,18.3,27.9,583.0,16.7,41.8,59.4
+79.9,66.7,22.1,24.1,3.92,15.5,27.9,542.0,13.1,36.8,33.1
+72.3,39.6,18.6,7.04,14.5,39.6,47.4,389.0,15.4,31.1,33.7
+101.0,67.3,22.3,68.5,5.67,30.8,39.6,594.0,10.4,27.1,13.9
+6.67,7.99,48.3,308.0,48.7,6.98,34.3,470.0,11.5,33.4,28.6
+42.6,25.5,20.2,17.5,10.1,7.17,20.9,474.0,11.4,24.6,23.9
+57.3,26.9,84.3,461.0,75.7,12.2,29.2,567.0,11.7,13.9,23.5
+65.5,28.6,18.1,93.9,7.37,22.7,31.1,562.0,91.4,125.0,15.7
+93.9,50.0,14.6,93.9,14.5,47.0,62.6,685.0,9.65,21.5,29.7
+59.4,36.8,31.6,67.9,47.0,11.3,21.1,698.0,12.9,35.9,40.0
+31.6,22.9,26.4,18.1,7.64,11.5,33.7,632.0,14.2,20.9,26.2
+30.5,21.7,16.0,255.0,6.73,8.51,21.7,414.0,49.6,97.3,193.0
+41.8,26.4,48.3,302.0,40.0,35.9,62.1,1334.0,10.0,32.5,33.1
+178.0,125.0,11.7,2.59,13.9,6.38,16.4,403.0,12.4,44.9,25.3
+57.8,50.0,13.3,145.0,13.9,14.9,10.2,820.0,12.7,16.7,18.8
+18.3,16.4,28.1,43.7,10.3,43.3,63.8,710.0,5.83,21.3,26.2
+131.0,119.0,78.4,250.0,48.7,90.6,126.0,466.0,3.59,7.99,1.08
+54.7,38.9,16.8,21.7,24.1,26.7,43.7,882.0,36.8,58.3,18.8
+67.3,31.3,1.0,7.5,389.0,21.3,25.3,621.0,7.04,22.1,22.1
+28.6,18.1,31.1,36.2,10.9,15.7,36.5,1000.0,3.05,31.3,27.4
+61.5,57.3,33.1,16.4,10.2,11.9,43.3,229.0,5.73,16.0,16.4
+40.3,23.3,31.9,39.2,2.57,6.79,13.7,692.0,11.3,28.1,29.7
+36.2,18.1,46.6,528.0,49.6,16.1,40.3,965.0,14.6,33.7,15.7
+38.9,16.4,24.4,195.0,39.6,11.0,20.4,496.0,9.56,30.8,17.5
+41.0,30.8,20.9,25.0,1.0,12.4,20.2,685.0,10.8,35.2,30.8
+91.4,53.8,17.5,18.8,5.57,13.0,22.3,496.0,12.9,27.9,4.14
+188.0,117.0,20.5,16.3,1.0,4.91,5.47,973.0,3.31,10.3,11.1
+184.0,85.8,8.98,213.0,6.79,20.2,24.1,730.0,13.0,33.4,28.4
+37.5,17.6,6.61,181.0,13.9,23.9,39.2,644.0,13.2,33.7,56.2
+50.0,33.1,19.6,22.9,5.88,5.73,20.0,698.0,6.61,17.9,30.8
+139.0,82.0,20.7,24.8,4.66,36.5,41.4,483.0,4.49,59.4,3.82
+101.0,57.8,17.9,62.1,11.7,20.7,42.2,470.0,10.6,37.5,21.7
+53.3,40.3,14.3,106.0,18.3,32.5,62.6,898.0,31.3,60.4,88.2
+58.3,44.5,21.9,17.3,5.67,37.9,89.0,1946.0,12.1,31.1,37.5
+175.0,126.0,14.1,137.0,5.09,102.0,160.0,2788.0,15.4,30.0,50.0
+34.6,25.5,32.2,35.9,10.9,2.29,7.37,125.0,13.9,25.7,29.4
+11.8,17.0,49.1,410.0,54.2,15.7,36.2,1219.0,10.1,22.1,19.6
+38.9,32.8,129.0,308.0,73.0,2.48,12.6,906.0,12.6,29.4,16.7
+34.3,26.9,54.2,79.1,32.8,9.14,13.5,410.0,14.1,30.5,20.9
+38.9,5.38,22.3,87.4,22.1,20.5,49.6,1046.0,5.38,5.42,4.87
+37.5,15.0,40.3,44.5,14.5,9.22,14.9,610.0,1.22,5.52,11.4
+33.7,21.5,18.9,217.0,9.22,14.1,18.6,542.0,10.4,19.3,40.7
+22.1,23.3,30.0,22.7,6.44,19.6,35.5,939.0,15.1,26.9,23.9
+35.9,25.0,93.9,474.0,77.7,97.3,158.0,1747.0,1.12,3.43,22.9
+37.9,18.1,14.9,153.0,5.28,10.2,26.7,389.0,48.3,118.0,138.0
+21.1,15.0,24.8,25.7,5.38,9.65,36.2,737.0,11.2,29.7,24.4
+31.1,24.4,19.5,248.0,29.4,21.7,34.6,505.0,13.6,22.9,19.3
+57.8,42.9,25.7,35.9,2.86,8.28,11.3,259.0,5.42,55.2,5.57
+56.2,29.2,47.4,262.0,36.5,1.51,13.5,667.0,8.58,11.9,4.1
+7.7,10.9,13.1,89.8,11.4,9.31,20.0,410.0,9.31,21.5,25.0
+112.0,76.4,44.1,487.0,67.3,15.1,21.1,505.0,8.82,13.9,7.99
+31.1,26.7,33.7,198.0,32.2,8.66,18.3,1197.0,5.33,8.98,9.06
+71.0,42.9,17.9,44.1,8.74,8.35,12.7,1094.0,10.6,44.1,44.5
+52.3,32.8,23.5,217.0,14.6,24.1,35.5,939.0,37.5,79.1,133.0
+149.0,96.5,59.9,302.0,40.0,4.41,16.4,137.0,6.38,20.7,16.5
+65.5,32.8,13.3,122.0,16.7,7.1,13.1,655.0,12.5,22.9,43.3
+44.5,37.2,18.4,250.0,28.1,20.5,21.3,533.0,3.55,16.8,28.1
+126.0,89.0,37.2,300.0,33.7,26.7,41.0,723.0,49.6,99.1,154.0
+59.4,36.8,10.2,157.0,14.6,11.7,24.4,349.0,12.1,20.2,21.7
+32.8,32.5,28.1,235.0,19.8,8.51,18.4,698.0,9.47,30.8,25.5
+22.1,18.8,18.1,27.9,10.6,14.1,23.7,487.0,13.5,36.2,33.1
+30.2,22.9,21.1,175.0,21.1,23.1,76.4,1263.0,7.84,22.3,18.8
+69.8,44.5,17.6,92.2,8.43,9.73,20.2,661.0,40.3,70.4,67.3
+40.7,22.1,35.5,200.0,42.9,7.17,11.0,533.0,13.7,28.4,27.6
+50.5,32.5,22.9,26.7,5.57,3.4,14.5,235.0,5.19,13.7,11.8
+106.0,85.8,19.5,86.6,10.0,49.1,67.9,483.0,7.1,25.5,36.2
+142.0,90.6,17.3,66.1,18.4,15.3,40.3,730.0,5.62,23.1,21.9
+184.0,132.0,21.1,21.1,10.4,5.88,40.7,1252.0,46.1,115.0,145.0
+50.0,31.6,15.5,61.0,11.7,16.3,34.9,874.0,40.7,107.0,106.0
+138.0,109.0,65.5,359.0,60.4,8.2,14.3,533.0,12.4,28.6,8.82
+55.2,32.2,13.6,142.0,10.2,9.47,25.5,346.0,7.7,23.5,28.4
+42.6,18.1,17.0,15.5,1.21,13.9,15.3,487.0,9.73,9.39,12.9
+78.4,74.3,25.9,110.0,42.2,17.2,42.9,626.0,10.4,18.6,35.2
+37.5,25.9,24.1,27.6,3.85,17.0,47.8,692.0,38.5,64.9,57.3
+21.1,6.55,24.6,28.1,3.68,15.5,41.0,882.0,7.7,10.8,14.7
+76.4,43.7,8.82,235.0,22.7,23.1,40.3,583.0,25.5,44.1,51.9
+61.5,64.4,16.1,163.0,2.71,25.5,34.0,487.0,7.7,23.9,29.4
+66.7,44.9,22.9,68.5,25.0,28.4,56.2,453.0,9.31,18.8,24.6
+56.7,25.9,21.3,21.3,16.1,22.1,32.5,922.0,9.06,23.9,27.1
+85.8,21.9,18.6,25.3,4.61,13.6,26.7,422.0,11.0,21.5,22.1
+39.6,28.1,20.9,18.8,15.3,24.1,39.2,604.0,13.6,31.3,39.2
+31.1,23.7,20.7,176.0,14.7,5.05,20.7,271.0,13.5,30.8,36.5
+29.4,20.0,16.5,46.1,5.83,14.7,43.3,461.0,28.6,47.4,3.13
+18.4,19.1,44.1,231.0,62.6,59.4,93.1,3619.0,24.4,56.7,77.0
+33.1,14.1,24.8,23.3,4.45,7.91,14.5,1155.0,4.14,12.6,4.29
+52.3,33.1,54.7,334.0,47.0,87.4,146.0,2864.0,16.7,25.5,33.1
+39.6,25.3,12.1,88.2,3.08,26.2,48.7,1395.0,31.1,60.4,74.3
+39.6,20.2,93.1,505.0,58.8,5.52,30.8,1843.0,7.1,18.4,18.8
+35.9,13.5,12.0,186.0,21.5,15.8,35.5,991.0,13.1,16.4,42.9
+58.8,40.0,22.5,63.8,23.1,11.3,15.0,528.0,67.9,97.3,3.89
+95.6,59.4,49.1,437.0,50.0,13.6,24.6,588.0,49.1,115.0,164.0
+32.2,25.9,28.6,204.0,20.5,45.3,74.3,2148.0,6.38,26.4,27.1
+33.1,21.7,13.8,103.0,10.5,12.9,22.7,509.0,9.14,22.7,29.7
+36.8,83.5,24.6,115.0,12.1,37.2,47.0,813.0,12.6,21.5,29.7
+47.0,26.9,27.4,19.5,8.35,7.37,18.4,649.0,11.3,30.8,36.8
+34.6,30.0,18.3,109.0,9.82,112.0,189.0,2525.0,10.3,20.9,22.9
+38.5,23.5,5.42,4.83,12.6,37.5,55.2,599.0,36.8,81.3,110.0
+204.0,130.0,23.7,21.5,4.0,15.5,34.6,737.0,12.9,15.1,32.5
+2.37,2.29,78.4,379.0,57.8,9.65,29.7,478.0,15.5,17.8,44.5
+26.2,39.2,24.8,44.9,16.3,50.0,90.6,1407.0,31.9,62.1,74.3
+27.9,17.9,45.7,141.0,26.2,19.6,34.9,947.0,15.0,22.3,29.2
+96.5,62.6,106.0,359.0,65.5,11.1,24.6,750.0,6.79,40.7,34.9
+191.0,121.0,15.8,106.0,11.0,12.9,22.5,638.0,8.98,18.9,21.5
+31.3,17.8,24.1,15.4,10.1,22.5,39.2,552.0,31.1,97.3,207.0
+43.7,25.7,9.91,113.0,9.06,40.0,58.8,483.0,17.8,47.0,88.2
+35.9,25.7,49.6,362.0,46.1,35.9,55.7,1877.0,9.39,21.9,27.6
+36.5,28.4,16.1,106.0,4.41,11.7,28.6,604.0,76.4,163.0,198.0
+163.0,94.7,17.5,23.9,6.92,13.8,46.1,400.0,8.13,11.8,17.3
+25.5,22.7,44.9,248.0,223.0,44.1,89.0,3078.0,35.5,70.4,103.0
+34.9,24.6,29.4,41.4,13.8,20.7,56.7,478.0,8.9,19.1,13.7
+30.2,16.7,18.8,62.1,14.1,12.7,32.2,717.0,4.83,26.2,36.8
+229.0,165.0,21.3,25.5,1.09,59.4,129.0,2436.0,9.91,20.0,15.5
+43.7,27.4,78.4,385.0,72.3,45.7,80.6,1611.0,9.14,16.5,13.8
+133.0,95.6,18.4,57.3,1.88,12.4,35.9,562.0,18.3,41.4,46.1
+23.3,30.2,31.3,202.0,43.3,58.3,104.0,1670.0,19.8,42.6,109.0
+33.4,21.5,23.7,32.2,4.57,11.7,34.6,359.0,14.1,26.9,34.6
+49.1,41.4,17.8,122.0,18.3,10.1,10.2,965.0,13.0,34.0,27.9
+37.5,22.3,24.4,67.3,26.7,9.65,16.5,300.0,8.9,13.5,9.56
+30.0,15.5,15.3,56.2,12.3,37.9,47.8,604.0,6.04,24.1,10.2
+38.5,32.8,11.7,7.5,11.4,61.5,154.0,3078.0,14.1,21.5,5.62
+36.8,25.3,41.0,146.0,54.7,10.2,25.7,1382.0,14.1,34.6,27.6
+31.9,15.3,19.5,15.8,5.09,16.5,42.2,1700.0,63.2,98.2,34.9
+189.0,121.0,21.3,27.9,14.6,29.7,44.9,661.0,2.13,67.9,5.88
+28.4,17.3,20.0,101.0,13.7,6.15,8.9,239.0,10.0,20.4,20.9
+170.0,103.0,15.5,32.5,3.02,39.2,59.9,2763.0,5.42,23.1,27.1
+37.9,21.9,52.3,322.0,39.6,22.7,41.0,483.0,8.74,17.8,30.0
+31.9,21.1,25.3,26.9,11.5,2.21,9.56,118.0,9.65,22.3,21.3
+47.8,31.6,24.6,98.2,8.9,42.9,110.0,1512.0,9.22,29.4,49.1
+27.9,20.9,39.2,103.0,44.9,33.1,62.6,764.0,6.73,23.5,25.3
+28.6,15.8,17.9,61.5,11.3,12.4,17.5,704.0,3.13,20.2,20.5
+132.0,130.0,56.7,237.0,52.8,23.1,36.2,483.0,9.22,27.4,35.2
+33.4,23.5,111.0,433.0,136.0,7.99,16.7,410.0,56.7,118.0,142.0
+85.8,47.0,25.7,89.0,8.9,67.9,108.0,1486.0,45.7,123.0,84.3
+39.6,27.9,14.2,80.6,10.7,17.9,30.0,547.0,31.3,66.7,112.0
+35.2,22.9,13.9,102.0,20.7,31.1,64.4,1715.0,8.66,30.5,22.5
+76.4,47.0,24.4,19.1,5.23,11.9,27.6,538.0,11.7,23.5,20.7
+34.3,38.9,22.1,30.0,7.17,10.6,19.1,538.0,17.0,46.1,59.4
+50.9,16.8,16.3,331.0,52.3,15.5,32.8,750.0,10.0,18.3,25.9
+35.9,22.5,16.5,15.0,7.1,5.14,10.3,661.0,20.9,51.4,72.3
+32.2,24.1,21.5,13.9,5.78,46.1,85.8,1322.0,2.37,40.3,26.7
+36.5,36.8,32.5,36.8,11.4,25.3,32.2,509.0,4.96,20.0,25.3
+57.8,37.2,5.38,12.1,4.7,16.7,38.2,991.0,11.9,31.3,31.1
+49.6,35.5,16.8,200.0,42.6,34.0,51.4,552.0,16.1,22.3,34.3
+27.9,17.6,16.8,105.0,22.7,13.0,32.5,2035.0,10.6,29.4,28.4
+53.8,27.1,30.2,13.5,1.3,93.9,170.0,2308.0,13.5,26.4,46.6
+30.2,20.7,17.2,44.5,2.04,25.0,43.7,835.0,10.6,23.5,8.66
+35.5,22.1,23.5,131.0,7.1,16.4,32.2,1670.0,12.1,30.5,44.1
+40.7,25.0,14.3,167.0,26.2,10.5,17.8,914.0,8.51,30.2,30.8
+43.7,22.1,21.1,125.0,16.1,16.3,16.4,514.0,18.1,32.5,44.5
+127.0,132.0,16.7,233.0,30.8,14.5,39.2,644.0,3.96,20.5,8.9
+89.8,49.6,12.3,163.0,15.8,9.73,18.1,784.0,20.9,69.8,68.5
+23.1,21.7,25.3,17.3,11.3,14.3,30.0,835.0,9.82,25.3,14.2
+36.8,17.6,9.47,161.0,25.3,52.8,92.2,2072.0,8.13,10.3,16.1
+30.5,26.7,36.5,34.9,13.1,50.0,105.0,2308.0,41.0,89.0,112.0
+59.9,46.1,25.0,35.5,8.74,43.7,91.4,1778.0,41.4,97.3,145.0
+23.7,40.0,10.2,122.0,1.76,13.0,21.7,858.0,34.6,77.7,98.2
+49.1,32.2,17.0,157.0,20.5,6.26,12.7,757.0,11.5,17.5,20.7
+35.9,25.7,21.7,28.4,13.1,16.3,28.6,692.0,56.7,85.1,27.1
+28.4,21.7,19.3,168.0,17.2,26.2,95.6,2969.0,11.2,38.5,58.8
+89.0,51.9,17.5,21.1,7.5,5.78,10.6,973.0,15.7,79.9,27.4
+27.1,30.8,23.1,16.5,4.33,13.3,39.6,982.0,12.5,25.7,42.6
+172.0,110.0,11.0,221.0,23.9,63.8,118.0,3134.0,9.65,19.8,26.4
+68.5,47.0,30.0,28.1,11.8,20.2,28.1,562.0,11.1,35.9,1.0
+22.1,19.8,19.8,157.0,13.0,28.1,34.6,538.0,7.64,25.0,29.2
+47.4,36.5,9.22,12.9,2.13,19.8,38.9,874.0,9.31,13.8,15.7
+57.3,46.6,13.3,75.7,10.0,10.1,28.1,449.0,10.8,20.0,17.5
+36.5,16.4,18.6,26.2,5.94,13.6,21.9,1762.0,15.1,37.5,11.0
+34.0,12.0,33.4,255.0,35.9,17.6,32.8,644.0,7.64,46.6,15.7
+36.8,13.3,14.6,24.8,9.73,70.4,118.0,1009.0,5.99,7.91,10.5
+42.6,26.2,30.0,21.1,7.3,9.91,35.9,403.0,8.28,24.1,22.9
+28.1,16.7,35.2,49.1,18.3,23.7,36.8,514.0,10.3,38.5,60.4
+142.0,76.4,18.6,22.7,2.84,32.5,55.2,890.0,20.2,41.0,43.7
+36.2,34.0,36.8,42.9,24.1,36.8,45.7,638.0,6.79,19.5,26.9
+33.1,29.4,22.1,42.2,2.84,23.1,33.1,1055.0,9.65,47.0,42.2
+215.0,109.0,13.9,42.9,4.18,29.4,60.4,3191.0,8.98,20.5,31.6
+115.0,80.6,22.3,27.4,2.25,20.7,31.6,567.0,10.4,25.3,29.7
+97.3,63.2,21.5,21.1,2.76,27.1,47.0,784.0,7.99,46.1,18.9
+129.0,93.9,23.7,16.0,9.22,7.91,38.2,403.0,1.91,6.04,1.13
+67.3,41.4,40.7,66.1,20.5,82.0,131.0,2017.0,10.8,16.3,27.6
+46.6,29.2,17.5,58.3,14.9,19.8,37.9,947.0,5.83,17.6,25.7
+58.3,40.7,16.5,150.0,12.5,14.9,35.2,914.0,3.85,13.9,28.4
+52.8,43.3,30.8,21.9,2.71,37.9,56.7,1554.0,18.4,32.8,35.2
+37.5,29.4,27.6,45.3,23.5,43.3,60.4,692.0,7.57,24.8,37.2
+165.0,98.2,23.7,17.3,13.2,13.1,23.9,737.0,13.2,21.5,23.1
+80.6,49.1,17.8,235.0,29.7,4.83,18.9,322.0,14.7,24.1,52.3
+36.2,18.6,19.1,14.1,16.0,19.1,30.5,661.0,13.3,19.1,37.2
+22.9,26.2,20.0,207.0,17.2,19.6,35.5,791.0,12.1,16.3,36.8
+35.2,34.9,20.7,204.0,18.6,18.3,29.4,588.0,13.3,22.3,36.8
+34.9,22.1,26.7,43.3,6.67,27.4,26.7,491.0,5.09,5.73,22.1
+178.0,100.0,27.4,300.0,20.5,34.3,67.3,1794.0,8.66,8.51,16.4
+50.5,30.2,19.3,11.0,6.1,17.3,28.9,632.0,23.7,63.8,59.9
+64.9,51.9,17.0,135.0,16.7,15.0,23.9,764.0,7.57,17.0,26.9
+54.7,37.2,20.0,16.1,9.73,35.2,53.8,552.0,14.5,31.1,5.14
+30.5,21.7,21.5,95.6,4.33,16.7,28.1,947.0,6.55,22.9,20.4
+51.4,32.8,32.8,23.9,21.1,13.6,23.7,843.0,9.56,21.7,21.9
+69.2,40.3,20.2,62.6,19.5,2.15,7.37,21.3,14.6,42.2,38.2
+36.8,22.7,28.1,23.1,4.78,20.7,32.8,433.0,42.2,104.0,95.6
+47.0,37.2,12.6,35.2,3.08,12.1,24.1,673.0,2.29,23.7,17.5
+37.2,29.2,35.5,29.7,19.6,56.7,82.0,1827.0,1.35,10.3,24.4
+50.5,29.2,15.0,143.0,7.91,17.9,32.5,470.0,6.85,24.4,15.7
+15.3,30.5,19.5,154.0,10.6,30.0,47.4,594.0,7.91,36.8,43.3
+38.2,21.9,36.5,382.0,44.5,17.0,39.2,500.0,11.1,24.1,32.5
+64.4,35.9,18.1,20.5,6.49,26.2,60.4,1640.0,20.4,42.6,42.2
+172.0,95.6,15.5,40.7,11.1,3.28,12.3,737.0,8.2,21.5,18.9
+35.5,28.1,17.8,20.5,11.2,50.9,89.0,890.0,6.15,7.23,14.9
+40.3,21.5,51.4,223.0,31.6,15.8,41.4,610.0,6.15,20.2,20.9
+22.9,19.3,13.9,16.7,7.77,111.0,172.0,2054.0,9.31,20.5,22.5
+53.8,49.6,25.5,20.2,6.32,6.15,13.0,939.0,24.6,45.3,68.5
+147.0,89.0,33.7,269.0,23.3,8.98,22.7,1000.0,11.1,20.0,34.9
+95.6,64.9,30.8,198.0,38.2,63.2,127.0,2308.0,14.2,25.5,52.3
+75.7,63.8,55.7,311.0,62.1,37.2,63.8,1685.0,13.0,26.2,38.2
+79.1,52.3,12.9,138.0,12.1,172.0,453.0,4826.0,7.64,28.9,28.4
+42.9,30.8,23.1,18.6,1.86,4.53,17.8,1065.0,5.78,19.1,12.3
+157.0,93.9,16.5,16.4,1.68,18.4,35.9,649.0,8.9,26.7,21.1
+223.0,153.0,10.7,87.4,6.04,38.2,69.2,2288.0,34.9,80.6,120.0
+33.1,20.9,21.5,84.3,17.2,17.6,27.9,573.0,9.73,24.1,16.4
+57.8,7.57,16.3,158.0,21.5,42.6,73.7,1009.0,5.0,12.0,17.6
+233.0,286.0,46.6,302.0,47.8,12.2,17.5,679.0,9.82,22.3,73.0
+52.3,45.3,10.4,83.5,6.98,14.2,31.3,931.0,7.23,26.4,42.2
+43.7,27.6,25.9,22.3,3.59,30.8,44.1,594.0,17.9,54.2,94.7
+36.2,19.3,21.3,16.4,1.53,28.9,40.0,890.0,6.32,30.5,17.6
+54.7,42.2,20.2,16.5,4.91,45.7,78.4,3652.0,12.9,19.5,29.7
+60.4,35.5,14.1,124.0,18.1,1.0,2.71,10.6,40.7,71.0,86.6
+59.9,48.7,30.2,209.0,8.06,22.1,41.0,509.0,8.43,21.5,18.1
+22.9,26.9,20.2,19.6,5.23,10.3,13.3,255.0,10.1,22.5,19.6
+164.0,225.0,18.4,52.8,1.46,50.0,68.5,453.0,2.39,18.4,13.9
+44.5,33.7,19.3,35.2,12.0,3.68,21.9,445.0,10.5,16.8,25.3
+36.5,22.5,17.2,16.5,7.3,21.5,48.7,604.0,21.9,42.9,44.1
+23.9,7.57,20.5,121.0,11.2,35.5,46.6,615.0,34.0,75.7,75.0
+49.6,41.4,25.7,11.1,9.06,28.9,57.3,1762.0,5.0,27.1,33.1
+143.0,74.3,24.4,51.4,14.7,50.0,82.8,2414.0,50.5,100.0,87.4
+35.2,16.3,16.8,20.0,13.9,9.06,34.0,407.0,7.3,29.2,35.2
+36.5,22.1,15.8,111.0,24.6,31.1,56.2,685.0,7.37,16.1,2.5
+34.3,21.1,14.6,132.0,12.5,9.56,14.9,799.0,6.15,16.5,25.5
+20.0,17.6,5.99,6.92,11.2,3.65,10.4,552.0,11.0,22.3,21.5
+73.0,50.0,28.9,32.2,18.8,10.2,17.9,319.0,8.43,17.0,42.2
+161.0,89.0,19.5,142.0,5.99,18.4,24.6,704.0,4.96,19.5,12.4
+31.3,31.3,18.8,17.3,1.86,21.7,49.6,1433.0,14.1,29.2,30.2
+27.1,28.4,16.1,20.5,19.1,14.7,25.9,626.0,1.0,46.1,3.08
+205.0,137.0,19.1,17.0,8.28,26.9,59.4,956.0,7.7,16.1,28.6
+47.4,38.5,24.6,31.3,1.0,57.3,93.9,1911.0,10.8,17.3,18.9
+52.8,31.3,44.9,264.0,30.2,12.1,35.9,1263.0,13.9,27.9,21.7
+164.0,87.4,22.1,26.4,1.96,12.1,13.9,533.0,12.5,31.9,25.7
+55.7,29.4,33.1,626.0,41.4,11.2,23.7,784.0,9.31,15.7,36.2
+40.0,44.1,63.8,346.0,71.7,12.7,29.2,578.0,16.7,41.4,53.3
+85.8,71.0,19.1,28.1,10.4,31.9,57.3,1582.0,9.22,13.7,34.3
+47.4,33.1,65.5,141.0,19.5,33.4,46.1,426.0,13.8,30.2,20.2
+37.5,28.1,13.9,34.0,3.92,11.3,21.9,1155.0,9.31,20.7,24.1
+26.7,15.0,9.82,154.0,7.04,25.7,39.6,325.0,14.7,29.7,52.8
+37.9,29.4,27.4,24.1,1.33,15.4,31.1,547.0,7.64,9.56,20.7
+29.4,22.5,45.7,328.0,21.5,94.7,170.0,2167.0,7.17,20.7,30.8
+33.1,26.4,21.5,50.9,6.98,117.0,135.0,445.0,49.6,109.0,103.0
+38.2,18.1,10.0,20.4,8.58,12.2,31.9,784.0,9.65,28.4,22.7
+36.8,24.4,15.7,44.5,5.62,23.7,43.7,1018.0,109.0,281.0,355.0
+41.0,31.9,20.0,105.0,16.8,34.0,67.9,1640.0,16.0,36.5,32.2
+141.0,76.4,24.8,35.9,3.4,4.53,10.2,922.0,9.22,22.5,25.9
+42.9,35.9,14.7,124.0,19.8,30.2,48.7,1104.0,2.97,13.2,18.4
+66.7,30.2,1.0,14.3,7.17,40.7,64.4,449.0,1.0,6.21,3.92
+28.1,12.4,24.8,22.5,6.1,14.6,40.7,514.0,8.35,20.9,24.1
+21.3,22.3,53.3,337.0,67.9,7.37,8.51,334.0,6.79,15.0,13.5
+28.6,22.5,10.6,19.1,19.8,60.4,147.0,2548.0,17.3,41.8,67.9
+225.0,149.0,9.39,11.3,10.4,24.8,59.9,1640.0,1.0,13.1,17.3
+143.0,161.0,26.9,16.1,11.7,8.43,25.9,799.0,23.3,47.8,39.6
+32.5,27.6,20.0,56.7,5.47,30.5,45.7,1208.0,27.6,64.9,131.0
+40.7,21.5,21.7,50.9,11.3,28.4,42.2,578.0,2.0,17.9,16.0
+53.3,47.4,29.2,47.4,13.0,9.39,23.5,1094.0,1.06,119.0,6.92
+85.8,46.1,58.3,355.0,62.1,13.0,27.9,466.0,32.8,99.1,59.9
+51.9,37.5,53.3,198.0,71.0,9.22,18.1,533.0,19.3,29.4,54.7
+67.3,72.3,10.5,119.0,5.19,23.3,41.0,632.0,47.4,131.0,264.0
+30.0,30.5,2.62,3.28,1.0,5.09,12.7,710.0,8.13,15.3,13.3
+24.1,18.3,17.9,97.3,7.1,63.2,112.0,1911.0,17.6,27.9,35.2
+32.2,19.1,14.3,77.0,12.1,17.5,30.2,562.0,18.3,50.0,62.6
+36.2,31.6,22.5,41.0,10.1,12.4,27.9,965.0,18.8,57.3,64.4
+72.3,53.8,24.8,20.7,3.92,16.3,28.9,1298.0,50.9,84.3,89.8
+34.9,25.7,20.4,81.3,2.97,21.5,50.5,1165.0,6.67,30.5,23.5
+151.0,80.6,43.3,47.0,15.7,20.0,49.1,704.0,8.74,11.3,15.0
+34.0,15.4,16.8,57.8,7.57,35.2,49.6,1762.0,9.31,28.6,27.1
+104.0,82.0,12.3,1.19,21.9,17.0,23.3,523.0,14.1,26.4,27.1
+88.2,35.9,20.0,131.0,11.4,34.6,55.2,1144.0,15.1,34.3,27.1
+107.0,56.2,19.6,195.0,15.3,29.4,46.6,638.0,8.35,21.1,13.9
+3.49,4.41,25.9,26.7,2.05,20.0,40.7,828.0,7.99,28.1,27.9
+50.5,33.4,51.9,385.0,57.8,16.7,22.9,487.0,4.18,18.1,32.2
+79.1,56.2,4.78,66.1,6.32,39.6,79.1,2503.0,25.0,62.1,72.3
+51.4,27.4,65.5,418.0,59.4,24.6,41.8,799.0,13.9,33.7,31.1
+48.3,33.4,25.0,28.6,6.1,3.92,8.9,158.0,3.28,12.7,19.3
+77.0,50.5,18.9,150.0,10.7,29.2,49.1,874.0,8.58,200.0,7.23
+41.0,27.6,20.0,16.1,1.31,13.7,42.9,610.0,36.8,77.0,121.0
+50.0,25.3,16.7,80.6,8.43,22.1,36.8,583.0,7.57,10.6,23.1
+57.3,35.5,62.6,437.0,49.1,4.53,15.1,806.0,47.4,59.4,14.3
+34.0,16.0,12.1,289.0,22.7,17.8,20.7,505.0,13.3,29.7,32.5
+31.9,23.5,25.3,23.5,3.31,10.7,24.6,851.0,11.9,22.7,7.37
+39.6,28.1,18.1,28.9,20.9,19.1,29.7,557.0,18.6,65.5,73.0
+88.2,63.8,78.4,337.0,51.4,28.4,44.5,828.0,17.9,52.3,55.2
+65.5,42.9,23.3,22.5,12.6,13.5,19.1,441.0,6.1,23.3,34.3
+108.0,71.7,16.8,183.0,23.9,16.1,30.0,400.0,13.6,21.5,44.1
+27.9,26.2,14.1,292.0,25.5,13.9,38.5,730.0,5.73,23.3,26.7
+114.0,69.8,12.2,211.0,10.3,63.8,98.2,1655.0,11.2,24.4,30.0
+48.7,28.9,32.2,31.3,17.0,32.8,57.8,1298.0,19.1,49.6,54.7
+41.0,18.1,14.6,22.1,1.0,24.4,38.9,594.0,9.56,17.9,7.3
+34.9,19.6,20.2,13.1,1.0,55.2,115.0,1843.0,7.04,25.3,36.2
+17.5,11.5,29.2,18.8,5.94,27.6,48.7,757.0,27.6,64.4,65.5
+67.9,71.7,18.1,14.2,9.14,39.2,47.8,939.0,15.0,34.9,54.2
+170.0,105.0,18.1,55.2,5.73,49.1,73.0,828.0,10.3,20.2,44.5
+31.9,25.5,29.7,24.8,2.64,1.0,10.2,38.9,8.28,12.0,33.4
+31.9,22.7,12.6,215.0,18.9,18.8,37.9,685.0,2.46,58.3,6.79
+29.2,22.9,20.9,74.3,4.03,12.0,28.1,414.0,5.78,16.8,13.8
+37.5,22.5,16.8,151.0,12.2,113.0,227.0,2642.0,8.98,14.9,4.33
+81.3,61.0,13.6,64.9,11.1,17.9,58.8,500.0,15.5,25.5,28.6
+77.7,55.2,18.3,127.0,11.9,55.2,84.3,1055.0,46.1,93.9,105.0
+27.6,18.9,21.1,75.0,18.9,16.1,29.2,1165.0,29.4,65.5,81.3
+75.7,37.9,10.2,8.98,7.7,10.2,28.1,461.0,22.9,42.9,64.4
+47.8,30.8,26.2,37.9,5.99,7.5,7.04,414.0,35.9,82.8,160.0
+178.0,108.0,54.2,274.0,29.7,41.0,71.0,1928.0,8.06,19.1,28.6
+73.0,43.7,26.2,343.0,42.2,49.6,80.6,1124.0,18.4,43.3,66.1
+34.3,21.3,4.29,13.5,9.31,9.82,25.7,649.0,1.0,64.4,4.33
+49.1,11.9,63.8,445.0,66.1,30.5,50.9,437.0,9.73,15.4,15.4
+50.9,36.8,21.7,274.0,20.2,12.3,21.5,491.0,10.9,33.4,45.3
+36.5,20.9,20.7,68.5,24.4,77.0,110.0,372.0,9.73,14.9,26.4
+73.7,16.8,32.5,24.1,1.0,34.3,55.2,567.0,9.56,22.3,20.5
+42.6,28.6,18.6,37.9,13.5,9.65,24.6,359.0,5.23,18.3,13.6
+91.4,55.2,18.3,196.0,10.6,33.7,50.9,655.0,10.6,27.4,43.3
+139.0,94.7,20.9,73.7,10.2,27.9,48.3,1197.0,15.7,36.2,46.1
+62.1,41.0,27.4,22.5,1.79,8.43,20.7,528.0,12.0,23.9,12.6
+63.8,41.0,22.3,14.9,1.09,30.5,64.9,1843.0,13.3,34.0,25.3
+89.8,82.0,12.5,27.4,10.1,17.3,31.1,882.0,16.5,47.0,68.5
+26.9,23.9,13.8,64.9,10.9,26.4,42.9,461.0,6.55,25.7,32.8
+112.0,69.2,23.3,45.7,10.8,28.6,59.9,1346.0,3.08,8.51,7.84
+69.2,36.8,26.9,19.3,7.37,17.9,33.4,1000.0,11.8,16.7,25.9
+28.9,18.3,44.1,433.0,67.3,21.1,29.7,449.0,11.0,36.2,42.6
+28.1,13.0,7.99,145.0,16.3,17.0,34.3,649.0,11.8,30.2,52.8
+23.3,13.1,82.0,239.0,26.2,30.8,50.5,956.0,16.8,26.9,18.6
+181.0,97.3,22.5,105.0,12.9,1.0,6.67,1.0,8.58,20.9,11.3
+136.0,87.4,14.1,161.0,21.9,22.5,43.3,2996.0,10.9,25.3,27.9
+48.3,21.5,21.5,21.1,9.14,6.61,22.9,573.0,35.2,71.0,147.0
+52.3,28.1,17.2,253.0,31.9,42.6,73.7,723.0,4.14,37.5,16.0
+31.3,18.8,54.2,300.0,42.2,32.5,58.3,1946.0,1.91,5.38,15.7
+44.1,18.4,23.5,22.7,6.61,22.9,36.8,496.0,16.0,34.0,14.5
+44.1,42.2,14.5,204.0,13.8,20.7,42.6,509.0,13.3,39.2,61.5
+31.9,16.5,12.9,146.0,28.1,60.4,106.0,1778.0,49.1,137.0,205.0
+37.5,25.3,21.3,40.3,10.6,13.0,54.7,362.0,31.6,66.1,71.7
+115.0,98.2,20.5,15.4,10.4,23.5,63.8,3652.0,11.8,22.5,18.4
+27.9,27.4,32.2,274.0,34.6,19.3,29.7,213.0,2.5,110.0,8.74
+34.3,19.5,22.5,205.0,17.8,16.4,29.7,528.0,21.7,41.4,10.4
+118.0,77.7,16.5,112.0,21.7,7.04,3.72,764.0,12.4,20.9,36.2
+33.4,13.3,34.0,41.0,10.8,10.7,28.6,866.0,10.9,25.9,20.0
+21.5,36.2,35.9,141.0,29.4,36.2,64.4,3460.0,11.5,30.5,43.3
+74.3,41.8,48.7,253.0,29.2,21.5,46.6,649.0,6.85,18.4,45.3
+37.2,18.9,22.1,11.1,8.82,16.8,104.0,2227.0,18.8,68.5,61.5
+28.6,31.6,40.7,433.0,56.7,3.43,12.4,898.0,5.73,28.4,13.7
+41.8,25.7,20.9,14.1,5.38,12.9,35.2,362.0,13.1,21.7,21.5
+274.0,196.0,22.3,43.7,8.35,6.73,23.1,1104.0,8.98,25.7,17.2
+27.6,25.5,19.8,36.8,5.42,12.6,20.5,562.0,12.4,46.6,52.3
+121.0,79.9,29.7,23.9,14.5,25.7,32.5,673.0,9.65,15.4,33.1
+237.0,170.0,70.4,241.0,41.4,37.5,53.8,322.0,9.22,15.8,15.8
+48.3,23.9,18.8,42.6,6.55,40.3,50.5,453.0,20.4,33.1,52.8
+163.0,114.0,24.4,24.4,14.3,49.1,71.7,599.0,49.6,96.5,105.0
+241.0,151.0,19.8,15.8,7.77,14.1,26.7,615.0,10.1,37.5,42.9
+74.3,58.8,12.7,150.0,8.13,11.4,22.7,552.0,8.9,21.7,18.4
+60.4,40.7,44.9,239.0,40.3,5.33,17.2,743.0,8.98,17.2,37.2
+32.2,16.7,33.1,311.0,45.7,37.5,63.2,698.0,12.5,36.2,56.7
+51.9,37.5,18.3,24.4,5.14,18.6,20.5,319.0,6.26,11.4,35.9
+133.0,80.6,28.4,36.8,6.61,37.9,51.9,343.0,111.0,331.0,355.0
+34.3,17.2,41.8,274.0,24.6,23.3,35.5,542.0,12.2,32.5,26.7
+39.6,30.0,29.2,241.0,35.9,7.99,25.7,457.0,2.48,20.7,14.5
+34.3,17.5,25.3,18.9,13.6,18.8,34.0,704.0,8.66,21.9,13.1
+31.3,34.3,17.9,17.6,12.9,2.05,8.35,385.0,50.9,117.0,151.0
+79.9,49.6,35.2,39.2,9.31,14.6,20.7,533.0,4.7,14.5,18.1
+122.0,143.0,27.4,33.4,6.85,21.9,31.3,547.0,8.82,25.0,23.1
+37.9,20.5,19.8,67.9,15.4,73.0,124.0,2393.0,8.13,11.7,20.4
+118.0,64.4,19.1,138.0,15.4,28.9,28.9,655.0,12.5,29.7,24.8
+38.9,14.5,15.8,60.4,37.9,26.4,45.7,777.0,10.8,15.3,16.1
+92.2,41.8,26.4,27.4,5.67,9.31,36.8,429.0,52.8,125.0,223.0
+33.1,14.6,31.1,12.2,9.06,7.7,13.7,255.0,16.0,24.4,37.5
+35.5,27.6,14.9,130.0,18.8,11.8,16.5,500.0,7.23,19.5,17.3
+59.4,30.8,5.94,29.4,9.22,101.0,161.0,1778.0,13.1,22.1,28.1
+78.4,51.9,22.9,23.7,10.4,5.38,9.73,583.0,6.67,14.2,15.4
+146.0,86.6,1.0,100.0,19.3,14.1,27.4,487.0,14.9,33.4,42.2
+26.9,14.2,15.3,45.3,10.0,16.3,28.4,644.0,27.4,56.2,79.9
+31.3,19.6,17.2,85.8,11.7,29.2,59.4,914.0,9.91,25.0,14.5
+30.8,24.8,21.1,91.4,19.6,15.0,41.4,519.0,33.7,84.3,81.3
+99.1,97.3,24.1,20.2,8.98,35.5,58.3,2350.0,7.43,24.4,18.6
+30.8,22.5,11.0,62.6,6.04,34.6,60.4,1472.0,10.6,27.6,39.6
+27.9,15.0,19.5,23.3,14.2,18.8,41.0,1241.0,4.22,8.2,15.4
+36.8,31.3,67.9,286.0,54.7,48.7,61.0,382.0,22.3,60.4,73.0
+109.0,83.5,59.4,305.0,49.6,35.9,67.9,3786.0,21.9,47.8,42.9
+44.5,28.1,7.57,146.0,19.6,15.5,29.4,567.0,5.28,26.7,17.5
+37.9,20.2,41.4,42.6,14.6,11.4,27.6,429.0,32.2,85.1,112.0
+53.3,38.2,25.3,107.0,13.2,8.28,14.3,264.0,12.3,24.1,32.5
+163.0,92.2,20.5,32.5,6.92,23.3,33.7,349.0,1.98,85.8,7.37
+33.4,27.1,16.3,142.0,9.22,106.0,191.0,2129.0,10.0,21.5,23.9
+34.3,13.2,21.1,24.8,12.2,25.7,51.9,519.0,10.4,23.1,30.0
+18.6,5.42,20.2,22.5,4.49,40.7,62.6,692.0,27.4,52.8,61.0
+37.2,23.1,7.64,22.5,13.2,79.1,147.0,1894.0,7.37,25.9,27.1
+26.7,15.7,28.1,334.0,48.3,14.1,21.1,906.0,5.88,28.4,21.9
+142.0,98.2,59.4,392.0,44.5,71.7,123.0,1762.0,34.3,118.0,137.0
+52.3,34.0,26.9,24.1,5.73,37.9,58.8,1459.0,6.98,22.1,27.6
+31.9,16.8,32.2,46.6,15.7,10.9,27.4,890.0,18.3,25.9,58.8
+106.0,68.5,12.4,175.0,16.8,12.3,40.3,685.0,8.74,28.4,9.91
+42.6,21.3,20.9,131.0,12.1,12.7,31.6,487.0,8.51,18.9,20.7
+34.9,16.4,17.8,18.8,2.15,34.6,59.4,445.0,53.8,78.4,20.2
+31.9,26.4,14.1,20.2,4.61,12.4,18.9,799.0,7.17,19.3,22.3
+36.5,20.7,29.4,36.5,21.3,2.07,9.91,26.7,30.5,50.5,9.65
+27.6,15.5,27.1,35.9,10.6,63.2,95.6,1197.0,13.6,17.9,21.9
+26.2,20.9,22.7,10.1,7.43,15.4,37.2,433.0,10.8,14.5,8.28
+16.1,25.0,18.1,34.6,4.49,3.52,13.6,704.0,11.5,26.9,37.5
+34.9,16.1,54.2,562.0,71.7,13.0,27.6,737.0,9.73,18.4,18.9
+153.0,82.0,33.4,48.7,8.28,11.9,28.6,710.0,16.1,47.0,36.5
+129.0,161.0,54.2,79.1,23.5,34.9,70.4,2788.0,6.55,7.64,34.0
+33.4,17.5,23.9,16.5,1.0,7.91,21.5,578.0,7.5,30.2,24.1
+31.9,33.4,64.9,474.0,77.0,40.3,46.6,1176.0,9.22,15.5,12.6
+25.9,16.7,14.7,217.0,36.8,87.4,151.0,2839.0,3.49,51.4,2.21
+98.2,67.9,11.1,79.1,6.04,9.56,21.3,470.0,51.4,93.1,178.0
+55.2,31.3,53.3,253.0,50.9,13.2,25.5,1176.0,12.2,26.2,30.8
+25.9,20.2,10.4,179.0,17.8,15.3,36.8,1155.0,4.14,14.2,7.99
+45.3,31.1,23.1,30.0,12.1,8.35,24.6,573.0,9.91,18.9,20.7
+53.8,31.6,29.7,40.0,14.5,57.3,89.0,1894.0,13.8,35.2,39.6
+43.7,34.6,24.8,14.7,5.88,28.9,67.3,1275.0,22.5,42.6,63.8
+196.0,113.0,14.2,92.2,2.41,11.7,15.0,638.0,7.57,22.1,25.9
+30.8,20.7,28.4,30.0,12.7,13.6,16.5,509.0,10.6,24.8,18.3
+21.3,23.5,18.3,85.1,7.37,22.5,37.5,466.0,28.9,56.7,63.8
+34.6,17.8,25.7,30.5,4.53,16.3,31.6,615.0,8.51,12.9,16.8
+30.2,17.3,61.5,122.0,72.3,9.56,26.4,583.0,7.5,22.9,13.8
+30.2,25.3,56.2,573.0,75.0,10.6,23.7,449.0,13.2,31.1,38.9
+30.2,11.8,21.5,25.5,11.5,6.73,19.3,204.0,5.47,13.2,23.7
+132.0,95.6,19.1,23.7,11.2,35.5,53.3,1144.0,25.3,60.4,123.0
+49.6,39.6,37.5,53.8,13.9,7.77,22.1,57.3,21.9,49.6,70.4
+33.4,16.0,23.1,32.2,8.51,29.7,40.0,557.0,13.3,9.06,10.0
+47.0,47.8,15.8,117.0,14.7,24.4,36.2,1000.0,10.5,37.9,94.7
+72.3,25.7,13.0,3.16,7.91,37.9,115.0,982.0,17.0,37.9,41.8
+139.0,91.4,19.5,70.4,7.23,13.0,22.5,414.0,7.04,20.5,2.55
+33.4,22.7,16.5,18.3,11.5,29.2,54.2,433.0,16.3,41.8,75.0
+92.2,79.9,108.0,221.0,1084.0,121.0,205.0,2503.0,10.5,16.0,25.5
+32.5,23.7,28.1,28.1,22.5,31.3,44.9,610.0,18.4,53.3,115.0
+35.2,18.6,20.7,24.1,4.07,12.9,26.4,538.0,9.31,27.6,60.4
+138.0,105.0,2.48,15.3,9.47,1.24,5.23,62.1,8.51,37.5,26.2
+37.5,23.1,13.3,292.0,7.3,9.39,38.2,1731.0,9.39,17.3,25.7
+37.9,8.66,17.3,33.4,7.91,20.2,45.7,2267.0,8.28,22.7,14.5
+75.0,50.9,16.4,29.7,9.14,61.0,108.0,1395.0,7.3,17.3,40.3
+38.2,26.2,30.0,27.6,6.49,20.2,24.8,509.0,17.2,35.2,17.8
+26.7,18.6,48.7,44.1,3.79,14.1,16.3,791.0,7.99,20.9,21.9
+30.5,22.9,22.1,27.1,6.44,59.9,113.0,1554.0,2.39,82.0,2.02
+59.9,47.0,18.8,193.0,32.2,10.5,25.9,667.0,13.5,32.8,49.1
+37.9,22.7,35.9,274.0,33.1,2.94,16.4,649.0,21.5,48.3,41.8
+36.2,17.5,47.8,160.0,20.9,59.4,101.0,1395.0,11.7,20.9,20.5
+43.3,27.1,33.4,30.2,11.9,9.73,20.7,215.0,3.05,20.9,1.0
+45.7,25.5,15.8,189.0,8.28,52.3,84.3,1420.0,11.3,42.9,36.2
+31.6,27.9,18.6,57.8,13.1,7.37,10.5,276.0,6.49,16.1,35.2
+200.0,95.6,8.58,16.4,3.62,36.5,67.9,991.0,9.91,22.9,11.7
+34.9,15.5,23.7,79.9,16.1,36.2,57.8,1144.0,5.47,19.6,26.7
+178.0,99.1,14.7,24.1,10.2,14.2,15.1,567.0,106.0,151.0,30.0
+94.7,38.2,16.1,211.0,32.2,16.0,28.9,538.0,9.39,19.6,9.91
+24.4,18.4,15.7,18.3,3.37,12.9,33.1,750.0,8.28,15.3,12.3
+55.2,55.2,8.43,146.0,21.5,13.6,27.9,649.0,7.17,21.7,23.3
+50.9,47.4,20.4,24.6,2.02,10.2,28.1,982.0,15.8,51.4,77.0
+54.2,34.3,12.0,139.0,19.6,12.3,18.8,621.0,6.26,18.8,37.9
+41.0,26.9,20.0,17.3,7.77,25.0,36.5,649.0,11.7,15.1,18.8
+27.1,27.1,17.9,17.5,6.38,6.21,22.1,372.0,11.2,25.3,47.4
+36.5,25.3,26.9,255.0,20.4,73.0,154.0,3106.0,10.1,38.5,41.0
+26.9,18.4,47.8,223.0,48.3,19.8,41.4,1298.0,10.9,31.6,31.9
+112.0,80.6,22.7,25.9,10.3,12.6,30.2,474.0,4.14,16.8,16.4
+30.0,17.6,20.5,24.1,1.07,93.1,176.0,3368.0,10.2,24.8,51.4
+28.9,20.9,27.6,34.9,10.7,21.7,44.1,1075.0,6.85,10.9,32.8
+35.9,22.3,15.4,157.0,20.7,1.26,23.3,17.3,6.38,18.8,20.7
+207.0,139.0,11.8,142.0,19.8,16.8,34.6,562.0,9.82,18.8,33.7
+30.0,33.1,11.8,38.5,14.7,6.79,18.3,1165.0,7.5,10.0,15.1
+28.9,15.3,41.4,142.0,35.5,16.1,34.6,478.0,3.79,24.1,24.1
+44.9,24.6,20.4,21.5,24.8,6.32,22.1,770.0,23.5,42.6,75.0
+15.0,7.04,18.9,237.0,23.3,244.0,474.0,5523.0,14.3,27.6,58.3
+41.8,23.1,19.3,158.0,15.0,30.5,46.6,483.0,9.91,24.1,28.9
+31.1,20.0,12.1,157.0,15.8,94.7,136.0,1046.0,10.5,33.7,51.4
+26.4,21.1,16.8,57.3,8.82,37.5,58.8,523.0,4.87,34.3,25.9
+69.2,37.9,19.8,17.0,1.27,28.1,48.3,644.0,8.51,29.7,26.2
+54.7,36.5,7.04,8.9,5.47,6.32,4.57,150.0,7.17,22.3,6.55
+25.9,13.3,89.8,422.0,73.0,30.2,44.9,661.0,10.3,27.6,41.4
+31.9,16.4,67.3,176.0,23.9,56.7,97.3,1263.0,13.2,14.3,26.7
+49.1,43.3,31.1,32.8,17.8,19.6,42.2,599.0,4.07,16.7,24.4
+28.4,20.2,9.14,165.0,12.5,13.7,27.9,403.0,10.6,20.4,23.5
+42.6,33.1,28.9,24.6,10.6,12.2,20.2,505.0,5.94,15.5,4.07
+29.4,25.5,12.2,75.7,12.0,18.9,42.2,2207.0,11.8,28.1,22.3
+34.3,17.6,19.6,20.7,14.1,30.2,41.0,313.0,9.14,19.5,14.9
+33.4,28.6,11.4,189.0,14.2,15.5,29.4,542.0,8.51,14.3,27.6
+69.2,54.2,19.5,16.3,11.1,11.4,24.8,573.0,11.3,27.1,59.4
+132.0,84.3,23.1,20.9,3.25,21.5,34.0,362.0,7.37,27.9,36.8
+1.14,2.11,23.5,19.5,1.0,24.1,46.6,973.0,71.0,184.0,207.0
+25.9,13.2,21.9,24.1,21.3,59.9,92.2,1370.0,7.77,20.7,26.9
+33.1,22.3,47.4,141.0,39.2,27.1,50.5,1000.0,1.0,75.0,7.7
+122.0,75.7,20.5,42.2,6.49,49.1,120.0,1322.0,9.14,16.0,22.3
+78.4,56.2,5.38,146.0,8.82,10.8,26.2,418.0,21.3,49.6,64.9
+63.2,50.9,58.8,389.0,59.4,21.7,33.7,858.0,13.6,24.1,13.7
+39.6,20.4,14.1,101.0,11.8,13.0,22.9,514.0,6.61,16.0,33.7
+204.0,138.0,17.5,191.0,25.5,5.52,14.6,914.0,4.03,18.8,30.2
+22.5,17.0,16.7,82.0,18.8,37.2,61.5,1186.0,10.7,22.7,28.6
+40.3,21.7,27.1,297.0,26.7,40.0,62.1,1055.0,9.91,22.7,35.9
+235.0,135.0,53.3,359.0,53.8,11.9,24.8,673.0,24.1,61.5,79.1
+24.1,13.0,72.3,337.0,85.8,1.01,2.44,158.0,6.21,15.3,17.2
+22.5,21.1,23.3,61.0,7.64,103.0,255.0,3752.0,12.5,25.9,22.3
+108.0,106.0,38.9,255.0,55.2,55.7,87.4,1395.0,9.06,39.2,26.7
+53.3,38.2,30.0,36.5,8.82,13.9,23.3,583.0,5.62,20.0,23.1
+132.0,59.9,36.2,160.0,44.9,8.66,36.5,359.0,9.39,27.4,17.9
+94.7,64.4,16.3,16.8,9.22,67.3,105.0,1981.0,10.3,22.5,20.5
+151.0,98.2,23.1,36.8,1.41,41.8,93.9,1554.0,10.0,17.5,1.17
+112.0,81.3,18.9,37.9,12.9,9.65,26.4,1395.0,5.33,15.1,28.1
+120.0,77.7,40.0,62.1,28.4,22.9,36.8,414.0,12.3,13.7,17.5
+39.2,34.9,75.7,433.0,73.0,11.7,39.2,449.0,25.5,51.4,75.7
+164.0,119.0,13.6,89.0,11.5,21.5,40.0,382.0,6.73,18.8,17.8
+29.7,16.7,85.1,274.0,41.8,15.0,25.5,523.0,11.9,29.2,63.8
+44.9,48.3,27.9,30.8,19.5,64.4,146.0,2091.0,11.1,27.6,23.5
+20.5,30.2,23.1,20.4,3.79,20.0,73.0,562.0,30.2,63.8,151.0
+172.0,90.6,22.7,16.3,7.1,70.4,89.8,403.0,4.14,22.7,36.2
+28.1,24.4,14.9,67.9,1.54,10.4,13.5,649.0,37.5,55.2,14.6
+46.1,20.2,18.1,81.3,8.82,18.3,39.2,567.0,11.4,15.7,32.5
+147.0,102.0,6.04,20.4,10.3,29.2,47.4,478.0,5.47,14.6,11.4
+32.8,28.1,17.3,20.9,3.82,100.0,172.0,2666.0,31.9,75.7,107.0
+9.39,18.1,14.2,17.6,8.13,11.2,21.1,457.0,115.0,184.0,27.6
+34.9,30.0,40.3,389.0,33.7,29.2,81.3,2247.0,8.35,12.6,19.1
+73.7,57.8,8.9,122.0,6.04,45.7,58.8,578.0,22.1,66.7,62.1
+56.2,44.5,18.1,20.7,5.62,10.7,31.9,403.0,11.0,30.5,53.8
+101.0,64.4,23.1,98.2,15.3,19.3,38.2,685.0,16.8,27.4,28.9
+77.7,43.7,17.2,21.5,5.09,12.4,23.1,947.0,8.28,20.0,15.3
+65.5,40.7,17.5,23.3,10.0,7.43,19.3,1000.0,2.25,64.4,1.12
+28.6,17.9,15.0,51.9,14.9,9.22,34.6,470.0,7.99,12.5,19.1
+63.2,28.6,60.4,161.0,36.5,63.8,98.2,890.0,13.7,22.3,21.9
+45.7,10.6,18.1,105.0,14.1,106.0,181.0,2167.0,14.6,29.4,22.1
+50.5,35.9,62.1,308.0,41.8,15.0,25.7,552.0,8.35,18.4,13.0
+13.8,18.3,13.5,54.2,21.9,18.4,39.6,655.0,8.43,30.5,34.3
+22.1,14.3,71.0,215.0,55.2,16.8,30.2,491.0,6.61,16.4,29.2
+40.0,18.3,22.3,29.2,11.1,50.0,101.0,2690.0,1.0,86.6,4.07
+38.2,13.7,15.8,47.4,4.96,11.9,28.9,470.0,45.3,89.8,114.0
+23.9,13.3,52.3,88.2,30.2,4.83,16.4,743.0,16.8,32.8,83.5
+90.6,57.8,28.9,23.3,1.93,16.0,35.9,396.0,42.2,95.6,100.0
+30.8,21.3,15.4,111.0,20.4,12.5,34.3,466.0,24.1,48.7,110.0
+36.2,17.3,15.5,136.0,18.1,18.4,31.3,505.0,41.4,78.4,121.0
+34.0,19.8,34.0,196.0,13.7,6.85,19.5,820.0,10.3,23.1,27.1
+104.0,105.0,27.1,379.0,65.5,15.0,26.4,638.0,12.5,19.6,15.8
+96.5,53.3,22.1,22.9,7.64,31.9,43.3,355.0,7.64,19.3,18.1
+82.0,61.0,8.43,89.8,7.43,12.2,18.4,615.0,13.1,46.6,43.3
+33.1,20.7,19.5,73.7,12.0,17.6,38.2,389.0,10.7,14.2,21.3
+37.9,21.1,25.7,24.6,5.88,30.2,51.4,947.0,6.55,41.0,32.2
+36.5,14.5,53.8,414.0,72.3,13.2,31.1,1084.0,11.8,50.0,41.8
+31.9,24.6,31.6,38.5,6.26,73.0,130.0,2110.0,8.35,15.7,17.5
+41.8,32.8,13.8,139.0,17.9,8.51,18.9,269.0,1.21,5.19,1.0
+42.2,32.5,69.8,105.0,44.9,35.9,85.1,2129.0,9.39,30.2,19.1
+37.5,23.3,16.1,151.0,16.1,41.0,69.8,1275.0,36.8,83.5,172.0
+18.6,17.3,96.5,491.0,109.0,11.9,32.8,346.0,18.6,41.8,89.8
+9.22,1.01,19.1,21.5,9.91,17.9,43.7,573.0,11.0,33.7,50.9
+35.9,20.7,45.7,284.0,31.9,13.9,34.9,478.0,3.4,4.18,33.1
+109.0,77.7,31.1,32.5,13.5,14.2,23.3,445.0,55.7,108.0,80.6
+16.4,10.5,20.9,14.9,18.4,12.0,44.1,474.0,37.2,101.0,114.0
+25.7,14.6,12.5,96.5,20.4,52.8,86.6,777.0,18.8,48.7,34.6
+32.8,12.9,14.7,106.0,14.5,15.3,30.8,615.0,1.0,84.3,7.99
+23.9,16.5,24.4,14.2,3.25,10.8,50.0,649.0,10.0,24.1,19.3
+43.7,21.1,33.4,34.3,8.28,10.2,30.5,632.0,14.3,29.4,4.37
+34.0,34.3,33.7,372.0,29.4,40.7,59.9,1420.0,39.2,99.1,129.0
+34.3,21.3,51.9,292.0,56.2,10.2,30.2,449.0,5.23,23.7,34.6
+115.0,58.8,20.2,57.3,15.3,67.3,115.0,1370.0,15.4,36.2,39.6
+150.0,97.3,1.0,77.0,7.77,63.2,99.1,1499.0,10.6,41.8,44.1
+38.9,22.5,20.9,22.1,6.32,6.44,12.0,496.0,11.3,17.3,40.3
+28.1,19.6,17.2,184.0,7.1,23.7,31.9,379.0,62.1,189.0,237.0
+32.8,22.9,19.5,21.7,13.1,20.7,50.5,737.0,9.91,22.7,22.1
+17.9,36.5,38.9,44.5,33.1,44.5,63.8,422.0,10.6,23.5,3.65
+22.7,26.2,17.6,63.8,9.91,35.9,66.7,1094.0,5.73,13.2,35.2
+22.9,34.3,18.1,22.9,8.74,2.17,10.6,99.1,1.04,1.0,3.82
+35.2,22.3,17.2,155.0,19.6,28.4,53.8,835.0,10.7,41.4,19.3
+29.7,25.5,37.9,57.8,14.6,11.2,21.1,470.0,7.43,22.5,23.5
+202.0,142.0,14.7,78.4,1.88,21.1,105.0,1298.0,7.17,23.3,25.5
+27.1,33.1,20.0,8.58,8.06,75.7,106.0,346.0,12.0,16.0,16.4
+31.1,22.7,14.1,90.6,13.2,33.1,61.0,1420.0,15.4,36.2,59.9
+17.5,19.3,118.0,365.0,77.0,10.4,30.5,1843.0,5.88,20.9,17.6
+37.9,19.6,28.1,142.0,17.6,9.39,24.6,457.0,9.82,25.9,14.5
+170.0,103.0,4.41,79.1,10.8,43.7,90.6,1540.0,4.33,7.7,8.58
+70.4,42.2,19.8,13.7,8.98,12.7,37.5,437.0,1.83,7.23,7.57
+33.7,22.1,34.0,219.0,17.2,82.8,135.0,2054.0,7.77,28.6,26.4
+23.3,21.7,23.9,26.7,7.77,30.8,43.3,385.0,16.5,44.5,62.1
+32.5,40.3,47.4,239.0,42.9,53.3,74.3,437.0,7.3,18.1,34.9
+167.0,99.1,23.7,33.1,16.3,9.39,19.5,449.0,10.3,32.5,47.4
+143.0,101.0,16.5,50.5,3.79,12.6,22.5,466.0,3.85,26.4,15.5
+48.3,42.9,14.2,279.0,18.9,54.2,102.0,2167.0,1.65,61.5,9.65
+37.9,23.1,7.5,13.7,5.52,18.3,19.6,820.0,10.0,15.8,16.0
+49.1,29.2,27.1,138.0,16.5,10.6,15.7,514.0,13.0,36.8,53.8
+55.2,40.0,12.6,115.0,13.9,33.7,49.1,396.0,3.02,37.5,3.0
+28.9,4.03,14.7,104.0,26.2,22.1,29.7,311.0,9.82,18.8,32.8
+61.5,41.8,21.7,20.2,3.16,14.2,25.7,594.0,10.3,17.6,23.5
+32.2,23.7,64.9,426.0,71.0,5.28,23.9,274.0,9.91,35.2,29.4
+62.1,31.9,23.5,20.4,17.5,22.1,27.9,414.0,27.9,58.8,72.3
+71.7,42.9,28.4,292.0,41.8,19.8,24.1,259.0,6.32,36.8,28.6
+49.6,40.0,30.0,195.0,35.2,3.72,22.7,219.0,29.2,69.8,103.0
+25.0,15.5,15.8,12.7,6.98,28.4,39.2,410.0,7.3,14.1,18.9
+37.5,18.1,26.7,655.0,78.4,17.2,31.9,505.0,13.7,32.5,38.5
+163.0,122.0,21.7,311.0,47.0,43.7,99.1,1894.0,3.65,21.3,26.2
+25.3,23.3,14.3,18.9,11.5,10.9,36.2,389.0,18.1,35.2,7.5
+30.8,22.7,39.2,528.0,35.2,6.92,20.4,533.0,10.4,21.5,23.7
+79.9,77.7,46.6,389.0,75.7,26.7,30.2,286.0,5.05,13.5,26.9
+70.4,52.8,19.1,15.3,3.96,23.1,36.2,372.0,14.6,38.2,63.2
+20.0,23.5,4.26,10.6,10.3,10.7,17.3,470.0,51.4,136.0,160.0
+191.0,138.0,30.2,23.3,7.99,10.5,28.4,396.0,25.0,63.8,69.2
+106.0,58.8,14.6,18.3,3.65,11.5,21.7,661.0,7.1,18.1,30.2
+76.4,70.4,16.5,124.0,15.5,10.2,37.2,685.0,18.8,18.4,7.04
+69.2,49.6,22.7,26.7,11.7,5.94,11.8,947.0,15.5,41.0,33.4
+41.8,44.1,38.2,79.1,30.0,22.1,44.5,538.0,6.32,24.8,37.5
+26.7,26.2,26.2,213.0,36.5,52.3,73.7,453.0,11.4,24.4,13.5
+28.9,7.37,50.5,255.0,67.9,17.3,31.3,410.0,17.9,36.5,47.4
+48.7,20.5,15.1,97.3,8.43,33.1,53.3,445.0,11.1,30.5,29.2
+112.0,79.1,23.9,30.8,6.04,4.7,19.3,956.0,8.82,21.9,34.0
+33.7,17.5,4.74,14.1,9.39,14.2,25.3,583.0,44.1,112.0,132.0
+131.0,77.7,6.67,129.0,36.2,20.4,35.9,519.0,16.5,51.4,75.7
+30.2,17.6,26.7,26.4,4.29,106.0,204.0,1794.0,30.0,59.9,66.7
+139.0,82.8,16.1,36.5,19.1,24.8,35.5,349.0,3.25,76.4,6.61
+36.5,15.8,25.0,23.3,1.38,30.2,62.1,505.0,2.55,5.09,1.72
+46.1,51.4,16.7,16.0,1.0,5.19,10.5,866.0,1.0,68.5,9.22
+36.8,22.5,15.7,239.0,27.4,22.1,34.6,449.0,9.65,31.1,20.9
+28.1,16.1,16.8,22.9,11.2,36.2,66.1,1582.0,3.82,21.9,38.2
+29.7,25.0,70.4,65.5,3.02,71.0,115.0,1827.0,10.6,24.6,23.3
+41.4,18.6,17.0,113.0,33.1,35.5,62.6,1582.0,7.64,26.7,6.44
+125.0,97.3,11.5,17.0,4.29,8.66,36.5,385.0,8.9,17.2,26.7
+37.9,22.5,19.1,21.3,3.4,34.3,50.9,519.0,30.5,76.4,90.6
+29.7,13.9,31.9,48.7,20.5,7.64,23.5,181.0,24.1,69.2,63.2
+89.0,54.7,22.7,21.9,5.73,5.67,24.6,250.0,10.5,22.3,25.7
+43.7,13.0,82.0,368.0,78.4,6.04,17.0,491.0,6.92,33.1,19.5
+33.4,19.5,12.3,105.0,12.1,42.6,65.5,1395.0,14.3,31.3,49.1
+61.5,31.9,4.57,14.2,1.95,32.5,48.3,244.0,13.9,31.3,23.1
+38.2,25.9,24.1,20.9,6.98,22.9,43.3,271.0,7.1,12.1,23.7
+33.7,18.4,10.2,12.1,12.1,6.26,13.9,389.0,52.8,73.0,2.69
+55.7,25.3,24.1,20.9,3.68,28.4,39.2,410.0,17.5,34.9,5.57
+48.7,27.4,42.9,215.0,25.5,74.3,121.0,1540.0,8.82,12.5,15.3
+20.4,14.5,37.2,30.8,12.9,21.1,34.6,328.0,10.5,14.6,16.7
+36.2,17.9,19.1,70.4,9.47,5.99,21.5,93.1,16.5,15.1,29.4
+14.7,13.8,26.2,31.9,6.04,62.1,111.0,1877.0,6.44,20.9,8.98
+145.0,143.0,10.6,281.0,15.4,7.99,17.8,626.0,13.2,26.2,17.6
+115.0,75.0,22.5,25.9,1.79,15.3,61.0,349.0,4.14,17.3,25.7
+85.1,48.3,21.5,19.1,1.06,8.13,5.94,311.0,6.21,12.6,15.8
+36.8,12.4,17.8,20.0,9.06,7.43,16.3,982.0,10.1,26.9,33.1
+48.7,24.4,112.0,414.0,125.0,10.0,17.6,638.0,7.91,22.7,19.8
+40.3,18.8,10.3,145.0,21.3,19.5,30.8,599.0,6.21,22.3,27.6
+18.3,17.0,38.5,269.0,24.4,5.42,19.6,253.0,7.84,27.9,22.3
+39.2,27.1,12.1,147.0,8.43,1.0,2.57,89.0,9.22,16.4,48.7
+38.9,22.5,42.2,403.0,55.2,14.1,35.9,487.0,12.5,39.2,59.4
+10.0,5.88,17.2,172.0,15.7,19.6,32.8,578.0,8.43,16.7,20.9
+49.1,26.7,22.7,81.3,12.0,49.1,101.0,2227.0,9.39,22.9,20.4
+60.4,47.0,38.2,43.3,6.38,13.5,22.5,407.0,11.3,27.9,20.0
+51.9,32.2,13.2,137.0,25.9,29.7,43.3,355.0,11.7,51.4,40.3
+40.0,23.1,21.9,20.4,4.66,26.7,58.8,1946.0,6.21,22.9,24.4
+30.2,17.0,46.6,289.0,56.7,61.5,113.0,1670.0,17.8,17.6,25.9
+34.9,20.5,26.4,16.3,1.0,20.0,39.6,414.0,6.61,17.0,25.9
+35.2,21.7,10.8,132.0,10.3,4.07,12.9,547.0,56.7,115.0,154.0
+49.1,28.1,6.15,14.3,20.4,11.1,35.2,466.0,6.67,25.9,37.9
+73.0,31.9,20.0,22.1,1.0,11.5,22.7,791.0,16.3,34.9,34.9
+44.5,27.1,57.8,279.0,42.6,85.8,145.0,1640.0,8.98,26.7,21.1
+35.2,13.8,18.1,17.0,12.0,6.38,15.7,422.0,12.5,26.4,25.9
+86.6,57.8,6.67,27.9,20.0,28.9,56.7,2503.0,12.2,18.8,23.9
+35.9,18.6,20.9,62.1,12.7,124.0,449.0,4958.0,8.28,24.6,6.21
+40.7,31.3,12.7,127.0,13.8,16.7,26.9,382.0,33.7,70.4,67.9
+138.0,97.3,14.7,133.0,15.8,23.7,43.7,562.0,8.28,22.3,36.5
+26.4,10.2,31.1,29.2,6.26,31.3,42.6,523.0,4.14,69.8,1.53
+151.0,85.8,19.3,95.6,11.9,5.73,14.5,250.0,20.9,60.4,88.2
+158.0,109.0,44.1,73.7,12.3,18.9,37.2,679.0,9.22,28.9,26.7
+35.2,20.9,67.9,365.0,71.7,28.4,42.9,368.0,4.03,55.2,3.13
+113.0,122.0,19.6,23.3,8.66,11.0,31.3,267.0,7.23,20.0,26.9
+44.1,20.0,34.9,43.3,21.7,54.2,153.0,1459.0,9.47,17.8,44.9
+30.5,25.5,13.7,98.2,10.9,8.43,26.4,250.0,14.9,18.8,11.5
+118.0,31.6,22.3,248.0,20.9,3.13,13.5,583.0,30.5,85.8,204.0
+113.0,106.0,8.13,89.0,10.6,15.8,25.5,947.0,26.4,56.7,78.4
+68.5,54.2,20.2,44.5,9.65,13.2,47.4,289.0,8.9,32.5,52.8
+26.9,20.0,23.1,131.0,14.7,30.2,106.0,858.0,10.1,23.1,35.2
+33.7,22.7,12.5,158.0,7.84,96.5,141.0,1843.0,10.1,15.0,28.6
+54.7,29.2,17.9,51.9,23.1,23.9,40.3,730.0,10.0,22.9,20.0
+40.7,24.6,8.9,78.4,7.57,59.4,108.0,2813.0,12.5,15.4,30.8
+188.0,125.0,29.7,239.0,51.4,15.8,46.1,750.0,10.3,26.2,23.7
+63.8,40.3,29.4,66.1,19.3,58.3,89.8,1027.0,58.8,165.0,259.0
+30.0,10.4,23.3,22.9,4.41,39.2,88.2,2072.0,31.3,75.7,89.8
+31.9,18.6,15.1,17.9,1.0,14.1,13.5,429.0,9.14,27.6,31.1
+26.2,2.0,19.3,49.1,12.7,4.33,13.9,170.0,8.74,31.6,12.3
+33.4,21.5,15.8,22.5,4.49,35.9,53.3,528.0,6.15,25.5,42.2
+241.0,200.0,9.82,143.0,24.1,35.9,76.4,1811.0,36.2,73.7,81.3
+18.1,26.9,10.1,77.7,17.3,34.6,89.0,1346.0,7.04,18.4,16.5
+38.9,25.5,26.9,16.8,8.58,17.5,32.2,496.0,11.9,33.7,48.7
+33.7,17.3,25.0,26.9,10.6,112.0,189.0,2035.0,3.55,16.1,23.1
+39.6,25.9,17.0,16.3,12.6,17.6,34.6,820.0,4.61,15.5,27.9
+69.8,51.9,13.3,86.6,20.5,15.0,17.3,583.0,8.43,13.0,21.3
+133.0,79.9,22.5,16.4,6.32,78.4,109.0,375.0,11.0,24.4,19.5
+26.4,24.1,18.6,14.7,5.05,9.06,18.9,1104.0,8.74,17.5,12.5
+44.5,23.1,23.9,21.1,1.0,12.7,21.7,679.0,13.5,21.5,30.5
+31.3,17.2,17.5,16.1,11.8,39.6,61.5,1055.0,8.82,16.4,20.2
+109.0,108.0,22.5,20.7,2.5,22.1,94.7,583.0,81.3,204.0,257.0
+70.4,40.7,22.9,22.3,3.05,16.7,28.1,542.0,10.5,19.5,21.5
+34.6,19.5,106.0,478.0,68.5,23.1,24.6,429.0,10.7,20.9,28.9
+43.3,31.6,42.2,69.2,23.3,22.3,34.6,667.0,4.33,5.83,3.92
+106.0,63.8,20.5,24.4,14.6,17.5,31.3,528.0,20.4,56.2,51.4
+34.3,17.9,7.77,137.0,24.1,24.4,44.9,1700.0,71.7,207.0,193.0
+23.5,32.5,24.4,55.7,13.3,11.3,26.4,851.0,9.22,23.3,33.7
+42.9,29.4,1.0,129.0,13.3,157.0,453.0,6378.0,9.73,33.1,56.7
+65.5,28.1,19.8,163.0,20.0,21.9,38.5,474.0,5.28,21.1,21.1
+34.3,25.3,17.6,90.6,15.0,7.5,8.9,184.0,19.6,68.5,34.3
+40.7,17.9,106.0,562.0,78.4,2.86,12.9,433.0,7.57,25.5,17.0
+103.0,75.0,40.3,49.6,18.6,6.15,7.64,211.0,10.8,16.4,25.9
+158.0,114.0,27.1,27.9,10.6,106.0,244.0,4294.0,21.3,43.7,11.0
+34.3,20.4,57.8,626.0,71.7,49.1,74.3,1252.0,10.0,25.0,20.4
+37.9,16.8,15.5,13.9,5.38,34.9,50.0,1472.0,10.1,25.9,27.4
+37.9,22.9,6.79,15.4,11.2,41.4,65.5,449.0,4.22,23.3,41.8
+28.1,16.7,27.9,372.0,30.8,44.9,97.3,1731.0,4.14,10.8,3.82
+28.6,5.57,31.6,32.8,13.1,17.2,24.8,519.0,9.65,24.4,20.2
+173.0,104.0,21.3,155.0,20.0,14.9,44.5,1512.0,12.6,33.1,45.7
+67.9,62.1,4.78,11.4,1.75,11.4,31.3,466.0,13.2,33.4,25.5
+106.0,55.7,16.7,14.1,8.43,13.7,40.7,437.0,14.7,28.4,42.6
+21.9,16.1,59.4,207.0,37.9,6.21,14.1,730.0,9.39,26.2,30.5
+40.7,15.1,23.9,17.8,6.26,11.3,21.3,557.0,11.8,20.5,26.7
+164.0,91.4,13.1,20.0,6.98,13.6,31.3,723.0,27.1,50.9,79.9
+23.9,19.5,20.9,16.5,5.57,10.2,21.3,334.0,29.7,53.8,102.0
+28.6,24.4,20.9,39.2,11.7,4.66,15.7,704.0,9.47,23.9,41.4
+89.8,52.8,13.1,150.0,2.41,13.3,31.3,764.0,9.31,20.2,15.5
+57.3,53.8,18.3,24.4,4.41,7.64,16.0,991.0,9.65,24.1,41.8
+52.8,44.5,16.7,43.7,5.0,69.2,97.3,1407.0,9.31,16.5,34.3
+32.8,27.4,22.3,25.7,7.5,29.4,83.5,2642.0,9.82,18.9,31.9
+168.0,103.0,7.3,130.0,10.2,6.26,25.5,196.0,14.5,19.8,31.6
+106.0,65.5,24.4,30.2,12.3,34.6,65.5,1144.0,2.41,12.1,17.6
+52.3,26.2,22.1,172.0,19.6,18.9,35.5,470.0,8.66,16.0,27.4
+64.4,15.3,18.1,20.0,6.38,10.5,28.4,644.0,10.3,26.7,17.0
+66.1,31.6,18.8,28.9,9.65,13.3,27.1,449.0,8.66,18.1,25.3
+53.8,40.0,13.1,195.0,12.6,34.6,63.2,1165.0,11.9,18.1,17.8
+16.7,13.1,6.73,11.5,8.2,4.91,14.7,667.0,8.28,19.3,27.6
+25.3,17.6,27.6,28.4,7.84,17.5,42.2,382.0,11.2,19.6,18.6
+33.4,27.1,22.9,19.3,2.04,12.5,26.9,594.0,17.3,38.5,46.1
+79.9,53.8,63.2,403.0,53.8,8.98,15.3,1027.0,26.4,57.3,92.2
+44.1,30.8,23.5,22.5,1.1,101.0,164.0,1459.0,11.8,25.7,32.2
+50.9,78.4,78.4,279.0,47.0,20.9,27.9,470.0,10.9,20.2,7.1
+126.0,83.5,21.3,24.1,10.6,75.0,165.0,3619.0,14.5,38.5,7.3
+117.0,66.1,4.74,16.3,15.5,22.3,37.5,328.0,8.74,23.1,19.8
+14.6,18.6,3.16,5.67,19.1,21.3,33.1,308.0,1.0,1.65,4.29
+17.2,39.6,4.0,14.9,23.7,23.1,34.3,328.0,1.15,5.42,2.81
+15.8,15.1,2.33,213.0,24.6,18.1,26.2,286.0,25.7,44.1,3.11
+9.39,14.7,1.12,1.0,1.01,8.51,28.4,1165.0,1.06,12.9,4.37
+9.82,6.04,4.37,17.2,16.8,13.9,18.9,461.0,6.32,10.5,4.83
+9.65,10.6,1.0,253.0,42.9,10.1,18.9,770.0,3.19,1.01,13.1
+33.7,19.6,19.6,28.6,8.2,7.7,8.98,533.0,24.8,44.9,12.5
+18.8,19.6,7.99,215.0,3.72,4.91,19.3,1241.0,9.82,7.43,13.8
+39.2,17.2,7.23,200.0,33.4,11.5,17.9,407.0,14.9,19.8,18.4
+16.1,15.4,7.17,114.0,32.5,18.3,28.1,167.0,14.6,23.1,19.6
+46.6,12.2,4.7,157.0,32.2,9.82,20.2,1334.0,3.08,1.0,1.96
+50.9,24.1,2.5,202.0,30.5,6.1,11.8,1275.0,1.0,1.63,1.02
+28.6,20.2,7.04,195.0,12.4,23.7,40.0,557.0,3.89,20.9,30.2
+13.1,40.0,5.0,29.4,38.5,13.1,17.2,262.0,6.21,12.0,6.21
+48.7,22.5,8.82,93.9,48.3,32.5,50.5,1310.0,1.04,6.85,85.8
+37.2,19.5,36.8,352.0,158.0,7.77,21.3,692.0,10.6,17.5,27.6
+11.3,6.21,14.2,23.7,12.5,26.7,36.8,340.0,17.3,41.8,44.1
+47.8,18.1,14.1,157.0,22.7,8.2,16.5,219.0,1.0,1.0,9.73
+17.5,29.4,6.32,113.0,12.7,10.4,23.1,400.0,10.5,21.9,2.25
+38.2,20.5,10.2,93.9,16.4,28.4,50.0,422.0,1.43,1.3,4.07
+2.55,12.4,5.52,122.0,42.9,18.9,42.2,965.0,2.81,17.9,74.3
+52.8,21.3,12.4,86.6,35.2,14.1,25.7,717.0,5.09,7.77,4.37
+41.8,45.3,3.72,241.0,28.1,7.57,11.4,661.0,13.2,23.7,12.6
+67.3,24.8,11.7,704.0,93.9,22.7,40.7,365.0,6.21,11.0,16.1
+13.7,10.1,13.1,48.7,30.0,19.3,28.4,644.0,3.25,1.96,7.84
+15.0,39.6,24.4,55.7,30.2,24.6,28.9,163.0,1.25,6.15,4.03
+21.9,18.3,7.77,9.56,19.3,11.3,25.9,461.0,1.37,1.0,8.82
+67.9,40.0,24.4,64.4,4.26,58.8,87.4,533.0,6.44,35.2,54.2
+10.2,13.5,13.8,233.0,51.9,17.3,49.6,1715.0,7.1,19.8,28.9
+15.8,22.1,12.0,17.9,78.4,2.21,10.7,799.0,8.98,19.5,11.3
+85.1,106.0,9.56,14.1,51.9,30.8,43.3,319.0,24.8,79.9,69.2
+57.8,16.5,15.4,40.0,135.0,16.7,25.5,382.0,4.07,5.62,10.3
+9.56,24.4,5.67,17.8,28.4,9.65,12.1,533.0,9.47,17.6,12.0
+27.9,27.4,3.79,1.01,9.22,8.13,20.5,487.0,6.1,20.9,52.3
+17.8,17.2,2.02,202.0,19.3,13.2,13.2,692.0,1.45,6.44,2.69
+34.9,15.0,7.17,176.0,47.0,10.7,18.6,453.0,30.0,48.3,22.7
+75.7,17.6,1.43,340.0,29.7,7.23,21.7,644.0,11.5,21.1,2.0
+38.5,16.0,1.0,806.0,106.0,2.74,13.1,441.0,8.98,15.0,1.51
+34.3,36.5,21.7,183.0,48.7,16.7,19.5,449.0,7.91,11.7,5.0
+20.4,15.7,10.2,229.0,54.7,29.4,61.0,414.0,4.18,5.52,2.15
+22.5,19.5,8.2,31.6,51.4,32.5,40.3,474.0,5.83,15.0,1.01
+73.0,24.1,14.1,29.2,31.1,35.2,75.0,730.0,8.9,16.3,70.4
+34.0,10.8,4.18,35.2,4.96,32.2,46.1,343.0,3.11,1.07,5.67
+50.0,25.5,9.73,10.9,30.0,31.6,38.9,217.0,1.0,1.0,13.0
+48.7,25.5,11.3,77.0,23.5,3.92,13.1,396.0,7.91,54.2,349.0
+61.0,25.5,8.74,99.1,37.9,6.92,22.7,1554.0,1.0,1.0,4.53
+64.4,33.4,51.9,418.0,124.0,19.1,34.9,255.0,42.9,74.3,20.4
+65.5,29.7,6.61,17.0,28.9,13.3,29.4,1104.0,10.5,27.9,163.0
+43.7,13.3,3.92,231.0,16.4,20.0,38.5,322.0,3.52,2.5,10.3
+33.4,23.3,2.0,31.1,15.4,23.1,40.3,337.0,18.8,35.2,6.21
+13.5,10.7,18.3,27.4,8.51,1.0,2.5,14.2,3.92,12.7,83.5
+11.7,4.37,6.61,153.0,26.4,37.9,118.0,947.0,48.3,102.0,145.0
+12.5,19.3,33.1,322.0,294.0,35.2,51.4,231.0,8.9,15.3,13.9
+84.3,35.2,8.13,153.0,24.1,5.57,17.6,547.0,6.67,6.92,17.5
+38.2,15.8,9.22,188.0,36.2,9.65,33.4,799.0,1.0,1.0,6.92
+28.1,9.22,12.1,11.1,55.2,45.7,139.0,1310.0,19.6,27.4,24.8
+11.7,8.74,13.0,14.3,45.7,31.1,56.7,1065.0,1.6,13.2,4.7
+1.0,3.46,8.58,231.0,41.4,25.5,29.2,429.0,30.8,126.0,239.0
+136.0,48.7,20.9,692.0,178.0,29.2,45.3,965.0,9.91,19.6,10.5
+19.5,13.8,16.4,528.0,150.0,2.86,1.0,147.0,11.0,5.78,13.9
+42.9,12.4,58.8,191.0,101.0,22.5,38.9,764.0,14.1,15.4,21.1
+5.28,5.57,4.91,8.51,1.11,10.1,38.5,1762.0,24.6,63.8,85.8
+79.1,50.5,50.0,328.0,129.0,9.31,16.1,588.0,1.0,1.0,6.61
+81.3,16.8,15.5,61.5,18.6,8.58,15.7,235.0,1.0,1.53,10.1
+32.2,26.9,3.4,231.0,33.7,69.8,110.0,820.0,18.3,26.2,12.6
+40.0,20.0,7.04,33.7,15.3,17.3,30.2,483.0,11.4,15.4,17.2
+19.6,20.2,13.3,172.0,41.8,21.7,38.9,505.0,1.0,1.0,5.62
+50.9,28.1,27.6,284.0,79.9,24.1,41.0,514.0,3.75,1.0,3.05
+41.4,27.1,39.2,59.4,61.5,17.5,42.6,487.0,18.3,39.2,5.78
+58.8,31.9,19.1,37.9,49.6,63.2,112.0,914.0,15.3,22.3,5.52
+64.9,21.1,6.49,143.0,44.1,34.0,66.1,655.0,22.1,26.7,4.45
+62.1,32.8,24.4,225.0,40.7,10.8,18.4,319.0,34.0,41.4,24.8
+32.2,28.1,31.3,429.0,193.0,7.43,26.2,466.0,8.82,23.3,10.6
+63.8,64.4,4.33,163.0,34.6,8.51,11.4,610.0,5.57,10.7,9.47
+22.1,26.7,10.4,126.0,7.43,24.6,42.9,322.0,1.7,19.6,10.2
+63.2,38.9,76.4,349.0,105.0,31.9,37.5,302.0,1.0,3.85,2.64
+132.0,54.7,15.5,25.0,17.9,11.0,21.3,557.0,7.43,18.6,15.1
+26.9,24.4,8.28,85.8,12.3,15.8,27.9,528.0,6.44,9.91,17.9
+39.2,17.6,1.73,5.62,6.21,16.1,32.8,757.0,15.1,12.6,11.8
+42.9,17.6,8.2,204.0,59.9,6.85,34.0,1568.0,8.28,26.7,1.15
+101.0,100.0,16.1,9.73,44.9,34.3,49.6,217.0,8.9,14.2,6.44
+73.0,23.1,5.88,221.0,34.3,14.3,26.2,426.0,9.14,3.43,8.2
+25.5,23.5,20.7,34.9,50.9,44.1,71.0,604.0,7.04,41.4,319.0
+33.7,16.8,12.3,131.0,44.1,28.6,42.6,279.0,6.49,16.8,12.2
+205.0,71.0,4.53,17.0,47.4,13.8,37.9,1794.0,13.7,23.3,62.6
+24.1,28.1,15.1,217.0,41.0,48.7,135.0,1055.0,10.7,16.3,9.47
+34.0,21.3,25.0,655.0,112.0,19.6,21.1,276.0,2.71,21.3,109.0
+57.3,23.5,31.9,322.0,58.8,19.8,35.5,835.0,21.5,33.1,16.1
+55.2,22.3,10.1,150.0,28.6,6.38,15.1,422.0,14.6,18.6,1.84
+77.0,21.1,2.33,7.17,3.13,38.5,119.0,1472.0,13.6,15.5,11.3
+59.4,41.4,68.5,175.0,44.5,70.4,100.0,407.0,9.06,15.5,9.65
+9.39,27.9,43.3,202.0,110.0,9.65,30.5,679.0,8.74,13.2,8.98
+16.5,33.4,7.7,120.0,46.1,14.1,27.6,414.0,7.1,5.99,13.0
+61.0,40.7,8.51,142.0,25.5,22.9,40.3,255.0,5.83,1.91,10.6
+63.8,34.9,1.0,241.0,19.8,7.99,18.8,1124.0,17.2,31.1,3.31
+45.7,12.1,4.18,186.0,21.1,15.8,20.2,311.0,10.7,10.9,16.1
+39.2,10.0,12.1,38.5,48.7,20.4,30.0,284.0,20.9,20.7,8.98
+120.0,85.8,6.67,13.1,35.9,22.7,46.1,453.0,40.3,77.0,37.2
+5.78,1.01,2.21,538.0,38.9,16.8,15.4,461.0,5.38,11.9,9.22
+35.2,10.4,46.1,289.0,89.0,1.86,6.44,161.0,18.6,29.2,19.8
+19.6,46.6,43.7,88.2,39.6,20.7,37.9,281.0,8.9,10.7,1.04
+34.0,18.8,8.43,97.3,56.7,11.7,31.1,533.0,2.62,12.7,1.45
+47.4,28.9,6.38,241.0,34.9,10.3,13.6,1009.0,33.4,54.7,15.8
+44.1,28.4,14.1,48.3,43.7,60.4,119.0,1459.0,1.1,1.7,5.73
+119.0,29.4,1.54,1.26,13.0,9.22,22.1,1186.0,15.5,25.5,11.4
+53.8,23.9,16.4,79.1,59.9,41.4,63.8,1114.0,17.2,22.1,14.6
+164.0,72.3,10.6,196.0,50.0,25.9,37.9,519.0,10.4,17.6,1.75
+42.2,22.3,14.5,340.0,63.8,5.28,10.6,382.0,10.8,9.22,8.51
+71.0,66.7,4.07,9.82,23.5,15.3,17.9,583.0,16.5,25.5,7.04
+59.9,32.8,11.4,151.0,17.5,20.7,25.3,186.0,22.7,36.8,3.96
+41.4,28.9,21.3,16.5,84.3,29.2,64.9,3398.0,1.32,48.3,6.26
+25.9,19.3,50.9,698.0,204.0,10.3,28.6,757.0,8.82,3.05,2.67
+78.4,44.1,44.1,153.0,51.9,63.8,138.0,1155.0,9.91,13.8,9.56
+47.0,57.3,3.55,13.6,20.0,19.6,32.5,349.0,20.0,35.2,12.9
+17.3,28.9,15.0,16.5,4.74,8.98,37.2,710.0,12.7,4.83,8.13
+53.3,19.8,5.0,21.5,40.0,3.34,16.1,1999.0,4.53,39.2,67.9
+20.5,15.0,9.56,75.0,17.8,15.5,21.3,777.0,17.2,20.2,8.28
+55.2,27.4,3.65,12.5,57.8,32.2,44.1,233.0,4.7,13.1,12.4
+84.3,23.1,6.1,227.0,40.7,75.0,114.0,2072.0,7.7,19.1,10.8
+135.0,198.0,4.87,215.0,27.4,16.4,61.0,2393.0,10.6,18.1,3.49
+25.3,17.5,16.5,30.8,17.6,11.8,25.3,599.0,5.47,11.3,6.15
+42.6,23.3,11.2,137.0,11.2,17.0,34.9,505.0,12.2,20.7,7.04
+71.0,40.7,17.0,136.0,10.1,76.4,122.0,2247.0,15.0,23.5,8.74
+62.6,26.4,17.2,244.0,62.1,10.6,17.2,505.0,13.0,35.2,18.1
+51.4,25.5,47.0,172.0,139.0,38.5,54.7,1298.0,3.11,17.8,18.9
+63.8,24.6,2.41,5.88,13.5,10.6,16.7,533.0,9.91,18.3,1.0
+73.7,34.9,30.0,84.3,41.8,145.0,375.0,2350.0,14.2,12.1,2.53
+46.6,19.3,3.4,1.01,1.15,17.8,40.3,355.0,11.5,13.9,5.19
+45.7,14.9,15.4,429.0,58.8,5.42,22.1,204.0,14.2,21.1,25.3
+86.6,36.5,6.15,111.0,23.1,50.0,75.7,1000.0,16.3,25.0,11.9
+30.5,23.1,19.8,64.9,26.2,11.3,22.7,322.0,1.0,11.7,15.4
+35.2,9.14,25.7,18.6,33.7,45.7,74.3,710.0,17.8,38.2,28.6
+211.0,88.2,11.9,157.0,24.4,45.7,94.7,1715.0,14.1,7.5,13.6
+43.7,21.5,5.28,302.0,28.6,36.2,88.2,1963.0,18.8,25.7,10.1
+19.5,13.8,7.17,22.3,37.5,12.2,34.9,644.0,19.3,32.5,12.4
+118.0,64.4,10.4,129.0,3.0,6.73,14.9,466.0,3.37,2.0,1.6
+64.4,24.8,10.8,153.0,35.9,111.0,231.0,1144.0,9.82,18.9,6.1
+43.7,26.7,31.9,66.1,18.9,18.6,31.9,382.0,12.4,19.3,10.9
+81.3,39.6,54.7,231.0,107.0,6.49,20.0,1065.0,19.6,20.2,8.66
+58.8,28.1,6.98,18.3,50.5,13.8,22.7,257.0,14.3,27.6,43.3
+21.7,18.6,29.2,414.0,168.0,5.73,15.3,382.0,34.0,68.5,43.3
+62.1,27.1,8.35,115.0,27.1,18.8,33.7,843.0,1.11,38.5,1.81
+24.6,25.5,14.7,81.3,43.7,73.7,184.0,1554.0,15.8,27.4,12.1
+6.1,21.3,69.8,125.0,196.0,10.9,44.5,1322.0,13.8,5.94,8.82
+154.0,86.6,9.14,189.0,35.5,20.4,36.8,621.0,10.5,14.9,11.8
+73.7,34.9,4.78,22.1,56.7,11.7,33.7,743.0,22.1,32.5,13.6
+70.4,37.5,42.9,136.0,59.4,36.8,75.0,538.0,25.5,27.6,9.47
+77.0,26.4,13.7,500.0,75.7,11.8,36.5,487.0,19.5,23.3,9.22
+11.8,22.5,9.39,122.0,12.9,37.2,54.7,667.0,9.39,14.5,3.68
+18.1,22.7,19.6,392.0,143.0,17.6,38.9,679.0,11.3,11.9,13.5
+32.5,25.7,12.9,308.0,72.3,33.4,75.7,1486.0,7.99,17.9,130.0
+49.6,46.1,10.3,453.0,66.1,17.5,23.1,389.0,20.4,22.3,10.2
+41.8,23.9,5.83,514.0,69.8,4.41,13.3,157.0,13.1,23.9,7.37
+20.5,32.5,11.1,289.0,64.9,19.8,34.3,337.0,15.3,8.58,10.3
+58.8,17.5,9.73,9.47,27.4,27.9,50.5,557.0,19.1,25.0,10.4
+41.4,26.4,3.08,24.4,19.6,30.2,48.3,385.0,8.58,8.51,8.13
+34.9,16.5,15.8,153.0,41.4,4.74,9.91,939.0,10.2,6.61,8.98
+20.0,19.1,24.4,578.0,97.3,10.7,26.9,835.0,7.04,13.8,5.33
+179.0,27.9,4.26,146.0,45.7,18.6,32.2,528.0,3.62,1.86,6.98
+51.9,30.2,3.46,271.0,48.7,23.3,40.0,422.0,11.4,35.2,17.3
+92.2,69.8,55.2,375.0,130.0,69.8,111.0,1018.0,1.0,6.73,5.52
+48.3,15.7,4.78,13.6,24.8,3.65,15.5,191.0,1.0,1.0,8.06
+85.1,27.9,1.36,158.0,6.67,16.4,34.0,410.0,44.9,75.7,26.9
+36.5,19.8,10.8,237.0,23.5,46.1,62.6,1407.0,20.0,32.5,12.7
+73.7,27.6,20.5,19.6,21.1,26.7,62.6,1334.0,20.2,36.5,6.79
+19.3,27.4,34.3,445.0,49.1,19.3,42.9,685.0,36.2,63.2,30.8
+28.9,21.7,4.53,22.7,7.5,4.49,21.9,1055.0,10.8,14.7,12.4
+50.9,120.0,9.56,44.5,14.2,50.0,89.8,710.0,22.1,26.9,14.1
+73.0,28.6,8.28,6.79,25.3,26.2,30.5,289.0,11.2,18.9,9.31
+62.1,27.1,6.98,13.1,59.4,36.8,49.1,791.0,39.6,77.7,52.8
+34.9,24.8,16.8,188.0,53.3,10.0,12.1,491.0,23.1,25.5,10.7
+66.1,63.8,16.0,138.0,26.7,16.0,34.9,505.0,12.0,3.68,14.6
+26.9,17.3,12.7,90.6,20.0,10.1,27.6,410.0,8.43,9.47,17.2
+78.4,21.1,9.06,264.0,53.3,157.0,331.0,1843.0,11.3,17.3,13.5
+37.5,31.1,6.44,284.0,34.6,18.6,34.6,557.0,24.4,12.0,7.17
+55.2,10.8,4.18,45.3,21.3,30.2,58.8,470.0,11.2,8.06,13.2
+55.7,24.8,7.57,496.0,55.7,16.4,42.2,441.0,21.1,36.8,8.82
+49.1,18.4,10.3,53.3,11.7,14.5,30.2,433.0,9.47,17.2,9.31
+61.5,21.1,6.61,14.5,30.0,10.2,15.0,343.0,10.6,18.6,15.1
+3.37,11.7,20.9,58.3,46.1,26.9,42.6,400.0,1.7,5.47,2.76
+181.0,93.9,7.1,22.1,66.7,45.3,64.4,906.0,8.58,11.1,3.85
+16.0,25.7,7.99,143.0,6.1,23.3,47.8,991.0,1.0,2.33,1.0
+27.1,41.8,10.0,117.0,23.3,34.9,50.5,365.0,1.0,16.4,11.0
+131.0,72.3,6.04,193.0,52.8,11.9,23.9,313.0,6.85,7.77,11.5
+65.5,31.1,17.2,124.0,7.37,100.0,305.0,2148.0,34.3,46.6,13.7
+6.61,18.8,28.4,67.3,86.6,5.33,25.7,1640.0,1.0,5.09,9.73
+27.6,18.6,1.0,292.0,4.74,2.35,2.97,1.0,8.28,13.6,14.6
+71.0,38.9,9.56,181.0,41.8,38.5,109.0,717.0,12.5,12.6,10.7
+98.2,36.8,1.81,28.9,16.7,24.8,42.6,362.0,17.2,32.2,13.0
+50.5,23.5,6.98,12.2,38.9,28.6,64.4,1046.0,31.1,48.3,13.3
+112.0,47.8,9.31,528.0,183.0,10.9,27.1,528.0,13.1,14.6,5.78
+83.5,54.2,1.84,4.53,15.3,6.98,18.9,764.0,22.9,25.9,2.17
+33.4,24.6,12.1,164.0,34.9,47.8,85.8,2329.0,23.7,43.7,26.2
+106.0,47.8,8.06,9.39,38.9,11.7,23.1,604.0,11.5,12.2,9.91
+25.3,40.0,4.14,155.0,27.6,12.4,19.8,710.0,8.9,18.4,9.31
+10.8,19.5,10.1,164.0,47.8,18.3,31.9,372.0,24.4,35.2,7.3
+3.16,4.26,19.5,32.2,40.0,4.7,48.3,509.0,24.4,29.2,14.7
+79.9,34.0,13.0,209.0,50.9,11.3,24.4,487.0,16.4,18.6,11.9
+93.1,44.9,57.8,500.0,136.0,41.0,76.4,2227.0,20.0,25.3,9.14
+37.5,18.3,16.3,1.15,9.22,13.5,25.3,362.0,6.85,20.9,24.8
+35.9,16.1,20.5,50.9,82.0,21.1,28.9,349.0,8.9,26.7,4.57
+107.0,30.0,12.5,200.0,20.7,7.91,53.8,2072.0,13.3,33.7,2.57
+102.0,32.5,7.64,246.0,59.4,29.2,44.5,319.0,15.3,14.2,10.4
+32.8,26.7,11.9,196.0,50.5,12.5,17.3,542.0,27.1,30.0,7.84
+100.0,27.1,34.6,396.0,103.0,64.4,124.0,1540.0,20.0,31.9,12.4
+90.6,58.3,14.1,305.0,26.7,33.7,60.4,1104.0,1.0,7.5,6.38
+100.0,25.7,77.7,246.0,37.2,8.06,8.74,509.0,15.8,28.6,40.0
+75.7,29.7,7.5,149.0,29.2,37.2,58.8,334.0,7.99,22.7,8.28
+53.8,20.7,59.4,337.0,223.0,13.2,31.1,533.0,29.7,40.7,12.1
+90.6,44.5,6.04,170.0,21.7,16.3,25.9,685.0,13.6,14.7,8.2
+69.8,47.4,11.1,372.0,18.9,4.61,26.4,632.0,13.2,25.0,9.56
+193.0,61.0,9.31,15.8,29.7,10.4,24.8,667.0,12.7,21.7,6.61
+85.8,22.3,16.8,66.7,36.8,25.3,51.9,547.0,25.9,31.9,17.9
+67.9,14.9,80.6,237.0,61.0,37.5,66.7,2666.0,15.3,39.6,12.4
+19.1,9.82,12.0,10.7,27.4,72.3,90.6,858.0,9.65,17.3,20.5
+16.1,15.3,13.9,73.0,24.6,16.8,30.2,385.0,15.4,25.9,23.5
+95.6,28.9,7.64,14.2,23.7,13.2,30.8,730.0,14.5,34.9,41.8
+49.1,21.3,1.83,297.0,49.6,24.4,46.6,1827.0,33.1,38.2,17.0
+18.9,26.2,24.8,264.0,69.8,31.1,93.9,1134.0,12.9,9.65,10.0
+74.3,36.5,5.42,244.0,33.7,12.2,20.7,235.0,5.83,25.0,120.0
+25.7,24.6,19.5,117.0,79.1,10.0,25.7,799.0,17.2,26.2,15.8
+61.0,31.1,15.8,145.0,41.8,27.9,45.7,359.0,14.6,13.9,5.78
+27.1,16.4,37.9,552.0,80.6,20.9,40.3,407.0,10.7,19.6,12.2
+151.0,48.7,36.8,89.0,76.4,21.9,38.9,382.0,11.4,18.6,6.92
+179.0,77.0,13.3,250.0,42.2,28.4,47.4,491.0,16.0,9.82,9.22
+154.0,136.0,17.2,42.6,78.4,4.29,23.5,1000.0,17.3,12.4,5.88
+73.7,36.2,3.43,3.25,1.01,7.37,16.1,1263.0,17.3,11.3,18.3
+95.6,42.9,40.7,40.3,58.3,8.9,16.7,523.0,15.8,15.4,7.04
+55.2,51.4,18.1,82.8,20.4,10.6,21.3,828.0,8.58,26.4,6.44
+36.5,10.5,23.3,211.0,28.6,11.3,49.6,2618.0,12.0,20.4,2.89
+30.5,15.7,15.7,141.0,27.6,15.5,20.4,343.0,5.78,18.4,10.8
+158.0,37.2,15.8,90.6,28.9,5.28,12.1,914.0,5.73,18.6,10.3
+49.6,31.9,5.83,305.0,38.9,19.6,23.1,271.0,21.9,28.9,5.0
+89.8,35.9,22.7,644.0,111.0,3.55,2.97,28.6,9.91,20.7,1.78
+35.9,18.1,9.56,117.0,27.4,8.74,15.7,667.0,10.6,21.3,7.7
+67.9,28.9,11.3,69.2,27.6,54.2,94.7,1155.0,11.5,17.9,11.9
+89.0,31.6,15.0,32.8,41.8,27.4,43.7,379.0,9.73,11.3,1.01
+57.8,21.7,36.2,588.0,118.0,27.4,43.7,418.0,14.6,26.9,5.0
+85.1,38.2,17.8,313.0,46.1,121.0,255.0,1625.0,11.8,13.6,8.74
+24.8,21.5,4.7,94.7,23.1,15.4,16.1,325.0,21.7,37.5,10.3
+63.8,19.6,4.49,227.0,27.1,13.2,13.7,433.0,11.3,21.7,12.9
+78.4,33.1,12.0,274.0,20.4,27.1,34.3,279.0,22.5,36.2,6.44
+73.7,32.8,51.9,528.0,157.0,25.5,60.4,1084.0,9.14,12.0,7.43
+117.0,40.3,1.43,13.5,55.2,17.8,30.8,500.0,18.9,24.1,12.3
+117.0,78.4,18.4,57.8,16.4,7.64,28.9,638.0,1.64,13.2,3.82
+34.3,20.5,16.0,23.9,48.7,21.5,68.5,1114.0,16.4,8.51,9.31
+179.0,34.6,26.2,29.7,15.5,6.73,62.6,1176.0,23.5,28.1,5.73
+106.0,39.2,17.9,101.0,38.2,49.6,93.1,1420.0,15.5,31.6,11.9
+39.2,17.8,26.2,426.0,106.0,110.0,172.0,1197.0,8.98,13.2,15.4
+71.7,25.7,5.73,246.0,48.3,16.0,79.9,1346.0,13.6,20.7,3.31
+13.9,21.1,15.3,235.0,45.3,24.1,29.4,322.0,15.1,7.57,4.26
+91.4,80.6,4.7,191.0,44.5,48.7,69.2,379.0,16.0,33.1,15.5
+50.5,13.6,10.6,114.0,19.8,18.1,28.4,407.0,1.0,5.83,1.78
+34.0,15.7,9.73,227.0,33.4,24.6,43.3,583.0,13.1,22.5,19.5
+48.7,19.5,22.3,121.0,43.3,110.0,328.0,1114.0,25.5,22.5,19.6
+84.3,34.6,27.1,85.1,47.0,8.58,20.7,632.0,13.2,13.8,3.25
+44.5,18.1,10.6,145.0,41.8,10.8,29.2,207.0,12.0,22.5,4.29
+31.3,21.3,7.5,1.0,1018.0,4.66,14.7,461.0,9.47,16.8,14.9
+79.1,59.4,10.7,158.0,36.5,10.9,34.0,644.0,19.1,26.9,9.22
+42.6,21.7,19.1,219.0,22.1,21.5,56.2,1395.0,10.2,9.56,12.6
+51.4,38.9,25.7,20.0,7.7,32.5,72.3,1186.0,16.5,31.6,12.5
+63.8,51.4,10.2,40.3,25.0,46.1,98.2,1526.0,13.3,17.2,6.85
+14.2,18.4,54.2,385.0,215.0,17.0,27.6,583.0,10.8,14.1,12.4
+42.9,20.4,5.78,213.0,24.4,110.0,316.0,1843.0,10.7,19.8,9.56
+26.4,17.2,11.2,204.0,39.6,43.7,74.3,1134.0,31.3,45.7,10.9
+6.21,4.87,4.29,221.0,14.9,28.4,47.4,400.0,15.5,22.1,7.17
+31.6,20.7,4.91,274.0,34.6,20.2,66.1,3820.0,23.9,23.3,6.26
+78.4,25.7,10.7,466.0,46.6,11.8,17.6,334.0,8.06,17.2,18.6
+30.0,9.31,28.6,131.0,56.7,41.4,89.8,2308.0,18.8,27.9,5.78
+50.5,18.8,7.04,18.4,24.4,15.4,25.0,271.0,19.5,30.5,9.14
+23.9,20.0,2.67,3.59,11.3,16.7,26.9,316.0,17.0,25.9,11.2
+73.7,23.3,7.17,21.3,18.9,15.5,23.7,588.0,16.4,13.1,6.73
+11.0,14.7,19.1,53.8,32.8,16.0,18.9,542.0,20.4,17.8,24.6
+65.5,25.3,15.1,117.0,23.9,18.6,23.3,474.0,11.3,16.3,8.35
+21.7,8.2,14.6,202.0,23.5,18.3,30.5,496.0,16.0,24.8,11.9
+63.8,18.4,9.22,322.0,51.4,21.7,84.3,1486.0,12.1,23.3,8.58
+104.0,60.4,7.84,158.0,36.8,23.5,41.8,340.0,7.43,16.5,12.4
+25.7,18.4,6.04,334.0,32.8,79.9,125.0,1124.0,14.1,9.65,4.07
+17.3,21.7,10.6,217.0,41.8,13.1,22.9,487.0,32.2,36.2,9.14
+8.43,36.8,10.1,418.0,45.3,14.2,25.9,717.0,5.19,26.4,54.7
+57.8,16.5,11.5,235.0,32.5,24.8,31.9,437.0,8.28,28.4,23.7
+91.4,104.0,7.77,145.0,61.0,70.4,138.0,982.0,20.0,31.6,6.04
+79.9,36.5,10.7,16.3,37.2,8.51,21.1,777.0,18.8,38.2,133.0
+81.3,32.5,21.9,59.4,38.5,9.06,23.3,400.0,10.0,23.1,3.79
+107.0,30.5,17.9,241.0,66.7,5.28,18.9,362.0,21.3,28.6,14.5
+99.1,36.2,2.84,15.8,28.1,21.9,49.1,1252.0,22.9,25.5,10.4
+93.9,45.3,21.3,25.3,28.6,12.6,31.1,478.0,6.73,20.4,1.6
+38.9,18.4,16.1,422.0,68.5,20.9,40.0,519.0,9.47,23.3,1.0
+78.4,20.9,5.14,255.0,30.8,22.1,36.5,392.0,20.0,38.2,6.15
+33.1,26.4,10.4,24.4,31.6,31.3,52.8,410.0,14.7,12.1,9.39
+60.4,22.5,14.9,106.0,31.1,62.6,84.3,1009.0,14.2,7.91,2.84
+70.4,23.1,15.4,145.0,39.6,67.9,106.0,1275.0,21.7,32.2,2.76
+51.9,29.4,10.7,113.0,37.5,34.0,58.8,692.0,7.91,2.37,9.47
+93.9,27.4,9.39,32.2,57.8,31.1,76.4,1334.0,16.7,25.7,3.13
+93.9,30.2,9.56,322.0,48.3,14.5,24.4,931.0,1.18,5.78,9.14
+33.1,9.31,14.6,311.0,54.2,10.5,30.5,1540.0,23.7,47.0,9.39
+37.9,19.6,17.2,91.4,25.9,31.1,44.9,562.0,3.02,18.3,15.1
+45.3,27.9,26.4,136.0,51.4,8.58,21.7,457.0,29.2,41.4,13.1
+105.0,80.6,7.91,229.0,42.2,5.42,22.9,1370.0,10.8,19.8,1.29
+75.0,31.9,12.4,119.0,33.1,31.9,39.6,407.0,32.5,26.4,10.1
+98.2,21.5,12.0,389.0,49.1,14.1,24.4,820.0,18.3,62.1,29.7
+78.4,24.8,8.98,111.0,44.5,8.58,19.3,1018.0,8.82,16.8,8.35
+147.0,31.1,11.5,129.0,56.7,47.4,147.0,1731.0,4.91,4.29,21.3
+14.5,13.0,8.74,21.5,27.4,5.83,38.9,1208.0,29.7,63.2,57.8
+121.0,33.7,22.3,225.0,72.3,112.0,217.0,1370.0,1.64,24.1,3.79
+89.8,32.8,17.0,23.7,34.9,37.2,49.6,461.0,22.9,29.2,9.91
+31.3,13.1,15.5,153.0,27.1,15.4,20.9,352.0,8.9,13.0,4.61
+27.9,17.8,11.5,167.0,22.5,4.66,19.8,1018.0,27.1,38.9,16.7
+59.9,16.4,25.5,813.0,106.0,23.5,54.2,882.0,19.3,29.4,7.04
+44.5,20.7,9.14,125.0,20.2,10.2,22.9,331.0,19.5,17.0,9.47
+85.1,22.9,23.5,235.0,78.4,33.7,58.8,491.0,8.13,6.1,5.23
+191.0,84.3,1.0,743.0,25.0,30.8,44.1,939.0,18.6,22.1,3.02
+106.0,22.9,14.1,470.0,86.6,20.9,34.3,542.0,10.9,20.5,6.61
+40.3,19.6,17.0,79.9,39.2,33.7,114.0,2480.0,23.1,34.9,11.0
+55.7,49.6,8.98,142.0,29.2,20.0,42.9,698.0,14.3,15.1,11.2
+45.3,29.2,23.7,18.8,17.5,33.1,57.8,578.0,3.82,7.1,6.38
+108.0,79.9,18.9,35.9,17.8,5.42,8.35,66.7,13.3,29.4,13.5
+108.0,51.4,13.5,168.0,24.6,6.44,17.0,437.0,15.5,27.6,5.94
+59.9,19.1,11.4,184.0,34.6,19.3,61.0,1310.0,7.17,10.8,10.4
+69.8,22.3,15.8,35.2,9.56,9.56,31.6,965.0,14.6,28.4,8.98
+85.1,27.6,17.9,168.0,12.5,15.3,38.9,519.0,26.9,36.5,7.7
+120.0,48.3,26.2,322.0,102.0,8.43,16.3,679.0,31.1,38.5,11.8
+151.0,44.5,41.8,63.2,75.0,16.0,24.6,403.0,31.3,29.2,25.5
+120.0,99.1,11.5,59.9,25.9,29.2,44.5,346.0,25.0,38.5,6.44
+131.0,115.0,10.3,135.0,55.2,9.91,19.8,599.0,12.3,9.39,14.7
+133.0,57.3,15.0,223.0,44.9,14.3,23.3,385.0,16.0,25.7,13.3
+106.0,35.5,21.1,209.0,42.6,24.6,88.2,3960.0,13.5,15.0,1.0
+22.9,17.9,10.2,85.8,53.8,52.8,86.6,813.0,10.8,10.1,2.33
+35.9,16.8,10.8,165.0,30.5,12.6,12.3,248.0,9.73,13.3,10.5
+47.0,44.9,15.7,26.2,41.0,15.7,30.0,389.0,20.9,23.1,11.3
+38.9,26.9,26.9,31.6,47.0,26.7,61.0,1144.0,17.5,34.0,1.0
+54.7,28.4,12.6,250.0,30.5,24.6,35.2,389.0,13.1,32.8,11.5
+46.6,20.4,34.3,262.0,63.8,11.3,23.7,255.0,13.2,20.5,4.26
+78.4,32.8,9.65,200.0,49.6,23.9,31.9,211.0,13.8,14.2,11.4
+49.1,24.8,10.9,28.9,20.0,41.0,78.4,1009.0,13.3,23.7,10.3
+59.4,18.3,16.8,28.9,11.8,34.6,46.1,375.0,17.8,23.9,14.3
+109.0,38.2,4.1,198.0,25.3,6.32,8.66,791.0,31.9,37.5,4.29
+78.4,76.4,5.78,2.23,1.12,5.0,10.8,594.0,18.1,17.6,13.8
+39.2,12.3,13.2,129.0,32.5,10.5,27.4,644.0,43.3,70.4,17.5
+89.0,34.9,7.57,294.0,50.9,4.83,19.1,649.0,40.3,65.5,23.3
+74.3,17.8,13.1,21.9,24.6,6.85,21.3,661.0,10.9,15.1,2.69
+47.4,22.9,26.7,30.5,37.2,3.75,26.2,281.0,14.3,37.9,2.71
+60.4,24.8,13.3,18.6,53.3,9.06,31.3,500.0,22.7,15.3,7.77
+80.6,20.9,21.9,15.0,2.13,26.7,37.5,414.0,12.7,17.5,5.19
+21.5,18.1,11.9,28.9,12.7,12.3,21.9,305.0,6.32,2.48,7.91
+189.0,61.0,32.8,85.1,87.4,4.66,10.9,947.0,14.1,13.1,1.84
+31.6,16.8,39.6,340.0,85.8,49.6,84.3,1446.0,16.0,19.8,8.82
+115.0,36.8,1.0,433.0,38.5,6.1,23.1,528.0,16.5,30.0,6.98
+114.0,59.4,19.6,10.3,105.0,36.5,75.7,1075.0,2.37,2.29,8.98
+17.9,25.3,12.1,64.4,25.3,13.3,26.9,422.0,12.6,27.4,4.78
+39.2,14.5,12.6,274.0,53.8,10.4,10.8,717.0,15.4,31.3,13.7
+126.0,142.0,19.1,163.0,15.1,26.9,38.9,583.0,1.72,13.1,12.3
+35.9,22.7,18.4,95.6,16.0,23.5,45.3,382.0,22.5,28.6,16.5
+207.0,56.7,13.9,137.0,13.3,53.3,122.0,1197.0,21.7,39.2,14.5
+62.1,27.6,23.5,49.6,38.5,24.4,57.3,947.0,20.5,10.6,14.6
+101.0,39.2,6.21,207.0,21.9,18.8,28.1,365.0,20.2,31.6,13.2
+15.1,14.7,6.32,8.28,16.4,17.2,22.9,407.0,15.1,22.9,4.07
+105.0,105.0,11.4,142.0,45.7,15.5,35.2,649.0,2.79,1.01,3.28
+62.6,33.4,11.7,119.0,44.5,24.6,52.8,2969.0,13.8,21.7,4.66
+30.5,27.9,24.6,34.9,13.6,12.7,67.9,123.0,12.2,15.1,9.47
+5.99,19.3,7.57,215.0,35.2,30.0,31.9,297.0,16.8,18.6,6.26
+8.82,4.96,25.5,7.77,42.6,21.1,31.1,396.0,54.7,147.0,69.8
+37.2,20.9,11.0,143.0,29.2,2.81,25.7,704.0,27.6,34.6,8.98
+16.3,9.47,9.47,25.7,24.8,12.4,22.9,271.0,30.8,31.1,17.2
+24.6,35.9,7.64,87.4,16.3,9.91,17.5,851.0,17.5,18.3,10.9
+75.7,21.1,27.9,82.8,47.8,22.5,35.5,246.0,25.7,43.7,10.4
+80.6,34.0,11.1,737.0,73.0,38.2,66.7,340.0,4.29,6.32,22.5
+33.1,11.2,15.8,154.0,23.1,31.1,61.5,764.0,17.6,21.9,14.2
+33.4,15.7,21.5,23.1,6.61,4.1,27.6,583.0,20.5,23.7,10.5
+34.3,16.4,17.6,56.2,47.0,5.99,10.6,215.0,42.9,68.5,18.1
+44.9,20.4,9.14,173.0,43.7,7.99,13.1,426.0,29.7,46.6,15.3
+36.5,16.3,9.91,157.0,45.3,9.65,11.5,626.0,2.86,1.0,10.6
+138.0,39.2,29.7,38.5,27.9,17.2,31.6,478.0,11.8,24.6,7.37
+68.5,34.6,10.7,207.0,52.8,13.8,22.9,313.0,17.6,12.4,9.47
+13.7,7.5,27.1,51.9,36.5,15.4,37.2,991.0,48.3,51.9,13.6
+75.7,44.9,14.2,143.0,36.8,3.31,34.9,1208.0,18.3,32.8,10.7
+35.9,36.8,11.2,135.0,81.3,15.0,24.8,764.0,12.7,34.3,17.6
+69.8,28.6,8.58,15.8,37.2,8.35,22.7,437.0,31.3,48.7,49.1
+68.5,39.6,3.79,19.1,29.7,7.77,18.8,289.0,3.79,3.75,25.3
+38.9,16.0,12.1,131.0,35.2,9.73,25.5,362.0,19.5,23.5,12.7
+35.2,29.7,28.1,56.7,14.1,15.0,20.0,638.0,14.2,23.5,13.8
+29.7,20.2,7.7,125.0,36.2,6.55,15.7,500.0,18.9,25.0,4.87
+61.5,23.9,18.3,87.4,17.5,19.8,25.9,255.0,34.6,50.0,12.6
+129.0,42.9,17.3,62.6,41.0,34.9,72.3,621.0,8.43,16.0,5.73
+91.4,27.6,1.03,172.0,7.3,34.6,40.7,407.0,16.5,24.8,15.8
+66.7,23.7,14.5,186.0,44.1,20.0,37.2,437.0,20.5,31.3,6.92
+79.1,31.1,44.5,147.0,77.7,13.5,16.7,567.0,13.9,12.6,16.3
+61.0,42.6,4.61,1.5,5.09,9.22,21.3,523.0,3.75,2.11,7.3
+51.9,16.8,9.39,188.0,26.9,4.91,10.5,259.0,5.33,1.0,10.0
+13.7,9.82,14.2,165.0,23.5,26.2,32.8,385.0,12.4,20.9,14.9
+22.5,14.2,6.67,276.0,31.3,19.8,58.3,1499.0,2.07,5.42,11.1
+46.1,21.9,11.3,18.4,88.2,11.0,18.4,667.0,28.4,38.9,13.5
+13.7,25.9,29.4,42.9,32.2,14.1,67.3,429.0,2.89,1.58,1.26
+27.4,14.1,16.5,71.7,11.8,17.9,52.8,882.0,15.8,18.1,25.0
+73.7,30.0,21.1,262.0,87.4,31.9,52.8,286.0,18.9,17.2,4.29
+17.2,21.9,20.0,57.8,34.0,16.0,30.5,523.0,37.9,58.3,23.3
+59.4,20.7,4.1,328.0,25.5,2.89,2.21,81.3,18.3,32.5,9.47
+67.3,30.2,36.5,311.0,62.6,16.0,32.5,470.0,23.5,32.8,16.0
+39.2,18.9,43.3,362.0,79.9,5.09,18.9,583.0,14.5,22.5,9.56
+67.9,31.3,13.8,52.3,30.8,20.2,31.6,279.0,5.28,17.2,4.49
+52.3,45.7,19.3,239.0,29.4,12.5,38.2,813.0,17.9,28.9,5.47
+89.0,38.2,12.4,211.0,36.2,23.1,81.3,1134.0,19.5,18.3,15.8
+54.2,20.7,24.8,717.0,108.0,13.9,99.1,1252.0,51.4,58.3,13.7
+51.9,58.8,9.91,107.0,12.7,12.1,35.2,973.0,18.9,27.9,11.3
+31.3,10.4,10.5,107.0,37.9,18.9,34.3,426.0,15.3,8.06,3.02
+69.8,34.6,19.8,34.3,17.9,1.78,1.01,76.4,28.6,48.7,28.1
+28.9,29.4,7.64,193.0,54.2,21.7,27.9,426.0,20.7,30.5,9.14
+95.6,49.1,14.1,259.0,50.0,54.7,113.0,1486.0,29.4,49.6,9.73
+47.4,21.7,7.99,132.0,15.3,12.5,31.1,346.0,3.31,2.41,2.76
+61.5,40.7,7.77,22.7,37.9,15.0,32.2,441.0,8.51,31.3,9.47
+40.7,25.0,7.04,3.75,20.2,18.6,27.9,433.0,46.6,58.3,17.0
+46.1,29.7,31.3,737.0,155.0,6.1,23.9,1568.0,34.3,47.8,20.5
+32.8,19.1,53.3,145.0,96.5,12.0,23.1,542.0,23.3,34.0,4.78
+93.9,23.3,14.2,47.8,45.7,12.2,48.3,3051.0,12.9,24.4,7.7
+67.3,33.4,67.9,418.0,138.0,16.0,24.6,403.0,18.1,24.4,3.96
+37.2,11.8,4.37,18.1,31.3,41.4,77.7,1263.0,20.9,38.5,11.2
+38.2,22.5,17.5,445.0,136.0,3.08,12.7,784.0,19.5,33.7,15.8
+20.7,22.7,15.5,112.0,19.6,48.3,122.0,1446.0,15.4,17.0,19.5
+13.6,13.7,5.47,5.94,14.6,26.4,53.3,1486.0,19.1,38.2,8.28
+173.0,193.0,10.7,289.0,55.7,27.1,47.8,1568.0,20.9,32.2,6.73
+14.7,18.6,63.2,193.0,54.7,34.0,64.4,661.0,25.3,40.7,1.31
+75.0,25.0,10.6,181.0,42.9,6.15,22.9,1611.0,16.4,29.4,11.2
+85.8,67.3,10.6,189.0,40.3,14.7,28.6,331.0,3.02,1.31,13.5
+87.4,44.5,9.31,21.9,43.3,2.76,11.8,843.0,17.2,34.9,13.6
+38.2,24.4,7.17,217.0,29.7,13.6,25.3,491.0,30.8,42.6,23.1
+38.2,24.1,17.0,92.2,38.9,25.7,36.2,644.0,2.07,28.9,65.5
+40.0,12.2,6.21,202.0,22.7,78.4,121.0,1186.0,28.1,34.0,13.7
+77.7,20.9,19.8,18.4,11.5,16.7,38.2,422.0,25.0,22.3,21.1
+74.3,29.7,1.43,211.0,34.3,13.5,27.6,403.0,1.93,3.52,6.55
+41.8,20.2,43.7,346.0,114.0,17.8,47.0,1625.0,36.5,81.3,79.1
+49.1,22.1,13.7,126.0,23.1,10.9,32.2,491.0,20.7,23.5,9.47
+50.0,27.1,18.8,81.3,41.0,11.3,31.1,562.0,22.9,21.3,1.0
+29.2,45.7,18.1,160.0,18.8,14.5,16.5,437.0,17.9,34.3,13.0
+80.6,36.8,1.0,453.0,67.9,12.1,33.7,552.0,17.2,16.5,4.33
+65.5,32.2,7.43,13.7,9.39,14.9,28.1,604.0,17.5,28.1,4.41
+179.0,55.7,16.3,80.6,27.6,4.49,18.9,1208.0,30.0,32.2,14.1
+34.0,24.1,10.3,173.0,41.0,10.2,23.1,385.0,22.5,28.4,10.5
+55.7,35.5,51.4,204.0,43.3,12.4,14.2,392.0,1.46,2.07,13.7
+80.6,36.5,1.38,108.0,16.0,10.5,21.9,500.0,20.7,24.1,11.9
+31.3,32.8,13.9,188.0,36.5,8.66,26.2,750.0,18.3,33.7,8.74
+49.6,32.2,47.8,487.0,94.7,21.7,32.2,542.0,19.8,41.0,12.6
+167.0,79.1,13.5,24.1,14.7,21.5,29.2,414.0,1.0,1.0,7.04
+71.7,50.9,48.7,93.1,55.7,9.91,28.4,505.0,12.2,11.0,1.86
+66.1,47.4,24.8,126.0,49.1,23.5,49.6,673.0,1.0,10.6,2.71
+52.8,14.6,13.5,149.0,45.3,15.5,25.5,385.0,21.9,22.5,15.3
+123.0,27.4,8.74,274.0,23.5,35.2,142.0,1894.0,26.9,47.4,4.57
+47.4,22.5,6.67,264.0,29.4,5.57,26.9,914.0,13.5,21.9,17.9
+21.5,18.1,1.01,698.0,55.7,21.9,33.7,457.0,21.5,20.7,6.55
+42.2,13.5,23.5,35.2,26.4,17.6,35.5,638.0,22.1,32.2,8.74
+9.65,16.1,15.1,237.0,25.0,13.5,25.0,300.0,22.7,17.3,1.88
+28.9,21.5,40.3,368.0,111.0,22.1,34.6,372.0,20.4,29.2,6.04
+93.9,44.5,12.9,217.0,25.9,18.3,39.2,418.0,20.9,25.3,7.57
+69.8,20.9,10.8,160.0,35.9,7.37,13.6,453.0,37.9,35.9,16.3
+41.8,14.6,33.7,491.0,103.0,36.5,60.4,319.0,26.7,24.6,7.43
+12.0,21.3,20.2,81.3,17.2,10.1,24.8,461.0,27.1,39.2,9.22
+31.1,23.9,9.82,179.0,34.9,64.4,143.0,1009.0,17.3,20.0,4.41
+62.1,30.2,13.3,205.0,20.9,47.8,73.0,1037.0,25.0,29.2,1.75
+14.9,16.8,11.9,107.0,47.0,16.5,48.7,567.0,21.7,33.1,8.9
+34.0,23.3,10.6,198.0,28.4,15.1,30.0,898.0,17.6,21.3,10.3
+69.2,19.3,9.47,289.0,25.7,10.5,15.8,414.0,18.1,16.4,13.2
+50.9,20.7,7.91,143.0,18.4,36.8,83.5,1018.0,44.9,65.5,24.6
+38.9,27.1,4.66,6.44,13.2,11.5,39.2,461.0,16.0,20.0,7.23
+88.2,24.4,12.0,225.0,55.2,25.7,76.4,1407.0,38.2,51.4,12.6
+107.0,54.2,22.3,104.0,1.0,11.5,18.3,523.0,21.5,24.4,8.74
+54.7,27.4,14.3,233.0,43.3,5.62,12.2,588.0,21.1,27.1,8.28
+10.4,4.57,8.43,106.0,30.2,5.23,21.5,1186.0,21.7,40.3,10.7
+59.9,8.28,11.4,51.4,22.9,51.9,99.1,1065.0,19.8,34.9,23.9
+101.0,25.3,10.8,56.7,36.2,30.2,110.0,1700.0,13.6,30.0,10.5
+14.6,28.9,7.1,53.3,5.99,7.91,17.2,445.0,8.51,29.4,15.4
+143.0,67.3,11.2,704.0,95.6,2.71,20.2,661.0,14.3,22.5,1.01
+96.5,29.7,5.67,126.0,21.9,37.2,53.8,1009.0,26.4,38.9,12.0
+103.0,89.8,13.3,167.0,44.1,18.3,23.3,500.0,1.0,1.04,10.6
+36.5,17.9,10.1,92.2,26.7,35.9,53.3,322.0,34.6,49.6,11.2
+66.7,81.3,19.5,213.0,121.0,5.83,6.79,279.0,17.0,40.0,50.5
+64.4,35.2,21.5,17.6,1.49,25.5,34.3,325.0,24.1,37.5,14.1
+110.0,34.0,2.44,4.83,1275.0,23.5,27.9,505.0,21.5,23.5,14.7
+23.1,30.2,10.0,403.0,75.7,23.7,36.5,389.0,19.6,33.7,6.55
+145.0,32.5,18.1,106.0,30.8,4.03,15.5,791.0,30.2,40.3,13.5
+48.7,17.3,7.04,32.8,91.4,20.7,42.6,340.0,44.9,64.4,18.4
+18.8,13.3,4.37,352.0,17.9,8.51,20.2,509.0,3.55,1.01,1.2
+64.4,31.1,3.13,209.0,26.2,28.4,33.7,305.0,25.7,31.6,19.5
+35.2,19.1,13.3,204.0,20.0,7.77,10.6,466.0,5.78,16.0,6.79
+29.7,22.9,29.7,49.1,28.6,12.5,13.7,784.0,17.0,14.9,10.2
+52.8,14.2,12.4,132.0,33.1,42.6,98.2,750.0,24.8,44.1,29.4
+34.0,17.8,20.9,248.0,33.4,4.78,13.5,743.0,26.7,36.5,15.3
+42.9,14.5,14.1,50.9,24.4,32.5,50.5,346.0,20.9,34.9,4.0
+33.4,27.4,53.8,57.3,32.5,44.1,94.7,1860.0,13.5,29.7,15.7
+111.0,38.2,16.1,264.0,65.5,25.0,33.1,437.0,1.0,3.85,5.14
+84.3,30.2,13.5,170.0,41.8,11.1,25.0,437.0,22.7,35.5,10.8
+37.9,20.9,12.9,89.0,19.5,29.4,38.5,204.0,38.2,46.1,11.8
+64.4,34.3,7.99,235.0,24.1,22.5,37.5,311.0,20.2,22.7,9.06
+44.5,22.1,1.43,308.0,28.6,22.5,102.0,1000.0,28.1,37.9,8.06
+36.8,20.7,24.1,46.6,1.26,15.0,28.1,578.0,21.5,30.0,10.6
+111.0,42.9,6.73,231.0,30.5,26.9,28.1,331.0,16.0,21.7,8.98
+42.6,16.3,2.27,271.0,17.9,9.06,23.7,538.0,27.1,41.0,14.2
+12.5,32.2,6.92,244.0,26.9,10.8,22.5,368.0,7.37,15.8,13.0
+28.1,30.5,2.69,239.0,15.8,6.21,19.3,791.0,20.0,42.6,3.13
+83.5,75.0,14.9,184.0,28.4,23.5,42.2,429.0,32.8,41.0,11.9
+87.4,39.2,55.7,300.0,112.0,16.1,39.2,2167.0,14.6,15.1,3.22
+29.4,29.7,17.0,319.0,54.7,33.1,45.3,382.0,18.3,18.6,8.13
+49.1,22.5,10.3,164.0,40.7,17.3,27.1,418.0,22.7,23.3,7.5
+122.0,85.1,46.1,215.0,45.7,20.5,35.9,578.0,26.9,22.7,11.1
+28.1,17.8,1.88,225.0,21.3,18.6,33.7,294.0,31.3,40.7,20.7
+19.3,17.3,5.14,12.0,21.5,12.5,30.2,483.0,17.9,23.5,14.5
+3.65,10.9,15.4,57.3,17.0,6.92,20.5,470.0,2.79,1.01,4.29
+25.5,1.25,15.0,229.0,59.9,14.5,25.3,269.0,27.4,35.9,27.6
+31.3,22.7,25.9,311.0,47.0,64.4,135.0,2436.0,22.5,29.7,15.0
+16.7,5.38,9.31,158.0,51.9,5.42,20.9,973.0,18.3,29.7,7.5
+71.7,19.5,45.7,474.0,108.0,38.2,149.0,1459.0,26.9,41.4,9.47
+37.5,10.3,6.15,153.0,30.0,17.6,31.3,445.0,17.8,20.7,14.7
+3.46,1.47,19.6,73.0,28.6,52.3,118.0,1670.0,8.82,16.4,7.7
+34.9,21.3,25.9,1176.0,196.0,31.1,42.2,311.0,20.7,24.8,10.9
+23.9,17.8,3.28,1.72,4.33,30.2,50.0,281.0,20.7,27.4,2.69
+26.4,29.2,3.46,429.0,41.0,24.8,31.9,414.0,17.2,31.1,11.9
+17.3,15.8,19.8,241.0,58.8,49.6,81.3,1241.0,1.49,5.78,5.0
+73.7,25.3,5.19,178.0,35.2,8.06,39.2,1075.0,23.5,40.0,13.5
+64.9,23.5,13.0,246.0,31.6,23.7,61.0,457.0,17.2,34.3,9.82
+53.8,14.5,46.1,97.3,66.7,15.1,22.7,362.0,22.7,16.4,4.37
+49.6,23.7,5.99,20.5,27.9,11.4,14.1,382.0,15.3,29.7,7.1
+1.35,8.82,8.98,157.0,33.4,38.2,160.0,1499.0,25.9,36.8,12.5
+50.9,15.1,7.1,75.7,47.8,3.02,13.6,667.0,22.5,34.0,5.47
+24.8,9.65,19.1,340.0,62.6,55.7,246.0,1046.0,41.4,47.4,13.2
+86.6,26.2,11.2,119.0,21.7,5.99,16.3,685.0,28.9,33.7,14.9
+34.9,11.5,25.5,322.0,72.3,17.2,42.2,610.0,16.3,24.6,12.0
+60.4,16.5,6.61,165.0,17.0,12.7,49.1,3718.0,25.5,37.5,16.7
+54.2,27.4,19.5,308.0,56.2,31.9,55.2,906.0,16.1,43.3,15.3
+58.3,28.6,16.5,127.0,39.6,4.78,15.8,604.0,4.33,14.5,1.45
+65.5,16.8,10.2,57.3,16.4,22.3,40.0,297.0,25.9,38.2,10.1
+67.3,20.7,5.33,567.0,64.9,35.5,80.6,991.0,15.4,19.1,10.1
+109.0,31.9,22.3,154.0,40.7,12.3,20.4,615.0,20.4,37.5,14.9
+127.0,68.5,9.65,5.57,34.9,13.6,36.2,478.0,19.3,23.5,9.39
+115.0,37.9,21.5,68.5,25.3,17.0,38.2,276.0,21.1,31.1,5.78
+21.3,13.5,36.5,62.1,48.3,8.82,30.5,382.0,30.8,39.6,2.02
+14.5,18.9,5.52,10.6,11.9,29.7,46.1,514.0,1.07,37.2,5.09
+56.7,23.7,7.23,124.0,37.2,30.2,57.8,286.0,21.3,33.7,3.68
+26.4,19.6,1.83,9.91,9.91,20.7,48.7,947.0,20.2,24.1,4.22
+9.39,6.04,34.6,87.4,28.1,19.6,31.9,294.0,29.4,36.8,11.9
+13.1,17.2,4.78,19.1,64.4,10.8,18.3,375.0,15.5,26.4,2.71
+63.2,28.1,25.7,80.6,55.2,15.7,20.2,547.0,20.9,34.3,9.22
+48.3,23.3,8.82,130.0,14.1,13.9,25.7,375.0,23.7,26.9,14.1
+31.6,16.7,14.1,37.2,3.92,11.8,30.0,400.0,25.7,31.9,19.8
+31.9,24.6,14.2,163.0,23.3,37.2,84.3,1554.0,3.59,1.18,7.5
+41.0,17.5,14.2,202.0,36.2,54.7,89.8,1540.0,21.1,33.4,7.57
+16.8,17.8,5.78,126.0,33.1,13.8,20.9,284.0,31.1,42.2,12.6
+44.5,12.5,5.47,112.0,27.6,8.9,15.5,396.0,11.7,20.4,6.21
+1.0,10.7,1.01,1.51,5.33,12.3,57.3,2072.0,14.1,32.5,10.7
+19.6,5.67,1.0,286.0,25.3,37.9,66.7,820.0,36.8,49.6,13.2
+26.7,18.9,2.53,21.1,22.1,8.43,15.4,349.0,18.8,23.3,9.22
+34.0,25.0,8.66,154.0,35.5,28.9,37.5,483.0,28.9,43.7,13.5
+74.3,35.9,13.5,172.0,51.4,5.83,24.4,319.0,27.9,40.3,11.9
+44.5,44.5,4.07,319.0,31.6,23.1,44.5,723.0,1.35,3.75,8.66
+23.9,29.7,12.3,95.6,18.8,6.38,18.4,259.0,16.0,31.1,14.1
+22.3,34.6,5.28,334.0,32.2,73.0,173.0,1346.0,23.5,56.7,173.0
+118.0,24.1,8.06,207.0,61.5,19.8,50.0,478.0,18.9,35.5,10.0
+109.0,38.5,8.58,126.0,21.5,10.1,21.7,426.0,24.1,28.1,18.9
+73.7,20.7,6.98,453.0,57.8,20.5,44.5,644.0,21.3,32.8,11.4
+25.9,23.1,10.3,155.0,18.3,17.5,18.3,368.0,31.1,41.4,4.41
+75.7,34.3,22.1,186.0,92.2,40.3,95.6,965.0,16.5,20.0,8.58
+37.9,6.73,2.33,269.0,42.2,23.3,40.7,449.0,43.7,60.4,16.5
+41.4,21.7,11.8,64.4,16.0,19.5,22.5,311.0,21.1,39.6,4.33
+90.6,29.4,17.5,18.4,3.0,34.9,41.0,655.0,20.4,25.3,11.3
+19.1,40.7,23.3,108.0,58.3,9.91,42.6,1459.0,17.0,28.6,11.5
+63.2,36.2,13.0,209.0,23.7,6.85,16.5,947.0,31.1,40.3,14.2
+75.0,31.6,27.6,308.0,52.8,86.6,154.0,1018.0,16.4,26.2,2.69
+36.8,24.4,8.28,20.0,34.6,3.89,12.4,313.0,2.21,1.15,4.33
+42.6,14.7,11.3,24.6,39.6,4.83,22.5,1526.0,25.5,31.9,6.32
+41.4,34.3,14.9,178.0,39.6,27.6,42.9,294.0,31.3,34.6,4.83
+20.2,17.8,9.06,178.0,36.5,11.7,29.4,673.0,1.0,10.7,10.0
+13.2,9.14,17.2,147.0,34.9,21.7,40.3,673.0,25.5,33.7,18.3
+18.3,11.3,17.2,141.0,44.1,71.0,114.0,1124.0,27.4,27.6,11.3
+11.9,4.53,7.57,172.0,38.2,10.8,18.4,414.0,2.35,9.47,10.8
+53.8,25.5,27.6,211.0,56.2,33.7,57.8,500.0,18.6,22.7,10.4
+10.0,10.2,12.9,52.8,9.06,39.6,100.0,1046.0,23.5,42.9,16.8
+58.3,32.8,25.0,8.82,42.2,5.73,45.3,528.0,30.2,39.6,3.96
+94.7,50.0,17.8,316.0,55.7,49.6,98.2,2148.0,18.1,37.2,6.55
+27.4,21.5,8.98,11.3,31.9,43.3,65.5,649.0,27.1,42.2,8.9
+37.2,15.0,56.7,154.0,84.3,35.9,175.0,1999.0,22.3,36.5,14.1
+153.0,107.0,13.1,160.0,32.8,9.39,20.0,533.0,1.98,4.14,11.7
+51.9,10.3,14.5,271.0,54.2,8.13,12.5,362.0,27.6,35.9,11.4
+78.4,25.9,1.0,382.0,33.1,20.2,43.3,1124.0,3.79,19.1,26.4
+69.8,24.4,8.82,207.0,30.2,21.5,32.5,385.0,23.7,37.2,15.0
+106.0,45.3,11.1,165.0,44.5,12.0,25.3,352.0,9.39,40.0,45.7
+204.0,75.7,21.7,179.0,57.8,4.57,19.3,359.0,17.9,24.4,6.49
+53.3,21.3,9.14,141.0,40.3,56.2,122.0,1009.0,1.43,1.01,1.21
+44.9,22.1,7.3,39.6,25.9,3.89,12.6,594.0,25.7,37.2,11.9
+38.2,16.0,5.88,53.8,6.92,21.9,54.2,673.0,21.5,22.5,3.05
+8.2,9.91,25.5,111.0,32.2,21.3,36.8,343.0,38.5,57.8,7.64
+93.9,46.1,6.67,126.0,28.4,27.6,41.4,352.0,1.0,6.92,7.91
+32.8,18.4,13.7,168.0,33.7,11.3,33.4,835.0,28.9,45.3,13.7
+80.6,40.7,17.5,120.0,53.3,11.1,20.4,331.0,23.5,26.4,5.78
+7.57,23.5,16.7,141.0,32.2,10.8,17.2,673.0,26.2,48.3,8.13
+28.9,19.1,5.78,573.0,93.9,19.6,30.0,213.0,23.1,25.3,6.92
+9.82,7.43,20.4,100.0,8.58,40.3,97.3,1084.0,22.3,29.2,13.0
+93.9,38.9,12.5,143.0,32.5,22.1,40.0,253.0,32.8,35.5,15.7
+40.3,24.8,5.73,14.3,47.4,20.5,27.1,392.0,24.8,34.3,16.3
+35.9,34.9,6.44,264.0,42.2,22.9,35.2,346.0,47.8,81.3,21.5
+66.1,27.9,6.15,284.0,51.4,61.0,91.4,514.0,26.2,29.4,12.0
+41.8,19.5,18.9,271.0,71.7,19.6,35.5,382.0,8.13,12.2,57.3
+20.9,27.6,4.96,267.0,35.9,24.4,38.5,547.0,24.1,27.4,6.38
+16.4,8.9,2.04,429.0,55.2,36.8,74.3,500.0,31.6,30.2,9.06
+59.4,32.2,2.81,239.0,12.2,4.87,14.2,193.0,21.1,34.0,7.17
+32.8,17.2,35.5,418.0,97.3,28.1,43.7,375.0,10.0,9.47,9.39
+44.9,20.0,1.81,10.1,19.6,17.6,30.5,340.0,21.7,31.3,12.7
+81.3,16.7,5.88,239.0,19.5,25.7,69.2,1685.0,33.1,46.6,8.13
+136.0,71.0,21.7,53.8,31.9,17.5,28.4,375.0,30.5,38.2,12.1
+23.5,16.3,17.6,18.6,8.28,23.3,42.6,233.0,10.8,40.7,21.5
+57.8,15.0,28.6,385.0,154.0,4.22,33.4,1165.0,34.3,46.1,8.58
+40.7,16.1,27.9,74.3,18.9,10.3,14.9,433.0,29.7,30.2,11.1
+45.7,15.4,12.9,145.0,18.6,23.5,26.9,257.0,28.6,28.9,10.8
+6.73,20.0,52.3,311.0,151.0,11.2,23.5,547.0,17.8,26.4,5.19
+125.0,123.0,11.4,279.0,15.1,30.2,29.2,340.0,20.9,15.5,2.19
+85.1,33.4,45.7,362.0,69.8,23.1,50.5,292.0,28.4,52.8,16.1
+186.0,165.0,1.61,239.0,1.38,23.3,40.7,474.0,45.3,111.0,55.2
+52.3,38.9,6.04,25.3,14.9,16.1,30.5,337.0,34.0,59.4,8.74
+96.5,30.2,14.5,191.0,82.0,5.28,8.13,441.0,22.7,31.1,10.8
+28.9,16.8,9.73,165.0,33.7,12.5,32.8,874.0,25.9,34.9,2.97
+105.0,40.3,8.66,246.0,30.8,37.9,63.2,1124.0,20.0,27.9,8.9
+149.0,36.5,26.9,45.7,44.9,18.3,34.3,237.0,16.0,26.7,1.0
+21.5,6.67,9.22,126.0,20.4,42.6,63.8,276.0,29.2,35.5,8.58
+50.5,38.5,15.0,205.0,36.8,28.1,47.8,259.0,15.7,25.7,27.4
+100.0,48.7,10.6,164.0,8.82,23.3,40.3,355.0,2.0,6.1,4.37
+80.6,31.3,18.8,110.0,37.9,26.2,48.7,289.0,15.5,37.2,11.7
+56.7,26.7,13.7,125.0,20.5,8.82,27.6,542.0,20.7,20.7,7.99
+81.3,28.1,13.5,313.0,26.2,21.1,40.3,276.0,33.7,44.5,7.04
+44.9,22.9,22.7,170.0,30.2,6.92,19.6,276.0,47.0,58.3,7.1
+97.3,33.7,11.3,96.5,35.5,19.3,31.6,340.0,27.6,31.6,8.43
+61.0,31.9,43.7,12.0,46.1,33.7,48.7,389.0,32.8,37.5,14.5
+64.4,33.1,7.7,204.0,34.9,16.0,29.2,250.0,25.5,31.1,6.67
+120.0,40.7,27.6,69.8,58.3,117.0,172.0,1811.0,1.79,3.49,15.7
+20.7,6.61,48.3,523.0,130.0,17.0,44.5,337.0,20.5,23.1,10.2
+31.1,15.1,45.3,75.7,47.0,12.7,31.9,470.0,18.4,40.0,6.21
+25.5,28.1,9.39,13.8,61.5,27.9,68.5,1433.0,19.1,32.2,23.9
+69.8,23.7,14.2,41.0,44.9,9.06,29.7,1877.0,29.2,28.9,4.66
+5.0,18.6,13.3,167.0,52.3,50.9,233.0,3134.0,45.7,55.7,20.5
+72.3,41.4,7.3,37.5,4.22,6.32,25.5,1811.0,1.0,6.73,8.43
+40.3,27.1,1.0,858.0,9.06,17.3,34.6,195.0,16.5,28.6,9.91
+7.99,29.4,9.91,89.8,31.1,60.4,93.1,538.0,17.2,22.7,8.2
+67.3,25.0,23.5,4.07,28.1,50.9,89.0,1018.0,17.5,22.5,9.82
+59.9,19.5,33.4,115.0,50.5,6.73,11.2,343.0,24.6,32.2,6.21
+37.9,19.6,13.9,119.0,43.7,15.0,54.7,528.0,33.4,37.2,11.2
+73.0,37.9,13.2,18.8,34.6,13.6,58.8,1018.0,21.3,27.9,9.47
+75.0,28.6,30.2,474.0,172.0,5.57,30.8,514.0,15.8,18.4,3.79
+33.1,21.9,8.9,168.0,34.3,23.1,39.2,316.0,21.1,26.4,3.19
+22.9,15.8,12.9,119.0,34.3,109.0,221.0,1027.0,10.6,13.0,6.73
+11.3,17.6,49.6,110.0,42.9,27.6,47.8,289.0,25.0,42.6,7.23
+49.1,15.0,11.1,142.0,33.1,12.9,17.0,311.0,4.66,16.7,50.9
+37.9,38.5,29.4,38.5,27.4,17.8,51.4,610.0,17.9,37.2,12.4
+6.44,16.3,5.33,217.0,32.2,5.19,37.5,346.0,21.9,25.7,8.98
+56.2,29.4,7.77,18.6,39.2,24.1,35.5,389.0,33.7,34.0,14.6
+85.1,37.5,11.8,21.9,28.1,26.9,31.6,269.0,13.8,31.3,30.5
+89.8,83.5,19.5,8.66,8.66,43.7,57.8,410.0,14.3,15.1,9.22
+74.3,32.2,1.01,253.0,16.4,47.4,127.0,1230.0,24.6,43.3,3.68
+30.0,23.7,3.34,86.6,14.1,29.4,44.1,343.0,30.2,21.9,15.4
+106.0,25.5,5.28,204.0,14.2,4.78,29.4,673.0,19.6,24.6,22.1
+61.5,23.1,96.5,292.0,63.8,38.2,60.4,461.0,17.6,28.9,4.66
+85.8,20.5,7.84,22.3,31.6,18.9,19.1,255.0,48.3,60.4,15.1
+47.8,17.9,16.7,149.0,43.7,27.6,46.6,914.0,18.3,17.0,5.62
+35.5,29.4,23.5,125.0,49.6,26.2,47.4,523.0,1.38,30.5,2.67
+48.3,19.1,13.0,55.2,26.7,15.3,27.4,319.0,1.81,7.77,2.11
+111.0,36.8,48.7,87.4,25.3,18.4,34.9,478.0,14.5,25.5,19.6
+53.3,20.9,11.1,211.0,22.9,16.8,23.7,352.0,19.5,18.3,9.82
+14.3,13.6,3.31,362.0,59.4,3.19,2.67,86.6,1.72,1.0,7.04
+39.6,11.1,17.9,15.7,2.53,11.4,13.0,487.0,26.9,31.9,11.7
+14.3,23.1,11.7,158.0,40.0,11.3,21.1,470.0,18.9,29.2,10.1
+126.0,45.7,2.39,250.0,1.54,47.8,76.4,939.0,12.7,18.8,70.4
+31.9,17.3,14.5,30.5,72.3,9.65,17.2,552.0,19.1,17.5,8.58
+56.2,30.2,9.22,71.0,26.7,22.3,38.2,365.0,25.3,23.3,19.8
+131.0,85.1,25.3,191.0,88.2,13.3,28.1,410.0,10.4,14.9,6.44
+34.9,10.8,7.43,153.0,41.0,22.7,69.2,1176.0,25.7,37.9,4.45
+30.5,12.9,17.6,64.9,14.6,20.4,31.6,396.0,22.5,39.6,10.5
+8.66,20.9,13.0,46.1,72.3,16.1,21.1,337.0,17.9,22.3,9.82
+46.1,16.1,9.73,34.6,3.43,30.5,40.7,379.0,31.3,43.3,13.0
+59.4,33.1,33.7,112.0,15.7,14.3,38.5,704.0,2.0,10.9,6.04
+93.1,22.3,8.9,211.0,57.3,53.3,95.6,1526.0,31.9,45.7,5.78
+38.5,22.5,16.1,449.0,82.0,34.9,43.7,557.0,17.9,21.1,6.04
+99.1,43.7,9.47,514.0,107.0,13.3,20.0,562.0,23.9,37.9,14.6
+76.4,22.7,14.7,184.0,47.4,26.9,48.3,352.0,29.2,44.1,18.3
+106.0,66.7,5.83,188.0,30.2,8.82,23.7,500.0,21.9,35.5,15.4
+112.0,28.1,14.3,123.0,20.0,3.16,18.4,1134.0,16.3,37.5,27.1
+105.0,58.3,7.84,175.0,55.7,7.91,13.7,453.0,23.1,26.9,15.1
+94.7,26.2,5.99,16.0,35.9,4.03,15.3,487.0,30.8,26.4,5.19
+87.4,153.0,8.58,13.5,61.0,26.7,36.2,396.0,36.2,45.3,17.6
+120.0,41.0,1.0,81.3,13.6,22.9,38.5,271.0,21.9,23.1,7.84
+52.3,25.0,15.4,84.3,26.7,22.1,24.8,281.0,21.3,27.1,16.0
+19.5,26.4,2.29,42.9,12.5,25.3,34.0,281.0,13.2,34.6,27.9
+92.2,28.9,1.1,289.0,31.6,47.0,68.5,204.0,24.6,33.1,14.3
+133.0,52.8,13.3,93.1,9.39,12.4,37.5,1310.0,26.4,40.7,13.0
+31.6,16.7,19.6,58.8,34.0,14.5,37.9,737.0,9.91,30.5,9.47
+57.8,19.6,10.6,24.1,19.3,14.7,28.6,305.0,13.0,35.5,30.5
+70.4,25.5,12.9,48.3,11.2,18.3,40.7,362.0,16.3,20.2,4.53
+66.7,23.5,2.13,615.0,82.0,9.65,29.7,422.0,28.9,23.9,13.0
+31.6,12.4,18.3,158.0,24.1,5.78,20.9,965.0,25.9,22.1,12.2
+86.6,24.1,11.4,204.0,38.9,51.9,90.6,673.0,31.1,36.8,10.1
+118.0,31.9,11.0,42.2,21.3,23.3,47.8,352.0,15.5,19.6,8.9
+61.5,16.8,10.3,40.7,28.4,3.72,11.5,1018.0,33.4,50.5,12.3
+34.9,16.1,5.52,470.0,53.3,73.0,119.0,704.0,26.9,28.1,4.61
+28.6,17.5,18.4,160.0,24.8,16.5,40.7,1065.0,26.2,26.9,8.51
+25.5,12.4,7.04,225.0,29.7,13.5,23.3,346.0,20.9,36.8,13.0
+31.3,28.6,6.61,302.0,45.7,23.7,40.7,470.0,42.2,62.1,136.0
+115.0,39.2,15.1,44.9,46.1,46.1,91.4,1055.0,25.3,32.8,17.3
+76.4,41.4,11.4,97.3,44.1,2.71,6.79,147.0,24.4,34.9,5.73
+99.1,28.6,4.49,22.3,17.6,23.3,45.7,375.0,25.3,39.6,9.82
+74.3,21.1,7.57,77.7,13.6,21.7,37.5,449.0,30.0,34.9,14.2
+93.1,31.1,9.06,151.0,5.0,7.17,26.2,1134.0,2.89,1.0,3.05
+10.1,22.3,16.7,27.1,35.5,10.6,41.8,567.0,28.1,47.4,8.06
+27.6,39.2,48.3,164.0,25.3,6.38,38.9,882.0,21.5,31.3,10.6
+12.6,20.5,6.61,170.0,30.0,10.3,40.0,717.0,19.3,17.5,20.0
+100.0,28.4,16.0,124.0,59.4,41.0,101.0,3162.0,5.99,9.06,2.07
+23.7,23.9,5.73,135.0,17.3,19.3,163.0,2091.0,20.7,23.7,11.4
+75.0,24.8,5.99,21.3,22.7,32.8,79.9,599.0,29.7,46.6,15.4
+54.7,46.6,16.3,167.0,33.7,16.7,27.4,483.0,46.1,62.6,9.56
+52.8,28.6,11.7,64.4,30.0,17.9,39.6,1144.0,18.4,21.1,7.84
+73.0,20.5,5.99,253.0,40.3,4.66,22.1,514.0,19.3,25.3,13.8
+27.9,17.5,6.1,23.9,12.5,79.9,129.0,1009.0,5.42,9.56,8.43
+89.0,77.7,8.06,165.0,39.2,45.7,151.0,1263.0,15.4,27.1,2.84
+11.2,1.83,47.8,147.0,150.0,34.0,88.2,1084.0,22.7,22.7,7.7
+112.0,32.8,5.94,337.0,38.2,5.99,24.1,644.0,31.9,45.7,20.7
+28.9,20.4,8.43,91.4,41.0,14.9,24.8,355.0,27.9,31.1,1.63
+12.7,13.7,1.0,1000.0,117.0,14.9,28.4,372.0,18.6,20.4,2.09
+59.9,24.6,9.06,17.2,24.4,13.9,29.2,403.0,1.2,9.73,2.97
+29.4,16.7,17.3,129.0,28.4,4.7,31.6,316.0,12.4,34.9,19.6
+47.4,33.4,3.4,131.0,40.0,15.4,24.4,300.0,45.3,61.0,16.8
+13.6,8.74,1.0,4.14,23.9,31.1,53.3,457.0,20.7,31.6,6.61
+106.0,108.0,6.79,74.3,53.8,10.4,25.7,567.0,60.4,88.2,28.1
+39.6,13.2,14.1,292.0,54.2,1.0,3.31,31.9,18.4,14.5,11.9
+88.2,54.7,7.43,129.0,41.0,22.9,43.3,279.0,32.5,33.7,8.9
+29.4,16.1,24.4,500.0,147.0,24.1,43.7,325.0,30.2,39.2,18.3
+72.3,48.3,12.9,33.4,45.3,2.86,18.1,1000.0,44.9,71.7,17.2
+36.8,13.7,12.6,30.2,48.7,25.7,44.5,340.0,21.3,31.1,8.82
+109.0,45.3,16.1,147.0,57.8,5.52,15.5,316.0,42.9,66.7,18.3
+27.4,19.8,3.37,239.0,42.6,110.0,179.0,1395.0,29.7,46.6,12.7
+25.9,30.2,1.75,392.0,21.1,10.3,23.1,372.0,25.5,17.0,9.73
+16.0,7.77,7.17,67.3,27.1,24.6,48.3,343.0,15.4,17.8,10.4
+118.0,56.7,16.0,19.8,29.2,18.3,28.4,407.0,22.5,41.4,9.14
+36.5,18.1,7.7,20.4,20.2,12.3,43.3,610.0,12.0,16.3,7.23
+35.5,14.6,16.5,33.4,32.2,4.03,16.8,300.0,34.9,55.7,16.1
+34.3,16.8,3.89,176.0,40.7,37.9,73.0,379.0,61.5,88.2,7.7
+13.8,19.3,31.6,311.0,84.3,9.73,30.2,250.0,31.9,54.2,14.1
+66.1,22.3,17.6,41.4,38.5,20.9,25.3,365.0,28.4,48.3,15.7
+32.2,14.9,63.8,181.0,34.0,10.7,32.5,610.0,33.7,30.0,16.8
+8.74,19.8,10.0,191.0,39.2,35.2,57.8,337.0,18.4,25.9,12.3
+103.0,23.9,63.8,61.0,82.8,73.0,223.0,1420.0,17.8,23.5,2.64
+98.2,33.4,15.3,43.3,15.0,88.2,147.0,1486.0,26.2,38.2,8.13
+25.0,14.6,12.6,139.0,33.4,10.1,22.7,433.0,22.5,33.1,2.0
+110.0,36.8,8.35,19.6,36.8,20.2,51.4,3078.0,9.82,33.1,15.0
+58.3,18.8,8.58,15.3,60.4,31.3,139.0,1241.0,13.3,26.4,13.1
+20.9,8.2,7.91,178.0,34.0,10.6,21.3,843.0,13.1,19.5,14.3
+105.0,58.8,20.7,264.0,75.0,44.9,71.7,1124.0,26.9,36.2,13.2
+64.9,29.4,17.0,51.4,17.3,74.3,104.0,956.0,40.0,47.0,10.8
+88.2,25.0,12.7,211.0,35.9,30.0,34.6,385.0,20.9,23.1,13.9
+69.2,18.1,9.39,164.0,27.9,13.5,26.9,259.0,47.4,69.8,27.6
+51.9,28.6,21.7,26.2,38.9,21.1,39.2,237.0,16.8,35.5,17.0
+28.4,20.4,25.3,51.9,24.8,4.96,16.3,922.0,23.5,42.6,11.9
+45.3,21.5,41.0,85.8,66.7,23.3,30.2,237.0,31.6,42.6,7.84
+157.0,73.7,17.0,193.0,47.4,11.7,20.4,375.0,23.5,26.9,15.8
+31.6,24.6,8.74,94.7,15.3,68.5,173.0,1084.0,26.4,37.2,8.66
+139.0,37.5,14.3,167.0,36.8,43.3,85.8,1554.0,19.3,24.1,18.4
+56.7,33.7,39.2,135.0,59.9,17.8,25.3,365.0,24.6,28.9,8.06
+79.9,31.9,8.66,211.0,11.4,28.4,40.3,257.0,23.7,40.3,10.4
+49.6,11.1,11.0,161.0,58.3,20.9,52.3,866.0,25.0,41.8,8.06
+79.1,30.8,11.7,31.6,66.1,5.33,20.0,906.0,21.1,30.8,8.98
+36.5,21.7,10.1,184.0,30.5,102.0,175.0,1018.0,19.1,36.5,8.9
+50.0,13.0,7.23,139.0,29.2,54.7,118.0,1554.0,24.1,26.7,1.49
+20.7,33.7,20.4,13.6,1.0,27.1,38.5,334.0,27.9,36.5,8.2
+58.8,22.5,2.67,292.0,27.6,6.73,23.5,1433.0,27.9,40.7,12.9
+52.3,14.6,11.4,127.0,43.3,17.9,33.4,483.0,32.8,42.6,13.8
+86.6,29.7,20.0,57.8,92.2,16.4,31.1,340.0,17.3,34.3,11.2
+91.4,55.2,10.1,355.0,44.5,59.9,103.0,757.0,38.9,44.9,13.0
+32.5,14.5,9.56,52.8,18.8,22.3,37.2,483.0,16.7,43.3,18.6
+57.8,32.5,13.9,692.0,179.0,14.5,25.7,257.0,15.5,25.5,12.3
+65.5,19.8,5.19,173.0,34.9,35.9,61.5,355.0,17.2,34.0,1.02
+64.9,22.9,19.1,704.0,106.0,4.66,18.4,757.0,18.4,26.2,5.47
+5.67,17.8,1.32,186.0,38.5,25.7,30.8,519.0,22.5,26.9,10.6
+57.8,32.5,14.6,108.0,28.9,13.7,38.5,352.0,18.6,17.6,13.1
+189.0,153.0,12.1,138.0,28.1,6.79,15.1,655.0,41.0,59.4,7.37
+31.9,26.9,63.8,308.0,138.0,4.1,22.5,274.0,34.3,66.1,46.1
+30.0,11.0,7.7,127.0,34.0,18.8,32.2,368.0,16.7,29.7,5.94
+16.4,13.9,5.88,19.1,36.2,86.6,120.0,1084.0,40.3,50.5,18.3
+46.6,18.3,10.6,17.0,50.9,37.9,63.8,466.0,34.9,50.0,18.3
+27.6,21.1,14.5,118.0,40.3,132.0,207.0,594.0,41.0,48.7,5.99
+62.6,18.4,9.91,202.0,36.5,392.0,547.0,764.0,27.9,47.0,15.3
+92.2,47.0,18.9,123.0,20.5,1.21,1.01,13.3,18.6,27.9,1.36
+50.9,30.2,3.85,9.39,26.7,11.7,34.3,359.0,29.2,41.0,5.38
+53.8,14.7,11.8,112.0,51.4,42.2,88.2,764.0,24.1,34.3,9.65
+102.0,30.8,10.8,164.0,18.8,34.9,50.0,610.0,56.2,73.0,21.9
+72.3,39.2,12.6,183.0,32.2,61.0,95.6,1186.0,20.7,25.3,7.17
+86.6,31.1,2.97,239.0,31.6,18.8,37.5,457.0,22.9,33.7,5.14
+110.0,35.2,46.1,147.0,44.9,3.92,20.9,698.0,20.7,33.7,9.31
+42.6,24.1,5.28,42.6,11.5,83.5,213.0,1928.0,23.9,30.2,7.3
+9.91,25.5,8.58,109.0,33.7,16.5,25.3,509.0,22.5,36.8,15.8
+106.0,54.2,7.99,147.0,35.2,33.1,69.2,777.0,26.7,35.9,8.35
+34.9,17.2,6.04,244.0,40.7,26.9,47.4,474.0,59.9,70.4,24.4
+4.22,7.57,26.7,311.0,67.3,14.3,32.2,322.0,18.8,26.7,11.2
+54.2,24.4,7.64,25.7,57.8,21.9,32.8,433.0,27.9,54.2,5.94
+36.5,14.5,1.67,204.0,50.0,17.2,26.9,461.0,16.4,30.0,13.0
+75.7,18.9,11.4,161.0,36.2,16.0,30.0,133.0,21.5,22.1,13.3
+29.4,22.3,26.7,457.0,49.1,8.2,21.3,441.0,20.9,41.0,8.74
+49.6,16.1,8.13,178.0,17.8,8.74,36.5,583.0,21.9,35.9,6.92
+4.74,18.9,18.1,15.0,7.84,9.39,18.1,328.0,18.9,20.7,8.13
+56.2,37.2,8.51,30.5,45.7,48.7,129.0,698.0,2.23,7.91,13.2
+85.1,28.6,11.1,101.0,62.1,10.5,27.1,1310.0,27.1,37.2,10.7
+14.2,15.4,33.7,95.6,67.3,18.8,33.4,253.0,22.1,29.7,4.53
+120.0,57.3,10.7,118.0,29.4,7.57,27.9,866.0,20.7,38.9,10.3
+46.6,20.7,8.98,13.9,41.0,20.4,55.7,1700.0,23.3,36.2,6.38
+29.7,20.7,8.06,213.0,37.9,23.9,49.1,244.0,48.3,67.9,21.5
+79.9,26.2,10.7,126.0,18.3,2.79,17.9,914.0,24.1,19.5,15.1
+15.7,29.7,11.4,92.2,50.5,4.74,13.3,710.0,1.0,1.0,5.33
+149.0,110.0,20.2,200.0,22.3,13.3,33.4,791.0,13.7,26.9,32.8
+85.8,23.9,28.4,142.0,112.0,67.3,178.0,991.0,16.0,25.3,1.0
+52.3,37.2,2.81,292.0,36.2,15.7,59.4,1700.0,21.5,25.3,9.82
+160.0,157.0,22.9,79.9,77.0,5.28,22.1,851.0,24.6,17.3,11.4
+99.1,19.6,16.7,8.58,36.2,23.9,45.3,284.0,28.4,40.3,7.23
+31.3,19.1,10.3,104.0,24.1,24.8,32.8,223.0,1.53,6.04,3.75
+14.3,22.1,13.5,93.1,41.8,15.5,20.4,244.0,17.5,30.0,13.9
+88.2,52.8,27.1,55.7,44.1,33.7,52.3,359.0,13.5,42.2,97.3
+38.9,20.2,7.84,124.0,22.3,13.8,30.2,302.0,17.2,14.2,12.1
+175.0,49.1,15.8,161.0,30.0,35.9,56.2,269.0,18.9,24.6,16.4
+125.0,61.0,14.5,173.0,23.1,30.0,48.3,284.0,37.5,36.5,19.5
+26.4,13.7,7.57,4.29,14.5,13.8,31.6,349.0,2.76,11.1,4.0
+54.2,22.3,13.0,161.0,62.6,31.9,45.7,284.0,25.0,29.2,4.91
+13.2,6.79,10.3,178.0,29.2,22.5,38.2,334.0,13.6,27.6,10.4
+20.0,23.1,14.5,179.0,34.6,11.3,30.2,276.0,10.4,11.5,4.07
+32.8,20.9,16.7,632.0,120.0,3.55,29.4,1640.0,22.3,34.6,6.15
+30.5,48.3,5.83,167.0,18.3,16.0,24.4,418.0,32.2,42.6,16.8
+75.7,28.6,13.6,118.0,37.9,59.4,105.0,2148.0,16.1,18.6,5.0
+50.5,20.0,10.8,175.0,26.2,26.4,31.3,337.0,23.3,34.0,6.21
+34.9,20.4,16.7,23.1,12.9,38.2,52.3,407.0,5.33,10.6,1.88
+30.8,12.3,30.2,157.0,63.8,18.8,36.5,255.0,15.3,25.9,1.43
+56.2,27.4,6.15,225.0,71.7,15.5,24.4,349.0,14.1,20.5,11.9
+16.3,9.31,12.3,79.1,50.0,4.41,21.1,297.0,25.3,33.7,7.1
+18.9,5.94,12.2,121.0,30.0,19.6,36.5,267.0,17.9,27.6,14.3
+49.1,9.91,1.57,422.0,15.4,18.4,30.5,478.0,33.1,61.0,7.43
+20.4,15.0,67.9,150.0,13.3,67.9,124.0,1685.0,25.7,36.8,5.99
+23.9,33.7,22.1,14.1,43.7,19.1,40.3,227.0,28.9,41.4,9.06
+71.0,22.3,3.4,2.79,24.1,40.7,96.5,1731.0,15.1,26.9,11.3
+27.4,24.1,23.9,8.74,30.5,9.47,23.5,661.0,3.25,7.64,5.78
+25.3,28.4,10.8,87.4,41.8,8.9,18.8,414.0,15.0,25.5,4.37
+12.6,26.2,20.5,181.0,77.7,61.0,107.0,2129.0,17.2,21.9,16.3
+165.0,37.5,16.3,223.0,66.7,10.5,20.7,441.0,25.5,37.9,16.3
+64.4,26.9,34.3,418.0,113.0,25.3,67.3,1275.0,25.3,40.3,18.3
+36.8,8.35,7.23,583.0,132.0,24.6,54.7,334.0,22.9,39.6,14.5
+84.3,48.3,10.9,125.0,18.1,17.9,35.9,337.0,21.7,25.9,7.99
+8.66,22.5,5.28,250.0,38.5,20.0,37.5,673.0,2.86,3.19,13.5
+7.57,4.91,2.64,372.0,19.1,15.5,34.3,227.0,21.5,23.9,10.2
+30.5,37.5,8.98,99.1,28.9,9.82,20.7,578.0,16.4,24.4,14.9
+7.91,21.7,9.06,189.0,18.8,62.6,96.5,1894.0,7.57,7.04,49.6
+7.17,16.3,13.0,104.0,39.2,5.09,16.7,757.0,15.1,18.9,1.49
+106.0,34.3,31.9,58.8,67.3,14.3,40.7,281.0,18.3,24.1,9.31
+94.7,82.8,12.9,145.0,28.9,23.9,63.2,1540.0,24.1,37.2,10.6
+57.3,25.7,16.1,41.4,29.7,20.7,27.9,259.0,34.0,42.9,8.28
+16.4,20.7,6.79,14.3,30.5,6.79,15.8,470.0,11.3,20.9,34.9
+68.5,47.8,9.06,25.9,33.1,42.6,73.0,1176.0,32.5,43.7,8.35
+14.3,15.5,14.1,121.0,27.4,28.1,46.6,615.0,18.6,23.1,9.22
+86.6,30.2,4.57,557.0,91.4,20.5,34.0,400.0,22.5,42.2,12.1
+29.4,42.6,5.94,18.9,30.0,77.7,122.0,1065.0,17.8,19.3,4.57
+36.8,23.7,28.1,305.0,95.6,2.92,14.1,1009.0,24.4,36.5,8.66
+67.3,32.5,17.8,181.0,27.6,12.6,23.1,437.0,42.9,63.8,4.57
+32.8,16.0,10.2,34.9,12.0,14.6,25.9,410.0,30.5,42.6,8.66
+35.2,47.4,13.1,227.0,46.6,11.3,29.4,276.0,20.2,16.5,2.19
+71.7,47.4,15.7,215.0,20.4,10.7,19.3,331.0,1.39,9.22,2.89
+85.8,38.2,13.2,184.0,41.8,20.0,81.3,1420.0,77.0,121.0,47.0
+66.7,18.3,11.8,120.0,34.0,36.5,51.4,437.0,22.1,17.9,3.31
+17.0,4.37,3.72,257.0,33.4,8.58,22.3,528.0,18.1,14.9,5.47
+62.1,32.8,6.98,129.0,27.1,16.0,34.9,533.0,19.3,33.4,15.4
+35.9,13.5,6.21,519.0,76.4,12.3,49.6,2227.0,29.2,39.6,15.4
+63.2,37.2,35.9,168.0,123.0,23.7,42.2,264.0,19.3,31.1,1.63
+75.7,14.6,4.33,151.0,35.9,6.38,46.6,396.0,24.6,38.2,11.9
+60.4,26.4,7.5,15.4,47.0,32.5,69.8,1165.0,12.7,23.5,9.65
+120.0,107.0,7.43,158.0,54.7,20.0,32.5,279.0,29.7,46.6,11.5
+36.5,19.1,23.3,279.0,101.0,13.6,22.9,279.0,37.2,36.5,14.9
+28.6,22.1,8.9,15.3,63.8,26.9,70.4,698.0,21.3,34.6,5.09
+8.66,15.5,14.5,41.8,20.5,21.9,40.0,211.0,29.2,34.9,20.4
+50.5,15.5,3.92,523.0,66.1,2.97,12.1,1155.0,16.4,27.1,7.23
+38.5,30.5,13.1,21.3,24.4,16.7,59.9,874.0,28.9,25.9,16.4
+9.39,17.8,3.16,229.0,34.6,9.31,13.6,505.0,36.2,56.2,16.3
+18.4,10.6,9.56,86.6,22.1,34.0,42.9,311.0,22.9,25.0,6.21
+26.9,18.3,5.09,176.0,34.3,32.2,44.5,359.0,21.7,32.5,9.06
+19.1,21.7,8.35,164.0,59.9,4.29,38.5,982.0,33.4,42.6,7.84
+35.2,12.0,12.6,115.0,44.9,66.7,176.0,799.0,33.7,46.6,10.3
+35.2,15.3,3.59,179.0,40.3,12.4,32.8,547.0,18.1,26.4,18.8
+40.0,22.5,1.0,737.0,63.8,23.3,25.3,294.0,24.8,37.5,15.8
+84.3,25.9,23.5,24.8,18.1,5.99,10.6,791.0,28.6,35.2,13.0
+3.46,16.1,11.5,109.0,26.7,13.1,31.3,626.0,28.6,31.9,15.5
+37.5,11.8,38.2,365.0,79.9,5.19,22.5,906.0,26.4,36.8,8.28
+89.0,33.7,13.8,28.4,16.5,75.7,227.0,1382.0,19.1,26.2,6.61
+67.9,19.1,21.5,43.3,57.8,40.0,55.2,673.0,12.7,15.3,8.13
+20.4,13.7,6.61,11.4,16.4,30.2,45.7,418.0,24.8,22.5,4.87
+14.7,17.0,18.3,21.3,27.9,44.9,56.2,325.0,24.8,26.7,10.5
+19.8,18.4,10.3,18.4,10.4,40.0,124.0,750.0,23.7,27.9,3.28
+45.7,14.2,1.0,437.0,55.2,11.0,20.4,319.0,18.6,30.8,3.13
+70.4,55.7,58.3,198.0,56.7,10.6,9.39,359.0,24.1,16.8,12.7
+4.33,1.01,7.17,5.0,1.45,5.88,17.5,389.0,23.9,24.1,10.6
+44.9,48.7,13.8,227.0,32.8,4.1,20.7,552.0,15.5,23.7,23.7
+58.3,17.8,15.7,269.0,44.5,16.5,40.3,379.0,25.5,20.4,8.06
+45.3,43.7,41.0,198.0,153.0,14.9,21.3,200.0,22.9,22.9,11.7
+59.9,15.4,11.1,78.4,8.13,9.91,34.6,991.0,17.8,31.9,5.14
+42.2,15.7,10.4,193.0,11.0,30.8,43.3,382.0,17.6,23.1,2.29
+15.1,11.2,12.2,271.0,44.9,15.3,51.4,2247.0,1.0,4.91,1.53
+72.3,40.7,17.0,88.2,23.7,13.8,25.7,319.0,25.9,34.0,9.73
+87.4,66.1,11.7,121.0,25.7,22.5,37.2,410.0,15.7,16.7,1.57
+31.1,24.1,12.3,89.8,42.2,38.9,55.7,328.0,27.4,46.1,10.9
+51.9,23.9,2.76,271.0,40.3,25.3,28.9,211.0,22.3,32.8,6.55
+48.7,20.0,8.98,9.31,36.5,10.9,20.9,403.0,18.4,33.1,11.2
+69.8,26.4,11.4,172.0,55.7,42.2,136.0,649.0,5.67,5.14,12.2
+44.9,16.4,7.37,308.0,39.6,1.75,21.7,851.0,22.5,29.4,10.9
+112.0,34.6,14.9,104.0,40.0,19.1,28.1,274.0,15.4,17.3,9.39
+41.8,20.0,3.59,13.5,38.9,50.9,79.1,1219.0,1.0,11.7,6.98
+86.6,30.0,11.3,157.0,23.1,21.5,53.3,557.0,1.24,3.75,5.38
+62.6,29.7,8.13,271.0,44.5,46.6,86.6,1263.0,12.1,11.1,2.31
+76.4,57.3,4.53,13.7,11.9,25.7,47.0,352.0,53.8,72.3,8.43
+61.5,23.3,16.3,281.0,52.8,24.1,106.0,1540.0,20.2,31.3,13.8
+176.0,294.0,337.0,644.0,9.73,18.4,101.0,5.99,93.1,505.0,142.0
+126.0,204.0,164.0,308.0,2.53,99.1,835.0,16.8,1358.0,6436.0,2110.0
+433.0,710.0,233.0,422.0,8.66,23.9,150.0,3.11,91.4,487.0,202.0
+161.0,248.0,362.0,661.0,6.38,69.8,505.0,8.98,1358.0,6916.0,4740.0
+151.0,257.0,93.1,172.0,14.3,47.0,392.0,26.4,69.8,422.0,418.0
+578.0,1037.0,246.0,777.0,33.1,49.1,319.0,10.6,32.8,165.0,131.0
+305.0,483.0,1446.0,2148.0,89.8,37.9,235.0,9.56,248.0,1433.0,750.0
+231.0,410.0,239.0,414.0,9.91,31.3,250.0,2.81,82.0,514.0,141.0
+1747.0,2267.0,99.1,184.0,5.33,48.3,372.0,6.61,392.0,2167.0,890.0
+191.0,276.0,262.0,491.0,3.02,32.5,175.0,7.3,35.5,205.0,723.0
+483.0,717.0,1018.0,1811.0,70.4,82.8,542.0,5.38,37.2,215.0,723.0
+250.0,426.0,175.0,362.0,1.63,42.2,274.0,12.9,35.2,191.0,135.0
+294.0,461.0,102.0,200.0,3.19,23.3,117.0,4.57,137.0,723.0,385.0
+17.2,44.1,241.0,403.0,6.85,13.6,153.0,6.79,59.9,362.0,146.0
+365.0,583.0,505.0,914.0,49.1,18.9,104.0,11.1,146.0,799.0,227.0
+1018.0,1625.0,110.0,209.0,3.96,53.8,403.0,2.86,54.2,308.0,284.0
+626.0,851.0,281.0,453.0,12.4,81.3,562.0,15.0,279.0,1747.0,704.0
+175.0,264.0,61.5,124.0,3.75,62.1,426.0,7.23,191.0,1084.0,346.0
+898.0,1499.0,599.0,1084.0,54.7,73.0,418.0,7.57,78.4,474.0,221.0
+410.0,764.0,168.0,362.0,9.14,23.9,137.0,11.0,193.0,1018.0,906.0
+170.0,311.0,108.0,207.0,2.48,193.0,1433.0,40.7,167.0,914.0,375.0
+161.0,286.0,429.0,866.0,4.41,34.9,276.0,1.24,62.6,246.0,108.0
+375.0,667.0,685.0,1334.0,8.51,54.7,340.0,12.2,225.0,1346.0,403.0
+13.1,10.4,359.0,547.0,8.35,55.7,313.0,10.1,89.8,557.0,154.0
+217.0,368.0,313.0,528.0,6.04,48.7,331.0,3.11,337.0,1811.0,262.0
+119.0,165.0,365.0,604.0,10.6,64.9,505.0,15.0,48.7,316.0,209.0
+161.0,239.0,679.0,1124.0,25.0,33.4,257.0,30.8,22.5,158.0,43.7
+39.2,57.8,414.0,799.0,2.97,64.4,352.0,13.8,133.0,698.0,117.0
+890.0,1407.0,158.0,246.0,10.2,43.3,262.0,9.65,37.9,246.0,109.0
+82.0,141.0,325.0,583.0,6.38,44.9,257.0,8.9,874.0,4332.0,806.0
+67.3,100.0,279.0,422.0,8.28,59.9,392.0,4.61,82.8,426.0,281.0
+368.0,583.0,368.0,679.0,5.23,69.2,505.0,7.7,17.8,99.1,47.4
+186.0,313.0,379.0,644.0,31.9,55.2,382.0,10.5,108.0,723.0,248.0
+1241.0,1794.0,1018.0,1640.0,44.5,56.2,368.0,14.5,60.4,343.0,172.0
+259.0,410.0,138.0,202.0,1.39,65.5,461.0,9.82,30.2,157.0,204.0
+429.0,673.0,105.0,200.0,3.96,72.3,470.0,19.8,828.0,4105.0,1499.0
+223.0,325.0,813.0,1407.0,16.8,42.6,248.0,12.2,66.7,316.0,106.0
+90.6,135.0,487.0,1027.0,61.0,108.0,730.0,7.1,16.7,89.8,31.6
+188.0,362.0,355.0,649.0,14.9,69.8,478.0,7.04,53.8,319.0,104.0
+297.0,514.0,322.0,632.0,1.17,21.7,107.0,9.22,30.5,198.0,114.0
+173.0,300.0,906.0,1582.0,15.3,18.1,113.0,2.31,103.0,583.0,146.0
+337.0,542.0,557.0,1027.0,2.33,17.6,105.0,82.8,227.0,1230.0,737.0
+155.0,223.0,48.3,82.8,16.3,11.2,59.9,110.0,67.3,429.0,119.0
+973.0,1499.0,685.0,1241.0,9.06,196.0,1358.0,71.0,704.0,3587.0,914.0
+334.0,528.0,84.3,160.0,20.5,34.3,239.0,5.94,70.4,396.0,167.0
+61.0,76.4,123.0,276.0,13.9,79.9,500.0,8.51,730.0,3752.0,2187.0
+414.0,770.0,219.0,389.0,16.4,44.5,308.0,1.72,42.2,297.0,183.0
+227.0,396.0,181.0,325.0,9.73,22.7,114.0,1.67,982.0,4740.0,1596.0
+698.0,1084.0,667.0,1114.0,39.6,47.8,255.0,8.9,36.2,204.0,53.3
+227.0,343.0,170.0,340.0,20.5,40.7,213.0,9.91,244.0,1322.0,1219.0
+400.0,626.0,153.0,239.0,4.53,45.3,316.0,12.1,102.0,599.0,90.6
+172.0,297.0,1208.0,1928.0,17.9,117.0,723.0,9.06,30.8,191.0,82.0
+343.0,528.0,188.0,365.0,9.39,73.0,491.0,7.91,47.4,328.0,253.0
+89.0,151.0,125.0,286.0,4.7,29.4,191.0,4.74,61.0,346.0,131.0
+151.0,262.0,302.0,509.0,2.15,14.7,168.0,4.96,352.0,1963.0,1420.0
+44.1,86.6,125.0,215.0,6.79,54.2,389.0,16.5,15.1,77.0,956.0
+352.0,583.0,137.0,257.0,10.2,31.1,189.0,8.82,82.0,466.0,175.0
+2350.0,3685.0,1104.0,1843.0,9.73,47.0,269.0,9.91,115.0,874.0,133.0
+137.0,225.0,173.0,289.0,11.0,26.2,150.0,1.0,221.0,1186.0,414.0
+491.0,813.0,121.0,262.0,1.01,32.2,155.0,4.74,461.0,2458.0,191.0
+136.0,178.0,264.0,449.0,7.64,27.6,221.0,9.06,279.0,1568.0,737.0
+193.0,346.0,231.0,392.0,5.0,104.0,679.0,8.9,284.0,1554.0,422.0
+271.0,392.0,129.0,246.0,16.0,37.2,231.0,11.8,76.4,519.0,181.0
+151.0,289.0,53.3,67.3,55.7,98.2,655.0,14.9,26.2,168.0,14.5
+528.0,866.0,231.0,392.0,19.3,101.0,717.0,12.4,244.0,1611.0,349.0
+115.0,215.0,385.0,685.0,66.1,26.9,168.0,2.57,106.0,717.0,355.0
+142.0,215.0,181.0,368.0,13.3,21.9,160.0,3.89,340.0,1911.0,1322.0
+292.0,437.0,557.0,1104.0,21.9,38.5,233.0,17.2,40.3,248.0,227.0
+70.4,110.0,1860.0,2943.0,135.0,52.8,355.0,5.88,167.0,982.0,200.0
+127.0,225.0,173.0,325.0,3.05,47.8,305.0,27.9,198.0,1208.0,644.0
+382.0,615.0,269.0,519.0,15.1,58.8,433.0,9.39,1055.0,5280.0,1310.0
+70.4,90.6,375.0,644.0,12.3,24.8,132.0,6.85,241.0,1446.0,922.0
+505.0,965.0,241.0,449.0,1.0,87.4,578.0,13.2,313.0,1625.0,461.0
+1499.0,2247.0,217.0,359.0,6.73,41.8,178.0,7.84,225.0,1358.0,478.0
+239.0,379.0,255.0,422.0,1.64,64.9,470.0,3.05,90.6,583.0,195.0
+305.0,437.0,389.0,757.0,14.3,38.2,221.0,1.36,25.7,117.0,106.0
+365.0,567.0,130.0,237.0,10.0,65.5,340.0,20.5,1165.0,5674.0,1370.0
+319.0,523.0,453.0,914.0,22.1,34.3,235.0,6.55,42.9,211.0,217.0
+205.0,305.0,757.0,1322.0,13.7,19.1,94.7,70.4,61.5,349.0,337.0
+2813.0,4179.0,313.0,599.0,13.8,36.5,241.0,8.98,99.1,644.0,227.0
+172.0,262.0,533.0,890.0,31.3,67.9,453.0,5.73,375.0,1981.0,685.0
+93.1,137.0,311.0,638.0,6.38,83.5,599.0,8.66,95.6,523.0,246.0
+202.0,325.0,743.0,1208.0,17.9,67.9,372.0,9.91,76.4,491.0,111.0
+178.0,284.0,292.0,514.0,1.0,64.4,407.0,17.0,64.9,372.0,193.0
+151.0,257.0,195.0,311.0,6.55,14.7,50.0,44.1,142.0,931.0,470.0
+225.0,382.0,95.6,172.0,1.02,30.2,186.0,9.22,131.0,764.0,292.0
+176.0,284.0,1094.0,1827.0,44.1,2.07,37.5,12.7,38.9,264.0,80.6
+215.0,328.0,599.0,1027.0,11.5,100.0,599.0,23.5,784.0,3820.0,1963.0
+470.0,784.0,193.0,337.0,11.2,31.1,175.0,11.5,44.5,257.0,127.0
+939.0,1370.0,96.5,188.0,8.58,26.4,200.0,5.62,20.9,127.0,50.9
+129.0,248.0,225.0,375.0,5.38,44.9,382.0,2.17,45.3,250.0,229.0
+313.0,429.0,195.0,385.0,15.1,78.4,523.0,28.4,34.9,52.3,1197.0
+437.0,806.0,123.0,244.0,4.57,49.6,286.0,88.2,973.0,4614.0,1472.0
+227.0,400.0,1554.0,2525.0,120.0,89.0,552.0,31.9,188.0,1252.0,346.0
+813.0,1334.0,519.0,965.0,15.0,48.7,279.0,14.3,38.9,244.0,219.0
+129.0,229.0,604.0,1000.0,25.9,42.6,225.0,10.9,578.0,2969.0,638.0
+284.0,457.0,146.0,284.0,11.8,56.7,289.0,26.7,340.0,2035.0,319.0
+244.0,313.0,319.0,542.0,3.22,74.3,449.0,13.6,257.0,1512.0,866.0
+355.0,615.0,1370.0,1963.0,34.6,41.0,235.0,6.67,124.0,615.0,372.0
+368.0,610.0,167.0,292.0,13.3,52.3,422.0,6.1,20.2,47.0,1370.0
+302.0,441.0,737.0,1275.0,25.3,69.2,313.0,31.9,35.9,235.0,191.0
+193.0,337.0,66.1,98.2,8.98,73.0,437.0,20.4,231.0,1407.0,922.0
+284.0,523.0,355.0,692.0,15.1,72.3,509.0,18.1,29.4,142.0,139.0
+93.1,114.0,379.0,743.0,13.0,145.0,1018.0,13.8,104.0,704.0,276.0
+135.0,202.0,429.0,692.0,17.0,57.3,375.0,23.7,170.0,1084.0,449.0
+1358.0,2072.0,114.0,233.0,4.87,35.5,161.0,10.3,108.0,615.0,200.0
+167.0,211.0,235.0,414.0,9.31,125.0,799.0,37.5,102.0,632.0,325.0
+567.0,770.0,71.7,141.0,6.61,34.3,207.0,4.96,47.0,302.0,178.0
+181.0,331.0,483.0,843.0,17.8,3.72,28.6,71.0,982.0,5003.0,2864.0
+519.0,890.0,276.0,588.0,6.98,108.0,632.0,5.14,19.6,93.9,160.0
+2890.0,4451.0,698.0,1263.0,157.0,55.2,365.0,13.6,1186.0,6153.0,1134.0
+200.0,300.0,289.0,496.0,5.88,63.8,368.0,9.06,93.1,562.0,319.0
+105.0,239.0,322.0,557.0,29.7,142.0,1009.0,54.7,46.1,191.0,437.0
+279.0,491.0,4.66,11.9,15.5,56.2,372.0,11.9,188.0,1104.0,1027.0
+248.0,407.0,422.0,828.0,9.47,32.5,188.0,12.1,179.0,1075.0,158.0
+621.0,1027.0,229.0,466.0,5.78,15.0,121.0,4.61,17.9,130.0,66.7
+145.0,241.0,145.0,246.0,1.67,40.7,246.0,8.43,27.6,150.0,24.6
+104.0,191.0,200.0,365.0,9.22,79.1,385.0,8.58,698.0,3429.0,1685.0
+615.0,991.0,217.0,368.0,10.1,40.3,297.0,7.43,31.1,209.0,183.0
+692.0,1065.0,820.0,2308.0,80.6,91.4,509.0,34.9,42.6,271.0,69.2
+143.0,221.0,1582.0,2548.0,40.3,89.0,594.0,23.3,542.0,2943.0,2503.0
+191.0,284.0,44.5,71.0,13.7,66.7,368.0,10.8,17.8,89.0,965.0
+145.0,244.0,114.0,207.0,4.57,44.5,229.0,13.9,55.2,334.0,71.7
+1075.0,1625.0,276.0,523.0,10.6,71.7,449.0,11.1,3.11,40.3,813.0
+372.0,533.0,1263.0,1999.0,47.0,27.9,184.0,1.09,114.0,730.0,207.0
+311.0,519.0,246.0,403.0,11.5,85.1,437.0,16.4,80.6,478.0,313.0
+219.0,352.0,3.37,15.3,30.5,75.7,509.0,15.5,52.8,346.0,302.0
+281.0,433.0,271.0,461.0,7.5,60.4,340.0,19.3,137.0,851.0,389.0
+250.0,441.0,215.0,418.0,10.5,25.5,189.0,1.01,1346.0,6671.0,2864.0
+284.0,433.0,359.0,583.0,9.39,18.4,103.0,5.05,98.2,610.0,131.0
+685.0,1208.0,153.0,300.0,5.38,58.8,359.0,13.8,47.4,286.0,368.0
+71.7,137.0,1094.0,1670.0,30.2,26.9,195.0,9.56,126.0,866.0,235.0
+241.0,418.0,343.0,655.0,10.0,91.4,519.0,9.56,51.9,264.0,483.0
+142.0,213.0,184.0,286.0,15.8,16.7,146.0,5.78,1.0,13.3,12.9
+70.4,100.0,1670.0,2458.0,113.0,93.9,567.0,39.6,65.5,379.0,91.4
+269.0,474.0,101.0,198.0,9.31,28.4,183.0,33.7,583.0,3023.0,2207.0
+308.0,509.0,557.0,922.0,15.1,43.3,178.0,8.82,48.7,302.0,87.4
+138.0,246.0,129.0,259.0,19.6,67.3,362.0,31.3,65.5,379.0,533.0
+337.0,533.0,112.0,191.0,4.33,78.4,500.0,5.88,44.1,264.0,184.0
+202.0,269.0,229.0,375.0,18.6,18.8,106.0,6.26,42.9,250.0,193.0
+124.0,217.0,104.0,186.0,38.2,50.5,331.0,21.1,61.5,403.0,799.0
+142.0,231.0,225.0,414.0,1.0,119.0,710.0,7.91,487.0,2864.0,692.0
+311.0,528.0,170.0,279.0,12.4,101.0,673.0,20.7,35.5,186.0,147.0
+1395.0,2148.0,75.7,119.0,1.65,91.4,567.0,25.9,27.6,172.0,89.0
+1611.0,2350.0,239.0,375.0,1.0,44.1,225.0,9.65,93.1,626.0,59.4
+209.0,349.0,239.0,437.0,3.31,50.9,264.0,18.1,679.0,3398.0,1322.0
+150.0,248.0,313.0,610.0,13.5,55.2,297.0,95.6,56.2,355.0,163.0
+433.0,698.0,1084.0,1860.0,1.53,64.4,382.0,17.5,118.0,784.0,343.0
+704.0,1346.0,382.0,583.0,6.67,71.7,433.0,8.66,217.0,1230.0,496.0
+359.0,621.0,453.0,991.0,28.1,53.8,362.0,5.33,59.9,343.0,135.0
+165.0,264.0,588.0,1124.0,6.26,104.0,610.0,27.9,46.6,294.0,107.0
+219.0,355.0,96.5,163.0,12.2,53.8,271.0,1.0,75.7,418.0,346.0
+198.0,308.0,160.0,305.0,3.75,78.4,710.0,89.0,49.1,305.0,141.0
+21.1,15.3,205.0,396.0,9.65,69.2,567.0,17.8,491.0,2714.0,806.0
+308.0,470.0,147.0,229.0,4.37,34.6,181.0,2.92,107.0,599.0,255.0
+122.0,209.0,965.0,1540.0,10.3,160.0,882.0,55.2,799.0,4105.0,2227.0
+638.0,1114.0,188.0,349.0,10.5,42.9,319.0,9.47,286.0,1655.0,229.0
+223.0,372.0,149.0,257.0,5.73,27.9,113.0,2.69,49.6,302.0,167.0
+519.0,965.0,183.0,328.0,7.23,11.5,108.0,4.1,55.2,379.0,179.0
+215.0,322.0,281.0,552.0,4.7,41.4,229.0,16.0,349.0,1827.0,262.0
+173.0,340.0,610.0,1230.0,6.85,81.3,500.0,16.0,109.0,615.0,155.0
+389.0,692.0,410.0,717.0,11.9,41.8,200.0,14.3,441.0,2393.0,764.0
+352.0,615.0,183.0,257.0,5.42,27.6,198.0,7.04,557.0,3051.0,588.0
+259.0,362.0,110.0,209.0,7.64,45.7,271.0,16.5,730.0,3718.0,1009.0
+223.0,362.0,410.0,730.0,11.8,111.0,661.0,14.6,302.0,1640.0,626.0
+349.0,594.0,195.0,337.0,12.0,38.5,219.0,14.7,79.1,487.0,165.0
+179.0,308.0,150.0,445.0,18.3,50.5,205.0,11.9,67.3,478.0,106.0
+352.0,562.0,147.0,271.0,4.41,33.1,267.0,3.89,403.0,2267.0,991.0
+352.0,599.0,433.0,791.0,5.33,96.5,723.0,4.18,22.5,127.0,29.4
+325.0,547.0,160.0,250.0,10.3,16.1,111.0,8.51,92.2,519.0,334.0
+3820.0,5829.0,125.0,209.0,1.01,103.0,528.0,10.0,94.7,578.0,267.0
+286.0,496.0,255.0,389.0,1.11,28.1,175.0,6.73,154.0,851.0,202.0
+429.0,723.0,248.0,414.0,11.7,57.3,292.0,15.0,385.0,2110.0,1263.0
+158.0,246.0,340.0,655.0,6.61,12.0,64.9,153.0,131.0,764.0,237.0
+223.0,267.0,385.0,692.0,16.0,126.0,820.0,40.0,106.0,649.0,193.0
+154.0,239.0,271.0,500.0,1.01,69.2,445.0,10.6,784.0,3854.0,1037.0
+429.0,667.0,433.0,791.0,20.7,34.0,225.0,3.02,483.0,2393.0,1084.0
+400.0,552.0,149.0,248.0,2.29,76.4,483.0,3.05,50.0,331.0,97.3
+141.0,215.0,75.7,151.0,4.14,80.6,466.0,22.3,170.0,1055.0,372.0
+483.0,757.0,259.0,491.0,15.3,75.7,474.0,12.3,69.8,414.0,250.0
+158.0,257.0,89.0,178.0,8.2,104.0,583.0,11.4,211.0,1322.0,1472.0
+355.0,533.0,302.0,567.0,9.06,62.1,362.0,9.39,135.0,799.0,235.0
+1811.0,2666.0,300.0,514.0,15.8,39.6,259.0,7.17,47.0,325.0,241.0
+191.0,262.0,71.7,121.0,8.82,103.0,615.0,36.2,474.0,2666.0,1000.0
+239.0,379.0,211.0,365.0,8.06,9.73,85.8,1.55,91.4,542.0,113.0
+281.0,478.0,673.0,1124.0,55.7,46.1,219.0,10.3,155.0,843.0,241.0
+316.0,505.0,392.0,750.0,6.49,42.2,196.0,7.3,195.0,1027.0,898.0
+389.0,685.0,843.0,1433.0,16.5,66.7,528.0,4.18,158.0,973.0,160.0
+297.0,514.0,176.0,334.0,5.88,142.0,806.0,10.2,112.0,737.0,257.0
+956.0,1499.0,322.0,523.0,4.29,62.6,396.0,30.0,32.5,205.0,135.0
+1037.0,1433.0,241.0,433.0,3.52,202.0,1219.0,83.5,54.2,281.0,92.2
+375.0,644.0,567.0,1027.0,16.7,38.2,223.0,1.08,1104.0,5674.0,965.0
+294.0,478.0,106.0,188.0,2.33,8.66,82.8,12.5,104.0,638.0,248.0
+207.0,334.0,225.0,407.0,10.7,38.2,262.0,8.28,34.9,161.0,77.7
+433.0,632.0,340.0,573.0,16.4,39.2,300.0,5.28,308.0,1794.0,368.0
+311.0,505.0,365.0,692.0,6.32,29.4,188.0,8.35,132.0,730.0,866.0
+302.0,491.0,179.0,325.0,5.0,105.0,655.0,11.4,56.7,349.0,99.1
+1762.0,2525.0,302.0,588.0,14.5,80.6,567.0,10.5,76.4,487.0,276.0
+77.0,110.0,599.0,1114.0,26.2,89.0,621.0,6.15,34.9,141.0,67.3
+209.0,313.0,160.0,316.0,10.1,124.0,835.0,15.3,34.3,181.0,143.0
+198.0,389.0,119.0,248.0,3.59,45.7,253.0,12.2,106.0,583.0,389.0
+219.0,385.0,6208.0,9058.0,308.0,19.3,130.0,5.05,259.0,1322.0,191.0
+297.0,445.0,673.0,1186.0,10.6,63.8,331.0,21.7,51.4,292.0,81.3
+158.0,276.0,167.0,292.0,12.3,71.0,418.0,4.14,47.4,264.0,145.0
+422.0,698.0,204.0,325.0,1.09,77.7,523.0,5.67,410.0,2247.0,1000.0
+118.0,163.0,46.6,102.0,4.7,112.0,679.0,17.0,422.0,2329.0,1298.0
+215.0,372.0,1596.0,2738.0,59.9,58.8,355.0,8.35,40.0,211.0,54.2
+538.0,843.0,67.9,108.0,5.19,16.4,106.0,1.0,138.0,906.0,355.0
+225.0,349.0,457.0,806.0,10.5,82.0,547.0,3.16,49.1,343.0,170.0
+202.0,325.0,667.0,1155.0,11.3,103.0,514.0,16.3,509.0,2642.0,982.0
+661.0,982.0,223.0,389.0,22.3,133.0,777.0,13.6,33.7,50.9,1094.0
+244.0,385.0,35.5,91.4,54.2,46.6,289.0,3.46,202.0,1219.0,229.0
+400.0,523.0,599.0,1075.0,10.6,198.0,1346.0,11.5,655.0,3249.0,1334.0
+1155.0,1582.0,914.0,1526.0,33.4,59.9,325.0,12.9,70.4,433.0,239.0
+311.0,533.0,267.0,441.0,2.76,49.6,319.0,9.31,62.1,403.0,44.1
+269.0,359.0,9.31,33.7,19.5,108.0,813.0,22.5,106.0,573.0,181.0
+322.0,578.0,124.0,248.0,1.51,66.7,523.0,26.7,147.0,757.0,186.0
+346.0,583.0,407.0,704.0,12.2,46.6,219.0,103.0,828.0,3995.0,1811.0
+172.0,239.0,1526.0,2350.0,50.5,64.9,496.0,17.5,583.0,3134.0,956.0
+231.0,346.0,183.0,331.0,17.9,105.0,599.0,13.1,51.9,343.0,300.0
+737.0,1219.0,181.0,322.0,6.61,59.9,433.0,15.7,94.7,528.0,150.0
+334.0,578.0,244.0,418.0,4.87,47.8,302.0,1.45,120.0,667.0,723.0
+396.0,615.0,215.0,346.0,1.14,29.4,149.0,1.93,18.1,32.8,418.0
+205.0,294.0,179.0,325.0,6.92,38.5,235.0,13.3,939.0,4870.0,1911.0
+418.0,632.0,196.0,385.0,10.8,63.8,392.0,14.6,125.0,737.0,632.0
+281.0,426.0,135.0,233.0,13.2,31.6,189.0,9.65,41.4,248.0,46.6
+264.0,396.0,1208.0,2035.0,66.7,127.0,655.0,12.3,88.2,505.0,264.0
+835.0,1286.0,730.0,1420.0,26.9,47.4,337.0,42.9,22.5,102.0,129.0
+806.0,1176.0,604.0,1114.0,12.0,88.2,583.0,10.5,165.0,882.0,542.0
+132.0,225.0,82.8,638.0,47.8,71.7,389.0,13.1,449.0,2393.0,1433.0
+583.0,922.0,533.0,874.0,26.9,21.1,189.0,2.48,478.0,2642.0,1219.0
+165.0,209.0,316.0,533.0,5.23,67.9,466.0,10.0,121.0,737.0,167.0
+160.0,248.0,375.0,704.0,8.51,27.4,142.0,4.49,117.0,730.0,146.0
+123.0,209.0,106.0,196.0,9.65,66.1,410.0,9.14,281.0,1731.0,991.0
+1046.0,1526.0,313.0,638.0,6.15,42.2,300.0,17.2,175.0,1144.0,392.0
+457.0,632.0,135.0,239.0,6.44,120.0,914.0,52.3,19.1,63.8,1512.0
+1046.0,1625.0,311.0,542.0,18.3,77.0,644.0,4.1,135.0,874.0,264.0
+161.0,239.0,289.0,573.0,3.89,44.5,231.0,1.57,250.0,1625.0,276.0
+94.7,138.0,151.0,225.0,6.21,68.5,426.0,7.77,88.2,528.0,105.0
+667.0,1219.0,237.0,407.0,6.38,57.8,343.0,7.64,96.5,466.0,133.0
+157.0,229.0,101.0,213.0,42.2,102.0,621.0,14.6,75.0,509.0,167.0
+567.0,965.0,491.0,906.0,1.79,14.2,69.2,5.38,149.0,1027.0,328.0
+231.0,372.0,820.0,1778.0,25.9,121.0,858.0,12.1,143.0,947.0,1018.0
+244.0,319.0,195.0,375.0,5.14,38.2,255.0,12.6,91.4,514.0,478.0
+246.0,372.0,294.0,523.0,5.99,82.8,478.0,10.9,69.2,372.0,207.0
+441.0,820.0,239.0,340.0,7.77,12.1,98.2,9.82,71.0,433.0,286.0
+294.0,457.0,284.0,441.0,21.5,30.8,124.0,11.4,100.0,692.0,433.0
+102.0,164.0,233.0,407.0,12.2,59.4,385.0,10.0,487.0,2690.0,1075.0
+165.0,250.0,300.0,567.0,10.5,161.0,991.0,7.91,10.4,43.7,965.0
+692.0,931.0,276.0,478.0,14.6,113.0,626.0,15.8,396.0,2017.0,496.0
+638.0,982.0,112.0,205.0,8.2,67.9,483.0,5.47,59.9,343.0,1395.0
+235.0,368.0,96.5,150.0,4.53,105.0,557.0,4.29,37.2,198.0,191.0
+248.0,429.0,244.0,453.0,8.2,41.0,200.0,6.92,130.0,770.0,255.0
+331.0,621.0,129.0,547.0,15.3,89.8,523.0,11.3,186.0,1000.0,723.0
+973.0,1472.0,77.0,114.0,13.6,25.0,137.0,8.66,86.6,588.0,127.0
+313.0,491.0,165.0,661.0,22.7,73.0,500.0,14.3,79.1,538.0,262.0
+578.0,1000.0,149.0,271.0,2.07,38.9,257.0,11.5,52.3,385.0,274.0
+750.0,1298.0,385.0,667.0,5.38,42.9,264.0,7.91,78.4,429.0,284.0
+133.0,259.0,250.0,461.0,1.0,58.3,349.0,37.9,32.5,154.0,813.0
+368.0,632.0,1860.0,2890.0,93.1,96.5,583.0,8.13,118.0,679.0,138.0
+227.0,422.0,305.0,437.0,21.9,99.1,777.0,3.13,26.2,64.4,882.0
+474.0,737.0,217.0,305.0,5.52,106.0,723.0,3.43,61.0,325.0,175.0
+200.0,294.0,1124.0,1860.0,95.6,17.9,123.0,14.3,43.7,250.0,110.0
+1104.0,1526.0,153.0,316.0,7.5,83.5,604.0,34.3,25.0,130.0,56.7
+93.1,132.0,474.0,757.0,24.8,64.9,437.0,8.9,105.0,557.0,184.0
+250.0,346.0,305.0,528.0,6.21,42.9,198.0,18.8,46.6,286.0,262.0
+1252.0,1843.0,491.0,922.0,12.0,76.4,496.0,5.0,313.0,1946.0,274.0
+262.0,483.0,135.0,241.0,3.72,87.4,533.0,8.66,11.3,53.8,84.3
+547.0,914.0,723.0,1370.0,11.0,27.9,200.0,9.73,209.0,1165.0,286.0
+202.0,337.0,89.8,196.0,8.28,91.4,470.0,23.5,45.3,274.0,129.0
+931.0,1433.0,90.6,200.0,3.31,72.3,437.0,10.7,55.2,325.0,80.6
+557.0,939.0,269.0,491.0,12.5,17.8,97.3,13.1,1611.0,7499.0,2247.0
+175.0,241.0,316.0,562.0,4.03,55.7,308.0,9.06,52.8,284.0,146.0
+379.0,523.0,64.9,121.0,2.67,56.2,286.0,5.99,205.0,1124.0,1009.0
+1114.0,1611.0,685.0,1252.0,17.2,58.8,375.0,9.91,1155.0,6378.0,2035.0
+257.0,392.0,922.0,1568.0,36.5,24.8,89.8,10.2,130.0,698.0,233.0
+133.0,235.0,552.0,1009.0,6.61,75.0,403.0,11.0,71.0,375.0,202.0
+96.5,150.0,215.0,316.0,8.9,43.3,284.0,4.37,50.5,292.0,168.0
+1843.0,2788.0,523.0,931.0,19.3,50.5,267.0,5.73,52.3,286.0,151.0
+723.0,1252.0,519.0,991.0,14.9,47.0,250.0,1.0,34.9,188.0,34.9
+127.0,186.0,396.0,717.0,11.9,28.9,202.0,14.3,86.6,487.0,382.0
+105.0,183.0,145.0,264.0,4.03,157.0,1055.0,33.4,90.6,533.0,300.0
+198.0,340.0,115.0,193.0,1.95,23.7,184.0,7.77,400.0,2480.0,757.0
+196.0,313.0,730.0,1346.0,15.5,69.8,385.0,8.58,27.4,108.0,111.0
+346.0,562.0,200.0,331.0,8.58,5.57,20.5,79.9,44.1,262.0,87.4
+184.0,289.0,284.0,478.0,10.3,42.2,325.0,7.7,95.6,542.0,244.0
+202.0,519.0,325.0,483.0,7.7,45.7,244.0,11.4,120.0,621.0,286.0
+99.1,126.0,300.0,496.0,20.4,23.5,141.0,7.1,73.0,478.0,108.0
+271.0,403.0,433.0,698.0,21.5,28.4,150.0,16.1,184.0,956.0,146.0
+117.0,173.0,176.0,311.0,7.04,54.7,429.0,4.0,154.0,906.0,139.0
+57.8,114.0,400.0,730.0,6.44,41.4,179.0,12.6,403.0,2129.0,2436.0
+235.0,355.0,717.0,1433.0,29.7,37.5,205.0,15.7,96.5,547.0,160.0
+644.0,1009.0,828.0,1472.0,80.6,32.8,160.0,6.67,59.4,340.0,80.6
+368.0,632.0,491.0,791.0,13.9,22.9,123.0,18.4,204.0,1018.0,2864.0
+313.0,461.0,50.5,142.0,71.7,38.5,271.0,8.2,47.0,279.0,124.0
+186.0,286.0,2110.0,3491.0,53.8,20.2,145.0,2.97,54.2,311.0,103.0
+200.0,286.0,267.0,478.0,7.99,60.4,375.0,6.92,223.0,1219.0,1843.0
+325.0,519.0,178.0,328.0,2.69,89.8,655.0,7.99,59.4,305.0,217.0
+743.0,1124.0,93.9,167.0,10.2,41.0,316.0,5.94,189.0,1230.0,237.0
+127.0,250.0,131.0,257.0,8.98,21.9,103.0,8.58,109.0,692.0,158.0
+108.0,167.0,284.0,470.0,9.06,61.0,311.0,3.05,42.9,215.0,75.7
+1715.0,2480.0,365.0,704.0,8.2,84.3,505.0,14.9,36.5,189.0,111.0
+334.0,528.0,155.0,284.0,4.26,99.1,557.0,20.2,83.5,538.0,178.0
+126.0,205.0,168.0,284.0,10.1,61.0,340.0,16.8,85.1,509.0,191.0
+138.0,255.0,54.2,90.6,5.14,42.6,300.0,2.48,158.0,939.0,253.0
+445.0,632.0,183.0,355.0,4.53,39.2,211.0,8.66,75.7,496.0,173.0
+851.0,1310.0,389.0,632.0,4.37,63.8,349.0,69.8,241.0,1407.0,982.0
+121.0,205.0,93.1,211.0,9.91,8.28,22.5,58.3,57.3,429.0,111.0
+2329.0,3398.0,328.0,567.0,12.4,111.0,717.0,9.06,151.0,1055.0,237.0
+217.0,308.0,267.0,496.0,7.3,30.5,231.0,13.9,135.0,750.0,297.0
+147.0,215.0,184.0,325.0,5.73,20.7,141.0,1.7,39.6,257.0,241.0
+189.0,328.0,359.0,649.0,5.83,59.9,319.0,20.7,56.2,352.0,396.0
+168.0,248.0,547.0,991.0,17.6,51.9,322.0,12.6,38.5,257.0,74.3
+311.0,514.0,250.0,418.0,16.4,95.6,542.0,14.2,93.1,698.0,262.0
+2017.0,3220.0,104.0,179.0,1.0,123.0,770.0,35.5,35.5,241.0,117.0
+449.0,667.0,1055.0,1794.0,38.2,36.2,160.0,23.7,50.9,313.0,69.8
+257.0,355.0,799.0,1655.0,40.0,40.0,289.0,10.1,1065.0,4958.0,1310.0
+161.0,300.0,743.0,1472.0,31.6,24.8,142.0,6.61,777.0,3854.0,1165.0
+379.0,604.0,331.0,632.0,11.5,97.3,533.0,11.0,81.3,457.0,227.0
+41.0,45.3,644.0,1144.0,22.1,79.1,519.0,19.5,45.3,92.2,667.0
+227.0,362.0,138.0,253.0,2.27,56.2,392.0,6.67,198.0,1219.0,281.0
+237.0,311.0,196.0,343.0,7.37,69.8,400.0,13.6,93.9,437.0,621.0
+1486.0,2227.0,743.0,1407.0,15.3,106.0,698.0,28.1,139.0,799.0,322.0
+79.9,104.0,101.0,186.0,9.22,42.6,313.0,7.17,49.1,281.0,77.0
+806.0,1219.0,183.0,337.0,1.01,80.6,610.0,2.76,186.0,1134.0,392.0
+153.0,286.0,562.0,1046.0,11.1,141.0,914.0,7.91,118.0,698.0,1685.0
+195.0,328.0,799.0,1526.0,23.3,57.8,193.0,2.21,170.0,1084.0,221.0
+244.0,400.0,119.0,215.0,6.85,62.1,385.0,7.04,49.6,300.0,127.0
+1114.0,1685.0,158.0,286.0,9.65,19.1,75.0,6.1,25.7,146.0,46.1
+538.0,764.0,2267.0,3619.0,91.4,82.0,474.0,23.7,679.0,3555.0,1176.0
+31.1,99.1,35.9,58.3,4.33,61.5,403.0,1.0,31.3,163.0,661.0
+496.0,730.0,142.0,284.0,1.0,32.2,195.0,46.1,77.0,396.0,137.0
+279.0,429.0,379.0,723.0,10.2,60.4,375.0,11.7,28.9,207.0,80.6
+1526.0,2187.0,281.0,483.0,10.6,19.5,82.8,7.57,164.0,866.0,2148.0
+828.0,1263.0,219.0,457.0,17.3,23.7,118.0,3.22,97.3,737.0,337.0
+259.0,368.0,124.0,202.0,10.4,19.1,129.0,4.29,45.7,253.0,770.0
+470.0,743.0,84.3,142.0,6.26,44.1,334.0,6.44,85.8,547.0,255.0
+1197.0,1747.0,233.0,461.0,18.6,33.7,168.0,7.91,487.0,2503.0,1486.0
+221.0,331.0,241.0,453.0,5.47,29.7,139.0,1.7,58.8,355.0,931.0
+93.1,137.0,176.0,322.0,14.1,47.0,289.0,1.0,82.8,478.0,241.0
+305.0,491.0,1459.0,2329.0,57.3,36.5,225.0,6.44,11.2,76.4,269.0
+231.0,372.0,161.0,289.0,8.06,101.0,594.0,11.7,62.6,400.0,200.0
+281.0,433.0,150.0,274.0,1.42,38.2,221.0,13.6,4.96,26.4,750.0
+81.3,106.0,422.0,813.0,2.89,43.7,244.0,14.1,599.0,3220.0,947.0
+231.0,365.0,692.0,1322.0,25.0,146.0,914.0,3.22,43.3,231.0,163.0
+279.0,478.0,125.0,225.0,13.8,37.2,221.0,114.0,158.0,973.0,316.0
+271.0,519.0,1286.0,2207.0,213.0,97.3,698.0,9.47,305.0,1778.0,1186.0
+200.0,308.0,1670.0,2690.0,61.0,25.0,178.0,8.51,286.0,1486.0,770.0
+98.2,165.0,426.0,710.0,25.9,54.7,319.0,1.68,1000.0,5048.0,2110.0
+233.0,437.0,27.6,102.0,44.9,54.7,297.0,8.2,85.8,474.0,379.0
+138.0,207.0,141.0,276.0,1.0,54.2,349.0,13.6,281.0,1526.0,777.0
+302.0,509.0,81.3,491.0,26.4,191.0,1219.0,43.3,63.2,375.0,71.0
+143.0,255.0,178.0,313.0,1.0,15.7,48.3,36.5,72.3,453.0,229.0
+237.0,365.0,372.0,806.0,20.7,55.2,368.0,5.94,149.0,866.0,1263.0
+131.0,223.0,692.0,1382.0,14.7,103.0,764.0,10.6,191.0,1263.0,253.0
+372.0,519.0,478.0,799.0,22.3,47.8,281.0,6.49,61.0,385.0,145.0
+523.0,890.0,250.0,410.0,10.6,141.0,866.0,85.1,24.4,147.0,94.7
+325.0,542.0,262.0,478.0,20.0,79.1,429.0,3.46,21.5,118.0,124.0
+474.0,791.0,302.0,410.0,10.0,53.3,407.0,13.2,253.0,1286.0,372.0
+151.0,262.0,207.0,372.0,17.6,85.8,519.0,15.4,61.5,233.0,319.0
+250.0,389.0,281.0,491.0,6.55,71.7,500.0,6.04,88.2,509.0,135.0
+418.0,673.0,777.0,1420.0,3.72,24.6,165.0,2.39,53.3,316.0,176.0
+115.0,170.0,346.0,567.0,11.1,37.9,178.0,5.14,246.0,1370.0,379.0
+743.0,1104.0,211.0,365.0,1.24,77.0,441.0,5.94,137.0,898.0,365.0
+259.0,362.0,410.0,1075.0,59.9,42.2,213.0,13.0,142.0,806.0,743.0
+496.0,757.0,151.0,300.0,6.15,83.5,588.0,1.57,40.7,269.0,121.0
+132.0,213.0,96.5,178.0,4.45,38.2,223.0,4.87,36.8,193.0,207.0
+308.0,441.0,478.0,914.0,15.8,54.2,389.0,4.41,22.9,131.0,196.0
+259.0,445.0,673.0,1310.0,16.7,1.0,7.1,12.4,52.3,305.0,343.0
+385.0,638.0,799.0,1554.0,24.1,79.9,538.0,13.8,56.7,340.0,77.0
+297.0,514.0,308.0,547.0,22.1,67.3,355.0,6.85,75.0,433.0,519.0
+349.0,547.0,158.0,237.0,1.01,69.8,382.0,14.5,188.0,922.0,1395.0
+271.0,453.0,466.0,777.0,11.3,66.7,379.0,9.65,69.2,389.0,175.0
+172.0,271.0,352.0,661.0,31.9,85.8,557.0,24.8,86.6,491.0,253.0
+710.0,1197.0,449.0,770.0,15.0,47.0,325.0,4.61,47.0,297.0,41.8
+281.0,483.0,231.0,389.0,9.65,17.8,121.0,7.3,32.5,204.0,135.0
+337.0,509.0,231.0,445.0,6.38,10.5,61.0,7.17,186.0,1219.0,248.0
+392.0,542.0,250.0,382.0,2.05,33.7,284.0,11.5,95.6,567.0,1065.0
+231.0,362.0,142.0,248.0,5.88,85.8,583.0,26.7,17.2,85.1,50.5
+626.0,1018.0,743.0,1298.0,16.8,122.0,730.0,17.9,33.4,198.0,120.0
+730.0,1208.0,311.0,519.0,19.1,47.8,276.0,8.98,61.5,352.0,362.0
+276.0,375.0,186.0,368.0,4.29,61.5,400.0,21.1,126.0,820.0,113.0
+523.0,914.0,138.0,223.0,7.84,77.0,500.0,10.2,311.0,1911.0,349.0
+331.0,496.0,441.0,866.0,10.8,117.0,835.0,17.9,355.0,1981.0,1275.0
+191.0,319.0,349.0,737.0,1.01,19.6,107.0,1.58,142.0,813.0,340.0
+1000.0,1526.0,685.0,1186.0,20.7,25.9,143.0,5.57,111.0,698.0,205.0
+599.0,1018.0,474.0,799.0,11.2,219.0,1499.0,18.6,101.0,621.0,129.0
+103.0,155.0,104.0,202.0,1.37,71.0,514.0,5.47,53.8,281.0,120.0
+305.0,422.0,478.0,898.0,11.5,15.4,79.1,1.36,28.1,160.0,94.7
+276.0,396.0,215.0,414.0,9.39,45.7,331.0,2.86,67.3,355.0,196.0
+557.0,828.0,1512.0,2595.0,294.0,45.3,276.0,12.2,13.0,64.9,1084.0
+105.0,200.0,483.0,931.0,5.73,75.0,445.0,13.2,47.8,325.0,172.0
+292.0,461.0,349.0,661.0,4.57,41.4,305.0,9.91,111.0,843.0,207.0
+130.0,244.0,233.0,400.0,5.19,98.2,610.0,20.4,54.2,349.0,142.0
+4614.0,7105.0,151.0,267.0,13.7,34.9,204.0,6.26,53.8,311.0,118.0
+322.0,474.0,567.0,1094.0,13.8,43.3,196.0,1.51,25.0,66.1,578.0
+135.0,207.0,164.0,319.0,1.78,35.9,262.0,13.9,770.0,3619.0,947.0
+195.0,281.0,1670.0,2548.0,98.2,40.7,227.0,12.7,76.4,426.0,359.0
+213.0,349.0,400.0,820.0,7.84,51.4,239.0,5.57,109.0,717.0,259.0
+478.0,973.0,389.0,1554.0,117.0,89.0,626.0,16.5,1186.0,5573.0,1144.0
+225.0,343.0,372.0,621.0,12.7,12.1,53.8,136.0,71.7,400.0,308.0
+487.0,757.0,835.0,1358.0,7.23,67.9,407.0,10.0,167.0,991.0,632.0
+253.0,368.0,96.5,170.0,3.22,122.0,552.0,22.7,30.2,158.0,362.0
+400.0,557.0,588.0,1065.0,13.5,16.4,92.2,4.45,172.0,1027.0,325.0
+213.0,382.0,322.0,594.0,7.57,56.7,328.0,4.53,129.0,750.0,267.0
+237.0,362.0,2148.0,3278.0,37.2,15.1,106.0,1.0,81.3,538.0,250.0
+253.0,437.0,149.0,302.0,10.1,36.5,233.0,6.61,32.8,223.0,82.0
+418.0,673.0,110.0,217.0,3.79,37.2,193.0,5.28,115.0,615.0,113.0
+195.0,325.0,250.0,433.0,8.82,143.0,1037.0,84.3,57.8,349.0,132.0
+74.3,115.0,168.0,410.0,22.3,54.2,297.0,14.1,97.3,604.0,193.0
+106.0,151.0,346.0,594.0,7.23,15.3,75.7,9.56,85.8,362.0,362.0
+328.0,528.0,198.0,294.0,6.38,74.3,496.0,4.66,83.5,528.0,319.0
+207.0,311.0,445.0,813.0,11.1,44.5,305.0,10.2,125.0,764.0,246.0
+294.0,414.0,104.0,191.0,10.6,31.1,255.0,5.33,28.9,160.0,66.1
+151.0,292.0,1346.0,2247.0,126.0,60.4,305.0,14.3,87.4,552.0,1596.0
+257.0,487.0,136.0,255.0,4.66,35.2,204.0,4.49,43.3,286.0,173.0
+105.0,151.0,750.0,1596.0,24.6,126.0,874.0,35.2,109.0,704.0,85.1
+294.0,474.0,209.0,385.0,8.43,66.1,375.0,2.29,5.23,34.0,973.0
+154.0,181.0,649.0,1027.0,52.8,70.4,500.0,7.17,79.9,483.0,262.0
+389.0,667.0,183.0,355.0,8.66,49.1,365.0,7.37,259.0,1446.0,588.0
+111.0,161.0,500.0,866.0,24.6,76.4,445.0,6.38,9.22,34.3,523.0
+340.0,588.0,505.0,858.0,11.2,81.3,509.0,2.57,41.8,294.0,157.0
+92.2,130.0,372.0,757.0,21.5,82.0,491.0,8.28,161.0,947.0,375.0
+1370.0,1860.0,193.0,385.0,257.0,70.4,410.0,5.67,49.1,311.0,84.3
+30.0,71.7,193.0,325.0,8.98,18.4,123.0,1.93,127.0,914.0,284.0
+355.0,519.0,692.0,1310.0,13.8,117.0,806.0,31.3,163.0,991.0,483.0
+57.8,50.5,474.0,858.0,8.98,19.3,167.0,8.58,167.0,1124.0,410.0
+202.0,302.0,74.3,93.9,12.0,69.2,457.0,20.2,55.7,340.0,211.0
+316.0,449.0,316.0,588.0,17.5,32.2,202.0,5.83,53.3,328.0,131.0
+730.0,1241.0,267.0,470.0,9.06,117.0,638.0,6.55,107.0,649.0,279.0
+1794.0,2714.0,271.0,487.0,1.38,34.0,163.0,7.84,229.0,1395.0,777.0
+1459.0,2110.0,170.0,313.0,7.43,53.3,372.0,8.35,213.0,1155.0,509.0
+331.0,523.0,191.0,325.0,10.0,47.0,355.0,12.0,54.2,340.0,225.0
+1037.0,1611.0,281.0,474.0,14.1,27.4,132.0,1.98,437.0,2329.0,1075.0
+379.0,573.0,1459.0,2267.0,46.6,37.5,241.0,8.28,93.9,604.0,167.0
+679.0,1018.0,259.0,407.0,19.6,80.6,457.0,21.9,131.0,939.0,213.0
+547.0,858.0,1843.0,2943.0,51.4,42.9,276.0,20.9,77.7,433.0,209.0
+14.5,32.5,655.0,1186.0,16.4,50.0,375.0,1.42,35.5,211.0,90.6
+77.0,124.0,284.0,523.0,11.2,85.1,599.0,15.5,186.0,1165.0,337.0
+523.0,866.0,106.0,198.0,3.72,36.8,217.0,1.0,158.0,931.0,322.0
+500.0,661.0,276.0,491.0,17.2,59.9,322.0,6.79,487.0,2890.0,573.0
+231.0,426.0,223.0,379.0,6.1,106.0,509.0,10.3,91.4,567.0,200.0
+359.0,615.0,604.0,1084.0,18.4,77.0,474.0,2.35,62.6,389.0,90.6
+264.0,418.0,457.0,874.0,10.4,53.3,346.0,2.09,8.06,37.2,1037.0
+328.0,557.0,939.0,1472.0,92.2,86.6,453.0,31.9,32.2,164.0,137.0
+202.0,313.0,770.0,1298.0,27.1,183.0,1241.0,66.1,1094.0,5523.0,1219.0
+557.0,922.0,337.0,567.0,17.3,53.8,331.0,16.0,108.0,573.0,130.0
+131.0,239.0,172.0,319.0,7.84,37.5,221.0,11.3,96.5,583.0,246.0
+85.1,137.0,311.0,533.0,16.5,28.1,123.0,6.98,717.0,3685.0,1075.0
+121.0,165.0,743.0,1407.0,5.57,16.4,184.0,63.2,113.0,685.0,246.0
+1794.0,2480.0,340.0,610.0,21.9,32.5,147.0,15.4,11.1,59.9,60.4
+514.0,704.0,316.0,661.0,5.57,79.9,382.0,10.6,205.0,1263.0,562.0
+991.0,1420.0,186.0,349.0,5.23,51.4,316.0,3.82,655.0,3249.0,1197.0
+470.0,835.0,109.0,235.0,18.8,45.7,276.0,13.5,130.0,843.0,213.0
+56.2,103.0,239.0,449.0,22.1,71.7,547.0,12.1,82.0,474.0,231.0
+132.0,217.0,311.0,632.0,1.67,79.9,496.0,3.68,29.2,137.0,956.0
+698.0,1124.0,155.0,286.0,12.1,75.0,410.0,26.7,25.0,115.0,40.3
+73.0,112.0,108.0,244.0,10.3,25.3,110.0,6.38,71.0,483.0,189.0
+269.0,414.0,179.0,328.0,1.64,95.6,615.0,17.3,56.7,349.0,533.0
+257.0,396.0,235.0,385.0,2.71,105.0,594.0,39.6,45.7,248.0,81.3
+259.0,372.0,118.0,193.0,1.26,26.7,184.0,1.0,239.0,1512.0,422.0
+150.0,241.0,142.0,259.0,9.31,43.7,259.0,12.6,64.4,403.0,259.0
+193.0,349.0,250.0,437.0,1.64,137.0,914.0,12.3,445.0,2329.0,2148.0
+221.0,385.0,764.0,1310.0,9.31,47.8,229.0,17.8,16.0,61.5,1568.0
+375.0,610.0,562.0,914.0,13.7,69.8,426.0,10.3,138.0,698.0,302.0
+67.9,97.3,615.0,1230.0,17.9,10.2,84.3,50.5,160.0,882.0,219.0
+286.0,449.0,337.0,632.0,15.1,24.4,175.0,3.68,41.0,262.0,215.0
+294.0,519.0,379.0,737.0,10.3,30.0,175.0,6.15,92.2,632.0,269.0
+102.0,181.0,898.0,1568.0,22.1,37.5,246.0,10.0,57.8,334.0,1252.0
+155.0,184.0,308.0,500.0,18.4,51.9,368.0,8.2,179.0,1046.0,176.0
+184.0,302.0,209.0,325.0,11.2,11.0,91.4,3.75,99.1,644.0,414.0
+300.0,514.0,343.0,610.0,7.04,34.0,142.0,6.49,32.5,172.0,66.1
+858.0,1358.0,244.0,437.0,19.1,34.0,127.0,7.04,48.3,300.0,69.2
+284.0,528.0,223.0,379.0,8.13,52.8,233.0,11.7,947.0,4656.0,1731.0
+262.0,355.0,813.0,1370.0,67.3,18.6,107.0,6.85,14.1,60.4,626.0
+349.0,496.0,241.0,337.0,7.84,62.1,334.0,9.56,52.8,322.0,70.4
+68.5,105.0,205.0,365.0,6.61,19.1,81.3,13.3,79.9,414.0,157.0
+227.0,410.0,217.0,414.0,2.09,48.7,355.0,5.14,46.1,281.0,743.0
+29.7,51.4,211.0,407.0,2.97,95.6,573.0,10.8,127.0,638.0,461.0
+207.0,313.0,239.0,389.0,15.8,15.7,51.9,5.42,44.9,316.0,165.0
+115.0,170.0,292.0,557.0,4.0,32.8,235.0,4.45,64.9,389.0,193.0
+186.0,300.0,68.5,262.0,13.2,23.1,163.0,4.26,49.1,337.0,181.0
+155.0,274.0,213.0,396.0,9.47,52.3,248.0,12.1,106.0,770.0,179.0
+181.0,297.0,150.0,271.0,1.0,67.3,392.0,10.7,47.0,250.0,882.0
+770.0,1197.0,264.0,392.0,4.83,21.3,150.0,15.3,81.3,433.0,179.0
+110.0,186.0,33.7,59.9,37.9,106.0,667.0,13.8,123.0,667.0,271.0
+578.0,1009.0,248.0,523.0,3.92,56.7,313.0,23.9,55.7,313.0,44.9
+248.0,422.0,158.0,267.0,11.2,49.1,264.0,5.52,12.4,69.8,231.0
+239.0,375.0,183.0,302.0,5.57,40.7,233.0,4.37,250.0,1407.0,505.0
+178.0,294.0,528.0,973.0,16.5,21.9,83.5,1.08,51.4,322.0,340.0
+167.0,289.0,308.0,538.0,3.05,29.7,164.0,3.4,820.0,4217.0,914.0
+578.0,914.0,1382.0,2247.0,53.8,54.2,305.0,10.7,41.8,244.0,102.0
+237.0,334.0,308.0,514.0,1.0,118.0,835.0,21.1,235.0,1358.0,632.0
+340.0,483.0,176.0,311.0,2.53,73.0,496.0,13.1,173.0,1027.0,362.0
+300.0,519.0,93.1,165.0,11.8,45.7,281.0,18.9,86.6,621.0,349.0
+615.0,931.0,95.6,163.0,3.75,59.4,281.0,7.57,22.7,137.0,122.0
+874.0,1370.0,407.0,655.0,12.5,50.5,379.0,2.48,98.2,557.0,215.0
+209.0,322.0,95.6,188.0,4.37,81.3,588.0,16.1,73.0,426.0,289.0
+67.3,113.0,269.0,1165.0,63.8,7.7,14.5,120.0,59.9,365.0,106.0
+269.0,422.0,483.0,835.0,18.9,92.2,594.0,20.2,130.0,806.0,213.0
+1009.0,1526.0,407.0,784.0,9.91,28.6,198.0,16.0,491.0,2738.0,1263.0
+117.0,198.0,231.0,426.0,6.67,44.9,231.0,10.5,1018.0,5328.0,2148.0
+96.5,99.1,200.0,340.0,3.05,69.8,491.0,12.4,509.0,2839.0,1252.0
+235.0,316.0,110.0,167.0,3.75,95.6,578.0,9.91,92.2,673.0,292.0
+547.0,931.0,305.0,483.0,11.1,50.9,286.0,1.84,65.5,372.0,322.0
+184.0,311.0,102.0,193.0,17.6,119.0,704.0,6.26,93.9,594.0,233.0
+491.0,813.0,638.0,1275.0,27.6,33.1,221.0,1.0,40.7,274.0,104.0
+289.0,396.0,382.0,679.0,19.6,52.8,359.0,2.27,77.0,407.0,382.0
+184.0,319.0,161.0,302.0,5.33,39.6,248.0,14.1,51.9,322.0,106.0
+461.0,644.0,175.0,322.0,2.09,29.7,160.0,7.99,49.1,297.0,145.0
+163.0,235.0,90.6,179.0,2.0,66.7,375.0,11.5,35.9,188.0,289.0
+196.0,334.0,2666.0,4740.0,184.0,93.9,519.0,9.22,717.0,3555.0,3398.0
+104.0,143.0,267.0,496.0,4.49,110.0,757.0,17.3,141.0,813.0,346.0
+547.0,874.0,328.0,426.0,24.1,48.7,325.0,8.06,58.8,403.0,276.0
+355.0,594.0,308.0,505.0,5.62,20.7,151.0,7.7,119.0,835.0,147.0
+523.0,858.0,235.0,478.0,14.2,39.2,223.0,2.71,62.6,368.0,328.0
+538.0,843.0,365.0,578.0,3.62,24.8,219.0,15.7,583.0,3051.0,1241.0
+255.0,429.0,271.0,414.0,9.31,79.1,514.0,62.6,164.0,791.0,939.0
+198.0,349.0,217.0,437.0,7.04,77.7,533.0,92.2,43.7,271.0,147.0
+1999.0,3051.0,172.0,289.0,2.41,56.7,269.0,12.6,66.1,429.0,113.0
+204.0,164.0,300.0,542.0,10.7,22.5,136.0,3.72,50.9,211.0,311.0
+237.0,325.0,281.0,562.0,6.67,21.3,111.0,5.42,46.1,281.0,300.0
+644.0,1084.0,500.0,851.0,11.2,45.7,365.0,1.0,71.7,433.0,359.0
+588.0,874.0,308.0,583.0,11.3,89.8,583.0,11.9,57.3,313.0,219.0
+1526.0,2371.0,229.0,396.0,9.31,27.4,198.0,5.67,49.6,319.0,79.1
+1596.0,2267.0,426.0,843.0,25.9,54.7,346.0,14.7,138.0,947.0,372.0
+253.0,325.0,274.0,449.0,26.7,27.1,137.0,3.37,120.0,791.0,219.0
+410.0,717.0,189.0,375.0,17.6,10.5,8.9,13.1,184.0,1055.0,269.0
+3368.0,4958.0,410.0,632.0,28.6,21.5,83.5,75.0,26.4,146.0,80.6
+31.6,64.4,437.0,757.0,16.4,76.4,533.0,21.3,74.3,474.0,215.0
+173.0,279.0,1446.0,2436.0,70.4,90.6,679.0,5.05,85.1,474.0,233.0
+730.0,1208.0,233.0,379.0,9.47,51.9,163.0,18.1,196.0,1084.0,389.0
+83.5,96.5,1263.0,2072.0,17.6,15.5,107.0,10.0,92.2,547.0,141.0
+184.0,316.0,211.0,343.0,1.07,34.9,231.0,8.82,96.5,673.0,219.0
+99.1,124.0,407.0,757.0,21.1,2.39,8.43,11.7,198.0,1197.0,316.0
+355.0,632.0,1640.0,2480.0,118.0,43.3,286.0,10.6,115.0,667.0,355.0
+264.0,407.0,165.0,470.0,108.0,56.7,403.0,9.91,31.9,244.0,87.4
+392.0,604.0,64.9,110.0,8.82,172.0,1055.0,8.98,229.0,1370.0,392.0
+474.0,750.0,52.3,82.0,3.46,47.4,255.0,7.64,858.0,4332.0,1027.0
+956.0,1446.0,552.0,956.0,25.5,41.4,331.0,2.94,69.8,389.0,132.0
+410.0,644.0,188.0,316.0,6.67,24.4,141.0,10.4,1046.0,5425.0,2267.0
+108.0,179.0,799.0,1298.0,16.1,58.3,305.0,32.8,71.7,392.0,198.0
+225.0,359.0,337.0,573.0,16.4,49.1,322.0,51.9,131.0,692.0,305.0
+274.0,396.0,133.0,204.0,7.3,33.1,178.0,1.01,10.6,79.9,322.0
+346.0,583.0,1911.0,2943.0,100.0,132.0,632.0,40.0,153.0,882.0,264.0
+1512.0,2167.0,186.0,322.0,14.7,18.4,84.3,6.44,69.8,400.0,104.0
+132.0,237.0,799.0,1407.0,18.9,28.4,178.0,9.56,93.1,519.0,262.0
+97.3,161.0,181.0,346.0,4.78,50.5,352.0,1.63,542.0,3220.0,453.0
+221.0,340.0,449.0,858.0,17.2,20.7,125.0,3.65,229.0,1219.0,806.0
+255.0,418.0,233.0,382.0,8.35,58.3,325.0,5.23,64.9,500.0,135.0
+150.0,231.0,186.0,328.0,7.77,48.7,284.0,2.94,120.0,621.0,898.0
+253.0,403.0,95.6,164.0,11.5,74.3,542.0,16.5,60.4,340.0,136.0
+922.0,1420.0,297.0,426.0,30.8,2.76,19.5,99.1,1046.0,5186.0,2247.0
+211.0,284.0,284.0,599.0,11.1,112.0,655.0,34.9,63.8,362.0,175.0
+97.3,64.4,91.4,170.0,7.17,147.0,914.0,11.8,67.9,433.0,202.0
+167.0,253.0,205.0,379.0,8.2,13.3,73.0,12.7,53.8,294.0,191.0
+632.0,1065.0,322.0,538.0,11.7,94.7,679.0,18.3,43.7,225.0,730.0
+85.1,150.0,947.0,1596.0,18.6,87.4,562.0,10.9,61.5,426.0,313.0
+205.0,334.0,87.4,151.0,6.32,225.0,1382.0,74.3,142.0,874.0,264.0
+302.0,487.0,496.0,882.0,22.7,28.1,146.0,20.7,23.5,146.0,121.0
+573.0,939.0,102.0,186.0,1.12,130.0,820.0,30.5,66.7,478.0,319.0
+269.0,362.0,227.0,349.0,14.5,137.0,1000.0,30.2,259.0,1459.0,305.0
+843.0,1275.0,146.0,279.0,10.4,64.4,400.0,4.91,64.4,418.0,142.0
+1554.0,2187.0,723.0,1310.0,23.7,31.1,198.0,8.82,914.0,4656.0,874.0
+193.0,237.0,289.0,478.0,8.13,8.51,46.1,81.3,32.8,211.0,35.2
+274.0,396.0,204.0,355.0,2.02,75.7,372.0,9.22,55.2,311.0,233.0
+562.0,843.0,547.0,973.0,13.5,50.5,294.0,11.1,53.3,349.0,175.0
+382.0,487.0,359.0,573.0,7.7,42.9,264.0,3.62,91.4,578.0,211.0
+1155.0,1700.0,255.0,466.0,8.66,23.9,130.0,8.74,73.0,457.0,175.0
+1075.0,1625.0,155.0,289.0,5.38,17.3,100.0,13.3,139.0,882.0,178.0
+294.0,400.0,183.0,325.0,3.0,27.9,176.0,2.53,157.0,890.0,365.0
+644.0,1144.0,237.0,385.0,17.6,55.2,253.0,11.4,76.4,487.0,131.0
+22.3,24.8,200.0,343.0,7.23,40.7,279.0,12.6,33.7,200.0,137.0
+343.0,470.0,737.0,2035.0,93.1,69.8,478.0,17.2,193.0,1275.0,410.0
+160.0,207.0,241.0,433.0,6.79,10.3,75.7,4.33,14.1,72.3,241.0
+445.0,710.0,331.0,632.0,8.35,33.4,196.0,81.3,743.0,3924.0,1298.0
+66.1,95.6,255.0,457.0,10.7,16.4,97.3,11.1,68.5,392.0,269.0
+533.0,874.0,12.5,15.7,17.5,81.3,466.0,8.66,125.0,743.0,281.0
+129.0,193.0,70.4,109.0,6.92,28.9,163.0,2.81,35.9,244.0,85.8
+173.0,241.0,241.0,418.0,11.7,163.0,1046.0,5.88,1104.0,5989.0,2436.0
+223.0,311.0,297.0,562.0,9.91,59.4,396.0,3.55,53.3,294.0,106.0
+121.0,175.0,59.9,188.0,36.8,39.2,250.0,4.18,77.7,418.0,207.0
+300.0,441.0,414.0,757.0,13.7,77.7,638.0,31.1,117.0,567.0,519.0
+246.0,410.0,418.0,626.0,15.0,117.0,710.0,22.9,66.1,449.0,396.0
+141.0,246.0,340.0,673.0,17.9,53.3,422.0,5.28,85.8,466.0,196.0
+179.0,340.0,125.0,213.0,5.23,67.9,500.0,9.73,24.4,126.0,204.0
+297.0,407.0,1894.0,2890.0,39.2,127.0,906.0,31.6,124.0,898.0,557.0
+193.0,257.0,259.0,375.0,14.2,59.9,352.0,6.44,189.0,947.0,1134.0
+414.0,626.0,213.0,346.0,10.7,5.19,29.4,86.6,68.5,407.0,205.0
+91.4,106.0,316.0,573.0,3.75,125.0,858.0,73.0,86.6,594.0,292.0
+90.6,133.0,956.0,1625.0,32.2,119.0,594.0,5.23,45.3,319.0,84.3
+791.0,1298.0,255.0,441.0,10.3,79.1,407.0,82.8,334.0,1911.0,1134.0
+679.0,1186.0,58.3,114.0,1.0,50.0,385.0,14.6,29.2,150.0,77.0
+111.0,183.0,441.0,874.0,6.92,22.3,124.0,1.0,74.3,487.0,355.0
+155.0,221.0,991.0,1685.0,30.8,53.3,305.0,18.1,189.0,1124.0,562.0
+717.0,1144.0,155.0,239.0,1.0,66.7,509.0,6.44,94.7,514.0,661.0
+890.0,1370.0,205.0,385.0,5.94,60.4,337.0,15.0,115.0,704.0,248.0
+193.0,313.0,66.7,106.0,3.55,21.9,120.0,1.96,3.85,44.5,39.2
+244.0,389.0,289.0,453.0,16.7,89.0,685.0,5.28,1134.0,5140.0,1827.0
+160.0,231.0,229.0,400.0,14.5,74.3,567.0,4.78,164.0,1037.0,246.0
+557.0,914.0,145.0,239.0,1.0,59.4,500.0,2.62,158.0,947.0,217.0
+221.0,385.0,279.0,538.0,7.1,124.0,764.0,25.5,250.0,1298.0,157.0
+259.0,396.0,183.0,322.0,16.8,8.51,63.2,67.9,37.9,202.0,132.0
+368.0,557.0,655.0,1176.0,25.9,22.9,170.0,11.9,547.0,2969.0,874.0
+102.0,127.0,189.0,313.0,12.5,27.4,179.0,3.59,533.0,3023.0,1046.0
+2054.0,3106.0,509.0,965.0,18.1,35.9,225.0,8.9,40.3,207.0,157.0
+407.0,594.0,313.0,567.0,39.2,40.0,311.0,3.82,75.7,496.0,147.0
+737.0,1104.0,396.0,710.0,21.3,157.0,914.0,27.4,179.0,1046.0,302.0
+165.0,209.0,487.0,1009.0,8.82,37.9,205.0,6.85,181.0,906.0,1486.0
+311.0,461.0,191.0,382.0,7.17,26.2,153.0,16.7,50.9,300.0,183.0
+1334.0,2091.0,757.0,1252.0,56.2,82.0,557.0,15.1,241.0,1420.0,297.0
+188.0,340.0,115.0,225.0,13.6,41.8,294.0,13.3,38.9,205.0,39.2
+1208.0,1794.0,784.0,1433.0,14.9,15.7,105.0,6.04,667.0,3368.0,813.0
+1358.0,2091.0,179.0,300.0,10.6,14.2,111.0,10.9,106.0,655.0,157.0
+109.0,149.0,362.0,644.0,12.0,105.0,710.0,13.6,31.9,188.0,215.0
+271.0,426.0,143.0,233.0,8.13,34.0,167.0,9.82,51.4,305.0,131.0
+115.0,173.0,316.0,604.0,10.0,52.3,313.0,2.44,72.3,418.0,281.0
+151.0,264.0,375.0,632.0,25.0,56.7,362.0,4.33,219.0,1176.0,250.0
+365.0,514.0,264.0,487.0,1.26,50.9,322.0,13.7,89.0,578.0,239.0
+262.0,437.0,250.0,445.0,7.7,44.5,297.0,2.41,95.6,626.0,111.0
+215.0,365.0,124.0,219.0,3.43,82.0,519.0,10.6,30.5,158.0,47.0
+172.0,176.0,449.0,828.0,12.3,71.7,445.0,20.7,445.0,2393.0,1334.0
+241.0,385.0,820.0,1554.0,15.1,34.3,205.0,5.73,62.6,300.0,264.0
+217.0,385.0,246.0,457.0,8.98,20.7,150.0,4.87,79.9,445.0,750.0
+1208.0,1778.0,1241.0,2110.0,44.9,52.3,264.0,9.47,129.0,777.0,906.0
+227.0,346.0,189.0,349.0,3.52,42.6,211.0,12.9,176.0,1114.0,407.0
+68.5,118.0,13.8,62.6,57.8,93.9,519.0,18.9,106.0,533.0,1700.0
+189.0,325.0,188.0,352.0,2.19,115.0,673.0,8.43,53.3,334.0,138.0
+331.0,500.0,644.0,1134.0,9.73,76.4,562.0,15.4,890.0,4179.0,1219.0
+157.0,262.0,764.0,1486.0,12.0,77.0,573.0,6.98,764.0,3786.0,1540.0
+542.0,906.0,125.0,219.0,1.88,19.8,111.0,3.96,48.3,267.0,186.0
+750.0,1094.0,403.0,667.0,14.5,56.7,375.0,12.2,1124.0,5425.0,1981.0
+491.0,704.0,138.0,235.0,6.92,112.0,750.0,13.2,79.9,519.0,237.0
+1065.0,1625.0,396.0,704.0,13.9,127.0,799.0,5.57,71.0,457.0,66.1
+487.0,784.0,170.0,313.0,13.3,40.3,157.0,12.5,24.4,122.0,151.0
+209.0,294.0,119.0,215.0,1.72,101.0,599.0,32.2,66.1,343.0,352.0
+538.0,1009.0,750.0,1370.0,20.0,46.6,267.0,1.84,48.3,279.0,221.0
+262.0,346.0,138.0,219.0,7.43,38.2,198.0,7.3,35.5,165.0,284.0
+246.0,302.0,750.0,1322.0,41.8,63.2,514.0,9.22,24.6,82.8,599.0
+207.0,281.0,241.0,422.0,8.51,17.9,108.0,7.84,328.0,1762.0,491.0
+284.0,470.0,281.0,461.0,11.2,79.1,557.0,9.82,66.1,325.0,19.8
+257.0,294.0,1611.0,2595.0,57.3,37.9,200.0,85.8,81.3,478.0,828.0
+124.0,184.0,78.4,117.0,12.6,122.0,890.0,41.4,76.4,466.0,183.0
+843.0,1298.0,385.0,667.0,18.9,69.8,474.0,4.0,65.5,352.0,146.0
+610.0,956.0,146.0,257.0,13.7,1.5,17.8,69.8,82.0,621.0,101.0
+1124.0,1794.0,437.0,757.0,30.8,161.0,1018.0,15.4,51.4,337.0,209.0
+621.0,931.0,64.9,157.0,13.3,29.7,175.0,13.9,64.4,349.0,168.0
+313.0,500.0,68.5,101.0,11.1,11.8,83.5,132.0,33.4,150.0,151.0
+710.0,1094.0,542.0,982.0,16.3,35.2,113.0,19.5,124.0,843.0,176.0
+813.0,1358.0,146.0,322.0,250.0,124.0,737.0,52.8,65.5,382.0,130.0
+1433.0,1928.0,1486.0,2308.0,28.4,122.0,777.0,5.42,225.0,1310.0,359.0
+82.8,143.0,267.0,483.0,2.09,57.3,340.0,17.8,362.0,2072.0,1298.0
+311.0,400.0,204.0,385.0,12.0,101.0,698.0,6.1,62.6,426.0,89.0
+340.0,474.0,271.0,519.0,1.95,93.1,552.0,16.4,115.0,730.0,110.0
+441.0,723.0,284.0,466.0,13.0,72.3,414.0,12.0,217.0,1124.0,764.0
+437.0,610.0,34.9,57.8,47.8,79.1,649.0,15.8,487.0,2642.0,1346.0
+175.0,294.0,259.0,667.0,27.6,52.8,233.0,18.6,57.8,343.0,188.0
+108.0,139.0,1582.0,2227.0,47.0,48.7,340.0,13.2,54.7,349.0,117.0
+466.0,743.0,151.0,271.0,1.93,70.4,346.0,50.5,83.5,552.0,113.0
+297.0,491.0,328.0,632.0,29.4,62.6,375.0,11.9,63.2,441.0,179.0
+644.0,922.0,215.0,382.0,6.32,59.9,422.0,7.99,126.0,710.0,195.0
+368.0,588.0,313.0,523.0,9.73,59.9,331.0,9.06,57.8,349.0,207.0
+104.0,161.0,286.0,519.0,7.1,149.0,939.0,18.4,43.7,257.0,588.0
+1370.0,1860.0,1134.0,1860.0,55.7,56.2,362.0,25.5,112.0,615.0,68.5
+262.0,389.0,131.0,219.0,2.71,41.0,213.0,19.6,791.0,4179.0,2148.0
+221.0,328.0,255.0,478.0,7.7,39.2,213.0,8.28,85.1,496.0,198.0
+250.0,365.0,437.0,799.0,13.3,57.3,355.0,18.1,172.0,1027.0,784.0
+189.0,276.0,155.0,322.0,10.6,54.7,359.0,11.2,96.5,632.0,239.0
+279.0,422.0,97.3,308.0,26.4,99.1,514.0,6.92,99.1,547.0,445.0
+311.0,437.0,146.0,294.0,5.09,62.6,496.0,9.39,88.2,562.0,583.0
+48.7,67.9,661.0,1197.0,36.2,44.9,319.0,17.0,82.0,552.0,281.0
+269.0,346.0,449.0,743.0,21.5,31.3,198.0,75.7,57.8,362.0,154.0
+209.0,264.0,343.0,621.0,9.56,54.7,362.0,10.5,69.2,414.0,294.0
+221.0,359.0,368.0,661.0,7.57,78.4,487.0,3.65,85.8,466.0,179.0
+1298.0,1827.0,239.0,426.0,20.2,62.1,410.0,12.2,77.0,483.0,279.0
+764.0,1219.0,1263.0,2017.0,20.2,67.3,340.0,22.7,70.4,403.0,198.0
+89.8,125.0,302.0,523.0,5.94,50.5,392.0,34.3,25.5,130.0,67.3
+257.0,403.0,267.0,500.0,15.0,31.6,248.0,1.55,58.8,316.0,80.6
+259.0,389.0,94.7,165.0,12.6,54.7,396.0,10.5,104.0,573.0,362.0
+157.0,147.0,93.1,172.0,20.0,108.0,655.0,18.1,487.0,2642.0,632.0
+429.0,673.0,1459.0,2350.0,31.6,204.0,1263.0,125.0,34.3,195.0,723.0
+231.0,284.0,109.0,209.0,6.15,119.0,698.0,8.66,75.0,389.0,227.0
+250.0,346.0,319.0,583.0,7.7,67.3,316.0,9.91,176.0,939.0,255.0
+88.2,150.0,204.0,418.0,4.87,54.7,274.0,16.3,56.7,286.0,108.0
+396.0,673.0,297.0,610.0,11.2,4.33,20.9,3.65,1018.0,5186.0,1554.0
+441.0,770.0,231.0,375.0,5.38,25.5,154.0,10.3,59.9,349.0,92.2
+167.0,313.0,193.0,368.0,12.6,55.2,274.0,17.2,50.9,279.0,150.0
+98.2,193.0,115.0,225.0,4.57,93.1,791.0,36.5,69.8,453.0,139.0
+311.0,519.0,205.0,359.0,4.7,75.0,466.0,12.6,102.0,615.0,233.0
+1370.0,1911.0,22.1,54.7,57.8,104.0,538.0,19.3,1094.0,5328.0,1407.0
+84.3,119.0,316.0,567.0,23.3,36.8,211.0,8.35,221.0,1197.0,1124.0
+483.0,770.0,133.0,267.0,9.73,77.7,557.0,12.4,161.0,874.0,557.0
+65.5,95.6,289.0,466.0,12.6,1.79,44.9,63.2,150.0,956.0,644.0
+835.0,1322.0,91.4,181.0,4.91,59.4,429.0,5.28,126.0,820.0,207.0
+334.0,573.0,1827.0,2943.0,68.5,65.5,491.0,2.89,70.4,457.0,154.0
+813.0,1230.0,368.0,638.0,22.1,60.4,379.0,15.3,19.3,112.0,119.0
+233.0,375.0,355.0,632.0,4.26,75.7,491.0,14.7,89.0,478.0,141.0
+233.0,289.0,340.0,667.0,16.4,18.4,133.0,17.5,108.0,704.0,302.0
+125.0,205.0,168.0,286.0,10.6,139.0,820.0,14.5,62.6,372.0,131.0
+698.0,956.0,1334.0,2148.0,170.0,21.9,153.0,9.14,69.2,349.0,195.0
+359.0,588.0,229.0,433.0,4.74,5.38,25.3,70.4,466.0,2525.0,914.0
+441.0,723.0,150.0,274.0,11.5,33.4,217.0,6.67,64.4,337.0,229.0
+97.3,136.0,403.0,757.0,5.57,3.08,35.2,103.0,528.0,2864.0,638.0
+1715.0,2350.0,118.0,195.0,5.99,37.2,241.0,4.87,129.0,685.0,250.0
+196.0,297.0,274.0,547.0,6.92,62.1,279.0,15.4,77.7,514.0,113.0
+241.0,396.0,181.0,305.0,6.04,110.0,610.0,9.39,59.9,359.0,163.0
+389.0,578.0,188.0,355.0,14.3,50.0,271.0,8.66,956.0,4914.0,1670.0
+257.0,461.0,799.0,1370.0,56.2,7.43,17.0,1.19,66.1,461.0,255.0
+2129.0,3278.0,483.0,965.0,17.0,73.0,396.0,13.9,85.8,599.0,209.0
+173.0,235.0,115.0,195.0,5.83,62.1,365.0,7.7,45.3,279.0,75.7
+866.0,1165.0,710.0,1055.0,33.7,44.9,264.0,8.66,186.0,1037.0,1037.0
+225.0,334.0,189.0,337.0,7.37,158.0,1144.0,40.7,135.0,764.0,151.0
+271.0,414.0,217.0,414.0,10.4,50.0,289.0,9.06,470.0,2788.0,1446.0
+418.0,638.0,1611.0,2788.0,77.0,61.0,375.0,7.04,123.0,737.0,445.0
+334.0,496.0,151.0,253.0,14.7,115.0,750.0,17.2,138.0,890.0,255.0
+365.0,573.0,346.0,615.0,8.13,38.9,227.0,4.41,679.0,3460.0,835.0
+195.0,337.0,179.0,319.0,10.6,77.0,478.0,17.5,46.6,90.6,500.0
+150.0,267.0,132.0,255.0,6.67,8.06,67.3,1.06,50.9,281.0,202.0
+389.0,626.0,1298.0,1911.0,33.4,67.3,519.0,30.0,50.9,294.0,189.0
+375.0,547.0,281.0,414.0,5.19,50.5,294.0,7.84,225.0,1263.0,604.0
+221.0,328.0,239.0,453.0,8.06,9.39,24.1,1.72,5.47,38.2,322.0
+1186.0,1860.0,158.0,284.0,3.96,92.2,562.0,22.7,42.9,259.0,237.0
+1382.0,1877.0,1075.0,1981.0,83.5,45.7,311.0,6.73,50.0,267.0,244.0
+39.2,8.9,4.26,9.22,1.88,25.9,46.6,223.0,3.02,31.6,65.5
+42.6,20.2,12.1,1.45,40.0,30.2,51.9,264.0,5.94,14.1,16.1
+5.88,17.9,3.43,2.19,18.1,105.0,300.0,1928.0,6.98,20.5,12.9
+34.3,18.8,3.65,1.7,16.5,352.0,519.0,1263.0,18.3,59.4,35.9
+24.6,16.0,6.92,9.39,8.06,15.7,53.8,346.0,9.31,18.1,12.5
+36.2,15.7,1.0,65.5,31.3,30.5,66.1,874.0,11.4,26.2,8.66
+2.81,10.3,4.37,1.0,6.26,30.5,105.0,483.0,17.2,32.8,6.44
+45.3,13.9,6.79,12.2,13.6,26.9,39.6,578.0,15.7,41.0,37.2
+15.3,25.7,3.37,3.52,11.9,9.65,17.5,382.0,9.22,25.9,14.2
+40.3,17.9,2.81,2.17,1.0,49.1,77.0,1568.0,17.5,32.2,5.23
+64.9,54.2,1.0,21.5,7.7,1.0,1.55,50.9,12.7,37.9,2.67
+30.0,22.1,4.87,1.12,9.22,3.92,46.6,173.0,17.2,25.0,10.6
+30.5,22.5,13.2,1.01,21.9,22.3,36.8,223.0,12.0,26.2,25.0
+25.0,34.0,2.29,1.01,15.1,7.3,16.1,276.0,13.6,38.5,60.4
+28.4,19.8,10.2,4.57,30.8,6.38,18.1,973.0,21.9,47.8,18.9
+65.5,56.7,1.0,2.41,2.05,126.0,204.0,2207.0,12.1,20.4,23.9
+35.2,18.6,3.22,2.81,26.4,25.5,172.0,200.0,27.1,40.3,15.1
+34.3,20.5,8.51,1.0,30.2,40.3,130.0,890.0,22.1,76.4,51.4
+61.0,38.9,3.46,5.19,26.2,12.0,24.6,487.0,14.7,21.3,13.8
+48.7,20.4,1.19,2.5,11.8,12.6,24.4,316.0,24.4,37.5,21.1
+35.5,13.8,8.28,7.99,17.2,45.3,77.0,1526.0,42.2,110.0,34.9
+31.9,44.1,5.42,1.31,6.32,13.8,13.3,349.0,12.7,23.3,9.39
+42.6,25.5,7.3,1.0,21.5,33.7,49.6,396.0,59.4,85.1,19.6
+78.4,21.9,9.31,4.66,44.9,10.7,26.4,866.0,17.2,21.9,7.84
+44.1,24.1,5.38,132.0,16.5,18.1,37.5,1219.0,3.05,17.6,63.8
+47.4,19.3,1.0,1.68,10.2,10.2,38.2,661.0,21.1,45.7,21.7
+105.0,41.4,2.69,3.82,9.56,28.6,59.9,362.0,17.0,25.5,12.0
+56.2,38.9,12.0,9.39,11.7,66.1,125.0,638.0,13.2,50.0,6.67
+72.3,24.4,5.28,179.0,35.2,22.1,42.6,196.0,26.9,38.9,20.7
+45.7,13.1,1.91,6.79,6.32,29.7,49.1,382.0,16.7,39.2,22.9
+56.7,25.5,1.84,1.0,25.7,6.98,31.9,851.0,8.51,20.5,160.0
+79.1,48.7,3.75,4.14,24.1,27.1,44.1,221.0,31.9,38.5,21.1
+15.4,23.9,1.86,6.26,32.8,41.4,68.5,331.0,5.99,5.05,44.5
+21.7,10.6,7.57,2.46,16.1,29.4,64.4,1155.0,30.2,77.0,28.1
+36.8,22.5,9.65,1.43,3.13,15.1,58.3,75.7,13.2,26.2,12.4
+52.8,17.5,5.94,179.0,14.6,11.5,22.1,457.0,13.9,39.2,18.4
+30.8,11.1,2.86,1.06,18.6,24.6,44.1,500.0,19.1,37.9,21.3
+21.1,20.7,22.9,4.66,13.1,10.3,22.1,334.0,20.9,32.2,15.7
+26.4,24.1,9.39,3.31,24.8,14.5,41.8,906.0,13.1,30.8,10.3
+36.8,25.9,10.2,1.96,35.9,46.6,111.0,947.0,23.1,50.0,35.5
+20.2,15.8,9.06,4.45,9.91,19.5,110.0,1358.0,16.5,35.9,17.8
+48.7,42.6,3.52,6.73,7.37,11.8,23.7,175.0,49.6,85.1,11.3
+43.7,8.82,8.82,2.74,6.85,20.5,27.6,281.0,13.0,24.1,18.1
+37.2,24.4,2.69,3.0,19.5,21.7,41.0,349.0,8.35,24.4,9.82
+69.2,26.9,15.4,3.22,20.2,25.0,83.5,644.0,15.8,26.4,8.9
+40.0,25.9,5.42,4.18,8.13,13.0,29.4,250.0,2.23,21.3,37.9
+30.5,15.4,2.64,147.0,47.8,61.0,131.0,1778.0,21.9,44.1,18.9
+40.7,14.5,2.37,1.0,26.4,23.3,54.7,813.0,15.5,21.9,16.5
+56.7,31.6,9.31,2.89,25.7,49.1,104.0,698.0,3.4,4.45,1.0
+86.6,125.0,8.28,10.6,47.0,73.7,170.0,3134.0,21.1,63.2,25.7
+27.6,17.8,5.94,6.21,32.8,57.8,110.0,1084.0,6.15,27.4,93.1
+63.8,23.7,20.9,17.5,12.1,34.0,52.3,355.0,26.7,51.4,33.4
+31.9,20.5,1.79,165.0,72.3,17.2,33.1,723.0,15.5,37.2,79.1
+48.3,18.3,2.31,2.09,18.3,16.0,24.8,392.0,24.8,57.3,23.5
+43.3,15.1,1.0,1.32,6.1,44.9,78.4,1685.0,10.0,34.6,14.2
+23.9,18.1,6.1,7.23,17.2,10.0,41.8,5.67,19.6,28.1,9.14
+26.7,19.5,1.0,1.12,11.2,41.4,71.7,791.0,19.8,36.5,26.2
+59.4,17.6,3.65,4.78,26.9,49.6,113.0,882.0,12.4,30.5,8.58
+8.13,24.4,12.4,1.03,21.7,28.6,193.0,62.1,11.2,40.0,108.0
+56.7,26.9,1.01,2.69,15.7,12.2,28.6,259.0,15.3,35.2,4.7
+73.0,30.2,6.49,3.46,1.0,13.3,78.4,757.0,6.73,38.5,27.4
+40.7,16.7,1.45,5.19,4.07,17.3,63.8,2054.0,3.13,18.6,65.5
+46.6,15.0,6.04,4.03,3.25,2.5,2.39,36.2,18.1,43.3,8.82
+47.8,24.4,1.32,1.0,3.65,12.9,24.1,474.0,15.4,24.1,10.5
+20.0,21.5,3.37,1.0,21.7,16.1,38.2,615.0,20.0,39.2,50.9
+24.4,17.3,1.06,40.7,13.8,14.5,26.2,286.0,14.9,29.7,12.2
+19.8,16.4,3.25,6.98,16.0,46.1,95.6,487.0,2.71,92.2,5.52
+64.9,32.8,4.91,1.09,1.58,14.2,23.5,429.0,12.1,43.3,7.3
+53.8,38.5,1.45,255.0,52.3,28.9,61.5,422.0,10.9,26.9,5.83
+75.7,31.1,5.23,1.01,18.1,10.8,32.2,483.0,2.74,12.0,54.7
+87.4,44.1,1.0,1.0,13.8,13.1,32.8,235.0,38.2,75.7,34.3
+41.4,21.9,20.7,2.55,18.8,10.0,26.7,414.0,3.46,19.1,30.0
+44.5,25.9,13.1,6.67,17.6,86.6,165.0,1928.0,14.5,32.5,19.6
+46.1,18.8,2.57,1.98,14.5,44.5,109.0,567.0,24.4,34.0,14.2
+54.7,26.9,4.33,2.71,11.1,20.5,85.1,1322.0,17.0,35.9,15.1
+119.0,39.2,1.0,6.26,21.7,55.7,149.0,1346.0,12.5,36.8,5.73
+11.7,30.8,2.84,6.32,10.6,66.1,86.6,922.0,1.51,21.7,80.6
+75.7,51.9,7.23,167.0,19.1,30.0,93.1,1860.0,1.78,30.5,39.6
+57.3,22.5,2.11,2.55,7.64,26.9,48.3,313.0,21.3,52.8,20.4
+16.4,21.5,5.52,3.85,22.7,12.2,69.8,1582.0,2.48,17.6,96.5
+57.3,29.4,5.09,4.22,17.6,8.74,34.3,649.0,9.82,26.9,16.5
+56.7,34.0,1.0,7.64,10.6,29.2,88.2,1611.0,5.57,34.0,106.0
+89.0,58.8,4.96,1.0,11.2,14.3,28.1,319.0,2.39,19.1,70.4
+47.4,25.7,6.49,1.95,1.0,60.4,176.0,1252.0,37.5,91.4,39.6
+51.9,13.1,9.14,1.79,4.91,30.2,74.3,698.0,22.5,76.4,39.2
+27.4,10.9,2.86,4.1,5.88,68.5,129.0,1459.0,20.2,35.9,8.9
+83.5,33.7,1.42,1.01,12.5,74.3,119.0,466.0,11.9,31.9,6.1
+13.8,12.4,13.9,7.3,12.9,5.42,16.1,588.0,15.3,42.2,10.7
+59.9,20.5,6.92,1.0,18.1,15.0,28.6,313.0,23.5,66.1,18.1
+56.2,20.9,8.43,2.86,1.93,25.0,54.7,1155.0,9.56,46.6,73.7
+108.0,27.9,10.9,7.57,7.7,42.2,120.0,922.0,25.3,50.9,10.9
+29.7,23.9,12.2,77.0,31.6,82.8,164.0,1827.0,20.5,30.8,17.3
+62.1,17.3,5.0,1.01,2.07,17.8,36.5,271.0,13.0,27.9,7.1
+47.0,20.4,6.98,3.85,12.4,8.98,20.2,474.0,44.5,129.0,44.1
+88.2,84.3,4.87,1.01,6.79,28.9,40.0,956.0,31.1,66.1,26.9
+38.2,20.4,15.1,4.91,19.8,45.7,138.0,2227.0,16.7,43.7,73.0
+38.2,22.5,2.62,1.0,16.5,32.8,82.8,1165.0,3.49,20.9,44.5
+61.0,31.1,1.89,1.0,28.9,50.9,82.0,538.0,7.5,18.8,10.4
+20.9,15.8,1.04,1.3,17.9,16.4,24.4,262.0,25.5,53.8,28.6
+52.8,26.9,17.0,1.15,35.9,8.74,31.1,717.0,15.7,28.1,21.9
+64.4,19.8,6.61,1.42,10.7,28.4,40.0,334.0,3.02,21.5,62.1
+48.7,18.3,6.79,1.01,13.5,11.5,22.9,359.0,21.3,42.6,29.7
+58.3,15.5,5.94,1.25,2.97,25.0,52.3,365.0,2.09,24.8,74.3
+62.6,16.3,5.28,2.64,1.0,23.7,44.9,173.0,20.7,31.9,21.1
+62.1,24.8,2.86,1.01,12.1,74.3,145.0,730.0,16.1,35.9,5.83
+29.4,38.9,3.92,1.19,4.22,5.78,30.0,914.0,37.5,66.7,19.5
+139.0,50.0,1.0,2.59,11.4,18.4,44.1,292.0,17.5,47.4,118.0
+173.0,164.0,7.57,1.0,3.52,14.3,26.7,491.0,1.18,704.0,77.0
+21.7,20.0,7.04,1.0,1.88,27.6,52.3,346.0,14.7,35.5,17.3
+71.7,30.5,1.0,2.74,11.9,53.3,151.0,1176.0,25.5,45.7,17.8
+70.4,33.4,4.57,2.74,7.23,11.8,14.1,359.0,46.6,84.3,36.2
+19.3,32.5,10.4,3.28,14.9,14.6,19.1,491.0,17.2,23.5,10.8
+58.3,33.7,9.47,4.41,14.3,7.04,28.4,478.0,17.9,35.9,12.2
+77.0,24.1,8.9,1.01,18.3,16.7,63.2,1252.0,15.3,33.4,6.92
+75.0,24.1,1.0,2.09,15.8,68.5,132.0,2288.0,5.94,33.1,138.0
+34.6,19.8,1.0,6.92,17.8,16.7,31.3,294.0,25.5,83.5,30.0
+82.0,33.7,1.32,3.16,12.9,41.4,93.1,757.0,27.4,79.1,38.9
+55.2,27.4,3.46,2.59,18.3,19.6,32.5,213.0,25.7,67.3,66.7
+93.1,62.6,1.06,6.98,2.02,6.32,37.2,500.0,1.93,19.1,57.8
+151.0,153.0,9.73,1.01,21.9,67.9,132.0,2571.0,90.6,114.0,25.5
+93.1,66.1,2.44,6.21,2.5,66.1,129.0,1877.0,4.37,20.9,57.8
+54.2,25.3,8.58,3.02,27.6,18.6,34.9,274.0,3.92,18.9,85.8
+113.0,57.8,11.7,3.62,20.0,44.5,76.4,509.0,4.53,23.9,160.0
+42.9,36.8,5.57,3.59,8.82,26.4,102.0,1446.0,17.6,30.2,15.8
+26.4,14.1,10.7,5.99,5.62,8.06,17.5,392.0,16.3,45.7,15.5
+138.0,176.0,14.2,1.0,7.3,38.2,58.8,246.0,63.2,87.4,16.5
+48.3,26.4,2.67,6.49,18.3,90.6,248.0,914.0,5.88,51.9,119.0
+54.2,19.1,5.42,2.11,29.7,104.0,346.0,2813.0,14.1,17.3,2.41
+77.0,51.9,1.33,3.4,17.3,53.8,91.4,813.0,18.6,27.6,10.8
+10.6,24.6,2.21,8.2,10.0,15.0,50.5,562.0,17.2,48.7,10.2
+78.4,39.6,6.1,1.01,12.9,16.7,48.7,123.0,18.3,37.2,6.26
+60.4,29.7,10.5,1.0,1.0,27.6,50.9,626.0,37.5,79.9,44.5
+24.8,33.4,1.33,1.55,2.25,41.8,122.0,698.0,16.7,44.1,95.6
+54.2,10.5,2.11,1.01,22.9,6.04,19.6,422.0,10.4,23.9,3.75
+103.0,30.0,3.28,4.45,8.2,50.0,80.6,1382.0,1.73,19.1,79.9
+16.8,23.9,5.99,4.91,14.3,6.98,52.3,547.0,1.25,10.0,46.1
+84.3,40.3,6.79,1.01,17.6,19.6,37.5,246.0,13.7,35.5,78.4
+56.7,38.2,2.11,2.53,12.9,16.7,38.5,523.0,30.0,69.2,42.9
+49.1,29.2,2.53,1.42,5.73,18.6,48.7,1165.0,27.9,40.7,21.9
+2.15,12.3,3.75,1.81,16.7,25.3,82.0,1000.0,19.1,39.2,10.9
+139.0,48.7,6.04,1.0,31.3,11.5,34.3,87.4,12.7,29.7,14.2
+48.3,23.9,6.26,6.04,10.6,18.3,44.5,710.0,2.69,19.1,47.4
+10.1,16.3,5.38,1.23,21.1,13.5,34.6,289.0,26.2,51.4,22.7
+82.0,62.1,3.96,1.08,13.6,2.59,30.2,27.9,2.39,17.8,84.3
+12.0,17.2,4.83,3.85,2.29,5.83,23.5,931.0,55.7,99.1,26.4
+28.1,17.6,1.63,1.01,17.2,19.1,28.1,221.0,42.2,114.0,73.7
+87.4,20.5,4.18,1.03,1.36,59.4,161.0,1084.0,17.8,35.5,14.1
+91.4,32.5,4.57,1.0,9.73,17.2,36.2,305.0,24.1,62.6,31.3
+10.6,1.58,6.85,4.26,12.0,25.9,61.0,898.0,32.2,75.7,40.3
+102.0,33.7,6.15,1.72,16.8,113.0,331.0,3078.0,12.6,31.3,13.6
+33.4,17.9,5.83,1.0,13.1,6.67,40.0,313.0,5.57,28.6,67.9
+55.7,40.3,15.0,1.02,21.7,69.2,130.0,1395.0,23.7,34.9,8.43
+90.6,37.2,2.69,1.24,4.91,8.82,22.7,519.0,11.9,18.3,14.1
+74.3,26.4,6.49,1.35,14.7,11.0,31.6,965.0,18.8,33.4,15.5
+46.1,48.3,3.43,1.68,12.0,32.8,95.6,552.0,2.76,33.4,99.1
+153.0,119.0,2.89,1.0,22.5,13.7,20.7,453.0,10.6,25.3,14.2
+19.8,15.4,3.96,7.1,4.37,19.5,36.5,474.0,18.4,38.2,7.91
+40.3,23.7,8.06,1.0,16.5,7.43,31.3,1094.0,13.6,30.2,11.0
+31.6,16.4,1.0,2.25,1.01,21.3,47.4,1075.0,22.9,61.0,21.7
+15.0,21.1,5.23,3.55,12.6,46.1,109.0,2548.0,2.25,5.42,5.83
+77.7,21.1,14.3,2.84,28.4,27.4,44.1,205.0,12.1,23.3,12.2
+58.3,23.5,5.28,9.73,29.2,20.4,44.9,649.0,10.1,22.7,14.5
+50.5,24.4,4.18,1.19,12.3,17.3,45.3,1407.0,13.7,35.9,12.9
+123.0,68.5,1.73,1.33,5.67,18.1,36.2,382.0,9.91,18.9,9.91
+55.2,16.7,1.0,1.0,8.28,30.2,111.0,1407.0,4.74,12.6,76.4
+82.8,27.6,1.0,2.17,15.0,5.52,22.3,487.0,16.1,39.6,6.79
+46.6,9.31,1.0,5.73,19.1,23.9,40.0,308.0,12.2,28.9,4.29
+66.1,71.7,5.09,2.44,21.1,43.3,108.0,1911.0,38.2,84.3,27.4
+51.4,24.8,18.8,9.82,25.7,24.1,47.8,1114.0,3.28,18.9,56.7
+61.0,22.7,4.18,5.0,1.61,12.7,22.9,221.0,16.1,30.5,13.8
+95.6,43.3,1.0,1.93,16.3,9.06,37.9,578.0,16.8,34.6,21.1
+42.9,26.9,1.01,1.23,11.5,26.2,34.0,340.0,13.9,26.2,12.1
+86.6,53.8,1.0,4.37,20.2,45.3,130.0,1000.0,32.5,59.4,17.6
+73.7,34.6,3.11,158.0,32.5,25.3,44.9,264.0,2.53,15.8,64.9
+106.0,46.6,2.57,2.97,22.5,10.1,37.5,610.0,1.0,55.2,4.0
+18.8,25.7,5.47,3.92,31.9,10.2,15.7,352.0,11.9,40.7,33.7
+27.6,34.6,1.0,1.01,12.2,5.88,16.1,385.0,14.9,23.7,15.8
+63.2,71.7,8.43,1.96,34.6,73.0,179.0,1625.0,15.5,29.4,10.9
+47.8,34.0,7.57,2.84,24.4,21.5,42.9,257.0,11.5,33.1,9.47
+74.3,24.4,2.21,1.98,16.0,67.9,121.0,227.0,7.5,18.9,83.5
+93.9,40.3,5.14,2.81,33.4,18.8,39.6,241.0,22.5,35.2,15.8
+62.1,20.2,7.77,1.0,11.8,31.9,47.4,235.0,27.1,73.7,18.8
+89.8,42.9,8.06,1.0,9.39,20.0,28.4,400.0,28.1,63.8,24.4
+55.7,62.6,2.19,5.52,34.6,11.0,78.4,2763.0,48.3,102.0,41.8
+90.6,31.6,18.4,5.14,29.7,27.6,48.7,193.0,38.9,85.8,57.8
+13.1,31.1,11.0,1.0,21.9,11.5,27.1,400.0,2.46,23.9,68.5
+66.7,23.7,3.28,1.0,20.4,9.22,53.3,828.0,13.8,52.8,130.0
+15.8,25.7,1.27,3.08,16.7,37.2,61.0,414.0,19.6,31.3,12.3
+17.2,37.2,14.1,3.31,28.9,13.5,31.6,491.0,26.4,77.7,29.7
+90.6,45.3,12.0,1.01,30.5,28.1,48.3,229.0,1.45,48.7,3.89
+14.1,11.5,3.19,1.0,20.9,12.4,126.0,189.0,23.3,34.3,17.6
+85.8,21.3,1.57,1.41,5.05,63.2,181.0,1731.0,23.7,50.5,150.0
+61.0,17.6,1.6,1.05,4.78,34.6,66.1,410.0,44.1,121.0,90.6
+132.0,172.0,2.15,2.25,8.66,16.4,33.1,426.0,38.2,64.9,21.9
+62.6,37.9,1.18,1.95,14.5,17.3,32.8,372.0,1.02,26.7,52.8
+44.1,40.3,1.54,1.0,20.2,70.4,126.0,615.0,31.1,74.3,40.0
+107.0,129.0,15.8,1.03,10.9,49.6,99.1,1298.0,28.4,50.9,31.1
+54.2,14.9,9.39,1.0,13.5,35.2,101.0,813.0,13.2,40.3,21.5
+33.1,26.4,2.17,1.0,14.6,21.7,41.0,947.0,7.04,27.1,9.39
+23.5,18.6,4.91,2.0,6.55,23.5,66.1,2187.0,19.5,31.1,6.38
+57.3,28.9,1.01,5.52,5.88,19.5,34.3,215.0,3.0,16.1,68.5
+61.0,19.6,2.74,1.06,12.3,12.4,26.9,300.0,4.57,10.4,69.8
+38.9,17.9,2.0,3.19,25.7,4.53,28.1,685.0,27.6,56.2,21.5
+97.3,47.0,1.0,2.15,26.7,38.2,137.0,2017.0,17.8,37.2,22.7
+118.0,104.0,16.8,2.13,16.5,27.6,38.9,403.0,30.0,51.9,17.5
+53.3,28.9,4.45,3.43,18.3,9.06,21.7,470.0,13.2,27.6,8.2
+445.0,89.8,1.01,3.62,14.1,12.1,34.6,931.0,22.3,45.3,11.0
+38.2,15.4,6.1,3.68,29.7,10.5,31.3,604.0,32.8,85.1,27.1
+56.7,25.9,1.83,3.96,21.7,13.5,26.2,698.0,22.3,53.8,4.26
+75.0,54.2,11.2,2.09,12.0,17.3,34.6,519.0,5.78,37.5,154.0
+19.6,27.4,5.88,1.0,29.4,42.6,89.8,1275.0,40.0,93.1,51.9
+59.4,30.5,4.7,1.53,12.9,29.2,75.7,267.0,15.0,24.4,4.57
+72.3,15.1,7.43,5.83,31.1,20.2,33.7,302.0,34.9,73.7,35.2
+49.6,25.0,3.85,1.1,17.2,4.26,6.98,181.0,3.89,20.9,90.6
+85.8,37.5,1.0,1.01,9.14,45.7,70.4,225.0,28.9,73.0,50.0
+46.6,17.3,6.98,1.18,2.81,117.0,223.0,528.0,25.7,36.8,29.7
+67.9,35.5,5.47,1.89,14.1,18.1,131.0,129.0,19.1,47.4,18.9
+28.9,22.9,1.31,1.0,6.73,11.8,30.8,496.0,14.3,37.2,9.56
+96.5,60.4,1.76,1.14,9.14,31.3,158.0,1084.0,36.2,67.3,33.1
+77.7,26.4,2.46,5.0,10.1,46.6,65.5,292.0,15.4,42.2,22.1
+40.7,19.1,1.55,3.96,4.03,27.9,46.1,281.0,23.7,30.8,27.4
+73.0,43.7,3.59,1.0,18.8,131.0,231.0,1186.0,9.14,18.1,11.7
+37.9,21.3,5.28,1.01,18.9,37.2,56.2,292.0,3.46,9.82,59.9
+88.2,45.3,11.1,1.0,17.8,37.5,75.0,1186.0,37.5,64.4,14.9
+15.4,23.7,4.91,1.0,2.25,34.3,62.6,1778.0,19.3,51.4,21.9
+72.3,50.0,5.28,1.01,25.0,34.3,90.6,1322.0,33.4,65.5,27.6
+85.1,23.5,8.74,1.01,18.6,8.28,23.3,717.0,4.18,9.73,4.14
+18.3,14.2,3.85,7.99,18.4,50.9,105.0,1009.0,37.9,56.2,23.1
+62.6,25.5,7.1,1.06,3.34,21.7,34.0,300.0,7.43,38.9,54.7
+8.2,17.9,1.03,1.55,21.7,41.8,106.0,1747.0,29.2,51.9,16.7
+88.2,29.7,13.8,3.25,13.2,31.6,58.8,667.0,22.3,45.7,13.8
+10.8,23.5,7.37,10.1,12.2,19.1,43.3,1018.0,15.1,23.9,18.3
+54.7,24.6,6.92,1.15,17.8,47.0,95.6,1877.0,1.0,1.0,7.7
+57.3,23.7,7.1,9.65,9.22,44.9,126.0,1186.0,3.49,18.4,77.7
+28.1,44.1,1.08,3.62,9.65,43.7,87.4,552.0,12.7,25.5,6.73
+21.1,15.8,7.43,2.48,21.5,13.8,36.2,784.0,25.3,45.3,82.0
+78.4,57.8,5.57,1.0,2.89,5.38,17.8,704.0,18.8,29.2,8.9
+6.98,28.4,9.73,1.0,6.85,34.6,66.1,355.0,23.3,42.6,22.9
+65.5,22.5,1.0,1.01,11.5,61.0,95.6,956.0,14.9,30.0,21.1
+58.3,24.6,4.0,4.96,24.1,5.94,34.3,874.0,4.14,16.8,109.0
+16.1,15.3,1.11,1.0,14.3,10.5,48.3,1762.0,4.22,20.5,50.9
+34.0,29.4,3.22,2.76,9.14,19.1,30.0,441.0,20.0,45.7,13.6
+14.3,16.8,1.81,5.73,27.6,12.9,33.7,523.0,47.8,106.0,58.8
+68.5,28.6,1.86,1.91,1.0,20.5,41.4,305.0,26.4,58.8,32.5
+63.2,29.2,2.46,1.91,1.42,25.7,54.7,337.0,33.1,79.1,31.6
+100.0,57.3,6.21,1.24,26.7,23.5,34.6,308.0,12.7,22.5,2.07
+103.0,41.4,6.04,10.5,12.9,5.73,22.1,500.0,21.1,44.1,24.4
+62.1,22.5,10.7,1.68,17.5,91.4,165.0,470.0,11.9,25.9,15.3
+81.3,47.4,1.08,1.0,9.06,7.64,35.2,743.0,19.3,39.6,21.3
+69.8,19.6,1.0,7.7,16.0,74.3,161.0,737.0,12.9,32.5,13.7
+42.9,20.9,4.7,1.25,26.2,24.1,65.5,806.0,3.16,12.6,85.8
+72.3,75.0,3.0,1.98,6.55,54.2,118.0,1027.0,27.9,67.3,27.1
+47.8,18.9,6.85,5.23,2.94,35.5,74.3,906.0,24.4,71.7,19.6
+73.0,40.0,5.73,1.01,31.6,34.0,84.3,1685.0,3.55,30.0,93.1
+46.1,35.9,11.3,1.27,11.9,37.2,97.3,764.0,17.2,42.2,11.7
+9.47,4.57,1.47,5.05,4.18,311.0,644.0,1946.0,13.1,30.2,13.3
+75.0,28.4,6.67,7.17,18.4,13.2,139.0,132.0,17.5,39.6,8.74
+25.9,42.2,2.86,1.01,21.3,11.0,25.9,429.0,25.0,43.3,5.47
+40.0,30.5,10.6,35.2,34.3,33.7,95.6,2666.0,24.8,42.6,13.1
+51.9,17.8,1.0,1.01,10.3,36.2,72.3,2091.0,8.2,17.3,32.8
+95.6,61.5,11.2,1.01,38.5,18.4,53.8,483.0,3.34,8.28,40.7
+49.6,18.1,10.9,2.33,25.0,20.2,35.2,355.0,13.8,25.9,7.91
+359.0,365.0,13.3,1.0,32.2,11.2,20.4,491.0,13.5,39.2,13.6
+71.0,47.4,2.97,3.11,16.5,27.6,35.2,241.0,1.0,68.5,4.29
+62.1,37.9,1.5,1.0,10.4,67.3,135.0,730.0,11.1,21.7,8.2
+4.18,21.9,4.49,2.23,15.4,46.6,97.3,2035.0,21.7,45.3,19.1
+14.2,7.1,10.6,4.14,9.91,34.0,55.2,308.0,21.5,64.4,21.7
+73.0,22.1,9.31,1.01,12.4,28.4,38.2,349.0,13.7,31.3,17.2
+23.9,22.5,2.27,2.57,13.8,46.6,82.8,588.0,1.7,53.8,2.0
+15.7,16.3,5.38,93.9,22.7,32.5,66.1,655.0,42.2,107.0,34.6
+36.2,39.6,1.86,5.42,1.0,40.3,101.0,1219.0,35.2,77.0,32.2
+69.8,21.9,9.47,1.01,17.3,24.6,61.0,297.0,9.73,28.9,13.1
+48.3,19.1,5.83,1.01,16.4,41.4,130.0,799.0,30.5,55.2,25.0
+138.0,125.0,6.85,2.55,9.31,9.06,5.38,133.0,18.9,38.5,3.4
+62.1,39.2,4.66,3.37,8.13,28.1,69.2,1275.0,28.4,50.9,14.2
+63.8,24.1,1.01,3.13,26.7,15.5,73.7,2110.0,1.0,2.94,3.16
+95.6,52.3,5.99,1.0,30.8,6.38,20.2,26.4,23.7,31.6,29.2
+7.84,26.2,10.0,8.43,16.7,7.37,14.6,248.0,13.2,23.1,30.5
+50.0,17.3,1.0,3.34,20.7,14.9,34.0,316.0,18.1,52.8,33.4
+12.0,12.4,4.66,1.0,3.08,26.7,65.5,982.0,30.5,38.2,9.31
+71.7,30.5,11.8,1.01,16.0,34.0,58.8,567.0,24.1,50.0,23.3
+17.8,24.6,1.23,1.01,13.0,8.82,23.5,843.0,11.3,44.9,86.6
+34.3,30.0,1.0,1.0,19.8,58.8,114.0,882.0,23.3,56.7,44.1
+27.1,24.8,14.6,2.39,23.9,12.3,71.0,1420.0,2.33,22.9,77.0
+55.7,34.9,1.75,3.92,5.62,44.5,79.9,1055.0,26.9,45.7,17.5
+70.4,32.8,1.04,1.88,8.74,20.4,43.3,730.0,12.4,21.3,1.0
+54.7,28.1,1.15,4.61,26.4,28.1,46.1,375.0,51.9,67.9,1.67
+30.2,24.6,6.67,1.79,1.0,20.5,43.3,491.0,2.29,6.85,4.18
+7.43,29.4,8.51,1.42,4.78,37.9,97.3,1700.0,6.73,12.6,5.52
+42.2,40.0,3.96,1.0,13.2,29.4,47.0,474.0,25.5,47.4,21.9
+29.4,22.1,3.85,3.68,7.04,29.4,73.7,1176.0,10.1,25.7,14.2
+130.0,117.0,7.77,1.06,27.1,34.6,58.8,418.0,3.46,20.0,95.6
+97.3,51.4,7.91,2.05,13.6,14.1,29.4,491.0,91.4,139.0,28.1
+77.0,91.4,1.54,1.0,17.6,31.1,36.5,316.0,14.9,36.8,8.58
+26.2,15.5,7.7,3.79,17.5,14.7,36.2,372.0,7.17,8.66,1.0
+44.1,15.3,3.43,2.41,5.88,17.5,43.3,349.0,35.5,83.5,37.9
+61.0,32.2,3.22,1.0,11.3,22.7,45.7,281.0,9.31,18.4,5.52
+82.8,50.5,8.2,1.96,18.1,32.8,55.2,422.0,18.1,33.1,13.0
+120.0,35.9,4.91,2.97,16.7,18.8,34.0,372.0,16.0,34.0,6.04
+51.9,46.1,13.2,1.01,18.4,6.73,13.0,474.0,24.4,50.5,77.7
+18.4,18.1,6.49,1.0,9.73,8.2,25.3,547.0,8.35,25.5,2.44
+154.0,53.8,6.44,1.0,6.21,33.7,57.8,1165.0,13.9,13.8,6.92
+47.0,27.1,5.83,1.01,14.1,11.3,39.6,723.0,29.4,48.3,27.6
+92.2,31.6,7.77,1.58,4.83,17.5,24.1,655.0,19.8,40.7,5.83
+64.9,24.6,4.33,1.0,17.5,6.1,19.1,757.0,26.4,50.5,10.0
+37.9,18.4,4.33,1.25,12.0,34.0,100.0,914.0,6.44,30.8,108.0
+37.5,29.7,1.81,1.01,5.62,27.9,50.0,289.0,14.7,28.1,1.0
+63.2,34.6,5.52,2.41,24.8,17.8,32.8,717.0,15.4,25.9,17.6
+8.98,22.1,7.99,3.62,7.43,78.4,145.0,673.0,6.85,19.8,1.0
+42.9,15.0,1.15,1.01,22.5,5.19,19.8,588.0,32.2,59.9,14.3
+69.8,20.4,5.23,1.01,2.84,56.7,127.0,698.0,16.7,32.8,17.6
+12.9,20.4,3.19,1.01,8.2,8.66,31.9,655.0,18.8,31.3,11.7
+106.0,24.1,4.53,1.01,17.9,61.5,111.0,1670.0,32.8,79.9,26.7
+59.9,23.7,1.6,3.02,16.5,17.6,42.2,269.0,18.9,41.8,18.1
+172.0,33.1,5.88,173.0,47.4,24.1,32.8,279.0,31.9,56.2,28.9
+39.6,18.1,4.83,1.0,21.7,13.7,35.5,198.0,32.5,84.3,60.4
+20.0,23.1,2.55,3.22,22.5,17.0,62.6,1252.0,3.52,36.8,67.9
+59.4,26.9,14.1,2.13,14.2,41.0,89.0,632.0,18.1,44.1,26.4
+82.0,26.2,1.01,1.3,12.1,27.4,69.8,1762.0,34.0,50.5,8.51
+65.5,35.2,7.37,1.72,9.39,8.98,22.7,474.0,9.73,25.5,14.7
+100.0,44.5,1.01,6.32,10.6,24.8,51.9,487.0,2.55,9.82,48.3
+122.0,46.1,1.32,1.33,16.4,46.1,91.4,2350.0,22.9,46.6,15.0
+55.7,22.9,3.22,6.67,12.7,14.9,53.3,1055.0,17.0,35.2,9.56
+100.0,57.3,4.26,1.01,13.3,11.7,29.2,322.0,21.1,31.6,13.7
+20.7,13.6,8.43,5.33,4.22,18.9,56.7,2458.0,9.39,19.8,1.98
+103.0,35.2,1.0,1.01,11.8,13.7,25.5,382.0,14.9,25.5,8.28
+67.9,20.4,1.0,2.27,10.9,18.4,30.8,205.0,13.2,40.3,17.3
+106.0,26.7,10.4,1.08,1.0,21.9,37.2,264.0,17.9,35.9,37.9
+98.2,30.0,5.47,2.27,11.7,3.46,19.6,820.0,40.0,71.7,40.0
+74.3,21.5,1.75,1.12,3.28,18.1,71.7,1999.0,29.2,52.3,9.06
+45.7,34.0,5.47,3.34,8.06,14.9,20.7,225.0,14.2,39.2,20.9
+65.5,31.9,4.41,3.46,9.56,43.7,79.1,922.0,28.1,50.9,27.6
+67.9,24.6,2.5,1.01,12.7,21.3,44.9,523.0,26.7,47.0,10.1
+94.7,36.5,6.79,1.23,5.47,14.6,30.2,567.0,113.0,175.0,37.9
+56.7,31.3,7.77,4.07,8.98,80.6,143.0,557.0,15.7,37.2,15.1
+55.2,24.4,1.73,6.38,9.65,14.3,29.7,328.0,2.46,13.7,75.0
+14.1,19.1,3.37,2.13,6.61,7.04,26.9,704.0,27.6,44.9,11.3
+75.0,18.3,3.28,1.01,15.4,24.6,38.5,175.0,15.5,33.4,89.0
+89.8,42.9,6.32,1.0,3.75,20.7,44.9,271.0,21.1,38.5,13.1
+68.5,25.7,3.4,1.25,5.73,7.84,20.7,27.6,16.0,33.4,11.8
+1.12,22.7,6.38,1.0,14.2,25.3,42.2,449.0,24.6,50.5,13.1
+43.7,28.4,10.2,1.23,14.6,17.8,39.6,337.0,19.1,41.0,12.7
+10.5,23.1,2.62,1.05,13.7,18.1,40.7,289.0,24.4,49.6,43.3
+47.4,16.3,1.84,1.95,7.77,32.5,57.3,445.0,20.5,42.2,22.9
+53.3,21.5,6.85,2.92,39.2,19.1,55.7,679.0,64.9,114.0,47.8
+41.4,24.1,11.8,1.55,8.35,9.91,58.3,389.0,2.59,16.1,79.9
+259.0,172.0,1.0,1.41,15.5,21.5,42.6,407.0,39.2,73.7,48.3
+99.1,46.6,5.33,1.3,20.5,10.9,32.5,466.0,7.04,21.9,2.67
+58.3,27.6,7.7,4.29,6.55,6.55,15.5,28.9,16.5,31.1,16.1
+54.7,33.4,9.73,2.17,19.8,46.6,85.8,604.0,31.6,54.7,26.4
+49.1,18.8,5.94,3.62,2.86,85.1,130.0,1027.0,15.4,42.9,67.9
+62.6,38.5,8.43,3.79,7.57,143.0,211.0,874.0,29.7,48.7,14.6
+53.3,30.5,3.55,9.31,15.3,36.2,86.6,2035.0,32.5,77.7,23.3
+71.0,23.7,12.7,3.31,12.2,8.74,17.5,547.0,12.2,29.7,8.9
+170.0,43.7,1.86,1.95,3.02,34.3,81.3,67.3,42.9,92.2,63.8
+61.0,14.9,3.31,2.53,22.1,19.6,47.8,237.0,2.67,18.6,13.7
+77.0,17.8,1.0,5.19,1.79,39.2,69.8,1134.0,2.37,19.3,57.3
+22.5,22.5,10.5,2.67,13.5,10.4,26.2,449.0,13.7,23.7,7.37
+66.7,27.9,4.1,1.0,17.5,18.1,28.1,410.0,5.14,11.2,86.6
+12.2,10.4,7.23,1.26,11.3,8.74,30.5,179.0,22.3,42.9,16.3
+73.7,18.9,3.68,1.36,18.8,7.84,16.5,433.0,1.0,9.47,4.91
+98.2,31.9,12.5,2.86,21.5,12.1,38.9,35.9,39.6,96.5,34.3
+10.5,13.6,2.33,1.01,10.1,15.5,35.5,400.0,25.5,47.4,25.5
+82.8,30.0,9.82,5.23,23.7,7.99,20.5,610.0,16.0,42.9,23.3
+12.5,14.3,1.0,1.01,2.81,41.0,61.5,311.0,13.0,31.3,15.7
+64.9,34.0,2.31,1.45,19.1,7.5,16.0,400.0,3.65,23.7,62.6
+18.3,15.5,3.05,4.53,25.7,30.2,56.7,1486.0,29.2,69.8,26.9
+57.3,33.7,1.0,2.84,8.9,79.9,153.0,1219.0,6.21,13.0,5.19
+59.9,35.2,8.66,1.33,14.9,6.79,29.4,12.0,14.1,36.8,13.3
+49.6,15.3,1.39,1.01,28.6,24.8,71.0,2035.0,9.73,23.1,26.9
+17.9,18.1,4.1,1.0,20.9,24.1,35.9,302.0,18.9,40.3,13.5
+69.8,32.8,3.62,1.68,10.2,11.9,26.4,426.0,1.93,20.7,44.1
+40.3,26.2,6.67,1.0,12.5,11.2,44.5,784.0,18.4,33.7,12.5
+79.9,27.9,3.89,1.0,13.8,49.6,139.0,1144.0,13.6,30.5,8.06
+93.9,34.3,1.0,1.0,7.7,8.82,24.4,632.0,5.62,12.1,115.0
+106.0,26.9,6.26,3.22,4.87,12.4,37.2,514.0,25.5,39.2,9.47
+7.1,21.7,4.49,2.97,18.4,21.9,101.0,1230.0,22.5,48.7,34.6
+57.3,29.7,2.02,2.86,15.5,12.0,21.5,259.0,11.1,22.1,11.1
+67.9,53.3,4.83,4.74,5.38,63.2,112.0,1486.0,39.6,65.5,29.7
+14.1,33.7,1.43,1.0,16.8,33.7,57.8,410.0,7.37,24.4,7.43
+56.2,26.2,6.85,3.25,13.2,68.5,121.0,626.0,28.1,73.7,45.7
+93.1,30.5,1.72,1.0,16.5,6.73,34.0,717.0,50.5,107.0,59.9
+50.0,31.1,1.86,1.79,7.64,19.1,33.1,267.0,3.34,21.1,56.2
+41.8,23.1,1.0,1.06,12.1,20.5,33.1,292.0,35.2,66.7,25.9
+170.0,142.0,26.7,170.0,39.2,39.2,75.7,874.0,10.7,20.0,9.56
+61.5,37.5,4.78,2.25,18.8,21.3,30.5,274.0,11.2,17.0,6.1
+108.0,46.1,5.88,1.0,9.56,26.4,28.9,316.0,36.2,68.5,54.7
+80.6,18.6,2.29,1.76,8.43,25.3,49.6,313.0,31.3,76.4,9.82
+10.6,17.5,1.57,1.84,14.2,15.1,48.7,1512.0,31.9,57.3,9.14
+71.0,22.5,10.7,1.53,31.3,16.1,34.9,429.0,3.34,9.22,5.99
+16.7,13.3,6.73,1.0,7.77,22.9,38.5,403.0,1.78,3.4,6.15
+161.0,42.2,5.94,1.75,1.49,7.3,15.4,750.0,17.5,31.3,20.4
+61.5,25.5,6.15,2.46,13.3,34.3,56.7,365.0,2.53,17.2,54.7
+31.9,23.7,1.25,1.7,18.4,39.2,61.5,604.0,20.5,38.5,16.0
+19.5,7.43,1.41,1.13,13.0,23.5,43.3,385.0,26.2,52.3,36.2
+50.5,19.6,3.37,5.67,1.93,20.7,36.8,429.0,17.5,41.8,10.5
+41.4,18.3,3.68,4.26,17.5,20.2,29.4,385.0,30.0,62.6,30.2
+50.5,21.3,4.18,3.08,16.1,13.9,31.6,505.0,17.0,36.5,14.3
+36.2,31.9,1.23,8.74,9.22,8.13,24.1,355.0,25.0,58.3,31.9
+86.6,35.2,4.87,1.91,1.54,85.8,184.0,1208.0,7.43,30.0,107.0
+92.2,63.2,3.52,3.34,19.5,11.2,31.1,457.0,19.8,29.4,12.1
+36.8,17.9,2.48,4.14,12.9,39.2,63.2,858.0,28.1,46.6,6.73
+71.7,21.9,2.27,5.05,11.0,26.9,47.4,334.0,37.9,69.2,20.4
+80.6,31.9,8.82,1.0,14.2,20.9,36.5,433.0,37.9,62.1,16.4
+13.6,40.7,2.15,5.09,13.7,19.6,31.1,257.0,24.4,41.4,27.9
+55.7,31.6,6.79,250.0,82.0,7.64,18.1,514.0,22.3,41.8,14.7
+23.7,14.7,1.21,2.48,1.0,7.99,19.8,487.0,26.4,58.3,23.1
+58.8,17.3,5.28,1.0,1.1,46.6,53.8,259.0,27.9,80.6,184.0
+36.8,14.1,6.98,1.0,8.28,14.3,36.5,500.0,53.3,101.0,77.7
+67.9,19.8,1.33,1.0,5.28,20.4,32.5,305.0,34.3,58.3,21.1
+47.4,25.0,1.01,2.15,34.6,28.9,61.0,1778.0,16.8,33.1,27.9
+11.1,13.8,14.7,5.09,9.47,44.1,86.6,723.0,26.4,84.3,48.7
+57.3,17.9,6.55,1.0,14.2,11.1,30.2,667.0,17.6,44.1,30.8
+64.9,26.7,1.0,1.0,22.7,40.7,73.0,2054.0,2.76,13.7,47.8
+67.9,39.6,15.5,6.61,17.5,18.8,42.6,18.1,37.9,86.6,35.9
+77.0,30.5,4.49,2.46,18.3,24.6,41.8,302.0,13.0,18.8,50.9
+91.4,30.8,7.64,5.94,10.1,6.32,10.5,300.0,6.49,13.7,56.2
+8.2,12.2,1.58,5.88,11.2,11.3,19.1,328.0,2.94,12.3,25.7
+69.8,24.8,1.0,2.69,17.9,29.2,61.5,1134.0,21.1,32.2,17.5
+37.9,19.5,1.0,2.94,6.38,93.9,168.0,661.0,4.83,23.5,69.8
+8.35,13.0,5.83,1.0,32.2,24.8,38.2,308.0,2.69,9.73,27.6
+161.0,113.0,3.82,2.11,17.9,28.6,64.9,523.0,17.6,42.2,13.6
+44.1,26.9,8.2,1.0,10.8,4.26,20.2,667.0,23.7,75.0,16.3
+64.4,25.9,5.78,3.62,18.6,10.4,40.0,820.0,20.7,40.3,13.0
+54.7,11.8,4.18,1.0,31.1,66.7,154.0,1928.0,20.7,57.3,23.9
+59.4,36.2,9.47,6.44,9.56,79.1,145.0,922.0,32.5,66.7,36.8
+88.2,34.0,1.0,167.0,35.2,19.8,41.8,241.0,1.64,12.2,42.9
+56.2,47.8,7.57,3.65,8.58,5.52,10.9,167.0,36.2,69.2,21.7
+27.6,21.3,4.26,1.88,11.9,9.39,19.6,828.0,5.78,13.6,78.4
+78.4,31.6,6.49,3.43,2.79,10.9,25.0,414.0,11.7,34.3,73.0
+70.4,40.0,2.57,1.65,3.43,23.5,42.9,392.0,2.39,11.4,43.3
+80.6,30.0,18.8,1.65,15.4,19.8,54.7,281.0,21.5,41.0,13.9
+88.2,37.5,7.3,1.57,1.79,71.7,186.0,1197.0,28.4,44.5,15.5
+43.7,37.2,5.38,2.27,8.2,6.1,13.8,567.0,11.5,35.5,13.2
+133.0,102.0,6.73,1.01,9.14,79.1,139.0,750.0,1.83,31.1,97.3
+14.2,25.5,8.2,1.01,22.7,57.8,87.4,1027.0,14.7,37.9,6.04
+56.2,24.8,3.75,5.05,10.9,12.7,30.2,229.0,4.66,14.9,65.5
+91.4,22.5,1.0,2.29,7.91,5.78,13.8,874.0,18.6,33.7,12.2
+70.4,31.9,6.61,1.0,12.0,45.3,101.0,2187.0,11.7,27.6,16.1
+118.0,59.9,9.47,2.94,6.73,18.9,59.4,692.0,33.4,51.9,31.9
+55.2,22.1,1.11,1.0,2.35,18.4,50.9,389.0,8.28,41.8,87.4
+60.4,57.3,7.23,1.0,8.43,93.1,165.0,1946.0,5.0,16.7,78.4
+72.3,22.1,3.55,1.01,13.0,10.3,25.5,334.0,4.18,21.1,83.5
+58.8,35.9,2.84,7.37,16.0,22.9,32.5,294.0,20.2,40.0,11.5
+121.0,38.9,15.4,25.3,24.6,27.6,45.7,346.0,15.8,40.3,13.1
+132.0,55.2,17.0,6.79,13.3,9.39,25.9,523.0,25.7,58.8,27.9
+111.0,36.5,6.98,1.0,15.3,28.4,54.2,211.0,4.66,33.7,100.0
+11.3,21.3,1.54,1.0,16.1,64.4,120.0,615.0,18.9,37.2,23.5
+54.7,16.1,5.09,5.05,22.5,7.64,18.3,500.0,24.4,42.6,11.1
+89.8,38.2,12.7,2.64,18.1,21.3,47.0,319.0,12.4,21.9,12.3
+79.1,16.5,6.1,1.64,15.5,7.99,29.4,385.0,32.2,67.9,21.7
+65.5,36.5,2.79,1.93,16.1,26.7,41.0,289.0,1.7,15.8,57.8
+328.0,346.0,1.0,1.0,23.3,13.9,38.2,271.0,41.4,78.4,19.8
+90.6,25.7,7.37,1.0,25.3,7.37,20.7,379.0,29.2,71.0,118.0
+119.0,76.4,7.04,2.17,8.98,24.8,41.0,343.0,7.5,54.2,48.7
+67.9,26.2,2.44,1.0,16.3,34.0,74.3,594.0,22.1,42.9,6.1
+56.2,8.98,8.9,5.14,35.2,17.8,60.4,1370.0,25.9,37.5,11.0
+25.5,16.8,10.6,1.01,11.8,48.3,117.0,453.0,40.3,75.0,63.8
+47.0,83.5,8.82,2.59,3.68,24.4,40.0,227.0,24.1,30.5,14.6
+36.2,16.7,6.73,3.85,18.9,34.6,57.3,632.0,2.69,25.0,91.4
+62.1,36.8,10.8,2.17,14.2,15.0,32.5,382.0,21.7,42.6,23.1
+32.8,22.7,8.66,1.57,18.3,41.8,52.3,349.0,18.4,41.0,22.7
+32.2,16.0,1.89,1.0,22.3,9.06,23.3,403.0,5.83,21.3,62.6
+110.0,53.3,3.89,1.0,14.3,12.5,33.1,292.0,31.9,75.7,69.2
+114.0,157.0,14.7,3.0,34.6,9.31,16.5,523.0,18.4,42.6,15.4
+41.8,18.8,18.8,7.43,25.3,10.7,19.6,429.0,21.3,55.2,18.1
+102.0,26.4,8.13,1.08,19.6,51.4,89.0,982.0,40.7,92.2,54.7
+93.1,27.1,3.79,1.75,20.9,17.0,29.7,583.0,35.5,61.0,32.2
+106.0,23.9,8.74,1.18,28.1,8.51,26.9,717.0,17.8,32.5,14.2
+75.7,31.9,4.91,4.96,18.8,37.2,66.7,610.0,24.1,58.8,43.7
+123.0,70.4,9.06,1.01,14.1,25.7,47.4,239.0,20.4,44.9,24.4
+47.0,26.4,1.79,1.02,25.7,36.2,85.1,1611.0,29.4,58.8,21.3
+70.4,47.4,3.37,1.23,13.7,13.5,20.4,621.0,30.0,71.7,139.0
+60.4,14.6,3.55,1.57,4.03,6.04,7.04,28.6,15.3,31.6,8.2
+101.0,32.5,9.39,1.29,13.9,13.8,41.4,478.0,24.4,53.8,96.5
+82.8,23.9,10.0,7.17,13.8,32.8,40.0,215.0,3.25,13.3,77.0
+85.8,30.0,11.5,1.0,11.9,8.9,20.9,567.0,19.5,37.5,4.57
+20.5,17.9,1.0,4.83,26.4,12.6,19.8,372.0,12.1,34.3,14.5
+18.1,23.9,3.49,1.01,8.28,19.5,46.1,418.0,6.85,25.7,83.5
+88.2,27.1,12.2,1.01,3.59,20.5,29.7,392.0,16.1,41.8,18.1
+103.0,44.1,3.52,1.38,19.6,10.5,20.4,396.0,15.5,36.2,32.8
+33.1,17.3,5.52,3.68,6.85,5.67,34.9,491.0,20.7,33.7,21.7
+10.5,23.9,3.34,2.86,26.4,5.62,28.4,777.0,25.3,58.8,31.9
+77.7,29.2,1.01,1.2,14.7,8.82,32.2,523.0,12.5,31.3,132.0
+52.3,29.4,3.13,1.23,1.93,51.9,147.0,939.0,11.9,24.4,12.0
+42.2,37.9,2.74,1.01,33.4,15.3,27.9,599.0,22.1,53.8,15.3
+71.0,30.8,8.43,4.03,15.1,12.5,35.5,164.0,3.05,18.9,89.0
+53.8,38.2,8.43,1.0,24.8,22.1,45.7,257.0,7.77,4.91,62.1
+77.0,34.9,1.47,1.68,19.1,34.9,63.2,1486.0,52.8,85.8,30.8
+14.2,12.5,9.73,1.01,13.5,21.7,51.9,319.0,1.0,47.8,4.1
+34.3,21.7,10.5,1.35,14.5,20.9,32.5,264.0,4.61,20.5,50.5
+77.7,43.3,5.52,1.0,3.72,22.9,41.0,239.0,15.7,36.5,7.84
+66.7,42.2,8.66,3.65,13.3,19.3,71.7,692.0,18.8,47.4,10.9
+67.9,30.8,6.73,1.22,17.3,62.6,104.0,547.0,1.72,42.9,3.31
+62.6,14.3,2.92,3.11,9.22,17.5,34.9,578.0,15.3,42.2,9.56
+60.4,19.8,1.0,1.95,34.9,4.78,21.1,692.0,33.4,83.5,30.2
+82.8,37.5,1.0,7.3,1.12,15.3,24.6,396.0,14.9,34.9,8.98
+79.9,64.9,6.61,1.01,1.0,20.0,33.1,334.0,11.7,24.1,6.61
+77.7,35.2,7.17,1.0,15.4,22.3,46.6,300.0,5.42,23.5,100.0
+98.2,28.9,6.61,1.0,9.91,50.0,105.0,533.0,2.48,29.7,56.2
+75.7,23.9,1.0,1.64,26.9,19.3,34.9,311.0,21.9,41.0,16.1
+67.3,26.9,8.66,9.91,22.5,33.4,102.0,737.0,62.1,111.0,61.0
+84.3,47.8,14.9,48.7,34.3,26.9,38.5,267.0,24.4,58.3,42.6
+89.8,21.9,13.5,2.31,22.5,16.3,58.8,2227.0,21.5,48.7,20.5
+91.4,26.7,1.38,2.39,13.1,17.2,32.5,186.0,15.8,50.0,18.4
+66.1,25.0,6.61,2.84,7.91,11.0,32.5,297.0,34.0,70.4,47.4
+71.7,53.3,4.29,6.1,48.7,12.3,25.5,337.0,15.4,34.6,9.22
+170.0,41.8,5.52,1.41,23.9,24.1,37.9,286.0,1.39,30.2,4.53
+37.2,17.9,10.9,1.0,23.3,27.4,44.5,313.0,5.09,18.8,50.0
+69.8,29.4,8.35,1.39,20.7,3.75,8.06,302.0,20.5,46.6,9.39
+50.0,25.5,2.04,72.3,28.9,31.1,63.8,1843.0,20.5,34.0,7.1
+74.3,35.5,5.73,3.52,17.8,18.6,32.8,244.0,5.99,23.7,111.0
+79.9,58.8,7.99,2.64,3.34,10.6,23.9,392.0,47.8,69.2,35.5
+73.0,29.7,5.94,4.29,12.3,13.6,145.0,154.0,23.7,48.7,15.5
+39.2,20.0,3.0,3.28,18.8,30.5,65.5,1670.0,36.8,87.4,92.2
+111.0,107.0,4.53,5.38,9.06,12.3,20.2,319.0,2.35,105.0,5.28
+50.9,30.0,12.1,1.79,21.7,1.64,20.0,770.0,29.2,66.7,18.8
+26.4,25.5,10.6,3.28,36.8,25.0,41.8,292.0,16.3,39.6,15.4
+89.8,57.8,4.7,1.15,18.1,22.5,40.3,271.0,10.8,22.1,9.47
+78.4,43.7,3.75,4.7,11.7,17.2,31.9,211.0,74.3,112.0,28.9
+53.8,17.5,4.83,1.01,4.0,41.4,71.0,1197.0,5.14,16.7,71.0
+7.57,32.2,8.43,1.01,7.5,14.1,30.5,305.0,34.3,63.8,14.9
+20.9,23.7,11.9,4.22,24.8,87.4,161.0,685.0,10.6,25.5,14.2
+75.7,23.9,6.44,1.0,20.0,15.7,34.0,474.0,24.4,55.2,21.1
+66.1,34.9,15.7,6.67,18.8,14.9,31.6,281.0,4.96,28.4,89.8
+51.4,18.1,9.14,1.0,6.73,24.8,51.9,337.0,24.8,70.4,59.9
+130.0,49.1,13.3,6.21,3.79,43.3,79.1,770.0,2.79,17.2,65.5
+132.0,77.0,2.19,1.61,5.52,6.92,19.8,379.0,14.6,34.0,14.3
+62.1,14.7,4.83,1.39,10.2,26.2,43.3,523.0,21.9,28.6,11.5
+13.1,10.6,6.85,2.92,5.05,23.7,40.3,340.0,4.53,23.7,111.0
+53.8,26.2,5.09,1.06,1.0,13.8,29.7,294.0,12.6,28.9,6.38
+54.2,23.1,5.78,2.64,7.43,34.3,59.9,466.0,2.09,56.2,4.22
+61.0,18.9,5.42,3.0,11.1,13.6,16.3,426.0,20.4,50.0,17.9
+54.7,18.9,3.02,4.37,13.8,21.7,35.9,235.0,14.1,25.7,10.8
+66.7,19.3,2.46,1.06,25.3,10.7,36.2,422.0,11.8,25.7,9.91
+75.7,29.2,2.13,1.0,18.6,10.5,14.3,276.0,58.3,85.8,30.0
+52.3,15.1,12.1,5.52,7.91,7.23,17.0,328.0,1.19,9.39,53.3
+77.0,28.6,11.2,3.28,16.4,14.6,35.9,355.0,25.3,41.8,13.3
+46.1,18.8,1.0,6.15,9.65,26.4,46.6,239.0,11.2,27.4,9.91
+175.0,77.0,3.72,2.33,11.3,10.1,26.9,588.0,24.4,37.5,25.7
+28.6,27.6,8.28,1.0,14.9,12.7,32.5,615.0,14.6,31.9,9.47
+96.5,40.0,1.0,3.25,15.1,27.1,48.3,757.0,24.8,43.7,20.0
+103.0,35.2,7.43,6.49,20.0,46.1,88.2,626.0,1.73,75.7,3.34
+6.67,12.9,2.15,7.99,17.2,11.7,49.1,514.0,4.66,24.1,63.2
+13.3,20.2,8.2,2.17,21.7,6.44,28.4,23.5,12.2,23.7,7.3
+145.0,53.3,7.7,1.39,1.84,50.9,113.0,843.0,22.3,44.1,64.4
+14.5,20.7,1.38,5.62,26.9,24.8,38.5,284.0,58.3,161.0,40.3
+97.3,36.2,1.76,2.11,21.3,2.31,22.5,426.0,3.46,34.0,95.6
+18.6,17.8,1.0,1.01,18.4,26.4,32.2,264.0,30.2,52.8,25.3
+63.8,22.5,4.74,1.11,20.5,13.7,28.4,528.0,11.5,20.2,1.68
+85.1,21.9,1.08,1.0,7.5,8.74,18.8,355.0,5.83,17.9,103.0
+69.2,16.4,5.99,1.21,13.7,14.7,34.0,281.0,2.27,19.8,83.5
+79.1,41.4,1.0,1.72,7.77,6.98,22.7,604.0,14.2,25.0,14.6
+83.5,19.5,7.57,1.08,2.76,17.9,33.4,316.0,16.7,26.9,15.4
+1.46,3.82,5.52,5.83,11.8,53.3,107.0,1843.0,21.9,61.0,19.1
+87.4,22.9,2.23,1.0,13.7,9.47,14.7,478.0,10.0,24.4,9.56
+73.0,61.5,9.47,3.96,15.4,7.17,13.7,241.0,36.5,76.4,49.1
+90.6,59.9,8.51,2.74,8.13,9.91,31.6,704.0,14.5,36.8,74.3
+50.5,20.9,1.88,1.91,14.7,34.3,107.0,1055.0,4.66,32.5,115.0
+141.0,139.0,8.58,1.01,12.3,7.84,25.3,791.0,20.9,41.4,18.6
+12.9,12.7,5.33,3.22,13.7,51.4,81.3,673.0,16.3,39.6,19.1
+176.0,36.5,1.32,5.88,20.5,11.8,33.4,255.0,17.0,33.1,29.4
+32.2,13.2,4.14,2.41,15.0,14.6,28.6,638.0,54.7,73.0,23.9
+17.6,8.2,4.61,1.0,6.79,24.6,51.4,193.0,20.7,33.7,4.87
+61.0,47.0,4.53,1.35,7.57,26.2,51.9,355.0,40.3,75.7,45.7
+49.1,34.3,3.28,1.0,2.19,23.5,38.2,264.0,36.2,62.6,95.6
+31.6,8.66,7.99,1.0,8.06,37.9,84.3,1611.0,8.51,56.2,239.0
+117.0,56.7,6.98,3.52,11.1,10.9,40.0,982.0,7.17,15.1,22.9
+84.3,46.1,4.45,1.01,11.5,5.99,14.1,18.6,21.1,59.9,274.0
+42.9,12.2,13.1,3.82,18.6,45.3,75.0,655.0,4.61,9.31,8.58
+73.0,25.5,2.41,1.23,18.4,21.7,50.0,533.0,19.1,31.9,19.3
+79.9,52.3,6.67,1.68,2.67,9.91,23.1,509.0,73.0,142.0,30.2
+58.8,13.1,10.4,1.01,5.47,23.1,43.3,334.0,6.04,24.6,95.6
+19.6,27.1,14.9,1.01,18.4,29.4,48.3,359.0,8.82,33.7,66.7
+51.4,16.3,1.27,4.07,13.1,25.7,44.1,274.0,15.1,34.0,9.65
+34.0,13.8,4.7,6.49,21.3,16.3,45.7,403.0,4.91,18.6,61.5
+71.0,21.3,6.73,2.81,12.1,44.9,71.0,319.0,19.8,37.2,25.0
+114.0,26.2,10.0,3.05,4.29,18.9,36.8,331.0,3.65,33.7,89.8
+49.6,30.5,7.3,2.02,5.47,21.1,41.0,237.0,14.5,34.9,10.5
+53.8,21.3,4.26,1.75,7.57,4.87,5.99,453.0,15.4,26.4,9.82
+36.2,17.8,5.14,3.43,9.65,14.7,31.6,385.0,15.7,31.1,11.2
+81.3,64.4,2.04,1.0,15.5,44.5,89.8,583.0,11.2,43.7,6.04
+93.1,32.5,4.91,8.58,27.1,21.5,49.1,1346.0,11.8,37.9,75.7
+30.8,16.7,7.37,3.02,9.65,18.6,31.6,297.0,22.1,29.7,7.1
+80.6,32.5,9.73,1.0,13.3,25.3,28.4,229.0,32.8,47.4,10.7
+59.4,15.3,1.01,2.37,19.6,15.7,41.0,269.0,11.1,22.1,6.44
+59.9,24.1,1.68,1.49,2.46,25.5,52.8,382.0,9.22,34.6,94.7
+66.7,18.8,4.7,1.0,5.78,41.0,89.8,1655.0,25.5,48.3,13.9
+74.3,18.6,3.4,1.01,7.7,20.2,36.8,235.0,30.2,79.9,75.7
+14.6,25.7,3.46,1.01,22.5,26.9,44.1,246.0,30.5,50.0,16.1
+81.3,30.2,5.09,2.89,15.4,14.7,29.7,644.0,4.1,14.7,22.5
+35.5,22.5,5.14,1.01,19.8,46.1,94.7,1596.0,5.33,25.5,89.8
+41.0,9.31,1.0,1.0,5.67,28.6,40.0,274.0,18.8,59.4,23.3
+81.3,38.5,8.43,1.12,1.0,16.8,36.5,519.0,27.6,52.8,13.1
+73.7,38.5,11.8,1.01,8.2,26.4,54.7,991.0,12.9,42.2,12.5
+17.8,19.3,16.3,2.07,20.4,7.84,7.5,375.0,25.5,47.4,12.3
+59.9,48.3,18.9,23.9,29.2,5.88,31.1,750.0,10.3,39.6,196.0
+107.0,32.5,4.87,1.91,7.1,2.84,16.5,491.0,28.4,67.9,25.5
+7.3,11.9,6.38,4.57,10.2,11.2,19.3,528.0,9.91,35.5,37.5
+58.8,22.7,3.28,3.46,7.43,12.3,36.2,267.0,3.31,25.0,75.0
+52.3,12.2,7.04,2.84,31.1,16.0,41.0,505.0,11.3,33.1,6.73
+61.5,23.1,8.74,7.3,9.65,13.7,39.2,400.0,29.7,46.6,16.0
+53.8,23.5,2.48,5.83,4.26,41.8,55.7,209.0,12.1,21.9,15.3
+94.7,44.5,5.05,2.59,19.1,30.0,53.3,610.0,27.1,52.3,13.8
+63.8,28.4,2.59,7.91,4.41,3.92,27.6,843.0,2.57,10.8,8.2
+33.4,33.1,7.37,3.96,1.0,71.0,120.0,305.0,15.3,42.9,82.8
+60.4,22.5,2.41,3.34,7.3,17.5,20.5,284.0,42.2,89.0,70.4
+63.2,25.5,2.09,4.7,4.96,66.1,132.0,770.0,18.9,38.9,95.6
+77.7,24.8,5.0,1.01,6.92,18.8,28.4,221.0,9.91,16.5,8.28
+59.4,27.4,5.38,2.48,5.52,8.74,13.6,461.0,12.3,19.8,12.7
+15.5,11.7,2.25,2.44,20.5,23.7,49.1,233.0,10.2,53.8,67.3
+18.6,11.3,2.59,1.0,1.19,15.4,24.4,426.0,20.4,44.9,8.98
+16.4,20.4,3.46,8.98,7.3,25.9,28.1,279.0,4.37,24.6,93.9
+18.4,31.9,1.0,1.65,1.31,30.2,60.4,1176.0,6.26,23.9,101.0
+59.9,13.8,2.11,1.88,10.9,50.0,97.3,1946.0,2.46,7.17,79.1
+87.4,25.5,5.99,1.0,4.57,43.3,89.0,1843.0,7.1,63.2,20.5
+36.8,19.6,1.84,2.71,10.0,8.2,23.5,449.0,2.86,22.9,106.0
+17.5,19.3,4.41,1.0,4.61,4.83,19.6,750.0,4.22,18.8,93.9
+44.9,30.5,8.43,6.79,22.3,3.22,25.0,820.0,12.0,31.9,18.9
+42.2,21.7,8.13,1.02,1.83,14.1,19.1,302.0,25.0,38.5,16.3
+69.8,22.5,5.73,1.01,16.1,35.5,45.3,313.0,20.7,53.3,20.5
+4.45,6.1,8.2,1.0,50.0,17.6,19.5,437.0,15.5,34.0,22.7
+13.1,27.9,12.4,1.0,10.8,39.6,112.0,743.0,22.9,32.8,21.7
+90.6,36.5,8.9,1.0,1.96,7.99,14.3,328.0,15.0,29.4,14.7
+85.1,16.3,3.16,1.09,6.92,63.8,179.0,898.0,4.37,14.3,77.7
+63.8,27.4,4.57,1.76,15.4,3.43,19.8,362.0,36.8,82.8,28.6
+11.1,18.4,6.44,1.01,19.1,20.0,38.2,368.0,27.9,54.2,38.2
+74.3,28.4,11.5,4.26,16.5,142.0,191.0,466.0,2.59,10.9,69.2
+87.4,41.8,1.0,2.71,9.82,30.2,63.2,396.0,1.0,106.0,10.0
+89.0,24.4,2.62,2.15,4.61,6.55,25.5,25.3,14.7,41.4,6.04
+121.0,77.7,3.55,1.0,14.5,6.61,19.3,661.0,26.2,42.6,14.3
+63.2,27.6,10.4,21.1,35.9,7.17,45.7,1358.0,5.73,49.1,142.0
+63.8,30.8,4.91,1.02,11.9,84.3,150.0,453.0,37.5,69.8,42.6
+77.0,33.1,5.19,4.07,16.7,13.0,32.5,441.0,25.3,50.5,22.9
+9.14,8.66,5.88,8.2,21.1,37.9,76.4,685.0,23.1,34.9,17.3
+51.4,20.0,6.79,1.01,11.9,10.0,29.4,410.0,21.3,33.1,20.2
+73.0,25.3,14.9,4.66,48.3,4.7,22.1,478.0,27.9,43.7,7.77
+93.9,34.9,5.52,1.89,5.23,45.3,141.0,922.0,24.8,53.8,30.0
+49.1,25.3,6.92,1.14,14.3,12.3,37.9,784.0,29.7,75.0,34.6
+43.7,18.6,2.84,1.01,14.3,24.4,57.3,890.0,6.26,2.46,3.72
+55.7,33.4,1.0,6.67,7.43,20.4,40.0,610.0,30.0,46.1,10.7
+62.1,23.1,3.52,2.79,39.2,11.3,15.7,400.0,2.79,34.9,66.7
+51.9,27.9,17.8,83.5,47.4,32.2,106.0,1382.0,14.5,27.1,13.7
+30.0,7.64,8.28,5.52,18.9,22.5,32.2,322.0,22.5,42.9,24.6
+9.39,26.9,13.8,2.46,16.3,15.5,26.9,237.0,11.4,20.4,18.8
+38.2,16.1,14.6,1.54,23.9,29.7,48.3,302.0,19.6,58.8,29.7
+66.7,27.6,1.41,1.01,28.1,20.5,34.9,233.0,7.23,47.0,161.0
+38.2,19.3,10.5,2.79,16.7,16.7,31.3,717.0,12.9,33.7,9.56
+33.7,13.3,4.14,1.0,17.2,18.9,37.5,375.0,1.0,66.7,13.5
+15.1,17.2,6.61,1.93,16.4,26.4,44.1,281.0,3.19,17.6,50.9
+60.4,22.9,9.06,1.01,2.55,21.7,41.4,233.0,13.3,38.2,10.9
+31.9,12.9,6.32,3.92,6.26,53.3,102.0,906.0,32.2,63.8,107.0
+76.4,41.4,5.88,5.14,12.9,62.1,117.0,445.0,12.7,23.7,3.85
+50.5,24.1,3.89,5.23,26.4,41.8,102.0,777.0,9.73,30.2,12.4
+55.2,18.8,6.04,5.99,13.9,29.2,60.4,445.0,13.5,30.0,6.79
+66.7,20.0,11.5,4.14,10.0,5.47,21.3,422.0,11.0,35.9,82.8
+42.2,32.8,2.27,3.28,24.6,42.6,124.0,1252.0,36.2,75.7,107.0
+38.2,19.8,14.9,1.0,5.78,4.57,38.2,573.0,20.9,52.3,17.0
+66.1,18.8,1.0,1.68,15.5,12.0,17.0,418.0,11.5,29.2,7.64
+56.2,20.9,7.43,1.0,18.9,10.9,27.1,449.0,19.5,30.5,9.65
+175.0,99.1,7.99,6.61,2.5,37.2,66.1,552.0,19.6,29.7,28.1
+17.5,30.5,13.2,3.28,20.5,13.9,20.2,271.0,8.43,25.0,88.2
+82.0,43.3,1.86,1.0,13.2,19.8,54.7,2167.0,11.2,17.9,8.74
+52.3,9.39,1.6,4.66,10.5,12.1,43.7,474.0,17.0,29.2,11.7
+17.9,16.8,9.65,8.06,14.3,19.3,31.6,710.0,23.3,47.4,20.0
+44.1,17.6,3.65,1.0,24.1,18.4,57.8,835.0,30.2,46.6,8.58
+66.1,23.1,3.08,1.23,22.7,28.4,55.2,982.0,6.73,36.5,81.3
+18.1,18.9,9.31,1.75,10.1,21.5,37.9,255.0,5.57,12.7,5.0
+78.4,20.5,2.94,3.11,27.9,14.2,28.9,496.0,8.98,27.6,82.8
+7.04,19.5,9.14,1.06,13.1,13.3,30.2,710.0,28.1,44.5,11.0
+71.0,26.4,3.19,2.81,1.47,28.1,47.0,346.0,24.8,41.4,33.4
+17.2,23.5,4.03,1.41,23.9,19.1,34.0,267.0,5.94,15.8,86.6
+87.4,30.5,10.3,1.57,18.6,26.7,40.0,334.0,33.1,73.0,34.3
+35.2,21.1,14.5,1.11,6.61,11.3,30.5,922.0,12.6,37.9,6.85
+74.3,25.5,2.92,1.01,15.3,4.07,35.5,487.0,7.37,27.6,58.3
+45.7,19.6,6.44,5.83,11.8,3.75,23.1,588.0,18.4,43.3,75.7
+56.2,16.4,8.58,4.49,5.0,17.0,127.0,982.0,15.4,30.2,12.9
+56.7,32.2,1.01,1.0,1.75,3.68,14.2,449.0,11.8,32.5,6.85
+33.4,55.2,5.38,4.37,10.2,23.5,47.8,316.0,21.5,46.1,9.56
+79.9,53.3,10.3,1.19,12.7,33.7,56.7,231.0,24.1,49.1,17.2
+86.6,58.8,5.42,2.94,12.4,18.9,33.1,478.0,18.3,35.2,7.1
+42.2,21.7,13.1,14.5,10.2,34.0,67.3,331.0,28.9,55.7,19.1
+47.8,29.7,11.4,6.85,11.9,18.1,29.7,259.0,7.77,21.5,5.19
+3.28,7.57,6.04,4.07,11.5,30.0,86.6,1065.0,19.1,44.1,17.8
+29.4,8.43,7.91,1.43,14.6,5.62,23.9,644.0,17.8,32.8,16.8
+40.3,22.9,1.45,1.01,5.28,25.0,37.5,355.0,33.1,63.8,33.7
+82.0,89.0,2.46,1.01,11.8,14.5,33.1,610.0,16.1,32.2,19.8
+41.4,28.6,6.92,2.37,4.96,30.8,61.5,638.0,11.4,23.3,5.52
+10.1,26.4,2.81,1.0,16.5,23.1,50.9,557.0,35.5,77.7,38.2
+73.0,31.9,5.0,1.0,10.4,22.9,46.1,300.0,5.05,25.9,71.0
+55.2,76.4,8.13,2.86,16.1,8.98,26.2,514.0,25.3,48.3,11.4
+54.2,16.4,12.2,1.12,8.98,11.5,39.2,375.0,23.9,35.5,15.5
+56.7,18.8,5.47,1.86,9.06,9.06,20.9,552.0,1.0,33.1,79.9
+36.2,44.5,33.7,147.0,66.1,18.3,28.9,188.0,2.35,18.6,67.3
+74.3,23.7,9.39,5.99,7.99,37.2,63.8,956.0,4.53,15.8,89.8
+21.7,36.8,4.07,1.0,23.1,34.9,62.6,379.0,33.4,71.7,18.3
+88.2,42.9,11.4,167.0,41.8,20.2,40.0,322.0,13.1,31.1,9.65
+66.1,19.3,10.8,1.0,16.7,13.9,38.2,255.0,16.1,30.2,11.2
+67.9,32.8,2.17,1.01,7.04,9.82,36.2,615.0,26.9,40.3,9.14
+37.2,15.3,18.9,23.1,19.1,15.8,33.4,284.0,27.6,32.2,13.5
+73.0,41.4,2.94,2.48,5.14,51.9,101.0,890.0,27.1,62.6,18.8
+64.9,43.3,6.1,1.0,28.4,10.0,22.9,491.0,12.2,25.9,6.61
+35.5,14.5,4.96,5.57,5.19,6.92,41.8,65.5,22.3,54.2,35.9
+10.4,9.82,5.94,1.0,16.7,28.1,49.6,331.0,6.26,24.4,10.5
+85.1,20.5,3.02,1.07,17.0,7.99,23.1,316.0,49.1,68.5,16.0
+63.8,34.3,3.34,1.0,14.3,15.0,63.8,931.0,1.0,20.0,67.9
+3.62,2.15,2.46,3.65,10.5,38.2,93.1,2054.0,13.7,16.4,9.56
+39.6,20.4,4.91,1.01,8.43,13.6,26.2,136.0,3.49,12.6,62.1
+43.7,12.5,3.62,2.69,6.73,6.1,28.1,583.0,30.5,49.1,15.8
+61.0,28.9,10.3,1.01,20.7,111.0,184.0,491.0,12.5,37.2,7.1
+23.3,27.4,9.06,1.01,6.92,25.0,77.7,478.0,39.2,109.0,26.2
+64.4,15.1,3.49,2.19,1.96,28.4,90.6,1860.0,23.7,39.6,23.5
+34.0,14.7,2.48,2.64,16.1,44.1,85.8,1114.0,1.86,19.5,25.7
+72.3,50.9,2.92,2.84,13.7,31.6,62.6,474.0,16.5,30.0,4.78
+63.8,21.7,7.77,1.58,21.5,14.5,28.1,382.0,14.1,33.1,19.6
+76.4,18.6,6.44,1.47,21.3,47.4,119.0,2393.0,2.64,17.5,62.6
+191.0,67.9,1.0,1.37,1.93,43.3,63.2,552.0,10.1,34.6,12.0
+30.0,16.0,10.3,7.57,2.23,28.4,54.2,791.0,8.2,16.5,9.82
+61.5,23.1,1.46,1.13,1.04,11.8,30.8,547.0,18.8,36.2,13.7
+23.7,22.5,6.15,2.44,13.7,5.52,38.2,552.0,37.5,86.6,58.8
+90.6,36.5,4.74,1.01,19.6,23.3,30.0,271.0,26.9,40.7,16.3
+27.4,26.9,8.2,2.62,8.51,18.9,37.2,246.0,36.8,67.9,34.9
+59.4,32.8,7.17,7.23,21.5,9.56,29.4,246.0,56.7,108.0,64.9
+1.0,7.5,17.8,4.74,12.4,6.67,32.5,552.0,5.09,32.2,57.3
+16.1,17.9,1.83,1.01,10.3,53.3,94.7,542.0,17.6,42.2,16.1
+55.7,31.6,8.06,2.69,16.5,9.31,28.1,1009.0,10.9,31.1,13.7
+34.6,15.4,1.24,4.14,16.5,18.1,30.8,241.0,12.5,21.3,12.6
+57.3,33.4,4.87,1.01,10.5,10.4,47.0,1407.0,45.3,50.9,21.7
+57.8,22.9,4.57,1.6,32.8,6.15,14.1,255.0,8.2,42.2,264.0
+67.9,36.5,14.5,5.14,10.3,45.7,80.6,898.0,18.4,34.3,22.3
+78.4,42.6,8.28,1.5,20.2,49.6,97.3,784.0,13.7,19.1,9.06
+31.3,16.7,10.2,5.09,20.4,22.5,48.3,828.0,6.21,24.1,94.7
+7.5,22.3,7.99,4.1,13.7,15.4,21.7,211.0,40.3,76.4,27.1
+38.5,23.9,1.37,2.21,4.29,33.7,61.0,730.0,10.0,17.9,6.44
+77.7,75.0,8.43,1.14,30.5,25.0,55.7,316.0,42.9,61.0,14.1
+46.1,39.2,6.38,1.14,14.3,3.02,19.5,828.0,3.02,16.5,83.5
+82.0,26.9,3.31,8.13,23.5,8.13,23.7,610.0,20.4,33.7,22.1
+85.1,24.1,5.88,2.29,18.8,11.5,22.5,437.0,5.47,42.9,90.6
+80.6,45.7,2.31,3.46,19.6,29.2,27.9,334.0,11.0,24.4,18.1
+82.8,25.7,7.3,1.86,10.7,9.14,23.3,349.0,20.7,44.9,23.7
+60.4,35.5,6.92,1.39,13.7,20.2,67.9,1512.0,37.2,40.3,11.2
+129.0,62.1,8.13,1.01,24.1,120.0,217.0,679.0,15.7,39.6,13.0
+66.1,28.1,11.5,3.82,8.35,2.81,11.5,319.0,21.9,40.3,22.1
+52.8,27.1,3.31,3.89,2.64,21.9,44.5,426.0,12.2,33.7,4.14
+37.5,26.9,15.4,1.0,1.63,13.2,55.2,1382.0,26.2,47.8,31.6
+57.8,34.3,4.87,1.95,14.6,16.8,32.8,289.0,13.2,23.9,22.1
+129.0,51.4,2.07,4.41,9.22,25.5,33.4,227.0,1.78,39.6,8.51
+30.2,20.5,3.13,8.74,3.59,12.3,27.4,349.0,22.3,43.3,5.0
+72.3,20.9,3.59,1.01,24.6,78.4,138.0,1486.0,32.2,45.3,15.1
+58.8,34.9,3.49,368.0,39.6,17.8,27.9,331.0,23.3,51.9,98.2
+71.7,27.6,4.91,3.96,8.35,21.3,34.3,274.0,30.0,63.2,13.3
+54.7,19.8,3.19,1.0,23.7,16.3,176.0,113.0,11.8,53.3,78.4
+25.0,25.0,15.3,2.29,32.2,20.9,41.8,227.0,5.28,20.0,82.8
+21.7,11.8,2.84,2.29,9.91,21.5,37.5,267.0,31.6,63.8,67.9
+59.4,31.1,6.61,1.0,1.53,16.4,23.7,379.0,1.58,8.13,2.55
+41.4,24.4,2.41,1.0,12.7,67.3,135.0,626.0,18.3,29.2,13.0
+47.8,25.9,7.17,1.0,16.5,23.1,40.7,379.0,3.43,30.0,4.07
+21.1,18.8,4.0,3.85,3.11,55.7,85.8,433.0,50.5,109.0,52.8
+45.3,19.8,16.4,4.78,8.35,6.44,17.5,610.0,12.6,24.8,10.9
+66.7,30.0,1.54,7.99,25.3,30.8,50.5,289.0,11.2,18.4,4.1
+38.5,22.9,7.17,4.61,22.9,103.0,229.0,594.0,29.4,64.9,4.96
+122.0,33.7,1.29,4.87,11.0,3.92,20.7,269.0,19.1,38.5,14.1
+37.5,23.9,7.1,4.41,5.67,10.3,19.6,292.0,29.2,42.2,18.8
+81.3,24.6,1.0,5.42,11.2,6.49,18.6,466.0,20.4,42.2,25.0
+30.8,20.5,8.06,1.47,28.9,29.7,47.4,655.0,12.6,31.3,7.7
+30.0,19.6,2.76,2.37,1.0,20.7,36.5,835.0,23.3,42.9,24.4
+20.4,45.7,2.89,1.31,6.61,20.5,40.3,250.0,10.7,46.6,94.7
+11.1,41.8,4.26,7.77,9.22,19.1,27.6,209.0,1.91,85.8,3.16
+176.0,93.9,7.04,3.92,13.7,28.6,41.0,250.0,11.9,23.5,15.7
+53.8,23.1,1.05,1.39,29.4,4.26,24.4,449.0,10.5,27.9,5.23
+44.5,23.7,6.79,3.4,12.5,31.9,57.3,221.0,46.1,65.5,38.9
+61.0,53.3,8.74,1.01,19.1,5.88,37.5,1334.0,20.2,36.8,9.91
+66.1,19.5,1.75,1.0,17.0,3.11,5.33,188.0,18.9,38.9,12.9
+59.9,31.9,1.0,1.01,20.9,24.6,41.4,239.0,17.0,28.6,13.6
+50.5,29.7,5.09,3.19,11.1,25.7,60.4,426.0,2.25,5.09,79.1
+69.8,22.3,14.2,2.64,16.3,37.2,102.0,2738.0,25.7,57.8,37.5
+106.0,30.2,1.01,5.14,10.6,14.9,30.8,457.0,3.96,34.0,114.0
+6.1,35.9,11.7,2.84,4.61,150.0,229.0,784.0,16.7,32.8,88.2
+9.73,17.5,4.18,5.62,4.66,22.3,36.5,322.0,23.1,62.1,79.1
+47.8,34.3,11.4,6.98,25.7,49.6,98.2,538.0,22.5,31.9,8.28
+103.0,69.8,33.1,7.77,42.9,16.0,44.5,1114.0,25.3,43.7,12.7
+74.3,38.5,3.11,1.01,12.4,15.4,34.0,538.0,30.2,64.4,23.3
+72.3,18.9,5.94,5.67,2.44,9.31,23.7,557.0,46.1,77.7,32.8
+11.9,49.6,8.35,3.08,8.2,29.2,202.0,191.0,13.9,37.5,10.4
+31.9,12.9,1.98,1.01,3.75,47.4,103.0,1928.0,50.5,109.0,55.2
+48.3,19.1,3.08,1.96,8.13,13.8,44.9,1134.0,22.1,41.8,6.92
+75.0,27.1,2.46,1.01,17.3,38.9,92.2,770.0,21.9,35.5,21.9
+74.3,26.4,7.7,7.3,1.58,10.6,25.7,400.0,8.43,18.4,6.61
+58.3,27.9,8.43,1.01,4.66,22.9,54.7,346.0,14.9,24.6,6.26
+49.1,23.1,1.83,1.7,15.0,47.0,104.0,2072.0,39.2,73.0,38.5
+79.1,23.5,5.23,4.66,15.3,15.8,32.5,379.0,25.0,57.8,29.2
+104.0,64.9,11.9,1.0,23.5,54.7,112.0,704.0,17.6,36.8,12.3
+42.9,39.2,10.9,3.31,12.3,36.2,76.4,487.0,13.7,31.3,11.1
+87.4,39.2,1.01,4.07,5.09,62.1,111.0,365.0,13.0,32.8,20.2
+53.8,18.9,5.0,1.54,17.2,22.3,38.9,189.0,28.4,78.4,20.0
+48.7,30.0,9.31,1.67,2.25,20.2,36.8,437.0,4.07,67.3,2.57
+40.3,22.9,3.46,6.26,14.1,29.4,209.0,1554.0,27.9,53.8,23.9
+82.0,42.2,4.0,5.33,9.06,7.99,18.4,385.0,14.7,13.0,7.17
+35.9,14.7,9.39,11.8,45.7,22.5,36.5,221.0,2.62,23.9,68.5
+38.5,20.2,16.4,8.43,22.3,27.6,49.6,250.0,20.5,49.1,17.3
+53.8,27.4,3.05,1.68,24.8,23.3,44.9,359.0,26.4,60.4,42.2
+56.2,19.8,9.91,4.87,6.73,26.7,41.0,221.0,28.4,40.0,9.73
+51.9,12.5,4.29,1.18,7.84,13.9,28.4,284.0,22.1,55.7,15.4
+57.3,23.7,9.56,1.83,9.47,17.6,49.6,717.0,22.1,40.3,12.1
+110.0,65.5,8.35,1.01,20.4,18.1,33.1,396.0,35.9,66.1,19.3
+61.0,41.0,3.96,3.92,19.8,27.6,44.5,355.0,28.9,69.2,34.9
+70.4,24.6,1.0,4.53,42.9,79.1,155.0,2227.0,3.96,12.0,33.4
+62.6,23.1,3.34,3.31,14.3,14.5,27.6,355.0,17.8,30.2,3.4
+113.0,73.0,1.0,1.31,11.5,8.74,31.1,487.0,40.0,79.9,43.7
+91.4,25.0,4.33,1.46,18.3,7.43,17.3,433.0,6.38,34.6,175.0
+2436.0,3685.0,16.4,40.0,11.2,1.0,41.8,105.0,6.38,23.7,77.7
+114.0,160.0,11.8,32.2,13.6,3.82,38.2,119.0,7.23,44.9,15.8
+557.0,947.0,7.7,18.6,36.5,5.19,64.9,138.0,2.05,20.0,12.4
+638.0,914.0,11.9,59.4,18.9,2.46,44.1,107.0,1.22,17.9,7.37
+316.0,461.0,4.91,73.7,24.6,4.7,30.5,2017.0,25.9,49.6,15.8
+181.0,279.0,4.61,281.0,50.9,5.23,50.9,215.0,1.72,28.1,13.0
+213.0,328.0,26.9,160.0,59.9,1.12,68.5,95.6,7.43,27.4,5.83
+139.0,189.0,2.5,457.0,32.2,1.6,105.0,403.0,1.7,32.2,9.91
+173.0,274.0,8.58,50.0,30.8,1.25,23.1,48.3,24.1,76.4,22.3
+322.0,500.0,15.5,23.5,9.06,1.83,38.2,36.8,1.0,23.7,9.65
+1999.0,2738.0,12.0,19.6,18.4,1.0,61.0,88.2,8.51,26.7,143.0
+389.0,588.0,11.1,82.0,13.6,29.4,119.0,4105.0,1.0,31.6,7.84
+122.0,181.0,19.5,9.65,2.07,1.54,45.7,96.5,6.1,23.7,4.1
+509.0,723.0,10.7,55.2,19.1,3.75,82.8,137.0,1.0,33.1,11.9
+227.0,334.0,21.7,35.5,14.1,3.92,120.0,269.0,9.06,55.2,17.0
+99.1,112.0,11.5,70.4,24.6,3.4,93.1,346.0,9.22,38.9,271.0
+175.0,231.0,11.2,110.0,42.6,12.3,141.0,3820.0,1.0,34.3,3.79
+1472.0,2129.0,11.0,5.47,20.0,1.0,23.3,78.4,1.0,10.8,6.21
+204.0,355.0,20.2,32.5,23.3,1.32,23.3,103.0,14.9,47.8,22.3
+1165.0,1685.0,12.6,16.5,3.02,3.13,84.3,349.0,1.0,29.4,15.5
+161.0,269.0,14.3,21.9,17.9,31.3,202.0,4332.0,4.7,29.7,12.6
+274.0,410.0,14.2,235.0,75.0,2.17,63.8,126.0,16.8,52.3,20.5
+248.0,389.0,10.2,82.8,33.4,11.9,69.8,1827.0,1.15,45.7,15.1
+372.0,588.0,16.5,379.0,64.4,2.41,110.0,331.0,1.81,21.3,15.3
+1046.0,1568.0,13.5,18.4,5.83,1.0,32.2,95.6,15.0,53.3,22.7
+286.0,375.0,17.8,33.4,10.1,7.7,59.4,355.0,11.9,44.9,13.9
+157.0,274.0,1.86,18.6,23.7,1.0,170.0,379.0,1.0,12.6,9.06
+461.0,723.0,12.3,15.1,12.6,12.0,37.5,737.0,10.6,47.4,12.3
+281.0,414.0,22.5,31.1,21.7,6.32,77.0,271.0,4.07,27.9,1.67
+621.0,1065.0,16.4,36.2,20.7,6.49,59.4,1894.0,20.9,58.8,28.9
+269.0,426.0,17.5,23.9,2.27,1.41,11.0,10.8,2.37,37.9,5.57
+305.0,445.0,10.3,20.0,8.58,1.0,19.3,106.0,1.0,26.7,5.78
+106.0,142.0,11.0,60.4,19.5,1.09,133.0,362.0,3.89,37.9,5.94
+49.6,49.6,13.8,63.8,19.5,27.9,100.0,1472.0,1.64,35.2,9.65
+95.6,136.0,13.1,25.3,11.4,2.86,42.2,223.0,28.6,129.0,75.0
+359.0,470.0,9.31,168.0,31.1,1.0,13.6,87.4,1.0,18.8,8.06
+181.0,271.0,25.9,135.0,48.3,6.92,121.0,385.0,44.1,111.0,50.5
+196.0,322.0,11.4,30.2,30.8,3.92,115.0,487.0,5.47,59.4,8.13
+59.4,72.3,10.6,21.7,5.05,37.9,158.0,3051.0,3.49,37.2,9.65
+114.0,145.0,7.77,131.0,30.0,1.0,32.5,107.0,11.9,33.7,17.3
+151.0,237.0,14.1,27.4,17.3,2.39,42.2,204.0,1.0,36.5,18.3
+433.0,667.0,7.1,10.6,32.8,2.0,83.5,334.0,4.41,14.1,7.57
+813.0,1208.0,14.2,72.3,27.6,3.34,75.7,233.0,2.46,11.5,5.33
+173.0,244.0,22.1,18.9,17.6,1.0,48.3,98.2,2.89,18.6,13.0
+274.0,433.0,8.13,146.0,31.6,2.11,64.4,322.0,2.67,107.0,349.0
+122.0,231.0,7.77,141.0,6.73,1.0,43.3,113.0,12.2,30.0,30.2
+1155.0,1700.0,5.57,155.0,13.9,4.22,52.8,1655.0,2.37,16.0,5.42
+154.0,165.0,9.65,183.0,36.2,3.4,111.0,316.0,49.1,90.6,42.2
+239.0,349.0,10.0,17.0,30.8,2.59,32.8,102.0,1.17,12.0,1.36
+355.0,453.0,10.3,19.8,15.3,2.13,155.0,319.0,1.65,21.7,3.65
+509.0,799.0,14.9,13.8,9.47,26.7,133.0,4217.0,11.7,54.7,28.9
+1208.0,1731.0,12.5,17.9,15.5,32.2,184.0,4826.0,2.55,33.4,11.5
+673.0,1055.0,19.8,22.3,8.82,1.24,26.4,33.7,1.41,40.7,1.0
+62.6,69.2,14.7,28.6,23.7,1.22,66.7,73.0,4.78,35.2,11.4
+124.0,176.0,15.0,25.9,31.6,1.0,31.1,124.0,2.67,29.7,12.6
+770.0,1084.0,13.8,19.1,8.28,27.4,145.0,6321.0,3.31,37.5,164.0
+100.0,126.0,18.4,32.5,7.84,10.8,111.0,189.0,6.49,45.7,11.0
+403.0,610.0,6.32,106.0,12.5,16.1,186.0,1094.0,3.02,30.2,15.8
+257.0,410.0,6.98,21.5,48.3,1.0,38.5,54.7,20.2,52.3,27.1
+1286.0,1827.0,10.0,50.9,42.2,3.62,59.9,183.0,33.7,96.5,48.3
+141.0,229.0,5.67,13.5,40.3,1.03,233.0,441.0,1.0,19.6,8.06
+55.7,112.0,14.6,20.4,7.77,1.88,16.7,10.9,3.72,10.6,3.96
+175.0,217.0,9.14,73.7,28.1,1.5,31.9,62.6,4.18,47.4,19.5
+1230.0,1700.0,12.9,142.0,43.7,2.84,33.7,79.1,10.3,38.5,25.7
+246.0,352.0,10.6,17.0,18.4,1.0,27.4,48.7,11.2,46.6,147.0
+12.7,17.9,13.1,56.2,14.1,1.14,32.8,45.7,3.16,33.1,11.5
+313.0,445.0,15.7,16.3,1.01,1.18,29.4,36.8,1.0,13.2,6.04
+67.3,106.0,14.5,22.9,15.4,20.5,71.7,882.0,5.19,16.4,7.37
+496.0,770.0,12.6,14.3,9.22,2.37,27.6,45.3,11.8,34.9,19.3
+368.0,588.0,19.8,130.0,51.4,17.2,67.9,2458.0,19.3,44.9,8.58
+204.0,244.0,18.4,27.6,25.9,1.0,42.2,82.0,5.99,5.62,3.75
+137.0,183.0,7.99,4.03,10.1,1.24,12.2,85.1,3.08,21.3,76.4
+305.0,552.0,4.0,183.0,24.6,2.62,28.1,155.0,1.58,47.8,11.7
+207.0,331.0,1.1,11.7,6.26,8.98,44.9,284.0,4.45,41.0,8.98
+215.0,337.0,44.1,109.0,87.4,3.89,25.5,1778.0,1.0,11.7,1.0
+334.0,449.0,11.9,87.4,21.5,4.78,82.0,1794.0,34.0,82.8,56.7
+120.0,215.0,16.0,22.7,4.78,2.79,66.1,279.0,8.9,30.0,23.5
+308.0,466.0,5.14,2.92,10.6,3.0,42.2,241.0,2.27,16.3,12.3
+42.2,46.6,14.2,21.9,14.5,6.1,79.1,1176.0,20.4,59.4,32.5
+39.6,59.4,9.65,21.1,10.6,1.91,14.1,55.7,1.0,11.5,7.57
+209.0,271.0,23.5,31.6,10.6,7.3,101.0,217.0,14.7,27.1,4.7
+281.0,400.0,9.73,23.1,30.5,25.5,153.0,2054.0,38.5,79.1,237.0
+132.0,188.0,18.9,17.5,2.97,55.2,219.0,4255.0,10.8,38.5,106.0
+433.0,638.0,7.99,130.0,26.7,1.96,74.3,215.0,4.07,23.3,12.2
+183.0,225.0,38.9,100.0,69.8,1.0,56.2,109.0,1.57,28.1,6.44
+308.0,514.0,13.7,59.9,6.85,4.74,67.9,292.0,9.91,101.0,172.0
+127.0,195.0,14.2,17.8,21.1,1.67,23.7,74.3,16.7,61.0,11.2
+1275.0,1827.0,8.74,16.0,5.52,4.87,39.6,100.0,23.1,56.2,15.8
+186.0,235.0,34.3,120.0,48.3,2.05,89.0,184.0,31.9,119.0,49.6
+105.0,155.0,17.2,19.3,6.85,1.0,31.9,137.0,1.0,12.9,8.9
+325.0,491.0,35.5,69.8,13.5,1.0,43.3,106.0,13.1,42.2,94.7
+69.8,109.0,11.9,49.6,11.0,2.07,113.0,264.0,11.5,37.5,10.6
+1018.0,1446.0,4.07,122.0,13.3,3.08,14.6,64.4,3.89,27.6,13.9
+76.4,57.3,20.9,109.0,112.0,28.6,137.0,2054.0,3.79,44.9,10.1
+59.4,63.2,28.6,61.5,27.9,1.53,37.2,139.0,23.5,53.8,21.9
+343.0,599.0,16.3,53.3,13.9,1.7,32.5,137.0,3.92,27.6,3.25
+297.0,403.0,5.78,22.9,7.3,3.37,109.0,328.0,3.65,22.7,6.15
+588.0,922.0,22.5,33.1,20.5,24.4,70.4,1286.0,7.37,51.4,98.2
+791.0,1197.0,47.0,13.0,26.9,1.61,28.6,53.3,44.5,88.2,25.0
+235.0,340.0,16.8,15.1,17.8,1.01,33.1,58.8,1.17,32.5,5.47
+170.0,239.0,6.92,67.3,11.0,16.0,63.2,1486.0,57.3,139.0,33.7
+644.0,1000.0,6.61,1.47,154.0,1.88,59.9,219.0,32.5,66.1,28.6
+284.0,414.0,17.0,20.4,8.35,2.35,28.1,35.5,1.0,32.5,13.1
+638.0,956.0,18.9,50.5,46.6,9.91,93.1,1382.0,1.35,33.1,16.1
+235.0,334.0,10.4,61.0,11.3,1.0,70.4,241.0,1.0,9.56,12.1
+225.0,340.0,13.8,56.7,36.8,2.13,58.3,255.0,2.04,29.4,1.95
+382.0,562.0,131.0,93.9,770.0,1.12,31.1,102.0,1.61,18.1,3.16
+2738.0,3924.0,14.9,11.1,6.04,2.57,78.4,221.0,1.65,18.1,3.4
+898.0,1407.0,7.77,13.9,30.2,12.3,77.7,1794.0,13.8,45.3,17.0
+193.0,264.0,20.5,19.5,17.9,18.9,61.0,1124.0,2.11,13.1,61.5
+42.9,34.3,117.0,219.0,59.9,3.31,30.5,91.4,15.4,32.8,195.0
+1472.0,2072.0,34.9,28.9,19.6,7.7,49.6,2308.0,10.7,40.3,68.5
+97.3,126.0,53.8,188.0,106.0,1.0,46.1,121.0,2.11,27.9,124.0
+85.8,123.0,16.4,103.0,12.3,1.0,63.8,241.0,1.01,19.8,3.4
+92.2,91.4,45.7,79.9,37.2,1.0,139.0,188.0,12.9,49.6,8.51
+1155.0,1747.0,15.5,154.0,27.4,2.33,75.7,248.0,4.07,29.7,8.9
+172.0,279.0,5.99,28.1,47.0,6.21,72.3,325.0,3.72,32.8,8.58
+143.0,229.0,14.5,25.0,20.0,2.29,30.2,61.5,3.55,16.7,10.5
+204.0,308.0,26.2,23.1,5.52,5.42,58.3,176.0,12.4,80.6,158.0
+167.0,289.0,17.0,33.1,13.2,4.57,141.0,325.0,12.2,32.2,112.0
+615.0,982.0,28.9,44.5,31.3,9.56,191.0,1670.0,1.18,7.37,7.64
+223.0,352.0,16.1,163.0,55.7,10.8,132.0,1568.0,9.31,34.9,13.9
+72.3,106.0,15.7,25.3,13.6,1.0,49.6,89.0,12.2,42.2,13.2
+300.0,449.0,22.7,25.9,5.73,11.3,67.9,1407.0,4.22,48.3,12.0
+31.3,34.6,7.57,150.0,21.1,1.31,118.0,257.0,31.1,58.8,22.3
+99.1,184.0,10.2,89.0,34.0,1.21,50.0,120.0,15.7,50.9,63.8
+39.2,38.2,9.06,80.6,25.0,1.47,66.1,195.0,1.89,50.9,1.0
+914.0,1370.0,4.18,15.5,63.8,1.88,49.1,143.0,2.11,29.4,4.07
+109.0,176.0,15.8,973.0,98.2,3.28,57.3,279.0,37.9,67.3,4.61
+86.6,81.3,89.0,246.0,111.0,1.0,33.7,80.6,11.4,35.2,71.7
+35.9,35.2,23.1,95.6,32.5,3.11,75.0,289.0,3.43,25.3,8.9
+487.0,685.0,13.0,18.4,4.7,5.0,121.0,392.0,17.8,41.8,17.2
+478.0,723.0,18.4,21.3,1.0,12.4,91.4,2503.0,1.73,39.6,12.5
+2714.0,3889.0,13.9,94.7,40.0,1.79,195.0,414.0,9.39,41.8,24.6
+78.4,205.0,20.0,18.4,17.0,1.15,22.5,69.8,1.02,43.7,7.84
+400.0,547.0,13.5,55.7,15.1,2.74,31.1,147.0,12.9,58.3,32.8
+519.0,730.0,13.2,64.9,23.7,6.55,30.2,1700.0,24.6,48.3,13.5
+225.0,305.0,33.7,58.3,30.8,7.3,56.7,1731.0,2.48,9.39,8.9
+193.0,267.0,17.6,88.2,64.4,1.0,12.3,145.0,1.07,14.7,2.13
+215.0,305.0,4.1,4.7,10.6,2.11,19.1,41.4,3.52,38.2,6.04
+50.0,46.1,20.7,11.3,17.8,1.0,56.2,253.0,2.48,54.2,11.9
+46.6,93.9,10.2,8.2,30.5,29.4,80.6,956.0,3.11,17.5,2.33
+1420.0,1928.0,14.3,119.0,45.7,2.21,99.1,215.0,1.0,9.56,8.13
+40.7,68.5,18.9,30.0,22.3,2.64,11.1,92.2,2.37,55.7,16.4
+27.6,10.7,17.0,17.5,8.74,1.0,31.3,53.8,2.33,43.3,4.03
+2035.0,2788.0,23.7,34.9,21.7,12.4,107.0,882.0,2.64,27.9,2.0
+453.0,661.0,136.0,241.0,48.7,2.62,53.3,173.0,5.62,50.0,145.0
+365.0,644.0,14.7,123.0,17.6,1.24,39.6,115.0,23.1,93.9,48.7
+41.8,28.4,22.3,25.7,1.23,1.57,40.7,195.0,38.5,102.0,52.8
+193.0,308.0,14.7,46.1,21.3,2.37,16.1,62.6,19.8,44.1,18.3
+1065.0,1526.0,117.0,281.0,93.9,3.16,22.5,110.0,45.7,74.3,21.1
+213.0,308.0,15.3,52.8,33.1,1.0,19.5,151.0,8.2,55.2,31.1
+193.0,289.0,20.9,70.4,38.2,7.91,67.9,294.0,11.2,40.0,22.5
+213.0,311.0,4.33,196.0,82.0,3.46,35.5,124.0,1.19,12.6,2.02
+340.0,500.0,24.8,85.1,39.2,2.35,25.0,16.0,9.31,50.5,24.4
+1134.0,1582.0,1.0,9.91,15.7,1.36,42.9,96.5,2.21,20.0,55.7
+132.0,198.0,3.05,22.7,56.7,2.29,72.3,215.0,23.1,80.6,42.2
+106.0,172.0,13.6,49.6,40.7,4.45,146.0,392.0,7.84,52.8,34.3
+57.8,72.3,26.7,54.7,43.7,6.38,35.2,248.0,9.82,30.8,10.6
+956.0,1382.0,16.7,20.9,13.8,11.0,49.6,1540.0,1.73,41.0,10.3
+599.0,898.0,20.4,14.3,2.79,1.53,30.5,136.0,1.18,35.2,6.61
+231.0,352.0,20.0,106.0,34.0,1.24,37.5,93.1,4.7,28.4,106.0
+698.0,1104.0,21.9,21.5,5.05,3.02,138.0,359.0,46.1,93.1,29.7
+1000.0,1512.0,16.8,106.0,24.1,6.85,63.2,271.0,4.1,23.3,17.6
+188.0,292.0,11.4,93.1,14.1,1.0,38.5,129.0,1.04,17.6,8.06
+56.2,56.7,11.9,120.0,31.3,1.0,57.3,163.0,3.4,13.9,12.9
+164.0,213.0,15.8,552.0,66.1,1.0,25.7,90.6,5.33,77.7,175.0
+1009.0,1420.0,21.1,26.7,53.3,6.49,67.3,346.0,1.0,31.6,1.79
+461.0,784.0,20.2,24.1,7.43,1.1,20.2,87.4,1.64,19.1,2.53
+297.0,437.0,7.7,18.4,17.6,23.7,77.7,973.0,1.0,44.9,12.7
+164.0,269.0,59.9,67.3,23.1,1.0,118.0,223.0,1.0,8.74,1.51
+649.0,1027.0,17.0,47.4,17.5,1.0,56.7,146.0,20.4,47.0,9.82
+130.0,184.0,16.4,46.1,23.7,1.55,59.9,89.8,1.0,36.8,14.2
+196.0,286.0,11.1,17.0,5.0,22.7,84.3,2308.0,2.79,10.1,7.37
+231.0,325.0,13.8,51.9,22.3,2.74,51.9,129.0,3.11,23.5,6.61
+23.9,32.5,15.4,4.03,23.3,5.14,49.6,1877.0,3.59,57.3,6.79
+130.0,191.0,42.6,262.0,93.9,1.0,110.0,294.0,1.43,29.2,7.3
+122.0,65.5,16.5,17.5,9.47,1.33,118.0,284.0,1.38,37.2,8.13
+253.0,372.0,17.9,32.5,31.9,6.98,64.9,246.0,1.42,39.6,117.0
+316.0,445.0,16.1,22.7,41.0,4.57,35.5,213.0,1.18,23.9,5.42
+27.6,54.2,26.7,71.0,34.9,1.35,80.6,227.0,49.6,84.3,36.2
+1124.0,1554.0,13.0,83.5,41.4,1.0,53.3,94.7,4.29,34.3,14.9
+167.0,255.0,14.6,58.8,5.28,2.11,79.1,237.0,1.0,14.7,14.6
+153.0,248.0,27.6,22.3,14.3,4.22,33.1,799.0,1.0,41.0,9.73
+217.0,191.0,48.7,56.2,18.8,17.6,170.0,991.0,1.0,26.7,10.7
+241.0,319.0,11.8,123.0,44.1,7.77,47.4,1334.0,3.0,52.3,20.9
+433.0,588.0,15.5,14.5,13.2,4.33,17.6,71.0,2.86,22.3,3.46
+1275.0,1811.0,15.1,19.1,14.2,16.5,121.0,1104.0,1.5,54.7,11.0
+85.8,124.0,16.4,53.8,26.4,5.78,96.5,276.0,4.18,17.9,69.2
+30.0,41.8,12.2,18.1,18.4,1.0,42.2,237.0,1.75,34.3,5.0
+227.0,316.0,25.5,56.2,31.3,2.74,20.7,61.5,18.4,62.1,25.7
+64.4,79.1,21.1,33.4,5.67,2.35,47.4,71.0,4.96,17.8,9.14
+931.0,1310.0,12.5,23.7,1.3,5.09,44.5,85.1,1.64,14.3,10.4
+466.0,777.0,16.5,18.8,10.6,1.08,64.4,163.0,16.4,51.9,30.2
+1037.0,1420.0,20.7,12.5,19.1,1.0,67.9,143.0,2.55,11.2,7.64
+85.8,107.0,14.5,35.2,8.74,1.36,17.6,50.0,3.59,38.9,2.55
+470.0,704.0,17.2,21.7,5.62,1.0,38.2,54.7,3.05,24.8,17.9
+673.0,939.0,24.1,24.8,2.07,7.57,112.0,1499.0,4.03,22.3,7.04
+82.8,103.0,17.5,19.6,11.0,6.79,53.3,2148.0,28.4,66.7,103.0
+84.3,142.0,9.65,142.0,8.35,1.45,126.0,352.0,3.65,29.2,111.0
+300.0,445.0,18.4,16.7,12.6,25.9,158.0,1715.0,17.6,51.4,20.5
+154.0,189.0,5.47,26.4,20.9,12.4,109.0,1433.0,2.15,53.8,11.0
+843.0,1241.0,47.8,95.6,11.4,1.37,83.5,269.0,1.53,37.9,7.04
+308.0,547.0,15.7,56.7,30.0,2.09,30.5,167.0,1.0,13.1,1.88
+145.0,164.0,15.7,193.0,11.1,4.1,91.4,389.0,11.8,34.9,13.0
+181.0,271.0,3.96,17.0,25.9,1.72,110.0,262.0,1.0,26.9,5.05
+1794.0,2393.0,17.3,51.4,31.6,1.09,26.2,124.0,6.85,35.9,3.62
+66.7,88.2,17.6,27.1,19.3,1.14,17.5,81.3,3.37,21.3,9.91
+241.0,375.0,18.9,17.5,6.38,1.04,109.0,217.0,11.9,31.9,8.74
+1252.0,1762.0,13.8,66.1,15.5,3.89,165.0,573.0,2.67,36.8,6.15
+131.0,213.0,26.7,487.0,86.6,3.25,48.7,147.0,14.2,57.8,82.0
+52.8,73.0,11.2,89.8,15.4,1.0,20.7,77.7,1.5,6.38,7.5
+1526.0,2227.0,30.0,52.8,70.4,18.6,46.1,1176.0,21.7,72.3,42.2
+914.0,1298.0,11.1,46.6,10.9,4.14,38.9,149.0,1.76,30.8,6.21
+62.1,71.7,12.9,85.1,26.4,1.84,43.3,61.0,1.61,29.7,13.7
+274.0,426.0,9.31,19.3,11.2,1.0,17.2,44.9,4.0,26.9,16.4
+38.9,36.5,20.9,37.2,14.7,3.08,76.4,259.0,7.57,53.8,9.73
+58.3,87.4,15.7,96.5,19.6,22.3,145.0,956.0,1.64,26.7,16.0
+160.0,257.0,15.5,64.4,30.0,6.85,46.6,2350.0,1.54,34.9,12.2
+227.0,289.0,8.2,173.0,25.3,8.13,155.0,449.0,1.27,44.9,17.6
+63.2,89.0,20.4,23.5,73.0,1.43,40.3,167.0,1.0,21.3,6.49
+157.0,231.0,18.8,15.7,15.0,25.5,97.3,757.0,3.05,10.0,7.84
+32.5,77.0,10.7,25.0,19.8,1.0,23.5,93.9,1.0,28.4,6.32
+209.0,334.0,21.5,11.9,7.3,1.54,51.9,164.0,30.8,115.0,56.7
+547.0,906.0,26.9,319.0,50.9,1.24,124.0,340.0,9.91,34.0,20.2
+158.0,204.0,7.99,23.9,13.2,1.78,41.8,173.0,3.02,24.4,5.52
+231.0,269.0,24.8,22.7,41.4,1.45,11.8,78.4,8.2,32.8,9.14
+138.0,193.0,17.2,68.5,29.2,26.2,227.0,2148.0,3.0,17.2,5.23
+1252.0,1778.0,38.9,52.3,21.1,4.0,24.8,137.0,2.39,34.6,10.3
+931.0,1395.0,42.2,133.0,313.0,1.18,122.0,183.0,1.04,32.5,3.16
+130.0,198.0,16.5,10.8,22.9,2.74,30.8,91.4,10.8,32.5,5.83
+103.0,176.0,29.4,66.7,78.4,1.67,20.5,66.7,1.5,48.7,5.0
+78.4,94.7,9.22,25.0,42.6,4.29,64.4,209.0,1.0,19.6,5.42
+231.0,322.0,14.1,21.7,14.2,1.0,66.7,62.6,15.1,59.9,14.5
+632.0,843.0,25.0,88.2,59.9,12.0,55.2,1747.0,1.0,61.5,13.6
+211.0,286.0,19.3,27.4,2.62,1.0,33.7,146.0,1.51,48.3,12.5
+1230.0,1843.0,12.2,15.0,15.8,1.0,23.7,126.0,1.81,21.5,6.21
+89.0,146.0,12.0,30.5,6.79,1.0,58.3,223.0,4.74,15.3,7.7
+195.0,269.0,24.4,130.0,48.7,1.0,65.5,146.0,29.4,93.9,37.9
+55.2,32.2,1.96,300.0,30.8,5.14,91.4,791.0,10.6,31.9,18.3
+1144.0,1611.0,10.5,145.0,12.7,20.2,61.5,1230.0,3.59,31.1,8.51
+186.0,302.0,1.0,271.0,16.3,6.98,44.5,449.0,1.57,17.6,6.1
+1055.0,1625.0,10.3,35.5,64.9,4.61,29.4,29.2,1.2,32.5,4.61
+483.0,737.0,13.7,55.2,21.9,2.57,91.4,292.0,1.0,30.8,15.1
+52.8,86.6,7.3,27.6,42.9,2.84,46.1,104.0,1.14,20.7,4.14
+95.6,137.0,21.9,37.5,13.1,1.54,41.4,123.0,1.2,16.0,8.98
+211.0,322.0,42.6,45.3,13.6,10.6,85.1,407.0,1.0,44.9,6.49
+302.0,437.0,12.7,39.2,17.9,1.0,53.3,168.0,3.62,50.9,79.9
+1275.0,1843.0,19.5,153.0,23.3,1.0,79.1,271.0,1.0,25.7,5.47
+533.0,813.0,5.94,12.4,20.5,1.0,32.2,65.5,1.5,20.4,2.33
+939.0,1433.0,32.5,25.5,37.2,2.94,28.6,98.2,1.58,22.3,76.4
+67.9,93.9,29.7,16.4,2.89,2.76,55.2,158.0,4.96,51.4,8.58
+178.0,284.0,19.6,48.3,18.1,3.79,44.5,1298.0,39.6,62.6,28.9
+1499.0,2091.0,26.2,52.8,106.0,3.43,133.0,331.0,3.85,30.5,16.3
+225.0,346.0,23.5,53.8,84.3,19.5,85.8,1459.0,2.39,25.0,6.73
+308.0,453.0,20.4,15.5,1.0,4.83,82.8,365.0,3.65,15.4,17.2
+175.0,264.0,12.6,17.2,18.4,2.21,39.6,866.0,1.0,31.3,1.0
+198.0,264.0,3.4,40.3,5.83,1.2,40.3,141.0,3.62,37.9,13.7
+80.6,105.0,25.9,15.7,25.3,4.57,117.0,233.0,16.5,41.0,18.3
+65.5,73.0,23.3,32.2,16.0,2.86,62.6,117.0,1.0,26.2,7.99
+44.9,74.3,24.4,12.3,29.4,3.82,178.0,352.0,3.96,13.6,7.99
+204.0,379.0,21.3,47.8,88.2,22.1,120.0,1540.0,10.7,37.5,18.3
+223.0,365.0,10.8,31.6,35.2,1.73,37.2,143.0,4.18,15.8,1.88
+87.4,167.0,25.5,379.0,66.7,1.0,45.7,57.8,33.1,57.8,43.3
+478.0,770.0,15.4,85.8,22.1,1.47,84.3,328.0,1.08,22.1,4.96
+58.8,125.0,7.57,196.0,27.4,2.81,17.2,98.2,4.26,20.5,14.9
+147.0,176.0,11.2,34.9,36.8,6.21,54.2,1459.0,16.3,55.7,32.2
+55.2,58.3,18.3,20.9,8.98,2.71,28.4,108.0,2.37,29.7,1.58
+231.0,343.0,16.3,59.4,20.5,2.97,30.0,124.0,2.67,22.9,3.82
+322.0,478.0,13.6,15.7,4.57,1.0,25.9,66.1,1.0,28.6,10.0
+241.0,328.0,13.2,94.7,25.7,2.55,23.9,153.0,2.67,9.91,3.65
+178.0,257.0,5.78,12.9,30.5,14.2,80.6,1911.0,5.99,42.2,10.6
+385.0,578.0,8.13,155.0,45.7,3.79,133.0,414.0,3.59,24.4,4.22
+300.0,426.0,21.1,20.5,12.1,3.72,61.0,274.0,1.3,24.1,7.64
+127.0,172.0,17.9,56.7,20.9,7.7,36.8,1018.0,1.0,26.4,10.2
+139.0,227.0,10.2,24.1,22.9,2.09,121.0,337.0,2.25,31.1,5.09
+244.0,322.0,14.7,12.0,3.82,1.76,54.7,118.0,4.49,58.8,30.2
+1219.0,1794.0,2.53,382.0,32.8,2.89,45.3,145.0,2.07,32.8,8.98
+193.0,311.0,10.3,28.9,77.0,42.6,337.0,2864.0,1.13,31.3,5.94
+562.0,906.0,15.5,18.3,12.1,1.19,35.2,85.1,7.1,38.5,17.0
+56.7,47.4,13.6,141.0,46.6,1.76,44.5,161.0,1.89,34.3,12.4
+157.0,223.0,22.7,217.0,71.7,1.58,59.4,114.0,1.22,19.3,10.5
+418.0,578.0,16.7,32.5,5.57,12.1,173.0,1670.0,9.14,64.4,7.1
+17.3,28.6,11.4,55.7,20.9,1.73,48.7,262.0,3.08,20.0,4.53
+1433.0,1999.0,25.9,23.1,13.0,4.91,77.0,1540.0,1.0,22.7,8.28
+101.0,167.0,46.1,313.0,66.1,68.5,599.0,5989.0,6.79,25.0,5.47
+253.0,346.0,13.0,117.0,36.5,13.7,53.3,300.0,34.3,76.4,26.7
+437.0,632.0,32.2,53.3,15.3,2.5,32.8,262.0,10.0,31.3,12.6
+56.7,45.7,14.9,123.0,52.3,2.5,47.8,170.0,2.19,21.5,5.78
+519.0,764.0,13.8,53.3,28.9,1.11,48.3,84.3,12.6,55.7,31.3
+137.0,253.0,4.41,13.7,13.7,6.98,4.91,325.0,2.69,11.3,14.9
+292.0,422.0,13.3,25.3,5.33,1.0,176.0,300.0,3.59,29.4,85.1
+63.8,71.0,12.7,15.7,1.0,1.0,44.1,50.9,4.07,40.3,121.0
+359.0,542.0,26.2,48.3,8.06,4.14,51.4,1540.0,1.19,31.6,7.43
+2227.0,3220.0,16.5,17.2,12.2,1.01,40.7,92.2,2.97,55.2,7.17
+737.0,1084.0,17.9,42.2,15.1,1.36,56.7,172.0,1.91,22.9,96.5
+227.0,334.0,23.9,63.8,17.3,14.7,64.9,1554.0,4.14,37.2,123.0
+164.0,244.0,13.9,14.6,1.0,1.83,71.7,150.0,2.76,26.9,5.14
+231.0,346.0,17.0,45.7,15.5,1.63,32.5,118.0,17.0,82.8,23.7
+40.0,51.9,17.6,164.0,56.7,1.43,56.2,122.0,3.46,28.4,4.66
+198.0,294.0,22.5,8.98,10.2,2.27,99.1,956.0,2.5,25.5,12.3
+141.0,221.0,13.5,64.9,31.9,2.89,80.6,193.0,1.45,25.0,10.8
+1310.0,1827.0,18.6,102.0,23.3,2.09,34.0,137.0,2.17,21.9,9.06
+168.0,269.0,10.6,161.0,19.3,1.98,49.1,178.0,1.25,12.1,5.42
+49.6,46.1,11.4,15.0,5.0,18.1,175.0,1197.0,1.0,20.4,10.0
+231.0,319.0,11.5,147.0,26.7,35.2,147.0,2916.0,2.15,36.8,8.13
+179.0,255.0,18.9,20.4,9.39,1.29,43.7,44.5,5.67,42.6,102.0
+106.0,136.0,15.7,12.1,24.1,2.94,178.0,487.0,3.49,32.8,86.6
+557.0,843.0,13.6,87.4,35.5,1.0,64.9,82.0,1.0,9.47,4.78
+94.7,137.0,23.3,9.22,40.0,4.0,22.1,410.0,1.07,50.9,17.8
+2187.0,3051.0,41.8,47.8,19.5,1.63,17.0,69.2,1.0,18.1,3.89
+328.0,403.0,8.13,20.9,17.5,1.0,18.1,82.0,1.08,21.5,13.0
+340.0,610.0,14.3,37.5,11.9,8.66,124.0,1407.0,1.0,17.6,4.07
+101.0,300.0,22.7,13.0,10.9,1.43,15.4,62.6,2.92,19.1,16.4
+160.0,229.0,15.8,48.7,4.83,1.0,55.7,179.0,21.7,52.8,20.5
+403.0,621.0,12.0,15.8,2.09,24.6,514.0,2035.0,2.41,28.9,2.86
+289.0,241.0,7.17,149.0,7.04,2.86,46.1,221.0,4.14,25.5,110.0
+509.0,799.0,28.1,31.3,20.9,25.5,139.0,2393.0,1.01,21.7,8.43
+661.0,991.0,54.2,101.0,20.0,3.11,34.3,183.0,3.68,23.1,8.74
+578.0,939.0,15.8,40.7,8.98,10.3,125.0,1568.0,1.21,33.7,11.0
+59.9,66.1,40.7,170.0,41.8,1.0,34.6,154.0,4.1,38.2,12.3
+253.0,359.0,15.5,20.7,34.3,4.03,93.1,267.0,1.0,33.4,7.37
+244.0,362.0,15.8,27.6,4.96,80.6,229.0,2738.0,23.1,46.6,27.1
+533.0,843.0,10.2,147.0,31.9,4.29,84.3,198.0,2.5,20.5,5.42
+204.0,308.0,22.7,33.7,14.1,26.7,96.5,882.0,7.5,31.1,11.1
+246.0,422.0,16.1,14.1,2.04,4.96,49.1,202.0,1.78,48.7,5.99
+1685.0,2393.0,17.2,110.0,34.0,1.75,55.7,137.0,2.09,40.0,8.66
+1499.0,2227.0,13.5,127.0,19.5,1.1,11.8,71.7,2.48,20.5,1.49
+64.9,99.1,34.9,43.3,69.8,5.67,138.0,410.0,4.61,12.7,1.64
+262.0,400.0,14.2,122.0,1.63,1.31,78.4,191.0,1.0,20.9,9.82
+86.6,74.3,8.43,136.0,16.3,24.1,72.3,1027.0,1.0,26.2,5.28
+679.0,982.0,9.39,131.0,8.28,9.56,73.0,255.0,3.43,36.2,2.53
+1446.0,2091.0,26.7,37.2,9.47,2.33,79.1,211.0,14.3,42.9,30.0
+573.0,882.0,12.4,11.5,4.0,9.22,65.5,289.0,1.27,14.9,7.43
+874.0,1298.0,15.0,10.4,16.5,1.15,15.4,86.6,2.44,40.0,13.5
+750.0,1144.0,12.6,14.5,11.4,12.4,47.4,939.0,11.0,20.7,8.66
+60.4,97.3,9.31,2.46,16.3,1.47,24.1,79.9,1.0,17.6,8.35
+328.0,466.0,14.7,39.6,49.6,6.61,60.4,165.0,2.31,48.3,15.5
+42.9,39.2,14.6,20.4,16.1,1.0,24.4,47.0,1.0,22.3,7.5
+474.0,799.0,16.4,20.0,25.5,13.2,56.2,1358.0,1.61,37.9,8.06
+196.0,267.0,42.9,65.5,104.0,11.2,59.9,422.0,1.79,36.8,14.7
+120.0,153.0,10.9,13.8,10.6,1.0,48.3,67.3,1.46,61.5,19.1
+227.0,340.0,10.2,22.1,3.65,1.0,33.1,31.9,1.96,24.6,6.1
+340.0,496.0,22.7,25.9,75.7,1.46,36.5,213.0,2.07,19.6,1.67
+365.0,542.0,3.59,21.3,34.3,10.8,126.0,445.0,1.23,21.9,8.82
+410.0,562.0,17.3,21.5,12.9,1.0,69.2,149.0,1.55,22.7,10.5
+55.2,85.1,6.04,20.2,5.0,1.96,67.9,126.0,4.66,22.5,8.2
+147.0,235.0,6.61,22.3,47.0,2.07,47.4,151.0,1.2,12.6,4.74
+155.0,227.0,34.0,49.6,7.3,2.74,36.2,147.0,2.48,24.6,2.64
+284.0,400.0,19.5,31.9,3.59,1.07,62.1,191.0,1.0,12.1,15.7
+2288.0,3429.0,35.2,42.6,18.9,1.43,30.5,1094.0,2.31,30.0,6.73
+355.0,523.0,14.1,25.9,16.5,2.09,93.9,294.0,5.67,30.2,6.15
+107.0,90.6,9.56,64.4,30.5,1.0,58.8,173.0,2.39,14.6,4.83
+139.0,165.0,14.6,21.7,11.0,1.37,67.9,137.0,1.0,14.1,2.05
+131.0,184.0,10.6,10.8,1.63,2.79,34.0,111.0,2.33,17.0,2.46
+81.3,139.0,21.3,20.9,8.35,1.0,12.6,50.0,1.12,45.3,12.9
+231.0,337.0,50.0,65.5,36.5,1.0,63.8,65.5,4.53,12.3,4.96
+49.6,54.7,27.1,337.0,38.2,4.91,47.8,1027.0,2.02,12.2,8.2
+523.0,828.0,13.2,73.7,15.4,1.0,119.0,279.0,1.2,37.9,6.73
+168.0,244.0,20.0,17.8,21.7,1.64,103.0,248.0,1.0,27.6,8.82
+799.0,1186.0,19.3,15.8,17.3,1.0,22.5,46.6,1.0,16.7,2.53
+349.0,441.0,50.0,328.0,79.1,2.02,28.1,58.3,1.0,15.5,4.07
+97.3,95.6,3.65,2.84,1165.0,7.5,160.0,429.0,2.86,43.7,7.5
+217.0,403.0,21.3,15.0,21.9,9.56,55.2,1459.0,4.57,40.0,13.8
+655.0,947.0,16.5,23.9,24.4,1.0,48.3,164.0,2.27,10.6,2.44
+71.7,115.0,25.0,36.8,10.5,3.08,71.7,259.0,1.0,15.5,7.7
+213.0,311.0,7.99,39.6,49.6,3.79,205.0,466.0,1.47,22.7,1.0
+250.0,372.0,19.8,248.0,79.9,4.78,151.0,328.0,2.71,9.56,10.0
+874.0,1334.0,26.2,30.8,7.23,1.0,28.4,46.1,1.49,17.6,7.1
+334.0,519.0,8.82,20.0,37.5,5.28,143.0,396.0,3.11,16.1,3.68
+186.0,235.0,25.5,61.0,22.9,8.82,126.0,1526.0,12.6,47.0,24.4
+88.2,91.4,14.1,13.3,8.9,8.98,97.3,1018.0,1.0,18.4,1.83
+757.0,1124.0,17.9,13.5,4.7,4.29,29.2,132.0,5.42,44.9,13.3
+160.0,255.0,36.8,83.5,24.8,4.1,30.8,191.0,2.21,27.4,7.77
+449.0,679.0,13.7,13.6,7.99,9.14,85.1,2091.0,2.57,53.8,6.55
+40.7,33.4,11.9,13.8,26.9,1.1,87.4,196.0,4.1,24.6,4.26
+25.7,113.0,9.82,20.2,33.7,4.1,113.0,385.0,18.3,56.7,67.3
+246.0,340.0,18.9,24.6,10.8,3.82,33.1,105.0,35.9,89.8,41.0
+42.2,73.0,19.3,56.2,50.5,5.62,67.9,1778.0,1.0,20.9,4.33
+105.0,139.0,30.2,38.2,16.8,2.67,84.3,262.0,1.0,13.6,2.76
+552.0,866.0,23.1,41.4,13.5,1.0,47.0,94.7,2.33,49.1,12.0
+965.0,1459.0,11.9,23.7,18.8,26.9,93.9,1275.0,2.19,35.9,7.37
+365.0,552.0,21.7,41.8,30.2,2.67,10.2,100.0,1.32,33.4,10.3
+223.0,313.0,15.4,77.0,29.4,3.65,70.4,1762.0,1.54,17.5,5.38
+63.2,110.0,40.7,343.0,78.4,1.0,85.1,255.0,3.4,37.5,36.2
+1165.0,1731.0,30.8,42.2,22.7,4.57,34.3,209.0,3.4,20.7,3.68
+131.0,175.0,11.2,17.6,7.23,1.0,32.8,39.2,1.45,32.8,15.0
+244.0,343.0,63.2,160.0,37.5,1.17,75.0,189.0,1.0,15.5,7.3
+12.6,25.9,13.7,46.1,30.5,4.53,120.0,359.0,15.5,62.6,26.7
+655.0,1027.0,33.1,30.5,14.2,18.3,54.7,1499.0,3.02,10.7,1.32
+253.0,340.0,40.0,441.0,106.0,1.0,147.0,349.0,2.05,24.4,4.96
+71.7,114.0,1.65,2.94,22.1,3.68,79.1,178.0,2.02,7.1,5.0
+1186.0,1762.0,35.5,42.9,48.3,2.39,73.0,253.0,1.0,31.9,12.6
+114.0,196.0,10.7,22.3,37.2,7.5,35.9,267.0,2.71,60.4,23.7
+528.0,784.0,10.5,26.4,21.5,1.0,28.4,82.0,18.4,38.5,10.5
+302.0,445.0,7.64,6.26,4.45,10.0,52.8,1358.0,1.29,33.4,8.2
+51.9,63.2,18.6,41.0,28.1,24.8,63.8,914.0,8.66,34.0,12.6
+437.0,621.0,39.2,61.0,7.91,1.0,52.8,51.9,1.98,13.9,6.26
+44.9,58.8,17.0,115.0,40.3,2.94,120.0,302.0,10.3,38.9,7.17
+79.9,71.7,15.8,61.0,27.4,1.75,21.3,110.0,2.31,16.7,2.11
+93.9,145.0,11.8,410.0,62.6,4.96,91.4,223.0,33.1,79.9,20.9
+308.0,453.0,28.1,146.0,42.2,3.05,61.0,154.0,1.22,21.3,4.18
+227.0,449.0,24.1,94.7,35.9,21.1,67.9,2788.0,2.5,37.2,4.78
+126.0,154.0,33.4,42.2,9.82,23.9,122.0,1446.0,2.71,13.5,5.47
+71.7,94.7,14.7,53.8,13.1,2.81,97.3,316.0,2.13,23.5,9.31
+39.6,55.7,9.56,248.0,28.1,12.1,133.0,1358.0,1.7,53.3,12.6
+743.0,1134.0,14.5,267.0,76.4,1.04,24.1,107.0,7.84,49.1,113.0
+104.0,139.0,12.3,40.3,15.5,1.0,17.8,107.0,1.0,49.1,6.61
+956.0,1420.0,10.6,20.5,12.1,3.46,43.7,202.0,1.42,61.5,16.5
+229.0,294.0,10.8,35.5,29.7,6.85,24.6,67.3,1.3,29.7,7.77
+453.0,573.0,12.3,129.0,44.1,7.99,143.0,441.0,5.73,46.1,14.5
+355.0,505.0,8.98,164.0,18.9,1.83,175.0,519.0,1.45,12.1,11.7
+547.0,820.0,13.3,24.1,18.6,4.22,46.1,189.0,15.4,44.9,23.9
+153.0,231.0,13.7,20.7,31.6,2.25,76.4,274.0,1.13,19.5,3.4
+178.0,289.0,8.13,231.0,31.6,20.0,64.4,965.0,1.03,23.7,6.49
+179.0,204.0,10.3,135.0,15.1,51.9,276.0,2996.0,14.5,41.0,8.2
+445.0,667.0,20.9,23.3,23.9,2.31,26.4,53.3,2.46,12.4,6.55
+922.0,1382.0,13.3,17.3,8.43,3.34,50.5,160.0,1.0,59.9,5.42
+13.9,18.3,16.4,20.9,6.98,1.03,23.5,48.3,1.64,25.9,3.65
+302.0,445.0,18.6,30.0,67.9,4.1,41.0,186.0,1.07,38.9,12.2
+1075.0,1540.0,13.6,110.0,21.9,12.0,119.0,4573.0,1.0,7.17,1.14
+193.0,136.0,9.91,198.0,35.2,3.59,47.0,204.0,2.59,33.7,5.62
+167.0,211.0,10.8,104.0,31.6,37.9,122.0,3555.0,2.84,36.5,6.32
+276.0,433.0,11.5,16.8,8.58,1.35,26.9,124.0,1.0,28.9,120.0
+262.0,365.0,12.2,30.0,37.2,87.4,223.0,3429.0,1.0,17.0,6.79
+274.0,375.0,1.26,322.0,40.0,1.0,23.9,85.8,2.81,10.0,4.14
+359.0,542.0,23.1,81.3,25.3,1.0,45.3,131.0,5.19,56.2,90.6
+382.0,588.0,22.1,27.6,5.73,10.6,119.0,1611.0,1.0,32.8,4.29
+1310.0,1963.0,14.5,103.0,41.0,9.22,44.5,973.0,6.61,17.8,51.9
+77.0,94.7,11.0,16.7,32.8,1.0,39.6,60.4,1.08,30.8,8.13
+189.0,284.0,16.8,58.8,25.9,18.4,69.2,1144.0,1.0,19.6,7.37
+615.0,965.0,20.9,11.4,10.0,1.0,30.2,29.7,1.65,31.1,1.0
+418.0,638.0,40.0,49.1,50.9,5.05,161.0,523.0,1.0,11.0,1.1
+225.0,340.0,10.5,19.8,61.5,1.0,85.8,137.0,1.17,26.9,6.79
+181.0,271.0,13.8,9.56,20.2,16.0,204.0,4491.0,2.5,31.3,67.9
+63.2,79.9,22.7,83.5,42.6,9.65,93.1,1747.0,1.3,31.1,7.43
+389.0,426.0,36.8,119.0,23.1,1.0,36.8,87.4,12.0,43.7,20.9
+457.0,685.0,6.55,34.9,25.7,1.23,108.0,223.0,1.0,25.5,81.3
+39.2,43.3,72.3,147.0,21.3,24.6,112.0,542.0,2.55,9.73,9.82
+209.0,311.0,6.79,49.6,19.3,16.5,178.0,191.0,3.75,31.1,21.7
+667.0,1000.0,14.2,16.0,10.6,2.81,22.5,54.7,1.0,27.1,12.9
+32.5,43.7,11.3,121.0,17.8,24.1,138.0,3960.0,2.41,16.7,6.21
+70.4,108.0,20.2,19.5,20.5,16.3,54.7,947.0,1.0,15.7,3.31
+183.0,271.0,6.15,215.0,19.1,1.0,22.1,3.65,26.7,69.8,92.2
+487.0,723.0,10.7,40.3,30.5,1.0,89.0,163.0,1.07,36.2,10.5
+1582.0,2308.0,45.7,48.7,11.8,2.37,77.7,259.0,7.37,40.7,5.05
+49.1,103.0,21.3,15.4,5.28,26.9,75.7,1065.0,4.33,44.9,7.99
+292.0,407.0,19.1,47.4,13.9,7.43,42.2,300.0,5.0,28.4,9.91
+308.0,461.0,17.5,11.4,10.2,5.73,131.0,3398.0,1.0,13.6,7.91
+111.0,168.0,14.7,7.99,7.77,1.0,20.4,45.3,1.0,10.2,5.19
+337.0,552.0,19.8,36.5,25.0,1.0,111.0,223.0,1.98,12.9,4.66
+117.0,142.0,18.1,14.7,9.82,5.62,89.0,221.0,2.76,15.1,3.52
+375.0,547.0,13.8,87.4,14.9,1.0,153.0,237.0,2.0,25.9,3.92
+365.0,673.0,63.8,139.0,23.5,2.69,59.9,184.0,1.0,46.1,7.3
+183.0,267.0,13.3,16.7,2.41,1.15,28.9,88.2,1.0,18.9,1.14
+85.1,130.0,13.6,12.9,12.6,2.74,21.9,179.0,1.25,22.1,8.82
+93.1,138.0,9.31,362.0,89.8,4.57,62.6,191.0,2.89,34.0,9.39
+193.0,279.0,27.9,40.7,10.4,2.0,69.2,165.0,5.47,16.3,8.13
+22.9,35.5,16.5,21.1,23.3,1.0,67.9,189.0,2.31,35.5,12.0
+392.0,557.0,16.4,196.0,14.5,1.61,61.5,172.0,5.05,50.0,7.23
+965.0,1472.0,2.17,16.0,46.1,1.17,39.6,130.0,1.0,16.5,3.89
+717.0,1114.0,51.4,61.5,15.1,2.05,88.2,257.0,1.23,33.7,1.84
+193.0,279.0,20.4,20.7,6.79,9.39,48.7,982.0,1.0,17.9,9.73
+382.0,496.0,16.0,50.0,25.3,4.29,80.6,233.0,1.0,10.5,2.15
+246.0,343.0,10.8,117.0,40.7,3.72,96.5,233.0,1.57,12.4,9.65
+418.0,626.0,9.22,71.0,28.1,1.88,108.0,276.0,1.0,8.9,13.9
+227.0,322.0,20.4,11.5,10.9,3.22,49.1,131.0,1.0,15.7,9.22
+137.0,233.0,30.0,83.5,70.4,3.92,48.7,157.0,2.27,28.4,3.79
+542.0,777.0,15.7,25.9,17.9,1.46,52.3,138.0,1.0,31.6,14.6
+168.0,257.0,22.1,90.6,37.5,1.0,56.7,75.0,1.98,28.4,1.06
+262.0,368.0,4.33,17.8,62.1,1.0,34.6,142.0,1.0,17.9,3.08
+237.0,382.0,19.8,16.1,16.7,24.8,79.1,874.0,35.2,153.0,57.3
+292.0,478.0,45.3,81.3,20.9,2.97,32.2,55.2,23.3,69.2,27.6
+505.0,704.0,1.47,262.0,36.8,5.0,85.8,407.0,1.0,19.5,59.9
+223.0,368.0,6.79,33.7,22.5,4.87,34.0,137.0,1.06,10.6,10.6
+170.0,253.0,15.4,15.8,9.39,10.1,57.8,1778.0,1.39,31.6,13.2
+292.0,400.0,19.8,57.3,44.1,23.5,172.0,1027.0,1.0,18.6,1.96
+47.4,42.9,21.7,28.4,19.5,4.37,34.0,65.5,3.55,34.6,4.45
+99.1,158.0,20.0,18.3,3.55,39.6,133.0,4614.0,1.0,13.2,1.0
+176.0,191.0,20.5,23.7,5.73,1.35,23.9,42.6,1.12,10.3,1.0
+898.0,1298.0,41.8,38.2,10.0,2.17,59.4,135.0,4.83,47.4,7.77
+217.0,305.0,11.8,45.3,65.5,9.22,130.0,449.0,6.79,47.4,7.7
+403.0,621.0,16.4,115.0,21.7,13.5,70.4,1512.0,3.92,9.56,9.14
+157.0,196.0,35.5,127.0,52.8,25.0,167.0,973.0,13.6,53.8,22.3
+461.0,750.0,13.7,62.6,13.8,1.0,54.2,123.0,1.6,16.3,3.37
+813.0,1155.0,11.1,75.7,43.3,1.0,83.5,255.0,1.08,20.7,4.83
+365.0,533.0,2.23,6.04,26.9,1.0,23.5,82.0,6.61,43.7,9.47
+221.0,328.0,30.2,46.6,16.3,2.81,28.6,69.2,1.0,25.7,8.74
+115.0,173.0,35.9,509.0,62.1,1.63,18.6,73.7,2.25,41.8,8.58
+1395.0,2110.0,23.3,33.4,5.57,2.48,19.8,103.0,6.92,48.3,25.7
+74.3,141.0,81.3,179.0,34.3,1.0,40.3,136.0,2.31,37.5,7.37
+542.0,813.0,14.6,18.1,18.3,4.45,127.0,1843.0,3.92,15.7,4.61
+365.0,533.0,16.1,50.5,23.7,3.89,70.4,186.0,1.0,10.0,3.08
+153.0,235.0,37.9,146.0,43.3,4.1,198.0,533.0,1.51,17.0,2.84
+1395.0,2017.0,2.02,75.0,13.5,1.0,32.2,66.1,29.4,82.8,62.6
+1554.0,2371.0,12.6,183.0,20.2,2.55,82.8,233.0,1.0,26.4,7.17
+150.0,239.0,9.47,89.8,20.2,36.2,147.0,2690.0,1.78,27.4,12.9
+71.0,80.6,5.73,1.54,24.6,1.0,153.0,418.0,1.0,13.5,5.94
+599.0,828.0,3.72,25.7,16.8,16.3,196.0,143.0,3.34,24.1,13.3
+172.0,204.0,17.6,16.0,13.9,1.0,31.9,53.3,1.0,19.6,7.43
+72.3,94.7,14.2,83.5,31.6,11.0,122.0,337.0,17.8,65.5,27.6
+244.0,352.0,8.43,108.0,25.0,2.02,59.4,213.0,1.86,21.1,2.84
+392.0,528.0,15.0,16.3,1.26,2.15,41.4,78.4,1.0,16.0,3.22
+202.0,271.0,10.2,31.9,41.4,1.88,73.7,292.0,2.55,25.0,6.85
+274.0,422.0,33.1,235.0,54.7,1.0,44.9,110.0,3.65,36.8,5.52
+158.0,259.0,9.47,32.2,19.5,3.62,52.3,1075.0,1.0,69.8,5.38
+632.0,1000.0,14.6,41.8,13.8,6.92,132.0,1176.0,4.03,17.0,11.3
+231.0,352.0,14.1,21.7,7.64,1.0,115.0,229.0,2.13,19.5,15.8
+1104.0,1554.0,14.9,119.0,21.5,2.33,119.0,403.0,1.0,41.8,5.0
+253.0,410.0,59.9,101.0,23.3,1.0,22.9,99.1,3.31,52.3,11.1
+281.0,426.0,14.5,54.7,16.1,17.0,59.4,858.0,1.96,26.9,6.49
+248.0,375.0,11.2,28.1,78.4,1.29,98.2,253.0,1.0,8.13,2.76
+59.4,99.1,20.7,41.0,12.4,17.9,93.9,573.0,1.98,53.8,10.5
+4.45,11.7,7.84,13.2,33.7,1.11,32.2,12.7,1.55,61.0,14.3
+29.2,22.1,3.34,1.76,18.3,20.5,58.8,898.0,1.0,27.9,8.28
+437.0,588.0,11.0,49.1,27.1,3.34,26.9,108.0,13.8,61.0,13.5
+188.0,235.0,13.8,19.1,13.8,2.84,79.1,337.0,3.68,16.1,7.77
+365.0,528.0,10.4,26.7,24.1,4.57,41.0,1700.0,1.0,28.6,7.43
+121.0,150.0,17.3,154.0,58.3,2.86,32.8,165.0,1.0,38.9,16.0
+300.0,400.0,29.2,389.0,173.0,1.0,64.9,248.0,2.23,21.5,7.64
+207.0,294.0,15.4,21.3,5.88,5.28,186.0,474.0,1.42,26.2,4.87
+246.0,349.0,8.74,66.7,14.9,4.26,25.5,198.0,4.14,14.9,50.0
+496.0,770.0,20.2,26.9,9.14,13.0,117.0,2525.0,1.0,28.9,2.92
+1472.0,2110.0,15.3,2.37,9.56,1.61,18.3,60.4,1.73,42.9,69.2
+47.4,59.9,38.9,375.0,57.8,2.48,67.3,178.0,3.89,26.7,10.9
+757.0,1144.0,2.62,542.0,55.7,3.19,54.2,137.0,1.0,31.1,3.62
+189.0,297.0,2.17,11.8,14.9,4.7,71.7,1446.0,1.86,48.3,12.3
+621.0,965.0,28.1,91.4,36.8,3.96,19.5,89.0,2.21,16.0,3.85
+135.0,241.0,11.4,48.7,14.5,6.67,205.0,704.0,1.03,11.4,1.0
+355.0,519.0,4.91,157.0,20.2,1.0,14.3,123.0,1.89,23.3,2.71
+255.0,403.0,46.1,52.3,5.19,1.0,107.0,229.0,1.81,30.0,4.87
+63.2,62.1,17.5,12.7,8.43,2.53,9.82,62.6,3.55,12.4,7.3
+141.0,193.0,45.7,54.7,21.9,17.8,137.0,2436.0,1.0,23.7,4.66
+626.0,1027.0,11.1,27.4,5.28,1.64,50.0,69.2,1.12,10.2,8.98
+939.0,1382.0,10.9,15.8,13.6,6.67,57.8,308.0,2.71,18.3,6.49
+1018.0,1420.0,11.8,23.5,5.05,5.0,179.0,542.0,1.05,22.5,13.0
+24.4,18.4,3.68,1.67,12.2,8.13,32.5,179.0,2.09,18.8,3.43
+382.0,615.0,20.9,16.8,1.0,1.33,20.0,61.5,1.45,13.0,4.57
+302.0,461.0,8.06,14.5,1.0,1.0,41.8,124.0,1.73,9.82,2.44
+32.5,40.3,8.13,161.0,52.8,1.37,71.0,235.0,2.97,17.9,4.45
+110.0,157.0,22.3,151.0,56.7,34.6,167.0,1055.0,1.45,17.2,7.77
+965.0,1370.0,14.2,15.8,16.7,13.0,78.4,302.0,1.0,22.5,9.22
+410.0,583.0,12.9,13.8,1.0,1.72,13.1,55.7,1.78,25.5,1.0
+1963.0,2714.0,13.5,25.0,10.5,2.59,44.9,188.0,34.6,71.7,20.0
+1433.0,2072.0,14.6,29.4,13.8,2.71,44.1,102.0,4.53,34.0,8.51
+215.0,362.0,7.3,18.1,35.2,3.02,25.9,172.0,1.35,20.9,5.67
+297.0,505.0,19.6,52.3,32.2,44.5,109.0,1370.0,2.92,24.4,8.58
+225.0,368.0,4.0,20.5,8.51,2.23,65.5,255.0,8.66,34.9,5.67
+43.7,55.7,18.3,96.5,27.6,1.0,42.6,69.2,14.3,42.9,23.5
+193.0,262.0,60.4,120.0,38.2,28.6,143.0,5989.0,13.5,42.6,17.2
+2329.0,3278.0,11.2,44.5,17.3,1.0,30.8,37.5,1.0,21.9,15.0
+538.0,874.0,11.0,39.6,17.6,2.86,129.0,248.0,2.57,46.1,14.5
+225.0,294.0,13.2,23.5,6.79,4.07,155.0,519.0,2.11,16.3,1.01
+25.9,64.9,43.3,55.7,7.57,22.9,66.1,931.0,14.2,40.7,19.1
+396.0,710.0,26.9,215.0,51.9,6.32,41.0,1446.0,33.7,110.0,56.2
+170.0,248.0,12.6,24.6,33.7,5.83,43.7,1104.0,1.0,22.9,1.39
+132.0,189.0,22.1,85.8,19.1,1.68,43.7,178.0,1.72,36.8,3.72
+1685.0,2480.0,16.0,15.7,4.87,8.98,46.6,1395.0,1.0,22.7,1.6
+142.0,205.0,1.27,13.1,32.8,1.29,70.4,127.0,1.41,31.6,12.3
+241.0,362.0,17.8,30.0,15.3,1.0,18.9,50.5,3.22,17.6,9.47
+523.0,813.0,16.3,30.8,18.9,3.19,22.9,64.4,1.11,19.3,3.75
+74.3,120.0,19.1,115.0,15.0,1.18,42.2,118.0,1.0,22.9,11.3
+284.0,426.0,17.8,16.4,11.7,1.0,47.4,66.1,11.1,74.3,20.0
+59.4,59.9,7.5,160.0,10.8,2.59,37.5,1310.0,2.62,12.6,3.85
+262.0,368.0,55.7,137.0,18.1,1.0,83.5,193.0,2.97,20.5,7.57
+422.0,655.0,2.35,466.0,42.9,23.9,92.2,2813.0,1.65,31.6,6.79
+86.6,146.0,43.7,38.9,3.92,1.0,77.0,109.0,1.0,13.5,2.69
+248.0,389.0,7.17,20.0,23.9,3.92,63.8,328.0,6.98,48.3,37.5
+223.0,302.0,27.1,170.0,37.5,2.5,63.2,130.0,1.0,28.9,7.04
+106.0,113.0,12.3,71.0,40.0,1.0,25.5,46.1,1.0,15.1,5.42
+125.0,184.0,2.33,5.14,5.57,3.34,47.4,146.0,1.0,26.7,5.88
+181.0,213.0,11.9,53.3,10.6,1.23,145.0,325.0,1.7,19.8,8.28
+567.0,806.0,18.8,41.0,18.6,1.13,31.6,115.0,4.49,22.3,12.3
+2436.0,3398.0,11.8,13.0,5.23,1.0,26.9,126.0,3.72,15.8,10.1
+340.0,491.0,11.9,22.1,9.06,9.73,70.4,2054.0,1.0,16.4,4.96
+453.0,685.0,9.91,15.0,10.8,9.82,109.0,322.0,1.55,10.6,7.99
+131.0,200.0,14.6,16.1,12.3,12.0,191.0,1731.0,2.48,20.7,9.82
+109.0,155.0,9.73,94.7,21.5,6.49,38.9,141.0,1.0,44.9,4.45
+5.78,17.6,8.66,50.9,40.0,1.61,50.5,158.0,1.35,17.8,10.6
+1794.0,2690.0,24.6,24.4,14.1,1.0,50.9,52.8,3.79,18.9,13.1
+305.0,478.0,25.9,34.0,4.41,1.43,35.2,54.7,1.0,34.9,10.6
+661.0,947.0,57.8,58.8,6.98,12.9,58.3,1433.0,2.84,9.73,2.64
+1981.0,2763.0,79.9,594.0,141.0,1.5,39.2,217.0,5.88,16.8,7.7
+59.9,98.2,6.38,47.4,20.7,4.57,41.0,1176.0,1.05,32.2,8.51
+835.0,1208.0,12.0,20.7,6.44,5.14,204.0,594.0,1.83,25.7,7.5
+698.0,1144.0,2.25,13.8,10.5,1.0,40.7,118.0,20.5,73.0,42.9
+170.0,207.0,3.19,13.2,28.4,2.29,100.0,276.0,3.68,32.2,8.2
+74.3,89.0,30.8,50.5,61.0,3.49,95.6,300.0,14.3,39.2,18.8
+253.0,355.0,7.3,20.4,15.7,1.0,15.0,28.4,6.98,48.3,259.0
+196.0,281.0,13.9,39.6,17.0,1.0,27.1,87.4,1.0,26.2,9.47
+63.2,86.6,14.2,13.6,7.43,1.11,22.7,67.3,5.28,31.3,15.7
+441.0,673.0,13.2,14.9,13.8,23.9,53.3,991.0,9.56,32.8,145.0
+42.2,45.3,16.3,98.2,36.8,21.5,114.0,2864.0,1.0,18.9,7.64
+279.0,349.0,8.51,30.5,10.3,31.1,90.6,2329.0,5.28,34.6,151.0
+337.0,509.0,15.0,106.0,30.5,2.04,149.0,389.0,2.35,23.7,13.8
+9.56,11.4,21.5,112.0,58.8,2.13,65.5,179.0,2.89,31.9,8.2
+294.0,400.0,53.8,80.6,21.9,1.0,27.6,73.0,8.82,50.0,16.4
+117.0,151.0,14.7,77.7,23.3,2.53,32.2,85.1,2.02,12.5,7.57
+710.0,1084.0,13.6,13.2,1.01,4.96,13.2,29.2,1.0,25.5,12.1
+528.0,828.0,15.0,12.5,1.0,1.06,53.8,119.0,2.57,22.7,2.64
+75.7,111.0,14.3,79.9,23.3,3.82,42.9,204.0,18.6,49.1,15.8
+42.9,71.7,23.7,302.0,106.0,2.25,56.7,153.0,3.08,57.8,11.3
+253.0,375.0,30.0,47.8,14.2,2.62,48.3,165.0,5.67,16.7,5.05
+264.0,457.0,3.85,14.1,41.4,1.0,39.6,89.8,1.79,26.2,3.43
+362.0,542.0,11.5,17.3,27.6,1.96,54.2,65.5,1.27,23.7,5.52
+235.0,334.0,17.8,13.8,14.1,4.07,102.0,349.0,2.48,11.9,1.0
+34.6,41.0,35.5,178.0,57.3,15.3,62.1,1055.0,2.09,18.4,8.82
+127.0,219.0,30.0,50.5,14.9,2.79,18.6,73.0,3.13,28.1,6.26
+267.0,362.0,18.1,44.1,19.1,1.0,19.6,63.2,2.17,27.1,7.43
+62.6,63.8,4.83,142.0,26.2,1.32,79.1,308.0,3.25,38.9,9.73
+372.0,599.0,10.9,107.0,17.9,1.0,36.5,79.1,4.87,30.8,9.91
+1084.0,1611.0,18.6,11.4,12.5,1.0,19.1,111.0,3.25,10.6,6.04
+2738.0,3889.0,11.3,86.6,13.3,19.1,64.4,1075.0,3.72,30.0,6.55
+241.0,368.0,16.4,300.0,69.2,2.97,43.7,120.0,12.7,34.0,107.0
+1241.0,1794.0,11.3,78.4,19.5,1.79,15.0,30.8,3.22,21.7,8.66
+43.3,73.0,13.7,42.6,101.0,2.81,103.0,362.0,2.02,16.0,9.73
+72.3,90.6,64.4,158.0,25.0,4.49,78.4,248.0,12.4,38.5,17.9
+661.0,1037.0,10.3,77.7,14.1,1.54,20.5,60.4,3.43,18.1,4.91
+292.0,457.0,43.7,334.0,92.2,2.94,69.2,227.0,1.3,13.9,4.07
+91.4,133.0,11.7,112.0,39.6,1.0,28.1,77.0,19.8,55.7,17.9
+130.0,155.0,41.0,67.9,18.1,7.99,33.7,111.0,2.11,15.7,3.96
+111.0,143.0,8.35,16.1,39.6,10.2,58.8,1963.0,82.8,112.0,25.9
+30.5,30.5,16.5,20.0,3.16,1.65,27.1,828.0,4.45,31.9,59.4
+319.0,422.0,5.78,89.0,38.5,2.0,50.0,195.0,1.0,40.0,4.96
+578.0,906.0,10.6,139.0,26.9,9.82,66.1,1554.0,1.76,20.2,11.0
+449.0,644.0,5.0,111.0,18.3,2.59,84.3,172.0,1.0,15.4,3.25
+117.0,213.0,15.3,158.0,44.1,3.13,161.0,375.0,12.6,43.3,16.4
+615.0,939.0,11.4,63.8,14.9,21.9,67.3,1433.0,1.0,20.2,17.0
+313.0,441.0,18.1,36.2,20.7,5.23,22.5,195.0,3.89,19.6,13.6
+77.7,98.2,26.4,51.9,36.8,4.1,75.7,205.0,4.1,28.4,8.66
+153.0,225.0,14.5,12.5,11.5,1.0,31.1,30.5,1.0,26.7,5.94
+368.0,538.0,19.3,40.7,14.2,3.08,62.1,1554.0,1.0,19.1,7.43
+349.0,533.0,18.1,17.6,12.0,6.15,46.1,149.0,6.92,29.4,167.0
+1046.0,1486.0,18.9,18.1,15.5,1.86,31.3,113.0,1.0,17.6,6.98
+334.0,533.0,31.9,41.8,1.86,1.0,22.5,22.9,1.33,44.5,11.7
+922.0,1407.0,28.4,34.9,12.1,14.6,50.0,604.0,1.35,15.1,15.3
+90.6,104.0,3.96,10.9,17.8,51.9,213.0,7041.0,1.0,16.8,9.22
+1018.0,1486.0,13.1,23.9,25.9,5.42,44.9,1794.0,2.35,15.3,13.5
+205.0,289.0,16.5,71.0,40.0,2.25,68.5,165.0,2.55,30.2,1.0
+213.0,331.0,3.62,289.0,59.9,1.0,28.6,55.2,1.33,8.66,6.26
+165.0,246.0,13.6,8.06,15.8,1.0,28.4,136.0,1.0,24.4,4.18
+200.0,269.0,13.8,18.8,21.9,1.53,119.0,389.0,1.0,44.9,12.0
+914.0,1420.0,18.1,127.0,49.6,1.02,48.7,167.0,2.86,30.2,20.0
+143.0,281.0,19.5,34.6,8.82,1.86,196.0,368.0,1.98,66.7,9.06
+142.0,253.0,13.1,13.8,7.5,2.62,42.2,88.2,1.19,44.5,5.94
+229.0,328.0,17.3,16.0,1.04,7.37,44.1,1358.0,3.28,30.5,7.84
+1778.0,2503.0,10.6,111.0,23.3,10.3,142.0,1946.0,1.0,35.5,1.0
+85.8,127.0,26.9,39.2,12.3,16.3,52.3,1382.0,2.31,23.7,9.65
+227.0,322.0,9.14,20.4,13.5,1.76,62.1,158.0,1.98,23.7,12.4
+319.0,414.0,13.7,1.0,14.9,1.0,163.0,276.0,1.0,21.9,10.3
+588.0,914.0,8.35,117.0,30.2,2.15,27.4,150.0,36.2,73.0,29.7
+223.0,313.0,3.31,16.8,18.9,1.43,60.4,153.0,2.92,37.2,6.21
+1252.0,1747.0,7.57,7.17,33.7,3.96,69.2,196.0,1.31,27.1,2.46
+221.0,269.0,32.8,11.2,30.0,9.73,85.1,1611.0,1.36,14.5,8.51
+414.0,615.0,13.8,25.7,17.5,3.72,55.2,237.0,6.85,32.8,23.7
+209.0,302.0,23.7,17.6,5.23,11.3,102.0,2110.0,3.96,26.2,1.0
+491.0,750.0,21.3,15.3,9.65,5.14,117.0,407.0,3.46,47.0,5.14
+965.0,1554.0,5.67,57.8,24.4,3.65,73.7,255.0,1.13,37.5,2.76
+359.0,594.0,10.0,10.6,1.0,1.0,41.4,117.0,9.14,43.7,34.9
+1877.0,2690.0,23.1,27.6,4.74,9.22,77.7,322.0,1.0,22.9,14.1
+292.0,433.0,56.7,123.0,55.7,6.04,239.0,1596.0,1.39,31.3,4.57
+151.0,183.0,47.8,37.5,5.78,1.0,30.0,30.5,1.0,15.8,4.18
+1055.0,1512.0,4.83,8.98,20.5,5.14,69.8,1407.0,1.0,36.5,10.0
+250.0,362.0,19.6,85.1,27.4,23.7,82.0,1596.0,4.1,55.7,9.91
+101.0,153.0,16.1,29.4,6.04,3.13,58.8,198.0,3.4,20.7,7.77
+136.0,179.0,14.5,22.5,19.5,1.0,44.5,102.0,1.0,18.9,6.98
+32.5,34.0,10.2,26.7,31.9,47.8,147.0,1999.0,1.47,27.9,10.8
+866.0,1208.0,17.3,31.9,32.5,2.09,18.6,692.0,1.0,23.5,3.52
+170.0,231.0,41.4,108.0,29.7,3.85,75.7,225.0,1.21,24.6,3.96
+120.0,253.0,10.3,69.8,17.0,5.73,34.3,1046.0,1.0,31.1,2.74
+184.0,259.0,5.38,131.0,23.7,11.0,50.5,1114.0,13.8,71.7,24.1
+44.1,40.7,12.7,57.3,18.6,1.0,52.8,72.3,1.0,16.4,4.07
+205.0,300.0,34.0,101.0,66.7,1.78,40.0,136.0,2.07,22.3,7.84
+100.0,178.0,17.8,165.0,24.8,1.0,82.0,191.0,1.17,40.7,7.57
+158.0,253.0,17.8,21.9,10.0,6.26,90.6,337.0,2.92,25.3,2.19
+1928.0,2788.0,8.58,131.0,46.1,1.0,22.9,78.4,1.88,38.9,2.17
+10.6,45.7,9.82,85.1,13.2,2.09,73.7,906.0,1.95,20.7,2.13
+271.0,426.0,13.1,67.3,26.7,2.79,45.7,165.0,1.75,15.5,4.14
+461.0,661.0,20.9,45.7,26.7,3.0,55.2,104.0,5.38,23.7,11.2
+4.74,4.29,5.83,21.5,14.7,3.62,14.6,26.2,2.79,55.7,8.43
+78.4,193.0,8.74,10.6,6.55,6.04,36.5,2329.0,2.39,13.2,10.8
+308.0,478.0,12.4,205.0,30.8,28.6,132.0,4698.0,2.48,22.3,4.26
+337.0,500.0,7.99,104.0,12.3,1.61,47.4,92.2,1.0,21.5,4.57
+422.0,615.0,8.74,76.4,25.9,7.1,51.4,835.0,2.15,3.59,12.4
+449.0,632.0,13.8,36.2,19.6,12.5,69.2,1009.0,15.4,42.6,18.4
+33.4,27.6,9.82,34.6,15.1,2.33,35.5,204.0,1.04,27.9,26.4
+87.4,94.7,9.91,60.4,18.4,2.21,67.3,165.0,1.0,15.7,10.9
+164.0,241.0,12.1,18.3,14.2,1.0,40.7,89.0,3.55,34.0,3.59
+77.0,114.0,14.1,27.1,15.7,3.16,50.0,2503.0,1.75,17.2,1.0
+98.2,168.0,24.8,55.2,9.06,7.7,54.7,1370.0,1.73,40.3,5.09
+32.5,37.2,46.1,1055.0,352.0,1.75,56.7,164.0,15.0,41.4,10.0
+835.0,1219.0,8.51,49.6,17.9,8.51,126.0,389.0,1.26,41.4,9.39
+103.0,186.0,8.2,189.0,24.8,4.33,22.3,77.0,1.0,31.3,12.3
+117.0,157.0,8.2,16.4,28.1,15.0,101.0,355.0,2.59,44.1,9.91
+1009.0,1540.0,55.2,79.1,10.4,3.05,29.7,698.0,2.07,11.4,3.62
+777.0,1241.0,7.5,84.3,13.8,13.3,69.8,1843.0,6.15,21.9,7.91
+410.0,704.0,5.99,105.0,28.6,3.75,29.2,139.0,1.31,30.8,4.45
+1208.0,1685.0,15.7,13.7,13.8,8.06,50.5,1395.0,2.04,25.0,77.0
+160.0,223.0,1.0,204.0,9.06,1.36,36.2,50.5,2.67,18.9,11.0
+292.0,422.0,18.6,120.0,59.9,3.16,119.0,248.0,3.96,31.9,11.5
+235.0,362.0,2.97,23.3,33.4,1.0,42.9,61.0,1.53,23.1,7.1
+188.0,255.0,41.4,85.8,23.7,1.42,26.4,75.0,1.0,19.3,9.39
+906.0,1433.0,15.1,19.3,4.14,1.33,75.0,147.0,1.91,19.6,10.8
+25.5,24.8,47.4,108.0,57.8,6.67,48.7,319.0,1.0,33.7,9.31
+229.0,325.0,13.7,82.8,21.5,4.29,18.6,62.1,2.79,30.2,1.0
+385.0,610.0,44.1,65.5,28.9,2.13,27.1,61.0,1.04,27.1,10.9
+835.0,1208.0,10.8,15.4,7.64,23.9,70.4,982.0,28.6,50.5,18.3
+92.2,158.0,7.23,125.0,53.3,1.24,90.6,305.0,3.52,14.7,11.5
+276.0,396.0,12.9,19.3,6.67,1.51,108.0,281.0,1.24,24.1,9.91
+9.39,12.0,78.4,165.0,47.4,10.7,56.2,2714.0,3.82,34.0,2.29
+146.0,191.0,22.9,24.8,9.73,20.2,64.9,1114.0,1.0,28.4,17.8
+791.0,1155.0,9.73,109.0,36.2,1.0,50.0,111.0,1.0,15.8,10.1
+1928.0,2690.0,17.2,379.0,175.0,2.94,21.3,68.5,1.58,22.1,2.97
+311.0,441.0,12.9,24.8,26.7,1.0,49.6,82.0,1.83,7.43,3.43
+289.0,422.0,6.44,198.0,24.8,15.3,59.4,1540.0,1.0,21.1,11.1
+33.4,48.7,19.1,37.5,19.8,1.25,42.9,91.4,2.19,20.9,7.91
+528.0,882.0,31.3,610.0,136.0,4.53,34.6,1731.0,1.0,19.1,9.73
+255.0,365.0,18.1,13.7,15.0,7.23,75.7,2267.0,2.69,21.5,13.3
+59.9,73.7,16.5,478.0,158.0,3.65,41.0,221.0,1.0,20.9,7.1
+178.0,308.0,15.4,145.0,25.0,3.19,34.9,158.0,1.0,13.6,10.6
+1310.0,1894.0,16.8,207.0,54.2,5.57,46.1,1625.0,3.62,35.5,41.0
+50.9,103.0,57.3,107.0,8.98,3.19,97.3,246.0,16.1,43.3,18.3
+1370.0,1928.0,7.77,257.0,23.5,9.47,157.0,355.0,1.53,16.7,3.85
+375.0,588.0,13.6,18.4,16.1,1.15,77.0,198.0,18.9,57.8,19.1
+147.0,219.0,12.7,40.0,17.3,5.09,49.6,233.0,1.0,35.5,7.1
+153.0,237.0,16.8,56.2,20.2,1.42,31.1,35.2,3.19,10.2,1.68
+209.0,292.0,25.7,113.0,48.3,2.48,38.5,125.0,4.45,40.7,89.0
+279.0,414.0,12.4,26.9,8.66,4.49,58.3,130.0,4.07,28.9,4.83
+982.0,1433.0,24.6,35.2,5.62,2.46,45.3,217.0,14.2,39.2,9.91
+750.0,1155.0,6.67,103.0,50.5,1.86,28.9,106.0,1.0,44.5,10.0
+519.0,806.0,9.91,73.7,12.2,3.62,89.8,308.0,2.41,24.1,3.34
+170.0,286.0,19.3,3.02,21.3,2.09,25.7,54.7,1.31,30.0,16.3
+244.0,359.0,23.9,22.7,14.5,2.19,44.5,193.0,10.5,30.2,34.0
+594.0,947.0,1.54,403.0,56.2,1.57,52.8,154.0,1.23,29.4,7.5
+50.9,61.0,41.0,109.0,15.0,2.25,56.7,1596.0,37.2,54.2,28.4
+90.6,122.0,60.4,137.0,12.5,3.4,102.0,319.0,2.04,10.2,4.45
+368.0,547.0,31.1,37.9,5.78,1.84,48.3,1134.0,3.59,35.5,5.83
+710.0,1027.0,14.7,11.2,6.1,1.13,51.9,157.0,1.0,22.1,5.78
+89.0,131.0,7.43,90.6,7.7,1.0,31.9,15.1,8.35,31.9,13.9
+523.0,813.0,16.1,5.83,27.4,1.43,149.0,346.0,7.5,61.5,21.7
+211.0,311.0,11.8,17.5,18.1,5.57,82.8,365.0,2.48,47.8,9.82
+441.0,710.0,131.0,111.0,737.0,15.8,71.7,1275.0,3.4,30.5,7.57
+56.2,100.0,14.6,16.1,5.94,1.88,57.8,195.0,1.25,17.5,5.62
+213.0,340.0,12.4,78.4,22.7,1.18,40.0,178.0,3.02,32.2,11.0
+331.0,429.0,4.03,15.8,61.5,5.33,89.0,365.0,4.66,56.7,205.0
+262.0,355.0,34.9,219.0,71.0,1.0,58.3,173.0,2.17,21.1,2.46
+76.4,79.9,36.5,193.0,56.2,1.0,33.1,84.3,5.33,7.5,11.0
+1499.0,2091.0,11.2,173.0,44.5,3.46,160.0,583.0,2.79,22.5,7.04
+50.0,56.7,16.7,13.3,6.73,1.0,15.5,68.5,2.5,14.2,7.37
+225.0,313.0,10.5,89.0,36.2,3.37,69.8,267.0,1.0,27.6,3.34
+225.0,359.0,17.8,15.3,5.38,31.1,85.1,1055.0,1.96,18.9,1.05
+94.7,167.0,15.3,20.5,12.4,3.4,54.2,151.0,1.0,42.6,15.1
+189.0,346.0,25.7,137.0,52.3,8.35,58.8,1499.0,2.17,16.0,11.3
+426.0,661.0,4.78,20.5,46.6,5.42,123.0,241.0,8.66,31.9,2.25
+172.0,286.0,17.8,14.2,1.27,1.0,137.0,267.0,1.54,12.5,1.79
+491.0,704.0,12.1,83.5,26.2,26.4,246.0,8896.0,1.0,16.7,8.82
+311.0,437.0,10.4,253.0,30.8,1.76,130.0,322.0,1.26,8.82,3.02
+34.3,58.8,8.66,14.2,17.5,1.76,25.9,57.3,1.06,21.3,10.7
+1230.0,1762.0,9.73,89.8,17.9,2.59,40.7,78.4,1.0,35.9,8.43
+89.8,141.0,13.6,11.3,2.31,2.29,32.5,66.1,2.04,13.1,4.33
+422.0,557.0,29.2,114.0,40.0,7.5,54.7,1322.0,27.1,120.0,38.2
+173.0,297.0,9.39,17.9,8.51,6.21,71.0,319.0,1.35,18.6,3.65
+302.0,445.0,13.3,25.7,2.53,7.17,90.6,1144.0,1.13,5.62,5.83
+215.0,375.0,4.83,54.7,7.5,1.0,49.1,163.0,2.07,18.9,6.32
+213.0,302.0,16.5,16.4,48.3,1.0,38.5,98.2,1.0,19.3,3.85
+349.0,547.0,9.14,142.0,17.2,1.96,59.9,165.0,4.61,25.5,5.67
+59.4,77.0,10.5,16.0,26.2,2.67,15.7,55.2,1.91,40.3,8.51
+64.9,93.1,7.17,111.0,43.3,2.23,50.5,133.0,4.18,29.2,7.64
+1084.0,1540.0,23.1,60.4,50.0,1.79,43.7,57.3,3.65,40.7,8.74
+279.0,379.0,13.6,13.8,4.49,2.48,69.8,101.0,1.36,46.6,3.89
+170.0,215.0,17.2,24.8,8.58,5.14,121.0,349.0,6.15,14.7,8.9
+107.0,184.0,16.5,297.0,63.8,9.14,48.7,1433.0,20.4,44.9,17.9
+835.0,1322.0,18.4,10.8,8.98,2.25,60.4,205.0,1.09,7.99,1.73
+445.0,615.0,5.88,76.4,19.6,6.67,50.9,264.0,2.23,17.2,4.61
+123.0,181.0,17.3,46.1,25.0,1.07,18.9,104.0,1.0,36.5,13.7
+661.0,1075.0,15.1,21.3,12.1,1.43,23.1,59.4,1.03,5.47,4.29
+403.0,638.0,13.8,31.9,36.2,1.26,29.2,63.8,2.84,12.6,6.1
+168.0,233.0,16.1,61.0,28.6,1.76,35.5,131.0,14.5,45.3,22.7
+311.0,483.0,12.2,9.06,8.58,1.03,63.2,213.0,38.2,74.3,12.6
+1219.0,1827.0,64.4,98.2,10.5,1.0,26.7,85.1,1.27,22.9,20.7
+319.0,491.0,31.1,168.0,34.9,1.39,75.7,129.0,2.48,25.7,8.58
+235.0,316.0,13.5,75.7,16.0,1.86,87.4,204.0,1.0,16.1,10.5
+76.4,125.0,7.37,163.0,15.7,3.0,47.8,142.0,1.0,24.8,5.47
+429.0,667.0,4.07,15.4,25.7,1.0,47.0,87.4,2.79,31.1,49.1
+433.0,610.0,14.7,108.0,51.9,1.57,110.0,269.0,7.23,39.2,10.4
+32.2,70.4,13.7,72.3,17.6,2.02,31.6,82.0,48.3,139.0,59.9
+40.3,46.6,11.3,17.9,5.94,2.92,132.0,279.0,2.23,13.1,5.52
+271.0,418.0,18.3,149.0,38.5,23.7,75.0,1298.0,1.95,23.9,12.0
+313.0,509.0,9.47,34.9,30.2,1.73,33.4,70.4,1.08,23.5,4.29
+286.0,403.0,11.9,80.6,50.9,1.29,98.2,286.0,1.45,41.0,10.7
+248.0,359.0,7.77,83.5,21.5,1.0,24.4,55.7,1.65,18.9,4.78
+64.9,85.1,11.4,106.0,36.2,2.23,145.0,253.0,1.0,11.2,3.43
+1433.0,2072.0,8.13,30.8,79.1,4.87,20.9,163.0,1.09,8.51,7.3
+271.0,418.0,6.98,12.5,29.4,1.0,45.3,64.9,1.1,17.3,9.56
+57.8,91.4,17.2,15.7,6.55,4.91,35.2,122.0,1.32,20.2,4.49
+346.0,594.0,15.7,12.1,19.6,1.0,58.8,158.0,1.78,32.2,4.33
+119.0,157.0,13.5,121.0,40.3,2.69,48.7,172.0,12.2,29.2,38.5
+225.0,355.0,16.4,20.0,9.22,20.5,207.0,3023.0,20.9,84.3,46.6
+111.0,147.0,3.79,10.7,29.7,7.64,50.0,1075.0,2.11,19.8,2.79
+14.6,18.6,18.3,16.3,3.16,4.57,16.7,474.0,6.85,26.2,28.6
+17.2,39.6,15.1,13.5,6.49,5.05,18.6,567.0,15.5,75.0,9.91
+15.8,15.1,3.75,191.0,3.72,7.64,19.6,770.0,12.2,21.1,12.0
+9.39,14.7,8.28,75.0,16.1,16.4,21.5,253.0,12.9,37.5,2.0
+9.82,6.04,2.21,179.0,20.7,26.9,27.4,385.0,10.1,22.5,5.57
+9.65,10.6,38.5,55.2,22.1,5.67,13.0,253.0,11.7,8.66,16.4
+33.7,19.6,8.9,28.4,20.9,6.85,18.8,1134.0,17.8,24.6,5.28
+18.8,19.6,68.5,205.0,17.3,19.3,31.3,305.0,7.17,17.8,5.83
+39.2,17.2,81.3,205.0,29.2,19.8,27.4,346.0,9.73,19.8,19.1
+16.1,15.4,11.7,16.4,9.65,7.3,11.9,519.0,35.5,64.4,21.9
+46.6,12.2,11.4,30.2,63.8,4.83,11.2,594.0,6.92,16.3,6.73
+50.9,24.1,3.05,491.0,79.9,35.2,44.1,547.0,13.5,26.4,11.9
+28.6,20.2,9.31,12.1,3.13,14.1,17.2,583.0,4.29,19.6,73.7
+13.1,40.0,17.8,11.9,4.61,6.32,45.3,1065.0,24.1,44.1,10.0
+48.7,22.5,26.9,514.0,154.0,13.1,21.5,835.0,27.9,78.4,32.5
+37.2,19.5,16.8,16.8,1.68,17.5,31.1,538.0,20.7,46.6,14.3
+11.3,6.21,17.0,13.3,1.23,9.31,14.3,457.0,15.5,29.2,14.2
+47.8,18.1,5.83,47.8,6.55,14.7,19.8,85.8,18.6,47.8,26.4
+17.5,29.4,10.4,14.6,4.03,29.2,35.5,331.0,12.1,25.5,21.5
+38.2,20.5,6.61,17.9,23.9,11.3,27.6,947.0,24.1,47.4,17.8
+2.55,12.4,1.83,200.0,16.7,3.05,15.8,655.0,20.2,36.8,10.7
+52.8,21.3,1.0,21.1,1.21,7.23,19.3,547.0,14.6,31.9,1.0
+41.8,45.3,4.26,157.0,23.9,23.9,43.3,355.0,14.6,26.2,13.8
+67.3,24.8,6.98,16.5,29.7,13.8,45.3,2595.0,5.83,18.6,26.9
+13.7,10.1,2.67,34.0,3.11,11.2,28.6,1981.0,19.3,37.5,26.4
+15.0,39.6,14.9,414.0,77.0,6.61,6.73,400.0,23.3,40.7,77.7
+21.9,18.3,1.0,89.0,5.88,3.89,12.4,491.0,9.06,27.4,16.7
+67.9,40.0,5.38,13.8,63.2,2.07,15.1,723.0,17.6,40.7,17.6
+10.2,13.5,15.0,34.0,26.4,1.73,6.26,106.0,10.5,18.9,25.5
+15.8,22.1,5.09,20.2,44.5,7.77,26.4,599.0,12.5,30.5,23.9
+85.1,106.0,11.9,67.9,11.3,21.1,32.5,389.0,10.0,27.9,13.7
+57.8,16.5,1.93,157.0,13.9,18.6,24.4,491.0,13.1,18.9,19.5
+9.56,24.4,4.91,184.0,17.6,11.2,18.9,874.0,3.37,12.9,112.0
+27.9,27.4,9.14,68.5,13.7,13.0,26.9,528.0,12.4,19.6,10.1
+17.8,17.2,25.0,31.1,2.29,19.3,25.9,311.0,17.3,29.7,18.9
+34.9,15.0,7.1,5.23,21.5,21.3,35.2,583.0,15.1,34.0,25.5
+75.7,17.6,11.1,30.0,5.23,28.6,46.6,225.0,15.4,40.0,18.4
+38.5,16.0,9.47,136.0,29.2,8.98,10.4,170.0,17.9,33.7,17.0
+34.3,36.5,43.7,63.8,19.6,5.38,16.7,331.0,20.5,40.7,9.65
+20.4,15.7,16.0,24.4,5.14,4.78,5.23,164.0,13.1,23.5,11.3
+22.5,19.5,6.32,188.0,14.1,9.82,13.0,673.0,6.32,23.7,105.0
+73.0,24.1,14.3,82.8,3.13,18.9,31.3,385.0,20.0,36.8,13.5
+34.0,10.8,79.1,165.0,16.5,5.83,17.3,267.0,20.5,60.4,93.1
+50.0,25.5,47.4,257.0,20.7,1.0,4.07,188.0,3.82,18.4,89.0
+48.7,25.5,16.1,122.0,67.3,28.6,41.4,538.0,18.3,45.7,15.5
+61.0,25.5,4.87,207.0,46.6,24.1,27.9,382.0,1.0,15.1,96.5
+64.4,33.4,13.5,28.6,1.0,18.9,33.7,403.0,3.85,8.74,73.0
+65.5,29.7,7.37,127.0,20.7,13.0,32.2,626.0,24.4,48.3,24.4
+43.7,13.3,18.3,23.1,6.79,8.35,5.78,200.0,5.57,12.5,15.1
+33.4,23.3,5.38,198.0,66.7,10.6,24.6,685.0,18.1,33.4,8.2
+13.5,10.7,9.39,3.59,29.7,4.91,34.3,227.0,13.7,33.1,12.2
+11.7,4.37,12.7,46.1,22.5,4.96,18.3,914.0,17.0,47.0,17.2
+12.5,19.3,14.3,55.7,32.8,3.05,10.4,274.0,3.4,26.7,114.0
+84.3,35.2,11.2,18.3,63.2,4.33,9.56,325.0,2.41,372.0,26.9
+38.2,15.8,5.67,136.0,18.1,33.1,69.2,379.0,22.9,71.0,43.3
+28.1,9.22,5.94,132.0,18.1,25.5,46.6,557.0,17.6,30.0,13.2
+11.7,8.74,26.9,42.2,15.0,17.3,23.9,474.0,4.57,13.2,21.7
+1.0,3.46,5.83,3.34,3.13,11.7,24.8,352.0,22.3,48.3,18.9
+136.0,48.7,3.43,19.1,25.0,4.49,18.6,274.0,23.9,44.1,5.42
+19.5,13.8,8.74,14.9,24.4,12.5,24.4,632.0,35.5,64.9,18.4
+42.9,12.4,11.0,9.06,4.7,11.8,31.6,305.0,2.07,17.5,82.0
+5.28,5.57,16.3,22.3,18.9,20.7,28.4,466.0,17.0,27.6,14.3
+79.1,50.5,24.6,53.8,40.0,10.7,21.1,445.0,19.1,41.8,10.8
+81.3,16.8,4.14,445.0,62.1,5.33,20.2,1094.0,5.09,23.3,52.3
+32.2,26.9,2.81,2.81,1.65,33.7,56.2,931.0,35.2,46.1,9.31
+40.0,20.0,14.2,85.1,18.9,6.04,12.3,379.0,5.0,15.5,74.3
+19.6,20.2,14.2,14.5,1.51,11.4,13.9,483.0,5.23,15.4,131.0
+50.9,28.1,6.26,235.0,14.5,5.05,13.7,644.0,26.7,42.9,20.9
+41.4,27.1,8.58,36.5,42.2,14.6,27.4,400.0,18.8,57.3,56.2
+58.8,31.9,4.07,14.2,3.96,7.64,11.2,231.0,16.3,39.2,17.5
+64.9,21.1,10.9,63.2,19.5,27.1,41.8,461.0,8.51,20.0,11.7
+62.1,32.8,11.4,18.1,22.7,10.7,47.0,1963.0,6.98,15.3,5.73
+32.2,28.1,20.0,19.6,3.19,8.28,15.3,110.0,23.7,58.3,9.56
+63.8,64.4,2.25,231.0,18.9,18.8,39.6,843.0,17.6,37.9,20.0
+22.1,26.7,3.65,26.4,10.6,14.2,26.4,737.0,30.5,42.9,16.7
+63.2,38.9,10.1,66.7,14.1,7.23,15.3,340.0,3.52,38.2,130.0
+132.0,54.7,10.0,44.1,109.0,13.5,30.0,267.0,27.1,47.0,18.6
+26.9,24.4,22.7,17.2,6.44,21.5,27.6,407.0,16.7,45.7,123.0
+39.2,17.6,59.4,119.0,12.7,16.4,28.6,313.0,54.7,74.3,19.3
+42.9,17.6,1.43,62.1,12.9,18.6,80.6,5523.0,10.2,21.3,15.7
+101.0,100.0,10.5,65.5,27.4,8.2,17.9,449.0,10.0,14.5,4.61
+73.0,23.1,5.42,92.2,14.6,4.26,30.2,991.0,30.8,74.3,36.5
+25.5,23.5,13.6,127.0,17.8,8.13,6.55,302.0,6.21,13.9,57.8
+33.7,16.8,12.5,12.7,16.3,5.52,16.0,264.0,16.8,34.3,2.67
+205.0,71.0,9.06,79.9,16.8,23.9,20.7,441.0,14.2,31.1,20.5
+24.1,28.1,22.7,94.7,36.8,17.9,33.7,400.0,25.9,55.2,31.1
+34.0,21.3,19.1,9.39,5.42,13.8,22.1,478.0,19.6,60.4,36.2
+57.3,23.5,10.7,45.3,52.8,8.82,20.7,1512.0,10.6,24.4,12.7
+55.2,22.3,17.6,22.5,9.39,23.7,27.6,375.0,24.6,53.8,22.5
+77.0,21.1,12.2,22.1,3.13,6.61,22.9,445.0,26.9,38.2,10.3
+59.4,41.4,9.73,14.9,6.15,9.06,20.4,500.0,30.2,56.7,14.5
+9.39,27.9,13.0,22.5,17.5,19.5,26.9,426.0,28.6,36.5,18.6
+16.5,33.4,1.0,403.0,35.5,16.0,33.1,710.0,16.4,29.4,19.5
+61.0,40.7,13.5,14.5,5.83,7.99,13.6,757.0,11.3,23.9,7.37
+63.8,34.9,8.82,85.8,17.5,14.7,26.9,604.0,2.92,16.8,64.4
+45.7,12.1,80.6,90.6,23.3,7.84,15.7,362.0,64.9,100.0,16.5
+39.2,10.0,4.45,15.0,27.6,10.6,17.8,437.0,11.8,28.6,40.3
+120.0,85.8,9.73,114.0,13.3,8.06,15.8,578.0,6.85,21.1,75.7
+5.78,1.01,8.82,60.4,31.1,15.5,31.3,730.0,3.31,15.8,56.2
+35.2,10.4,10.2,10.4,26.4,10.8,26.4,604.0,20.9,48.3,16.5
+19.6,46.6,1.63,37.9,7.5,13.1,19.3,528.0,21.9,60.4,44.5
+34.0,18.8,42.9,89.8,44.9,4.61,17.9,673.0,25.7,49.1,25.5
+47.4,28.9,9.14,19.5,73.7,19.3,27.6,453.0,3.34,20.5,61.5
+44.1,28.4,17.2,22.5,13.5,13.3,20.2,313.0,23.7,33.4,14.5
+119.0,29.4,16.1,15.3,9.82,18.6,28.6,396.0,49.6,64.4,18.8
+53.8,23.9,8.82,97.3,24.6,3.96,7.57,153.0,15.1,28.1,15.7
+164.0,72.3,3.89,11.4,40.7,10.9,29.2,1928.0,25.5,41.4,25.7
+42.2,22.3,1.36,38.5,21.5,24.1,39.6,588.0,20.4,34.0,16.4
+71.0,66.7,4.91,11.4,14.2,5.0,16.0,346.0,18.3,33.4,13.2
+59.9,32.8,12.7,12.5,17.5,39.6,61.0,882.0,32.2,73.0,26.7
+41.4,28.9,15.3,30.2,13.0,18.6,41.0,557.0,4.87,27.1,71.7
+25.9,19.3,13.5,20.0,5.05,15.4,33.1,757.0,27.9,56.2,13.8
+78.4,44.1,16.3,16.5,3.16,94.7,198.0,1055.0,6.67,16.3,17.5
+47.0,57.3,9.39,164.0,52.8,9.31,14.6,638.0,10.0,29.7,9.47
+17.3,28.9,10.2,88.2,9.82,22.7,24.1,328.0,21.9,37.9,14.1
+53.3,19.8,13.2,34.3,22.1,9.56,16.3,638.0,2.33,12.0,53.3
+20.5,15.0,10.3,12.6,29.4,34.0,70.4,1762.0,3.68,17.2,127.0
+55.2,27.4,55.7,131.0,31.1,10.2,20.7,375.0,8.66,23.3,26.9
+84.3,23.1,3.31,311.0,25.5,4.87,10.4,244.0,10.1,29.4,57.8
+135.0,198.0,5.38,120.0,13.7,9.73,23.1,519.0,10.1,26.9,13.9
+25.3,17.5,6.15,126.0,23.7,6.98,18.8,56.7,8.28,14.7,10.2
+42.6,23.3,16.4,40.0,1.75,6.55,10.5,610.0,11.9,25.9,45.7
+71.0,40.7,13.0,157.0,40.3,5.19,11.4,1.0,2.76,21.1,74.3
+62.6,26.4,9.22,15.8,61.5,6.26,9.91,311.0,2.97,17.3,124.0
+51.4,25.5,7.64,77.7,23.1,14.2,22.9,311.0,27.6,44.9,16.4
+63.8,24.6,22.5,12.7,20.7,14.9,26.9,655.0,7.04,23.5,91.4
+73.7,34.9,19.3,85.1,47.4,8.98,20.7,538.0,24.1,30.5,17.0
+46.6,19.3,13.5,37.5,123.0,9.06,14.1,717.0,2.57,20.2,106.0
+45.7,14.9,5.88,14.6,25.0,21.5,36.2,445.0,6.67,15.4,49.6
+86.6,36.5,1.0,461.0,36.8,42.2,54.7,227.0,5.88,13.8,42.6
+30.5,23.1,6.26,157.0,9.91,8.66,20.9,237.0,23.5,36.2,5.33
+35.2,9.14,17.2,12.4,3.62,18.8,34.0,784.0,20.0,39.6,15.1
+211.0,88.2,5.88,205.0,17.9,26.4,34.0,305.0,14.9,41.0,11.8
+43.7,21.5,10.5,29.7,26.2,11.4,19.5,422.0,11.7,39.6,9.22
+19.5,13.8,19.3,14.1,1.27,5.23,33.7,1046.0,32.2,75.0,42.6
+118.0,64.4,35.5,100.0,121.0,21.7,36.2,922.0,1.24,34.0,1.0
+64.4,24.8,91.4,188.0,50.5,1.96,13.8,523.0,4.26,22.5,122.0
+43.7,26.7,49.6,59.9,11.7,11.8,41.4,3523.0,39.6,83.5,72.3
+81.3,39.6,18.6,21.7,4.45,5.47,18.1,67.9,3.28,14.3,70.4
+58.8,28.1,18.9,38.9,43.7,4.96,17.8,562.0,26.9,57.3,20.9
+21.7,18.6,11.1,19.5,12.7,19.6,34.0,305.0,17.6,30.0,12.2
+62.1,27.1,2.62,178.0,28.1,58.3,89.0,1526.0,34.3,63.8,20.9
+24.6,25.5,10.6,18.1,1.31,2.17,31.9,3.02,12.7,30.5,20.5
+6.1,21.3,1.89,196.0,40.3,53.3,93.1,1197.0,20.2,29.7,2.37
+154.0,86.6,34.0,337.0,160.0,25.5,47.4,1486.0,3.28,35.2,231.0
+73.7,34.9,24.4,331.0,70.4,3.96,10.8,426.0,7.57,27.4,20.4
+70.4,37.5,6.55,8.66,6.67,12.3,13.5,300.0,21.7,50.5,12.1
+77.0,26.4,17.8,14.2,13.9,34.0,53.3,491.0,6.44,13.8,10.4
+11.8,22.5,5.73,8.98,12.6,7.1,20.5,947.0,18.3,33.7,20.5
+18.1,22.7,4.07,163.0,12.2,14.1,28.4,610.0,7.3,10.7,4.18
+32.5,25.7,6.55,264.0,61.0,9.22,14.6,523.0,23.1,39.2,18.8
+49.6,46.1,9.06,47.8,25.0,7.37,16.5,441.0,10.1,13.6,6.21
+41.8,23.9,4.53,14.5,32.2,12.3,24.1,441.0,17.9,29.2,12.4
+20.5,32.5,10.1,55.7,18.8,3.68,24.6,311.0,2.25,18.8,68.5
+58.8,17.5,13.6,23.9,2.25,6.15,12.4,264.0,3.02,22.9,85.1
+41.4,26.4,44.9,110.0,24.6,3.72,3.16,667.0,3.08,11.2,51.4
+34.9,16.5,4.33,72.3,25.9,39.6,70.4,1230.0,12.6,30.5,42.2
+20.0,19.1,10.2,14.3,16.7,21.1,19.6,325.0,21.7,38.9,20.5
+179.0,27.9,6.49,10.2,7.91,7.77,10.3,626.0,15.8,22.7,17.0
+51.9,30.2,8.74,96.5,25.3,6.92,15.0,483.0,10.1,28.6,27.4
+92.2,69.8,13.9,17.9,12.9,17.2,27.6,491.0,15.7,34.9,17.9
+48.3,15.7,10.1,87.4,11.0,28.1,49.1,552.0,25.9,46.6,16.8
+85.1,27.9,17.2,437.0,107.0,16.3,27.9,621.0,22.3,39.2,27.9
+36.5,19.8,6.38,14.7,24.8,44.1,183.0,1208.0,7.64,27.9,111.0
+73.7,27.6,11.3,25.7,26.7,18.1,28.9,233.0,4.29,27.6,125.0
+19.3,27.4,13.7,131.0,51.4,11.4,18.1,673.0,5.47,10.4,21.5
+28.9,21.7,11.7,71.0,21.3,13.3,21.5,947.0,27.9,44.5,9.82
+50.9,120.0,27.4,37.5,20.2,20.4,39.2,466.0,7.37,17.2,27.4
+73.0,28.6,14.1,23.3,3.43,379.0,730.0,3854.0,14.9,33.7,16.5
+62.1,27.1,11.9,21.3,8.9,7.17,33.4,1027.0,5.14,8.74,67.9
+34.9,24.8,111.0,221.0,28.6,43.7,71.0,1747.0,22.7,49.1,15.7
+66.1,63.8,9.91,88.2,25.7,6.49,17.9,730.0,18.3,37.9,8.51
+26.9,17.3,6.92,17.9,18.3,6.79,17.3,717.0,26.7,41.4,30.5
+78.4,21.1,8.43,32.2,40.3,5.78,17.9,213.0,10.5,23.7,11.2
+37.5,31.1,16.3,17.5,5.99,5.33,11.0,328.0,21.7,34.6,11.9
+55.2,10.8,6.1,8.06,18.6,12.7,49.1,1252.0,28.9,47.0,24.8
+55.7,24.8,9.31,114.0,15.4,10.2,17.2,414.0,17.2,32.5,13.1
+49.1,18.4,14.6,23.7,6.49,4.7,12.7,136.0,3.92,25.0,127.0
+61.5,21.1,11.0,13.6,33.7,5.57,45.3,1197.0,17.8,35.9,15.5
+3.37,11.7,21.1,54.7,5.52,21.7,27.1,1104.0,12.6,36.8,105.0
+181.0,93.9,8.74,147.0,19.3,18.8,18.6,355.0,7.57,15.7,73.0
+16.0,25.7,16.1,82.0,14.5,4.83,12.5,319.0,28.6,47.4,8.13
+27.1,41.8,13.3,18.1,15.8,7.43,16.5,562.0,30.5,48.3,20.5
+131.0,72.3,9.47,17.5,22.5,9.31,15.1,533.0,9.39,32.8,178.0
+65.5,31.1,15.1,17.2,2.64,21.9,29.7,547.0,26.7,44.5,17.3
+6.61,18.8,1.14,141.0,12.3,22.5,22.7,437.0,18.4,23.1,10.5
+27.6,18.6,17.6,13.2,15.7,18.8,37.5,505.0,6.1,21.7,21.7
+71.0,38.9,5.62,7.37,5.73,8.66,19.3,939.0,12.7,30.2,15.0
+98.2,36.8,13.9,31.1,47.4,18.6,27.6,346.0,17.5,35.5,19.6
+50.5,23.5,7.77,10.6,41.8,9.56,19.6,644.0,24.1,53.8,15.7
+112.0,47.8,2.84,193.0,39.6,4.26,14.6,828.0,10.1,18.8,70.4
+83.5,54.2,13.1,21.1,8.2,23.5,36.5,426.0,24.1,48.3,24.6
+33.4,24.6,3.34,17.8,6.79,8.66,12.9,1037.0,28.4,38.2,23.3
+106.0,47.8,6.61,11.1,42.9,103.0,255.0,1981.0,28.9,44.5,21.9
+25.3,40.0,13.8,17.6,7.57,9.31,17.5,813.0,6.85,15.7,4.14
+10.8,19.5,12.5,107.0,18.1,3.68,13.8,723.0,10.7,16.7,50.9
+3.16,4.26,12.1,73.0,26.9,160.0,207.0,1275.0,9.39,23.5,26.7
+79.9,34.0,8.74,22.3,73.7,13.9,23.7,496.0,21.9,48.3,11.8
+93.1,44.9,9.65,28.4,16.0,17.3,23.5,615.0,23.7,44.9,8.28
+37.5,18.3,15.3,16.1,10.3,3.62,19.3,1208.0,24.8,43.3,30.0
+35.9,16.1,10.6,8.35,11.2,22.9,33.1,154.0,21.5,40.3,14.3
+107.0,30.0,8.66,38.2,9.82,6.26,8.13,466.0,5.88,27.6,155.0
+102.0,32.5,5.78,297.0,29.4,2.46,13.1,41.0,15.3,24.6,19.3
+32.8,26.7,15.1,29.4,9.39,45.7,63.8,1144.0,16.0,28.4,9.82
+100.0,27.1,8.13,94.7,22.7,4.41,14.7,257.0,12.9,32.5,49.1
+90.6,58.3,4.41,132.0,13.6,16.4,68.5,3854.0,26.7,71.0,39.6
+100.0,25.7,1.0,241.0,33.7,19.5,29.4,552.0,24.1,47.0,27.9
+75.7,29.7,9.31,151.0,32.8,14.1,49.1,547.0,20.9,40.3,11.4
+53.8,20.7,13.8,82.8,31.3,3.08,12.7,375.0,18.9,30.8,7.04
+90.6,44.5,5.14,11.7,51.4,18.3,27.9,325.0,45.7,67.3,26.4
+69.8,47.4,18.8,135.0,23.7,8.06,36.8,1778.0,9.91,24.4,16.8
+193.0,61.0,28.9,74.3,35.2,27.1,40.7,259.0,40.3,53.8,11.3
+85.8,22.3,7.23,104.0,26.9,23.5,38.5,509.0,30.5,58.3,35.5
+67.9,14.9,10.7,41.0,20.0,34.3,50.9,337.0,19.3,34.6,22.1
+19.1,9.82,2.21,5.0,12.5,3.72,20.2,1731.0,2.59,30.8,141.0
+16.1,15.3,31.9,50.9,32.2,20.9,33.1,349.0,25.3,47.0,24.4
+95.6,28.9,1.84,14.5,49.6,22.7,55.7,906.0,7.43,28.9,124.0
+49.1,21.3,4.91,89.8,21.7,2.62,17.9,947.0,9.73,47.0,264.0
+18.9,26.2,10.7,155.0,23.1,12.5,27.1,567.0,15.7,25.9,37.5
+74.3,36.5,20.9,9.06,6.21,2.48,13.7,491.0,4.74,16.4,71.7
+25.7,24.6,10.6,35.9,10.0,15.1,35.5,698.0,37.2,53.3,16.4
+61.0,31.1,7.91,7.64,35.9,15.7,28.9,610.0,24.4,39.6,16.8
+27.1,16.4,12.2,135.0,22.5,8.2,19.8,757.0,17.5,43.7,2.31
+151.0,48.7,10.8,29.7,64.9,5.88,21.5,685.0,1.0,86.6,3.05
+179.0,77.0,11.1,207.0,45.3,4.14,8.28,133.0,12.7,19.3,36.5
+154.0,136.0,24.6,26.4,4.78,2.21,12.7,509.0,23.7,31.3,8.82
+73.7,36.2,27.9,157.0,61.0,12.9,16.0,237.0,5.28,18.4,66.7
+95.6,42.9,9.65,74.3,45.3,13.0,70.4,1811.0,24.1,50.5,16.3
+55.2,51.4,17.6,18.3,16.7,17.5,19.5,319.0,1.84,12.6,67.9
+36.5,10.5,10.5,19.5,9.91,15.7,26.4,400.0,3.92,17.0,55.7
+30.5,15.7,4.57,18.9,32.5,11.9,12.9,655.0,5.73,9.91,59.4
+158.0,37.2,16.7,20.9,4.66,14.7,17.6,375.0,15.4,22.5,20.4
+49.6,31.9,39.2,246.0,69.2,7.3,16.5,457.0,12.2,15.8,6.73
+89.8,35.9,15.4,51.9,14.2,25.7,56.2,1165.0,17.3,22.3,6.92
+35.9,18.1,10.2,17.9,23.1,40.7,70.4,1596.0,9.31,20.4,2.41
+67.9,28.9,15.0,16.8,12.6,6.92,18.8,890.0,7.99,19.6,85.1
+89.0,31.6,15.3,41.4,73.7,42.2,52.8,379.0,20.2,50.9,29.7
+57.8,21.7,4.18,64.4,9.39,5.14,69.2,1322.0,32.8,56.2,11.9
+85.1,38.2,17.2,19.8,3.08,12.2,32.8,890.0,4.37,24.4,86.6
+24.8,21.5,3.28,173.0,10.1,37.5,56.7,698.0,21.3,35.2,11.7
+63.8,19.6,14.7,36.2,46.1,11.1,51.4,1334.0,8.82,11.1,41.8
+78.4,33.1,19.3,25.9,3.89,17.6,21.5,418.0,26.2,55.7,19.3
+73.7,32.8,2.23,17.8,16.3,31.1,44.9,267.0,27.9,47.0,24.6
+117.0,40.3,11.2,137.0,20.7,23.3,35.2,649.0,9.14,12.1,69.2
+117.0,78.4,11.3,11.4,6.21,1.64,6.55,673.0,2.92,22.7,47.4
+34.3,20.5,5.94,52.3,18.9,6.92,18.1,538.0,61.0,91.4,8.35
+179.0,34.6,11.1,14.3,1.0,61.0,175.0,1499.0,4.22,20.5,117.0
+106.0,39.2,2.74,155.0,7.37,17.0,34.6,557.0,27.4,55.7,46.6
+39.2,17.8,5.67,205.0,64.4,14.7,31.1,340.0,26.2,54.2,69.8
+71.7,25.7,16.0,12.4,19.1,24.4,27.9,274.0,3.79,23.3,85.1
+13.9,21.1,15.8,35.9,16.5,11.7,15.0,1322.0,13.0,23.7,13.1
+91.4,80.6,6.49,67.3,18.4,8.58,10.3,466.0,2.92,21.7,110.0
+50.5,13.6,12.2,15.3,21.9,20.5,26.9,365.0,23.3,44.1,19.8
+34.0,15.7,12.0,81.3,27.9,15.0,30.2,500.0,5.23,14.5,74.3
+48.7,19.5,25.7,14.5,4.87,22.1,34.6,414.0,30.5,53.8,14.6
+84.3,34.6,10.0,15.3,12.9,7.77,22.5,375.0,34.3,53.3,21.7
+44.5,18.1,18.8,41.8,20.4,18.1,22.1,466.0,23.9,40.3,21.1
+31.3,21.3,10.3,33.1,81.3,16.1,23.5,588.0,21.3,41.8,21.3
+79.1,59.4,24.4,34.9,3.46,22.5,42.2,422.0,23.3,34.6,14.3
+42.6,21.7,11.7,40.3,2.74,10.5,25.0,610.0,8.06,35.5,99.1
+51.4,38.9,13.3,15.7,6.38,17.8,29.2,621.0,1.65,16.5,86.6
+63.8,51.4,9.06,13.3,8.2,14.9,24.6,523.0,26.2,40.7,18.8
+14.2,18.4,18.8,64.9,23.3,9.39,21.9,757.0,31.6,47.8,15.1
+42.9,20.4,37.2,117.0,83.5,13.8,21.9,578.0,13.1,33.4,172.0
+26.4,17.2,9.82,164.0,30.8,5.67,16.0,1219.0,4.96,19.1,86.6
+6.21,4.87,49.1,66.1,21.1,6.55,16.8,914.0,18.4,30.2,9.91
+31.6,20.7,13.7,16.3,4.53,19.5,30.8,449.0,33.4,44.9,13.3
+78.4,25.7,12.5,28.4,49.1,24.1,31.3,346.0,8.98,24.6,9.82
+30.0,9.31,18.6,19.3,13.5,8.13,33.1,466.0,6.26,34.0,107.0
+50.5,18.8,16.8,23.9,16.4,25.0,23.9,227.0,2.27,11.5,97.3
+23.9,20.0,8.51,99.1,18.3,5.28,20.2,813.0,13.2,32.5,19.6
+73.7,23.3,16.0,33.1,49.6,4.33,6.55,106.0,3.37,41.4,119.0
+11.0,14.7,15.8,42.9,18.3,16.0,33.4,362.0,37.9,56.7,45.3
+65.5,25.3,12.3,145.0,19.8,4.03,14.3,914.0,4.57,22.5,77.7
+21.7,8.2,9.31,17.5,63.2,7.43,15.7,429.0,7.3,17.6,58.8
+63.8,18.4,7.04,143.0,23.7,49.6,65.5,1433.0,2.33,16.4,60.4
+104.0,60.4,2.11,173.0,14.7,11.8,15.1,410.0,26.4,50.9,19.5
+25.7,18.4,8.06,22.1,44.5,17.2,26.2,284.0,28.1,44.5,23.1
+17.3,21.7,35.2,37.5,22.3,8.28,11.1,533.0,2.74,13.3,97.3
+8.43,36.8,24.1,22.9,9.39,14.7,20.4,685.0,12.5,15.1,5.09
+57.8,16.5,11.2,83.5,11.8,31.3,44.1,1794.0,18.1,35.5,11.7
+91.4,104.0,38.9,70.4,26.2,33.7,62.6,956.0,11.4,23.7,10.7
+79.9,36.5,8.13,93.9,8.43,9.91,16.7,644.0,20.0,39.2,7.3
+81.3,32.5,7.64,35.9,3.65,9.22,17.5,400.0,47.0,70.4,27.6
+107.0,30.5,1.95,9.47,7.91,54.7,82.0,1459.0,23.5,42.9,13.1
+99.1,36.2,16.7,17.9,17.5,1.63,21.5,956.0,31.3,52.3,22.5
+93.9,45.3,4.91,23.1,10.6,12.1,7.99,692.0,8.35,21.7,82.8
+38.9,18.4,13.7,14.9,10.5,8.58,23.3,410.0,6.44,12.0,80.6
+78.4,20.9,9.56,17.0,45.7,16.8,24.6,528.0,26.2,44.5,7.04
+33.1,26.4,15.1,11.0,15.1,18.6,27.9,828.0,21.5,37.2,10.6
+60.4,22.5,12.5,31.9,2.05,20.9,34.3,519.0,6.61,12.1,64.4
+70.4,23.1,6.15,331.0,49.6,34.9,70.4,1310.0,16.1,33.1,13.2
+51.9,29.4,61.0,121.0,79.9,9.82,27.9,1275.0,10.6,24.4,5.47
+93.9,27.4,5.52,16.5,26.2,10.6,14.3,204.0,5.47,19.1,109.0
+93.9,30.2,1.88,422.0,25.7,3.92,16.5,717.0,1.0,115.0,7.43
+33.1,9.31,14.9,12.6,7.84,17.2,75.7,2571.0,15.3,36.8,19.3
+37.9,19.6,1.0,184.0,24.8,19.3,30.8,588.0,20.4,28.6,26.2
+45.3,27.9,5.62,87.4,15.4,4.26,19.1,866.0,20.4,38.9,26.4
+105.0,80.6,18.4,8.98,7.5,16.3,26.2,414.0,11.0,13.2,10.5
+75.0,31.9,11.7,93.1,16.0,3.22,15.4,95.6,11.8,33.1,42.2
+98.2,21.5,7.43,75.0,20.5,6.92,10.8,496.0,27.9,48.7,16.7
+78.4,24.8,5.88,163.0,26.9,13.0,25.0,638.0,27.1,44.9,13.6
+147.0,31.1,17.3,19.1,11.5,11.7,23.3,599.0,36.5,57.3,14.2
+14.5,13.0,7.04,17.9,1.68,9.22,22.7,445.0,16.0,35.5,10.6
+121.0,33.7,4.14,90.6,29.4,6.26,7.04,181.0,8.74,24.6,90.6
+89.8,32.8,8.2,36.8,35.2,12.9,26.7,717.0,2.17,11.7,24.8
+31.3,13.1,9.22,101.0,12.4,6.73,13.6,422.0,19.6,33.1,10.0
+27.9,17.8,9.31,112.0,12.5,4.7,8.98,198.0,26.2,50.5,15.1
+59.9,16.4,29.7,71.7,119.0,12.7,15.7,429.0,17.6,37.9,21.1
+44.5,20.7,24.1,186.0,45.7,13.6,29.7,461.0,15.7,36.2,12.4
+85.1,22.9,48.7,69.2,12.2,11.1,23.3,649.0,21.3,58.3,10.6
+191.0,84.3,13.8,207.0,38.2,6.61,37.2,1322.0,3.28,3.96,2.25
+106.0,22.9,2.59,83.5,27.4,29.7,38.9,396.0,11.2,20.5,9.56
+40.3,19.6,6.73,311.0,92.2,5.38,9.56,588.0,16.0,38.5,11.2
+55.7,49.6,4.26,12.5,33.4,3.89,14.6,9.73,17.2,45.7,95.6
+45.3,29.2,4.33,14.5,6.38,8.43,20.9,533.0,78.4,127.0,16.7
+108.0,79.9,42.6,77.0,8.98,34.9,61.5,1197.0,6.79,14.1,58.3
+108.0,51.4,10.8,54.2,20.0,25.0,32.8,259.0,6.73,12.1,34.9
+59.9,19.1,8.2,149.0,29.7,12.3,20.5,552.0,13.8,31.3,16.1
+69.8,22.3,13.5,418.0,87.4,6.44,46.6,259.0,19.5,39.6,15.8
+85.1,27.6,2.35,9.56,21.9,10.2,25.7,514.0,20.2,50.9,9.47
+120.0,48.3,13.9,10.6,11.3,6.67,25.3,429.0,3.75,45.3,233.0
+151.0,44.5,5.62,142.0,13.0,6.38,11.7,259.0,14.5,37.5,12.0
+120.0,99.1,7.1,135.0,28.1,7.43,20.7,638.0,5.83,27.4,136.0
+131.0,115.0,10.3,58.8,10.5,21.9,34.0,478.0,8.35,22.3,10.2
+133.0,57.3,10.3,15.1,1.13,5.78,40.0,626.0,6.79,12.4,37.9
+106.0,35.5,15.0,18.6,9.56,8.2,20.7,679.0,24.4,47.0,13.2
+22.9,17.9,35.2,63.2,23.5,7.37,11.1,523.0,35.9,58.3,13.8
+35.9,16.8,17.3,198.0,33.1,17.3,35.2,294.0,1.51,9.22,72.3
+47.0,44.9,11.1,13.9,37.9,24.8,20.0,547.0,18.3,44.5,17.8
+38.9,26.9,11.0,68.5,17.5,18.9,25.5,418.0,40.0,62.6,22.3
+54.7,28.4,12.7,53.3,85.1,38.2,57.3,882.0,28.9,46.6,19.3
+46.6,20.4,19.5,27.4,9.06,19.1,18.8,583.0,14.5,34.0,13.6
+78.4,32.8,15.1,13.3,11.0,7.91,22.5,1094.0,17.6,36.8,14.5
+49.1,24.8,10.6,18.1,25.3,12.4,28.9,389.0,7.43,20.5,69.8
+59.4,18.3,5.67,143.0,42.9,15.4,28.4,483.0,18.4,28.6,10.2
+109.0,38.2,7.91,14.5,25.3,23.7,28.4,487.0,21.3,39.6,24.6
+78.4,76.4,3.37,147.0,8.35,5.94,18.6,737.0,3.4,18.6,66.7
+39.2,12.3,12.1,132.0,17.9,11.0,20.9,973.0,13.9,29.2,19.1
+89.0,34.9,13.9,27.4,87.4,14.1,21.1,638.0,22.9,28.9,15.8
+74.3,17.8,8.51,123.0,34.0,44.1,67.3,400.0,17.2,46.6,25.0
+47.4,22.9,3.11,15.7,9.91,10.6,23.9,400.0,17.6,32.2,12.2
+60.4,24.8,11.1,1114.0,126.0,7.43,9.65,615.0,1.13,112.0,6.1
+80.6,20.9,13.6,76.4,20.2,28.9,35.5,246.0,8.2,18.4,74.3
+21.5,18.1,9.56,108.0,26.2,10.5,7.5,433.0,10.4,24.4,10.9
+189.0,61.0,10.5,150.0,25.7,9.47,26.9,552.0,4.03,15.3,62.1
+31.6,16.8,6.61,3.52,5.67,16.4,39.6,1009.0,2.19,23.9,112.0
+115.0,36.8,11.3,17.6,3.59,36.5,51.9,316.0,9.47,18.8,2.11
+114.0,59.4,7.91,17.3,31.3,18.8,27.1,322.0,25.3,52.3,35.5
+17.9,25.3,22.7,43.3,91.4,13.8,20.4,429.0,6.15,15.3,91.4
+39.2,14.5,1.96,215.0,33.4,8.9,20.7,437.0,6.26,17.8,17.2
+126.0,142.0,17.3,10.0,3.25,7.64,28.4,382.0,8.58,20.0,8.58
+35.9,22.7,7.7,22.9,9.73,6.73,15.0,610.0,28.1,44.9,17.3
+207.0,56.7,3.52,172.0,20.0,5.67,19.3,316.0,17.8,48.3,56.7
+62.1,27.6,16.1,37.5,32.8,19.5,38.9,470.0,3.59,27.1,96.5
+101.0,39.2,33.4,91.4,52.8,8.43,27.9,223.0,15.4,30.5,5.73
+15.1,14.7,4.07,19.5,38.2,2.94,18.4,3.4,21.5,46.6,15.7
+105.0,105.0,7.7,26.4,25.9,7.04,38.5,890.0,23.5,59.4,200.0
+62.6,33.4,10.1,51.9,18.3,17.5,32.8,313.0,31.6,53.8,12.7
+30.5,27.9,13.0,20.5,5.57,4.78,15.3,615.0,45.7,77.7,14.1
+5.99,19.3,9.73,10.9,48.3,16.5,24.6,679.0,53.3,73.0,25.0
+8.82,4.96,8.98,17.5,56.7,11.0,21.9,389.0,20.9,49.1,13.3
+37.2,20.9,13.7,26.2,63.2,6.44,15.8,578.0,3.79,16.5,47.8
+16.3,9.47,10.2,65.5,28.6,13.3,24.6,692.0,13.8,29.2,41.0
+24.6,35.9,10.6,11.7,31.6,15.5,26.9,407.0,48.7,84.3,30.0
+75.7,21.1,25.9,122.0,66.1,23.7,39.6,328.0,23.5,41.8,8.66
+80.6,34.0,8.43,127.0,23.5,38.2,62.6,2091.0,2.33,3.4,6.79
+33.1,11.2,13.2,86.6,10.8,26.2,39.6,382.0,49.1,73.0,20.2
+33.4,15.7,2.62,271.0,33.4,8.58,16.7,509.0,12.1,25.9,20.9
+34.3,16.4,16.1,21.5,5.78,25.7,45.7,433.0,13.5,32.2,18.4
+44.9,20.4,18.4,23.7,7.17,11.5,19.8,337.0,17.6,45.7,25.3
+36.5,16.3,17.5,42.6,58.3,8.74,20.9,599.0,31.9,76.4,20.9
+138.0,39.2,1.88,149.0,15.3,10.6,15.4,737.0,1.0,82.8,5.67
+68.5,34.6,20.2,40.0,65.5,11.7,24.8,583.0,22.7,47.8,22.9
+13.7,7.5,16.7,8.06,10.9,14.7,27.9,538.0,14.6,34.3,13.3
+75.7,44.9,6.98,50.0,11.1,10.8,17.0,594.0,18.4,26.2,15.8
+35.9,36.8,2.25,3.62,12.7,9.82,21.5,519.0,1.72,18.3,78.4
+69.8,28.6,2.11,181.0,28.6,14.2,47.8,730.0,25.5,42.6,22.7
+68.5,39.6,16.3,21.7,34.3,4.91,22.3,403.0,24.6,41.8,15.7
+38.9,16.0,1.68,186.0,29.4,58.3,96.5,1611.0,2.46,8.13,22.5
+35.2,29.7,18.3,47.8,48.3,17.2,31.1,445.0,10.1,17.6,10.0
+29.7,20.2,12.7,22.7,5.88,11.1,23.7,237.0,25.3,42.9,17.2
+61.5,23.9,25.7,122.0,35.2,104.0,160.0,649.0,2.02,10.0,73.0
+129.0,42.9,2.97,4.26,6.1,8.13,19.3,346.0,8.28,26.9,50.0
+91.4,27.6,6.98,25.3,26.4,5.23,12.5,906.0,25.5,45.3,17.3
+66.7,23.7,9.39,16.0,40.0,17.3,29.2,407.0,15.7,41.8,7.57
+79.1,31.1,18.4,44.5,26.7,4.07,19.3,965.0,11.9,16.3,9.91
+61.0,42.6,1.0,334.0,22.1,8.06,32.5,820.0,6.04,12.3,4.78
+51.9,16.8,11.4,12.6,16.7,2.81,20.5,858.0,14.1,28.9,14.3
+13.7,9.82,5.33,109.0,29.4,25.3,38.5,445.0,15.3,24.6,9.31
+22.5,14.2,7.04,195.0,31.6,43.7,63.8,1486.0,8.98,24.1,8.28
+46.1,21.9,1.45,2.76,7.1,11.1,25.5,638.0,18.8,36.2,13.9
+13.7,25.9,23.9,36.8,11.9,8.28,21.9,799.0,25.7,47.8,16.1
+27.4,14.1,18.8,20.5,3.4,10.9,16.4,196.0,17.5,35.2,15.1
+73.7,30.0,23.5,73.7,23.9,8.82,21.3,813.0,17.3,41.8,8.2
+17.2,21.9,13.3,12.2,19.8,4.29,2.74,445.0,20.9,25.7,20.2
+59.4,20.7,15.7,28.1,15.5,23.5,26.2,389.0,4.03,18.4,77.7
+67.3,30.2,12.6,667.0,86.6,24.1,41.8,253.0,7.23,13.8,6.98
+39.2,18.9,12.3,47.0,25.9,30.8,45.3,457.0,9.82,27.6,75.0
+67.9,31.3,9.56,91.4,23.5,51.9,82.8,2207.0,24.1,43.7,8.98
+52.3,45.7,5.62,129.0,19.1,30.2,64.4,673.0,57.8,84.3,31.1
+89.0,38.2,7.17,13.2,18.4,18.8,25.0,349.0,20.4,34.0,17.9
+54.2,20.7,1.0,105.0,13.1,22.3,42.9,1134.0,2.15,7.77,76.4
+51.9,58.8,6.44,176.0,10.3,4.37,18.3,851.0,13.1,25.7,21.1
+31.3,10.4,10.7,118.0,29.4,19.8,27.6,322.0,23.9,39.2,22.3
+69.8,34.6,9.65,223.0,36.8,12.4,18.4,851.0,1.51,72.3,11.3
+28.9,29.4,23.7,50.9,93.9,6.98,19.1,552.0,15.5,29.2,12.7
+95.6,49.1,4.41,141.0,10.8,9.91,20.5,519.0,20.0,44.5,15.5
+47.4,21.7,7.37,16.8,5.57,16.7,23.3,325.0,17.2,32.2,16.1
+61.5,40.7,11.3,90.6,20.4,3.96,7.04,186.0,17.2,34.3,12.7
+40.7,25.0,23.9,264.0,58.8,15.8,33.7,638.0,20.9,35.9,9.22
+46.1,29.7,9.73,13.7,8.51,24.6,36.2,483.0,19.8,36.2,9.39
+32.8,19.1,5.62,19.8,13.9,21.9,33.7,368.0,25.7,49.6,13.3
+93.9,23.3,5.99,219.0,38.2,10.2,20.5,594.0,11.1,23.7,5.38
+67.3,33.4,20.5,25.0,1.78,7.99,16.3,667.0,11.0,34.0,9.14
+37.2,11.8,17.9,16.1,17.9,13.1,62.6,2864.0,32.2,62.6,37.5
+38.2,22.5,13.2,8.66,9.14,6.1,6.61,470.0,4.0,21.1,115.0
+20.7,22.7,21.7,21.7,14.6,9.65,45.7,1104.0,5.28,43.3,205.0
+13.6,13.7,5.94,10.3,17.2,8.2,24.6,429.0,24.1,51.9,20.0
+173.0,193.0,10.8,14.3,9.14,17.6,31.3,248.0,20.4,58.8,20.7
+14.7,18.6,11.2,45.3,10.1,22.5,27.4,209.0,11.1,33.1,16.0
+75.0,25.0,5.28,133.0,44.1,31.3,53.3,1000.0,15.8,42.9,64.4
+85.8,67.3,8.06,32.2,31.3,35.2,40.0,403.0,2.59,25.3,49.6
+87.4,44.5,34.6,47.8,17.2,18.6,33.7,300.0,10.9,32.2,46.1
+38.2,24.4,22.9,20.2,11.1,3.19,23.3,851.0,2.86,11.3,31.6
+38.2,24.1,1.21,514.0,59.9,26.9,41.8,509.0,3.72,23.9,154.0
+40.0,12.2,11.2,21.5,44.1,21.7,32.2,478.0,15.3,41.8,18.8
+77.7,20.9,45.7,50.9,16.8,32.8,48.7,1433.0,17.2,31.9,7.91
+74.3,29.7,2.46,219.0,13.0,9.06,20.4,750.0,48.3,89.0,31.3
+41.8,20.2,9.47,149.0,41.4,34.9,75.7,1241.0,3.08,24.8,25.5
+49.1,22.1,2.79,83.5,16.4,8.9,15.5,449.0,20.7,39.2,23.5
+50.0,27.1,7.7,16.0,41.0,8.82,11.8,784.0,22.7,47.8,15.3
+29.2,45.7,7.04,62.1,17.0,10.1,23.5,685.0,13.8,36.2,104.0
+80.6,36.8,6.92,98.2,17.6,13.6,21.3,626.0,11.3,42.2,153.0
+65.5,32.2,9.39,15.5,13.5,7.77,23.9,1554.0,15.7,32.2,8.98
+179.0,55.7,18.8,509.0,80.6,11.5,16.0,164.0,25.0,33.7,15.0
+34.0,24.1,3.65,47.8,31.9,22.5,59.9,1358.0,38.9,67.3,18.9
+55.7,35.5,47.4,73.0,176.0,8.98,20.9,552.0,16.3,25.5,13.0
+80.6,36.5,4.61,89.0,10.2,19.5,28.9,533.0,10.5,23.9,50.9
+31.3,32.8,10.6,25.7,49.1,11.4,38.9,1596.0,23.9,51.4,13.1
+49.6,32.2,17.9,7.84,9.31,6.79,13.5,604.0,16.3,28.9,11.1
+167.0,79.1,31.6,49.1,23.7,13.2,17.3,500.0,13.9,30.0,15.4
+71.7,50.9,5.73,130.0,8.74,13.3,28.4,478.0,1.23,18.8,114.0
+66.1,47.4,6.49,26.9,34.6,8.98,31.9,453.0,1.3,13.8,79.9
+52.8,14.6,25.7,178.0,41.8,6.21,10.8,255.0,16.8,36.8,17.0
+123.0,27.4,10.8,13.7,42.6,5.05,15.3,939.0,13.9,25.7,9.31
+47.4,22.5,1.91,229.0,23.1,11.0,27.4,573.0,13.2,40.3,17.8
+21.5,18.1,7.3,34.9,15.7,9.47,14.2,644.0,3.55,16.3,33.1
+42.2,13.5,13.8,68.5,31.9,4.78,34.6,422.0,28.6,42.6,20.2
+9.65,16.1,12.4,21.7,1.47,13.0,35.2,470.0,24.1,43.7,23.1
+28.9,21.5,8.74,15.8,35.5,3.46,21.9,355.0,17.8,44.1,11.8
+93.9,44.5,12.1,10.0,4.29,25.3,32.2,396.0,3.19,26.4,99.1
+69.8,20.9,4.53,5.67,4.41,25.0,39.6,319.0,16.5,40.7,75.7
+41.8,14.6,8.2,15.7,16.0,8.74,11.9,382.0,15.7,35.5,4.78
+12.0,21.3,11.3,74.3,13.8,7.91,20.0,939.0,30.2,48.7,5.67
+31.1,23.9,21.9,19.1,10.1,13.2,20.7,505.0,6.79,17.3,13.8
+62.1,30.2,17.8,15.4,6.55,8.13,22.1,457.0,10.0,17.6,8.13
+14.9,16.8,12.5,31.6,12.7,17.8,28.1,276.0,18.1,35.9,19.1
+34.0,23.3,13.2,202.0,23.3,21.9,30.2,319.0,18.1,22.7,1.46
+69.2,19.3,12.6,12.4,12.1,11.1,23.9,615.0,1.75,7.5,10.2
+50.9,20.7,9.73,150.0,17.0,4.29,14.5,164.0,14.9,18.1,9.73
+38.9,27.1,3.19,15.0,8.35,10.8,22.7,685.0,15.0,35.5,13.1
+88.2,24.4,1.78,87.4,11.8,25.9,47.0,392.0,13.7,17.3,7.64
+107.0,54.2,63.8,235.0,115.0,18.1,34.3,382.0,16.3,19.5,8.82
+54.7,27.4,6.38,15.8,25.0,58.3,98.2,1420.0,18.1,24.8,7.17
+10.4,4.57,18.9,25.5,13.6,4.07,44.1,644.0,24.4,42.9,6.38
+59.9,8.28,17.2,52.8,2.44,14.6,26.2,538.0,3.16,9.82,2.97
+101.0,25.3,5.99,235.0,34.3,1.45,21.7,673.0,22.7,26.2,12.3
+14.6,28.9,10.6,87.4,22.7,29.4,47.0,365.0,13.8,11.7,8.35
+143.0,67.3,3.79,9.56,54.7,3.85,14.6,221.0,7.17,16.7,13.6
+96.5,29.7,13.9,16.0,2.46,6.98,19.5,1055.0,10.7,11.1,3.89
+103.0,89.8,5.09,4.74,7.37,9.91,24.8,557.0,21.3,38.5,14.6
+36.5,17.9,1.04,343.0,30.2,10.4,39.6,1700.0,7.91,9.82,5.67
+66.7,81.3,12.2,14.5,4.37,17.3,31.6,286.0,16.0,14.3,4.45
+64.4,35.2,15.5,11.2,7.7,7.1,22.7,433.0,20.9,25.9,8.43
+110.0,34.0,14.1,31.3,25.3,7.3,16.5,505.0,17.8,29.2,11.7
+23.1,30.2,1.1,311.0,27.1,11.5,23.7,594.0,18.6,28.9,7.91
+145.0,32.5,11.8,52.3,19.1,35.2,59.4,389.0,18.6,25.7,5.14
+48.7,17.3,1.38,13.6,56.2,4.96,26.9,1263.0,11.0,15.7,8.9
+18.8,13.3,7.23,89.0,23.9,8.74,18.1,692.0,4.14,19.5,94.7
+64.4,31.1,7.91,246.0,51.4,22.1,37.2,385.0,21.5,28.9,17.9
+35.2,19.1,19.8,53.8,77.0,22.1,32.8,334.0,16.7,28.1,5.47
+29.7,22.9,13.6,45.7,13.9,18.8,35.2,552.0,18.3,31.3,6.79
+52.8,14.2,13.6,11.2,7.91,6.98,24.6,422.0,2.19,9.14,67.3
+34.0,17.8,19.1,16.1,6.73,6.21,13.1,667.0,12.3,5.99,3.43
+42.9,14.5,69.2,186.0,32.8,4.87,23.3,382.0,13.2,25.7,3.22
+33.4,27.4,10.1,61.5,13.1,10.8,24.1,573.0,3.37,4.14,8.9
+111.0,38.2,10.5,12.6,9.82,36.8,64.9,1596.0,19.3,19.6,8.2
+84.3,30.2,15.7,19.1,17.0,21.1,32.8,311.0,17.8,31.6,3.13
+37.9,20.9,6.85,59.4,22.7,6.1,5.67,704.0,15.4,15.1,10.1
+64.4,34.3,9.14,89.8,15.1,5.83,12.1,271.0,17.0,23.7,8.51
+44.5,22.1,4.87,12.1,12.0,2.69,20.4,685.0,17.6,16.5,13.6
+36.8,20.7,12.5,13.1,10.5,47.8,59.4,835.0,19.3,45.3,5.62
+111.0,42.9,11.3,14.1,9.47,18.6,32.8,244.0,46.6,55.2,9.06
+42.6,16.3,15.0,50.9,20.0,12.5,25.0,352.0,12.3,16.3,1.88
+12.5,32.2,11.9,75.0,20.2,25.3,37.5,418.0,16.8,73.7,163.0
+28.1,30.5,9.73,52.3,5.99,3.49,15.3,19.8,15.7,26.2,10.6
+83.5,75.0,9.14,82.0,30.0,20.0,36.5,385.0,19.5,34.9,11.5
+87.4,39.2,14.6,403.0,84.3,29.2,45.3,461.0,12.2,26.7,5.0
+29.4,29.7,9.39,77.7,26.2,17.8,24.4,385.0,9.14,34.9,120.0
+49.1,22.5,9.91,21.3,55.2,8.82,12.6,599.0,9.73,43.7,198.0
+122.0,85.1,10.0,17.3,20.4,25.0,44.1,1420.0,2.81,11.8,59.4
+28.1,17.8,10.3,21.1,35.5,17.8,29.2,835.0,3.31,12.5,2.23
+19.3,17.3,20.0,34.0,8.9,12.0,24.6,523.0,15.7,24.6,20.7
+3.65,10.9,14.2,67.3,33.7,4.18,16.8,23.3,2.0,7.7,48.7
+25.5,1.25,16.3,15.0,8.2,16.8,29.4,292.0,15.5,18.9,3.52
+31.3,22.7,4.83,12.6,11.0,21.1,31.6,289.0,25.9,41.0,17.5
+16.7,5.38,1.01,11.8,20.4,16.0,25.3,274.0,19.5,21.1,13.8
+71.7,19.5,10.6,28.6,28.4,23.9,38.5,316.0,15.5,26.4,6.15
+37.5,10.3,11.7,51.9,15.8,5.05,26.4,53.8,5.88,8.51,6.67
+3.46,1.47,9.06,36.2,71.0,5.28,20.4,284.0,16.7,34.3,10.3
+34.9,21.3,9.22,178.0,7.7,38.9,64.4,1911.0,29.7,42.2,12.4
+23.9,17.8,7.99,40.7,14.5,31.1,81.3,1762.0,15.7,12.9,5.0
+26.4,29.2,15.3,10.6,6.55,10.9,24.8,426.0,11.3,28.9,17.2
+17.3,15.8,12.7,18.9,5.94,4.57,14.5,1018.0,17.8,41.0,4.37
+73.7,25.3,4.83,12.1,28.6,6.21,18.4,621.0,15.1,30.8,8.58
+64.9,23.5,6.32,23.1,33.1,12.7,29.2,599.0,17.8,23.1,4.57
+53.8,14.5,9.14,227.0,29.2,9.73,16.0,692.0,3.0,10.8,2.25
+49.6,23.7,13.6,20.7,40.0,20.7,42.6,313.0,12.5,13.6,9.39
+1.35,8.82,18.8,14.9,7.17,14.6,18.4,457.0,11.0,13.6,6.55
+50.9,15.1,1.21,1.33,7.64,7.17,14.9,567.0,11.9,11.5,7.5
+24.8,9.65,6.67,246.0,30.5,2.97,24.1,352.0,37.2,41.8,7.64
+86.6,26.2,23.3,86.6,111.0,17.3,28.9,509.0,6.61,10.5,14.7
+34.9,11.5,19.6,11.9,14.5,14.7,31.9,437.0,19.5,30.2,2.71
+60.4,16.5,9.39,155.0,22.7,19.3,62.1,567.0,17.0,23.7,13.2
+54.2,27.4,15.0,15.0,8.66,5.19,16.4,882.0,24.8,39.6,20.4
+58.3,28.6,7.99,11.7,2.97,5.47,15.1,34.0,2.55,2.07,7.84
+65.5,16.8,16.4,18.6,10.8,23.1,38.2,461.0,26.9,39.6,7.37
+67.3,20.7,28.4,51.9,21.1,5.73,16.4,610.0,1.0,2.11,2.79
+109.0,31.9,2.53,1.08,509.0,17.3,18.6,241.0,14.9,21.9,2.89
+127.0,68.5,25.9,70.4,139.0,17.9,38.2,382.0,1.0,16.5,6.92
+115.0,37.9,32.8,34.0,18.1,19.6,27.6,445.0,12.6,17.3,10.6
+21.3,13.5,11.5,20.0,95.6,18.9,28.9,491.0,3.0,17.3,73.7
+14.5,18.9,21.3,20.4,17.9,19.3,20.5,262.0,15.3,22.5,3.89
+56.7,23.7,8.82,69.8,16.4,18.6,44.5,1310.0,8.82,13.9,7.1
+26.4,19.6,23.1,11.4,6.85,13.1,21.3,547.0,13.2,13.7,8.35
+9.39,6.04,6.26,5.83,3.75,20.5,35.5,396.0,14.2,16.1,8.28
+13.1,17.2,16.1,12.4,13.2,8.2,27.6,533.0,5.94,39.6,95.6
+63.2,28.1,17.2,21.3,5.28,19.6,34.6,661.0,52.3,163.0,57.8
+48.3,23.3,5.19,75.0,21.7,17.8,28.6,673.0,15.7,34.0,3.82
+31.6,16.7,7.43,250.0,23.5,12.2,25.3,496.0,10.1,13.6,9.91
+31.9,24.6,13.7,24.8,13.5,6.15,15.8,621.0,22.7,31.1,7.43
+41.0,17.5,8.66,46.1,35.9,3.96,13.9,418.0,21.1,38.5,12.9
+16.8,17.8,17.0,21.1,6.04,3.92,12.9,562.0,8.82,10.6,36.2
+44.5,12.5,3.25,379.0,69.8,17.5,37.9,372.0,5.33,9.65,1.63
+1.0,10.7,15.0,15.0,18.8,31.1,45.3,461.0,38.5,60.4,183.0
+19.6,5.67,1.0,99.1,12.3,13.8,42.9,1197.0,7.57,48.3,91.4
+26.7,18.9,19.6,14.3,4.41,18.8,25.0,457.0,16.8,19.8,11.5
+34.0,25.0,11.5,19.5,15.8,14.3,15.5,519.0,12.1,14.3,1.79
+74.3,35.9,9.82,104.0,35.5,23.3,30.2,433.0,15.5,25.9,5.57
+44.5,44.5,4.41,68.5,9.91,32.8,47.8,403.0,77.0,133.0,49.6
+23.9,29.7,4.41,15.5,14.9,21.3,34.0,311.0,14.5,22.5,8.66
+22.3,34.6,2.02,124.0,4.96,33.4,35.5,340.0,15.1,19.5,1.19
+118.0,24.1,6.32,188.0,34.0,13.7,22.3,396.0,24.8,48.3,76.4
+109.0,38.5,11.7,18.6,18.3,9.73,18.9,362.0,15.8,25.3,6.15
+73.7,20.7,5.78,143.0,32.2,3.72,12.6,483.0,13.3,11.1,5.05
+25.9,23.1,27.9,37.5,12.5,13.3,25.9,453.0,1.04,17.3,14.9
+75.7,34.3,16.1,58.8,21.1,12.7,23.5,300.0,3.25,7.91,3.08
+37.9,6.73,11.0,34.0,35.9,31.1,34.6,316.0,8.13,14.5,6.85
+41.4,21.7,3.37,239.0,19.8,6.98,15.8,914.0,8.98,23.7,34.0
+90.6,29.4,12.5,57.3,12.7,2.46,11.4,533.0,19.5,42.6,27.4
+19.1,40.7,13.1,22.3,9.47,13.0,26.9,403.0,14.7,18.6,15.3
+63.2,36.2,14.2,62.6,15.0,11.9,19.3,389.0,20.0,37.5,20.4
+75.0,31.6,10.2,118.0,26.7,13.7,20.7,449.0,13.9,31.3,10.5
+36.8,24.4,6.79,12.7,7.99,12.4,34.0,422.0,10.6,25.5,5.0
+42.6,14.7,17.9,6.73,31.6,10.6,67.3,2571.0,1.0,63.8,4.1
+41.4,34.3,5.83,241.0,22.3,7.5,7.5,685.0,2.86,1.33,5.94
+20.2,17.8,6.32,111.0,42.9,4.1,16.3,375.0,5.88,29.2,145.0
+13.2,9.14,4.91,2.71,1.29,12.3,24.4,474.0,15.3,16.5,7.64
+18.3,11.3,8.2,221.0,35.9,264.0,528.0,5989.0,6.15,10.6,4.66
+11.9,4.53,2.48,121.0,9.82,5.47,15.0,547.0,15.3,26.2,10.2
+53.8,25.5,2.89,183.0,29.7,10.1,17.0,692.0,8.82,6.61,8.58
+10.0,10.2,11.7,21.9,17.8,32.2,52.8,1176.0,49.6,121.0,32.8
+58.3,32.8,12.2,1.38,27.9,26.4,50.9,784.0,46.1,88.2,18.8
+94.7,50.0,6.85,10.2,31.6,33.7,38.9,276.0,8.9,23.9,1.68
+27.4,21.5,7.04,6.38,74.3,5.73,15.3,610.0,16.4,13.3,3.31
+37.2,15.0,15.0,11.0,9.22,21.3,31.3,255.0,8.9,14.2,13.7
+153.0,107.0,11.4,75.0,8.66,15.0,63.2,2969.0,14.1,14.9,6.73
+51.9,10.3,10.9,85.8,27.4,3.34,13.7,217.0,28.4,51.4,12.9
+78.4,25.9,1.0,264.0,44.5,17.3,28.9,509.0,11.7,16.5,3.68
+69.8,24.4,54.7,129.0,14.1,15.4,27.9,375.0,4.37,12.3,10.1
+106.0,45.3,6.79,142.0,27.4,6.85,23.9,1252.0,29.4,28.1,9.06
+204.0,75.7,24.6,49.1,105.0,24.6,51.9,1009.0,22.3,27.4,4.87
+53.3,21.3,9.22,9.65,17.0,10.6,47.0,1625.0,10.7,14.3,5.28
+44.9,22.1,12.1,41.8,14.6,9.47,21.1,429.0,25.7,39.2,14.3
+38.2,16.0,29.7,31.1,30.0,12.4,18.6,621.0,12.4,19.8,8.51
+8.2,9.91,6.26,13.8,9.14,26.4,30.5,389.0,17.5,17.6,5.23
+93.9,46.1,3.43,8.2,55.7,10.5,18.1,461.0,11.3,13.3,12.7
+32.8,18.4,6.49,24.4,4.61,22.3,36.8,322.0,20.2,34.3,3.05
+80.6,40.7,22.7,10.3,8.06,13.8,56.2,2864.0,16.0,26.9,3.62
+7.57,23.5,1.43,6.92,18.1,2.84,1.31,136.0,12.6,30.5,7.1
+28.9,19.1,37.2,9.56,58.3,6.61,13.6,82.0,15.8,24.4,16.5
+9.82,7.43,6.73,13.8,46.6,30.8,42.6,466.0,15.1,24.1,12.0
+93.9,38.9,9.73,125.0,20.5,25.9,38.5,453.0,7.77,35.5,223.0
+40.3,24.8,50.0,229.0,88.2,15.0,29.4,248.0,15.1,19.5,8.58
+35.9,34.9,4.14,13.2,30.0,7.64,25.0,638.0,17.6,30.0,7.99
+66.1,27.9,4.57,183.0,44.1,4.1,22.3,698.0,10.8,31.1,4.96
+41.8,19.5,3.43,8.58,8.28,5.88,17.0,362.0,21.5,26.4,8.98
+20.9,27.6,13.6,48.3,54.7,1.0,1.47,198.0,13.2,22.7,8.51
+16.4,8.9,33.1,54.2,16.5,26.4,35.2,466.0,9.65,13.3,1.43
+59.4,32.2,55.7,97.3,37.5,19.5,30.2,331.0,11.3,18.4,6.15
+32.8,17.2,13.0,10.6,2.48,56.7,84.3,1685.0,26.7,49.6,31.1
+44.9,20.0,8.43,155.0,16.4,12.3,27.9,359.0,23.1,41.0,17.8
+81.3,16.7,7.04,141.0,33.7,7.99,11.8,730.0,37.2,58.8,17.2
+136.0,71.0,15.1,17.0,4.78,16.8,31.6,396.0,20.0,40.7,12.5
+23.5,16.3,3.19,1.0,445.0,10.6,18.3,389.0,28.1,46.1,17.9
+57.8,15.0,37.5,40.0,18.8,29.4,30.5,322.0,10.6,34.9,22.3
+40.7,16.1,16.5,12.5,3.02,17.6,31.9,843.0,61.5,85.1,25.5
+45.7,15.4,8.98,124.0,22.1,4.18,8.66,661.0,11.7,17.5,8.43
+6.73,20.0,10.4,143.0,25.3,32.2,38.2,478.0,26.7,47.4,19.1
+125.0,123.0,14.1,10.4,4.96,16.0,16.4,514.0,19.3,21.1,4.14
+85.1,33.4,12.4,50.0,20.2,10.6,19.6,898.0,16.7,34.3,1.35
+186.0,165.0,22.9,26.4,4.83,8.74,16.5,538.0,36.2,30.5,12.3
+52.3,38.9,3.75,18.3,26.2,7.77,12.4,313.0,16.0,34.9,58.8
+96.5,30.2,14.1,23.5,13.7,28.6,48.3,1124.0,13.7,19.8,5.05
+28.9,16.8,3.72,20.5,44.9,7.99,18.1,279.0,3.79,16.1,71.7
+105.0,40.3,11.3,18.4,13.9,14.7,27.1,359.0,28.4,30.5,7.17
+149.0,36.5,4.03,9.91,3.65,20.4,33.7,372.0,14.6,16.8,6.04
+21.5,6.67,17.9,89.8,31.6,39.2,55.2,257.0,16.4,22.7,10.6
+50.5,38.5,8.2,42.9,10.7,14.3,21.3,599.0,22.5,37.2,19.8
+100.0,48.7,7.5,17.0,16.3,16.3,23.5,300.0,12.3,11.1,2.71
+80.6,31.3,13.1,34.9,17.0,10.8,14.5,422.0,15.0,21.3,7.64
+56.7,26.7,9.22,15.1,2.57,6.26,9.73,352.0,38.2,54.7,30.5
+81.3,28.1,9.06,16.7,47.0,21.7,24.4,274.0,119.0,297.0,155.0
+44.9,22.9,9.47,14.7,17.3,11.8,30.8,466.0,13.2,17.9,4.49
+97.3,33.7,16.7,64.9,23.3,8.58,12.5,286.0,35.5,57.3,15.4
+61.0,31.9,17.8,16.4,10.1,13.3,28.1,1911.0,1.79,9.73,3.4
+64.4,33.1,20.2,578.0,82.8,7.77,18.9,368.0,1.84,17.8,76.4
+120.0,40.7,7.57,898.0,123.0,16.8,28.4,319.0,11.1,24.1,10.8
+20.7,6.61,16.0,16.4,9.47,3.62,21.3,874.0,17.5,22.5,5.05
+31.1,15.1,66.7,63.8,16.4,26.7,34.3,400.0,12.7,16.1,10.8
+25.5,28.1,5.23,7.17,42.2,64.9,104.0,1670.0,1.0,10.9,6.49
+69.8,23.7,5.19,14.6,47.4,28.6,69.8,491.0,22.5,26.2,7.64
+5.0,18.6,10.1,72.3,19.3,24.1,32.8,368.0,10.3,12.0,2.39
+72.3,41.4,21.3,34.9,12.3,5.0,14.9,433.0,15.8,17.2,11.0
+40.3,27.1,21.9,29.2,8.51,16.8,39.6,547.0,2.84,3.13,5.33
+7.99,29.4,10.4,62.1,4.45,12.4,21.3,441.0,54.7,96.5,48.3
+67.3,25.0,8.43,16.0,12.5,12.0,28.9,594.0,10.0,27.6,1.27
+59.9,19.5,1.0,213.0,5.28,2.44,9.06,188.0,26.7,31.9,13.1
+37.9,19.6,14.5,19.8,12.5,6.26,19.6,791.0,2.48,14.1,87.4
+73.0,37.9,43.3,68.5,11.5,21.3,48.7,1104.0,8.43,20.9,1.0
+75.0,28.6,33.4,57.8,15.3,25.5,40.7,407.0,13.3,20.2,5.67
+33.1,21.9,4.29,87.4,24.8,2.59,23.7,1084.0,16.7,28.4,8.2
+22.9,15.8,11.3,297.0,58.3,3.79,23.7,874.0,20.4,45.3,70.4
+11.3,17.6,7.91,18.4,55.2,23.7,82.0,939.0,12.9,13.0,7.91
+49.1,15.0,8.2,246.0,71.7,4.18,7.43,533.0,30.2,47.4,19.3
+37.9,38.5,4.45,60.4,22.5,3.37,20.2,491.0,20.4,29.4,5.19
+6.44,16.3,21.5,31.3,13.3,6.73,12.3,632.0,21.7,33.1,3.37
+56.2,29.4,42.2,13.1,49.6,3.37,8.74,389.0,3.75,5.78,4.57
+85.1,37.5,8.9,121.0,27.1,7.7,23.5,1114.0,22.5,42.9,2.81
+89.8,83.5,11.5,15.5,11.2,17.9,28.6,422.0,12.5,15.4,6.1
+74.3,32.2,14.2,15.3,11.4,13.3,30.0,500.0,2.76,6.49,11.9
+30.0,23.7,16.4,55.7,49.1,15.8,20.5,552.0,13.5,21.5,1.54
+106.0,25.5,6.85,34.3,35.2,6.38,29.4,931.0,9.56,17.9,7.99
+61.5,23.1,12.1,33.4,28.6,15.3,30.0,340.0,41.8,59.4,30.0
+85.8,20.5,135.0,422.0,250.0,22.3,46.1,1486.0,6.04,7.64,4.37
+47.8,17.9,19.5,55.2,41.8,19.8,28.9,426.0,14.7,21.3,10.7
+35.5,29.4,11.5,57.3,34.6,6.32,17.0,820.0,5.0,5.88,29.7
+48.3,19.1,10.1,25.5,31.9,11.2,24.6,514.0,2.11,16.7,94.7
+111.0,36.8,6.26,115.0,13.7,5.23,30.5,717.0,20.0,42.6,14.1
+53.3,20.9,22.3,35.2,10.6,3.92,26.7,764.0,16.0,28.4,9.91
+14.3,13.6,10.6,355.0,69.8,6.49,3.96,542.0,19.8,48.3,25.0
+39.6,11.1,16.0,43.7,53.8,25.3,44.1,496.0,14.3,26.2,19.6
+14.3,23.1,7.57,267.0,28.9,10.0,35.5,1433.0,19.3,34.6,9.82
+126.0,45.7,8.82,90.6,15.8,6.38,26.9,828.0,7.84,17.9,1.0
+31.9,17.3,12.4,20.4,5.42,7.91,9.82,770.0,12.7,17.2,6.67
+56.2,30.2,16.4,16.4,16.4,5.33,13.9,610.0,1.88,1.05,5.62
+131.0,85.1,1.54,126.0,11.8,5.0,16.4,514.0,20.0,27.1,8.2
+34.9,10.8,15.7,16.3,3.4,13.3,26.2,1009.0,21.5,42.6,9.31
+30.5,12.9,9.73,96.5,12.0,1.96,4.66,76.4,1.0,66.1,3.52
+8.66,20.9,9.73,14.7,35.5,10.0,16.1,528.0,2.64,42.9,75.7
+46.1,16.1,2.39,16.8,45.3,19.3,38.2,723.0,15.1,28.4,8.98
+59.4,33.1,14.2,10.4,9.31,12.0,27.9,276.0,17.6,7.84,2.79
+93.1,22.3,5.73,47.8,10.1,12.5,24.1,334.0,10.5,17.9,8.82
+38.5,22.5,5.78,74.3,23.3,10.6,13.0,835.0,15.8,23.3,7.57
+99.1,43.7,1.0,161.0,23.3,7.64,17.9,578.0,5.14,17.3,21.3
+76.4,22.7,10.1,71.7,24.4,38.5,88.2,500.0,20.9,24.1,13.2
+106.0,66.7,9.65,12.1,31.9,23.5,31.9,449.0,4.53,15.3,14.3
+112.0,28.1,10.8,28.6,15.8,21.1,35.5,410.0,23.9,35.2,9.73
+105.0,58.3,68.5,215.0,20.7,2.5,30.0,820.0,9.14,13.9,1.83
+94.7,26.2,7.91,118.0,27.9,12.5,24.6,523.0,9.06,10.0,1.7
+87.4,153.0,9.91,42.9,6.73,23.5,31.1,334.0,12.7,20.2,12.5
+120.0,41.0,15.0,57.8,24.6,20.9,32.8,379.0,1.0,18.9,97.3
+52.3,25.0,9.82,119.0,16.3,24.4,92.2,1582.0,2.41,12.4,58.3
+19.5,26.4,7.5,21.5,93.9,3.46,13.7,882.0,22.5,41.8,13.0
+92.2,28.9,9.06,3.46,23.3,15.3,31.1,429.0,10.8,9.39,1.95
+133.0,52.8,4.41,93.1,31.6,2.27,11.3,956.0,18.1,25.0,6.1
+31.6,16.7,12.2,17.5,14.9,6.73,21.3,806.0,7.77,9.82,12.4
+57.8,19.6,13.5,33.4,6.61,44.9,79.1,931.0,15.8,21.7,13.7
+70.4,25.5,3.31,11.7,5.78,20.2,25.9,284.0,30.8,59.4,12.6
+66.7,23.5,1.0,124.0,14.9,11.5,17.2,461.0,37.5,59.4,21.3
+31.6,12.4,30.5,53.3,15.7,17.5,35.5,331.0,23.7,36.5,9.65
+86.6,24.1,4.57,15.8,18.8,30.8,56.2,737.0,11.4,17.8,3.72
+118.0,31.9,15.7,15.5,26.4,4.0,16.8,632.0,9.91,11.1,7.3
+61.5,16.8,5.23,105.0,22.9,5.73,27.6,396.0,25.0,25.9,5.94
+34.9,16.1,11.8,46.6,20.5,16.8,15.4,343.0,14.3,22.5,9.14
+28.6,17.5,7.57,94.7,6.85,20.9,72.3,115.0,6.04,52.3,67.9
+25.5,12.4,23.1,38.5,15.5,25.5,36.5,426.0,13.0,20.2,13.2
+31.3,28.6,13.3,7.23,1.12,2.17,9.65,262.0,12.2,2.89,4.74
+115.0,39.2,7.5,66.1,11.2,22.7,27.6,250.0,36.2,57.8,16.5
+76.4,41.4,18.4,281.0,68.5,9.22,21.5,667.0,16.4,29.4,14.2
+99.1,28.6,8.9,186.0,10.6,19.3,32.8,737.0,25.5,26.9,7.57
+74.3,21.1,3.46,10.1,25.0,13.7,16.7,487.0,10.3,12.3,10.6
+93.1,31.1,10.6,137.0,23.5,16.3,25.7,422.0,9.65,23.1,5.14
+10.1,22.3,21.3,35.5,15.5,4.53,9.31,359.0,13.0,27.1,17.0
+27.6,39.2,10.5,12.3,3.52,7.84,17.3,730.0,5.28,34.0,142.0
+12.6,20.5,10.8,227.0,28.9,13.0,25.5,514.0,14.6,20.2,19.3
+100.0,28.4,27.1,215.0,67.3,26.2,30.8,331.0,25.7,37.5,10.6
+23.7,23.9,1.0,407.0,43.3,5.78,17.6,1459.0,11.9,20.7,3.65
+75.0,24.8,9.91,16.5,88.2,15.8,31.1,429.0,1.72,2.64,2.71
+54.7,46.6,17.9,24.1,17.0,25.0,33.4,337.0,18.3,27.6,6.49
+52.8,28.6,5.83,92.2,17.6,8.2,13.6,685.0,18.3,24.6,11.8
+73.0,20.5,16.5,8.98,5.78,14.9,34.3,271.0,3.49,2.35,7.5
+27.9,17.5,5.62,10.5,36.8,33.1,44.5,632.0,16.3,26.4,13.0
+89.0,77.7,14.9,25.3,34.6,11.8,22.9,441.0,1.0,8.51,9.65
+11.2,1.83,15.1,24.8,61.0,4.57,20.4,638.0,15.8,19.8,6.85
+112.0,32.8,18.4,30.5,7.64,8.35,12.3,441.0,17.6,21.1,4.07
+28.9,20.4,18.3,25.3,11.8,5.14,20.5,23.1,20.0,26.9,14.6
+12.7,13.7,18.6,55.2,23.5,9.22,15.0,649.0,16.3,17.8,5.28
+59.9,24.6,14.5,67.3,21.5,29.4,48.3,466.0,18.9,24.8,1.81
+29.4,16.7,5.09,26.7,49.1,5.23,28.1,723.0,5.23,10.0,39.6
+47.4,33.4,12.7,289.0,59.4,12.9,31.6,523.0,6.55,11.1,22.1
+13.6,8.74,13.0,39.2,25.0,18.4,30.2,379.0,15.7,37.9,8.74
+106.0,108.0,4.66,10.9,21.9,10.6,22.9,396.0,32.8,48.7,20.2
+39.6,13.2,9.14,66.1,5.47,12.4,25.7,496.0,18.8,28.6,8.74
+88.2,54.7,5.47,15.8,4.03,10.5,29.4,649.0,3.43,22.7,61.5
+29.4,16.1,10.3,21.1,2.89,10.6,20.5,449.0,4.14,7.17,4.7
+72.3,48.3,14.6,103.0,24.4,26.7,40.3,396.0,17.6,23.3,2.81
+36.8,13.7,10.9,170.0,18.1,16.1,39.6,457.0,20.5,25.5,6.32
+109.0,45.3,13.7,16.5,11.1,11.5,22.3,528.0,3.13,7.64,27.4
+27.4,19.8,25.5,528.0,93.1,20.9,37.5,385.0,3.55,16.0,106.0
+25.9,30.2,6.67,289.0,13.6,9.31,20.2,583.0,19.6,34.3,12.9
+16.0,7.77,1.0,239.0,30.2,11.7,20.4,562.0,1.36,1.27,1.06
+118.0,56.7,13.2,24.8,38.2,58.8,85.1,799.0,13.7,20.7,8.43
+36.5,18.1,9.06,120.0,32.8,3.37,24.6,154.0,13.7,19.3,6.1
+35.5,14.6,8.06,10.4,14.5,24.4,32.8,352.0,19.8,34.0,12.2
+34.3,16.8,14.5,17.3,12.3,54.2,135.0,2813.0,11.8,30.2,139.0
+13.8,19.3,15.4,85.8,19.1,20.7,53.3,717.0,3.68,22.1,67.9
+66.1,22.3,4.49,161.0,33.4,34.0,53.3,343.0,16.1,39.6,18.8
+32.2,14.9,14.6,10.7,8.82,14.1,26.2,328.0,12.9,21.1,5.57
+8.74,19.8,8.43,56.2,29.7,15.3,19.1,429.0,37.9,67.9,27.6
+103.0,23.9,9.22,173.0,470.0,15.8,34.3,235.0,18.9,41.4,12.7
+98.2,33.4,10.0,18.4,21.1,10.3,15.8,615.0,1.0,31.1,2.19
+25.0,14.6,36.8,43.3,13.9,12.5,16.0,567.0,14.3,17.6,6.67
+110.0,36.8,32.8,44.9,7.04,8.28,17.6,129.0,9.06,8.06,5.14
+58.3,18.8,13.5,27.9,12.2,13.1,25.3,1877.0,31.6,47.4,13.8
+20.9,8.2,13.8,15.0,8.58,18.9,31.9,346.0,16.5,19.3,1.43
+105.0,58.8,12.1,41.0,44.1,11.1,26.2,552.0,13.0,25.3,5.42
+64.9,29.4,17.8,109.0,34.3,4.33,9.73,379.0,15.1,13.6,2.84
+88.2,25.0,46.1,62.1,8.82,6.79,12.9,851.0,15.3,26.2,7.17
+69.2,18.1,5.14,121.0,24.4,8.58,37.2,186.0,20.0,23.3,14.7
+51.9,28.6,13.9,16.3,7.77,30.2,58.8,1715.0,21.5,28.1,3.0
+28.4,20.4,16.1,12.4,2.35,5.52,17.0,316.0,18.6,27.1,5.99
+45.3,21.5,15.4,115.0,29.4,3.96,60.4,757.0,8.06,13.7,21.3
+157.0,73.7,10.9,16.0,40.7,10.7,18.4,334.0,23.1,34.0,6.32
+31.6,24.6,13.7,9.82,7.99,2.37,7.04,117.0,28.1,40.3,14.5
+139.0,37.5,54.2,80.6,20.5,8.74,25.3,379.0,11.1,17.2,6.1
+56.7,33.7,3.22,141.0,38.9,5.52,26.2,514.0,1.42,90.6,8.43
+79.9,31.9,15.0,24.6,20.9,23.5,85.8,973.0,8.28,20.4,1.0
+49.6,11.1,9.39,14.9,1.0,2.29,7.84,552.0,19.3,36.2,14.7
+79.1,30.8,5.73,120.0,25.7,37.2,48.3,649.0,11.2,13.7,4.91
+36.5,21.7,42.6,71.7,12.6,11.1,22.7,375.0,15.7,29.4,11.1
+50.0,13.0,2.55,11.0,37.5,3.16,10.0,176.0,18.3,31.1,9.65
+20.7,33.7,15.4,15.3,12.7,32.8,50.0,470.0,10.5,14.7,3.75
+58.8,22.5,15.5,23.3,17.5,4.87,6.26,274.0,15.3,23.9,4.66
+52.3,14.6,6.67,82.0,8.13,8.13,19.8,533.0,4.22,13.9,14.9
+86.6,29.7,11.9,65.5,12.3,27.4,47.4,227.0,11.7,21.1,2.33
+91.4,55.2,8.2,21.7,11.7,19.1,34.0,418.0,11.9,15.5,9.47
+32.5,14.5,11.9,16.5,48.3,22.1,38.9,343.0,3.28,27.9,87.4
+57.8,32.5,13.0,93.9,23.1,4.53,32.2,2247.0,28.9,26.2,1.0
+65.5,19.8,9.31,22.3,22.7,20.4,45.3,939.0,12.0,21.7,5.33
+64.9,22.9,13.2,31.9,4.14,13.7,44.5,1298.0,11.4,25.9,12.4
+5.67,17.8,19.6,20.5,7.1,14.5,25.9,717.0,21.9,34.9,8.06
+57.8,32.5,8.9,12.2,6.04,6.92,36.8,62.6,7.5,12.7,5.99
+189.0,153.0,13.6,21.1,5.94,21.9,29.7,253.0,18.1,27.6,6.32
+31.9,26.9,23.7,51.4,22.7,6.61,10.9,573.0,29.4,42.6,13.1
+30.0,11.0,7.5,14.9,16.0,26.4,41.8,685.0,19.3,33.7,9.06
+16.4,13.9,4.57,138.0,24.4,11.8,35.2,1322.0,16.0,18.4,9.82
+46.6,18.3,33.7,65.5,4.87,21.1,35.2,429.0,15.0,37.5,21.7
+27.6,21.1,22.3,20.7,31.9,6.1,28.4,679.0,9.39,50.0,98.2
+62.6,18.4,7.57,23.3,7.77,6.15,9.82,255.0,1.18,24.8,1.46
+92.2,47.0,18.9,16.5,4.78,1.08,4.74,25.3,7.04,43.7,106.0
+50.9,30.2,1.43,340.0,55.7,10.6,19.1,340.0,37.5,69.2,17.0
+53.8,14.7,31.9,46.1,13.6,21.9,51.4,914.0,10.4,20.2,7.3
+102.0,30.8,9.06,95.6,18.6,4.18,17.2,621.0,5.99,15.5,4.87
+72.3,39.2,21.1,14.6,20.4,6.55,12.2,478.0,14.1,20.7,10.6
+86.6,31.1,27.9,98.2,37.2,13.8,18.4,149.0,15.4,21.5,8.66
+110.0,35.2,56.2,111.0,34.9,7.04,15.8,407.0,14.7,5.33,7.99
+42.6,24.1,6.1,20.4,49.6,4.66,13.3,466.0,14.7,14.1,1.65
+9.91,25.5,12.3,23.9,47.0,20.7,30.0,396.0,6.73,18.6,47.8
+106.0,54.2,7.23,16.5,63.2,3.52,4.26,379.0,18.6,27.4,5.52
+34.9,17.2,12.4,32.8,15.0,13.6,21.7,594.0,10.3,16.0,2.84
+4.22,7.57,1.67,437.0,73.0,6.04,13.2,375.0,8.9,20.2,4.37
+54.2,24.4,31.9,38.5,8.82,4.0,8.58,122.0,17.5,22.9,3.55
+36.5,14.5,6.49,53.8,19.8,5.19,9.39,253.0,9.65,8.9,3.75
+75.7,18.9,39.2,34.0,9.82,6.92,20.4,429.0,12.5,17.0,4.45
+29.4,22.3,5.99,92.2,14.3,17.5,33.7,355.0,20.2,18.1,2.09
+49.6,16.1,17.9,21.9,13.1,7.5,37.5,698.0,14.2,24.6,7.99
+4.74,18.9,5.88,183.0,33.7,19.3,30.2,375.0,21.5,28.6,13.5
+56.2,37.2,12.1,75.7,31.1,16.8,36.5,375.0,13.3,7.64,4.83
+85.1,28.6,1.0,164.0,2.64,11.0,19.6,375.0,5.88,4.74,3.68
+14.2,15.4,12.4,14.1,10.2,2.62,11.5,385.0,18.6,36.2,18.8
+120.0,57.3,11.4,39.2,58.8,20.2,22.3,325.0,13.8,35.5,93.9
+46.6,20.7,19.1,26.2,16.3,21.1,32.8,407.0,63.2,88.2,27.4
+29.7,20.7,12.1,253.0,43.7,9.31,19.3,1155.0,13.2,26.2,10.8
+79.9,26.2,2.92,45.3,6.92,10.6,25.9,519.0,20.4,27.9,4.87
+15.7,29.7,42.6,83.5,51.9,18.6,77.0,4914.0,16.7,27.6,13.6
+149.0,110.0,23.9,79.9,82.0,7.64,30.8,1382.0,15.8,25.0,9.56
+85.8,23.9,27.6,34.3,17.0,19.5,27.6,305.0,13.5,16.5,10.4
+52.3,37.2,17.6,33.7,15.5,6.21,23.1,956.0,13.8,17.9,7.64
+160.0,157.0,16.7,153.0,25.3,25.7,32.5,313.0,23.3,28.1,3.82
+99.1,19.6,8.82,17.9,40.0,22.9,40.7,429.0,13.0,15.0,1.0
+31.3,19.1,8.51,22.1,17.9,17.8,33.7,355.0,10.7,18.6,6.79
+14.3,22.1,18.4,11.4,1.68,22.5,39.2,426.0,8.9,17.3,3.19
+88.2,52.8,9.47,14.6,8.28,34.9,56.7,400.0,20.9,38.9,14.2
+38.9,20.2,15.7,16.3,1.29,9.14,75.7,1433.0,33.1,50.9,8.98
+175.0,49.1,7.84,7.77,26.2,17.3,34.0,313.0,14.2,14.6,2.97
+125.0,61.0,23.1,41.4,10.5,8.98,61.0,874.0,13.9,15.7,2.97
+26.4,13.7,16.7,98.2,21.3,11.5,30.8,470.0,4.1,36.5,147.0
+54.2,22.3,9.47,149.0,14.3,13.5,22.9,956.0,2.48,3.0,3.62
+13.2,6.79,6.21,149.0,27.6,32.8,50.9,418.0,25.3,26.9,10.0
+20.0,23.1,5.62,125.0,42.2,44.5,89.0,1860.0,5.19,14.3,3.43
+32.8,20.9,9.65,58.8,11.5,11.7,18.6,552.0,12.7,17.3,11.4
+30.5,48.3,10.5,54.2,16.0,14.7,32.8,491.0,16.8,19.3,9.31
+75.7,28.6,3.28,10.7,7.3,20.9,34.9,328.0,13.9,28.6,6.67
+50.5,20.0,13.3,179.0,27.9,10.5,28.1,1165.0,1.0,15.8,1.0
+34.9,20.4,15.3,20.7,14.7,32.5,57.8,1055.0,16.4,21.1,6.98
+30.8,12.3,14.6,13.8,2.11,4.37,18.6,368.0,2.97,1.0,2.27
+56.2,27.4,8.98,141.0,31.3,10.7,21.1,505.0,13.6,15.5,5.05
+16.3,9.31,17.6,25.3,62.1,10.3,33.7,441.0,1.32,5.78,6.85
+18.9,5.94,11.5,172.0,25.7,2.07,13.8,528.0,7.57,11.2,12.0
+49.1,9.91,13.8,23.3,44.5,8.13,46.6,259.0,22.3,39.6,25.9
+20.4,15.0,2.17,257.0,20.4,4.53,8.82,31.9,10.7,11.5,13.3
+23.9,33.7,23.7,17.9,11.1,9.06,16.0,567.0,13.9,15.5,7.64
+71.0,22.3,18.9,20.7,10.0,28.4,36.8,858.0,10.2,5.67,5.38
+27.4,24.1,10.0,21.5,17.5,12.1,27.1,599.0,19.6,36.8,8.35
+25.3,28.4,13.0,16.3,38.5,6.1,16.8,655.0,6.04,20.0,121.0
+12.6,26.2,11.1,63.8,28.4,11.4,62.6,457.0,18.6,94.7,514.0
+165.0,37.5,16.7,72.3,27.1,14.1,20.2,244.0,15.3,15.1,1.89
+64.4,26.9,34.3,36.2,30.5,5.33,57.3,1000.0,16.7,28.6,16.0
+36.8,8.35,5.0,131.0,20.7,6.44,38.9,791.0,21.3,27.6,7.43
+84.3,48.3,1.0,294.0,21.3,33.4,52.3,453.0,22.7,24.4,7.64
+8.66,22.5,8.74,31.6,46.6,13.9,25.0,626.0,29.4,34.0,1.93
+7.57,4.91,8.58,18.8,117.0,10.7,17.3,470.0,14.3,21.3,17.5
+30.5,37.5,4.33,16.5,23.9,4.37,14.9,250.0,3.25,1.17,6.49
+7.91,21.7,7.99,165.0,46.1,22.5,36.8,437.0,20.2,20.9,8.43
+7.17,16.3,2.79,11.5,11.5,20.0,27.9,466.0,31.3,71.0,24.6
+106.0,34.3,1.0,209.0,31.6,9.47,15.5,422.0,9.39,10.8,10.2
+23.5,13.6,40.7,372.0,37.9,4.96,14.1,851.0,9.14,30.0,85.8
+16.5,14.7,14.9,79.9,37.9,2.76,6.98,213.0,1.81,8.43,51.4
+17.8,18.9,15.3,396.0,48.7,25.0,52.3,750.0,16.3,49.1,75.7
+5.88,8.51,28.9,26.2,7.3,73.0,112.0,1219.0,1.0,20.7,47.4
+17.3,18.9,14.6,19.1,5.14,16.5,32.2,710.0,1.0,1.0,30.2
+47.4,40.0,20.9,21.7,15.8,81.3,121.0,1877.0,7.3,28.1,93.1
+10.6,12.7,11.0,124.0,22.5,11.5,37.5,770.0,6.73,27.1,60.4
+10.3,15.0,37.2,34.9,14.6,89.0,133.0,407.0,15.1,46.1,85.1
+13.7,16.5,4.83,18.4,1.22,21.9,27.4,610.0,2.05,19.1,75.7
+25.5,17.9,22.3,17.2,17.5,13.7,23.1,604.0,31.3,45.7,72.3
+13.2,15.7,60.4,389.0,59.9,26.2,41.4,359.0,1.0,2.41,37.9
+63.8,50.9,32.5,23.9,4.03,151.0,248.0,3619.0,15.0,33.4,41.8
+17.0,16.8,22.5,22.3,12.5,12.0,22.5,547.0,17.6,24.6,36.5
+49.6,71.0,23.9,13.0,10.0,113.0,204.0,3308.0,15.3,67.9,340.0
+20.4,18.6,54.2,322.0,54.7,51.4,75.7,235.0,20.2,37.9,45.7
+14.5,13.0,26.4,18.1,9.31,41.0,75.7,638.0,1.0,2.21,42.6
+36.8,22.9,5.73,1.0,15.4,36.2,62.1,1794.0,17.6,33.7,41.8
+14.9,34.3,20.7,18.8,8.82,106.0,163.0,2642.0,31.9,95.6,113.0
+102.0,81.3,6.1,26.4,23.9,123.0,217.0,1843.0,3.85,5.78,44.9
+16.4,25.7,59.9,71.7,16.5,183.0,257.0,1811.0,4.41,31.6,81.3
+22.9,15.0,3.72,1.01,9.73,89.0,126.0,368.0,1.95,5.88,21.3
+80.6,86.6,64.9,294.0,27.1,47.0,61.0,491.0,23.1,38.2,52.8
+9.31,6.44,22.7,16.7,18.8,123.0,202.0,3220.0,1.14,3.28,46.1
+14.2,10.0,86.6,466.0,93.9,37.9,54.2,445.0,42.6,90.6,400.0
+19.3,13.8,21.3,30.8,15.5,4.7,42.9,538.0,14.1,31.9,48.3
+33.4,19.6,14.2,19.3,12.7,158.0,213.0,334.0,17.8,31.3,34.9
+38.5,27.1,34.0,31.6,3.62,114.0,202.0,2017.0,33.4,77.7,167.0
+59.4,75.0,22.7,29.2,3.75,32.2,42.6,615.0,3.37,17.6,80.6
+15.3,16.7,12.2,239.0,28.1,5.33,7.99,328.0,14.6,22.7,8.06
+21.7,32.5,20.7,34.3,5.57,97.3,175.0,2642.0,30.8,55.2,76.4
+30.0,14.9,22.3,35.5,2.46,137.0,316.0,5829.0,1.0,14.1,13.2
+31.6,13.0,26.4,37.2,1.0,23.1,35.2,1275.0,6.38,5.33,50.5
+18.8,11.1,71.0,466.0,64.4,20.0,39.6,615.0,14.9,44.5,110.0
+7.64,28.1,6.79,18.1,7.77,47.0,64.4,1104.0,23.7,45.7,44.9
+40.7,59.9,1.86,4.41,3.19,29.2,43.3,644.0,25.7,40.0,53.8
+21.9,28.1,84.3,403.0,76.4,125.0,186.0,1568.0,4.1,9.47,30.5
+51.4,22.1,94.7,117.0,17.6,76.4,102.0,947.0,8.58,25.7,129.0
+30.5,15.5,53.3,142.0,19.1,77.7,151.0,2738.0,94.7,179.0,328.0
+8.9,13.3,74.3,359.0,54.2,7.77,21.7,519.0,10.6,7.37,43.3
+37.2,19.1,11.8,19.8,7.17,8.9,17.0,588.0,1.0,1.0,44.5
+13.8,9.56,16.7,146.0,19.3,175.0,223.0,661.0,10.4,42.2,70.4
+11.1,25.0,85.1,552.0,93.9,20.9,35.9,331.0,18.3,22.5,32.2
+17.2,6.79,28.9,29.2,11.1,11.4,30.8,552.0,3.75,4.33,44.9
+61.5,93.1,17.0,21.1,1.01,4.26,15.1,599.0,23.9,38.5,106.0
+17.2,13.7,57.3,97.3,31.3,37.5,66.7,2329.0,8.74,2.33,35.2
+16.8,46.1,18.6,63.2,11.8,18.9,31.9,649.0,8.2,23.5,50.9
+12.1,10.5,21.3,18.9,4.26,176.0,483.0,8354.0,15.1,9.06,53.8
+17.3,26.4,82.8,414.0,106.0,40.0,64.9,1018.0,13.0,20.9,27.6
+21.5,22.3,73.0,519.0,87.4,3.72,12.3,851.0,1.31,33.1,10.9
+25.7,15.8,34.3,37.5,2.89,5.23,20.2,422.0,1.0,64.4,8.28
+13.1,11.7,21.7,132.0,42.2,36.5,49.1,542.0,1.08,5.88,13.2
+44.1,29.2,39.6,119.0,63.2,36.8,47.8,365.0,3.52,6.79,30.2
+38.2,14.2,7.1,28.1,8.98,172.0,233.0,1075.0,8.58,25.7,57.3
+32.2,35.2,35.9,276.0,61.0,44.9,62.6,418.0,8.43,32.8,77.0
+34.6,18.8,54.2,313.0,54.7,16.1,34.3,704.0,1.0,13.7,8.06
+4.96,12.6,47.8,57.8,19.6,3.43,19.1,655.0,19.5,42.9,62.6
+28.4,31.9,59.4,257.0,57.3,6.26,17.2,382.0,10.5,18.9,57.3
+69.8,50.0,20.7,19.5,12.3,59.4,104.0,337.0,34.3,72.3,139.0
+32.2,21.3,104.0,519.0,87.4,45.7,61.5,1286.0,22.1,34.3,42.6
+30.0,32.5,17.0,22.1,7.5,49.6,86.6,1124.0,23.1,40.0,47.0
+40.7,19.5,1.26,1.07,1.55,77.7,81.3,279.0,7.7,13.0,64.9
+22.1,17.2,33.1,14.6,17.0,26.9,27.4,433.0,25.5,62.6,231.0
+23.3,12.0,55.2,262.0,64.9,12.3,59.9,3023.0,17.0,27.1,50.5
+24.6,19.5,20.9,17.2,13.1,3.85,14.5,1208.0,11.4,15.7,77.0
+73.0,93.9,27.9,29.7,1.01,89.0,132.0,1762.0,11.9,28.4,12.1
+23.1,10.7,17.8,80.6,3.68,22.3,30.8,483.0,8.66,28.4,48.3
+20.7,12.7,20.9,25.5,9.82,17.9,25.0,632.0,3.85,7.99,46.1
+14.1,9.31,18.3,3.37,29.4,112.0,161.0,939.0,8.51,16.3,46.1
+16.1,6.26,20.2,17.3,8.82,75.0,125.0,1894.0,19.1,37.5,63.8
+22.1,15.8,21.3,32.2,8.98,3.85,22.3,328.0,1.47,7.23,48.7
+44.9,45.7,16.1,16.8,10.3,29.2,94.7,1715.0,32.8,66.7,137.0
+62.6,52.3,35.9,233.0,49.1,167.0,271.0,2207.0,6.85,12.2,44.1
+45.3,62.6,21.3,17.5,15.7,65.5,95.6,1433.0,13.0,26.4,36.2
+19.5,20.2,24.8,30.2,10.4,19.6,43.3,573.0,2.69,4.57,7.77
+17.8,16.3,14.3,85.8,17.0,20.5,33.1,922.0,43.7,62.1,62.1
+14.2,13.9,18.9,19.5,8.43,66.1,154.0,2329.0,18.6,40.7,68.5
+77.0,43.3,53.3,284.0,60.4,56.2,110.0,1762.0,22.1,24.8,81.3
+6.44,18.3,15.7,41.4,13.1,44.1,56.2,750.0,35.5,59.4,76.4
+14.3,18.4,5.05,1.75,8.13,31.1,58.8,407.0,18.8,47.0,48.7
+30.2,54.7,40.0,211.0,41.4,14.9,32.5,588.0,5.99,15.0,45.3
+13.5,21.9,35.5,40.7,7.91,44.9,103.0,3460.0,1.18,18.6,58.3
+93.9,52.3,30.8,31.3,14.6,74.3,137.0,1794.0,9.39,24.6,92.2
+24.6,9.65,37.5,40.3,18.1,35.5,130.0,2763.0,36.8,49.6,59.9
+19.8,11.7,23.5,16.7,15.1,3.37,19.3,470.0,13.7,31.1,56.7
+30.2,19.8,24.4,19.8,1.0,50.0,72.3,673.0,37.2,62.1,91.4
+18.1,23.7,7.77,41.8,26.2,42.9,54.2,538.0,10.6,47.0,81.3
+13.8,13.2,32.5,46.6,15.0,104.0,172.0,1747.0,20.4,30.8,63.2
+19.1,14.6,22.9,32.8,11.4,78.4,127.0,1596.0,13.6,29.4,30.0
+20.0,16.3,26.7,176.0,10.0,106.0,168.0,2571.0,9.39,8.28,13.9
+23.1,11.5,14.5,42.6,103.0,119.0,204.0,2480.0,58.3,67.3,13.2
+25.3,28.6,18.3,61.5,16.4,18.4,24.1,717.0,6.73,66.1,132.0
+25.0,20.5,31.1,445.0,55.2,40.0,57.8,359.0,11.8,20.4,55.7
+17.0,7.04,21.7,24.4,8.66,33.1,44.1,750.0,13.5,37.9,37.9
+29.7,22.3,20.0,17.2,1.38,121.0,219.0,1999.0,7.37,22.5,37.5
+22.5,17.5,23.9,77.7,17.5,35.2,56.2,340.0,4.37,26.7,47.4
+61.0,33.1,37.9,311.0,48.7,137.0,352.0,4698.0,47.0,85.8,157.0
+17.3,10.1,28.1,27.9,3.28,44.9,66.1,403.0,7.17,23.7,42.9
+129.0,109.0,41.8,161.0,48.7,5.09,15.1,644.0,16.3,39.2,88.2
+21.3,16.4,21.1,22.5,16.5,3.46,25.3,578.0,7.17,36.2,48.3
+91.4,41.4,24.8,319.0,38.9,17.9,30.5,956.0,18.6,34.3,79.1
+14.7,22.3,27.6,35.9,13.5,9.39,20.5,382.0,1.0,12.9,13.8
+19.3,10.1,5.38,4.1,2.25,7.77,17.0,982.0,9.22,24.8,49.6
+28.4,21.7,38.2,170.0,37.2,29.7,39.6,692.0,9.22,17.5,69.2
+72.3,76.4,17.9,15.5,16.1,63.2,109.0,947.0,25.0,82.8,205.0
+6.55,10.2,16.8,22.9,1.0,82.8,113.0,679.0,14.5,20.7,59.9
+12.5,5.23,69.8,131.0,50.0,21.7,31.3,414.0,10.2,74.3,3.59
+32.8,18.3,23.5,23.1,3.31,53.8,85.1,610.0,10.5,35.5,53.3
+19.1,10.3,20.5,78.4,18.1,26.2,35.2,505.0,6.15,17.9,54.7
+24.6,11.8,30.0,30.8,14.6,32.8,48.3,362.0,3.19,3.19,50.9
+16.8,13.6,75.7,123.0,46.1,6.44,37.9,1000.0,12.2,20.5,18.3
+7.17,17.0,23.7,23.3,5.33,25.7,41.0,491.0,14.7,28.6,54.7
+19.1,13.9,15.8,74.3,21.9,24.1,34.3,474.0,9.39,27.6,39.6
+20.5,20.9,17.3,120.0,15.3,11.7,24.1,644.0,9.06,16.1,50.9
+18.4,19.8,12.7,81.3,11.3,6.21,44.1,496.0,84.3,119.0,41.0
+20.9,8.82,20.7,300.0,31.3,19.5,37.2,542.0,18.6,29.2,49.1
+14.9,15.0,17.6,170.0,24.1,22.7,32.2,453.0,18.6,31.1,79.9
+16.1,14.3,8.9,42.9,21.1,17.0,30.2,698.0,9.91,21.1,38.5
+12.3,13.8,4.07,1.01,1.65,26.4,37.5,784.0,1.2,28.1,27.1
+26.9,20.2,19.5,170.0,23.3,8.51,15.4,487.0,32.5,67.3,118.0
+131.0,95.6,12.3,189.0,16.5,36.8,62.1,1084.0,22.1,33.7,69.8
+62.1,71.0,8.9,4.45,9.56,4.41,17.3,655.0,60.4,146.0,209.0
+30.0,10.3,26.7,22.1,15.4,11.3,21.1,552.0,5.42,13.0,34.3
+52.8,39.2,17.2,161.0,19.5,4.83,20.0,410.0,8.66,19.3,29.7
+75.0,52.8,42.2,259.0,39.6,20.4,41.4,692.0,17.8,58.3,60.4
+32.2,14.3,25.3,24.4,3.85,9.56,29.2,1275.0,14.3,21.7,38.9
+18.3,19.8,14.3,18.6,1.88,1.76,1.01,93.9,11.1,26.2,41.8
+13.7,25.3,14.6,147.0,13.9,18.8,46.6,777.0,57.3,131.0,181.0
+27.6,18.1,35.5,340.0,26.9,17.9,30.0,379.0,7.7,39.6,42.9
+17.0,10.9,22.7,67.3,13.5,34.0,47.4,626.0,26.4,24.1,85.8
+26.4,37.2,41.4,183.0,33.7,103.0,175.0,1395.0,15.7,29.7,59.9
+19.8,20.4,21.9,25.5,2.59,67.9,104.0,407.0,1.35,28.1,47.8
+7.23,38.9,90.6,418.0,73.0,26.9,36.8,262.0,7.37,16.7,35.5
+145.0,88.2,21.3,30.8,12.9,158.0,264.0,3460.0,15.0,28.4,49.6
+34.9,20.4,58.8,474.0,69.8,34.9,43.7,407.0,13.0,29.4,30.2
+31.3,19.1,20.7,110.0,27.1,41.0,83.5,813.0,25.7,39.2,58.8
+19.5,16.3,25.5,19.3,2.71,26.2,31.6,644.0,18.6,42.2,49.6
+19.5,15.1,14.5,13.6,3.62,13.2,29.4,519.0,35.2,69.8,48.3
+20.9,20.2,1.0,92.2,14.5,52.8,76.4,1186.0,17.9,23.5,48.3
+22.1,11.8,8.58,10.1,11.9,22.7,33.7,491.0,20.5,16.1,53.3
+25.7,11.4,21.7,19.5,4.78,4.1,25.5,340.0,10.6,13.6,50.0
+30.8,20.0,36.5,48.7,4.45,43.7,66.7,1084.0,31.3,67.9,225.0
+53.3,44.5,13.9,99.1,5.94,14.2,36.2,673.0,1.0,18.3,48.3
+16.5,12.4,27.6,26.2,1.0,4.18,19.3,791.0,17.6,28.1,54.2
+17.8,17.0,26.7,15.5,4.7,21.5,38.9,1065.0,5.73,30.5,12.3
+73.7,39.6,25.7,30.5,17.2,54.7,81.3,604.0,31.6,55.2,111.0
+95.6,65.5,158.0,392.0,93.1,17.2,36.5,514.0,57.3,133.0,188.0
+56.7,50.5,17.9,209.0,16.7,3.25,27.1,264.0,10.5,15.1,56.2
+32.8,6.85,47.4,368.0,59.4,36.8,54.7,626.0,23.1,30.0,63.2
+24.6,33.4,10.6,64.4,12.5,9.22,45.7,730.0,10.0,25.3,30.0
+24.6,17.5,27.9,18.1,19.1,14.9,26.9,496.0,40.0,55.2,85.1
+27.9,9.91,117.0,514.0,73.0,57.8,90.6,1176.0,14.3,31.1,39.2
+34.3,15.8,7.23,1.41,3.68,2.64,14.3,429.0,21.5,48.7,28.1
+23.9,20.2,63.8,385.0,69.2,6.67,14.6,604.0,13.6,32.5,51.4
+17.3,7.3,17.6,16.0,11.3,1.54,7.04,63.8,10.5,14.2,40.7
+20.7,11.9,77.7,294.0,79.9,6.61,19.5,478.0,9.82,24.6,109.0
+27.6,19.5,41.8,101.0,18.1,14.5,24.6,533.0,6.61,26.2,48.7
+11.1,6.73,15.8,19.8,8.82,5.57,32.5,621.0,16.3,26.2,62.6
+17.8,13.3,22.9,13.1,3.34,102.0,172.0,3338.0,6.73,27.1,54.2
+13.6,13.9,24.4,23.1,9.31,41.8,61.5,704.0,13.9,28.9,37.2
+6.32,12.3,22.5,27.4,7.3,4.87,16.8,368.0,21.7,28.6,68.5
+15.0,20.7,25.0,24.6,5.88,106.0,176.0,3023.0,12.1,18.6,35.2
+27.1,12.5,20.9,131.0,19.6,54.7,83.5,1075.0,22.3,36.5,118.0
+11.2,7.17,20.2,20.7,8.51,31.1,44.9,470.0,18.8,50.9,89.0
+31.1,38.5,20.0,20.9,3.55,4.33,21.7,562.0,13.8,43.3,77.7
+77.7,154.0,25.3,20.9,1.14,8.28,34.9,931.0,17.3,43.7,58.3
+18.8,23.7,37.9,42.2,12.7,32.5,38.5,449.0,4.53,6.61,7.23
+21.1,21.5,21.7,26.4,3.05,23.7,37.5,349.0,47.0,124.0,31.6
+28.6,18.8,14.5,17.9,8.66,30.5,43.7,422.0,11.8,40.0,52.8
+59.9,44.9,25.9,155.0,48.3,13.3,23.7,478.0,15.4,44.1,46.1
+17.9,5.88,19.3,14.6,8.2,13.9,26.2,610.0,20.5,21.1,44.5
+45.7,26.9,65.5,250.0,49.1,21.1,44.5,638.0,15.1,21.1,53.3
+38.5,21.5,21.9,23.1,5.0,26.7,44.1,500.0,14.2,33.1,52.3
+81.3,77.7,31.3,21.3,8.82,20.0,35.5,466.0,8.82,25.0,42.6
+12.1,7.57,18.9,22.3,8.2,5.14,22.1,626.0,3.85,16.0,26.9
+167.0,101.0,93.1,470.0,68.5,67.9,117.0,1298.0,9.47,19.8,39.6
+21.7,16.7,22.5,80.6,9.31,20.9,37.5,723.0,10.1,19.6,23.7
+3.89,7.23,29.7,65.5,19.8,29.2,40.7,491.0,10.8,55.7,49.6
+24.1,16.3,24.1,25.0,12.0,16.1,14.5,523.0,11.5,34.0,37.2
+16.5,13.6,16.7,36.5,6.79,35.5,54.2,474.0,7.43,41.0,50.5
+7.77,12.3,26.2,34.9,1.0,42.2,50.0,533.0,8.98,14.9,50.9
+75.7,53.3,24.8,21.5,2.41,6.92,16.3,835.0,38.9,94.7,175.0
+33.7,10.2,34.0,33.7,8.98,20.9,42.6,599.0,7.23,10.8,69.2
+32.5,13.6,23.1,17.5,5.57,16.7,27.6,655.0,26.4,47.0,102.0
+25.3,17.9,9.65,200.0,24.4,16.0,31.3,661.0,36.8,47.8,50.0
+14.3,23.5,18.9,23.9,11.5,12.4,32.8,615.0,16.1,20.5,31.1
+31.1,28.1,26.7,42.9,15.3,2.27,14.5,173.0,27.1,61.0,87.4
+23.9,17.6,17.6,45.7,9.65,5.94,12.9,533.0,12.6,23.1,30.8
+57.3,50.5,60.4,400.0,68.5,36.5,59.4,359.0,35.5,64.9,106.0
+31.9,13.7,20.5,24.4,2.48,8.28,41.0,610.0,16.0,18.6,45.7
+28.6,14.5,16.3,21.7,4.29,30.8,46.6,349.0,22.9,41.4,1.43
+17.5,12.7,21.7,19.8,10.8,38.2,48.7,429.0,47.4,69.2,73.0
+85.1,73.7,6.26,1.0,2.92,18.1,38.9,604.0,12.9,21.1,55.7
+34.0,12.9,16.3,75.0,4.96,3.79,24.1,379.0,31.3,45.3,93.1
+26.4,21.9,35.5,217.0,49.6,90.6,227.0,2072.0,11.3,37.9,29.2
+21.1,13.5,4.78,15.1,20.7,4.53,28.6,389.0,14.3,20.4,47.8
+17.8,9.22,14.3,20.7,4.57,25.0,35.9,365.0,22.3,29.7,24.4
+21.1,17.0,22.3,26.7,10.6,24.1,28.6,538.0,11.5,27.1,34.3
+26.7,11.2,29.7,29.2,5.62,16.4,22.3,594.0,5.83,28.4,19.5
+16.5,19.3,17.5,34.0,10.3,57.8,123.0,1928.0,4.03,22.1,37.2
+26.2,11.3,25.5,24.1,20.5,17.9,38.2,610.0,13.2,21.3,62.1
+30.5,35.5,17.2,168.0,22.5,7.84,22.9,882.0,10.3,22.7,70.4
+25.5,23.9,52.3,410.0,56.2,4.41,23.3,418.0,9.31,25.0,31.1
+36.2,13.1,27.1,30.5,10.2,75.0,115.0,414.0,24.1,40.0,41.4
+21.1,20.9,56.2,441.0,59.9,10.1,35.9,567.0,17.8,36.5,64.4
+89.8,73.0,17.6,17.6,13.9,1.7,3.75,331.0,13.7,35.5,62.6
+22.9,13.8,39.6,170.0,38.5,7.64,17.3,562.0,1.14,12.3,2.92
+17.8,20.4,23.5,133.0,29.2,15.0,21.7,599.0,29.7,62.1,108.0
+19.1,12.3,23.3,15.0,9.39,15.0,17.8,410.0,25.7,28.4,67.9
+28.1,23.9,12.4,18.4,9.31,34.6,38.2,286.0,16.1,26.7,58.8
+20.2,10.9,58.8,325.0,64.4,36.8,48.3,457.0,29.7,54.2,84.3
+33.7,17.6,21.3,41.4,7.37,66.7,95.6,505.0,22.7,34.3,20.5
+13.8,17.6,31.1,38.2,3.85,157.0,223.0,433.0,16.0,22.7,18.4
+41.8,29.2,42.9,211.0,42.2,47.0,73.0,379.0,6.92,36.5,53.3
+7.57,16.0,13.3,133.0,8.51,12.1,31.3,599.0,6.32,43.7,41.4
+22.5,15.0,21.5,237.0,18.6,13.5,19.1,542.0,16.4,21.1,55.7
+29.2,4.26,27.9,17.5,4.61,47.4,85.8,1230.0,11.2,20.9,39.2
+16.8,18.1,11.1,55.7,5.62,41.0,54.7,325.0,15.1,27.6,16.3
+31.6,20.4,30.2,29.2,10.3,3.68,11.4,615.0,3.55,36.8,75.7
+23.3,8.13,14.5,15.3,14.9,17.6,20.7,692.0,18.1,44.5,61.0
+46.6,30.0,38.5,96.5,22.5,9.65,27.1,673.0,54.7,82.8,149.0
+30.8,19.8,45.7,113.0,7.99,13.3,33.4,491.0,10.1,25.5,37.9
+25.9,15.1,24.1,170.0,8.98,26.4,42.2,557.0,18.1,30.2,24.6
+42.9,23.9,18.9,23.5,14.2,2.86,22.3,483.0,13.0,34.0,49.6
+69.8,37.9,15.0,337.0,35.2,6.32,61.5,392.0,41.8,71.0,57.3
+13.9,20.2,32.8,48.3,12.9,17.3,33.4,505.0,15.7,36.8,41.4
+22.1,19.1,20.9,16.1,5.57,149.0,269.0,3051.0,11.9,45.3,83.5
+63.2,89.0,18.9,35.2,25.9,14.7,19.3,743.0,3.25,15.7,13.1
+18.3,18.8,24.1,82.0,25.0,89.0,170.0,1700.0,15.4,21.7,47.8
+12.6,24.8,17.9,9.65,1.0,73.7,132.0,1715.0,26.7,73.7,97.3
+20.0,19.8,23.9,38.9,7.3,30.8,49.1,1219.0,16.0,30.0,41.0
+18.9,11.5,71.0,470.0,80.6,45.7,55.7,392.0,11.0,14.7,49.6
+69.8,48.7,12.3,23.9,12.6,12.3,21.5,509.0,11.8,35.9,50.0
+7.99,7.84,35.9,365.0,44.9,12.6,29.7,1155.0,6.04,41.4,66.7
+22.7,5.38,69.2,359.0,59.4,4.61,20.2,491.0,17.3,44.1,53.8
+22.9,23.9,23.3,23.7,7.64,10.4,21.3,557.0,89.0,170.0,173.0
+86.6,84.3,13.8,22.9,8.43,15.1,22.1,496.0,47.4,85.8,160.0
+92.2,63.8,34.6,21.1,8.43,1.0,7.43,155.0,10.6,8.98,37.5
+28.9,20.7,104.0,519.0,88.2,25.0,35.5,426.0,51.4,106.0,179.0
+52.8,30.2,27.6,29.4,17.6,12.9,25.9,594.0,97.3,129.0,32.2
+23.9,12.2,22.7,27.1,5.33,57.8,75.0,547.0,21.3,34.9,42.6
+13.6,14.1,9.91,3.89,8.51,10.2,19.6,474.0,15.4,22.1,33.7
+25.7,9.65,23.3,31.6,14.1,54.2,113.0,2167.0,7.04,30.0,34.6
+22.5,14.1,75.0,588.0,71.7,23.7,42.2,505.0,7.1,17.0,4.22
+107.0,92.2,142.0,667.0,115.0,10.4,22.5,799.0,97.3,131.0,23.5
+8.43,8.74,31.6,267.0,40.0,6.15,13.5,483.0,62.6,96.5,50.5
+25.5,15.8,30.0,35.5,28.9,43.7,69.2,1811.0,6.44,24.4,47.0
+80.6,57.8,7.23,165.0,15.5,5.09,8.9,346.0,11.2,21.1,33.4
+55.2,31.3,16.5,19.5,7.1,22.7,44.5,1055.0,25.9,44.5,59.9
+65.5,34.3,21.5,80.6,4.33,25.7,30.8,542.0,53.3,118.0,155.0
+19.5,10.9,122.0,453.0,73.0,5.23,27.6,655.0,20.5,24.8,38.2
+28.4,9.82,18.6,198.0,17.8,93.1,154.0,1762.0,57.8,113.0,153.0
+16.7,14.7,24.1,55.2,30.2,20.4,30.5,626.0,5.19,20.4,31.3
+118.0,89.8,22.7,19.5,7.04,32.2,38.2,583.0,20.4,34.9,48.7
+22.9,11.4,122.0,337.0,50.5,6.61,41.8,626.0,11.5,31.9,51.9
+34.6,17.6,6.61,165.0,13.2,30.2,89.8,2091.0,15.1,33.4,56.7
+51.9,40.0,13.5,168.0,5.99,25.5,39.6,1346.0,21.1,32.8,12.9
+18.1,8.98,40.0,59.4,18.6,7.5,21.1,400.0,16.7,35.5,37.2
+15.8,25.7,13.8,24.1,10.6,53.8,74.3,538.0,8.43,32.2,28.4
+16.1,18.4,25.9,44.9,33.7,19.6,40.3,528.0,38.5,92.2,172.0
+17.0,31.1,24.4,18.1,9.47,17.5,35.2,562.0,23.7,57.3,66.7
+17.9,8.2,10.8,32.2,6.98,21.5,50.9,396.0,9.22,25.5,38.5
+33.4,19.8,17.0,20.5,6.26,29.2,43.3,284.0,1.0,11.4,33.4
+40.7,18.3,22.7,26.9,4.87,20.4,41.0,858.0,18.8,34.6,30.2
+17.2,14.7,24.1,34.3,10.6,36.5,47.4,313.0,8.51,38.9,47.4
+16.5,7.91,14.7,17.8,7.5,9.56,15.5,491.0,16.1,73.7,79.1
+23.3,16.3,26.4,30.8,10.5,15.3,26.4,777.0,26.2,33.1,39.6
+20.9,16.3,21.9,27.9,12.5,14.2,22.1,604.0,19.3,40.3,38.9
+67.9,53.3,22.1,22.3,8.58,46.1,53.3,500.0,21.7,35.9,49.1
+33.4,8.9,20.9,25.9,5.78,17.0,22.3,717.0,11.7,32.2,57.3
+21.3,7.91,4.78,12.4,4.7,14.2,36.2,649.0,6.38,22.9,38.2
+16.8,13.6,19.1,26.2,16.1,33.7,63.8,806.0,22.1,37.5,64.9
+19.6,17.2,38.5,286.0,24.6,17.0,26.9,583.0,6.73,34.6,32.8
+61.0,47.4,11.7,46.6,28.9,44.9,104.0,3368.0,15.8,27.9,51.9
+40.3,22.7,5.38,8.98,6.1,109.0,136.0,400.0,34.9,110.0,253.0
+28.9,20.0,15.3,21.7,3.79,93.9,130.0,1037.0,13.1,30.0,23.3
+21.3,16.4,14.1,22.9,2.59,25.9,42.9,311.0,1.78,75.7,5.52
+18.4,19.3,158.0,91.4,250.0,13.3,30.5,717.0,40.7,73.7,121.0
+59.4,19.1,9.14,121.0,26.9,60.4,131.0,1981.0,21.1,41.0,43.7
+17.8,3.43,18.4,28.9,18.1,64.9,137.0,2288.0,12.6,30.2,24.8
+18.3,17.0,21.9,18.9,4.57,4.66,3.79,91.4,16.4,39.2,49.1
+25.7,10.1,47.0,49.6,10.2,17.3,32.2,368.0,5.42,16.3,40.0
+80.6,52.8,16.1,10.3,3.68,63.8,84.3,523.0,24.8,46.6,63.2
+50.5,47.8,17.6,31.3,13.2,37.5,49.6,437.0,10.5,18.8,4.29
+77.7,61.0,4.49,3.13,7.1,18.6,36.2,487.0,16.4,26.9,42.6
+26.7,22.7,15.8,137.0,30.8,61.0,93.9,882.0,9.73,26.4,54.2
+19.5,2.41,12.6,158.0,12.1,9.22,20.4,806.0,23.5,32.8,36.5
+35.2,20.5,46.6,38.9,20.5,8.2,75.0,698.0,6.85,10.0,54.7
+30.0,17.3,1.51,5.73,1.01,4.83,17.3,466.0,53.3,72.3,65.5
+20.2,13.7,25.3,35.2,31.3,6.73,49.1,426.0,43.7,71.0,217.0
+19.8,22.1,3.37,5.33,6.21,40.0,50.9,578.0,84.3,153.0,215.0
+23.1,25.7,15.0,215.0,20.4,20.4,35.2,557.0,16.5,34.9,22.5
+14.6,10.9,10.9,21.5,17.5,19.5,27.9,770.0,7.3,17.0,69.8
+23.7,24.6,45.7,207.0,32.8,38.2,62.6,552.0,19.1,30.8,31.6
+26.4,12.3,26.4,17.6,1.0,86.6,143.0,1963.0,4.78,18.3,27.4
+22.7,21.1,30.5,29.7,17.5,33.7,46.1,437.0,51.4,146.0,213.0
+24.1,19.5,19.6,26.4,4.74,14.9,25.7,679.0,1.02,2.46,7.04
+6.15,17.5,24.4,26.7,4.57,19.6,32.2,557.0,15.1,33.4,50.5
+32.2,19.8,28.6,31.9,5.42,44.9,91.4,991.0,1.0,56.2,11.1
+75.7,86.6,20.2,80.6,20.7,3.68,15.7,1114.0,17.5,32.8,31.1
+42.9,34.0,67.3,250.0,39.2,9.73,21.3,583.0,77.7,150.0,146.0
+108.0,71.0,20.7,27.9,6.04,26.2,39.6,496.0,15.1,29.4,56.7
+11.0,18.6,12.6,269.0,17.6,15.4,28.1,487.0,8.9,20.9,32.5
+13.5,15.0,27.1,167.0,15.3,29.4,42.9,437.0,23.7,40.3,35.5
+21.1,10.0,27.6,28.1,8.06,8.51,20.0,757.0,16.7,16.7,45.3
+16.4,6.98,3.75,5.62,1.22,32.2,47.4,523.0,31.3,52.3,82.8
+63.2,59.4,22.7,57.3,12.5,54.2,77.0,340.0,41.8,75.0,85.8
+19.6,5.05,42.6,84.3,30.8,25.3,64.9,1778.0,7.7,22.3,61.0
+23.5,13.2,22.1,17.8,1.19,12.9,37.9,1762.0,22.9,25.3,51.9
+17.2,8.2,23.3,71.0,18.6,13.3,31.9,400.0,56.2,101.0,355.0
+9.39,41.4,4.53,13.3,8.82,63.8,106.0,1104.0,58.3,110.0,183.0
+20.2,19.6,29.2,35.9,4.53,22.5,29.7,500.0,10.0,25.9,53.3
+24.4,10.9,18.9,15.0,8.58,14.1,30.5,770.0,16.5,32.5,40.3
+16.7,9.73,22.7,34.9,23.9,6.26,19.6,982.0,12.0,21.5,26.2
+27.9,14.9,111.0,284.0,43.7,34.3,44.5,667.0,45.3,88.2,158.0
+20.9,12.1,21.3,92.2,6.73,2.04,14.2,334.0,46.6,69.8,125.0
+31.9,19.6,17.5,13.3,11.9,26.7,42.2,453.0,16.3,17.2,40.7
+16.0,8.13,16.5,17.2,14.1,34.3,60.4,418.0,10.5,26.4,32.8
+12.9,15.4,66.1,63.8,28.6,22.3,34.9,400.0,14.3,24.4,48.3
+34.6,12.9,21.9,20.9,5.94,18.3,27.6,621.0,9.31,26.2,37.5
+27.6,17.0,13.9,98.2,10.9,39.6,62.1,552.0,29.4,45.3,44.5
+65.5,34.0,14.7,13.8,5.38,26.2,44.5,717.0,13.9,36.5,52.3
+19.8,18.3,15.5,19.6,10.6,6.73,39.2,1611.0,11.0,37.9,59.4
+11.9,18.9,24.4,21.1,10.0,17.0,32.5,474.0,20.0,26.9,24.1
+9.65,12.3,20.4,12.1,1.0,42.9,59.9,632.0,30.8,48.3,45.7
+26.4,11.2,63.8,542.0,92.2,13.7,28.6,723.0,15.4,30.0,34.3
+34.0,12.0,77.0,292.0,47.8,37.5,84.3,1197.0,16.4,38.9,22.7
+29.2,29.7,24.6,15.5,3.62,5.0,8.13,991.0,19.6,37.5,17.8
+43.7,7.7,50.9,86.6,40.3,25.0,58.8,1540.0,17.8,31.9,62.6
+44.5,17.3,21.1,22.5,13.5,2.33,16.4,466.0,66.7,142.0,271.0
+25.7,40.0,19.5,17.9,11.5,34.3,74.3,2436.0,12.7,42.6,76.4
+73.7,62.6,20.9,12.6,3.72,17.9,30.8,649.0,8.82,23.5,13.7
+16.5,7.91,25.5,20.5,4.78,34.3,83.5,1640.0,11.3,27.1,34.0
+38.5,22.5,22.9,19.8,4.41,25.3,34.3,365.0,9.56,30.0,56.7
+30.5,15.8,29.4,129.0,28.6,103.0,163.0,1554.0,4.37,9.65,9.47
+36.2,35.5,29.2,46.1,14.7,16.0,25.3,403.0,17.8,45.3,51.9
+27.9,16.7,4.87,8.43,16.8,76.4,127.0,1395.0,17.5,25.5,29.2
+14.1,15.3,32.5,305.0,57.8,1.0,4.96,241.0,23.7,55.7,82.8
+41.8,26.2,23.1,26.2,4.61,2.09,18.4,362.0,13.7,29.2,20.9
+20.7,28.6,12.6,41.0,10.3,24.8,41.0,638.0,12.5,18.6,69.2
+16.4,18.4,21.7,13.9,6.26,24.6,36.5,644.0,13.6,37.5,57.8
+32.8,10.6,21.9,54.2,10.6,23.7,33.1,289.0,15.0,31.9,41.4
+111.0,107.0,13.1,17.8,6.79,20.7,34.9,757.0,11.5,22.1,38.5
+13.9,39.6,15.4,22.5,7.1,31.1,43.3,396.0,72.3,167.0,372.0
+85.1,64.4,6.85,13.7,5.47,32.8,63.2,1981.0,11.2,18.4,44.9
+68.5,63.8,26.2,23.3,3.79,5.0,8.51,547.0,23.9,41.0,52.8
+16.5,8.2,20.4,115.0,19.5,4.14,16.1,453.0,8.43,17.3,21.9
+12.9,15.4,23.7,14.9,3.82,62.6,127.0,3023.0,13.5,15.8,48.3
+11.7,14.5,21.5,13.6,10.6,69.2,108.0,2054.0,9.14,22.3,29.2
+13.7,37.5,18.6,23.9,7.3,63.8,108.0,638.0,6.38,16.8,17.9
+22.7,11.8,22.1,23.3,9.39,107.0,274.0,3460.0,18.6,36.8,28.6
+20.0,13.1,25.9,94.7,10.9,35.5,63.2,1155.0,11.0,24.8,45.3
+13.2,13.3,8.82,24.6,25.0,2.57,15.7,449.0,29.7,55.2,66.1
+9.39,19.1,53.3,105.0,35.5,66.7,118.0,1946.0,12.6,28.9,23.5
+47.0,32.2,41.0,253.0,36.5,5.38,26.2,514.0,13.7,26.4,34.3
+25.5,8.98,93.9,649.0,107.0,30.2,37.9,505.0,28.9,53.8,41.8
+66.1,20.4,10.6,176.0,17.0,51.4,77.7,491.0,26.9,42.2,46.6
+6.92,6.32,24.6,16.7,6.26,13.3,14.6,474.0,7.57,50.5,77.0
+88.2,61.5,21.7,26.7,5.73,87.4,158.0,2788.0,17.0,19.5,50.0
+14.7,21.9,1.18,5.78,11.2,7.77,13.0,552.0,22.7,32.5,55.2
+9.91,21.7,19.8,18.9,7.1,33.4,50.9,533.0,19.6,42.9,44.9
+52.3,30.8,15.1,68.5,1.96,96.5,132.0,422.0,9.56,8.74,30.5
+46.6,31.9,1.0,1.01,9.06,2.57,27.9,478.0,10.1,35.9,52.8
+98.2,56.2,12.4,200.0,18.6,38.9,60.4,784.0,18.9,20.7,38.5
+16.3,9.39,25.7,11.9,1.91,150.0,225.0,2308.0,18.1,33.7,25.3
+14.7,10.1,7.5,66.7,3.4,18.3,38.5,1055.0,9.47,43.3,67.3
+9.91,13.5,33.1,57.3,21.3,11.8,29.2,594.0,15.3,26.7,56.7
+22.3,10.4,16.5,17.3,14.7,25.5,22.3,253.0,34.9,74.3,106.0
+14.2,10.5,46.6,302.0,63.8,25.3,38.5,392.0,19.3,44.1,53.8
+28.4,32.8,28.9,35.2,11.9,106.0,181.0,1747.0,6.26,24.6,44.9
+13.1,27.4,15.8,29.7,10.7,5.73,16.3,457.0,13.1,32.5,57.3
+53.8,7.77,24.1,49.1,4.18,24.6,34.0,457.0,7.3,26.9,75.0
+21.3,15.1,16.3,23.9,4.61,44.1,62.6,632.0,37.2,67.3,150.0
+6.67,6.21,22.9,34.9,1.53,27.1,38.2,474.0,13.0,17.9,37.9
+26.4,11.3,11.1,29.2,10.6,1.0,3.25,305.0,73.0,157.0,237.0
+21.3,14.2,22.3,47.0,20.7,132.0,196.0,1310.0,11.1,21.1,58.8
+22.5,30.8,24.4,18.3,13.0,30.8,43.3,352.0,11.0,16.7,34.0
+31.6,13.9,14.1,21.7,1.0,7.91,23.7,615.0,18.4,42.2,121.0
+12.4,4.7,14.3,75.7,7.91,10.3,33.4,799.0,2.46,6.55,33.7
+61.0,14.3,6.32,229.0,19.3,9.14,12.3,528.0,15.5,24.8,35.9
+16.0,8.82,15.3,58.8,18.1,36.5,52.8,375.0,17.2,30.0,39.2
+77.7,105.0,20.5,126.0,10.1,19.5,33.4,496.0,12.0,15.7,52.8
+62.6,49.1,27.1,20.7,6.85,15.0,36.5,806.0,8.74,31.3,71.7
+21.1,17.3,4.37,1.89,2.71,14.1,30.5,610.0,15.3,33.1,50.5
+17.2,14.1,16.0,37.2,12.1,16.5,29.7,514.0,13.5,33.4,33.4
+43.3,26.2,23.3,16.0,3.16,40.3,58.8,588.0,10.4,28.6,57.3
+6.32,10.1,25.0,17.3,1.37,3.55,21.7,509.0,8.66,25.3,48.3
+13.8,17.0,9.47,259.0,20.4,32.8,48.3,528.0,21.9,34.0,52.3
+25.7,7.64,48.7,389.0,59.9,10.3,29.4,649.0,10.0,20.5,30.0
+14.9,10.1,24.4,17.9,8.13,16.5,22.5,547.0,13.1,30.0,41.4
+22.3,5.94,57.8,505.0,75.7,11.1,20.9,777.0,10.5,16.5,19.6
+14.1,10.1,32.8,47.4,14.7,14.3,55.2,3023.0,13.1,30.0,38.5
+37.5,20.4,14.1,215.0,27.4,17.9,22.5,743.0,14.5,46.1,40.0
+17.3,8.66,22.7,33.1,16.7,45.3,48.7,453.0,16.5,43.3,60.4
+17.9,16.3,52.8,279.0,27.1,30.2,45.3,449.0,10.6,35.2,48.3
+22.9,27.1,8.82,27.4,9.31,10.4,23.3,644.0,16.1,16.4,37.9
+21.1,13.3,47.4,10.7,56.2,54.2,101.0,1346.0,5.33,59.4,6.79
+13.2,18.6,19.6,21.9,3.05,31.6,42.6,349.0,62.6,123.0,229.0
+19.6,29.4,57.8,573.0,62.1,18.3,28.6,644.0,13.6,37.5,44.5
+10.6,11.3,21.7,15.1,6.26,8.9,86.6,3429.0,32.8,63.2,107.0
+12.5,15.8,38.2,211.0,27.6,8.51,24.1,1540.0,16.5,31.1,31.9
+13.9,11.0,26.2,24.8,2.02,16.5,27.6,679.0,10.4,22.1,61.0
+22.1,5.28,23.7,36.2,11.4,10.7,22.3,449.0,10.4,25.0,36.2
+13.9,5.33,25.5,16.7,7.1,23.3,51.4,1114.0,11.5,15.3,17.5
+22.1,20.0,6.98,16.8,18.1,28.4,46.6,359.0,16.1,42.6,122.0
+59.4,51.4,29.4,349.0,39.2,38.9,53.8,528.0,16.7,37.2,33.7
+18.4,8.35,19.6,24.1,3.96,19.5,35.9,858.0,3.25,77.7,9.65
+34.3,34.3,16.1,67.3,17.3,44.9,54.7,362.0,4.91,8.35,31.3
+13.9,15.5,7.43,16.4,11.4,23.5,43.3,396.0,13.5,33.7,61.5
+22.5,14.3,17.5,131.0,26.4,93.1,147.0,1794.0,12.1,42.9,25.5
+28.4,31.9,24.6,29.4,2.69,28.4,42.6,461.0,22.1,40.3,50.0
+37.5,2.67,24.4,170.0,18.6,27.6,47.0,457.0,12.2,22.3,27.6
+21.7,16.7,17.3,18.8,13.9,61.0,100.0,1037.0,11.4,34.9,48.7
+14.9,11.9,21.5,22.9,11.2,48.3,79.9,514.0,53.8,109.0,164.0
+19.3,8.2,15.8,21.1,5.88,4.87,20.2,890.0,15.3,23.1,41.8
+26.7,31.6,6.79,19.8,6.15,67.3,115.0,1715.0,29.2,54.2,37.5
+17.0,13.5,15.0,337.0,34.6,25.7,42.6,368.0,26.4,48.3,46.1
+28.6,55.7,13.7,170.0,28.1,23.7,35.2,519.0,11.8,20.7,47.0
+12.3,9.47,17.3,13.6,15.4,33.4,57.8,437.0,16.7,26.9,68.5
+13.1,23.7,11.8,141.0,15.0,12.6,28.4,567.0,13.8,18.3,52.3
+31.6,22.7,20.5,127.0,16.1,15.5,29.4,491.0,12.9,38.5,36.5
+32.2,20.0,21.1,20.7,7.43,85.1,133.0,2129.0,9.22,25.0,53.8
+17.2,14.2,21.7,13.8,6.04,31.9,50.0,557.0,5.47,28.6,44.5
+8.98,6.21,20.7,13.7,12.9,42.6,62.1,542.0,14.3,22.7,51.4
+13.7,15.3,17.5,22.9,9.56,18.9,42.9,496.0,9.73,59.4,48.3
+64.9,38.2,50.5,269.0,44.9,11.8,17.5,496.0,13.9,31.6,40.7
+20.0,13.1,17.9,44.9,5.38,3.85,8.82,305.0,17.0,27.1,64.9
+11.9,20.9,11.1,2.94,29.4,3.28,21.5,514.0,9.82,17.8,29.7
+2.29,19.1,18.6,12.6,2.59,33.7,43.3,557.0,10.1,11.8,1.01
+61.5,34.0,3.55,9.22,8.58,21.7,42.9,866.0,8.98,23.5,28.1
+25.3,20.9,15.4,25.7,10.2,5.94,7.99,655.0,13.7,17.9,45.3
+27.1,14.9,15.5,24.4,12.7,21.9,35.5,355.0,96.5,130.0,37.2
+12.2,9.91,21.7,279.0,58.3,11.3,20.7,542.0,12.0,24.4,35.9
+49.1,35.2,25.7,37.5,10.0,5.23,12.1,813.0,10.0,21.7,45.7
+11.4,4.33,11.1,96.5,14.3,22.1,44.1,890.0,8.74,32.8,56.2
+20.7,9.06,23.5,20.4,4.61,57.8,82.0,922.0,52.3,80.6,111.0
+13.9,16.8,30.0,38.2,16.3,43.7,90.6,2207.0,41.8,76.4,157.0
+90.6,42.9,13.0,14.1,45.7,87.4,142.0,2503.0,20.2,36.5,58.8
+34.3,41.0,5.19,5.88,13.1,25.5,52.3,305.0,14.9,36.2,41.4
+17.6,12.0,10.7,16.0,3.89,155.0,267.0,3555.0,17.0,31.9,56.2
+18.8,20.0,3.22,322.0,37.2,64.4,88.2,1018.0,15.8,24.6,41.4
+16.0,14.5,16.5,175.0,18.4,29.4,38.2,300.0,17.5,41.4,57.8
+12.4,35.5,11.0,126.0,19.6,4.74,31.1,698.0,10.9,29.7,34.3
+23.3,14.5,20.7,276.0,24.8,19.1,77.0,1640.0,42.9,72.3,143.0
+7.77,19.5,42.9,302.0,55.7,3.72,16.5,615.0,12.1,18.6,27.1
+18.1,16.1,30.2,31.6,13.0,85.1,125.0,1241.0,24.6,49.6,46.6
+61.0,5.67,25.9,26.4,7.5,24.1,45.3,505.0,18.1,28.9,63.2
+26.7,16.4,21.7,29.4,4.0,16.0,22.1,509.0,67.9,151.0,349.0
+9.22,16.5,19.3,21.1,13.8,19.1,26.7,655.0,67.3,145.0,331.0
+39.6,16.3,32.8,33.1,7.7,62.6,93.9,1811.0,11.8,29.7,51.4
+157.0,74.3,32.5,54.7,13.8,32.2,49.1,858.0,13.1,38.9,57.8
+22.5,12.3,34.9,322.0,56.7,21.7,37.9,538.0,21.1,22.9,30.8
+14.5,12.1,27.4,17.5,8.06,80.6,117.0,379.0,4.29,10.5,44.9
+126.0,213.0,18.9,111.0,20.9,14.3,27.4,505.0,12.0,16.0,18.9
+23.7,11.0,41.4,75.7,3.02,85.1,105.0,372.0,19.8,33.7,63.8
+26.4,7.43,21.5,89.0,10.1,16.0,30.0,474.0,2.31,6.38,10.6
+39.2,48.7,17.8,11.4,1.93,78.4,121.0,1197.0,24.6,44.9,53.3
+21.9,20.4,55.7,483.0,61.0,28.1,44.5,757.0,11.8,17.3,59.4
+22.9,7.43,80.6,279.0,42.6,27.4,45.3,1433.0,65.5,113.0,107.0
+15.3,13.9,23.1,17.0,1.5,15.5,29.7,939.0,3.82,35.9,13.3
+30.2,14.7,17.6,29.2,10.3,3.19,17.8,289.0,12.7,32.8,36.5
+23.7,17.0,24.8,89.0,14.9,39.6,58.8,441.0,8.06,15.5,11.1
+17.5,16.5,19.3,158.0,27.9,9.22,27.4,626.0,18.9,27.1,77.0
+18.1,21.3,16.1,109.0,14.7,17.8,28.9,509.0,10.8,25.9,64.4
+24.4,17.9,3.08,11.1,2.13,17.9,38.2,528.0,9.82,16.8,38.9
+28.6,16.1,38.9,198.0,43.7,53.3,68.5,644.0,1.58,6.98,8.35
+14.2,7.99,6.79,12.7,21.5,139.0,198.0,1310.0,4.78,10.9,2.94
+51.9,32.8,77.7,461.0,63.8,27.4,39.6,547.0,42.6,75.7,40.7
+5.38,17.6,35.5,557.0,61.5,32.8,55.7,843.0,36.8,61.5,125.0
+12.0,9.82,27.9,23.9,7.84,52.3,75.7,457.0,12.4,22.9,34.3
+90.6,77.0,81.3,334.0,64.9,2.35,33.7,368.0,1.0,49.6,6.38
+12.7,13.0,16.7,100.0,15.4,7.77,24.8,813.0,25.5,71.7,112.0
+20.0,14.3,12.5,126.0,14.7,12.5,43.7,820.0,11.5,21.1,1.0
+13.0,8.28,23.1,24.1,7.37,57.3,83.5,1046.0,13.2,35.9,58.8
+12.4,9.39,41.0,77.0,23.5,52.8,94.7,1075.0,9.56,21.3,36.2
+7.91,27.4,19.5,147.0,27.4,20.5,24.8,457.0,17.2,23.3,50.5
+60.4,29.4,27.1,16.5,2.07,8.13,26.7,583.0,20.7,37.2,32.5
+10.9,19.3,31.9,262.0,60.4,13.8,14.6,784.0,66.1,97.3,204.0
+17.3,18.3,14.2,15.1,8.74,49.1,94.7,2110.0,13.2,31.1,46.1
+13.9,15.1,26.4,36.5,9.14,32.5,36.8,710.0,3.43,73.0,2.76
+63.2,64.9,9.91,139.0,14.7,85.8,121.0,362.0,30.5,46.1,29.7
+33.4,28.9,12.2,21.7,14.3,22.5,75.0,1794.0,15.0,25.5,38.2
+12.2,12.7,16.4,17.2,7.77,3.16,22.7,777.0,9.39,16.8,38.9
+9.47,11.0,38.5,54.7,17.8,91.4,165.0,1911.0,18.8,30.2,38.9
+38.5,30.5,24.6,31.1,24.4,28.1,36.2,433.0,12.4,28.9,61.0
+75.7,82.0,44.5,54.2,23.3,20.4,28.9,533.0,12.5,37.5,45.7
+21.5,10.3,19.6,186.0,23.5,8.35,29.2,843.0,12.7,28.9,48.7
+16.1,13.5,24.1,7.17,8.43,20.0,37.2,866.0,15.4,30.0,53.3
+17.0,17.9,1.0,15.0,10.2,34.9,63.8,414.0,11.3,25.7,35.5
+25.7,8.66,13.9,21.1,6.21,73.7,126.0,1778.0,167.0,403.0,626.0
+7.84,9.56,21.3,426.0,48.3,33.7,55.2,496.0,28.6,52.3,51.9
+23.5,21.5,23.9,19.6,5.19,79.1,178.0,2371.0,19.3,38.9,47.8
+16.4,12.9,23.3,19.6,21.1,28.1,58.8,1176.0,18.3,31.6,40.7
+13.3,9.31,15.1,14.9,6.04,135.0,189.0,274.0,13.8,15.8,34.6
+64.9,64.9,19.3,19.6,16.3,85.1,127.0,1928.0,1.46,10.7,20.2
+8.35,25.5,23.5,25.3,14.2,2.09,10.6,217.0,42.9,68.5,58.8
+18.3,17.5,19.8,22.3,2.64,119.0,191.0,2690.0,12.6,28.1,26.7
+6.04,32.8,24.1,24.4,1.06,83.5,145.0,1762.0,9.31,15.0,7.37
+16.3,9.31,35.5,178.0,27.1,102.0,157.0,1700.0,10.0,16.5,52.8
+45.3,33.4,21.7,18.1,8.2,36.8,61.5,1104.0,12.1,17.3,47.4
+9.39,19.6,14.9,92.2,14.2,42.9,66.7,1009.0,37.9,56.7,59.4
+8.28,14.6,40.0,359.0,44.9,267.0,368.0,3106.0,15.0,25.3,38.2
+12.9,14.2,22.7,28.1,5.73,15.5,32.8,483.0,14.2,24.8,48.3
+2.74,3.11,44.9,211.0,41.0,22.1,39.6,491.0,11.9,29.7,34.0
+21.7,16.8,20.5,108.0,16.7,12.6,24.1,542.0,17.8,40.7,36.5
+18.4,16.0,25.3,12.0,8.9,17.5,32.2,583.0,10.6,32.5,46.6
+19.5,15.0,15.5,178.0,11.9,64.9,83.5,1009.0,21.5,25.7,42.6
+38.9,30.5,22.7,21.9,6.73,12.6,23.5,583.0,4.37,16.5,75.7
+16.0,17.8,20.5,21.1,4.7,18.9,39.6,365.0,11.8,24.8,30.0
+81.3,55.7,98.2,567.0,62.1,105.0,173.0,2371.0,15.3,9.47,51.4
+18.4,15.1,23.7,26.4,3.49,37.5,56.2,757.0,13.7,22.7,50.0
+23.7,18.9,14.6,13.8,3.59,52.3,68.5,457.0,12.5,29.2,44.5
+3.19,11.7,20.9,22.5,3.31,28.9,44.5,500.0,14.7,27.4,29.4
+19.3,15.8,19.6,57.8,23.3,12.4,25.5,547.0,15.1,36.2,30.2
+85.1,61.5,18.1,18.1,5.0,22.5,33.7,1134.0,10.9,21.9,24.8
+9.06,13.9,46.6,114.0,12.7,10.0,31.3,828.0,8.51,25.0,30.2
+155.0,109.0,3.59,7.04,8.82,15.7,25.5,737.0,10.6,20.2,35.2
+8.58,10.2,15.8,23.1,2.02,94.7,122.0,453.0,16.3,48.7,130.0
+75.7,56.2,18.6,32.8,10.6,18.8,33.1,523.0,11.8,32.8,41.4
+27.6,37.2,69.8,137.0,32.8,16.0,34.3,685.0,12.1,18.8,29.4
+24.6,35.2,15.7,50.0,14.6,38.9,69.8,470.0,9.65,16.8,34.6
+27.9,25.9,29.2,25.0,5.23,44.5,69.8,1459.0,28.6,47.8,146.0
+16.1,13.0,23.3,16.1,10.9,37.9,53.8,433.0,54.7,127.0,115.0
+37.2,31.9,9.82,211.0,21.1,6.85,17.3,649.0,18.6,37.2,133.0
+9.39,13.1,20.2,46.1,21.1,58.3,101.0,1446.0,9.47,14.9,21.1
+32.2,22.9,1.0,4.87,5.23,28.1,42.2,547.0,8.51,22.9,51.9
+10.8,9.31,10.3,313.0,22.7,14.9,21.3,538.0,25.9,58.3,14.9
+17.6,14.9,13.6,11.8,3.43,17.9,27.9,583.0,9.73,26.4,19.5
+16.5,8.43,16.0,17.3,1.39,17.5,22.3,599.0,32.8,44.9,71.7
+13.8,22.3,13.0,99.1,2.11,42.6,49.6,359.0,27.1,55.2,49.1
+16.3,7.84,33.4,313.0,20.5,70.4,110.0,2035.0,25.9,49.6,66.7
+24.4,10.1,24.8,22.5,4.45,6.26,38.9,1219.0,16.3,24.6,33.4
+90.6,62.6,1.76,3.34,5.42,27.1,95.6,1382.0,29.2,52.3,106.0
+70.4,63.2,17.9,14.1,14.1,108.0,161.0,2267.0,7.99,22.5,46.1
+56.2,21.5,70.4,368.0,77.7,17.3,29.4,698.0,39.2,72.3,66.1
+24.8,9.14,22.9,470.0,46.1,28.9,44.5,457.0,9.39,15.5,24.6
+19.5,10.6,21.1,35.5,5.83,12.5,17.9,655.0,12.6,15.1,35.5
+20.0,12.1,16.5,19.3,15.8,95.6,160.0,1395.0,10.0,32.2,33.4
+22.7,18.9,52.8,160.0,40.0,28.9,52.8,441.0,14.1,34.0,52.3
+14.7,16.7,10.8,14.7,21.3,25.7,37.5,487.0,6.38,22.5,28.6
+23.5,17.8,26.2,153.0,19.5,14.7,36.2,1009.0,9.73,29.7,75.0
+20.9,7.5,4.33,18.3,15.8,17.0,27.9,610.0,12.4,34.6,39.6
+19.1,10.6,12.3,20.9,16.8,55.7,93.1,1625.0,31.1,61.5,42.2
+119.0,96.5,61.0,453.0,85.8,20.5,34.9,422.0,6.98,21.1,24.4
+21.5,13.6,13.7,37.2,6.55,17.6,30.8,685.0,3.72,13.8,44.1
+21.3,11.8,22.9,170.0,20.2,69.2,118.0,2110.0,54.7,79.9,19.8
+12.3,12.9,13.9,13.7,8.13,13.2,65.5,1433.0,13.6,32.5,51.4
+18.6,18.8,31.9,359.0,45.7,63.8,119.0,2187.0,39.6,85.1,235.0
+54.7,47.0,29.4,44.5,7.77,2.39,17.9,279.0,19.1,47.8,53.8
+23.5,13.3,35.2,41.0,25.9,12.0,33.1,626.0,31.9,74.3,138.0
+72.3,15.5,63.8,264.0,68.5,28.6,52.8,457.0,9.56,22.1,43.3
+19.8,17.5,17.5,28.1,7.5,5.19,38.2,906.0,23.7,49.6,6.38
+11.8,13.2,17.2,137.0,19.5,15.3,38.2,791.0,20.0,33.7,30.5
+38.5,35.2,20.0,223.0,30.5,18.3,44.9,474.0,16.0,16.3,55.2
+12.4,16.1,136.0,410.0,95.6,11.5,22.7,368.0,15.1,30.5,40.0
+15.7,23.1,12.0,36.2,2.29,10.7,28.4,433.0,39.6,85.1,80.6
+37.5,23.5,22.5,23.1,8.9,68.5,86.6,858.0,15.7,37.5,81.3
+15.7,19.3,52.3,68.5,21.1,7.43,31.6,777.0,83.5,160.0,231.0
+25.3,13.5,49.1,130.0,31.9,77.0,126.0,2247.0,7.99,26.9,26.9
+12.9,9.39,40.3,193.0,34.3,269.0,379.0,1685.0,2.76,7.1,29.4
+17.8,11.7,3.52,20.4,16.8,28.6,45.3,1009.0,2.86,23.3,58.3
+29.2,4.03,18.6,17.3,7.17,12.3,26.9,599.0,50.5,120.0,186.0
+23.1,28.1,23.3,25.7,17.3,10.4,11.4,737.0,2.89,14.6,13.9
+33.1,16.4,108.0,297.0,71.7,106.0,131.0,407.0,5.88,18.9,52.8
+84.3,67.3,19.5,18.9,1.49,23.1,50.5,429.0,7.43,18.3,31.9
+23.3,17.3,45.7,461.0,55.7,32.2,42.9,410.0,8.9,21.1,43.3
+14.9,11.0,23.1,19.1,11.0,29.4,47.8,343.0,4.18,57.3,6.85
+14.9,17.9,17.8,26.9,13.5,19.3,35.2,965.0,7.3,23.1,31.1
+53.8,22.3,24.6,28.4,13.2,17.6,56.7,2436.0,262.0,334.0,7.84
+20.4,9.22,20.7,23.5,4.61,54.2,78.4,649.0,32.8,68.5,107.0
+7.23,10.4,1.38,5.94,4.45,10.2,17.6,644.0,6.79,23.5,25.9
+84.3,48.7,20.9,27.9,14.9,47.4,77.7,414.0,11.9,27.6,28.6
+40.3,23.1,28.4,20.9,6.15,13.8,33.4,939.0,11.4,16.8,37.9
+113.0,78.4,20.7,28.9,7.43,79.9,133.0,692.0,6.21,10.9,1.68
+21.7,15.5,24.6,16.7,3.37,25.0,44.9,604.0,4.61,37.9,77.7
+18.4,13.0,16.7,11.7,2.94,41.4,59.9,1114.0,8.98,25.5,57.3
+48.7,10.0,29.4,26.4,8.66,10.6,17.8,127.0,6.55,23.3,34.3
+6.44,14.7,21.7,29.7,6.26,4.07,16.4,1046.0,23.5,28.6,37.5
+20.4,15.4,20.7,29.4,9.39,38.2,61.0,1459.0,36.8,87.4,191.0
+12.0,8.13,36.8,47.0,12.5,39.2,91.4,1472.0,9.22,24.6,42.6
+29.7,20.9,4.1,16.7,18.3,17.6,34.9,784.0,9.39,32.5,35.5
+19.3,24.4,20.4,26.2,1.25,38.2,63.8,1286.0,19.1,20.0,68.5
+21.1,38.2,31.3,34.0,8.98,2.97,21.1,519.0,10.0,26.9,38.2
+41.8,26.4,31.3,91.4,27.1,30.5,51.4,385.0,4.61,31.6,38.5
+20.5,10.5,22.3,15.4,12.7,33.4,67.3,429.0,37.9,79.1,100.0
+37.2,26.7,20.2,61.0,12.3,18.1,38.9,947.0,4.26,15.0,26.7
+42.2,33.1,5.83,15.1,6.04,90.6,172.0,2187.0,13.7,23.7,53.3
+42.6,42.9,22.9,31.9,10.7,19.1,34.3,655.0,12.0,15.0,35.9
+16.8,5.67,25.9,48.3,24.8,6.98,11.2,445.0,5.47,16.0,14.1
+15.8,10.4,23.9,20.4,7.43,4.91,22.9,457.0,31.1,46.6,93.1
+15.3,6.04,18.1,36.2,11.1,48.7,61.5,750.0,25.5,51.9,41.0
+28.1,14.1,9.82,186.0,52.3,3.02,21.9,328.0,5.99,23.5,42.2
+33.1,30.2,17.2,26.7,2.02,17.2,27.6,372.0,20.2,19.3,37.2
+40.0,30.0,41.8,36.5,5.42,26.7,35.9,437.0,31.9,77.0,79.1
+22.9,21.9,18.9,56.7,13.2,11.3,25.3,621.0,16.1,28.1,30.2
+20.0,11.2,35.2,36.2,9.22,3.37,3.49,110.0,17.9,33.7,36.2
+27.1,28.6,22.9,209.0,30.8,40.0,62.1,626.0,54.2,87.4,9.31
+17.0,12.7,47.4,114.0,48.7,8.06,16.5,784.0,5.09,14.1,45.3
+16.0,29.2,17.3,23.9,20.2,38.2,57.3,519.0,12.0,31.9,63.8
+28.6,22.5,15.8,33.7,13.1,33.7,53.8,286.0,37.2,78.4,167.0
+15.4,8.66,3.25,4.45,2.55,154.0,308.0,4451.0,41.0,104.0,179.0
+17.6,14.3,18.9,15.8,6.26,46.6,71.0,578.0,11.5,17.2,67.3
+26.7,15.7,25.3,31.1,5.67,8.66,29.7,1009.0,12.6,42.6,33.7
+32.8,13.5,1.61,1.0,6.04,56.2,78.4,1055.0,12.9,34.6,40.7
+125.0,71.0,25.0,34.0,14.3,30.8,40.3,457.0,11.9,32.8,26.9
+19.3,19.1,20.5,248.0,27.6,58.3,80.6,255.0,16.0,22.5,38.9
+11.5,11.8,31.9,322.0,51.4,10.3,24.4,578.0,6.26,15.8,29.4
+85.8,61.0,61.0,372.0,59.4,37.5,55.2,313.0,36.5,75.7,196.0
+28.6,14.7,15.8,211.0,20.4,8.82,15.8,649.0,28.4,51.9,83.5
+58.8,32.5,2.57,9.39,11.8,80.6,122.0,478.0,50.9,106.0,289.0
+24.1,21.1,2.17,1.83,2.92,3.02,17.2,127.0,13.0,36.8,93.1
+21.9,10.2,24.8,58.8,14.9,24.1,41.0,302.0,6.38,22.3,50.5
+19.3,8.2,22.1,73.0,22.9,13.6,22.1,770.0,24.4,50.9,82.8
+32.8,22.1,16.3,17.2,7.7,17.3,27.6,638.0,11.1,27.9,54.7
+27.6,16.0,18.9,26.7,12.5,82.8,127.0,1700.0,103.0,138.0,33.7
+17.6,16.5,19.1,13.9,10.0,8.06,82.0,552.0,82.8,163.0,250.0
+13.0,17.5,10.1,46.6,6.61,23.1,47.8,519.0,8.28,27.9,40.7
+34.9,52.8,20.9,18.9,4.87,22.7,33.7,649.0,5.0,17.0,17.5
+24.1,13.6,16.3,19.1,1.0,82.0,195.0,2738.0,6.67,21.7,19.5
+24.4,32.5,17.2,32.2,11.8,44.5,61.5,346.0,8.9,14.3,21.5
+71.7,59.4,13.3,379.0,21.1,30.2,41.0,723.0,44.1,119.0,160.0
+12.9,6.79,80.6,461.0,79.9,27.4,45.7,311.0,20.0,36.2,24.6
+14.2,18.1,23.5,21.9,9.06,36.8,62.6,445.0,9.39,24.8,26.2
+31.6,15.1,9.82,235.0,24.1,9.73,31.9,770.0,8.74,27.4,46.1
+52.8,32.8,4.03,9.82,8.35,42.9,67.9,791.0,10.7,21.3,55.2
+79.9,56.2,17.5,17.2,10.2,138.0,217.0,615.0,8.43,21.7,47.8
+105.0,34.9,20.9,27.6,4.57,42.6,66.1,505.0,49.1,82.0,114.0
+129.0,21.7,26.4,27.1,3.34,85.1,147.0,1625.0,7.17,13.0,32.2
+64.9,38.2,13.6,149.0,37.2,34.0,51.4,445.0,26.4,52.3,87.4
+24.6,13.3,10.8,21.5,8.98,26.7,38.9,334.0,7.37,11.2,36.8
+48.3,35.2,14.7,26.4,2.84,12.9,30.5,791.0,19.3,35.9,33.4
+20.7,17.8,22.3,20.9,16.7,33.7,50.0,491.0,27.9,47.0,47.8
+32.2,22.5,22.3,107.0,8.28,18.4,41.0,750.0,8.06,36.8,66.1
+48.3,27.9,18.1,13.5,10.7,37.9,85.8,2091.0,6.26,23.9,32.5
+15.8,16.7,29.2,441.0,94.7,27.4,48.3,851.0,9.91,25.5,44.9
+25.9,22.3,32.2,95.6,50.0,13.9,24.4,1094.0,5.67,13.2,30.8
+31.3,15.5,79.9,552.0,106.0,25.3,36.8,372.0,13.0,28.1,36.8
+17.6,17.9,14.3,25.5,12.5,43.3,79.1,557.0,9.91,16.7,25.0
+25.7,10.4,18.6,19.6,9.65,14.9,34.9,1027.0,10.0,30.0,57.8
+113.0,103.0,19.8,33.7,16.7,160.0,257.0,1794.0,27.4,64.9,84.3
+9.56,15.8,15.7,14.5,2.35,22.5,42.9,806.0,11.5,17.3,40.0
+48.3,23.5,33.1,111.0,31.1,6.73,30.2,743.0,4.87,23.9,41.4
+22.5,14.2,10.6,176.0,15.7,25.0,43.3,316.0,13.1,25.7,50.9
+22.7,3.37,20.5,30.2,8.9,18.8,40.0,784.0,19.5,31.6,32.5
+76.4,46.1,27.4,41.4,7.37,52.3,76.4,552.0,1.41,29.2,46.6
+20.5,9.73,20.5,23.3,9.06,33.1,46.1,487.0,11.1,23.9,36.2
+12.6,39.2,23.3,18.8,3.79,59.4,96.5,667.0,12.2,32.5,31.6
+43.7,23.1,17.0,17.9,2.86,38.2,47.0,264.0,7.91,15.4,24.1
+18.1,15.4,21.1,61.0,10.8,14.7,23.9,389.0,7.99,15.7,39.6
+21.7,10.6,18.8,12.5,6.92,179.0,279.0,2187.0,9.22,17.6,44.5
+126.0,21.9,20.9,25.0,9.91,16.7,23.7,474.0,14.1,24.4,48.7
+23.7,25.5,16.4,289.0,22.1,25.9,32.2,441.0,51.9,83.5,104.0
+21.1,5.0,35.2,53.3,8.35,123.0,250.0,3491.0,8.58,21.7,44.9
+22.5,10.5,18.9,17.2,4.74,93.9,142.0,956.0,10.4,35.9,38.5
+39.2,11.5,37.5,54.2,23.1,124.0,179.0,2288.0,18.9,36.2,38.2
+13.7,9.39,17.6,17.3,2.0,17.5,27.6,246.0,12.5,22.5,34.0
+32.2,18.1,91.4,382.0,76.4,17.6,38.9,882.0,73.0,139.0,328.0
+53.3,36.2,18.4,23.1,9.56,16.3,28.1,710.0,8.82,12.1,35.5
+19.5,7.17,80.6,491.0,81.3,27.6,46.6,1582.0,8.35,26.4,61.5
+16.8,20.7,3.92,20.7,10.6,30.2,51.4,328.0,11.4,28.9,37.9
+2.92,13.0,15.1,34.3,2.07,137.0,178.0,337.0,13.7,30.2,65.5
+27.6,13.0,11.2,14.6,9.82,65.5,93.1,418.0,14.3,26.9,51.9
+24.4,5.05,17.3,117.0,7.99,123.0,231.0,1526.0,23.9,48.3,69.2
+27.6,17.9,21.3,20.0,5.47,17.3,30.5,389.0,7.3,16.3,34.6
+163.0,39.2,17.0,11.4,9.06,143.0,235.0,1526.0,6.61,6.21,34.0
+17.5,8.06,24.1,38.5,25.0,48.7,66.7,352.0,57.8,67.3,29.2
+16.1,18.1,24.6,204.0,16.3,67.3,198.0,1655.0,10.0,16.5,34.6
+28.9,15.1,14.6,5.14,29.2,63.8,79.9,191.0,22.3,36.2,51.4
+22.5,62.1,15.7,21.5,22.7,64.9,121.0,1197.0,8.28,26.9,27.6
+25.3,58.8,70.4,308.0,67.9,4.37,12.0,264.0,10.0,24.8,25.3
+4.29,13.2,27.1,24.1,11.5,11.3,32.8,523.0,6.85,14.6,12.2
+17.9,11.7,17.8,161.0,13.1,12.6,21.1,588.0,51.4,109.0,143.0
+42.2,25.9,4.22,10.4,1.96,76.4,110.0,461.0,1.76,106.0,3.89
+25.3,21.5,66.1,382.0,77.7,37.9,57.8,483.0,14.3,39.6,42.6
+9.65,31.9,14.7,30.8,8.82,28.1,48.7,649.0,20.4,39.6,39.2
+8.74,13.7,10.2,176.0,27.9,56.2,119.0,1700.0,15.0,26.7,41.8
+17.2,12.0,25.3,91.4,15.3,7.7,34.9,1700.0,14.2,23.1,30.2
+22.9,21.9,14.9,26.4,8.43,55.2,91.4,882.0,9.56,17.5,32.5
+14.7,8.98,19.1,18.3,1.46,69.8,105.0,1252.0,19.8,31.1,31.6
+14.6,9.56,12.3,15.0,17.8,48.3,66.7,567.0,10.9,24.6,21.9
+24.6,22.7,13.6,75.0,6.73,20.2,37.9,500.0,9.73,38.2,106.0
+37.2,37.9,13.3,154.0,17.2,37.2,50.9,313.0,16.4,28.4,31.3
+85.8,106.0,9.22,257.0,34.3,14.7,18.9,94.7,9.73,30.5,30.2
+17.3,19.6,11.9,83.5,13.3,15.1,27.4,523.0,4.87,12.3,31.3
+9.22,28.1,19.6,14.9,6.92,47.8,76.4,813.0,12.9,18.1,26.9
+23.1,16.4,11.9,46.6,1.01,2.94,25.3,461.0,8.35,15.5,10.6
+13.3,10.2,19.5,20.5,5.0,6.92,15.7,717.0,20.0,32.5,61.5
+20.5,9.22,50.9,161.0,71.0,10.7,19.3,449.0,7.77,17.3,61.5
+12.6,30.5,61.0,461.0,82.0,11.9,22.3,457.0,6.73,24.1,33.1
+55.7,51.9,11.3,80.6,8.74,46.6,45.3,407.0,104.0,125.0,49.1
+20.9,16.3,8.28,111.0,5.67,30.2,52.3,474.0,13.9,30.2,39.2
+100.0,73.0,23.1,26.4,11.1,9.06,28.4,496.0,23.1,47.0,62.6
+17.8,17.9,10.2,24.1,21.7,38.2,39.6,308.0,15.0,25.7,36.2
+29.2,16.3,9.82,28.1,4.45,23.1,54.7,1420.0,17.9,28.1,54.7
+19.5,15.4,22.1,21.5,10.3,34.9,52.8,661.0,7.77,17.5,32.2
+33.1,17.0,51.4,505.0,65.5,69.2,104.0,1000.0,5.38,135.0,10.6
+47.4,26.2,41.4,202.0,30.2,7.37,16.7,578.0,2.21,23.5,25.3
+7.5,11.7,21.9,28.6,14.7,3.52,24.8,433.0,7.3,23.7,51.4
+47.0,18.6,13.3,35.5,3.16,20.5,28.9,578.0,10.4,24.1,36.5
+30.8,15.7,63.2,552.0,51.4,18.6,27.4,528.0,74.3,129.0,153.0
+10.6,14.6,14.7,22.3,9.91,12.7,44.9,1065.0,14.2,30.0,76.4
+33.1,58.8,29.7,368.0,34.3,40.7,53.8,906.0,14.1,28.1,57.3
+16.3,16.1,5.38,5.62,11.8,28.9,41.0,300.0,8.13,20.0,25.0
+123.0,73.0,13.9,107.0,22.5,20.5,39.2,661.0,19.8,48.7,157.0
+22.5,17.0,25.7,33.1,12.2,44.1,72.3,1700.0,11.8,40.7,102.0
+26.2,11.3,4.91,2.69,9.82,32.2,50.0,382.0,8.13,17.8,18.1
+18.4,9.31,25.9,305.0,47.4,28.6,43.7,359.0,24.1,53.8,89.0
+36.8,20.9,19.3,28.4,2.25,124.0,168.0,679.0,10.6,34.0,32.2
+19.1,25.9,26.2,173.0,19.8,61.5,115.0,2247.0,19.8,31.3,62.1
+17.6,18.9,17.8,20.7,10.9,5.99,50.0,588.0,9.82,23.5,39.6
+21.5,8.51,29.7,106.0,12.4,106.0,178.0,1981.0,34.3,79.9,110.0
+18.8,8.74,1.0,7.1,11.0,5.52,20.5,523.0,14.5,25.0,59.4
+36.2,10.8,47.8,53.3,5.73,8.9,26.2,965.0,2.33,13.7,51.9
+3.46,2.39,6.49,23.9,18.3,132.0,189.0,644.0,10.7,31.6,61.5
+47.0,25.9,19.3,16.1,1.0,17.8,98.2,2839.0,12.9,24.4,37.2
+7.37,11.1,12.7,107.0,9.14,13.0,23.7,644.0,22.7,39.2,49.1
+17.9,12.3,1.02,10.6,11.4,2.23,29.4,474.0,8.66,2.33,12.1
+19.6,18.9,18.1,38.2,23.3,4.7,27.6,851.0,10.0,34.6,49.1
+17.9,19.8,41.4,191.0,18.8,3.72,27.4,372.0,10.1,21.7,29.7
+12.6,16.3,15.5,62.6,19.1,28.6,47.0,483.0,6.32,20.0,43.7
+75.7,57.3,23.3,202.0,36.5,4.7,12.4,441.0,12.5,23.3,70.4
+113.0,66.7,46.6,433.0,59.9,18.4,31.9,851.0,22.3,38.2,40.7
+120.0,53.3,5.0,12.1,11.0,114.0,160.0,991.0,4.57,25.0,40.7
+35.5,25.0,13.9,103.0,15.1,15.0,22.7,594.0,12.1,19.8,33.7
+33.1,22.7,4.22,3.08,12.5,60.4,107.0,1358.0,7.7,6.55,30.5
+15.3,7.17,19.8,22.9,7.91,14.5,38.9,644.0,21.7,45.7,110.0
+14.1,22.3,15.3,343.0,40.7,28.6,47.4,334.0,7.3,52.3,115.0
+28.1,24.8,20.9,23.7,6.38,12.5,27.1,414.0,13.1,27.6,32.8
+28.1,11.0,36.2,37.2,28.1,101.0,149.0,1263.0,15.8,28.1,69.8
+8.13,18.3,19.6,21.5,11.5,29.4,50.5,349.0,5.62,18.6,31.1
+11.2,49.6,26.4,44.5,33.7,26.9,47.8,382.0,7.99,26.4,40.3
+28.4,22.3,36.5,33.1,11.2,35.9,56.2,294.0,16.5,30.0,67.3
+25.7,15.3,35.2,38.2,2.05,36.5,56.2,588.0,9.56,21.3,40.0
+16.5,14.7,23.1,17.3,1.06,76.4,150.0,2054.0,13.0,29.4,47.4
+11.7,15.5,28.1,33.4,9.65,38.9,50.5,604.0,4.14,9.47,43.7
+124.0,73.0,18.6,30.2,8.2,11.9,29.7,403.0,27.9,64.9,112.0
+23.9,14.6,11.9,233.0,43.7,71.7,92.2,1395.0,7.84,40.0,52.8
+20.7,15.4,59.4,193.0,58.3,76.4,115.0,359.0,11.3,20.4,34.0
+17.2,12.3,17.3,178.0,31.9,32.5,48.3,496.0,16.0,34.0,28.1
+23.5,8.58,25.7,33.7,15.0,119.0,281.0,1670.0,12.2,29.4,32.8
+13.7,18.6,15.0,106.0,9.47,8.9,18.9,583.0,11.5,18.3,31.6
+119.0,37.2,67.9,528.0,92.2,54.7,73.0,385.0,11.1,40.0,37.5
+14.3,11.9,46.1,69.2,72.3,42.9,75.7,717.0,7.37,18.1,49.1
+66.7,31.1,12.1,213.0,10.2,44.9,51.4,279.0,6.98,21.9,39.2
+26.7,19.1,18.9,22.1,7.91,25.3,36.2,328.0,4.29,2.23,13.3
+22.7,16.1,14.5,70.4,15.0,19.6,22.3,692.0,10.6,31.6,27.6
+26.2,17.2,7.17,106.0,16.0,9.73,15.7,578.0,13.8,26.7,89.0
+33.1,17.9,12.9,158.0,27.4,82.8,146.0,1499.0,12.1,20.7,37.5
+17.3,8.66,2.92,9.22,3.72,52.3,97.3,1358.0,13.5,19.6,30.2
+8.74,20.0,7.23,319.0,32.5,31.9,71.0,3106.0,12.2,17.5,51.9
+20.7,3.79,53.8,229.0,46.1,20.4,29.7,426.0,12.4,26.7,63.2
+73.0,63.2,32.2,28.6,6.15,67.9,112.0,2890.0,16.4,24.4,64.4
+18.4,10.6,2.27,1.11,509.0,35.5,62.1,588.0,6.92,21.5,59.4
+38.2,34.0,13.2,20.5,11.9,4.91,12.7,441.0,22.5,30.2,73.0
+11.2,22.7,12.2,139.0,10.1,12.7,26.9,547.0,31.9,41.4,52.3
+66.7,42.6,16.7,10.5,4.45,28.6,39.6,302.0,33.7,50.5,77.7
+1.01,1.0,1.73,4.96,5.83,42.6,70.4,509.0,16.4,26.7,47.4
+9.31,11.3,27.6,20.7,5.57,100.0,202.0,2017.0,8.51,15.3,26.2
+22.1,6.67,8.98,168.0,9.22,15.4,34.9,547.0,15.4,47.0,66.1
+21.5,11.0,10.2,209.0,16.0,13.5,19.5,583.0,28.6,42.9,79.9
+45.3,18.6,28.4,45.3,12.9,213.0,337.0,4255.0,9.39,8.06,35.2
+20.7,15.7,18.6,114.0,30.5,31.1,50.9,385.0,11.9,26.7,53.3
+82.0,61.5,18.9,30.5,2.97,57.8,119.0,1762.0,11.4,15.3,42.2
+15.1,14.5,10.7,10.7,2.35,32.8,55.7,334.0,7.99,16.1,34.6
+17.0,14.9,24.4,29.2,13.5,64.4,103.0,1334.0,16.5,42.6,63.2
+24.6,32.2,22.3,23.9,6.26,104.0,188.0,2788.0,10.2,25.9,53.3
+23.9,15.1,26.9,19.5,3.4,5.67,21.5,692.0,15.0,35.5,45.3
+28.9,16.1,13.2,62.6,21.7,21.3,31.3,519.0,8.35,18.3,15.5
+70.4,55.2,9.14,16.3,10.0,37.5,55.7,422.0,10.9,23.9,32.8
+20.9,11.4,26.4,26.7,14.7,32.5,60.4,514.0,16.5,20.7,40.0
+89.0,67.3,16.0,24.1,5.09,27.4,36.8,470.0,19.1,21.1,31.1
+12.9,4.14,17.5,13.1,10.3,3.34,33.1,710.0,10.7,37.9,81.3
+19.5,4.53,66.7,297.0,66.1,46.6,62.6,461.0,47.8,82.0,106.0
+17.3,13.8,29.7,313.0,41.8,35.9,48.3,445.0,11.7,35.2,73.7
+74.3,42.2,24.1,28.6,7.57,18.4,37.9,552.0,22.5,39.6,47.8
+22.1,24.1,27.4,400.0,32.8,196.0,274.0,931.0,16.7,24.4,40.0
+18.3,20.9,49.6,114.0,25.7,38.5,52.8,449.0,18.3,26.9,45.7
+50.0,50.0,58.8,379.0,80.6,14.3,18.4,496.0,6.67,13.8,14.6
+38.9,9.91,35.5,93.9,21.9,8.51,54.7,1186.0,5.73,34.6,38.5
+25.0,10.0,17.2,17.0,3.31,34.6,46.6,281.0,9.65,17.0,48.7
+22.5,14.3,13.1,122.0,20.9,35.9,71.7,1186.0,9.82,30.5,28.1
+13.0,26.7,28.6,33.4,16.1,64.4,118.0,1046.0,12.4,37.5,147.0
+17.2,15.1,29.7,453.0,48.3,33.7,47.8,1263.0,40.0,78.4,121.0
+9.73,3.05,30.5,30.2,10.4,15.0,57.3,1144.0,11.1,20.0,49.6
+21.5,37.9,22.3,24.4,6.44,37.5,55.7,429.0,5.78,27.4,52.3
+11.2,13.2,17.6,7.04,13.8,32.5,46.1,410.0,2.57,64.9,3.31
+3.96,13.7,12.0,123.0,13.2,35.2,53.8,615.0,3.43,23.1,35.2
+25.7,8.58,25.3,27.6,8.74,28.6,37.5,426.0,11.2,26.2,32.2
+16.8,18.3,56.7,567.0,79.1,43.3,65.5,737.0,16.8,19.1,25.0
+71.7,58.3,69.2,523.0,61.0,16.4,29.7,542.0,21.9,41.0,59.9
+48.3,47.0,18.4,14.5,3.11,15.8,60.4,2227.0,8.9,24.4,39.2
+21.9,2.76,22.9,125.0,14.1,15.5,26.9,392.0,37.5,70.4,145.0
+7.3,16.8,12.7,202.0,16.7,28.9,49.1,594.0,5.05,30.2,28.1
+19.1,10.4,12.1,195.0,13.0,97.3,151.0,1843.0,9.73,33.7,37.9
+20.7,12.2,12.6,22.5,17.2,96.5,127.0,1155.0,6.55,31.3,45.7
+30.2,17.9,66.1,276.0,66.7,50.0,76.4,673.0,29.7,56.7,74.3
+22.3,22.7,12.7,64.9,6.98,38.5,77.7,2350.0,8.98,18.1,45.7
+30.0,20.7,20.0,17.8,12.1,3.96,17.3,407.0,10.9,26.2,66.7
+26.2,4.14,11.5,15.0,10.3,12.1,21.9,578.0,15.1,30.0,53.3
+27.9,14.3,9.65,14.3,7.84,19.6,33.1,331.0,5.94,18.9,26.4
+20.9,5.52,23.5,292.0,56.7,158.0,257.0,1794.0,16.3,41.0,45.7
+16.3,20.0,16.1,25.3,1.45,55.2,78.4,505.0,10.4,18.9,44.5
+13.7,13.0,25.5,28.6,8.74,16.4,41.4,466.0,13.3,31.9,50.9
+16.0,17.2,11.5,21.7,9.39,129.0,209.0,1860.0,12.1,14.9,36.5
+22.7,19.6,26.2,26.7,18.9,16.8,30.5,615.0,13.3,25.0,39.6
+36.8,14.5,17.5,23.5,9.06,9.31,41.4,1298.0,44.9,71.7,119.0
+8.06,15.7,27.9,31.3,9.47,14.2,36.8,851.0,9.82,15.4,37.2
+31.6,49.6,9.22,167.0,23.7,84.3,103.0,311.0,5.47,15.3,23.1
+58.8,11.4,80.6,491.0,61.5,21.5,47.4,882.0,13.5,27.1,27.1
+18.4,11.5,5.62,15.8,9.82,4.0,17.8,523.0,28.4,58.8,126.0
+40.0,23.7,2.15,60.4,8.28,23.9,45.7,284.0,8.35,7.3,43.3
+12.7,15.8,16.4,13.1,3.34,21.9,46.1,461.0,9.14,20.0,28.1
+25.3,3.96,8.82,5.14,4.78,18.8,37.9,723.0,35.9,76.4,186.0
+19.6,18.6,56.7,422.0,79.1,4.53,8.98,209.0,6.32,11.2,24.6
+29.7,26.2,10.8,25.9,13.7,19.5,30.2,843.0,3.68,18.8,48.7
+16.7,9.82,20.2,372.0,57.8,65.5,89.0,362.0,8.43,15.4,40.3
+10.3,11.8,13.7,85.8,20.0,45.3,77.0,1186.0,13.7,20.2,33.1
+16.1,10.0,19.3,23.9,11.0,123.0,205.0,956.0,18.6,37.5,59.4
+20.4,17.6,18.4,20.7,3.13,13.6,27.4,806.0,13.8,33.7,70.4
+8.82,6.38,17.9,15.1,3.75,35.9,50.9,445.0,37.5,46.1,34.6
+73.0,67.9,35.2,63.2,18.9,42.2,66.1,523.0,13.9,21.9,14.1
+22.1,21.7,16.4,18.8,2.57,11.2,24.6,594.0,8.51,24.4,38.5
+33.4,14.6,9.73,157.0,13.6,28.4,47.8,478.0,6.85,12.9,16.5
+27.1,7.84,57.8,276.0,44.9,30.2,53.3,519.0,13.3,32.2,77.7
+25.9,16.1,13.6,16.1,15.7,29.4,44.9,599.0,3.49,32.8,41.0
+76.4,50.5,5.99,13.5,15.0,36.5,63.8,509.0,12.7,19.3,34.3
+23.5,7.99,22.7,34.3,11.4,153.0,276.0,2017.0,5.67,35.5,39.6
+20.5,8.43,20.9,23.3,8.66,33.4,54.2,311.0,9.56,21.1,25.5
+30.0,17.0,29.4,31.9,5.05,13.8,23.7,267.0,14.2,30.5,27.1
+27.6,9.65,5.62,10.4,8.35,38.9,73.7,1286.0,10.6,19.5,37.5
+13.8,12.3,24.8,20.7,7.3,39.2,57.8,426.0,13.7,26.7,35.5
+16.3,20.9,51.9,66.1,37.9,7.17,18.8,626.0,16.3,43.3,31.1
+76.4,70.4,21.1,25.7,5.33,38.5,62.1,483.0,15.4,16.3,44.1
+21.7,22.5,21.9,29.7,7.57,37.5,69.8,723.0,7.57,17.3,18.6
+22.3,7.7,38.9,75.0,8.2,2.33,18.8,422.0,42.2,61.5,73.0
+14.5,40.0,12.7,143.0,34.0,62.1,109.0,1144.0,9.56,24.8,40.3
+61.0,42.6,18.1,27.9,4.66,10.3,16.5,337.0,37.5,73.0,119.0
+30.8,23.1,74.3,410.0,65.5,77.0,163.0,1219.0,16.1,20.7,39.6
+1.0,5.0,8.9,184.0,19.1,7.57,27.6,588.0,1.43,98.2,7.7
+27.4,15.3,19.5,29.2,9.39,64.9,87.4,764.0,6.85,34.3,20.5
+13.1,16.7,57.3,379.0,56.7,84.3,181.0,1486.0,10.4,25.3,30.8
+20.7,7.77,23.1,55.7,12.9,93.9,176.0,1512.0,34.3,38.9,64.9
+7.91,12.7,9.91,22.3,7.64,32.8,48.3,302.0,8.51,21.7,39.6
+10.9,18.4,18.3,10.6,5.52,40.7,60.4,343.0,8.51,20.5,34.6
+15.1,10.7,10.1,78.4,9.91,19.3,38.2,692.0,389.0,542.0,110.0
+17.3,12.6,24.6,30.0,6.98,16.3,26.2,372.0,18.6,32.2,38.9
+175.0,43.3,29.4,41.4,16.8,1.96,10.1,213.0,5.09,4.66,4.22
+41.8,39.6,12.0,126.0,11.1,7.37,24.4,528.0,17.8,33.7,57.3
+41.8,16.1,28.6,25.0,8.82,18.4,31.3,483.0,11.5,38.2,76.4
+16.7,12.7,14.7,77.7,13.2,5.99,42.6,441.0,8.66,25.9,44.1
+79.9,167.0,14.7,22.7,7.43,13.6,27.9,588.0,10.6,9.56,16.8
+16.8,16.5,25.0,20.9,7.91,53.3,85.8,813.0,20.7,40.7,19.8
+15.1,11.8,55.7,129.0,26.4,31.9,48.7,352.0,10.4,13.5,22.7
+7.43,10.6,13.1,93.1,10.9,42.9,57.3,365.0,6.26,20.7,38.9
+13.9,8.66,14.7,31.6,6.67,93.1,196.0,2414.0,10.0,22.3,24.4
+17.3,16.1,13.2,14.7,5.62,12.9,30.8,621.0,20.0,42.2,76.4
+25.9,17.2,17.8,13.9,4.07,25.5,27.9,382.0,11.3,23.7,47.8
+7.37,14.1,34.3,32.8,9.31,23.7,40.3,610.0,30.5,60.4,114.0
+20.4,16.0,54.2,86.6,42.9,99.1,170.0,1963.0,12.1,20.9,29.2
+14.3,15.8,32.5,32.2,18.3,6.67,16.5,1000.0,11.1,17.8,36.8
+19.1,13.2,24.4,147.0,14.6,66.7,93.1,757.0,12.6,43.7,82.8
+94.7,50.9,26.4,48.7,13.5,64.9,117.0,2595.0,19.5,40.7,62.6
+12.5,9.06,14.2,179.0,23.7,13.0,30.0,400.0,22.5,42.9,59.9
+11.7,5.23,24.4,42.6,9.82,42.6,59.4,533.0,3.65,16.8,44.9
+10.3,18.3,23.9,27.4,1.22,24.4,38.2,710.0,18.8,15.0,41.0
+12.1,25.0,5.94,449.0,45.3,93.9,153.0,1568.0,4.29,47.0,6.49
+21.3,13.8,45.3,422.0,49.6,167.0,279.0,2890.0,16.3,28.6,35.2
+51.9,32.2,11.1,175.0,8.35,73.0,131.0,1263.0,13.9,31.9,32.8
+26.2,12.4,21.1,24.4,4.96,114.0,244.0,1946.0,1.25,18.6,4.78
+13.7,11.3,27.6,30.2,4.41,12.5,19.6,505.0,10.6,19.6,48.7
+14.5,9.65,5.67,302.0,20.9,34.0,55.7,311.0,13.1,28.6,37.9
+8.9,20.0,23.5,21.7,2.89,1.1,13.9,178.0,15.7,22.3,39.6
+25.3,7.57,22.3,29.2,11.0,22.7,31.9,267.0,15.5,29.2,61.0
+34.0,22.5,93.9,667.0,73.7,22.9,38.9,433.0,34.6,54.7,37.5
+6.79,5.57,47.8,176.0,57.8,27.4,45.7,352.0,17.0,20.0,22.1
+52.3,31.3,21.9,139.0,17.5,21.5,33.7,433.0,16.1,25.0,29.7
+30.0,17.9,18.1,17.2,2.86,18.3,36.5,445.0,11.5,22.9,41.4
+21.3,22.7,8.35,149.0,16.1,23.7,38.9,289.0,20.5,38.5,49.6
+11.8,8.35,22.3,24.8,4.83,13.6,13.8,328.0,5.78,26.9,30.0
+47.4,19.3,22.7,30.8,6.92,30.0,45.3,562.0,7.23,31.9,49.1
+37.9,12.3,18.4,33.1,13.2,5.38,12.2,588.0,11.4,22.1,6.92
+64.4,44.1,21.7,25.7,4.61,86.6,126.0,359.0,9.39,22.5,39.6
+28.9,13.1,8.74,58.8,5.0,8.2,54.7,1094.0,38.5,113.0,142.0
+95.6,49.6,23.1,30.5,6.55,22.3,37.5,491.0,5.52,11.8,33.4
+29.4,47.0,9.47,196.0,27.9,33.4,52.3,426.0,44.9,88.2,161.0
+98.2,71.7,18.3,23.1,7.5,28.4,49.1,422.0,11.0,22.5,37.9
+145.0,133.0,40.7,389.0,73.0,29.2,34.0,389.0,10.4,16.0,49.6
+72.3,49.6,27.6,19.6,8.74,43.3,98.2,2187.0,1.0,8.13,40.3
+13.6,11.5,80.6,538.0,70.4,16.8,30.8,757.0,13.1,26.7,66.1
+15.5,5.09,10.0,142.0,18.4,22.5,34.6,437.0,15.5,32.8,67.9
+20.2,25.7,12.7,155.0,18.6,6.67,48.7,453.0,11.9,24.4,37.5
+79.9,48.3,20.9,19.6,2.86,28.9,24.6,457.0,17.2,24.4,104.0
+2.97,6.98,15.5,103.0,10.6,34.3,50.9,382.0,10.9,19.8,30.2
+16.1,18.6,28.4,143.0,13.3,47.8,69.2,445.0,56.7,149.0,337.0
+20.0,19.3,14.5,28.4,10.3,24.1,53.8,284.0,9.82,31.3,52.3
+25.9,18.8,6.61,20.7,8.43,14.5,33.4,594.0,6.32,12.2,1.0
+21.5,10.6,3.22,2.44,7.43,29.7,43.3,372.0,6.49,14.9,23.1
+14.9,14.7,24.6,34.3,12.5,13.3,17.6,604.0,13.9,14.1,41.0
+8.58,10.7,98.2,204.0,58.3,22.9,42.2,343.0,20.7,52.3,11.2
+10.5,15.5,13.5,19.6,1.68,17.6,42.6,667.0,12.5,33.4,73.7
+72.3,62.6,21.7,27.4,15.4,24.1,35.5,281.0,15.0,12.2,41.0
+25.7,24.8,20.4,20.4,2.89,6.79,33.1,588.0,59.9,160.0,316.0
+12.3,9.65,15.7,30.5,4.57,58.8,86.6,1554.0,17.2,36.2,31.1
+22.9,35.5,16.5,14.9,5.28,53.3,86.6,567.0,10.4,33.1,24.6
+12.5,13.2,10.3,23.9,5.05,86.6,131.0,1999.0,11.2,16.7,55.2
+44.5,17.9,37.9,64.4,27.4,75.7,147.0,1065.0,12.3,19.6,21.5
+16.1,26.2,20.2,18.8,5.94,23.5,36.2,379.0,26.7,40.7,67.9
+12.0,6.15,17.3,44.1,8.82,59.9,93.1,604.0,15.0,31.1,49.1
+15.8,11.7,19.3,17.8,7.7,47.4,117.0,2690.0,45.3,67.3,13.8
+14.9,9.56,21.3,29.7,16.1,67.3,113.0,1241.0,33.7,58.8,164.0
+24.8,34.0,13.3,18.4,6.92,27.1,46.1,858.0,10.7,34.3,39.6
+14.2,13.2,11.9,100.0,5.19,37.9,57.8,757.0,11.8,19.1,40.3
+62.1,47.0,15.4,22.7,5.78,36.2,49.6,461.0,12.2,19.6,37.5
+10.5,6.98,23.5,35.5,5.23,32.2,53.8,851.0,14.1,20.2,78.4
+24.1,1.0,13.0,403.0,84.3,20.5,21.5,255.0,1.63,84.3,1.36
+19.3,1.01,19.3,112.0,37.2,64.9,61.0,276.0,2.37,137.0,1.2
+3.43,1.96,9.22,183.0,22.9,10.5,15.8,632.0,19.5,36.2,1.12
+16.4,1.01,48.7,385.0,113.0,9.39,23.9,704.0,8.9,15.8,1.14
+29.4,1.0,15.5,30.0,17.5,8.43,18.4,340.0,18.4,61.0,6.1
+36.8,1.0,30.8,225.0,85.1,13.1,13.7,248.0,1.14,414.0,2.05
+19.3,1.01,22.3,239.0,38.2,26.2,26.2,337.0,1.0,3.11,1.09
+42.2,6.49,22.5,21.9,16.0,15.5,19.6,241.0,1.0,82.8,1.24
+54.2,4.83,58.8,55.7,19.1,124.0,181.0,3191.0,1.0,1.0,1.0
+20.0,1.0,3.79,5.23,15.3,30.0,33.4,276.0,1.0,173.0,2.04
+20.4,1.0,37.9,355.0,82.8,12.6,19.3,271.0,1.0,626.0,2.11
+136.0,1.0,41.4,57.8,15.5,13.2,17.9,305.0,1.0,8.66,1.0
+17.5,1.21,27.4,271.0,86.6,49.1,46.1,791.0,1.07,1.0,3.62
+29.2,2.13,22.9,25.5,3.43,13.0,17.2,292.0,1.0,1.63,1.21
+16.4,1.01,32.8,35.2,6.26,10.2,16.8,233.0,1.0,25.5,6.98
+7.5,1.01,23.7,146.0,55.7,142.0,179.0,2839.0,1.0,59.9,2.69
+28.9,1.27,33.1,14.2,62.1,79.9,95.6,1540.0,1.0,396.0,1.63
+20.2,1.01,15.3,257.0,31.3,1.0,3.05,8.58,1.3,1.0,3.72
+138.0,1.01,52.3,178.0,58.3,23.5,23.9,385.0,1.0,3.49,2.69
+77.0,5.83,15.0,15.1,13.5,8.28,13.7,239.0,1.0,1.01,2.33
+41.8,1.01,1.0,6.32,1.75,7.91,8.35,308.0,1.0,1.01,1.6
+31.6,1.01,13.7,77.0,26.2,12.6,13.9,316.0,1.0,1.0,2.09
+1.0,1.0,48.7,202.0,62.1,5.83,16.7,461.0,1.0,5.52,2.44
+22.9,1.0,21.7,138.0,39.2,24.6,28.1,349.0,1.84,1.0,4.29
+11.1,1.01,17.6,365.0,46.6,17.5,24.1,267.0,1.0,1.01,1.03
+17.0,1.01,23.1,26.9,21.5,2.53,11.8,305.0,1.53,37.2,2.33
+20.0,1.0,2.74,4.7,23.7,47.8,65.5,1446.0,1.0,27.6,1.5
+57.3,1.01,71.0,204.0,130.0,5.88,9.73,403.0,7.17,21.5,5.42
+20.5,1.01,8.74,27.6,22.5,7.1,10.4,257.0,1.0,1.75,1.0
+30.5,1.25,40.0,34.3,13.5,20.5,22.7,334.0,1.0,246.0,1.51
+28.4,1.01,35.9,231.0,73.0,7.91,20.7,343.0,1.0,1.0,2.19
+42.6,1.13,3.43,89.8,9.91,79.9,84.3,1094.0,1.0,1.01,1.0
+43.3,1.0,8.51,22.5,1.0,13.8,23.3,578.0,1.0,1.01,1.49
+5.62,1.11,41.4,34.9,7.43,34.6,41.4,538.0,1.0,1.0,1.21
+71.0,1.0,10.7,14.2,29.4,2.17,11.2,346.0,1.0,13.2,3.37
+42.9,2.13,21.3,33.1,20.4,7.37,11.8,352.0,1.0,2.62,1.37
+12.4,1.07,9.31,22.3,13.1,11.7,22.5,274.0,1.0,34.6,2.19
+5.94,1.0,37.5,10.9,53.3,129.0,151.0,2227.0,4.29,36.5,2.81
+16.8,1.22,52.8,457.0,101.0,6.49,15.1,349.0,1.0,1.32,1.55
+39.6,1.0,33.7,621.0,142.0,2.94,15.7,562.0,1.0,11.2,2.53
+22.9,1.42,14.9,34.6,30.5,24.1,33.7,433.0,1.0,113.0,1.0
+25.5,1.01,24.4,26.7,46.1,20.7,26.4,302.0,1.0,7.84,1.0
+15.7,1.01,41.0,49.1,25.9,40.0,56.7,890.0,3.19,11.7,1.64
+21.3,1.01,2.11,11.8,9.82,16.1,25.9,426.0,1.0,6.32,1.47
+40.3,1.03,23.9,62.6,20.9,9.22,19.8,334.0,1.0,1.01,1.96
+36.5,1.21,28.9,30.0,11.4,5.09,22.5,235.0,1.0,1.0,1.0
+27.9,1.01,18.3,233.0,74.3,11.5,12.7,250.0,2.37,1370.0,2.86
+1.0,1.58,101.0,453.0,129.0,6.04,15.3,355.0,1.24,1.0,1.0
+27.4,4.29,16.8,44.9,16.0,1.73,11.2,271.0,1.24,28.1,1.86
+25.7,1.32,79.9,500.0,164.0,8.43,12.2,340.0,1.0,15.1,1.0
+31.9,1.01,42.6,313.0,168.0,19.5,16.1,308.0,10.7,403.0,1.04
+82.0,1.33,9.31,213.0,15.8,14.2,19.5,257.0,1.0,82.8,1.26
+170.0,1.0,20.2,138.0,13.7,14.1,11.7,352.0,1.0,1.0,1.41
+62.1,1.0,31.9,32.5,11.9,145.0,237.0,2813.0,1.07,1.0,1.19
+16.3,1.2,29.7,119.0,37.9,12.5,11.3,235.0,1.21,93.1,1.93
+26.4,1.01,4.18,1.91,939.0,24.1,28.4,337.0,1.0,1.0,1.79
+40.3,2.11,18.4,115.0,25.0,12.1,19.3,281.0,2.92,38.5,4.49
+21.3,1.01,20.9,48.7,21.3,24.6,24.4,372.0,1.0,1.83,1.0
+52.3,1.01,16.5,29.7,23.1,8.9,17.3,343.0,1.0,7.1,2.27
+20.0,1.01,25.3,27.9,1.0,10.2,15.1,239.0,1.0,3.52,1.01
+29.2,1.01,15.4,41.8,24.4,11.3,27.9,429.0,1.0,71.0,1.27
+29.7,1.0,26.9,26.9,31.1,26.7,34.9,308.0,1.0,44.5,1.0
+30.5,1.0,17.8,188.0,48.3,12.6,12.6,311.0,1.0,422.0,1.57
+76.4,1.36,8.43,4.83,1.0,10.8,17.6,355.0,1.0,4.07,1.01
+40.0,1.01,6.79,9.47,3.62,13.1,11.8,389.0,1.0,1.55,1.54
+44.1,1.01,28.1,22.5,10.6,21.1,37.2,445.0,1.0,8.98,1.88
+37.2,1.0,11.5,18.8,25.3,34.0,35.2,319.0,1.06,1.0,2.39
+70.4,1.0,9.65,18.9,23.9,10.1,14.7,244.0,1.01,1.51,1.01
+37.9,1.01,7.17,21.1,20.2,1.5,10.3,615.0,1.0,1.01,1.5
+33.7,1.15,32.5,496.0,103.0,17.6,25.3,334.0,1.21,8.98,4.83
+61.5,1.01,34.3,457.0,73.0,25.7,26.4,365.0,1.08,1.0,1.86
+34.9,1.01,117.0,882.0,255.0,41.0,75.7,1459.0,1.81,86.6,1.17
+23.5,1.58,18.1,15.3,3.4,71.0,108.0,2091.0,1.0,2.5,1.0
+25.3,1.03,10.9,40.0,16.7,75.7,68.5,316.0,1.0,1.0,1.0
+39.2,1.68,22.1,191.0,30.8,4.96,17.5,396.0,1.0,1.86,1.31
+38.9,1.2,8.74,19.5,15.1,79.1,97.3,1499.0,4.18,42.9,3.92
+1.0,1.07,10.7,122.0,30.5,68.5,79.9,1094.0,1.0,16.1,3.11
+32.2,1.01,20.4,89.0,31.9,5.09,25.3,403.0,1.0,5.62,3.52
+35.9,1.01,7.43,17.5,19.5,13.0,16.8,368.0,1.0,11.1,1.83
+52.3,1.01,7.99,16.3,9.39,18.8,33.4,519.0,7.3,76.4,4.78
+14.7,1.01,23.3,33.4,23.7,19.1,20.4,294.0,1.0,126.0,1.15
+31.6,1.01,34.6,40.3,34.6,16.8,21.9,422.0,1.21,154.0,1.33
+35.5,1.01,14.7,20.0,11.7,7.84,10.7,257.0,1.0,1.43,1.95
+34.3,1.01,36.2,45.3,34.0,6.32,9.31,244.0,1.0,1.0,2.69
+41.8,1.0,71.7,410.0,202.0,12.1,30.0,1655.0,1.0,173.0,1.73
+24.1,1.01,27.9,27.4,32.2,58.8,71.7,1322.0,1.0,2.41,2.11
+71.0,1.38,24.1,150.0,46.1,13.7,17.2,276.0,1.0,1.0,1.73
+86.6,1.01,41.4,279.0,66.7,51.9,69.2,851.0,1.0,1.09,1.47
+143.0,1.01,16.1,122.0,26.7,15.1,43.3,1134.0,1.0,3.46,1.0
+8.28,1.0,13.9,137.0,30.5,10.0,10.8,302.0,2.23,1.0,2.44
+29.4,1.04,10.6,35.2,22.5,12.0,20.5,352.0,1.0,1.0,1.0
+40.3,1.06,24.6,26.2,18.3,6.15,10.5,259.0,1.0,4.18,2.29
+38.5,1.24,24.4,50.9,42.9,27.4,24.6,213.0,11.1,1197.0,14.3
+38.5,2.07,15.8,22.3,20.9,5.67,20.5,615.0,7.99,172.0,6.98
+26.4,1.0,93.9,820.0,195.0,84.3,92.2,1382.0,15.3,777.0,24.1
+37.9,1.01,18.6,18.4,2.37,12.1,15.8,257.0,1.1,132.0,2.37
+27.9,1.01,20.5,20.2,9.31,19.6,28.1,292.0,1.27,12.0,1.79
+31.9,1.0,21.9,14.1,10.8,3.59,15.0,426.0,2.64,108.0,1.3
+227.0,1.01,5.57,15.4,3.75,8.98,11.1,385.0,1.0,161.0,1.37
+34.0,1.01,11.1,154.0,28.1,63.2,67.9,1512.0,1.0,1.0,1.57
+32.2,1.33,10.6,25.7,6.38,3.22,5.33,392.0,1.0,1.01,2.59
+4.0,1.0,64.4,362.0,209.0,79.1,111.0,1715.0,1.08,21.9,1.88
+36.8,1.17,82.0,253.0,155.0,7.3,13.7,331.0,1.0,15.5,2.0
+36.5,1.0,29.7,30.0,19.5,12.5,12.2,246.0,1.86,103.0,2.84
+173.0,1.0,5.83,11.3,11.0,22.3,27.6,322.0,1.0,17.3,1.27
+35.9,1.01,14.3,85.1,25.7,6.32,9.82,262.0,16.5,4.7,1.0
+84.3,1.36,12.3,200.0,42.9,3.85,11.1,264.0,1.0,1.36,2.84
+38.9,3.89,18.6,77.7,22.1,5.99,30.0,644.0,1.0,10.2,1.14
+30.5,1.0,31.3,99.1,14.5,2.69,6.92,313.0,1.51,2.04,1.41
+31.3,1.01,54.2,189.0,94.7,22.1,31.3,221.0,1.0,11.2,1.84
+35.9,1.27,19.5,105.0,19.1,13.2,16.3,418.0,3.82,167.0,2.41
+38.2,1.0,23.9,21.3,10.3,13.1,17.0,449.0,1.0,74.3,1.3
+48.3,1.01,13.1,289.0,58.8,150.0,259.0,3078.0,9.06,106.0,19.5
+17.8,1.98,41.0,51.9,42.2,12.3,16.0,246.0,2.13,17.0,1.0
+34.6,1.01,8.51,244.0,22.7,196.0,215.0,2167.0,1.81,2.41,1.29
+35.5,1.0,35.5,115.0,54.7,13.5,22.5,368.0,1.0,1.21,2.25
+33.4,1.01,35.2,34.6,28.6,7.57,12.4,241.0,1.49,42.9,3.72
+9.91,1.07,8.06,10.8,16.7,7.7,10.6,372.0,1.0,15.4,1.31
+45.7,1.01,23.7,83.5,46.6,33.4,42.2,1018.0,1.0,13.1,1.33
+44.9,1.01,27.1,35.5,17.2,5.67,7.23,259.0,1.91,1.0,1.39
+39.6,2.59,51.9,85.1,122.0,22.3,67.9,1322.0,1.0,2.04,1.39
+88.2,1.01,14.1,259.0,25.3,8.58,13.0,248.0,1.02,2.5,1.93
+3.55,1.06,25.3,17.8,13.7,3.08,18.8,157.0,1.0,217.0,1.15
+30.5,1.0,11.9,173.0,34.6,58.3,97.3,1731.0,1.0,110.0,2.48
+92.2,1.13,59.9,66.1,47.8,2.05,7.3,85.1,1.0,1.0,1.25
+160.0,1.21,18.8,24.4,3.79,15.7,18.1,352.0,1.0,1.0,1.07
+1.5,1.35,18.3,21.9,19.8,10.9,17.3,362.0,1.0,20.4,1.01
+26.4,1.0,24.1,13.9,12.1,10.7,31.3,956.0,1.0,48.7,1.0
+2.76,1.35,15.0,107.0,30.8,8.9,15.1,331.0,1.0,1.0,1.0
+22.1,1.42,19.8,109.0,20.5,9.22,13.6,286.0,1.0,1.01,1.2
+41.8,1.01,26.9,62.1,13.6,3.72,6.61,313.0,1.0,8.9,1.04
+32.2,1.01,47.4,115.0,57.3,9.39,12.6,422.0,4.07,3.52,1.55
+34.0,1.0,7.37,16.1,12.7,11.9,17.5,267.0,3.96,9.82,1.11
+25.5,1.42,82.0,77.0,39.2,20.7,16.1,269.0,7.64,85.8,2.07
+36.5,1.06,26.7,19.8,13.5,22.1,20.9,334.0,33.4,1433.0,3.89
+10.6,2.44,27.1,58.8,19.5,24.1,23.5,322.0,9.82,19.3,4.57
+67.9,1.01,8.51,149.0,47.0,41.8,40.7,334.0,1.24,36.2,3.59
+39.6,1.01,23.7,20.4,5.52,86.6,108.0,1811.0,1.0,1.18,1.0
+37.9,2.27,32.5,319.0,59.9,59.4,72.3,1018.0,1.0,1.91,1.01
+24.4,1.1,24.8,22.7,15.5,15.5,15.4,325.0,1.0,1.0,2.35
+35.2,1.12,17.3,241.0,46.6,9.73,19.6,331.0,1.0,1.64,1.0
+31.1,1.61,23.9,26.4,9.14,6.44,15.7,453.0,1.12,71.0,1.06
+39.2,1.0,28.4,22.3,3.43,10.0,14.5,255.0,2.37,34.6,1.1
+2.74,1.01,22.9,21.3,11.1,1.73,15.1,322.0,1.0,2.48,1.79
+33.7,1.37,9.56,204.0,31.3,7.77,14.9,403.0,1.0,12.6,2.48
+47.4,1.01,23.7,24.1,11.8,16.1,18.9,343.0,1.0,18.6,16.4
+34.6,1.33,79.1,178.0,50.5,4.61,16.8,644.0,1.0,349.0,1.0
+38.9,1.5,20.4,25.7,17.8,15.0,16.8,375.0,12.7,237.0,12.6
+64.4,1.0,25.7,123.0,31.9,10.6,19.1,316.0,1.0,1.0,1.0
+32.5,6.32,38.2,21.7,3.72,41.0,48.7,649.0,1.0,6.73,1.27
+34.0,1.0,23.7,32.5,21.3,3.65,25.9,300.0,1.0,5.57,1.42
+22.3,1.04,5.94,9.14,7.57,24.6,25.7,414.0,1.08,1.0,1.89
+129.0,1.01,37.5,34.0,35.9,21.1,28.9,274.0,2.02,8.35,1.35
+21.3,3.08,17.9,151.0,31.9,16.4,19.3,362.0,2.29,25.5,6.92
+42.6,1.0,18.8,181.0,30.8,22.7,28.6,311.0,1.0,1.49,1.0
+71.0,2.37,20.4,28.1,8.06,106.0,103.0,313.0,1.0,1.01,1.61
+8.06,1.84,61.0,547.0,157.0,5.33,16.3,289.0,1.0,5.19,1.0
+17.9,1.45,28.4,17.3,12.2,22.9,30.5,422.0,1.0,2.71,1.01
+101.0,1.01,22.9,20.0,11.7,107.0,125.0,2458.0,1.0,1.0,1.0
+35.2,1.0,17.8,26.4,7.77,7.91,18.8,389.0,1.76,43.3,4.14
+18.1,1.13,10.9,244.0,27.4,30.5,33.1,286.0,1.0,1.0,1.5
+35.2,1.47,84.3,196.0,43.7,15.3,23.9,340.0,1.0,121.0,1.76
+37.5,1.38,16.5,28.1,11.4,4.07,18.3,403.0,1.0,50.9,2.17
+106.0,1.0,24.1,26.2,24.1,6.73,16.1,355.0,1.0,80.6,1.0
+29.7,1.89,27.1,30.5,20.5,4.49,20.2,407.0,1.0,1.01,1.0
+24.6,1.78,72.3,449.0,141.0,15.0,13.9,289.0,1.0,2.04,1.93
+33.1,1.0,25.0,27.6,21.5,13.3,16.7,269.0,1.0,1.83,2.76
+48.7,1.0,48.3,97.3,24.4,8.66,12.6,289.0,1.0,5.88,1.64
+36.8,1.01,15.4,15.5,4.29,30.8,39.2,757.0,1.0,195.0,3.05
+250.0,1.01,20.0,44.5,17.9,27.6,39.6,626.0,1.84,1.0,1.32
+95.6,1.0,10.5,22.5,23.5,4.7,11.4,445.0,1.86,31.3,2.37
+55.2,1.01,11.4,215.0,47.0,16.8,18.8,375.0,1.0,1.0,2.09
+11.2,3.05,26.7,26.4,13.0,8.66,11.7,453.0,1.0,4.18,1.0
+7.17,1.01,2.76,15.5,4.57,7.23,16.8,355.0,1.0,1.01,1.46
+38.5,1.0,35.5,60.4,44.1,7.84,7.3,286.0,1.0,4.53,2.13
+24.6,1.3,41.8,215.0,91.4,34.9,34.6,284.0,1.0,12.2,1.72
+53.8,1.0,23.7,101.0,22.1,3.02,15.3,352.0,1.0,2.09,1.0
+83.5,1.01,30.8,23.1,15.0,71.7,73.0,947.0,1.0,17.2,1.76
+118.0,2.46,36.5,66.1,8.66,7.5,50.9,704.0,1.0,1208.0,1.76
+43.3,1.09,17.0,17.6,1.0,4.07,46.6,135.0,1.0,1.0,2.44
+34.9,1.02,21.7,12.3,7.5,29.7,35.2,294.0,1.0,1.36,1.32
+37.9,1.0,9.56,229.0,29.2,131.0,123.0,843.0,1.0,286.0,2.53
+33.1,1.01,28.6,343.0,84.3,6.26,7.64,300.0,1.0,129.0,1.45
+25.5,1.01,40.3,392.0,115.0,18.9,25.3,359.0,1.0,14.7,1.0
+31.6,1.02,9.73,13.3,11.4,58.8,64.4,890.0,1.0,25.3,1.08
+32.8,1.7,17.9,130.0,37.5,23.1,21.9,308.0,1.0,1.0,3.43
+26.7,2.23,9.82,118.0,21.1,4.57,10.7,667.0,3.13,322.0,7.1
+44.9,1.0,9.14,147.0,28.6,28.1,32.2,316.0,7.17,392.0,10.3
+79.9,20.5,36.5,18.9,13.9,16.7,19.3,343.0,1.0,1999.0,2.0
+35.2,1.03,22.7,26.9,10.4,7.7,13.7,281.0,11.9,1.41,1.0
+9.73,1.01,15.5,26.9,9.82,9.14,14.3,292.0,1.0,1.0,1.0
+36.5,2.25,17.0,27.6,8.9,91.4,120.0,1358.0,1.0,6.26,2.92
+14.5,1.95,22.1,106.0,22.7,69.2,74.3,1407.0,1.0,6.1,2.05
+181.0,1.01,25.9,22.7,23.7,20.5,38.2,621.0,1.0,1.0,2.31
+21.1,1.37,16.4,161.0,16.4,4.66,10.4,379.0,1.0,107.0,1.58
+217.0,1.27,25.3,18.9,15.7,77.0,95.6,1286.0,1.0,2.09,1.0
+44.5,1.1,18.4,21.5,1.17,31.6,28.6,858.0,1.0,108.0,2.31
+29.7,1.26,17.9,137.0,42.6,23.3,41.8,626.0,1.0,1.0,1.0
+111.0,1.26,33.7,29.4,14.6,3.34,12.0,213.0,1.0,7.5,4.7
+45.7,1.0,29.2,150.0,36.8,65.5,93.1,1999.0,1.0,4.37,1.95
+15.4,1.95,20.5,235.0,25.0,17.0,27.1,403.0,1.0,10.6,1.5
+39.2,1.0,22.9,15.4,6.61,23.5,21.7,325.0,1.91,1.01,1.0
+36.5,3.52,25.0,69.8,8.35,13.2,25.0,328.0,1.12,289.0,1.41
+36.2,1.01,17.6,21.3,20.0,10.2,14.5,286.0,2.09,165.0,1.0
+62.6,3.08,9.82,155.0,40.3,23.3,30.2,457.0,1.7,8.9,1.76
+132.0,7.43,16.8,173.0,48.7,6.73,9.73,337.0,1.0,4.41,2.48
+12.6,6.04,17.3,35.9,29.4,82.0,105.0,1685.0,1.0,2.59,2.39
+223.0,1.01,16.1,213.0,33.7,17.9,23.5,331.0,15.7,26.4,3.96
+38.9,1.21,27.6,44.1,13.3,14.9,28.1,372.0,2.46,105.0,3.72
+45.7,2.09,13.9,89.0,24.8,77.0,79.9,1084.0,1.22,1.0,1.0
+23.7,1.0,26.7,29.7,6.98,1715.0,1715.0,1197.0,2.09,30.8,2.64
+41.4,1.0,24.6,14.7,16.0,6.04,12.3,246.0,2.48,1.25,1.79
+47.0,1.19,26.7,35.9,43.3,34.6,41.0,704.0,1.09,279.0,1.0
+22.9,1.22,30.0,13.3,15.5,18.3,25.7,379.0,1.0,1.01,1.47
+36.8,1.0,24.8,26.9,14.1,22.5,22.7,289.0,1.38,478.0,12.3
+44.1,1.0,8.28,10.7,12.1,12.3,21.7,355.0,1.0,1.76,1.25
+42.2,1.0,18.8,24.1,19.1,7.91,10.6,368.0,1.0,1.0,1.6
+24.1,2.62,34.9,141.0,36.5,45.7,51.4,799.0,1.0,12.5,1.83
+101.0,1.73,27.6,40.7,10.8,7.99,11.8,325.0,1.0,18.4,1.42
+29.4,1.01,16.1,164.0,15.3,59.4,75.7,1124.0,9.65,1.0,1.2
+12.7,1.46,26.7,34.3,19.6,13.9,11.4,284.0,3.43,9.06,2.35
+32.2,1.01,26.4,21.1,20.4,21.5,21.9,359.0,1.0,28.9,1.0
+125.0,7.17,33.1,57.3,24.8,105.0,106.0,1334.0,1.0,1.0,1.84
+68.5,25.0,21.9,153.0,28.6,97.3,136.0,2148.0,1.0,1.45,1.64
+26.9,1.0,20.7,91.4,37.2,4.18,19.3,562.0,1.0,164.0,1.89
+29.4,1.83,27.1,19.5,38.9,20.7,18.3,219.0,1.0,30.2,1.83
+28.1,1.63,45.3,37.2,32.8,18.6,20.5,343.0,1.0,1.3,1.39
+35.9,1.19,28.1,34.0,18.9,10.6,13.2,237.0,1.0,1.01,1.27
+26.9,2.0,16.0,59.9,16.7,67.3,76.4,1843.0,3.92,16.7,25.5
+37.9,1.15,21.3,10.7,16.5,18.8,27.6,286.0,4.49,1.0,2.79
+36.2,1.0,23.5,26.2,6.38,63.8,95.6,1568.0,1.0,75.7,1.0
+36.5,1.98,20.7,146.0,35.5,21.3,24.8,308.0,9.56,7.99,4.37
+20.0,1.01,19.1,18.4,2.59,15.7,20.7,349.0,1.0,1.0,1.25
+21.9,1.0,19.3,139.0,24.1,14.3,23.9,835.0,1.06,28.1,1.83
+67.9,1.0,17.8,130.0,25.0,7.37,15.3,311.0,1.31,10.0,1.0
+28.9,1.32,28.1,297.0,38.9,4.07,10.0,426.0,1.0,1.0,1.01
+16.3,36.8,30.2,35.2,9.82,20.7,37.5,1134.0,1.0,1.0,1.81
+61.5,1.01,20.5,17.5,8.28,47.4,51.9,1144.0,17.5,2267.0,15.5
+19.5,2.92,28.9,151.0,42.2,3.52,23.1,426.0,1.0,12.0,1.45
+215.0,8.9,19.5,96.5,21.7,49.6,56.2,1134.0,1.15,2.17,1.55
+28.9,2.94,25.3,22.9,17.9,95.6,105.0,1981.0,4.1,1.0,3.92
+50.5,1.0,27.6,31.6,23.9,83.5,99.1,1382.0,43.3,379.0,14.5
+46.6,1.57,4.37,1.49,382.0,20.5,38.5,483.0,1.0,1.0,1.01
+8.06,1.0,15.1,164.0,32.5,6.49,11.9,204.0,1.0,1.01,1.3
+24.6,1.11,6.73,14.5,29.7,7.3,18.1,313.0,1.0,1.03,1.3
+27.9,1.61,4.66,7.84,17.3,2.57,9.31,737.0,2.94,340.0,5.67
+40.0,1.01,16.3,136.0,11.4,18.1,21.9,334.0,10.1,1611.0,17.0
+189.0,15.4,14.2,331.0,50.9,4.87,17.2,346.0,12.0,135.0,12.2
+26.7,1.0,11.5,179.0,46.1,2.46,7.64,257.0,1.0,122.0,1.0
+1.0,1.45,10.1,14.6,13.2,13.6,10.4,279.0,1.0,11.7,1.31
+56.2,1.0,28.1,97.3,38.9,19.6,18.4,257.0,1.0,1.0,2.53
+64.4,3.13,44.9,147.0,35.2,4.83,1.08,101.0,1.0,1.0,1.47
+75.0,1.01,25.7,48.3,15.8,15.3,22.3,355.0,1.0,1.01,1.2
+129.0,1.68,41.0,39.6,13.3,6.15,18.8,461.0,8.58,219.0,6.79
+5.28,1.01,4.37,10.3,13.9,4.18,23.1,621.0,1.0,1.0,1.95
+25.7,2.09,48.3,85.1,34.3,11.3,13.8,255.0,1.0,1.67,1.0
+49.6,1.01,30.2,47.4,19.8,18.3,16.5,331.0,1.0,1.01,1.13
+42.6,2.25,67.9,505.0,149.0,18.4,28.9,334.0,1.0,9.39,1.26
+20.5,2.59,16.5,89.8,23.1,37.2,39.2,328.0,1.0,1.0,1.95
+37.2,2.62,8.58,17.9,13.7,63.8,75.7,1208.0,1.0,102.0,1.24
+33.1,1.0,5.88,149.0,27.6,10.7,22.3,573.0,17.2,91.4,7.17
+22.5,1.72,20.5,112.0,31.1,3.22,7.1,346.0,1.0,1.0,2.92
+49.1,1.0,23.5,95.6,26.9,15.5,28.1,269.0,1.0,1.0,1.17
+34.0,3.55,22.9,30.5,8.51,85.1,103.0,1715.0,1.0,3.55,1.21
+49.6,1.09,27.6,21.9,7.84,10.6,15.4,204.0,1.0,1.45,1.0
+77.7,2.0,10.7,331.0,45.7,15.5,20.0,276.0,1.0,1.0,1.81
+31.6,2.89,25.3,92.2,22.9,5.67,8.74,264.0,14.5,264.0,1.12
+47.8,1.95,14.3,94.7,26.4,29.7,30.2,389.0,1.0,15.5,1.72
+31.6,2.69,21.7,16.7,2.05,4.41,26.9,389.0,1.0,233.0,1.47
+41.0,1.7,26.7,18.3,10.6,36.8,33.4,264.0,1.0,5.83,1.33
+16.7,2.39,30.5,34.3,40.7,13.9,13.9,308.0,1.0,1.0,1.0
+16.8,2.37,18.3,217.0,64.9,5.05,14.2,542.0,1.0,1.0,1.03
+104.0,1.0,18.4,56.2,10.4,10.1,13.9,262.0,1.0,1.0,2.37
+29.2,2.09,30.5,58.8,46.6,42.2,48.3,851.0,9.39,193.0,1.08
+40.3,1.22,16.0,164.0,30.8,23.3,32.5,483.0,1.73,1.0,2.02
+41.0,1.0,11.5,122.0,31.6,35.2,31.1,392.0,2.31,319.0,1.32
+54.2,1.0,12.2,108.0,36.8,81.3,118.0,1928.0,3.72,26.4,1.0
+26.4,1.01,12.7,101.0,25.9,21.9,30.5,392.0,13.3,2996.0,18.9
+34.9,2.15,15.0,23.3,3.55,56.2,73.7,1037.0,1.0,3.79,1.63
+34.0,2.29,12.0,25.9,8.43,53.8,85.1,1346.0,1.0,3.19,2.19
+25.9,1.65,26.9,161.0,26.2,11.7,28.6,764.0,1.0,1.0,1.17
+75.0,1.0,17.9,204.0,46.6,6.21,10.7,297.0,1.0,9.91,1.0
+4.14,1.32,18.4,18.6,15.0,7.5,9.39,334.0,1.75,1.0,1.55
+117.0,6.92,21.9,23.3,12.5,80.6,110.0,1999.0,1.0,1.18,1.58
+35.9,2.81,15.4,138.0,42.6,15.7,20.0,319.0,1.15,1.0,3.13
+89.8,2.23,16.8,173.0,23.9,11.0,13.6,253.0,1.0,157.0,1.43
+13.9,2.48,66.1,264.0,95.6,8.98,11.9,362.0,1.83,14.3,1.37
+44.9,1.31,31.1,55.7,31.9,8.58,13.5,500.0,2.46,4.83,1.15
+24.4,4.22,13.8,77.0,40.7,24.6,24.8,372.0,1.0,147.0,1.41
+9.39,4.0,23.3,30.5,25.3,17.9,22.5,279.0,1.0,1.0,1.65
+26.2,3.19,26.9,30.8,31.6,12.6,14.2,286.0,1.0,10.0,1.0
+33.1,1.88,10.5,244.0,22.3,9.65,13.6,407.0,4.49,382.0,8.9
+52.3,5.99,15.4,1.61,16.7,12.4,14.7,233.0,1.0,64.9,1.63
+1.18,1.57,22.5,143.0,47.8,17.8,23.1,257.0,2.81,80.6,1.0
+191.0,13.9,32.2,45.3,13.9,9.56,18.1,346.0,1.0,3.72,1.19
+1.0,2.48,18.9,60.4,17.0,1.91,1.0,56.7,1.0,11.5,1.15
+35.2,2.07,21.7,84.3,20.2,12.1,38.2,1928.0,1.0,6.73,1.7
+77.0,1.05,24.4,15.3,1.22,18.8,31.1,352.0,1.0,153.0,4.7
+9.65,1.2,84.3,21.5,80.6,4.87,11.3,583.0,1.0,202.0,2.29
+44.9,2.57,87.4,599.0,168.0,33.4,44.1,1310.0,1.0,4.49,1.13
+42.9,4.41,20.9,16.7,6.44,40.0,33.7,313.0,1.0,1.18,1.19
+57.8,1.51,11.1,229.0,37.2,8.9,16.0,313.0,1.0,1.0,1.0
+43.3,1.38,31.6,71.0,18.1,24.6,35.2,445.0,1.45,58.3,1.63
+46.1,1.0,17.8,136.0,31.1,10.1,9.73,433.0,1.0,104.0,1.65
+112.0,7.04,60.4,410.0,89.0,9.22,17.8,302.0,1.0,422.0,3.52
+58.3,1.58,24.8,61.0,18.4,196.0,284.0,4573.0,1.0,3.49,1.53
+23.7,3.34,28.9,29.4,10.9,42.2,48.3,649.0,1.0,10.5,1.76
+18.1,1.0,23.1,12.6,7.43,21.3,23.5,279.0,1.0,17.9,8.66
+30.5,1.01,16.8,40.3,25.0,14.1,24.6,274.0,2.79,21.7,1.36
+25.5,3.16,26.7,83.5,29.2,23.5,27.1,274.0,1.0,136.0,7.3
+31.1,1.3,3.59,22.9,35.5,20.0,19.6,359.0,1.0,1.0,1.38
+25.3,2.25,14.7,198.0,23.5,75.0,90.6,1186.0,1.0,1.0,1.57
+33.1,2.46,29.4,24.8,4.96,12.5,17.9,300.0,1.0,10.5,1.32
+38.9,1.0,25.9,115.0,30.5,15.4,36.5,583.0,1.0,1.0,1.81
+66.7,8.06,21.9,6.1,9.82,66.7,82.0,1009.0,1.54,90.6,1.98
+44.5,5.78,14.7,108.0,30.2,5.05,11.3,281.0,1.0,308.0,1.65
+56.7,1.86,4.22,6.21,20.0,4.1,26.2,437.0,1.0,6.98,1.0
+40.0,1.88,20.9,13.3,19.5,17.5,23.9,346.0,1.0,2.27,1.19
+26.9,2.64,12.5,178.0,29.4,5.83,6.92,281.0,1.0,1.07,1.0
+16.4,9.65,25.7,37.9,14.6,24.1,25.7,355.0,1.0,1.01,1.0
+139.0,6.92,15.4,115.0,16.1,7.7,17.8,474.0,2.37,9.56,1.13
+35.9,5.83,25.7,28.6,12.7,28.4,30.8,334.0,1.0,1.0,4.49
+50.5,1.01,19.3,13.7,16.4,19.6,20.7,281.0,1.0,1.0,1.0
+31.6,1.7,21.9,26.2,16.4,26.4,32.8,279.0,1.0,4.91,1.64
+51.9,1.03,89.8,542.0,150.0,18.8,25.0,281.0,3.75,1.11,1.5
+39.2,1.55,19.8,155.0,15.8,14.1,18.6,316.0,1.0,1.0,2.0
+54.7,1.01,18.6,250.0,38.2,22.1,20.5,325.0,1.0,1322.0,47.4
+46.6,1.01,20.0,17.5,19.1,8.35,19.8,311.0,1.0,1.75,1.0
+21.9,3.62,8.9,389.0,72.3,9.73,13.5,368.0,1.0,7.91,1.22
+33.7,1.46,17.9,23.9,17.9,7.43,13.1,346.0,1.58,1.26,1.7
+4.1,1.0,20.2,19.8,12.3,41.8,76.4,1055.0,1.0,3.52,1.76
+38.9,1.6,27.4,18.1,2.05,16.7,18.9,368.0,8.2,300.0,1.11
+31.1,2.5,20.5,160.0,21.3,15.4,24.6,244.0,2.81,302.0,8.58
+56.2,15.1,13.8,143.0,23.5,5.88,12.0,253.0,1.0,13.7,1.0
+58.3,1.0,9.91,19.5,24.1,22.7,32.2,264.0,3.59,2.81,1.43
+37.9,1.01,29.4,22.9,19.8,36.8,53.3,1186.0,1.0,11.8,1.96
+29.2,3.25,14.7,126.0,11.5,12.5,15.1,337.0,1.0,4.41,2.13
+26.2,1.72,62.1,457.0,121.0,2.64,18.4,157.0,1.0,1.01,1.68
+25.5,2.31,12.7,64.4,23.1,7.84,6.79,300.0,1.0,1.5,1.72
+34.3,1.17,13.2,165.0,25.5,19.6,23.1,292.0,1.0,1.0,2.29
+1.0,1.32,14.5,17.3,18.1,1.38,1.0,117.0,17.2,1811.0,6.73
+29.4,2.69,8.98,109.0,43.3,8.2,16.4,233.0,1.05,6098.0,25.9
+79.9,27.4,10.9,193.0,42.9,24.8,34.3,407.0,1.0,2.0,1.0
+50.0,1.58,11.4,131.0,22.5,22.7,29.2,723.0,1.0,1.38,1.0
+30.5,2.41,20.7,54.7,22.5,10.4,13.7,308.0,1.0,1.22,1.89
+25.0,5.57,21.7,35.2,23.5,34.9,38.5,410.0,3.72,1.0,1.58
+28.6,2.86,23.5,28.4,11.5,32.5,36.8,337.0,4.91,16.4,7.1
+36.8,1.0,20.5,26.9,15.5,12.6,16.1,496.0,1.0,25.5,1.0
+21.7,1.67,43.7,60.4,40.3,29.2,39.6,400.0,1.5,10.4,1.49
+138.0,1.0,16.4,204.0,27.1,10.2,28.4,396.0,1.0,4.57,1.43
+77.7,1.2,12.1,131.0,23.3,71.7,115.0,1670.0,1.0,1.0,1.15
+14.6,1.37,14.3,302.0,37.9,76.4,123.0,1275.0,1.0,13.6,1.63
+27.6,1.41,18.8,117.0,40.3,5.73,10.2,578.0,28.9,10.2,1.65
+36.8,1.93,37.9,29.4,26.7,15.8,22.3,331.0,1.0,3.37,1.0
+35.5,2.27,22.7,16.8,4.1,53.3,69.2,717.0,1.61,19.8,1.0
+2.23,2.71,10.2,40.7,50.0,21.9,29.2,403.0,25.7,505.0,9.22
+29.4,10.1,31.1,32.2,8.35,82.8,95.6,1582.0,8.28,3.43,1.0
+130.0,47.0,9.31,157.0,31.9,33.4,54.2,685.0,1.0,8.06,1.01
+2.86,1.0,21.9,319.0,59.4,11.4,17.6,375.0,1.0,18.3,1.24
+50.0,6.26,10.4,117.0,34.6,12.4,15.4,207.0,2.97,167.0,3.02
+38.9,1.01,31.1,27.1,26.7,4.7,31.3,331.0,1.0,1.0,1.12
+10.1,1.04,9.56,219.0,53.8,14.1,19.6,433.0,1.47,1.0,1.75
+11.1,1.65,25.0,14.6,1.49,76.4,83.5,1407.0,1.0,1.41,2.0
+66.1,1.01,9.47,19.6,33.7,15.7,16.5,235.0,1.58,6.38,1.49
+52.8,25.3,32.8,21.9,9.22,15.8,20.0,346.0,1.06,1.0,2.05
+28.1,1.38,51.4,322.0,120.0,6.98,17.0,355.0,1.0,221.0,2.19
+94.7,5.38,22.7,21.9,4.66,5.83,7.99,248.0,1.0,1.0,1.0
+36.5,1.55,31.3,29.2,17.5,14.9,13.7,262.0,1.0,1.0,1.37
+44.5,4.7,30.8,91.4,22.7,2.02,5.94,692.0,9.47,1582.0,4.1
+46.6,1.01,19.6,14.3,1.78,11.0,16.3,246.0,19.6,973.0,14.9
+16.7,4.37,14.9,178.0,40.3,10.2,10.7,368.0,1.0,1.01,1.83
+43.7,2.39,38.2,382.0,131.0,15.4,20.7,292.0,1.0,11.8,3.65
+46.6,1.38,12.7,21.1,24.8,16.7,25.9,297.0,1.6,3.59,1.83
+28.4,2.23,20.5,136.0,38.5,13.2,20.2,382.0,14.5,5.33,1.01
+58.3,1.01,16.8,16.7,13.3,13.2,12.5,271.0,3.52,2.44,1.29
+35.5,1.01,35.5,200.0,65.5,13.3,9.31,319.0,1.0,7.57,1.0
+4.1,6.98,15.1,14.2,7.64,8.82,12.4,308.0,1.0,10.9,1.39
+40.3,1.25,16.5,37.5,17.3,10.1,17.5,175.0,1.0,1.38,3.22
+50.5,2.37,10.6,269.0,33.4,12.5,8.98,281.0,1.0,4.22,1.21
+38.5,1.01,17.5,167.0,28.9,60.4,62.1,965.0,1.81,1.0,1.7
+2.53,1.0,20.0,98.2,22.7,23.3,31.3,311.0,1.36,1.19,1.32
+10.9,4.96,14.3,16.1,20.7,11.3,17.6,284.0,2.92,1.0,2.92
+61.5,1.78,132.0,241.0,136.0,15.1,18.6,276.0,1.49,2247.0,2.15
+38.5,2.07,19.6,80.6,23.1,15.3,21.7,292.0,1.0,500.0,4.49
+50.9,2.15,29.2,21.7,38.9,18.6,25.9,407.0,1.45,111.0,11.9
+113.0,1.01,20.7,23.9,16.3,9.31,15.1,289.0,1.0,61.0,1.0
+50.0,1.01,10.9,8.82,18.9,29.7,32.5,292.0,1.0,13.3,1.38
+36.2,1.01,20.0,28.6,8.9,5.09,15.3,449.0,1.05,5.62,4.49
+44.1,3.52,15.7,115.0,35.9,5.0,12.6,704.0,7.84,12.7,2.76
+5.38,4.1,49.6,414.0,73.0,12.5,17.3,284.0,2.81,1.01,1.33
+47.8,1.01,15.5,123.0,36.8,11.5,17.0,319.0,1.0,1.01,1.11
+49.6,1.89,30.0,24.8,5.14,14.1,16.0,241.0,1.0,1.0,2.5
+168.0,1.0,23.7,27.1,17.5,2.94,15.4,604.0,1.0,48.3,1.0
+30.5,1.76,33.7,35.2,33.7,12.0,67.3,2350.0,1.0,1.0,2.25
+38.2,1.11,11.0,227.0,37.9,4.26,36.5,77.0,1.0,1.0,1.63
+4.83,1.35,29.2,10.4,4.49,4.33,9.39,331.0,1.0,100.0,1.08
+26.9,1.36,20.2,105.0,36.2,2.19,8.28,851.0,1.0,1.53,1.01
+64.4,1.01,6.49,168.0,37.5,14.1,20.5,244.0,1.0,13.0,1.1
+27.1,3.25,14.6,13.0,10.7,29.2,32.8,396.0,10.3,1.72,1.05
+23.1,1.72,21.9,136.0,53.8,9.47,13.5,359.0,1.0,102.0,1.15
+30.0,4.96,22.9,22.9,11.2,5.14,24.8,533.0,1.0,4.37,1.07
+38.2,1.01,28.4,15.7,17.0,3.72,34.9,59.9,1.0,1.0,1.3
+42.9,1.0,38.9,18.6,30.2,8.13,11.7,286.0,1.0,1.01,1.0
+105.0,1.01,17.9,217.0,57.3,33.7,42.9,632.0,1.0,138.0,1.79
+35.5,1.81,14.1,184.0,24.1,17.3,31.1,396.0,1.0,1.0,1.01
+5.42,1.0,23.9,14.1,16.4,15.8,16.4,294.0,1.0,1.0,1.0
+53.8,14.3,4.26,5.0,4.26,20.4,22.7,337.0,1.0,1.0,1.0
+26.9,1.01,22.1,6.32,18.4,2.67,9.91,184.0,1.0,1.0,1.21
+13.2,1.31,23.7,78.4,33.7,25.5,33.1,241.0,2.15,523.0,2.59
+63.2,4.0,19.3,22.5,6.1,17.6,28.9,931.0,1.0,136.0,1.93
+35.2,1.84,14.1,3.46,14.6,2.46,6.79,478.0,1.26,1.13,1.11
+3.22,1.46,22.7,22.1,11.4,50.9,71.0,874.0,1.0,1.0,1.01
+34.3,1.76,6.67,18.8,14.3,27.9,43.7,552.0,1.0,8.06,1.01
+35.2,2.55,26.7,16.0,5.14,6.44,1.2,142.0,6.55,6.21,1.25
+24.1,2.35,36.5,46.6,37.5,29.2,37.2,851.0,8.2,276.0,1.25
+47.4,1.67,66.7,311.0,100.0,3.92,16.8,505.0,1.0,43.3,1.0
+46.1,2.97,20.5,21.9,1.0,11.5,20.4,583.0,1.09,7.99,1.0
+35.2,4.57,10.6,188.0,32.8,42.6,53.3,626.0,1.0,1.0,1.79
+47.4,3.43,22.9,111.0,30.8,54.2,72.3,1219.0,1.0,4.7,1.54
+100.0,1.21,12.4,155.0,43.3,10.4,16.3,269.0,1.0,25.9,1.58
+30.0,3.68,16.0,12.9,18.4,19.6,20.7,382.0,1.81,1.72,3.59
+49.6,9.39,16.7,217.0,31.3,18.3,26.9,279.0,2.09,1.39,3.05
+56.7,2.17,2.5,12.0,22.7,10.9,22.7,890.0,2.92,30.2,2.05
+45.3,3.68,7.23,111.0,21.9,7.57,62.6,557.0,1.78,1.0,1.42
+38.9,2.31,41.0,410.0,80.6,20.4,25.9,302.0,12.6,302.0,6.1
+38.9,2.62,13.8,204.0,41.4,26.7,34.0,692.0,2.04,22.1,4.1
+33.7,4.7,49.1,362.0,98.2,11.9,16.3,346.0,1.0,3.34,1.45
+1.39,1.6,20.5,18.3,1.65,33.7,35.5,441.0,1.0,1.36,1.6
+32.2,3.46,23.1,16.8,10.4,8.13,16.5,346.0,1.0,1.63,1.0
+42.9,4.57,25.5,12.9,8.06,31.1,38.9,882.0,1.0,1.0,1.43
+10.4,1.01,19.6,55.7,11.5,1.93,7.3,655.0,1.0,1.0,1.0
+21.9,2.53,23.9,20.5,1.0,22.3,21.1,279.0,1.02,2.92,1.32
+34.3,1.0,12.6,138.0,13.1,34.9,48.7,2148.0,1.0,77.0,1.0
+37.9,2.07,72.3,644.0,141.0,36.2,40.0,698.0,1.0,158.0,1.32
+32.5,4.29,21.7,161.0,32.2,63.8,89.0,1911.0,1.0,38.2,1.89
+108.0,1.0,11.1,127.0,26.4,14.6,20.7,286.0,1.0,45.7,1.15
+61.0,1.1,19.8,15.8,5.38,44.1,52.8,947.0,1.0,4.1,1.49
+31.1,1.06,63.8,77.7,38.9,40.3,42.9,302.0,1.0,14.9,1.25
+58.3,2.19,79.1,514.0,136.0,35.9,47.0,692.0,12.9,1018.0,1.57
+44.1,1.0,47.4,84.3,64.4,13.7,23.9,284.0,2.17,37.5,4.07
+30.0,3.28,15.7,47.0,40.7,19.8,17.3,274.0,1.0,17.9,1.54
+38.9,2.21,14.5,179.0,17.3,33.4,76.4,1094.0,1.0,1.0,1.53
+44.1,1.01,13.5,9.56,3.85,13.1,19.3,389.0,1.0,1.05,2.27
+44.5,1.05,7.17,23.5,4.66,13.8,16.4,319.0,1.0,6.79,1.58
+124.0,1.0,55.7,244.0,75.7,21.5,25.5,375.0,2.57,4.78,10.9
+36.5,1.01,20.9,32.5,16.0,77.0,103.0,2371.0,1.0,9.06,1.55
+111.0,1.01,91.4,259.0,97.3,31.3,31.1,340.0,1.0,142.0,1.54
+34.0,6.55,2.64,10.3,8.2,9.91,16.4,400.0,1.3,4.83,1.18
+32.5,3.65,14.5,157.0,20.5,22.5,27.9,365.0,1.0,1.0,1.0
+29.2,1.01,11.7,29.4,21.3,5.42,26.2,470.0,1.0,1.18,1.0
+15.3,7.91,16.8,130.0,20.0,10.7,16.0,271.0,1.0,250.0,4.14
+14.5,2.69,18.4,137.0,48.7,12.0,13.3,334.0,1.0,85.1,10.6
+82.0,1.35,14.9,137.0,35.5,14.9,17.8,334.0,1.0,3.59,1.0
+85.1,3.4,11.4,213.0,20.4,5.78,10.0,396.0,1.0,2.84,1.0
+14.1,1.0,22.1,79.1,13.3,7.91,10.0,368.0,2.05,1843.0,1.09
+39.2,1.65,20.9,155.0,49.6,27.6,36.2,385.0,4.91,9.56,7.57
+131.0,5.99,18.3,16.8,7.04,12.0,12.2,276.0,4.87,227.0,2.46
+23.3,1.04,15.7,205.0,49.6,12.2,18.1,334.0,1.0,1.0,1.0
+32.8,1.0,22.9,31.9,20.0,28.4,43.7,737.0,1.0,1.0,1.17
+40.0,6.26,15.5,106.0,9.91,19.6,28.6,385.0,1.0,1.01,1.0
+39.2,3.62,22.3,26.7,21.5,7.04,25.0,437.0,1.0,10.3,1.15
+29.2,1.29,21.7,23.3,15.1,4.29,6.21,426.0,1.84,1.0,3.72
+66.1,1.01,20.9,7.64,24.1,3.75,17.5,457.0,8.43,125.0,1.08
+58.3,1.0,14.2,129.0,38.5,19.8,26.4,331.0,1.0,147.0,2.84
+29.7,1.0,12.5,92.2,17.5,26.2,41.8,1144.0,4.18,41.8,1.61
+42.2,1.88,16.4,22.3,20.4,2.39,10.1,217.0,1.0,99.1,1.42
+36.5,1.04,24.1,6.44,28.9,15.7,17.3,300.0,1.0,1.0,1.68
+58.3,10.2,16.7,26.9,24.8,6.92,13.6,1065.0,7.37,400.0,5.88
+36.2,2.27,14.2,200.0,36.8,6.85,16.0,491.0,1.0,5.78,1.17
+50.0,1.06,25.5,27.4,3.68,10.2,13.0,292.0,2.33,12.3,1.53
+30.2,2.05,19.1,21.9,14.6,40.0,56.2,1134.0,1.0,5.88,1.79
+53.3,1.53,46.1,379.0,102.0,38.5,55.7,392.0,5.19,588.0,2.35
+46.1,2.44,39.6,362.0,66.1,4.07,8.58,233.0,5.28,2.35,1.1
+8.66,1.01,10.2,10.6,14.5,2.59,12.3,248.0,22.1,72.3,4.74
+31.1,2.86,25.9,17.3,12.0,16.7,18.1,349.0,23.1,692.0,10.7
+24.8,4.0,23.9,27.6,23.7,64.9,67.3,305.0,1.0,1.0,1.12
+54.2,1.0,1.5,23.9,16.1,34.9,41.8,355.0,12.5,483.0,1.06
+46.6,1.73,11.0,133.0,25.5,11.8,13.2,246.0,1.0,105.0,4.45
+30.8,1.0,20.9,196.0,38.9,57.8,62.6,743.0,1.0,1.0,1.6
+22.5,1.36,17.2,241.0,28.4,7.99,45.7,403.0,1.19,31.6,1.38
+124.0,4.91,27.4,219.0,67.9,52.3,71.7,1065.0,1.0,1.01,1.72
+49.1,1.0,16.3,175.0,24.8,106.0,121.0,1298.0,1.0,1155.0,1.64
+68.5,3.02,23.1,27.1,13.2,11.4,17.8,461.0,1.0,11.9,2.35
+59.4,1.01,9.31,281.0,30.0,23.7,25.3,349.0,1.0,1.01,1.25
+6.21,2.11,9.82,127.0,25.5,14.3,29.4,466.0,4.29,25.5,1.0
+35.2,3.16,21.9,38.5,51.4,3.62,16.7,259.0,1.0,1.0,1.27
+49.1,2.25,11.0,292.0,34.0,30.5,37.5,379.0,1.0,90.6,2.74
+44.9,3.08,27.6,2.27,41.0,8.06,10.5,382.0,1.0,1.0,1.0
+48.3,1.32,17.2,145.0,16.4,9.31,24.1,1219.0,1.0,1.0,1.0
+33.4,3.16,18.8,69.8,7.84,7.7,12.6,328.0,1.0,28.1,1.1
+47.0,2.0,47.0,56.7,48.7,8.51,14.2,368.0,1.0,15.0,1.89
+125.0,1.43,5.42,223.0,29.4,21.1,18.9,313.0,1.0,9.39,1.5
+47.0,1.3,47.4,115.0,22.1,8.28,12.1,300.0,1.64,1.84,1.42
+10.2,1.6,22.5,18.6,20.9,7.37,16.0,615.0,8.28,271.0,1.64
+34.9,3.02,30.8,24.1,20.4,18.8,19.5,239.0,39.2,28.4,7.99
+58.8,5.33,18.6,18.9,7.1,23.1,29.4,248.0,20.2,5.14,1.6
+40.7,2.23,19.3,27.4,15.3,8.28,6.49,221.0,1.0,82.0,2.46
+31.9,2.37,8.51,227.0,37.2,26.2,35.9,340.0,2.35,1.0,1.39
+45.3,1.0,28.4,14.9,4.1,20.7,23.7,281.0,1.0,221.0,3.55
+48.7,2.23,19.1,22.7,11.5,30.8,44.5,750.0,1.0,5.23,1.96
+30.0,1.21,55.2,449.0,117.0,9.06,11.4,400.0,1.0,1.0,1.03
+1.0,2.07,22.3,135.0,21.3,26.9,33.4,368.0,1.19,14.3,2.29
+34.6,1.64,13.2,133.0,30.8,6.61,9.39,514.0,1.0,1.0,1.19
+40.7,2.69,21.7,183.0,56.2,17.3,15.3,269.0,1.0,1.96,1.11
+43.7,4.07,34.6,31.6,11.4,4.96,6.15,257.0,1.0,6.61,2.02
+60.4,1.01,16.7,157.0,22.3,37.2,44.1,784.0,1.0,3.02,1.42
+36.5,3.85,14.9,127.0,20.0,25.7,31.6,334.0,1.0,3.02,1.3
+22.3,2.35,24.8,24.6,3.55,11.0,14.7,340.0,1.0,1.35,1.0
+39.2,1.01,16.7,8.9,2.35,61.0,67.3,1075.0,1.0,13.8,1.0
+8.28,1.0,12.3,117.0,8.06,7.5,18.8,599.0,1.0,1.0,1.0
+26.7,2.76,10.7,284.0,46.6,7.91,21.5,1114.0,2.07,28.4,1.7
+39.2,1.32,28.1,40.0,18.4,34.9,42.9,523.0,1.15,1.01,4.22
+57.3,7.57,10.8,100.0,20.7,9.65,13.1,286.0,1.0,30.5,1.98
+41.0,2.71,15.5,97.3,34.9,26.4,29.4,313.0,1.0,1.01,1.0
+12.0,7.57,20.0,18.9,10.9,20.5,32.5,368.0,1.0,1.0,1.38
+31.6,1.78,18.8,18.9,3.13,23.5,28.1,414.0,1.0,15.8,2.71
+33.4,2.39,7.5,205.0,35.2,92.2,106.0,1843.0,1.0,2.81,4.22
+40.7,4.07,20.0,15.5,7.17,13.0,17.3,297.0,1.0,1.61,1.21
+40.3,1.01,18.3,99.1,42.6,21.7,34.0,449.0,1.0,1.27,1.0
+31.3,2.44,17.9,57.8,11.7,8.51,14.7,328.0,1.0,108.0,2.15
+31.6,2.39,5.33,183.0,31.6,10.6,12.5,382.0,1.42,120.0,1.67
+35.5,1.58,16.3,90.6,18.8,12.5,37.5,743.0,1.0,1.02,1.0
+30.0,4.87,11.0,175.0,18.9,6.32,16.8,233.0,1.0,1.06,1.35
+24.8,2.86,10.0,20.4,17.5,13.8,12.0,352.0,1.0,1.41,1.01
+24.8,2.69,13.5,164.0,31.3,18.8,27.6,281.0,1.0,1.43,1.46
+85.8,22.9,28.4,28.9,18.4,11.5,13.5,239.0,1.0,1.13,1.0
+8.66,1.0,7.77,213.0,32.8,16.4,20.4,334.0,1.0,1.72,1.0
+78.4,2.89,26.9,33.4,7.5,17.9,22.3,359.0,1.11,1.79,1.42
+62.1,1.03,9.91,205.0,35.5,9.14,12.0,253.0,3.16,259.0,1.19
+42.2,7.64,35.5,372.0,77.0,30.0,28.9,349.0,5.52,2.71,1.27
+35.2,1.29,39.2,279.0,64.4,10.9,15.7,319.0,1.06,1.01,1.23
+13.8,1.0,21.9,16.4,13.7,52.8,61.0,1065.0,1.0,1.0,1.03
+7.64,1.27,12.7,139.0,38.5,8.82,9.91,300.0,1.0,1.0,1.37
+35.9,2.02,13.8,112.0,7.43,77.0,93.1,1582.0,1.0,1.01,1.23
+28.6,2.48,20.4,20.9,6.1,15.8,25.0,257.0,4.03,1.0,1.33
+60.4,9.82,34.3,50.9,32.5,22.3,21.7,269.0,1.0,157.0,1.67
+31.9,1.22,16.4,231.0,37.5,7.57,14.9,248.0,1.0,12.6,1.72
+23.7,2.11,15.0,120.0,25.9,40.0,45.7,737.0,1.0,1.83,1.11
+47.8,7.7,25.7,26.9,13.9,37.2,40.0,349.0,2.41,104.0,3.79
+58.3,10.4,28.6,25.7,14.2,29.7,27.6,237.0,24.1,2017.0,1.22
+53.8,1.01,5.42,15.8,62.6,8.66,11.1,300.0,1.0,1.07,1.6
+28.9,10.1,50.5,253.0,73.0,67.9,79.9,1526.0,1.0,3.08,1.01
+35.9,3.85,32.5,37.2,19.6,4.33,14.3,331.0,1.0,12.6,1.29
+85.1,1.0,18.3,17.0,6.73,49.1,61.5,806.0,8.28,294.0,2.29
+40.0,1.73,17.9,19.3,15.7,69.2,90.6,1731.0,1.61,13.8,1.53
+40.3,3.59,23.9,35.5,62.6,27.9,47.8,649.0,1.0,1.36,2.02
+40.0,3.72,17.5,123.0,28.4,12.6,14.7,233.0,1.0,59.9,2.74
+31.3,3.43,19.8,25.9,16.5,21.7,21.7,281.0,1.0,16.3,1.19
+26.2,2.19,11.9,188.0,35.5,61.0,87.4,1286.0,1.0,1.01,2.76
+48.7,1.58,21.9,21.9,14.2,5.0,12.6,346.0,1.0,4.49,13.1
+51.4,1.01,22.3,25.5,31.6,8.9,15.1,328.0,1.0,10.8,2.33
+62.6,1.08,18.4,12.7,13.0,74.3,85.1,1252.0,1.0,2.21,1.75
+44.5,1.01,20.0,12.7,13.6,2.67,10.0,372.0,1.0,2.37,7.7
+47.0,1.0,21.7,120.0,10.6,2.92,16.8,255.0,1.68,4.7,9.56
+28.6,2.39,11.0,168.0,18.4,29.4,38.9,407.0,1.0,1.01,1.55
+35.9,2.62,29.7,29.2,28.1,44.9,52.8,799.0,2.41,349.0,3.22
+22.7,2.17,9.73,284.0,14.1,12.2,20.7,359.0,1.33,17.9,1.2
+47.4,2.13,18.9,19.6,6.61,18.1,22.3,294.0,2.86,1.0,1.18
+41.0,1.83,25.0,18.8,21.7,50.5,55.2,673.0,2.21,3.02,1.0
+25.7,2.19,20.2,23.1,18.3,14.2,22.7,297.0,1.0,1.01,2.37
+33.4,2.94,16.5,93.9,20.7,52.8,59.9,1219.0,3.37,62.6,4.07
+1.02,2.13,33.7,163.0,55.7,6.55,12.6,626.0,1.31,25.5,1.09
+20.5,10.8,16.1,111.0,17.9,20.0,25.5,316.0,1.0,96.5,2.31
+39.2,1.01,17.3,137.0,25.3,7.77,15.3,274.0,3.79,101.0,2.09
+31.3,1.51,29.7,37.9,22.7,19.1,17.3,235.0,1.0,109.0,1.38
+51.9,1.01,30.0,35.2,29.7,35.9,48.3,649.0,1.0,28.4,1.72
+39.6,1.24,19.1,25.0,17.6,20.0,34.0,375.0,1.0,14.1,1.49
+47.0,1.64,23.5,9.31,5.33,64.9,68.5,947.0,1.0,2.97,1.37
+35.5,1.13,18.3,137.0,35.2,16.5,23.3,359.0,4.45,157.0,1.53
+67.3,21.9,8.9,205.0,34.9,28.6,34.9,276.0,3.11,95.6,3.37
+22.3,3.34,34.9,271.0,55.2,11.7,31.9,567.0,3.0,1.0,1.61
+139.0,4.66,30.8,54.7,84.3,59.9,69.2,1037.0,1.0,154.0,1.72
+41.8,2.59,30.5,17.6,19.6,2.67,10.2,1037.0,1.0,1.0,1.0
+5.09,1.31,18.1,117.0,20.0,7.3,8.9,352.0,1.0,19.1,1.45
+17.6,10.6,12.9,141.0,42.2,8.13,9.47,289.0,12.9,3.65,1.96
+38.2,3.68,18.4,82.8,18.8,17.3,72.3,2525.0,1.0,7.64,1.19
+36.8,1.47,15.1,82.0,34.0,2.44,6.85,255.0,1.04,1.0,3.19
+49.1,1.86,1.49,18.9,7.77,15.7,16.5,308.0,4.66,1.01,2.0
+58.8,1.81,12.7,231.0,35.2,9.31,13.7,302.0,63.2,2525.0,12.6
+44.5,1.0,23.9,48.7,5.05,8.66,25.5,552.0,1.47,9.06,4.53
+24.6,6.73,27.4,20.5,1.01,35.5,37.5,319.0,2.25,184.0,3.55
+6.44,1.95,16.8,24.1,23.3,9.47,18.4,2129.0,2.35,1.0,1.06
+31.9,1.54,15.1,143.0,7.04,11.9,17.3,328.0,2.07,1.0,1.06
+9.56,1.06,27.1,77.7,22.1,12.9,17.3,368.0,1.0,1.0,1.06
+1.95,1.06,21.5,36.5,18.6,23.9,25.9,407.0,1.0,1.0,1.21
+91.4,2.07,14.1,14.3,7.1,14.1,45.3,750.0,1.0,1.09,1.0
+57.3,2.15,18.4,62.1,27.4,9.82,9.31,279.0,1.0,3.49,1.0
+40.7,5.33,13.5,18.4,15.8,33.1,44.1,965.0,17.6,311.0,30.5
+153.0,1.84,25.7,19.6,16.3,12.4,21.3,334.0,2.33,27.9,2.25
+27.9,1.01,24.8,99.1,31.6,12.2,18.4,466.0,2.67,175.0,1.6
+43.7,1.0,12.6,17.0,25.0,35.9,50.5,791.0,1.0,186.0,1.37
+22.3,2.92,44.9,165.0,82.8,14.6,24.8,346.0,1.0,19.8,3.85
+37.9,2.81,13.6,179.0,16.1,7.5,54.2,604.0,1.0,1.0,2.71
+51.4,2.27,16.1,66.1,10.8,37.2,52.8,1134.0,1.57,82.0,3.68
+28.9,1.0,20.7,168.0,25.0,14.9,38.5,1114.0,1.0,14.3,1.88
+68.5,7.43,26.7,27.1,8.51,28.4,30.8,311.0,7.5,241.0,1.45
+51.4,4.57,12.1,29.2,16.1,18.6,30.5,382.0,1.0,196.0,3.16
+34.3,1.42,11.1,146.0,15.5,54.7,74.3,1731.0,4.91,483.0,1.51
+38.2,2.29,35.9,27.6,18.6,16.4,26.2,422.0,2.35,1.0,1.49
+27.6,1.23,18.9,239.0,29.4,88.2,110.0,2110.0,2.97,63.8,1.06
+25.7,2.57,19.6,16.4,3.82,8.51,21.1,1144.0,1.0,1.0,1.84
+44.5,1.86,47.0,302.0,118.0,11.1,17.3,300.0,1.0,50.5,1.6
+53.3,2.02,11.4,95.6,4.29,35.5,50.9,667.0,8.82,519.0,4.14
+24.8,1.15,33.4,274.0,72.3,10.6,22.3,311.0,1.0,1.64,5.0
+31.9,2.92,20.5,352.0,61.5,10.3,9.91,375.0,1.0,176.0,1.0
+28.6,1.42,19.3,8.2,8.9,39.6,54.7,692.0,1.0,10.3,1.47
+37.9,1.65,23.5,191.0,98.2,47.4,58.8,1275.0,1.0,9.82,1.01
+112.0,7.91,24.4,40.0,19.6,6.49,11.7,414.0,1.25,1.0,4.87
+135.0,1.0,4.57,337.0,45.3,53.8,56.7,1114.0,1.0,4.07,1.67
+54.7,2.94,37.5,264.0,54.2,10.0,12.3,297.0,1.27,806.0,2.89
+15.7,2.31,19.8,37.5,30.8,11.1,16.5,343.0,1.0,1.01,1.3
+15.0,1.01,43.3,69.2,49.6,12.6,16.4,241.0,8.2,231.0,1.47
+32.8,5.33,16.0,248.0,41.4,58.8,89.0,1009.0,1.49,1.0,1.18
+6.67,3.4,19.8,34.0,12.0,23.5,30.0,349.0,1.0,7.3,1.61
+38.2,4.18,16.5,16.0,22.9,10.9,15.5,292.0,1.75,1.0,1.49
+34.9,3.55,9.73,146.0,30.5,6.49,14.1,319.0,2.79,22.7,1.49
+30.8,1.01,22.9,76.4,28.4,4.74,10.1,704.0,2.39,31.3,1.0
+38.5,1.39,31.9,286.0,57.8,12.4,17.3,400.0,1.0,7.37,1.1
+31.6,1.01,15.8,142.0,48.7,12.0,16.1,292.0,1.0,1.0,1.39
+44.1,2.97,17.3,21.5,9.47,20.2,37.5,1165.0,1.0,3.72,1.0
+47.4,1.25,21.7,14.5,5.42,8.98,16.5,325.0,1.0,1.0,2.09
+33.1,1.0,11.5,414.0,50.5,15.0,25.7,340.0,1.0,10.6,2.11
+21.1,1.0,12.4,86.6,24.4,27.4,36.8,385.0,1.0,1.0,1.07
+26.4,4.18,8.9,294.0,43.3,6.04,21.7,478.0,1.0,215.0,1.04
+33.1,1.72,27.9,26.7,17.5,7.17,10.8,300.0,1.0,15.1,1.32
+43.7,3.11,42.2,41.0,47.0,8.51,13.5,316.0,1.0,1.01,2.37
+37.9,5.0,29.7,41.4,18.1,9.31,11.7,316.0,1.31,1.0,5.62
+18.3,1.01,20.0,25.3,4.74,71.0,87.4,1134.0,1.0,10.9,1.76
+43.7,1.31,60.4,221.0,31.9,6.44,10.6,311.0,1.0,3.43,2.19
+39.6,1.57,16.7,147.0,41.0,8.2,11.4,365.0,1.23,13.7,4.45
+53.8,1.09,20.2,18.3,32.8,6.98,14.5,294.0,1.0,1.0,2.19
+42.9,3.79,10.0,19.5,12.6,42.2,40.0,229.0,1.0,1.39,1.89
+36.5,1.31,18.4,183.0,29.4,53.3,88.2,1582.0,9.73,69.2,1.93
+37.2,1.0,12.9,235.0,16.7,10.6,15.3,437.0,1.0,9.22,1.0
+19.8,4.29,15.1,30.0,6.49,3.92,9.31,1009.0,2.31,4.49,1.05
+31.3,1.84,18.1,92.2,13.0,9.14,16.4,297.0,1.0,3.13,1.7
+33.4,2.94,43.3,308.0,85.8,7.43,11.9,281.0,13.2,276.0,2.15
+44.9,11.8,33.4,22.1,22.1,13.0,15.8,334.0,5.94,6.85,2.53
+26.7,1.01,22.3,50.0,13.2,18.9,18.6,352.0,1.0,70.4,1.26
+53.8,1.21,15.0,100.0,44.5,57.3,67.3,1843.0,3.43,6.79,1.06
+26.4,3.52,31.6,28.1,18.9,16.8,28.9,385.0,1.0,3.11,1.55
+53.8,1.91,28.6,22.7,9.91,16.8,16.5,313.0,1.0,1.0,1.41
+40.3,1.01,13.5,165.0,28.6,4.22,17.9,322.0,1.07,17.2,1.91
+9.65,1.75,18.9,25.7,1.57,53.8,54.7,343.0,1.0,1.91,1.04
+24.8,2.17,41.8,172.0,48.7,31.1,38.9,410.0,1.0,127.0,1.38
+34.9,1.0,27.6,69.2,31.1,25.3,35.2,355.0,1.0,3.79,1.38
+1.19,1.83,67.3,188.0,154.0,34.9,36.8,437.0,1.26,6.67,1.76
+17.9,6.79,23.9,23.3,15.3,27.4,43.7,1219.0,1.0,1.0,1.08
+40.0,1.27,5.57,189.0,24.8,11.2,16.5,396.0,1.0,12.2,2.39
+1.0,1.54,27.6,23.3,17.9,89.0,114.0,2329.0,1.0,1.0,1.38
+36.5,1.0,46.1,15.0,67.3,7.7,34.3,638.0,1.0,1.01,1.53
+35.2,1.0,26.2,40.3,19.5,21.5,19.3,340.0,6.1,68.5,14.7
+61.5,3.82,20.9,32.5,9.39,21.5,33.1,453.0,1.57,12.6,2.02
+49.6,1.0,27.1,18.3,12.1,14.5,18.8,259.0,9.14,615.0,3.08
+49.6,1.61,28.1,21.7,11.8,67.3,72.3,1046.0,1.0,269.0,3.13
+37.2,1.11,56.2,85.1,97.3,14.7,21.7,253.0,1.0,18.9,1.38
+32.2,1.18,15.3,16.8,19.3,7.7,13.2,305.0,1.0,2.23,1.0
+72.3,3.02,37.9,10.6,71.0,3.22,10.4,286.0,1.0,1.01,2.94
+16.0,5.83,17.8,66.1,44.9,13.7,16.7,308.0,1.0,1.01,1.01
+38.2,2.62,8.98,229.0,24.6,5.62,14.3,407.0,1.0,9.65,1.35
+89.8,1.18,31.1,54.7,10.0,10.4,10.1,319.0,1.65,255.0,1.54
+41.4,2.13,50.9,83.5,5.83,26.2,34.0,1027.0,1.0,2.92,1.27
+33.1,1.25,23.7,31.6,22.1,9.39,12.6,250.0,1.0,1.0,1.2
+34.6,1.39,9.06,109.0,32.5,12.4,10.6,322.0,1.0,2.07,2.02
+44.1,1.0,17.9,91.4,35.5,17.9,25.7,300.0,1.0,2.39,1.14
+34.6,6.55,27.4,16.5,1.01,7.3,18.3,313.0,19.6,4.45,11.7
+24.1,2.09,34.0,346.0,83.5,93.1,114.0,1241.0,8.58,1.0,1.07
+61.0,2.21,42.6,227.0,98.2,4.03,13.7,217.0,5.78,26.9,3.49
+42.2,1.76,18.1,63.8,15.5,6.79,12.5,346.0,1.0,5.67,1.12
+39.6,3.68,77.7,253.0,80.6,47.8,61.0,723.0,1.0,1.0,1.02
+48.7,11.0,18.6,248.0,48.3,10.7,15.1,235.0,1.0,1.0,1.11
+54.2,1.0,18.1,40.0,11.2,41.4,53.3,692.0,10.1,552.0,10.6
+27.4,1.01,16.3,119.0,26.9,5.67,10.5,445.0,5.52,113.0,1.86
+21.9,1.01,23.9,17.8,11.0,17.5,22.7,340.0,7.64,115.0,1.25
+40.0,2.64,25.5,101.0,15.0,8.74,13.2,257.0,1.0,186.0,1.0
+37.2,2.23,9.31,17.8,12.6,3.49,17.0,368.0,1.29,1.0,1.21
+47.8,3.72,2.27,17.2,42.9,17.9,21.7,410.0,1.0,1.35,4.03
+39.6,1.53,18.3,67.9,17.6,9.06,10.0,250.0,1.0,10.6,1.0
+3.55,1.0,19.1,1.57,6.38,12.4,15.1,297.0,1.0,1.0,1.86
+88.2,1.31,18.8,93.1,52.8,9.14,15.3,389.0,1.88,1.0,1.46
+19.8,3.52,27.1,43.7,8.66,15.8,83.5,1186.0,4.7,26.4,6.04
+18.9,3.52,17.3,188.0,42.2,14.5,18.1,365.0,1.0,1.0,1.03
+34.6,4.07,22.5,100.0,41.8,41.0,62.6,1134.0,1.0,2.55,1.0
+50.5,12.5,18.1,23.3,15.0,70.4,84.3,1611.0,8.9,63.2,14.2
+35.2,1.0,25.3,23.5,13.0,23.3,18.3,305.0,1.0,17.9,1.0
+27.1,1.11,27.4,35.9,14.1,20.4,22.3,297.0,1.0,15.4,1.49
+59.9,1.01,41.4,311.0,93.9,9.39,12.3,294.0,1.0,445.0,2.19
+14.3,1.76,32.2,227.0,19.6,18.1,29.4,737.0,1.0,7.17,2.44
+28.4,2.11,1.0,6.1,30.5,18.6,22.1,269.0,21.1,2690.0,5.99
+44.1,1.89,30.0,39.6,21.1,2.5,9.22,279.0,3.65,308.0,7.91
+43.3,1.61,13.1,120.0,24.4,4.74,5.33,79.9,1.0,1.01,1.58
+40.3,2.64,13.7,111.0,27.9,13.3,17.3,325.0,1.0,1.0,1.0
+176.0,1.01,31.1,35.2,23.9,21.7,24.4,305.0,1.0,1.01,1.24
+25.9,1.58,6.67,147.0,17.2,10.2,13.0,276.0,1.0,1.53,1.0
+21.9,3.62,23.7,26.9,7.23,58.8,90.6,1420.0,1.0,5.28,1.68
+85.1,1.0,17.9,161.0,12.4,10.6,20.2,308.0,3.37,340.0,14.5
+34.0,1.95,27.9,30.8,30.2,4.33,6.04,133.0,1.0,53.3,1.0
+51.9,1.0,14.5,147.0,34.3,7.37,14.7,274.0,2.07,40.7,5.47
+31.9,2.62,20.2,25.9,10.5,22.9,33.1,311.0,1.0,1.0,1.2
+38.9,1.33,10.1,20.5,7.91,69.8,81.3,1334.0,1.0,1.0,2.55
+45.3,1.0,24.1,36.5,15.8,4.7,23.3,346.0,5.73,250.0,1.6
+31.9,2.71,13.7,195.0,20.2,16.1,16.8,322.0,1.0,11.8,2.67
+49.1,12.4,32.8,27.9,22.7,11.7,38.2,1144.0,1.0,2.55,1.0
+23.3,4.61,17.8,22.1,14.9,48.7,67.3,922.0,1.0,9.82,1.0
+28.1,4.49,18.8,20.2,10.2,3.08,21.9,730.0,1.0,1.75,2.0
+34.6,7.1,5.73,20.7,15.1,32.2,41.4,813.0,44.5,1382.0,2.44
+30.5,1.01,7.3,173.0,22.9,6.61,13.7,890.0,1.0,1.0,1.65
diff --git a/gcda/dependency/composed.py b/gcda/dependency/composed.py
new file mode 100644
index 0000000..9f55ec4
--- /dev/null
+++ b/gcda/dependency/composed.py
@@ -0,0 +1,94 @@
+"""Conditional sampling for multi-parent nodes composed from *pairwise* building blocks.
+
+``ConditionalSampler`` (conditional.py) fits a dedicated vine for one specific
+``child | parents`` triple on one dataset, so it only exists for parent sets
+that were present when the library was built. To reuse learned *pairwise*
+dependencies for a multi-parent node that never existed in any source dataset
+(or whose edges come from different datasets), this module composes the
+conditional density of the child from one bivariate copula per incoming edge:
+
+    c(u_C | u_P1, ..., u_Pk)  ∝  prod_j c_j(u_C, u_Pj)
+
+This is exact when the parents are conditionally independent given the child
+in copula space (a star-shaped vine truncated after the first tree, the
+"copula Bayesian network" local density of Elidan, 2010) and an approximation
+otherwise. It deliberately does NOT encode any parent-parent dependence: the
+parents' joint distribution is whatever the surrounding graph generates, which
+is what a transplanted causal mechanism should do.
+
+Sampling inverts the normalized conditional CDF numerically on a fixed grid
+that is uniform in normal-score space (dense in both tails).
+"""
+
+import warnings
+
+import numpy as np
+import pyvinecopulib as pv
+from scipy.stats import norm
+
+from gcda.dependency.conditional import EPS, FallbackWarning
+
+_Z_GRID = np.linspace(-5.5, 5.5, 801)
+
+
+class PairwiseProductConditional:
+    """Sample ``child | parents`` from a product of per-edge bivariate copulas.
+
+    ``edges`` is a list of ``(bicop, child_is_first)`` in the same order as
+    ``parents``: ``child_is_first`` says whether the child occupies the
+    copula's first column (asymmetric/rotated families care about this).
+    """
+
+    def __init__(self, child: str, parents: list[str], edges: list[tuple[pv.Bicop, bool]], clip_eps: float = EPS):
+        if len(edges) != len(parents):
+            raise ValueError("need exactly one bivariate copula per parent")
+        self.child = child
+        self.parents = list(parents)
+        self.edges = edges
+        self.clip_eps = clip_eps
+        self.last_fallback_count_ = 0
+        grid = norm.cdf(_Z_GRID)
+        self.grid_ = np.clip(grid, clip_eps, 1 - clip_eps)
+
+    def _log_density_on_grid(self, u_parents: np.ndarray) -> np.ndarray:
+        n, m = u_parents.shape[0], len(self.grid_)
+        log_dens = np.zeros((n, m))
+        g = np.broadcast_to(self.grid_, (n, m)).ravel()
+        for j, (bicop, child_is_first) in enumerate(self.edges):
+            p = np.repeat(u_parents[:, j], m)
+            pts = np.column_stack([g, p]) if child_is_first else np.column_stack([p, g])
+            dens = bicop.pdf(pts).reshape(n, m)
+            log_dens += np.log(np.maximum(dens, 1e-300))
+        return log_dens
+
+    def sample(self, u_parents: np.ndarray, seed: int | None = None) -> np.ndarray:
+        rng = np.random.default_rng(seed)
+        u_parents = np.clip(np.atleast_2d(np.asarray(u_parents, dtype=float)), self.clip_eps, 1 - self.clip_eps)
+        n = u_parents.shape[0]
+        self.last_fallback_count_ = 0
+        w = rng.uniform(self.clip_eps, 1 - self.clip_eps, size=n)
+        out = np.empty(n)
+        # chunk to bound memory (n x grid)
+        for start in range(0, n, 2000):
+            sl = slice(start, start + 2000)
+            log_dens = self._log_density_on_grid(u_parents[sl])
+            log_dens -= log_dens.max(axis=1, keepdims=True)
+            dens = np.exp(log_dens)
+            # trapezoid CDF over the u-grid (density is w.r.t. u)
+            du = np.diff(self.grid_)
+            seg = 0.5 * (dens[:, 1:] + dens[:, :-1]) * du
+            cdf = np.concatenate([np.zeros((dens.shape[0], 1)), np.cumsum(seg, axis=1)], axis=1)
+            total = cdf[:, -1:]
+            ok = np.isfinite(total[:, 0]) & (total[:, 0] > 0)
+            cdf = np.where(ok[:, None], cdf / np.where(total > 0, total, 1.0), 0.0)
+            draws = np.array([np.interp(wi, ci, self.grid_) for wi, ci in zip(w[sl], cdf)])
+            draws[~ok] = rng.uniform(self.clip_eps, 1 - self.clip_eps, size=int((~ok).sum()))
+            self.last_fallback_count_ += int((~ok).sum())
+            out[sl] = draws
+        if self.last_fallback_count_:
+            warnings.warn(
+                f"PairwiseProductConditional({self.child}|{self.parents}): "
+                f"{self.last_fallback_count_}/{n} degenerate rows, independent fallback used",
+                FallbackWarning,
+            )
+        return np.clip(out, self.clip_eps, 1 - self.clip_eps)
diff --git a/gcda/dependency/conditional.py b/gcda/dependency/conditional.py
index bc1982b..c461882 100644
--- a/gcda/dependency/conditional.py
+++ b/gcda/dependency/conditional.py
@@ -26,6 +26,14 @@ from gcda.dependency.families import DEFAULT_BICOP_FAMILIES
 EPS = 1e-6
 
 
+class FallbackWarning(UserWarning):
+    """Emitted whenever a sampling step falls back to an independent U(0,1) draw.
+
+    A dedicated subclass lets callers count genuine fallback events without
+    also counting unrelated library deprecation warnings.
+    """
+
+
 class ConditionalSampler:
     """Sample a child variable conditional on 1-2 (core) or more parents."""
 
@@ -35,7 +43,9 @@ class ConditionalSampler:
         parents: list[str],
         family_set: list[pv.BicopFamily] = DEFAULT_BICOP_FAMILIES,
         selection_criterion: str = "bic",
+        clip_eps: float = EPS,
     ):
+        self.clip_eps = clip_eps
         self.child = child
         self.parents = list(parents)
         self.family_set = family_set
@@ -43,18 +53,38 @@ class ConditionalSampler:
         self.vine_: pv.Vinecop | None = None
         self.last_fallback_count_ = 0
 
-    def fit(self, u_df: pd.DataFrame) -> "ConditionalSampler":
+    def fit(self, u_df: pd.DataFrame, u_minus_df: pd.DataFrame | None = None,
+            var_types: dict[str, str] | None = None) -> "ConditionalSampler":
+        """Fit the vine on pseudo-observations.
+
+        With `u_minus_df` and `var_types` (see `preprocessing.discrete_cdf_pairs`)
+        discrete columns use the native discrete likelihood instead of
+        jittered pseudo-observations; the stored vine is the latent
+        continuous vine with the selected pair-copulas, used for sampling.
+        """
         columns = [self.child, *self.parents]
         data = u_df[columns].to_numpy()
         d = len(columns)
         # child listed first -> ends up last/fully-conditioned in the vine's
         # internal processing order (see module docstring).
         structure = pv.RVineStructure.from_order(list(range(1, d + 1)))
-        self.vine_ = pv.Vinecop.from_structure(structure=structure)
         controls = pv.FitControlsVinecop(
             family_set=self.family_set, selection_criterion=self.selection_criterion
         )
+        types = [(var_types or {}).get(c, "c") for c in columns]
+        if u_minus_df is not None and "d" in types:
+            fitted = pv.Vinecop.from_structure(structure=structure, var_types=types)
+            fitted.select(np.column_stack([data, u_minus_df[columns].to_numpy()]), controls)
+            pair_copulas = [
+                [pv.Bicop(family=b.family, rotation=b.rotation, parameters=b.parameters) for b in tree]
+                for tree in fitted.pair_copulas
+            ]
+            self.vine_ = pv.Vinecop.from_structure(structure=structure, pair_copulas=pair_copulas)
+            self.var_types_ = types
+            return self
+        self.vine_ = pv.Vinecop.from_structure(structure=structure)
         self.vine_.select(data, controls)
+        self.var_types_ = ["c"] * d
         return self
 
     def sample(self, u_parents: np.ndarray, seed: int | None = None) -> np.ndarray:
@@ -69,31 +99,34 @@ class ConditionalSampler:
 
         # Stability guard: clip to keep every U away from the 0/1 boundary,
         # where inverse-CDF-style computations can blow up.
-        u_parents = np.clip(u_parents, EPS, 1 - EPS)
+        eps = self.clip_eps
+        u_parents = np.clip(u_parents, eps, 1 - eps)
 
         try:
             u_obs = np.column_stack([np.full(n, 0.5), u_parents])
             u_rosen = self.vine_.rosenblatt(u_obs)
             u_final = u_rosen
-            u_final[:, 0] = rng.uniform(EPS, 1 - EPS, size=n)
+            u_final[:, 0] = rng.uniform(eps, 1 - eps, size=n)
             v_final = self.vine_.inverse_rosenblatt(u_final)
-            child_u = np.clip(v_final[:, 0], EPS, 1 - EPS)
+            child_u = np.clip(v_final[:, 0], eps, 1 - eps)
         except Exception as exc:  # noqa: BLE001 - fall back rather than abort a sampling run
             warnings.warn(
                 f"ConditionalSampler({self.child}|{self.parents}) failed ({exc!r}); "
-                "falling back to independent sampling for this batch."
+                "falling back to independent sampling for this batch.",
+                FallbackWarning,
             )
             self.last_fallback_count_ = n
-            return rng.uniform(EPS, 1 - EPS, size=n)
+            return rng.uniform(eps, 1 - eps, size=n)
 
         bad = ~np.isfinite(child_u)
         n_bad = int(bad.sum())
         if n_bad:
             warnings.warn(
                 f"ConditionalSampler({self.child}|{self.parents}): {n_bad}/{n} "
-                "non-finite draws, falling back to independent sampling for those rows."
+                "non-finite draws, falling back to independent sampling for those rows.",
+                FallbackWarning,
             )
-            child_u[bad] = rng.uniform(EPS, 1 - EPS, size=n_bad)
+            child_u[bad] = rng.uniform(eps, 1 - eps, size=n_bad)
             self.last_fallback_count_ = n_bad
         return child_u
 
diff --git a/gcda/dependency/library.py b/gcda/dependency/library.py
index f8ab867..d9f35d1 100644
--- a/gcda/dependency/library.py
+++ b/gcda/dependency/library.py
@@ -1,4 +1,10 @@
-"""Container for the T4 "dependency library": pairwise + conditional models plus marginals."""
+"""Container for the T4 "dependency library": pairwise + conditional models plus marginals.
+
+The library is the only interface between fitting and sampling. It is
+JSON-serializable, indexed by ``dataset`` (a namespace) and variable name, and
+can be merged with other libraries so that a single graph can draw building
+blocks from several source datasets (see ``DependencyLibrary.merge``).
+"""
 
 import json
 from pathlib import Path
@@ -8,6 +14,13 @@ import numpy as np
 from gcda.data.preprocessing import CategoricalMarginal, EmpiricalMarginal
 from gcda.dependency.conditional import ConditionalSampler
 
+SCHEMA_VERSION = 2
+_REQUIRED_KEYS = ("pairwise", "conditional", "marginals")
+
+
+class LibraryFormatError(ValueError):
+    """Raised when a serialized library does not have the expected structure."""
+
 
 class DependencyLibrary:
     """Holds everything needed to later sample a graph (T5): fitted pairwise
@@ -19,28 +32,54 @@ class DependencyLibrary:
         self.pairwise: list[dict] = []
         self.conditional: list[dict] = []
         self.marginals: dict[str, dict[str, dict]] = {}
+        self.metadata: dict = {}
 
+    # ------------------------------------------------------------------ building
     def add_pairwise(self, entries: list[dict]) -> None:
         self.pairwise.extend(entries)
 
     def add_conditional(self, dataset: str, sampler: ConditionalSampler) -> None:
         self.conditional.append({"dataset": dataset, **sampler.to_dict()})
 
-    def add_marginals(self, dataset: str, marginals: dict) -> None:
+    def add_marginals(self, dataset: str, marginals: dict, max_points: int | None = None) -> None:
+        """Store each column's marginal.
+
+        ``max_points`` (optional) compresses an empirical marginal to that many
+        quantile knots instead of storing every sorted observation; this keeps
+        libraries small for large n at the cost of a piecewise-linear
+        approximation of the quantile function between knots.
+        """
         stored = {}
         for col, m in marginals.items():
             if isinstance(m, CategoricalMarginal):
                 stored[col] = {"type": "categorical", "categories": list(m.categories_), "cum_probs": m.cum_probs_.tolist()}
-            else:
-                stored[col] = {
-                    "type": "empirical",
-                    "sorted_values": m.sorted_values_.tolist(),
-                    "plotting_positions": m.plotting_positions_.tolist(),
-                }
+                continue
+            values, positions = m.sorted_values_, m.plotting_positions_
+            if max_points is not None and len(values) > max_points:
+                knots = np.linspace(positions[0], positions[-1], max_points)
+                values = np.interp(knots, positions, values)
+                positions = knots
+            stored[col] = {
+                "type": "empirical",
+                "sorted_values": np.asarray(values).tolist(),
+                "plotting_positions": np.asarray(positions).tolist(),
+            }
         self.marginals[dataset] = stored
 
+    # ------------------------------------------------------------------ lookup
+    @property
+    def datasets(self) -> list[str]:
+        names = set(self.marginals) | {e["dataset"] for e in self.pairwise} | {e["dataset"] for e in self.conditional}
+        return sorted(names)
+
+    def has_marginal(self, dataset: str, column: str) -> bool:
+        return column in self.marginals.get(dataset, {})
+
     def get_marginal(self, dataset: str, column: str):
-        stored = self.marginals[dataset][column]
+        try:
+            stored = self.marginals[dataset][column]
+        except KeyError:
+            raise KeyError(f"no marginal for {dataset}:{column}") from None
         if stored["type"] == "categorical":
             marginal = CategoricalMarginal()
             marginal.categories_ = stored["categories"]
@@ -51,14 +90,53 @@ class DependencyLibrary:
         marginal.plotting_positions_ = np.array(stored["plotting_positions"])
         return marginal
 
+    def get_pairwise_entry(self, dataset: str, var_a: str, var_b: str) -> dict:
+        """Return the fitted pairwise entry for the unordered pair {var_a, var_b}."""
+        for entry in self.pairwise:
+            if entry["dataset"] == dataset and {entry["var_i"], entry["var_j"]} == {var_a, var_b} and "error" not in entry:
+                return entry
+        raise KeyError(f"no pairwise model for {dataset}: {var_a} -- {var_b}")
+
     def get_conditional_sampler(self, dataset: str, child: str, parents: list[str]) -> ConditionalSampler:
+        """Return the conditional model for ``child | parents``.
+
+        Matching is on the *set* of parents: the returned sampler keeps its own
+        fitted parent order in ``sampler.parents``, and callers must supply
+        parent columns in that order (``GraphSampler`` does this automatically).
+        An earlier version matched on the ordered list, so the same DAG written
+        with its edges in a different order silently lost its learned model.
+        """
+        wanted = set(parents)
         for entry in self.conditional:
-            if entry["dataset"] == dataset and entry["child"] == child and entry["parents"] == list(parents):
+            if entry["dataset"] == dataset and entry["child"] == child and set(entry["parents"]) == wanted:
                 return ConditionalSampler.from_dict(entry)
-        raise KeyError(f"No conditional model for {dataset}: {child} | {parents}")
+        raise KeyError(f"No conditional model for {dataset}: {child} | {sorted(parents)}")
 
+    # ------------------------------------------------------------------ combining
+    def merge(self, other: "DependencyLibrary", overwrite: bool = False) -> "DependencyLibrary":
+        """Return a new library containing the models of ``self`` and ``other``.
+
+        Dataset namespaces must not collide (two libraries both defining
+        ``sachs`` would make every lookup ambiguous) unless ``overwrite=True``,
+        in which case ``other`` wins for colliding namespaces.
+        """
+        clash = set(self.datasets) & set(other.datasets)
+        if clash and not overwrite:
+            raise ValueError(f"dataset namespaces present in both libraries: {sorted(clash)}")
+        merged = DependencyLibrary()
+        keep_self = [d for d in self.datasets if d not in clash] if overwrite else self.datasets
+        merged.pairwise = [e for e in self.pairwise if e["dataset"] in keep_self] + list(other.pairwise)
+        merged.conditional = [e for e in self.conditional if e["dataset"] in keep_self] + list(other.conditional)
+        merged.marginals = {d: m for d, m in self.marginals.items() if d in keep_self}
+        merged.marginals.update(other.marginals)
+        merged.metadata = {"merged_from": [self.metadata, other.metadata]}
+        return merged
+
+    # ------------------------------------------------------------------ io
     def save(self, path: str | Path) -> None:
         payload = {
+            "schema_version": SCHEMA_VERSION,
+            "metadata": self.metadata,
             "pairwise": self.pairwise,
             "conditional": self.conditional,
             "marginals": self.marginals,
@@ -68,8 +146,32 @@ class DependencyLibrary:
     @classmethod
     def load(cls, path: str | Path) -> "DependencyLibrary":
         payload = json.loads(Path(path).read_text())
+        return cls.from_payload(payload)
+
+    @classmethod
+    def from_payload(cls, payload: dict) -> "DependencyLibrary":
+        if not isinstance(payload, dict) or any(k not in payload for k in _REQUIRED_KEYS):
+            raise LibraryFormatError(f"library JSON must contain keys {_REQUIRED_KEYS}")
+        version = payload.get("schema_version", 1)  # v1 files (thesis outputs) have no version field
+        if version > SCHEMA_VERSION:
+            raise LibraryFormatError(f"library schema_version {version} is newer than supported {SCHEMA_VERSION}")
+        for entry in payload["pairwise"]:
+            if not {"dataset", "var_i", "var_j"} <= set(entry):
+                raise LibraryFormatError(f"malformed pairwise entry: {sorted(entry)}")
+        for entry in payload["conditional"]:
+            if not {"dataset", "child", "parents", "vine_json"} <= set(entry):
+                raise LibraryFormatError(f"malformed conditional entry: {sorted(entry)}")
         library = cls()
         library.pairwise = payload["pairwise"]
         library.conditional = payload["conditional"]
         library.marginals = payload["marginals"]
+        library.metadata = payload.get("metadata", {})
+        return library
+
+    @classmethod
+    def load_many(cls, paths: list[str | Path]) -> "DependencyLibrary":
+        """Load and merge several library files (namespaces must not collide)."""
+        library = cls()
+        for path in paths:
+            library = library.merge(cls.load(path))
         return library
diff --git a/gcda/dependency/pairwise.py b/gcda/dependency/pairwise.py
index 4d36ee1..f21971a 100644
--- a/gcda/dependency/pairwise.py
+++ b/gcda/dependency/pairwise.py
@@ -1,5 +1,6 @@
 """T4c: fit pairwise dependence models (AIC/BIC family selection) and store diagnostics."""
 
+from concurrent.futures import ThreadPoolExecutor
 from itertools import combinations
 
 import numpy as np
@@ -14,21 +15,39 @@ def fit_bicop(
     u_j: np.ndarray,
     family_set: list[pv.BicopFamily] = DEFAULT_BICOP_FAMILIES,
     selection_criterion: str = "bic",
+    u_i_minus: np.ndarray | None = None,
+    u_j_minus: np.ndarray | None = None,
+    var_types: tuple[str, str] = ("c", "c"),
 ) -> tuple[pv.Bicop, dict]:
-    """Fit a single bivariate copula on two U(0,1) columns, selecting the family via AIC/BIC."""
-    u = np.column_stack([u_i, u_j])
-    cop = pv.Bicop()
+    """Fit a single bivariate copula on two U(0,1) columns, selecting the family via AIC/BIC.
+
+    With `var_types` containing "d", the native discrete likelihood is used:
+    `u_*` must then be F(x) and `u_*_minus` F(x-) (see
+    `preprocessing.discrete_cdf_pairs`). The returned copula is the latent
+    (continuous) copula, which is what the samplers need.
+    """
     controls = pv.FitControlsBicop(family_set=family_set, selection_criterion=selection_criterion)
-    cop.select(u, controls)
+    if "d" in var_types:
+        u = np.column_stack([u_i, u_j, u_i_minus, u_j_minus])
+        fitted = pv.Bicop(var_types=list(var_types))
+        fitted.select(u, controls)
+        cop = pv.Bicop(family=fitted.family, rotation=fitted.rotation, parameters=fitted.parameters)
+        aic, bic = fitted.aic(u), fitted.bic(u)
+    else:
+        u = np.column_stack([u_i, u_j])
+        cop = pv.Bicop()
+        cop.select(u, controls)
+        aic, bic = cop.aic(u), cop.bic(u)
 
     diagnostics = {
         "family": cop.family.name,
         "rotation": cop.rotation,
         "parameters": cop.parameters.tolist(),
         "tau": cop.tau,
-        "aic": cop.aic(u),
-        "bic": cop.bic(u),
+        "aic": aic,
+        "bic": bic,
         "n": len(u_i),
+        "var_types": list(var_types),
     }
     return cop, diagnostics
 
@@ -39,28 +58,57 @@ def build_pairwise_library(
     pairs: list[tuple[str, str]] | None = None,
     family_set: list[pv.BicopFamily] = DEFAULT_BICOP_FAMILIES,
     selection_criterion: str = "bic",
+    n_jobs: int = 1,
+    u_minus_df: pd.DataFrame | None = None,
+    var_types: dict[str, str] | None = None,
 ) -> list[dict]:
     """Fit pairwise dependence models for many variable pairs and collect metadata.
 
-    Defaults to every unordered pair of columns in `u_df`. Failures on a
-    given pair are recorded (with an `error` field) rather than aborting the
-    whole run, since the library is meant to be built once from real data.
+    Defaults to every unordered pair of columns in `u_df` (O(p^2) fits); pass
+    `pairs` (e.g. only a graph's edges) to restrict it for large p. Pairs are
+    independent, so `n_jobs > 1` fits them in a thread pool; results are
+    identical to the sequential run and returned in the same order. Failures
+    on a given pair are recorded (with an `error` field) rather than aborting
+    the whole run.
     """
     if pairs is None:
         pairs = list(combinations(u_df.columns, 2))
 
-    entries = []
-    for var_i, var_j in pairs:
+    def fit_one(pair: tuple[str, str]) -> dict:
+        var_i, var_j = pair
         entry = {"dataset": dataset_name, "var_i": var_i, "var_j": var_j}
         try:
+            vt = (var_types or {}).get(var_i, "c"), (var_types or {}).get(var_j, "c")
+            native = u_minus_df is not None and "d" in vt
             _, diagnostics = fit_bicop(
                 u_df[var_i].to_numpy(),
                 u_df[var_j].to_numpy(),
                 family_set=family_set,
                 selection_criterion=selection_criterion,
+                u_i_minus=u_minus_df[var_i].to_numpy() if native else None,
+                u_j_minus=u_minus_df[var_j].to_numpy() if native else None,
+                var_types=vt if native else ("c", "c"),
             )
             entry.update(diagnostics)
         except Exception as exc:  # noqa: BLE001 - keep building the library on a bad pair
             entry["error"] = str(exc)
-        entries.append(entry)
-    return entries
+        return entry
+
+    if n_jobs > 1:
+        with ThreadPoolExecutor(max_workers=n_jobs) as pool:
+            return list(pool.map(fit_one, pairs))
+    return [fit_one(pair) for pair in pairs]
+
+
+def top_k_partners(pairwise_entries: list[dict], target: str, k: int = 2) -> list[str]:
+    """Rank a target variable's pairwise partners by |Kendall's tau| and return the top k."""
+    scored = []
+    for entry in pairwise_entries:
+        if "error" in entry:
+            continue
+        if entry["var_i"] == target:
+            scored.append((abs(entry["tau"]), entry["var_j"]))
+        elif entry["var_j"] == target:
+            scored.append((abs(entry["tau"]), entry["var_i"]))
+    scored.sort(reverse=True)
+    return [name for _, name in scored[:k]]
diff --git a/gcda/evaluation/causal_discovery.py b/gcda/evaluation/causal_discovery.py
index 76bb20c..a059d37 100644
--- a/gcda/evaluation/causal_discovery.py
+++ b/gcda/evaluation/causal_discovery.py
@@ -40,6 +40,20 @@ def run_pc(df: pd.DataFrame, indep_test: str = "fisherz", alpha: float = 0.05):
     return pc(data, alpha=alpha, indep_test=indep_test, node_names=node_names, show_progress=False)
 
 
+def run_ges(df: pd.DataFrame, discrete: bool = False):
+    """Greedy Equivalence Search (causal-learn) with BIC (continuous) or BDeu (discrete) score.
+
+    Returns an object with a `.G` attribute (the estimated CPDAG), like `run_pc`.
+    """
+    from types import SimpleNamespace
+
+    from causallearn.search.ScoreBased.GES import ges
+
+    score = "local_score_BDeu" if discrete else "local_score_BIC"
+    record = ges(df.to_numpy().astype(float), score_func=score, node_names=list(df.columns))
+    return SimpleNamespace(G=record["G"])
+
+
 def encode_categorical(df: pd.DataFrame, category_orders: dict[str, list]) -> pd.DataFrame:
     """Map categorical columns to integer codes (0..K-1) for chisq/gsq independence tests."""
     out = {}
diff --git a/gcda/evaluation/discrete.py b/gcda/evaluation/discrete.py
index 3de557b..5703ba5 100644
--- a/gcda/evaluation/discrete.py
+++ b/gcda/evaluation/discrete.py
@@ -94,20 +94,35 @@ def compare_discrete_dependence(
 
 
 def measure_generation_stability(sampler, n: int, seed: int = 0) -> tuple[pd.DataFrame, dict]:
-    """Sample from `sampler` (a GraphSampler) once, recording wall-clock time
-    and how many fallback events (T4d/T5c.iv warnings) were raised.
+    """Sample from `sampler` (a GraphSampler) once, recording wall-clock time,
+    fallback events and fallback draws.
+
+    `n_fallback_events` counts `FallbackWarning`s only (an earlier version
+    counted every UserWarning, so unrelated library deprecation warnings could
+    inflate it). `n_fallback_draws` comes from the sampler's own per-node
+    counters, and `n_marginal_drift_nodes` counts nodes flagged by a
+    `MarginalDriftWarning`.
     """
+    from gcda.dependency.conditional import FallbackWarning
+    from gcda.generation.graph_sampler import MarginalDriftWarning
+
     with warnings.catch_warnings(record=True) as caught:
         warnings.simplefilter("always")
         t0 = time.time()
         df = sampler.sample(n=n, seed=seed)
         elapsed = time.time() - t0
 
-    fallback_events = [str(w.message) for w in caught if issubclass(w.category, UserWarning)]
+    fallback_events = [w for w in caught if issubclass(w.category, FallbackWarning)]
+    drift_events = [w for w in caught if issubclass(w.category, MarginalDriftWarning)]
+    n_draws = int(sum(getattr(sampler, "fallback_counts_", {}).values()))
+    n_nodes = len(sampler.dag.nodes)
     metrics = {
         "n": n,
         "elapsed_sec": elapsed,
         "n_fallback_events": len(fallback_events),
-        "fallback_event_rate": len(fallback_events) / len(sampler.dag.nodes),
+        "fallback_event_rate": len(fallback_events) / n_nodes,
+        "n_fallback_draws": n_draws,
+        "fallback_draw_rate": n_draws / (n * n_nodes),
+        "n_marginal_drift_nodes": len(drift_events),
     }
     return df, metrics
diff --git a/gcda/evaluation/realism.py b/gcda/evaluation/realism.py
index 3809bd4..d29aadf 100644
--- a/gcda/evaluation/realism.py
+++ b/gcda/evaluation/realism.py
@@ -105,33 +105,90 @@ def _subsample(x: np.ndarray, max_n: int, rng: np.random.Generator) -> np.ndarra
     return x[idx]
 
 
-def energy_distance(x: np.ndarray, y: np.ndarray, max_n: int = 500, seed: int = 0) -> float:
-    """Energy distance between two multivariate samples (Szekely & Rizzo).
+def energy_distance(x: np.ndarray, y: np.ndarray, max_n: int = 500, seed: int = 0, unbiased: bool = False) -> float:
+    """Energy distance between two multivariate samples (Szekely & Rizzo, 2013).
 
     E = 2*E|X-Y| - E|X-X'| - E|Y-Y'|, using Euclidean distance. O(n^2), so both
-    samples are subsampled to `max_n` points.
+    samples are subsampled to `max_n` points. The default (`unbiased=False`) is
+    the V-statistic that includes the zero diagonal of the within-sample
+    distance matrices (the values reported in the thesis sweep table);
+    `unbiased=True` excludes the diagonal (U-statistic), which is centred at
+    0 when both samples come from the same distribution.
     """
     rng = np.random.default_rng(seed)
     x = _subsample(np.atleast_2d(x), max_n, rng)
     y = _subsample(np.atleast_2d(y), max_n, rng)
-    d_xy = cdist(x, y).mean()
-    d_xx = cdist(x, x).mean()
-    d_yy = cdist(y, y).mean()
-    return float(2 * d_xy - d_xx - d_yy)
+    return _energy(x, y, unbiased)
 
 
-def gaussian_mmd(x: np.ndarray, y: np.ndarray, max_n: int = 500, seed: int = 0) -> float:
-    """Squared MMD between two multivariate samples with an RBF kernel (median-distance bandwidth)."""
+def _within_mean(d: np.ndarray, unbiased: bool) -> float:
+    if not unbiased:
+        return float(d.mean())
+    n = d.shape[0]
+    return float((d.sum() - np.trace(d)) / (n * (n - 1)))
+
+
+def _energy(x: np.ndarray, y: np.ndarray, unbiased: bool) -> float:
+    return float(2 * cdist(x, y).mean() - _within_mean(cdist(x, x), unbiased) - _within_mean(cdist(y, y), unbiased))
+
+
+def gaussian_mmd(x: np.ndarray, y: np.ndarray, max_n: int = 500, seed: int = 0, unbiased: bool = False,
+                 bandwidth: float | None = None) -> float:
+    """Squared MMD (Gretton et al., 2012) with an RBF kernel (median-distance bandwidth).
+
+    `unbiased=True` gives the unbiased U-statistic estimator (diagonal terms
+    excluded); the default biased V-statistic matches the thesis sweep table.
+    """
     rng = np.random.default_rng(seed)
     x = _subsample(np.atleast_2d(x), max_n, rng)
     y = _subsample(np.atleast_2d(y), max_n, rng)
+    if bandwidth is None:
+        bandwidth = _median_bandwidth(x, y)
+    return _mmd(x, y, bandwidth, unbiased)
 
+
+def _median_bandwidth(x: np.ndarray, y: np.ndarray) -> float:
     combined = np.vstack([x, y])
     pairwise = cdist(combined, combined)
     median_dist = np.median(pairwise[pairwise > 0])
-    bandwidth = median_dist if median_dist > 0 else 1.0
+    return float(median_dist) if median_dist > 0 else 1.0
+
 
+def _mmd(x: np.ndarray, y: np.ndarray, bandwidth: float, unbiased: bool) -> float:
     def kernel(a, b):
         return np.exp(-cdist(a, b) ** 2 / (2 * bandwidth ** 2))
 
-    return float(kernel(x, x).mean() + kernel(y, y).mean() - 2 * kernel(x, y).mean())
+    return float(_within_mean(kernel(x, x), unbiased) + _within_mean(kernel(y, y), unbiased) - 2 * kernel(x, y).mean())
+
+
+def permutation_test(statistic, x: np.ndarray, y: np.ndarray, n_permutations: int = 200, max_n: int = 500,
+                     seed: int = 0) -> dict:
+    """Two-sample permutation test for `energy_distance` or `gaussian_mmd`.
+
+    Both samples are subsampled to `max_n` once, the unbiased statistic is
+    computed, and the pooled sample is re-split `n_permutations` times.
+    Returns the observed statistic and the permutation p-value (with the +1
+    correction, so it is never exactly 0).
+    """
+    rng = np.random.default_rng(seed)
+    x = _subsample(np.atleast_2d(x), max_n, rng)
+    y = _subsample(np.atleast_2d(y), max_n, rng)
+    if statistic is gaussian_mmd:
+        bw = _median_bandwidth(x, y)
+
+        def stat(a, b):
+            return _mmd(a, b, bw, True)
+    elif statistic is energy_distance:
+        def stat(a, b):
+            return _energy(a, b, True)
+    else:
+        stat = statistic
+    observed = stat(x, y)
+    pooled = np.vstack([x, y])
+    nx_ = len(x)
+    exceed = 0
+    for _ in range(n_permutations):
+        idx = rng.permutation(len(pooled))
+        if stat(pooled[idx[:nx_]], pooled[idx[nx_:]]) >= observed:
+            exceed += 1
+    return {"statistic": observed, "p_value": (exceed + 1) / (n_permutations + 1), "n_permutations": n_permutations}
diff --git a/gcda/experiments/__init__.py b/gcda/experiments/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/gcda/experiments/common.py b/gcda/experiments/common.py
new file mode 100644
index 0000000..bf18ae6
--- /dev/null
+++ b/gcda/experiments/common.py
@@ -0,0 +1,126 @@
+"""Shared helpers for the remediation experiments (held-out libraries, baselines, statistics)."""
+
+import warnings
+
+import networkx as nx
+import numpy as np
+import pandas as pd
+import pyvinecopulib as pv
+from scipy import stats
+
+from gcda.data.preprocessing import discrete_cdf_pairs, to_pseudo_observations_mixed
+from gcda.dependency.conditional import ConditionalSampler
+from gcda.dependency.families import DEFAULT_BICOP_FAMILIES
+from gcda.dependency.library import DependencyLibrary
+from gcda.dependency.pairwise import build_pairwise_library
+from gcda.generation.graph_sampler import GraphSampler, NodeSpec, node_spec_from_library
+
+GAUSSIAN_ONLY = [pv.BicopFamily.indep, pv.BicopFamily.gaussian]
+
+
+def fit_graph_library(df: pd.DataFrame, dag: nx.DiGraph, category_orders: dict | None, dataset: str,
+                      family_set=DEFAULT_BICOP_FAMILIES, n_jobs: int = 4, all_pairs: bool = False,
+                      discrete_mode: str = "jitter") -> DependencyLibrary:
+    """Fit marginals, pairwise copulas (graph edges only unless all_pairs) and one
+    conditional vine per multi-parent node, on a *training* draw.
+
+    discrete_mode="jitter": discrete columns are continuized by jittering (thesis method);
+    discrete_mode="native": pyvinecopulib's discrete likelihood on F(x), F(x-).
+    """
+    u_df, marginals = to_pseudo_observations_mixed(df, category_orders=category_orders, seed=0)
+    u_minus, var_types = None, None
+    if discrete_mode == "native":
+        u_df, u_minus, var_types = discrete_cdf_pairs(df, marginals)
+    elif discrete_mode != "jitter":
+        raise ValueError(f"unknown discrete_mode {discrete_mode!r}")
+    library = DependencyLibrary()
+    library.add_marginals(dataset, marginals)
+    pairs = None if all_pairs else [tuple(e) for e in dag.edges]
+    library.add_pairwise(build_pairwise_library(u_df, dataset, pairs=pairs, family_set=family_set, n_jobs=n_jobs,
+                                                u_minus_df=u_minus, var_types=var_types))
+    for node in dag.nodes:
+        parents = list(dag.predecessors(node))
+        if len(parents) >= 2:
+            sampler = ConditionalSampler(child=node, parents=parents, family_set=family_set)
+            library.add_conditional(dataset, sampler.fit(u_df, u_minus, var_types))
+    return library
+
+
+def learned_specs(library: DependencyLibrary, dataset: str, dag: nx.DiGraph, compose: bool = False) -> dict[str, NodeSpec]:
+    return {n: node_spec_from_library(library, dataset, n, list(dag.predecessors(n)), compose=compose) for n in dag.nodes}
+
+
+def baseline_specs(library: DependencyLibrary, dataset: str, dag: nx.DiGraph) -> dict[str, NodeSpec]:
+    """Real marginals, fixed-correlation Gaussian dependence everywhere (the thesis baseline)."""
+    return {n: NodeSpec(marginal=library.get_marginal(dataset, n)) for n in dag.nodes}
+
+
+def sample(dag, specs, n, seed, calibrate=False):
+    max_indeg = max([d for _, d in dag.in_degree()] + [1])
+    with warnings.catch_warnings():
+        warnings.simplefilter("ignore")
+        sampler = GraphSampler(dag, node_specs=specs, max_indegree=max(max_indeg, 2), calibrate_margins=calibrate)
+        return sampler.sample(n=n, seed=seed), sampler
+
+
+def cpt_refit_sample(train_df: pd.DataFrame, dag: nx.DiGraph, n: int, seed: int) -> pd.DataFrame:
+    """Natural discrete baseline: refit the network's CPTs by maximum likelihood on
+    the training draw, then forward-sample. Uses the TRUE DAG, like every generator here."""
+    with warnings.catch_warnings():
+        warnings.simplefilter("ignore")
+        try:
+            from pgmpy.models import DiscreteBayesianNetwork as BN
+        except ImportError:  # pragma: no cover - older pgmpy
+            from pgmpy.models import BayesianNetwork as BN
+        model = BN(list(dag.edges))
+        model.add_nodes_from(dag.nodes)
+        model.fit(train_df[list(dag.nodes)])  # default estimator = maximum likelihood (all pgmpy versions)
+        out = model.simulate(n_samples=n, seed=seed, show_progress=False)
+    return out[list(dag.nodes)].reset_index(drop=True)
+
+
+def skeleton_scores(true_dag: nx.DiGraph, est_graph, node_names: list[str]) -> dict:
+    """Adjacency precision/recall/F1 of a causal-learn graph against the true DAG."""
+    adj = est_graph.graph
+    est = {frozenset((node_names[i], node_names[j])) for i in range(len(node_names)) for j in range(i + 1, len(node_names))
+           if adj[i, j] != 0 or adj[j, i] != 0}
+    true = {frozenset(e) for e in true_dag.edges}
+    tp = len(est & true)
+    precision = tp / len(est) if est else 1.0
+    recall = tp / len(true) if true else 1.0
+    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
+    return {"n_edges_found": len(est), "skeleton_precision": precision, "skeleton_recall": recall, "skeleton_f1": f1}
+
+
+def bootstrap_ci(values, n_boot: int = 5000, seed: int = 0, level: float = 0.95) -> tuple[float, float]:
+    values = np.asarray(values, dtype=float)
+    if len(values) < 2:
+        return float("nan"), float("nan")
+    rng = np.random.default_rng(seed)
+    means = rng.choice(values, size=(n_boot, len(values)), replace=True).mean(axis=1)
+    lo, hi = np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2])
+    return float(lo), float(hi)
+
+
+def paired_comparison(a, b) -> dict:
+    """Paired comparison of two per-seed metric vectors (a - b): mean difference,
+    bootstrap 95% CI, Wilcoxon signed-rank and paired t-test p-values."""
+    a, b = np.asarray(a, float), np.asarray(b, float)
+    d = a - b
+    lo, hi = bootstrap_ci(d)
+    try:
+        w = stats.wilcoxon(a, b, zero_method="zsplit").pvalue if np.any(d != 0) else 1.0
+    except ValueError:
+        w = float("nan")
+    t = stats.ttest_rel(a, b).pvalue if np.std(d) > 0 else (1.0 if np.mean(d) == 0 else 0.0)
+    return {"mean_diff": float(d.mean()), "ci_low": lo, "ci_high": hi, "wilcoxon_p": float(w), "ttest_p": float(t), "n": len(d)}
+
+
+def summarize(df: pd.DataFrame, group: list[str], metric: str) -> pd.DataFrame:
+    rows = []
+    for key, g in df.groupby(group):
+        lo, hi = bootstrap_ci(g[metric])
+        key = key if isinstance(key, tuple) else (key,)
+        rows.append({**dict(zip(group, key)), "mean": g[metric].mean(), "std": g[metric].std(ddof=1),
+                     "ci_low": lo, "ci_high": hi, "n": len(g)})
+    return pd.DataFrame(rows)
diff --git a/gcda/experiments/composition.py b/gcda/experiments/composition.py
new file mode 100644
index 0000000..c852e41
--- /dev/null
+++ b/gcda/experiments/composition.py
@@ -0,0 +1,252 @@
+"""RQ5: are learned dependencies reusable as building blocks for graphs that never existed?
+
+Two experiments:
+
+(a) The thesis' cross-dataset graph praf -> pmek, praf -> dysp, built from a
+    merged Sachs + Asia library. praf/pmek keep their Sachs marginals and the
+    learned praf-pmek copula; dysp keeps its Asia marginal; the cross-dataset
+    edge praf -> dysp re-uses (binds) the copula Asia learned for
+    bronc -> dysp. Reported: marginal fidelity of every node, and whether
+    each edge reproduces the dependence of the copula it was built from.
+
+(b) Novel random DAGs over the 11 Sachs variables (max indegree 2): none of
+    these graphs exists in the data. For each DAG and each generator
+    (learned pairwise copulas + fitted vines; learned pairwise copulas +
+    pairwise-composed multi-parent models; fitted Gaussian copula; fixed
+    rho=0.5 baseline) we report: PC's SHD/skeleton-F1 to the *specified* DAG
+    (does the generator produce data faithful to the requested graph?),
+    per-edge tau fidelity to the library copula, marginal drift with and
+    without calibration, and varsortability (Reisach et al., 2021).
+"""
+
+import warnings
+
+import networkx as nx
+import numpy as np
+import pandas as pd
+from scipy.stats import kendalltau, ks_2samp
+
+from gcda.data.datasets import load_asia, load_sachs
+from gcda.data.preprocessing import to_pseudo_observations, to_pseudo_observations_mixed
+from gcda.dependency.conditional import ConditionalSampler
+from gcda.dependency.library import DependencyLibrary
+from gcda.dependency.pairwise import build_pairwise_library
+from gcda.evaluation.causal_discovery import run_pc, structural_hamming_distance
+from gcda.evaluation.discrete import compare_category_frequencies
+from gcda.experiments.common import GAUSSIAN_ONLY, bootstrap_ci, paired_comparison, skeleton_scores
+from gcda.generation.graph_sampler import GraphSampler, NodeSpec
+from gcda.generation.spec import build_node_specs
+
+
+def kendall_tau_a(x, y) -> float:
+    """Kendall's tau-a via tau_b and tie fractions (exact identity, O(n log n))."""
+    x, y = np.asarray(x), np.asarray(y)
+    tb = kendalltau(x, y, variant="b")[0]
+    n = len(x)
+    n0 = n * (n - 1) / 2
+
+    def tied_pairs(v):
+        _, c = np.unique(v, return_counts=True)
+        return float((c * (c - 1) / 2).sum())
+
+    return float(tb * np.sqrt((n0 - tied_pairs(x)) * (n0 - tied_pairs(y))) / n0)
+
+
+def varsortability(df: pd.DataFrame, dag: nx.DiGraph) -> float:
+    """Fraction of directed paths (here: edges) along which marginal variance increases."""
+    var = df.var()
+    edges = list(dag.edges)
+    if not edges:
+        return float("nan")
+    return float(np.mean([1.0 if var[b] > var[a] else 0.5 if var[b] == var[a] else 0.0 for a, b in edges]))
+
+
+# --------------------------------------------------------------------------- (a)
+def cross_dataset_rq5(seeds: list[int], n: int = 10000) -> tuple[pd.DataFrame, dict]:
+    sachs = load_sachs()
+    asia, asia_dag, orders = load_asia(n_samples=10000, seed=0)
+    lib = DependencyLibrary()
+    u_s, m_s = to_pseudo_observations(sachs)
+    lib.add_marginals("sachs", m_s)
+    lib.add_pairwise(build_pairwise_library(u_s, "sachs", pairs=[("praf", "pmek")]))
+    lib_a = DependencyLibrary()
+    u_a, m_a = to_pseudo_observations_mixed(asia, category_orders=orders, seed=0)
+    lib_a.add_marginals("asia", m_a)
+    lib_a.add_pairwise(build_pairwise_library(u_a, "asia", pairs=[("bronc", "dysp")]))
+    merged = lib.merge(lib_a)
+    spec = {
+        "nodes": {"praf": {"dataset": "sachs"}, "pmek": {"dataset": "sachs"}, "dysp": {"dataset": "asia"}},
+        "edges": [["praf", "pmek"], {"from": "praf", "to": "dysp", "copula": {"dataset": "asia", "pair": ["bronc", "dysp"]}}],
+    }
+    dag, specs, report = build_node_specs(merged, spec, strict=True)
+    tau_cop_sachs = merged.get_pairwise_entry("sachs", "praf", "pmek")["tau"]
+    tau_cop_asia = merged.get_pairwise_entry("asia", "bronc", "dysp")["tau"]
+    dysp_codes = asia["dysp"].map({s: i for i, s in enumerate(orders["dysp"])})
+    bronc_codes = asia["bronc"].map({s: i for i, s in enumerate(orders["bronc"])})
+    rows = []
+    for seed in seeds:
+        sampler = GraphSampler(dag, node_specs=specs)
+        gen = sampler.sample(n=n, seed=seed)
+        lat = sampler.u_values_
+        gen_dysp = gen["dysp"].map({s: i for i, s in enumerate(orders["dysp"])})
+        rows.append({
+            "seed": seed,
+            "ks_praf": ks_2samp(gen["praf"], sachs["praf"]).statistic,
+            "ks_pmek": ks_2samp(gen["pmek"], sachs["pmek"]).statistic,
+            "tvd_dysp": compare_category_frequencies(asia[["dysp"]], gen[["dysp"]])["total_variation_distance"][0],
+            "tau_praf_pmek_generated": kendalltau(gen["praf"], gen["pmek"])[0],
+            "tau_praf_pmek_sachs_data": kendalltau(sachs["praf"], sachs["pmek"])[0],
+            "tau_praf_pmek_copula": tau_cop_sachs,
+            "tau_latent_praf_dysp_generated": kendalltau(lat["praf"], lat["dysp"])[0],
+            "tau_a_praf_dysp_generated": kendall_tau_a(gen["praf"], gen_dysp),
+            "tau_a_bronc_dysp_asia_data": kendall_tau_a(bronc_codes, dysp_codes),
+            "tau_bronc_dysp_copula": tau_cop_asia,
+        })
+    return pd.DataFrame(rows), {"decisions": report}
+
+
+# --------------------------------------------------------------------------- (b)
+def random_dag(nodes: list[str], rng: np.random.Generator, max_parents: int = 2, edge_prob: float = 0.3) -> nx.DiGraph:
+    order = list(rng.permutation(nodes))
+    dag = nx.DiGraph()
+    dag.add_nodes_from(order)
+    for i, child in enumerate(order[1:], start=1):
+        candidates = order[:i]
+        k = min(max_parents, int(rng.binomial(len(candidates), edge_prob)) if candidates else 0)
+        k = min(k, len(candidates))
+        for parent in rng.choice(candidates, size=k, replace=False):
+            dag.add_edge(parent, child)
+    return dag
+
+
+def _sachs_libraries(u_df, marginals):
+    full, gauss = DependencyLibrary(), DependencyLibrary()
+    for lib, fams in [(full, None), (gauss, GAUSSIAN_ONLY)]:
+        lib.add_marginals("sachs", marginals)
+        kwargs = {"family_set": fams} if fams else {}
+        lib.add_pairwise(build_pairwise_library(u_df, "sachs", n_jobs=4, **kwargs))
+    return full, gauss
+
+
+def novel_graph_study(n_dags: int, n: int = 5000, observational_only: bool = False, dag_start: int = 0) -> pd.DataFrame:
+    sachs = load_sachs(observational_only=observational_only)
+    u_df, marginals = to_pseudo_observations(sachs)
+    lib_full, lib_gauss = _sachs_libraries(u_df, marginals)
+    nodes = list(sachs.columns)
+    rows = []
+    for d in range(dag_start, dag_start + n_dags):
+        rng = np.random.default_rng(1000 + d)
+        dag = random_dag(nodes, rng)
+        spec = {"nodes": {v: {"dataset": "sachs"} for v in nodes}, "edges": [list(e) for e in dag.edges]}
+        # fitted-vine variant: fit a conditional vine for every multi-parent node of THIS graph
+        lib_vine = DependencyLibrary.from_payload({"pairwise": lib_full.pairwise, "conditional": [], "marginals": lib_full.marginals})
+        for v in nodes:
+            ps = list(dag.predecessors(v))
+            if len(ps) >= 2:
+                lib_vine.add_conditional("sachs", ConditionalSampler(child=v, parents=ps).fit(u_df))
+        generators = {
+            "learned_fitted_vine": build_node_specs(lib_vine, spec, compose=False)[1],
+            "learned_composed": build_node_specs(lib_full, spec, compose=True)[1],
+            "gaussian_copula_fitted": build_node_specs(lib_gauss, spec, compose=True)[1],
+            "baseline_fixed_rho": {v: NodeSpec(marginal=lib_full.get_marginal("sachs", v)) for v in nodes},
+        }
+        for label, specs in generators.items():
+            for calibrate in (False, True):
+                with warnings.catch_warnings():
+                    warnings.simplefilter("ignore")
+                    sampler = GraphSampler(dag, node_specs=specs, calibrate_margins=calibrate)
+                    gen = sampler.sample(n=n, seed=d)
+                    cg = run_pc(gen[nodes], indep_test="fisherz")
+                ks = [ks_2samp(gen[v], sachs[v]).statistic for v in nodes]
+                tau_err = []
+                for a, b in dag.edges:
+                    if dag.in_degree(b) == 1:
+                        lib = lib_gauss if label == "gaussian_copula_fitted" else lib_full
+                        target = lib.get_pairwise_entry("sachs", a, b)["tau"] if label != "baseline_fixed_rho" else 2 / np.pi * np.arcsin(0.5)
+                        tau_err.append(abs(kendalltau(gen[a], gen[b])[0] - target))
+                rows.append({
+                    "dag": d, "generator": label, "calibrated": calibrate, "n_edges": dag.number_of_edges(),
+                    "max_indegree": max(dict(dag.in_degree()).values()),
+                    "shd": structural_hamming_distance(dag, cg.G, nodes),
+                    **skeleton_scores(dag, cg.G, nodes),
+                    "mean_marginal_ks": float(np.mean(ks)), "max_marginal_ks": float(np.max(ks)),
+                    "indeg1_tau_abs_error": float(np.mean(tau_err)) if tau_err else np.nan,
+                    "n_drift_nodes": int(sum(1 for v in sampler.diagnostics_.values()
+                                             if v["n_parents"] and v["u_uniformity_ks"] > max(0.05, 1.95 / np.sqrt(n)))),
+                    "varsortability": varsortability(gen[nodes], dag),
+                    "fallback_draws": sampler.total_fallback_draws,
+                })
+        # reference: a linear-Gaussian SCM on the same DAG (Reisach et al. varsortability check)
+        w_rng = np.random.default_rng(5000 + d)
+        x = pd.DataFrame(index=range(n), columns=nodes, dtype=float)
+        for v in nx.topological_sort(dag):
+            x[v] = w_rng.normal(size=n)
+            for p in dag.predecessors(v):
+                x[v] += w_rng.choice([-1, 1]) * w_rng.uniform(0.5, 2.0) * x[p]
+        rows.append({"dag": d, "generator": "linear_gaussian_scm_reference", "calibrated": False,
+                     "n_edges": dag.number_of_edges(), "varsortability": varsortability(x, dag)})
+        print(f"  novel DAG {d} done ({dag.number_of_edges()} edges)")
+    return pd.DataFrame(rows)
+
+
+def summarize_novel(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
+    metrics = ["shd", "skeleton_f1", "mean_marginal_ks", "indeg1_tau_abs_error", "n_drift_nodes", "varsortability"]
+    rows = []
+    for (gen, cal), g in results.groupby(["generator", "calibrated"]):
+        row = {"generator": gen, "calibrated": cal, "n_dags": g["dag"].nunique()}
+        for m in metrics:
+            if m in g and g[m].notna().any():
+                lo, hi = bootstrap_ci(g[m].dropna())
+                row[m] = g[m].mean()
+                row[f"{m}_ci"] = f"[{lo:.3f}, {hi:.3f}]"
+        rows.append(row)
+    tests = []
+    uncal = results[(results.calibrated == False) & results.shd.notna()]  # noqa: E712
+    wide = uncal.pivot(index="dag", columns="generator", values="shd")
+    for other in ["learned_composed", "gaussian_copula_fitted", "baseline_fixed_rho"]:
+        if other in wide:
+            tests.append({"comparison": f"learned_fitted_vine - {other}", "metric": "shd",
+                          **paired_comparison(wide["learned_fitted_vine"], wide[other])})
+    return pd.DataFrame(rows), pd.DataFrame(tests)
+
+
+def main_rq5_only(out_dir, n_seeds: int = 30) -> None:
+    import json
+    from pathlib import Path
+
+    from gcda.provenance import write_metadata
+
+    out_dir = Path(out_dir)
+    rq5, info = cross_dataset_rq5(list(range(n_seeds)))
+    rq5.to_csv(out_dir / "rq5_cross_dataset.csv", index=False)
+    (out_dir / "rq5_cross_dataset_decisions.json").write_text(json.dumps(info, indent=2))
+    write_metadata(out_dir / "rq5_cross_dataset.csv")
+    print(rq5.describe().T[["mean", "std"]].round(4).to_string())
+
+
+def main(n_dags: int, n_seeds: int, out_dir, dag_start: int = 0) -> None:
+    import json
+    from pathlib import Path
+
+    from gcda.provenance import write_metadata
+
+    out_dir = Path(out_dir)
+    out_dir.mkdir(parents=True, exist_ok=True)
+    rq5, info = cross_dataset_rq5(list(range(min(n_seeds, 30))))
+    rq5.to_csv(out_dir / "rq5_cross_dataset.csv", index=False)
+    (out_dir / "rq5_cross_dataset_decisions.json").write_text(json.dumps(info, indent=2))
+    write_metadata(out_dir / "rq5_cross_dataset.csv")
+    print(rq5.describe().T[["mean", "std"]].round(4).to_string())
+
+    for obs in (False, True):
+        tag = "observational" if obs else "pooled"
+        res = novel_graph_study(n_dags, observational_only=obs, dag_start=dag_start)
+        summary, tests = summarize_novel(res)
+        for fname, frame in [(f"novel_dags_{tag}_per_dag.csv", res), (f"novel_dags_{tag}_summary.csv", summary),
+                             (f"novel_dags_{tag}_tests.csv", tests)]:
+            frame.to_csv(out_dir / fname, index=False)
+            write_metadata(out_dir / fname, n_dags=n_dags, sachs_rows=tag)
+        with pd.option_context("display.width", 250, "display.max_columns", 30):
+            print(f"--- novel DAGs ({tag}) ---")
+            print(summary.round(3).to_string(index=False))
+            print(tests.round(4).to_string(index=False))
diff --git a/gcda/experiments/discrete_native.py b/gcda/experiments/discrete_native.py
new file mode 100644
index 0000000..f3fb522
--- /dev/null
+++ b/gcda/experiments/discrete_native.py
@@ -0,0 +1,87 @@
+"""Ablation: jitter continuization vs. pyvinecopulib's native discrete copula likelihood.
+
+For every edge of Asia and Insurance, fit a bivariate copula on a training
+draw (a) to jittered pseudo-observations (the thesis' method) and (b) with
+var_types=("d","d"), i.e. the likelihood of the discrete data itself using
+F(x) and F(x-). Simulate from each fitted copula, map both coordinates back
+through the empirical discrete quantile function, and compare the
+dependence of the simulated pair to a held-out test draw (Cramer's V,
+Kendall's tau-b). This isolates the effect of jitter dilution.
+"""
+
+import warnings
+
+import numpy as np
+import pandas as pd
+import pyvinecopulib as pv
+from scipy.stats import kendalltau
+
+from gcda.data.datasets import load_asia, load_insurance
+from gcda.data.preprocessing import CategoricalMarginal, to_pseudo_observations_mixed
+from gcda.dependency.families import DEFAULT_BICOP_FAMILIES
+from gcda.evaluation.discrete import cramers_v
+from gcda.compat import bicop_sample
+
+
+def _cdf_pair(values, states):
+    m = CategoricalMarginal().fit(values, categories=states)
+    idx = np.array([states.index(v) for v in values])
+    upper = m.cum_probs_[idx]
+    lower = np.where(idx == 0, 0.0, m.cum_probs_[idx - 1])
+    return upper, lower, m
+
+
+def run(name, loader, n=10000, n_sim=10000):
+    train, dag, orders = loader(n, 0)
+    test, _, _ = loader(n, 1)
+    u_jit, _ = to_pseudo_observations_mixed(train, category_orders=orders, seed=0)
+    controls = pv.FitControlsBicop(family_set=DEFAULT_BICOP_FAMILIES, selection_criterion="bic")
+    rows = []
+    for a, b in dag.edges:
+        ua, la, ma = _cdf_pair(train[a].to_numpy(), list(orders[a]))
+        ub, lb, mb = _cdf_pair(train[b].to_numpy(), list(orders[b]))
+        jit = pv.Bicop()
+        jit.select(np.column_stack([u_jit[a], u_jit[b]]), controls)
+        nat = pv.Bicop(var_types=["d", "d"])
+        nat.select(np.column_stack([ua, ub, la, lb]), controls)
+        code_a = {s: i for i, s in enumerate(orders[a])}
+        code_b = {s: i for i, s in enumerate(orders[b])}
+        true_v = cramers_v(test[a], test[b])
+        true_t = kendalltau(test[a].map(code_a), test[b].map(code_b))[0]
+        row = {"network": name, "edge": f"{a}->{b}", "cramers_v_test": true_v, "tau_b_test": true_t}
+        for label, cop in [("jitter", jit), ("native", nat)]:
+            sim_cop = pv.Bicop(family=cop.family, rotation=cop.rotation, parameters=cop.parameters)
+            s = bicop_sample(sim_cop, n_sim, seeds=[11, 12, 13])
+            xa, xb = ma.inverse_transform(s[:, 0]), mb.inverse_transform(s[:, 1])
+            row[f"family_{label}"] = cop.family.name
+            row[f"cramers_v_{label}"] = cramers_v(xa, xb)
+            row[f"tau_b_{label}"] = kendalltau(pd.Series(xa).map(code_a), pd.Series(xb).map(code_b))[0]
+            row[f"cramers_v_abs_err_{label}"] = abs(row[f"cramers_v_{label}"] - true_v)
+            row[f"tau_b_abs_err_{label}"] = abs(row[f"tau_b_{label}"] - true_t)
+        rows.append(row)
+    return pd.DataFrame(rows)
+
+
+def main(out_dir) -> None:
+    from pathlib import Path
+
+    from gcda.experiments.common import paired_comparison
+    from gcda.provenance import write_metadata
+
+    out_dir = Path(out_dir)
+    out_dir.mkdir(parents=True, exist_ok=True)
+    with warnings.catch_warnings():
+        warnings.simplefilter("ignore")
+        res = pd.concat([run("asia", lambda n, s: load_asia(n, s)), run("insurance", lambda n, s: load_insurance(n, s))])
+    res.to_csv(out_dir / "discrete_native_vs_jitter.csv", index=False)
+    write_metadata(out_dir / "discrete_native_vs_jitter.csv")
+    summ = []
+    for net, g in res.groupby("network"):
+        for m in ("cramers_v", "tau_b"):
+            summ.append({"network": net, "metric": m, "mean_abs_err_jitter": g[f"{m}_abs_err_jitter"].mean(),
+                         "mean_abs_err_native": g[f"{m}_abs_err_native"].mean(),
+                         **paired_comparison(g[f"{m}_abs_err_native"], g[f"{m}_abs_err_jitter"])})
+    s = pd.DataFrame(summ)
+    s.to_csv(out_dir / "discrete_native_vs_jitter_summary.csv", index=False)
+    print(res[res.network == "asia"].round(3).to_string(index=False))
+    print(s.round(4).to_string(index=False))
diff --git a/gcda/experiments/learned_indegree.py b/gcda/experiments/learned_indegree.py
new file mode 100644
index 0000000..9b1ad94
--- /dev/null
+++ b/gcda/experiments/learned_indegree.py
@@ -0,0 +1,76 @@
+"""Learned (not baseline) multi-parent conditional vines at indegree 2-4 on held-out data.
+
+For every multi-parent node of Insurance (indegree 2-3) and Alarm (indegree
+2-4), a conditional vine is fitted on a training draw; the child is then
+sampled given the parents of an independent test draw, and the child-parent
+dependence (Cramer's V, tau) and the child's category frequencies are compared
+with the test data. Repeated over seeds for the test draw.
+"""
+
+import warnings
+
+import pandas as pd
+from scipy.stats import kendalltau
+
+from gcda.data.preprocessing import discrete_cdf_pairs, to_pseudo_observations_mixed
+from gcda.data.registry import load_dataset
+from gcda.dependency.conditional import ConditionalSampler
+from gcda.evaluation.discrete import cramers_v
+
+
+def main(out_dir, n_seeds: int = 10) -> None:
+    from pathlib import Path
+
+    from gcda.provenance import write_metadata
+
+    out_dir = Path(out_dir)
+    out_dir.mkdir(parents=True, exist_ok=True)
+    rows = []
+    for name in ("insurance", "alarm"):
+        train, dag, orders = load_dataset(name, n=10000, seed=10_000)
+        u_train, marg = to_pseudo_observations_mixed(train, category_orders=orders, seed=0)
+        up, lo, vt = discrete_cdf_pairs(train, marg)
+        fitted = {
+            "jitter": {v: ConditionalSampler(child=v, parents=list(dag.predecessors(v))).fit(u_train)
+                       for v in dag.nodes if dag.in_degree(v) >= 2},
+            "native": {v: ConditionalSampler(child=v, parents=list(dag.predecessors(v))).fit(up, lo, vt)
+                       for v in dag.nodes if dag.in_degree(v) >= 2},
+        }
+        for seed in range(min(n_seeds, 10)):
+          test, _, _ = load_dataset(name, n=10000, seed=seed)
+          u_test, _ = to_pseudo_observations_mixed(test, category_orders=orders, seed=seed)
+          # native mode conditions on the parents' latent uniforms: draw them from
+          # the parents' CDF rectangles [F(x-), F(x)] (randomized PIT)
+          import numpy as np
+          rng = np.random.default_rng(seed)
+          t_up, t_lo, _ = discrete_cdf_pairs(test, marg)
+          u_latent = t_lo + rng.uniform(size=t_lo.shape) * (t_up - t_lo)
+          for mode, samplers in fitted.items():
+            parents_u = u_test if mode == "jitter" else u_latent
+            for v, s in samplers.items():
+                with warnings.catch_warnings():
+                    warnings.simplefilter("ignore")
+                    u_child = s.sample(parents_u[s.parents].to_numpy(), seed=seed)
+                child = marg[v].inverse_transform(u_child)
+                codes = {c: i for i, c in enumerate(orders[v])}
+                for p in s.parents:
+                    pc = {c: i for i, c in enumerate(orders[p])}
+                    rows.append({
+                        "network": name, "seed": seed, "mode": mode, "child": v, "parent": p, "indegree": len(s.parents),
+                        "cramers_v_test": cramers_v(test[v], test[p]), "cramers_v_sim": cramers_v(child, test[p]),
+                        "tau_test": kendalltau(test[v].map(codes), test[p].map(pc))[0],
+                        "tau_sim": kendalltau(pd.Series(child).map(codes), test[p].map(pc))[0],
+                        "fallback_draws": s.last_fallback_count_,
+                    })
+        print(f"  {name} done")
+    res = pd.DataFrame(rows)
+    res["cramers_v_abs_err"] = (res.cramers_v_sim - res.cramers_v_test).abs()
+    res["tau_abs_err"] = (res.tau_sim - res.tau_test).abs()
+    res.to_csv(out_dir / "learned_indegree_per_edge.csv", index=False)
+    summ = res.groupby(["network", "mode", "indegree"]).agg(
+        n_edges=("parent", "size"), cramers_v_test=("cramers_v_test", "mean"),
+        cramers_v_abs_err=("cramers_v_abs_err", "mean"), tau_abs_err=("tau_abs_err", "mean"),
+        fallback_draws=("fallback_draws", "sum")).reset_index()
+    summ.to_csv(out_dir / "learned_indegree_summary.csv", index=False)
+    write_metadata(out_dir / "learned_indegree_summary.csv")
+    print(summ.round(4).to_string(index=False))
diff --git a/gcda/experiments/rq1.py b/gcda/experiments/rq1.py
new file mode 100644
index 0000000..f41bccd
--- /dev/null
+++ b/gcda/experiments/rq1.py
@@ -0,0 +1,62 @@
+"""RQ1 (quantitative): do strong fitted pairwise dependencies coincide with known causal edges?
+
+Ranks all 55 Sachs variable pairs by |tau| of the fitted pairwise copula and
+scores the ranking against the skeleton of the Sachs consensus network
+(bnlearn/pgmpy, 17 edges): AUROC (with the Mann-Whitney p-value),
+precision@k, and the rank of praf-pmek. Run on the pooled 7,466 rows and on
+the 853-row observational (CD3/CD28) condition.
+"""
+
+from itertools import combinations
+
+import numpy as np
+import pandas as pd
+from scipy.stats import mannwhitneyu
+from sklearn.metrics import roc_auc_score
+
+from gcda.data.datasets import load_sachs, sachs_consensus_dag
+from gcda.data.preprocessing import to_pseudo_observations
+from gcda.dependency.pairwise import build_pairwise_library
+
+
+def score(observational_only: bool) -> tuple[dict, pd.DataFrame]:
+    df = load_sachs(observational_only=observational_only)
+    u, _ = to_pseudo_observations(df)
+    entries = build_pairwise_library(u, "sachs", n_jobs=4)
+    skeleton = {frozenset(e) for e in sachs_consensus_dag().edges}
+    rows = [{"var_i": e["var_i"], "var_j": e["var_j"], "family": e["family"], "tau": e["tau"],
+             "abs_tau": abs(e["tau"]), "consensus_edge": frozenset((e["var_i"], e["var_j"])) in skeleton}
+            for e in entries if "error" not in e]
+    pairs = pd.DataFrame(rows).sort_values("abs_tau", ascending=False).reset_index(drop=True)
+    y, s = pairs["consensus_edge"].to_numpy(), pairs["abs_tau"].to_numpy()
+    k_true = int(y.sum())
+    res = {
+        "rows": len(df), "n_pairs": len(pairs), "n_consensus_edges": k_true,
+        "auroc": roc_auc_score(y, s),
+        "mannwhitney_p": mannwhitneyu(s[y], s[~y], alternative="greater").pvalue,
+        **{f"precision_at_{k}": float(y[:k].mean()) for k in (3, 5, 10, k_true)},
+        "random_precision": k_true / len(pairs),
+        "rank_praf_pmek": int(pairs.index[(pairs.var_i.isin(["praf", "pmek"])) & (pairs.var_j.isin(["praf", "pmek"]))][0]) + 1,
+    }
+    return res, pairs
+
+
+def main(out_dir) -> None:
+    from pathlib import Path
+
+    from gcda.provenance import write_metadata
+
+    out_dir = Path(out_dir)
+    out_dir.mkdir(parents=True, exist_ok=True)
+    summary = []
+    for obs in (False, True):
+        tag = "observational" if obs else "pooled"
+        res, pairs = score(obs)
+        summary.append({"data": tag, **res})
+        pairs.to_csv(out_dir / f"rq1_sachs_pairs_{tag}.csv", index=False)
+        print(f"--- {tag} ---")
+        print(pairs.head(10).to_string(index=False))
+    s = pd.DataFrame(summary)
+    s.to_csv(out_dir / "rq1_summary.csv", index=False)
+    write_metadata(out_dir / "rq1_summary.csv")
+    print(s.round(4).T.to_string())
diff --git a/gcda/experiments/rq2.py b/gcda/experiments/rq2.py
new file mode 100644
index 0000000..9adaa7b
--- /dev/null
+++ b/gcda/experiments/rq2.py
@@ -0,0 +1,64 @@
+"""RQ2 (held-out): does sampling the synthetic SCM's graph with learned models
+reproduce its per-edge dependence, marginals and joint distribution?
+
+The library is fitted on a training draw (seed 10,000) and every metric is
+computed against independent test draws (seeds 0..n-1). Reports per-edge
+|tau error|, marginal KS, and U-space energy distance / MMD (unbiased) with
+permutation p-values, for the fixed-rho baseline, the fitted Gaussian copula
+and the learned models.
+"""
+
+import numpy as np
+import pandas as pd
+from scipy.stats import kendalltau, ks_2samp
+
+from gcda.data.datasets import make_synthetic_scm
+from gcda.data.preprocessing import to_pseudo_observations
+from gcda.evaluation.realism import energy_distance, gaussian_mmd, permutation_test
+from gcda.experiments.common import GAUSSIAN_ONLY, baseline_specs, fit_graph_library, learned_specs, sample, summarize
+
+
+def main(out_dir, n_seeds: int = 30) -> None:
+    from pathlib import Path
+
+    from gcda.provenance import write_metadata
+
+    out_dir = Path(out_dir)
+    out_dir.mkdir(parents=True, exist_ok=True)
+    train, dag = make_synthetic_scm(n=5000, seed=10_000)
+    lib = fit_graph_library(train, dag, None, "synthetic_scm", all_pairs=True)
+    lib_g = fit_graph_library(train, dag, None, "synthetic_scm", family_set=GAUSSIAN_ONLY, all_pairs=True)
+    rows, edge_rows = [], []
+    for seed in range(n_seeds):
+        test, _ = make_synthetic_scm(n=5000, seed=seed)
+        tu, _ = to_pseudo_observations(test)
+        for label, specs in [("baseline_fixed_rho", baseline_specs(lib, "synthetic_scm", dag)),
+                             ("gaussian_copula_fitted", learned_specs(lib_g, "synthetic_scm", dag)),
+                             ("learned", learned_specs(lib, "synthetic_scm", dag))]:
+            gen, _ = sample(dag, specs, 5000, seed + 500)
+            gu, _ = to_pseudo_observations(gen)
+            errs = {f"{a}->{b}": abs(kendalltau(gen[a], gen[b])[0] - kendalltau(test[a], test[b])[0]) for a, b in dag.edges}
+            for e, v in errs.items():
+                edge_rows.append({"seed": seed, "source": label, "edge": e, "tau_abs_error": v})
+            do_perm = seed < 10  # permutation tests are O(n_perm * max_n^2): first 10 seeds only
+            row = {"seed": seed, "source": label, "mean_edge_tau_abs_error": np.mean(list(errs.values())),
+                   "mean_marginal_ks": np.mean([ks_2samp(gen[c], test[c]).statistic for c in test.columns]),
+                   "energy_distance": energy_distance(tu.to_numpy(), gu.to_numpy(), unbiased=True),
+                   "gaussian_mmd": gaussian_mmd(tu.to_numpy(), gu.to_numpy(), unbiased=True)}
+            if do_perm:
+                row["energy_p"] = permutation_test(energy_distance, tu.to_numpy(), gu.to_numpy(), n_permutations=200)["p_value"]
+                row["mmd_p"] = permutation_test(gaussian_mmd, tu.to_numpy(), gu.to_numpy(), n_permutations=200)["p_value"]
+            rows.append(row)
+        print(f"  rq2 seed {seed} done")
+    res, edges = pd.DataFrame(rows), pd.DataFrame(edge_rows)
+    res.to_csv(out_dir / "rq2_heldout_per_seed.csv", index=False)
+    edges.to_csv(out_dir / "rq2_heldout_edges.csv", index=False)
+    summ = pd.concat([summarize(res, ["source"], m).assign(metric=m) for m in
+                      ["mean_edge_tau_abs_error", "mean_marginal_ks", "energy_distance", "gaussian_mmd"]])
+    p = res.groupby("source")[["energy_p", "mmd_p"]].agg(lambda x: float((x.dropna() < 0.05).mean()))
+    summ.to_csv(out_dir / "rq2_heldout_summary.csv", index=False)
+    p.to_csv(out_dir / "rq2_heldout_rejection_rates.csv")
+    write_metadata(out_dir / "rq2_heldout_summary.csv", n_seeds=n_seeds, train_seed=10_000)
+    print(summ.round(4).to_string(index=False))
+    print("fraction of seeds where the permutation test rejects equality at 5%:\n", p.round(3).to_string())
+    print(edges.groupby(["edge", "source"]).tau_abs_error.mean().unstack().round(4).to_string())
diff --git a/gcda/experiments/rq4.py b/gcda/experiments/rq4.py
new file mode 100644
index 0000000..3d05384
--- /dev/null
+++ b/gcda/experiments/rq4.py
@@ -0,0 +1,85 @@
+"""RQ4 (held-out, multi-seed): reconstruct discrete / mixed networks.
+
+Library fitted once on a training draw (seed 10,000); each evaluation seed
+draws independent true data. Sources: fixed-rho baseline (real marginals),
+learned with jittered discrete columns (thesis method), learned with the
+native discrete likelihood, the same two with margin calibration, and CPT
+refitting. Metrics: mean category-frequency TVD over nodes, mean |Cramer's V
+error| and |NMI error| over the true edges, fallback draws.
+"""
+
+import pandas as pd
+
+from gcda.data.registry import load_dataset
+from gcda.evaluation.discrete import compare_category_frequencies, compare_discrete_dependence
+from gcda.experiments.common import (
+    baseline_specs, cpt_refit_sample, fit_graph_library, learned_specs, paired_comparison, sample, summarize,
+)
+
+TRAIN_SEED = 10_000
+
+
+def run_network(name: str, seeds: list[int], n: int = 10000) -> pd.DataFrame:
+    train, dag, orders = load_dataset(name, n=n, seed=TRAIN_SEED)
+    lib_j = fit_graph_library(train, dag, orders, name, discrete_mode="jitter")
+    lib_n = fit_graph_library(train, dag, orders, name, discrete_mode="native")
+    discrete_cols = [c for c in dag.nodes if orders and c in orders]
+    rows = []
+    for seed in seeds:
+        true, _, _ = load_dataset(name, n=n, seed=seed)
+        sources = {
+            "baseline_fixed_rho": sample(dag, baseline_specs(lib_j, name, dag), n, seed)[0],
+            "learned_jitter": sample(dag, learned_specs(lib_j, name, dag), n, seed)[0],
+            "learned_native": sample(dag, learned_specs(lib_n, name, dag), n, seed)[0],
+            "learned_native_calibrated": sample(dag, learned_specs(lib_n, name, dag), n, seed, calibrate=True)[0],
+            "baseline_calibrated": sample(dag, baseline_specs(lib_j, name, dag), n, seed, calibrate=True)[0],
+        }
+        if len(discrete_cols) == len(dag.nodes):
+            sources["cpt_refit"] = cpt_refit_sample(train, dag, n, seed)
+        edges = [e for e in dag.edges if e[0] in discrete_cols and e[1] in discrete_cols]
+        for label, sim in sources.items():
+            freq = compare_category_frequencies(true[discrete_cols], sim[discrete_cols])
+            dep = compare_discrete_dependence(true, sim, pairs=edges) if edges else pd.DataFrame()
+            rows.append({
+                "network": name, "seed": seed, "source": label,
+                "mean_tvd": freq["total_variation_distance"].mean(),
+                "mean_cramers_v_abs_err": dep["cramers_v_abs_error"].mean() if len(dep) else float("nan"),
+                "mean_nmi_abs_err": dep["nmi_abs_error"].mean() if len(dep) else float("nan"),
+            })
+        print(f"  rq4 {name} seed {seed} done")
+    return pd.DataFrame(rows)
+
+
+def main(out_dir, networks: list[str], n_seeds: int, seed_start: int = 0) -> None:
+    from pathlib import Path
+
+    out_dir = Path(out_dir)
+    out_dir.mkdir(parents=True, exist_ok=True)
+    seeds = list(range(seed_start, seed_start + n_seeds))
+    res = pd.concat([run_network(nw, seeds) for nw in networks], ignore_index=True)
+    write_outputs(res, out_dir, networks=networks, seeds=seeds, train_seed=TRAIN_SEED)
+
+
+def write_outputs(res: pd.DataFrame, out_dir, **meta) -> None:
+    from pathlib import Path
+
+    from gcda.provenance import write_metadata
+
+    out_dir = Path(out_dir)
+    summ = pd.concat([summarize(res, ["network", "source"], m).assign(metric=m)
+                      for m in ["mean_tvd", "mean_cramers_v_abs_err", "mean_nmi_abs_err"]])
+    tests = []
+    for nw, g in res.groupby("network"):
+        for m in ["mean_tvd", "mean_cramers_v_abs_err"]:
+            w = g.pivot(index="seed", columns="source", values=m)
+            for other in ["learned_jitter", "baseline_fixed_rho", "cpt_refit"]:
+                if other in w and "learned_native" in w:
+                    tests.append({"network": nw, "metric": m, "comparison": f"learned_native - {other}",
+                                  **paired_comparison(w["learned_native"], w[other])})
+    tests = pd.DataFrame(tests)
+    for fname, frame in [("rq4_heldout_per_seed.csv", res), ("rq4_heldout_summary.csv", summ), ("rq4_heldout_tests.csv", tests)]:
+        frame.to_csv(out_dir / fname, index=False)
+        write_metadata(out_dir / fname, **meta)
+    with pd.option_context("display.width", 220):
+        print(summ.round(4).to_string(index=False))
+        print(tests.round(4).to_string(index=False))
diff --git a/gcda/experiments/rq6.py b/gcda/experiments/rq6.py
new file mode 100644
index 0000000..b8672bd
--- /dev/null
+++ b/gcda/experiments/rq6.py
@@ -0,0 +1,129 @@
+"""RQ6 (held-out, multi-seed): is the generated data usable by a structure-learning algorithm?
+
+Changes relative to the thesis' original protocol (scripts/evaluate_causal_discovery.py):
+  * held-out: the dependency library is fitted ONCE on a training draw
+    (seed TRAIN_SEED) that is disjoint from every evaluation seed; the
+    original protocol re-used the library's own training data for seed 1;
+  * more seeds (default 30) and four graphs (synthetic SCM, Asia, Insurance, Alarm);
+  * stronger baselines: besides the fixed rho=0.5 Gaussian baseline, a
+    *fitted* Gaussian copula (same pipeline, Gaussian/independence families
+    only) and, for discrete networks, CPT refitting by maximum likelihood;
+  * learned_native: discrete columns fitted with the native discrete copula
+    likelihood instead of jittering (discrete graphs only);
+  * statistics: bootstrap 95% CIs and paired Wilcoxon / t-tests per pair of
+    sources, plus skeleton precision/recall/F1 and number of edges found.
+"""
+
+import time
+import warnings
+
+import numpy as np
+import pandas as pd
+
+from gcda.data.registry import load_dataset
+from gcda.evaluation.causal_discovery import encode_categorical, run_ges, run_pc, structural_hamming_distance
+from gcda.experiments.common import (
+    GAUSSIAN_ONLY,
+    baseline_specs,
+    cpt_refit_sample,
+    fit_graph_library,
+    learned_specs,
+    paired_comparison,
+    sample,
+    skeleton_scores,
+    summarize,
+)
+
+TRAIN_SEED = 10_000
+GRAPHS = {
+    "synthetic_scm": {"n": 5000, "test": "fisherz", "discrete": False},
+    "asia": {"n": 8000, "test": "chisq", "discrete": True},
+    "insurance": {"n": 8000, "test": "chisq", "discrete": True},
+    "alarm": {"n": 8000, "test": "chisq", "discrete": True},
+}
+
+
+def run_graph(name: str, seeds: list[int], alpha: float = 0.05, n_jobs: int = 4, algorithm: str = "pc") -> pd.DataFrame:
+    cfg = GRAPHS[name]
+    train_df, dag, orders = load_dataset(name, n=cfg["n"], seed=TRAIN_SEED)
+    t0 = time.time()
+    lib_full = fit_graph_library(train_df, dag, orders, name, n_jobs=n_jobs)
+    lib_gauss = fit_graph_library(train_df, dag, orders, name, family_set=GAUSSIAN_ONLY, n_jobs=n_jobs)
+    lib_native = fit_graph_library(train_df, dag, orders, name, n_jobs=n_jobs, discrete_mode="native") if cfg["discrete"] else None
+    fit_seconds = time.time() - t0
+    nodes = list(dag.nodes)
+    rows = []
+    for seed in seeds:
+        true_df, _, _ = load_dataset(name, n=cfg["n"], seed=seed)
+        true_df = true_df[nodes]
+        sources = {"true_data": true_df}
+        sources["baseline_fixed_rho"], _ = sample(dag, baseline_specs(lib_full, name, dag), cfg["n"], seed)
+        sources["gaussian_copula_fitted"], _ = sample(dag, learned_specs(lib_gauss, name, dag), cfg["n"], seed)
+        sources["learned"], learned_sampler = sample(dag, learned_specs(lib_full, name, dag), cfg["n"], seed)
+        if cfg["discrete"]:
+            sources["learned_native"], _ = sample(dag, learned_specs(lib_native, name, dag), cfg["n"], seed)
+            sources["cpt_refit"] = cpt_refit_sample(train_df, dag, cfg["n"], seed)
+        for label, df in sources.items():
+            data = encode_categorical(df[nodes], orders) if cfg["discrete"] else df[nodes]
+            with warnings.catch_warnings():
+                warnings.simplefilter("ignore")
+                if algorithm == "pc":
+                    cg = run_pc(data, indep_test=cfg["test"], alpha=alpha)
+                else:
+                    cg = run_ges(data, discrete=cfg["discrete"])
+            rows.append({
+                "graph": name, "seed": seed, "source": label, "alpha": alpha, "algorithm": algorithm,
+                "shd": structural_hamming_distance(dag, cg.G, nodes),
+                **skeleton_scores(dag, cg.G, nodes),
+                "true_edges": dag.number_of_edges(),
+                "fallback_draws": learned_sampler.total_fallback_draws if label == "learned" else 0,
+                "library_fit_seconds": fit_seconds,
+            })
+        print(f"  {name} seed {seed} done")
+    return pd.DataFrame(rows)
+
+
+def analyse(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
+    summary = []
+    for metric in ["shd", "n_edges_found", "skeleton_f1"]:
+        s = summarize(results, ["graph", "source"], metric)
+        s.insert(2, "metric", metric)
+        summary.append(s)
+    summary = pd.concat(summary, ignore_index=True)
+
+    tests = []
+    for graph, g in results.groupby("graph"):
+        wide = g.pivot(index="seed", columns="source", values="shd")
+        for other in [c for c in wide.columns if c != "learned"]:
+            res = paired_comparison(wide["learned"], wide[other])
+            tests.append({"graph": graph, "comparison": f"learned - {other}", "metric": "shd", **res})
+    return summary, pd.DataFrame(tests)
+
+
+def write_outputs(results: pd.DataFrame, out_dir, **meta) -> None:
+    from pathlib import Path
+
+    from gcda.provenance import write_metadata
+
+    out_dir = Path(out_dir)
+    summary, tests = analyse(results)
+    for fname, frame in [("rq6_heldout_per_seed.csv", results), ("rq6_heldout_summary.csv", summary),
+                         ("rq6_heldout_tests.csv", tests)]:
+        frame.to_csv(out_dir / fname, index=False)
+        write_metadata(out_dir / fname, **meta)
+    with pd.option_context("display.width", 200):
+        print(summary[summary.metric == "shd"].round(3).to_string(index=False))
+        print(tests.round(4).to_string(index=False))
+
+
+def main(graphs: list[str], n_seeds: int, out_dir, alpha: float = 0.05, seed_start: int = 0,
+         algorithm: str = "pc") -> None:
+    from pathlib import Path
+
+    from gcda.provenance import write_metadata
+
+    out_dir = Path(out_dir)
+    out_dir.mkdir(parents=True, exist_ok=True)
+    seeds = list(range(seed_start, seed_start + n_seeds))
+    results = pd.concat([run_graph(g, seeds, alpha=alpha, algorithm=algorithm) for g in graphs], ignore_index=True)
+    write_outputs(results, out_dir, graphs=graphs, seeds=seeds, train_seed=TRAIN_SEED, alpha=alpha, algorithm=algorithm)
diff --git a/gcda/experiments/sweep.py b/gcda/experiments/sweep.py
new file mode 100644
index 0000000..cdf1dd1
--- /dev/null
+++ b/gcda/experiments/sweep.py
@@ -0,0 +1,209 @@
+"""T6c/T7: sweep key hyperparameters and log metrics (optionally to W&B).
+
+Sweeps (all read from configs/sweep.yaml):
+  1. dependency-model sweep: copula family set x AIC/BIC x dataset, for one
+     multi-parent conditional target per dataset (Table 6.1);
+  2. indegree-cap sweep: GraphSampler's Gaussian baseline at 2..K parents,
+     repeated over several seeds, with the theoretical tau as reference
+     (Table 6.2);
+  3. clipping-epsilon sweep: the stability guard's epsilon (task T6c
+     "clipping/fallback settings"), recording fallback draws and accuracy.
+"""
+
+import os
+import time
+from itertools import chain, product
+from pathlib import Path
+
+import networkx as nx
+import numpy as np
+import pandas as pd
+import pyvinecopulib as pv
+import yaml
+from scipy.stats import kendalltau
+
+from gcda.data.preprocessing import handle_missing_values, to_pseudo_observations_mixed
+from gcda.data.registry import load_dataset
+from gcda.dependency.conditional import EPS, ConditionalSampler
+from gcda.evaluation.realism import compare_pairwise_dependence, energy_distance, gaussian_mmd
+from gcda.generation.graph_sampler import GraphSampler, valid_baseline_rho
+
+WANDB_PROJECT = "graph-conditioned-augmentation"
+REPO_ROOT = Path(__file__).resolve().parents[2]
+DEFAULT_CONFIG_PATH = REPO_ROOT / "configs" / "sweep.yaml"
+OUTPUT_DIR = REPO_ROOT / "outputs"
+
+# sample sizes used by the sweep (kept from the thesis runs for exact reproducibility)
+SWEEP_N = {"synthetic_scm": 5000, "asia": 8000, "insurance": 8000}
+SWEEP_SEED = {"synthetic_scm": 1, "asia": 0, "insurance": 0}
+
+
+def load_config(path: Path) -> dict:
+    config = yaml.safe_load(Path(path).read_text())
+    config["family_sets"] = {
+        name: [getattr(pv.BicopFamily, family) for family in families]
+        for name, families in config["family_sets"].items()
+    }
+    return config
+
+
+def _prepare(dataset_name: str) -> pd.DataFrame:
+    df, _dag, category_orders = load_dataset(dataset_name, n=SWEEP_N.get(dataset_name), seed=SWEEP_SEED.get(dataset_name))
+    clean, _ = handle_missing_values(df, strategy="drop")
+    u_df, _ = to_pseudo_observations_mixed(clean, category_orders=category_orders, seed=0)
+    return u_df
+
+
+def _evaluate_sampler(sampler: ConditionalSampler, u_df: pd.DataFrame, child: str, parents: list[str]) -> dict:
+    columns = [child, *parents]
+    u_sim = sampler.sample(u_df[parents].to_numpy(), seed=0)
+    sim_u_df = u_df[parents].copy()
+    sim_u_df[child] = u_sim
+    dep = compare_pairwise_dependence(u_df[columns], sim_u_df[columns], pairs=[(child, p) for p in parents])
+    data_np, sim_np = u_df[columns].to_numpy(), sim_u_df[columns].to_numpy()
+    return {
+        "mean_tau_abs_error": dep["tau_abs_error"].mean(),
+        "energy_distance": energy_distance(data_np, sim_np),
+        "gaussian_mmd": gaussian_mmd(data_np, sim_np),
+        "n_fallback": sampler.last_fallback_count_,
+    }
+
+
+def run_dependency_sweep(config: dict, use_wandb: bool = False) -> pd.DataFrame:
+    targets = config["targets"]
+    family_sets = config["family_sets"]
+    rows = []
+    for dataset_name, family_set_name, criterion in product(targets, family_sets, config["selection_criteria"]):
+        print(f"  {dataset_name} / {family_set_name} / {criterion}")
+        u_df = _prepare(dataset_name)
+        child, parents = targets[dataset_name]["child"], targets[dataset_name]["parents"]
+        sampler = ConditionalSampler(
+            child=child, parents=parents, family_set=family_sets[family_set_name], selection_criterion=criterion,
+        ).fit(u_df)
+        data_np = u_df[[child, *parents]].to_numpy()
+        vine = sampler.vine_
+        metrics = {
+            "dataset": dataset_name,
+            "family_set": family_set_name,
+            "selection_criterion": criterion,
+            "child": child,
+            "parents": ",".join(parents),
+            "n": len(u_df),
+            "vine_aic": vine.aic(data_np),
+            "vine_bic": vine.bic(data_np),
+            "families_selected": ",".join(f.name for f in chain.from_iterable(vine.families)),
+            **_evaluate_sampler(sampler, u_df, child, parents),
+            "clip_eps": EPS,
+        }
+        rows.append(metrics)
+        if use_wandb:
+            import wandb
+            wandb.log(metrics)
+    return pd.DataFrame(rows)
+
+
+def run_indegree_sweep(config: dict, use_wandb: bool = False) -> pd.DataFrame:
+    """Baseline Gaussian sampler at increasing indegree caps.
+
+    The per-parent correlation is capped by `valid_baseline_rho` so the
+    baseline stays a valid (positive-definite) model at every cap; the
+    theoretical tau = 2/pi * arcsin(rho_eff) is reported alongside. Each cap is
+    repeated `repeats` times with seeds seed, seed+1, ... (repeat 0 uses the
+    original seed, so its row equals the thesis' single run for caps 2-3).
+    """
+    spec = config["indegree_sweep"]
+    rho, n, seed, repeats = spec["baseline_rho"], spec["n"], spec["seed"], spec.get("repeats", 1)
+    rows = []
+    for cap in spec["caps"]:
+        parents = [f"P{i}" for i in range(cap)]
+        dag = nx.DiGraph()
+        dag.add_nodes_from([*parents, "X"])
+        dag.add_edges_from([(p, "X") for p in parents])
+        rho_eff = valid_baseline_rho(cap, rho)
+        for r in range(repeats):
+            print(f"  indegree_cap={cap} repeat={r}")
+            t0 = time.perf_counter()
+            sampler = GraphSampler(dag, max_indegree=cap, baseline_rho=rho)
+            df = sampler.sample(n=n, seed=seed + r)
+            elapsed = time.perf_counter() - t0
+            taus = [kendalltau(df[p], df["X"])[0] for p in parents]
+            metrics = {
+                "indegree_cap": cap,
+                "repeat": r,
+                "seed": seed + r,
+                "baseline_rho": rho,
+                "rho_effective": rho_eff,
+                "tau_theoretical": float(2 / np.pi * np.arcsin(rho_eff)),
+                "mean_tau": float(np.mean(taus)),
+                "min_tau": float(np.min(taus)),
+                "max_tau": float(np.max(taus)),
+                "elapsed_sec": elapsed,
+                "fallback_draws": sampler.total_fallback_draws,
+                "clip_eps": EPS,
+            }
+            rows.append(metrics)
+            if use_wandb:
+                import wandb
+                wandb.log(metrics)
+    return pd.DataFrame(rows)
+
+
+def run_clip_sweep(config: dict, use_wandb: bool = False) -> pd.DataFrame:
+    """Vary the clipping epsilon of the conditional sampler (T6c)."""
+    spec = config.get("clip_sweep")
+    if not spec:
+        return pd.DataFrame()
+    targets = config["targets"]
+    rows = []
+    for dataset_name in spec["datasets"]:
+        u_df = _prepare(dataset_name)
+        child, parents = targets[dataset_name]["child"], targets[dataset_name]["parents"]
+        for eps in spec["eps_values"]:
+            print(f"  clip sweep {dataset_name} eps={eps}")
+            sampler = ConditionalSampler(child=child, parents=parents, clip_eps=float(eps)).fit(u_df)
+            metrics = {"dataset": dataset_name, "clip_eps": float(eps), **_evaluate_sampler(sampler, u_df, child, parents)}
+            rows.append(metrics)
+            if use_wandb:
+                import wandb
+                wandb.log(metrics)
+    return pd.DataFrame(rows)
+
+
+def main(config_path: Path = DEFAULT_CONFIG_PATH, use_wandb: bool = False, output_dir: Path = OUTPUT_DIR) -> None:
+    from gcda.provenance import write_metadata
+
+    config = load_config(config_path)
+    if use_wandb:
+        import wandb
+        wandb.init(
+            project=WANDB_PROJECT, name="hyperparameter-sweep",
+            mode=os.environ.get("WANDB_MODE", "offline"),
+            config={"config_file": str(config_path), **yaml.safe_load(Path(config_path).read_text())},
+        )
+
+    print("Dependency-model sweep (family set x AIC/BIC x dataset):")
+    dep_results = run_dependency_sweep(config, use_wandb=use_wandb)
+    print("\nIndegree-cap sweep:")
+    indegree_results = run_indegree_sweep(config, use_wandb=use_wandb)
+    print("\nClipping-epsilon sweep:")
+    clip_results = run_clip_sweep(config, use_wandb=use_wandb)
+
+    output_dir = Path(output_dir)
+    output_dir.mkdir(parents=True, exist_ok=True)
+    for name, frame in [("sweep_dependency_models.csv", dep_results), ("sweep_indegree_cap.csv", indegree_results),
+                        ("sweep_clip_eps.csv", clip_results)]:
+        frame.to_csv(output_dir / name, index=False)
+        write_metadata(output_dir / name, config_file=str(config_path))
+
+    print("\n=== dependency-model sweep results ===")
+    print(dep_results.drop(columns=["parents", "families_selected"]).to_string(index=False))
+    print("\n=== indegree-cap sweep results (mean over repeats) ===")
+    print(indegree_results.groupby("indegree_cap")[["rho_effective", "tau_theoretical", "mean_tau", "elapsed_sec"]].mean().to_string())
+    if not clip_results.empty:
+        print("\n=== clipping-epsilon sweep ===")
+        print(clip_results.to_string(index=False))
+    print(f"\nSaved results to {output_dir}/")
+
+    if use_wandb:
+        import wandb
+        wandb.finish()
diff --git a/gcda/generation/graph_sampler.py b/gcda/generation/graph_sampler.py
index 14daec0..49876d7 100644
--- a/gcda/generation/graph_sampler.py
+++ b/gcda/generation/graph_sampler.py
@@ -1,50 +1,64 @@
-"""T5: sample an n x p continuous dataset for a user-specified DAG.
+"""T5: sample an n x p dataset for a user-specified DAG.
 
 Building blocks come from the T4 dependency library:
-  - indegree 0 (root): draw from a marginal (a learned `EmpiricalMarginal`,
-    or a standard-normal baseline if none is supplied).
+  - indegree 0 (root): draw U(0,1) and map through a marginal (a learned
+    marginal, or a standard-normal baseline if none is supplied).
   - indegree 1: sample the child conditional on its parent using a fitted
     `pv.Bicop` (from the T4 pairwise library, or a baseline Gaussian copula)
-    via its h-function inverse (verified against Clayton's known conditional
-    distribution before writing this module - see hinv1/hinv2 usage below).
-  - indegree 2 (core; 3-4 as an extension): sample via a T4 `ConditionalSampler`
-    vine, or a baseline Gaussian one if none is supplied.
+    via its h-function inverse.
+  - indegree >= 2: sample via a T4 `ConditionalSampler` vine fitted for that
+    exact parent set, or via a `PairwiseProductConditional` composed from the
+    per-edge pairwise copulas, or a baseline Gaussian vine if neither is given.
 
 Every node's sampling step is wrapped in a try/except: on failure (or any
-non-finite output) it logs a warning and falls back to an independent
-U(0,1) draw for that node, so one bad edge cannot break the whole graph.
+non-finite output) it emits a `FallbackWarning` and falls back to an
+independent U(0,1) draw. Fallback draws are counted per node in
+``GraphSampler.fallback_counts_`` and summarized in ``diagnostics_``.
 """
 
 import warnings
-from dataclasses import dataclass
+from dataclasses import dataclass, field
 
 import networkx as nx
 import numpy as np
 import pandas as pd
 import pyvinecopulib as pv
-from scipy.stats import norm
+from scipy.stats import kstest, norm, rankdata
 
 from gcda.data.preprocessing import EmpiricalMarginal
-from gcda.dependency.conditional import EPS, ConditionalSampler
+from gcda.dependency.composed import PairwiseProductConditional
+from gcda.dependency.conditional import EPS, ConditionalSampler, FallbackWarning
 from gcda.dependency.library import DependencyLibrary
 
 CORE_MAX_INDEGREE = 2
 DEFAULT_BASELINE_RHO = 0.5
 
 
+class MarginalDriftWarning(UserWarning):
+    """A node's generated U-values are far from uniform, so mapping them through
+    the stored marginal will NOT reproduce that marginal. Typical cause: a
+    multi-parent model whose implied parent dependence differs from the
+    dependence of the parents actually generated in this graph."""
+
+
 @dataclass
 class EdgeModel:
     """How to sample a node given its parent(s)."""
 
     bicop: pv.Bicop | None = None  # used when the node has exactly 1 parent
     bicop_parent_is_first: bool = True  # column convention of `bicop` (see hinv1/hinv2 below)
-    conditional_sampler: ConditionalSampler | None = None  # used when the node has >= 2 parents
+    conditional_sampler: ConditionalSampler | PairwiseProductConditional | None = None  # >= 2 parents
+    # graph-node names of the parents, in the column order `conditional_sampler` expects;
+    # None -> use the sampler's own `parents` attribute if it matches, else the DAG's order
+    parent_order: list[str] | None = None
+    source: str = "learned"
 
 
 @dataclass
 class NodeSpec:
     marginal: EmpiricalMarginal | None = None  # None -> standard-normal baseline marginal
     edge_model: EdgeModel | None = None  # None -> baseline Gaussian dependence
+    notes: list[str] = field(default_factory=list)
 
 
 def baseline_marginal() -> EmpiricalMarginal:
@@ -61,77 +75,162 @@ def baseline_bicop(rho: float = DEFAULT_BASELINE_RHO) -> pv.Bicop:
     return pv.Bicop(family=pv.BicopFamily.gaussian, parameters=np.array([[rho]]))
 
 
+def valid_baseline_rho(n_parents: int, rho: float = DEFAULT_BASELINE_RHO) -> float:
+    """Largest per-parent correlation <= `rho` that keeps the baseline valid.
+
+    The baseline puts correlation rho between the child and each of k mutually
+    independent parents; that correlation matrix is positive definite only if
+    k * rho^2 < 1. With rho = 0.5 this fails at k = 4 (singular: the child
+    becomes a deterministic function of its parents) and k >= 5 (not PSD).
+    We cap k * rho^2 at 0.9. For k <= 3 and rho = 0.5 the value is unchanged,
+    so every result produced before this guard was added is unaffected.
+    """
+    return float(min(rho, np.sqrt(0.9 / max(n_parents, 1))))
+
+
 def _fit_baseline_conditional_sampler(
     child: str, parents: list[str], rng: np.random.Generator,
-    rho: float = DEFAULT_BASELINE_RHO, n_fit: int = 4000,
+    rho: float = DEFAULT_BASELINE_RHO, n_fit: int = 4000, clip_eps: float = EPS,
 ) -> ConditionalSampler:
     """Simple baseline dependence for a multi-parent edge: a Gaussian vine
     with each parent correlated `rho` with the child (T5c.i)."""
     dim = len(parents) + 1
+    rho = valid_baseline_rho(len(parents), rho)
     corr = np.eye(dim)
     for i in range(len(parents)):
         corr[0, i + 1] = corr[i + 1, 0] = rho
     z = rng.multivariate_normal(np.zeros(dim), corr, size=n_fit)
     u = pd.DataFrame(norm.cdf(z), columns=[child, *parents])
-    return ConditionalSampler(child=child, parents=parents, family_set=[pv.BicopFamily.gaussian]).fit(u)
+    return ConditionalSampler(
+        child=child, parents=parents, family_set=[pv.BicopFamily.gaussian], clip_eps=clip_eps
+    ).fit(u)
 
 
 class GraphSampler:
-    """Samples an n x p dataset for a DAG, using pairwise/conditional copula models as edge building blocks."""
+    """Samples an n x p dataset for a DAG, using pairwise/conditional copula models as edge building blocks.
+
+    Parameters beyond the DAG and node specs:
+      max_indegree      reject DAGs with more parents per node than this.
+      baseline_rho      correlation used by the Gaussian baseline (capped per
+                        `valid_baseline_rho` for many parents).
+      clip_eps          U-values are kept inside [clip_eps, 1 - clip_eps].
+      calibrate_margins if True, each non-root node's U column is replaced by
+                        its normalized ranks before it is used downstream and
+                        mapped through its marginal. Ranks (and hence the
+                        generated copula) are unchanged, but the node's
+                        marginal is reproduced exactly even when its
+                        conditional model is not "compatible" with the parent
+                        distribution generated in this graph.
+      drift_tolerance   KS distance of a node's U column from U(0,1) above which
+                        a MarginalDriftWarning is emitted (uncalibrated mode).
+    """
 
     def __init__(
         self,
         dag: nx.DiGraph,
         node_specs: dict[str, NodeSpec] | None = None,
         max_indegree: int = CORE_MAX_INDEGREE,
+        baseline_rho: float = DEFAULT_BASELINE_RHO,
+        clip_eps: float = EPS,
+        calibrate_margins: bool = False,
+        drift_tolerance: float = 0.05,
     ):
         if not nx.is_directed_acyclic_graph(dag):
             raise ValueError("graph must be a DAG")
         too_many = {node: d for node, d in dag.in_degree() if d > max_indegree}
         if too_many:
             raise ValueError(f"nodes exceed max indegree {max_indegree}: {too_many}")
+        if not 0 < clip_eps < 0.5:
+            raise ValueError("clip_eps must be in (0, 0.5)")
 
         self.dag = dag
         self.max_indegree = max_indegree
+        self.baseline_rho = baseline_rho
+        self.clip_eps = clip_eps
+        self.calibrate_margins = calibrate_margins
+        self.drift_tolerance = drift_tolerance
         self.node_specs = {node: NodeSpec() for node in dag.nodes}
         if node_specs:
+            unknown = set(node_specs) - set(dag.nodes)
+            if unknown:
+                raise ValueError(f"node_specs given for nodes not in the DAG: {sorted(unknown)}")
             self.node_specs.update(node_specs)
+        self.fallback_counts_: dict[str, int] = {}
+        self.diagnostics_: dict[str, dict] = {}
 
     def sample(self, n: int, seed: int | None = None) -> pd.DataFrame:
         rng = np.random.default_rng(seed)
+        eps = self.clip_eps
         u_values: dict[str, np.ndarray] = {}
+        self.fallback_counts_ = {node: 0 for node in self.dag.nodes}
+        self.diagnostics_ = {}
 
         for node in nx.topological_sort(self.dag):
             parents = list(self.dag.predecessors(node))
             spec = self.node_specs[node]
+            kind = "root" if not parents else (spec.edge_model.source if spec.edge_model else "baseline")
             try:
                 if not parents:
-                    u_node = rng.uniform(EPS, 1 - EPS, size=n)
+                    u_node = rng.uniform(eps, 1 - eps, size=n)
                 elif len(parents) == 1:
                     u_node = self._sample_indegree1(parents[0], u_values, spec, rng, n)
                 else:
                     u_node = self._sample_indegree_k(node, parents, u_values, spec, rng, n)
+                    sampler_fallbacks = getattr(self._last_sampler, "last_fallback_count_", 0)
+                    self.fallback_counts_[node] += int(sampler_fallbacks)
             except Exception as exc:  # noqa: BLE001 - one bad node must not break the whole graph
-                warnings.warn(f"sampling node {node!r} failed ({exc!r}); falling back to an independent draw")
-                u_node = rng.uniform(EPS, 1 - EPS, size=n)
+                warnings.warn(f"sampling node {node!r} failed ({exc!r}); falling back to an independent draw", FallbackWarning)
+                u_node = rng.uniform(eps, 1 - eps, size=n)
+                self.fallback_counts_[node] = n
 
+            u_node = np.asarray(u_node, dtype=float)
             bad = ~np.isfinite(u_node)
             if bad.any():
-                warnings.warn(f"node {node!r}: {int(bad.sum())} non-finite draws; using independent fallback for those")
-                u_node = np.where(bad, rng.uniform(EPS, 1 - EPS, size=n), u_node)
-            u_values[node] = np.clip(u_node, EPS, 1 - EPS)
-
+                warnings.warn(f"node {node!r}: {int(bad.sum())} non-finite draws; using independent fallback for those", FallbackWarning)
+                u_node = np.where(bad, rng.uniform(eps, 1 - eps, size=n), u_node)
+                self.fallback_counts_[node] = max(self.fallback_counts_[node], int(bad.sum()))
+            u_node = np.clip(u_node, eps, 1 - eps)
+
+            ks = float(kstest(u_node, "uniform").statistic) if parents else 0.0
+            if parents and self.calibrate_margins:
+                u_node = np.clip(rankdata(u_node) / (n + 1), eps, 1 - eps)
+            # flag only drift that is both practically large and beyond
+            # sampling noise (0.1% KS critical value ~ 1.95 / sqrt(n))
+            elif parents and ks > max(self.drift_tolerance, 1.95 / np.sqrt(n)):
+                warnings.warn(
+                    f"node {node!r}: generated U deviates from uniform (KS={ks:.3f}); its marginal will not be "
+                    "reproduced. Consider calibrate_margins=True.",
+                    MarginalDriftWarning,
+                )
+            u_values[node] = u_node
+            self.diagnostics_[node] = {
+                "model": kind,
+                "n_parents": len(parents),
+                "fallback_draws": self.fallback_counts_[node],
+                "u_uniformity_ks": ks,
+                "calibrated": bool(parents and self.calibrate_margins),
+            }
+
+        # latent (copula-scale) values of the last run, e.g. to check that a
+        # transplanted copula is reproduced before discretization by a marginal
+        self.u_values_ = pd.DataFrame(u_values)[list(self.dag.nodes)]
         data = {}
         for node in self.dag.nodes:
             marginal = self.node_specs[node].marginal or baseline_marginal()
             data[node] = marginal.inverse_transform(u_values[node])
         return pd.DataFrame(data, columns=list(self.dag.nodes))
 
+    @property
+    def total_fallback_draws(self) -> int:
+        return int(sum(self.fallback_counts_.values()))
+
     def _sample_indegree1(self, parent: str, u_values: dict, spec: NodeSpec, rng: np.random.Generator, n: int) -> np.ndarray:
+        self._last_sampler = None
         edge_model = spec.edge_model
-        bicop = edge_model.bicop if edge_model and edge_model.bicop is not None else baseline_bicop()
-        parent_is_first = edge_model.bicop_parent_is_first if edge_model else True
-        w = rng.uniform(EPS, 1 - EPS, size=n)
+        has_bicop = edge_model is not None and edge_model.bicop is not None
+        bicop = edge_model.bicop if has_bicop else baseline_bicop(self.baseline_rho)
+        parent_is_first = edge_model.bicop_parent_is_first if has_bicop else True
+        w = rng.uniform(self.clip_eps, 1 - self.clip_eps, size=n)
         u_parent = u_values[parent]
         # h1(u1,u2) = P(U2<=u2|U1=u1): hinv1([u1, w]) samples u2|u1.
         # h2(u1,u2) = P(U1<=u1|U2=u2): hinv2([w, u2]) samples u1|u2.
@@ -139,46 +238,109 @@ class GraphSampler:
             return bicop.hinv1(np.column_stack([u_parent, w]))
         return bicop.hinv2(np.column_stack([w, u_parent]))
 
+    def _resolve_parent_order(self, parents: list[str], edge_model: EdgeModel | None, sampler) -> list[str]:
+        if edge_model is not None and edge_model.parent_order is not None:
+            if set(edge_model.parent_order) != set(parents):
+                raise ValueError(f"parent_order {edge_model.parent_order} does not match DAG parents {parents}")
+            return list(edge_model.parent_order)
+        sampler_parents = list(getattr(sampler, "parents", []))
+        if set(sampler_parents) == set(parents):
+            return sampler_parents
+        return parents
+
     def _sample_indegree_k(self, node: str, parents: list[str], u_values: dict, spec: NodeSpec, rng: np.random.Generator, n: int) -> np.ndarray:
         edge_model = spec.edge_model
         sampler = edge_model.conditional_sampler if edge_model and edge_model.conditional_sampler else None
         if sampler is None:
-            sampler = _fit_baseline_conditional_sampler(node, parents, rng)
-        u_parents = np.column_stack([u_values[p] for p in parents])
+            sampler = _fit_baseline_conditional_sampler(node, parents, rng, rho=self.baseline_rho, clip_eps=self.clip_eps)
+            order = parents
+        else:
+            order = self._resolve_parent_order(parents, edge_model, sampler)
+        self._last_sampler = sampler
+        u_parents = np.column_stack([u_values[p] for p in order])
         return sampler.sample(u_parents, seed=int(rng.integers(0, 2**31 - 1)))
 
 
+# ---------------------------------------------------------------------- library helpers
+
 def _bicop_from_pairwise_entry(entry: dict) -> pv.Bicop:
-    family = getattr(pv.BicopFamily, entry["family"])
+    name = entry["family"]
+    if not isinstance(name, str) or not hasattr(pv.BicopFamily, name) or name.startswith("_"):
+        raise ValueError(f"unknown copula family {name!r} in library entry")
+    family = getattr(pv.BicopFamily, name)
     params = np.array(entry["parameters"], dtype=float)
     if params.size == 0:
         # e.g. the "indep" family has no parameters; .tolist() loses the (0, 0)
         # shape pv.Bicop's constructor requires, collapsing it to a bare [].
         params = params.reshape(0, 0)
-    return pv.Bicop(family=family, rotation=entry["rotation"], parameters=params)
-
-
-def node_spec_from_library(library: DependencyLibrary, dataset: str, node: str, parents: list[str]) -> NodeSpec:
+    return pv.Bicop(family=family, rotation=int(entry["rotation"]), parameters=params)
+
+
+def bind_pairwise_copula(library: DependencyLibrary, dataset: str, source_parent: str, source_child: str) -> EdgeModel:
+    """Re-use the copula learned for the pair (source_parent, source_child) in
+    `dataset` on ANY edge parent -> child of a new graph.
+
+    The source parent's column of the stored copula is mapped to the new
+    edge's parent, so asymmetric families keep their orientation. This is the
+    building-block reuse mechanism: the edge's dependence pattern (family,
+    rotation, parameters, hence tau and tail behaviour) is transplanted, while
+    the endpoints keep their own marginals.
+    """
+    entry = library.get_pairwise_entry(dataset, source_parent, source_child)
+    return EdgeModel(
+        bicop=_bicop_from_pairwise_entry(entry),
+        bicop_parent_is_first=entry["var_i"] == source_parent,
+        source=f"bound:{dataset}:{source_parent}->{source_child}",
+    )
+
+
+def composed_conditional(
+    library: DependencyLibrary, child: str, parents: list[str], edge_sources: dict[str, tuple[str, str, str]],
+    clip_eps: float = EPS,
+) -> EdgeModel:
+    """Build a multi-parent model from per-edge pairwise copulas.
+
+    `edge_sources[parent] = (dataset, source_parent, source_child)` names the
+    library pair whose copula is used for the edge parent -> child.
+    """
+    edges = []
+    for p in parents:
+        dataset, sp, sc = edge_sources[p]
+        entry = library.get_pairwise_entry(dataset, sp, sc)
+        edges.append((_bicop_from_pairwise_entry(entry), entry["var_i"] == sc))
+    sampler = PairwiseProductConditional(child=child, parents=parents, edges=edges, clip_eps=clip_eps)
+    return EdgeModel(conditional_sampler=sampler, parent_order=list(parents), source="composed")
+
+
+def node_spec_from_library(
+    library: DependencyLibrary, dataset: str, node: str, parents: list[str], compose: bool = False,
+) -> NodeSpec:
     """Build a NodeSpec for `node` (as it appeared in `dataset`) with the given parents,
-    using the T4 pairwise/conditional models and marginal already fit on that dataset."""
+    using the T4 pairwise/conditional models and marginal already fit on that dataset.
+
+    For >= 2 parents a fitted ConditionalSampler for that parent *set* is used
+    if one exists; otherwise, with `compose=True`, a PairwiseProductConditional
+    is assembled from the pairwise models of each (parent, node) pair, and with
+    `compose=False` a KeyError is raised (the historical behaviour).
+    """
     marginal = library.get_marginal(dataset, node)
 
     if not parents:
         edge_model = None
     elif len(parents) == 1:
         parent = parents[0]
-        entry = next(
-            (
-                e for e in library.pairwise
-                if e["dataset"] == dataset and {e["var_i"], e["var_j"]} == {node, parent} and "error" not in e
-            ),
-            None,
-        )
-        if entry is None:
-            raise KeyError(f"no pairwise model for {dataset}: {node} | {parent}")
+        try:
+            entry = library.get_pairwise_entry(dataset, node, parent)
+        except KeyError:
+            raise KeyError(f"no pairwise model for {dataset}: {node} | {parent}") from None
         edge_model = EdgeModel(bicop=_bicop_from_pairwise_entry(entry), bicop_parent_is_first=entry["var_i"] == parent)
     else:
-        sampler = library.get_conditional_sampler(dataset, node, parents)
-        edge_model = EdgeModel(conditional_sampler=sampler)
+        try:
+            sampler = library.get_conditional_sampler(dataset, node, parents)
+            edge_model = EdgeModel(conditional_sampler=sampler)
+        except KeyError:
+            if not compose:
+                raise
+            edge_model = composed_conditional(library, node, parents, {p: (dataset, p, node) for p in parents})
 
     return NodeSpec(marginal=marginal, edge_model=edge_model)
diff --git a/gcda/generation/spec.py b/gcda/generation/spec.py
new file mode 100644
index 0000000..084c9a6
--- /dev/null
+++ b/gcda/generation/spec.py
@@ -0,0 +1,173 @@
+"""Turn a user graph specification into GraphSampler node specs.
+
+Graph spec (JSON), all fields except "edges" optional:
+
+    {
+      "nodes": {"A": {"dataset": "sachs", "variable": "praf"},
+                "B": {"dataset": "asia",  "variable": "dysp"}},
+      "edges": [["A", "C"],
+                {"from": "A", "to": "B",
+                 "copula": {"dataset": "sachs", "pair": ["praf", "pmek"]}}]
+    }
+
+* A node maps to a (dataset, variable) in the library; it defaults to
+  (default_dataset, node name). Its marginal comes from that entry.
+* An edge's dependence is, in order of preference: an explicit "copula"
+  binding (any learned pair, from any dataset, re-used for this edge: the
+  first variable of "pair" plays the parent role); the learned pair copula
+  of the two endpoints if both come from the same dataset; otherwise the
+  Gaussian baseline (reported).
+* A multi-parent node uses the fitted conditional vine for that parent set
+  when all endpoints come from one dataset and such a vine exists;
+  otherwise (compose=True) a PairwiseProductConditional built from the
+  per-edge copulas above; otherwise the baseline Gaussian vine.
+
+Every decision is recorded in the returned report, and strict=True turns any
+baseline fallback into an error instead.
+"""
+
+import json
+from dataclasses import dataclass
+from pathlib import Path
+
+import networkx as nx
+
+from gcda.dependency.composed import PairwiseProductConditional
+from gcda.dependency.library import DependencyLibrary
+from gcda.generation.graph_sampler import (
+    DEFAULT_BASELINE_RHO,
+    EdgeModel,
+    NodeSpec,
+    _bicop_from_pairwise_entry,
+    baseline_bicop,
+)
+
+
+@dataclass
+class EdgeSource:
+    dataset: str
+    parent_var: str
+    child_var: str
+
+
+class StrictModeError(RuntimeError):
+    pass
+
+
+def load_graph_spec(path: str | Path) -> dict:
+    return json.loads(Path(path).read_text())
+
+
+def parse_graph_spec(spec: dict) -> tuple[nx.DiGraph, dict[str, dict], dict[tuple[str, str], dict]]:
+    dag = nx.DiGraph()
+    nodes = spec.get("nodes", [])
+    node_map: dict[str, dict] = {}
+    if isinstance(nodes, dict):
+        dag.add_nodes_from(nodes)
+        node_map = {k: (v or {}) for k, v in nodes.items()}
+    else:
+        dag.add_nodes_from(nodes)
+    bindings: dict[tuple[str, str], dict] = {}
+    for edge in spec["edges"]:
+        if isinstance(edge, dict):
+            u, v = edge["from"], edge["to"]
+            if "copula" in edge:
+                bindings[(u, v)] = edge["copula"]
+        else:
+            u, v = edge
+        dag.add_edge(u, v)
+    if not nx.is_directed_acyclic_graph(dag):
+        raise ValueError("graph spec is not a DAG")
+    return dag, node_map, bindings
+
+
+def build_node_specs(
+    library: DependencyLibrary,
+    spec: dict,
+    default_dataset: str | None = None,
+    compose: bool = True,
+    strict: bool = False,
+    baseline_rho: float = DEFAULT_BASELINE_RHO,
+) -> tuple[nx.DiGraph, dict[str, NodeSpec], list[dict]]:
+    dag, node_map, bindings = parse_graph_spec(spec)
+    source = {
+        n: (node_map.get(n, {}).get("dataset", default_dataset), node_map.get(n, {}).get("variable", n))
+        for n in dag.nodes
+    }
+    report: list[dict] = []
+
+    def fallback(item: dict) -> None:
+        report.append(item)
+        if strict:
+            raise StrictModeError(f"baseline fallback in strict mode: {item}")
+
+    def edge_source(parent: str, child: str) -> EdgeSource | None:
+        if (parent, child) in bindings:
+            b = bindings[(parent, child)]
+            return EdgeSource(b["dataset"], b["pair"][0], b["pair"][1])
+        (dp, vp), (dc, vc) = source[parent], source[child]
+        if dp is not None and dp == dc:
+            try:
+                library.get_pairwise_entry(dp, vp, vc)
+                return EdgeSource(dp, vp, vc)
+            except KeyError:
+                return None
+        return None
+
+    node_specs: dict[str, NodeSpec] = {}
+    for node in nx.topological_sort(dag):
+        ds, var = source[node]
+        marginal = None
+        if ds is not None and library.has_marginal(ds, var):
+            marginal = library.get_marginal(ds, var)
+        else:
+            fallback({"node": node, "what": "marginal", "decision": "standard-normal baseline marginal"})
+        parents = list(dag.predecessors(node))
+        edge_model = None
+        if len(parents) == 1:
+            es = edge_source(parents[0], node)
+            if es is None:
+                fallback({"node": node, "what": f"edge {parents[0]}->{node}", "decision": "baseline Gaussian copula"})
+            else:
+                entry = library.get_pairwise_entry(es.dataset, es.parent_var, es.child_var)
+                edge_model = EdgeModel(
+                    bicop=_bicop_from_pairwise_entry(entry),
+                    bicop_parent_is_first=entry["var_i"] == es.parent_var,
+                    source=f"pairwise:{es.dataset}:{es.parent_var}->{es.child_var}",
+                )
+                report.append({"node": node, "what": f"edge {parents[0]}->{node}", "decision": edge_model.source})
+        elif len(parents) >= 2:
+            edge_model = _multi_parent_model(library, node, parents, source, bindings, edge_source, compose, baseline_rho, report, fallback)
+        node_specs[node] = NodeSpec(marginal=marginal, edge_model=edge_model)
+    return dag, node_specs, report
+
+
+def _multi_parent_model(library, node, parents, source, bindings, edge_source, compose, baseline_rho, report, fallback):
+    ds, var = source[node]
+    same_ds = all(source[p][0] == ds for p in parents) and not any((p, node) in bindings for p in parents)
+    if same_ds and ds is not None:
+        by_var = {source[p][1]: p for p in parents}
+        try:
+            sampler = library.get_conditional_sampler(ds, var, list(by_var))
+            order = [by_var[v] for v in sampler.parents]
+            report.append({"node": node, "what": "parents", "decision": f"fitted vine {ds}:{var}|{sampler.parents}"})
+            return EdgeModel(conditional_sampler=sampler, parent_order=order, source="fitted-vine")
+        except KeyError:
+            pass
+    if not compose:
+        fallback({"node": node, "what": "parents", "decision": "baseline Gaussian vine (no fitted vine, compose disabled)"})
+        return None
+    edges, used = [], []
+    for p in parents:
+        es = edge_source(p, node)
+        if es is None:
+            fallback({"node": node, "what": f"edge {p}->{node}", "decision": "baseline Gaussian copula inside composed model"})
+            edges.append((baseline_bicop(baseline_rho), False))
+            used.append("baseline")
+        else:
+            entry = library.get_pairwise_entry(es.dataset, es.parent_var, es.child_var)
+            edges.append((_bicop_from_pairwise_entry(entry), entry["var_i"] == es.child_var))
+            used.append(f"{es.dataset}:{es.parent_var}->{es.child_var}")
+    report.append({"node": node, "what": "parents", "decision": f"composed from pairwise {used}"})
+    sampler = PairwiseProductConditional(child=node, parents=parents, edges=edges)
+    return EdgeModel(conditional_sampler=sampler, parent_order=list(parents), source="composed")
diff --git a/gcda/provenance.py b/gcda/provenance.py
new file mode 100644
index 0000000..e606247
--- /dev/null
+++ b/gcda/provenance.py
@@ -0,0 +1,53 @@
+"""Run metadata attached to every generated artifact (library, sweep, evaluation).
+
+Records the package versions, Python version, platform, git commit and the
+arguments/seeds of a run, so a number in the thesis can be traced back to the
+exact code and environment that produced it.
+"""
+
+import json
+import platform
+import subprocess
+import sys
+from datetime import datetime, timezone
+from importlib import metadata
+from pathlib import Path
+
+_PACKAGES = ["numpy", "scipy", "pandas", "networkx", "pyvinecopulib", "pgmpy", "causal-learn", "scikit-learn"]
+
+
+def _git_sha() -> str | None:
+    try:
+        root = Path(__file__).resolve().parent.parent
+        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=5)
+        sha = out.stdout.strip()
+        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, timeout=5)
+        return sha + ("+dirty" if dirty.stdout.strip() else "") if sha else None
+    except Exception:  # noqa: BLE001 - provenance must never break a run
+        return None
+
+
+def run_metadata(**extra) -> dict:
+    versions = {}
+    for pkg in _PACKAGES:
+        try:
+            versions[pkg] = metadata.version(pkg)
+        except metadata.PackageNotFoundError:
+            versions[pkg] = None
+    return {
+        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
+        "python": sys.version.split()[0],
+        "platform": platform.platform(),
+        "git_sha": _git_sha(),
+        "packages": versions,
+        "argv": sys.argv,
+        **extra,
+    }
+
+
+def write_metadata(path: str | Path, **extra) -> Path:
+    """Write `<path>.meta.json` next to an output file and return its path."""
+    path = Path(path)
+    meta_path = path.with_name(path.name + ".meta.json")
+    meta_path.write_text(json.dumps(run_metadata(output=path.name, **extra), indent=2, default=str))
+    return meta_path
diff --git a/pyproject.toml b/pyproject.toml
index 191fcd5..7d3df65 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -4,28 +4,39 @@ build-backend = "setuptools.build_meta"
 
 [project]
 name = "graph-conditioned-augmentation"
-version = "0.1.0"
+version = "0.2.0"
 description = "Graph-Conditioned Causal Data Augmentation: a copula-based synthetic data generator for graph learning"
 requires-python = ">=3.10"
+# Lower bounds = oldest versions the thesis results were produced with; upper
+# bounds only where a known removal would break the code (pgmpy 1.3 removes
+# get_example_model). The exact environment that reproduced every table
+# bit-for-bit is pinned in requirements-lock.txt.
 dependencies = [
-    "numpy",
-    "scipy",
-    "pandas",
-    "matplotlib",
-    "scikit-learn",
-    "networkx",
-    "pyvinecopulib",
-    "PyYAML",
-    "wandb",
-    "pgmpy",
-    "causal-learn",
+    "numpy>=1.26",
+    "scipy>=1.11",
+    "pandas>=2.1",
+    "matplotlib>=3.8",
+    "scikit-learn>=1.3",
+    "networkx>=3.2",
+    "pyvinecopulib>=0.7.6",
+    "PyYAML>=6.0",
+    "wandb>=0.16",
+    "pgmpy>=0.1.25,<1.3",
+    "causal-learn>=0.1.3.8",
 ]
 
 [project.optional-dependencies]
-test = ["pytest"]
+test = ["pytest>=8"]
 
 [project.scripts]
 gcda = "gcda.cli:main"
 
 [tool.setuptools.packages.find]
 include = ["gcda*"]
+
+[tool.setuptools.package-data]
+"gcda.data" = ["resources/*.csv"]
+
+[tool.pytest.ini_options]
+testpaths = ["tests"]
+filterwarnings = ["ignore::FutureWarning", "ignore::DeprecationWarning"]
diff --git a/requirements.txt b/requirements.txt
index 037be94..4580887 100644
--- a/requirements.txt
+++ b/requirements.txt
@@ -17,5 +17,5 @@ pyvinecopulib
 pytest
 PyYAML
 wandb
-pgmpy
+pgmpy<1.3
 causal-learn
diff --git a/scripts/build_dependency_library.py b/scripts/build_dependency_library.py
index 6a71e51..6382898 100644
--- a/scripts/build_dependency_library.py
+++ b/scripts/build_dependency_library.py
@@ -10,25 +10,12 @@ from gcda.data.datasets import load_sachs, load_uci_diabetes, make_synthetic_scm
 from gcda.data.preprocessing import handle_missing_values, to_pseudo_observations
 from gcda.dependency.conditional import ConditionalSampler
 from gcda.dependency.library import DependencyLibrary
-from gcda.dependency.pairwise import build_pairwise_library
+from gcda.dependency.pairwise import build_pairwise_library, top_k_partners
+from gcda.provenance import run_metadata
 
 OUTPUT_PATH = Path(__file__).parent.parent / "outputs" / "dependency_library.json"
 
 
-def top_k_partners(pairwise_entries: list[dict], target: str, k: int = 2) -> list[str]:
-    """Rank a target variable's pairwise partners by |Kendall's tau| and return the top k."""
-    scored = []
-    for entry in pairwise_entries:
-        if "error" in entry:
-            continue
-        if entry["var_i"] == target:
-            scored.append((abs(entry["tau"]), entry["var_j"]))
-        elif entry["var_j"] == target:
-            scored.append((abs(entry["tau"]), entry["var_i"]))
-    scored.sort(reverse=True)
-    return [name for _, name in scored[:k]]
-
-
 def process_dataset(library: DependencyLibrary, name: str, df, conditional_child: str | None = None,
                      conditional_parents: list[str] | None = None) -> None:
     print(f"\n=== {name} ({df.shape[0]} rows, {df.shape[1]} vars) ===")
@@ -76,6 +63,7 @@ def main() -> None:
     )
 
     OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
+    library.metadata = run_metadata(script='build_dependency_library.py')
     library.save(OUTPUT_PATH)
     print(f"\nSaved dependency library ({len(library.pairwise)} pairwise, "
           f"{len(library.conditional)} conditional models) to {OUTPUT_PATH}")
diff --git a/scripts/build_discrete_library.py b/scripts/build_discrete_library.py
index ab643d9..84757c6 100644
--- a/scripts/build_discrete_library.py
+++ b/scripts/build_discrete_library.py
@@ -18,7 +18,8 @@ from gcda.data.datasets import load_asia, load_insurance, make_discretized_sachs
 from gcda.data.preprocessing import to_pseudo_observations_mixed
 from gcda.dependency.conditional import ConditionalSampler
 from gcda.dependency.library import DependencyLibrary
-from gcda.dependency.pairwise import build_pairwise_library
+from gcda.dependency.pairwise import build_pairwise_library, top_k_partners
+from gcda.provenance import run_metadata
 
 OUTPUT_PATH = Path(__file__).parent.parent / "outputs" / "discrete_dependency_library.json"
 
@@ -29,19 +30,6 @@ OUTPUT_PATH = Path(__file__).parent.parent / "outputs" / "discrete_dependency_li
 DISCRETIZED_SACHS_TARGET = "pmek"
 
 
-def top_k_partners(pairwise_entries: list[dict], target: str, k: int = 2) -> list[str]:
-    scored = []
-    for entry in pairwise_entries:
-        if "error" in entry:
-            continue
-        if entry["var_i"] == target:
-            scored.append((abs(entry["tau"]), entry["var_j"]))
-        elif entry["var_j"] == target:
-            scored.append((abs(entry["tau"]), entry["var_i"]))
-    scored.sort(reverse=True)
-    return [name for _, name in scored[:k]]
-
-
 def build_graph_library(
     library: DependencyLibrary, name: str, df: pd.DataFrame, dag: nx.DiGraph, category_orders: dict[str, list]
 ) -> None:
@@ -90,6 +78,7 @@ def main() -> None:
     library.add_conditional("discretized_sachs", sampler)
 
     OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
+    library.metadata = run_metadata(script='build_discrete_library.py')
     library.save(OUTPUT_PATH)
     print(f"\nSaved discrete dependency library ({len(library.pairwise)} pairwise, "
           f"{len(library.conditional)} conditional models) to {OUTPUT_PATH}")
diff --git a/scripts/check_reproduction.py b/scripts/check_reproduction.py
new file mode 100644
index 0000000..c0cca0e
--- /dev/null
+++ b/scripts/check_reproduction.py
@@ -0,0 +1,21 @@
+"""Compare a freshly produced sweep CSV with the committed reference (exit 1 on mismatch).
+
+    python scripts/check_reproduction.py NEW.csv outputs/sweep_dependency_models.csv
+"""
+
+import sys
+
+import numpy as np
+import pandas as pd
+
+new, ref = pd.read_csv(sys.argv[1]), pd.read_csv(sys.argv[2])
+keys = ["dataset", "family_set", "selection_criterion"]
+m = ref.merge(new, on=keys, suffixes=("_ref", "_new"))
+ok = len(m) == len(ref)
+for col in ["vine_aic", "vine_bic", "mean_tau_abs_error"]:
+    diff = np.abs(m[f"{col}_ref"] - m[f"{col}_new"]).max()
+    print(f"{col}: max |diff| = {diff:.3g}")
+    ok &= diff < 1e-6
+same = (m["families_selected_ref"] == m["families_selected_new"]).all()
+print("families identical:", same)
+sys.exit(0 if ok and same else 1)
diff --git a/scripts/demo.py b/scripts/demo.py
index 5988180..ade420a 100644
--- a/scripts/demo.py
+++ b/scripts/demo.py
@@ -20,7 +20,7 @@ import networkx as nx
 import pandas as pd
 from scipy.stats import kendalltau
 
-from gcda.data.datasets import load_asia, make_synthetic_scm
+from gcda.data.datasets import load_asia, load_sachs, make_synthetic_scm
 from gcda.data.preprocessing import to_pseudo_observations, to_pseudo_observations_mixed
 from gcda.dependency.conditional import ConditionalSampler
 from gcda.dependency.library import DependencyLibrary
@@ -28,6 +28,7 @@ from gcda.dependency.pairwise import build_pairwise_library
 from gcda.evaluation.causal_discovery import compare_causal_discovery, encode_categorical
 from gcda.evaluation.realism import compare_marginals, compare_pairwise_dependence
 from gcda.generation.graph_sampler import GraphSampler, NodeSpec, node_spec_from_library
+from gcda.generation.spec import build_node_specs
 
 
 def banner(title: str) -> None:
@@ -97,20 +98,30 @@ def step_4_discrete_network() -> DependencyLibrary:
 
 def step_5_cross_dataset_composition(continuous_library: DependencyLibrary, discrete_library: DependencyLibrary) -> None:
     banner("5. Compose a NOVEL graph from two different datasets' building blocks")
-    merged = DependencyLibrary()
-    merged.pairwise = continuous_library.pairwise + discrete_library.pairwise
-    merged.conditional = continuous_library.conditional + discrete_library.conditional
-    merged.marginals = {**continuous_library.marginals, **discrete_library.marginals}
-
-    # a graph that never existed in either original dataset
-    dag = nx.DiGraph([("x1", "x4"), ("x1", "dysp")])
-    node_specs = {
-        "x1": node_spec_from_library(merged, "synthetic_scm", "x1", []),
-        "x4": node_spec_from_library(merged, "synthetic_scm", "x4", ["x1"]),
-        "dysp": node_spec_from_library(merged, "asia", "dysp", []),
+    # Sachs building blocks (marginals + the learned praf-pmek copula)
+    sachs = load_sachs()
+    u_s, m_s = to_pseudo_observations(sachs)
+    sachs_library = DependencyLibrary()
+    sachs_library.add_marginals("sachs", m_s)
+    sachs_library.add_pairwise(build_pairwise_library(u_s, "sachs", pairs=[("praf", "pmek")]))
+    merged = sachs_library.merge(discrete_library)
+
+    # praf -> pmek uses the copula learned on Sachs; the cross-dataset edge
+    # praf -> dysp RE-USES the copula Asia learned for bronc -> dysp
+    # (graph that never existed in either dataset; strict = no baseline fallback)
+    spec = {
+        "nodes": {"praf": {"dataset": "sachs"}, "pmek": {"dataset": "sachs"}, "dysp": {"dataset": "asia"}},
+        "edges": [["praf", "pmek"],
+                  {"from": "praf", "to": "dysp", "copula": {"dataset": "asia", "pair": ["bronc", "dysp"]}}],
     }
-    df = GraphSampler(dag, node_specs=node_specs).sample(n=1000, seed=0)
-    print("A graph mixing a continuous Sachs-style pair with a discrete Asia node:")
+    dag, node_specs, report = build_node_specs(merged, spec, strict=True)
+    for item in report:
+        print(f"  {item['node']}: {item['what']} <- {item['decision']}")
+    df = GraphSampler(dag, node_specs=node_specs).sample(n=5000, seed=0)
+    print(f"tau(praf, pmek): generated={kendalltau(df['praf'], df['pmek'])[0]:.3f} "
+          f"real Sachs={kendalltau(sachs['praf'], sachs['pmek'])[0]:.3f}")
+    print(f"P(dysp=yes): generated={(df['dysp'] == 'yes').mean():.3f} "
+          f"(Asia marginal re-used)")
     print(df.head())
 
 
diff --git a/scripts/evaluate_causal_discovery.py b/scripts/evaluate_causal_discovery.py
index 17d95ba..373c6ff 100644
--- a/scripts/evaluate_causal_discovery.py
+++ b/scripts/evaluate_causal_discovery.py
@@ -30,6 +30,7 @@ import pandas as pd
 from gcda.data.datasets import load_asia, make_synthetic_scm
 from gcda.dependency.library import DependencyLibrary
 from gcda.evaluation.causal_discovery import compare_causal_discovery, encode_categorical
+from gcda.provenance import write_metadata
 from gcda.generation.graph_sampler import GraphSampler, NodeSpec, node_spec_from_library
 
 CONTINUOUS_LIBRARY_PATH = Path(__file__).parent.parent / "outputs" / "dependency_library.json"
@@ -111,3 +112,8 @@ if __name__ == "__main__":
     print(disc.pivot(index="seed", columns="source", values="shd_to_true_dag").to_string())
     print("\nmean SHD across seeds (lower is better):")
     print(summarize(disc).to_string())
+
+    out = Path(__file__).parent.parent / "outputs" / "causal_discovery_results.csv"
+    pd.concat([cont.assign(graph="synthetic_scm"), disc.assign(graph="asia")]).to_csv(out, index=False)
+    write_metadata(out, seeds=SEEDS)
+    print(f"\nSaved per-seed results to {out}")
diff --git a/scripts/evaluate_discrete_generation.py b/scripts/evaluate_discrete_generation.py
index 74725fd..e3d59e7 100644
--- a/scripts/evaluate_discrete_generation.py
+++ b/scripts/evaluate_discrete_generation.py
@@ -52,6 +52,7 @@ from gcda.evaluation.discrete import (
     compare_discrete_dependence,
     measure_generation_stability,
 )
+from gcda.provenance import write_metadata
 from gcda.generation.graph_sampler import GraphSampler, NodeSpec, node_spec_from_library
 
 LIBRARY_PATH = Path(__file__).parent.parent / "outputs" / "discrete_dependency_library.json"
@@ -88,6 +89,15 @@ def evaluate_network(library: DependencyLibrary, dataset: str, true_df, dag: nx.
         print(f"  [{label}] T7d.ii edge dependence: mean cramers_v_abs_error={dep['cramers_v_abs_error'].mean():.4f}, "
               f"mean nmi_abs_error={dep['nmi_abs_error'].mean():.4f}")
 
+    out_dir = LIBRARY_PATH.parent
+    for label, res in results.items():
+        res["freq"].assign(source=label).to_csv(out_dir / f"discrete_{dataset}_{label}_frequencies.csv", index=False)
+        res["dep"].assign(source=label).to_csv(out_dir / f"discrete_{dataset}_{label}_edge_dependence.csv", index=False)
+    summary = out_dir / f"discrete_{dataset}_stability.json"
+    import json
+    summary.write_text(json.dumps({k: v["stability"] for k, v in results.items()}, indent=2))
+    write_metadata(summary, dataset=dataset)
+
     dep_learned = results["learned"]["dep"]
     worst = dep_learned.sort_values("cramers_v_abs_error", ascending=False).head(3)
     print("  worst-matched edges in the learned run (largest Cramer's V error):")
diff --git a/scripts/evaluate_mixed_generation.py b/scripts/evaluate_mixed_generation.py
index c7f8097..c428648 100644
--- a/scripts/evaluate_mixed_generation.py
+++ b/scripts/evaluate_mixed_generation.py
@@ -23,6 +23,8 @@ small enough that a separate build step isn't needed), then evaluates:
     continuous-discrete and discrete-discrete edges alike.
 """
 
+from pathlib import Path
+
 import networkx as nx
 import numpy as np
 import pandas as pd
@@ -34,6 +36,7 @@ from gcda.dependency.library import DependencyLibrary
 from gcda.dependency.pairwise import build_pairwise_library
 from gcda.evaluation.discrete import compare_category_frequencies, cramers_v
 from gcda.evaluation.realism import compare_marginals, compare_pairwise_dependence
+from gcda.provenance import write_metadata
 from gcda.generation.graph_sampler import GraphSampler, node_spec_from_library
 
 
@@ -89,6 +92,10 @@ def main() -> None:
     true_numeric = to_ordinal_numeric(true_df, category_orders)
     sim_numeric = to_ordinal_numeric(sim_df, category_orders)
     dep = compare_pairwise_dependence(true_numeric, sim_numeric, pairs=list(dag.edges))
+    out = Path(__file__).parent.parent / "outputs" / "mixed_generation_edges.csv"
+    out.parent.mkdir(parents=True, exist_ok=True)
+    dep.to_csv(out, index=False)
+    write_metadata(out)
     for _, row in dep.iterrows():
         edge_type = "discrete-discrete" if {row.var_i, row.var_j} <= set(discrete_cols) else (
             "continuous-continuous" if {row.var_i, row.var_j} <= set(continuous_cols) else "mixed"
diff --git a/scripts/merge_results.py b/scripts/merge_results.py
new file mode 100644
index 0000000..6045a9d
--- /dev/null
+++ b/scripts/merge_results.py
@@ -0,0 +1,32 @@
+"""Merge per-seed results of Slurm array tasks and recompute summaries/tests.
+
+    python scripts/merge_results.py rq6 outputs/hpc/rq6/task_* --out outputs/hpc/rq6/merged
+    python scripts/merge_results.py rq4 outputs/hpc/rq4/task_* --out outputs/hpc/rq4/merged
+"""
+
+import argparse
+from pathlib import Path
+
+import pandas as pd
+
+FILES = {"rq6": "rq6_heldout_per_seed.csv", "rq4": "rq4_heldout_per_seed.csv"}
+
+if __name__ == "__main__":
+    p = argparse.ArgumentParser()
+    p.add_argument("experiment", choices=sorted(FILES))
+    p.add_argument("dirs", nargs="+", type=Path)
+    p.add_argument("--out", type=Path, required=True)
+    a = p.parse_args()
+    frames = [pd.read_csv(d / FILES[a.experiment]) for d in a.dirs if (d / FILES[a.experiment]).exists()]
+    res = pd.concat(frames, ignore_index=True).drop_duplicates()
+    key = ["graph", "seed", "source"] if a.experiment == "rq6" else ["network", "seed", "source"]
+    dup = res.duplicated(key).sum()
+    if dup:
+        raise SystemExit(f"{dup} duplicated (graph/network, seed, source) rows across tasks")
+    a.out.mkdir(parents=True, exist_ok=True)
+    if a.experiment == "rq6":
+        from gcda.experiments.rq6 import write_outputs
+    else:
+        from gcda.experiments.rq4 import write_outputs
+    write_outputs(res, a.out, merged_from=[str(d) for d in a.dirs])
+    print(f"merged {len(frames)} task directories, {res['seed'].nunique()} seeds")
diff --git a/scripts/run_experiments.py b/scripts/run_experiments.py
new file mode 100644
index 0000000..1554b7c
--- /dev/null
+++ b/scripts/run_experiments.py
@@ -0,0 +1,56 @@
+"""Entry point for the extended (remediation) experiments.
+
+    python scripts/run_experiments.py rq4 --graphs asia insurance alarm mixed_scm --seeds 10
+    python scripts/run_experiments.py rq6 --graphs synthetic_scm asia insurance alarm --seeds 30
+    python scripts/run_experiments.py composition --n-dags 20
+    python scripts/run_experiments.py rq1
+    python scripts/run_experiments.py discrete-native
+    python scripts/run_experiments.py learned-indegree
+    python scripts/run_experiments.py rq2
+
+Every experiment writes CSV/JSON results plus a `.meta.json` provenance file to
+--out (default outputs/experiments/). The same commands are wrapped in
+slurm/*.slurm for larger seed counts on the Lichtenberg cluster.
+"""
+
+import argparse
+from pathlib import Path
+
+DEFAULT_OUT = Path(__file__).resolve().parent.parent / "outputs" / "experiments"
+
+if __name__ == "__main__":
+    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
+    p.add_argument("experiment", choices=["rq4", "rq6", "composition", "rq5", "rq1", "discrete-native", "learned-indegree", "rq2"])
+    p.add_argument("--graphs", nargs="+", default=["synthetic_scm", "asia", "insurance", "alarm"])
+    p.add_argument("--seeds", type=int, default=30, help="number of evaluation seeds")
+    p.add_argument("--seed-start", type=int, default=0, help="first evaluation seed (for Slurm array splits)")
+    p.add_argument("--n-dags", type=int, default=20)
+    p.add_argument("--alpha", type=float, default=0.05)
+    p.add_argument("--algorithm", choices=["pc", "ges"], default="pc", help="discovery algorithm for rq6")
+    p.add_argument("--dag-start", type=int, default=0, help="first random-DAG index for composition (array splits)")
+    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
+    a = p.parse_args()
+    if a.experiment == "rq4":
+        from gcda.experiments.rq4 import main
+        main(a.out, a.graphs, a.seeds, seed_start=a.seed_start)
+    elif a.experiment == "rq6":
+        from gcda.experiments.rq6 import main
+        main(a.graphs, a.seeds, a.out, alpha=a.alpha, seed_start=a.seed_start, algorithm=a.algorithm)
+    elif a.experiment == "composition":
+        from gcda.experiments.composition import main
+        main(a.n_dags, a.seeds, a.out, dag_start=a.dag_start)
+    elif a.experiment == "rq5":
+        from gcda.experiments.composition import main_rq5_only
+        main_rq5_only(a.out, a.seeds)
+    elif a.experiment == "rq1":
+        from gcda.experiments.rq1 import main
+        main(a.out)
+    elif a.experiment == "discrete-native":
+        from gcda.experiments.discrete_native import main
+        main(a.out)
+    elif a.experiment == "learned-indegree":
+        from gcda.experiments.learned_indegree import main
+        main(a.out, a.seeds)
+    elif a.experiment == "rq2":
+        from gcda.experiments.rq2 import main
+        main(a.out, a.seeds)
diff --git a/scripts/sweep_hyperparameters.py b/scripts/sweep_hyperparameters.py
index 1067221..020a2b7 100644
--- a/scripts/sweep_hyperparameters.py
+++ b/scripts/sweep_hyperparameters.py
@@ -1,17 +1,4 @@
-"""T6c/T7: sweep key hyperparameters and log metrics (optionally to W&B).
-
-Sweeps: copula family set x AIC-vs-BIC selection x dataset choice (for the
-2-parent conditional model) across BOTH continuous (Sachs, UCI diabetes,
-synthetic SCM) and discrete (Asia, Insurance) datasets, plus a separate
-indegree-cap sweep (T5's GraphSampler extension beyond the core
-max-indegree-2 target). Every run also records the clipping epsilon and
-how many fallback draws were needed, per T6c's "clipping/fallback
-settings" logging requirement.
-
-What to sweep is read from configs/sweep.yaml (T8b.i) rather than hardcoded
-here, so a sweep is reproducible from a versioned config file - which
-matters for W&B runs (T8b.iii): the config that produced a run should be
-diffable/checkoutable, not baked into the script that ran it.
+"""T6c/T7: sweep key hyperparameters (thin wrapper around gcda.experiments.sweep).
 
 Run: python scripts/sweep_hyperparameters.py [--wandb] [--config PATH]
 
@@ -20,177 +7,15 @@ wandb/); set WANDB_MODE=online and log in beforehand to sync for real.
 """
 
 import argparse
-import os
-import time
-from itertools import chain, product
 from pathlib import Path
 
-import networkx as nx
-import numpy as np
-import pandas as pd
-import pyvinecopulib as pv
-import yaml
-from scipy.stats import kendalltau
-
-from gcda.data.datasets import load_asia, load_insurance, load_sachs, load_uci_diabetes, make_synthetic_scm
-from gcda.data.preprocessing import handle_missing_values, to_pseudo_observations_mixed
-from gcda.dependency.conditional import EPS, ConditionalSampler
-from gcda.evaluation.realism import compare_pairwise_dependence, energy_distance, gaussian_mmd
-from gcda.generation.graph_sampler import GraphSampler
-
-OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
-DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "configs" / "sweep.yaml"
-WANDB_PROJECT = "graph-conditioned-augmentation"
-
-
-def _load_discrete(loader) -> tuple[pd.DataFrame, dict[str, list]]:
-    """Discrete loaders return (df, dag, category_orders); the sweep only needs data + category orders."""
-    df, _dag, category_orders = loader()
-    return df, category_orders
-
-
-# Each entry returns (df, category_orders); category_orders is None for continuous data.
-LOADERS = {
-    "sachs": lambda: (load_sachs(), None),
-    "uci_diabetes": lambda: (load_uci_diabetes(), None),
-    "synthetic_scm": lambda: (make_synthetic_scm(n=5000, seed=1)[0], None),
-    "asia": lambda: _load_discrete(lambda: load_asia(n_samples=8000, seed=0)),
-    "insurance": lambda: _load_discrete(lambda: load_insurance(n_samples=8000, seed=0)),
-}
-
-
-def load_config(path: Path) -> dict:
-    config = yaml.safe_load(path.read_text())
-    config["family_sets"] = {
-        name: [getattr(pv.BicopFamily, family) for family in families]
-        for name, families in config["family_sets"].items()
-    }
-    return config
-
-
-def run_dependency_sweep(config: dict, use_wandb: bool = False) -> pd.DataFrame:
-    targets = config["targets"]
-    family_sets = config["family_sets"]
-    rows = []
-    for dataset_name, family_set_name, criterion in product(targets, family_sets, config["selection_criteria"]):
-        print(f"  {dataset_name} / {family_set_name} / {criterion}")
-        df, category_orders = LOADERS[dataset_name]()
-        clean, _ = handle_missing_values(df, strategy="drop")
-        u_df, _ = to_pseudo_observations_mixed(clean, category_orders=category_orders, seed=0)
-
-        target = targets[dataset_name]
-        child, parents = target["child"], target["parents"]
-        columns = [child, *parents]
-
-        sampler = ConditionalSampler(
-            child=child, parents=parents,
-            family_set=family_sets[family_set_name], selection_criterion=criterion,
-        )
-        sampler.fit(u_df)
-
-        u_sim = sampler.sample(u_df[parents].to_numpy(), seed=0)
-        sim_u_df = u_df[parents].copy()
-        sim_u_df[child] = u_sim
-
-        dep = compare_pairwise_dependence(u_df[columns], sim_u_df[columns], pairs=[(child, p) for p in parents])
-        data_np = u_df[columns].to_numpy()
-        sim_np = sim_u_df[columns].to_numpy()
-
-        vine = sampler.vine_
-        families_selected = [f.name for f in chain.from_iterable(vine.families)]
+from gcda.experiments.sweep import DEFAULT_CONFIG_PATH, main
 
-        metrics = {
-            "dataset": dataset_name,
-            "family_set": family_set_name,
-            "selection_criterion": criterion,
-            "child": child,
-            "parents": ",".join(parents),
-            "n": len(u_df),
-            "vine_aic": vine.aic(data_np),
-            "vine_bic": vine.bic(data_np),
-            "families_selected": ",".join(families_selected),
-            "mean_tau_abs_error": dep["tau_abs_error"].mean(),
-            "energy_distance": energy_distance(data_np, sim_np),
-            "gaussian_mmd": gaussian_mmd(data_np, sim_np),
-            "n_fallback": sampler.last_fallback_count_,
-            "clip_eps": EPS,
-        }
-        rows.append(metrics)
-        if use_wandb:
-            import wandb
-            wandb.log(metrics)
-    return pd.DataFrame(rows)
-
-
-def run_indegree_sweep(config: dict, use_wandb: bool = False) -> pd.DataFrame:
-    spec = config["indegree_sweep"]
-    rho, n, seed = spec["baseline_rho"], spec["n"], spec["seed"]
-    rows = []
-    for cap in spec["caps"]:
-        print(f"  indegree_cap={cap}")
-        parents = [f"P{i}" for i in range(cap)]
-        dag = nx.DiGraph()
-        dag.add_nodes_from([*parents, "X"])
-        dag.add_edges_from([(p, "X") for p in parents])
-
-        t0 = time.time()
-        sampler = GraphSampler(dag, max_indegree=cap)
-        df = sampler.sample(n=n, seed=seed)
-        elapsed = time.time() - t0
-
-        taus = [kendalltau(df[p], df["X"])[0] for p in parents]
-        metrics = {
-            "indegree_cap": cap,
-            "baseline_rho": rho,
-            "mean_tau": float(np.mean(taus)),
-            "min_tau": float(np.min(taus)),
-            "max_tau": float(np.max(taus)),
-            "elapsed_sec": elapsed,
-            "clip_eps": EPS,
-        }
-        rows.append(metrics)
-        if use_wandb:
-            import wandb
-            wandb.log(metrics)
-    return pd.DataFrame(rows)
-
-
-def main() -> None:
+if __name__ == "__main__":
     parser = argparse.ArgumentParser(description=__doc__)
     parser.add_argument("--wandb", action="store_true", help="log each run to Weights & Biases (offline by default)")
-    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="sweep config YAML (default: configs/sweep.yaml)")
+    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="sweep config YAML")
+    parser.add_argument("--output-dir", type=Path, default=None)
     args = parser.parse_args()
-
-    config = load_config(args.config)
-
-    if args.wandb:
-        import wandb
-        wandb.init(
-            project=WANDB_PROJECT, name="hyperparameter-sweep",
-            mode=os.environ.get("WANDB_MODE", "offline"),
-            config={"config_file": str(args.config), **yaml.safe_load(args.config.read_text())},
-        )
-
-    print("Dependency-model sweep (family set x AIC/BIC x dataset):")
-    dep_results = run_dependency_sweep(config, use_wandb=args.wandb)
-
-    print("\nIndegree-cap sweep:")
-    indegree_results = run_indegree_sweep(config, use_wandb=args.wandb)
-
-    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
-    dep_results.to_csv(OUTPUT_DIR / "sweep_dependency_models.csv", index=False)
-    indegree_results.to_csv(OUTPUT_DIR / "sweep_indegree_cap.csv", index=False)
-
-    print("\n=== dependency-model sweep results ===")
-    print(dep_results.drop(columns=["parents", "families_selected"]).to_string(index=False))
-    print("\n=== indegree-cap sweep results ===")
-    print(indegree_results.to_string(index=False))
-    print(f"\nSaved full results to {OUTPUT_DIR}/sweep_dependency_models.csv and sweep_indegree_cap.csv")
-
-    if args.wandb:
-        import wandb
-        wandb.finish()
-
-
-if __name__ == "__main__":
-    main()
+    kwargs = {"output_dir": args.output_dir} if args.output_dir else {}
+    main(config_path=args.config, use_wandb=args.wandb, **kwargs)
diff --git a/scripts/verify_sachs_subset.py b/scripts/verify_sachs_subset.py
new file mode 100644
index 0000000..540bd16
--- /dev/null
+++ b/scripts/verify_sachs_subset.py
@@ -0,0 +1,31 @@
+"""Verify that the first 853 rows of the bundled Sachs file are the CD3/CD28
+(observational) condition, by comparing with an independent copy of that
+condition, e.g. bnlearn's continuous observational data:
+
+    wget https://www.bnlearn.com/book-crc/code/sachs.data.txt.gz && gunzip sachs.data.txt.gz
+    python scripts/verify_sachs_subset.py sachs.data.txt
+
+The reference is read as whitespace-separated with a header; columns are
+matched by order (Raf, Mek, Plcg, PIP2, PIP3, Erk, Akt, PKA, PKC, P38, Jnk).
+Exit status 0 if all 853 rows match (relative tolerance 1e-3), 1 otherwise.
+"""
+
+import sys
+
+import numpy as np
+import pandas as pd
+
+from gcda.data.datasets import SACHS_OBSERVATIONAL_ROWS, load_sachs
+
+ref = pd.read_csv(sys.argv[1], sep=r"\s+")
+ours = load_sachs(observational_only=True)
+if len(ref) != SACHS_OBSERVATIONAL_ROWS:
+    print(f"reference has {len(ref)} rows, expected {SACHS_OBSERVATIONAL_ROWS}")
+same_rows = np.isclose(ref.to_numpy()[:len(ours)], ours.to_numpy(), rtol=1e-3).all(axis=1)
+print(f"{same_rows.sum()}/{len(ours)} rows match row-by-row")
+if not same_rows.all():
+    # order-insensitive check (the reference may be sorted differently)
+    a = np.sort(np.round(ref.to_numpy(), 2), axis=0)
+    b = np.sort(np.round(ours.to_numpy(), 2), axis=0)
+    print("column-wise multiset match:", bool(np.allclose(a[:len(b)], b, rtol=1e-3)))
+sys.exit(0 if same_rows.all() else 1)
diff --git a/slurm/env_lichtenberg.sh b/slurm/env_lichtenberg.sh
new file mode 100644
index 0000000..9fb838d
--- /dev/null
+++ b/slurm/env_lichtenberg.sh
@@ -0,0 +1,22 @@
+#!/usr/bin/env bash
+# Shared environment for all gcda Slurm jobs on the TU Darmstadt Lichtenberg cluster.
+# Source this from the job scripts. Adjust the module names once to whatever
+# `module avail python` / `module avail gcc` list on the cluster (they change
+# between software stacks); everything else is self-contained.
+set -euo pipefail
+
+: "${GCDA_REPO:=$HOME/copula-simulator}"        # clone of this repository
+: "${GCDA_VENV:=$HOME/venvs/gcda}"              # virtual environment (created by slurm/setup_env.sh)
+: "${GCDA_OUT:=$GCDA_REPO/outputs/hpc}"         # results root (consider /work/scratch/$USER for large runs)
+
+module purge
+module load gcc python 2>/dev/null || module load python   # e.g. "module load gcc/11.2.0 python/3.11.4"
+
+source "$GCDA_VENV/bin/activate"
+cd "$GCDA_REPO"
+export WANDB_MODE=offline
+# one numerical thread per process; parallelism comes from Slurm tasks / arrays
+export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
+mkdir -p "$GCDA_OUT" logs
+python -c "import gcda, sys; print('python', sys.version.split()[0], 'gcda at', gcda.__file__)"
+git rev-parse HEAD
diff --git a/slurm/learned_indegree.slurm b/slurm/learned_indegree.slurm
new file mode 100644
index 0000000..b71db49
--- /dev/null
+++ b/slurm/learned_indegree.slurm
@@ -0,0 +1,14 @@
+#!/bin/bash
+#SBATCH -J gcda_indeg
+#SBATCH --mail-type=END,FAIL
+#SBATCH -A project_XXXXX            # <- your Lichtenberg project (see `csreport` / HPC portal)
+#SBATCH --output=logs/%x_%A_%a.out
+#SBATCH --error=logs/%x_%A_%a.err
+#SBATCH --array=0
+#SBATCH -n 1
+#SBATCH --cpus-per-task=4
+#SBATCH --mem-per-cpu=2000
+#SBATCH -t 03:00:00
+# Learned conditional vines at indegree 2-4 (Insurance, Alarm), jitter vs native, 10 held-out seeds.
+source slurm/env_lichtenberg.sh
+python scripts/run_experiments.py learned-indegree --seeds 10 --out "$GCDA_OUT/learned_indegree"
diff --git a/slurm/novel_dags.slurm b/slurm/novel_dags.slurm
new file mode 100644
index 0000000..a21707b
--- /dev/null
+++ b/slurm/novel_dags.slurm
@@ -0,0 +1,18 @@
+#!/bin/bash
+#SBATCH -J gcda_novel
+#SBATCH --mail-type=END,FAIL
+#SBATCH -A project_XXXXX            # <- your Lichtenberg project (see `csreport` / HPC portal)
+#SBATCH --output=logs/%x_%A_%a.out
+#SBATCH --error=logs/%x_%A_%a.err
+#SBATCH --array=0-9                 # 10 tasks x 20 random DAGs = 200 novel graphs
+#SBATCH -n 1
+#SBATCH --cpus-per-task=4
+#SBATCH --mem-per-cpu=2000
+#SBATCH -t 04:00:00                 # ~1.5 min per DAG (pooled + observational, 4 generators x 2 calibration modes)
+# RQ5 novel-graph study (Table 6.5): random DAGs over the Sachs variables.
+source slurm/env_lichtenberg.sh
+python scripts/run_experiments.py composition --n-dags 20 --dag-start $((SLURM_ARRAY_TASK_ID * 20)) --seeds 30 \
+    --out "$GCDA_OUT/novel_dags/task_$SLURM_ARRAY_TASK_ID"
+# merge: concatenate novel_dags_*_per_dag.csv over tasks, then
+#   python -c "import pandas as pd, glob; from gcda.experiments.composition import summarize_novel; ..."
+# (see docs/HPC_RUNBOOK.md, section 'novel-dags')
diff --git a/slurm/rq4_heldout.slurm b/slurm/rq4_heldout.slurm
new file mode 100644
index 0000000..b39a0d2
--- /dev/null
+++ b/slurm/rq4_heldout.slurm
@@ -0,0 +1,17 @@
+#!/bin/bash
+#SBATCH -J gcda_rq4
+#SBATCH --mail-type=END,FAIL
+#SBATCH -A project_XXXXX            # <- your Lichtenberg project (see `csreport` / HPC portal)
+#SBATCH --output=logs/%x_%A_%a.out
+#SBATCH --error=logs/%x_%A_%a.err
+#SBATCH --array=0-4                 # 5 tasks x 10 seeds = 50 seeds
+#SBATCH -n 1
+#SBATCH --cpus-per-task=4
+#SBATCH --mem-per-cpu=2000
+#SBATCH -t 04:00:00
+# Held-out RQ4 (Table 6.4): discrete/mixed network reconstruction, jitter vs native vs CPT refit.
+source slurm/env_lichtenberg.sh
+START=$((SLURM_ARRAY_TASK_ID * 10))
+python scripts/run_experiments.py rq4 --graphs asia insurance alarm mixed_scm --seeds 10 --seed-start $START \
+    --out "$GCDA_OUT/rq4/task_$SLURM_ARRAY_TASK_ID"
+# after all tasks:  python scripts/merge_results.py rq4 $GCDA_OUT/rq4/task_* --out $GCDA_OUT/rq4/merged
diff --git a/slurm/rq6_heldout.slurm b/slurm/rq6_heldout.slurm
new file mode 100644
index 0000000..25a6ed9
--- /dev/null
+++ b/slurm/rq6_heldout.slurm
@@ -0,0 +1,21 @@
+#!/bin/bash
+#SBATCH -J gcda_rq6
+#SBATCH --mail-type=END,FAIL
+#SBATCH -A project_XXXXX            # <- your Lichtenberg project (see `csreport` / HPC portal)
+#SBATCH --output=logs/%x_%A_%a.out
+#SBATCH --error=logs/%x_%A_%a.err
+#SBATCH --array=0-9                 # 10 tasks x 10 seeds = 100 evaluation seeds per graph
+#SBATCH -n 1
+#SBATCH --cpus-per-task=4
+#SBATCH --mem-per-cpu=2000          # MB; peak ~3 GB (Alarm, 5 sources)
+#SBATCH -t 06:00:00                 # measured locally: ~4 min/seed Insurance, ~3 min/seed Alarm (4 cores)
+# Held-out RQ6 (Table 6.6/Fig. 6.10): PC + SHD on SCM, Asia, Insurance, Alarm; 100 seeds.
+# ALGO=ges sbatch slurm/rq6_heldout.slurm   runs the same with GES instead of PC.
+source slurm/env_lichtenberg.sh
+ALGO=${ALGO:-pc}
+SEEDS_PER_TASK=10
+START=$((SLURM_ARRAY_TASK_ID * SEEDS_PER_TASK))
+python scripts/run_experiments.py rq6 --graphs synthetic_scm asia insurance alarm \
+    --seeds $SEEDS_PER_TASK --seed-start $START --algorithm $ALGO \
+    --out "$GCDA_OUT/rq6_$ALGO/task_$SLURM_ARRAY_TASK_ID"
+# after all tasks:  python scripts/merge_results.py rq6 $GCDA_OUT/rq6_$ALGO/task_* --out $GCDA_OUT/rq6_$ALGO/merged
diff --git a/slurm/setup_env.sh b/slurm/setup_env.sh
new file mode 100644
index 0000000..0bc7163
--- /dev/null
+++ b/slurm/setup_env.sh
@@ -0,0 +1,18 @@
+#!/usr/bin/env bash
+# One-time setup on a Lichtenberg login node (has internet access):
+#   bash slurm/setup_env.sh
+set -euo pipefail
+: "${GCDA_REPO:=$HOME/copula-simulator}"
+: "${GCDA_VENV:=$HOME/venvs/gcda}"
+module purge
+module load gcc python 2>/dev/null || module load python
+python3 -c 'import sys; assert sys.version_info >= (3, 10), "need Python >= 3.10: pick a newer python module"'
+python3 -m venv "$GCDA_VENV"
+source "$GCDA_VENV/bin/activate"
+pip install --upgrade pip
+cd "$GCDA_REPO"
+# exact versions that reproduced every thesis table; fall back to the unpinned
+# requirements if a pinned wheel is unavailable for the cluster's Python
+pip install -r requirements-lock.txt || pip install -r requirements.txt
+pip install -e . --no-deps
+pytest -q
diff --git a/slurm/sweep_and_rebuild.slurm b/slurm/sweep_and_rebuild.slurm
new file mode 100644
index 0000000..45a12f6
--- /dev/null
+++ b/slurm/sweep_and_rebuild.slurm
@@ -0,0 +1,33 @@
+#!/bin/bash
+#SBATCH -J gcda_repro
+#SBATCH --mail-type=END,FAIL
+#SBATCH -A project_XXXXX            # <- your Lichtenberg project (see `csreport` / HPC portal)
+#SBATCH --output=logs/%x_%A_%a.out
+#SBATCH --error=logs/%x_%A_%a.err
+#SBATCH --array=0
+#SBATCH -n 1
+#SBATCH --cpus-per-task=8
+#SBATCH --mem-per-cpu=1500
+#SBATCH -t 02:00:00
+# Full from-scratch reproduction: rebuild both dependency libraries, rerun every
+# thesis script and compare with the committed outputs (never done end-to-end
+# locally: the local audit reused the committed library JSON files).
+source slurm/env_lichtenberg.sh
+D="$GCDA_OUT/repro_$SLURM_JOB_ID"; mkdir -p "$D"
+cp -r outputs "$D/committed_outputs"
+python t3_validation.py
+python scripts/build_dependency_library.py
+python scripts/build_discrete_library.py
+python scripts/sweep_hyperparameters.py --output-dir "$D/sweep"
+python scripts/check_reproduction.py "$D/sweep/sweep_dependency_models.csv" "$D/committed_outputs/sweep_dependency_models.csv"
+python scripts/evaluate_generation.py         > "$D/evaluate_generation.txt"
+python scripts/evaluate_discrete_generation.py > "$D/evaluate_discrete_generation.txt"
+python scripts/evaluate_mixed_generation.py    > "$D/evaluate_mixed_generation.txt"
+python scripts/evaluate_causal_discovery.py    > "$D/evaluate_causal_discovery.txt"
+python - <<'PY'
+import json, hashlib, pathlib
+for f in ["outputs/dependency_library.json", "outputs/discrete_dependency_library.json"]:
+    new = json.loads(pathlib.Path(f).read_text())
+    print(f, "pairwise:", len(new["pairwise"]), "conditional:", len(new["conditional"]))
+PY
+git diff --stat -- outputs/   # any change vs the committed artifacts is a reproducibility finding
diff --git a/smoke_test.py b/smoke_test.py
index 0e967a4..bbb7188 100644
--- a/smoke_test.py
+++ b/smoke_test.py
@@ -4,7 +4,11 @@ from scipy.stats import kendalltau
 import wandb
 
 # Initialize logging
-wandb.init(project="graph-conditioned-augmentation", name="smoke-test")
+import os
+
+# offline by default so the smoke test runs without credentials;
+# set WANDB_MODE=online (and `wandb login`) to sync
+wandb.init(project="graph-conditioned-augmentation", name="smoke-test", mode=os.environ.get("WANDB_MODE", "offline"))
 
 # Step 1: generate synthetic data
 SEED = 42
diff --git a/t3_validation.py b/t3_validation.py
index a501ded..5d04951 100644
--- a/t3_validation.py
+++ b/t3_validation.py
@@ -36,6 +36,7 @@ from pathlib import Path
 import numpy as np
 import pyvinecopulib as pv
 from scipy.stats import kendalltau, spearmanr
+from gcda.compat import bicop_sample
 
 N_SAMPLES = 3000
 SEED = 42
@@ -80,7 +81,7 @@ def validate_case(case: ToyCase, seed: int) -> dict:
 
     # i. Generate synthetic data with known dependence.
     true_cop = pv.Bicop(family=case.family, parameters=case.true_params)
-    u_true = true_cop.simulate(N_SAMPLES, seeds=[seed, seed + 1, seed + 2])
+    u_true = bicop_sample(true_cop, N_SAMPLES, seeds=[seed, seed + 1, seed + 2])
     tau_true_theoretical = true_cop.tau
     tau_true_empirical = kendalltau(u_true[:, 0], u_true[:, 1])[0]
     rho_true_empirical = spearmanr(u_true[:, 0], u_true[:, 1])[0]
@@ -99,7 +100,7 @@ def validate_case(case: ToyCase, seed: int) -> dict:
     tau_fit_ok = abs(fitted_cop.tau - tau_true_theoretical) < TAU_TOL
 
     # iii. Sample new data from the fitted copula and compare dependence stats.
-    u_sim = fitted_cop.simulate(N_SAMPLES, seeds=[seed + 10, seed + 11, seed + 12])
+    u_sim = bicop_sample(fitted_cop, N_SAMPLES, seeds=[seed + 10, seed + 11, seed + 12])
     tau_sim = kendalltau(u_sim[:, 0], u_sim[:, 1])[0]
     rho_sim = spearmanr(u_sim[:, 0], u_sim[:, 1])[0]
     tau_sim_ok = abs(tau_sim - tau_true_empirical) < TAU_TOL
diff --git a/tests/test_datasets.py b/tests/test_datasets.py
index b61a5ee..2a1d043 100644
--- a/tests/test_datasets.py
+++ b/tests/test_datasets.py
@@ -57,3 +57,40 @@ def test_make_mixed_synthetic_scm_has_continuous_and_discrete_columns():
     # x5 has one discrete parent (x2) and one continuous parent (x4) - the
     # mixed-type 2-parent edge this dataset exists to exercise.
     assert set(dag.predecessors("x5")) == {"x2", "x4"}
+
+
+def test_sachs_observational_subset_and_condition_boundaries():
+    import numpy as np
+
+    from gcda.data.datasets import SACHS_OBSERVATIONAL_ROWS, load_sachs
+
+    full = load_sachs()
+    obs = load_sachs(observational_only=True)
+    assert len(full) == 7466 and len(obs) == SACHS_OBSERVATIONAL_ROWS == 853
+    # the file concatenates the nine Sachs et al. conditions (853, 902, 911, 723,
+    # 810, 799, 848, 913, 707 rows); every boundary shows a clear distribution
+    # shift, which is what justifies taking the first 853 rows as one condition.
+    x = np.log1p(full.to_numpy())
+    bounds = np.cumsum([853, 902, 911, 723, 810, 799, 848, 913])
+
+    def jump(i, w=200):
+        return np.abs(x[i - w:i].mean(0) - x[i:i + w].mean(0)).sum()
+
+    inside = [jump(i) for i in (400, 1300, 2200, 3000, 3800, 4600, 5400, 6300, 7100)]
+    assert min(jump(int(b)) for b in bounds) > np.median(inside)
+
+
+def test_sachs_consensus_dag_has_mek_with_three_parents():
+    from gcda.data.datasets import sachs_consensus_dag
+
+    dag = sachs_consensus_dag()
+    assert dag.number_of_edges() == 17
+    assert dag.in_degree("pmek") == 3
+
+
+def test_registry_loads_every_dataset_name():
+    from gcda.data.registry import DATASET_NAMES, load_dataset
+
+    for name in DATASET_NAMES:
+        df, dag, orders = load_dataset(name, n=200, seed=0) if name not in ("sachs", "sachs_observational", "uci_diabetes", "discretized_sachs") else load_dataset(name)
+        assert len(df) > 0
diff --git a/tests/test_graph_sampler.py b/tests/test_graph_sampler.py
index 3aa2bc2..cd081a2 100644
--- a/tests/test_graph_sampler.py
+++ b/tests/test_graph_sampler.py
@@ -128,3 +128,22 @@ def test_bicop_from_pairwise_entry_handles_independence():
     entry = {"family": "indep", "rotation": 0, "parameters": []}
     bicop = _bicop_from_pairwise_entry(entry)
     assert bicop.family.name == "indep"
+
+
+def test_hinv1_direction_matches_empirical_conditional_quantiles_of_clayton():
+    # thesis Sec. 3.4: which argument of h1/hinv1 is the conditioning value was
+    # checked by binning a large Clayton sample near a fixed conditioning value
+    import pyvinecopulib as pv
+
+    from gcda.compat import bicop_sample
+
+    cop = pv.Bicop(family=pv.BicopFamily.clayton, parameters=np.array([[3.0]]))
+    u = bicop_sample(cop, 600000, seeds=[1, 2, 3])
+    u1 = 0.2
+    near = u[np.abs(u[:, 0] - u1) < 0.002, 1]
+    for q in (0.1, 0.5, 0.9):
+        model_q = cop.hinv1(np.array([[u1, q]]))[0]
+        wrong_q = cop.hinv1(np.array([[q, u1]]))[0]  # arguments swapped
+        empirical = np.quantile(near, q)
+        assert abs(empirical - model_q) < 0.025
+        assert abs(empirical - wrong_q) > 4 * abs(empirical - model_q) or abs(empirical - wrong_q) > 0.1
diff --git a/tests/test_pairwise.py b/tests/test_pairwise.py
index 6e5e26d..09e32d7 100644
--- a/tests/test_pairwise.py
+++ b/tests/test_pairwise.py
@@ -3,11 +3,12 @@ import pandas as pd
 import pyvinecopulib as pv
 
 from gcda.dependency.pairwise import build_pairwise_library, fit_bicop
+from gcda.compat import bicop_sample
 
 
 def test_fit_bicop_recovers_known_gaussian_dependence():
     true_cop = pv.Bicop(family=pv.BicopFamily.gaussian, parameters=np.array([[0.6]]))
-    u = true_cop.simulate(3000, seeds=[1, 2, 3])
+    u = bicop_sample(true_cop, 3000, seeds=[1, 2, 3])
 
     fitted_cop, diagnostics = fit_bicop(u[:, 0], u[:, 1])
 
diff --git a/tests/test_preprocessing.py b/tests/test_preprocessing.py
index 996a148..d957dd6 100644
--- a/tests/test_preprocessing.py
+++ b/tests/test_preprocessing.py
@@ -139,3 +139,16 @@ def test_jitter_dilutes_tau_for_skewed_binary_variables_by_the_expected_factor()
     predicted = tau_b * np.sqrt((1 - tie_fraction(df["x"])) * (1 - tie_fraction(df["y"])))
     assert abs(tau_jittered - predicted) < 0.02
     assert tau_jittered < 0.5 * tau_b  # the dilution is substantial for this skew
+
+
+def test_pseudo_observations_of_a_permuted_column_invert_to_the_same_permutation():
+    # regression test for the scrambled-pseudo-observation bug (thesis Sec. 3.2/4.2):
+    # transforming a permuted copy must give the permuted pseudo-observations, and
+    # inverting must recover the permuted original values in that same order
+    rng = np.random.default_rng(7)
+    x = rng.gamma(2.0, size=1500)
+    perm = rng.permutation(len(x))
+    u_df, marginals = to_pseudo_observations(pd.DataFrame({"x": x}))
+    u_perm, marginals_perm = to_pseudo_observations(pd.DataFrame({"x": x[perm]}))
+    assert np.allclose(u_perm["x"].to_numpy(), u_df["x"].to_numpy()[perm])
+    assert np.allclose(marginals_perm["x"].inverse_transform(u_perm["x"].to_numpy()), x[perm])
diff --git a/tests/test_provenance.py b/tests/test_provenance.py
new file mode 100644
index 0000000..8863722
--- /dev/null
+++ b/tests/test_provenance.py
@@ -0,0 +1,8 @@
+from gcda.provenance import run_metadata, write_metadata
+
+
+def test_run_metadata_records_versions_and_extra_fields(tmp_path):
+    meta = run_metadata(seed=3)
+    assert meta["seed"] == 3 and "pyvinecopulib" in meta["packages"] and meta["python"]
+    path = write_metadata(tmp_path / "x.csv", note="hi")
+    assert path.name == "x.csv.meta.json" and '"note": "hi"' in path.read_text()
diff --git a/tests/test_remediation.py b/tests/test_remediation.py
new file mode 100644
index 0000000..93014fb
--- /dev/null
+++ b/tests/test_remediation.py
@@ -0,0 +1,281 @@
+"""Regression tests for the issues found in the thesis audit (thesis_audit/AUDIT_REPORT.md)."""
+
+import json
+import warnings
+
+import networkx as nx
+import numpy as np
+import pandas as pd
+import pyvinecopulib as pv
+import pytest
+from scipy.stats import kendalltau, ks_2samp, norm
+
+from gcda.cli import main as cli_main
+from gcda.data.preprocessing import to_pseudo_observations
+from gcda.dependency.composed import PairwiseProductConditional
+from gcda.dependency.conditional import ConditionalSampler, FallbackWarning
+from gcda.dependency.library import DependencyLibrary, LibraryFormatError
+from gcda.dependency.pairwise import build_pairwise_library, top_k_partners
+from gcda.evaluation.realism import energy_distance, gaussian_mmd, permutation_test
+from gcda.generation.graph_sampler import (
+    EdgeModel,
+    GraphSampler,
+    MarginalDriftWarning,
+    NodeSpec,
+    _bicop_from_pairwise_entry,
+    bind_pairwise_copula,
+    node_spec_from_library,
+    valid_baseline_rho,
+)
+from gcda.generation.spec import StrictModeError, build_node_specs
+from gcda.compat import bicop_sample
+
+
+def _toy_library(dataset="toy", seed=0, n=3000):
+    rng = np.random.default_rng(seed)
+    a = rng.normal(size=n)
+    b = rng.normal(size=n)
+    c = 0.7 * a + 0.4 * b + rng.normal(scale=0.5, size=n)
+    df = pd.DataFrame({"a": a, "b": b, "c": c})
+    u, m = to_pseudo_observations(df)
+    lib = DependencyLibrary()
+    lib.add_marginals(dataset, m)
+    lib.add_pairwise(build_pairwise_library(u, dataset))
+    lib.add_conditional(dataset, ConditionalSampler(child="c", parents=["a", "b"]).fit(u))
+    return lib, df
+
+
+# ---------------------------------------------------------------- I1: parent order
+def test_conditional_lookup_ignores_parent_order():
+    lib, _ = _toy_library()
+    assert lib.get_conditional_sampler("toy", "c", ["b", "a"]).parents == ["a", "b"]
+
+
+def test_same_dag_with_reordered_edges_gives_identical_samples():
+    lib, _ = _toy_library()
+    out = []
+    for edges in ([("a", "c"), ("b", "c")], [("b", "c"), ("a", "c")]):
+        dag = nx.DiGraph()
+        dag.add_nodes_from(["a", "b", "c"])
+        dag.add_edges_from(edges)
+        specs = {n: node_spec_from_library(lib, "toy", n, list(dag.predecessors(n))) for n in dag.nodes}
+        out.append(GraphSampler(dag, node_specs=specs).sample(2000, seed=3)[["a", "b", "c"]])
+    pd.testing.assert_frame_equal(out[0], out[1])
+
+
+def test_cli_generate_is_invariant_to_edge_order(tmp_path):
+    lib_path = tmp_path / "lib.json"
+    cli_main(["build-library", "--dataset", "synthetic_scm", "--output", str(lib_path)])
+    frames = []
+    for i, edges in enumerate(([["x1", "x4"], ["x2", "x4"]], [["x2", "x4"], ["x1", "x4"]])):
+        g = tmp_path / f"g{i}.json"
+        g.write_text(json.dumps({"edges": edges}))
+        out = tmp_path / f"o{i}.csv"
+        cli_main(["generate", "--dag", str(g), "--library", str(lib_path), "--dataset", "synthetic_scm",
+                  "--n", "2000", "--output", str(out)])
+        frames.append(pd.read_csv(out))
+        report = json.loads(out.with_name(out.name + ".report.json").read_text())
+        assert report["diagnostics"]["x4"]["model"] == "fitted-vine"
+    # node insertion order changes the topological order (hence the random
+    # stream), so compare distributions: before the fix the reordered graph
+    # silently fell back to a standard-normal marginal and baseline dependence
+    a, b = frames
+    assert abs(a["x4"].std() - b["x4"].std()) < 0.05
+    assert abs(kendalltau(a["x1"], a["x4"])[0] - kendalltau(b["x1"], b["x4"])[0]) < 0.04
+
+
+# ---------------------------------------------------------------- I2: merge + binding + CLI
+def test_merge_rejects_namespace_collisions_and_combines_libraries():
+    lib1, _ = _toy_library("d1")
+    lib2, _ = _toy_library("d2", seed=1)
+    merged = lib1.merge(lib2)
+    assert merged.datasets == ["d1", "d2"]
+    with pytest.raises(ValueError, match="both libraries"):
+        lib1.merge(lib1)
+
+
+def test_bind_pairwise_copula_transplants_dependence_and_orientation():
+    # asymmetric (Clayton) source copula, stored with the "parent" in the SECOND column
+    cop = pv.Bicop(family=pv.BicopFamily.clayton, parameters=np.array([[3.0]]))
+    u = bicop_sample(cop, 4000, seeds=[1, 2, 3])
+    lib = DependencyLibrary()
+    lib.add_pairwise(build_pairwise_library(pd.DataFrame({"y": u[:, 0], "x": u[:, 1]}), "src", pairs=[("y", "x")]))
+    edge = bind_pairwise_copula(lib, "src", source_parent="x", source_child="y")
+    assert edge.bicop_parent_is_first is False
+    dag = nx.DiGraph([("P", "C")])
+    gen = GraphSampler(dag, node_specs={"C": NodeSpec(edge_model=edge)}).sample(6000, seed=0)
+    assert abs(kendalltau(gen["P"], gen["C"])[0] - cop.tau) < 0.03
+
+
+def test_cli_generate_composes_two_libraries_with_cross_dataset_binding(tmp_path):
+    l1, l2 = tmp_path / "scm.json", tmp_path / "asia.json"
+    cli_main(["build-library", "--dataset", "synthetic_scm", "--output", str(l1)])
+    cli_main(["build-library", "--dataset", "asia", "--n", "3000", "--output", str(l2)])
+    spec = {
+        "nodes": {"x1": {"dataset": "synthetic_scm"}, "x4": {"dataset": "synthetic_scm"}, "dysp": {"dataset": "asia"}},
+        "edges": [["x1", "x4"], {"from": "x1", "to": "dysp", "copula": {"dataset": "asia", "pair": ["bronc", "dysp"]}}],
+    }
+    g = tmp_path / "g.json"
+    g.write_text(json.dumps(spec))
+    out = tmp_path / "o.csv"
+    cli_main(["generate", "--dag", str(g), "--library", str(l1), "--library", str(l2), "--n", "1000",
+              "--output", str(out), "--strict"])
+    df = pd.read_csv(out)
+    assert set(df["dysp"]) <= {"yes", "no"}
+    report = json.loads(out.with_name(out.name + ".report.json").read_text())
+    assert any("asia:bronc->dysp" in d["decision"] for d in report["decisions"])
+
+
+def test_strict_mode_rejects_baseline_fallbacks():
+    lib, _ = _toy_library()
+    with pytest.raises(StrictModeError):
+        build_node_specs(lib, {"edges": [["a", "zzz"]]}, default_dataset="toy", strict=True)
+
+
+# ---------------------------------------------------------------- I3: composition + drift
+def test_pairwise_product_conditional_matches_gaussian_theory_for_star_model():
+    # C -> P1, C -> P2 (parents of C in the *sampling* graph are conditionally independent
+    # given C), so the product of pairwise Gaussian copulas is the exact conditional.
+    r1, r2 = 0.7, 0.5
+    edges = [(pv.Bicop(family=pv.BicopFamily.gaussian, parameters=np.array([[r]])), True) for r in (r1, r2)]
+    s = PairwiseProductConditional("C", ["P1", "P2"], edges)
+    z = np.array([1.0, -0.5])
+    draws = norm.ppf(s.sample(np.tile(norm.cdf(z), (20000, 1)), seed=0))
+    prec = 1 + r1**2 / (1 - r1**2) + r2**2 / (1 - r2**2)
+    mean = (r1 * z[0] / (1 - r1**2) + r2 * z[1] / (1 - r2**2)) / prec
+    assert abs(draws.mean() - mean) < 0.03
+    assert abs(draws.var() - 1 / prec) < 0.03
+
+
+def test_compose_flag_builds_multi_parent_model_from_pairwise_blocks():
+    lib, _ = _toy_library()
+    lib.conditional = []
+    with pytest.raises(KeyError):
+        node_spec_from_library(lib, "toy", "c", ["a", "b"])
+    spec = node_spec_from_library(lib, "toy", "c", ["a", "b"], compose=True)
+    assert isinstance(spec.edge_model.conditional_sampler, PairwiseProductConditional)
+
+
+def test_calibrate_margins_reproduces_marginal_and_drift_is_flagged():
+    lib, df = _toy_library()
+    # dependent parents (a -> b) although the vine for c was fitted with independent a, b
+    dag = nx.DiGraph([("a", "b"), ("a", "c"), ("b", "c")])
+    specs = {n: node_spec_from_library(lib, "toy", n, list(dag.predecessors(n))) for n in dag.nodes}
+    specs["b"] = NodeSpec(marginal=lib.get_marginal("toy", "b"), edge_model=EdgeModel(
+        bicop=pv.Bicop(family=pv.BicopFamily.gaussian, parameters=np.array([[0.9]]))))
+    with pytest.warns(MarginalDriftWarning):
+        raw = GraphSampler(dag, node_specs=specs).sample(5000, seed=0)
+    cal = GraphSampler(dag, node_specs=specs, calibrate_margins=True).sample(5000, seed=0)
+    assert ks_2samp(cal["c"], df["c"]).statistic < ks_2samp(raw["c"], df["c"]).statistic
+    assert ks_2samp(cal["c"], df["c"]).statistic < 0.03
+
+
+# ---------------------------------------------------------------- I4: valid baseline
+def test_valid_baseline_rho_unchanged_up_to_three_parents_and_valid_beyond():
+    assert valid_baseline_rho(2) == 0.5 and valid_baseline_rho(3) == 0.5
+    for k in range(4, 9):
+        r = valid_baseline_rho(k)
+        corr = np.eye(k + 1)
+        corr[0, 1:] = corr[1:, 0] = r
+        assert np.linalg.eigvalsh(corr).min() > 0.05
+
+
+@pytest.mark.parametrize("k", [4, 5])
+def test_baseline_sampler_at_high_indegree_hits_theoretical_tau(k):
+    dag = nx.DiGraph([(f"P{i}", "X") for i in range(k)])
+    sampler = GraphSampler(dag, max_indegree=k)
+    df = sampler.sample(5000, seed=0)
+    target = 2 / np.pi * np.arcsin(valid_baseline_rho(k))
+    taus = [kendalltau(df[f"P{i}"], df["X"])[0] for i in range(k)]
+    assert abs(np.mean(taus) - target) < 0.02
+    assert sampler.total_fallback_draws == 0
+
+
+# ---------------------------------------------------------------- I7: fallback counters
+class _BrokenBicop:
+    def hinv1(self, u):
+        raise RuntimeError("boom")
+
+
+def test_fallback_counter_counts_each_failed_draw_once():
+    dag = nx.DiGraph([("A", "B"), ("B", "C")])
+    sampler = GraphSampler(dag, node_specs={"B": NodeSpec(edge_model=EdgeModel(bicop=_BrokenBicop()))})
+    with pytest.warns(FallbackWarning):
+        sampler.sample(300, seed=0)
+    assert sampler.fallback_counts_ == {"A": 0, "B": 300, "C": 0}
+    assert sampler.diagnostics_["B"]["fallback_draws"] == 300
+
+
+# ---------------------------------------------------------------- I15: distances
+def test_unbiased_distances_and_permutation_tests():
+    rng = np.random.default_rng(0)
+    x, y = rng.uniform(size=(400, 3)), rng.uniform(size=(400, 3))
+    z = rng.uniform(size=(400, 3)) ** 2
+    assert abs(energy_distance(x, y, unbiased=True)) < energy_distance(x, y)
+    assert permutation_test(energy_distance, x, y, n_permutations=99)["p_value"] > 0.05
+    assert permutation_test(gaussian_mmd, x, z, n_permutations=99)["p_value"] < 0.05
+
+
+# ---------------------------------------------------------------- I19/I20: validation
+def test_library_load_validates_structure_and_family_names(tmp_path):
+    bad = tmp_path / "bad.json"
+    bad.write_text(json.dumps({"pairwise": []}))
+    with pytest.raises(LibraryFormatError):
+        DependencyLibrary.load(bad)
+    with pytest.raises(ValueError, match="unknown copula family"):
+        _bicop_from_pairwise_entry({"family": "__class__", "rotation": 0, "parameters": []})
+
+
+def test_v1_libraries_without_schema_version_still_load():
+    lib = DependencyLibrary.from_payload({"pairwise": [], "conditional": [], "marginals": {}})
+    assert lib.pairwise == []
+
+
+def test_marginal_compression_keeps_quantiles():
+    lib, df = _toy_library()
+    _, m = to_pseudo_observations(df)
+    lib.add_marginals("small", m, max_points=200)
+    small = lib.get_marginal("small", "a")
+    assert len(small.sorted_values_) == 200
+    q = np.array([0.05, 0.5, 0.95])
+    assert np.allclose(small.inverse_transform(q), np.quantile(df["a"], q), atol=0.05)
+
+
+# ---------------------------------------------------------------- I18: parallel fitting
+def test_parallel_pairwise_fitting_matches_sequential():
+    lib, df = _toy_library()
+    u, _ = to_pseudo_observations(df)
+    seq = build_pairwise_library(u, "t")
+    par = build_pairwise_library(u, "t", n_jobs=3)
+    assert [(e["var_i"], e["var_j"], e["family"], round(e["tau"], 10)) for e in seq] == \
+           [(e["var_i"], e["var_j"], e["family"], round(e["tau"], 10)) for e in par]
+    assert top_k_partners(seq, "c", k=1) == ["a"]
+
+
+# ---------------------------------------------------------------- dilution identity (contribution 4)
+def test_jitter_dilution_formula_is_the_tau_a_identity():
+    rng = np.random.default_rng(0)
+    x = rng.integers(0, 2, size=3000)
+    y = np.where(rng.uniform(size=3000) < 0.1 + 0.3 * x, 1, 0)
+    n0 = 3000 * 2999 / 2
+
+    def tied(v):
+        _, c = np.unique(v, return_counts=True)
+        return (c * (c - 1) / 2).sum()
+
+    tau_b = kendalltau(x, y, variant="b")[0]
+    tau_a_direct = sum(np.sign(x[i] - x[i + 1:]) @ np.sign(y[i] - y[i + 1:]) for i in range(len(x))) / n0
+    predicted = tau_b * np.sqrt((1 - tied(x) / n0) * (1 - tied(y) / n0))
+    assert predicted == pytest.approx(tau_a_direct, abs=1e-12)
+
+
+def test_measure_generation_stability_ignores_unrelated_warnings():
+    from gcda.evaluation.discrete import measure_generation_stability
+
+    class Noisy(GraphSampler):
+        def sample(self, n, seed=None):
+            warnings.warn("some deprecation", UserWarning)
+            return super().sample(n, seed)
+
+    _, metrics = measure_generation_stability(Noisy(nx.DiGraph([("A", "B")])), n=200)
+    assert metrics["n_fallback_events"] == 0 and metrics["n_fallback_draws"] == 0

```