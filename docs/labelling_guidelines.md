# Labelling Guidelines

Version: 0.3

Pilot draft, 2026-11-05.

## Purpose

This project decides whether two grocery product listings from different Bangladeshi online shops refer to the same product. Your task is to look at one pair of listings at a time and record whether they are the same item. Your labels are the reference answers ("ground truth") used both to train the matching system and to test it, so consistency matters more than speed.

## What you are deciding

Two listings are a match when a customer could buy either one and receive the same item: the same product, from the same brand (or from no brand at all), in the same variant and in the same pack size. Every pair comes from two different shops.

## What you may use

For each listing you are shown the title exactly as the shop displays it, the brand, the size, the source (the shop) and the category. Decide only from these.

- Do not open the product page, look at photographs or search the web.
- The price is hidden on purpose, so that a similar price does not influence your decision.
- The brand and size fields may be empty. If either is missing from its field but stated in the title, use the title.

## The three labels

- `match`: the listings are the same item under the definition above.
- `non_match`: the listings are different items.
- `unsure`: use only when the information shown genuinely cannot settle the question. Do not use it because a pair is difficult or because a rule feels strict. Unsure pairs are published with the dataset, so a careful use of this label is valuable.

## Deciding step by step

Check every step below, even after one of them has given a result. Each step gives `non_match`, `unsure` or no difference. Then decide the label by this rule:

1. If any step gives `non_match`, the label is `non_match`.
2. Otherwise, if any step gives `unsure`, the label is `unsure`.
3. Otherwise, the label is `match`.

Add every tag that applies (see "Tags"), whichever label results.

1. **Size.** Convert both sizes to grams (g) or millilitres (ml): 1 kg is 1000 g, and 1 L is 1000 ml. Bangla digits and Bangla unit words mean the same as their English counterparts (১ কেজি is 1 kg). Sizes must be exactly equal after conversion.
   - Different sizes: `non_match`.
   - One size is a weight and the other a volume (for example 1 L against 1 kg): `non_match`. Do not convert between them.
   - A size is missing from both its field and the title, or the field and the title disagree: `unsure`.
   - If a title announces a free extra quantity (for example "500 gm + 50 gm free"), use the base size (500 gm) and ignore the free extra. If the size field shows the combined total, use the base size from the title. This is not a disagreement between field and title.
2. **Packs.** A multipack (for example "2 x 500 gm") is a different item from a single larger pack of the same total ("1 kg"): `non_match`. Two identical multipacks can match. Bundles of different products are not part of the pilot. If you meet one, skip it and tell the project owner.
3. **Variant.** Variety, grade and type are part of the product. If they differ, the pair is a `non_match`. If you cannot tell whether a word names a variant or only advertises, use `unsure`. Two kinds of word have rules of their own, and the same rule applies to both:
   - **Brand line.** A brand line is a word after the brand that names a range of that brand and is not a variety, grade or product word. In "Brand X Gold Rice" and "Brand X Classic Rice", Gold and Classic are lines of Brand X. A line is part of the product. Different lines: `non_match`. The same line, in any position or spelling: no difference. A line in one title only: `unsure`, because the shorter title may only have dropped it. No line in either title: no difference. If you cannot tell whether a word is a line or only a description, use `unsure`.
   - **Origin.** An origin word says where a product comes from: Deshi (local), Imported, or the name of a country. A title without an origin word may be the product of either origin, and a deshi product is often a different product from the imported kind. Different origins, such as Deshi against Imported: `non_match`. The same origin in both titles: no difference. An origin word in one title only: `unsure`. No origin word in either title: no difference.
4. **Brand.**
   - Both give a brand and the brands differ: `non_match`.
   - Both give the same brand: no difference. Different spellings or scripts of one brand name count as the same brand when you are confident.
   - Exactly one gives a brand: `unsure`.
   - Neither gives a brand: no difference.

Unbranded loose staples (for example loose rice, lentils or spices) match when variety, grade and size all agree.

## Things that do not change the product

- Promotional words such as "offer" or "discount". (A title that says "combo" may be a multipack or a bundle of different products: see step 2.)
- Container type (pouch, bottle, jar), unless it changes the size.
- Spelling, script or digit style: "Chinigura Rice", "Chinigura Chal" and "চিনিগুড়া চাল" name the same variety.

## Tags

Every label may carry tags describing the pair. Write them in the note field, lower case, separated by semicolons with no spaces, for example `unbranded;cross_script`. You may add a free-text comment after ` # `. Leave the note empty if no tag applies. Add every tag that applies, even when an earlier step has already decided the label.

| Tag | Add it when |
|---|---|
| `unbranded` | Neither listing gives a brand |
| `brand_missing` | Exactly one listing gives a brand |
| `brand_differs` | Both listings give a brand and the brands differ |
| `size_differs` | The sizes differ after conversion |
| `variant_differs` | The variety, grade, type, brand line or origin differs |
| `multipack` | Either listing is a multipack |
| `unit_kind_differs` | One size is a weight and the other a volume |
| `promo_quantity` | Either title announces a free extra quantity |
| `cross_script` | Exactly one of the two titles contains Bangla letters. The labelling tool adds this tag automatically, from the text of the titles. The digits ০ to ৯ do not count as Bangla letters. |

