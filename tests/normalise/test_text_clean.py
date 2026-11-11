"""Tests for src.normalise.text_clean.

All strings are invented. Characters outside ASCII are built from code points (see
tests/helpers.py), so each one is visible as a number and no tool can silently change it.
"""

import random
import re
import unicodedata

import pytest

from src.normalise.digits import bangla_digits_to_ascii
from src.normalise.patterns import WORD_CHARS
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
KILO = bn(0x0995, 0x09BF, 0x09B2, 0x09CB)  # কিলো
KILOGRAM = bn(0x0995, 0x09BF, 0x09B2, 0x09CB, 0x0997, 0x09CD, 0x09B0, 0x09BE, 0x09AE)  # কিলোগ্রাম
LITAR = bn(0x09B2, 0x09BF, 0x099F, 0x09BE, 0x09B0)  # লিটার
LI_DOTTED = bn(0x09B2, 0x09BF, 0x2E)  # লি.
MILILITAR = bn(0x09AE, 0x09BF, 0x09B2, 0x09BF, 0x09B2, 0x09BF, 0x099F, 0x09BE, 0x09B0)  # মিলিলিটার
EMEL = bn(0x098F, 0x09AE, 0x098F, 0x09B2)  # এমএল
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
    pytest.param("Dal 1,000gm", "dal 1000 g", id="thousands"),
    pytest.param("Dal 1,000,000 gm", "dal 1000000 g", id="two-thousands-commas"),
    pytest.param("Dal 1,5kg", "dal 1 5 kg", id="comma-decimal"),
    pytest.param("Dal 10,50 gm", "dal 10 50 g", id="comma-decimal-two"),
    pytest.param("Oil 0.5L", "oil 0.5 l", id="decimal-unit"),
    pytest.param("Rice 2kg-3kg", "rice 2 kg 3 kg", id="two-sizes"),
    pytest.param("7up 500ml", "7up 500 ml", id="number-at-the-start-of-a-word"),
    pytest.param("B12 Vitamin 100gm", "b12 vitamin 100 g", id="number-inside-a-word"),
    pytest.param("Rice 1 kgx", "rice 1 kgx", id="not-a-unit"),
    pytest.param("Rice 1kgx", "rice 1kgx", id="not-a-unit-attached"),
    pytest.param("Dal 5 lb", "dal 5 lb", id="unknown-unit"),
    pytest.param("Oil 1 ltr. Special", "oil 1 l special", id="dotted-latin-unit"),
    pytest.param(f"{HALF} kg", f"{HALF} kg", id="vulgar-fraction"),
    # Multiplication.
    pytest.param("Soybean Oil 2x500ml", "soybean oil 2 x 500 ml", id="x"),
    pytest.param("Soybean Oil 2X500ml", "soybean oil 2 x 500 ml", id="capital-x"),
    pytest.param(f"Soybean Oil 2{TIMES}500 ml", "soybean oil 2 x 500 ml", id="times-sign"),
    pytest.param("Tea 2 * 100g", "tea 2 x 100 g", id="asterisk"),
    pytest.param("Tea 2x5x3", "tea 2 x 5 x 3", id="two-multiplications"),
    pytest.param("Tea 100g*2", "tea 100 g x 2", id="count-last-asterisk"),
    pytest.param(f"Tea 100g{TIMES}2", "tea 100 g x 2", id="count-last-times-sign"),
    pytest.param("Tea 100 g * 2", "tea 100 g x 2", id="count-last-spaced"),
    pytest.param("Tea 100gm*2", "tea 100 g x 2", id="count-last-gm"),
    pytest.param("Oil 500ml*3", "oil 500 ml x 3", id="count-last-ml"),
    pytest.param("Tea 1.5kg*2", "tea 1.5 kg x 2", id="count-last-decimal"),
    pytest.param("Oil 1 ltr.*2", "oil 1 l x 2", id="count-last-dotted-latin-unit"),
    pytest.param("Tea 100g*2*3", "tea 100 g x 2 x 3", id="count-last-then-another-factor"),
    pytest.param("Tea 100g*", "tea 100 g", id="asterisk-without-a-digit"),
    pytest.param("Tea 100 pcs*2", "tea 100 pcs 2", id="asterisk-after-an-unknown-unit"),
    pytest.param("Tea b100g*2", "tea b100g 2", id="asterisk-after-a-number-inside-a-word"),
    pytest.param("Rice 5 x tin", "rice 5 x tin", id="x-not-between-digits"),
    # Bangla.
    pytest.param(f"{CHAL} 1{KEJI}", f"{CHAL} 1 kg", id="bangla-unit-attached"),
    pytest.param(f"{CHAL} 1{KEJI_DOTTED}", f"{CHAL} 1 kg", id="bangla-dotted-attached"),
    pytest.param(f"{CHAL} 1 {KEJI_DOTTED}", f"{CHAL} 1 kg", id="bangla-dotted-spaced"),
    pytest.param(f"{TEL} 500 {MILI_DOTTED}", f"{TEL} 500 ml", id="bangla-dotted-ml"),
    pytest.param(f"{MOSLA} 250{GRA_DOTTED}", f"{MOSLA} 250 g", id="bangla-dotted-trailing"),
    pytest.param(f"{CHAL} 1{KEJI}*2", f"{CHAL} 1 kg x 2", id="bangla-count-last"),
    pytest.param(f"{CHAL} 1 {KEJI_DOTTED}*2", f"{CHAL} 1 kg x 2", id="bangla-dotted-count-last"),
    pytest.param(
        f"{MOSLA} 250{GRA_DOTTED}*2", f"{MOSLA} 250 g x 2", id="bangla-trailing-dot-count"
    ),
    pytest.param(GRAM, GRAM, id="vowel-signs-and-virama-are-kept"),
    pytest.param(f"{CHAL} {TEL} {MOSLA}", f"{CHAL} {TEL} {MOSLA}", id="bangla-words"),
    # Case and normalisation corner.
    pytest.param(CAPITAL_I_WITH_DOT, "i" + COMBINING_DOT_ABOVE, id="capital-i-with-dot"),
    pytest.param(f"Caf{E_ACUTE} 1kg", f"caf{E_ACUTE} 1 kg", id="accented-letter-is-kept"),
]


