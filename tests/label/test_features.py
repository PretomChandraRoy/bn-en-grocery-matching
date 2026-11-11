"""Tests for src.label.features.

All titles and values are invented. The expected similarities are worked out by hand in the
comments. Bangla text is built from code points (see tests/helpers.py).
"""

from decimal import Decimal

import pytest

from src.label.features import (
    char3_jaccard,
    format_decimal,
    format_total,
    name_tokens,
    ratio,
    size_ratio,
    size_relation,
    token_jaccard,
    token_overlap,
    total_amount,
    unit_price_ratio,
)
from src.normalise.sizes import SizeResult
from tests.helpers import bn

CHAL = bn(0x099A, 0x09BE, 0x09B2)  # চাল
BANGLA_ONE = bn(0x09E7)  # ১
KEJI = bn(0x0995, 0x09C7, 0x099C, 0x09BF)  # কেজি
ZERO_WIDTH_SPACE = bn(0x200B)


# The name tokens: a title without its size.


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        pytest.param("Test Rice 1kg", ("test", "rice"), id="size-at-the-end"),
        pytest.param("TEST RICE 1KG", ("test", "rice"), id="capitals"),
        pytest.param("Test Oil 2 x 500ml", ("test", "oil"), id="multipack"),
        pytest.param("Test Oil 2x500ml", ("test", "oil"), id="multipack-attached"),
        pytest.param("Gram Flour 1kg", ("gram", "flour"), id="a-unit-word-in-the-name"),
        pytest.param("Rice 1 kg 500 gm", ("rice",), id="two-sizes"),
        pytest.param("Dal 1,000gm", ("dal",), id="thousands-comma"),
        pytest.param("Dal 0.5 L", ("dal",), id="decimal"),
        pytest.param("Test Rice", ("test", "rice"), id="no-size"),
        pytest.param("Chilli Powder 500gm + 50gm Free", ("chilli", "powder", "free"), id="free"),
        pytest.param("7up 500ml", ("7up",), id="digit-inside-a-word-is-kept"),
        pytest.param("Dal kg 5", ("dal", "kg"), id="unit-before-the-number-is-kept"),
        pytest.param("Dal 5 lb", ("dal", "lb"), id="unknown-unit-is-kept"),
        pytest.param("Rice x 5", ("rice", "x"), id="x-before-a-number-is-kept"),
        pytest.param("Tin 2 x tin", ("tin", "x", "tin"), id="x-before-a-word-is-kept"),
        pytest.param("100 Pieces", ("pieces",), id="count-word"),
        pytest.param("1kg", (), id="size-only"),
        pytest.param("", (), id="empty"),
        pytest.param(f"{CHAL} {BANGLA_ONE} {KEJI}", (CHAL,), id="bangla-digit-and-unit"),
        pytest.param(
            f"Test{ZERO_WIDTH_SPACE} Rice 1kg", ("test", "rice"), id="invisible-character"
        ),
    ],
)
def test_name_tokens(title: str, expected: tuple[str, ...]) -> None:
    assert name_tokens(title) == expected


def test_the_same_name_gives_the_same_tokens_whatever_the_unit_spelling() -> None:
    assert name_tokens("Dal 500 gm") == name_tokens("Dal 500g") == name_tokens("DAL 500 GRAMS")


def test_name_tokens_rejects_other_types() -> None:
    with pytest.raises(TypeError):
        name_tokens(None)  # type: ignore[arg-type]


# The similarities, worked out by hand.


def test_token_jaccard_is_shared_over_all() -> None:
    # {a, b, c} and {b, c, d}: 2 shared of 4 in all.
    assert token_jaccard(("a", "b", "c"), ("b", "c", "d")) == Decimal("0.5000")


def test_token_overlap_is_shared_over_the_shorter() -> None:
    # {a, b, c} and {b, c, d}: 2 shared, and both sets have 3.
    assert token_overlap(("a", "b", "c"), ("b", "c", "d")) == Decimal("0.6667")
    # {a, b} is inside {a, b, c, d}: all of the shorter is shared.
    assert token_overlap(("a", "b"), ("a", "b", "c", "d")) == Decimal("1.0000")
    assert token_jaccard(("a", "b"), ("a", "b", "c", "d")) == Decimal("0.5000")


