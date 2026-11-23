import numpy as np
import pandas as pd

from gcda.data.preprocessing import to_pseudo_observations
from gcda.dependency.conditional import ConditionalSampler
from gcda.dependency.library import DependencyLibrary
from gcda.dependency.pairwise import build_pairwise_library


def test_dependency_library_save_load_roundtrip(tmp_path):
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "a": rng.normal(size=2000),
            "b": rng.normal(size=2000),
            "c": rng.normal(size=2000),
        }
    )
    u_df, marginals = to_pseudo_observations(df)

    library = DependencyLibrary()
    library.add_marginals("toy", marginals)
    library.add_pairwise(build_pairwise_library(u_df, dataset_name="toy"))

    sampler = ConditionalSampler(child="c", parents=["a", "b"]).fit(u_df)
    library.add_conditional("toy", sampler)

    path = tmp_path / "library.json"
    library.save(path)
    loaded = DependencyLibrary.load(path)

    assert len(loaded.pairwise) == len(library.pairwise)
    assert len(loaded.conditional) == 1

    restored_marginal = loaded.get_marginal("toy", "a")
    x = df["a"].to_numpy()
    assert np.allclose(restored_marginal.inverse_transform(restored_marginal.transform(x)), x)

    restored_sampler = loaded.get_conditional_sampler("toy", "c", ["a", "b"])
    u_parents = u_df[["a", "b"]].to_numpy()[:100]
    out = restored_sampler.sample(u_parents, seed=0)
    assert out.shape == (100,)
    assert np.all((out > 0) & (out < 1))
