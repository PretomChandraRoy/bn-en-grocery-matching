"""Tests for src.label.validate.

All listings and labels are invented (see tests/label/builders.py). The invented listings are
written to a scratch data/raw folder, so no real data is read.
"""

import codecs
from decimal import Decimal
from pathlib import Path

import pytest

from src.collect.validate import COLUMNS
from src.label.records import LABEL_COLUMNS, SKIPPED_COLUMNS
from src.label.validate import (
    Context,
    FileResult,
    load_context,
    main,
    n3_disagreements,
    validate_file,
    validate_files,
)
from src.normalise.sizes import SizeResult
from tests.label.builders import (
    FIRST_TIME,
    NOW,
    SECOND_TIME,
    csv_bytes,
    label_file,
    label_row,
    listing_row,
    pair,
    write_guidelines,
    write_raw,
)


def make_context(tmp_path: Path, candidates: list[str] | None = None) -> Context:
    raw = write_raw(tmp_path / "raw")
    guidelines = write_guidelines(tmp_path)
    path = tmp_path / "candidates.csv"
    if candidates is not None:
        path.write_bytes(csv_bytes(("pair_id", "category"), [[c, "rice"] for c in candidates]))
    return load_context(raw_dir=raw, candidates_path=path, guidelines_path=guidelines, now=NOW)


def validate(
    tmp_path: Path,
    content: bytes,
    name: str = "labels_L1.csv",
    candidates: list[str] | None = None,
) -> FileResult:
    path = tmp_path / "labelled" / name
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(content)
    return validate_file(path, make_context(tmp_path, candidates))


def errors(result: FileResult) -> list[str]:
    return [problem.describe() for problem in result.errors]


def warnings(result: FileResult) -> list[str]:
    return [problem.describe() for problem in result.warnings]


def validate_rows(tmp_path: Path, *rows: dict[str, str], **kwargs) -> FileResult:  # noqa: ANN003
    return validate(tmp_path, label_file(list(rows)), **kwargs)


# A valid file.


def test_a_valid_file_has_no_problems(tmp_path: Path) -> None:
    result = validate_rows(
        tmp_path,
        label_row("1001", "2001"),
        label_row("1001", "2002", "non_match", "size_differs", labelled_at=SECOND_TIME),
    )
    assert result.problems == []
    assert result.row_count == 2
    assert result.kind == "labels"
    assert result.labeller == "L1"
    assert result.current == {pair("1001", "2001"): "match", pair("1001", "2002"): "non_match"}
    assert dict(result.versions) == {"0.2": 2}


def test_a_cross_script_pair_with_its_tag_is_valid(tmp_path: Path) -> None:
    result = validate_rows(tmp_path, label_row("1005", "2001", "match", "cross_script"))
    assert result.problems == []


def test_a_file_for_another_labeller_is_valid(tmp_path: Path) -> None:
    row = label_row(labeller="L2")
    assert validate(tmp_path, label_file([row]), name="labels_L2.csv").problems == []


# Encoding, structure and the file name.


def test_a_byte_order_mark_is_an_error(tmp_path: Path) -> None:
    result = validate(tmp_path, codecs.BOM_UTF8 + label_file([label_row()]))
    assert len(result.errors) == 1
    assert "byte-order mark" in errors(result)[0]


def test_invalid_utf8_is_an_error(tmp_path: Path) -> None:
    content = label_file([label_row(note="# a")]).replace(b"# a", b"# \xff")
    assert "not valid UTF-8" in errors(validate(tmp_path, content))[0]


def test_an_empty_file_is_an_error(tmp_path: Path) -> None:
    assert errors(validate(tmp_path, b"")) == ["error: the file is empty"]


def test_a_file_with_only_a_header_is_a_warning(tmp_path: Path) -> None:
    result = validate(tmp_path, label_file([]))
    assert result.errors == []
    assert warnings(result) == ["warning: the file has a header but no rows"]


@pytest.mark.parametrize(
    "header",
    [
        pytest.param([LABEL_COLUMNS[1], LABEL_COLUMNS[0], *LABEL_COLUMNS[2:]], id="swapped"),
        pytest.param(list(LABEL_COLUMNS[:-1]), id="a-column-missing"),
        pytest.param([*LABEL_COLUMNS, "extra"], id="an-extra-column"),
        pytest.param([column.upper() for column in LABEL_COLUMNS], id="upper-case"),
    ],
)
def test_the_header_must_be_exactly_the_label_columns(tmp_path: Path, header: list[str]) -> None:
    result = validate(tmp_path, csv_bytes(tuple(header), [["x"] * len(header)]))
    assert len(result.errors) == 1
    assert "(row 1)" in errors(result)[0]
    assert "the header must be exactly" in errors(result)[0]


