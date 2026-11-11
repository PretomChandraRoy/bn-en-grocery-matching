"""Tests for src.label.candidates.

All listings are invented (see tests/label/builders.py) and are written to scratch folders; no
real data is read. The prices of the first pairs are chosen so that the ratios can be worked out
by hand.
"""

import csv
from decimal import Decimal
from pathlib import Path

import pytest

from src.label.candidates import (
    CANDIDATE_COLUMNS,
    STRATA,
    STRATEGY_PILOT,
    Thresholds,
    assign_stratum,
    build_candidates,
    expected_pair_count,
    main,
    render_csv,
    strata_preview,
    write_candidates,
)
from src.label.listings import Listing, load_listings, read_candidate_pair_ids, read_prices
from src.label.validate import load_context, validate_file
from tests.label.builders import (
    LISTINGS,
    NOW,
    label_file,
    label_row,
    pair,
    write_guidelines,
    write_raw,
)

# Prices that make the ratios of the first pairs easy to work out.
PRICES = {
    ("pandamart", "1001"): "100",
    ("meenabazar", "2001"): "80",
    ("meenabazar", "2002"): "300",
    ("pandamart", "1003"): "120",
    ("meenabazar", "2003"): "150",
    ("pandamart", "1008"): "50",
}


def build(tmp_path: Path, listings: list[tuple[str, ...]] | None = None) -> list[dict[str, str]]:
    raw = write_raw(tmp_path / "raw", listings, PRICES)
    return build_candidates(load_listings(raw), read_prices(raw))


def by_pair(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["pair_id"]: row for row in rows}


# Which pairs there are.


def test_every_cross_shop_pair_in_a_category_is_a_candidate(tmp_path: Path) -> None:
    rows = build(tmp_path)
    # Pandamart by meenabazar listings: rice 4 x 3, cooking oil 2 x 2, spices 1 x 1, lentils 1 x 1.
    counts = {}
    for row in rows:
        counts[row["category"]] = counts.get(row["category"], 0) + 1
    assert counts == {"cooking_oil": 4, "lentils": 1, "rice": 12, "spices": 1}
    assert len(rows) == expected_pair_count(load_listings(tmp_path / "raw")) == 18


def test_a_pair_has_two_different_sources_and_one_category(tmp_path: Path) -> None:
    listings = load_listings(write_raw(tmp_path / "raw"))
    for row in build(tmp_path):
        left = listings[(row["left_source"], row["left_id"])]
        right = listings[(row["right_source"], row["right_id"])]
        assert left.source != right.source
        assert left.category == right.category == row["category"]


def test_the_alphabetically_first_source_is_the_left_one(tmp_path: Path) -> None:
    for row in build(tmp_path):
        assert (row["left_source"], row["right_source"]) == ("meenabazar", "pandamart")
        assert row["pair_id"] == f"meenabazar:{row['left_id']}|pandamart:{row['right_id']}"


def test_there_are_no_duplicate_pairs_and_the_rows_are_sorted(tmp_path: Path) -> None:
    rows = build(tmp_path)
    ids = [row["pair_id"] for row in rows]
    assert len(set(ids)) == len(ids)
    assert rows == sorted(rows, key=lambda row: (row["category"], row["pair_id"]))


def test_no_pair_is_made_within_one_source_or_across_categories(tmp_path: Path) -> None:
    ids = {row["pair_id"] for row in build(tmp_path)}
    assert pair("1001", "2003") not in ids  # rice with cooking oil
    assert not any(i.startswith("pandamart:") for i in ids)
    assert all(i.count("meenabazar") == 1 and i.count("pandamart") == 1 for i in ids)


