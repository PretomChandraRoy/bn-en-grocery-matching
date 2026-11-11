"""Tests for src.collect.validate.

All rows are invented; no real listing appears here. Characters outside ASCII are built from code
points (see tests/helpers.py).
"""

import codecs
import csv
import io
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.collect.validate import (
    COLUMNS,
    REQUIRED_COLUMNS,
    ValidationResult,
    has_bangla_letters,
    main,
    parse_timestamp,
    validate_file,
)
from tests.helpers import bn

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
STORE = (
    "https://www.foodpanda.com.bd/darkstore/vbpl/pandamart-gulshan-banani/category/"
    "00000000-0000-4000-8000-000000000000/product/"
)
CHAL = bn(0x099A, 0x09BE, 0x09B2)  # চাল
KEJI = bn(0x0995, 0x09C7, 0x099C, 0x09BF)  # কেজি
RUPEE = bn(0x09F3)  # ৳
ZERO_WIDTH_SPACE = bn(0x200B)
RIGHT_QUOTE = bn(0x2019)
BANGLA_4001 = bn(0x09EA, 0x09E6, 0x09E6, 0x09E7)  # ৪০০১
MEENA = "https://meenabazaronline.com/product/"
SLUG = "TEST-BRAND-SAMPLE-RICE-2KG"


def make_row(listing_id: str = "1001", **changes: str) -> dict[str, str]:
    row = {
        "source": "pandamart",
        "listing_id": listing_id,
        "title_raw": "Test Rice 1kg",
        "brand": "",
        "size_value": "",
        "size_unit": "",
        "price_bdt": "100",
        "category": "rice",
        "source_category": "Test Category",
        "script": "english",
        "url": STORE + listing_id,
        "collected_at": "2026-11-05T19:30:00+06:00",
    }
    row.update(changes)
    return row


def make_meena_row(listing_id: str = "40001", **changes: str) -> dict[str, str]:
    row = make_row(
        listing_id,
        source="meenabazar",
        title_raw="TEST BRAND SAMPLE RICE 2KG",
        brand="Test Foods Ltd",
        price_bdt="420.00",
        source_category="",
        url=f"{MEENA}{SLUG}/{listing_id}",
    )
    row.update(changes)
    return row


def csv_bytes(rows: list, header: tuple[str, ...] | list[str] = COLUMNS) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([row[column] for column in COLUMNS] if isinstance(row, dict) else row)
    return buffer.getvalue().encode("utf-8")


def validate(tmp_path: Path, content: bytes, name: str = "collected.csv") -> ValidationResult:
    path = tmp_path / name
    path.write_bytes(content)
    return validate_file(path, raw_dir=tmp_path / "raw", now=NOW)


def errors(result: ValidationResult) -> list[str]:
    return [problem.describe() for problem in result.errors]


def warnings(result: ValidationResult) -> list[str]:
    return [problem.describe() for problem in result.warnings]


# A valid file, and the name it would get in data/raw.


def test_a_valid_file_has_no_problems(tmp_path: Path) -> None:
    result = validate(tmp_path, csv_bytes([make_row("1001"), make_row("1002")]))
    assert result.problems == []
    assert result.row_count == 2
    assert result.accepted_name == "pandamart_20261105.csv"


def test_the_file_is_named_after_its_last_collection_day(tmp_path: Path) -> None:
    rows = [
        make_row("1001", collected_at="2026-11-06T12:22:00+06:00"),
        make_row("1002", collected_at="2026-11-05T19:30:00+06:00"),
    ]
    assert validate(tmp_path, csv_bytes(rows)).accepted_name == "pandamart_20261106.csv"


# Encoding and structure.


def test_a_byte_order_mark_is_an_error(tmp_path: Path) -> None:
    result = validate(tmp_path, codecs.BOM_UTF8 + csv_bytes([make_row()]))
    assert len(result.errors) == 1
    assert "byte-order mark" in errors(result)[0]


def test_invalid_utf8_is_an_error(tmp_path: Path) -> None:
    content = csv_bytes([make_row()]).replace(b"Test Rice", b"Test \xff Rice")
    result = validate(tmp_path, content)
    assert "not valid UTF-8" in errors(result)[0]


def test_an_empty_file_is_an_error(tmp_path: Path) -> None:
    assert "the file is empty" in errors(validate(tmp_path, b""))[0]


