"""Size parsing: find the pack size of a listing and convert it to grams or millilitres.

parse_size reads the size from the shop's separate size fields and from the title, compares the
two, and returns a SizeResult. It never changes the title.

The input must already have been through clean_unicode and bangla_digits_to_ascii. The parser
recognises ASCII digits only, so Bangla digits passed in directly give "missing".

The project's regular-expression rules apply here: digits are matched with [0-9], word
boundaries use WORD_CHARS from patterns.py, and numbers become values only through Decimal.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from src.normalise.checks import require_str
from src.normalise.patterns import BOUNDARY_AFTER, WORD_CHARS
from src.normalise.units import UNITS, lookup_unit, unit_alternation

Status = Literal["ok", "missing", "ambiguous", "conflict"]
Kind = Literal["weight", "volume"]
Source = Literal["field", "title"]

# Reasons. A reason is set whenever the status is not "ok".
NO_SIZE_FOUND = "no_size_found"
FRACTION = "fraction"
COMMA_DECIMAL = "comma_decimal"
ZERO_AMOUNT = "zero_amount"
MULTIPLE_SIZES = "multiple_sizes"
MULTIPLE_MULTIPACKS = "multiple_multipacks"
UNREADABLE_FIELD = "unreadable_field"
FIELD_TITLE_CONFLICT = "field_title_conflict"
REASONS = (
    NO_SIZE_FOUND,
    FRACTION,
    COMMA_DECIMAL,
    ZERO_AMOUNT,
    MULTIPLE_SIZES,
    MULTIPLE_MULTIPACKS,
    UNREADABLE_FIELD,
    FIELD_TITLE_CONFLICT,
)

# The Bangla rupee sign (U+09F3). A number straight after it is a price, never a size.
RUPEE_SIGN = "\u09f3"
# Signs that mean "times" between a pack count and a size: x, X, the multiplication sign
# (U+00D7) and the asterisk.
MULTIPLY_SIGNS = "xX\u00d7*"
# The body of a character class holding the vulgar fractions: U+00BC to U+00BE, which include
# the half sign, and U+2150 to U+215E.
VULGAR_FRACTIONS = "\u00bc-\u00be\u2150-\u215e"


@dataclass(frozen=True)
class SizeResult:
    """The outcome of parsing the size of one listing.

    Attributes:
        status: "ok" if one size was found, "missing" if none was, "ambiguous" if the text
            cannot be read safely, or "conflict" if the size field and the title disagree.
        reason: Why the status is not "ok" (one of REASONS); empty for "ok".
        amount: The size of one pack in grams or millilitres, or None.
        kind: "weight" or "volume", or None.
        pack_count: The number of packs (2 for "2 x 500 gm"); 1 otherwise.
        source: Where the size came from, "field" or "title", or None.
        free_extra: True if the title announces a free extra quantity such as "+ 50 gm free".
            The extra is ignored; amount is the base size.
        matched_text: The exact text the result was parsed from. For a title it is the matched
            substring. For a size field it is the value and the unit joined by a space. When
            several pieces are involved they are joined by " | ". Empty if there is none.
    """

    status: Status
    reason: str = ""
    amount: Decimal | None = None
    kind: Kind | None = None
    pack_count: int = 1
    source: Source | None = None
    free_extra: bool = False
    matched_text: str = ""

    @property
    def total(self) -> Decimal | None:
        """The amount of all packs together (amount times pack_count), or None."""
        if self.amount is None:
            return None
        return self.amount * self.pack_count

    @property
    def amount_text(self) -> str:
        """The amount as plain text without an exponent or trailing zeros, or an empty string."""
        if self.amount is None:
            return ""
        return format(self.amount.normalize(), "f")


# Regular-expression pieces. Digits are matched with [0-9]; the unit table supplies the units.
_UNIT = unit_alternation()
_NUMBER = r"[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?"
# A number cannot start straight after a word character or the rupee sign, or after a digit
# and a "." "," or "/". The last rule stops "1,5 kg" being read as 5 kg and "1/2 kg" as 2 kg.
_LEFT = rf"(?<![{WORD_CHARS}{RUPEE_SIGN}])(?<![0-9][.,/])"

_FRACTION_SIZE = re.compile(
    rf"{_LEFT}(?:[0-9]+\s*)?(?:[0-9]+/[0-9]+|[{VULGAR_FRACTIONS}])\s*(?:{_UNIT}){BOUNDARY_AFTER}"
)
_COMMA_DECIMAL_SIZE = re.compile(
    rf"{_LEFT}[0-9]+,[0-9]{{1,2}}(?![0-9])\s*(?:{_UNIT}){BOUNDARY_AFTER}"
)
_MULTIPACK_FIRST = re.compile(
    rf"{_LEFT}(?P<count>[0-9]+)\s*[{MULTIPLY_SIGNS}]\s*(?P<num>{_NUMBER})\s*(?P<unit>{_UNIT})"
    rf"{BOUNDARY_AFTER}"
)
_MULTIPACK_LAST = re.compile(
    rf"{_LEFT}(?P<num>{_NUMBER})\s*(?P<unit>{_UNIT})\s*[{MULTIPLY_SIGNS}]\s*(?P<count>[0-9]+)"
    rf"(?![{WORD_CHARS}])"
)
_EXTRA = re.compile(rf"\+\s*(?P<num>{_NUMBER})\s*(?P<unit>{_UNIT}){BOUNDARY_AFTER}")
_SINGLE = re.compile(rf"{_LEFT}(?P<num>{_NUMBER})\s*(?P<unit>{_UNIT}){BOUNDARY_AFTER}")

# The patterns are tried in stages. A later stage ignores text already claimed by an earlier
# one, so "2 x 500 gm" is not also read as a plain "500 gm", and "+ 50 gm" is not read as a size.
_STAGES = (
    (("fraction", _FRACTION_SIZE),),
    (("comma_decimal", _COMMA_DECIMAL_SIZE),),
    (("multipack", _MULTIPACK_FIRST), ("multipack", _MULTIPACK_LAST)),
    (("extra", _EXTRA),),
    (("single", _SINGLE),),
)

_FIELD_NUMBER = re.compile(f"(?:{_NUMBER})")
_FIELD_FRACTION = re.compile(rf"(?:[0-9]+\s*)?(?:[0-9]+/[0-9]+|[{VULGAR_FRACTIONS}])")
_FIELD_COMMA_DECIMAL = re.compile(r"[0-9]+,[0-9]{1,2}")


@dataclass(frozen=True)
class _Match:
    """One piece of text found in a title."""

    form: str
    start: int
    end: int
    text: str
    amount: Decimal | None
    kind: Kind | None
    count: int


@dataclass(frozen=True)
class _Part:
    """What the title, or the size field, says on its own."""

    state: Literal["none", "ok", "ambiguous"]
    reason: str = ""
    amount: Decimal | None = None
    kind: Kind | None = None
    pack_count: int = 1
    matched_text: str = ""
    free_extra: bool = False
    extra_total: Decimal = Decimal(0)


def _whole_number(text: str) -> int:
    """Convert text matched by [0-9]+ to an int, through Decimal."""
    return int(Decimal(text))


def _to_match(form: str, found: re.Match[str]) -> _Match:
    """Turn a regular-expression match into a _Match with its amount in grams or millilitres."""
    groups = found.groupdict()
    amount = None
    kind = None
    count = 1
    if "num" in groups:
        unit = UNITS[groups["unit"].lower()]
        amount = Decimal(groups["num"].replace(",", "")) * unit.factor
        kind = unit.kind
    if "count" in groups:
        count = _whole_number(groups["count"])
    return _Match(form, found.start(), found.end(), found.group(0), amount, kind, count)


def _overlaps(start: int, end: int, claimed: list[tuple[int, int]]) -> bool:
    return any(
        start < claimed_end and claimed_start < end for claimed_start, claimed_end in claimed
    )


def _scan(title: str) -> list[_Match]:
    """Find every size-like piece of text in a title, in order of position."""
    found: list[_Match] = []
    claimed: list[tuple[int, int]] = []
    for stage in _STAGES:
        stage_matches = [
            _to_match(form, match)
            for form, pattern in stage
            for match in pattern.finditer(title)
            if not _overlaps(match.start(), match.end(), claimed)
        ]
        found.extend(stage_matches)
        claimed.extend((match.start, match.end) for match in stage_matches)
    return sorted(found, key=lambda match: match.start)


def _join(matches: list[_Match]) -> str:
    return " | ".join(match.text for match in matches)


def _distinct(sizes: list[_Match]) -> list[_Match]:
    """Keep the first of each size that has the same amount, kind and pack count."""
    first: dict[tuple[Decimal | None, Kind | None, int], _Match] = {}
    for size in sizes:
        first.setdefault((size.amount, size.kind, size.count), size)
    return list(first.values())


def _parse_title(title: str) -> _Part:
    """Read the size from a title."""
    found = _scan(title)
    for form, reason in (("fraction", FRACTION), ("comma_decimal", COMMA_DECIMAL)):
        flagged = [match for match in found if match.form == form]
        if flagged:
            return _Part("ambiguous", reason, matched_text=_join(flagged))
    sizes = [match for match in found if match.form in ("multipack", "single")]
    zeros = [match for match in sizes if match.amount == 0 or match.count == 0]
    if zeros:
        return _Part("ambiguous", ZERO_AMOUNT, matched_text=_join(zeros))
    distinct = _distinct(sizes)
    multipacks = [match for match in distinct if match.form == "multipack"]
    if len(multipacks) > 1:
        return _Part("ambiguous", MULTIPLE_MULTIPACKS, matched_text=_join(multipacks))
    if len(distinct) > 1:
        return _Part("ambiguous", MULTIPLE_SIZES, matched_text=_join(distinct))
    if not distinct:
        return _Part("none")
    base = distinct[0]
    extras = [match for match in found if match.form == "extra" and match.kind == base.kind]
    return _Part(
        "ok",
        amount=base.amount,
        kind=base.kind,
        pack_count=base.count,
        matched_text=base.text,
        free_extra=any(match.form == "extra" for match in found),
        extra_total=sum((match.amount or Decimal(0) for match in extras), Decimal(0)),
    )


def _parse_field(size_value: str, size_unit: str) -> _Part:
    """Read the size from the shop's separate value and unit fields."""
    value = size_value.strip()
    unit_text = size_unit.strip()
    if not value and not unit_text:
        return _Part("none")
    text = " ".join(part for part in (value, unit_text) if part)
    if not value or not unit_text:
        return _Part("ambiguous", UNREADABLE_FIELD, matched_text=text)
    if _FIELD_FRACTION.fullmatch(value):
        return _Part("ambiguous", FRACTION, matched_text=text)
    if _FIELD_COMMA_DECIMAL.fullmatch(value):
        return _Part("ambiguous", COMMA_DECIMAL, matched_text=text)
    unit = lookup_unit(unit_text)
    if unit is None or not _FIELD_NUMBER.fullmatch(value):
        return _Part("ambiguous", UNREADABLE_FIELD, matched_text=text)
    amount = Decimal(value.replace(",", "")) * unit.factor
    if amount == 0:
        return _Part("ambiguous", ZERO_AMOUNT, matched_text=text)
    return _Part("ok", amount=amount, kind=unit.kind, matched_text=text)


