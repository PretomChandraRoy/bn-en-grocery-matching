"""The command-line labelling tool.

    python -m src.label.tool --labeller L1

The tool shows one pair at a time, side by side, and records the labeller's decision in
data/labelled/labels_<labeller>.csv. It follows docs/labelling_guidelines.md, which the labeller
must read first; the tool prints the version of that file when it starts and stamps it on every
label.

What a labeller sees for each listing: the title exactly as collected, the brand field (which can
hold the manufacturer, not the brand), the size_value and size_unit fields only if they are
filled in, the source and the category. The shop's own category label (source_category) is not
shown: the guidelines list the category only. The labeller reads the size from the title, as the
guidelines require. The tool never shows the price, the reading of the size by the size parser
(N3), the similarity scores or the sampling strata. The labels will later be used to evaluate
that parser and the matching models, so they must not depend on them. To make this checkable,
this module imports neither the size parser nor the feature code, and it reads only the pair_id
column of candidates.csv. tests/label/test_tool.py checks all of this.

Keys (type the key and press Enter; a bare Enter does nothing):

    m  match           n  non_match        u  unsure
    s  skip a pair with excluded content, such as a bundle of different products
    b  go back to the previous pair, to correct its label
    q  quit            ?  help

After a label the tool asks for an optional note: tags separated by semicolons with no spaces, and
a comment after " # ". It lists the allowed tags each time. The tag cross_script is added
automatically when exactly one title has Bangla letters.

Every label is appended to the file and flushed to disk at once, so nothing is lost if the
session ends. Rows are never edited or deleted: a correction adds a row, and the current label
of a pair is its latest row. Starting the tool again resumes with the first pair that has no
label and has not been skipped. The tool reads and writes only the files of its own labeller.

The pairs come in a fixed order that depends only on the pair_id (a hash), so the order does not
change when pairs are added and does not group pairs by category.
"""

import argparse
import codecs
import csv
import hashlib
import io
import os
import shutil
import sys
import unicodedata
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from itertools import zip_longest
from pathlib import Path

from src.collect.validate import RAW_DIR, parse_timestamp
from src.label.listings import Listing, load_listings, read_candidate_pair_ids
from src.label.records import (
    AUTOMATIC_TAGS,
    CANDIDATES_PATH,
    GUIDELINES_PATH,
    LABEL_COLUMNS,
    LABELLED_DIR,
    LABELLER_ID,
    LABELS,
    SKIPPED_COLUMNS,
    TAG_REQUIRED_LABELS,
    TAGS,
    PairKey,
    check_label_and_tags,
    cross_script,
    format_note,
    labels_file_name,
    parse_note,
    parse_pair_id,
    read_guidelines_version,
    read_version_history,
    skipped_file_name,
    sort_tags,
)

KEYS = {"m": "match", "n": "non_match", "u": "unsure"}
# Every key of the label prompt, and the word it stands for. "?" shows the help.
ACTION_KEYS = {**KEYS, "s": "skip", "b": "back", "q": "quit"}
HELP_KEY = "?"
BACK_TO_LABEL = "<"
KEEP_NOTE = "="
NARROW_WIDTH = 72
DEFAULT_WIDTH = 100
MAX_WIDTH = 140


class ToolError(Exception):
    """A problem that stops the tool; its message is shown to the labeller."""


@dataclass(frozen=True)
class Stored:
    """The current label of a pair: its latest row.

    Attributes:
        label: The label.
        note: The note field of the row.
    """

    label: str
    note: str


@dataclass
class Config:
    """Where the tool reads and writes.

    Attributes:
        labeller: The labeller's ID, for example L1.
        raw_dir: The data/raw folder.
        labelled_dir: The data/labelled folder.
        candidates_path: The candidate pairs file.
        guidelines_path: The labelling guidelines.
        width: The width of the display; None uses the width of the terminal.
    """

    labeller: str
    raw_dir: Path = RAW_DIR
    labelled_dir: Path = LABELLED_DIR
    candidates_path: Path = CANDIDATES_PATH
    guidelines_path: Path = GUIDELINES_PATH
    width: int | None = None