## Worked examples

The titles below are invented for illustration. They are not real listings.

| Left | Right | Label | Tags |
|---|---|---|---|
| Chinigura Rice 1 kg (no brand) | চিনিগুড়া চাল ১ কেজি (no brand) | `match` | `unbranded;cross_script` |
| Chinigura Rice 1 kg (no brand) | Chinigura Chal 5 kg (no brand) | `non_match` | `unbranded;size_differs` |
| Brand X Soybean Oil 1 L | Brand X Soyabean Oil 1000 ml | `match` | |
| Brand X Soybean Oil 1 L | Brand Y Soybean Oil 1 L | `non_match` | `brand_differs` |
| Brand X Soybean Oil 1 L | Soybean Oil 1 L (no brand) | `unsure` | `brand_missing` |
| Brand X Soybean Oil 1 L | Brand X Soybean Oil 1 kg | `non_match` | `unit_kind_differs` |
| Masoor Dal 500 gm (no brand) | Moog Dal 500 gm (no brand) | `non_match` | `unbranded;variant_differs` |
| Brand X Turmeric Powder 2 x 100 gm | Brand X Turmeric Powder 200 gm | `non_match` | `multipack` |
| Brand X Chilli Powder 100 gm Offer | Brand X Chilli Powder 100 gm | `match` | |
| Brand X Chilli Powder 500 gm + 50 gm Free | Brand X Chilli Powder 500 gm | `match` | `promo_quantity` |
| Brand X Gold Basmati Rice 1 kg | Brand X Classic Basmati Rice 1 kg | `non_match` | `variant_differs` |
| Brand X Gold Basmati Rice 1 kg | Brand X Basmati Rice Gold 1 kg | `match` | |
| Brand X Gold Basmati Rice 1 kg | Brand X Basmati Rice 1 kg | `unsure` | |
| Brand X Deshi Basmati Rice 1 kg | Brand X Basmati Rice 1 kg | `unsure` | |
| Brand X Deshi Basmati Rice 1 kg | Brand X Imported Basmati Rice 1 kg | `non_match` | `variant_differs` |
| Brand X Soybean Oil (no size shown) | Brand Y Soybean Oil 1 L | `non_match` | `brand_differs` |

In the last example, the missing size gives `unsure` (step 1) and the different brands give `non_match` (step 4). Because any `non_match` outweighs `unsure`, the label is `non_match`. The size is unknown, so `size_differs` is not added.

## The script field

Each listing also carries a `script` value that was entered by hand when the listing was collected. Labellers do not enter or change it. It is separate from the `cross_script` tag, which the labelling tool works out from the text of the two titles (Bangla letters in one title and not in the other).

When the value was entered, the title was judged as displayed, ignoring digits, punctuation, spaces and unit abbreviations such as kg, gm, ml and ltr:

- `english`: Latin script; English words and product, brand or variety names only.
- `romanised`: Latin script that contains at least one generic Bangla word written in Latin letters, for example chal, dal, tel, morich, holud or moshla.
- `bangla`: Bangla script only.
- `mixed`: both scripts in the same title, including a Latin brand name in a Bangla-script title.

Brand names and variety names are ignored when choosing between `english` and `romanised`, even when they are Bangla words (for example Radhuni, Miniket, Nazirshail or Chinigura). The full entry rules are in `docs/data_entry_rules.md`.

## Agreement and adjudication

To measure how reliable the labels are, a second labeller labels an overlap sample independently.

1. **Overlap sample.** The project owner draws about 150 pairs at random from the labelled pairs, using a fixed random seed. The second labeller labels them without seeing the first labeller's labels.
2. **Agreement.** Before any discussion, Cohen's kappa and the percentage of identical labels are computed from the two independent sets of labels, using all three labels (`match`, `non_match` and `unsure`). A script kept in the repository does the computation, so the figures can be reproduced.
3. **Adjudication.** Only after the agreement figures are recorded do the two labellers go through each disagreeing pair together and agree a final label. A short reason, one sentence, is recorded for each.
4. **Published labels.** The final dataset uses the adjudicated label and also publishes both original labels for every pair in the overlap sample.
5. **Guidelines.** If a disagreement shows that a rule is missing or unclear, or if a rule is added or changed for any other reason, the project owner updates these guidelines, increases the version number and records the change in the version history. Earlier labels affected by the change are re-checked under the new version, and the re-check is recorded: the version history states which rule changed, how many labels were re-checked and how many of them changed, and each changed label keeps its earlier version on record.

## Working practices

- Label independently. If you are a second labeller, do not look at another labeller's labels or discuss specific pairs until you have both finished.
- If these guidelines do not cover a case, label it `unsure`, describe the case in a comment and tell the project owner. Do not invent your own rule, and do not change how you apply a rule part-way through.
- Always read the version number at the top before a session. Changes to these guidelines are listed below.

## Version history

- 0.1 (2026-11-04): pilot draft.
- 0.2 (2026-11-05): defined the four values of the script field; no change to the labelling rules.
- 0.3 (2026-11-13): added to step 3 the treatment of brand lines and of origin words such as Deshi, with worked examples, and extended the description of the tag `variant_differs`; no other rule changed. No label of the dataset existed when it was made.
