"""Regression tests for the issues found in the thesis audit (corrections listed in thesis_audit/)."""

import json
import warnings

import networkx as nx
import numpy as np
import pandas as pd
import pyvinecopulib as pv
import pytest
from scipy.stats import kendalltau, ks_2samp, norm

from gcda.cli import main as cli_main
from gcda.data.preprocessing import to_pseudo_observations
from gcda.dependency.composed import PairwiseProductConditional
from gcda.dependency.conditional import ConditionalSampler, FallbackWarning
from gcda.dependency.library import DependencyLibrary, LibraryFormatError
from gcda.dependency.pairwise import build_pairwise_library, top_k_partners
from gcda.evaluation.realism import energy_distance, gaussian_mmd, permutation_test
from gcda.generation.graph_sampler import (
    EdgeModel,
    GraphSampler,
    MarginalDriftWarning,
    NodeSpec,
    _bicop_from_pairwise_entry,
    bind_pairwise_copula,
    node_spec_from_library,
    valid_baseline_rho,
)
from gcda.generation.spec import StrictModeError, build_node_specs
from gcda.compat import bicop_sample


def _toy_library(dataset="toy", seed=0, n=3000):
    rng = np.random.default_rng(seed)
    a = rng.normal(size=n)
    b = rng.normal(size=n)
    c = 0.7 * a + 0.4 * b + rng.normal(scale=0.5, size=n)
    df = pd.DataFrame({"a": a, "b": b, "c": c})
    u, m = to_pseudo_observations(df)
    lib = DependencyLibrary()
    lib.add_marginals(dataset, m)
    lib.add_pairwise(build_pairwise_library(u, dataset))
    lib.add_conditional(dataset, ConditionalSampler(child="c", parents=["a", "b"]).fit(u))
    return lib, df


# ---------------------------------------------------------------- I1: parent order
def test_conditional_lookup_ignores_parent_order():
    lib, _ = _toy_library()
    assert lib.get_conditional_sampler("toy", "c", ["b", "a"]).parents == ["a", "b"]


def test_same_dag_with_reordered_edges_gives_identical_samples():
    lib, _ = _toy_library()
    out = []
    for edges in ([("a", "c"), ("b", "c")], [("b", "c"), ("a", "c")]):
        dag = nx.DiGraph()
        dag.add_nodes_from(["a", "b", "c"])
        dag.add_edges_from(edges)
        specs = {n: node_spec_from_library(lib, "toy", n, list(dag.predecessors(n))) for n in dag.nodes}
        out.append(GraphSampler(dag, node_specs=specs).sample(2000, seed=3)[["a", "b", "c"]])
    pd.testing.assert_frame_equal(out[0], out[1])


def test_cli_generate_is_invariant_to_edge_order(tmp_path):
    lib_path = tmp_path / "lib.json"
    cli_main(["build-library", "--dataset", "synthetic_scm", "--output", str(lib_path)])
    frames = []
    for i, edges in enumerate(([["x1", "x4"], ["x2", "x4"]], [["x2", "x4"], ["x1", "x4"]])):
        g = tmp_path / f"g{i}.json"
        g.write_text(json.dumps({"edges": edges}))
        out = tmp_path / f"o{i}.csv"
        cli_main(["generate", "--dag", str(g), "--library", str(lib_path), "--dataset", "synthetic_scm",
                  "--n", "2000", "--output", str(out)])
        frames.append(pd.read_csv(out))
        report = json.loads(out.with_name(out.name + ".report.json").read_text())
        assert report["diagnostics"]["x4"]["model"] == "fitted-vine"
    # node insertion order changes the topological order (hence the random
    # stream), so compare distributions: before the fix the reordered graph
    # silently fell back to a standard-normal marginal and baseline dependence
    a, b = frames
    assert abs(a["x4"].std() - b["x4"].std()) < 0.05
    assert abs(kendalltau(a["x1"], a["x4"])[0] - kendalltau(b["x1"], b["x4"])[0]) < 0.04


# ---------------------------------------------------------------- I2: merge + binding + CLI
def test_merge_rejects_namespace_collisions_and_combines_libraries():
    lib1, _ = _toy_library("d1")
    lib2, _ = _toy_library("d2", seed=1)
    merged = lib1.merge(lib2)
    assert merged.datasets == ["d1", "d2"]
    with pytest.raises(ValueError, match="both libraries"):
        lib1.merge(lib1)


