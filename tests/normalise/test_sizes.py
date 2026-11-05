"""Tests for src.normalise.sizes.

All titles are invented. Bangla text is built from code points (see tests/helpers.py), so each
character is visible as a number and no tool can silently change it.
"""

import dataclasses
import re
from decimal import Decimal

import pytest

from src.normalise.digits import bangla_digits_to_ascii
from src.normalise.sizes import REASONS, VULGAR_FRACTIONS, SizeResult, parse_size
from src.normalise.unicode_clean import clean_unicode
from src.normalise.units import UNITS
from tests.helpers import bn

# Bangla words used in titles.
KEJI = bn(0x0995, 0x09C7, 0x099C, 0x09BF)  # কেজি kg
KE_JI_DOTTED = bn(0x0995, 0x09C7, 0x2E, 0x099C, 0x09BF, 0x2E)  # কে.জি. kg, dotted
KILO = bn(0x0995, 0x09BF, 0x09B2, 0x09CB)  # কিলো kilo
KILOGRAM = bn(0x0995, 0x09BF, 0x09B2, 0x09CB, 0x0997, 0x09CD, 0x09B0, 0x09BE, 0x09AE)  # কিলোগ্রাম
GRAM = bn(0x0997, 0x09CD, 0x09B0, 0x09BE, 0x09AE)  # গ্রাম gram
GRA_DOTTED = bn(0x0997, 0x09CD, 0x09B0, 0x09BE, 0x2E)  # গ্রা. gram, dotted
LITAR = bn(0x09B2, 0x09BF, 0x099F, 0x09BE, 0x09B0)  # লিটার litre
LI_DOTTED = bn(0x09B2, 0x09BF, 0x2E)  # লি. litre, dotted
MILI = bn(0x09AE, 0x09BF, 0x09B2, 0x09BF)  # মিলি ml
MILILITAR = bn(
    0x09AE, 0x09BF, 0x09B2, 0x09BF, 0x09B2, 0x09BF, 0x099F, 0x09BE, 0x09B0
)  # মিলিলিটার millilitre
MI_LI_DOTTED = bn(0x09AE, 0x09BF, 0x2E, 0x09B2, 0x09BF, 0x2E)  # মি.লি. ml, dotted
EMEL = bn(0x098F, 0x09AE, 0x098F, 0x09B2)  # এমএল ml, spelt out in letters
CHAL = bn(0x099A, 0x09BE, 0x09B2)  # চাল rice
TEL = bn(0x09A4, 0x09C7, 0x09B2)  # তেল oil
MOSLA = bn(0x09AE, 0x09B8, 0x09B2, 0x09BE)  # মসলা spice
KEJI_SUFFIXED = KEJI + bn(0x09A4, 0x09C7)  # তে "kejite": the unit word with a longer ending

BANGLA_ONE = bn(0x09E7)  # ১
RUPEE = bn(0x09F3)  # ৳
HALF = bn(0x00BD)
QUARTER = bn(0x00BC)
TIMES = bn(0x00D7)
KELVIN = bn(0x212A)

MISSING = SizeResult("missing", "no_size_found")


def title_ok(amount: str, kind: str, text: str, count: int = 1, extra: bool = False) -> SizeResult:
    return SizeResult("ok", "", Decimal(amount), kind, count, "title", extra, text)


def field_ok(amount: str, kind: str, text: str, extra: bool = False) -> SizeResult:
    return SizeResult("ok", "", Decimal(amount), kind, 1, "field", extra, text)


def ambiguous(reason: str, text: str) -> SizeResult:
    return SizeResult("ambiguous", reason, matched_text=text)


def conflict(text: str) -> SizeResult:
    return SizeResult("conflict", "field_title_conflict", matched_text=text)


