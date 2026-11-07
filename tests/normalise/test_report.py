"""Tests for src.normalise.report.

All rows are invented; no real listing appears here. Bangla text is built from code points (see
tests/helpers.py).
"""

import codecs
import csv
import io
from decimal import Decimal
from pathlib import Path

import pytest

from src.collect.validate import COLUMNS
from src.normalise.report import main, report_row
from tests.helpers import bn

CHAL = bn(0x099A, 0x09BE, 0x09B2)  # চাল
BANGLA_ONE = bn(0x09E7)  # ১
KEJI = bn(0x0995, 0x09C7, 0x099C, 0x09BF)  # কেজি
CURRENCY_FRACTION = bn(0x09F4)  # ৴


def make_row(listing_id: str, title: str, category: str = "rice") -> dict[str, str]:
    row = dict.fromkeys(COLUMNS, "")
    row.update(source="pandamart", listing_id=listing_id, title_raw=title, category=category)
    return row


def write_csv(path: Path, rows: list[dict[str, str]], prefix: bytes = b"") -> Path:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_bytes(prefix + buffer.getvalue().encode("utf-8"))
    return path


ROWS = [
    make_row("1", "Test Rice Pack of 2 1kg"),
    make_row("2", "Test Dal 500g", category="lentils"),
    make_row("3", "Test Snack 6 Packs 300g", category=""),
    make_row("4", f"{CHAL} {BANGLA_ONE} {KEJI}"),
    make_row("5", "Test Spice 100 pcs", category="spices"),
    make_row("6", "Test Drink 70g +/-3g", category=""),
    make_row("7", f"Test Oil 1L {CURRENCY_FRACTION}", category="cooking_oil"),
]


def test_report_row_applies_n1_to_n4() -> None:
    result = report_row("f.csv", make_row("4", f"{CHAL} {BANGLA_ONE} {KEJI}"))
    assert result.size.status == "ok"
    assert result.size.amount == Decimal(1000)
    assert result.title_norm == f"{CHAL} 1 {KEJI}"
    assert result.in_scope


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Test Rice Pack of 2 1kg", "pack of 2"),
        ("Test Rice 2 Packs 1kg", "2 packs"),
        ("Test Rice 3packs 1kg", "3packs"),
        ("Test Rice Packs of 4 1kg", "packs of 4"),
        ("Test Rice Package 1kg", ""),
        ("Test Rice 1kg", ""),
    ],
)
def test_pack_count_wording_is_found(title: str, expected: str) -> None:
    assert report_row("f.csv", make_row("1", title)).pack_wording == expected


def test_the_report_prints_results_and_a_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_csv(tmp_path / "rows.csv", ROWS)
    assert main([str(path)]) == 0
    out = capsys.readouterr().out
    assert "rows: 7 (5 in scope, 2 out of scope)" in out
    assert "size status: ok 5, missing 1, ambiguous 1" in out
    assert "reasons: no_size_found 1, multiple_sizes 1" in out
    assert "in-scope titles with pack-count wording (N3 does not handle these): 1" in out
    assert "rows.csv 1: 'pack of 2'" in out
    assert "'6 packs' (out of scope)" in out
    assert "Bangla currency fraction signs (U+09F4 to U+09F9): 1" in out
    assert "words after a number that are not units: packs 1, pcs 1" in out
    assert "most frequent words (evidence for N5): test 6" in out


def test_a_word_after_two_numbers_is_still_counted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Regression test: the second number was once consumed with the first, so "pcs" was missed.
    path = write_csv(tmp_path / "rows.csv", [make_row("1", "Test Item 2 3 pcs")])
    main([str(path)])
    assert "words after a number that are not units: pcs 1" in capsys.readouterr().out


def test_the_report_writes_no_files(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "rows.csv", ROWS)
    before = sorted(tmp_path.rglob("*"))
    main([str(path)])
    assert sorted(tmp_path.rglob("*")) == before


def test_a_byte_order_mark_is_noted_but_the_file_is_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_csv(tmp_path / "rows.csv", ROWS[:1], prefix=codecs.BOM_UTF8)
    assert main([str(path)]) == 0
    out = capsys.readouterr().out
    assert "byte-order mark" in out
    assert "rows: 1 (1 in scope" in out


def test_an_unreadable_file_gives_status_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "bad.csv"
    path.write_bytes(b"title_raw\nTest \xff Rice\n")
    assert main([str(path)]) == 1
    assert "cannot read" in capsys.readouterr().out


def test_a_file_without_a_title_column_gives_status_one(tmp_path: Path) -> None:
    path = tmp_path / "other.csv"
    path.write_bytes(b"name\nTest\n")
    assert main([str(path)]) == 1