# Display.


def display_width(text: str) -> int:
    """Return how many terminal columns a text takes, approximately.

    Combining marks (such as Bangla vowel signs of the kind Mn and the virama) take none, and
    wide East Asian characters take two. This keeps the two columns aligned for Bangla titles.
    """
    total = 0
    for char in text:
        if unicodedata.category(char) in ("Mn", "Me", "Cf"):
            continue
        total += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
    return total


def _pad(text: str, width: int) -> str:
    """Pad a text with spaces on the right to a display width."""
    return text + " " * max(0, width - display_width(text))


def _split_long(word: str, limit: int) -> list[str]:
    """Split a word that is wider than the limit into pieces that fit."""
    pieces: list[str] = []
    piece = ""
    for char in word:
        if piece and display_width(piece + char) > limit:
            pieces.append(piece)
            piece = ""
        piece += char
    pieces.append(piece)
    return pieces


def wrap_display(text: str, width: int, indent: str = "") -> list[str]:
    """Wrap a text into lines of at most the display width, breaking at spaces.

    A word longer than a line is split. Every line after the first starts with the indent.

    Args:
        text: The text.
        width: The width of a line, at least 8.
        indent: The text that starts the continuation lines.

    Returns:
        The lines; one empty line if the text is empty.
    """
    width = max(width, 8)
    limit = max(1, width - display_width(indent))
    lines: list[str] = []
    current = ""
    for word in text.split():
        for piece in _split_long(word, limit):
            candidate = f"{current} {piece}" if current else piece
            if current and display_width(candidate) > width:
                lines.append(current)
                current = indent + piece
            else:
                current = candidate
    lines.append(current)
    return lines


def _listing_lines(item: Listing, width: int) -> list[str]:
    """Return the lines that describe one listing, wrapped to the width."""
    rows = [("source", item.source), ("category", item.category)]
    rows.append(("brand field", item.brand or "(empty)"))
    if item.size_value or item.size_unit:
        rows.append(("size fields", f"{item.size_value} {item.size_unit}".strip()))
    lines: list[str] = []
    for name, value in rows:
        lines += wrap_display(f"{name}: {value}", width, indent="  ")
    lines.append("title:")
    lines += ["  " + line for line in wrap_display(item.title_raw, width - 2)]
    return lines


def render_pair(
    left: Listing,
    right: Listing,
    *,
    heading: str,
    width: int = DEFAULT_WIDTH,
) -> str:
    """Draw a pair for the labeller: the two listings side by side.

    Only the fields that the guidelines allow are shown. On a narrow display the listings are
    stacked instead.

    Args:
        left: The left listing.
        right: The right listing.
        heading: The first line (the position of the pair, and so on).
        width: The width of the display in columns.

    Returns:
        The text, without a final newline.
    """
    rule = "-" * min(width, MAX_WIDTH)
    lines = [heading, rule]
    if width >= NARROW_WIDTH:
        column = (min(width, MAX_WIDTH) - 3) // 2
        left_lines = ["LEFT", *_listing_lines(left, column)]
        right_lines = ["RIGHT", *_listing_lines(right, column)]
        for a, b in zip_longest(left_lines, right_lines, fillvalue=""):
            lines.append(f"{_pad(a, column)} | {b}".rstrip())
    else:
        lines += ["LEFT", *_listing_lines(left, width), rule]
        lines += ["RIGHT", *_listing_lines(right, width)]
    lines.append(rule)
    if left.brand or right.brand:
        lines.append(
            "A brand field can hold the manufacturer, not the brand. Read the brand from the title."
        )
    return "\n".join(lines)


