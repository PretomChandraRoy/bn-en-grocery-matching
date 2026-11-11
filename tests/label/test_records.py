"""Tests for src.label.records.

All values are invented. Bangla text is built from code points (see tests/helpers.py).
"""

from pathlib import Path

import pytest

from src.label.records import (
    LABEL_COLUMNS,
    LABELLER_ID,
    LABELS,
    TAG_REQUIRED_LABELS,
    TAGS,
    PairKey,
    ParsedNote,
    check_label_and_tags,
    cross_script,
    format_note,
    labels_file_name,
    make_pair_id,
    parse_note,
    parse_pair_id,
    read_guidelines_version,
    read_version_history,
    skipped_file_name,
    sort_tags,
)
from tests.helpers import bn

CHAL = bn(0x099A, 0x09BE, 0x09B2)  # চাল
BANGLA_ONE = bn(0x09E7)  # ১
KEJI = bn(0x0995, 0x09C7, 0x099C, 0x09BF)  # কেজি


# File names and constants.


def test_file_names() -> None:
    assert labels_file_name("L1") == "labels_L1.csv"
    assert skipped_file_name("L2") == "skipped_L2.csv"


def test_the_label_columns_are_the_ten_agreed_columns() -> None:
    assert LABEL_COLUMNS[:5] == ("pair_id", "left_source", "left_id", "right_source", "right_id")
    assert LABEL_COLUMNS[5:] == ("label", "note", "labeller", "labelled_at", "guidelines_version")


def test_the_labels_are_match_non_match_and_unsure() -> None:
    assert LABELS == ("match", "non_match", "unsure")


@pytest.mark.parametrize("labeller", ["L1", "L2", "L10"])
def test_labeller_ids_that_are_allowed(labeller: str) -> None:
    assert LABELLER_ID.fullmatch(labeller)


@pytest.mark.parametrize("labeller", ["", "L", "l1", "Pretom", "L1 ", "1", "L-1", "L1x"])
def test_labeller_ids_that_are_not_allowed(labeller: str) -> None:
    assert LABELLER_ID.fullmatch(labeller) is None


# pair_id.


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        pytest.param(
            ("pandamart", "6142151", "meenabazar", "4525"),
            "meenabazar:4525|pandamart:6142151",
            id="the-source-that-comes-first-alphabetically-is-left",
        ),
        pytest.param(
            ("meenabazar", "4525", "pandamart", "6142151"),
            "meenabazar:4525|pandamart:6142151",
            id="already-in-order",
        ),
        pytest.param(("shop", "9", "shop", "10"), "shop:9|shop:10", id="same-source-by-value"),
        pytest.param(("shop", "10", "shop", "9"), "shop:9|shop:10", id="same-source-swapped"),
        pytest.param(("shop", "007", "shop", "7"), "shop:007|shop:7", id="same-value-keeps-order"),
        pytest.param(("shop", "b1", "shop", "a1"), "shop:a1|shop:b1", id="same-source-text-ids"),
        pytest.param(("shop", "5", "shop", "a1"), "shop:5|shop:a1", id="digits-before-text"),
    ],
)
def test_make_pair_id_puts_the_listings_in_the_required_order(
    args: tuple[str, str, str, str], expected: str
) -> None:
    assert make_pair_id(*args) == expected


@pytest.mark.parametrize(
    "args",
    [
        ("", "1", "other", "2"),
        ("shop", "", "other", "2"),
        ("shop", "1", "other", "2:3"),
        ("shop", "1", "ot|her", "2"),
        ("sh op", "1", "other", "2"),
        ("shop", "1", "other", "2 "),
    ],
)
def test_make_pair_id_rejects_parts_that_would_break_the_format(
    args: tuple[str, str, str, str],
) -> None:
    with pytest.raises(ValueError, match="must have the form"):
        make_pair_id(*args)


def test_parse_pair_id_returns_the_four_parts() -> None:
    key = parse_pair_id("meenabazar:4525|pandamart:6142151")
    assert key == PairKey("meenabazar", "4525", "pandamart", "6142151")
    assert key.pair_id == "meenabazar:4525|pandamart:6142151"
    assert key.is_canonical
    assert not key.is_same_source


@pytest.mark.parametrize(
    "pair_id",
    [
        "",
        "a:1",
        "a:1|b",
        "a:1|b:2|c:3",
        "a:1|:2",
        "a:|b:2",
        ":1|b:2",
        "a:1 | b:2",
        "a:1|b:2 ",
        "a:1:x|b:2",
        "a:1||b:2",
        "a-1|b-2",
    ],
)
def test_parse_pair_id_rejects_malformed_text(pair_id: str) -> None:
    with pytest.raises(ValueError, match="must have the form"):
        parse_pair_id(pair_id)


@pytest.mark.parametrize(
    ("pair_id", "canonical"),
    [
        ("meenabazar:1|pandamart:2", True),
        ("pandamart:2|meenabazar:1", False),
        ("shop:9|shop:10", True),
        ("shop:10|shop:9", False),
        ("shop:7|shop:7", True),
    ],
)
def test_is_canonical(pair_id: str, canonical: bool) -> None:
    assert parse_pair_id(pair_id).is_canonical is canonical


