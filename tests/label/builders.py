"""Builders for the tests of the labelling code: invented listings, label rows and files.

Every value is invented. Bangla text is built from code points (see tests/helpers.py). The
listings are written to a scratch data/raw folder; nothing here touches the real data.
"""

import csv
import io
from datetime import UTC, datetime
from pathlib import Path

from src.collect.validate import COLUMNS
from src.label.records import LABEL_COLUMNS, make_pair_id
from tests.helpers import bn

CHAL = bn(0x099A, 0x09BE, 0x09B2)  # চাল
KEJI = bn(0x0995, 0x09C7, 0x099C, 0x09BF)  # কেজি

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
FIRST_TIME = "2026-11-10T10:00:00+06:00"
SECOND_TIME = "2026-11-10T10:05:00+06:00"
GUIDELINES_TEXT = """# Labelling Guidelines

Version: 0.2

## Version history

- 0.1 (2026-11-04): pilot draft.
- 0.2 (2026-11-05): defined the script field.
"""

# (source, listing_id, title_raw, brand, category, script). Prices are fixed per source below.
LISTINGS = [
    ("pandamart", "1001", "Test Rice 1kg", "", "rice", "english"),
    ("pandamart", "1002", "Test Rice 5kg", "", "rice", "english"),
    ("pandamart", "1003", "Test Oil 2 x 500ml", "", "cooking_oil", "english"),
    ("pandamart", "1004", "Test Chilli Powder 500gm + 50gm Free", "", "spices", "english"),
    ("pandamart", "1005", f"{CHAL} 1 {KEJI}", "", "rice", "bangla"),
    ("pandamart", "1006", "Test Mustard Oil 1L", "", "cooking_oil", "english"),
    ("pandamart", "1007", "Zorbaxo Dal 500gm", "", "lentils", "english"),
    ("pandamart", "1008", "Test Rice", "", "rice", "english"),
    ("meenabazar", "2001", "TEST RICE 1KG", "Test Foods Ltd", "rice", "english"),
    ("meenabazar", "2002", "TEST RICE 5KG", "Test Foods Ltd", "rice", "english"),
    ("meenabazar", "2003", "TEST OIL 1000ML", "No Brand", "cooking_oil", "english"),
    ("meenabazar", "2004", "TEST CHILLI POWDER 500GM", "Test Foods Ltd", "spices", "english"),
    ("meenabazar", "2005", "TEST RICE 1KG", "No Brand", "rice", "english"),
    ("meenabazar", "2006", "TEST MUSTARD OIL 1KG", "Test Foods Ltd", "cooking_oil", "english"),
    ("meenabazar", "2007", "ZORBAXO DAL 500GM", "Test Foods Ltd", "lentils", "english"),
]
# Prices that no other test value can equal; the labelling tool must never show them.
PRICES = {"pandamart": "7777.77", "meenabazar": "8888.88"}


def listing_row(
    source: str,
    listing_id: str,
    title: str,
    brand: str = "",
    category: str = "rice",
    script: str = "english",
    **changes: str,
) -> dict[str, str]:
    """Return one invented listing as a row of a data/raw file."""
    row = {
        "source": source,
        "listing_id": listing_id,
        "title_raw": title,
        "brand": brand,
        "size_value": "",
        "size_unit": "",
        "price_bdt": PRICES.get(source, "100"),
        "category": category,
        "source_category": "",
        "script": script,
        "url": f"https://example.invalid/{source}/{listing_id}",
        "collected_at": "2026-11-05T19:30:00+06:00",
    }
    row.update(changes)
    return row


def csv_bytes(columns: tuple[str, ...], rows: list[dict[str, str]] | list[list[str]]) -> bytes:
    """Return a CSV file (LF line ends, UTF-8) with the header and the rows."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row[column] for column in columns] if isinstance(row, dict) else row)
    return buffer.getvalue().encode("utf-8")


def write_raw(
    raw_dir: Path,
    listings: list[tuple[str, ...]] | None = None,
    prices: dict[tuple[str, str], str] | None = None,
) -> Path:
    """Write the invented listings into a scratch data/raw folder, one file per source.

    Args:
        raw_dir: The folder.
        listings: Tuples of (source, listing_id, title, brand, category, script); defaults to
            LISTINGS.
        prices: Prices by (source, listing_id) that replace the default price of the source.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    items = listings or LISTINGS
    for source in sorted({item[0] for item in items}):
        rows = []
        for item in items:
            if item[0] != source:
                continue
            price = (prices or {}).get((item[0], item[1]), PRICES.get(source, "100"))
            rows.append(listing_row(*item, price_bdt=price))
        (raw_dir / f"{source}_20261105.csv").write_bytes(csv_bytes(COLUMNS, rows))
    return raw_dir


def write_guidelines(directory: Path, text: str = GUIDELINES_TEXT) -> Path:
    """Write a small guidelines file with the versions 0.1 and 0.2."""
    path = directory / "labelling_guidelines.md"
    path.write_text(text, encoding="utf-8")
    return path


def pair(pandamart_id: str, meenabazar_id: str) -> str:
    """Return the pair_id of a pandamart listing and a meenabazar listing."""
    return make_pair_id("pandamart", pandamart_id, "meenabazar", meenabazar_id)


def label_row(
    pandamart_id: str = "1001",
    meenabazar_id: str = "2001",
    label: str = "match",
    note: str = "",
    labeller: str = "L1",
    labelled_at: str = FIRST_TIME,
    version: str = "0.2",
    **changes: str,
) -> dict[str, str]:
    """Return one valid row of a label file; the meenabazar listing is the left one."""
    row = {
        "pair_id": pair(pandamart_id, meenabazar_id),
        "left_source": "meenabazar",
        "left_id": meenabazar_id,
        "right_source": "pandamart",
        "right_id": pandamart_id,
        "label": label,
        "note": note,
        "labeller": labeller,
        "labelled_at": labelled_at,
        "guidelines_version": version,
    }
    row.update(changes)
    return row


def label_file(rows: list[dict[str, str]]) -> bytes:
    """Return the bytes of a label file holding the rows."""
    return csv_bytes(LABEL_COLUMNS, rows)


# Values that must never reach a labeller. They are written into the candidates file of the
# tool tests, and the tests check that they appear nowhere in what the tool shows or saves.
POISON = ("0.4242", "0.9191", "0.7373", "ZZPOISON")


def write_candidates_file(path: Path, pair_ids: list[str]) -> Path:
    """Write a candidates file whose columns other than pair_id hold values the tool must ignore."""
    rows = [[pair_id, "rice", POISON[0], "ZZPOISON", POISON[1], POISON[2]] for pair_id in pair_ids]
    columns = (
        "pair_id",
        "category",
        "char3_jaccard",
        "size_relation",
        "price_ratio",
        "unit_price_ratio",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(csv_bytes(columns, rows))
    return path
