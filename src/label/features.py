"""Features of a pair of listings: text similarity, size agreement and price proximity.

The candidate pair generator records these for every pair, so that the sampling strata can be
tried on real data. The validator for labelled files uses the size relation too, so that both
read the sizes in the same way.

Text similarity compares the names of the products, not their sizes. A title is first prepared
(prepare) and cleaned (clean_text, which also writes every unit as kg, g, l or ml). The numbers,
the units that follow them and the "x" of a multipack are then dropped, so that two titles with
the same size do not look similar because of the size alone. Size agreement is a feature of its
own. The words that are left are the "name tokens".

All ratios and similarities are Decimal values rounded to four places and written as text, so
that the same input always gives the same file on every machine.

The project's regular-expression rules apply: digits are matched with [0-9].
"""

import re
from collections.abc import Sequence
from decimal import Decimal
from typing import Literal

from src.normalise.prepare import prepare
from src.normalise.sizes import SizeResult
from src.normalise.text_clean import clean_text

SizeRelation = Literal[
    "same", "same_total_different_pack", "different_amount", "different_kind", "unknown"
]

_NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)?")
_UNIT_SYMBOLS = frozenset({"kg", "g", "l", "ml"})
_FOUR_PLACES = Decimal("0.0001")
_TRIGRAM = 3


def name_tokens(title_raw: str) -> tuple[str, ...]:
    """Return the words of a title that name the product, without its size.

    The title is prepared and cleaned (lower case, one unit symbol, single spaces). Then these
    tokens are dropped: every number, a unit symbol straight after a number, and an "x" between
    two numbers. A token such as "7up", which mixes letters and digits, is kept.

    Args:
        title_raw: The title as collected; it is not changed.

    Returns:
        The remaining tokens, in order. The tuple is empty if nothing is left.
    """
    tokens = clean_text(prepare(title_raw)).split()
    is_number = [bool(_NUMBER.fullmatch(token)) for token in tokens]
    kept = []
    for index, token in enumerate(tokens):
        after_number = index > 0 and is_number[index - 1]
        before_number = index + 1 < len(tokens) and is_number[index + 1]
        if is_number[index]:
            continue
        if token in _UNIT_SYMBOLS and after_number:
            continue
        if token == "x" and after_number and before_number:
            continue
        kept.append(token)
    return tuple(kept)


def _quantise(value: Decimal) -> Decimal:
    """Round to four places."""
    return value.quantize(_FOUR_PLACES)


def token_jaccard(left: Sequence[str], right: Sequence[str]) -> Decimal:
    """Return the Jaccard similarity of the two sets of tokens: shared over all.

    Args:
        left: The name tokens of one title.
        right: The name tokens of the other title.

    Returns:
        A value from 0 to 1, or 0 if either title has no tokens.
    """
    a, b = set(left), set(right)
    if not a or not b:
        return _quantise(Decimal(0))
    return _quantise(Decimal(len(a & b)) / Decimal(len(a | b)))


def token_overlap(left: Sequence[str], right: Sequence[str]) -> Decimal:
    """Return the overlap coefficient of the two sets of tokens: shared over the smaller set.

    It stays high when one shop drops brand-line words that the other keeps.

    Args:
        left: The name tokens of one title.
        right: The name tokens of the other title.

    Returns:
        A value from 0 to 1, or 0 if either title has no tokens.
    """
    a, b = set(left), set(right)
    if not a or not b:
        return _quantise(Decimal(0))
    return _quantise(Decimal(len(a & b)) / Decimal(min(len(a), len(b))))


def _trigrams(tokens: Sequence[str]) -> set[str]:
    """Return the character trigrams of the tokens joined without spaces."""
    text = "".join(tokens)
    if len(text) < _TRIGRAM:
        return {text} if text else set()
    return {text[i : i + _TRIGRAM] for i in range(len(text) - _TRIGRAM + 1)}


def char3_jaccard(left: Sequence[str], right: Sequence[str]) -> Decimal:
    """Return the Jaccard similarity of the character trigrams of the two names.

    The tokens are joined without spaces, so a different word order or a different spelling
    (Chili and Chilli) changes only some of the trigrams.

    Args:
        left: The name tokens of one title.
        right: The name tokens of the other title.

    Returns:
        A value from 0 to 1, or 0 if either title has no tokens.
    """
    a, b = _trigrams(left), _trigrams(right)
    if not a or not b:
        return _quantise(Decimal(0))
    return _quantise(Decimal(len(a & b)) / Decimal(len(a | b)))


def total_amount(size: SizeResult) -> Decimal:
    """Return the total of a size in grams or millilitres: the pack size times the pack count.

    Args:
        size: A SizeResult with the status "ok".

    Returns:
        The total.

    Raises:
        ValueError: If the size has no amount.
    """
    if size.amount is None:
        raise ValueError("the size has no amount; only a size with the status 'ok' has one")
    return size.amount * size.pack_count


def size_relation(left: SizeResult, right: SizeResult) -> SizeRelation:
    """Say how two sizes read by N3 compare.

    Sizes are compared by kind, then by total (so "2 x 500 g" has the same total as "1000 g"),
    then by pack count.

    Args:
        left: The size of the left listing.
        right: The size of the right listing.

    Returns:
        "unknown" if either status is not "ok"; "different_kind" for a weight and a volume;
        "different_amount" for different totals; "same_total_different_pack" for the same total
        in different pack counts; otherwise "same".
    """
    if left.status != "ok" or right.status != "ok":
        return "unknown"
    if left.kind != right.kind:
        return "different_kind"
    if total_amount(left) != total_amount(right):
        return "different_amount"
    if left.pack_count != right.pack_count:
        return "same_total_different_pack"
    return "same"


def ratio(first: Decimal, second: Decimal) -> Decimal | None:
    """Return the smaller of two positive numbers over the larger, rounded to four places.

    Args:
        first: One number.
        second: The other number.

    Returns:
        A value above 0 up to 1, or None if either number is not above 0.
    """
    if first <= 0 or second <= 0:
        return None
    small, large = sorted((first, second))
    return _quantise(small / large)


def size_ratio(left: SizeResult, right: SizeResult) -> Decimal | None:
    """Return the ratio of the two totals, or None unless both sizes are read and of one kind."""
    if size_relation(left, right) in ("unknown", "different_kind"):
        return None
    return ratio(total_amount(left), total_amount(right))


def unit_price_ratio(
    left_price: Decimal, left: SizeResult, right_price: Decimal, right: SizeResult
) -> Decimal | None:
    """Return the ratio of the prices per 100 g or 100 ml, or None if it cannot be worked out.

    It needs both sizes read and of one kind. A price that is not above 0 gives None, through
    ratio.
    """
    if size_relation(left, right) in ("unknown", "different_kind"):
        return None
    left_unit = left_price / total_amount(left) * 100
    right_unit = right_price / total_amount(right) * 100
    return ratio(left_unit, right_unit)


def format_decimal(value: Decimal | None) -> str:
    """Write a Decimal as plain text without an exponent; None becomes an empty string."""
    if value is None:
        return ""
    return format(value, "f")


def format_total(value: Decimal) -> str:
    """Write a total in grams or millilitres without trailing zeros, for example 1000 or 12.5."""
    return format(value.normalize(), "f")
