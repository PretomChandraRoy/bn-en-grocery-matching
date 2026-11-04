"""Tests for src.normalise.units.

Bangla units are built from code points (see tests/helpers.py), so each character is visible as
a number and no tool can silently change it.
"""

import re

import pytest

from src.normalise.unicode_clean import clean_unicode
from src.normalise.units import UNITS, Unit, lookup_unit, unit_alternation
from tests.helpers import bn

KILOGRAM = Unit("weight", 1000)
GRAM = Unit("weight", 1)
LITRE = Unit("volume", 1000)
MILLILITRE = Unit("volume", 1)

LATIN_UNITS = {
    **dict.fromkeys(["kg", "kgs"], KILOGRAM),
    **dict.fromkeys(["g", "gm", "gms", "gram", "grams"], GRAM),
    **dict.fromkeys(["l", "ltr", "ltr.", "ltrs", "litre", "litres", "liter", "liters"], LITRE),
    **dict.fromkeys(["ml", "mls"], MILLILITRE),
}

# (code points, unit): the Bangla spellings of the units, with the word in the comment.
BANGLA_UNITS = [
    pytest.param((0x0995, 0x09C7, 0x099C, 0x09BF), KILOGRAM, id="keji"),
    pytest.param((0x0995, 0x09C7, 0x2E, 0x099C, 0x09BF, 0x2E), KILOGRAM, id="ke.ji."),
    pytest.param((0x0995, 0x09BF, 0x09B2, 0x09CB), KILOGRAM, id="kilo"),
    pytest.param(
        (0x0995, 0x09BF, 0x09B2, 0x09CB, 0x0997, 0x09CD, 0x09B0, 0x09BE, 0x09AE),
        KILOGRAM,
        id="kilogram",
    ),
    pytest.param((0x0997, 0x09CD, 0x09B0, 0x09BE, 0x09AE), GRAM, id="gram"),
    pytest.param((0x0997, 0x09CD, 0x09B0, 0x09BE, 0x2E), GRAM, id="gra."),
    pytest.param((0x09B2, 0x09BF, 0x099F, 0x09BE, 0x09B0), LITRE, id="litar"),
    pytest.param((0x09B2, 0x09BF, 0x2E), LITRE, id="li."),
    pytest.param((0x09AE, 0x09BF, 0x09B2, 0x09BF), MILLILITRE, id="mili"),
    pytest.param(
        (0x09AE, 0x09BF, 0x09B2, 0x09BF, 0x09B2, 0x09BF, 0x099F, 0x09BE, 0x09B0),
        MILLILITRE,
        id="mililitar",
    ),
    pytest.param((0x09AE, 0x09BF, 0x2E, 0x09B2, 0x09BF, 0x2E), MILLILITRE, id="mi.li."),
    pytest.param((0x098F, 0x09AE, 0x098F, 0x09B2), MILLILITRE, id="emel"),
]


def _bangla_keys() -> set[str]:
    return {key for key in UNITS if not key.isascii()}


@pytest.mark.parametrize(("key", "unit"), LATIN_UNITS.items())
def test_latin_units_are_in_the_table(key: str, unit: Unit) -> None:
    assert UNITS[key] == unit


@pytest.mark.parametrize(("code_points", "unit"), BANGLA_UNITS)
def test_bangla_units_are_in_the_table(code_points: tuple[int, ...], unit: Unit) -> None:
    assert UNITS[bn(*code_points)] == unit


def test_table_holds_exactly_the_agreed_units() -> None:
    bangla = {bn(*param.values[0]) for param in BANGLA_UNITS}
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
    assert lookup_unit(bn(0x0995, 0x09C7, 0x099C, 0x09BF)) == KILOGRAM


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