def test_three_sources_give_every_pair_of_sources(tmp_path: Path) -> None:
    listings = [
        ("alpha", "1", "Test Rice 1kg", "", "rice", "english"),
        ("alpha", "2", "Test Rice 2kg", "", "rice", "english"),
        ("beta", "3", "Test Rice 1kg", "", "rice", "english"),
        ("gamma", "4", "Test Rice 1kg", "", "rice", "english"),
        ("gamma", "5", "Test Dal 1kg", "", "lentils", "english"),
    ]
    rows = build(tmp_path, listings)
    # alpha by beta 2, alpha by gamma 2, beta by gamma 1; the lentil has no partner.
    assert sorted(row["pair_id"] for row in rows) == [
        "alpha:1|beta:3",
        "alpha:1|gamma:4",
        "alpha:2|beta:3",
        "alpha:2|gamma:4",
        "beta:3|gamma:4",
    ]
    assert expected_pair_count(load_listings(tmp_path / "raw")) == 5


def test_one_source_gives_no_pairs(tmp_path: Path) -> None:
    listings = [item for item in LISTINGS if item[0] == "pandamart"]
    assert build(tmp_path, listings) == []


def test_a_wrong_pair_count_is_reported_as_a_bug(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = write_raw(tmp_path / "raw")
    monkeypatch.setattr("src.label.candidates.expected_pair_count", lambda listings: 999)
    with pytest.raises(RuntimeError, match="differs from the count expected"):
        build_candidates(load_listings(raw), read_prices(raw))


def test_no_listings_give_no_pairs(tmp_path: Path) -> None:
    assert build_candidates({}, {}) == []


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        pytest.param({("rice", "a"): 3, ("rice", "b"): 2}, 6, id="two-sources"),
        pytest.param({("rice", "a"): 2, ("rice", "b"): 1, ("rice", "c"): 1}, 5, id="three"),
        pytest.param({("rice", "a"): 3}, 0, id="one-source"),
        pytest.param(
            {("rice", "a"): 2, ("rice", "b"): 2, ("oil", "a"): 1, ("oil", "b"): 5}, 9, id="two-cat"
        ),
        pytest.param({("rice", "a"): 2, ("oil", "b"): 2}, 0, id="no-shared-category"),
    ],
)
def test_expected_pair_count(counts: dict[tuple[str, str], int], expected: int) -> None:
    listings = {}
    for (category, source), number in counts.items():
        for index in range(number):
            item = Listing(
                source, f"{category}{index}", "t", "", "", "", category, "", "english", "u"
            )
            listings[item.key] = item
    assert expected_pair_count(listings) == expected


# The features of particular pairs.


def test_a_pair_of_identical_names_with_the_same_size(tmp_path: Path) -> None:
    row = by_pair(build(tmp_path))[pair("1001", "2001")]
    assert row["strategy"] == STRATEGY_PILOT == "pilot_all_pairs"
    assert row["category"] == "rice"
    assert (row["token_jaccard"], row["token_overlap"], row["char3_jaccard"]) == (
        "1.0000",
        "1.0000",
        "1.0000",
    )
    assert row["size_relation"] == "same"
    assert (row["left_kind"], row["left_total"], row["left_packs"]) == ("weight", "1000", "1")
    assert (row["right_kind"], row["right_total"], row["right_packs"]) == ("weight", "1000", "1")
    assert row["size_ratio"] == "1.0000"
    # 80 against 100.
    assert row["price_ratio"] == "0.8000"
    assert row["unit_price_ratio"] == "0.8000"
    assert (row["left_script"], row["right_script"], row["cross_script"]) == (
        "english",
        "english",
        "false",
    )


def test_a_pair_of_different_sizes(tmp_path: Path) -> None:
    row = by_pair(build(tmp_path))[pair("1001", "2002")]
    assert row["size_relation"] == "different_amount"
    assert (row["left_total"], row["right_total"]) == ("5000", "1000")
    assert row["size_ratio"] == "0.2000"
    # 100 against 300 is 0.3333; per 100 g, 6 against 10 is 0.6.
    assert row["price_ratio"] == "0.3333"
    assert row["unit_price_ratio"] == "0.6000"
    assert row["token_jaccard"] == "1.0000"


