"""Candidate pairs for labelling: every cross-shop pair within a category, with its features.

    python -m src.label.candidates                    write data/interim/candidates.csv
    python -m src.label.candidates --preview-strata   print how the features would split the
                                                      pairs into sampling strata; writes nothing

For the pilot, a candidate is every pair of listings from two different sources in the same
project category (pandamart by meenabazar). The file lists the pairs with the features that the
sampling strata will use later: text similarity of the product names, agreement of the sizes read
by N3, and price proximity (features.py). It is generated from data/raw only, is the same on every
run (no timestamp, no random choice), and holds IDs and numbers, never a title. Within a pair
the alphabetically first source is the left one, as docs/data_entry_rules.md requires.

The strata are not decided yet. --preview-strata applies provisional thresholds, which can be
changed on the command line, so that the strata can be tried on real data before the full
collection. Nothing in the file depends on them: its strategy column only says how the pair was
chosen (every pair), and the labelling tool shows labellers neither the features nor the strata.

The price is read here, from data/raw, only to work out the price features; it is never written.
"""

import argparse
import csv
import io
import os
import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from src.collect.validate import RAW_DIR
from src.label.features import (
    char3_jaccard,
    format_decimal,
    format_total,
    name_tokens,
    parse_listing_size,
    ratio,
    size_ratio,
    size_relation,
    token_jaccard,
    token_overlap,
    total_amount,
    unit_price_ratio,
)
from src.label.listings import (
    Listing,
    ListingKey,
    load_listings,
    read_candidate_pair_ids,
    read_prices,
)
from src.label.records import CANDIDATES_PATH, cross_script, make_pair_id
from src.normalise.sizes import SizeResult

STRATEGY_PILOT = "pilot_all_pairs"

# The columns of data/interim/candidates.csv, in order. docs/data_entry_rules.md describes them,
# and tests/label/test_candidates_sync.py checks that the two agree.
CANDIDATE_COLUMNS = (
    "pair_id",
    "left_source",
    "left_id",
    "right_source",
    "right_id",
    "category",
    "strategy",
    "token_jaccard",
    "token_overlap",
    "char3_jaccard",
    "size_relation",
    "left_kind",
    "left_total",
    "left_packs",
    "right_kind",
    "right_total",
    "right_packs",
    "size_ratio",
    "price_ratio",
    "unit_price_ratio",
    "left_script",
    "right_script",
    "cross_script",
)

# The provisional strata, in the order in which a pair is assigned to the first that fits.
STRATA = ("wording_variation", "likely_match", "hard_negative", "random_negative")


@dataclass(frozen=True)
class Thresholds:
    """The provisional limits that split pairs into strata. They are tried, not decided.

    Attributes:
        high: Text similarity (char3_jaccard) from which two names count as similar.
        low: Text similarity below which two names count as worded differently.
        price_min: The price ratio from which two prices count as close.
    """

    high: Decimal = Decimal("0.60")
    low: Decimal = Decimal("0.35")
    price_min: Decimal = Decimal("0.70")


def _read_size(listing: Listing) -> SizeResult:
    """Return the N3 reading of a listing's size."""
    return parse_listing_size(listing)


def _pair_row(
    left: Listing,
    right: Listing,
    names: dict[ListingKey, tuple[str, ...]],
    prices: dict[ListingKey, Decimal],
) -> dict[str, str]:
    """Build the row of one pair."""
    left_size, right_size = _read_size(left), _read_size(right)
    left_ok, right_ok = left_size.status == "ok", right_size.status == "ok"
    left_name, right_name = names[left.key], names[right.key]
    left_price, right_price = prices[left.key], prices[right.key]
    return {
        "pair_id": make_pair_id(left.source, left.listing_id, right.source, right.listing_id),
        "left_source": left.source,
        "left_id": left.listing_id,
        "right_source": right.source,
        "right_id": right.listing_id,
        "category": left.category,
        "strategy": STRATEGY_PILOT,
        "token_jaccard": format_decimal(token_jaccard(left_name, right_name)),
        "token_overlap": format_decimal(token_overlap(left_name, right_name)),
        "char3_jaccard": format_decimal(char3_jaccard(left_name, right_name)),
        "size_relation": size_relation(left_size, right_size),
        "left_kind": (left_size.kind or "") if left_ok else "",
        "left_total": format_total(total_amount(left_size)) if left_ok else "",
        "left_packs": str(left_size.pack_count) if left_ok else "",
        "right_kind": (right_size.kind or "") if right_ok else "",
        "right_total": format_total(total_amount(right_size)) if right_ok else "",
        "right_packs": str(right_size.pack_count) if right_ok else "",
        "size_ratio": format_decimal(size_ratio(left_size, right_size)),
        "price_ratio": format_decimal(ratio(left_price, right_price)),
        "unit_price_ratio": format_decimal(
            unit_price_ratio(left_price, left_size, right_price, right_size)
        ),
        "left_script": left.script,
        "right_script": right.script,
        "cross_script": "true" if cross_script(left.title_raw, right.title_raw) else "false",
    }