def test_a_file_with_only_a_header_is_an_error(tmp_path: Path) -> None:
    assert "no data rows" in errors(validate(tmp_path, csv_bytes([])))[0]


@pytest.mark.parametrize(
    "header",
    [
        pytest.param([COLUMNS[1], COLUMNS[0], *COLUMNS[2:]], id="two-columns-swapped"),
        pytest.param(list(COLUMNS[:-1]), id="a-column-missing"),
        pytest.param([*COLUMNS, "notes"], id="an-extra-column"),
        pytest.param([column.upper() for column in COLUMNS], id="upper-case-names"),
    ],
)
def test_the_header_must_be_exactly_the_twelve_columns(tmp_path: Path, header: list[str]) -> None:
    content = csv_bytes([["x"] * len(header)], header=header)
    result = validate(tmp_path, content)
    assert len(result.errors) == 1
    assert "header" in errors(result)[0]


def test_a_row_with_the_wrong_number_of_fields_is_an_error(tmp_path: Path) -> None:
    short = [make_row()[column] for column in COLUMNS[:-1]]
    result = validate(tmp_path, csv_bytes([short]))
    assert "11 fields; expected 12" in errors(result)[0]


def test_an_empty_row_is_an_error(tmp_path: Path) -> None:
    content = (
        csv_bytes([make_row("1001")]) + b"\n" + csv_bytes([make_row("1002")]).split(b"\n", 1)[1]
    )
    result = validate(tmp_path, content)
    assert errors(result) == ["error (row 3): the row is empty"]


# Required fields and allowed values.


@pytest.mark.parametrize("column", REQUIRED_COLUMNS)
def test_a_required_field_must_not_be_empty(tmp_path: Path, column: str) -> None:
    row = make_row()
    row[column] = ""  # set afterwards, so that the URL keeps its product ID
    result = validate(tmp_path, csv_bytes([row]))
    assert errors(result) == [f"error (row 2, {column}): is empty"]


def test_an_out_of_scope_row_with_no_category_cannot_enter_data_raw(tmp_path: Path) -> None:
    result = validate(tmp_path, csv_bytes([make_row(category="")]))
    assert result.accepted_name is None


@pytest.mark.parametrize(("column", "value"), [("category", "flour"), ("script", "latin")])
def test_category_and_script_must_be_allowed_values(
    tmp_path: Path, column: str, value: str
) -> None:
    result = validate(tmp_path, csv_bytes([make_row(**{column: value})]))
    assert len(result.errors) == 1
    assert f"(row 2, {column})" in errors(result)[0]


def test_a_source_that_is_not_cleared_is_an_error(tmp_path: Path) -> None:
    result = validate(tmp_path, csv_bytes([make_row(source="chaldal")]))
    assert "not a cleared source" in errors(result)[0]


def test_a_file_must_hold_one_source_only(tmp_path: Path) -> None:
    result = validate(tmp_path, csv_bytes([make_row("1001"), make_row("1002", source="other")]))
    assert any("more than one source" in message for message in errors(result))


# listing_id and url.


@pytest.mark.parametrize(
    ("listing_id", "expected"),
    [
        pytest.param("10a1", "does not have the form", id="not-digits"),
        pytest.param("1001 ", "contains a space", id="trailing-space"),
    ],
)
def test_listing_id_form(tmp_path: Path, listing_id: str, expected: str) -> None:
    result = validate(tmp_path, csv_bytes([make_row(listing_id, url=STORE + "1001")]))
    assert any(expected in message for message in errors(result))


def test_listing_id_must_equal_the_product_id_in_the_url(tmp_path: Path) -> None:
    result = validate(tmp_path, csv_bytes([make_row("1001", url=STORE + "1002")]))
    assert errors(result) == [
        "error (row 2, url): the product ID in the URL (1002) differs from listing_id '1001'"
    ]


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        pytest.param(STORE.replace("gulshan-banani", "other-store") + "1001", "not a product page"),
        pytest.param(STORE.replace("https", "http") + "1001", "not a product page", id="http"),
        pytest.param(STORE + "1001/extra", "not a product page", id="extra-path"),
        pytest.param(STORE.replace("/category/", "/view-all/") + "1001", "view-all", id="view-all"),
    ],
)
def test_url_must_be_a_product_page_of_the_allowed_store(
    tmp_path: Path, url: str, expected: str
) -> None:
    result = validate(tmp_path, csv_bytes([make_row("1001", url=url)]))
    assert len(result.errors) == 1
    assert expected in errors(result)[0]


