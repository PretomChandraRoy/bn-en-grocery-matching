"""Validation of hand-collected listing files before they go into data/raw.

Run it on every CSV file exported from the collection sheet:

    python -m src.collect.validate FILE [FILE ...]
    python -m src.collect.validate --accept FILE

The first form only reports and never changes a file. The second form also copies the file,
byte for byte, into data/raw, but only if it has no errors. The copy is named
<source>_<YYYYMMDD>.csv after the last collection day in the file, and an existing file is never
overwritten, because data/raw is never edited. --accept is the only way a file should enter
data/raw. After it, run "dvc add data/raw" and commit data/raw.dvc.

Errors make the exit status 1. Warnings are reported but do not fail a file. The rules are
described in docs/data_entry_rules.md. Values are shown with ascii(), so that any character
outside ASCII appears as an escape and can be checked.
"""

import argparse
import codecs
import csv
import io
import re
import shutil
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from src.normalise.units import UNITS

REPO_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_DIR / "data" / "raw"

COLUMNS = (
    "source",
    "listing_id",
    "title_raw",
    "brand",
    "size_value",
    "size_unit",
    "price_bdt",
    "category",
    "source_category",
    "script",
    "url",
    "collected_at",
)
REQUIRED_COLUMNS = (
    "source",
    "listing_id",
    "title_raw",
    "price_bdt",
    "category",
    "script",
    "url",
    "collected_at",
)
CATEGORIES = ("rice", "lentils", "cooking_oil", "spices")
SCRIPTS = ("english", "romanised", "bangla", "mixed")

_PRICE = re.compile(r"[0-9]+(?:\.[0-9]{1,2})?")
_COLLECTED_AT = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[+-][0-9]{2}:[0-9]{2}"
)
_LATIN_WORD = re.compile(r"[A-Za-z]+")
# Latin words that do not count when the script is judged: unit abbreviations, and the "x" of
# a multipack such as "2 x 500 gm".
_IGNORED_LATIN_WORDS = frozenset(
    {unit.replace(".", "") for unit in UNITS if unit.isascii()} | {"x"}
)
_BANGLA_BLOCK = range(0x0980, 0x0A00)

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class SourceRules:
    """What the fields of a listing must look like for one cleared source.

    Attributes:
        listing_id: The pattern that a listing_id must match in full.
        url: The pattern that a product URL must match in full. Its group "id" must equal the
            listing_id.
        has_brand_field: Whether the shop shows the brand as a separate field. If it does, an
            empty brand is a warning; if it does not, a filled-in brand is a warning.
        has_size_fields: Whether the shop shows the size as separate fields. If it does not, a
            filled-in size_value or size_unit is a warning.
    """

    listing_id: re.Pattern[str]
    url: re.Pattern[str]
    has_brand_field: bool
    has_size_fields: bool


# The sources that docs/sources.md allows. Add a source here only when its entry there allows
# collection.
CLEARED_SOURCES: dict[str, SourceRules] = {
    "pandamart": SourceRules(
        listing_id=re.compile(r"[0-9]+"),
        url=re.compile(
            r"https://www\.foodpanda\.com\.bd/darkstore/vbpl/pandamart-gulshan-banani/"
            r"category/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/"
            r"product/(?P<id>[0-9]+)"
        ),
        has_brand_field=False,
        has_size_fields=False,
    ),
    # The slug is free text that can disagree with the title (docs/data_entry_rules.md), so it is
    # only required to stay within one path segment: no "/", "?", "#" or whitespace.
    "meenabazar": SourceRules(
        listing_id=re.compile(r"[0-9]+"),
        url=re.compile(r"https://meenabazaronline\.com/product/[^/?#\s]+/(?P<id>[0-9]+)"),
        has_brand_field=True,
        has_size_fields=False,
    ),
}