@pytest.mark.parametrize("function", [token_jaccard, token_overlap, char3_jaccard])
def test_identical_names_score_one(function) -> None:  # noqa: ANN001
    assert function(("test", "rice"), ("test", "rice")) == Decimal("1.0000")


@pytest.mark.parametrize("function", [token_jaccard, token_overlap, char3_jaccard])
def test_names_with_nothing_shared_score_zero(function) -> None:  # noqa: ANN001
    assert function(("abc",), ("xyz",)) == Decimal("0.0000")


@pytest.mark.parametrize("function", [token_jaccard, token_overlap, char3_jaccard])
def test_an_empty_name_scores_zero(function) -> None:  # noqa: ANN001
    assert function((), ("a",)) == Decimal("0.0000")
    assert function(("a",), ()) == Decimal("0.0000")
    assert function((), ()) == Decimal("0.0000")


@pytest.mark.parametrize("function", [token_jaccard, token_overlap, char3_jaccard])
def test_the_similarities_are_symmetric(function) -> None:  # noqa: ANN001
    left, right = ("basmati", "rice", "premium"), ("rice", "basmati", "aged", "extra")
    assert function(left, right) == function(right, left)


def test_repeated_tokens_count_once() -> None:
    assert token_jaccard(("a", "a", "b"), ("a", "b")) == Decimal("1.0000")


def test_char3_jaccard_tolerates_a_different_spelling() -> None:
    # "chilipowder" has 9 trigrams (chi hil ili lip ipo pow owd wde der); "chillipowder" has 10
    # (chi hil ill lli lip ipo pow owd wde der). 8 are shared and 11 are in all: 8/11.
    assert char3_jaccard(("chili", "powder"), ("chilli", "powder")) == Decimal("0.7273")
    assert token_jaccard(("chili", "powder"), ("chilli", "powder")) == Decimal("0.3333")


def test_char3_jaccard_tolerates_a_different_word_order() -> None:
    # "ricebasmati" and "basmatirice" have 9 trigrams each; 7 are shared and 11 are in all.
    assert char3_jaccard(("rice", "basmati"), ("basmati", "rice")) == Decimal("0.6364")
    assert token_jaccard(("rice", "basmati"), ("basmati", "rice")) == Decimal("1.0000")


def test_char3_jaccard_for_very_short_names() -> None:
    assert char3_jaccard(("ab",), ("ab",)) == Decimal("1.0000")
    assert char3_jaccard(("ab",), ("abc",)) == Decimal("0.0000")


def test_the_similarities_are_rounded_to_four_places() -> None:
    assert token_jaccard(("a",), ("a", "b", "c")) == Decimal("0.3333")
    assert token_jaccard(("a", "b"), ("a", "b", "c", "d", "e", "f")) == Decimal("0.3333")
    assert token_overlap(("a", "b", "c"), ("b", "c", "d")) == Decimal("0.6667")


# Sizes.


def size(
    kind: str = "weight", amount: str = "1000", count: int = 1, status: str = "ok"
) -> SizeResult:
    if status != "ok":
        return SizeResult(status, "no_size_found")  # type: ignore[arg-type]
    return SizeResult("ok", amount=Decimal(amount), kind=kind, pack_count=count)  # type: ignore[arg-type]


def test_total_amount_is_the_pack_size_times_the_pack_count() -> None:
    assert total_amount(size(amount="500", count=2)) == Decimal(1000)
    assert total_amount(size(amount="250")) == Decimal(250)


@pytest.mark.parametrize("status", ["missing", "ambiguous", "conflict"])
def test_total_amount_needs_a_size_that_was_read(status: str) -> None:
    with pytest.raises(ValueError, match="no amount"):
        total_amount(size(status=status))


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        pytest.param(size(), size(), "same", id="same"),
        pytest.param(size(amount="500", count=2), size(amount="500", count=2), "same", id="packs"),
        pytest.param(size(amount="500", count=2), size(), "same_total_different_pack", id="pack"),
        pytest.param(size(), size(amount="500", count=2), "same_total_different_pack", id="pack-2"),
        pytest.param(size(), size(amount="5000"), "different_amount", id="amount"),
        pytest.param(size(amount="500", count=2), size(amount="500"), "different_amount", id="n"),
        pytest.param(size(), size(kind="volume"), "different_kind", id="kind"),
        pytest.param(size(kind="volume"), size(), "different_kind", id="kind-2"),
        pytest.param(size(), size(status="missing"), "unknown", id="missing"),
        pytest.param(size(status="ambiguous"), size(), "unknown", id="ambiguous"),
        pytest.param(size(status="conflict"), size(status="missing"), "unknown", id="both"),
    ],
)
def test_size_relation(left: SizeResult, right: SizeResult, expected: str) -> None:
    assert size_relation(left, right) == expected