def expected_pair_count(listings: dict[ListingKey, Listing]) -> int:
    """Count the pairs there should be: per category, every pair of listings of two sources.

    This is worked out from the counts of listings alone, as a check on build_candidates.
    """
    counts = Counter((item.category, item.source) for item in listings.values())
    total = 0
    for category in {category for category, _ in counts}:
        per_source = [n for (name, _), n in counts.items() if name == category]
        everyone = sum(per_source)
        total += (everyone * everyone - sum(n * n for n in per_source)) // 2
    return total


def build_candidates(
    listings: dict[ListingKey, Listing], prices: dict[ListingKey, Decimal]
) -> list[dict[str, str]]:
    """Build the rows of the candidate pairs file.

    Args:
        listings: The listings, by (source, listing_id).
        prices: The price of each listing; used only for the price features.

    Returns:
        One row per pair of listings from two different sources in the same category, sorted
        by category and pair_id.

    Raises:
        RuntimeError: If the number of rows differs from expected_pair_count, which would be a
            bug in this function.
    """
    names = {key: name_tokens(item.title_raw) for key, item in listings.items()}
    groups: dict[tuple[str, str], list[Listing]] = {}
    for item in listings.values():
        groups.setdefault((item.category, item.source), []).append(item)
    sources = sorted({item.source for item in listings.values()})
    categories = sorted({item.category for item in listings.values()})
    rows = []
    for category in categories:
        for index, first in enumerate(sources):
            for second in sources[index + 1 :]:
                for left in groups.get((category, first), []):
                    for right in groups.get((category, second), []):
                        rows.append(_pair_row(left, right, names, prices))
    rows.sort(key=lambda row: (row["category"], row["pair_id"]))
    if len(rows) != expected_pair_count(listings):
        raise RuntimeError("the number of candidate pairs differs from the count expected")
    return rows