@dataclass(frozen=True)
class Problem:
    """One problem found in a file.

    Attributes:
        severity: "error" makes the file invalid; "warning" is only reported.
        message: What is wrong.
        row: The row number, counting the header as row 1, or None for the whole file.
        column: The column concerned, or None.
    """

    severity: Severity
    message: str
    row: int | None = None
    column: str | None = None

    def describe(self) -> str:
        """Return the problem as one line of text."""
        parts = []
        if self.row is not None:
            parts.append(f"row {self.row}")
        if self.column is not None:
            parts.append(self.column)
        place = f" ({', '.join(parts)})" if parts else ""
        return f"{self.severity}{place}: {self.message}"


@dataclass
class ValidationResult:
    """Everything found when one file was validated.

    Attributes:
        path: The file.
        problems: The errors and warnings, in the order found.
        row_count: The number of data rows read.
        source: The source of the rows, if all rows have the same one.
        last_day: The last collection day in the file, as YYYYMMDD.
    """

    path: Path
    problems: list[Problem] = field(default_factory=list)
    row_count: int = 0
    source: str | None = None
    last_day: str | None = None

    @property
    def errors(self) -> list[Problem]:
        """The problems that make the file invalid."""
        return [problem for problem in self.problems if problem.severity == "error"]

    @property
    def warnings(self) -> list[Problem]:
        """The problems that are only reported."""
        return [problem for problem in self.problems if problem.severity == "warning"]

    @property
    def expected_name(self) -> str | None:
        """The name the file has, or would have, in data/raw: <source>_<last day>.csv."""
        if self.source is None or self.last_day is None:
            return None
        return f"{self.source}_{self.last_day}.csv"

    @property
    def accepted_name(self) -> str | None:
        """The name the file would get in data/raw, or None if it has errors."""
        return None if self.errors else self.expected_name

    def error(self, message: str, row: int | None = None, column: str | None = None) -> None:
        """Record an error."""
        self.problems.append(Problem("error", message, row, column))

    def warning(self, message: str, row: int | None = None, column: str | None = None) -> None:
        """Record a warning."""
        self.problems.append(Problem("warning", message, row, column))


def validate_file(
    path: Path, *, raw_dir: Path = RAW_DIR, now: datetime | None = None
) -> ValidationResult:
    """Validate one collected CSV file against the data entry rules.

    Args:
        path: The CSV file.
        raw_dir: The data/raw folder. Its files are used for the duplicate check, and a file
            inside it must carry its expected name.
        now: The current time, with a time zone; tests pass a fixed value. Defaults to now.

    Returns:
        The ValidationResult. The file is valid if result.errors is empty.
    """
    result = ValidationResult(path)
    now = now or datetime.now(UTC)
    data = path.read_bytes()
    if data.startswith(codecs.BOM_UTF8):
        result.error("the file starts with a UTF-8 byte-order mark (BOM); export it without one")
        data = data[len(codecs.BOM_UTF8) :]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        result.error(
            f"the file is not valid UTF-8: the first bad byte is at position {error.start}"
        )
        return result
    try:
        records = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as error:
        result.error(f"the file cannot be read as CSV: {error}")
        return result
    if not records:
        result.error("the file is empty")
        return result
    if tuple(records[0]) != COLUMNS:
        found = ascii(", ".join(records[0]))
        result.error(f"the header must be exactly {', '.join(COLUMNS)}; found {found}", row=1)
        return result
    _check_rows(records[1:], result, raw_dir=raw_dir, now=now)
    _check_name_in_raw_dir(result, raw_dir)
    return result


