"""Checks that the code follows the project's rules about regular expressions and characters.

The rules are described in CLAUDE.md. Each file is parsed, and only string literals that are not
docstrings are inspected. Comments never appear in the parse tree, and docstrings are skipped,
so comments and docstrings may mention the forbidden constructs and may contain visible Bangla.

Regular-expression rules (checked for src/):
    * no \\d, \\D, \\w, \\W, \\b or \\B, no inline (?a flag and no re.ASCII.

Character rules (checked for src/ and tests/):
    * a string literal must not contain a non-ASCII character; write it as an escape instead;
    * every string literal, and every bn(...) call with constant arguments, that contains Bangla
      must have a comment on the same line that shows the text in readable Bangla.
"""

import ast
import io
import textwrap
import tokenize
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_DIR / "src"
TESTS_DIR = REPO_DIR / "tests"

# Regular-expression escapes that must not be used (a backslash followed by a letter).
FORBIDDEN_ESCAPES = ("\\d", "\\D", "\\w", "\\W", "\\b", "\\B")
# An unprefixed "\b" in an ordinary string literal silently becomes this character.
BACKSPACE = "\x08"
ASCII_FLAG_NAMES = {"ASCII", "A"}
# The Bengali Unicode block.
BANGLA_BLOCK = range(0x0980, 0x0A00)


def _has_bangla(text: str) -> bool:
    return any(ord(char) in BANGLA_BLOCK for char in text)


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
    """Return the regular-expression rule violations found in one string literal."""
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


def find_regex_violations(source: str) -> list[str]:
    """Return a description of each regular-expression rule violation in the Python source."""
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


def _comments_by_line(source: str) -> dict[int, str]:
    """Return the text of the comment on each line that has one."""
    comments: dict[int, str] = {}
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            comments[token.start[0]] = token.string
    return comments


def _constant_bn_text(node: ast.AST) -> str | None:
    """Return the text built by a bn(...) call whose arguments are all integer constants."""
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "bn"
        and not node.keywords
        and node.args
        and all(isinstance(arg, ast.Constant) and isinstance(arg.value, int) for arg in node.args)
    ):
        return None
    return "".join(chr(arg.value) for arg in node.args if isinstance(arg, ast.Constant))


def _docstring_positions(tree: ast.AST) -> set[tuple[int, int]]:
    """Return the (line, column) where each docstring starts."""
    positions: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                positions.add((first.value.lineno, first.value.col_offset))
    return positions


def _non_ascii_source_problems(source: str, docstrings: set[tuple[int, int]]) -> list[str]:
    """Find non-ASCII characters written literally in string literals that are not docstrings.

    This looks at the text as written (the tokens), not at the value of the string, because an
    escape such as a backslash, "u" and four hex digits is ASCII in the source even though its
    value is not.
    """
    problems = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        is_string = token.type in (tokenize.STRING, tokenize.FSTRING_MIDDLE)
        if not is_string or token.start in docstrings:
            continue
        non_ascii = sorted({f"U+{ord(char):04X}" for char in token.string if ord(char) > 127})
        if non_ascii:
            problems.append(
                f"line {token.start[0]}: string contains non-ASCII characters "
                f"{', '.join(non_ascii)}; write them as escapes"
            )
    return problems


def find_character_violations(source: str) -> list[str]:
    """Return a description of each character rule violation in the Python source."""
    tree = ast.parse(source)
    docstrings = _docstring_constants(tree)
    comments = _comments_by_line(source)
    problems = _non_ascii_source_problems(source, _docstring_positions(tree))
    for node in ast.walk(tree):
        text: str | None = None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings:
                continue
            text = node.value
        else:
            text = _constant_bn_text(node)
        if text is not None and _has_bangla(text):
            end_line = getattr(node, "end_lineno", None) or node.lineno  # type: ignore[attr-defined]
            lines = range(node.lineno, end_line + 1)  # type: ignore[attr-defined]
            if not any(_has_bangla(comments.get(line, "")) for line in lines):
                problems.append(
                    f"line {node.lineno}: Bangla text needs a comment on the same line "  # type: ignore[attr-defined]
                    "that shows it in readable Bangla"
                )
    return problems


