"""Tests for src.normalise.text_clean.

All strings are invented. Characters outside ASCII are built from code points (see
tests/helpers.py), so each one is visible as a number and no tool can silently change it.
"""

import random
import unicodedata

import pytest

from src.normalise.digits import bangla_digits_to_ascii
from src.normalise.text_clean import clean_text
from src.normalise.unicode_clean import clean_unicode
from src.normalise.units import UNITS
from tests.helpers import bn

# Bangla words.
CHAL = bn(0x099A, 0x09BE, 0x09B2)  # চাল
TEL = bn(0x09A4, 0x09C7, 0x09B2)  # তেল
MOSLA = bn(0x09AE, 0x09B8, 0x09B2, 0x09BE)  # মসলা
KEJI = bn(0x0995, 0x09C7, 0x099C, 0x09BF)  # কেজি
KEJI_DOTTED = bn(0x0995, 0x09C7, 0x2E, 0x099C, 0x09BF, 0x2E)  # কে.জি.
KE = bn(0x0995, 0x09C7)  # কে
JI = bn(0x099C, 0x09BF)  # জি
MILI = bn(0x09AE, 0x09BF, 0x09B2, 0x09BF)  # মিলি
MILI_DOTTED = bn(0x09AE, 0x09BF, 0x2E, 0x09B2, 0x09BF, 0x2E)  # মি.লি.
GRAM = bn(0x0997, 0x09CD, 0x09B0, 0x09BE, 0x09AE)  # গ্রাম
GRA = bn(0x0997, 0x09CD, 0x09B0, 0x09BE)  # গ্রা
GRA_DOTTED = bn(0x0997, 0x09CD, 0x09B0, 0x09BE, 0x2E)  # গ্রা.
DANDA = bn(0x0964)
RUPEE = bn(0x09F3)  # ৳
BANGLA_FIVE = bn(0x09EB)  # ৫
BANGLA_ZERO = bn(0x09E6)  # ০

# Other characters outside ASCII.
NO_BREAK_SPACE = bn(0x00A0)
LINE_SEPARATOR = bn(0x2028)
NEXT_LINE = bn(0x0085)
TIMES = bn(0x00D7)
RIGHT_QUOTE = bn(0x2019)
HALF = bn(0x00BD)
CAPITAL_I_WITH_DOT = bn(0x0130)
COMBINING_DOT_ABOVE = bn(0x0307)
E_ACUTE = bn(0x00E9)

