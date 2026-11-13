"""Tests for src.label.tool.

All listings, pairs and labels are invented (see tests/label/builders.py) and live in scratch
folders. A session is driven by scripted answers: the tool asks, the test answers. A clock that the
test controls stands in for the computer's clock.
"""

import ast
import csv
import hashlib
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.collect.validate import parse_timestamp
from src.label.listings import Listing
from src.label.records import (
    AUTOMATIC_TAGS,
    LABEL_COLUMNS,
    REPO_DIR,
    SKIPPED_COLUMNS,
    TAGS,
    labels_file_name,
    skipped_file_name,
)
from src.label.tool import (
    Config,
    Session,
    ToolError,
    display_width,
    main,
    render_pair,
    tag_list_text,
    wrap_display,
)
from src.label.validate import load_context, validate_files
from tests.helpers import bn
from tests.label.builders import (
    LISTINGS,
    NOW,
    POISON,
    PRICES,
    csv_bytes,
    label_file,
    label_row,
    pair,
    write_candidates_file,
    write_guidelines,
    write_raw,
)

BANGLA_TIME = timezone(timedelta(hours=6))
CHAL = bn(0x099A, 0x09BE, 0x09B2)  # চাল
KEJI = bn(0x0995, 0x09C7, 0x099C, 0x09BF)  # কেজি
COMMENT_IN_BANGLA = bn(0x09AD, 0x09BE, 0x09B2, 0x09CB)  # ভালো
VIRAMA = bn(0x09CD)  # ◌্
NO_BREAK_SPACE = bn(0x00A0)
CJK_CHARACTER = bn(0x4E2D)

# Five pairs among the invented listings, none with a Bangla title (BANGLA_PAIR has one).
DEFAULT_PAIRS = [
    pair("1001", "2001"),
    pair("1001", "2002"),
    pair("1004", "2004"),
    pair("1003", "2003"),
    pair("1006", "2006"),
]
BANGLA_PAIR = pair("1005", "2001")
SINGLE = [pair("1001", "2001")]


class Clock:
    """A clock that moves forward one second at each reading."""

    def __init__(self, start: datetime | None = None, step: int = 1) -> None:
        self.start = start or datetime(2026, 11, 12, 9, 0, 0, tzinfo=BANGLA_TIME)
        self.step = step
        self.readings = 0

    def __call__(self) -> datetime:
        moment = self.start + timedelta(seconds=self.step * self.readings)
        self.readings += 1
        return moment


@dataclass
class World:
    root: Path
    raw: Path
    labelled: Path
    candidates: Path
    guidelines: Path

    def config(self, labeller: str = "L1", width: int | None = 100) -> Config:
        return Config(labeller, self.raw, self.labelled, self.candidates, self.guidelines, width)

    def args(self, labeller: str = "L1") -> list[str]:
        return [
            "--labeller",
            labeller,
            "--raw-dir",
            str(self.raw),
            "--labelled-dir",
            str(self.labelled),
            "--candidates",
            str(self.candidates),
            "--guidelines",
            str(self.guidelines),
            "--width",
            "100",
        ]

    def labels(self, labeller: str = "L1") -> list[dict[str, str]]:
        return read_rows(self.labelled / labels_file_name(labeller))

    def skipped(self, labeller: str = "L1") -> list[dict[str, str]]:
        return read_rows(self.labelled / skipped_file_name(labeller))


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def make_world(
    tmp_path: Path,
    pairs: list[str] | None = None,
    listings: list[tuple[str, ...]] | None = None,
    guidelines: str | None = None,
) -> World:
    labelled = tmp_path / "labelled"
    labelled.mkdir()
    return World(
        root=tmp_path,
        raw=write_raw(tmp_path / "raw", listings),
        labelled=labelled,
        candidates=write_candidates_file(tmp_path / "candidates.csv", pairs or DEFAULT_PAIRS),
        guidelines=write_guidelines(tmp_path, *([guidelines] if guidelines else [])),
    )


@dataclass
class Run:
    status: int
    out: str
    prompts: list[str] = field(default_factory=list)


def run(
    world: World,
    answers: list[str],
    *,
    labeller: str = "L1",
    clock: Clock | None = None,
    on_prompt=None,  # noqa: ANN001
) -> Run:
    """Run main with scripted answers; when they run out the input ends, like Ctrl+Z."""
    queue = list(answers)
    result = Run(0, "")
    shown: list[str] = []

    def fake_input(prompt: str) -> str:
        result.prompts.append(prompt)
        if on_prompt is not None:
            on_prompt(len(result.prompts))
        if not queue:
            raise EOFError
        return queue.pop(0)

    result.status = main(
        world.args(labeller), input_fn=fake_input, print_fn=shown.append, now_fn=clock or Clock()
    )
    result.out = "\n".join(shown)
    return result


def expected_order(pair_ids: list[str]) -> list[str]:
    return sorted(pair_ids, key=lambda i: (hashlib.sha256(i.encode("utf-8")).hexdigest(), i))


def listing(**changes: str) -> Listing:
    values = {
        "source": "pandamart",
        "listing_id": "1",
        "title_raw": "Test Rice 1kg",
        "brand": "",
        "size_value": "",
        "size_unit": "",
        "category": "rice",
        "source_category": "",
        "script": "english",
        "url": "https://example.invalid/1",
    }
    values.update(changes)
    return Listing(**values)


