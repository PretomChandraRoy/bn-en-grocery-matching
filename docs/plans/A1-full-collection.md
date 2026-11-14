# Full-scale collection plan (stage A1)

Status: revised and approved by the project owner, 2026-11-14. Decisions 1 to 9, 13, 15, 16 and 17 of section 8 are decided; decisions 10, 11, 12 and 14 are actions for the owner and stay open. It covers the rest of stage A1, from 2026-11-16 until plan C is complete (about 24 April 2027), and rests on `docs/reviews/A1-pilot.md`. Every number that comes from an assumption, not a measurement, is marked as such; batch 0 replaces the time assumptions with measured values.

## 1. Target and arithmetic

**Target.** About 1,000 labelled pairs (plan C, decision 1; stage A1 in `CLAUDE.md`). The three sizes below are nested and use the same procedure. A and B are kept for reference: at 5 hours a week they would end about 11 June and 25 July 2027.

| | A | B | C |
|---|---|---|---|
| Labelled pairs | 2,000 | 1,500 | 1,000 |
| likely_match | 400 | 300 | 200 |
| wording_variation | 300 | 225 | 150 |
| hard_negative | 700 | 525 | 350 |
| random_negative | 600 | 450 | 300 |
| Expected matches, if every true match is in the first two strata (assumption) | about 460 | about 345 | about 230 |
| Products sold at both shops (overlap) | 500 | 380 | 250 |
| Other listings per shop (extras) | 150 | 120 | 80 |
| Listings per shop | 650 | 500 | 330 |
| Listings in all | 1,300 | 1,000 | 660 |
| Candidate pairs in the category (universe) | about 112,000 | about 66,000 | about 29,000 |
| Share of the universe labelled | 1.8 percent | 2.3 percent | 3.5 percent |
| **Sensitivity: 20 percent of true matches fall in other strata.** Matches expected with the same overlap | about 370 (18 percent of the pairs) | about 275 (18 percent) | about 185 (18 percent) |
| Overlap needed to still reach the expected matches | 625 (+125) | 475 (+95) | 313 (+63) |
| Extra collection hours for that overlap, with contingency | 18.6 h | 14.1 h | 9.4 h |

**The two strata that hold the matches are a census, not a sample.** `likely_match` and `wording_variation` are meant to contain nearly every true match among the collected pairs. Every pair in them is labelled (take-all), and their thresholds are set so that their populations are within about 25 percent of the targets above (section 4). Only `hard_negative` and `random_negative` are samples. The expected matches therefore equal nearly all the true matches. A true match outside the two strata is never labelled; in the pilot, 1 of the 5 matches was outside them (similarity 0.52, between the thresholds). The sensitivity rows show the cost of a leak of that size: either about 18 percent of the labelled pairs are matches instead of 23, or the overlap must rise by a quarter. If the populations turn out larger than the targets, the two strata are samples, not censuses, and the expected matches fall further (the gate in section 4).

**How the numbers follow.**

- Pairs are formed only within a category, so the universe is the sum over categories of (listings of one shop) x (listings of the other). With a category mix per shop of spices 35, rice 20, cooking oil 20 and lentils 25 percent (a hypothesis until scouting), 650 listings per shop give 228^2 + 130^2 + 130^2 + 163^2 = about 112,000 pairs.
- The matches come from the two census strata. Assume 90 percent of the `likely_match` pairs and 33 percent of the `wording_variation` pairs are matches. These rates are assumptions: in the pilot, 4 of the 5 `likely_match` pairs were matches and none of the 8 `wording_variation` pairs, and 5 matches are not evidence. For A: 0.9 x 400 + 0.33 x 300 = about 460.
- Each match needs one product that both shops sell, so the overlap must be at least the number of matches. An overlap of 500 for A leaves a margin of about 9 percent.
- The extras are listings with no counterpart: near-miss siblings (another brand, line, origin or variant), unbranded staples and shop-only products. About 23 percent of the listings.
- Hard negatives come mostly from the sizes. A family with k sizes at both shops gives k matches and k(k-1) same-name, different-size pairs. If the 500 overlapping products fall into about 200 families of 2.5 sizes on average, that is about 750 pairs, which covers the 700 required before counting near-miss siblings.
- The 22 pilot listings count towards the listings if their titles are confirmed (section 3).

## 2. Product selection