def tag_list_text() -> str:
    """Return the list of tags that a labeller may type, with the labels some of them need."""
    names = []
    for tag in TAGS:
        if tag in AUTOMATIC_TAGS:
            continue
        needs = [label for label in LABELS if label in TAG_REQUIRED_LABELS.get(tag, ())]
        names.append(f"{tag} ({' or '.join(needs)} only)" if needs else tag)
    automatic = ", ".join(sorted(AUTOMATIC_TAGS))
    return (
        "Allowed tags: " + ", ".join(names) + f".\n  {automatic} is added by the tool; "
        "do not type it. The tags are explained in docs/labelling_guidelines.md."
    )


HELP_TEXT = """Keys (type the key, then Enter):
  m  match            the same item (see the guidelines)
  n  non_match        different items
  u  unsure           only when the information shown cannot settle the question
  s  skip             only for excluded content, such as a bundle of different products;
                      a difficult pair gets unsure, not skip. A skipped pair is left out.
  b  back             go back to the previous pair and correct its label
  q  quit             your labels are already saved
Read the size from the title. The price and the sizes read by the program are not shown."""


# Files.


class CsvLog:
    """An append-only CSV file with a fixed header. Each append is flushed to disk."""

    def __init__(self, path: Path, columns: tuple[str, ...]) -> None:
        """Remember the file and its columns; nothing is read or written yet."""
        self.path = path
        self.columns = columns

    def append(self, row: dict[str, str]) -> None:
        """Append one row, writing the header first if the file is new or empty."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not self.path.exists() or self.path.stat().st_size == 0
        with self.path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            if is_new:
                writer.writerow(self.columns)
            writer.writerow([row[column] for column in self.columns])
            handle.flush()
            os.fsync(handle.fileno())


def read_log(path: Path, columns: tuple[str, ...]) -> list[dict[str, str]]:
    """Read an existing file of the tool, strictly.

    Args:
        path: The file; a missing file has no rows.
        columns: The columns it must have, in order.

    Returns:
        The rows.

    Raises:
        ToolError: If the file has a byte-order mark, is not UTF-8, has a wrong header, has a
            row with the wrong number of fields, or does not end with a line end (which means
            that its last row is incomplete).
    """
    if not path.is_file():
        return []
    data = path.read_bytes()
    if not data:
        return []
    if data.startswith(codecs.BOM_UTF8):
        raise ToolError(f"{path.name} starts with a byte-order mark; run the validator")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ToolError(f"{path.name} is not valid UTF-8; run the validator") from None
    if not text.endswith("\n"):
        raise ToolError(f"{path.name} does not end with a line end: its last row is incomplete")
    records = list(csv.reader(io.StringIO(text, newline="")))
    if tuple(records[0]) != columns:
        raise ToolError(f"{path.name} does not have the expected header; run the validator")
    rows = []
    for number, record in enumerate(records[1:], start=2):
        if len(record) != len(columns):
            raise ToolError(f"{path.name}, row {number}: wrong number of fields; run the validator")
        rows.append(dict(zip(columns, record, strict=True)))
    return rows


def _local_now() -> datetime:
    """Return the current local time with its UTC offset."""
    return datetime.now().astimezone()


@dataclass
class _State:
    """What the session knows about the labeller's files and the pairs."""

    order: list[PairKey]
    listings: dict[str, tuple[Listing, Listing]]
    current: dict[str, Stored] = field(default_factory=dict)
    labelled_first: list[str] = field(default_factory=list)
    skipped: set[str] = field(default_factory=set)
    last_time: datetime | None = None


def _hash_order(pair_ids: Sequence[str]) -> list[str]:
    """Order pair IDs by a hash of the ID, so that the order depends on nothing else."""
    return sorted(pair_ids, key=lambda i: (hashlib.sha256(i.encode("utf-8")).hexdigest(), i))


# The session.