# The display.


def test_the_two_listings_are_side_by_side_on_a_wide_display() -> None:
    left = listing(source="meenabazar", title_raw="LEFT TITLE")
    right = listing(title_raw="Right Title")
    text = render_pair(left, right, heading="Pair 1 of 2", width=100)
    row = next(line for line in text.splitlines() if "LEFT TITLE" in line)
    assert " | " in row
    assert row.index("LEFT TITLE") < row.index("Right Title")
    assert text.splitlines()[0] == "Pair 1 of 2"
    assert "source: meenabazar" in text
    assert "source: pandamart" in text
    assert "category: rice" in text


def test_the_listings_are_stacked_on_a_narrow_display() -> None:
    text = render_pair(
        listing(title_raw="LEFT TITLE"), listing(title_raw="Right Title"), heading="h", width=50
    )
    assert " | " not in text
    assert text.index("LEFT TITLE") < text.index("Right Title")
    assert all(display_width(line) <= 50 for line in text.splitlines())


def test_a_long_title_is_wrapped_inside_its_column() -> None:
    title = "Alpha Beta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa Lambda Mu Nu Xi Omicron"
    text = render_pair(listing(title_raw=title), listing(), heading="h", width=80)
    assert all(display_width(line) <= 80 for line in text.splitlines())
    shown = " ".join(part.split(" | ")[0].strip() for part in text.splitlines())
    for word in title.split():
        assert word in shown


def test_the_columns_stay_aligned_for_a_bangla_title() -> None:
    left = listing(title_raw=f"{CHAL} {KEJI} Test {CHAL} {KEJI}", source="meenabazar")
    text = render_pair(left, listing(), heading="h", width=100)
    body = text.splitlines()[2:-1]
    column = (100 - 3) // 2
    for line in body:
        assert " |" in line
        assert display_width(line.split(" |")[0]) == column, line


def test_the_brand_is_shown_with_the_reminder_that_it_may_be_the_manufacturer() -> None:
    text = render_pair(listing(brand="Test Foods Ltd"), listing(), heading="h", width=100)
    assert "brand field: Test Foods Ltd" in text
    assert "brand field: (empty)" in text
    assert "can hold the manufacturer, not the brand" in text
    assert "Read the brand from the title." in text


def test_there_is_no_brand_reminder_when_no_listing_has_a_brand() -> None:
    text = render_pair(listing(), listing(), heading="h", width=100)
    assert "manufacturer" not in text


def test_size_fields_are_shown_only_when_filled_in() -> None:
    plain = render_pair(listing(), listing(), heading="h", width=100)
    assert "size field" not in plain
    both = render_pair(listing(size_value="500", size_unit="gm"), listing(), heading="h", width=100)
    assert "size fields: 500 gm" in both
    only_unit = render_pair(listing(size_unit="gm"), listing(), heading="h", width=100)
    assert "size fields: gm" in only_unit


def test_the_shops_own_category_is_not_shown() -> None:
    # The guidelines list the category of the project only; a shop's label could steer the labeller.
    text = render_pair(
        listing(source_category="Zorbaxo Shelf"),
        listing(source_category="Other Shelf"),
        heading="h",
        width=100,
    )
    assert "Zorbaxo Shelf" not in text
    assert "Other Shelf" not in text
    assert "shop category" not in text


def test_the_script_and_the_url_are_not_shown() -> None:
    text = render_pair(listing(script="romanised"), listing(), heading="h", width=100)
    assert "romanised" not in text
    assert "english" not in text
    assert "example.invalid" not in text


def test_the_title_is_shown_exactly_as_collected() -> None:
    title = f"  TEST   {CHAL} Rice 1kg{NO_BREAK_SPACE}"
    text = render_pair(listing(title_raw=title), listing(), heading="h", width=200)
    assert f"TEST {CHAL} Rice 1kg" in text  # only the spacing is laid out


@pytest.mark.parametrize(
    ("text", "width"),
    [("", 0), ("abc", 3), (CHAL, 3), (KEJI, 4), ("a" + VIRAMA, 1), (CJK_CHARACTER, 2)],
)
def test_display_width(text: str, width: int) -> None:
    # A vowel sign that takes a place counts one; a virama or other combining mark counts none.
    assert display_width(text) == width


def test_wrap_display() -> None:
    assert wrap_display("Zorbaxo Fine Grain Style Mix", 20) == [
        "Zorbaxo Fine Grain",
        "Style Mix",
    ]
    assert wrap_display("", 20) == [""]
    # A line may be exactly as wide as the width, and no wider.
    assert wrap_display("aaaa bbb", 8) == ["aaaa bbb"]
    assert wrap_display("aaaa bbbb", 8) == ["aaaa", "bbbb"]
    assert wrap_display("abcdefghijklmnop", 10, "  ") == ["abcdefgh", "  ijklmnop"]
    assert all(display_width(line) <= 12 for line in wrap_display("x" * 40 + " y", 12, "  "))


