"""Tests that src.label.records agrees with the documents it mirrors.

The documents are docs/labelling_guidelines.md, docs/data_entry_rules.md and CLAUDE.md. If one
of them changes without records.py (or the other way round), a test here fails and names the
difference. Each reader fails with a clear message if the part of the document it reads is no
longer in the expected form, so that a change of wording is noticed instead of passing silently.

These tests read the real documents; they contain no listing text.
"""

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.collect.validate import parse_timestamp
from src.label import records
from src.label.records import (
    ADJUDICATION_COLUMNS,
    AUTOMATIC_TAGS,
    GUIDELINES_PATH,
    LABEL_COLUMNS,
    LABELLER_ID,
    LABELS,
    OVERLAP_COLUMNS,
    REPO_DIR,
    SKIPPED_COLUMNS,
    TAG_REQUIRED_LABELS,
    TAGS,
    PairKey,
    check_label_and_tags,
    labels_file_name,
    read_guidelines_version,
    read_version_history,
    skipped_file_name,
)
from tests.label.doc_readers import read, section, table_rows

ENTRY_RULES = REPO_DIR / "docs" / "data_entry_rules.md"
CLAUDE_MD = REPO_DIR / "CLAUDE.md"
_BACKTICKED = re.compile(r"`([^`]+)`")


def guideline_tag_rows() -> list[list[str]]:
    rows = table_rows(section(read(GUIDELINES_PATH), "Tags"))
    assert rows, "the Tags table of the guidelines was not found"
    return rows


# The labels and the version.


def test_the_labels_are_those_listed_in_the_guidelines() -> None:
    lines = section(read(GUIDELINES_PATH), "The three labels")
    listed = [match.group(1) for line in lines if (match := re.match(r"- `([a-z_]+)`:", line))]
    assert tuple(listed) == LABELS


def test_the_version_line_is_the_latest_entry_of_the_version_history() -> None:
    assert read_guidelines_version() == read_version_history()[-1]


def test_the_version_history_has_no_repeated_version() -> None:
    history = read_version_history()
    assert len(set(history)) == len(history)


def test_the_version_history_only_goes_up() -> None:
    def key(version: str) -> tuple[int, ...]:
        return tuple(int(part) for part in version.split("."))

    history = read_version_history()
    assert list(history) == sorted(history, key=key)


# The tags.


def test_the_tags_are_those_of_the_guidelines_table_in_the_same_order() -> None:
    listed = [_BACKTICKED.fullmatch(row[0]).group(1) for row in guideline_tag_rows()]
    assert tuple(listed) == TAGS


def test_the_automatic_tags_are_those_the_guidelines_say_the_tool_adds() -> None:
    automatic = {
        _BACKTICKED.fullmatch(row[0]).group(1)
        for row in guideline_tag_rows()
        if "adds this tag automatically" in row[1]
    }
    assert automatic == set(AUTOMATIC_TAGS)


def consistency_rule() -> str:
    lines = section(read(ENTRY_RULES), "Labelled data files")
    rules = [line for line in lines if line.startswith("- Consistency rules")]
    assert len(rules) == 1, "the 'Consistency rules' bullet of the entry rules was not found"
    return rules[0]


def test_the_tag_rules_are_those_of_the_entry_rules() -> None:
    text = consistency_rule()
    documented: dict[str, frozenset[str]] = {}
    group = re.search(r"the tags (.+?) require the label `([a-z_]+)`", text)
    assert group, "the sentence 'the tags ... require the label ...' was not found"
    for tag in _BACKTICKED.findall(group.group(1)):
        documented[tag] = frozenset({group.group(2)})
    single = re.search(r"`([a-z_]+)` requires `([a-z_]+)` or `([a-z_]+)`", text)
    assert single, "the sentence '`tag` requires `label` or `label`' was not found"
    documented[single.group(1)] = frozenset({single.group(2), single.group(3)})
    assert documented == TAG_REQUIRED_LABELS


def test_the_worked_examples_of_the_guidelines_pass_the_consistency_rules() -> None:
    rows = table_rows(section(read(GUIDELINES_PATH), "Worked examples"))
    assert len(rows) >= 10, "the worked examples table was not found"
    for left, right, label_cell, tags_cell in rows:
        label = _BACKTICKED.fullmatch(label_cell).group(1)
        tags = [tag for cell in _BACKTICKED.findall(tags_cell) for tag in cell.split(";")]
        assert check_label_and_tags(label, tags) == [], f"{left} / {right}"


def test_the_example_notes_in_the_guidelines_use_known_tags() -> None:
    text = "\n".join(section(read(GUIDELINES_PATH), "Tags"))
    for example in re.findall(r"for example `([a-z_;]+)`", text):
        assert set(example.split(";")) <= set(TAGS)