# Building the test snippets without typing escapes or Bangla into this file.
BACKSLASH = chr(92)
KA = chr(0x0995)  # the Bangla letter KA
E_ACUTE = chr(0x00E9)


def _violations_in(snippet: str) -> list[str]:
    return find_regex_violations(textwrap.dedent(snippet))


def _character_violations_in(snippet: str) -> list[str]:
    return find_character_violations(textwrap.dedent(snippet))


# Tests of the regular-expression scanner, on invented snippets.


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


# Tests of the character scanner, on invented snippets.


def test_non_ascii_character_in_a_string_literal_is_flagged() -> None:
    problems = _character_violations_in(f'X = "{E_ACUTE}"\n')
    assert len(problems) == 1
    assert "U+00E9" in problems[0]


def test_non_ascii_character_inside_an_f_string_literal_part_is_flagged() -> None:
    problems = _character_violations_in(f'NAME = "x"\nX = f"{E_ACUTE}{{NAME}}"\n')
    assert len(problems) == 1


def test_visible_non_ascii_text_is_allowed_in_docstrings_and_comments() -> None:
    problems = _character_violations_in(
        f'"""Module docstring with {KA}."""\n\n# A comment with {KA}.\n\n\n'
        f'def function() -> None:\n    """Function docstring with {KA}."""\n'
    )
    assert problems == []


def test_escaped_non_bangla_literal_needs_no_comment() -> None:
    assert _character_violations_in(f'X = "{BACKSLASH}u00e9"\n') == []


def test_escaped_bangla_literal_without_a_comment_is_flagged() -> None:
    problems = _character_violations_in(f'X = "{BACKSLASH}u0995"\n')
    assert len(problems) == 1
    assert "comment" in problems[0]


def test_escaped_bangla_literal_with_a_non_bangla_comment_is_flagged() -> None:
    assert len(_character_violations_in(f'X = "{BACKSLASH}u0995"  # the letter KA\n')) == 1


def test_escaped_bangla_literal_with_a_bangla_comment_is_accepted() -> None:
    assert _character_violations_in(f'X = "{BACKSLASH}u0995"  # {KA} the letter KA\n') == []


def test_bangla_literal_inside_a_multi_line_expression_uses_its_own_line() -> None:
    source = f'ITEMS = [\n    "{BACKSLASH}u0995",  # {KA}\n    "{BACKSLASH}u0995",\n]\n'
    problems = _character_violations_in(source)
    assert len(problems) == 1
    assert "line 3" in problems[0]


def test_bn_call_with_bangla_needs_a_bangla_comment() -> None:
    assert len(_character_violations_in("X = bn(0x0995)\n")) == 1
    assert _character_violations_in(f"X = bn(0x0995)  # {KA}\n") == []


def test_bn_call_without_bangla_needs_no_comment() -> None:
    assert _character_violations_in("X = bn(0x00E9)\n") == []


def test_bn_call_with_non_constant_arguments_is_not_checked() -> None:
    assert _character_violations_in("X = bn(*CODE_POINTS)\n") == []


# The real checks.


def _python_files(*directories: Path) -> list[Path]:
    files = sorted(path for directory in directories for path in directory.rglob("*.py"))
    assert files, f"no Python files found under {directories}"
    return files


def test_source_files_follow_the_regular_expression_rules() -> None:
    violations = [
        f"{path.relative_to(REPO_DIR)}: {problem}"
        for path in _python_files(SRC_DIR)
        for problem in find_regex_violations(path.read_text(encoding="utf-8"))
    ]
    assert violations == []


def test_source_and_test_files_follow_the_character_rules() -> None:
    violations = [
        f"{path.relative_to(REPO_DIR)}: {problem}"
        for path in _python_files(SRC_DIR, TESTS_DIR)
        for problem in find_character_violations(path.read_text(encoding="utf-8"))
    ]
    assert violations == []