def test_a_row_with_the_wrong_number_of_fields_is_an_error(tmp_path: Path) -> None:
    short = [label_row()[column] for column in LABEL_COLUMNS[:-1]]
    result = validate(tmp_path, csv_bytes(LABEL_COLUMNS, [short]))
    assert errors(result) == ["error (row 2): the row has 9 fields; expected 10"]


def test_an_empty_row_is_an_error(tmp_path: Path) -> None:
    content = label_file([label_row()]) + b"\n" + label_file([label_row()]).split(b"\n", 1)[1]
    result = validate(tmp_path, content)
    assert "error (row 3): the row is empty" in errors(result)


@pytest.mark.parametrize("name", ["labels.csv", "labels_L1.txt", "data.csv", "label_L1.csv"])
def test_the_file_name_must_be_labels_or_skipped_with_a_labeller(tmp_path: Path, name: str) -> None:
    result = validate(tmp_path, label_file([label_row()]), name=name)
    assert errors(result) == [
        "error: the name must be labels_<labeller>.csv or skipped_<labeller>.csv"
    ]


@pytest.mark.parametrize("labeller", ["pretom", "l1", "L", "L1x"])
def test_the_labeller_in_the_file_name_must_be_l_and_digits(tmp_path: Path, labeller: str) -> None:
    result = validate(tmp_path, label_file([label_row()]), name=f"labels_{labeller}.csv")
    assert any("in the file name must be L and digits" in message for message in errors(result))


@pytest.mark.parametrize("name", ["adjudication.csv", "overlap_sample.csv"])
def test_adjudication_and_overlap_files_are_not_checked_yet(tmp_path: Path, name: str) -> None:
    result = validate(tmp_path, b"anything", name=name)
    assert result.kind == "later"
    assert result.problems == []


# Required fields.


@pytest.mark.parametrize("column", [c for c in LABEL_COLUMNS if c != "note"])
def test_a_required_field_must_not_be_empty(tmp_path: Path, column: str) -> None:
    row = label_row()
    row[column] = ""
    result = validate_rows(tmp_path, row)
    assert f"error (row 2, {column}): is empty" in errors(result)


def test_the_note_may_be_empty(tmp_path: Path) -> None:
    assert validate_rows(tmp_path, label_row(note="")).problems == []


# pair_id.


@pytest.mark.parametrize(
    "pair_id",
    ["garbage", "meenabazar:2001", "meenabazar:2001 | pandamart:1001", "a:1|b:2|c:3"],
)
def test_a_malformed_pair_id_is_an_error(tmp_path: Path, pair_id: str) -> None:
    result = validate_rows(tmp_path, label_row(pair_id=pair_id))
    assert any(
        message.startswith("error (row 2, pair_id)") and "must have the form" in message
        for message in errors(result)
    )


def test_the_listings_must_be_in_the_required_order(tmp_path: Path) -> None:
    row = label_row(
        pair_id="pandamart:1001|meenabazar:2001",
        left_source="pandamart",
        left_id="1001",
        right_source="meenabazar",
        right_id="2001",
    )
    assert errors(validate_rows(tmp_path, row)) == [
        "error (row 2, pair_id): the listings are not in the required order; "
        "it must be meenabazar:2001|pandamart:1001"
    ]


def test_a_pair_from_one_source_is_an_error(tmp_path: Path) -> None:
    row = label_row(
        pair_id="pandamart:1001|pandamart:1002",
        left_source="pandamart",
        left_id="1001",
        right_source="pandamart",
        right_id="1002",
    )
    assert errors(validate_rows(tmp_path, row)) == [
        "error (row 2, pair_id): both listings are from the same source; a pair is across two shops"
    ]


def test_a_listing_that_is_not_in_data_raw_is_an_error(tmp_path: Path) -> None:
    result = validate_rows(tmp_path, label_row("1001", "9999"))
    assert errors(result) == [
        "error (row 2, pair_id): the listing meenabazar:9999 is not in data/raw"
    ]
    both = validate_rows(tmp_path, label_row("8888", "9999"))
    assert len(both.errors) == 2


