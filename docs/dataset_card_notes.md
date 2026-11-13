# Dataset Card Notes

Running notes for the dataset card, which is an A1 deliverable. Each entry records a decision that users of the dataset need to know. Entries are added as decisions are made.

## The script field is a manual annotation

The `script` field of each listing (`bangla`, `romanised`, `english` or `mixed`) is entered by hand at collection time. It is not computed from the title. Judging romanised Bangla against English is subjective, so the field may contain inconsistencies. The four values are defined in `docs/data_entry_rules.md`: brand and variety names are ignored when choosing between `english` and `romanised`, so only generic Bangla words such as chal, dal or tel make a title `romanised`. (Added 2026-11-04.)

## The category field is project-defined

The `category` field takes one of four values defined by this project: `rice`, `lentils`, `cooking_oil` and `spices`. It is not the shop's own category. The shop's label, where available, is kept in the optional `source_category` field. (Added 2026-11-04.)

## Price is hidden during labelling

Labellers see the title, brand, size, source and category of each listing, but not the price, so that a similar price does not influence the decision. Labels therefore rest on the recorded identity fields only. (Added 2026-11-04.)

## Sampling mix and rationale

The pairs offered for labelling are a deliberately non-natural sample, not a random sample of all possible pairs. All pairs are between a pandamart listing and a meenabazar listing. The planned strata are likely matches, hard negatives, random negatives and a wording-variation stratum of about 15 percent. The wording-variation stratum is chosen by category, parsed size and price proximity, but from candidates with low text similarity, because true matches that are worded differently (different word order, brand-line words, abbreviations or spelling) would otherwise be under-sampled.

The final proportions and the reasons for them are to be recorded here once pair generation is built. (Added 2026-11-04; incomplete.)

## Guideline version

Each label records the version of the labelling guidelines in force when it was made (`guidelines_version`). The dataset card must state which versions were used and summarise the version history. When a rule is added or changed, affected earlier labels are re-checked under the new version, and the re-check is recorded in the version history. (Added 2026-11-04.)

## Agreement figures apply to this dataset only

Cohen's kappa is computed on an overlap sample drawn from the sampled pairs described above, not from the natural distribution of pairs. Kappa depends on how common each label is, so the reported figure describes agreement on this dataset and should not be compared directly with figures from other datasets. (Added 2026-11-04.)

## Number of sources

Stage A1 collects listings from two sources: pandamart (foodpanda's own grocery shop, one store) and meenabazar (Meena Bazar Online, items sold by the shop itself, one fixed delivery location). Shwapno, Daraz and Chaldal are excluded because their terms prohibit collection; see `docs/sources.md`. Every cross-shop pair therefore involves the same two shops, so results may not generalise to other shops. (Added 2026-11-04; replaced 2026-11-11.)

## No Bangla-script titles

Neither source uses Bangla-script titles. The dataset therefore covers cross-shop matching in Latin script: variation in spelling, wording, capitalisation, units and brand-line words, with some romanised Bangla words. It does not measure matching between Bangla script and Latin script. The values `bangla` and `mixed` of `script` and the `cross_script` tag do not occur in the data. (Added 2026-11-11.)

## The brand field differs by source

meenabazar gives the brand as a separate field, copied exactly as shown. It often holds the manufacturer rather than the brand and can read "No Brand". pandamart has no brand field, so its brand appears only in the title. Labellers read the brand from the title for both. (Added 2026-11-11.)

## Delivery location

Prices of perishable items on meenabazar vary with the delivery location. All meenabazar listings were collected with the same location (to be added). (Added 2026-11-11.)

## Capitalisation and URL slugs

meenabazar shows product headings as stored, sometimes in title case and sometimes in capitals, and they are copied as shown. A URL slug can disagree with the title; the title is authoritative. (Added 2026-11-11.)

## Redistribution of listing text

For pandamart, the redistribution of listing text is unclear (see `docs/sources.md`). It is treated as not permitted until written permission is obtained. What the public dataset may contain, for example whether `title_raw` can be published, is therefore undecided. (Added 2026-11-04.)

## How the titles were captured

The 11 pilot titles from pandamart were transcribed by hand from screenshots, not copied from the page, so they may contain small errors, for example in spaces or apostrophes. They were accepted for the pilot without being checked against the website. The 11 pilot titles from meenabazar were transcribed from screenshots in the same way, so they may contain the same kinds of small errors. Like the pandamart titles, the 11 meenabazar titles were accepted without being checked against the website. Every later listing is copied directly from the page with Ctrl+C and pasted as plain text. (Added 2026-11-07; extended 2026-11-08 and 2026-11-11.)

## Labeller L9 is reserved for assistant-suggested labels

The labeller ID L9 is reserved for pilot labels suggested by an AI assistant from the labelling guidelines. The 47 labels in `labels_L9.csv` were written to the file by a script and not entered through the labelling tool, and their `labelled_at` times are synthetic (10-second steps from 2026-11-13T23:30:00+06:00). They were made to test the tools only. They are excluded from the final dataset and from every agreement statistic. The ID L1 is reserved for the independent labels of the project owner. A first attempt to enter the same suggestions through the labelling tool produced 46 rows with transcription errors; the size cross-check of the validator for labelled files flagged 10 of them, and the file was discarded. (Added 2026-11-13.)

## Gaps found in the guidelines during the pilot

Reading the pilot pairs showed two gaps in version 0.2 of the guidelines, which version 0.3 is to close: how brand-line words are treated (for example ACI Aroma against ACI Pure), and whether the word "Deshi" names a variant. The version history of the guidelines records the change, and the labels made under each version carry its number in `guidelines_version`. (Added 2026-11-13.)
