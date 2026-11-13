"""Reading the collected listings from data/raw for the labelling code.

The validator for labelled files, the candidate pair generator and the labelling tool all need
the listings behind a pair, and the pair IDs of the candidates file. This module reads them once,
in one way.

A Listing deliberately has no price. The labelling tool builds on it, and labellers must not see
the price (docs/labelling_guidelines.md), so code that only has a Listing cannot show one. The
pair generator reads prices separately, with read_prices.

This module does not import the size parser (N3), on purpose: the labelling tool imports it,
and the tool must not show N3's reading, because the labels will later be used to evaluate that
parser. The reading of a listing's size is parse_listing_size in features.py, which only the
validator and the pair generator use.
"""

import csv
from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.collect.validate import COLUMNS, RAW_DIR

ListingKey = tuple[str, str]


@dataclass(frozen=True)
class Listing:
    """One collected listing, without its price.

    Attributes:
        source: The short source name, for example "pandamart".
        listing_id: The source's own identifier.
        title_raw: The title exactly as collected.
        brand: The shop's brand field as shown; empty if the shop has none.
        size_value: The shop's size value field; empty if the shop has none.
        size_unit: The shop's size unit field; empty if the shop has none.
        category: The project category.
        source_category: The shop's own category label; may be empty.
        script: The hand-entered script value.
        url: The product page address.
    """

    source: str
    listing_id: str
    title_raw: str
    brand: str
    size_value: str
    size_unit: str
    category: str
    source_category: str
    script: str
    url: str

    @property
    def key(self) -> ListingKey:
        """The pair (source, listing_id) that identifies the listing."""
        return (self.source, self.listing_id)


# The columns of a data/raw file that a Listing holds: all but the price and the collection time.
_LISTING_FIELDS = tuple(item.name for item in fields(Listing))


def _read_rows(raw_dir: Path) -> list[tuple[str, int, dict[str, str]]]:
    """Read every row of every CSV file in raw_dir: (file name, row number, row)."""
    rows = []
    for path in sorted(raw_dir.glob("*.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != COLUMNS:
                raise ValueError(f"{path.name} does not have the 12 listing columns in order")
            for number, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"{path.name}, row {number}, does not have 12 fields")
                rows.append((path.name, number, row))
    return rows


def load_listings(raw_dir: Path = RAW_DIR) -> dict[ListingKey, Listing]:
    """Read all listings in the CSV files of a data/raw folder.

    Args:
        raw_dir: The data/raw folder. A missing folder gives no listings.

    Returns:
        The listings by (source, listing_id), in the order of the files and rows.

    Raises:
        ValueError: If a file does not have the 12 listing columns, a row has the wrong number
            of fields, or a (source, listing_id) appears twice. The message names the file and
            the row, never a title.
    """
    listings: dict[ListingKey, Listing] = {}
    if not raw_dir.is_dir():
        return listings
    first_seen: dict[ListingKey, str] = {}
    for file_name, number, row in _read_rows(raw_dir):
        listing = Listing(**{name: row[name] for name in _LISTING_FIELDS})
        if listing.key in listings:
            raise ValueError(
                f"{file_name}, row {number}: listing {listing.source}:{listing.listing_id} "
                f"is also in {first_seen[listing.key]}"
            )
        listings[listing.key] = listing
        first_seen[listing.key] = f"{file_name}, row {number}"
    return listings


def read_prices(raw_dir: Path = RAW_DIR) -> dict[ListingKey, Decimal]:
    """Read the price of every listing in a data/raw folder.

    Only the pair generator uses this. The labelling tool must never call it.

    Args:
        raw_dir: The data/raw folder. A missing folder gives no prices.

    Returns:
        The price_bdt of each listing by (source, listing_id).

    Raises:
        ValueError: If a file is malformed (see load_listings) or a price is not a number.
    """
    prices: dict[ListingKey, Decimal] = {}
    if not raw_dir.is_dir():
        return prices
    for file_name, number, row in _read_rows(raw_dir):
        try:
            prices[(row["source"], row["listing_id"])] = Decimal(row["price_bdt"])
        except InvalidOperation:
            raise ValueError(f"{file_name}, row {number}: price_bdt is not a number") from None
    return prices


def read_candidate_pair_ids(path: Path) -> frozenset[str] | None:
    """Read the pair_id column of the candidate pairs file.

    Args:
        path: The candidates file, normally data/interim/candidates.csv.

    Returns:
        The pair_id values, or None if the file does not exist.

    Raises:
        ValueError: If the file has no pair_id column, a pair_id is empty or a pair_id appears
            twice.
    """
    if not path.is_file():
        return None
    ids: set[str] = set()
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if "pair_id" not in (reader.fieldnames or ()):
            raise ValueError(f"{path.name} has no pair_id column")
        for number, row in enumerate(reader, start=2):
            pair_id = row["pair_id"] or ""
            if not pair_id:
                raise ValueError(f"{path.name}, row {number}: pair_id is empty")
            if pair_id in ids:
                raise ValueError(f"{path.name}, row {number}: pair_id {pair_id} appears twice")
            ids.add(pair_id)
    return frozenset(ids)
