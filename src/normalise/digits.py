r"""Conversion of Bangla digits to ASCII digits.

Python treats every Unicode decimal digit as a digit. The regular-expression class \d matches
Bangla digits, and int(), float() and Decimal() accept them. To keep behaviour independent of
which digits appear in a title, the normalisation code follows these rules:

* This module converts the ten Bangla digits to ASCII digits, and nothing else.
* Regular expressions match digits with [0-9], never with \d. They do not use re.ASCII, because
  that flag also changes how Bangla letters are treated.
* Numbers are turned into values only with Decimal() on text already matched by [0-9].

Run this step after clean_unicode, so that invisible characters have already been removed.
"""

from src.normalise.checks import require_str

# The ten Bangla digits, zero to nine (U+09E6 to U+09EF), written as escapes so that each one
# is visible and reviewable in the source.
BANGLA_DIGITS = "\u09e6\u09e7\u09e8\u09e9\u09ea\u09eb\u09ec\u09ed\u09ee\u09ef"
ASCII_DIGITS = "0123456789"

# Maps each Bangla digit to the ASCII digit at the same position. Digits of other scripts (for
# example Devanagari or fullwidth digits) are deliberately left unchanged.
_TRANSLATION = str.maketrans(BANGLA_DIGITS, ASCII_DIGITS)


def bangla_digits_to_ascii(text: str) -> str:
    """Replace each Bangla digit with the ASCII digit of the same value.

    Every digit is converted wherever it appears, including inside numbers that mix Bangla and
    ASCII digits and inside words. Nothing else is changed: the Bangla rupee sign (U+09F3), the
    currency fraction signs (U+09F4 to U+09F9) and digits of other scripts stay as they are.

    Args:
        text: The string to convert.

    Returns:
        The string with Bangla digits replaced by ASCII digits.

    Raises:
        TypeError: If text is not a str.
    """
    require_str(text)
    return text.translate(_TRANSLATION)
