"""Validation of the labelled files in data/labelled.

    python -m src.label.validate [FILE ...]

With no file, every labels_<labeller>.csv and skipped_<labeller>.csv in data/labelled is
checked. The command only reports and never changes a file. Errors make the exit status 1;
warnings are reported but do not fail a file. The files and rules are described in
docs/data_entry_rules.md ("Labelled data files") and docs/labelling_guidelines.md.

Errors, for every row of a label file:

* the file name, the header, the encoding (strict UTF-8, no byte-order mark) and the fields;
* pair_id: its form, the required order of the two listings, the agreement of the four ID
  columns with it, that both listings are in data/raw, that they come from different sources,
  and that the pair is in data/interim/candidates.csv (when that file exists);
* label, note and tags: the allowed values and the consistency rules of records.py, and that
  the tag cross_script is present exactly when exactly one title has Bangla letters;
* labeller (it must match the file name), labelled_at (the form, a real time, not in the
  future, and not earlier than the row above) and guidelines_version (it must be in the
  version history of docs/labelling_guidelines.md).

A skipped_<labeller>.csv file gets the same checks of its pairs, reason and skipped_at.

Warnings compare the labels with how the size parser (N3) reads the two titles: a match whose
sizes N3 reads as different, a size, unit-kind, multipack or promo_quantity tag that N3's
reading does not support, and the same tag missing where N3's reading supports it. N3 can be
wrong, so these are only warnings. The reason is that the labels are meant to evaluate the
parser: they must be made from the titles, not from N3.

A pair may have several rows (a correction adds a row; nothing is edited), and its current
label is its latest row. The files adjudication.csv and overlap_sample.csv are not checked yet.

Messages name rows, columns and IDs, and show values with ascii(). They never contain a title.
"""

import argparse
import codecs
import csv
import io
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from src.collect.validate import RAW_DIR, Problem, parse_timestamp
from src.label.features import size_relation
from src.label.listings import (
    Listing,
    ListingKey,
    load_listings,
    parse_listing_size,
    read_candidate_pair_ids,
)
from src.label.records import (
    CANDIDATES_PATH,
    GUIDELINES_PATH,
    LABEL_COLUMNS,
    LABELLED_DIR,
    LABELLER_ID,
    LABELS,
    SKIPPED_COLUMNS,
    PairKey,
    check_label_and_tags,
    cross_script,
    make_pair_id,
    parse_note,
    parse_pair_id,
    read_version_history,
)
from src.normalise.sizes import SizeResult

Kind = Literal["labels", "skipped", "later"]

_FILE_NAME = re.compile(r"(labels|skipped)_(.+)\.csv")
# Files that exist in data/labelled but are not checked by this module yet.
_LATER_FILES = ("adjudication.csv", "overlap_sample.csv")


@dataclass(frozen=True)
class Context:
    """What the checks compare a labelled file with.

    Attributes:
        listings: The collected listings by (source, listing_id).
        versions: The versions in the version history of the labelling guidelines.
        candidates: The pair_id values of data/interim/candidates.csv, or None if that file
            does not exist (the check that a pair is a candidate is then skipped).
        now: The current time, with a time zone.
    """

    listings: dict[ListingKey, Listing]
    versions: tuple[str, ...]
    candidates: frozenset[str] | None
    now: datetime


def load_context(
    *,
    raw_dir: Path = RAW_DIR,
    candidates_path: Path = CANDIDATES_PATH,
    guidelines_path: Path = GUIDELINES_PATH,
    now: datetime | None = None,
) -> Context:
    """Read everything that labelled files are checked against.

    Args:
        raw_dir: The data/raw folder.
        candidates_path: The candidate pairs file; it may not exist.
        guidelines_path: The labelling guidelines.
        now: The current time, with a time zone; tests pass a fixed value. Defaults to now.

    Returns:
        The Context.

    Raises:
        ValueError: If the listings, the candidates file or the guidelines cannot be read.
    """
    return Context(
        listings=load_listings(raw_dir),
        versions=read_version_history(guidelines_path),
        candidates=read_candidate_pair_ids(candidates_path),
        now=now or datetime.now(UTC),
    )


