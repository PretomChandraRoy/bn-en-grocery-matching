"""Safety checks on the data folders.

Real collected data lives in local/ (never committed) and in data/raw (tracked by DVC, not by
Git). These tests fail if Git ever tracks a file in either place, they validate every file that
is in data/raw on this machine, and they fail if a real title from local/ appears in any file that
could be committed. That last check is skipped when local/ holds no titles, for example in a
fresh clone. Its report names files and rows, never the titles themselves.
"""

import csv
import shutil
import subprocess
from pathlib import Path

import pytest

from src.collect.validate import RAW_DIR, validate_file

REPO_DIR = Path(__file__).resolve().parent.parent
LOCAL_DIR = REPO_DIR / "local"

# A title is found in a file if the whole title, or any run of this many words from it, appears
# in the file, ignoring case and spacing. A run must also be at least this long in characters.
RUN_WORDS = 3
MIN_RUN_CHARACTERS = 15
# Used only when Git is not available: folders that never hold files to commit.
SKIPPED_FOLDERS = frozenset(
    {".git", ".venv", "local", ".pytest_cache", ".ruff_cache", "__pycache__", ".dvc", "raw"}
)
MAX_FILE_BYTES = 5_000_000


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


# Finding real titles in files that could be committed.


def _normalise(text: str) -> str:
    """Return the text in lower case with every run of white space reduced to one space."""
    return " ".join(text.lower().split())


def _fragments(title: str) -> set[str]:
    """Return the whole title and every long enough run of words from it, normalised."""
    normalised = _normalise(title)
    words = normalised.split()
    runs = {" ".join(words[i : i + RUN_WORDS]) for i in range(len(words) - RUN_WORDS + 1)}
    return {fragment for fragment in {normalised, *runs} if len(fragment) >= MIN_RUN_CHARACTERS}


def find_leaks(titles: dict[str, str], texts: dict[str, str]) -> list[str]:
    """Find real titles that appear in file contents, without ever quoting a title.

    Args:
        titles: The real titles, each under a label such as "file.csv row 3".
        texts: The contents of the files to search, each under the file's path.

    Returns:
        One line for each file and title that match, naming the file and the title's label.
    """
    fragments = {label: _fragments(title) for label, title in titles.items()}
    leaks = []
    for path, text in sorted(texts.items()):
        normalised = _normalise(text)
        for label, parts in sorted(fragments.items()):
            if any(part in normalised for part in parts):
                leaks.append(f"{path} contains a title from {label}")
    return leaks


def read_local_titles(directory: Path = LOCAL_DIR) -> dict[str, str]:
    """Read the title_raw values from every CSV file in a folder, labelled by file and row."""
    titles: dict[str, str] = {}
    if not directory.is_dir():
        return titles
    for path in sorted(directory.glob("*.csv")):
        with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
            for number, row in enumerate(csv.DictReader(handle), start=2):
                title = row.get("title_raw") or ""
                if title.strip():
                    titles[f"{path.name} row {number}"] = title
    return titles


def _files_that_could_be_committed() -> list[Path]:
    """Return the files Git tracks or could add: everything except ignored files."""
    git = shutil.which("git")
    if git is not None and (REPO_DIR / ".git").exists():
        listed = subprocess.run(
            [git, "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=REPO_DIR,
            capture_output=True,
            check=True,
        ).stdout.decode("utf-8")
        paths = [REPO_DIR / name for name in listed.split("\0") if name]
    else:
        paths = [
            path
            for path in REPO_DIR.rglob("*")
            if not set(path.relative_to(REPO_DIR).parts) & SKIPPED_FOLDERS
        ]
    return [path for path in paths if path.is_file() and path.stat().st_size <= MAX_FILE_BYTES]


def test_no_real_title_appears_in_any_file_that_could_be_committed() -> None:
    titles = read_local_titles()
    if not titles:
        pytest.skip("local/ holds no titles to check against")
    texts = {
        str(path.relative_to(REPO_DIR)): path.read_bytes().decode("utf-8", errors="ignore")
        for path in _files_that_could_be_committed()
    }
    assert texts, "no files were found to search"
    assert find_leaks(titles, texts) == []


# Tests of the leak finder itself, on invented titles.

TITLES = {
    "a.csv row 2": "Zorbo Imaginary Spice Blend 250g",
    "a.csv row 3": "Quilt-Free  Fancy Tea Mix",
    "b.csv row 2": "Tiny Tea",
}


@pytest.mark.parametrize(
    "text",
    [
        "zorbo imaginary spice blend 250g",
        "Example: ZORBO   Imaginary\nSpice Blend 250g.",
        "the imaginary spice blend is new",
        "A line mentioning zorbo imaginary spice only.",
    ],
)
def test_a_whole_title_or_a_run_of_three_words_is_found(text: str) -> None:
    assert find_leaks(TITLES, {"docs/x.md": text}) == [
        "docs/x.md contains a title from a.csv row 2"
    ]


@pytest.mark.parametrize(
    "text",
    [
        "imaginary spice",
        "zorbo spice blend",
        "tiny tea",
        "A different imaginary mix of spice",
        "",
    ],
)
def test_two_words_or_scattered_words_are_not_found(text: str) -> None:
    assert find_leaks(TITLES, {"docs/x.md": text}) == []


def test_case_and_spacing_do_not_hide_a_title() -> None:
    leaks = find_leaks(TITLES, {"docs/x.md": "QUILT-FREE FANCY    tea\tMIX"})
    assert leaks == ["docs/x.md contains a title from a.csv row 3"]


def test_a_title_shorter_than_the_minimum_run_is_never_found() -> None:
    assert find_leaks(TITLES, {"docs/x.md": "tiny tea"}) == []


def test_every_file_and_title_that_match_are_listed() -> None:
    texts = {"one.md": TITLES["a.csv row 2"], "two.md": TITLES["a.csv row 3"], "three.md": "no"}
    assert find_leaks(TITLES, texts) == [
        "one.md contains a title from a.csv row 2",
        "two.md contains a title from a.csv row 3",
    ]


def test_the_report_never_contains_the_title_text() -> None:
    leaks = find_leaks(TITLES, {"docs/x.md": TITLES["a.csv row 2"]})
    assert leaks
    assert all("zorbo" not in leak.lower() for leak in leaks)


def test_local_titles_are_read_with_their_file_and_row(tmp_path: Path) -> None:
    (tmp_path / "rows.csv").write_bytes(
        b"\xef\xbb\xbftitle_raw,other\nZorbo Imaginary Spice Blend 250g,x\n,y\nSecond Title,z\n"
    )
    (tmp_path / "ignored.txt").write_text("title_raw\nnot read\n", encoding="utf-8")
    assert read_local_titles(tmp_path) == {
        "rows.csv row 2": "Zorbo Imaginary Spice Blend 250g",
        "rows.csv row 4": "Second Title",
    }


def test_a_missing_local_folder_gives_no_titles(tmp_path: Path) -> None:
    assert read_local_titles(tmp_path / "missing") == {}