TITLE_CASES = [
    # Latin units, any case, plurals and abbreviations.
    pytest.param("Chinigura Rice 1 kg", title_ok("1000", "weight", "1 kg"), id="kg"),
    pytest.param("Rice 1KG", title_ok("1000", "weight", "1KG"), id="KG"),
    pytest.param("Rice 1Kg", title_ok("1000", "weight", "1Kg"), id="Kg"),
    pytest.param("Rice 1kG", title_ok("1000", "weight", "1kG"), id="kG"),
    pytest.param("Rice 2 kgs", title_ok("2000", "weight", "2 kgs"), id="kgs"),
    pytest.param("Dal 500 gm", title_ok("500", "weight", "500 gm"), id="gm"),
    pytest.param("Dal 500gm", title_ok("500", "weight", "500gm"), id="gm-attached"),
    pytest.param("Dal 500 GM", title_ok("500", "weight", "500 GM"), id="GM"),
    pytest.param("Dal 250 gms", title_ok("250", "weight", "250 gms"), id="gms"),
    pytest.param("Dal 100 gram", title_ok("100", "weight", "100 gram"), id="gram"),
    pytest.param("Dal 100 Grams", title_ok("100", "weight", "100 Grams"), id="Grams"),
    pytest.param("Dal 5 g", title_ok("5", "weight", "5 g"), id="g"),
    pytest.param("Oil 0.5 L", title_ok("500", "volume", "0.5 L"), id="half-litre"),
    pytest.param("Oil 500ml", title_ok("500", "volume", "500ml"), id="ml-attached"),
    pytest.param("Oil 500 ML", title_ok("500", "volume", "500 ML"), id="ML"),
    pytest.param("Oil 250 mls", title_ok("250", "volume", "250 mls"), id="mls"),
    pytest.param("Oil 1.5 Ltr", title_ok("1500", "volume", "1.5 Ltr"), id="Ltr"),
    pytest.param("Oil 1 ltr.", title_ok("1000", "volume", "1 ltr."), id="ltr-dot"),
    pytest.param("Oil 2 ltrs", title_ok("2000", "volume", "2 ltrs"), id="ltrs"),
    pytest.param("Oil 5 litres", title_ok("5000", "volume", "5 litres"), id="litres"),
    pytest.param("Oil 5 Liters", title_ok("5000", "volume", "5 Liters"), id="Liters"),
    pytest.param("Oil 1 litre", title_ok("1000", "volume", "1 litre"), id="litre"),
    pytest.param("Oil 1 liter", title_ok("1000", "volume", "1 liter"), id="liter"),
    pytest.param("Dal 1,000 gm", title_ok("1000", "weight", "1,000 gm"), id="thousands-comma"),
    pytest.param("Oil 2.01 L", title_ok("2010", "volume", "2.01 L"), id="exact-decimal"),
    # Bangla units.
    pytest.param(f"{CHAL} 1 {KEJI}", title_ok("1000", "weight", f"1 {KEJI}"), id="bn-keji"),
    pytest.param(f"{CHAL} 1{KEJI}", title_ok("1000", "weight", f"1{KEJI}"), id="bn-keji-attached"),
    pytest.param(
        f"{CHAL} 1 {KE_JI_DOTTED}",
        title_ok("1000", "weight", f"1 {KE_JI_DOTTED}"),
        id="bn-keji-dots",
    ),
    pytest.param(f"{CHAL} 1 {KILO}", title_ok("1000", "weight", f"1 {KILO}"), id="bn-kilo"),
    pytest.param(
        f"{CHAL} 1 {KILOGRAM}", title_ok("1000", "weight", f"1 {KILOGRAM}"), id="bn-kilogram"
    ),
    pytest.param(f"{MOSLA} 250 {GRAM}", title_ok("250", "weight", f"250 {GRAM}"), id="bn-gram"),
    pytest.param(
        f"{MOSLA} 250 {GRA_DOTTED}", title_ok("250", "weight", f"250 {GRA_DOTTED}"), id="bn-gra-dot"
    ),
    pytest.param(f"{TEL} 1 {LITAR}", title_ok("1000", "volume", f"1 {LITAR}"), id="bn-litar"),
    pytest.param(
        f"{TEL} 1 {LI_DOTTED}", title_ok("1000", "volume", f"1 {LI_DOTTED}"), id="bn-li-dot"
    ),
    pytest.param(f"{TEL} 500 {MILI}", title_ok("500", "volume", f"500 {MILI}"), id="bn-mili"),
    pytest.param(
        f"{TEL} 500 {MILILITAR}", title_ok("500", "volume", f"500 {MILILITAR}"), id="bn-mililitar"
    ),
    pytest.param(
        f"{TEL} 500 {MI_LI_DOTTED}",
        title_ok("500", "volume", f"500 {MI_LI_DOTTED}"),
        id="bn-mili-dots",
    ),
    pytest.param(f"{TEL} 500 {EMEL}", title_ok("500", "volume", f"500 {EMEL}"), id="bn-emel"),
    # Word boundaries and what may come before a number.
    pytest.param("Rice 1 kgx", MISSING, id="nonsense-suffix"),
    pytest.param(f"{CHAL} 1 {KEJI_SUFFIXED}", MISSING, id="bn-longer-word"),
    pytest.param("Rice 5 lb", MISSING, id="unknown-unit"),
    pytest.param(f"Rice 1 {KELVIN}g", MISSING, id="kelvin-sign-is-not-k"),
    pytest.param(f"Rice {RUPEE}1 kg", MISSING, id="price-after-rupee-sign"),
    # A number straight after "digit and slash, dot or comma" is never the start of a size.
    pytest.param("Item 1/2.5 kg", MISSING, id="slash-before-number"),
    pytest.param("Item 1.2.5 kg", MISSING, id="dots-before-number"),
    pytest.param("Item 1,2,5 kg", MISSING, id="commas-before-number"),
    pytest.param("Rice B12 500 gm", title_ok("500", "weight", "500 gm"), id="number-in-a-word"),
    pytest.param("Rice (1 kg)", title_ok("1000", "weight", "1 kg"), id="brackets"),
    pytest.param("Rice, 5 kg", title_ok("5000", "weight", "5 kg"), id="after-comma-and-space"),
    # Numbers that cannot be read safely.
    pytest.param("Rice 1,5 kg", ambiguous("comma_decimal", "1,5 kg"), id="comma-decimal"),
    pytest.param("Rice 10,50 gm", ambiguous("comma_decimal", "10,50 gm"), id="comma-decimal-2"),
    pytest.param(f"Item {HALF} kg", ambiguous("fraction", f"{HALF} kg"), id="half-sign"),
    pytest.param("Item 1/2 kg", ambiguous("fraction", "1/2 kg"), id="slash-fraction"),
    pytest.param("Item 1 1/2 kg", ambiguous("fraction", "1 1/2 kg"), id="mixed-fraction"),
    pytest.param(f"Item 1{HALF} kg", ambiguous("fraction", f"1{HALF} kg"), id="mixed-half-sign"),
    pytest.param(f"Item {QUARTER} L", ambiguous("fraction", f"{QUARTER} L"), id="quarter-sign"),
    pytest.param("Item 3/4 L", ambiguous("fraction", "3/4 L"), id="three-quarters"),
    pytest.param("Dal 0 kg", ambiguous("zero_amount", "0 kg"), id="zero-amount"),
    pytest.param("Item 0 x 500 gm", ambiguous("zero_amount", "0 x 500 gm"), id="zero-packs"),
    # Multipacks.
    pytest.param(
        "Item 2 x 500 gm", title_ok("500", "weight", "2 x 500 gm", count=2), id="multipack"
    ),
    pytest.param(
        "Item 2X500gm", title_ok("500", "weight", "2X500gm", count=2), id="multipack-attached"
    ),
    pytest.param(
        f"Item 2{TIMES}500 gm",
        title_ok("500", "weight", f"2{TIMES}500 gm", count=2),
        id="multipack-times-sign",
    ),
    pytest.param(
        "Item 2 * 500 ml", title_ok("500", "volume", "2 * 500 ml", count=2), id="multipack-star"
    ),
    pytest.param(
        "Item 500 gm x 2", title_ok("500", "weight", "500 gm x 2", count=2), id="count-last"
    ),
    pytest.param(
        f"Item 500gm {TIMES} 3",
        title_ok("500", "weight", f"500gm {TIMES} 3", count=3),
        id="count-last-times-sign",
    ),
    pytest.param(
        "Item 1 x 500 gm", title_ok("500", "weight", "1 x 500 gm", count=1), id="one-pack"
    ),
    pytest.param(
        "Item 3 x 1.5 L", title_ok("1500", "volume", "3 x 1.5 L", count=3), id="multipack-decimal"
    ),
    pytest.param(
        "Item 2 x 500 gm x 3",
        ambiguous("multiple_multipacks", "2 x 500 gm | 500 gm x 3"),
        id="two-multiplications",
    ),
    pytest.param(
        "Item 2 x 500 ml (1 L)",
        ambiguous("multiple_sizes", "2 x 500 ml | 1 L"),
        id="multipack-and-single",
    ),
    # Free extra quantities.
    pytest.param(
        "Item 500 gm + 50 gm Free",
        title_ok("500", "weight", "500 gm", extra=True),
        id="free-extra",
    ),
    pytest.param(
        "Item 500gm +50gm free",
        title_ok("500", "weight", "500gm", extra=True),
        id="free-extra-attached",
    ),
    pytest.param(
        "Item 500 gm (+50 gm free)",
        title_ok("500", "weight", "500 gm", extra=True),
        id="free-extra-brackets",
    ),
    pytest.param(
        "Item 2 x 500 gm + 50 gm",
        title_ok("500", "weight", "2 x 500 gm", count=2, extra=True),
        id="multipack-with-extra",
    ),
    pytest.param("Item + 50 gm free", MISSING, id="extra-only"),
    # Several sizes in one title.
    pytest.param("Oil 1 L 5 L", ambiguous("multiple_sizes", "1 L | 5 L"), id="two-sizes"),
    pytest.param("Oil 1 L (1000 ml)", title_ok("1000", "volume", "1 L"), id="same-size-twice"),
    # No size at all, and the digit policy.
    pytest.param("Rice", MISSING, id="no-size"),
    pytest.param("", MISSING, id="empty-title"),
    pytest.param(f"{BANGLA_ONE} {KEJI}", MISSING, id="bangla-digit-is-not-parsed-here"),
]

