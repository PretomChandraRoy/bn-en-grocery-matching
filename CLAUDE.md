# CLAUDE.md

## Project

bn-en-grocery-matching is an entity resolution system that decides whether two grocery product listings from different Bangladeshi online shops refer to the same product. The plan is to deploy it as a production machine learning system and to publish the labelled dataset with a peer-reviewed paper.

The problem is hard for these reasons:

- Listings mix Bangla script, romanised Bangla and English. The same rice may appear as "Chinigura Rice", "Chinigura Chal" or "চিনিগুড়া চাল".
- Pack sizes and units vary: "1 kg", "1000 gm", "১ কেজি", "500ml", "0.5 L".
- Brand names are spelt inconsistently or are missing, and titles contain promotional words such as "Combo" or "Offer".
- Text contains Bangla digits (০ to ৯), inconsistent Unicode normalisation and zero-width characters.

## Stages

| Stage | Period | Scope |
|---|---|---|
| A1 Data (CURRENT) | Nov 2026 to Mar 2027 | Collect listings from two or more sources, label about 2,000 candidate pairs, write a dataset card |
| A2 Models | Apr to Jun 2027 | Blocking, rule-based baseline, learned similarity (gradient boosting on string features, then multilingual sentence embeddings), evaluation with precision, recall, F1 and pair completeness, error analysis by script |
| A3 Production | Jul to Sep 2027 | FastAPI and Docker serving, MLflow model registry, GitHub Actions CI/CD, Prometheus and Grafana monitoring, Evidently drift detection, drift-triggered retraining, canary rollout |
| A4 Paper | Aug to Oct 2027 | Dataset or resource paper |

Build nothing for A2 to A4 yet, but keep every design choice compatible with them.

## Data design

Listing record (one row per listing):

- `source`: short source name, for example "chaldal"
- `listing_id`: the source's own identifier
- `title_raw`: exactly as displayed; never modified after collection
- `brand`, `size_value`, `size_unit`: may be empty
- `price_bdt`
- `category`: one of the four project categories: `rice`, `lentils`, `cooking_oil`, `spices`
- `source_category`: the shop's own category label; optional, may be empty
- `script`: one of `bangla`, `romanised`, `english`, `mixed`; entered by hand, as defined in `docs/data_entry_rules.md`
- `url`
- `collected_at`: ISO 8601 timestamp in local time with its UTC offset, as recorded at collection (for example `2026-11-03T15:30:00+06:00`). The normalisation code converts it to UTC and writes it to `data/interim` as `collected_at_utc`.

Pair record (one row per labelled pair):

- `pair_id`, `left_source`, `left_id`, `right_source`, `right_id` (each `*_id` is a `listing_id` within its source)
- `label`: one of `match`, `non_match`, `unsure`
- `note`, `labeller`, `labelled_at`
- `guidelines_version`: the version of `docs/labelling_guidelines.md` in force when the label was made (for example "0.1"). The labelling tool fills it in automatically from the `Version:` line of that file, so that line must keep its format.

Labels follow the rules in `docs/labelling_guidelines.md`.

Data layout:

- `data/raw`: collected data, never edited after collection
- `data/interim`: cleaned and normalised data. Normalised fields such as `title_norm` and `collected_at_utc` are produced by the normalisation code and are never written into `data/raw`.
- `data/labelled`: labelled pairs

All data is versioned with DVC and never committed to Git directly. DVC tracks `data/raw` through `data/raw.dvc`.

## Repository layout

- `src/collect`: collection code, including the validator for collected files (`validate.py`)
- `src/normalise`: normalisation code
- `src/label`: pair generation and the labelling tool
- `tests`: pytest tests, mirroring the structure of `src`
- `notebooks`: exploration only; no logic that other code depends on
- `local/`: real collected data for local checks only; ignored by Git and never committed
- `docs`: sources, data entry rules, labelling guidelines, dataset card notes, progress and reviews

## Rules for collecting data (strict)

- Do not collect from any source automatically until `docs/sources.md` records that its terms of use and robots.txt allow it. If permission is unclear, stop and tell the user, who will then collect manually or choose another source.
- Collect only public product information. No personal data, no logging in and no bypassing of access controls.
- Be polite to servers: at most one request every few seconds, a generic client name in the User-Agent, and cached responses so that no page is fetched twice.
- Record in `docs/sources.md` whether each source's listing text may be redistributed. This decides what the public dataset can contain.

## Working rules

