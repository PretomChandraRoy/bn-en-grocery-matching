"""Readers of the Markdown documents, shared by the tests that compare code with the docs."""

from pathlib import Path


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(text: str, heading: str) -> list[str]:
    """Return the lines under a '## ' heading, up to the next '## ' heading."""
    lines = text.splitlines()
    assert f"## {heading}" in lines, f"no '## {heading}' heading found"
    start = lines.index(f"## {heading}") + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start:end]


def table_rows(lines: list[str]) -> list[list[str]]:
    """Return the cells of each body row of the Markdown tables in the lines."""
    rows = []
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue  # the separator row
        rows.append(cells)
    return rows[1:] if rows else rows  # the first row is the header