FIELD_CASES = [
    pytest.param("Rice", "1", "kg", field_ok("1000", "weight", "1 kg"), id="field-only"),
    pytest.param("", "500", MILI, field_ok("500", "volume", f"500 {MILI}"), id="bangla-unit"),
    pytest.param("", "1.5", "L", field_ok("1500", "volume", "1.5 L"), id="decimal"),
    pytest.param("", "1,000", "gm", field_ok("1000", "weight", "1,000 gm"), id="thousands"),
    pytest.param("", "2", "KG", field_ok("2000", "weight", "2 KG"), id="upper-case-unit"),
    pytest.param("Rice", "1", "", ambiguous("unreadable_field", "1"), id="value-without-unit"),
    pytest.param("Rice", "", "kg", ambiguous("unreadable_field", "kg"), id="unit-without-value"),
    pytest.param("Rice", "1", "pcs", ambiguous("unreadable_field", "1 pcs"), id="unknown-unit"),
    pytest.param("", "abc", "kg", ambiguous("unreadable_field", "abc kg"), id="not-a-number"),
    pytest.param("", "1/2", "kg", ambiguous("fraction", "1/2 kg"), id="slash-fraction"),
    pytest.param("", HALF, "kg", ambiguous("fraction", f"{HALF} kg"), id="half-sign"),
    pytest.param("", "1,5", "kg", ambiguous("comma_decimal", "1,5 kg"), id="comma-decimal"),
    pytest.param("", "0", "kg", ambiguous("zero_amount", "0 kg"), id="zero"),
    pytest.param(
        "Rice 1 kg", "  ", " ", title_ok("1000", "weight", "1 kg"), id="blank-fields-are-absent"
    ),
    pytest.param("Rice", "", "", MISSING, id="nothing-anywhere"),
    pytest.param("Rice 1 kg", "1", "kg", field_ok("1000", "weight", "1 kg"), id="agree"),
    pytest.param(
        "Rice 1 kg", "1000", "gm", field_ok("1000", "weight", "1000 gm"), id="agree-other-unit"
    ),
    pytest.param("Rice 1 kg", "2", "kg", conflict("1 kg | 2 kg"), id="conflict"),
    pytest.param("Oil 1 L", "1", "kg", conflict("1 L | 1 kg"), id="conflict-kind"),
    pytest.param(
        "Item 500 gm + 50 gm Free",
        "550",
        "gm",
        title_ok("500", "weight", "500 gm", extra=True),
        id="field-is-base-plus-extra",
    ),
    pytest.param(
        "Item 500 gm + 50 gm Free",
        "500",
        "gm",
        field_ok("500", "weight", "500 gm", extra=True),
        id="field-is-base",
    ),
    pytest.param(
        "Item 2 x 500 gm",
        "500",
        "gm",
        title_ok("500", "weight", "2 x 500 gm", count=2),
        id="field-is-per-pack",
    ),
    pytest.param(
        "Item 2 x 500 gm",
        "1000",
        "gm",
        title_ok("500", "weight", "2 x 500 gm", count=2),
        id="field-is-total",
    ),
    pytest.param(
        "Item 2 x 500 gm", "700", "gm", conflict("2 x 500 gm | 700 gm"), id="multipack-conflict"
    ),
    pytest.param("Item 1/2 kg", "500", "gm", ambiguous("fraction", "1/2 kg"), id="title-ambiguous"),
    pytest.param(
        "Rice 1 kg", "1", "pcs", ambiguous("unreadable_field", "1 pcs"), id="field-unreadable"
    ),
]