def render_csv(rows: Sequence[dict[str, str]]) -> bytes:
    """Return the file: UTF-8 without a byte-order mark, LF line ends, the 23 columns in order."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CANDIDATE_COLUMNS)
    for row in rows:
        writer.writerow([row[column] for column in CANDIDATE_COLUMNS])
    return buffer.getvalue().encode("utf-8")


def write_candidates(rows: Sequence[dict[str, str]], output: Path, *, replace: bool = False) -> str:
    """Write the candidate pairs file, unless that would lose pairs that may have been labelled.

    The file is written to a temporary file next to it and then moved into place, so a failure
    never leaves half a file.

    Args:
        rows: The rows from build_candidates.
        output: The file to write.
        replace: Allow the new file to lack pairs that the existing file has, or to replace an
            existing file that cannot be read.

    Returns:
        "created", "updated" or "unchanged".

    Raises:
        ValueError: If the existing file has pairs that the new rows lack (or cannot be read)
            and replace is false.
    """
    data = render_csv(rows)
    status = "created"
    if output.is_file():
        if output.read_bytes() == data:
            return "unchanged"
        status = "updated"
        try:
            old = read_candidate_pair_ids(output) or frozenset()
        except ValueError as error:
            if not replace:
                raise ValueError(f"{output.name} exists but cannot be read ({error})") from None
            old = frozenset()
        lost = old - {row["pair_id"] for row in rows}
        if lost and not replace:
            raise ValueError(
                f"{len(lost)} pairs of the existing {output.name} are not in the new one; "
                "labels may refer to them"
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, output)
    return status


# The preview of the sampling strata.


def _decimal(value: str) -> Decimal | None:
    """Read a number from the file, or None if the field is empty."""
    return Decimal(value) if value else None


def assign_stratum(row: dict[str, str], limits: Thresholds) -> str:
    """Say which provisional stratum a pair falls into, by the first rule that fits.

    * wording_variation: the sizes are the same and the prices are close, but the names are not
      similar (the names are worded differently);
    * likely_match: the sizes are the same and the names are similar;
    * hard_negative: the names are similar but the sizes are not the same (or are not known);
    * random_negative: every other pair.

    Args:
        row: A row of the candidate pairs file.
        limits: The thresholds.

    Returns:
        One of STRATA.
    """
    similarity = Decimal(row["char3_jaccard"])
    same_size = row["size_relation"] == "same"
    price = _decimal(row["price_ratio"])
    if same_size and similarity < limits.low and price is not None and price >= limits.price_min:
        return "wording_variation"
    if same_size and similarity >= limits.high:
        return "likely_match"
    if similarity >= limits.high:
        return "hard_negative"
    return "random_negative"


def strata_preview(rows: Sequence[dict[str, str]], limits: Thresholds) -> str:
    """Describe how the pairs would split into strata, and how the features are spread.

    Args:
        rows: The rows from build_candidates.
        limits: The provisional thresholds.

    Returns:
        The text to print.
    """
    lines = [
        f"{len(rows)} candidate pairs. Provisional thresholds (not decided): "
        f"similar from {limits.high} (char3_jaccard), different below {limits.low}, "
        f"prices close from {limits.price_min}.",
        "",
        "Pairs by stratum and category (a pair goes to the first stratum that fits):",
    ]
    strata_of = [assign_stratum(row, limits) for row in rows]
    categories = sorted({row["category"] for row in rows})
    width = max([len(name) for name in (*STRATA, "all pairs")])
    lines.append(f"  {'':{width}}  {'all':>5}  " + "  ".join(f"{c:>11}" for c in categories))
    for stratum in STRATA:
        picked = [row for row, name in zip(rows, strata_of, strict=True) if name == stratum]
        by_category = Counter(row["category"] for row in picked)
        lines.append(
            f"  {stratum:{width}}  {len(picked):>5}  "
            + "  ".join(f"{by_category[c]:>11}" for c in categories)
        )
    by_category = Counter(row["category"] for row in rows)
    lines.append(
        f"  {'all pairs':{width}}  {len(rows):>5}  "
        + "  ".join(f"{by_category[c]:>11}" for c in categories)
    )
    if rows:
        share = Decimal(strata_of.count("wording_variation")) * 100 / Decimal(len(rows))
        lines.append(
            f"  wording_variation is {share:.1f} percent of the pairs (the plan says about 15)"
        )
    lines += [
        "",
        "Text similarity (char3_jaccard) by size relation: pairs, minimum, median, maximum:",
    ]
    for relation in (
        "same",
        "same_total_different_pack",
        "different_amount",
        "different_kind",
        "unknown",
    ):
        values = [Decimal(row["char3_jaccard"]) for row in rows if row["size_relation"] == relation]
        if values:
            lines.append(
                f"  {relation:26} {len(values):>4}  {min(values):.4f}  "
                f"{statistics.median(values):.4f}  {max(values):.4f}"
            )
    same = [row for row in rows if row["size_relation"] == "same"]
    prices = [Decimal(row["price_ratio"]) for row in same if row["price_ratio"]]
    if prices:
        lines += [
            "",
            "Price ratio for pairs of the same size: pairs, minimum, median, maximum:",
            f"  {len(prices):>4}  {min(prices):.4f}  "
            f"{statistics.median(prices):.4f}  {max(prices):.4f}",
        ]
    return "\n".join(lines)


# The command line.


def _summary(rows: Sequence[dict[str, str]]) -> list[str]:
    """Describe the pairs by category and by size relation."""
    categories = Counter(row["category"] for row in rows)
    relations = Counter(row["size_relation"] for row in rows)
    return [
        "  by category: " + ", ".join(f"{name} {categories[name]}" for name in sorted(categories)),
        "  by size relation: "
        + ", ".join(f"{name} {relations[name]}" for name in sorted(relations)),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Generate the candidate pairs, or preview the strata.

    Args:
        argv: The command-line arguments, without the program name. Defaults to sys.argv.

    Returns:
        The exit status: 0 on success, otherwise 1.
    """
    parser = argparse.ArgumentParser(
        prog="python -m src.label.candidates",
        description="Write data/interim/candidates.csv from the listings in data/raw.",
    )
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--output", type=Path, default=CANDIDATES_PATH)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="allow the new file to lack pairs that the existing file has",
    )
    parser.add_argument(
        "--preview-strata", action="store_true", help="print the strata preview; write nothing"
    )
    defaults = Thresholds()
    parser.add_argument("--high", type=Decimal, default=defaults.high)
    parser.add_argument("--low", type=Decimal, default=defaults.low)
    parser.add_argument("--price-min", type=Decimal, default=defaults.price_min)
    args = parser.parse_args(argv)
    if (
        not Decimal(0) <= args.low <= args.high <= Decimal(1)
        or not Decimal(0) < args.price_min <= 1
    ):
        print("error: the thresholds need 0 <= low <= high <= 1 and 0 < price-min <= 1")
        return 1
    try:
        listings = load_listings(args.raw_dir)
        rows = build_candidates(listings, read_prices(args.raw_dir))
    except ValueError as error:
        print(f"error: {error}")
        return 1
    if args.preview_strata:
        print(strata_preview(rows, Thresholds(args.high, args.low, args.price_min)))
        return 0
    try:
        status = write_candidates(rows, args.output, replace=args.replace)
    except ValueError as error:
        print(f"error: {error}; use --replace to write the file anyway")
        return 1
    print(f"{args.output}: {len(rows)} pairs ({status})")
    for line in _summary(rows):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