def test_a_multipack_with_the_same_total(tmp_path: Path) -> None:
    row = by_pair(build(tmp_path))[pair("1003", "2003")]
    assert row["size_relation"] == "same_total_different_pack"
    assert (row["left_kind"], row["left_total"], row["left_packs"]) == ("volume", "1000", "1")
    assert (row["right_kind"], row["right_total"], row["right_packs"]) == ("volume", "1000", "2")
    assert row["size_ratio"] == "1.0000"
    # 150 against 120 is 0.8; per 100 ml the totals are equal, so the same ratio.
    assert row["price_ratio"] == row["unit_price_ratio"] == "0.8000"


def test_a_multipack_on_the_left_side(tmp_path: Path) -> None:
    listings = [
        ("pandamart", "1", "Test Oil 1L", "", "cooking_oil", "english"),
        ("meenabazar", "2", "TEST OIL 2 X 500ML", "", "cooking_oil", "english"),
    ]
    row = build(tmp_path, listings)[0]
    assert row["size_relation"] == "same_total_different_pack"
    assert (row["left_kind"], row["left_total"], row["left_packs"]) == ("volume", "1000", "2")
    assert (row["right_kind"], row["right_total"], row["right_packs"]) == ("volume", "1000", "1")


def test_a_weight_against_a_volume(tmp_path: Path) -> None:
    row = by_pair(build(tmp_path))[pair("1006", "2006")]
    assert row["size_relation"] == "different_kind"
    assert (row["left_kind"], row["right_kind"]) == ("weight", "volume")
    assert (row["left_total"], row["right_total"]) == ("1000", "1000")
    assert row["size_ratio"] == ""
    assert row["unit_price_ratio"] == ""
    assert row["price_ratio"] != ""


def test_a_size_that_was_not_read_leaves_its_fields_empty(tmp_path: Path) -> None:
    row = by_pair(build(tmp_path))[pair("1008", "2001")]
    assert row["size_relation"] == "unknown"
    assert (row["right_kind"], row["right_total"], row["right_packs"]) == ("", "", "")
    assert (row["left_kind"], row["left_total"], row["left_packs"]) == ("weight", "1000", "1")
    assert row["size_ratio"] == row["unit_price_ratio"] == ""
    # 50 against 80.
    assert row["price_ratio"] == "0.6250"


def test_a_bangla_title_sets_cross_script(tmp_path: Path) -> None:
    row = by_pair(build(tmp_path))[pair("1005", "2001")]
    assert row["cross_script"] == "true"
    assert (row["left_script"], row["right_script"]) == ("english", "bangla")
    assert by_pair(build(tmp_path))[pair("1005", "2002")]["cross_script"] == "true"
    assert by_pair(build(tmp_path))[pair("1001", "2001")]["cross_script"] == "false"


def test_the_text_features_ignore_the_size(tmp_path: Path) -> None:
    # "Test Rice 1kg" and "TEST RICE 5KG" differ only in size, so their names are identical.
    assert by_pair(build(tmp_path))[pair("1001", "2002")]["char3_jaccard"] == "1.0000"


def test_the_text_features_of_two_partly_different_names(tmp_path: Path) -> None:
    listings = [
        ("pandamart", "1", "Test Rice Special 1kg", "", "rice", "english"),
        ("meenabazar", "2", "TEST RICE 1KG", "", "rice", "english"),
    ]
    row = build(tmp_path, listings)[0]
    # Names {test, rice, special} and {test, rice}: 2 shared of 3 in all, and of 2 in the shorter.
    assert row["token_jaccard"] == "0.6667"
    assert row["token_overlap"] == "1.0000"
    # "testricespecial" has 13 trigrams and "testrice" has 6, all of them in the first: 6/13.
    assert row["char3_jaccard"] == "0.4615"
    assert row["size_relation"] == "same"


def test_every_row_has_every_column_and_no_empty_core_field(tmp_path: Path) -> None:
    for row in build(tmp_path):
        assert tuple(row) == CANDIDATE_COLUMNS
        for column in CANDIDATE_COLUMNS[:10] + ("price_ratio", "left_script", "cross_script"):
            assert row[column] != "", column


# What the file holds, and does not.