def test_a_different_kind_wins_over_a_different_amount() -> None:
    assert size_relation(size(amount="1"), size(kind="volume", amount="9")) == "different_kind"


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        pytest.param(size(), size(), Decimal("1.0000"), id="same"),
        pytest.param(size(amount="500"), size(), Decimal("0.5000"), id="half"),
        pytest.param(size(), size(amount="500"), Decimal("0.5000"), id="half-reversed"),
        pytest.param(size(amount="500", count=2), size(), Decimal("1.0000"), id="pack"),
        pytest.param(size(amount="1"), size(amount="3"), Decimal("0.3333"), id="third"),
        pytest.param(size(), size(kind="volume"), None, id="kinds"),
        pytest.param(size(), size(status="missing"), None, id="unknown"),
    ],
)
def test_size_ratio(left: SizeResult, right: SizeResult, expected: Decimal | None) -> None:
    assert size_ratio(left, right) == expected


# Prices.


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        (Decimal(2), Decimal(4), Decimal("0.5000")),
        (Decimal(4), Decimal(2), Decimal("0.5000")),
        (Decimal(7), Decimal(7), Decimal("1.0000")),
        (Decimal("1"), Decimal("32"), Decimal("0.0312")),  # 0.03125 rounds half to even
        (Decimal("3"), Decimal("32"), Decimal("0.0938")),  # 0.09375 rounds half to even
        (Decimal(0), Decimal(3), None),
        (Decimal(3), Decimal(0), None),
        (Decimal(-1), Decimal(3), None),
    ],
)
def test_ratio(first: Decimal, second: Decimal, expected: Decimal | None) -> None:
    assert ratio(first, second) == expected


def test_unit_price_ratio_compares_the_price_per_100_units() -> None:
    # 100 for 500 g is 20 per 100 g; 150 for 1000 g is 15 per 100 g; 15 / 20.
    result = unit_price_ratio(Decimal(100), size(amount="500"), Decimal(150), size())
    assert result == Decimal("0.7500")


def test_unit_price_ratio_uses_the_total_of_a_multipack() -> None:
    # 100 for 2 x 500 g is 10 per 100 g; 100 for 1000 g is also 10 per 100 g.
    result = unit_price_ratio(Decimal(100), size(amount="500", count=2), Decimal(100), size())
    assert result == Decimal("1.0000")


def test_unit_price_ratio_for_volumes() -> None:
    result = unit_price_ratio(Decimal(90), size(kind="volume"), Decimal(60), size(kind="volume"))
    assert result == Decimal("0.6667")


@pytest.mark.parametrize(
    ("left_price", "left", "right_price", "right"),
    [
        pytest.param(Decimal(1), size(), Decimal(1), size(kind="volume"), id="kinds-differ"),
        pytest.param(Decimal(1), size(), Decimal(1), size(status="missing"), id="size-unknown"),
        pytest.param(Decimal(0), size(), Decimal(1), size(), id="zero-price"),
        pytest.param(Decimal(1), size(), Decimal(-5), size(), id="negative-price"),
    ],
)
def test_unit_price_ratio_is_none_when_it_cannot_be_worked_out(
    left_price: Decimal, left: SizeResult, right_price: Decimal, right: SizeResult
) -> None:
    assert unit_price_ratio(left_price, left, right_price, right) is None


# Writing numbers.


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ""),
        (Decimal("0.5"), "0.5"),
        (Decimal("1.0000"), "1.0000"),
        (Decimal("0.0000"), "0.0000"),
        (Decimal("0E-4"), "0.0000"),
    ],
)
def test_format_decimal(value: Decimal | None, expected: str) -> None:
    assert format_decimal(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("1000"), "1000"),
        (Decimal("1000.0"), "1000"),
        (Decimal("5E+2"), "500"),
        (Decimal("12.50"), "12.5"),
        (Decimal("100000"), "100000"),
        (Decimal("0.5"), "0.5"),
    ],
)
def test_format_total(value: Decimal, expected: str) -> None:
    assert format_total(value) == expected