@dataclass
class FileResult:
    """Everything found when one labelled file was validated.

    Attributes:
        path: The file.
        kind: "labels", "skipped", or "later" for a file that is not checked yet.
        labeller: The labeller named in the file name, or None.
        problems: The errors and warnings, in the order found.
        row_count: The number of data rows read.
        current: For a label file, the current label (the latest valid row) of each pair.
        versions: For a label file, how many rows were made under each guidelines version.
        first_row: For a skipped file, the first row of each pair.
    """

    path: Path
    kind: Kind | None = None
    labeller: str | None = None
    problems: list[Problem] = field(default_factory=list)
    row_count: int = 0
    current: dict[str, str] = field(default_factory=dict)
    versions: Counter[str] = field(default_factory=Counter)
    first_row: dict[str, int] = field(default_factory=dict)

    @property
    def errors(self) -> list[Problem]:
        """The problems that make the file invalid."""
        return [problem for problem in self.problems if problem.severity == "error"]

    @property
    def warnings(self) -> list[Problem]:
        """The problems that are only reported."""
        return [problem for problem in self.problems if problem.severity == "warning"]

    def error(self, message: str, row: int | None = None, column: str | None = None) -> None:
        """Record an error."""
        self.problems.append(Problem("error", message, row, column))

    def warning(self, message: str, row: int | None = None, column: str | None = None) -> None:
        """Record a warning."""
        self.problems.append(Problem("warning", message, row, column))


# The reading of the size parser, compared with the labels.


# How the relations of features.size_relation are written in a warning.
_RELATION_PHRASES = {
    "same": "equal",
    "same_total_different_pack": "the same size in different packs",
    "different_amount": "different sizes",
    "different_kind": "of different kinds",
}


def _describe(size: SizeResult) -> str:
    """Describe the size N3 read, for example '500 g' or '2 x 500 g'."""
    assert size.amount is not None
    unit = "g" if size.kind == "weight" else "ml"
    amount = format(size.amount.normalize(), "f")
    return f"{size.pack_count} x {amount} {unit}" if size.pack_count > 1 else f"{amount} {unit}"


def n3_disagreements(
    label: str, tags: Sequence[str], left: SizeResult, right: SizeResult
) -> list[str]:
    """Compare a label and its tags with the reading of the two sizes by N3.

    Sizes are equal when they are of the same kind and have the same total, so "2 x 500 g"
    equals "1000 g"; they differ as packs when the pack counts differ. Only sizes with the
    status "ok" are used, because N3 gives no usable reading otherwise.

    Args:
        label: The label.
        tags: The tags of the note.
        left: The size N3 read for the left listing.
        right: The size N3 read for the right listing.

    Returns:
        The disagreements, as messages; empty if the labels and N3's reading agree.
    """
    problems = []
    relation_code = size_relation(left, right)
    if relation_code != "unknown":
        same_kind = relation_code != "different_kind"
        sizes_differ = relation_code == "different_amount"
        relation = _RELATION_PHRASES[relation_code]
        reading = f"N3 reads {_describe(left)} and {_describe(right)}"
        if label == "match" and relation_code != "same":
            problems.append(f"{reading} ({relation}), but the label is match")
        if "size_differs" in tags and not sizes_differ:
            problems.append(f"the tag size_differs is present, but {reading} ({relation})")
        if "size_differs" not in tags and sizes_differ:
            problems.append(f"{reading} ({relation}), but the tag size_differs is missing")
        if "unit_kind_differs" in tags and same_kind:
            problems.append(f"the tag unit_kind_differs is present, but {reading} ({relation})")
        if "unit_kind_differs" not in tags and not same_kind:
            problems.append(f"{reading} ({relation}), but the tag unit_kind_differs is missing")
    read = [size for size in (left, right) if size.status == "ok"]
    for tag, seen in (
        ("multipack", any(size.pack_count > 1 for size in read)),
        ("promo_quantity", any(size.free_extra for size in read)),
    ):
        if tag in tags and not seen and len(read) == 2:
            problems.append(f"the tag {tag} is present, but N3 reads neither title as having it")
        if tag not in tags and seen:
            problems.append(f"N3 reads a title as having {tag}, but the tag is missing")
    return problems


# Reading a file.


