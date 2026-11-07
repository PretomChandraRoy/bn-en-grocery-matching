# Dataset Card Notes

Running notes for the dataset card, which is an A1 deliverable. Each entry records a decision that users of the dataset need to know. Entries are added as decisions are made.

## The script field is a manual annotation

The `script` field of each listing (`bangla`, `romanised`, `english` or `mixed`) is entered by hand at collection time. It is not computed from the title. Judging romanised Bangla against English is subjective, so the field may contain inconsistencies. The four values are defined in `docs/data_entry_rules.md`: brand and variety names are ignored when choosing between `english` and `romanised`, so only generic Bangla words such as chal, dal or tel make a title `romanised`. (Added 2026-11-04.)

## The category field is project-defined

The `category` field takes one of four values defined by this project: `rice`, `lentils`, `cooking_oil` and `spices`. It is not the shop's own category. The shop's label, where available, is kept in the optional `source_category` field. (Added 2026-11-04.)

## Price is hidden during labelling

Labellers see the title, brand, size, source and category of each listing, but not the price, so that a similar price does not influence the decision. Labels therefore rest on the recorded identity fields only. (Added 2026-11-04.)

## Sampling mix and rationale

The pairs offered for labelling are a deliberately non-natural sample, not a random sample of all possible pairs. The planned strata are likely matches, hard negatives, random negatives and a cross-script stratum of about 15 percent. The cross-script stratum is chosen by category, parsed size and price proximity instead of text similarity, because text similarity between Bangla-script and Latin-script titles is close to zero and would otherwise leave cross-script matches under-sampled.

The final proportions and the reasons for them are to be recorded here once pair generation is built. (Added 2026-11-04; incomplete.)

## Guideline version

Each label records the version of the labelling guidelines in force when it was made (`guidelines_version`). The dataset card must state which versions were used and summarise the version history. When a rule is added or changed, affected earlier labels are re-checked under the new version, and the re-check is recorded in the version history. (Added 2026-11-04.)

## Agreement figures apply to this dataset only

Cohen's kappa is computed on an overlap sample drawn from the sampled pairs described above, not from the natural distribution of pairs. Kappa depends on how common each label is, so the reported figure describes agreement on this dataset and should not be compared directly with figures from other datasets. (Added 2026-11-04.)

## Number of sources

Stage A1 collects listings from two or more sources, not the three originally planned. Shwapno and Daraz are excluded because their terms prohibit automated collection and the use of listing content (for Daraz, manual collection as well); see `docs/sources.md`. The pilot may use only pandamart (foodpanda's own grocery shop) and possibly Chaldal, subject to the source checks. Every cross-shop pair then involves the same two shops, so results may not generalise to other shops. (Added 2026-11-04.)

## Redistribution of listing text

For pandamart, the redistribution of listing text is unclear (see `docs/sources.md`). It is treated as not permitted until written permission is obtained. What the public dataset may contain, for example whether `title_raw` can be published, is therefore undecided. (Added 2026-11-04.)

## How the titles were captured

The 11 pilot titles from pandamart were transcribed by hand from screenshots, not copied from the page, so they may contain small errors, for example in spaces or apostrophes. They were accepted for the pilot without being checked against the website. Every later listing is copied directly from the page with Ctrl+C and pasted as plain text. (Added 2026-11-07.)