def _check_rows(
    records: list[list[str]], result: ValidationResult, *, raw_dir: Path, now: datetime
) -> None:
    """Check every data row, then the rules that concern the file as a whole."""
    if not records:
        result.error("the file has no data rows")
        return
    already_in_raw = _listing_ids_in(raw_dir, exclude=result.path)
    first_row_of: dict[tuple[str, str], int] = {}
    sources: set[str] = set()
    days: list[str] = []
    for number, record in enumerate(records, start=2):
        result.row_count += 1
        if not any(value.strip() for value in record):
            result.error("the row is empty", row=number)
            continue
        if len(record) != len(COLUMNS):
            result.error(f"the row has {len(record)} fields; expected {len(COLUMNS)}", row=number)
            continue
        row = dict(zip(COLUMNS, record, strict=True))
        day = _check_row(row, number, result, now)
        if day is not None:
            days.append(day)
        if row["source"]:
            sources.add(row["source"])
        listing_id = row["listing_id"]
        if not listing_id:
            continue
        key = (row["source"], listing_id)
        if key in first_row_of:
            result.error(
                f"listing_id {ascii(listing_id)} also appears in row {first_row_of[key]}",
                row=number,
                column="listing_id",
            )
        else:
            first_row_of[key] = number
        earlier_file = already_in_raw.get(row["source"], {}).get(listing_id)
        if earlier_file is not None:
            result.error(
                f"listing_id {ascii(listing_id)} is already in data/raw/{earlier_file}; "
                "re-collecting a listing is not allowed",
                row=number,
                column="listing_id",
            )
    if len(sources) > 1:
        result.error(f"the file holds rows from more than one source: {', '.join(sorted(sources))}")
    elif len(sources) == 1:
        result.source = next(iter(sources))
    if days:
        result.last_day = max(days)


def _check_row(
    row: dict[str, str], number: int, result: ValidationResult, now: datetime
) -> str | None:
    """Check one row, and return its collection day as YYYYMMDD if collected_at is valid."""
    for column in REQUIRED_COLUMNS:
        if not row[column].strip():
            result.error("is empty", row=number, column=column)
    source = row["source"]
    rules = CLEARED_SOURCES.get(source)
    if source and rules is None:
        cleared = ", ".join(sorted(CLEARED_SOURCES))
        result.error(
            f"{ascii(source)} is not a cleared source (cleared: {cleared})",
            row=number,
            column="source",
        )
    _check_listing_and_url(row, number, result, rules)
    if rules is not None:
        _check_source_fields(row, number, result, rules)
    _check_price(row["price_bdt"], number, result)
    category = row["category"]
    if category and category not in CATEGORIES:
        result.error(
            f"{ascii(category)} is not one of {', '.join(CATEGORIES)}",
            row=number,
            column="category",
        )
    script = row["script"]
    if script and script not in SCRIPTS:
        result.error(
            f"{ascii(script)} is not one of {', '.join(SCRIPTS)}", row=number, column="script"
        )
    elif script and row["title_raw"]:
        problem = _script_problem(script, row["title_raw"])
        if problem is not None:
            result.error(problem, row=number, column="script")
    _check_title(row["title_raw"], number, result)
    if bool(row["size_value"].strip()) != bool(row["size_unit"].strip()):
        result.warning(
            "size_value and size_unit should both be filled in or both be blank",
            row=number,
            column="size_value",
        )
    return _check_collected_at(row["collected_at"], number, result, now)


def _check_listing_and_url(
    row: dict[str, str], number: int, result: ValidationResult, rules: SourceRules | None
) -> None:
    """Check listing_id and url, and that they agree with each other."""
    listing_id = row["listing_id"]
    url = row["url"]
    if listing_id and any(char.isspace() for char in listing_id):
        result.error("contains a space", row=number, column="listing_id")
    if rules is None:
        return
    if listing_id and not rules.listing_id.fullmatch(listing_id):
        result.error(
            f"{ascii(listing_id)} does not have the form required for this source",
            row=number,
            column="listing_id",
        )
    if not url:
        return
    if "/view-all/" in url:
        result.error("is a view-all page, which must not be used", row=number, column="url")
        return
    match = rules.url.fullmatch(url)
    if match is None:
        result.error(
            "is not a product page of the store allowed in docs/sources.md",
            row=number,
            column="url",
        )
    elif listing_id and match.group("id") != listing_id:
        result.error(
            f"the product ID in the URL ({match.group('id')}) differs from listing_id "
            f"{ascii(listing_id)}",
            row=number,
            column="url",
        )


