"""Single registry of dataset loaders used by the CLI, the sweep and the experiments.

Each loader returns ``(df, dag_or_None, category_orders_or_None)``. Sample
sizes and seeds are explicit arguments, so different entry points that need
different sizes (the sweep historically used n=8000 for Asia/Insurance, the
library builder n=10000) state it instead of silently diverging.
"""

from gcda.data import datasets as ds

DEFAULT_N = {"synthetic_scm": 5000, "mixed_scm": 5000, "asia": 10000, "insurance": 10000, "alarm": 10000}
DEFAULT_SEED = {"synthetic_scm": 1, "mixed_scm": 1, "asia": 0, "insurance": 0, "alarm": 0}


def load_dataset(name: str, n: int | None = None, seed: int | None = None):
    n = n if n is not None else DEFAULT_N.get(name)
    seed = seed if seed is not None else DEFAULT_SEED.get(name)
    if name == "sachs":
        return ds.load_sachs(), ds.sachs_consensus_dag(), None
    if name == "sachs_observational":
        return ds.load_sachs(observational_only=True), ds.sachs_consensus_dag(), None
    if name == "uci_diabetes":
        return ds.load_uci_diabetes(), None, None
    if name == "discretized_sachs":
        df, orders = ds.make_discretized_sachs()
        return df, None, orders
    if name == "synthetic_scm":
        df, dag = ds.make_synthetic_scm(n=n, seed=seed)
        return df, dag, None
    if name == "mixed_scm":
        return ds.make_mixed_synthetic_scm(n=n, seed=seed)
    if name == "asia":
        return ds.load_asia(n_samples=n, seed=seed)
    if name == "insurance":
        return ds.load_insurance(n_samples=n, seed=seed)
    if name == "alarm":
        return ds.load_alarm(n_samples=n, seed=seed)
    raise KeyError(f"unknown dataset {name!r}; choose from {sorted(DATASET_NAMES)}")


DATASET_NAMES = [
    "sachs", "sachs_observational", "uci_diabetes", "discretized_sachs",
    "synthetic_scm", "mixed_scm", "asia", "insurance", "alarm",
]