@pytest.mark.parametrize(
    ("column", "expected"),
    [
        ("left_source", "meenabazar"),
        ("left_id", "2001"),
        ("right_source", "pandamart"),
        ("right_id", "1001"),
    ],
)
def test_the_four_id_columns_must_agree_with_pair_id(
    tmp_path: Path, column: str, expected: str
) -> None:
    result = validate_rows(tmp_path, label_row(**{column: "x1"}))
    assert errors(result) == [f"error (row 2, {column}): is 'x1', but pair_id says {expected!r}"]


def test_a_labelled_pair_must_be_in_candidates_when_that_file_exists(tmp_path: Path) -> None:
    candidates = [pair("1001", "2001")]
    ok = validate_rows(tmp_path, label_row("1001", "2001"), candidates=candidates)
    assert ok.problems == []
    result = validate_rows(
        tmp_path, label_row("1001", "2002", "non_match", "size_differs"), candidates=candidates
    )
    assert errors(result) == ["error (row 2, pair_id): the pair is not in candidates.csv"]


def test_an_empty_candidates_file_has_no_candidates(tmp_path: Path) -> None:
    result = validate_rows(tmp_path, label_row(), candidates=[])
    assert errors(result) == ["error (row 2, pair_id): the pair is not in candidates.csv"]


def test_without_a_candidates_file_the_check_is_skipped(tmp_path: Path) -> None:
    assert validate_rows(tmp_path, label_row(), candidates=None).problems == []


# label, note and tags.


def test_an_unknown_label_is_an_error_in_the_label_column(tmp_path: Path) -> None:
    result = validate_rows(tmp_path, label_row(label="maybe"))
    assert errors(result) == [
        "error (row 2, label): 'maybe' is not one of match, non_match, unsure"
    ]


@pytest.mark.parametrize(
    "tag", ["size_differs", "variant_differs", "brand_differs", "unit_kind_differs"]
)
@pytest.mark.parametrize("label", ["match", "unsure"])
def test_a_difference_tag_needs_non_match(tmp_path: Path, tag: str, label: str) -> None:
    result = validate_rows(tmp_path, label_row("1006", "2006", label, tag))
    assert any(
        message.startswith("error (row 2, note)") and f"the tag {tag} requires" in message
        for message in errors(result)
    )


def test_brand_missing_needs_unsure_or_non_match(tmp_path: Path) -> None:
    assert validate_rows(tmp_path, label_row(label="match", note="brand_missing")).errors
    assert validate_rows(tmp_path, label_row(label="unsure", note="brand_missing")).errors == []
    non_match = label_row(label="non_match", note="brand_missing")
    assert validate_rows(tmp_path, non_match).errors == []


def test_an_unknown_tag_is_an_error(tmp_path: Path) -> None:
    result = validate_rows(tmp_path, label_row(note="unbranded;nonsense"))
    assert len(result.errors) == 1
    assert "(row 2, note): 'nonsense' is not a tag" in errors(result)[0]


def test_a_repeated_tag_is_an_error(tmp_path: Path) -> None:
    result = validate_rows(tmp_path, label_row(note="unbranded;unbranded"))
    assert errors(result) == ["error (row 2, note): the tag unbranded appears twice"]


@pytest.mark.parametrize("note", ["unbranded; multipack", "unbranded;", ";unbranded", "unbranded "])
def test_a_malformed_note_is_an_error(tmp_path: Path, note: str) -> None:
    result = validate_rows(tmp_path, label_row(note=note))
    assert any(message.startswith("error (row 2, note)") for message in errors(result))


@pytest.mark.parametrize(
    "note", ["# same oil", "unbranded # same oil", "unbranded;multipack # two"]
)
def test_a_comment_after_the_tags_or_alone_is_valid(tmp_path: Path, note: str) -> None:
    result = validate_rows(
        tmp_path, label_row("1003", "2003", "non_match", note.replace("two", "x"))
    )
    assert result.errors == []


def test_a_comment_alone_must_start_with_a_hash_and_a_space(tmp_path: Path) -> None:
    result = validate_rows(tmp_path, label_row(note=" # same oil"))
    assert "a note with only a comment must start with '# '" in errors(result)[0]


# cross_script.


def test_cross_script_is_required_when_exactly_one_title_has_bangla(tmp_path: Path) -> None:
    result = validate_rows(tmp_path, label_row("1005", "2001", "match", ""))
    assert errors(result) == [
        "error (row 2, note): the tag cross_script is missing: exactly one title has Bangla letters"
    ]