def test_bind_pairwise_copula_transplants_dependence_and_orientation():
    # asymmetric (Clayton) source copula, stored with the "parent" in the SECOND column
    cop = pv.Bicop(family=pv.BicopFamily.clayton, parameters=np.array([[3.0]]))
    u = bicop_sample(cop, 4000, seeds=[1, 2, 3])
    lib = DependencyLibrary()
    lib.add_pairwise(build_pairwise_library(pd.DataFrame({"y": u[:, 0], "x": u[:, 1]}), "src", pairs=[("y", "x")]))
    edge = bind_pairwise_copula(lib, "src", source_parent="x", source_child="y")
    assert edge.bicop_parent_is_first is False
    dag = nx.DiGraph([("P", "C")])
    gen = GraphSampler(dag, node_specs={"C": NodeSpec(edge_model=edge)}).sample(6000, seed=0)
    assert abs(kendalltau(gen["P"], gen["C"])[0] - cop.tau) < 0.03


def test_cli_generate_composes_two_libraries_with_cross_dataset_binding(tmp_path):
    l1, l2 = tmp_path / "scm.json", tmp_path / "asia.json"
    cli_main(["build-library", "--dataset", "synthetic_scm", "--output", str(l1)])
    cli_main(["build-library", "--dataset", "asia", "--n", "3000", "--output", str(l2)])
    spec = {
        "nodes": {"x1": {"dataset": "synthetic_scm"}, "x4": {"dataset": "synthetic_scm"}, "dysp": {"dataset": "asia"}},
        "edges": [["x1", "x4"], {"from": "x1", "to": "dysp", "copula": {"dataset": "asia", "pair": ["bronc", "dysp"]}}],
    }
    g = tmp_path / "g.json"
    g.write_text(json.dumps(spec))
    out = tmp_path / "o.csv"
    cli_main(["generate", "--dag", str(g), "--library", str(l1), "--library", str(l2), "--n", "1000",
              "--output", str(out), "--strict"])
    df = pd.read_csv(out)
    assert set(df["dysp"]) <= {"yes", "no"}
    report = json.loads(out.with_name(out.name + ".report.json").read_text())
    assert any("asia:bronc->dysp" in d["decision"] for d in report["decisions"])


def test_strict_mode_rejects_baseline_fallbacks():
    lib, _ = _toy_library()
    with pytest.raises(StrictModeError):
        build_node_specs(lib, {"edges": [["a", "zzz"]]}, default_dataset="toy", strict=True)


# ---------------------------------------------------------------- I3: composition + drift
def test_pairwise_product_conditional_matches_gaussian_theory_for_star_model():
    # C -> P1, C -> P2 (parents of C in the *sampling* graph are conditionally independent
    # given C), so the product of pairwise Gaussian copulas is the exact conditional.
    r1, r2 = 0.7, 0.5
    edges = [(pv.Bicop(family=pv.BicopFamily.gaussian, parameters=np.array([[r]])), True) for r in (r1, r2)]
    s = PairwiseProductConditional("C", ["P1", "P2"], edges)
    z = np.array([1.0, -0.5])
    draws = norm.ppf(s.sample(np.tile(norm.cdf(z), (20000, 1)), seed=0))
    prec = 1 + r1**2 / (1 - r1**2) + r2**2 / (1 - r2**2)
    mean = (r1 * z[0] / (1 - r1**2) + r2 * z[1] / (1 - r2**2)) / prec
    assert abs(draws.mean() - mean) < 0.03
    assert abs(draws.var() - 1 / prec) < 0.03


def test_compose_flag_builds_multi_parent_model_from_pairwise_blocks():
    lib, _ = _toy_library()
    lib.conditional = []
    with pytest.raises(KeyError):
        node_spec_from_library(lib, "toy", "c", ["a", "b"])
    spec = node_spec_from_library(lib, "toy", "c", ["a", "b"], compose=True)
    assert isinstance(spec.edge_model.conditional_sampler, PairwiseProductConditional)


