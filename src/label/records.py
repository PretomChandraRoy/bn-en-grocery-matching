"""Shared definitions for the labelled data: files, columns, labels, tags and pair IDs.

The validator for labelled files, the candidate pair generator and the labelling tool all
import from here, so that they cannot disagree. The definitions mirror three documents:

* docs/data_entry_rules.md, section "Labelled data files": the files, their columns and the
  consistency rules;
* docs/labelling_guidelines.md: the labels, the tags and the "Version:" line;
* CLAUDE.md: the pair record.

tests/label/test_records_sync.py compares the definitions with those documents and fails if
they drift apart.

The project's regular-expression rules apply: digits are matched with [0-9], and neither the
word-character escape nor the word-boundary escape is used.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from src.collect.validate import has_bangla_letters

REPO_DIR = Path(__file__).resolve().parents[2]
LABELLED_DIR = REPO_DIR / "data" / "labelled"
INTERIM_DIR = REPO_DIR / "data" / "interim"
CANDIDATES_PATH = INTERIM_DIR / "candidates.csv"
GUIDELINES_PATH = REPO_DIR / "docs" / "labelling_guidelines.md"

# The three labels, in the order of the guidelines.
LABELS = ("match", "non_match", "unsure")

# The columns of each file in data/labelled, in order.
LABEL_COLUMNS = (
    "pair_id",
    "left_source",
    "left_id",
    "right_source",
    "right_id",
    "label",
    "note",
    "labeller",
    "labelled_at",
    "guidelines_version",
)
ADJUDICATION_COLUMNS = (
    "pair_id",
    "final_label",
    "final_note",
    "reason",
    "adjudicated_by",
    "adjudicated_at",
    "guidelines_version",
)
OVERLAP_COLUMNS = ("pair_id", "seed", "drawn_at")
SKIPPED_COLUMNS = ("pair_id", "reason", "skipped_at")

# A labeller is a pseudonymous ID such as L1 or L2, never a name, because the dataset will be
# public. Labellers are not renamed in the files.
LABELLER_ID = re.compile(r"L[0-9]+")

# The tags, in the order of the table in docs/labelling_guidelines.md.
TAGS = (
    "unbranded",
    "brand_missing",
    "brand_differs",
    "size_differs",
    "variant_differs",
    "multipack",
    "unit_kind_differs",
    "promo_quantity",
    "cross_script",
)
# Tags that the labelling tool adds itself; a labeller does not type them.
AUTOMATIC_TAGS = frozenset({"cross_script"})
# The labels that a tag allows. A tag that is not listed here goes with any label. These are
# the consistency rules of docs/data_entry_rules.md.
TAG_REQUIRED_LABELS: dict[str, frozenset[str]] = {
    "size_differs": frozenset({"non_match"}),
    "variant_differs": frozenset({"non_match"}),
    "brand_differs": frozenset({"non_match"}),
    "unit_kind_differs": frozenset({"non_match"}),
    "brand_missing": frozenset({"unsure", "non_match"}),
}

# A note holds semicolon-separated tags, then an optional comment after this separator. A
# comment with no tags is written "# comment".
COMMENT_SEPARATOR = " # "

_PART = r"[^:|\s]+"
_PAIR_ID = re.compile(rf"({_PART}):({_PART})\|({_PART}):({_PART})")
_DIGITS = re.compile(r"[0-9]+")
_VERSION_LINE = re.compile(r"Version: ([0-9]+\.[0-9]+)")
_HISTORY_LINE = re.compile(r"- ([0-9]+\.[0-9]+) \([0-9]{4}-[0-9]{2}-[0-9]{2}\): .+")
_HISTORY_HEADING = "## Version history"


def labels_file_name(labeller: str) -> str:
    """Return the name of a labeller's label file, for example labels_L1.csv."""
    return f"labels_{labeller}.csv"


def skipped_file_name(labeller: str) -> str:
    """Return the name of a labeller's file of skipped pairs, for example skipped_L1.csv."""
    return f"skipped_{labeller}.csv"