@pytest.mark.parametrize("ids", [("1001", "2001"), ("1001", "2002")])
def test_cross_script_must_not_be_present_without_a_bangla_title(
    tmp_path: Path, ids: tuple[str, str]
) -> None:
    label = "match" if ids == ("1001", "2001") else "non_match"
    note = "cross_script" if label == "match" else "size_differs;cross_script"
    result = validate_rows(tmp_path, label_row(*ids, label, note))
    assert errors(result) == [
        "error (row 2, note): the tag cross_script is present, "
        "but not exactly one title has Bangla letters"
    ]


# labeller.


def test_the_labeller_must_match_the_file_name(tmp_path: Path) -> None:
    result = validate_rows(tmp_path, label_row(labeller="L2"))
    assert errors(result) == ["error (row 2, labeller): is 'L2', but the file is labels_L1.csv"]


def test_the_id_columns_are_checked_even_when_the_pair_is_not_sound(tmp_path: Path) -> None:
    # Listing 9999 does not exist, and left_id disagrees with pair_id: both are reported.
    result = validate_rows(tmp_path, label_row("1001", "9999", left_id="x1"))
    assert errors(result) == [
        "error (row 2, pair_id): the listing meenabazar:9999 is not in data/raw",
        "error (row 2, left_id): is 'x1', but pair_id says '9999'",
    ]


def test_the_labeller_column_must_be_l_and_digits_when_the_file_name_is_not(tmp_path: Path) -> None:
    row = label_row(labeller="pretom")
    result = validate(tmp_path, label_file([row]), name="labels_pretom.csv")
    assert errors(result) == [
        "error: the labeller 'pretom' in the file name must be L and digits",
        "error (row 2, labeller): 'pretom' must be L and digits",
    ]


# labelled_at.


@pytest.mark.parametrize(
    "value",
    ["2026-11-10 10:00:00+06:00", "2026-11-10T10:00:00", "2026-11-10T10:00:00Z", "10/11/2026", "x"],
)
def test_labelled_at_must_have_the_agreed_form(tmp_path: Path, value: str) -> None:
    result = validate_rows(tmp_path, label_row(labelled_at=value))
    assert len(result.errors) == 1
    assert "(row 2, labelled_at)" in errors(result)[0]
    assert "must have the form" in errors(result)[0]


def test_labelled_at_must_be_a_real_time(tmp_path: Path) -> None:
    result = validate_rows(tmp_path, label_row(labelled_at="2026-02-30T10:00:00+06:00"))
    assert "not a real date and time" in errors(result)[0]


def test_labelled_at_must_not_be_in_the_future(tmp_path: Path) -> None:
    # NOW is 12:00 UTC on 12 November, which is 18:00 at +06:00.
    late = validate_rows(tmp_path, label_row(labelled_at="2026-11-12T18:30:00+06:00"))
    assert "is in the future" in errors(late)[0]
    ok = validate_rows(tmp_path, label_row(labelled_at="2026-11-12T17:30:00+06:00"))
    assert ok.errors == []


def test_a_row_must_not_be_earlier_than_the_row_above(tmp_path: Path) -> None:
    result = validate_rows(
        tmp_path,
        label_row("1001", "2001", labelled_at=SECOND_TIME),
        label_row("1001", "2002", "non_match", "size_differs", labelled_at=FIRST_TIME),
    )
    assert errors(result) == [
        "error (row 3, labelled_at): labelled_at is earlier than the row above it"
    ]


def test_equal_times_are_in_order(tmp_path: Path) -> None:
    result = validate_rows(
        tmp_path,
        label_row("1001", "2001", labelled_at=FIRST_TIME),
        label_row("1001", "2002", "non_match", "size_differs", labelled_at=FIRST_TIME),
    )
    assert result.problems == []


def test_the_order_is_by_moment_not_by_text(tmp_path: Path) -> None:
    # 10:00 at +06:00 is 04:00 UTC; 06:00 at +00:00 is later, although its text sorts earlier.
    result = validate_rows(
        tmp_path,
        label_row("1001", "2001", labelled_at="2026-11-10T10:00:00+06:00"),
        label_row(
            "1001", "2002", "non_match", "size_differs", labelled_at="2026-11-10T06:00:00+00:00"
        ),
    )
    assert result.errors == []


def test_a_row_is_compared_with_the_latest_valid_row_above_it(tmp_path: Path) -> None:
    result = validate_rows(
        tmp_path,
        label_row("1001", "2001", labelled_at=SECOND_TIME),
        label_row("1001", "2002", "non_match", "size_differs", labelled_at="bad"),
        label_row("1006", "2006", "non_match", "unit_kind_differs", labelled_at=FIRST_TIME),
    )
    assert len(result.errors) == 2
    assert "(row 3, labelled_at)" in errors(result)[0]
    assert "(row 4, labelled_at): labelled_at is earlier" in errors(result)[1]


