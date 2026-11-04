"""Tests for src.normalise.patterns.

All Bangla strings are written as \\u escapes and are invented for testing.
"""

import re
import unicodedata

import pytest

from src.normalise.patterns import BOUNDARY_AFTER, BOUNDARY_BEFORE, WORD_CHARS, bounded

WORD_CHAR = re.compile(f"[{WORD_CHARS}]")
KEJI = "কেজি"  # the unit word "keji" (kg): KA + E sign + JA + I sign


def _class_code_points() -> list[int]:
    """Return the code points that the Bangla part of WORD_CHARS covers."""
    return [*range(0x0980, 0x09F2), 0x09FC, 0x09FE]


def test_word_chars_text_is_the_agreed_definition() -> None:
    assert WORD_CHARS == "A-Za-z0-9ঀ-ৱৼ৾"


def test_every_assigned_bangla_character_in_the_class_is_a_letter_mark_or_digit() -> None:
    for code_point in _class_code_points():
        category = unicodedata.category(chr(code_point))
        if category == "Cn":  # not assigned
            continue
        assert category[0] in "LM" or category == "Nd", f"U+{code_point:04X} is {category}"


@pytest.mark.parametrize("code_point", [*range(0x09F2, 0x09FC), 0x09FD])
def test_bangla_symbols_are_not_word_characters(code_point: int) -> None:
    assert WORD_CHAR.fullmatch(chr(code_point)) is None


@pytest.mark.parametrize(
    "char",
    ["a", "Z", "0", "9", "ক", "ে", "ি", "্", "১", "ৼ", "৾"],
)
def test_letters_vowel_signs_and_digits_are_word_characters(char: str) -> None:
    assert WORD_CHAR.fullmatch(char) is not None


@pytest.mark.parametrize(
    "char", [" ", ".", ",", "-", "/", "(", ")", "_", "×", "৳", "।", "é"]
)
def test_separators_are_not_word_characters(char: str) -> None:
    # U+00D7 is the multiplication sign, U+09F3 the rupee sign and U+0964 the danda.
    # U+00E9 (e-acute) is a known limitation: accented Latin letters count as separators.
    assert WORD_CHAR.fullmatch(char) is None


def test_a_whole_bangla_word_is_one_run_of_word_characters() -> None:
    assert re.findall(f"[{WORD_CHARS}]+", KEJI) == [KEJI]


@pytest.mark.parametrize(
    ("text", "found"),
    [
        pytest.param("1 kg", True, id="after-space"),
        pytest.param("(kg)", True, id="in-brackets"),
        pytest.param("rice,kg", True, id="after-comma"),
        pytest.param("kg", True, id="whole-string"),
        pytest.param("1kg", False, id="digit-before"),
        pytest.param("kgs", False, id="letter-after"),
        pytest.param("okg", False, id="letter-before"),
        pytest.param("৳kg", True, id="rupee-sign-is-a-separator"),
    ],
)
def test_bounded_latin_word(text: str, found: bool) -> None:
    assert bool(re.search(bounded("kg"), text)) is found


@pytest.mark.parametrize(
    ("text", "found"),
    [
        pytest.param(" " + KEJI + " ", True, id="between-spaces"),
        pytest.param("1 " + KEJI, True, id="after-number-and-space"),
        pytest.param(KEJI + "তে", False, id="longer-word"),
        pytest.param("প্র" + KEJI, False, id="inside-longer-word"),
    ],
)
def test_bounded_bangla_word(text: str, found: bool) -> None:
    assert bool(re.search(bounded(KEJI), text)) is found


def test_bounded_groups_alternatives() -> None:
    pattern = re.compile(bounded("kg|gm"))
    assert pattern.search("1 gm") is not None
    assert pattern.search("1 kg") is not None
    # Both alternatives must be bounded on the right. Without the group, "kgs" would match,
    # because only the last alternative would carry the lookahead.
    assert pattern.search("1 kgs") is None
    assert pattern.search("1 gms") is None


def test_bounded_works_with_ignore_case() -> None:
    pattern = re.compile(bounded("kg"), re.IGNORECASE)
    assert [pattern.search(text) is not None for text in ("KG", "Kg", "kG")] == [True] * 3


def test_boundaries_are_the_pieces_bounded_is_made_from() -> None:
    assert bounded("x") == f"{BOUNDARY_BEFORE}(?:x){BOUNDARY_AFTER}"