def _id_key(listing_id: str) -> tuple[int, int, str]:
    """Return a sort key for a listing_id: digit-only IDs by value, then the rest as text."""
    if _DIGITS.fullmatch(listing_id):
        return (0, int(listing_id), listing_id)
    return (1, 0, listing_id)


@dataclass(frozen=True)
class PairKey:
    """The two listings of a pair, as written in a pair_id.

    Attributes:
        left_source: The source of the left listing.
        left_id: The listing_id of the left listing.
        right_source: The source of the right listing.
        right_id: The listing_id of the right listing.
    """

    left_source: str
    left_id: str
    right_source: str
    right_id: str

    @property
    def pair_id(self) -> str:
        """The pair_id text: <left_source>:<left_id>|<right_source>:<right_id>."""
        return f"{self.left_source}:{self.left_id}|{self.right_source}:{self.right_id}"

    @property
    def is_same_source(self) -> bool:
        """Whether both listings come from the same source."""
        return self.left_source == self.right_source

    @property
    def is_canonical(self) -> bool:
        """Whether the listings are in the order the entry rules require.

        The source that comes first alphabetically is the left one. If both are from the same
        source, the smaller listing_id comes first.
        """
        if self.left_source != self.right_source:
            return self.left_source < self.right_source
        return _id_key(self.left_id) <= _id_key(self.right_id)


def make_pair_id(source_a: str, id_a: str, source_b: str, id_b: str) -> str:
    """Build the pair_id of two listings, putting them in the required order.

    Args:
        source_a: The source of one listing.
        id_a: Its listing_id.
        source_b: The source of the other listing.
        id_b: Its listing_id.

    Returns:
        The pair_id, whichever order the listings were given in.

    Raises:
        ValueError: If a source or an ID is empty or contains ":", "|" or white space.
    """
    first = PairKey(source_a, id_a, source_b, id_b)
    second = PairKey(source_b, id_b, source_a, id_a)
    key = first if first.is_canonical else second
    parse_pair_id(key.pair_id)  # rejects empty parts and the separator characters
    return key.pair_id


def parse_pair_id(pair_id: str) -> PairKey:
    """Split a pair_id into its four parts.

    The order of the two listings is not checked here; see PairKey.is_canonical.

    Args:
        pair_id: Text of the form <left_source>:<left_id>|<right_source>:<right_id>.

    Returns:
        The PairKey.

    Raises:
        ValueError: If the text does not have that form.
    """
    found = _PAIR_ID.fullmatch(pair_id)
    if found is None:
        raise ValueError(
            f"{ascii(pair_id)} must have the form <source>:<id>|<source>:<id>, with no space"
        )
    return PairKey(*found.groups())


@dataclass(frozen=True)
class ParsedNote:
    """A note split into its tags and its comment.

    Attributes:
        tags: The tags, in the order written.
        comment: The comment, without its separator; empty if there is none.
    """

    tags: tuple[str, ...]
    comment: str


def parse_note(note: str) -> ParsedNote:
    """Split a note into tags and comment.

    A note is semicolon-separated tags with no spaces, then optionally " # " and a comment. A
    note with only a comment starts with "# ". Whether the tags exist is not checked here; see
    check_label_and_tags.

    Args:
        note: The note field of a label.

    Returns:
        The ParsedNote.

    Raises:
        ValueError: If the tag part has a space, or an empty tag (for example "a;;b" or a
            trailing semicolon), or if a comment with no tags does not start with "# ".
    """
    if note.startswith("# "):
        return ParsedNote((), note[2:])
    tag_part, separator, comment = note.partition(COMMENT_SEPARATOR)
    if not tag_part:
        if separator:
            raise ValueError(f"a note with only a comment must start with '# ', not {ascii(note)}")
        return ParsedNote((), "")
    tags = tuple(tag_part.split(";"))
    if any(not tag for tag in tags):
        raise ValueError(f"the tags {ascii(tag_part)} contain an empty tag")
    if any(char.isspace() for char in tag_part):
        raise ValueError(
            f"the tags {ascii(tag_part)} must be separated by semicolons with no spaces"
        )
    return ParsedNote(tags, comment)