def test_a_pair_from_one_source_is_reported_as_same_source() -> None:
    assert parse_pair_id("shop:1|shop:2").is_same_source


def test_make_pair_id_and_parse_pair_id_round_trip() -> None:
    pair_id = make_pair_id("pandamart", "1", "meenabazar", "2")
    key = parse_pair_id(pair_id)
    assert key.is_canonical
    assert make_pair_id(key.right_source, key.right_id, key.left_source, key.left_id) == pair_id


# Notes.


@pytest.mark.parametrize(
    ("note", "tags", "comment"),
    [
        pytest.param("", (), "", id="empty"),
        pytest.param("unbranded", ("unbranded",), "", id="one-tag"),
        pytest.param("unbranded;cross_script", ("unbranded", "cross_script"), "", id="two-tags"),
        pytest.param("unbranded # same oil", ("unbranded",), "same oil", id="tag-and-comment"),
        pytest.param("a;b # x # y", ("a", "b"), "x # y", id="only-the-first-separator-counts"),
        pytest.param("# only a comment", (), "only a comment", id="comment-only"),
        pytest.param("# ", (), "", id="empty-comment-only"),
        pytest.param("a # ", ("a",), "", id="tag-and-empty-comment"),
        pytest.param("a;b # c;d", ("a", "b"), "c;d", id="semicolon-in-comment"),
    ],
)
def test_parse_note(note: str, tags: tuple[str, ...], comment: str) -> None:
    assert parse_note(note) == ParsedNote(tags, comment)


@pytest.mark.parametrize(
    ("note", "message"),
    [
        pytest.param("a; b", "no spaces", id="space-after-semicolon"),
        pytest.param("a ;b", "no spaces", id="space-before-semicolon"),
        pytest.param("a b", "no spaces", id="space-inside"),
        pytest.param("a;;b", "empty tag", id="empty-tag"),
        pytest.param("a;", "empty tag", id="trailing-semicolon"),
        pytest.param(";a", "empty tag", id="leading-semicolon"),
        pytest.param(" # c", "must start with", id="space-then-comment"),
    ],
)
def test_parse_note_rejects_a_malformed_tag_part(note: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_note(note)


@pytest.mark.parametrize(
    ("tags", "comment", "note"),
    [
        ((), "", ""),
        (("unbranded",), "", "unbranded"),
        (("unbranded", "size_differs"), "", "unbranded;size_differs"),
        (("unbranded",), "same oil", "unbranded # same oil"),
        ((), "only a comment", "# only a comment"),
    ],
)
def test_format_note_is_the_inverse_of_parse_note(
    tags: tuple[str, ...], comment: str, note: str
) -> None:
    assert format_note(tags, comment) == note
    assert parse_note(note) == ParsedNote(tags, comment)


def test_sort_tags_follows_the_table_of_the_guidelines() -> None:
    assert sort_tags(["cross_script", "size_differs", "unbranded"]) == (
        "unbranded",
        "size_differs",
        "cross_script",
    )
    assert sort_tags(["zzz", "unbranded", "aaa"]) == ("unbranded", "zzz", "aaa")
    assert sort_tags([]) == ()


# The consistency rules.


@pytest.mark.parametrize("tag", ["size_differs", "variant_differs", "brand_differs"])
@pytest.mark.parametrize("label", ["match", "unsure"])
def test_a_difference_tag_requires_non_match(tag: str, label: str) -> None:
    problems = check_label_and_tags(label, [tag])
    assert problems == [f"the tag {tag} requires the label non_match, not {label}"]


def test_unit_kind_differs_requires_non_match() -> None:
    assert check_label_and_tags("non_match", ["unit_kind_differs"]) == []
    assert check_label_and_tags("match", ["unit_kind_differs"])
    assert check_label_and_tags("unsure", ["unit_kind_differs"])


@pytest.mark.parametrize(("label", "ok"), [("match", False), ("unsure", True), ("non_match", True)])
def test_brand_missing_requires_unsure_or_non_match(label: str, ok: bool) -> None:
    problems = check_label_and_tags(label, ["brand_missing"])
    if ok:
        assert problems == []
    else:
        assert problems == [
            "the tag brand_missing requires the label non_match or unsure, not match"
        ]


@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("tag", ["unbranded", "multipack", "promo_quantity", "cross_script"])
def test_other_tags_go_with_any_label(label: str, tag: str) -> None:
    assert check_label_and_tags(label, [tag]) == []


def test_the_tags_with_a_required_label_are_the_five_agreed_tags() -> None:
    assert set(TAG_REQUIRED_LABELS) == {
        "size_differs",
        "variant_differs",
        "brand_differs",
        "unit_kind_differs",
        "brand_missing",
    }
    assert set(TAG_REQUIRED_LABELS) <= set(TAGS)


def test_an_unknown_tag_is_a_problem() -> None:
    problems = check_label_and_tags("match", ["unbranded", "Unbranded", "other"])
    assert len(problems) == 2
    assert "'Unbranded' is not a tag" in problems[0]
    assert "'other' is not a tag" in problems[1]


def test_an_unknown_label_is_a_problem() -> None:
    assert "'maybe' is not one of match, non_match, unsure" in check_label_and_tags("maybe", [])[0]
    # The tag rules are not applied to a label that does not exist.
    assert len(check_label_and_tags("maybe", ["size_differs"])) == 1


def test_a_repeated_tag_is_a_problem() -> None:
    assert check_label_and_tags("match", ["unbranded", "unbranded"]) == [
        "the tag unbranded appears twice"
    ]


def test_the_worked_example_of_a_label_with_several_tags() -> None:
    assert check_label_and_tags("non_match", ["unbranded", "size_differs", "cross_script"]) == []


def test_every_problem_is_reported() -> None:
    problems = check_label_and_tags("match", ["size_differs", "brand_missing", "nonsense"])
    assert len(problems) == 3


# cross_script.


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        pytest.param("Test Rice 1 kg", f"{CHAL} 1 {KEJI}", True, id="one-bangla"),
        pytest.param(f"{CHAL} 1 {KEJI}", "Test Rice 1 kg", True, id="one-bangla-other-side"),
        pytest.param("Test Rice 1 kg", "Test Chal 1 kg", False, id="no-bangla"),
        pytest.param(f"{CHAL} 1 {KEJI}", f"{CHAL} 2 {KEJI}", False, id="both-bangla"),
        pytest.param("Test Rice 1 kg", f"Rice {BANGLA_ONE} kg", False, id="digit-is-not-a-letter"),
        pytest.param(f"Test {CHAL} 1 kg", "Test Rice", True, id="mixed-title-counts-as-bangla"),
        pytest.param("", "", False, id="both-empty"),
    ],
)
def test_cross_script(left: str, right: str, expected: bool) -> None:
    assert cross_script(left, right) is expected