CASES = [
    # Spaces and case.
    pytest.param(f"Chinigura  Rice{NO_BREAK_SPACE}1kg", "chinigura rice 1 kg", id="nbsp"),
    pytest.param("Rice\t1 kg\n", "rice 1 kg", id="tab-and-newline"),
    pytest.param(f"Rice{LINE_SEPARATOR}Dal{NEXT_LINE}Oil", "rice dal oil", id="other-spaces"),
    pytest.param("  Rice   Dal  ", "rice dal", id="runs-of-spaces"),
    pytest.param("RICE Dal", "rice dal", id="case"),
    # Punctuation.
    pytest.param("Rice - Special (Offer!) 5KG", "rice special offer 5 kg", id="punctuation"),
    pytest.param("Nando's Peri-Peri 250ml", "nandos peri peri 250 ml", id="apostrophe-hyphen"),
    pytest.param(f"Nando{RIGHT_QUOTE}s Peri", "nandos peri", id="typographic-apostrophe"),
    pytest.param("Salt & Pepper", "salt pepper", id="ampersand"),
    pytest.param("Offer: 10% off!", "offer 10 off", id="percent"),
    pytest.param("Milk 3.5% fat 1L", "milk 3.5 fat 1 l", id="decimal-and-percent"),
    pytest.param("Dr. Oetker's e.g. mix", "dr oetkers e g mix", id="dots-in-abbreviations"),
    pytest.param("Item 1/2 kg", "item 1 2 kg", id="slash"),
    pytest.param(f"Oil {RUPEE}120 0.5L", "oil 120 0.5 l", id="rupee-sign"),
    pytest.param(f"{CHAL}{DANDA}{TEL}", f"{CHAL} {TEL}", id="danda"),
    pytest.param("a.5 and 1.5.2", "a 5 and 1.5.2", id="decimal-points"),
    pytest.param("!!!", "", id="only-punctuation"),
    pytest.param("-", "", id="only-hyphen"),
    pytest.param("   ", "", id="only-spaces"),
    pytest.param("", "", id="empty"),
    # Numbers and units.
    pytest.param("Dal 1,000gm", "dal 1000 gm", id="thousands"),
    pytest.param("Dal 1,000,000 gm", "dal 1000000 gm", id="two-thousands-commas"),
    pytest.param("Dal 1,5kg", "dal 1 5 kg", id="comma-decimal"),
    pytest.param("Dal 10,50 gm", "dal 10 50 gm", id="comma-decimal-two"),
    pytest.param("Oil 0.5L", "oil 0.5 l", id="decimal-unit"),
    pytest.param("Rice 2kg-3kg", "rice 2 kg 3 kg", id="two-sizes"),
    pytest.param("7up 500ml", "7up 500 ml", id="number-at-the-start-of-a-word"),
    pytest.param("B12 Vitamin 100gm", "b12 vitamin 100 gm", id="number-inside-a-word"),
    pytest.param("Rice 1 kgx", "rice 1 kgx", id="not-a-unit"),
    pytest.param("Rice 1kgx", "rice 1kgx", id="not-a-unit-attached"),
    pytest.param("Dal 5 lb", "dal 5 lb", id="unknown-unit"),
    pytest.param("Oil 1 ltr. Special", "oil 1 ltr special", id="dotted-latin-unit"),
    pytest.param(f"{HALF} kg", f"{HALF} kg", id="vulgar-fraction"),
    # Multiplication.
    pytest.param("Soybean Oil 2x500ml", "soybean oil 2 x 500 ml", id="x"),
    pytest.param("Soybean Oil 2X500ml", "soybean oil 2 x 500 ml", id="capital-x"),
    pytest.param(f"Soybean Oil 2{TIMES}500 ml", "soybean oil 2 x 500 ml", id="times-sign"),
    pytest.param("Tea 2 * 100g", "tea 2 x 100 g", id="asterisk"),
    pytest.param("Tea 2x5x3", "tea 2 x 5 x 3", id="two-multiplications"),
    pytest.param("Tea 100g*2", "tea 100 g 2", id="count-last-loses-the-x"),
    pytest.param("Rice 5 x tin", "rice 5 x tin", id="x-not-between-digits"),
    # Bangla.
    pytest.param(f"{CHAL} 1{KEJI}", f"{CHAL} 1 {KEJI}", id="bangla-unit-attached"),
    pytest.param(f"{CHAL} 1{KEJI_DOTTED}", f"{CHAL} 1 {KEJI}", id="bangla-dotted-attached"),
    pytest.param(f"{CHAL} 1 {KEJI_DOTTED}", f"{CHAL} 1 {KEJI}", id="bangla-dotted-spaced"),
    pytest.param(f"{TEL} 500 {MILI_DOTTED}", f"{TEL} 500 {MILI}", id="bangla-dotted-ml"),
    pytest.param(f"{MOSLA} 250{GRA_DOTTED}", f"{MOSLA} 250 {GRA}", id="bangla-dotted-trailing"),
    pytest.param(GRAM, GRAM, id="vowel-signs-and-virama-are-kept"),
    pytest.param(f"{CHAL} {TEL} {MOSLA}", f"{CHAL} {TEL} {MOSLA}", id="bangla-words"),
    # Case and normalisation corner.
    pytest.param(CAPITAL_I_WITH_DOT, "i" + COMBINING_DOT_ABOVE, id="capital-i-with-dot"),
    pytest.param(f"Caf{E_ACUTE} 1kg", f"caf{E_ACUTE} 1 kg", id="accented-letter-is-kept"),
]