# price_bdt.


@pytest.mark.parametrize(
    "price",
    ["1,000", "Tk 100", RUPEE + "100", "12.345", "-5", "abc", "1e3", " 100"],
)
def test_price_must_be_a_bare_number(tmp_path: Path, price: str) -> None:
    result = validate(tmp_path, csv_bytes([make_row(price_bdt=price)]))
    assert any("must be a bare number" in message for message in errors(result))


@pytest.mark.parametrize("price", ["0", "0.00"])
def test_price_must_be_greater_than_zero(tmp_path: Path, price: str) -> None:
    result = validate(tmp_path, csv_bytes([make_row(price_bdt=price)]))
    assert errors(result) == ["error (row 2, price_bdt): must be greater than zero"]


@pytest.mark.parametrize("price", ["315", "12.5", "12.50"])
def test_valid_prices(tmp_path: Path, price: str) -> None:
    assert validate(tmp_path, csv_bytes([make_row(price_bdt=price)])).errors == []


# collected_at.


@pytest.mark.parametrize(
    "value",
    [
        "2026-11-05 19:30:00+06:00",
        "2026-11-05T19:30:00",
        "2026-11-05T19:30+06:00",
        "05/11/2026",
        "2026-11-05T19:30:00Z",
    ],
)
def test_collected_at_must_have_the_agreed_form(tmp_path: Path, value: str) -> None:
    result = validate(tmp_path, csv_bytes([make_row(collected_at=value)]))
    assert any("must have the form" in message for message in errors(result))


def test_collected_at_must_be_a_real_date(tmp_path: Path) -> None:
    result = validate(tmp_path, csv_bytes([make_row(collected_at="2026-02-30T10:00:00+06:00")]))
    assert any("not a real date" in message for message in errors(result))


def test_collected_at_must_not_be_in_the_future(tmp_path: Path) -> None:
    # NOW is 12:00 UTC on 6 November, which is 18:00 in Bangladesh (UTC+06:00).
    result = validate(tmp_path, csv_bytes([make_row(collected_at="2026-11-06T18:30:00+06:00")]))
    assert any("in the future" in message for message in errors(result))
    earlier = validate(tmp_path, csv_bytes([make_row(collected_at="2026-11-06T17:30:00+06:00")]))
    assert earlier.errors == []


# Duplicates.


def test_a_listing_id_may_appear_only_once_in_a_file(tmp_path: Path) -> None:
    result = validate(tmp_path, csv_bytes([make_row("1001"), make_row("1001")]))
    assert errors(result) == ["error (row 3, listing_id): listing_id '1001' also appears in row 2"]


def test_a_listing_already_in_data_raw_cannot_be_collected_again(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "pandamart_20261101.csv").write_bytes(csv_bytes([make_row("1001")]))
    result = validate(tmp_path, csv_bytes([make_row("1001"), make_row("1002")]))
    assert len(result.errors) == 1
    assert "already in data/raw/pandamart_20261101.csv" in errors(result)[0]


# The script value against the title.


@pytest.mark.parametrize(
    ("title", "script"),
    [
        pytest.param(f"{CHAL} 1 kg", "bangla", id="bangla-with-a-latin-unit"),
        pytest.param(f"{CHAL} 2 x 500 gm", "bangla", id="bangla-with-a-multipack"),
        pytest.param(f"Teer {CHAL} 1 kg", "mixed", id="mixed-with-a-latin-brand"),
        pytest.param("Test Chal 1kg", "romanised", id="romanised-is-not-checked"),
        pytest.param("Test Rice 1kg", "english", id="english"),
    ],
)
def test_script_values_that_fit_the_title(tmp_path: Path, title: str, script: str) -> None:
    result = validate(tmp_path, csv_bytes([make_row(title_raw=title, script=script)]))
    assert result.errors == []