def test_the_file_holds_no_title_price_brand_or_url(tmp_path: Path) -> None:
    raw = write_raw(tmp_path / "raw", prices=None)
    text = render_csv(build_candidates(load_listings(raw), read_prices(raw))).decode("utf-8")
    for forbidden in (
        "Zorbaxo",
        "ZORBAXO",
        "Test Rice",
        "TEST",
        "Foods",
        "7777",
        "8888",
        "example",
    ):
        assert forbidden not in text, forbidden


def test_the_file_is_utf_8_with_lf_line_ends_and_the_columns_in_order(tmp_path: Path) -> None:
    rows = build(tmp_path)
    data = render_csv(rows)
    assert not data.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in data
    lines = data.decode("utf-8").split("\n")
    assert lines[0] == ",".join(CANDIDATE_COLUMNS)
    assert len(lines) == len(rows) + 2  # the header, the rows and the empty text after the last LF
    assert lines[-1] == ""
    assert len(CANDIDATE_COLUMNS) == 23


def test_the_same_data_always_gives_the_same_bytes(tmp_path: Path) -> None:
    raw = write_raw(tmp_path / "raw", prices=PRICES)
    listings, prices = load_listings(raw), read_prices(raw)
    first = render_csv(build_candidates(listings, prices))
    assert render_csv(build_candidates(listings, prices)) == first
    reversed_listings = dict(reversed(list(listings.items())))
    assert render_csv(build_candidates(reversed_listings, prices)) == first


def test_a_file_with_no_pairs_is_just_a_header(tmp_path: Path) -> None:
    assert render_csv([]) == (",".join(CANDIDATE_COLUMNS) + "\n").encode("utf-8")


# The candidates file and the validator.


def test_the_file_can_be_read_and_the_validator_accepts_a_generated_pair(tmp_path: Path) -> None:
    rows = build(tmp_path)
    path = tmp_path / "candidates.csv"
    write_candidates(rows, path)
    assert read_candidate_pair_ids(path) == frozenset(row["pair_id"] for row in rows)
    ctx = load_context(
        raw_dir=tmp_path / "raw",
        candidates_path=path,
        guidelines_path=write_guidelines(tmp_path),
        now=NOW,
    )
    labels = tmp_path / "labels_L1.csv"
    labels.write_bytes(label_file([label_row("1001", "2001")]))
    assert validate_file(labels, ctx).problems == []
    labels.write_bytes(label_file([label_row("1001", "2003")]))
    errors = [problem.describe() for problem in validate_file(labels, ctx).errors]
    assert errors == ["error (row 2, pair_id): the pair is not in candidates.csv"]


# Writing the file.


def test_write_candidates_creates_updates_and_leaves_an_unchanged_file(tmp_path: Path) -> None:
    rows = build(tmp_path)
    path = tmp_path / "interim" / "candidates.csv"
    assert write_candidates(rows[:5], path) == "created"
    assert write_candidates(rows[:5], path) == "unchanged"
    assert write_candidates(rows, path) == "updated"
    assert path.read_bytes() == render_csv(rows)
    assert [item.name for item in path.parent.iterdir()] == ["candidates.csv"]


def test_a_new_file_that_lacks_pairs_of_the_old_one_is_refused(tmp_path: Path) -> None:
    rows = build(tmp_path)
    path = tmp_path / "candidates.csv"
    write_candidates(rows, path)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="3 pairs of the existing candidates.csv are not in"):
        write_candidates(rows[:-3], path)
    assert path.read_bytes() == before
    assert write_candidates(rows[:-3], path, replace=True) == "updated"
    assert path.read_bytes() == render_csv(rows[:-3])


def test_an_existing_file_that_cannot_be_read_is_not_replaced_without_permission(
    tmp_path: Path,
) -> None:
    rows = build(tmp_path)
    path = tmp_path / "candidates.csv"
    path.write_text("category\nrice\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exists but cannot be read"):
        write_candidates(rows, path)
    assert path.read_text(encoding="utf-8") == "category\nrice\n"
    assert write_candidates(rows, path, replace=True) == "updated"


