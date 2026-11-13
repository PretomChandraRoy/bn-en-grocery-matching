# Data Entry Rules

These rules describe how to copy listings by hand into a Google Sheet and export them to `data/raw`. They apply to the listing record described in `CLAUDE.md`. Follow `docs/sources.md` for what may be collected from each source and how. Nothing may be collected from a source until its entry there allows it.

## Sheet and file

- Use one sheet per source. Rows may come from several collection days.
- The first row holds exactly these column names, in this order: `source`, `listing_id`, `title_raw`, `brand`, `size_value`, `size_unit`, `price_bdt`, `category`, `source_category`, `script`, `url`, `collected_at`.
- Format the `listing_id` and `collected_at` columns as plain text before typing, because Google Sheets otherwise drops leading zeros and reformats dates.
- Export the sheet as CSV (UTF-8, without a byte-order mark) and save it in `local/`, which Git ignores. Never copy a file into `data/raw` by hand; see "Validation and acceptance" below.

## Validation and acceptance

1. Check the file with `python -m src.collect.validate local/<file>.csv`. It lists every error and warning by row and column and changes nothing. Fix errors in the sheet and export again. Warnings, such as a typographic apostrophe or two spaces in a row in a title, are worth checking against the website.
2. When the file has no errors and every title has been checked against the website, accept it with `python -m src.collect.validate --accept local/<file>.csv`. This copies the file byte for byte into `data/raw` as `<source>_<YYYYMMDD>.csv`, named after the last collection day in the file. It never overwrites a file.
3. Then run `dvc add data/raw`, commit `data/raw.dvc`, and back the data up with `dvc push` (see "Backing up").

A listing that is already in `data/raw` cannot be accepted again: re-collecting a listing is not allowed for now. A file in `data/raw` is never edited; a new collection is a new file.

## Backing up

The DVC remote is a folder in Google Drive for desktop, set in `.dvc/config.local` (see "Getting the data" in the README). After each `--accept`, and after each labelling session:

1. Run `dvc add` on the new or changed file (`data/raw`, or the one labelled file) and commit the `.dvc` file.
2. Run `dvc push`, then `dvc status -c`, which should report "Cache and remote 'storage' are in sync."
3. Wait until Google Drive for desktop has finished uploading, and check that the new files appear on the Drive website, before relying on the copy. `dvc push` finishes when the files have been written to the synced folder; the upload to Google happens afterwards. To compare, list the files and sizes in the synced folder with `Get-ChildItem -Recurse -File "<folder>" | Select-Object FullName, Length` in PowerShell, then open the same folder on the Drive website (My Drive, the DVC folder, `files`, `md5`) and check that every subfolder, file name and size matches. An empty file shows as 0 bytes.

The remote folder holds real titles, so it must stay private and must not be shared by link. `local/` is not under DVC: keep a separate copy of anything in it that exists nowhere else, such as the out-of-scope test titles.

## Columns

| Column | What to enter |
|---|---|
| `source` | A short lower-case name for the shop: `pandamart` (the foodpanda grocery shop) or `meenabazar` (Meena Bazar Online). |
| `listing_id` | The shop's own identifier from the product URL if there is one, otherwise the URL slug. For pandamart it is the numeric product ID at the end of the product URL. |
| `title_raw` | The title copied exactly as displayed, with no changes. Copy it directly from the page with Ctrl+C and paste it as plain text. Do not retype it and do not transcribe it from a screenshot. |
| `brand` | The brand, only if the shop shows it as a separate field, exactly as shown. Otherwise leave it blank. Never extract it from the title by hand. |
| `size_value` | The size value, only if the shop shows it as a separate field, exactly as shown (for example `500`). Otherwise leave it blank. Never extract it from the title by hand. |
| `size_unit` | The size unit, only if the shop shows it as a separate field, exactly as shown (for example `gm`). Otherwise leave it blank. |
| `price_bdt` | The selling price shown at the time of collection, as a bare number with no currency sign and no thousands separator. |
| `category` | One of `rice`, `lentils`, `cooking_oil` and `spices`. These are the project's own categories. |
| `source_category` | The shop's own category label for the product, or blank. |
| `script` | One of `english`, `romanised`, `bangla` and `mixed`, entered by hand. See "The script values" below. |
| `url` | The product page address. |
| `collected_at` | The local time of collection with its offset, as plain text, for example `2026-11-03T15:30:00+06:00`. The normalisation code converts it to UTC. |

## Rules for each source

