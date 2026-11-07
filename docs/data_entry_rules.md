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
| `source` | A short lower-case name for the shop. For the foodpanda grocery shop use `pandamart`. |
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
- Consistency rules, which the validator for labelled files will check: the tags `size_differs`, `variant_differs`, `brand_differs` and `unit_kind_differs` require the label `non_match`; `brand_missing` requires `unsure` or `non_match`; both listings exist in `data/raw`; `guidelines_version` appears in the version history of the guidelines; `labelled_at` is not in the future; adjudicated pairs are in the overlap sample.

Generated files, which are never edited by hand:

- `data/interim/candidates.csv` lists the candidate pairs with the strategy and scores that selected each one. Keeping this outside `data/labelled/` leaves the label files in the agreed pair-record format plus `guidelines_version`.
- `data/interim/pairs_final.csv` has one row per pair for the published dataset: the adjudicated label if there is one, otherwise the single labeller's current label, together with both original labels for the pairs in the overlap sample.

Agreement is computed from each labeller's latest label made before the first row of `adjudication.csv`. A script prints Cohen's kappa and the percentage of identical labels, and the figures are recorded in `docs/reviews/`.