**Why overlap first.** In the pilot the shops were sampled independently and 5 of 47 pairs were matches. The number of matches is the number of products that both shops sell, however many other listings are collected.

**Procedure.**

1. **Scouting pass (about 3 hours, before batch 1).** For each category in each shop, count the listings, note the brands and sizes, and estimate the overlap. This is the gate: I have not checked what either shop lists. If fewer than about 40 percent of the products in the four categories are sold by both shops, return to this plan before collecting.
2. **Product families.** Build a worklist of families (brand, product, variety, line), each with the sizes sold at both shops. Brands seen in the pilot are ACI (lines Pure and Aroma), Radhuni, Pran, Pusti, Fresh and Rupchanda; the scouting pass decides the rest.
3. **Several sizes each**, on average 2.5 per family.
4. **Near misses**: the same product in another size; the same brand in another line; another brand of the same product; another variety; and, for lentils and rice, the deshi and imported versions (a rule of guidelines 0.3).
5. **Unbranded staples**: loose rice and lentils at both shops, about 15 percent of the overlapping products.
6. **Extras**: shop-only products and further siblings, as in section 1.

**Categories.** Keep the four. They are built into the validator, the guidelines, the tests and the dataset card; they cover branded packaged goods (spices, oil, rice) and loose staples (rice, lentils), which exercise different rules of the guidelines; and the pilot's overlap came from branded packaged goods. Weigh the collection by the scouting results; I expect spices and packaged cooking oil to overlap most and lentils to need the most searching, but this is a hypothesis from 22 listings. Each category should have at least 15 percent of the listings, so that error analysis per category in stage A2 has data. Add a fifth category (for example sugar, flour or tea) only if scouting shows that the four cannot supply the overlap. That is a small change (one constant, the tests and the documents).

## 3. Collection procedure

- **Copy, never screenshots.** Select the title on the page, copy it with Ctrl+C and paste it as plain text. Copy the brand field, the price and the ID the same way.
- **Both sides together.** Collect a product family at both shops in the same session, so that catalogue and price changes do not separate the two sides. A listing already in `data/raw` cannot be collected again.
- **Worklist.** Keep a collection sheet outside the repository (it holds titles for convenience) with the family list and, for each family, the intended counterparts and the designed near misses. Its ID columns are exported for decision 16 (section 4).
- **Fixed conditions.** pandamart: the Gulshan-Banani store, site language EN. meenabazar: items sold by Meena Bazar itself, always the same delivery location. Record the location and the terms URL in `docs/sources.md` before batch 1. I suggest a delivery location in the same area as the pandamart store, so that prices are comparable; this is a suggestion, not a verified fact about either shop.
- **Sessions.** One session per day produces one file per source, named after the source and the last collection day; `--accept` never overwrites, so a second file for the same source on the same day is refused. A session has 30 listings in all (about 15 per shop; decision 7). It takes about 1.25 hours when the listings have no counterpart to find (2.5 minutes each) and about 1.6 hours when all are overlapping pairs (2.5 minutes for the first listing of a pair and 4 minutes for the second, which includes 1.5 minutes to find it), plus about 15 minutes to validate, accept and back up. These are assumptions. The overhead of 22 sessions for C (5.5 hours) is included in section 6.
- **After each session.** Validate, `--accept`, `dvc add`, commit the `.dvc` file, `dvc push`, `dvc status -c`, and wait for the Drive upload.
- **Batch 0.** One timed session of 30 listings (about 6 product families at both shops). Replace the time assumptions of section 6 with the measured values, and time the labelling of up to 50 of its pairs (all of them if fewer). These pairs are practice labels: they go to a separate practice file and are not part of the dataset (section 5), because they are not drawn by the sampler and their inclusion probability is unknown.
- **Yield report.** After each session, run `python -m src.label.candidates --preview-strata` and note per category the listings, the overlap found and the pairs. If the share of deliberately paired products that turn out to be matches falls below about 70 percent, change the search method.
- **Terms.** Re-read the terms of both shops at the start of December and record the date.

**Pilot titles (decision 6).** Check each of the 22 pilot titles against its page (about 30 minutes). If all are correct, nothing needs building, and the listings stay. If any is wrong, a fix is impossible today: `data/raw` is never edited and `--accept` refuses a listing already in `data/raw`. Proposed mechanism, to be built only if a title is wrong: a tracked list of superseded files (`docs/superseded_files.csv`: file name, date, reason, replaced-by; no titles).