@pytest.mark.parametrize(("text", "expected"), CASES)
def test_clean_text(text: str, expected: str) -> None:
    assert clean_text(text) == expected


# Unit canonicalisation (step 8): the unit word after a number becomes kg, g, l or ml.
# Every title here is invented.
CANONICAL_CASES = [
    # Spelling, case and spacing.
    pytest.param("Rice 500gm", "rice 500 g", id="gm-attached"),
    pytest.param("Rice 500 GM", "rice 500 g", id="gm-capitals-spaced"),
    pytest.param("Oil 2ltr", "oil 2 l", id="ltr-attached"),
    pytest.param("Oil 2 Ltr.", "oil 2 l", id="ltr-dotted-title-case"),
    pytest.param("Oil 250 mls", "oil 250 ml", id="mls"),
    pytest.param("Sugar 5 kgs", "sugar 5 kg", id="kgs"),
    pytest.param("Oil 1.5 Litres", "oil 1.5 l", id="litres-decimal"),
    pytest.param("Milk 2 x 1 liter", "milk 2 x 1 l", id="liter-after-a-count"),
    pytest.param("Dal 500 Grams", "dal 500 g", id="grams"),
    pytest.param("Rice 5\tKG", "rice 5 kg", id="tab-between-number-and-unit"),
    pytest.param("Rice 1 kg 500 gm", "rice 1 kg 500 g", id="two-sizes"),
    pytest.param("Dal 1,000gm", "dal 1000 g", id="thousands-comma"),
    # Packs.
    pytest.param("Tea 2 x 500gm", "tea 2 x 500 g", id="count-first"),
    pytest.param("Tea 2x500gm", "tea 2 x 500 g", id="count-first-attached"),
    pytest.param("Tea 100gm*2", "tea 100 g x 2", id="count-last-asterisk"),
    pytest.param("Tea 100 gm * 2", "tea 100 g x 2", id="count-last-spaced"),
    # Only a unit word directly after a number is changed.
    pytest.param("Gram Flour 1kg", "gram flour 1 kg", id="gram-as-a-word"),
    pytest.param("Gram Flour 500 Grams", "gram flour 500 g", id="gram-word-and-gram-unit"),
    pytest.param("Dal kg 5", "dal kg 5", id="unit-before-the-number"),
    pytest.param("Dal 1 litre litre", "dal 1 l litre", id="only-the-first-unit-word"),
    pytest.param("Dal Ltr", "dal ltr", id="unit-without-a-number"),
    pytest.param("Vitamin G 5gm", "vitamin g 5 g", id="g-as-a-letter"),
    # Not units, or not directly after a number: unchanged.
    pytest.param("Rice 1 kgx", "rice 1 kgx", id="kgx"),
    pytest.param("Rice 1kgx", "rice 1kgx", id="kgx-attached"),
    pytest.param("Rice 1 Large", "rice 1 large", id="word-that-starts-with-a-unit"),
    pytest.param("Rice 1 gramophone", "rice 1 gramophone", id="word-that-starts-with-gram"),
    pytest.param("Dal 5 lb", "dal 5 lb", id="lb"),
    pytest.param("Dal 5 oz", "dal 5 oz", id="oz"),
    pytest.param("Spice 100 pcs", "spice 100 pcs", id="pcs"),
    pytest.param("Vitamin b12gm", "vitamin b12gm", id="number-inside-a-word"),
    # Bangla unit words become the Latin symbols.
    pytest.param(f"{CHAL} 1{KEJI}", f"{CHAL} 1 kg", id="bangla-keji"),
    pytest.param(f"{CHAL} 2 {KEJI_DOTTED}", f"{CHAL} 2 kg", id="bangla-keji-dotted"),
    pytest.param(f"{CHAL} 1 {KILO}", f"{CHAL} 1 kg", id="bangla-kilo"),
    pytest.param(f"{MOSLA} 250 {GRAM}", f"{MOSLA} 250 g", id="bangla-gram"),
    pytest.param(f"{TEL} 1 {LITAR}", f"{TEL} 1 l", id="bangla-litre"),
    pytest.param(f"{TEL} 500 {MILI}", f"{TEL} 500 ml", id="bangla-ml"),
    pytest.param(f"{TEL} 2 x 500{EMEL}", f"{TEL} 2 x 500 ml", id="bangla-ml-after-a-count"),
    pytest.param(f"{CHAL} {KEJI} 5", f"{CHAL} {KEJI} 5", id="bangla-unit-before-the-number"),
]


