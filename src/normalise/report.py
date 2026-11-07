"""Local report on how the normalisation steps treat the titles in collected CSV files.

    python -m src.normalise.report FILE [FILE ...]

This is a local check for the real data kept in local/, which must never be committed. It only
prints: it writes no files and changes nothing. For each row it applies clean_unicode and
bangla_digits_to_ascii to the title and the size fields, then parse_size (N3) and clean_text
(N4), and prints the size result and title_norm. A summary follows:

* counts by size status and by reason;
* in-scope titles with pack-count wording such as "Pack of 2" or "2 Packs", which N3 does not
  yet handle (a row is in scope when its category is one of the project's four);
* how many titles contain the Bangla currency fraction signs (U+09F4 to U+09F9);
* the words most often found straight after a number but not in the unit table;
* the most frequent words in title_norm, as evidence for the promotional-word step (N5).
"""

import argparse
import codecs
import csv
import io
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from src.collect.validate import CATEGORIES
from src.normalise.digits import bangla_digits_to_ascii
from src.normalise.patterns import BOUNDARY_AFTER, BOUNDARY_BEFORE, WORD_CHARS
from src.normalise.sizes import SizeResult, parse_size
from src.normalise.text_clean import clean_text
from src.normalise.unicode_clean import clean_unicode
from src.normalise.units import UNITS

# Pack-count wording in title_norm (lower case by then): "pack of 2", "packs of 3", "2 packs".
_PACK_WORDING = re.compile(rf"{BOUNDARY_BEFORE}(?:packs? of [0-9]+|[0-9]+ ?packs?){BOUNDARY_AFTER}")
# A number in title_norm, and (in a lookahead, so that it is not consumed and can itself be
# a number followed by a word) the token straight after it.
_WORD_AFTER_NUMBER = re.compile(rf"(?<![{WORD_CHARS}])[0-9]+(?:\.[0-9]+)? (?=([^ ]+))")
_UNIT_WORDS = frozenset(unit.replace(".", "") for unit in UNITS)
_CURRENCY_FRACTION_SIGNS = range(0x09F4, 0x09FA)
_TOP_WORDS_AFTER_NUMBERS = 15
_TOP_WORDS = 25


@dataclass(frozen=True)
class RowReport:
    """The normalisation results for one row.

    Attributes:
        file: The name of the file the row came from.
        listing_id: The row's listing_id.
        title_raw: The title as collected.
        in_scope: Whether the row's category is one of the project's four.
        size: The result of parse_size.
        title_norm: The result of clean_text.
        pack_wording: The pack-count wording found in title_norm, or an empty string.
        has_currency_fraction: Whether the title contains a sign from U+09F4 to U+09F9.
    """

    file: str
    listing_id: str
    title_raw: str
    in_scope: bool
    size: SizeResult
    title_norm: str
    pack_wording: str
    has_currency_fraction: bool


def _prepare(text: str) -> str:
    """Apply the first two normalisation steps (N1 and N2)."""
    return bangla_digits_to_ascii(clean_unicode(text))


def report_row(file_name: str, row: dict[str, str]) -> RowReport:
    """Run the normalisation steps on one row of a collected file.

    Args:
        file_name: The name of the file the row came from.
        row: The row, as read by csv.DictReader. Missing values count as empty.

    Returns:
        The RowReport.
    """
    title = row.get("title_raw") or ""
    prepared = _prepare(title)
    size = parse_size(
        prepared, _prepare(row.get("size_value") or ""), _prepare(row.get("size_unit") or "")
    )
    title_norm = clean_text(prepared)
    pack = _PACK_WORDING.search(title_norm)
    return RowReport(
        file=file_name,
        listing_id=row.get("listing_id") or "",
        title_raw=title,
        in_scope=(row.get("category") or "") in CATEGORIES,
        size=size,
        title_norm=title_norm,
        pack_wording=pack.group(0) if pack else "",
        has_currency_fraction=any(ord(char) in _CURRENCY_FRACTION_SIGNS for char in title),
    )


def read_rows(path: Path) -> tuple[list[dict[str, str]], str]:
    """Read a CSV file as UTF-8.

    Args:
        path: The CSV file.

    Returns:
        The rows, and a note about the file (empty if there is nothing to note).

    Raises:
        UnicodeDecodeError: If the file is not valid UTF-8.
        ValueError: If the file has no title_raw column.
    """
    data = path.read_bytes()
    note = ""
    if data.startswith(codecs.BOM_UTF8):
        data = data[len(codecs.BOM_UTF8) :]
        note = (
            "the file starts with a byte-order mark; it is ignored here, but the validator "
            "rejects it"
        )
    reader = csv.DictReader(io.StringIO(data.decode("utf-8"), newline=""))
    rows = list(reader)
    if "title_raw" not in (reader.fieldnames or []):
        raise ValueError("the file has no title_raw column")
    return rows, note