# The guidelines file.


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "guidelines.md"
    path.write_text(text, encoding="utf-8")
    return path


GOOD_FILE = """# Labelling Guidelines

Version: 0.2

Intro.

## Version history

- 0.1 (2026-11-04): pilot draft.
- 0.2 (2026-11-05): defined the script field.
"""


def test_the_version_is_read_from_the_version_line(tmp_path: Path) -> None:
    assert read_guidelines_version(write(tmp_path, GOOD_FILE)) == "0.2"


@pytest.mark.parametrize("version", ["0.1", "0.10", "1.0", "12.34"])
def test_other_versions(tmp_path: Path, version: str) -> None:
    assert read_guidelines_version(write(tmp_path, f"Version: {version}\n")) == version


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("# Title\n\nNo version here.\n", id="missing"),
        pytest.param("Version: 0.2\nVersion: 0.3\n", id="twice"),
        pytest.param("Version:0.2\n", id="no-space"),
        pytest.param("Version:  0.2\n", id="two-spaces"),
        pytest.param("Version: 0.2.1\n", id="three-numbers"),
        pytest.param("Version: 2\n", id="one-number"),
        pytest.param("Version: v0.2\n", id="letter"),
        pytest.param("Version: 0.2 draft\n", id="trailing-text"),
        pytest.param("Version: \n", id="empty"),
        pytest.param("Version: 0,2\n", id="comma"),
    ],
)
def test_a_version_line_in_the_wrong_form_is_an_error(tmp_path: Path, text: str) -> None:
    with pytest.raises(ValueError, match="Version"):
        read_guidelines_version(write(tmp_path, text))


def test_a_version_in_the_middle_of_a_line_is_not_the_version_line(tmp_path: Path) -> None:
    text = "This is Version: 0.9 of the text.\n"
    with pytest.raises(ValueError, match="exactly one line"):
        read_guidelines_version(write(tmp_path, text))


def test_the_version_history_lists_the_versions_in_order(tmp_path: Path) -> None:
    assert read_version_history(write(tmp_path, GOOD_FILE)) == ("0.1", "0.2")


def test_the_version_history_stops_at_the_next_heading(tmp_path: Path) -> None:
    text = GOOD_FILE + "\n## Later section\n\n- 0.9 (2026-12-01): not a version.\n"
    assert read_version_history(write(tmp_path, text)) == ("0.1", "0.2")


def test_other_list_lines_in_the_history_are_ignored(tmp_path: Path) -> None:
    text = GOOD_FILE + "- a note that is not a version line\n- 0.3 2026-11-06 no brackets\n"
    assert read_version_history(write(tmp_path, text)) == ("0.1", "0.2")


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("Version: 0.2\n", id="no-heading"),
        pytest.param("Version: 0.2\n\n## Version history\n\nNothing yet.\n", id="no-versions"),
    ],
)
def test_a_missing_version_history_is_an_error(tmp_path: Path, text: str) -> None:
    with pytest.raises(ValueError, match="no '## Version history' heading|lists no version"):
        read_version_history(write(tmp_path, text))