def _read_table(path: Path, columns: tuple[str, ...], result: FileResult) -> list[list[str]] | None:
    """Read a CSV file as strict UTF-8 and check its header; return the data rows or None."""
    data = path.read_bytes()
    if data.startswith(codecs.BOM_UTF8):
        result.error("the file starts with a UTF-8 byte-order mark (BOM)")
        data = data[len(codecs.BOM_UTF8) :]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        result.error(
            f"the file is not valid UTF-8: the first bad byte is at position {error.start}"
        )
        return None
    try:
        records = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as error:
        result.error(f"the file cannot be read as CSV: {error}")
        return None
    if not records:
        result.error("the file is empty")
        return None
    if tuple(records[0]) != columns:
        found = ascii(", ".join(records[0]))
        result.error(f"the header must be exactly {', '.join(columns)}; found {found}", row=1)
        return None
    return records[1:]


def _classify(path: Path, result: FileResult) -> None:
    """Set the kind and the labeller of a file from its name, recording an error if needed."""
    if path.name in _LATER_FILES:
        result.kind = "later"
        return
    found = _FILE_NAME.fullmatch(path.name)
    if found is None:
        result.error("the name must be labels_<labeller>.csv or skipped_<labeller>.csv")
        return
    result.kind = "labels" if found.group(1) == "labels" else "skipped"
    if LABELLER_ID.fullmatch(found.group(2)):
        result.labeller = found.group(2)
    else:
        result.error(f"the labeller {ascii(found.group(2))} in the file name must be L and digits")


# Checks of one row.


def _check_pair(
    pair_id: str, number: int, result: FileResult, ctx: Context
) -> tuple[PairKey | None, tuple[Listing, Listing] | None]:
    """Check a pair_id and what it refers to.

    Returns:
        The key, or None if the pair_id is malformed; and the two listings, or None if the
        pair is not sound (a malformed pair_id, the wrong order, one source, or a listing that
        is not in data/raw). The check that the pair is a candidate does not affect the second
        value.
    """
    try:
        key = parse_pair_id(pair_id)
    except ValueError as error:
        result.error(str(error), row=number, column="pair_id")
        return None, None
    sound = True
    if key.is_same_source:
        result.error(
            "both listings are from the same source; a pair is across two shops", number, "pair_id"
        )
        sound = False
    elif not key.is_canonical:
        right_order = make_pair_id(key.left_source, key.left_id, key.right_source, key.right_id)
        result.error(
            f"the listings are not in the required order; it must be {right_order}",
            number,
            "pair_id",
        )
        sound = False
    listings = []
    for source, listing_id in ((key.left_source, key.left_id), (key.right_source, key.right_id)):
        listing = ctx.listings.get((source, listing_id))
        if listing is None:
            result.error(f"the listing {source}:{listing_id} is not in data/raw", number, "pair_id")
            sound = False
        else:
            listings.append(listing)
    if ctx.candidates is not None and pair_id not in ctx.candidates:
        result.error("the pair is not in candidates.csv", number, "pair_id")
    if not sound or len(listings) != 2:
        return key, None
    return key, (listings[0], listings[1])


def _check_timestamp(
    value: str,
    column: str,
    number: int,
    result: FileResult,
    ctx: Context,
    previous: datetime | None,
) -> datetime | None:
    """Check a timestamp and that it is not earlier than the row above; return it if valid."""
    try:
        moment = parse_timestamp(value, ctx.now)
    except ValueError as error:
        result.error(str(error), number, column)
        return None
    if previous is not None and moment < previous:
        result.error(f"{column} is earlier than the row above it", number, column)
    return moment


def _check_required(
    row: dict[str, str], columns: Sequence[str], number: int, result: FileResult
) -> None:
    """Record an error for each of the columns that is empty."""
    for column in columns:
        if not row[column].strip():
            result.error("is empty", number, column)


@dataclass
class _LabelState:
    """What is remembered between the rows of a label file."""

    previous_time: datetime | None = None
    last_row: dict[str, tuple[int, tuple[str, str, str]]] = field(default_factory=dict)


