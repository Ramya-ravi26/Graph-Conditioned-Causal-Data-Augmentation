"""Container for the T4 "dependency library": pairwise + conditional models plus marginals.

The library is the only interface between fitting and sampling. It is
JSON-serializable, indexed by ``dataset`` (a namespace) and variable name, and
can be merged with other libraries so that a single graph can draw building
blocks from several source datasets (see ``DependencyLibrary.merge``).
"""

import json
from pathlib import Path

import numpy as np

from gcda.data.preprocessing import CategoricalMarginal, EmpiricalMarginal
from gcda.dependency.conditional import ConditionalSampler

SCHEMA_VERSION = 2
_REQUIRED_KEYS = ("pairwise", "conditional", "marginals")


class LibraryFormatError(ValueError):
    """Raised when a serialized library does not have the expected structure."""


class DependencyLibrary:
    """Holds everything needed to later sample a graph (T5): fitted pairwise
    and conditional dependence models, plus per-dataset marginals so U-space
    samples can be mapped back to original units.
    """

    def __init__(self):
        self.pairwise: list[dict] = []
        self.conditional: list[dict] = []
        self.marginals: dict[str, dict[str, dict]] = {}
        self.metadata: dict = {}

    # ------------------------------------------------------------------ building
    def add_pairwise(self, entries: list[dict]) -> None:
        self.pairwise.extend(entries)

    def add_conditional(self, dataset: str, sampler: ConditionalSampler) -> None:
        self.conditional.append({"dataset": dataset, **sampler.to_dict()})

    def add_marginals(self, dataset: str, marginals: dict, max_points: int | None = None) -> None:
        """Store each column's marginal.

        ``max_points`` (optional) compresses an empirical marginal to that many
        quantile knots instead of storing every sorted observation; this keeps
        libraries small for large n at the cost of a piecewise-linear
        approximation of the quantile function between knots.
        """
        stored = {}
        for col, m in marginals.items():
            if isinstance(m, CategoricalMarginal):
                stored[col] = {"type": "categorical", "categories": list(m.categories_), "cum_probs": m.cum_probs_.tolist()}
                continue
            values, positions = m.sorted_values_, m.plotting_positions_
            if max_points is not None and len(values) > max_points:
                knots = np.linspace(positions[0], positions[-1], max_points)
                values = np.interp(knots, positions, values)
                positions = knots
            stored[col] = {
                "type": "empirical",
                "sorted_values": np.asarray(values).tolist(),
                "plotting_positions": np.asarray(positions).tolist(),
            }
        self.marginals[dataset] = stored

    # ------------------------------------------------------------------ lookup
    @property
    def datasets(self) -> list[str]:
        names = set(self.marginals) | {e["dataset"] for e in self.pairwise} | {e["dataset"] for e in self.conditional}
        return sorted(names)

    def has_marginal(self, dataset: str, column: str) -> bool:
        return column in self.marginals.get(dataset, {})

    def get_marginal(self, dataset: str, column: str):
        try:
            stored = self.marginals[dataset][column]
        except KeyError:
            raise KeyError(f"no marginal for {dataset}:{column}") from None
        if stored["type"] == "categorical":
            marginal = CategoricalMarginal()
            marginal.categories_ = stored["categories"]
            marginal.cum_probs_ = np.array(stored["cum_probs"])
            return marginal
        marginal = EmpiricalMarginal()
        marginal.sorted_values_ = np.array(stored["sorted_values"])
        marginal.plotting_positions_ = np.array(stored["plotting_positions"])
        return marginal

    def get_pairwise_entry(self, dataset: str, var_a: str, var_b: str) -> dict:
        """Return the fitted pairwise entry for the unordered pair {var_a, var_b}."""
        for entry in self.pairwise:
            if entry["dataset"] == dataset and {entry["var_i"], entry["var_j"]} == {var_a, var_b} and "error" not in entry:
                return entry
        raise KeyError(f"no pairwise model for {dataset}: {var_a} -- {var_b}")

    def get_conditional_sampler(self, dataset: str, child: str, parents: list[str]) -> ConditionalSampler:
        """Return the conditional model for ``child | parents``.

        Matching is on the *set* of parents: the returned sampler keeps its own
        fitted parent order in ``sampler.parents``, and callers must supply
        parent columns in that order (``GraphSampler`` does this automatically).
        An earlier version matched on the ordered list, so the same DAG written
        with its edges in a different order silently lost its learned model.
        """
        wanted = set(parents)
        for entry in self.conditional:
            if entry["dataset"] == dataset and entry["child"] == child and set(entry["parents"]) == wanted:
                return ConditionalSampler.from_dict(entry)
        raise KeyError(f"No conditional model for {dataset}: {child} | {sorted(parents)}")

    # ------------------------------------------------------------------ combining
    def merge(self, other: "DependencyLibrary", overwrite: bool = False) -> "DependencyLibrary":
        """Return a new library containing the models of ``self`` and ``other``.

        Dataset namespaces must not collide (two libraries both defining
        ``sachs`` would make every lookup ambiguous) unless ``overwrite=True``,
        in which case ``other`` wins for colliding namespaces.
        """
        clash = set(self.datasets) & set(other.datasets)
        if clash and not overwrite:
            raise ValueError(f"dataset namespaces present in both libraries: {sorted(clash)}")
        merged = DependencyLibrary()
        keep_self = [d for d in self.datasets if d not in clash] if overwrite else self.datasets
        merged.pairwise = [e for e in self.pairwise if e["dataset"] in keep_self] + list(other.pairwise)
        merged.conditional = [e for e in self.conditional if e["dataset"] in keep_self] + list(other.conditional)
        merged.marginals = {d: m for d, m in self.marginals.items() if d in keep_self}
        merged.marginals.update(other.marginals)
        merged.metadata = {"merged_from": [self.metadata, other.metadata]}
        return merged

    # ------------------------------------------------------------------ io
    def save(self, path: str | Path) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "metadata": self.metadata,
            "pairwise": self.pairwise,
            "conditional": self.conditional,
            "marginals": self.marginals,
        }
        Path(path).write_text(json.dumps(payload, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "DependencyLibrary":
        payload = json.loads(Path(path).read_text())
        return cls.from_payload(payload)

    @classmethod
    def from_payload(cls, payload: dict) -> "DependencyLibrary":
        if not isinstance(payload, dict) or any(k not in payload for k in _REQUIRED_KEYS):
            raise LibraryFormatError(f"library JSON must contain keys {_REQUIRED_KEYS}")
        version = payload.get("schema_version", 1)  # v1 files (thesis outputs) have no version field
        if version > SCHEMA_VERSION:
            raise LibraryFormatError(f"library schema_version {version} is newer than supported {SCHEMA_VERSION}")
        for entry in payload["pairwise"]:
            if not {"dataset", "var_i", "var_j"} <= set(entry):
                raise LibraryFormatError(f"malformed pairwise entry: {sorted(entry)}")
        for entry in payload["conditional"]:
            if not {"dataset", "child", "parents", "vine_json"} <= set(entry):
                raise LibraryFormatError(f"malformed conditional entry: {sorted(entry)}")
        library = cls()
        library.pairwise = payload["pairwise"]
        library.conditional = payload["conditional"]
        library.marginals = payload["marginals"]
        library.metadata = payload.get("metadata", {})
        return library

    @classmethod
    def load_many(cls, paths: list[str | Path]) -> "DependencyLibrary":
        """Load and merge several library files (namespaces must not collide)."""
        library = cls()
        for path in paths:
            library = library.merge(cls.load(path))
        return library
