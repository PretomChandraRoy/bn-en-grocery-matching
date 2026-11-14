# Pilot review (stage A1)

Status: approved by the project owner, 2026-11-14. The figures are computed from `data/raw` (22 listings), `data/interim/candidates.csv` (47 pairs) and `data/labelled/labels_L9.csv` (47 labels). No listing title is quoted; listings are identified by source and ID, and everything else by counts. Item 12 of section 6 (the backup check) is for the owner to run and report.

## 1. What was done

**Sources.** Five candidate sources were checked between 2026-11-04 and 2026-11-08 (`docs/sources.md`). Two are usable.

| Source | Automated collection | Redistribution of text | Outcome |
|---|---|---|---|
| Shwapno | no | no | excluded by its terms |
| Daraz (grocery) | no, and manual collection is excluded too | no | excluded by its terms |
| foodpanda (pandamart) | unclear | unclear | manual collection only, pandamart's own store, Gulshan-Banani |
| Chaldal | no, and manual collection is excluded too | no | excluded by its terms (usable only with written permission) |
| Meena Bazar Online (meenabazar) | unclear | unclear | manual collection only, items sold by the shop itself, one delivery location |

**Listings.** 22 listings were accepted into `data/raw`: `pandamart_20261106.csv` and `meenabazar_20261108.csv`, collected on 2026-11-05, 2026-11-06 and 2026-11-08.

| Category | pandamart | meenabazar |
|---|---|---|
| rice | 3 | 3 |
| lentils | 1 | 1 |
| cooking_oil | 1 | 1 |
| spices | 6 | 6 |
| all | 11 | 11 |

Twelve pandamart titles and one meenabazar item were kept in `local/` for tests only and are not in `data/raw`.

**Pairs.** Pairing every pandamart listing with every meenabazar listing of the same category gives 47 pairs: rice 9, lentils 1, cooking oil 1, spices 36 (`candidates.csv`, under DVC).

**Labels.** 47 labels exist, all in `labels_L9.csv`: match 5, non_match 41, unsure 1. They were suggested by an AI assistant and written by a script (see section 5).

**Guidelines.** Version 0.1 (2026-11-04), 0.2 (2026-11-05, script field defined) and 0.3 (2026-11-13, brand lines and origin words). The L9 labels were made under 0.2.

**Software.** 4,301 lines in `src` and 7,066 lines of tests; 1,414 tests pass and `ruff` is clean.

## 2. What worked

| Tool | Evidence |
|---|---|
| Collection validator (`src.collect.validate`) | Both files were accepted with 0 errors and 0 warnings and named by their last collection day. 55 deliberate bugs, one per rule, were applied to scratch copies and all were caught. |
| Normalisation N1 to N4 | N3 read the size of all 22 titles (status "ok"). N4 now writes every unit as kg, g, l or ml, which removes the shops' spelling difference (gm and g, ltr and L): meenabazar writes gm in 6 titles and pandamart writes g in 7. 19 deliberate bugs were caught, and a trial on 300,000 random strings showed no failure of idempotence. |
| Candidate generation (`src.label.candidates`) | 47 pairs, identical bytes on two runs. An independent recomputation (regular expressions and exact fractions) agreed on all 47 pairs with 0 differences. 60 effective deliberate bugs were caught. |
| Labelling tool (`src.label.tool`) | Scripted sessions on the real data saved labels after each answer, resumed, corrected and skipped as designed. The price, the size parser's reading and the candidate scores are not shown or saved. A test shows that importing the tool loads none of the size parser, the features or the validator. 74 deliberate bugs were caught. |
| Label validator (`src.label.validate`) | `labels_L9.csv`: 47 rows, 0 errors, 0 warnings. On a scratch file with 10 deliberate faults it gave 14 errors and 1 warning. On the discarded typed attempt its size cross-check flagged 10 rows. 79 deliberate bugs were caught. |
| DVC backup and restore | `data/raw`, `candidates.csv` and `labels_L9.csv` are tracked by DVC. A restore test on 2026-11-07 gave identical hashes. On 2026-11-11 `data/raw` was restored on a second computer with `dvc pull` and 641 tests passed (reported by the owner). |
| Safety tests | The title-leak test failed correctly when an example in a new test file had been taken from real data, and the example was replaced. |