`docs/sources.md` says what may be collected from each source and how. These are the entry rules that follow from it. The validator requires a meenabazar URL to be exactly `https://meenabazaronline.com/product/<slug>/<id>`, with no `www`, query string, fragment or trailing slash, where the slug contains no `/`, `?`, `#` or space and `<id>` equals `listing_id`, and it warns, without failing the file, when a meenabazar `brand` is empty ("No Brand" is a valid value), when a pandamart `brand` is filled in, or when `size_value` or `size_unit` is filled in for either source.

### pandamart

- Only the Gulshan-Banani store, with the site language set to EN.
- `listing_id` is the numeric product ID at the end of the product URL.
- `brand`, `size_value` and `size_unit` are blank, because the shop has no separate fields for them. Labellers read the brand and the size from the title.

### meenabazar

- Only items sold by Meena Bazar itself (the "Sold By" field), always with the same delivery location, which is recorded in `docs/sources.md`.
- `listing_id` is the numeric ID at the end of the product URL, which has the form `/product/<SLUG>/<id>`. The URL slug can disagree with the title (for example one spelling in the URL and another in the title); the title is authoritative.
- `title_raw` is the main product heading, copied as shown. Headings are shown as stored, sometimes in capitals.
- `brand` is the Brand field exactly as shown. It often holds the manufacturer, not the brand (for example a food company's name for a product sold under one of its brands), and it can read "No Brand". Record it as shown; labellers read the brand from the title.
- `price_bdt` is the selling price as shown, with its two decimals (for example `420.00`).
- `size_value` and `size_unit` are blank, because the site has no separate size field. Its "unit" field (EACH or KG) is not a size and must not be entered there.
- Items sold per kg (Unit: KG) are excluded from the pilot, because their size is variable. They can be kept in `local/` for tests only.
- "Add Wishlist" instead of "Add to cart" probably means that the item is out of stock. The listing is still collected.

## The script values

The `script` value describes the script and language of the title as displayed. When judging, ignore digits, punctuation, spaces and unit abbreviations such as kg, gm, ml and ltr.

- `english`: Latin script; English words and product, brand or variety names only.
- `romanised`: Latin script that contains at least one generic Bangla word written in Latin letters, for example chal, dal, tel, morich, holud or moshla.
- `bangla`: Bangla script only.
- `mixed`: both scripts in the same title, including a Latin brand name in a Bangla-script title.

Brand names and variety names are ignored when choosing between `english` and `romanised`, even when they are Bangla words (for example Radhuni, Miniket, Nazirshail or Chinigura). Only generic words for a product or an ingredient make a title `romanised`.

The titles below are invented for illustration.

| Title | Value | Reason |
|---|---|---|
| Miniket Rice 5 kg | `english` | Miniket is a variety name, so it is ignored. |
| Moyurpankhi Turmeric Powder 100 gm | `english` | Moyurpankhi is an invented brand name made from Bangla words, so it is ignored. |
| Pran Soyabean Oil 1 L | `english` | Only a brand name and English words. |
| Teer Chinigura Chal 1 kg | `romanised` | Chal is a generic Bangla word. |
| Moog Dal 500 gm | `romanised` | Dal is a generic Bangla word. |
| Mustard Tel 500 ml | `romanised` | Tel is a generic Bangla word. |
| চাল ১ কেজি | `bangla` | Bangla script only. |
| চাল 1 kg | `bangla` | The digit and the unit abbreviation are ignored. |
| Teer চাল 1 kg | `mixed` | A Latin brand name in a Bangla-script title. |
| Rice চাল 1 kg | `mixed` | Both scripts. |

The `script` value is a manual annotation and may contain inconsistencies, especially between `english` and `romanised`. It is not the same as the `cross_script` tag in the labelling guidelines, which the labelling tool works out from the text of the two titles. Later analysis by script uses the `script` values.

These definitions also appear in `docs/labelling_guidelines.md`. If one changes, change the other.

## Labelled data files

The labelling tool writes the labels to `data/labelled/`. Each file there is added to DVC on its own (`dvc add data/labelled/<file>`), not the folder, so that two labellers never change the same DVC output.

| File | Rows | Columns |
|---|---|---|
| `labels_<labeller>.csv`, one per labeller, only ever added to | One row per pair, labeller and labelling event | `pair_id`, `left_source`, `left_id`, `right_source`, `right_id`, `label`, `note`, `labeller`, `labelled_at`, `guidelines_version` |
| `adjudication.csv` | One row per adjudicated pair | `pair_id`, `final_label`, `final_note`, `reason`, `adjudicated_by`, `adjudicated_at`, `guidelines_version` |
| `overlap_sample.csv` | One row per pair in the second labeller's sample | `pair_id`, `seed`, `drawn_at` |
| `skipped_<labeller>.csv` | One row per pair skipped because of excluded content, such as a bundle of different products | `pair_id`, `reason`, `skipped_at` |

Rules for these files:

- `labeller` is a pseudonymous ID such as `L1` or `L2`, never a name, because the dataset will be public. A labeller's file is named after their ID.
- `pair_id` is `<left_source>:<left_id>|<right_source>:<right_id>`. The source that comes first alphabetically is the left one; if both are the same source, the smaller `listing_id` comes first. The four ID columns must agree with `pair_id`.
- `labelled_at`, `adjudicated_at`, `drawn_at` and `skipped_at` use an ISO 8601 time with the local offset, in the same form as `collected_at`, for example `2026-11-07T15:30:00+06:00`.
- `label` is one of `match`, `non_match` and `unsure`. `note` holds the tags from `docs/labelling_guidelines.md` separated by semicolons, with an optional comment after ` # `.
- The tool fills in `guidelines_version` from the `Version:` line of `docs/labelling_guidelines.md`, and adds the `cross_script` tag itself.
- A labeller's current label for a pair is their latest row for it. Earlier rows are kept. A correction, or a re-check after the guidelines change, adds a new row with the new `guidelines_version`; nothing is deleted or edited.
- The labelling tool for one labeller never reads another labeller's file, so that the labels stay independent.
- Consistency rules, which the validator for labelled files checks (all except the last, which waits for the check of `adjudication.csv`): the tags `size_differs`, `variant_differs`, `brand_differs` and `unit_kind_differs` require the label `non_match`; `brand_missing` requires `unsure` or `non_match`; both listings exist in `data/raw`; `guidelines_version` appears in the version history of the guidelines; `labelled_at` is not in the future; adjudicated pairs are in the overlap sample.

Check the label and skipped files with `python -m src.label.validate`, which checks every `labels_<labeller>.csv` and `skipped_<labeller>.csv` in `data/labelled` (or the files named) and changes nothing. Errors, which make the exit status 1, are a wrong header, encoding or file name; a `pair_id` that is malformed, in the wrong order, from one source, absent from `data/raw` or (once `candidates.csv` exists) absent from it; ID columns that disagree with `pair_id`; an unknown label or tag, or a break of the consistency rules above; a `cross_script` tag that is missing or surplus; a `labeller` that differs from the file name; a `labelled_at` that is malformed, in the future or earlier than the row above; and a `guidelines_version` that is not in the version history. Warnings, which do not fail a file, report where the size parser (N3) reads the two titles differently from the labels and tags, for example a `match` whose sizes N3 reads as different, or a `size_differs` tag where N3 reads equal sizes. N3 can be wrong, so these are for review; the labels are made from the titles, not from N3. Run the validator after each labelling session, before `dvc add`. The messages name rows, columns and IDs and never contain a title.

Generated files, which are never edited by hand:

- `data/interim/candidates.csv` lists the candidate pairs with the strategy and features that selected each one (see "Candidate pairs" below). Keeping this outside `data/labelled/` leaves the label files in the agreed pair-record format plus `guidelines_version`.
- `data/interim/pairs_final.csv` has one row per pair for the published dataset: the adjudicated label if there is one, otherwise the single labeller's current label, together with both original labels for the pairs in the overlap sample.

Agreement is computed from each labeller's latest label made before the first row of `adjudication.csv`. A script prints Cohen's kappa and the percentage of identical labels, and the figures are recorded in `docs/reviews/`.

## Candidate pairs

`python -m src.label.candidates` writes `data/interim/candidates.csv` from the listings in `data/raw`. For the pilot, a candidate is every pair of listings from two different sources in the same project category (pandamart by meenabazar). The file is generated, never edited by hand, and is the same on every run: it has no timestamp and no random choice. It holds IDs and numbers only, never a title and never a price, so it can be tracked by DVC like the other data files. After generating it, run `dvc add data/interim/candidates.csv`, commit the `.dvc` file and `dvc push`. A new run refuses to replace an existing file that has pairs the new one lacks, because labels may refer to them; `--replace` overrides this.

The text features compare the names of the products and not their sizes: the title is cleaned (`title_norm`, which writes every unit as `kg`, `g`, `l` or `ml`), and then the numbers, the units after them and the `x` of a multipack are dropped. The size features use the reading of the sizes by N3, with the total of a pack being its size times its pack count. The price features are ratios of the smaller to the larger value, from 0 to 1, rounded to four places. These features are for sampling and analysis. The labelling tool shows labellers none of them.

| Column | Meaning |
|---|---|
| `pair_id` | The pair, in the form of the label files |
| `left_source` | The source of the left listing, the one that comes first alphabetically |
| `left_id` | The `listing_id` of the left listing |
| `right_source` | The source of the right listing |
| `right_id` | The `listing_id` of the right listing |
| `category` | The project category, which both listings share |
| `strategy` | How the pair was chosen; `pilot_all_pairs` means that every pair was taken |
| `token_jaccard` | Shared name words over all name words |
| `token_overlap` | Shared name words over the words of the shorter name |
| `char3_jaccard` | Shared character trigrams over all trigrams of the names, written without spaces |
| `size_relation` | `same`, `same_total_different_pack`, `different_amount`, `different_kind` or `unknown` (a size was not read) |
| `left_kind` | `weight` or `volume` for the left size; empty if it was not read |
| `left_total` | The left total in grams or millilitres; empty if the size was not read |
| `left_packs` | The left pack count; empty if the size was not read |
| `right_kind` | `weight` or `volume` for the right size; empty if it was not read |
| `right_total` | The right total in grams or millilitres; empty if the size was not read |
| `right_packs` | The right pack count; empty if the size was not read |
| `size_ratio` | The smaller total over the larger; empty unless both sizes were read and are of one kind |
| `price_ratio` | The smaller price over the larger |
| `unit_price_ratio` | The ratio of the prices per 100 g or 100 ml; empty unless `size_ratio` is given |
| `left_script` | The `script` value of the left listing |
| `right_script` | The `script` value of the right listing |
| `cross_script` | `true` if exactly one title has Bangla letters, as for the tag of that name; otherwise `false` |

The sampling strata are not decided. `python -m src.label.candidates --preview-strata` prints, without writing anything, how the pairs would split into the provisional strata `wording_variation`, `likely_match`, `hard_negative` and `random_negative`, and how the features are spread. The thresholds of the preview can be changed with `--high`, `--low` and `--price-min`.

## Labelling with the tool

Read `docs/labelling_guidelines.md` before every session. Then run `python -m src.label.tool --labeller L1`, with your own ID in place of `L1` (the letter L and digits, never a name). The tool needs `data/interim/candidates.csv` and the listings in `data/raw`. It prints the version of the guidelines when it starts and stamps that version on every label.

For each pair the tool shows the two listings side by side: the source, the category, the brand field, the `size_value` and `size_unit` fields only if the shop filled them in, and the title exactly as collected. The brand field can hold the manufacturer instead of the brand; read the brand from the title. Read the size from the title too, as the guidelines require. The tool never shows the price, the reading of the size by the size parser (N3) or the scores and strata of the candidate pairs, because the labels will later be used to evaluate that parser and the matching models, and they must not depend on them. The comparison of the labels with N3's reading is made afterwards, by the validator, as warnings. If Bangla text does not line up in the two columns on your terminal, use `--width 60`, which stacks the two listings.

Type a key and press Enter. A bare Enter does nothing, so that no label is given by accident.

| Key | Meaning |
|---|---|
| `m` | The label `match` |
| `n` | The label `non_match` |
| `u` | The label `unsure`, only when the information shown cannot settle the question |
| `s` | Skip the pair, only for excluded content such as a bundle of different products; the tool asks for a reason, and an empty reason cancels. A difficult pair gets `unsure`, not a skip |
| `b` | Go back to the previous pair and correct its label |
| `q` | Quit; the labels are already saved |
| `?` | Show the keys |

After a label the tool lists the allowed tags and asks for an optional note: tags separated by semicolons with no spaces, then optionally a comment after ` # `, or only `# comment`. A note that breaks the consistency rules is refused with the reason, and `<` goes back to choose the label again. The tag `cross_script` is added by the tool when exactly one title has Bangla letters; a typed one is ignored. When a pair is corrected with `b`, `=` keeps the current note.

Every label is appended to `data/labelled/labels_<labeller>.csv` and flushed to disk at once, so nothing is lost if the session ends. Rows are never edited or deleted: a correction adds a row, the current label of a pair is its latest row, and a correction that changes nothing adds nothing. A skipped pair is appended to `skipped_<labeller>.csv`. Starting the tool again resumes with the first pair that has no label and was not skipped. The pairs come in a fixed order that depends only on the `pair_id`, so adding pairs later does not reorder the existing ones. The tool reads and writes only the files of its own labeller. It stops with a message, and writes nothing, if the guidelines version is not in the version history, if the candidates or the listings cannot be read, if the labeller's own files are malformed, or if the clock of the computer reads earlier than the last row.

After each session: run `python -m src.label.validate`, then `dvc add data/labelled/labels_<labeller>.csv` (and the skipped file, if there is one), commit the `.dvc` file, `dvc push`, `dvc status -c`, and wait for the Google Drive upload to finish. The options of the tool are `--labeller` (required), `--raw-dir`, `--labelled-dir`, `--candidates`, `--guidelines` and `--width`.
