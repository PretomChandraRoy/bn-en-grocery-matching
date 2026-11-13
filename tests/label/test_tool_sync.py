"""Tests that src.label.tool agrees with the description in docs/data_entry_rules.md.

The keys, the symbols of the note prompt and the command-line options are described in the section
"Labelling with the tool". If the code or the document changes alone, a test here fails.
"""

import re

import pytest

from src.label.records import REPO_DIR
from src.label.tool import ACTION_KEYS, BACK_TO_LABEL, HELP_KEY, KEEP_NOTE, main
from tests.label.doc_readers import read, section, table_rows

ENTRY_RULES = REPO_DIR / "docs" / "data_entry_rules.md"
_BACKTICKED = re.compile(r"`([^`]+)`")


def tool_section() -> list[str]:
    lines = section(read(ENTRY_RULES), "Labelling with the tool")
    assert any(line.startswith("|") for line in lines), "the table of keys was not found"
    return lines


def test_the_keys_are_those_of_the_entry_rules() -> None:
    documented = {_BACKTICKED.fullmatch(row[0]).group(1) for row in table_rows(tool_section())}
    assert documented == {*ACTION_KEYS, HELP_KEY}


def test_every_documented_key_has_a_meaning() -> None:
    for row in table_rows(tool_section()):
        assert len(row[1]) > 10, row[0]


def test_the_symbols_of_the_note_prompt_are_documented() -> None:
    text = "\n".join(tool_section())
    assert f"`{BACK_TO_LABEL}` goes back to choose the label again" in text
    assert f"`{KEEP_NOTE}` keeps the current note" in text


def test_the_options_in_the_entry_rules_exist(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    help_text = capsys.readouterr().out
    text = "\n".join(tool_section())
    documented = set(re.findall(r"(?<![A-Za-z-])(--[a-z]+(?:-[a-z]+)*)", text))
    assert documented == {
        "--labeller",
        "--raw-dir",
        "--labelled-dir",
        "--candidates",
        "--guidelines",
        "--width",
    }
    for option in documented:
        assert option in help_text


def test_the_documented_command_names_the_module() -> None:
    assert "python -m src.label.tool --labeller L1" in "\n".join(tool_section())
