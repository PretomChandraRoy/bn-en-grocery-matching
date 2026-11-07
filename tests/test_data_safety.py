"""Safety checks on the data folders.

Real collected data lives in local/ (never committed) and in data/raw (tracked by DVC, not by
Git). These tests fail if Git ever tracks a file in either place, and they validate every file
that is in data/raw on this machine.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from src.collect.validate import RAW_DIR, validate_file

REPO_DIR = Path(__file__).resolve().parent.parent


def test_git_tracks_nothing_under_local_or_data_raw() -> None:
    git = shutil.which("git")
    if git is None or not (REPO_DIR / ".git").exists():
        pytest.skip("Git or the .git folder is not available")
    tracked = subprocess.run(
        [git, "ls-files", "--", "local", "data/raw"],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert tracked == []


def test_every_file_in_data_raw_is_valid() -> None:
    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        pytest.skip("data/raw holds no CSV files (for example in a fresh clone before dvc pull)")
    problems = {
        path.name: [problem.describe() for problem in validate_file(path).errors] for path in files
    }
    assert {name: found for name, found in problems.items() if found} == {}
