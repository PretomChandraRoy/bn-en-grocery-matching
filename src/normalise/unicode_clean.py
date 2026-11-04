"""Unicode clean-up for listing titles.

These functions return a new string and never change their input. They are the first step in
building ``title_norm``; ``title_raw`` is always kept exactly as the shop displayed it.
"""

import unicodedata

# Invisible "format" characters (Unicode category Cf) that carry no meaning for matching.
# Each one is written as an escape so that it is visible and reviewable in the source.
#
# ZWJ (U+200D) and ZWNJ (U+200C) affect how Bangla conjuncts are displayed, so removing them
# can change how a word looks. That is acceptable here because the result is used only for
# matching (title_norm). title_raw keeps them.
INVISIBLE_CHARACTERS: frozenset[str] = frozenset(
    {
        "​",  # ZERO WIDTH SPACE
        "‌",  # ZERO WIDTH NON-JOINER (ZWNJ)
        "‍",  # ZERO WIDTH JOINER (ZWJ)
        "⁠",  # WORD JOINER
        "﻿",  # ZERO WIDTH NO-BREAK SPACE (byte-order mark)
        "­",  # SOFT HYPHEN
        "‎",  # LEFT-TO-RIGHT MARK
        "‏",  # RIGHT-TO-LEFT MARK
    }
)


def _require_str(value: object) -> None:
    """Raise a TypeError unless the value is a str.

    Args:
        value: The value to check.

    Raises:
        TypeError: If value is not a str.
    """
    if not isinstance(value, str):
        raise TypeError(f"expected str, got {type(value).__name__}")


def remove_invisible(text: str) -> str:
    """Remove the invisible characters listed in INVISIBLE_CHARACTERS.

    Args:
        text: The string to clean.

    Returns:
        The string without any invisible characters.

    Raises:
        TypeError: If text is not a str.
    """
    _require_str(text)
    return "".join(char for char in text if char not in INVISIBLE_CHARACTERS)


def clean_unicode(text: str) -> str:
    """Remove invisible characters, then convert the string to Unicode NFC.

    The order matters. An invisible character between the parts of a Bangla letter stops NFC
    from joining them: ে, ZWNJ and া stay as three characters under NFC alone, but become the
    single vowel sign ো once the ZWNJ has been removed first.

    NFC also turns the precomposed letters য় (U+09DF), ড় (U+09DC) and ঢ় (U+09DD) into the
    base letter followed by the nukta sign (U+09BC), so both ways of typing them give the same
    result.

    Args:
        text: The string to clean.

    Returns:
        The cleaned string in NFC form.

    Raises:
        TypeError: If text is not a str.
    """
    return unicodedata.normalize("NFC", remove_invisible(text))
