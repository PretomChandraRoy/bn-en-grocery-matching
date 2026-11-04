"""Tests for src.normalise.unicode_clean.

All Bangla strings are written as \\u escapes and are invented for testing. The escapes stop
an editor from silently changing the exact characters being tested.
"""

import pytest

from src.normalise.unicode_clean import INVISIBLE_CHARACTERS, clean_unicode, remove_invisible

# Bangla building blocks used below.
NUKTA = "\u09bc"  # BENGALI SIGN NUKTA
VOWEL_E = "\u09c7"  # BENGALI VOWEL SIGN E
VOWEL_AA = "\u09be"  # BENGALI VOWEL SIGN AA
VOWEL_O = "\u09cb"  # BENGALI VOWEL SIGN O (the composition of E + AA)
CHAL = "\u099a\u09be\u09b2"  # the word "chal" (rice): CA + AA sign + LA

# Each pair: (precomposed letter, the same letter as base + nukta).
NUKTA_LETTERS = [
    pytest.param("\u09df", "\u09af" + NUKTA, id="YYA"),
    pytest.param("\u09dc", "\u09a1" + NUKTA, id="RRA"),
    pytest.param("\u09dd", "\u09a2" + NUKTA, id="RHA"),
]


def test_invisible_set_is_the_agreed_eight_characters() -> None:
    expected = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD, 0x200E, 0x200F}
    assert {ord(char) for char in INVISIBLE_CHARACTERS} == expected


@pytest.mark.parametrize("char", sorted(INVISIBLE_CHARACTERS))
def test_each_invisible_character_is_removed(char: str) -> None:
    assert remove_invisible("a" + char + "b") == "ab"
    assert clean_unicode("a" + char + "b") == "ab"


def test_invisible_character_inside_a_bangla_word_is_removed() -> None:
    word_with_zwj = "\u099a\u200d\u09be\u09b2"
    assert clean_unicode(word_with_zwj) == CHAL


@pytest.mark.parametrize(("precomposed", "base_plus_nukta"), NUKTA_LETTERS)
def test_nukta_letters_become_base_plus_nukta(precomposed: str, base_plus_nukta: str) -> None:
    assert clean_unicode(precomposed) == base_plus_nukta


@pytest.mark.parametrize(("precomposed", "base_plus_nukta"), NUKTA_LETTERS)
def test_both_spellings_of_a_nukta_letter_agree(precomposed: str, base_plus_nukta: str) -> None:
    assert precomposed != base_plus_nukta  # the raw strings differ
    assert clean_unicode(precomposed) == clean_unicode(base_plus_nukta)


def test_vowel_signs_e_and_aa_compose_into_o() -> None:
    assert clean_unicode(VOWEL_E + VOWEL_AA) == VOWEL_O
    assert clean_unicode(VOWEL_O) == VOWEL_O


def test_zwnj_between_vowel_signs_does_not_block_composition() -> None:
    # NFC alone leaves E + ZWNJ + AA as three characters. Removing the ZWNJ first lets the
    # two vowel signs compose, so this fails if the two steps are ever put in the wrong order.
    assert clean_unicode(VOWEL_E + "\u200c" + VOWEL_AA) == VOWEL_O


def test_nfc_applies_to_latin_text_too() -> None:
    assert clean_unicode("e\u0301") == "\u00e9"  # e + combining acute -> precomposed e-acute


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Chinigura Rice 1 kg",
        "500ml",
        CHAL,
        "\u09e6\u09e7\u09e8\u09e9\u09ea\u09eb\u09ec\u09ed\u09ee\u09ef",  # Bangla digits
        "  two  spaces  ",
        "non\u00a0breaking",  # U+00A0 is left for the later whitespace step
    ],
)
def test_text_without_issues_is_unchanged(text: str) -> None:
    assert clean_unicode(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "\u09df\u200d" + CHAL,
        VOWEL_E + "\u200c" + VOWEL_AA,
        "a\u00adb\ufeff",
        "",
    ],
)
def test_clean_unicode_is_idempotent(text: str) -> None:
    once = clean_unicode(text)
    assert clean_unicode(once) == once


@pytest.mark.parametrize("value", [None, 123, 1.5, float("nan"), b"abc", ["a"]])
def test_non_str_input_raises_type_error(value: object) -> None:
    with pytest.raises(TypeError, match="expected str"):
        remove_invisible(value)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="expected str"):
        clean_unicode(value)  # type: ignore[arg-type]
