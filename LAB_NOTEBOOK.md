# Lab Notebook — Graph-Conditioned Causal Data Augmentation

T8a deliverable: a chronological record of decisions, what was verified
before being trusted, results, and bugs found (with root cause and fix) -
organized by task phase since that's how the work actually proceeded.
Each numeric result below was reproduced while writing this file, not
transcribed from memory.

## T1 — Setup

Conda environment (`environment.yml`) + `requirements.txt` pinned from a
working install. A smoke test (`smoke_test.py`) fits a Gaussian copula on
random uniform data and logs Kendall's tau (original vs. generated) to
W&B, to prove the fit → sample → log loop works before building anything
on top of it.

## T3 — Choose tools, validate on toy data

**Decision:** `pyvinecopulib` as the main copula/vine library. C++
backend, native AIC/BIC family selection (needed for T4c anyway), vine
support (needed for T4d/T5). No strong reason found to prefer the pure-
Python `copulas` package instead.

**Validation before trusting it:** generated toy data from known
Gaussian/Student-t/Clayton copulas, fit back, checked recovered
family/parameters/tau against the ground truth, then resampled from the
*fitted* copula and checked its dependence matched the original. All
three passed. One wrinkle: Student-t's degrees-of-freedom parameter
converges much more slowly than the correlation parameter (still ~10%
off at n=20000), so it needed a relative tolerance where the correlation
parameter only needed an absolute one - a real property of that
parameter, not a bug.

## T4 — Dependency library from real data

**Design:** rank-transform each column to U(0,1) via `EmpiricalMarginal`
(empirical CDF with (n+1) plotting positions, so pseudo-observations never
land exactly on 0 or 1), fit a bivariate copula per pair via
`Bicop.select` with AIC/BIC family selection, store family/parameters/tau
as JSON-serializable metadata.

**Bug found and fixed:** `to_pseudo_observations` called
`marginal.transform()` with no argument, which defaulted to transforming
the *sorted* array rather than the original row order - every pairwise
fit was silently being computed on scrambled data. This wasn't caught by
inspection; it surfaced as every pair in a sanity check showing
`tau ≈ 0.999` regardless of which variables were involved, which is what
prompted a closer look. Fixed by requiring the caller to pass the
original values explicitly.

**Results after the fix** (recognizable real structure recovered, not
just "a number came out"):
- Sachs: `praf`↔`pmek` came out as the strongest pair (tau=0.666,
  family=joe) - a known direct edge in the raf/mek/erk signaling cascade.
- UCI diabetes: `bmi` and `s5` came out as the two variables most
  dependent on `disease_progression` - matches that dataset's own
  documented strongest predictors.

**T4d, conditional sampling (child | 2 parents):** `pyvinecopulib`'s docs
describe conditional sampling via the inverse Rosenblatt transform but
don't spell out the exact recipe. Reverse-engineered and verified before
committing to it: building a D-vine with the child listed *first* in
`RVineStructure.from_order([...])` makes it the fully-conditioned
variable in the vine's internal processing order (verified empirically by
fixing one column at a time and observing which columns cascade); to draw
`child | parent1=p1, parent2=p2`, forward-transform (parents, placeholder)
through `rosenblatt`, overwrite the placeholder with fresh uniform noise,
then `inverse_rosenblatt` back. Verified against the closed-form Gaussian
conditional mean/variance for a known trivariate correlation matrix before
trusting it in code - matched to within Monte Carlo noise.

## T5 — Generate data for a given graph

`GraphSampler` samples a DAG in topological order: baseline Gaussian
dependence when no learned model is given (T5c.i), a fitted `pv.Bicop`'s
h-function inverse for indegree-1 edges (T5c.ii), the T4 conditional
sampler for indegree ≥2 (T5c.iii), with a try/except + non-finite check
around every node that falls back to an independent draw on failure
(T5c.iv).