def _check_source_fields(
    row: dict[str, str], number: int, result: ValidationResult, rules: SourceRules
) -> None:
    """Warn when brand, size_value or size_unit does not fit the fields the shop shows.

    These are warnings, not errors: they point to a likely slip in data entry, but a file with
    them is still well formed.
    """
    source = row["source"]
    brand = row["brand"].strip()
    if rules.has_brand_field and not brand:
        result.warning(
            f"is empty, but {source} shows a Brand field; copy it as shown "
            '("No Brand" is a valid value)',
            row=number,
            column="brand",
        )
    elif not rules.has_brand_field and brand:
        result.warning(
            f"is filled in, but {source} has no brand field; leave it blank",
            row=number,
            column="brand",
        )
    if rules.has_size_fields:
        return
    for column in ("size_value", "size_unit"):
        if row[column].strip():
            result.warning(
                f"is filled in, but {source} has no separate size field; leave it blank",
                row=number,
                column=column,
            )


def _check_price(value: str, number: int, result: ValidationResult) -> None:
    """Check that price_bdt is a bare positive number."""
    if not value:
        return
    if not _PRICE.fullmatch(value):
        result.error(
            f"{ascii(value)} must be a bare number such as 315 or 12.50, with no currency sign "
            "and no comma",
            row=number,
            column="price_bdt",
        )
    elif Decimal(value) <= 0:
        result.error("must be greater than zero", row=number, column="price_bdt")


def _has_bangla_letters(text: str) -> bool:
    """Return True if the text contains a Bangla letter or mark (digits do not count)."""
    return any(
        ord(char) in _BANGLA_BLOCK and unicodedata.category(char)[0] in "LM" for char in text
    )


def _script_problem(script: str, title: str) -> str | None:
    """Return why the script value cannot be right for the title, or None.

    Only what can be decided from the characters is checked. Whether a Latin title is english or
    romanised depends on the meaning of its words, so that is not checked.
    """
    has_bangla = _has_bangla_letters(title)
    latin_words = [
        word for word in _LATIN_WORD.findall(title) if word.lower() not in _IGNORED_LATIN_WORDS
    ]
    if script == "bangla" and not has_bangla:
        return "is 'bangla', but the title has no Bangla letters"
    if script == "bangla" and latin_words:
        return "is 'bangla', but the title has Latin words other than units, so it is 'mixed'"
    if script in ("english", "romanised") and has_bangla:
        return f"is {ascii(script)}, but the title has Bangla letters"
    if script == "mixed" and not (has_bangla and latin_words):
        return "is 'mixed', but the title does not have both Bangla letters and Latin words"
    return None


def _check_title(title: str, number: int, result: ValidationResult) -> None:
    """Warn about characters in title_raw that are worth checking against the website."""
    if not title:
        return
    if title != title.strip():
        result.warning("has a space at the start or the end", row=number, column="title_raw")
    if "  " in title:
        result.warning("contains two spaces in a row", row=number, column="title_raw")
    hidden = sorted(
        {f"U+{ord(char):04X}" for char in title if unicodedata.category(char) in ("Cc", "Cf")}
    )
    if hidden:
        result.warning(
            f"contains invisible or control characters: {', '.join(hidden)}",
            row=number,
            column="title_raw",
        )
    unusual = sorted(
        {
            f"U+{ord(char):04X}"
            for char in title
            if not (" " <= char <= "~")
            and ord(char) not in _BANGLA_BLOCK
            and unicodedata.category(char) not in ("Cc", "Cf")
        }
    )
    if unusual:
        result.warning(
            f"contains characters outside ASCII and Bangla: {', '.join(unusual)}; "
            "check them against the website",
            row=number,
            column="title_raw",
        )


def _check_collected_at(
    value: str, number: int, result: ValidationResult, now: datetime
) -> str | None:
    """Check collected_at, and return its day as YYYYMMDD if it is valid."""
    if not value:
        return None
    if not _COLLECTED_AT.fullmatch(value):
        result.error(
            f"{ascii(value)} must have the form 2026-11-05T19:30:00+06:00",
            row=number,
            column="collected_at",
        )
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        result.error(
            f"{ascii(value)} is not a real date and time", row=number, column="collected_at"
        )
        return None
    if moment > now:
        result.error(f"{ascii(value)} is in the future", row=number, column="collected_at")
        return None
    return value[:10].replace("-", "")