@pytest.mark.parametrize(("title", "expected"), TITLE_CASES)
def test_size_from_the_title_only(title: str, expected: SizeResult) -> None:
    assert parse_size(title) == expected


@pytest.mark.parametrize(("title", "size_value", "size_unit", "expected"), FIELD_CASES)
def test_size_from_the_field_and_the_title(
    title: str, size_value: str, size_unit: str, expected: SizeResult
) -> None:
    assert parse_size(title, size_value, size_unit) == expected


def test_reason_is_set_exactly_when_the_status_is_not_ok() -> None:
    expected_results = [param.values[-1] for param in [*TITLE_CASES, *FIELD_CASES]]
    for result in expected_results:
        assert (result.status == "ok") == (result.reason == "")
        if result.status != "ok":
            assert result.reason in REASONS


def test_every_reason_is_used_by_at_least_one_case() -> None:
    used = {param.values[-1].reason for param in [*TITLE_CASES, *FIELD_CASES]}
    assert set(REASONS) <= used


def test_fractions_are_never_read_as_the_digit_after_the_slash() -> None:
    # Regression test: "1/2 kg" was once read as 2 kg.
    for title in ("Item 1/2 kg", "Item 1 1/2 kg", f"Item 1{HALF} kg"):
        result = parse_size(title)
        assert result.status == "ambiguous"
        assert result.amount is None