@pytest.mark.parametrize(("text", "expected"), CANONICAL_CASES)
def test_the_unit_after_a_number_becomes_its_symbol(text: str, expected: str) -> None:
    assert clean_text(text) == expected


# Every spelling in the table of units, with the symbol that clean_text must write for it. It is
# written out here, not read from the table, so that a wrong symbol in the table is caught.
UNIT_SYMBOLS = [
    pytest.param("kg", "kg", id="kg"),
    pytest.param("kgs", "kg", id="kgs"),
    pytest.param(KEJI, "kg", id="keji"),
    pytest.param(KEJI_DOTTED, "kg", id="keji-dotted"),
    pytest.param(KILO, "kg", id="kilo"),
    pytest.param(KILOGRAM, "kg", id="kilogram"),
    pytest.param("g", "g", id="g"),
    pytest.param("gm", "g", id="gm"),
    pytest.param("gms", "g", id="gms"),
    pytest.param("gram", "g", id="gram"),
    pytest.param("grams", "g", id="grams"),
    pytest.param(GRAM, "g", id="bangla-gram"),
    pytest.param(GRA_DOTTED, "g", id="bangla-gra-dotted"),
    pytest.param("l", "l", id="l"),
    pytest.param("ltr", "l", id="ltr"),
    pytest.param("ltr.", "l", id="ltr-dotted"),
    pytest.param("ltrs", "l", id="ltrs"),
    pytest.param("litre", "l", id="litre"),
    pytest.param("litres", "l", id="litres"),
    pytest.param("liter", "l", id="liter"),
    pytest.param("liters", "l", id="liters"),
    pytest.param(LITAR, "l", id="litar"),
    pytest.param(LI_DOTTED, "l", id="li-dotted"),
    pytest.param("ml", "ml", id="ml"),
    pytest.param("mls", "ml", id="mls"),
    pytest.param(MILI, "ml", id="mili"),
    pytest.param(MILILITAR, "ml", id="mililitar"),
    pytest.param(MILI_DOTTED, "ml", id="mili-dotted"),
    pytest.param(EMEL, "ml", id="emel"),
]


def test_the_symbol_table_covers_every_unit_in_the_table_of_units() -> None:
    assert {param.values[0] for param in UNIT_SYMBOLS} == set(UNITS)


