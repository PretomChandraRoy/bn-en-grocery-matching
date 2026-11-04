r"""Shared regular-expression building blocks for the normalisation steps.

Python's \w and \b do not treat Bangla vowel signs as word characters, so they split a single
Bangla word into pieces. The normalisation code therefore never uses them. Instead, every step
imports the one definition below: WORD_CHARS is the set of characters that can be part of a
word, and word boundaries are written as lookarounds on that set.

tests/test_source_policy.py enforces that the source code does not use \w, \b or re.ASCII.
"""

# The body of a character class (the text between [ and ]) holding every character that can be
# part of a word: Latin letters and digits, plus all Bangla letters, vowel signs and other
# marks, and digits (U+0980 to U+09F1, U+09FC and U+09FE). The Bangla currency signs and
# fraction signs (U+09F2 to U+09FB) and U+09FD are deliberately left out, so they count as
# separators.
WORD_CHARS = "A-Za-z0-9ঀ-ৱৼ৾"

# Lookarounds that succeed where the neighbouring character is not a word character, or where
# the string starts (BOUNDARY_BEFORE) or ends (BOUNDARY_AFTER).
BOUNDARY_BEFORE = f"(?<![{WORD_CHARS}])"
BOUNDARY_AFTER = f"(?![{WORD_CHARS}])"


def bounded(pattern: str) -> str:
    """Wrap a pattern so that it only matches a whole word or phrase.

    The match must not be directly preceded or followed by a word character. Because digits are
    word characters, "kg" does not match inside "1kg"; patterns that must match straight after
    a number build their own left-hand side instead.

    Args:
        pattern: The regular-expression text to wrap. It is grouped, so alternatives are safe.

    Returns:
        The pattern with a boundary on each side.
    """
    return f"{BOUNDARY_BEFORE}(?:{pattern}){BOUNDARY_AFTER}"
