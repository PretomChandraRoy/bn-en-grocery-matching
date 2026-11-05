"""Text clean-up: the last character-level step in building title_norm.

clean_text makes a title easier to compare. Run it after clean_unicode and
bangla_digits_to_ascii. Size parsing (sizes.py) reads the text before this step, so the two do
not depend on each other, and the size text stays in the result.

The steps run in this fixed order, and the order matters:

 1. The text is put into lower case.
 2. A times sign or an asterisk between two digits becomes "x".
 3. A thousands comma between digits is removed ("1,000" becomes "1000").
 4. The dots inside dotted unit abbreviations are joined, so the Bangla abbreviations of kg and
    ml are not split into two words. This is also allowed straight after a digit.
 5. An apostrophe between two word characters is removed ("nando's" becomes "nandos").
 6. Only letters, marks and numbers are kept, with a decimal point between two digits. Everything
    else becomes a space. This includes every Unicode space character (a no-break space, a line
    separator, a tab, a newline): they are replaced by a normal space, not removed. Bangla vowel
    signs and the virama are marks, so they are kept.
 7. "x" between two digits gets a space on each side ("2x500" becomes "2 x 500").
 8. A space is put between a number and a unit ("500ml" becomes "500 ml"), unless the number
    follows a word character, so "7up" and "b12" are not split.
 9. Runs of spaces are collapsed and the ends are trimmed.

Steps that delete or replace characters come first and steps that insert spaces come last, so
that a later step never changes what an earlier step looked at. That is why clean_text is
idempotent: running it on its own output changes nothing. A test checks this on many random
strings.
"""

import re
import unicodedata

from src.normalise.checks import require_str
from src.normalise.patterns import BOUNDARY_AFTER, WORD_CHARS
from src.normalise.units import UNITS

TIMES_SIGN = "\u00d7"  # U+00D7, the multiplication sign
RIGHT_SINGLE_QUOTE = "\u2019"  # U+2019, the typographic apostrophe
ASCII_DIGITS = "0123456789"
_OPTIONAL_DOT = re.escape(".") + "?"


def _alternation(units: set[str]) -> str:
    """Return a regular-expression alternation of the units, longest first.

    The text is already in lower case when these patterns are used, and the Latin keys of the
    unit table are in lower case, so no case handling is needed here.
    """
    return "|".join(re.escape(unit) for unit in sorted(units, key=len, reverse=True))


# Every unit with its dots removed ("ltr." becomes "ltr").
_DOT_FREE_UNITS = {unit.replace(".", "") for unit in UNITS}
# The units written with a dot inside, such as the dotted Bangla abbreviations of kg and ml.
# Their final dot, if they have one, is optional.
_DOTTED_UNITS = {unit.rstrip(".") for unit in UNITS if "." in unit.rstrip(".")}

_TIMES_BETWEEN_DIGITS = re.compile(rf"(?<=[0-9])\s*[{TIMES_SIGN}*]\s*(?=[0-9])")
_THOUSANDS_COMMA = re.compile(r"(?<=[0-9]),(?=[0-9]{3}(?![0-9]))")
_DOTTED_UNIT = re.compile(
    rf"(?:(?<![{WORD_CHARS}])|(?<=[0-9]))(?:{_alternation(_DOTTED_UNITS)}){_OPTIONAL_DOT}"
    rf"{BOUNDARY_AFTER}"
)
_APOSTROPHE = re.compile(rf"(?<=[{WORD_CHARS}])['{RIGHT_SINGLE_QUOTE}](?=[{WORD_CHARS}])")
_X_BETWEEN_DIGITS = re.compile(r"(?<=[0-9])\s*x\s*(?=[0-9])")
_NUMBER_BEFORE_UNIT = re.compile(
    rf"(?<![{WORD_CHARS}])([0-9]+(?:\.[0-9]+)?)\s*({_alternation(_DOT_FREE_UNITS)}){BOUNDARY_AFTER}"
)


def _keep_letters_marks_and_numbers(text: str) -> str:
    """Replace everything except letters, marks, numbers and decimal points with a space."""
    kept = []
    for index, char in enumerate(text):
        is_decimal_point = (
            char == "."
            and 0 < index < len(text) - 1
            and text[index - 1] in ASCII_DIGITS
            and text[index + 1] in ASCII_DIGITS
        )
        if is_decimal_point or char == " " or unicodedata.category(char)[0] in "LMN":
            kept.append(char)
        else:
            kept.append(" ")
    return "".join(kept)


def clean_text(text: str) -> str:
    """Clean a title for comparison: spaces, case, punctuation and number-unit spacing.

    See the module description for the steps and their order.

    Args:
        text: The text to clean, already passed through clean_unicode and
            bangla_digits_to_ascii.

    Returns:
        The cleaned text. It is empty if the text had no letters, marks or numbers.

    Raises:
        TypeError: If text is not a str.
    """
    require_str(text)
    text = text.lower()
    text = _TIMES_BETWEEN_DIGITS.sub("x", text)
    text = _THOUSANDS_COMMA.sub("", text)
    text = _DOTTED_UNIT.sub(lambda match: match.group(0).replace(".", ""), text)
    text = _APOSTROPHE.sub("", text)
    text = _keep_letters_marks_and_numbers(text)
    text = _X_BETWEEN_DIGITS.sub(" x ", text)
    text = _NUMBER_BEFORE_UNIT.sub(lambda match: f"{match.group(1)} {match.group(2)}", text)
    return " ".join(text.split())
