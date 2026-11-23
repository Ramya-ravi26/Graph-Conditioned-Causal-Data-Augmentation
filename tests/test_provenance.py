from gcda.provenance import run_metadata, write_metadata


def test_run_metadata_records_versions_and_extra_fields(tmp_path):
    meta = run_metadata(seed=3)
    assert meta["seed"] == 3 and "pyvinecopulib" in meta["packages"] and meta["python"]
    path = write_metadata(tmp_path / "x.csv", note="hi")
    assert path.name == "x.csv.meta.json" and '"note": "hi"' in path.read_text()