def test_a_file_may_gain_pairs_without_permission(tmp_path: Path) -> None:
    rows = build(tmp_path)
    path = tmp_path / "candidates.csv"
    write_candidates(rows[:4], path)
    assert write_candidates(rows, path) == "updated"


# The provisional strata.


def row_of(similarity: str, relation: str, price: str) -> dict[str, str]:
    return {
        "category": "rice",
        "char3_jaccard": similarity,
        "size_relation": relation,
        "price_ratio": price,
    }


LIMITS = Thresholds(high=Decimal("0.60"), low=Decimal("0.35"), price_min=Decimal("0.70"))


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        pytest.param(row_of("0.2000", "same", "0.9000"), "wording_variation", id="wording"),
        pytest.param(row_of("0.3499", "same", "0.7000"), "wording_variation", id="wording-edge"),
        pytest.param(row_of("0.3500", "same", "0.9000"), "random_negative", id="low-is-excluded"),
        pytest.param(row_of("0.2000", "same", "0.6999"), "random_negative", id="price-too-far"),
        pytest.param(row_of("0.2000", "same", ""), "random_negative", id="no-price"),
        pytest.param(row_of("0.6000", "same", "0.9000"), "likely_match", id="likely"),
        pytest.param(row_of("0.5999", "same", "0.9000"), "random_negative", id="just-below-high"),
        pytest.param(row_of("0.5000", "same", "0.9000"), "random_negative", id="same-mid"),
        pytest.param(row_of("0.9000", "different_amount", "0.9"), "hard_negative", id="hard"),
        pytest.param(row_of("0.6000", "different_kind", "0.9"), "hard_negative", id="hard-kind"),
        pytest.param(row_of("0.9000", "unknown", "0.9"), "hard_negative", id="hard-unknown"),
        pytest.param(
            row_of("0.9000", "same_total_different_pack", "0.9"), "hard_negative", id="hard-pack"
        ),
        pytest.param(row_of("0.2000", "different_amount", "0.9"), "random_negative", id="random"),
        pytest.param(row_of("0.2000", "unknown", "0.9"), "random_negative", id="random-unknown"),
    ],
)
def test_assign_stratum(row: dict[str, str], expected: str) -> None:
    assert assign_stratum(row, LIMITS) == expected


def test_the_thresholds_change_the_strata() -> None:
    row = row_of("0.5000", "same", "0.9000")
    assert assign_stratum(row, LIMITS) == "random_negative"
    assert assign_stratum(row, Thresholds(Decimal("0.5"), Decimal("0.3"), Decimal("0.7"))) == (
        "likely_match"
    )
    assert assign_stratum(row, Thresholds(Decimal("0.9"), Decimal("0.6"), Decimal("0.7"))) == (
        "wording_variation"
    )


def test_the_strata_are_the_four_planned_ones() -> None:
    assert STRATA == ("wording_variation", "likely_match", "hard_negative", "random_negative")


def test_the_preview_counts_the_pairs_of_each_stratum() -> None:
    rows = [
        row_of("0.2000", "same", "0.9000"),
        row_of("0.2000", "same", "0.9000") | {"category": "spices"},
        row_of("0.8000", "same", "0.9000"),
        row_of("0.9000", "different_amount", "0.9"),
        row_of("0.1000", "different_amount", "0.9"),
        row_of("0.1000", "unknown", "0.9"),
    ]
    text = strata_preview(rows, LIMITS)
    assert text.startswith("6 candidate pairs.")
    assert "similar from 0.60" in text
    assert "different below 0.35" in text
    assert "prices close from 0.70" in text
    # Columns: all pairs, then the categories in order (rice, spices).
    counts = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) > 1 and parts[0] in STRATA and parts[1].isdigit():
            counts[parts[0]] = parts[1:]
        elif parts[:2] == ["all", "pairs"]:
            counts["all"] = parts[2:]
    assert counts == {
        "wording_variation": ["2", "1", "1"],
        "likely_match": ["1", "1", "0"],
        "hard_negative": ["1", "1", "0"],
        "random_negative": ["2", "2", "0"],
        "all": ["6", "5", "1"],
    }
    assert "wording_variation is 33.3 percent of the pairs" in text


