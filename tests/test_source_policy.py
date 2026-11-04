"""Checks that the source code follows the regular-expression rules in CLAUDE.md.

The scanner parses each file and inspects only string literals that are not docstrings.
Comments never appear in the parse tree, so comments and docstrings may mention the forbidden
constructs when they explain why those are avoided.
"""

import ast
import textwrap
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"

# Regular-expression escapes that must not be used (a backslash followed by a letter).
FORBIDDEN_ESCAPES = ("\\d", "\\D", "\\w", "\\W", "\\b", "\\B")
# An unprefixed "\b" in an ordinary string literal silently becomes this character.
BACKSPACE = "\x08"
ASCII_FLAG_NAMES = {"ASCII", "A"}


def _docstring_constants(tree: ast.AST) -> set[int]:
    """Return the ids of the string constants that are docstrings."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                ids.add(id(first.value))
    return ids


def _literal_problems(node: ast.Constant) -> list[str]:
    """Return the rule violations found in one string literal."""
    value = str(node.value)
    problems = [
        f"line {node.lineno}: string contains {escape}"
        for escape in FORBIDDEN_ESCAPES
        if escape in value
    ]
    if BACKSPACE in value:
        problems.append(f"line {node.lineno}: string contains a backspace character")
    if "(?a" in value:
        problems.append(f"line {node.lineno}: string contains the inline ASCII flag (?a")
    return problems


def find_violations(source: str) -> list[str]:
    """Return a description of each rule violation in the given Python source."""
    tree = ast.parse(source)
    docstrings = _docstring_constants(tree)
    problems: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in docstrings:
                problems.extend(_literal_problems(node))
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "re"
            and node.attr in ASCII_FLAG_NAMES
        ):
            problems.append(f"line {node.lineno}: use of re.{node.attr}")
        elif isinstance(node, ast.ImportFrom) and node.module == "re":
            problems.extend(
                f"line {node.lineno}: import of {alias.name} from re"
                for alias in node.names
                if alias.name in ASCII_FLAG_NAMES
            )
    return problems


def _violations_in(snippet: str) -> list[str]:
    return find_violations(textwrap.dedent(snippet))


# Tests of the scanner itself, on invented snippets.


def test_digit_class_in_a_pattern_is_flagged() -> None:
    problems = _violations_in(
        r"""
        import re
        PATTERN = re.compile(r"\d+")
        """
    )
    assert len(problems) == 1
    assert "\\d" in problems[0]


def test_word_boundary_in_a_raw_pattern_is_flagged() -> None:
    problems = _violations_in(
        r"""
        PATTERN = r"\bkg\b"
        """
    )
    assert len(problems) == 1
    assert "\\b" in problems[0]


def test_unprefixed_word_boundary_becomes_a_backspace_and_is_flagged() -> None:
    problems = _violations_in(
        r"""
        PATTERN = "\bkg"
        """
    )
    assert len(problems) == 1
    assert "backspace" in problems[0]


def test_forbidden_escape_inside_an_f_string_is_flagged() -> None:
    problems = _violations_in(
        r"""
        WORD = "a-z"
        PATTERN = rf"(?<![{WORD}])\d"
        """
    )
    assert len(problems) == 1


def test_inline_ascii_flag_is_flagged() -> None:
    problems = _violations_in(
        r"""
        PATTERN = r"(?a)abc"
        """
    )
    assert len(problems) == 1


def test_ascii_flag_attribute_is_flagged() -> None:
    for flag in ("ASCII", "A"):
        problems = _violations_in(f"import re\nre.compile('a', re.{flag})\n")
        assert len(problems) == 1, flag


def test_ascii_flag_import_is_flagged() -> None:
    assert len(_violations_in("from re import ASCII\n")) == 1


def test_comments_and_docstrings_may_mention_forbidden_constructs() -> None:
    problems = _violations_in(
        r'''
        r"""Module docstring that mentions \d and re.ASCII."""

        # Never use \d here, and never use re.ASCII.


        def function() -> None:
            r"""Function docstring that mentions \w, \b and (?a)."""


        class Example:
            r"""Class docstring that mentions \D."""
        '''
    )
    assert problems == []


def test_allowed_patterns_are_not_flagged() -> None:
    problems = _violations_in(
        r"""
        import re
        PATTERN = re.compile(r"[0-9]+(?:\.[0-9]+)?", re.IGNORECASE)
        """
    )
    assert problems == []


# The real check: every Python file under src/.


def test_source_files_follow_the_regular_expression_rules() -> None:
    files = sorted(SRC_DIR.rglob("*.py"))
    assert files, f"no Python files found under {SRC_DIR}"
    violations = [
        f"{path.relative_to(SRC_DIR.parent)}: {problem}"
        for path in files
        for problem in find_violations(path.read_text(encoding="utf-8"))
    ]
    assert violations == []