# guidelines_version.


def test_the_version_must_be_in_the_version_history(tmp_path: Path) -> None:
    result = validate_rows(tmp_path, label_row(version="0.3"))
    assert errors(result) == [
        "error (row 2, guidelines_version): '0.3' is not in the version history "
        "of the guidelines (0.1, 0.2)"
    ]


def test_an_earlier_version_in_the_history_is_valid(tmp_path: Path) -> None:
    result = validate_rows(tmp_path, label_row(version="0.1"))
    assert result.problems == []
    assert dict(result.versions) == {"0.1": 1}


# Several rows for one pair.


def test_a_correction_adds_a_row_and_the_latest_row_is_current(tmp_path: Path) -> None:
    result = validate_rows(
        tmp_path,
        label_row("1001", "2001", "unsure", "brand_missing", labelled_at=FIRST_TIME),
        label_row("1001", "2001", "match", "", labelled_at=SECOND_TIME),
    )
    assert result.problems == []
    assert result.current == {pair("1001", "2001"): "match"}


def test_a_row_that_repeats_the_one_above_for_its_pair_is_a_warning(tmp_path: Path) -> None:
    result = validate_rows(
        tmp_path,
        label_row("1001", "2001", labelled_at=FIRST_TIME),
        label_row("1001", "2002", "non_match", "size_differs", labelled_at=FIRST_TIME),
        label_row("1001", "2001", labelled_at=SECOND_TIME),
    )
    assert result.errors == []
    assert warnings(result) == [
        "warning (row 4, pair_id): repeats row 2 (same label, note and version)"
    ]


def test_a_row_with_a_new_version_is_not_a_repeat(tmp_path: Path) -> None:
    result = validate_rows(
        tmp_path,
        label_row(version="0.1", labelled_at=FIRST_TIME),
        label_row(version="0.2", labelled_at=SECOND_TIME),
    )
    assert result.problems == []


# Warnings from the reading of the sizes by N3.


@pytest.mark.parametrize(
    ("ids", "label", "note", "expected"),
    [
        pytest.param(("1001", "2001"), "match", "", None, id="equal-sizes-match"),
        pytest.param(("1001", "2002"), "non_match", "size_differs", None, id="different-sizes"),
        pytest.param(
            ("1006", "2006"), "non_match", "unit_kind_differs", None, id="different-kinds"
        ),
        pytest.param(("1003", "2003"), "non_match", "multipack", None, id="multipack"),
        pytest.param(("1004", "2004"), "match", "promo_quantity", None, id="promo"),
        pytest.param(("1005", "2001"), "match", "cross_script", None, id="bangla-title"),
        pytest.param(
            ("1001", "2002"),
            "match",
            "",
            "N3 reads 5000 g and 1000 g (different sizes), but the label is match",
            id="match-with-different-sizes",
        ),
        pytest.param(
            ("1001", "2002"),
            "non_match",
            "",
            "but the tag size_differs is missing",
            id="size_differs-missing",
        ),
        pytest.param(
            ("1001", "2001"),
            "non_match",
            "size_differs",
            "the tag size_differs is present, but N3 reads 1000 g and 1000 g (equal)",
            id="size_differs-without-a-difference",
        ),
        pytest.param(
            ("1006", "2006"),
            "non_match",
            "size_differs",
            "the tag size_differs is present, but N3 reads 1000 g and 1000 ml (of different kinds)",
            id="size_differs-for-different-kinds",
        ),
        pytest.param(
            ("1006", "2006"),
            "non_match",
            "",
            "(of different kinds), but the tag unit_kind_differs is missing",
            id="unit_kind_differs-missing",
        ),
        pytest.param(
            ("1001", "2001"),
            "non_match",
            "unit_kind_differs",
            "the tag unit_kind_differs is present, but N3 reads 1000 g and 1000 g (equal)",
            id="unit_kind_differs-without-a-difference",
        ),
        pytest.param(
            ("1003", "2003"),
            "match",
            "multipack",
            "(the same size in different packs), but the label is match",
            id="match-with-different-packs",
        ),
        pytest.param(
            ("1003", "2003"),
            "non_match",
            "",
            "N3 reads a title as having multipack, but the tag is missing",
            id="multipack-missing",
        ),
        pytest.param(
            ("1001", "2001"),
            "match",
            "multipack",
            "the tag multipack is present, but N3 reads neither title as having it",
            id="multipack-without-a-multipack",
        ),
        pytest.param(
            ("1004", "2004"),
            "match",
            "",
            "N3 reads a title as having promo_quantity, but the tag is missing",
            id="promo-missing",
        ),
        pytest.param(
            ("1001", "2001"),
            "match",
            "promo_quantity",
            "the tag promo_quantity is present, but N3 reads neither title as having it",
            id="promo-without-a-promo",
        ),
    ],
)
def test_n3_disagreements_are_warnings_only(
    tmp_path: Path, ids: tuple[str, str], label: str, note: str, expected: str | None
) -> None:
    note = (
        f"{note};cross_script".strip(";")
        if ids[0] == "1005" and "cross_script" not in note
        else note
    )
    result = validate_rows(tmp_path, label_row(*ids, label, note))
    assert result.errors == []
    if expected is None:
        assert result.warnings == []
    else:
        assert any(expected in message for message in warnings(result)), warnings(result)