def _describe_size(size: SizeResult) -> str:
    """Return the size result as short text."""
    if size.amount is None:
        return f"{size.status} ({size.reason})"
    unit = "g" if size.kind == "weight" else "ml"
    text = f"ok {size.amount_text} {unit}"
    if size.pack_count > 1:
        text += f" x {size.pack_count}"
    if size.free_extra:
        text += " plus a free extra"
    return f"{text} (from the {size.source}: {size.matched_text!r})"


def _counts(counter: Counter[str]) -> str:
    """Return a counter as text, most frequent first."""
    return ", ".join(f"{key} {count}" for key, count in counter.most_common()) or "none"


def print_report(rows: list[RowReport]) -> None:
    """Print one block per row, then the summary."""
    for row in rows:
        scope = "in scope" if row.in_scope else "out of scope"
        print(f"{row.file} {row.listing_id} ({scope})")
        print(f"  title:      {row.title_raw}")
        print(f"  size:       {_describe_size(row.size)}")
        print(f"  title_norm: {row.title_norm}")
        if row.pack_wording:
            handled = "N3 does not handle this yet" if row.in_scope else "out of scope"
            print(f"  pack-count wording: {row.pack_wording!r} ({handled})")
    in_scope = [row for row in rows if row.in_scope]
    print()
    print("Summary")
    print(
        f"  rows: {len(rows)} ({len(in_scope)} in scope, {len(rows) - len(in_scope)} out of scope)"
    )
    print(f"  size status: {_counts(Counter(row.size.status for row in rows))}")
    print(f"  reasons: {_counts(Counter(row.size.reason for row in rows if row.size.reason))}")
    flagged = [row for row in in_scope if row.pack_wording]
    print(f"  in-scope titles with pack-count wording (N3 does not handle these): {len(flagged)}")
    for row in flagged:
        print(f"    {row.file} {row.listing_id}: {row.pack_wording!r}")
    fractions = sum(row.has_currency_fraction for row in rows)
    print(f"  titles with Bangla currency fraction signs (U+09F4 to U+09F9): {fractions}")
    after_numbers: Counter[str] = Counter()
    words: Counter[str] = Counter()
    for row in rows:
        for word in _WORD_AFTER_NUMBER.findall(row.title_norm):
            if _is_counted_word(word):
                after_numbers[word] += 1
        for word in row.title_norm.split():
            if _is_counted_word(word):
                words[word] += 1
    top_after = Counter(dict(after_numbers.most_common(_TOP_WORDS_AFTER_NUMBERS)))
    top_words = Counter(dict(words.most_common(_TOP_WORDS)))
    print(f"  words after a number that are not units: {_counts(top_after)}")
    print(f"  most frequent words (evidence for N5): {_counts(top_words)}")


def _is_counted_word(token: str) -> bool:
    """Return True if a token has a letter and is neither a unit nor the "x" of a multipack."""
    has_letter = any(unicodedata.category(char)[0] == "L" for char in token)
    return has_letter and token not in _UNIT_WORDS and token != "x"


def _use_utf8_output() -> None:
    """Print UTF-8 so that Bangla titles work in a Windows terminal, whatever its default."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(encoding="utf-8", errors="replace")
    except (ValueError, io.UnsupportedOperation):
        return


def main(argv: Sequence[str] | None = None) -> int:
    """Print the report for the files named on the command line.

    Args:
        argv: The command-line arguments, without the program name. Defaults to sys.argv.

    Returns:
        The exit status: 0 if every file could be read, otherwise 1.
    """
    parser = argparse.ArgumentParser(
        prog="python -m src.normalise.report",
        description="Print how the normalisation steps treat the titles in collected files.",
    )
    parser.add_argument("files", nargs="+", type=Path, help="CSV files, normally in local/")
    args = parser.parse_args(argv)
    _use_utf8_output()
    status = 0
    rows: list[RowReport] = []
    for path in args.files:
        try:
            records, note = read_rows(path)
        except (OSError, UnicodeDecodeError, ValueError, csv.Error) as error:
            print(f"{path}: cannot read: {error}")
            status = 1
            continue
        if note:
            print(f"{path}: note: {note}")
        rows.extend(report_row(path.name, record) for record in records)
    print_report(rows)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
