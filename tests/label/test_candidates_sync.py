"""Tests that src.label.candidates agrees with the description in docs/data_entry_rules.md.

The columns of data/interim/candidates.csv, the values of its strategy and size relation columns,
the names of the provisional strata and the command-line options are all described in the
section "Candidate pairs". If the code or the document changes alone, a test here fails.
"""

import re
from typing import get_args

import pytest

from src.label.candidates import CANDIDATE_COLUMNS, STRATA, STRATEGY_PILOT, main
from src.label.features import SizeRelation
from src.label.records import REPO_DIR
from tests.label.doc_readers import read, section, table_rows

ENTRY_RULES = REPO_DIR / "docs" / "data_entry_rules.md"
_BACKTICKED = re.compile(r"`([^`]+)`")


def candidate_section() -> list[str]:
    lines = section(read(ENTRY_RULES), "Candidate pairs")
    assert any(line.startswith("|") for line in lines), "the table of columns was not found"
    return lines


def test_the_columns_are_those_of_the_entry_rules_in_the_same_order() -> None:
    documented = tuple(
        _BACKTICKED.fullmatch(row[0]).group(1) for row in table_rows(candidate_section())
    )
    assert documented == CANDIDATE_COLUMNS


def test_every_documented_column_has_a_meaning() -> None:
    for row in table_rows(candidate_section()):
        assert len(row) == 2
        assert len(row[1]) > 10, row[0]


def test_the_strategy_value_is_documented() -> None:
    assert f"`{STRATEGY_PILOT}`" in "\n".join(candidate_section())


@pytest.mark.parametrize("value", get_args(SizeRelation))
def test_every_size_relation_is_documented(value: str) -> None:
    assert f"`{value}`" in "\n".join(candidate_section())


@pytest.mark.parametrize("name", STRATA)
def test_every_stratum_is_named_in_the_entry_rules(name: str) -> None:
    assert f"`{name}`" in "\n".join(candidate_section())


def test_the_options_in_the_entry_rules_exist(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    help_text = capsys.readouterr().out
    text = "\n".join(candidate_section())
    documented = set(re.findall(r"(?<![A-Za-z-])(--[a-z]+(?:-[a-z]+)*)", text))
    assert documented == {"--replace", "--preview-strata", "--high", "--low", "--price-min"}
    for option in documented:
        assert option in help_text