def sort_tags(tags: Sequence[str]) -> tuple[str, ...]:
    """Return the tags in the order of the guidelines' table; unknown tags go last, as given."""
    known = [tag for tag in TAGS if tag in tags]
    unknown = [tag for tag in tags if tag not in TAGS]
    return tuple(known + unknown)


def format_note(tags: Sequence[str], comment: str = "") -> str:
    """Build a note from tags and a comment, the inverse of parse_note.

    Args:
        tags: The tags, written in the order given.
        comment: An optional comment.

    Returns:
        "tag;tag # comment", "tag;tag", "# comment" or an empty string.
    """
    tag_part = ";".join(tags)
    if tag_part and comment:
        return f"{tag_part}{COMMENT_SEPARATOR}{comment}"
    if comment:
        return f"# {comment}"
    return tag_part


def check_label_and_tags(label: str, tags: Sequence[str]) -> list[str]:
    """Check a label and its tags against the consistency rules.

    The validator and the labelling tool both call this function.

    Args:
        label: The label.
        tags: The tags of the note.

    Returns:
        The problems found, as messages; empty if the label and tags are consistent.
    """
    problems = []
    if label not in LABELS:
        problems.append(f"{ascii(label)} is not one of {', '.join(LABELS)}")
    seen: set[str] = set()
    for tag in tags:
        if tag not in TAGS:
            problems.append(f"{ascii(tag)} is not a tag; the tags are {', '.join(TAGS)}")
        elif tag in seen:
            problems.append(f"the tag {tag} appears twice")
        elif label in LABELS and label not in TAG_REQUIRED_LABELS.get(tag, frozenset(LABELS)):
            allowed = " or ".join(name for name in LABELS if name in TAG_REQUIRED_LABELS[tag])
            problems.append(f"the tag {tag} requires the label {allowed}, not {label}")
        seen.add(tag)
    return problems


def cross_script(left_title: str, right_title: str) -> bool:
    """Return whether exactly one of the two titles contains Bangla letters.

    This is the rule for the cross_script tag. The digits U+09E6 to U+09EF are not letters, so
    they do not count.

    Args:
        left_title: The title of the left listing, as displayed.
        right_title: The title of the right listing, as displayed.

    Returns:
        True if the tag cross_script applies.
    """
    return has_bangla_letters(left_title) != has_bangla_letters(right_title)


def read_guidelines_version(path: Path = GUIDELINES_PATH) -> str:
    """Read the version from the "Version:" line of the labelling guidelines.

    Args:
        path: The guidelines file.

    Returns:
        The version, for example "0.2".

    Raises:
        ValueError: If the file has no line starting "Version:", more than one, or one that
            is not exactly "Version: " followed by two numbers separated by a dot.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    version_lines = [line for line in lines if line.startswith("Version:")]
    if len(version_lines) != 1:
        raise ValueError(f"{path.name} must have exactly one line starting 'Version:'")
    found = _VERSION_LINE.fullmatch(version_lines[0])
    if found is None:
        raise ValueError(f"the line {ascii(version_lines[0])} must have the form 'Version: 0.2'")
    return found.group(1)


def read_version_history(path: Path = GUIDELINES_PATH) -> tuple[str, ...]:
    """Read the versions listed under "Version history" in the labelling guidelines.

    Args:
        path: The guidelines file.

    Returns:
        The versions in the order listed, for example ("0.1", "0.2").

    Raises:
        ValueError: If there is no "Version history" heading or it lists no version. A list
            line has the form "- 0.2 (2026-11-05): what changed".
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if _HISTORY_HEADING not in lines:
        raise ValueError(f"{path.name} has no '{_HISTORY_HEADING}' heading")
    versions = []
    for line in lines[lines.index(_HISTORY_HEADING) + 1 :]:
        if line.startswith("#"):
            break
        found = _HISTORY_LINE.fullmatch(line)
        if found is not None:
            versions.append(found.group(1))
    if not versions:
        raise ValueError(f"the version history in {path.name} lists no version")
    return tuple(versions)