@pytest.mark.parametrize(("key", "symbol"), UNIT_SYMBOLS)
def test_every_unit_in_the_table_is_split_from_its_number_and_becomes_its_symbol(
    key: str, symbol: str
) -> None:
    assert clean_text(f"1{key}") == f"1 {symbol}"
    assert clean_text(f"1 {key}") == f"1 {symbol}"
    assert clean_text(f"0.5{key}") == f"0.5 {symbol}"
    assert clean_text(f"Rice 1{key.upper()}") == f"rice 1 {symbol}"
    assert clean_text(f"Rice 1{key} Pack") == f"rice 1 {symbol} pack"
    assert clean_text(f"Rice 2 x 500{key}") == f"rice 2 x 500 {symbol}"
    assert clean_text(f"Rice 500{key}*2") == f"rice 500 {symbol} x 2"


@pytest.mark.parametrize(("key", "symbol"), UNIT_SYMBOLS)
def test_a_unit_that_does_not_follow_a_number_is_kept(key: str, symbol: str) -> None:
    # Only the dots inside dotted abbreviations are joined (step 4); the word itself stays.
    kept = key.replace(".", "")
    assert clean_text(f"Rice {key} 5") == f"rice {kept} 5"
    assert clean_text(key) == kept
    assert clean_text(f"Rice b1{key}") == f"rice b1{kept}"


@pytest.mark.parametrize(
    ("key", "symbol"), [param for param in UNIT_SYMBOLS if "." not in param.values[0]]
)
def test_a_word_that_only_starts_with_a_unit_is_not_changed(key: str, symbol: str) -> None:
    assert clean_text(f"Rice 1 {key}x") == f"rice 1 {key}x"
    assert clean_text(f"Rice 1{key}x") == f"rice 1{key}x"


def test_a_dotted_bangla_unit_is_not_joined_after_a_letter() -> None:
    # The join is allowed after a digit or a non-word character, not straight after a letter.
    assert clean_text("x" + KEJI_DOTTED) == "x" + KE + " " + JI


def test_text_in_the_expected_pipeline_order() -> None:
    raw = f"{CHAL} {BANGLA_FIVE}{BANGLA_ZERO}{BANGLA_ZERO}{chr(0x200C)}{MILI_DOTTED}"
    prepared = bangla_digits_to_ascii(clean_unicode(raw))
    assert clean_text(prepared) == f"{CHAL} 500 ml"


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
    "gram",
    "litre",
    "kgs",
    "mls",
    "gms",
    "ltr",
    "liters",
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
    LITAR,
    EMEL,
    MILI,
    GRAM,
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


# A unit word directly after a number, found in the output of clean_text. The unit words are the
# dot-free spellings in the table of units; the word-character class is the project's own.
_UNIT_WORDS_BY_LENGTH = sorted({key.replace(".", "") for key in UNITS}, key=len, reverse=True)
_UNIT_AFTER_NUMBER = re.compile(
    rf"(?<![{WORD_CHARS}])[0-9]+(?:\.[0-9]+)?\s*({'|'.join(map(re.escape, _UNIT_WORDS_BY_LENGTH))})"
    rf"(?![{WORD_CHARS}])"
)
SYMBOLS = {"kg", "g", "l", "ml"}


def units_after_numbers(text: str) -> list[str]:
    """Return the unit words that directly follow a number in the text."""
    return _UNIT_AFTER_NUMBER.findall(text)


def test_the_invariant_check_finds_a_unit_that_is_not_a_symbol() -> None:
    # Guards the check below against passing because it finds nothing.
    text = "rice 1 gm and 2 x 500 ml and 3 kg and 4 gramophone"
    assert units_after_numbers(text) == ["gm", "ml", "kg"]
    assert units_after_numbers(f"{CHAL} 1 {KEJI} gram flour b12gm kg 5") == [KEJI]


@pytest.mark.parametrize("seed", SEEDS)
def test_every_unit_directly_after_a_number_in_the_output_is_a_symbol(seed: int) -> None:
    found = 0
    for text in _random_strings(seed):
        units = units_after_numbers(clean_text(text))
        found += len(units)
        assert set(units) <= SYMBOLS, ascii(text)
    assert found > 100  # the random strings do put units after numbers


@pytest.mark.parametrize("value", [None, 123, 1.5, float("nan"), b"abc", ["a"]])
def test_non_str_input_raises_type_error(value: object) -> None:
    with pytest.raises(TypeError, match="expected str"):
        clean_text(value)  # type: ignore[arg-type]