def test_the_tag_list_names_every_tag_a_labeller_may_type() -> None:
    text = tag_list_text()
    allowed_line = text.splitlines()[0]
    for tag in TAGS:
        if tag in AUTOMATIC_TAGS:
            assert f"{tag} is added by the tool" in text
            assert tag not in allowed_line
        else:
            assert tag in allowed_line
    assert "size_differs (non_match only)" in text
    assert "brand_missing (non_match or unsure only)" in text
    assert "unbranded," in text


# Labelling.


def test_the_session_starts_with_the_guidelines_version(tmp_path: Path) -> None:
    result = run(make_world(tmp_path), [])
    assert result.status == 0
    assert "Labelling as L1. Guidelines version 0.2" in result.out
    assert "read it before you label" in result.out


def test_a_label_is_written_with_every_field(tmp_path: Path) -> None:
    world = make_world(tmp_path, SINGLE)
    clock = Clock()
    result = run(world, ["m", ""], clock=clock)
    assert result.status == 0
    assert world.labels() == [
        {
            "pair_id": pair("1001", "2001"),
            "left_source": "meenabazar",
            "left_id": "2001",
            "right_source": "pandamart",
            "right_id": "1001",
            "label": "match",
            "note": "",
            "labeller": "L1",
            # The clock was read once when the session started and once for the label.
            "labelled_at": "2026-11-12T09:00:01+06:00",
            "guidelines_version": "0.2",
        }
    ]
    assert "Saved: match" in result.out


def test_the_file_is_utf_8_with_lf_line_ends_and_the_header_first(tmp_path: Path) -> None:
    world = make_world(tmp_path, SINGLE)
    run(world, ["m", ""])
    data = (world.labelled / "labels_L1.csv").read_bytes()
    assert data.decode("utf-8").splitlines()[0] == ",".join(LABEL_COLUMNS)
    assert b"\r" not in data
    assert not data.startswith(b"\xef\xbb\xbf")
    assert data.endswith(b"\n")


@pytest.mark.parametrize(
    ("answer", "label"),
    [("m", "match"), ("n", "non_match"), ("u", "unsure"), ("match", "match"), ("N", "non_match")],
)
def test_the_three_labels(tmp_path: Path, answer: str, label: str) -> None:
    world = make_world(tmp_path, SINGLE)
    run(world, [answer, ""])
    assert [row["label"] for row in world.labels()] == [label]


def test_a_bare_enter_or_a_wrong_key_does_not_label(tmp_path: Path) -> None:
    world = make_world(tmp_path, SINGLE)
    result = run(world, ["", "x", "yes", "m", ""])
    assert [row["label"] for row in world.labels()] == ["match"]
    assert result.out.count("Type m, n, u, s, b, q or ? and press Enter.") == 3


def test_help_lists_the_keys(tmp_path: Path) -> None:
    result = run(make_world(tmp_path, SINGLE), ["?", "q"])
    assert "m  match" in result.out
    assert "s  skip" in result.out
    assert "a difficult pair gets unsure, not skip" in result.out


