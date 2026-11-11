"""The table of size units understood by the size parser.

This is the one place to add or change a unit. Each key is the unit exactly as it appears in a
title: Latin keys are in lower case, and matching ignores the case of Latin letters. The table
grows from the pilot report of numbers followed by words that were not recognised.

Every key must already be in the form produced by clean_unicode (NFC, no invisible
characters). The Bangla keys are written as escapes in the code.

Each unit also has one symbol (kg, g, l or ml), the form that title normalisation writes in
place of every spelling in its group. The symbols are themselves keys of the table, so a
normalised title still reads as a title with known units.
"""

import re
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Unit:
    """A size unit and how to convert it to the base unit.

    Attributes:
        kind: "weight" (base unit: gram) or "volume" (base unit: millilitre).
        factor: How many base units one of this unit is.
        symbol: The one spelling (a Latin key of the table) that title normalisation writes for
            every spelling of this unit.
    """

    kind: Literal["weight", "volume"]
    factor: int
    symbol: str


_KILOGRAM = Unit("weight", 1000, "kg")
_GRAM = Unit("weight", 1, "g")
_LITRE = Unit("volume", 1000, "l")
_MILLILITRE = Unit("volume", 1, "ml")

UNITS: dict[str, Unit] = {
    # Kilogram (1000 g).
    "kg": _KILOGRAM,
    "kgs": _KILOGRAM,
    "\u0995\u09c7\u099c\u09bf": _KILOGRAM,  # কেজি
    "\u0995\u09c7.\u099c\u09bf.": _KILOGRAM,  # কে.জি.
    "\u0995\u09bf\u09b2\u09cb": _KILOGRAM,  # কিলো
    "\u0995\u09bf\u09b2\u09cb\u0997\u09cd\u09b0\u09be\u09ae": _KILOGRAM,  # কিলোগ্রাম
    # Gram (1 g).
    "g": _GRAM,
    "gm": _GRAM,
    "gms": _GRAM,
    "gram": _GRAM,
    "grams": _GRAM,
    "\u0997\u09cd\u09b0\u09be\u09ae": _GRAM,  # গ্রাম
    "\u0997\u09cd\u09b0\u09be.": _GRAM,  # গ্রা.
    # Litre (1000 ml).
    "l": _LITRE,
    "ltr": _LITRE,
    "ltr.": _LITRE,
    "ltrs": _LITRE,
    "litre": _LITRE,
    "litres": _LITRE,
    "liter": _LITRE,
    "liters": _LITRE,
    "\u09b2\u09bf\u099f\u09be\u09b0": _LITRE,  # লিটার
    "\u09b2\u09bf.": _LITRE,  # লি.
    # Millilitre (1 ml).
    "ml": _MILLILITRE,
    "mls": _MILLILITRE,
    "\u09ae\u09bf\u09b2\u09bf": _MILLILITRE,  # মিলি
    "\u09ae\u09bf\u09b2\u09bf\u09b2\u09bf\u099f\u09be\u09b0": _MILLILITRE,  # মিলিলিটার
    "\u09ae\u09bf.\u09b2\u09bf.": _MILLILITRE,  # মি.লি.
    "\u098f\u09ae\u098f\u09b2": _MILLILITRE,  # এমএল
}


def lookup_unit(text: str) -> Unit | None:
    """Return the unit for a unit word, ignoring the case of Latin letters.

    Args:
        text: The unit word, for example "KG" or the Bangla word for kilogram.

    Returns:
        The matching Unit, or None if the word is not in the table.
    """
    return UNITS.get(text.strip().lower())


def symbols_by_dot_free_unit(units: dict[str, Unit] = UNITS) -> dict[str, str]:
    """Return the symbol for each unit spelling, with the dots of the spelling removed.

    Title normalisation removes the dots inside unit abbreviations before it looks for a unit,
    so "ltr." is looked up as "ltr". This table is the single source for the replacement.

    Args:
        units: The unit table; tests pass a changed copy.

    Returns:
        A dictionary from each dot-free spelling to its symbol.

    Raises:
        ValueError: If two spellings become the same once their dots are removed but have
            different symbols, which would make the replacement ambiguous.
    """
    symbols: dict[str, str] = {}
    for key, unit in units.items():
        word = key.replace(".", "")
        if symbols.setdefault(word, unit.symbol) != unit.symbol:
            raise ValueError(f"the unit spellings that become {word!r} have different symbols")
    return symbols


def _either_case(unit: str) -> str:
    """Return a pattern for one unit in which each ASCII letter matches either case."""
    pieces = []
    for char in unit:
        if char.isascii() and char.isalpha():
            pieces.append(f"[{char.lower()}{char.upper()}]")
        else:
            pieces.append(re.escape(char))
    return "".join(pieces)


def unit_alternation() -> str:
    """Return a regular-expression alternation that matches every unit in UNITS.

    Longer units come first, so that "kgs" is tried before "kg". Letter case is handled by
    character classes such as [kK], not by re.IGNORECASE, which would also accept a few
    unrelated non-ASCII letters.

    Returns:
        The alternation, without surrounding parentheses.
    """
    return "|".join(_either_case(unit) for unit in sorted(UNITS, key=len, reverse=True))