- A listed file stays in `data/raw` and in DVC. The collection validator ignores its listing IDs in the duplicate check, so the corrected listing can be collected again and accepted as a new file. The loader (`load_listings`) skips the rows of a listed file, so no ID appears twice anywhere downstream.
- It touches `src/collect/validate.py` (duplicate check, `--accept`), `src/label/listings.py` (loader), `docs/data_entry_rules.md` with a sync test of the list format, and the tests of the validator, the loader, the candidate generator and the data-safety check that every raw file is valid. About 25 new tests, 8 to 10 deliberate-bug checks, half a day of assistant work.
- Rule: supersede a file only before its listings are labelled, because a label is made from the title.
- Simpler alternative if only a few titles are wrong: an exclusion list that drops those listings from the dataset. It touches only the loader and the sampler (about 10 tests) and loses the listings.

**Seller column (decision 5).** The pilot files cannot be edited, so adding `seller` makes a second schema version. Version 1 is the 12 columns of the pilot files; version 2 adds `seller` as the last column.

- The validator reads the header: exactly the 12 columns means version 1, exactly the 13 means version 2, anything else is an error. A version 1 file is accepted only if every row was collected before a cutover date (the day of the first version 2 session), so that new sessions cannot omit the seller.
- In version 2, `seller` is required and must be a value allowed for the source: for meenabazar the text of the "Sold By" field for Meena Bazar itself, to be recorded in `docs/sources.md` from the page during scouting (I have not seen the exact text); for pandamart the value `pandamart`. Any other value, including a third party or an empty field, is an error.
- Duplicate checks read both versions by column name. The loader reads both; `seller` is not part of `Listing`, so the labelling tool cannot show it. `--accept` copies bytes as before. For version 1 meenabazar rows the seller is unknown, and the dataset card says so.
- Cost: edits in `src/collect/validate.py`, `src/label/listings.py`, the test builders and about eight test files that import the column list, and four documents (the data design in `CLAUDE.md`, the entry rules, the card notes, and the sheet template). About 50 new tests and 10 to 15 deliberate-bug checks: one build step of about the size of piece 1b (a day of assistant work and about an hour of your review). The sheet gets one more column.

## 4. Sampling

**Strata and proportions.** Four strata as in the pilot, with the sizes of section 1 (for A: likely_match 20 percent, wording_variation 15, hard_negative 35, random_negative 30). Reasons: the first two contain the matches; hard negatives are where models fail and give the most for error analysis; random negatives show how much of the universe is trivially negative, which blocking relies on.

**Take-all strata and the gate.** `likely_match` and `wording_variation` are drawn take-all (section 1). When the thresholds are set, count the populations of both strata. In the pilot the wording stratum held 8 of 47 pairs (17 percent); if a similar share held at scale it would be thousands of pairs, far more than 300. If either population is more than about 25 percent above its target, the stratum has to be narrowed. Narrowing is not free: every true match that the narrower definition leaves out falls into a sampled stratum (`hard_negative` or `random_negative`) and is probably never labelled. That is the leak of section 1. Therefore:

1. **Estimate the expected leak before tightening**, from the calibration sample below. For each tightening option, the leak is the estimated number of true matches in the pairs it excludes: for each similarity band and price band of the calibration sample, the share of matches in the sample times the number of pairs in that band of the universe, summed over the excluded bands, with an interval from the sample size. State it as a number of matches and as a share of all estimated true matches.
2. **Tighten by the price minimum first** (raise it from 0.70), and raise `low` only if that is not enough. Price proximity separated best in the pilot: raising the minimum from 0.70 to 0.85 would have removed 3 of the 18 same-size pairs and none of the 5 matches (a small sample, not evidence).
3. **Record the estimated leak** (the number, the share, the interval, and the definition it belongs to) in `docs/dataset_card_notes.md` before the main draw. If the estimated leak is above 20 percent, the sensitivity row of section 1 applies; choose between a larger overlap, accepting a sampled stratum, or the intended pairs (decision 16).
4. If tightening does not bring a population near its target without a larger leak, the stratum stays a sample, its matches are sampled, and the expected matches of section 1 fall by the unsampled share.