def _check_label_row(
    row: dict[str, str], number: int, result: FileResult, ctx: Context, state: _LabelState
) -> None:
    """Check one row of a label file."""
    _check_required(row, [c for c in LABEL_COLUMNS if c != "note"], number, result)
    key, pair = _check_pair(row["pair_id"], number, result, ctx) if row["pair_id"] else (None, None)
    if key is not None:
        for column, expected in (
            ("left_source", key.left_source),
            ("left_id", key.left_id),
            ("right_source", key.right_source),
            ("right_id", key.right_id),
        ):
            if row[column] != expected:
                result.error(
                    f"is {ascii(row[column])}, but pair_id says {ascii(expected)}", number, column
                )
    label = row["label"]
    tags: tuple[str, ...] | None
    try:
        tags = parse_note(row["note"]).tags
    except ValueError as error:
        result.error(str(error), number, "note")
        tags = None
    if label:
        problems = check_label_and_tags(label, tags or ())
        for index, message in enumerate(problems):
            column = "label" if label not in LABELS and index == 0 else "note"
            result.error(message, number, column)
    if pair is not None and tags is not None:
        _check_cross_script(tags, pair[0], pair[1], number, result)
        if label in LABELS:
            _check_n3(label, tags, pair[0], pair[1], number, result)
    labeller = row["labeller"]
    if labeller and result.labeller is not None and labeller != result.labeller:
        result.error(
            f"is {ascii(labeller)}, but the file is {result.path.name}", number, "labeller"
        )
    elif labeller and result.labeller is None and not LABELLER_ID.fullmatch(labeller):
        result.error(f"{ascii(labeller)} must be L and digits", number, "labeller")
    if row["labelled_at"]:
        moment = _check_timestamp(
            row["labelled_at"], "labelled_at", number, result, ctx, state.previous_time
        )
        if moment is not None:
            state.previous_time = moment
    version = row["guidelines_version"]
    if version:
        result.versions[version] += 1
        if version not in ctx.versions:
            history = ", ".join(ctx.versions)
            result.error(
                f"{ascii(version)} is not in the version history of the guidelines ({history})",
                number,
                "guidelines_version",
            )
    pair_id = row["pair_id"]
    if key is not None and label in LABELS:
        result.current[pair_id] = label
        content = (label, row["note"], version)
        earlier = state.last_row.get(pair_id)
        if earlier is not None and earlier[1] == content:
            result.warning(
                f"repeats row {earlier[0]} (same label, note and version)", number, "pair_id"
            )
        state.last_row[pair_id] = (number, content)


def _check_cross_script(
    tags: Sequence[str], left: Listing, right: Listing, number: int, result: FileResult
) -> None:
    """Check that cross_script is present exactly when exactly one title has Bangla letters."""
    expected = cross_script(left.title_raw, right.title_raw)
    present = "cross_script" in tags
    if expected and not present:
        result.error(
            "the tag cross_script is missing: exactly one title has Bangla letters", number, "note"
        )
    elif present and not expected:
        result.error(
            "the tag cross_script is present, but not exactly one title has Bangla letters",
            number,
            "note",
        )


def _check_n3(
    label: str, tags: Sequence[str], left: Listing, right: Listing, number: int, result: FileResult
) -> None:
    """Record a warning for each disagreement with how N3 reads the two sizes."""
    for message in n3_disagreements(
        label, tags, parse_listing_size(left), parse_listing_size(right)
    ):
        result.warning(message, number, "note")


def _check_skipped_row(
    row: dict[str, str], number: int, result: FileResult, ctx: Context, state: _LabelState
) -> None:
    """Check one row of a file of skipped pairs."""
    _check_required(row, SKIPPED_COLUMNS, number, result)
    pair_id = row["pair_id"]
    if pair_id:
        _check_pair(pair_id, number, result, ctx)
        if pair_id in result.first_row:
            result.warning(
                f"the pair is also in row {result.first_row[pair_id]}", number, "pair_id"
            )
        else:
            result.first_row[pair_id] = number
    if row["skipped_at"]:
        moment = _check_timestamp(
            row["skipped_at"], "skipped_at", number, result, ctx, state.previous_time
        )
        if moment is not None:
            state.previous_time = moment


# Files.


