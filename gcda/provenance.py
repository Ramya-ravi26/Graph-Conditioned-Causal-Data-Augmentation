"""Run metadata attached to every generated artifact (library, sweep, evaluation).

Records the package versions, Python version, platform, git commit and the
arguments/seeds of a run, so a number in the thesis can be traced back to the
exact code and environment that produced it.
"""

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

_PACKAGES = ["numpy", "scipy", "pandas", "networkx", "pyvinecopulib", "pgmpy", "causal-learn", "scikit-learn"]


def _git_sha() -> str | None:
    try:
        root = Path(__file__).resolve().parent.parent
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=5)
        sha = out.stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, timeout=5)
        return sha + ("+dirty" if dirty.stdout.strip() else "") if sha else None
    except Exception:  # noqa: BLE001 - provenance must never break a run
        return None


def run_metadata(**extra) -> dict:
    versions = {}
    for pkg in _PACKAGES:
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            versions[pkg] = None
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_sha": _git_sha(),
        "packages": versions,
        "argv": sys.argv,
        **extra,
    }


def write_metadata(path: str | Path, **extra) -> Path:
    """Write `<path>.meta.json` next to an output file and return its path."""
    path = Path(path)
    meta_path = path.with_name(path.name + ".meta.json")
    meta_path.write_text(json.dumps(run_metadata(output=path.name, **extra), indent=2, default=str))
    return meta_path