- At the start of every session, read `docs/progress.md` for the current status and open questions.
- Plan before acting: for every task, show the plan and wait for approval before creating or changing files.
- Work in small, reviewable steps, one logical change at a time.
- Never run git commit or git push. The user makes all commits. When a step is finished, suggest a commit message.
- Never commit data files; use DVC.
- Files enter `data/raw` only through `python -m src.collect.validate --accept FILE` (see `docs/data_entry_rules.md`). Real collected data for local checks lives in `local/`, which Git ignores. Real titles must never be committed anywhere in the repository, including tests and documentation. `tests/test_data_safety.py` fails if Git tracks anything under `local/` or `data/raw`.
- Use Python 3.12 with the virtual environment in `.venv`. `requirements.txt` lists the direct dependencies with minimum versions; `requirements-lock.txt` holds the full `pip freeze` output.
- Always read and write text files with encoding='utf-8' explicitly, including CSV files and pandas I/O. Never rely on the platform default encoding, because on Windows it can corrupt Bangla text.
- In regular expressions, match digits with `[0-9]`, never `\d`. Never use `re.ASCII` or `(?a`. Never use `\w` or `\b`, because Python does not treat Bangla vowel signs as word characters. For word boundaries use the project's word-character class (`A-Za-z0-9` plus U+0980 to U+09F1, U+09FC and U+09FE) with lookarounds; it is defined once, as `WORD_CHARS` in `src/normalise/patterns.py`, and every step imports it. Convert numbers to values only with `Decimal` on text already matched by `[0-9]`. `tests/test_source_policy.py` enforces these regular-expression rules for `src/`.
- Never write a non-ASCII character literally in a string literal in code, test data included; write it as an escape (a backslash, `u` and four hex digits), or in tests build the text from code points with `bn(...)` from `tests/helpers.py`. Docstrings and comments may contain visible Bangla. Every escaped Bangla string literal, and every `bn(...)` call with constant arguments that builds Bangla, must have a comment on the same line that shows the text in readable Bangla, so that it can be reviewed. After writing or formatting a file, run the tests: Claude's file-writing tool turns a single escape sequence into the literal character, and `ruff format` can move a comment away from its literal. `tests/test_source_policy.py` enforces both rules for `src/` and `tests/`.
- Use type hints and docstrings, write pytest tests for all normalisation and parsing code, and lint with ruff.
- Code is formatted with `ruff format`.
- Prefer clear code over clever code, explain design decisions briefly, and explain any tool or technique that may be unfamiliar when it is introduced.
- Write documentation in British English, in clean formal prose, without emojis.
- Do not invent facts about sources, libraries or results. If something cannot be verified, say so.
- If anything in this file conflicts with what is found in the repository, or looks wrong, tell the user rather than guessing.
- At the end of every working session, add a dated entry to `docs/progress.md` covering what was done, what comes next and any open questions.

## Verification

After every step:

- Run `pytest`, `ruff check` and `ruff format --check` and report the results. A step is not finished until all three pass.
- Never delete, skip or weaken a test to make it pass. Find and fix the cause, or tell the user if the test itself appears to be wrong.
- Run new code on a small real sample (for example, a handful of listings) and show the output.
- State briefly what was checked and anything that could not be checked.

## Stage reviews

At the end of each stage, before it is marked complete, carry out a full review and write it to `docs/reviews/<stage>.md` (for example `docs/reviews/A1.md`). The review covers:

- Correctness: re-read all code written during the stage and look for bugs, unhandled edge cases (empty fields, mixed scripts, unusual units, malformed rows) and silent failures.
- Tests: list what is covered and what is not, and propose tests for important untested behaviour.
- Data integrity: confirm `data/raw` has not been modified, row counts and schemas match expectations, and there are no duplicates. From A2 onwards, also confirm there is no leakage between training and evaluation data.
- Reproducibility: set up the environment from a clean clone by following the README, reproduce the stage's outputs, and record the exact commands.
- Rule compliance: confirm all collection followed `docs/sources.md`, and that no data files, credentials or secrets are tracked by Git.
- Documentation: confirm `README.md`, `CLAUDE.md` and the `docs` folder are up to date.
- Honest results (from A2 onwards): every reported number must come from a script that can be rerun and must be stated exactly as produced, with no selective reporting.

List every issue as must-fix or nice-to-have. Fix must-fix issues only after the user approves, then rerun all checks and update the review file.

From stage A3 onwards, tests and linting must also run automatically in GitHub Actions on every push.
