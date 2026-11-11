"""Tests for src.normalise.units.

Bangla units are built from code points (see tests/helpers.py), so each character is visible as
a number and no tool can silently change it.
"""

import re

import pytest

from src.normalise.unicode_clean import clean_unicode
from src.normalise.units import UNITS, Unit, lookup_unit, symbols_by_dot_free_unit, unit_alternation
from tests.helpers import bn

KILOGRAM = Unit("weight", 1000, "kg")
GRAM = Unit("weight", 1, "g")
LITRE = Unit("volume", 1000, "l")
MILLILITRE = Unit("volume", 1, "ml")

LATIN_UNITS = {
    **dict.fromkeys(["kg", "kgs"], KILOGRAM),
    **dict.fromkeys(["g", "gm", "gms", "gram", "grams"], GRAM),
    **dict.fromkeys(["l", "ltr", "ltr.", "ltrs", "litre", "litres", "liter", "liters"], LITRE),
    **dict.fromkeys(["ml", "mls"], MILLILITRE),
}

# (the unit as written in a title, its Unit): the Bangla spellings in the unit table.
BANGLA_UNITS = [
    pytest.param(bn(0x0995, 0x09C7, 0x099C, 0x09BF), KILOGRAM, id="keji"),  # কেজি
    pytest.param(bn(0x0995, 0x09C7, 0x2E, 0x099C, 0x09BF, 0x2E), KILOGRAM, id="ke.ji."),  # কে.জি.
    pytest.param(bn(0x0995, 0x09BF, 0x09B2, 0x09CB), KILOGRAM, id="kilo"),  # কিলো
    pytest.param(
        bn(0x0995, 0x09BF, 0x09B2, 0x09CB, 0x0997, 0x09CD, 0x09B0, 0x09BE, 0x09AE),  # কিলোগ্রাম
        KILOGRAM,
        id="kilogram",
    ),
    pytest.param(bn(0x0997, 0x09CD, 0x09B0, 0x09BE, 0x09AE), GRAM, id="gram"),  # গ্রাম
    pytest.param(bn(0x0997, 0x09CD, 0x09B0, 0x09BE, 0x2E), GRAM, id="gra."),  # গ্রা.
    pytest.param(bn(0x09B2, 0x09BF, 0x099F, 0x09BE, 0x09B0), LITRE, id="litar"),  # লিটার
    pytest.param(bn(0x09B2, 0x09BF, 0x2E), LITRE, id="li."),  # লি.
    pytest.param(bn(0x09AE, 0x09BF, 0x09B2, 0x09BF), MILLILITRE, id="mili"),  # মিলি
    pytest.param(
        bn(0x09AE, 0x09BF, 0x09B2, 0x09BF, 0x09B2, 0x09BF, 0x099F, 0x09BE, 0x09B0),  # মিলিলিটার
        MILLILITRE,
        id="mililitar",
    ),
    pytest.param(bn(0x09AE, 0x09BF, 0x2E, 0x09B2, 0x09BF, 0x2E), MILLILITRE, id="mi.li."),  # মি.লি.
    pytest.param(bn(0x098F, 0x09AE, 0x098F, 0x09B2), MILLILITRE, id="emel"),  # এমএল
]


def _bangla_keys() -> set[str]:
    return {key for key in UNITS if not key.isascii()}


@pytest.mark.parametrize(("key", "unit"), LATIN_UNITS.items())
def test_latin_units_are_in_the_table(key: str, unit: Unit) -> None:
    assert UNITS[key] == unit


@pytest.mark.parametrize(("text", "unit"), BANGLA_UNITS)
def test_bangla_units_are_in_the_table(text: str, unit: Unit) -> None:
    assert UNITS[text] == unit


def test_table_holds_exactly_the_agreed_units() -> None:
    bangla = {param.values[0] for param in BANGLA_UNITS}
    assert set(UNITS) == set(LATIN_UNITS) | bangla
    assert _bangla_keys() == bangla


def test_latin_keys_are_lower_case() -> None:
    for key in UNITS:
        if key.isascii():
            assert key == key.lower()


def test_every_key_is_already_clean_unicode() -> None:
    for key in UNITS:
        assert clean_unicode(key) == key