def test_no_size_warning_when_n3_cannot_read_a_size(tmp_path: Path) -> None:
    # Listing 1008 has no size in its title, so N3 gives "missing" and nothing can be compared.
    result = validate_rows(tmp_path, label_row("1008", "2002", "match"))
    assert result.problems == []
    result = validate_rows(tmp_path, label_row("1008", "2002", "non_match", "size_differs"))
    assert result.problems == []


# The comparison with N3 itself, without files.


def size(
    kind: str = "weight",
    amount: str = "1000",
    count: int = 1,
    free: bool = False,
    status: str = "ok",
) -> SizeResult:
    if status != "ok":
        return SizeResult(status, "no_size_found")  # type: ignore[arg-type]
    return SizeResult(
        "ok",
        amount=Decimal(amount),
        kind=kind,
        pack_count=count,
        free_extra=free,  # type: ignore[arg-type]
    )


def test_equal_totals_in_the_same_kind_are_equal() -> None:
    assert n3_disagreements("match", [], size(), size()) == []
    two = size(amount="500", count=2)
    assert n3_disagreements("match", ["multipack"], two, two) == []


def test_a_multipack_with_the_same_total_differs_only_as_a_pack() -> None:
    messages = n3_disagreements("non_match", ["multipack"], size(amount="500", count=2), size())
    assert messages == []
    messages = n3_disagreements("match", ["multipack"], size(amount="500", count=2), size())
    assert messages == [
        "N3 reads 2 x 500 g and 1000 g (the same size in different packs), but the label is match"
    ]


def test_the_total_is_used_for_the_size_difference() -> None:
    messages = n3_disagreements("non_match", [], size(amount="500", count=2), size(amount="500"))
    assert messages == [
        "N3 reads 2 x 500 g and 500 g (different sizes), but the tag size_differs is missing",
        "N3 reads a title as having multipack, but the tag is missing",
    ]


@pytest.mark.parametrize("status", ["missing", "ambiguous", "conflict"])
def test_a_size_that_is_not_ok_gives_no_warning(status: str) -> None:
    bad = size(status=status)
    assert n3_disagreements("match", [], bad, size()) == []
    assert n3_disagreements("non_match", ["size_differs", "multipack"], size(), bad) == []


def test_a_multipack_is_noticed_even_when_the_other_size_is_not_ok() -> None:
    messages = n3_disagreements("non_match", [], size(count=2), size(status="missing"))
    assert messages == ["N3 reads a title as having multipack, but the tag is missing"]
    # but a tag cannot be called unsupported when one of the sizes was not read
    assert n3_disagreements("non_match", ["multipack"], size(), size(status="missing")) == []


def test_the_amount_is_written_without_a_trailing_exponent() -> None:
    messages = n3_disagreements("match", [], size(amount="50000"), size(amount="100"))
    assert "N3 reads 50000 g and 100 g" in messages[0]


# Skipped files.


def skipped_file(rows: list[dict[str, str]]) -> bytes:
    return csv_bytes(SKIPPED_COLUMNS, rows)


def skipped_row(pair_id: str | None = None, **changes: str) -> dict[str, str]:
    row = {
        "pair_id": pair("1001", "2001") if pair_id is None else pair_id,
        "reason": "bundle of different products",
        "skipped_at": FIRST_TIME,
    }
    row.update(changes)
    return row