@pytest.mark.parametrize(
    ("title", "script"),
    [
        pytest.param(f"{CHAL} 1kg", "english", id="english-with-bangla-letters"),
        pytest.param(f"{CHAL} 1kg", "romanised", id="romanised-with-bangla-letters"),
        pytest.param(f"Teer {CHAL} 1 kg", "bangla", id="bangla-with-a-latin-word"),
        pytest.param("Test Rice 1kg", "bangla", id="bangla-without-bangla-letters"),
        pytest.param("Test Rice 1kg", "mixed", id="mixed-without-bangla-letters"),
        pytest.param(f"{CHAL} 1 {KEJI}", "mixed", id="mixed-without-latin-words"),
    ],
)
def test_script_values_that_cannot_be_right(tmp_path: Path, title: str, script: str) -> None:
    result = validate(tmp_path, csv_bytes([make_row(title_raw=title, script=script)]))
    assert len(result.errors) == 1
    assert "(row 2, script)" in errors(result)[0]


# Warnings, which do not make a file invalid.


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        pytest.param({"title_raw": "Test Rice 1kg "}, "space at the start or the end", id="end"),
        pytest.param({"title_raw": "Test  Rice 1kg"}, "two spaces", id="double-space"),
        pytest.param({"title_raw": f"Test{ZERO_WIDTH_SPACE} Rice"}, "U+200B", id="invisible"),
        pytest.param({"title_raw": f"Test{RIGHT_QUOTE}s Rice"}, "U+2019", id="typographic"),
        pytest.param({"size_value": "500"}, "both be filled in", id="size-value-only"),
        pytest.param({"size_unit": "gm"}, "both be filled in", id="size-unit-only"),
    ],
)
def test_warnings_do_not_make_a_file_invalid(
    tmp_path: Path, changes: dict[str, str], expected: str
) -> None:
    result = validate(tmp_path, csv_bytes([make_row(**changes)]))
    assert result.errors == []
    assert any(expected in message for message in warnings(result))


# meenabazar: listing_id and url.


@pytest.mark.parametrize(
    ("listing_id", "url"),
    [
        pytest.param("4001", f"{MEENA}{SLUG}/4001", id="hyphenated-capitals-4-digits"),
        pytest.param("40001", f"{MEENA}{SLUG}/40001", id="hyphenated-capitals-5-digits"),
        pytest.param("4001", f"{MEENA}TestBrandSampleLentil500gm/4001", id="mixed-case-4-digits"),
        pytest.param("40001", f"{MEENA}TestBrandSampleLentil500gm/40001", id="mixed-case-5-digits"),
        pytest.param("40001", f"{MEENA}Test-Oil-1.5ltr/40001", id="slug-with-a-dot"),
    ],
)
def test_a_valid_meenabazar_file_has_no_problems(tmp_path: Path, listing_id: str, url: str) -> None:
    result = validate(tmp_path, csv_bytes([make_meena_row(listing_id, url=url)]))
    assert result.problems == []
    assert result.accepted_name == "meenabazar_20261105.csv"


@pytest.mark.parametrize(
    "url",
    [
        pytest.param(f"http://meenabazaronline.com/product/{SLUG}/40001", id="http"),
        pytest.param(f"https://www.meenabazaronline.com/product/{SLUG}/40001", id="www"),
        pytest.param(f"{MEENA}{SLUG}/40001?ref=home", id="query-string"),
        pytest.param(f"{MEENA}{SLUG}/40001?", id="empty-query-string"),
        pytest.param(f"{MEENA}{SLUG}/40001#reviews", id="fragment"),
        pytest.param(f"{MEENA}{SLUG}/40001/", id="trailing-slash"),
        pytest.param(f"{MEENA}{SLUG}/40001/reviews", id="extra-path-after-the-id"),
        pytest.param(f"{MEENA}extra/{SLUG}/40001", id="extra-path-before-the-slug"),
        pytest.param(f"{MEENA}{SLUG}", id="missing-id"),
        pytest.param(f"{MEENA}{SLUG}/", id="missing-id-with-slash"),
        pytest.param(f"{MEENA}40001", id="missing-slug"),
        pytest.param(f"{MEENA}/40001", id="empty-slug"),
        pytest.param(f"{MEENA}TEST BRAND RICE/40001", id="space-in-slug"),
        pytest.param(f"{MEENA}TEST\tBRAND/40001", id="tab-in-slug"),
        pytest.param(f"{MEENA}TEST?BRAND/40001", id="question-mark-in-slug"),
        pytest.param(f"{MEENA}TEST#BRAND/40001", id="hash-in-slug"),
        pytest.param(f"{MEENA}{SLUG}/4000a", id="non-numeric-id"),
        pytest.param(f"{MEENA}{SLUG}/{BANGLA_4001}", id="bangla-digit-id"),
        pytest.param(f"https://meenabazar.com/product/{SLUG}/40001", id="wrong-host"),
        pytest.param(f"https://meenabazaronline.com.bd/product/{SLUG}/40001", id="longer-host"),
        pytest.param(f"https://shop.meenabazaronline.com/product/{SLUG}/40001", id="subdomain"),
        pytest.param(f"https://MeenaBazarOnline.com/product/{SLUG}/40001", id="host-case"),
        pytest.param(f"https://meenabazaronline.com/products/{SLUG}/40001", id="products"),
        pytest.param(STORE + "40001", id="a-pandamart-url"),
    ],
)
def test_meenabazar_url_must_be_an_exact_product_page(tmp_path: Path, url: str) -> None:
    result = validate(tmp_path, csv_bytes([make_meena_row("40001", url=url)]))
    assert errors(result) == [
        "error (row 2, url): is not a product page of the store allowed in docs/sources.md"
    ]


