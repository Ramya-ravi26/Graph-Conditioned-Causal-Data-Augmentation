"""T4a/T7b: the Phase 1 continuous datasets and the Phase 2 discrete/mixed datasets."""

import os
import warnings
from importlib import resources
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

# Bundled as package data (gcda/data/resources) so the loaders work from a
# regular (non-editable) install too; GCDA_DATA_DIR overrides the location.
SACHS_FILENAME = "sachs_continuous.csv"

# The CDT "cyto_full_data" file is the concatenation of the nine Sachs et al.
# (2005) experimental conditions; the first 853 rows are the CD3/CD28
# condition, the general-stimulation (observational) data used in most
# causal-discovery benchmarks.  See data/raw/README.md and
# tests/test_datasets.py for the consistency check.
SACHS_OBSERVATIONAL_ROWS = 853

# Consensus network of Sachs et al. (2005) as distributed by bnlearn/pgmpy,
# expressed in this dataset's column names.
SACHS_NAME_MAP = {
    "praf": "Raf", "pmek": "Mek", "plcg": "Plcg", "PIP2": "PIP2", "PIP3": "PIP3",
    "p44/42": "Erk", "pakts473": "Akt", "PKA": "PKA", "PKC": "PKC", "P38": "P38", "pjnk": "Jnk",
}


def _sachs_path() -> Path:
    override = os.environ.get("GCDA_DATA_DIR")
    if override:
        return Path(override) / SACHS_FILENAME
    return Path(str(resources.files("gcda.data").joinpath("resources", SACHS_FILENAME)))


def load_sachs(observational_only: bool = False) -> pd.DataFrame:
    """Sachs et al. (2005) protein-signaling dataset: 11 continuous variables.

    By default all 7,466 rows are returned. These pool the nine experimental
    conditions of the original study (one general stimulation + eight
    interventions), i.e. they are NOT i.i.d. observational data. Pass
    ``observational_only=True`` for the 853-row CD3/CD28 condition only.
    See data/raw/README.md for provenance and citation.
    """
    df = pd.read_csv(_sachs_path())
    if observational_only:
        df = df.iloc[:SACHS_OBSERVATIONAL_ROWS].reset_index(drop=True)
    return df


def sachs_consensus_dag() -> nx.DiGraph:
    """The bnlearn/pgmpy Sachs consensus network, relabelled to this dataset's columns."""
    model = _example_model("sachs")
    inverse = {v: k for k, v in SACHS_NAME_MAP.items()}
    dag = nx.DiGraph()
    dag.add_nodes_from(SACHS_NAME_MAP)
    dag.add_edges_from((inverse[a], inverse[b]) for a, b in model.edges())
    return dag


def load_uci_diabetes() -> pd.DataFrame:
    """UCI-style continuous dataset for robustness checks (10 features + target).

    Loaded via scikit-learn (no network access needed), all continuous.
    """
    from sklearn.datasets import load_diabetes

    bunch = load_diabetes(as_frame=True)
    df = bunch.frame.copy()
    df = df.rename(columns={"target": "disease_progression"})
    return df


def make_synthetic_scm(n: int = 2000, seed: int = 0) -> tuple[pd.DataFrame, nx.DiGraph]:
    """Synthetic SCM with a known ground-truth DAG (max indegree 2).

    Graph: X1 -> X3, X1 -> X4, X2 -> X4, X4 -> X5. X1, X2 are exogenous roots.
    X4 has two parents (X1, X2), matching the core T4d target. Noise on X5
    is Student-t to keep at least one non-Gaussian dependency in the mix.
    """
    rng = np.random.default_rng(seed)

    x1 = rng.normal(0, 1, size=n)
    x2 = rng.normal(0, 1, size=n)
    x3 = 0.8 * x1 + rng.normal(0, 0.5, size=n)
    x4 = 0.6 * x1 + 0.5 * x2 + rng.normal(0, 0.5, size=n)
    x5 = 0.7 * x4 + rng.standard_t(df=4, size=n) * 0.5

    df = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3, "x4": x4, "x5": x5})

    dag = nx.DiGraph()
    dag.add_nodes_from(df.columns)
    dag.add_edges_from([("x1", "x3"), ("x1", "x4"), ("x2", "x4"), ("x4", "x5")])
    return df, dag


