"""T4: build a pairwise + conditional "dependency library" from real continuous datasets.

Run: python scripts/build_dependency_library.py
Writes the library to outputs/dependency_library.json.
"""

from pathlib import Path

from gcda.data.datasets import load_sachs, load_uci_diabetes, make_synthetic_scm
from gcda.data.preprocessing import handle_missing_values, to_pseudo_observations
from gcda.dependency.conditional import ConditionalSampler
from gcda.dependency.library import DependencyLibrary
from gcda.dependency.pairwise import build_pairwise_library, top_k_partners
from gcda.provenance import run_metadata

OUTPUT_PATH = Path(__file__).parent.parent / "outputs" / "dependency_library.json"


def process_dataset(library: DependencyLibrary, name: str, df, conditional_child: str | None = None,
                     conditional_parents: list[str] | None = None) -> None:
    print(f"\n=== {name} ({df.shape[0]} rows, {df.shape[1]} vars) ===")
    clean, missing_report = handle_missing_values(df, strategy="drop")
    if missing_report["missing_counts"]:
        print(f"  missing values: {missing_report}")

    u_df, marginals = to_pseudo_observations(clean)
    library.add_marginals(name, marginals)

    pairwise_entries = build_pairwise_library(u_df, dataset_name=name)
    library.add_pairwise(pairwise_entries)
    n_ok = sum(1 for e in pairwise_entries if "error" not in e)
    print(f"  fit {n_ok}/{len(pairwise_entries)} pairwise models")

    if conditional_child is None:
        return
    if conditional_parents is None:
        conditional_parents = top_k_partners(pairwise_entries, conditional_child, k=2)
    print(f"  fitting conditional model: {conditional_child} | {conditional_parents}")
    sampler = ConditionalSampler(child=conditional_child, parents=conditional_parents)
    sampler.fit(u_df)
    library.add_conditional(name, sampler)

    # quick self-check: resampled child should reproduce dependence on each parent
    from scipy.stats import kendalltau

    u_sim = sampler.sample(u_df[conditional_parents].to_numpy(), seed=0)
    for parent in conditional_parents:
        tau_true = kendalltau(u_df[conditional_child], u_df[parent])[0]
        tau_sim = kendalltau(u_sim, u_df[parent])[0]
        print(f"    tau({conditional_child},{parent}): true={tau_true:.3f} resampled={tau_sim:.3f}")
    print(f"    fallback draws used: {sampler.last_fallback_count_}")


def main() -> None:
    library = DependencyLibrary()

    process_dataset(library, "sachs", load_sachs(), conditional_child="pmek")
    process_dataset(library, "uci_diabetes", load_uci_diabetes(), conditional_child="disease_progression")
    scm_df, scm_dag = make_synthetic_scm(n=5000, seed=1)
    process_dataset(
        library, "synthetic_scm", scm_df,
        conditional_child="x4", conditional_parents=["x1", "x2"],
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    library.metadata = run_metadata(script='build_dependency_library.py')
    library.save(OUTPUT_PATH)
    print(f"\nSaved dependency library ({len(library.pairwise)} pairwise, "
          f"{len(library.conditional)} conditional models) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