class Session:
    """One labelling session of one labeller.

    Loading happens in the constructor and raises ToolError if anything is wrong; run then
    talks to the labeller through input_fn and print_fn.
    """

    def __init__(
        self,
        config: Config,
        *,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[[str], None] = print,
        now_fn: Callable[[], datetime] = _local_now,
    ) -> None:
        """Read the guidelines version, the pairs, the listings and the labeller's files.

        Args:
            config: Where to read and write.
            input_fn: Asks the labeller a question and returns the answer (input by default).
            print_fn: Shows a text to the labeller (print by default).
            now_fn: Returns the current local time with its UTC offset.

        Raises:
            ToolError: If the labeller's ID is not allowed, the guidelines version is unknown,
                the candidates or listings cannot be read, or the labeller's files are malformed.
        """
        self.config = config
        self.input = input_fn
        self.print = print_fn
        self.now = now_fn
        if not LABELLER_ID.fullmatch(config.labeller):
            raise ToolError(f"the labeller {config.labeller!r} must be L and digits, such as L1")
        self.version = self._read_version()
        self.state = self._load_pairs()
        self.labels_log = CsvLog(
            config.labelled_dir / labels_file_name(config.labeller), LABEL_COLUMNS
        )
        self.skipped_log = CsvLog(
            config.labelled_dir / skipped_file_name(config.labeller), SKIPPED_COLUMNS
        )
        self._load_files()
        self.history: list[str] = list(self.state.labelled_first)
        self.new_labels = 0

    # Loading.

    def _read_version(self) -> str:
        """Read the guidelines version and check that it is in the version history."""
        try:
            version = read_guidelines_version(self.config.guidelines_path)
            history = read_version_history(self.config.guidelines_path)
        except (OSError, ValueError) as error:
            raise ToolError(f"cannot read the guidelines: {error}") from None
        if version not in history:
            raise ToolError(f"the guidelines version {version} is not in its version history")
        return version

    def _load_pairs(self) -> _State:
        """Read the candidate pairs and the listings behind them."""
        path = self.config.candidates_path
        try:
            pair_ids = read_candidate_pair_ids(path)
        except ValueError as error:
            raise ToolError(f"cannot read the candidate pairs: {error}") from None
        if pair_ids is None:
            raise ToolError(
                f"{path.name} was not found; make it with python -m src.label.candidates"
            )
        try:
            listings = load_listings(self.config.raw_dir)
        except ValueError as error:
            raise ToolError(f"cannot read the listings: {error}") from None
        keys = []
        pairs: dict[str, tuple[Listing, Listing]] = {}
        for pair_id in _hash_order(sorted(pair_ids)):
            try:
                key = parse_pair_id(pair_id)
            except ValueError as error:
                raise ToolError(f"{path.name}: {error}") from None
            found = (
                listings.get((key.left_source, key.left_id)),
                listings.get((key.right_source, key.right_id)),
            )
            if found[0] is None or found[1] is None:
                raise ToolError(f"{path.name}: a listing of the pair {pair_id} is not in data/raw")
            keys.append(key)
            pairs[pair_id] = (found[0], found[1])
        return _State(order=keys, listings=pairs)

    def _load_files(self) -> None:
        """Read the labeller's own label and skipped files, and nothing else."""
        state = self.state
        known = set(state.listings)
        now = self.now()
        for number, row in enumerate(read_log(self.labels_log.path, LABEL_COLUMNS), start=2):
            self._check_row_pair(row["pair_id"], known, self.labels_log.path.name, number)
            if row["labeller"] != self.config.labeller:
                raise ToolError(
                    f"{self.labels_log.path.name}, row {number}: the labeller is "
                    f"{row['labeller']!r}, not {self.config.labeller}"
                )
            if row["label"] not in LABELS:
                raise ToolError(
                    f"{self.labels_log.path.name}, row {number}: the label {row['label']!r} "
                    "is not allowed; run the validator"
                )
            state.last_time = self._later(
                state.last_time, row["labelled_at"], self.labels_log.path.name, number, now
            )
            if row["pair_id"] not in state.current:
                state.labelled_first.append(row["pair_id"])
            state.current[row["pair_id"]] = Stored(row["label"], row["note"])
        for number, row in enumerate(read_log(self.skipped_log.path, SKIPPED_COLUMNS), start=2):
            self._check_row_pair(row["pair_id"], known, self.skipped_log.path.name, number)
            state.skipped.add(row["pair_id"])
            state.last_time = self._later(
                state.last_time, row["skipped_at"], self.skipped_log.path.name, number, now
            )

    def _check_row_pair(self, pair_id: str, known: set[str], name: str, number: int) -> None:
        """Check that a pair of the labeller's file is a candidate."""
        if pair_id not in known:
            raise ToolError(
                f"{name}, row {number}: the pair is not in {self.config.candidates_path.name}; "
                "run the validator"
            )

    @staticmethod
    def _later(
        last: datetime | None, value: str, name: str, number: int, now: datetime
    ) -> datetime:
        """Return the later of the last time and a time read from a file."""
        try:
            moment = parse_timestamp(value, now)
        except ValueError as error:
            raise ToolError(f"{name}, row {number}: {error}; run the validator") from None
        return moment if last is None or moment > last else last

    # Talking to the labeller.

    def _say(self, text: str = "") -> None:
        self.print(text)

    def _width(self) -> int:
        if self.config.width is not None:
            return self.config.width
        return min(shutil.get_terminal_size((DEFAULT_WIDTH, 24)).columns, MAX_WIDTH)

    def _pending(self) -> str | None:
        """Return the first pair, in order, with no label that has not been skipped."""
        for key in self.state.order:
            if key.pair_id not in self.state.current and key.pair_id not in self.state.skipped:
                return key.pair_id
        return None

    def _counts(self) -> tuple[int, int, int]:
        """Return the numbers of pairs labelled, skipped and still to do."""
        labelled = len(self.state.current)
        skipped = len(self.state.skipped)
        return labelled, skipped, len(self.state.order) - labelled - skipped

    def _show(self, pair_id: str) -> None:
        """Show a pair."""
        left, right = self.state.listings[pair_id]
        position = next(i for i, key in enumerate(self.state.order, 1) if key.pair_id == pair_id)
        labelled, skipped, remaining = self._counts()
        heading = (
            f"Pair {position} of {len(self.state.order)}   {pair_id}   "
            f"labelled {labelled}, skipped {skipped}, to do {remaining}"
        )
        stored = self.state.current.get(pair_id)
        if stored is not None:
            heading += f"\nCurrent label: {stored.label}" + (
                f"   note: {stored.note}" if stored.note else ""
            )
        self._say()
        self._say(render_pair(left, right, heading=heading, width=self._width()))

    def _ask(self, prompt: str) -> str | None:
        """Ask a question; None means that the labeller ended the input (Ctrl+Z, Ctrl+C)."""
        try:
            return self.input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return None

    def _ask_action(self) -> str:
        """Ask for m, n, u, s, b or q until the answer is one of them; return its word."""
        prompt = "Label: m match, n non_match, u unsure, s skip, b back, q quit, ? help > "
        words = ACTION_KEYS
        while True:
            answer = self._ask(prompt)
            if answer is None:
                return "quit"
            answer = answer.lower()
            if answer == HELP_KEY:
                self._say(HELP_TEXT)
            elif answer in words:
                return words[answer]
            elif answer in words.values():
                return answer
            else:
                self._say("Type m, n, u, s, b, q or ? and press Enter.")

    def _ask_note(
        self, label: str, left: Listing, right: Listing, stored: Stored | None
    ) -> tuple[tuple[str, ...], str] | None:
        """Ask for the optional note; return (tags, comment), or None to choose the label again.

        The tag cross_script is added here when it applies, and never taken from the labeller.
        """
        automatic = tuple(AUTOMATIC_TAGS) if cross_script(left.title_raw, right.title_raw) else ()
        self._say(tag_list_text())
        options = f"Enter for none, {BACK_TO_LABEL} to choose the label again"
        if stored is not None:
            options += f", {KEEP_NOTE} to keep the current note"
        prompt = f"Note for {label} ({options}) > "
        while True:
            answer = self._ask(prompt)
            if answer is None:
                return None
            if answer == BACK_TO_LABEL:
                return None
            try:
                if answer == KEEP_NOTE and stored is not None:
                    parsed = parse_note(stored.note)
                else:
                    parsed = parse_note(answer)
            except ValueError as error:
                self._say(f"  {error}")
                continue
            typed = [tag for tag in parsed.tags if tag not in AUTOMATIC_TAGS]
            if len(typed) != len(parsed.tags) and answer != KEEP_NOTE:
                self._say("  cross_script is added by the tool and was ignored.")
            tags = sort_tags([*typed, *automatic])
            problems = check_label_and_tags(label, tags)
            if problems:
                for problem in problems:
                    self._say(f"  {problem}")
                self._say(f"  Fix the note, or type {BACK_TO_LABEL} to choose the label again.")
                continue
            return tags, parsed.comment

    # Writing.

    def _timestamp(self) -> str:
        """Return the current local time as text, refusing a time before the last row."""
        moment = self.now()
        last = self.state.last_time
        if last is not None and moment < last:
            raise ToolError(
                f"the clock reads {moment.isoformat(timespec='seconds')}, earlier than the "
                f"last row ({last.isoformat(timespec='seconds')}); nothing was saved. "
                "Check the date and time of the computer."
            )
        self.state.last_time = moment
        return moment.isoformat(timespec="seconds")

    def _save_label(self, pair_id: str, label: str, note: str) -> None:
        """Append a label row, flushed to disk, and update what the session knows."""
        key = parse_pair_id(pair_id)
        row = {
            "pair_id": pair_id,
            "left_source": key.left_source,
            "left_id": key.left_id,
            "right_source": key.right_source,
            "right_id": key.right_id,
            "label": label,
            "note": note,
            "labeller": self.config.labeller,
            "labelled_at": self._timestamp(),
            "guidelines_version": self.version,
        }
        self.labels_log.append(row)
        if pair_id not in self.state.current:
            self.history.append(pair_id)
        self.state.current[pair_id] = Stored(label, note)
        self.new_labels += 1

    def _save_skip(self, pair_id: str, reason: str) -> None:
        """Append a skipped row, flushed to disk."""
        row = {"pair_id": pair_id, "reason": reason, "skipped_at": self._timestamp()}
        self.skipped_log.append(row)
        self.state.skipped.add(pair_id)

    # The loop.

    def _handle(self, pair_id: str, revisiting: bool) -> str:
        """Ask about one pair; return "done", "back", "skipped" or "quit"."""
        left, right = self.state.listings[pair_id]
        stored = self.state.current.get(pair_id)
        self._show(pair_id)
        while True:
            action = self._ask_action()
            if action in ("quit", "back"):
                return action
            if action == "skip":
                if stored is not None:
                    self._say("This pair is labelled; a labelled pair cannot be skipped.")
                    continue
                reason = self._ask("Reason for skipping (Enter to cancel) > ")
                if not reason:
                    self._say("Not skipped.")
                    continue
                self._save_skip(pair_id, reason)
                self._say("Skipped.")
                return "skipped"
            noted = self._ask_note(action, left, right, stored)
            if noted is None:
                continue
            tags, comment = noted
            note = format_note(tags, comment)
            if stored is not None and stored == Stored(action, note):
                self._say("Unchanged; nothing was written.")
                return "done"
            self._save_label(pair_id, action, note)
            self._say(f"Saved: {action}" + (f"   note: {note}" if note else ""))
            return "done"

    def run(self) -> int:
        """Run the session until the labeller quits or no pair is left.

        Returns:
            0 when the session ended normally, 1 if it stopped on an error.
        """
        self._say(
            f"Labelling as {self.config.labeller}. Guidelines version {self.version} "
            f"({self.config.guidelines_path.name}): read it before you label."
        )
        labelled, skipped, remaining = self._counts()
        if labelled or skipped:
            self._say(f"Resuming: {labelled} labelled, {skipped} skipped, {remaining} to do.")
        self._say("Type ? for the keys.")
        revisit: int | None = None
        try:
            while True:
                if revisit is None:
                    pair_id = self._pending()
                    if pair_id is None:
                        self._say("\nEvery pair is labelled or skipped.")
                        break
                else:
                    pair_id = self.history[revisit]
                outcome = self._handle(pair_id, revisit is not None)
                if outcome == "quit":
                    break
                if outcome == "back":
                    earlier = len(self.history) - 1 if revisit is None else revisit - 1
                    if earlier < 0:
                        self._say("There is no earlier pair to go back to.")
                    else:
                        revisit = earlier
                elif revisit is not None:
                    revisit = revisit + 1 if revisit + 1 < len(self.history) else None
        except ToolError as error:
            self._say(f"\nerror: {error}")
            return 1
        self._finish()
        return 0

    def _finish(self) -> None:
        """Print what the session did and what to do next."""
        counts = Counter(stored.label for stored in self.state.current.values())
        by_label = ", ".join(f"{label} {counts[label]}" for label in LABELS)
        labelled, skipped, remaining = self._counts()
        self._say(
            f"\nThis session wrote {self.new_labels} label rows. In all: {labelled} pairs "
            f"labelled ({by_label}), {skipped} skipped, {remaining} to do."
        )
        self._say(f"Labels are saved in {self.labels_log.path}")
        steps = [
            "python -m src.label.validate",
            f"dvc add data/labelled/{self.labels_log.path.name}"
            + (f" data/labelled/{self.skipped_log.path.name}" if self.state.skipped else ""),
            "commit the .dvc file(s), then dvc push and dvc status -c",
            "wait until Google Drive for desktop has finished uploading",
        ]
        self._say("Next: " + "; then ".join(steps) + ".")


