"""Tests for src.normalise.prepare. Strings are invented; Bangla is built from code points."""

import pytest

from src.normalise.digits import bangla_digits_to_ascii
from src.normalise.prepare import prepare
from src.normalise.unicode_clean import clean_unicode
from tests.helpers import bn

CHAL = bn(0x099A, 0x09BE, 0x09B2)  # চাল
BANGLA_FIVE_ZERO = bn(0x09EB, 0x09E6)  # ৫০
ZERO_WIDTH_SPACE = bn(0x200B)


def test_prepare_converts_bangla_digits_and_removes_invisible_characters() -> None:
    text = f"{CHAL} {BANGLA_FIVE_ZERO}{ZERO_WIDTH_SPACE}0 gm"
    assert prepare(text) == f"{CHAL} 500 gm"


def test_prepare_is_the_two_steps_in_order() -> None:
    text = f"Test{ZERO_WIDTH_SPACE} {BANGLA_FIVE_ZERO} kg"
    assert prepare(text) == bangla_digits_to_ascii(clean_unicode(text))


def test_prepare_leaves_plain_text_alone() -> None:
    assert prepare("Test Rice 1 kg") == "Test Rice 1 kg"
    assert prepare("") == ""


def test_prepare_does_not_change_case_or_spacing() -> None:
    assert prepare("  TEST  Rice ") == "  TEST  Rice "


@pytest.mark.parametrize("value", [None, 5, b"abc", ["a"]])
def test_prepare_rejects_other_types(value: object) -> None:
    with pytest.raises(TypeError):
        prepare(value)  # type: ignore[arg-type]