def validate_file(path: Path, ctx: Context) -> FileResult:
    """Validate one labelled file.

    Args:
        path: A labels_<labeller>.csv or skipped_<labeller>.csv file.
        ctx: What the file is checked against.

    Returns:
        The FileResult. The file is valid if result.errors is empty.
    """
    result = FileResult(path)
    _classify(path, result)
    if result.kind in (None, "later"):
        return result
    columns = LABEL_COLUMNS if result.kind == "labels" else SKIPPED_COLUMNS
    records = _read_table(path, columns, result)
    if records is None:
        return result
    if not records:
        result.warning("the file has a header but no rows")
    state = _LabelState()
    for number, record in enumerate(records, start=2):
        result.row_count += 1
        if not any(value.strip() for value in record):
            result.error("the row is empty", row=number)
        elif len(record) != len(columns):
            result.error(f"the row has {len(record)} fields; expected {len(columns)}", row=number)
        else:
            row = dict(zip(columns, record, strict=True))
            if result.kind == "labels":
                _check_label_row(row, number, result, ctx, state)
            else:
                _check_skipped_row(row, number, result, ctx, state)
    return result


def validate_files(paths: Sequence[Path], ctx: Context) -> list[FileResult]:
    """Validate several labelled files, then the checks that compare two files.

    A pair that a labeller skipped should not also be labelled by the same labeller; that is
    reported as a warning on the skipped file.

    Args:
        paths: The files.
        ctx: What the files are checked against.

    Returns:
        One FileResult per file, in the order given.
    """
    results = [validate_file(path, ctx) for path in paths]
    labelled = {
        result.labeller: result
        for result in results
        if result.kind == "labels" and result.labeller is not None
    }
    for result in results:
        if result.kind != "skipped" or result.labeller not in labelled:
            continue
        labels = labelled[result.labeller]
        for pair_id, number in result.first_row.items():
            if pair_id in labels.current:
                result.warning(
                    f"the pair is also labelled in {labels.path.name}; a skipped pair is one "
                    "that is left out",
                    number,
                    "pair_id",
                )
    return results


# The command line.


def _summary(result: FileResult) -> str:
    """Return a one-line summary of what a valid file holds."""
    if result.kind == "labels":
        counts = Counter(result.current.values())
        by_label = ", ".join(f"{label} {counts[label]}" for label in LABELS)
        versions = ", ".join(f"{v} ({n} rows)" for v, n in sorted(result.versions.items()))
        return f"{len(result.current)} pairs labelled ({by_label}); guidelines {versions or 'none'}"
    return f"{len(result.first_row)} pairs skipped"


def _report(result: FileResult) -> None:
    """Print the result for one file."""
    if result.kind == "later":
        print(f"{result.path}: not checked yet (this version checks label and skipped files)")
        return
    print(
        f"{result.path}: {result.row_count} rows, {len(result.errors)} errors, "
        f"{len(result.warnings)} warnings"
    )
    for problem in result.problems:
        print(f"  {problem.describe()}")
    if not result.errors and result.kind in ("labels", "skipped"):
        print(f"  valid; {_summary(result)}")


def main(argv: Sequence[str] | None = None, *, now: datetime | None = None) -> int:
    """Validate labelled files and print the result.

    Args:
        argv: The command-line arguments, without the program name. Defaults to sys.argv.
        now: The current time, with a time zone; tests pass a fixed value. Defaults to now.

    Returns:
        The exit status: 0 if no file has an error, otherwise 1.
    """
    parser = argparse.ArgumentParser(
        prog="python -m src.label.validate",
        description="Validate the labelled files in data/labelled. Nothing is changed.",
    )
    parser.add_argument("files", nargs="*", type=Path, help="default: all in the labelled folder")
    parser.add_argument("--labelled-dir", type=Path, default=LABELLED_DIR)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--candidates", type=Path, default=CANDIDATES_PATH)
    parser.add_argument("--guidelines", type=Path, default=GUIDELINES_PATH)
    args = parser.parse_args(argv)
    paths = args.files or sorted(args.labelled_dir.glob("*.csv"))
    if not paths:
        print(f"no labelled files found in {args.labelled_dir}")
        return 0
    try:
        ctx = load_context(
            raw_dir=args.raw_dir,
            candidates_path=args.candidates,
            guidelines_path=args.guidelines,
            now=now,
        )
    except ValueError as error:
        print(f"error: {error}")
        return 1
    status = 0
    for path in paths:
        if not path.is_file():
            print(f"{path}: not a file")
            status = 1
    results = validate_files([path for path in paths if path.is_file()], ctx)
    for result in results:
        _report(result)
        if result.errors:
            status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
