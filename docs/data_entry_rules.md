# Data Entry Rules

These rules describe how to copy listings by hand into a Google Sheet and export them to `data/raw`. They apply to the listing record described in `CLAUDE.md`. Follow `docs/sources.md` for what may be collected from each source and how. Nothing may be collected from a source until its entry there allows it.

## Sheet and file

- Use one sheet per source and collection day.
- The first row holds exactly these column names, in this order: `source`, `listing_id`, `title_raw`, `brand`, `size_value`, `size_unit`, `price_bdt`, `category`, `source_category`, `script`, `url`, `collected_at`.
- Format the `listing_id` and `collected_at` columns as plain text before typing, because Google Sheets otherwise drops leading zeros and reformats dates.
- Export the sheet as CSV (UTF-8) and save it as `data/raw/<source>_<YYYYMMDD>.csv`, for example `pandamart_20261110.csv`. Do not edit a file after collection; a new collection is a new file.

## Columns

| Column | What to enter |
|---|---|
| `source` | A short lower-case name for the shop. For the foodpanda grocery shop use `pandamart`. |
| `listing_id` | The shop's own identifier from the product URL if there is one, otherwise the URL slug. For pandamart it is the numeric product ID at the end of the product URL. |
| `title_raw` | The title copied exactly as displayed, with no changes. |
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
| Radhuni Turmeric Powder 100 gm | `english` | Radhuni is a brand name, so it is ignored. |
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