def test_a_valid_skipped_file_has_no_problems(tmp_path: Path) -> None:
    rows = [skipped_row(), skipped_row(pair("1001", "2002"), skipped_at=SECOND_TIME)]
    result = validate(tmp_path, skipped_file(rows), name="skipped_L1.csv")
    assert result.problems == []
    assert result.kind == "skipped"
    assert result.first_row == {pair("1001", "2001"): 2, pair("1001", "2002"): 3}


def test_the_header_of_a_skipped_file(tmp_path: Path) -> None:
    result = validate(tmp_path, label_file([label_row()]), name="skipped_L1.csv")
    assert "the header must be exactly pair_id, reason, skipped_at" in errors(result)[0]


@pytest.mark.parametrize("column", SKIPPED_COLUMNS)
def test_a_skipped_row_has_no_empty_field(tmp_path: Path, column: str) -> None:
    result = validate(tmp_path, skipped_file([skipped_row(**{column: ""})]), name="skipped_L1.csv")
    assert f"error (row 2, {column}): is empty" in errors(result)


def test_a_skipped_pair_is_checked_like_a_labelled_pair(tmp_path: Path) -> None:
    rows = [
        skipped_row("pandamart:1001|meenabazar:2001"),
        skipped_row(pair("1001", "9999"), skipped_at=SECOND_TIME),
        skipped_row("nonsense", skipped_at=SECOND_TIME),
    ]
    result = validate(
        tmp_path, skipped_file(rows), name="skipped_L1.csv", candidates=[pair("1001", "2001")]
    )
    messages = errors(result)
    assert any(
        "(row 2, pair_id): the listings are not in the required order" in m for m in messages
    )
    assert any(
        "(row 3, pair_id): the listing meenabazar:9999 is not in data/raw" in m for m in messages
    )
    assert any("(row 3, pair_id): the pair is not in candidates.csv" in m for m in messages)
    assert any("(row 4, pair_id)" in m and "must have the form" in m for m in messages)


def test_skipped_times_must_be_in_order_and_not_in_the_future(tmp_path: Path) -> None:
    rows = [
        skipped_row(skipped_at=SECOND_TIME),
        skipped_row(pair("1001", "2002"), skipped_at=FIRST_TIME),
        skipped_row(pair("1006", "2006"), skipped_at="2026-11-13T10:00:00+06:00"),
    ]
    result = validate(tmp_path, skipped_file(rows), name="skipped_L1.csv")
    assert errors(result) == [
        "error (row 3, skipped_at): skipped_at is earlier than the row above it",
        "error (row 4, skipped_at): '2026-11-13T10:00:00+06:00' is in the future",
    ]


def test_a_pair_skipped_twice_is_a_warning(tmp_path: Path) -> None:
    rows = [skipped_row(), skipped_row(skipped_at=SECOND_TIME)]
    result = validate(tmp_path, skipped_file(rows), name="skipped_L1.csv")
    assert result.errors == []
    assert warnings(result) == ["warning (row 3, pair_id): the pair is also in row 2"]