The deliberate-bug checks missed eight real gaps in the tests on their first run (for example, no test used a Bangla vowel sign on its own). All were closed.

**Not verified in this review:** `dvc status -c` could not be run against the Drive folder, which was not reachable from the session used for this review. It must be run on a computer where Google Drive for desktop is mounted (section 6, item 12).

## 3. What did not work or caused problems

1. **Screenshots instead of copying.** All 22 pilot titles (11 per shop) were transcribed from screenshots. They were accepted without being checked against the websites and may contain small errors. `data/raw` is never edited, so an error found later cannot be corrected in place.
2. **Typing suggested labels.** A first attempt to type the L9 suggestions through the tool produced 46 rows (47 pairs) with transcription errors. The size cross-check flagged 10 of them; errors that do not touch sizes or tags are outside what the validator can see. The file was discarded and replaced by one written by a script. Typing a pair's labels from a list is not how the tool is meant to be used, since a labeller does not type IDs.
3. **Unfilled template lines.** `docs/sources.md` still has six empty lines ("Scripts and languages used" and "Fields available" for the three excluded sources) and two "to be added" markers for meenabazar (the exact terms URL and the delivery location). The dataset card also says "to be added" for the delivery location.
4. **Delivery location not recorded.** Meena Bazar prices of perishable items vary with the delivery location, and the rule is "always the same location". Without the location recorded, the rule cannot be audited.
5. **Sources lost to terms of use.** Three of five sources were excluded. Chaldal was the planned source of Bangla-script titles; its loss removed cross-script matching from the project (see section 4).
6. **Framing change.** The project was framed around Bangla, romanised and English titles. This was found on 2026-11-08 to be wrong for both sources, and building was paused until the framing was changed to cross-shop matching in Latin script.
7. **Guidelines changed after the first look at the pairs.** Version 0.3 was needed because two gaps (brand-line words, and "Deshi") only appeared when the pairs were labelled. More gaps are likely at scale.
8. **Seller not recorded.** The 12 listing columns do not record the seller, so "only items sold by Meena Bazar itself" rests on discipline alone.
9. **Interactive use untested.** Only scripted sessions of the labelling tool were run, so how it behaves in the Windows terminal (the prompts, the keys, long titles) is untested.
10. **No timing.** The hours spent on collecting and labelling were not recorded, so the time per listing and per pair is unknown.
11. **Slips found by the checks.** The assistant misread `source_category` as empty (both shops fill it in every row), used a real-looking example title in a test, and gave two test files the same name. The tests and safety checks caught them. The same checks cannot catch a wrong decision that is consistently implemented, so review of design choices remains necessary.

## 4. What the data showed

**Overlap.** Items were collected independently per shop. 5 of the 11 listings in each shop (45 percent) have a counterpart in the other shop's 11: spices 4 of 6, rice 1 of 3, lentils 0 of 1, cooking oil 0 of 1. Of the 47 pairs, 5 are matches (10.6 percent). The sample is far too small to generalise.

**Size relations (N3).** 18 pairs have the same size and 29 differ in amount; none differ in kind or in pack structure, and all 22 sizes were read. The 29 differing pairs match the 29 `size_differs` tags in L9, and the validator found no disagreement.

**Name similarity** (character-trigram Jaccard on the title without its size):

| Pairs | n | minimum | median | maximum |
|---|---|---|---|---|
| same size | 18 | 0.05 | 0.32 | 1.00 |
| different amount | 29 | 0.00 | 0.15 | 1.00 |

The 5 matches have values 0.52, 0.63, 0.86, 1.00 and 1.00; token Jaccard 0.40 to 1.00. Among the 18 same-size pairs: 0 matches in the 10 below 0.35; 1 match, 0 unsure and 2 non-matches in the 3 from 0.35 to 0.60; 4 matches, 1 unsure and 0 non-matches in the 5 from 0.60 up.

**Price.** The price ratio of the 18 same-size pairs runs from 0.43 to 1.00 (median 0.93). All 5 matches have a ratio of 0.88 or more; 13 of the 18 same-size pairs do.

**Strata preview** (provisional thresholds 0.60, 0.35 and 0.70) against the L9 labels:

| Stratum | Pairs | match | non_match | unsure |
|---|---|---|---|---|
| wording_variation | 8 | 0 | 8 | 0 |
| likely_match | 5 | 4 | 0 | 1 |
| hard_negative | 2 | 0 | 2 | 0 |
| random_negative | 32 | 1 | 31 | 0 |

