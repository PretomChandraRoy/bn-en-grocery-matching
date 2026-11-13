"""Tests for src.label.listings. All data is invented (see tests/label/builders.py)."""

import dataclasses
from decimal import Decimal
from pathlib import Path

import pytest

from src.collect.validate import COLUMNS
from src.label.listings import (
    Listing,
    load_listings,
    read_candidate_pair_ids,
    read_prices,
)
from tests.helpers import bn
from tests.label.builders import (
    CHAL,
    KEJI,
    LISTINGS,
    PRICES,
    csv_bytes,
    listing_row,
    write_raw,
)

BANGLA_ONE = bn(0x09E7)  # ১
BANGLA_FIVE_ZERO = bn(0x09EB, 0x09E6)  # ৫০


def test_all_listings_are_read_with_their_fields(tmp_path: Path) -> None:
    listings = load_listings(write_raw(tmp_path / "raw"))
    assert len(listings) == len(LISTINGS)
    first = listings[("pandamart", "1001")]
    assert first.title_raw == "Test Rice 1kg"
    assert first.category == "rice"
    assert first.key == ("pandamart", "1001")
    assert listings[("meenabazar", "2001")].brand == "Test Foods Ltd"


def test_a_listing_has_no_price(tmp_path: Path) -> None:
    # The labelling tool builds on Listing, and labellers must not see the price.
    names = {item.name for item in dataclasses.fields(Listing)}
    assert not any("price" in name for name in names)
    listing = load_listings(write_raw(tmp_path / "raw"))[("pandamart", "1001")]
    assert PRICES["pandamart"] not in repr(listing)


def test_a_missing_folder_gives_no_listings(tmp_path: Path) -> None:
    assert load_listings(tmp_path / "missing") == {}
    assert read_prices(tmp_path / "missing") == {}


def test_titles_are_read_as_utf_8(tmp_path: Path) -> None:
    raw = write_raw(tmp_path / "raw")
    listing = load_listings(raw)[("pandamart", "1005")]
    assert listing.title_raw == f"{CHAL} 1 {KEJI}"


def test_prices_are_read_separately_as_decimals(tmp_path: Path) -> None:
    prices = read_prices(write_raw(tmp_path / "raw"))
    assert prices[("pandamart", "1001")] == Decimal("7777.77")
    assert prices[("meenabazar", "2001")] == Decimal("8888.88")
    assert len(prices) == len(LISTINGS)


def test_a_price_that_is_not_a_number_is_an_error(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    row = listing_row("pandamart", "1", "Zorbaxo Rice", price_bdt="abc")
    (raw / "pandamart_20261105.csv").write_bytes(csv_bytes(COLUMNS, [row]))
    with pytest.raises(ValueError, match=r"pandamart_20261105.csv, row 2: price_bdt") as caught:
        read_prices(raw)
    assert "Zorbaxo" not in str(caught.value)


def test_a_listing_in_two_files_is_an_error_that_names_no_title(tmp_path: Path) -> None:
    raw = write_raw(tmp_path / "raw")
    row = listing_row("pandamart", "1001", "Zorbaxo Rice 1kg")
    (raw / "pandamart_20261106.csv").write_bytes(csv_bytes(COLUMNS, [row]))
    with pytest.raises(
        ValueError, match=r"pandamart:1001 is also in pandamart_20261105.csv"
    ) as caught:
        load_listings(raw)
    assert "Zorbaxo" not in str(caught.value)


def test_a_file_with_the_wrong_header_is_an_error(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "pandamart_20261105.csv").write_bytes(csv_bytes(COLUMNS[:-1], []))
    with pytest.raises(ValueError, match="12 listing columns"):
        load_listings(raw)


def test_a_row_with_the_wrong_number_of_fields_is_an_error(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "pandamart_20261105.csv").write_bytes(csv_bytes(COLUMNS, [["a", "b"]]))
    with pytest.raises(ValueError, match="row 2, does not have 12 fields"):
        load_listings(raw)


# The candidates file.


def write_candidates(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8", newline="")
    return path


def test_candidate_pair_ids_are_read(tmp_path: Path) -> None:
    path = write_candidates(tmp_path / "c.csv", "pair_id,category\na:1|b:2,rice\na:1|b:3,rice\n")
    assert read_candidate_pair_ids(path) == frozenset({"a:1|b:2", "a:1|b:3"})


def test_a_missing_candidates_file_gives_none(tmp_path: Path) -> None:
    assert read_candidate_pair_ids(tmp_path / "missing.csv") is None


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("category\nrice\n", "no pair_id column"),
        ("pair_id\na:1|b:2\na:1|b:2\n", "appears twice"),
        ("pair_id,x\n,rice\n", "pair_id is empty"),
    ],
)
def test_a_malformed_candidates_file_is_an_error(tmp_path: Path, text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        read_candidate_pair_ids(write_candidates(tmp_path / "c.csv", text))


def test_an_empty_candidates_file_with_a_header_has_no_pairs(tmp_path: Path) -> None:
    assert read_candidate_pair_ids(write_candidates(tmp_path / "c.csv", "pair_id\n")) == frozenset()
