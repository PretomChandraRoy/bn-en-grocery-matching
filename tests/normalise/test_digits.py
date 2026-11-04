"""Tests for src.normalise.digits.

All Bangla strings are written as \\u escapes and are invented for testing.
"""

import unicodedata

import pytest

from src.normalise.digits import ASCII_DIGITS, BANGLA_DIGITS, bangla_digits_to_ascii
from src.normalise.unicode_clean import clean_unicode

KEJI = "কেজি"  # the unit word "keji" (kg): KA + E sign + JA + I sign
MILI = "মিলি"  # the unit word "mili" (ml): MA + I sign + LA + I sign


def test_digit_tables_are_consistent_with_unicode() -> None:
    assert len(BANGLA_DIGITS) == len(ASCII_DIGITS) == 10
    for value, (bangla, ascii_digit) in enumerate(zip(BANGLA_DIGITS, ASCII_DIGITS, strict=True)):
        assert ord(bangla) == 0x09E6 + value
        assert unicodedata.digit(bangla) == value
        assert ascii_digit == str(value)


@pytest.mark.parametrize("value", range(10))
def test_each_bangla_digit_becomes_the_matching_ascii_digit(value: int) -> None:
    assert bangla_digits_to_ascii(BANGLA_DIGITS[value]) == str(value)


def test_ascii_digits_are_unchanged() -> None:
    assert bangla_digits_to_ascii("0123456789") == "0123456789"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("১0", "10", id="bangla-then-ascii"),
        pytest.param("1০", "10", id="ascii-then-bangla"),
        pytest.param("১০6", "106", id="three-digits-mixed"),
    ],
)
def test_digits_mixed_within_one_number(text: str, expected: str) -> None:
    assert bangla_digits_to_ascii(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("১.৫", "1.5", id="decimal"),
        pytest.param("০.৫ L", "0.5 L", id="decimal-with-unit"),
        pytest.param("১,০০০", "1,000", id="comma-is-left-alone"),
    ],
)
def test_decimal_point_and_comma_are_left_alone(text: str, expected: str) -> None:
    assert bangla_digits_to_ascii(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("১" + KEJI, "1" + KEJI, id="bangla-unit-word"),
        pytest.param("৫০০" + MILI, "500" + MILI, id="bangla-unit-word-500"),
        pytest.param("৫০০ml", "500ml", id="latin-unit"),
    ],
)
def test_digits_attached_to_unit_words_get_no_space(text: str, expected: str) -> None:
    assert bangla_digits_to_ascii(text) == expected


def test_digits_inside_a_word_are_converted() -> None:
    assert bangla_digits_to_ascii("ক২খ") == "ক2খ"


def test_rupee_sign_is_not_changed() -> None:
    # U+09F3 is a currency symbol, not a digit. Only the digits next to it change.
    assert bangla_digits_to_ascii("৳৫০") == "৳50"


@pytest.mark.parametrize("code_point", range(0x09F4, 0x09FA))
def test_currency_fraction_signs_are_not_changed(code_point: int) -> None:
    sign = chr(code_point)
    assert bangla_digits_to_ascii(sign) == sign
    assert bangla_digits_to_ascii("a" + sign + "১") == "a" + sign + "1"


@pytest.mark.parametrize(
    "digit",
    [
        pytest.param("९", id="devanagari-nine"),
        pytest.param("٩", id="arabic-indic-nine"),
        pytest.param("１", id="fullwidth-one"),
    ],
)
def test_digits_of_other_scripts_are_not_changed(digit: str) -> None:
    assert bangla_digits_to_ascii(digit) == digit


@pytest.mark.parametrize("text", ["", "Chinigura Rice 1 kg", "½ kg", "  spaces  "])
def test_text_without_bangla_digits_is_unchanged(text: str) -> None:
    assert bangla_digits_to_ascii(text) == text


@pytest.mark.parametrize("text", ["১২", "১.৫" + KEJI, "", "a1b"])
def test_conversion_is_idempotent(text: str) -> None:
    once = bangla_digits_to_ascii(text)
    assert bangla_digits_to_ascii(once) == once


@pytest.mark.parametrize(
    "text",
    [
        "১‌০",  # an invisible character between two digits
        "১‍0 " + KEJI,
        "য়৪",  # a nukta letter next to a digit
        "plain 5",
    ],
)
def test_order_relative_to_clean_unicode_does_not_matter_for_digits(text: str) -> None:
    digits_after_clean = bangla_digits_to_ascii(clean_unicode(text))
    clean_after_digits = clean_unicode(bangla_digits_to_ascii(text))
    assert digits_after_clean == clean_after_digits


def test_invisible_character_between_digits_is_gone_after_both_steps() -> None:
    assert bangla_digits_to_ascii(clean_unicode("১‌০")) == "10"


@pytest.mark.parametrize("value", [None, 123, 1.5, float("nan"), b"abc", ["a"]])
def test_non_str_input_raises_type_error(value: object) -> None:
    with pytest.raises(TypeError, match="expected str"):
        bangla_digits_to_ascii(value)  # type: ignore[arg-type]