def _ok(part: _Part, source: Source) -> SizeResult:
    return SizeResult(
        "ok",
        "",
        part.amount,
        part.kind,
        part.pack_count,
        source,
        part.free_extra,
        part.matched_text,
    )


def _compare(title: _Part, field: _Part) -> SizeResult:
    """Combine a title size and a field size that were both read successfully."""
    if title.kind == field.kind and title.amount is not None and field.amount is not None:
        if title.pack_count == 1 and field.amount == title.amount:
            return SizeResult(
                "ok", "", field.amount, field.kind, 1, "field", title.free_extra, field.matched_text
            )
        if title.pack_count > 1 and field.amount in (
            title.amount,
            title.amount * title.pack_count,
        ):
            return _ok(title, "title")
        if (
            title.pack_count == 1
            and title.free_extra
            and field.amount == title.amount + title.extra_total
        ):
            return _ok(title, "title")
    return SizeResult(
        "conflict",
        FIELD_TITLE_CONFLICT,
        matched_text=f"{title.matched_text} | {field.matched_text}",
    )


def parse_size(title: str, size_value: str = "", size_unit: str = "") -> SizeResult:
    """Find the pack size of a listing and convert it to grams or millilitres.

    The size comes from the shop's separate size fields if they are filled in, and from the
    title. If both give a size they must agree. Text that cannot be read safely, such as a
    fraction or "1,5 kg", gives "ambiguous" and is never guessed.

    The text must already have been through clean_unicode and bangla_digits_to_ascii. Pass an
    empty string for a missing size field; the caller handles None and NaN.

    Args:
        title: The listing title.
        size_value: The shop's size value field (for example "500"), or an empty string.
        size_unit: The shop's size unit field (for example "gm"), or an empty string.

    Returns:
        The SizeResult.

    Raises:
        TypeError: If any argument is not a str.
    """
    require_str(title)
    require_str(size_value)
    require_str(size_unit)
    title_part = _parse_title(title)
    field_part = _parse_field(size_value, size_unit)
    if field_part.state == "ambiguous":
        return SizeResult("ambiguous", field_part.reason, matched_text=field_part.matched_text)
    if title_part.state == "ambiguous":
        return SizeResult("ambiguous", title_part.reason, matched_text=title_part.matched_text)
    if field_part.state == "none" and title_part.state == "none":
        return SizeResult("missing", NO_SIZE_FOUND)
    if field_part.state == "none":
        return _ok(title_part, "title")
    if title_part.state == "none":
        return _ok(field_part, "field")
    return _compare(title_part, field_part)
