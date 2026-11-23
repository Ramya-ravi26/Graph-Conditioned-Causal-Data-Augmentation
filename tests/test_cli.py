import json

import pandas as pd
import pytest

from gcda.cli import main


def test_build_library_and_generate_for_a_novel_subgraph(tmp_path, capsys):
    lib_path = tmp_path / "lib.json"
    main(["build-library", "--dataset", "synthetic_scm", "--output", str(lib_path)])
    assert lib_path.exists()

    # a genuinely user-specified graph: a strict subset of synthetic_scm's
    # own nodes/edges, exercising "sample data for any user-specified graph"
    # rather than just replaying the dataset's own structure.
    dag_path = tmp_path / "dag.json"
    dag_path.write_text(json.dumps({"edges": [["x1", "x4"], ["x2", "x4"]]}))

    out_path = tmp_path / "generated.csv"
    main([
        "generate", "--dag", str(dag_path), "--library", str(lib_path),
        "--dataset", "synthetic_scm", "--n", "500", "--seed", "0", "--output", str(out_path),
    ])

    df = pd.read_csv(out_path)
    assert set(df.columns) == {"x1", "x2", "x4"}
    assert len(df) == 500


def test_generate_falls_back_gracefully_for_unknown_node(tmp_path, capsys):
    lib_path = tmp_path / "lib.json"
    main(["build-library", "--dataset", "synthetic_scm", "--output", str(lib_path)])

    dag_path = tmp_path / "dag.json"
    dag_path.write_text(json.dumps({"edges": [["x1", "brand_new_node"]]}))
    out_path = tmp_path / "generated.csv"

    main([
        "generate", "--dag", str(dag_path), "--library", str(lib_path),
        "--dataset", "synthetic_scm", "--n", "200", "--output", str(out_path),
    ])
    captured = capsys.readouterr()
    assert "brand_new_node" in captured.err

    df = pd.read_csv(out_path)
    assert df.shape == (200, 2)


def test_evaluate_reports_marginals_and_dependence(tmp_path, capsys):
    import numpy as np

    rng = np.random.default_rng(0)
    true_df = pd.DataFrame({"a": rng.normal(size=500), "b": rng.normal(size=500)})
    sim_df = pd.DataFrame({"a": rng.normal(size=500), "b": rng.normal(size=500)})
    true_path, sim_path = tmp_path / "true.csv", tmp_path / "sim.csv"
    true_df.to_csv(true_path, index=False)
    sim_df.to_csv(sim_path, index=False)

    main(["evaluate", "--true-csv", str(true_path), "--sim-csv", str(sim_path)])
    captured = capsys.readouterr()
    assert "marginals" in captured.out
    assert "pairwise dependence" in captured.out


def test_unknown_dataset_rejected_by_argument_parsing(tmp_path, capsys):
    # argparse's `choices=` on --dataset rejects this before it ever reaches
    # _load_dataset's own (otherwise unreachable) unknown-dataset check.
    with pytest.raises(SystemExit):
        main(["build-library", "--dataset", "not_a_real_dataset", "--output", str(tmp_path / "x.json")])
    assert "invalid choice" in capsys.readouterr().err