**hinv1/hinv2 column convention** wasn't obvious from the docs either
(`h1(u1,u2) = P(U2≤u2|U1=u1)`, but which argument is the conditioning
value in `hinv1`'s input?). Verified against Clayton's known closed-form
conditional distribution (binned a huge Clayton sample near a fixed u1,
compared its empirical conditional quantiles of u2 to `hinv1`'s output)
before using it for real.

**Bug found and fixed:** reconstructing a `pv.Bicop` from a saved pairwise
entry crashed for the `indep` family. `.tolist()` on an "indep" copula's
(0,0)-shaped empty parameter array collapses it to a bare `[]`;
`np.array([])` then reconstructs as shape `(0,)`, not `(0,0)`, which
`pv.Bicop()`'s constructor rejects. Only surfaced when reconstructing
Asia's full network in T7, since earlier demos happened to avoid picking
an `indep`-selected pair. Fixed with an explicit reshape guard, added a
regression test.

**End-to-end check:** sampling the synthetic SCM's own DAG using T4's
models learned from its own data reproduced both the true marginal
statistics and *every* pairwise Kendall's tau (direct and induced through
the graph) closely; the Gaussian-everywhere baseline did not (uniform
tau≈0.33 on every edge regardless of the edge's true strength).

## T6 — Evaluation + hyperparameter sweeps

`realism.py`: marginals (KS statistic, decile quantile L1),
pairwise dependence (tau/rho), and a multivariate distance (energy
distance, MMD) computed in U-space so it isolates dependence-structure
realism rather than being dominated by whichever column has the largest
raw units. `graph_conditioning.py`: removing an edge collapses its
dependence towards zero; strengthening an edge's copula parameter
increases the resulting tau monotonically.

**Bug found and fixed:** `dependence_strength_sweep`'s rho-override only
applies to the indegree-1 sampling path (a single `pv.Bicop`); the first
demo call targeted a node that actually had 2 parents in the DAG, so the
override was silently ignored and tau stayed constant across every rho
value tested. Added a validation guard that raises clearly if the target
child doesn't have exactly one parent, instead of the previous silent
no-op.

**Sweep result:** on Sachs, allowing the full parametric family set
(vs. Gaussian-only) improved the fitted vine's AIC from -7769 to -13650 -
a large, genuine improvement, consistent with Sachs' pairwise fits mostly
selecting non-Gaussian families (`joe`, `student`, `gumbel`). On the more
linear/Gaussian-like datasets (diabetes, synthetic SCM) the improvement
was much smaller. AIC and BIC picked identical models everywhere in this
first pass - only after extending the sweep to discrete data (T7) did
AIC/BIC actually diverge on some runs.

## T7 (extension) — Mixed/discrete variables

**Decision:** continuize discrete/categorical columns to U(0,1) via
jittering (`CategoricalMarginal`: each observation of a category gets an
independent draw uniform on that category's empirical-CDF slice) rather
than implementing `pyvinecopulib`'s native discrete support directly. This
is one of the task plan's own suggested "simple and documented" options,
and it means *nothing* in T4/T5/T6 needs to change to handle discrete
data - once continuized, a discrete column is just another U(0,1) column.

**Datasets:** Asia (8 binary vars) and Insurance (27 categorical vars, max
indegree 3) are sampled from their real CPTs via `pgmpy`'s *bundled* BIF
files - discovered this after `bnlearn.com` (the canonical source) 403'd
through the network proxy; `pgmpy.utils.get_example_model` ships the same
networks as local `.bif.gz` files, no network needed at all.

**End-to-end check:** reconstructed the full Asia network from scratch;
every node's category frequencies matched the true data closely (mean
total-variation distance ≈0.003), with zero fallback events.

**Major finding (not a bug, but initially mischaracterized as one):**
jittering *dilutes* measured dependence relative to Kendall's tau-b, and
the dilution is severe for skewed/rare binary variables specifically. For
two variables with "tie probabilities" `t_x, t_y` (chance two random
draws share a category), the tau on the jittered data comes out close to
`tau_b(raw) * sqrt((1 - t_x)(1 - t_y))`. Derived this after noticing the
naive Gaussian baseline sometimes beat the "learned" model's edge
dependence on *ordinary* Asia edges (e.g. `smoke→lung`, tau_b=0.196 but
jittered tau=0.037) - not just the near-deterministic `either` node I'd
initially blamed. Verified the formula against 4 independent Asia edges
(predicted vs. observed jittered tau within 0.01 in every case) and
committed it as a regression test
(`test_jitter_dilutes_tau_for_skewed_binary_variables_by_the_expected_factor`).
A copula fit on jittered data is *correctly* fitting the diluted
dependence - the near-determinism of `either = tub OR lung` is an extreme
instance of the same mechanism (it's also a ~93/7 skewed split), not a
separate phenomenon.

## Audit pass — re-checking the T1-T7 checklist against the task plan

Asked directly "are you sure T1-T7 is fully done" rather than assuming
yes. Re-checked each scope bullet against the actual code and found five
real gaps, all fixed in a follow-up pass:

1. **Ordinal category order defaulted to alphabetical.** Insurance's
   `SocioEcon` (true order Prole<Middle<UpperMiddle<Wealthy),
   `RiskAversion` (Psychopath<Adventurous<Normal<Cautious) and `CarValue`
   have no relation to their alphabetical order - fitting a copula against
   the wrong order corrupts concordance for any pair involving them. Fixed
   by returning each dataset's true CPT state order and threading it
   through to `CategoricalMarginal`.
2. **"Mixed continuous+discrete" was only unit-tested**, never run
   end-to-end - Asia is all-binary, Insurance all-categorical. Added
   `make_mixed_synthetic_scm` (continuous→discrete edge, and a 2-parent
   node with one continuous + one discrete parent) and a dedicated
   end-to-end script.
3. **The hyperparameter sweep never covered discrete data.** Extended it
   to Asia and Insurance - this is what first revealed AIC and BIC
   actually diverging on the discrete datasets.
4. **No baseline comparison for the discrete pipeline**, unlike T6a's
   continuous one. Adding it (real marginal + baseline dependence, mirroring
   T6a) is what led directly to the jitter-dilution finding above - the
   comparison surfaced *why* baseline sometimes wins on individual edges.
   While fixing this, found and fixed the identical bug in T6's own
   `evaluate_generation.py`: its baseline always used a standard-normal
   marginal instead of the library's real one, conflating marginal
   mismatch with dependence-model quality in that comparison too.
5. **The 3-parent closed-form verification was done ad hoc during
   development and never committed as a test.** Committed it
   (`test_conditional_sampler_matches_gaussian_theory_with_three_parents`).

## Closing the loop — does it meet the actual goal?

Asked directly whether the tool meets the stated Goal/Objective, not just
the T1-T8 task checklist. Two things hadn't been checked yet:

**"Reuse learned dependencies as building blocks for *any* user-specified
graph"** - every existing demo happened to reconstruct a dataset's *own*
structure, which doesn't actually prove cross-dataset composability.
Tested it live: merged the continuous Sachs library and the discrete
Asia/Insurance library into one `DependencyLibrary`, built a graph
`praf → pmek, praf → dysp` (mixing a continuous Sachs pair with a discrete
Asia node, in a structure that never existed in either original dataset,
and deliberately treating `dysp` as a root rather than its real 2-parent
role). It sampled correctly. This is now also exposed directly through the
CLI (`gcda generate --dag <any graph>.json`).

**"Many ML methods for graph discovery need lots of training data" - is
the generated data actually usable for that?** Nothing before this point
had checked it; every prior evaluation validated statistical realism, not
the downstream use case. Ran the PC algorithm (`causal-learn`) on true
data vs. our generated data for known DAGs, compared recovered graphs to
the truth via Structural Hamming Distance (SHD; lower is better):

| source | continuous (synthetic SCM) mean SHD | discrete (Asia) mean SHD |
|---|---|---|
| true data | 1.25 | 6.50 |
| baseline (Gaussian everywhere) | 1.00 | 8.25 |
| learned (T4 models) | 1.00 | 6.75 |

(averaged over 4 data-generation seeds each - a single seed first made
"learned" look like it beat real data outright on Asia, which didn't hold
up once averaged, so the script reports the average rather than one draw.)

Continuous: all three tie at the theoretical floor (one edge orientation
PC can never identify from observational data alone, regardless of data
source). Discrete: learned-model data supports causal discovery almost as
well as real data, while the naive baseline is measurably worse - it
generates spurious edges because a single fixed correlation strength on
every edge violates the graph's true conditional-independence structure.
This is the result that actually validates the objective.

## T8 — Writing + final deliverables

- Renamed the project and package (`copula_simulator` → `gcda`,
  "copula-simulator" → "Graph-Conditioned Causal Data Augmentation")
  after the project's actual title was clarified - a full rename
  (directory move + import rewrite across every module/script/test), not
  just a documentation relabel.
- Added the `gcda` CLI (`build-library` / `generate` / `evaluate` /
  `sweep` subcommands) as the composable interface to the package;
  `scripts/*.py` remain the narrated, detailed versions of the same
  operations.
- Extracted the sweep's hyperparameters into `configs/sweep.yaml` so a
  sweep run is reproducible from a versioned config file rather than
  constants baked into a script.
- This lab notebook, a thesis-chapter outline, an end-to-end demo script,
  and a presentation outline (see `docs/`) close out the T8b.iv
  deliverable, alongside the actual repo/CLI/library artifacts above.
- `requirements.txt` and `pyproject.toml` were fixed for portability: the
  former pinned exact versions captured from this development sandbox,
  which uses a non-standard package index (`certifi==2026.6.17` and
  `click==8.4.1` don't exist on real PyPI) - installing from it failed
  outright on the Lichtenberg cluster. Replaced with an unpinned
  direct-dependency list; `pyproject.toml` previously declared no
  dependencies at all, so `pip install -e .` alone installed nothing.

## Cluster run - cross-environment reproducibility check

Ran the pipeline on the Lichtenberg cluster (Python 3.11, freshly
resolved dependency versions rather than this sandbox's pins) and
compared the generated `outputs/` against this environment's:

- **Continuous results matched exactly** (Sachs' `praf`-`pmek` fit,
  `synthetic_scm`'s sweep AIC/BIC, the indegree-cap sweep) - these never
  depend on any randomness beyond `numpy`'s seeded generator, which is
  bit-stable across versions/platforms for basic draws.
- **Discrete sweep results (Asia, Insurance) did not match**, and
  investigating why surfaced a real, previously-unnoticed bug:
  `sweep_hyperparameters.py`'s `run_dependency_sweep` called
  `to_pseudo_observations_mixed(...)` without a `seed`, so every run drew
  fresh OS-entropy jitter randomness for the categorical columns rather
  than a fixed one. This wasn't caught earlier because every other call
  site in the codebase (`build_discrete_library.py`,
  `evaluate_mixed_generation.py`, the CLI's `build-library` command) does
  pass `seed=0`, and the sweep's own continuous rows never exercised the
  bug at all - it took an independent cluster run producing *different*
  numbers from the exact same code and seed to surface it. Fixed by
  passing `seed=0`; verified by running the sweep twice in a row locally
  and confirming the discrete rows are now bit-identical, which they
  weren't before the fix. The qualitative conclusions (parametric family
  set beats Gaussian-only on both Asia and Insurance; AIC and BIC select
  different models on discrete data) held in every run regardless of this
  bug - only the exact fitted numbers varied.

## Post-audit remediation

An external-style audit of thesis, LaTeX source and code was turned into a
backlog and worked off; the resulting corrections are recorded in
`thesis_audit/THESIS_CHANGES.md` and `thesis_audit/CODE_CHANGES.md`.
Decisions worth recording:

- **Parent-order bug.** `get_conditional_sampler` matched the *ordered*
  parent list, so the same DAG written with its edges in a different order
  silently lost its fitted vine and (via the CLI fallback) its real
  marginal. Now matched by parent *set*; the sampler feeds parent columns in
  the vine's own order. Regression tests at library and CLI level.
- **Composition was mostly marginals.** The demo's cross-dataset edge used
  the ρ = 0.5 baseline. Added `DependencyLibrary.merge`, copula binding
  (`bind_pairwise_copula`, CLI graph spec with per-edge `copula`), and a
  pairwise-composed multi-parent model (`PairwiseProductConditional`,
  product of per-edge copula densities, exact under conditional
  independence of the parents given the child).
- **Compatibility of transplanted multi-parent models.** A vine fitted under
  one parent distribution does not reproduce the child's marginal under
  another (this is what drove the Insurance baseline's TVD, concentrated at
  multi-parent nodes - not "error propagation"). Added a per-node
  uniformity diagnostic (`MarginalDriftWarning`) and optional rank
  calibration (`calibrate_margins`).
- **Baseline validity.** ρ = 0.5 with k = 4 independent parents gives a
  singular correlation matrix (child deterministic), k ≥ 5 not PSD. Capped at
  `sqrt(0.9 / k)`; unchanged for k ≤ 3, so the original results stand.
- **Jitter dilution is the τ_a identity** (known in the discrete-copula
  literature), and it is fixable: pyvinecopulib's native discrete likelihood
  (`discrete_mode="native"`) removes most of the per-edge dependence loss.
- **Sachs data are pooled over nine experimental conditions**; the first
  853 rows are the CD3/CD28 condition (boundary evidence in
  `tests/test_datasets.py`; byte-level confirmation listed as a cluster/login
  task). 91% of `praf` values are ties (rounded measurements); the tie
  method does not change the praf-pmek fit (Joe, τ = 0.666 under max-rank,
  mid-rank and random tie-breaking), but the empirical τ_b of the raw data is
  0.616 - the 0.666 in the thesis is the fitted copula's τ.
- **Held-out evaluation.** Every new experiment fits on seed 10,000 and
  evaluates on seeds 0..n-1; the original RQ6 seed 1 reused the training data.