def test_calibrate_margins_reproduces_marginal_and_drift_is_flagged():
    lib, df = _toy_library()
    # dependent parents (a -> b) although the vine for c was fitted with independent a, b
    dag = nx.DiGraph([("a", "b"), ("a", "c"), ("b", "c")])
    specs = {n: node_spec_from_library(lib, "toy", n, list(dag.predecessors(n))) for n in dag.nodes}
    specs["b"] = NodeSpec(marginal=lib.get_marginal("toy", "b"), edge_model=EdgeModel(
        bicop=pv.Bicop(family=pv.BicopFamily.gaussian, parameters=np.array([[0.9]]))))
    with pytest.warns(MarginalDriftWarning):
        raw = GraphSampler(dag, node_specs=specs).sample(5000, seed=0)
    cal = GraphSampler(dag, node_specs=specs, calibrate_margins=True).sample(5000, seed=0)
    assert ks_2samp(cal["c"], df["c"]).statistic < ks_2samp(raw["c"], df["c"]).statistic
    assert ks_2samp(cal["c"], df["c"]).statistic < 0.03


# ---------------------------------------------------------------- I4: valid baseline
def test_valid_baseline_rho_unchanged_up_to_three_parents_and_valid_beyond():
    assert valid_baseline_rho(2) == 0.5 and valid_baseline_rho(3) == 0.5
    for k in range(4, 9):
        r = valid_baseline_rho(k)
        corr = np.eye(k + 1)
        corr[0, 1:] = corr[1:, 0] = r
        assert np.linalg.eigvalsh(corr).min() > 0.05


@pytest.mark.parametrize("k", [4, 5])
def test_baseline_sampler_at_high_indegree_hits_theoretical_tau(k):
    dag = nx.DiGraph([(f"P{i}", "X") for i in range(k)])
    sampler = GraphSampler(dag, max_indegree=k)
    df = sampler.sample(5000, seed=0)
    target = 2 / np.pi * np.arcsin(valid_baseline_rho(k))
    taus = [kendalltau(df[f"P{i}"], df["X"])[0] for i in range(k)]
    assert abs(np.mean(taus) - target) < 0.02
    assert sampler.total_fallback_draws == 0


# ---------------------------------------------------------------- I7: fallback counters
class _BrokenBicop:
    def hinv1(self, u):
        raise RuntimeError("boom")


def test_fallback_counter_counts_each_failed_draw_once():
    dag = nx.DiGraph([("A", "B"), ("B", "C")])
    sampler = GraphSampler(dag, node_specs={"B": NodeSpec(edge_model=EdgeModel(bicop=_BrokenBicop()))})
    with pytest.warns(FallbackWarning):
        sampler.sample(300, seed=0)
    assert sampler.fallback_counts_ == {"A": 0, "B": 300, "C": 0}
    assert sampler.diagnostics_["B"]["fallback_draws"] == 300


# ---------------------------------------------------------------- I15: distances
def test_unbiased_distances_and_permutation_tests():
    rng = np.random.default_rng(0)
    x, y = rng.uniform(size=(400, 3)), rng.uniform(size=(400, 3))
    z = rng.uniform(size=(400, 3)) ** 2
    assert abs(energy_distance(x, y, unbiased=True)) < energy_distance(x, y)
    assert permutation_test(energy_distance, x, y, n_permutations=99)["p_value"] > 0.05
    assert permutation_test(gaussian_mmd, x, z, n_permutations=99)["p_value"] < 0.05


# ---------------------------------------------------------------- I19/I20: validation
def test_library_load_validates_structure_and_family_names(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"pairwise": []}))
    with pytest.raises(LibraryFormatError):
        DependencyLibrary.load(bad)
    with pytest.raises(ValueError, match="unknown copula family"):
        _bicop_from_pairwise_entry({"family": "__class__", "rotation": 0, "parameters": []})


def test_v1_libraries_without_schema_version_still_load():
    lib = DependencyLibrary.from_payload({"pairwise": [], "conditional": [], "marginals": {}})
    assert lib.pairwise == []


def test_marginal_compression_keeps_quantiles():
    lib, df = _toy_library()
    _, m = to_pseudo_observations(df)
    lib.add_marginals("small", m, max_points=200)
    small = lib.get_marginal("small", "a")
    assert len(small.sorted_values_) == 200
    q = np.array([0.05, 0.5, 0.95])
    assert np.allclose(small.inverse_transform(q), np.quantile(df["a"], q), atol=0.05)


# ---------------------------------------------------------------- I18: parallel fitting
def test_parallel_pairwise_fitting_matches_sequential():
    lib, df = _toy_library()
    u, _ = to_pseudo_observations(df)
    seq = build_pairwise_library(u, "t")
    par = build_pairwise_library(u, "t", n_jobs=3)
    assert [(e["var_i"], e["var_j"], e["family"], round(e["tau"], 10)) for e in seq] == \
           [(e["var_i"], e["var_j"], e["family"], round(e["tau"], 10)) for e in par]
    assert top_k_partners(seq, "c", k=1) == ["a"]