# The command line.


def _use_utf8_streams() -> None:
    """Make standard output and input UTF-8 when they are not, so Bangla titles are not lost."""
    for stream in (sys.stdout, sys.stdin):
        if stream.encoding and stream.encoding.lower().replace("-", "") != "utf8":
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]


def main(
    argv: Sequence[str] | None = None,
    *,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
    now_fn: Callable[[], datetime] = _local_now,
) -> int:
    """Run the labelling tool.

    Args:
        argv: The command-line arguments, without the program name. Defaults to sys.argv.
        input_fn: Asks the labeller a question; tests pass scripted answers.
        print_fn: Shows a text to the labeller.
        now_fn: Returns the current local time with its UTC offset.

    Returns:
        The exit status: 0 if the session ended normally, otherwise 1.
    """
    parser = argparse.ArgumentParser(
        prog="python -m src.label.tool",
        description="Label candidate pairs. Your labels are saved as you make them.",
    )
    parser.add_argument("--labeller", required=True, help="your ID, for example L1")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--labelled-dir", type=Path, default=LABELLED_DIR)
    parser.add_argument("--candidates", type=Path, default=CANDIDATES_PATH)
    parser.add_argument("--guidelines", type=Path, default=GUIDELINES_PATH)
    parser.add_argument("--width", type=int, default=None, help="columns; default: the terminal")
    args = parser.parse_args(argv)
    config = Config(
        labeller=args.labeller,
        raw_dir=args.raw_dir,
        labelled_dir=args.labelled_dir,
        candidates_path=args.candidates,
        guidelines_path=args.guidelines,
        width=args.width,
    )
    try:
        session = Session(config, input_fn=input_fn, print_fn=print_fn, now_fn=now_fn)
    except ToolError as error:
        print_fn(f"error: {error}")
        return 1
    return session.run()


if __name__ == "__main__":
    _use_utf8_streams()
    raise SystemExit(main())