def test_the_tags_are_listed_each_time_a_note_is_asked_for(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    result = run(world, ["m", "", "n", "", "u", ""])
    assert result.out.count("Allowed tags: ") == 3
    assert result.out.count("cross_script is added by the tool") == 3
    assert "unbranded" in result.out
    assert any(prompt.startswith("Note for match") for prompt in result.prompts)


def test_tags_and_a_comment_are_written_as_typed(tmp_path: Path) -> None:
    world = make_world(tmp_path, SINGLE)
    run(world, ["n", "unbranded;size_differs # not the same bag"])
    assert world.labels()[0]["note"] == "unbranded;size_differs # not the same bag"


def test_a_comment_without_tags_is_written_with_a_hash(tmp_path: Path) -> None:
    world = make_world(tmp_path, SINGLE)
    run(world, ["m", "# same product"])
    assert world.labels()[0]["note"] == "# same product"


def test_tags_are_written_in_the_order_of_the_guidelines(tmp_path: Path) -> None:
    world = make_world(tmp_path, SINGLE)
    run(world, ["n", "size_differs;unbranded"])
    assert world.labels()[0]["note"] == "unbranded;size_differs"


def test_a_bangla_comment_is_saved_as_utf_8(tmp_path: Path) -> None:
    world = make_world(tmp_path, SINGLE)
    run(world, ["m", f"# {COMMENT_IN_BANGLA}"])
    assert world.labels()[0]["note"] == f"# {COMMENT_IN_BANGLA}"
    assert f"# {COMMENT_IN_BANGLA}".encode() in (world.labelled / "labels_L1.csv").read_bytes()


def test_cross_script_is_added_when_exactly_one_title_has_bangla(tmp_path: Path) -> None:
    world = make_world(tmp_path, [BANGLA_PAIR])
    run(world, ["m", ""])
    assert world.labels()[0]["note"] == "cross_script"


def test_cross_script_comes_after_the_typed_tags_and_before_the_comment(tmp_path: Path) -> None:
    world = make_world(tmp_path, [BANGLA_PAIR])
    run(world, ["m", "unbranded # same rice"])
    assert world.labels()[0]["note"] == "unbranded;cross_script # same rice"


def test_a_typed_cross_script_is_ignored_with_a_message(tmp_path: Path) -> None:
    on_bangla = (
        make_world(tmp_path / "a", [BANGLA_PAIR]) if (tmp_path / "a").mkdir() is None else None
    )
    result = run(on_bangla, ["m", "cross_script"])
    assert on_bangla.labels()[0]["note"] == "cross_script"
    assert "cross_script is added by the tool and was ignored." in result.out
    elsewhere = make_world(tmp_path / "b", SINGLE) if (tmp_path / "b").mkdir() is None else None
    run(elsewhere, ["m", "cross_script"])
    assert elsewhere.labels()[0]["note"] == ""


def test_a_wrong_note_is_asked_for_again_with_the_reason(tmp_path: Path) -> None:
    world = make_world(tmp_path, SINGLE)
    result = run(
        world,
        [
            "m",
            "nonsense",
            "unbranded; multipack",
            "size_differs",
            "unbranded",
        ],
    )
    assert [row["note"] for row in world.labels()] == ["unbranded"]
    assert "'nonsense' is not a tag" in result.out
    assert "must be separated by semicolons with no spaces" in result.out
    assert "the tag size_differs requires the label non_match, not match" in result.out
    assert "Fix the note, or type < to choose the label again." in result.out


def test_less_than_goes_back_to_the_label(tmp_path: Path) -> None:
    world = make_world(tmp_path, SINGLE)
    run(world, ["m", "size_differs", "<", "n", "size_differs"])
    assert [(row["label"], row["note"]) for row in world.labels()] == [
        ("non_match", "size_differs")
    ]


def test_nothing_is_written_until_the_note_is_accepted(tmp_path: Path) -> None:
    world = make_world(tmp_path, SINGLE)
    run(world, ["m", "nonsense"])
    assert world.labels() == []


def test_every_label_is_flushed_before_the_next_question(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    rows_seen = []

    def watch(count: int) -> None:
        rows_seen.append(len(world.labels()))

    run(world, ["m", "", "n", "", "u", ""], on_prompt=watch)
    # Prompts: label, note, label, note, label, note, label (an end of input).
    assert rows_seen[:7] == [0, 0, 1, 1, 2, 2, 3]


def test_a_crash_loses_no_label(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    answers = iter(["m", "", "n", "", "boom"])

    def fake_input(prompt: str) -> str:
        answer = next(answers)
        if answer == "boom":
            raise RuntimeError("the computer failed")
        return answer

    with pytest.raises(RuntimeError):
        main(world.args(), input_fn=fake_input, print_fn=lambda text: None, now_fn=Clock())
    assert [row["label"] for row in world.labels()] == ["match", "non_match"]


def test_each_label_and_skip_is_in_the_file_when_it_is_synchronised_to_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = make_world(tmp_path)
    rows_in_files = []

    def fake_fsync(descriptor: int) -> None:
        rows_in_files.append(len(world.labels()) + len(world.skipped()))

    monkeypatch.setattr("os.fsync", fake_fsync)
    run(world, ["m", "", "s", "bundle", "n", ""])
    # Each synchronisation comes after the row was written and flushed, not before.
    assert rows_in_files == [1, 2, 3]


def test_the_time_is_written_in_whole_seconds(tmp_path: Path) -> None:
    world = make_world(tmp_path, SINGLE)
    clock = Clock(datetime(2026, 11, 12, 9, 0, 0, 654321, tzinfo=BANGLA_TIME))
    run(world, ["m", ""], clock=clock)
    assert world.labels()[0]["labelled_at"] == "2026-11-12T09:00:01+06:00"


# Order and resuming.


def test_the_pairs_come_in_the_order_of_a_hash_of_their_ids(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    session = Session(world.config(), print_fn=lambda text: None, now_fn=Clock())
    assert [key.pair_id for key in session.state.order] == expected_order(DEFAULT_PAIRS)


def test_a_new_pair_does_not_change_the_order_of_the_others(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    before = [k.pair_id for k in Session(world.config(), now_fn=Clock()).state.order]
    write_candidates_file(world.candidates, [*DEFAULT_PAIRS, pair("1002", "2001")])
    after = [k.pair_id for k in Session(world.config(), now_fn=Clock()).state.order]
    assert [pair_id for pair_id in after if pair_id in before] == before


def test_the_order_does_not_depend_on_the_order_of_the_candidates_file(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    first = [k.pair_id for k in Session(world.config(), now_fn=Clock()).state.order]
    write_candidates_file(world.candidates, list(reversed(DEFAULT_PAIRS)))
    second = [k.pair_id for k in Session(world.config(), now_fn=Clock()).state.order]
    assert first == second


def test_the_first_pair_shown_is_the_first_in_order(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    result = run(world, ["q"])
    assert f"Pair 1 of 5   {expected_order(DEFAULT_PAIRS)[0]}" in result.out


def test_a_second_session_resumes_with_the_first_unlabelled_pair(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    clock = Clock()
    run(world, ["m", "", "n", "", "q"], clock=clock)
    order = expected_order(DEFAULT_PAIRS)
    second = run(world, ["q"], clock=clock)
    assert "Resuming: 2 labelled, 0 skipped, 3 to do." in second.out
    assert f"Pair 3 of 5   {order[2]}" in second.out
    assert order[0] not in second.out.split("Resuming")[1]


def test_all_pairs_done_ends_the_session(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    clock = Clock()
    result = run(world, ["m", ""] * 5, clock=clock)
    assert result.status == 0
    assert "Every pair is labelled or skipped." in result.out
    assert len(world.labels()) == 5
    again = run(world, [], clock=clock)
    assert "Every pair is labelled or skipped." in again.out
    assert len(world.labels()) == 5


def test_quitting_prints_a_summary_and_the_next_steps(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    result = run(world, ["m", "", "n", "", "q"])
    assert result.status == 0
    assert (
        "This session wrote 2 label rows. In all: 2 pairs labelled (match 1, non_match 1, unsure 0)"
        in result.out
    )
    assert "0 skipped, 3 to do." in result.out
    assert "python -m src.label.validate" in result.out
    assert "dvc add data/labelled/labels_L1.csv" in result.out
    assert "dvc push and dvc status -c" in result.out
    assert "Google Drive" in result.out


def test_the_next_steps_name_the_skipped_file_when_there_is_one(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    result = run(world, ["s", "bundle", "q"])
    assert "dvc add data/labelled/labels_L1.csv data/labelled/skipped_L1.csv" in result.out


def test_quitting_at_the_start_writes_no_file(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    assert run(world, ["q"]).status == 0
    assert list(world.labelled.iterdir()) == []


def test_the_end_of_the_input_and_ctrl_c_quit_without_losing_labels(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    clock = Clock()
    assert run(world, ["m", ""], clock=clock).status == 0
    assert len(world.labels()) == 1
    answers = iter(["m", ""])

    def interrupt(prompt: str) -> str:
        try:
            return next(answers)
        except StopIteration:
            raise KeyboardInterrupt from None

    assert main(world.args(), input_fn=interrupt, print_fn=lambda text: None, now_fn=clock) == 0
    assert len(world.labels()) == 2


# Skipping.


def test_a_skipped_pair_is_written_to_the_skipped_file_and_left_out(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    clock = Clock()
    result = run(world, ["s", "bundle of two products", "m", "", "q"], clock=clock)
    order = expected_order(DEFAULT_PAIRS)
    assert world.skipped() == [
        {
            "pair_id": order[0],
            "reason": "bundle of two products",
            "skipped_at": "2026-11-12T09:00:01+06:00",
        }
    ]
    assert [row["pair_id"] for row in world.labels()] == [order[1]]
    assert "Skipped." in result.out
    again = run(world, ["q"], clock=clock)
    assert "Resuming: 1 labelled, 1 skipped, 3 to do." in again.out
    assert f"Pair 3 of 5   {order[2]}" in again.out


def test_an_empty_reason_cancels_the_skip(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    result = run(world, ["s", "", "m", "", "q"])
    assert world.skipped() == []
    assert "Not skipped." in result.out
    assert len(world.labels()) == 1


def test_a_labelled_pair_cannot_be_skipped(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    result = run(world, ["m", "", "b", "s", "q"])
    assert "This pair is labelled; a labelled pair cannot be skipped." in result.out
    assert world.skipped() == []


# Going back.


def test_back_shows_the_previous_pair_and_a_new_label_adds_a_row(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    order = expected_order(DEFAULT_PAIRS)
    result = run(world, ["m", "", "b", "n", "size_differs", "q"])
    rows = world.labels()
    assert [(row["pair_id"], row["label"], row["note"]) for row in rows] == [
        (order[0], "match", ""),
        (order[0], "non_match", "size_differs"),
    ]
    assert "Current label: match" in result.out
    # After the correction the session goes on with the pending pair.
    assert result.out.count(f"Pair 2 of 5   {order[1]}") == 2


def test_an_unchanged_label_writes_nothing(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    result = run(world, ["n", "size_differs", "b", "n", "=", "q"])
    assert len(world.labels()) == 1
    assert "Unchanged; nothing was written." in result.out


def test_equals_keeps_the_current_note_and_a_changed_label_keeps_it_too(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    run(world, ["n", "unbranded;multipack # two bags", "b", "u", "=", "q"])
    rows = world.labels()
    assert [(row["label"], row["note"]) for row in rows] == [
        ("non_match", "unbranded;multipack # two bags"),
        ("unsure", "unbranded;multipack # two bags"),
    ]


def test_equals_keeps_cross_script_without_duplicating_it(tmp_path: Path) -> None:
    world = make_world(tmp_path, [BANGLA_PAIR, pair("1001", "2001")])
    run(world, ["m", "unbranded", "b", "u", "=", "q"])
    assert [row["note"] for row in world.labels()] == ["unbranded;cross_script"] * 2


def test_back_twice_goes_two_pairs_back_and_forward_again(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    order = expected_order(DEFAULT_PAIRS)
    result = run(world, ["m", "", "n", "", "b", "b", "m", "", "n", "", "q"])
    assert len(world.labels()) == 2  # both were left unchanged
    shown = [line for line in result.out.splitlines() if line.startswith("Pair ")]
    assert [line.split()[1] for line in shown] == ["1", "2", "3", "2", "1", "2", "3"]
    assert order[0] in shown[0]


def test_back_at_the_start_says_there_is_nothing_earlier(tmp_path: Path) -> None:
    result = run(make_world(tmp_path), ["b", "q"])
    assert "There is no earlier pair to go back to." in result.out


def test_back_cannot_go_before_the_first_pair(tmp_path: Path) -> None:
    result = run(make_world(tmp_path), ["m", "", "b", "b", "q"])
    assert result.out.count("There is no earlier pair to go back to.") == 1


def test_back_reaches_pairs_labelled_in_an_earlier_session(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    clock = Clock()
    run(world, ["m", "", "n", "", "q"], clock=clock)
    result = run(world, ["b", "u", "", "q"], clock=clock)
    order = expected_order(DEFAULT_PAIRS)
    assert world.labels()[-1]["pair_id"] == order[1]
    assert world.labels()[-1]["label"] == "unsure"
    assert "Current label: non_match" in result.out


def test_a_corrected_pair_appears_once_in_the_history_after_a_resume(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    clock = Clock()
    run(world, ["m", "", "b", "n", "", "q"], clock=clock)  # two rows for the first pair
    result = run(world, ["b", "b", "q"], clock=clock)
    assert result.out.count("There is no earlier pair to go back to.") == 1


def test_the_current_label_of_a_pair_is_its_latest_row_after_a_resume(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    clock = Clock()
    run(world, ["m", "", "b", "n", "", "q"], clock=clock)
    result = run(world, ["q"], clock=clock)
    assert "Resuming: 1 labelled, 0 skipped, 4 to do." in result.out
    again = run(world, ["b", "n", "=", "q"], clock=clock)
    assert "Unchanged; nothing was written." in again.out


# Starting conditions.


@pytest.mark.parametrize("labeller", ["pretom", "l1", "L", "L1x", ""])
def test_the_labeller_must_be_l_and_digits(tmp_path: Path, labeller: str) -> None:
    world = make_world(tmp_path)
    result = run(world, [], labeller=labeller)
    assert result.status == 1
    assert "must be L and digits" in result.out
    assert list(world.labelled.iterdir()) == []


def test_the_labeller_option_is_required() -> None:
    with pytest.raises(SystemExit):
        main([])


def test_the_version_comes_from_the_guidelines(tmp_path: Path) -> None:
    text = "Version: 0.1\n\n## Version history\n\n- 0.1 (2026-11-04): pilot draft.\n"
    world = make_world(tmp_path, SINGLE, guidelines=text)
    run(world, ["m", ""])
    assert world.labels()[0]["guidelines_version"] == "0.1"


def test_a_version_missing_from_the_history_stops_the_tool(tmp_path: Path) -> None:
    text = "Version: 0.3\n\n## Version history\n\n- 0.1 (2026-11-04): pilot draft.\n"
    world = make_world(tmp_path, SINGLE, guidelines=text)
    result = run(world, ["m", ""])
    assert result.status == 1
    assert "the guidelines version 0.3 is not in its version history" in result.out
    assert list(world.labelled.iterdir()) == []


def test_unreadable_guidelines_stop_the_tool(tmp_path: Path) -> None:
    world = make_world(tmp_path, SINGLE, guidelines="No version line here\n")
    result = run(world, [])
    assert result.status == 1
    assert "cannot read the guidelines" in result.out


def test_a_missing_candidates_file_stops_the_tool_and_says_how_to_make_it(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    world.candidates.unlink()
    result = run(world, [])
    assert result.status == 1
    assert "candidates.csv was not found; make it with python -m src.label.candidates" in result.out


def test_a_candidates_file_without_pair_ids_stops_the_tool(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    world.candidates.write_text("category\nrice\n", encoding="utf-8")
    result = run(world, [])
    assert result.status == 1
    assert "no pair_id column" in result.out


def test_a_pair_with_a_listing_missing_from_data_raw_stops_the_tool(tmp_path: Path) -> None:
    world = make_world(tmp_path, [pair("1001", "9999")])
    result = run(world, [])
    assert result.status == 1
    assert "is not in data/raw" in result.out


def test_a_malformed_pair_id_in_the_candidates_stops_the_tool(tmp_path: Path) -> None:
    world = make_world(tmp_path, ["nonsense"])
    assert run(world, []).status == 1


def test_a_clock_that_goes_backwards_stops_the_tool_before_it_writes(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    start = datetime(2026, 11, 12, 9, 0, 0, tzinfo=BANGLA_TIME)
    readings = iter([start + timedelta(minutes=5), start + timedelta(minutes=6), start])

    result = run_with_clock(world, ["m", "", "n", ""], lambda: next(readings))
    assert result.status == 1
    assert "earlier than the last row (2026-11-12T09:06:00+06:00); nothing was saved." in result.out
    assert [row["label"] for row in world.labels()] == ["match"]


def run_with_clock(world: World, answers: list[str], clock) -> Run:  # noqa: ANN001
    queue = list(answers)
    shown: list[str] = []

    def fake_input(prompt: str) -> str:
        if not queue:
            raise EOFError
        return queue.pop(0)

    status = main(world.args(), input_fn=fake_input, print_fn=shown.append, now_fn=clock)
    return Run(status, "\n".join(shown))


def test_a_file_written_in_the_future_stops_the_tool(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    row = existing_row(DEFAULT_PAIRS[0], labelled_at="2026-11-12T09:10:00+06:00")
    (world.labelled / "labels_L1.csv").write_bytes(label_file([row]))
    result = run(world, [], clock=Clock())  # the clock reads 09:00
    assert result.status == 1
    assert "is in the future; run the validator" in result.out


def pair_id_of(value: str) -> dict[str, str]:
    left, right = value.split("|")
    return {
        "pair_id": value,
        "left_source": left.split(":")[0],
        "left_id": left.split(":")[1],
        "right_source": right.split(":")[0],
        "right_id": right.split(":")[1],
    }


def existing_row(pair_text: str, **changes: str) -> dict[str, str]:
    row = label_row("1001", "2001", labelled_at="2026-11-10T10:00:00+06:00")
    row.update(pair_id_of(pair_text))
    row.update(changes)
    return row


@pytest.mark.parametrize(
    ("make", "message"),
    [
        pytest.param(
            lambda p: label_file([existing_row(p, labeller="L2")]),
            "the labeller is 'L2', not L1",
            id="labeller",
        ),
        pytest.param(
            lambda p: label_file([existing_row(p, label="maybe")]),
            "the label 'maybe' is not allowed",
            id="label",
        ),
        pytest.param(
            lambda p: label_file([existing_row(pair("9", "9"))]),
            "the pair is not in candidates.csv",
            id="not-a-candidate",
        ),
        pytest.param(
            lambda p: label_file([existing_row(p, labelled_at="yesterday")]),
            "must have the form",
            id="time",
        ),
        pytest.param(
            lambda p: csv_bytes(LABEL_COLUMNS[:-1], [["x"] * 9]),
            "does not have the expected header",
            id="header",
        ),
        pytest.param(
            lambda p: label_file([existing_row(p)]).rstrip(b"\n"),
            "does not end with a line end",
            id="partial-last-row",
        ),
        pytest.param(
            lambda p: b"\xef\xbb\xbf" + label_file([existing_row(p)]),
            "byte-order mark",
            id="bom",
        ),
        pytest.param(
            lambda p: label_file([existing_row(p)]).replace(b"match", b"m\xffatch"),
            "not valid UTF-8",
            id="utf8",
        ),
        pytest.param(
            lambda p: csv_bytes(LABEL_COLUMNS, [["x"] * 9]),
            "wrong number of fields",
            id="fields",
        ),
    ],
)
def test_a_malformed_label_file_stops_the_tool_and_is_left_unchanged(
    tmp_path: Path,
    make,
    message: str,  # noqa: ANN001
) -> None:
    world = make_world(tmp_path)
    path = world.labelled / "labels_L1.csv"
    path.write_bytes(make(DEFAULT_PAIRS[0]))
    before = path.read_bytes()
    result = run(world, ["m", ""])
    assert result.status == 1
    assert message in result.out
    assert path.read_bytes() == before


def test_a_malformed_skipped_file_stops_the_tool(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    (world.labelled / "skipped_L1.csv").write_bytes(
        csv_bytes(SKIPPED_COLUMNS, [["nonsense", "r", "2026-11-10T10:00:00+06:00"]])
    )
    result = run(world, [])
    assert result.status == 1
    assert "skipped_L1.csv, row 2: the pair is not in candidates.csv" in result.out


# Only the labeller's own files.


def test_the_tool_never_opens_another_labellers_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = make_world(tmp_path)
    (world.labelled / "labels_L2.csv").write_bytes(b"not a label file at all \xff\xfe")
    (world.labelled / "skipped_L2.csv").mkdir()  # opening it would fail
    opened = []
    for name in ("open", "read_bytes", "read_text"):
        original = getattr(Path, name)

        def spy(self, *args, _original=original, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
            opened.append(str(self))
            return _original(self, *args, **kwargs)

        monkeypatch.setattr(Path, name, spy)
    result = run(world, ["m", "", "q"])
    assert result.status == 0
    assert opened
    assert not any("L2" in path for path in opened)
    assert (world.labelled / "labels_L2.csv").read_bytes() == b"not a label file at all \xff\xfe"


def test_two_labellers_keep_separate_files(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    clock = Clock()
    run(world, ["m", "", "q"], labeller="L1", clock=clock)
    run(world, ["n", "", "q"], labeller="L2", clock=clock)
    assert [row["label"] for row in world.labels("L1")] == ["match"]
    assert [row["label"] for row in world.labels("L2")] == ["non_match"]
    assert [row["labeller"] for row in world.labels("L1")] == ["L1"]
    assert [row["labeller"] for row in world.labels("L2")] == ["L2"]
    # L2 starts at the first pair too, as L1's labels are not read.
    assert world.labels("L1")[0]["pair_id"] == world.labels("L2")[0]["pair_id"]


def test_the_tool_changes_none_of_its_inputs(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    inputs = [path for path in tmp_path.rglob("*") if path.is_file()]
    before = {path: path.read_bytes() for path in inputs}
    run(world, ["m", "", "s", "bundle", "n", "size_differs", "q"])
    assert {path: path.read_bytes() for path in inputs} == before


# What the labeller must not see.


def everything_shown_and_saved(world: World, result: Run) -> str:
    saved = "".join(
        path.read_text(encoding="utf-8") for path in world.labelled.iterdir() if path.is_file()
    )
    text = result.out + "\n".join(result.prompts) + saved
    return text.replace(str(world.root), "<folder>")  # the folder name holds the test name


def test_neither_the_price_nor_a_candidate_score_is_shown_or_saved(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    result = run(world, ["m", "", "n", "size_differs", "u", "", "s", "bundle", "b", "q"])
    text = everything_shown_and_saved(world, result)
    for secret in (*PRICES.values(), "7777", "8888", *POISON):
        assert secret not in text, secret
    assert "price" not in text.lower()
    assert "jaccard" not in text.lower()
    assert "stratum" not in text.lower()
    assert "similarity" not in text.lower()


def test_no_reading_of_the_size_by_n3_is_shown_or_saved(tmp_path: Path) -> None:
    # N3 reads these as 1500 ml and as 2 x 345 ml (a total of 690 ml); none of those figures
    # appears in the titles, so they would show only if the tool displayed N3's reading.
    listings = [
        ("pandamart", "1", "Test Oil 2 x 345ml", "", "cooking_oil", "english"),
        ("meenabazar", "2", "TEST OIL 1.5L", "No Brand", "cooking_oil", "english"),
    ]
    world = make_world(tmp_path, [pair("1", "2")], listings)
    result = run(world, ["n", "size_differs", "q"])
    text = everything_shown_and_saved(world, result)
    for figure in ("1500", "690", "volume", "weight", "different_amount", "same_total", "N3"):
        assert figure not in text, figure
    assert "TEST OIL 1.5L" in text
    assert "Test Oil 2 x 345ml" in text


def test_the_displayed_text_has_only_the_allowed_fields(tmp_path: Path) -> None:
    world = make_world(tmp_path, SINGLE)
    result = run(world, ["q"])
    shown = result.out
    assert "title:" in shown and "brand field:" in shown and "source:" in shown
    for hidden in ("example.invalid", "english", "script", "price", "collected", "romanised"):
        assert hidden not in shown.lower(), hidden


def test_importing_the_tool_loads_no_size_parser_feature_code_or_validator() -> None:
    code = (
        "import sys\n"
        "import src.label.tool\n"
        "banned = ['src.normalise.sizes', 'src.label.features', 'src.label.candidates',\n"
        "          'src.label.validate', 'src.normalise.report', 'src.normalise.prepare',\n"
        "          'src.normalise.text_clean']\n"
        "print(','.join(name for name in banned if name in sys.modules))\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code], cwd=REPO_DIR, capture_output=True, text=True, check=True
    )
    assert done.stdout.strip() == ""


def test_the_tool_names_nothing_that_belongs_to_prices_or_n3() -> None:
    tree = ast.parse((REPO_DIR / "src" / "label" / "tool.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.alias):
            names.add(node.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
    for name in names:
        lowered = name.lower()
        for forbidden in (
            "price",
            "parse_size",
            "parse_listing_size",
            "sizeresult",
            "features",
            "jaccard",
        ):
            assert forbidden not in lowered, name
    assert "src.label.candidates" not in names
    assert "src.label.validate" not in names


# The files the tool writes pass the validator.


def test_every_file_the_tool_writes_passes_the_validator(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    pairs = expected_order(DEFAULT_PAIRS)
    clock = Clock()
    run(
        world,
        [
            "m",
            "# same product",
            "n",
            "unbranded;size_differs # five kilos against one",
            "s",
            "bundle",
            "u",
            "brand_missing",
            "b",
            "m",
            "=",
            "q",
        ],
        clock=clock,
    )
    run(world, ["n", "variant_differs", "b", "q"], clock=clock)
    ctx = load_context(
        raw_dir=world.raw,
        candidates_path=world.candidates,
        guidelines_path=world.guidelines,
        now=NOW,
    )
    paths = sorted(world.labelled.glob("*.csv"))
    assert [path.name for path in paths] == ["labels_L1.csv", "skipped_L1.csv"]
    for result in validate_files(paths, ctx):
        assert [problem.describe() for problem in result.errors] == []
    assert len(world.labels()) >= 4
    assert pairs[0] in {row["pair_id"] for row in world.labels() + world.skipped()}


def test_cross_script_written_by_the_tool_satisfies_the_validator(tmp_path: Path) -> None:
    world = make_world(tmp_path, [BANGLA_PAIR])
    run(world, ["m", ""])
    ctx = load_context(
        raw_dir=world.raw,
        candidates_path=world.candidates,
        guidelines_path=world.guidelines,
        now=NOW,
    )
    (result,) = validate_files([world.labelled / "labels_L1.csv"], ctx)
    assert result.errors == []


def test_the_timestamps_written_have_the_agreed_form(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    run(world, ["m", "", "n", "", "u", ""])
    for row in world.labels():
        assert parse_timestamp(row["labelled_at"], NOW).utcoffset() == timedelta(hours=6)


def test_a_labelled_session_on_the_listings_of_the_builders_uses_every_default_listing() -> None:
    # A guard for this file: the default pairs name listings that exist in the builders.
    ids = {(item[0], item[1]) for item in LISTINGS}
    for text in DEFAULT_PAIRS:
        for part in text.split("|"):
            source, listing_id = part.split(":")
            assert (source, listing_id) in ids


def test_a_tool_error_reports_the_message_without_a_traceback(tmp_path: Path) -> None:
    with pytest.raises(ToolError, match="must be L and digits"):
        Session(make_world(tmp_path).config("bad"))