# ---------------------------------------------------------------- dilution identity (contribution 4)
def test_jitter_dilution_formula_is_the_tau_a_identity():
    rng = np.random.default_rng(0)
    x = rng.integers(0, 2, size=3000)
    y = np.where(rng.uniform(size=3000) < 0.1 + 0.3 * x, 1, 0)
    n0 = 3000 * 2999 / 2

    def tied(v):
        _, c = np.unique(v, return_counts=True)
        return (c * (c - 1) / 2).sum()

    tau_b = kendalltau(x, y, variant="b")[0]
    tau_a_direct = sum(np.sign(x[i] - x[i + 1:]) @ np.sign(y[i] - y[i + 1:]) for i in range(len(x))) / n0
    predicted = tau_b * np.sqrt((1 - tied(x) / n0) * (1 - tied(y) / n0))
    assert predicted == pytest.approx(tau_a_direct, abs=1e-12)


def test_measure_generation_stability_ignores_unrelated_warnings():
    from gcda.evaluation.discrete import measure_generation_stability

    class Noisy(GraphSampler):
        def sample(self, n, seed=None):
            warnings.warn("some deprecation", UserWarning)
            return super().sample(n, seed)

    _, metrics = measure_generation_stability(Noisy(nx.DiGraph([("A", "B")])), n=200)
    assert metrics["n_fallback_events"] == 0 and metrics["n_fallback_draws"] == 0


# ---------------------------------------------------------------- native discrete mode
def test_native_discrete_fit_reproduces_observable_dependence_that_jitter_dilutes():
    # Native discrete fitting reproduces the observable (cell-probability) dependence;
    # with the family fixed to Gaussian it also recovers the latent (tetrachoric)
    # correlation. With free family selection the latent tau is NOT identified from a
    # 2x2 table (copulas of discrete data are not unique), so it is not asserted.
    import pyvinecopulib as pv

    from gcda.data.preprocessing import discrete_cdf_pairs, to_pseudo_observations_mixed
    from gcda.evaluation.discrete import cramers_v

    rng = np.random.default_rng(3)
    z = rng.multivariate_normal([0, 0], [[1, 0.7], [0.7, 1]], size=6000)
    df = pd.DataFrame({"a": np.where(z[:, 0] > 1.28, "yes", "no"),   # ~10% yes
                       "b": np.where(z[:, 1] > 1.28, "yes", "no")})
    orders = {"a": ["no", "yes"], "b": ["no", "yes"]}
    u_jit, marg = to_pseudo_observations_mixed(df, category_orders=orders, seed=0)
    up, lo, vt = discrete_cdf_pairs(df, marg)
    v_data = cramers_v(df["a"], df["b"])

    def simulated_v(entry):
        s = bicop_sample(_bicop_from_pairwise_entry(entry), 20000, seeds=[1, 2, 3])
        return cramers_v(marg["a"].inverse_transform(s[:, 0]), marg["b"].inverse_transform(s[:, 1]))

    native = build_pairwise_library(up, "t", u_minus_df=lo, var_types=vt)[0]
    jitter = build_pairwise_library(u_jit, "t")[0]
    gauss = build_pairwise_library(up, "t", u_minus_df=lo, var_types=vt, family_set=[pv.BicopFamily.gaussian])[0]
    assert abs(simulated_v(native) - v_data) < 0.04
    assert simulated_v(jitter) < 0.6 * v_data
    assert abs(gauss["tau"] - 2 / np.pi * np.arcsin(0.7)) < 0.05

    # conditional vine in native mode fits and samples without fallback
    df["c"] = np.where(z[:, 0] + z[:, 1] + rng.normal(size=6000) > 2.5, "yes", "no")
    orders["c"] = ["no", "yes"]
    _, marg = to_pseudo_observations_mixed(df, category_orders=orders, seed=0)
    up, lo, vt = discrete_cdf_pairs(df, marg)
    sampler = ConditionalSampler(child="c", parents=["a", "b"]).fit(up, lo, vt)
    out = sampler.sample(up[["a", "b"]].to_numpy()[:500], seed=0)
    assert out.shape == (500,) and sampler.last_fallback_count_ == 0
