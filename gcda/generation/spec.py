"""Turn a user graph specification into GraphSampler node specs.

Graph spec (JSON), all fields except "edges" optional:

    {
      "nodes": {"A": {"dataset": "sachs", "variable": "praf"},
                "B": {"dataset": "asia",  "variable": "dysp"}},
      "edges": [["A", "C"],
                {"from": "A", "to": "B",
                 "copula": {"dataset": "sachs", "pair": ["praf", "pmek"]}}]
    }

* A node maps to a (dataset, variable) in the library; it defaults to
  (default_dataset, node name). Its marginal comes from that entry.
* An edge's dependence is, in order of preference: an explicit "copula"
  binding (any learned pair, from any dataset, re-used for this edge: the
  first variable of "pair" plays the parent role); the learned pair copula
  of the two endpoints if both come from the same dataset; otherwise the
  Gaussian baseline (reported).
* A multi-parent node uses the fitted conditional vine for that parent set
  when all endpoints come from one dataset and such a vine exists;
  otherwise (compose=True) a PairwiseProductConditional built from the
  per-edge copulas above; otherwise the baseline Gaussian vine.

Every decision is recorded in the returned report, and strict=True turns any
baseline fallback into an error instead.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from gcda.dependency.composed import PairwiseProductConditional
from gcda.dependency.library import DependencyLibrary
from gcda.generation.graph_sampler import (
    DEFAULT_BASELINE_RHO,
    EdgeModel,
    NodeSpec,
    _bicop_from_pairwise_entry,
    baseline_bicop,
)


@dataclass
class EdgeSource:
    dataset: str
    parent_var: str
    child_var: str


class StrictModeError(RuntimeError):
    pass


def load_graph_spec(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def parse_graph_spec(spec: dict) -> tuple[nx.DiGraph, dict[str, dict], dict[tuple[str, str], dict]]:
    dag = nx.DiGraph()
    nodes = spec.get("nodes", [])
    node_map: dict[str, dict] = {}
    if isinstance(nodes, dict):
        dag.add_nodes_from(nodes)
        node_map = {k: (v or {}) for k, v in nodes.items()}
    else:
        dag.add_nodes_from(nodes)
    bindings: dict[tuple[str, str], dict] = {}
    for edge in spec["edges"]:
        if isinstance(edge, dict):
            u, v = edge["from"], edge["to"]
            if "copula" in edge:
                bindings[(u, v)] = edge["copula"]
        else:
            u, v = edge
        dag.add_edge(u, v)
    if not nx.is_directed_acyclic_graph(dag):
        raise ValueError("graph spec is not a DAG")
    return dag, node_map, bindings


def build_node_specs(
    library: DependencyLibrary,
    spec: dict,
    default_dataset: str | None = None,
    compose: bool = True,
    strict: bool = False,
    baseline_rho: float = DEFAULT_BASELINE_RHO,
) -> tuple[nx.DiGraph, dict[str, NodeSpec], list[dict]]:
    dag, node_map, bindings = parse_graph_spec(spec)
    source = {
        n: (node_map.get(n, {}).get("dataset", default_dataset), node_map.get(n, {}).get("variable", n))
        for n in dag.nodes
    }
    report: list[dict] = []

    def fallback(item: dict) -> None:
        report.append(item)
        if strict:
            raise StrictModeError(f"baseline fallback in strict mode: {item}")

    def edge_source(parent: str, child: str) -> EdgeSource | None:
        if (parent, child) in bindings:
            b = bindings[(parent, child)]
            return EdgeSource(b["dataset"], b["pair"][0], b["pair"][1])
        (dp, vp), (dc, vc) = source[parent], source[child]
        if dp is not None and dp == dc:
            try:
                library.get_pairwise_entry(dp, vp, vc)
                return EdgeSource(dp, vp, vc)
            except KeyError:
                return None
        return None

    node_specs: dict[str, NodeSpec] = {}
    for node in nx.topological_sort(dag):
        ds, var = source[node]
        marginal = None
        if ds is not None and library.has_marginal(ds, var):
            marginal = library.get_marginal(ds, var)
        else:
            fallback({"node": node, "what": "marginal", "decision": "standard-normal baseline marginal"})
        parents = list(dag.predecessors(node))
        edge_model = None
        if len(parents) == 1:
            es = edge_source(parents[0], node)
            if es is None:
                fallback({"node": node, "what": f"edge {parents[0]}->{node}", "decision": "baseline Gaussian copula"})
            else:
                entry = library.get_pairwise_entry(es.dataset, es.parent_var, es.child_var)
                edge_model = EdgeModel(
                    bicop=_bicop_from_pairwise_entry(entry),
                    bicop_parent_is_first=entry["var_i"] == es.parent_var,
                    source=f"pairwise:{es.dataset}:{es.parent_var}->{es.child_var}",
                )
                report.append({"node": node, "what": f"edge {parents[0]}->{node}", "decision": edge_model.source})
        elif len(parents) >= 2:
            edge_model = _multi_parent_model(library, node, parents, source, bindings, edge_source, compose, baseline_rho, report, fallback)
        node_specs[node] = NodeSpec(marginal=marginal, edge_model=edge_model)
    return dag, node_specs, report


def _multi_parent_model(library, node, parents, source, bindings, edge_source, compose, baseline_rho, report, fallback):
    ds, var = source[node]
    same_ds = all(source[p][0] == ds for p in parents) and not any((p, node) in bindings for p in parents)
    if same_ds and ds is not None:
        by_var = {source[p][1]: p for p in parents}
        try:
            sampler = library.get_conditional_sampler(ds, var, list(by_var))
            order = [by_var[v] for v in sampler.parents]
            report.append({"node": node, "what": "parents", "decision": f"fitted vine {ds}:{var}|{sampler.parents}"})
            return EdgeModel(conditional_sampler=sampler, parent_order=order, source="fitted-vine")
        except KeyError:
            pass
    if not compose:
        fallback({"node": node, "what": "parents", "decision": "baseline Gaussian vine (no fitted vine, compose disabled)"})
        return None
    edges, used = [], []
    for p in parents:
        es = edge_source(p, node)
        if es is None:
            fallback({"node": node, "what": f"edge {p}->{node}", "decision": "baseline Gaussian copula inside composed model"})
            edges.append((baseline_bicop(baseline_rho), False))
            used.append("baseline")
        else:
            entry = library.get_pairwise_entry(es.dataset, es.parent_var, es.child_var)
            edges.append((_bicop_from_pairwise_entry(entry), entry["var_i"] == es.child_var))
            used.append(f"{es.dataset}:{es.parent_var}->{es.child_var}")
    report.append({"node": node, "what": "parents", "decision": f"composed from pairwise {used}"})
    sampler = PairwiseProductConditional(child=node, parents=parents, edges=edges)
    return EdgeModel(conditional_sampler=sampler, parent_order=list(parents), source="composed")