@pytest.mark.parametrize(("text", "expected"), CASES)
def test_clean_text(text: str, expected: str) -> None:
    assert clean_text(text) == expected


@pytest.mark.parametrize("key", sorted(UNITS))
def test_every_unit_in_the_table_is_split_from_its_number(key: str) -> None:
    expected = "1 " + key.replace(".", "")
    assert clean_text(f"1{key}") == expected
    assert clean_text(f"1 {key}") == expected
    assert clean_text(f"Rice 1{key.upper()}") == "rice " + expected


def test_a_dotted_bangla_unit_is_not_joined_after_a_letter() -> None:
    # The join is allowed after a digit or a non-word character, not straight after a letter.
    assert clean_text("x" + KEJI_DOTTED) == "x" + KE + " " + JI


def test_text_in_the_expected_pipeline_order() -> None:
    raw = f"{CHAL} {BANGLA_FIVE}{BANGLA_ZERO}{BANGLA_ZERO}{chr(0x200C)}{MILI_DOTTED}"
    prepared = bangla_digits_to_ascii(clean_unicode(raw))
    assert clean_text(prepared) == f"{CHAL} 500 {MILI}"


@pytest.mark.parametrize("space", [" ", "\t", "\n", "\r", "\x0b", "\x0c", NO_BREAK_SPACE])
def test_every_kind_of_space_becomes_a_normal_space(space: str) -> None:
    assert clean_text(f"a{space}b") == "a b"


# Random strings: invariants that must hold for any input.

PIECES = [
    "0",
    "1",
    "5",
    "7",
    ".",
    ",",
    " ",
    "  ",
    "x",
    "X",
    TIMES,
    "*",
    "k",
    "g",
    "m",
    "l",
    "kg",
    "ml",
    "ltr.",
    "gm",
    "KG",
    "'",
    RIGHT_QUOTE,
    "-",
    "/",
    RUPEE,
    DANDA,
    bn(0x0995),  # ক
    bn(0x09C7),  # ◌ে
    bn(0x09BF),  # ◌ি
    bn(0x09CD),  # ◌্
    NO_BREAK_SPACE,
    "\t",
    "\n",
    E_ACUTE,
    "%",
    "&",
    "L",
    "t",
    "r",
    "b",
    "B",
    CAPITAL_I_WITH_DOT,
    KEJI_DOTTED,
    MILI_DOTTED,
    GRA_DOTTED,
    bn(0x09B2, 0x09BF, 0x2E),  # লি.
    KEJI,
]
SEEDS = [20261104, 1, 2, 3]


def _random_strings(seed: int, count: int = 5000) -> list[str]:
    rng = random.Random(seed)
    return ["".join(rng.choice(PIECES) for _ in range(rng.randint(0, 12))) for _ in range(count)]


@pytest.mark.parametrize("seed", SEEDS)
def test_clean_text_is_idempotent(seed: int) -> None:
    for text in _random_strings(seed):
        once = clean_text(text)
        assert clean_text(once) == once, ascii(text)


@pytest.mark.parametrize("seed", SEEDS)
def test_output_has_no_stray_spaces_and_only_allowed_characters(seed: int) -> None:
    for text in _random_strings(seed):
        result = clean_text(text)
        assert result == result.strip(), ascii(text)
        assert "  " not in result, ascii(text)
        for char in result:
            allowed = char in " ." or unicodedata.category(char)[0] in "LMN"
            assert allowed, f"{ascii(char)} in {ascii(result)} from {ascii(text)}"


@pytest.mark.parametrize("value", [None, 123, 1.5, float("nan"), b"abc", ["a"]])
def test_non_str_input_raises_type_error(value: object) -> None:
    with pytest.raises(TypeError, match="expected str"):
        clean_text(value)  # type: ignore[arg-type]