def _listing_ids_in(raw_dir: Path, *, exclude: Path) -> dict[str, dict[str, str]]:
    """Return, for each source, the listing IDs already in data/raw and the file holding each."""
    found: dict[str, dict[str, str]] = {}
    if not raw_dir.is_dir():
        return found
    for path in sorted(raw_dir.glob("*.csv")):
        if path.resolve() == exclude.resolve():
            continue
        text = path.read_bytes().removeprefix(codecs.BOM_UTF8).decode("utf-8", errors="replace")
        try:
            for record in csv.DictReader(io.StringIO(text, newline="")):
                source = record.get("source") or ""
                listing_id = record.get("listing_id") or ""
                if listing_id:
                    found.setdefault(source, {}).setdefault(listing_id, path.name)
        except csv.Error:
            continue
    return found


def _check_name_in_raw_dir(result: ValidationResult, raw_dir: Path) -> None:
    """A file inside data/raw must be named after its source and last collection day."""
    if result.path.resolve().parent != raw_dir.resolve():
        return
    expected = result.expected_name
    if expected is not None and result.path.name != expected:
        result.error(f"a file in data/raw must be named {expected} (its source and last day)")


def _report(result: ValidationResult, raw_dir: Path, *, accepting: bool) -> None:
    """Print the result for one file."""
    print(
        f"{result.path}: {result.row_count} rows, {len(result.errors)} errors, "
        f"{len(result.warnings)} warnings"
    )
    for problem in result.problems:
        print(f"  {problem.describe()}")
    if result.accepted_name is not None and not accepting:
        print(f"  valid; --accept would copy it to {raw_dir / result.accepted_name}")


def _accept(result: ValidationResult, raw_dir: Path) -> int:
    """Copy a valid file into data/raw under its accepted name, never overwriting a file."""
    name = result.accepted_name
    if name is None:
        return 1
    if result.path.resolve().parent == raw_dir.resolve():
        print("  not copied: the file is already in data/raw")
        return 1
    target = raw_dir / name
    if target.exists():
        print(f"  not copied: {target} already exists, and files in data/raw are never overwritten")
        return 1
    raw_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(result.path, target)
    if target.read_bytes() != result.path.read_bytes():
        print(f"  error: the copy at {target} differs from the original")
        return 1
    print(f"  copied to {target}")
    print("  next: run 'dvc add data/raw' and commit data/raw.dvc")
    return 0


def main(argv: Sequence[str] | None = None, *, now: datetime | None = None) -> int:
    """Validate the files named on the command line, and accept them into data/raw if asked.

    Args:
        argv: The command-line arguments, without the program name. Defaults to sys.argv.
        now: The current time, with a time zone; tests pass a fixed value. Defaults to now.

    Returns:
        The exit status: 0 if every file is valid (and, with --accept, copied), otherwise 1.
    """
    parser = argparse.ArgumentParser(
        prog="python -m src.collect.validate",
        description="Validate collected listing files before they go into data/raw.",
    )
    parser.add_argument("files", nargs="+", type=Path, help="CSV files from the collection sheet")
    parser.add_argument("--accept", action="store_true", help="copy each valid file into data/raw")
    parser.add_argument(
        "--raw-dir", type=Path, default=RAW_DIR, help="the data/raw folder (default: %(default)s)"
    )
    args = parser.parse_args(argv)
    status = 0
    for path in args.files:
        if not path.is_file():
            print(f"{path}: not a file")
            status = 1
            continue
        result = validate_file(path, raw_dir=args.raw_dir, now=now)
        _report(result, args.raw_dir, accepting=args.accept)
        if result.errors:
            status = 1
        elif args.accept:
            status = max(status, _accept(result, args.raw_dir))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