def test_the_preview_describes_the_spread_of_the_features() -> None:
    rows = [
        row_of("0.2000", "same", "0.9000"),
        row_of("0.4000", "same", "0.5000"),
        row_of("0.6000", "same", "0.7000"),
        row_of("0.1000", "different_amount", "0.9"),
    ]
    text = strata_preview(rows, LIMITS)
    spread = {}
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0] in ("same", "different_amount") and len(parts) == 5:
            spread[parts[0]] = parts[1:]
    # Pairs, minimum, median, maximum.
    assert spread == {
        "same": ["3", "0.2000", "0.4000", "0.6000"],
        "different_amount": ["1", "0.1000", "0.1000", "0.1000"],
    }
    assert "3  0.5000  0.7000  0.9000" in text


def test_the_preview_of_no_pairs_does_not_fail() -> None:
    text = strata_preview([], LIMITS)
    assert text.startswith("0 candidate pairs.")


# The command line.


def run(tmp_path: Path, *args: str) -> list[str]:
    return [
        "--raw-dir",
        str(write_raw(tmp_path / "raw", prices=PRICES)),
        "--output",
        str(tmp_path / "interim" / "candidates.csv"),
        *args,
    ]


def test_the_command_writes_the_file_and_reports(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(run(tmp_path)) == 0
    output = capsys.readouterr().out
    assert "candidates.csv: 18 pairs (created)" in output
    assert "by category: cooking_oil 4, lentils 1, rice 12, spices 1" in output
    assert "by size relation:" in output
    with (tmp_path / "interim" / "candidates.csv").open(encoding="utf-8", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 18
    assert main(run(tmp_path)) == 0
    assert "(unchanged)" in capsys.readouterr().out


def test_the_preview_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(run(tmp_path, "--preview-strata")) == 0
    assert "18 candidate pairs." in capsys.readouterr().out
    assert not (tmp_path / "interim").exists()


def test_the_preview_takes_thresholds_from_the_command_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = run(tmp_path, "--preview-strata", "--high", "0.8", "--low", "0.2", "--price-min", "0.5")
    assert main(args) == 0
    output = capsys.readouterr().out
    assert "similar from 0.8" in output
    assert "different below 0.2" in output
    assert "prices close from 0.5" in output


@pytest.mark.parametrize(
    "thresholds",
    [
        ["--high", "0.3", "--low", "0.5"],
        ["--high", "1.5"],
        ["--low", "-0.1"],
        ["--price-min", "0"],
        ["--price-min", "1.5"],
    ],
)
def test_impossible_thresholds_are_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], thresholds: list[str]
) -> None:
    assert main(run(tmp_path, "--preview-strata", *thresholds)) == 1
    assert "error: the thresholds need" in capsys.readouterr().out


def test_the_command_refuses_to_drop_pairs_unless_told_to(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = run(tmp_path)
    output = tmp_path / "interim" / "candidates.csv"
    output.parent.mkdir()
    write_candidates([*build(tmp_path)], output)
    extra = build(tmp_path)[0] | {"pair_id": "meenabazar:9|pandamart:9"}
    write_candidates([*build(tmp_path), extra], output, replace=True)
    assert main(args) == 1
    message = capsys.readouterr().out
    assert "1 pairs of the existing candidates.csv are not in the new one" in message
    assert "use --replace" in message
    assert main([*args, "--replace"]) == 0


def test_unreadable_listings_give_status_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = run(tmp_path)
    (tmp_path / "raw" / "pandamart_20261106.csv").write_text("a,b\n", encoding="utf-8")
    assert main(args) == 1
    assert "error: pandamart_20261106.csv does not have the 12 listing columns" in (
        capsys.readouterr().out
    )


def test_the_command_changes_no_file_in_data_raw(tmp_path: Path) -> None:
    args = run(tmp_path)
    raw = tmp_path / "raw"
    before = {path.name: path.read_bytes() for path in raw.iterdir()}
    main(args)
    assert {path.name: path.read_bytes() for path in raw.iterdir()} == before