def _example_model(name: str):
    """Load a bnlearn network bundled with pgmpy.

    `pgmpy.utils.get_example_model` (bundled BIF files, no network access) is
    deprecated and scheduled for removal in pgmpy 1.3, so pyproject pins
    pgmpy<1.3; if it is unavailable we fall back to its successor
    `pgmpy.example_models.load_model("bnlearn/<name>")`.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # pgmpy deprecation warnings
        try:
            from pgmpy.utils import get_example_model

            return get_example_model(name)
        except ImportError:  # pragma: no cover - pgmpy >= 1.3
            from pgmpy.example_models import load_model

            return load_model(f"bnlearn/{name}")


def _load_bnlearn_model(name: str, n_samples: int, seed: int) -> tuple[pd.DataFrame, nx.DiGraph, dict[str, list]]:
    """Sample a discrete Bayesian network bundled with pgmpy (no network access needed).

    Also returns each variable's state order exactly as defined in the network's
    CPTs. Several bnlearn variables are genuinely ordinal (e.g. Insurance's
    SocioEcon: Prole < Middle < UpperMiddle < Wealthy) and the CPT order is the
    authoritative one - falling back to alphabetical order would silently
    scramble it (e.g. RiskAversion's true order Psychopath/Adventurous/Normal/
    Cautious has no relation to its alphabetical order), corrupting which pairs
    of observations count as concordant/discordant for every copula fit
    involving that variable.
    """
    model = _example_model(name)

    dag = nx.DiGraph()
    dag.add_nodes_from(model.nodes())
    dag.add_edges_from(model.edges())
    category_orders = {node: list(model.get_cpds(node).state_names[node]) for node in dag.nodes}
    df = model.simulate(n_samples=n_samples, seed=seed, show_progress=False)
    return df[list(dag.nodes)].reset_index(drop=True), dag, category_orders


def load_asia(n_samples: int = 10000, seed: int = 0) -> tuple[pd.DataFrame, nx.DiGraph, dict[str, list]]:
    """Asia network (Lauritzen & Spiegelhalter, 1988): 8 binary variables, max
    indegree 2 - the small discrete benchmark for sanity checks (T7b.i).

    Returns (data, DAG, category_orders); category order doesn't matter for
    these binary variables, but is returned for interface consistency with
    `load_insurance`.
    """
    return _load_bnlearn_model("asia", n_samples=n_samples, seed=seed)


def load_alarm(n_samples: int = 10000, seed: int = 0) -> tuple[pd.DataFrame, nx.DiGraph, dict[str, list]]:
    """ALARM network (Beinlich et al., 1989): 37 discrete variables, max indegree 4.
    The task plan's alternative larger discrete benchmark (T7b.ii)."""
    return _load_bnlearn_model("alarm", n_samples=n_samples, seed=seed)


def load_insurance(n_samples: int = 10000, seed: int = 0) -> tuple[pd.DataFrame, nx.DiGraph, dict[str, list]]:
    """Insurance network (Binder et al., 1997): 27 categorical variables (2-5
    categories each), several genuinely ordinal - the larger discrete
    benchmark (T7b.ii). Returns (data, DAG, category_orders); pass
    category_orders through to `to_pseudo_observations_mixed` so ordinal
    variables are continuized in their real order, not alphabetically.
    """
    return _load_bnlearn_model("insurance", n_samples=n_samples, seed=seed)


def make_discretized_sachs(n_bins: int = 3) -> tuple[pd.DataFrame, dict[str, list]]:
    """Discretize the real continuous Sachs dataset into `n_bins` quantile bins
    per column, for stress-testing the discrete pipeline on real (if binned)
    dependence structure (T7b.iii). No ground-truth DAG is attached, same as
    the continuous `load_sachs()`.

    Every column uses the same ordinal bin order (low < medium < high, or
    q0 < q1 < ... for n_bins > 3); returned as `category_orders` since it's
    the same for every column but callers still need to pass it through to
    `to_pseudo_observations_mixed` (alphabetically "high" < "low" < "medium"
    would otherwise scramble the intended order).
    """
    labels = ["low", "medium", "high"][:n_bins] if n_bins <= 3 else [f"q{i}" for i in range(n_bins)]
    df = load_sachs()
    binned = df.apply(lambda col: pd.qcut(col, q=n_bins, labels=labels).astype(str))
    category_orders = {col: labels for col in binned.columns}
    return binned, category_orders


def make_mixed_synthetic_scm(n: int = 5000, seed: int = 0) -> tuple[pd.DataFrame, nx.DiGraph, dict[str, list]]:
    """Synthetic SCM with a known DAG that genuinely mixes continuous and
    discrete/categorical variables (T7a: "mixed continuous+discrete"),
    including a continuous->discrete edge and a 2-parent edge with one
    continuous and one discrete parent - neither is exercised by Asia
    (all-binary) or Insurance (all-categorical).

    Graph: x1 -> x2, x1 -> x4, x3 -> x4, x2 -> x5, x4 -> x5.
      x1: continuous root.
      x2: 3-level ordinal ("low"/"medium"/"high"), driven by x1 (continuous parent).
      x3: continuous root, independent of x1.
      x4: continuous, driven by x1 and x3 (2 continuous parents).
      x5: binary ("no"/"yes"), driven by x2 (discrete) and x4 (continuous) -
          a genuinely mixed-type 2-parent node.
    """
    rng = np.random.default_rng(seed)

    x1 = rng.normal(0, 1, size=n)
    x2_score = x1 + rng.normal(0, 0.6, size=n)
    x2 = pd.cut(x2_score, bins=[-np.inf, -0.5, 0.5, np.inf], labels=["low", "medium", "high"]).astype(str)
    x3 = rng.normal(0, 1, size=n)
    x4 = 0.6 * x1 + 0.5 * x3 + rng.normal(0, 0.5, size=n)

    x2_numeric = pd.Series(x2).map({"low": -1.0, "medium": 0.0, "high": 1.0}).to_numpy()
    x5_score = 0.9 * x2_numeric + 0.7 * x4 + rng.normal(0, 0.7, size=n)
    x5 = np.where(x5_score > np.median(x5_score), "yes", "no")

    df = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3, "x4": x4, "x5": x5})

    dag = nx.DiGraph()
    dag.add_nodes_from(df.columns)
    dag.add_edges_from([("x1", "x2"), ("x1", "x4"), ("x3", "x4"), ("x2", "x5"), ("x4", "x5")])

    category_orders = {"x2": ["low", "medium", "high"], "x5": ["no", "yes"]}
    return df, dag, category_orders