@pytest.mark.parametrize(
    ("letter", "name"),
    [
        pytest.param(bn(0x00E9), "e-acute", id="e-acute"),
        pytest.param(bn(0x00F1), "n-tilde", id="n-tilde"),
        pytest.param(bn(0x00DF), "sharp-s", id="sharp-s"),
    ],
)
def test_unit_followed_by_a_non_ascii_latin_letter_is_still_read(letter: str, name: str) -> None:
    # Known limitation, pinned so that any change in this behaviour is noticed.
    # WORD_CHARS holds only the ASCII Latin letters, so an accented letter counts as a separator,
    # not as part of a word. A unit followed straight by one therefore still ends at the unit:
    # "1 kg" plus e-acute is read as 1 kg, whereas "1 kgx" (an ASCII letter) is not read at all.
    # Titles are Bangla and English, so this should be rare. Revisit it if pilot data shows
    # accented Latin words straight after a unit.
    assert parse_size("Rice 1 kg" + letter) == title_ok("1000", "weight", "1 kg"), name
    assert parse_size("Rice 1 kgx") == MISSING


@pytest.mark.parametrize("key", sorted(UNITS))
def test_every_unit_in_the_table_is_parsed(key: str) -> None:
    unit = UNITS[key]
    for text in {key, key.upper()}:
        result = parse_size(f"Item 1 {text}")
        assert result.status == "ok", text
        assert result.amount == Decimal(unit.factor), text
        assert result.kind == unit.kind, text