# The files and their columns.


def test_the_columns_of_each_labelled_file_are_those_of_the_entry_rules() -> None:
    rows = table_rows(section(read(ENTRY_RULES), "Labelled data files"))
    documented = {}
    for cells in rows:
        file_name = _BACKTICKED.search(cells[0]).group(1)
        documented[file_name] = tuple(_BACKTICKED.findall(cells[2]))
    assert documented == {
        labels_file_name("<labeller>"): LABEL_COLUMNS,
        "adjudication.csv": ADJUDICATION_COLUMNS,
        "overlap_sample.csv": OVERLAP_COLUMNS,
        skipped_file_name("<labeller>"): SKIPPED_COLUMNS,
    }


def entry_rule_bullet(start: str) -> str:
    lines = section(read(ENTRY_RULES), "Labelled data files")
    found = [line for line in lines if line.startswith(start)]
    assert len(found) == 1, f"the bullet starting {start!r} was not found"
    return found[0]


def test_the_pair_id_format_is_that_of_the_entry_rules() -> None:
    bullet = entry_rule_bullet("- `pair_id` is")
    documented = _BACKTICKED.findall(bullet)[1]
    assert (
        documented == PairKey("<left_source>", "<left_id>", "<right_source>", "<right_id>").pair_id
    )


def test_the_ordering_rule_of_the_entry_rules_is_still_worded_as_implemented() -> None:
    bullet = entry_rule_bullet("- `pair_id` is")
    assert "The source that comes first alphabetically is the left one" in bullet
    assert "if both are the same source, the smaller `listing_id` comes first" in bullet


def test_the_labeller_ids_in_the_entry_rules_are_allowed() -> None:
    bullet = entry_rule_bullet("- `labeller` is a pseudonymous ID")
    examples = re.search(r"such as `([A-Z0-9]+)` or `([A-Z0-9]+)`", bullet)
    assert examples, "the example labeller IDs were not found"
    assert all(LABELLER_ID.fullmatch(example) for example in examples.groups())


def test_the_timestamp_form_is_the_one_documented_for_the_label_files() -> None:
    bullet = entry_rule_bullet("- `labelled_at`, `adjudicated_at`")
    example = re.search(r"for example `([^`]+)`", bullet)
    assert example, "the example timestamp was not found"
    parse_timestamp(example.group(1), datetime(2030, 1, 1, tzinfo=UTC))


# The pair record in CLAUDE.md.


def claude_pair_record_bullets() -> list[str]:
    lines = read(CLAUDE_MD).splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("Pair record")]
    assert len(starts) == 1, "the 'Pair record' paragraph of CLAUDE.md was not found"
    bullets = []
    for line in lines[starts[0] + 1 :]:
        if line.startswith("- "):
            bullets.append(line)
        elif bullets:
            break
    assert bullets, "the pair record bullets of CLAUDE.md were not found"
    return bullets


def test_the_pair_record_of_claude_md_names_the_label_columns() -> None:
    names = []
    for bullet in claude_pair_record_bullets():
        names += _BACKTICKED.findall(re.split(r"[:(]", bullet[2:], maxsplit=1)[0])
    assert tuple(names) == LABEL_COLUMNS


def test_the_labels_in_claude_md_are_the_labels() -> None:
    bullet = next(b for b in claude_pair_record_bullets() if b.startswith("- `label`"))
    assert tuple(_BACKTICKED.findall(bullet.split("one of", 1)[1])) == LABELS


def test_the_version_line_is_named_in_claude_md_in_the_form_the_reader_expects() -> None:
    bullet = next(b for b in claude_pair_record_bullets() if b.startswith("- `guidelines_version`"))
    assert "`docs/labelling_guidelines.md`" in bullet
    assert "from the `Version:` line of that file" in bullet


def test_the_module_defines_no_tag_or_label_that_the_documents_lack() -> None:
    # A guard for new names: every public tuple of strings in records.py is one of the checked
    # ones, so that a definition added later also needs a sync test.
    checked = {
        "LABELS",
        "TAGS",
        "LABEL_COLUMNS",
        "ADJUDICATION_COLUMNS",
        "OVERLAP_COLUMNS",
        "SKIPPED_COLUMNS",
    }
    tuples = {
        name
        for name, value in vars(records).items()
        if name.isupper() and isinstance(value, tuple) and all(isinstance(v, str) for v in value)
    }
    assert tuples == checked


@pytest.mark.parametrize("path", [GUIDELINES_PATH, ENTRY_RULES, CLAUDE_MD])
def test_the_documents_exist_and_are_utf8(path: Path) -> None:
    assert read(path)