The `wording_variation` stratum held no match. The one match that was worded differently (0.52) fell between the thresholds, into `random_negative`. The definition (similarity below 0.35) was therefore too low in this sample; with 5 matches nothing firmer can be said.

**Labels (L9).** match 5, non_match 41, unsure 1. Tags: `size_differs` 29, `variant_differs` 34, `brand_differs` 24; 3 notes carry a comment. By category: spices 4 matches in 36 pairs, rice 1 match and 1 unsure in 9, lentils and cooking oil none.

**Titles.** None is in Bangla script: all 22 are Latin; the hand-entered `script` value is english for 18 and romanised for 4 (pandamart 3, meenabazar 1). One of the 11 meenabazar titles is in capitals. Unit spellings differ by shop (see section 2). Of the 11 meenabazar brand fields, 7 appear in the title and 4 do not (they hold a manufacturer); there are 4 distinct values and no "No Brand". The shop's own category label is filled in every row, with 2 distinct values at pandamart and 1 at meenabazar.

## 5. Limits of the pilot

- The 47 labels were suggested by an AI assistant from the guidelines (reserved labeller L9), with synthetic times. They test the tools. They say nothing about agreement between people or about how hard the pairs are for a human, and they are excluded from the dataset and from any agreement statistic.
- 47 pairs, 5 of them matches, 22 listings from two shops, one store and one delivery location, and 77 percent of the pairs in one category (spices): too few for conclusions about thresholds, strata, categories or difficulty.
- The strata thresholds were set before there was any data, and the preview was tested on the same 47 pairs.
- The size parser and the normalisation were checked on 22 titles. Bangla-script titles, multipacks and free-extra quantities did not occur, so those parts were tested on invented titles only.
- The time per listing and per pair, and the pace at which a person can keep going, were not measured.

## 6. Changes to make before full-scale collection

| # | Change | Reason |
|---|---|---|
| 1 | Collect overlap first: products that both shops sell, in several sizes, plus near misses | Independent collection gave 5 matches in 47 pairs; the number of matches grows with the overlap, not with the number of listings |
| 2 | Always copy text with Ctrl+C; check the 22 pilot titles against the websites once | Screenshot transcription may have introduced errors that `data/raw` cannot correct |
| 3 | Record the delivery location, the terms URL and the other empty lines of `docs/sources.md` before the first batch | The rule cannot be audited; the lines are a documented gap |
| 4 | Add a `seller` column to the listing record (decision for the owner) | Cheaper to change before bulk collection; makes "sold by the shop itself" checkable |
| 5 | One accepted file per source per day | `--accept` names a file after its last day and never overwrites, so a second batch on the same day would be refused |
| 6 | Set the strata thresholds from a calibration sample of about 150 labelled pairs, and redefine `wording_variation` | 0 of 8 `wording_variation` pairs matched in this sample, and the one worded-differently match was at 0.52 |
| 7 | Build a sampler that draws the pairs to label by stratum, with a recorded seed and the stratum sizes (inclusion probabilities) | Only a sample can be labelled, and evaluation in stage A2 needs the sampling probabilities |
| 8 | Exclude the reserved labeller L9 explicitly (a named constant and a test) when `pairs_final.csv` and the agreement script are built | Synthetic labels must not reach the dataset or a statistic |
| 9 | Build the checks for `overlap_sample.csv` and `adjudication.csv`, and decide the form of `adjudicated_by` | Needed for the second labeller's sample |
| 10 | Measure the labelling time on the pairs of batch 0, as practice labels in a separate file that is excluded from the dataset (plan, sections 3 and 5) | The 47 pilot pairs cannot be labelled as L1: the owner has seen the assistant-suggested labels for all of them, so L1 labels on them would not be independent. Batch 0 gives the first real timing and the first interactive test of the tool |
| 11 | Label a first 150 pairs, review the guidelines, then freeze the version | Gaps appear when pairs are labelled; later changes require recorded re-checks |
| 12 | Run `dvc status -c` with Drive mounted, and test a restore from the remote after each month | The backup could not be verified in this review |
| 13 | Ask both shops now for written permission to publish listing text, and ask Chaldal for permission to collect | Publication of titles depends on it; Chaldal could supply Bangla-script titles |