def test_a_pair_both_skipped_and_labelled_by_one_labeller_is_a_warning(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    folder = tmp_path / "labelled"
    folder.mkdir()
    (folder / "labels_L1.csv").write_bytes(label_file([label_row("1001", "2001")]))
    (folder / "skipped_L1.csv").write_bytes(skipped_file([skipped_row(pair("1001", "2001"))]))
    (folder / "skipped_L2.csv").write_bytes(skipped_file([skipped_row(pair("1001", "2001"))]))
    results = validate_files(sorted(folder.glob("*.csv")), ctx)
    by_name = {result.path.name: result for result in results}
    assert warnings(by_name["skipped_L1.csv"]) == [
        "warning (row 2, pair_id): the pair is also labelled in labels_L1.csv; "
        "a skipped pair is one that is left out"
    ]
    assert by_name["skipped_L2.csv"].warnings == []
    assert by_name["labels_L1.csv"].problems == []


# The command line.


def write_workspace(tmp_path: Path, rows: list[dict[str, str]]) -> list[str]:
    write_raw(tmp_path / "raw")
    write_guidelines(tmp_path)
    folder = tmp_path / "labelled"
    folder.mkdir(exist_ok=True)
    (folder / "labels_L1.csv").write_bytes(label_file(rows))
    return [
        "--raw-dir",
        str(tmp_path / "raw"),
        "--labelled-dir",
        str(folder),
        "--candidates",
        str(tmp_path / "no_candidates.csv"),
        "--guidelines",
        str(tmp_path / "labelling_guidelines.md"),
    ]


def test_the_default_is_every_file_in_the_labelled_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = write_workspace(
        tmp_path,
        [
            label_row(),
            label_row("1001", "2002", "non_match", "size_differs", labelled_at=SECOND_TIME),
        ],
    )
    (tmp_path / "labelled" / "skipped_L1.csv").write_bytes(
        skipped_file([skipped_row(pair("1006", "2006"))])
    )
    assert main(args, now=NOW) == 0
    output = capsys.readouterr().out
    assert "labels_L1.csv: 2 rows, 0 errors, 0 warnings" in output
    assert (
        "valid; 2 pairs labelled (match 1, non_match 1, unsure 0); guidelines 0.2 (2 rows)"
        in output
    )
    assert "skipped_L1.csv: 1 rows, 0 errors, 0 warnings" in output
    assert "valid; 1 pairs skipped" in output


def test_an_error_gives_exit_status_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = write_workspace(tmp_path, [label_row(label="maybe")])
    assert main(args, now=NOW) == 1
    assert "1 errors" in capsys.readouterr().out


def test_warnings_alone_give_exit_status_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = write_workspace(tmp_path, [label_row("1001", "2002", "match")])
    assert main(args, now=NOW) == 0
    output = capsys.readouterr().out
    assert "0 errors, 2 warnings" in output
    assert "valid;" in output


def test_files_named_on_the_command_line_are_checked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = write_workspace(tmp_path, [label_row()])
    other = tmp_path / "labelled" / "labels_L2.csv"
    other.write_bytes(label_file([label_row(labeller="L2", label="maybe")]))
    assert main([str(other), *args], now=NOW) == 1
    output = capsys.readouterr().out
    assert "labels_L2.csv" in output
    assert "labels_L1.csv" not in output


def test_no_labelled_files_is_not_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = write_workspace(tmp_path, [label_row()])
    (tmp_path / "labelled" / "labels_L1.csv").unlink()
    assert main(args, now=NOW) == 0
    assert "no labelled files found" in capsys.readouterr().out


def test_a_missing_file_gives_status_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = write_workspace(tmp_path, [label_row()])
    assert main([str(tmp_path / "missing.csv"), *args], now=NOW) == 1
    assert "missing.csv: not a file" in capsys.readouterr().out


def test_adjudication_and_overlap_files_are_reported_as_not_checked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = write_workspace(tmp_path, [label_row()])
    (tmp_path / "labelled" / "adjudication.csv").write_bytes(b"x")
    assert main(args, now=NOW) == 0
    assert "adjudication.csv: not checked yet" in capsys.readouterr().out


def test_unreadable_listings_give_status_one_and_an_error_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = write_workspace(tmp_path, [label_row()])
    (tmp_path / "raw" / "pandamart_20261106.csv").write_bytes(csv_bytes(COLUMNS[:-1], []))
    assert main(args, now=NOW) == 1
    assert (
        "error: pandamart_20261106.csv does not have the 12 listing columns"
        in capsys.readouterr().out
    )


def test_a_malformed_candidates_file_gives_status_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = write_workspace(tmp_path, [label_row()])
    (tmp_path / "no_candidates.csv").write_text("category\nrice\n", encoding="utf-8")
    assert main(args, now=NOW) == 1
    assert "error: no_candidates.csv has no pair_id column" in capsys.readouterr().out


def test_the_output_never_contains_a_title(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Listings 1007 and 2007 carry a word that appears nowhere else.
    rows = [
        label_row("1007", "2007", "match", "size_differs"),
        label_row("1007", "2007", "maybe", "nonsense", labelled_at=SECOND_TIME),
        label_row("1007", "2001", "non_match", "multipack", labelled_at=SECOND_TIME),
        label_row("1007", "9999", labelled_at=SECOND_TIME),
    ]
    args = write_workspace(tmp_path, rows)
    assert main(args, now=NOW) == 1
    output = capsys.readouterr().out
    assert "error" in output
    assert "warning" in output
    assert "orbaxo" not in output.lower()


def test_the_validator_changes_no_file(tmp_path: Path) -> None:
    args = write_workspace(tmp_path, [label_row(label="maybe")])
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    main(args, now=NOW)
    after = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert before == after


def test_listing_rows_for_the_other_tests_are_valid_listings() -> None:
    # A guard for the builders: a listing row has the 12 columns of data/raw.
    assert tuple(listing_row("pandamart", "1", "Zorbaxo")) == COLUMNS