@pytest.mark.parametrize("char", [HALF, QUARTER, bn(0x00BE), bn(0x2153), bn(0x215B), bn(0x215E)])
def test_vulgar_fraction_signs_are_recognised(char: str) -> None:
    assert re.fullmatch(f"[{VULGAR_FRACTIONS}]", char)


@pytest.mark.parametrize("char", ["x", "1", "/", " ", bn(0x00D7)])
def test_other_characters_are_not_vulgar_fractions(char: str) -> None:
    assert re.fullmatch(f"[{VULGAR_FRACTIONS}]", char) is None


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Oil 0.5 L", "500"),
        ("Rice 1 kg", "1000"),
        ("Oil 1.5 Ltr", "1500"),
        ("Dal 5 g", "5"),
        ("Dal 0.25 kg", "250"),
        ("Rice", ""),
    ],
)
def test_amount_text_has_no_exponent_and_no_trailing_zeros(title: str, expected: str) -> None:
    assert parse_size(title).amount_text == expected


@pytest.mark.parametrize(("title", "expected"), [("Oil 2.01 L", "2010"), ("Oil 4.02 L", "4020")])
def test_conversion_is_exact_where_float_arithmetic_is_not(title: str, expected: str) -> None:
    # float("2.01") * 1000 gives 2009.9999999999998, so Decimal arithmetic is used instead.
    assert parse_size(title).amount == Decimal(expected)


def test_total_multiplies_the_amount_by_the_pack_count() -> None:
    assert parse_size("Item 2 x 500 gm").total == Decimal("1000")
    assert parse_size("Item 1 kg").total == Decimal("1000")
    assert parse_size("Item").total is None


@pytest.mark.parametrize(
    "text",
    [
        BANGLA_ONE + " " + KEJI,
        "1 " + KEJI,
        BANGLA_ONE + chr(0x200C) + " " + KEJI,
        "1 kg",
    ],
)
def test_after_the_earlier_steps_all_spellings_of_one_kilogram_agree(text: str) -> None:
    result = parse_size(bangla_digits_to_ascii(clean_unicode(text)))
    assert result.status == "ok"
    assert result.amount == Decimal(1000)
    assert result.kind == "weight"


def test_result_is_immutable() -> None:
    result = parse_size("Rice 1 kg")
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.amount = Decimal(1)  # type: ignore[misc]


def test_reasons_are_unique() -> None:
    assert len(set(REASONS)) == len(REASONS) == 8


@pytest.mark.parametrize(
    "arguments",
    [
        (None,),
        (123,),
        (float("nan"),),
        ("Rice 1 kg", None),
        ("Rice 1 kg", 1),
        ("Rice 1 kg", "1", None),
        ("Rice 1 kg", "1", float("nan")),
        (b"Rice 1 kg",),
    ],
)
def test_non_str_arguments_raise_type_error(arguments: tuple[object, ...]) -> None:
    with pytest.raises(TypeError, match="expected str"):
        parse_size(*arguments)  # type: ignore[arg-type]