**Thresholds from real data.** The pilot thresholds were guesses, and in the pilot the `wording_variation` stratum held no match. In the first half of January, after the December sessions (about 310 listings, a little under half of C's 660):

1. Draw a calibration sample of about 150 pairs. Pairs are formed within categories only, never across them. Take pairs from all four categories, at least 25 from each, from those with the same size and a price ratio of 0.7 or more, spread evenly over bands of name similarity. Label it as L1.
2. Read off the share of matches per band. Set `high` at the similarity from which at least about 80 percent are matches, and `low` at the similarity below which fewer than about 10 percent are.
3. Define `wording_variation` as same size, price ratio of 0.7 or more, and similarity between `low` and `high`; `likely_match` as same size and similarity from `high`; `hard_negative` as similarity from `high` with a different size, line, brand or origin; `random_negative` as the rest.
4. Freeze the thresholds, the seed and the stratum definitions in `docs/dataset_card_notes.md` before the main draw. The calibration pairs are labelled pairs of the dataset, and their inclusion probabilities are recorded.

**Intended pairs (decision 16).** While collecting, record for each product family the pairs of listings that are intended as the same product (counterparts) and the designed near misses (another size, line, brand or origin). Label these intended pairs with certainty, whatever their similarity. This closes the leak of section 1 for the matches that the collector paired on purpose. Matches that were not intended can still be found only through `wording_variation`.

- **The worklist holds listing IDs only, never titles.** Each row has the two (source, listing ID) values of the pair, a numeric family number and the kind (match intended, near miss); no title, no brand and no text copied from a page. The titles stay in the collection sheet, which is outside the repository.
- **Where it lives (proposal): `data/interim/intended_pairs.csv`, tracked by DVC, not by Git and not in `local/`.** The sampler reads it, so the draw can be reproduced only if the file is versioned with the data. The project rule is that data is versioned with DVC and never committed to Git. `local/` is ignored by Git and is not under DVC, so a lost disk would lose the intended pairs and with them the draw. Because it holds IDs only, no listing text enters the repository either way. A safety test checks its columns. The alternative, tracking it in Git, would work technically but breaks the rule for data files.

**The draw.** A sampler (to be built; section 8) draws the pairs by stratum in rounds of 25 percent, each round stratified in the same proportions, so that stopping after any round leaves a valid stratified sample. It records the stratum, the seed and the number of pairs in each stratum's universe. The sampler excludes every pair whose two listings are both in the pilot files and every pair in the practice file (section 5), and the labelling tool reads the sampler's output, so `candidates.csv` stays the universe and the L9 rows stay valid against it.

**Selection bias.** The listings are chosen deliberately, overlap first. The recorded sampling probabilities correct for which pairs of collected listings are labelled; they do not correct for which listings were collected. Every metric therefore describes pairs of collected listings, not the shops' catalogues, and not the pairs a customer would meet. The dataset card must say so in its own entry.

## 5. Labelling

- **L1** is the owner's independent labels under guidelines 0.3. The tool hides the price, the size parser's reading and the strata; the order is a hash of the pair ID. The owner collected the data and knows which pairs were meant to match, which is a risk of bias; the second labeller reduces it.
- **The 47 pilot pairs (decision 15).** The owner has seen the assistant-suggested labels (L9) for all 47 pairs, so L1 labels on them would not be independent. They are not labelled as L1. Recommended: exclude the 47 pairs from the dataset and from the sampling universe, but keep the 22 pilot listings if the title check passes; pairs between a pilot listing and a new listing are unaffected. The alternative, keeping them with a flag, would add 5 matches but no clean labels, because they would have to be left out of every agreement and evaluation figure anyway. The L9 labels stay as test data for the tools.
- **Practice labels from batch 0 (decision 15).** The up to 50 pairs labelled to measure the time are not drawn by the sampler, so their inclusion probability is unknown, and labelling them again later for the dataset would not be independent. They are therefore practice, kept in a separate file: `data/practice/labels_L1.csv` (labeller L1; the folder name marks it as practice). To make sure that no pilot pair is offered, build a candidates file from the batch 0 files alone: run `python -m src.label.candidates` with `--raw-dir` pointing at a folder that holds copies of the batch 0 files and `--output data/practice/candidates.csv`, then run the tool with the same `--raw-dir` and `--candidates` and with `--labelled-dir data/practice`. No new code is needed. The practice file is excluded from the dataset and from every statistic: the default validator, `pairs_final.csv` and the agreement script read `data/labelled` only, and the practice file is validated by naming it. The sampler excludes its pairs from the universe in the same way as the 47 pilot pairs. Track it with `dvc add data/practice/labels_L1.csv`; the data-safety test is extended to `data/practice`.
- **Time per pair** (assumption): 20 seconds for random negatives, 45 for likely matches and hard negatives, 90 for wording-variation pairs, plus 15 percent for session starts, notes and corrections: about 51 seconds on average. Measure it on the batch 0 practice pairs and replace the assumption. Sessions of 100 pairs, then `python -m src.label.validate` and the DVC steps (10 minutes).
- **Guidelines checkpoint.** Label the calibration pairs, review the gaps, issue version 0.4 if needed, and freeze the version by 2027-01-31. A later change needs a recorded re-check (version history).
- **Second labeller (L2): a stratified sample, not a simple random one.** A simple random sample of 150 pairs gives only about 35 matches at these proportions, and kappa is unstable when one class is rare. Draw the overlap sample by the sampling strata, from the pairs L1 has labelled, with at least about 50 expected matches: 45 from `likely_match`, 30 from `wording_variation`, 40 from `hard_negative` and 35 from `random_negative` (150 pairs; expected matches 0.9 x 45 + 0.33 x 30 = about 50). Record the seed and the number drawn from each stratum. This changes step 1 of "Agreement and adjudication" in the guidelines, which says "at random"; the change goes into version 0.4.
- **Agreement.** Compute the three-label Cohen's kappa as the guidelines require, and report with it the positive agreement (2a / (2a + b + c)) and the negative agreement (2d / (2d + b + c)), where a is both matches, d is both not-matches (non_match or unsure), and b and c are the disagreements, each with a bootstrap interval. State that kappa describes this stratified sample, not the dataset. L2 labels independently, without seeing L1; then the two labellers go through the disagreements and agree the final labels (about 2 hours for L2 and about 3 hours for the owner, assumption). A person must be found now.
- **L9** is not used for the dataset or any statistic.

## 6. Time estimate

**Assumptions (not measured; replaced after batch 0).**

- Collection: 2.5 minutes to find and copy a listing; 1.5 minutes to find the counterpart of a listing at the other shop, so 4 minutes for the second listing of a pair and 6.5 minutes for the pair; 15 minutes per session of 30 listings (decision 7) to validate, accept and back up; 10 percent extra to fix validator errors. Collection hours = listings x 2.5 min + overlap products x 1.5 min + sessions x 15 min, plus 10 percent of the first two. For C: 660 x 2.5 min = 27.5 h, 250 x 1.5 min = 6.2 h, 22 sessions x 15 min = 5.5 h, fixes 3.4 h; total 42.6 h. Sessions of 30 listings instead of 50 add 2.2 h to C. A session of 30 takes about 1.25 h (no counterparts) to 1.6 h (15 overlapping pairs), plus 0.25 h.
- Labelling: the times of section 5.
- Preparation 13 h (scouting 3, permission requests 2, the gaps of `docs/sources.md` 1, title check 0.5, review of the new tools 3, planning and decisions 2.5, labelling up to 50 batch 0 pairs as practice 1); overlap sample and adjudication 3 h; documents 25 h (dataset card, stage review `docs/reviews/A1.md`, progress notes, reproduction from a clean clone). These 41 h are the same for A, B and C. Contingency 15 percent.

| | A (2,000) | B (1,500) | C (1,000) |
|---|---|---|---|
| Collection (sessions of 30 listings) | 84.2 h | 64.6 h | 42.6 h |
| Labelling and session checks | 31.6 h | 23.7 h | 15.8 h |
| Preparation, overlap sample, documents | 41.0 h | 41.0 h | 41.0 h |
| Contingency (15 percent) | 23.5 h | 19.4 h | 14.9 h |
| **Total** | **180.3 h** | **148.7 h** | **114.3 h** |
| Weeks at 5 h a week | 36.1 | 29.7 | 22.9 |
| End, from 2026-11-16 | about 25 Jul 2027 | about 11 Jun 2027 | **about 24 Apr 2027** |

**Hours available.** About 5 hours a week, the same every month, from 2026-11-16 until stage A1 is complete (decision 2). Ramadan does not change the owner's hours.

| Period | Hours | Cumulative |
|---|---|---|
| 16 to 30 Nov | 10.7 | 10.7 |
| December | 22.1 | 32.9 |
| 1 to 15 Jan | 10.7 | 43.6 |
| 16 to 31 Jan | 11.4 | 55.0 |
| February | 20.0 | 75.0 |
| March | 22.1 | 97.1 |
| 1 to 25 April | 17.9 | 115.0 |

**End date.** Stage A1 ends when C is complete; C is not reduced to finish by March (decision 1). C needs 114.3 h including the contingency: 22.9 weeks, about 24 April 2027. Its tasks alone, with the extra 4 h of analysis and checkpoints below, are 103.4 h, which would end about 9 April if none of the buffer were used. A missed week moves the end by a week.

**Does C's collection fit by 31 January?** Not entirely. Hours to 31 January: 55.0. Before that date: preparation 13 h, calibration labelling 2.1 h, thresholds, populations and the leak estimate 2.0 h, the guidelines checkpoint 1.0 h. That leaves 36.9 h for collection. At 660 listings in 42.6 h (15.5 listings an hour), **571 of the 660 listings (87 percent) fit; 89 are short, which is 5.7 h or 8 days**, so collection ends about 8 February. If the time assumptions are 15 percent worse: 497 listings by 31 January and an end of collection about 17 February.

C is 500 overlap listings and 160 extras. The two options for the shortfall were fewer listings (stop on 31 January with 571: all 500 overlap listings, so all the matches, and 71 of the 160 extras) or continuing into February. Decision 17 chose the second: collection ends with a hard stop on 8 February 2027, the day before Ramadan is expected to begin, so that no listing is collected during Ramadan. Sessions are ordered overlap first and extras last. If the pace measured at 15 January projects an end after 8 February, the extras are cut instead of extending the collection.

**Schedule for C at 5 hours a week.** Main labelling starts in February, after collection, because the sampler needs the whole universe and January has no spare hours. No labelling sessions in the week of Eid.

| Period | Hours | Work |
|---|---|---|
| 16 to 30 Nov | 10.7 | Scouting (3); permission requests (2); `docs/sources.md` gaps (1); title check (0.5); review of new tools (3); planning (1.2) |
| December | 22.1 | Rest of planning (1.3); batch 0, timed, and up to 50 of its pairs labelled as practice (1); collection, 19.8 h (about 310 listings with batch 0) |
| 1 to 15 Jan | 10.7 | Calibration sample labelled (2.1); thresholds, populations and the leak estimate (2); collection, 6.6 h (about 410 listings in all) |
| 16 to 31 Jan | 11.4 | Guidelines checkpoint and freeze (1); collection, 10.4 h (about 570 listings in all) |
| February | 20.0 | Collection to 8 February (5.7 h; the last 89 listings); sampler draws (1); main labelling (13.3) |
| March | 22.1 | Rest of labelling (0.4); overlap sample drawn (1); L2 labels; adjudication (2, before Eid); documents (18.7) |
| 1 to 25 April | 17.9 | Documents (6.3: dataset card, stage review, reproduction from a clean clone, last push and restore test); buffer 11.6 h |

The thresholds analysis, the checkpoint and the sampler draws (4 h) are not in the 99.4 h of tasks; they use part of the contingency. The real slack is the 11.6 h of buffer, about two weeks. The nested design means that what has been collected and labelled at any point remains a coherent dataset.

## 7. Risks and dependencies

| Risk or dependency | What to do |
|---|---|
| Written permission to publish listing text is unclear for both shops | Ask now. If it is refused, release pair IDs, labels and derived features, with a script that re-reads the pages, instead of the titles. The paper's scope depends on this |
| No Bangla-script titles; Chaldal needs written permission | Ask Chaldal; do not plan on it |
| Overlap smaller than hoped | The scouting gate (section 2); add a category only if needed |
| Catalogue and price changes over four months | Collect both sides in one session; never re-collect; labelling uses titles, not prices |
| Delivery location of meenabazar | Fixed and recorded before batch 1 |
| Ramadan (expected from 9 February 2027) and Eid al-Fitr (expected 10 March, or 11 March if the moon is not sighted on 9 March; Bangla Date Today, subject to moon sighting): the shops may change catalogues, prices and promotions. This is a risk to the data, not to the owner's hours | Collection ends by 8 February, the day before Ramadan is expected to begin; every listing carries its collection time in `collected_at`; if a listing is collected during Ramadan, say so in the dataset card |
| Hours: about 5 a week, the same every month (decision 2) | Keep a log of hours per week and compare it with the assumptions after batch 0; a missed week moves the end by a week |
| Collection does not finish by 31 January: 571 of 660 listings fit | Decision 17: overlap first, extras last, hard stop on 8 February; cut the extras if the pace at 15 January projects a later end |
| Time assumptions wrong; if 15 percent worse, only 497 listings fit by 31 January and collection would end about 17 February | Batch 0 measures them; cut the extras instead of collecting during Ramadan |
| Stage A1 ends about 24 April and stage A2 starts in April | A2's blocking and rule-based baseline need the listings and the candidate pairs, not the labels; evaluation waits for the labels (complete about the end of March) |
| Collector and labeller are the same person | Hidden strata, hash order, second labeller |
| Guidelines change while labelling | Checkpoint and freeze; recorded re-checks |
| Second labeller not found | Ask now; without L2 there is no agreement figure |
| Drive backup unverified | Run `dvc status -c` and a restore test each month |
| Sampling probabilities lost | The sampler records them with the seed |
| Selection bias from deliberate collection: the recorded sampling probabilities do not cover which listings were collected | The dataset card states that metrics describe pairs of collected listings, not the shops' catalogues |
| Matches outside the two census strata | The gate and the leak estimate of section 4 (recorded in the dataset card), the sensitivity of section 1, and the intended pairs (decision 16) |
| A wrong pilot title cannot be fixed today | Check the titles first; build the superseded-files list only if one is wrong (decision 6) |
| Pilot pairs seen with L9 labels, and batch 0 practice pairs, cannot be labelled independently | Do not label them for the dataset; exclude them from the universe (decision 15) |
| Seller schema change | Version 2 of the listing file with a cutover date; section 3 (decision 5) |

## 8. Decisions

Decided by the owner on 2026-11-14: decisions 1 to 9, 13, 15, 16 and 17. Decisions 10, 11, 12 and 14 are actions for the owner and stay open.

| # | Decision | Status |
|---|---|---|
| 1 | Target size | **Decided: plan C** (1,000 labelled pairs, 660 listings). Stage A1 ends when C is complete (about 24 April 2027), not in March. `CLAUDE.md` says "about 1,000 (plan C)" and gives the period as November 2026 to April 2027 |
| 2 | Weekly hours | **Decided: about 5 hours a week**, the same every month, until stage A1 is complete |
| 3 | Overlap-first collection | **Decided: yes** |
| 4 | Categories | **Decided: keep the four** |
| 5 | Seller column (schema version 2) | **Decided: yes**, before batch 1; cost in section 3 |
| 6 | The 22 pilot titles | **Decided:** check them first (about 30 minutes); build the superseded-files list only if a title is wrong; the simpler exclusion list if only a few are wrong and the owner accepts losing them |
| 7 | Sessions | **Decided: 30 listings per session**, with the extra overhead included in section 6 |
| 8 | Thresholds | **Decided:** from a calibration sample of about 150 pairs in the first half of January |
| 9 | Guidelines freeze | **Decided:** 2027-01-31, with the stratified overlap sample written into version 0.4 |
| 10 | Second labeller | Open (an action for the owner): choose and ask now |
| 11 | Permissions | Open (an action for the owner): send requests to both shops and to Chaldal this month; the messages can be drafted |
| 12 | meenabazar delivery location | Open (an action for the owner): recommended, a location in the same area as the pandamart store |
| 13 | Build before batch 1 | **Decided:** the sampler (take-all strata, pilot and practice pairs excluded, output read by the tool), the stratified overlap sample and the agreement figures (kappa, positive and negative agreement), the exclusion of L9, the yield report, and the seller schema |
| 14 | A helper for manual collection | Open (an action for the owner): optional; a second person following the same rules would cut the owner's collection hours and, at 5 hours a week, the end date |
| 15 | The 47 pilot pairs and the batch 0 practice pairs | **Decided:** exclude both sets of pairs from the dataset and from the sampling universe; keep the 22 pilot listings if verified; keep the practice labels in `data/practice/` as practice, excluded from every statistic |
| 16 | Label the intended pairs of the worklist with certainty | **Decided: yes**; the worklist is an ID-only file, `data/interim/intended_pairs.csv`, under DVC (not Git, not `local/`) |
| 17 | End of collection | **Decided:** a hard stop on 8 February 2027, the day before Ramadan is expected to begin, instead of 31 January; sessions ordered overlap first and extras last; cut the extras if the pace at 15 January projects a later end |