def test_meenabazar_listing_id_must_equal_the_id_in_the_url(tmp_path: Path) -> None:
    result = validate(tmp_path, csv_bytes([make_meena_row("40001", url=f"{MEENA}{SLUG}/40002")]))
    assert errors(result) == [
        "error (row 2, url): the product ID in the URL (40002) differs from listing_id '40001'"
    ]


def test_a_meenabazar_url_is_not_accepted_for_pandamart(tmp_path: Path) -> None:
    result = validate(tmp_path, csv_bytes([make_row("40001", url=f"{MEENA}{SLUG}/40001")]))
    assert any("not a product page" in message for message in errors(result))


@pytest.mark.parametrize(
    "listing_id",
    [
        pytest.param("4000a", id="letter"),
        pytest.param("40 01", id="inner-space"),
        pytest.param("-4001", id="sign"),
        pytest.param("4001.0", id="decimal"),
        pytest.param(BANGLA_4001, id="bangla-digits"),
        pytest.param(SLUG, id="the-slug"),
    ],
)
def test_meenabazar_listing_id_must_be_digits_only(tmp_path: Path, listing_id: str) -> None:
    result = validate(tmp_path, csv_bytes([make_meena_row(listing_id, url=f"{MEENA}{SLUG}/40001")]))
    assert any(
        message.startswith("error (row 2, listing_id)") and "does not have the form" in message
        for message in errors(result)
    )


# meenabazar: prices, under the one generic price rule.


@pytest.mark.parametrize("price", ["420.00", "1000.00", "30.50", "30.5", "30"])
def test_valid_meenabazar_prices(tmp_path: Path, price: str) -> None:
    assert validate(tmp_path, csv_bytes([make_meena_row(price_bdt=price)])).errors == []


@pytest.mark.parametrize(
    "price", ["1,000.00", "420.000", "Tk 420.00", RUPEE + "420.00", "420.", ".50", "420.00 "]
)
def test_invalid_meenabazar_prices(tmp_path: Path, price: str) -> None:
    result = validate(tmp_path, csv_bytes([make_meena_row(price_bdt=price)]))
    assert any("must be a bare number" in message for message in errors(result))


def test_a_meenabazar_price_of_zero_is_an_error(tmp_path: Path) -> None:
    result = validate(tmp_path, csv_bytes([make_meena_row(price_bdt="0.00")]))
    assert errors(result) == ["error (row 2, price_bdt): must be greater than zero"]


# Per-source warnings on brand, size_value and size_unit; they do not make a file invalid.


@pytest.mark.parametrize("brand", ["", " "])
def test_an_empty_meenabazar_brand_is_a_warning(tmp_path: Path, brand: str) -> None:
    result = validate(tmp_path, csv_bytes([make_meena_row(brand=brand)]))
    assert result.errors == []
    assert result.accepted_name == "meenabazar_20261105.csv"
    assert warnings(result) == [
        "warning (row 2, brand): is empty, but meenabazar shows a Brand field; copy it as shown "
        '("No Brand" is a valid value)'
    ]


def test_no_brand_is_a_valid_meenabazar_brand(tmp_path: Path) -> None:
    assert validate(tmp_path, csv_bytes([make_meena_row(brand="No Brand")])).problems == []