def test_no_key_contains_a_digit_or_a_space() -> None:
    for key in UNITS:
        assert not any(char.isdigit() or char.isspace() for char in key)


def test_units_convert_to_grams_or_millilitres_by_a_whole_factor() -> None:
    for unit in UNITS.values():
        assert unit.kind in ("weight", "volume")
        assert unit.factor in (1, 1000)


@pytest.mark.parametrize("text", ["KG", "Kg", "kG", " kg ", "LTR.", "Gm"])
def test_lookup_ignores_case_and_surrounding_spaces(text: str) -> None:
    assert lookup_unit(text) == UNITS[text.strip().lower()]


@pytest.mark.parametrize("text", ["", "pcs", "kgx", "k", "lb"])
def test_lookup_returns_none_for_unknown_words(text: str) -> None:
    assert lookup_unit(text) is None


def test_lookup_finds_a_bangla_unit() -> None:
    assert lookup_unit(bn(0x0995, 0x09C7, 0x099C, 0x09BF)) == KILOGRAM  # কেজি


def test_alternation_matches_every_unit_in_any_case() -> None:
    pattern = re.compile(f"(?:{unit_alternation()})")
    for key in UNITS:
        assert pattern.fullmatch(key), key
        assert pattern.fullmatch(key.upper()), key


@pytest.mark.parametrize("text", ["kG", "lTr.", "gMs", "Litres"])
def test_alternation_accepts_mixed_case(text: str) -> None:
    assert re.fullmatch(f"(?:{unit_alternation()})", text)


@pytest.mark.parametrize("text", ["pcs", "kgx", "k", "lb", "", "kg.", "mm"])
def test_alternation_rejects_other_words(text: str) -> None:
    assert re.fullmatch(f"(?:{unit_alternation()})", text) is None


@pytest.mark.parametrize("text", ["kgs", "ltrs", "ltr.", "litres", "gms"])
def test_alternation_prefers_the_longer_unit(text: str) -> None:
    found = re.match(f"(?:{unit_alternation()})", text)
    assert found is not None
    assert found.group(0) == text


def test_dots_in_units_are_matched_literally() -> None:
    pattern = re.compile(f"(?:{unit_alternation()})")
    assert pattern.fullmatch("ltr.")
    assert pattern.fullmatch("ltrX") is None


# Symbols: the one spelling that title normalisation writes for a unit.


def test_each_unit_group_has_exactly_one_symbol() -> None:
    symbols_of_group: dict[tuple[str, int], set[str]] = {}
    for unit in UNITS.values():
        symbols_of_group.setdefault((unit.kind, unit.factor), set()).add(unit.symbol)
    assert symbols_of_group == {
        ("weight", 1000): {"kg"},
        ("weight", 1): {"g"},
        ("volume", 1000): {"l"},
        ("volume", 1): {"ml"},
    }


def test_the_four_groups_have_four_different_symbols() -> None:
    assert sorted({unit.symbol for unit in UNITS.values()}) == ["g", "kg", "l", "ml"]


def test_every_symbol_is_a_latin_key_of_the_table_for_its_own_unit() -> None:
    for unit in UNITS.values():
        assert unit.symbol.isascii()
        assert UNITS[unit.symbol] == unit


def test_symbols_by_dot_free_unit_covers_every_key_with_its_symbol() -> None:
    symbols = symbols_by_dot_free_unit()
    assert set(symbols) == {key.replace(".", "") for key in UNITS}
    for key, unit in UNITS.items():
        assert symbols[key.replace(".", "")] == unit.symbol
    assert symbols["ltr"] == "l"
    assert symbols["gm"] == "g"


def test_spellings_that_differ_only_by_a_dot_may_share_a_symbol() -> None:
    table = {"ltr": LITRE, "ltr.": LITRE}
    assert symbols_by_dot_free_unit(table) == {"ltr": "l"}


def test_spellings_that_differ_only_by_a_dot_must_not_have_different_symbols() -> None:
    table = {"ltr": LITRE, "ltr.": Unit("volume", 1000, "ltr")}
    with pytest.raises(ValueError, match="different symbols"):
        symbols_by_dot_free_unit(table)
