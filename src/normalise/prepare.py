"""The first two normalisation steps, as one function: N1 (unicode clean-up) and N2 (digits).

Every step that reads a title, such as size parsing (N3) and text clean-up (N4), expects its
input to have been through these two steps. This module gives them one name, so that the
smoke report, the pair generator and the validator for labelled files all prepare titles in the
same way. The original title is never changed: the function returns a new string.
"""

from src.normalise.digits import bangla_digits_to_ascii
from src.normalise.unicode_clean import clean_unicode


def prepare(text: str) -> str:
    """Apply clean_unicode (N1) and then bangla_digits_to_ascii (N2).

    Args:
        text: A title or a size field, as collected.

    Returns:
        The prepared text.

    Raises:
        TypeError: If text is not a str.
    """
    return bangla_digits_to_ascii(clean_unicode(text))