def test_a_filled_in_pandamart_brand_is_a_warning(tmp_path: Path) -> None:
    result = validate(tmp_path, csv_bytes([make_row(brand="Test Brand")]))
    assert result.errors == []
    assert result.accepted_name == "pandamart_20261105.csv"
    assert warnings(result) == [
        "warning (row 2, brand): is filled in, but pandamart has no brand field; leave it blank"
    ]


@pytest.mark.parametrize("make", [make_row, make_meena_row], ids=["pandamart", "meenabazar"])
@pytest.mark.parametrize(("column", "value"), [("size_value", "500"), ("size_unit", "gm")])
def test_a_filled_in_size_field_is_a_warning(
    tmp_path: Path, make: Callable[..., dict[str, str]], column: str, value: str
) -> None:
    row = make(**{column: value})
    result = validate(tmp_path, csv_bytes([row]))
    assert result.errors == []
    assert result.accepted_name is not None
    assert (
        f"warning (row 2, {column}): is filled in, but {row['source']} has no separate size "
        "field; leave it blank"
    ) in warnings(result)


def test_both_size_fields_filled_in_give_one_warning_each(tmp_path: Path) -> None:
    result = validate(tmp_path, csv_bytes([make_meena_row(size_value="500", size_unit="gm")]))
    assert [problem.column for problem in result.warnings] == ["size_value", "size_unit"]


# meenabazar: one source per file, and duplicates.


def test_a_file_mixing_pandamart_and_meenabazar_is_an_error(tmp_path: Path) -> None:
    result = validate(tmp_path, csv_bytes([make_row("1001"), make_meena_row("40001")]))
    assert errors(result) == [
        "error: the file holds rows from more than one source: meenabazar, pandamart"
    ]
    assert result.accepted_name is None


def test_a_meenabazar_listing_id_may_appear_only_once_in_a_file(tmp_path: Path) -> None:
    result = validate(tmp_path, csv_bytes([make_meena_row("40001"), make_meena_row("40001")]))
    assert errors(result) == ["error (row 3, listing_id): listing_id '40001' also appears in row 2"]


def test_the_same_listing_id_in_another_source_is_not_a_duplicate(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "pandamart_20261101.csv").write_bytes(csv_bytes([make_row("4001")]))
    assert validate(tmp_path, csv_bytes([make_meena_row("4001")])).errors == []


def test_a_meenabazar_listing_already_in_data_raw_cannot_be_collected_again(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "meenabazar_20261101.csv").write_bytes(csv_bytes([make_meena_row("40001")]))
    result = validate(tmp_path, csv_bytes([make_meena_row("40001")]))
    assert "already in data/raw/meenabazar_20261101.csv" in errors(result)[0]


# The two helpers that the labelled-data code also uses.

BANGLA_FIVE = bn(0x09EB)  # ৫
VOWEL_SIGN_AA = bn(0x09BE)  # ◌া
VIRAMA = bn(0x09CD)  # ◌্


@pytest.mark.parametrize(
    ("value", "moment"),
    [
        ("2026-11-05T19:30:00+06:00", datetime(2026, 11, 5, 13, 30, tzinfo=UTC)),
        ("2026-11-06T17:59:59+06:00", datetime(2026, 11, 6, 11, 59, 59, tzinfo=UTC)),
        ("2026-11-05T10:00:00-05:00", datetime(2026, 11, 5, 15, 0, tzinfo=UTC)),
    ],
)
def test_parse_timestamp_returns_the_moment_with_its_offset(value: str, moment: datetime) -> None:
    parsed = parse_timestamp(value, NOW)
    assert parsed == moment
    assert parsed.utcoffset() is not None


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("2026-11-05 19:30:00+06:00", "must have the form"),
        ("2026-11-05T19:30:00", "must have the form"),
        ("2026-11-05T19:30:00Z", "must have the form"),
        ("", "must have the form"),
        ("2026-02-30T10:00:00+06:00", "not a real date"),
        ("2026-11-05T25:00:00+06:00", "not a real date"),
        ("2026-11-06T18:00:01+06:00", "in the future"),
    ],
)
def test_parse_timestamp_rejects_bad_values(value: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_timestamp(value, NOW)


def test_parse_timestamp_accepts_the_present_moment() -> None:
    # NOW is 12:00 UTC on 6 November, which is 18:00 at +06:00.
    assert parse_timestamp("2026-11-06T18:00:00+06:00", NOW) == NOW


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (CHAL, True),
        (f"Test {CHAL} 1 kg", True),
        (KEJI, True),
        (VOWEL_SIGN_AA, True),
        (VIRAMA, True),
        ("Test Rice 1 kg", False),
        ("", False),
        (BANGLA_FIVE, False),
        (f"Test {BANGLA_FIVE} kg", False),
        (RUPEE, False),
    ],
)
def test_has_bangla_letters(text: str, expected: bool) -> None:
    assert has_bangla_letters(text) is expected


# Files inside data/raw.


def test_a_file_in_data_raw_must_carry_its_expected_name(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    wrong = raw / "pilot.csv"
    wrong.write_bytes(csv_bytes([make_row()]))
    result = validate_file(wrong, raw_dir=raw, now=NOW)
    assert any("must be named pandamart_20261105.csv" in message for message in errors(result))
    right = raw / "pandamart_20261105.csv"
    right.write_bytes(csv_bytes([make_row("2002")]))
    wrong.unlink()
    assert validate_file(right, raw_dir=raw, now=NOW).errors == []


# The command line and --accept.


def write(tmp_path: Path, content: bytes, name: str = "collected.csv") -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


def test_without_accept_nothing_is_copied(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, csv_bytes([make_row()]))
    raw = tmp_path / "raw"
    assert main([str(path), "--raw-dir", str(raw)], now=NOW) == 0
    assert not raw.exists()
    assert "--accept would copy it to" in capsys.readouterr().out


def test_accept_copies_the_file_byte_for_byte(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, csv_bytes([make_row()]))
    raw = tmp_path / "raw"
    assert main(["--accept", str(path), "--raw-dir", str(raw)], now=NOW) == 0
    target = raw / "pandamart_20261105.csv"
    assert target.read_bytes() == path.read_bytes()
    assert "dvc add data/raw" in capsys.readouterr().out


def test_accept_names_a_meenabazar_file_after_its_source_and_last_day(tmp_path: Path) -> None:
    rows = [
        make_meena_row("4001", collected_at="2026-11-06T11:00:00+06:00"),
        make_meena_row("40001", collected_at="2026-11-05T19:30:00+06:00"),
    ]
    path = write(tmp_path, csv_bytes(rows), name="meenabazar_pilot.csv")
    raw = tmp_path / "raw"
    assert main(["--accept", str(path), "--raw-dir", str(raw)], now=NOW) == 0
    assert [target.name for target in raw.iterdir()] == ["meenabazar_20261106.csv"]
    assert (raw / "meenabazar_20261106.csv").read_bytes() == path.read_bytes()


def test_accept_refuses_an_invalid_file(tmp_path: Path) -> None:
    path = write(tmp_path, csv_bytes([make_row(category="")]))
    raw = tmp_path / "raw"
    assert main(["--accept", str(path), "--raw-dir", str(raw)], now=NOW) == 1
    assert not raw.exists()


def test_accept_never_overwrites_a_file(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    existing = raw / "pandamart_20261105.csv"
    existing.write_bytes(csv_bytes([make_row("9999")]))
    before = existing.read_bytes()
    path = write(tmp_path, csv_bytes([make_row("1001")]))
    assert main(["--accept", str(path), "--raw-dir", str(raw)], now=NOW) == 1
    assert existing.read_bytes() == before


def test_accept_refuses_a_file_that_is_already_in_data_raw(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    path = write(raw, csv_bytes([make_row()]), name="pandamart_20261105.csv")
    assert main(["--accept", str(path), "--raw-dir", str(raw)], now=NOW) == 1


def test_a_second_file_with_an_accepted_listing_is_refused(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    first = write(tmp_path, csv_bytes([make_row("1001")]), name="first.csv")
    assert main(["--accept", str(first), "--raw-dir", str(raw)], now=NOW) == 0
    later = make_row("1001", collected_at="2026-11-06T10:00:00+06:00")
    second = write(tmp_path, csv_bytes([later]), name="second.csv")
    assert main(["--accept", str(second), "--raw-dir", str(raw)], now=NOW) == 1
    assert sorted(path.name for path in raw.iterdir()) == ["pandamart_20261105.csv"]


def test_a_missing_file_gives_status_one(tmp_path: Path) -> None:
    assert main([str(tmp_path / "missing.csv"), "--raw-dir", str(tmp_path / "raw")], now=NOW) == 1
