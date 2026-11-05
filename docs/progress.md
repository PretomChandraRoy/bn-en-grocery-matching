# Progress

## 2026-11-03

### Done

- Created the folder structure: `data/raw`, `data/interim`, `data/labelled`, `docs`, `src/collect`, `src/label`, `src/normalise`, `tests` and `notebooks`, each with a `.gitkeep` file.
- Created `docs/sources.md` and `docs/labelling_guidelines.md` as title-only placeholders.
- Created `.gitignore` covering `.venv/`, Python and tool caches, Jupyter checkpoints and `.env`.
- Created a Python 3.12.10 virtual environment in `.venv` and installed `pandas`, `dvc`, `pytest` and `ruff`. All four installed without errors, and `pip check` reported no broken requirements.
- Wrote `requirements.txt` (direct dependencies with minimum versions) and `requirements-lock.txt` (full `pip freeze` output, 104 packages).
- Ran `ruff check .`, which passed (there are no Python files yet). Ran `pytest`, which exited with code 5 because no tests exist yet.
- Initialised DVC (`dvc init`) and tracked `data/raw` (`dvc add data/raw`). `data/raw/.gitkeep` was first removed from the Git index (`git rm --cached`), because DVC refuses to track a path that Git already tracks. DVC now records the folder in `data/raw.dvc`, and `data/.gitignore` excludes `data/raw` from Git.
- Drafted and saved `CLAUDE.md` at the repository root, recording the project brief, stages, data design, repository layout, collection rules, working rules, verification steps and stage review requirements.
- Diagnosed why `dvc` was not found in new VS Code terminals. The `.venv` was complete (Python 3.12.10 with `dvc`, `pytest` and `ruff`), but VS Code had the parent folder open, not the repository folder, and no `.vscode` settings existed. The PowerShell execution policy is also likely to block `Activate.ps1` (see open questions).
- Added `.vscode/settings.json` (interpreter path and automatic activation) and listed `.vscode/` in `.gitignore`, because the interpreter path is Windows-specific. The settings file is therefore not committed.
- Wrote the Setup and Troubleshooting sections of `README.md`.
- Created the `docs/sources.md` template with sections for Chaldal, Shwapno, Daraz (grocery section) and foodpanda (grocery). All values are blank, to be completed by the project owner.

- Presented the pilot plan (about 200 listings, normalisation module, candidate pair generation, command-line labelling tool). The owner approved it and decided the matching rules: different pack sizes do not match, size must be exactly equal after conversion, unbranded loose staples match when variety, grade and size agree, and `unsure` is used only when the recorded fields cannot decide.
- Added `source_category` (the shop's own category label, optional) to the listing record in `CLAUDE.md`, and defined `category` as one of `rice`, `lentils`, `cooking_oil` and `spices`.

### Next

- Review the draft of `docs/labelling_guidelines.md`, written so that a second labeller can follow it without help.
- Add `pyproject.toml` (pytest and ruff settings), then build the normalisation steps in the agreed order, testing the NFC behaviour of য় on real strings first.
- Check each source's terms of use and robots.txt and complete `docs/sources.md` before any listings are copied. Enter the pilot listings in Google Sheets and export them as CSV (UTF-8).
- Propose the DVC remote setup (Google Drive) before the labelling tool is built.
- Confirm in a clean VS Code terminal, with the repository folder as the workspace, that the environment activates automatically.

### Open questions

- Confirm whether the PowerShell execution policy blocks `Activate.ps1` in a VS Code terminal. If it does, run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once.
- Confirm that the Python extension (`ms-python.python`) is installed in VS Code.
- DVC enables anonymous usage analytics by default. Decide whether to disable it with `dvc config core.analytics false`.
- Choose a DVC remote before the pilot collection in December 2026. Until then, versioned data exists only on the local machine, and a clean clone cannot run `dvc pull`.
- Generate a Linux-compatible lock file for CI (stage A3). The current `requirements-lock.txt` was generated on Windows and pins `pywin32`, which is required only on Windows and is unlikely to install on Linux.

## 2026-11-04

### Done

- Saved `docs/labelling_guidelines.md` as version 0.1. It defines the three labels, a precedence rule (any `non_match` outweighs `unsure`, which outweighs `match`), nine note tags (`unbranded`, `brand_missing`, `brand_differs`, `size_differs`, `variant_differs`, `multipack`, `unit_kind_differs`, `promo_quantity`, `cross_script`), worked examples, and the agreement and adjudication procedure for a second labeller. The version is on a line of the form `Version: 0.1`, which the labelling tool will read.
- Updated the data design in `CLAUDE.md`: `collected_at` is kept as local time with its UTC offset in `data/raw`, and the normalisation code writes `collected_at_utc` to `data/interim`. Added `guidelines_version` to the pair record, filled in automatically by the labelling tool. Added `docs/dataset_card_notes.md` to the repository layout.
- Created `docs/dataset_card_notes.md` with entries on the manual `script` annotation, the project-defined `category`, the hidden price during labelling, the sampling mix (incomplete), the guideline version and the dataset-specific scope of Cohen's kappa.
- Recorded the owner's summary of the source checks so far. The evidence for each source is to be entered in `docs/sources.md`, which is still blank. Shwapno and Daraz are excluded, because their terms prohibit automated collection and use of listing content. foodpanda is usable for manual collection from pandamart only, provided the listings can be viewed without logging in. Chaldal is pending, because the site was unavailable when checked. The pilot may therefore use only two sources (pandamart and possibly Chaldal). Pair generation must keep working for two or more sources.
- Entered the four source entries in `docs/sources.md` as supplied by the owner: Shwapno and Daraz (automated collection: no; redistribution: no), foodpanda (grocery) restricted to pandamart (both unclear) and Chaldal (incomplete, site unavailable on 2026-11-04). The entries were recorded verbatim and have not been independently checked. The link to the foodpanda terms was added afterwards.
- Changed the A1 stage description in `CLAUDE.md` from "three or more sources" to "two or more sources". Added the source-count limitation and the redistribution position (pandamart: unclear, treated as not permitted) to `docs/dataset_card_notes.md`.
- Created `pyproject.toml` with pytest settings (`src` importable from tests) and ruff settings (line length 100; style, error, import-order, docstring, type-hint and encoding rules; tests are exempt from docstring and type-hint rules only).
- Added the foodpanda terms link to `docs/sources.md` and pushed the commits so far.
- Step N1 (Unicode clean-up): added `src/normalise/unicode_clean.py` with `INVISIBLE_CHARACTERS` (eight code points), `remove_invisible` and `clean_unicode` (remove invisible characters, then NFC). Non-`str` input raises `TypeError`. Added `tests/normalise/test_unicode_clean.py`, including the case that ZWNJ between two vowel signs must not block composition. NFC was checked on invented strings: it turns য় (U+09DF), ড় (U+09DC) and ঢ় (U+09DD) into base letter plus nukta, composes ে + া into ো, and leaves zero-width characters and Bangla digits unchanged.
- Step N2 (digits): added `src/normalise/digits.py` with `bangla_digits_to_ascii`, which converts only the ten Bangla digits. Added `tests/normalise/test_digits.py`. Moved the string check into `src/normalise/checks.py` (`require_str`), which both `unicode_clean.py` and `digits.py` now use. Digit policy: regular expressions match digits with `[0-9]`, never `\d`, and never use `re.ASCII`; numbers become values only through `Decimal()` on text matched by `[0-9]`. Verified on invented strings that `\d`, `int()`, `float()` and `Decimal()` all accept Bangla digits and digits of other scripts.
- Added `src/normalise/patterns.py`, which defines the word-character class `WORD_CHARS` once (Latin letters and digits plus U+0980 to U+09F1, U+09FC and U+09FE), the lookarounds `BOUNDARY_BEFORE` and `BOUNDARY_AFTER`, and `bounded()`. Added `tests/normalise/test_patterns.py`, which checks that every assigned Bangla character in the class is a letter, mark or digit.
- Added `tests/test_source_policy.py`, which parses every file under `src/` and flags `\d`, `\D`, `\w`, `\W`, `\b`, `\B`, the backspace character, `(?a` and `re.ASCII` in string literals and code, while ignoring comments and docstrings. Checked on a scratch copy that it fails when violations are added. Added the matching regular-expression rule to the working rules in `CLAUDE.md`.
- Adopted `ruff format` as a project rule: `CLAUDE.md` now says code is formatted with it, and `ruff format --check` joins `pytest` and `ruff check` in the checks after every step. Running it on the whole codebase changed one line in one test file.
- Found that the file-writing tool turns a single Unicode escape sequence (a backslash, `u` and four hex digits) into the literal character. The source and test files written so far therefore held literal Bangla and invisible characters, although their comments said they were escapes. Rewrote every non-ASCII character in non-docstring string literals as an escape, using a one-off script that proved the parse tree identical before and after, so no string value changed. New tests build Bangla text from code points through `tests/helpers.py`. Saved the quirk to private memory.
- Step N3 (size parsing): added `src/normalise/units.py` (the single unit table, with `lookup_unit` and `unit_alternation`), `src/normalise/sizes.py` (`parse_size` and `SizeResult`), `tests/helpers.py`, `tests/normalise/test_units.py` and `tests/normalise/test_sizes.py`. Results carry a status (ok, missing, ambiguous, conflict), a reason whenever the status is not ok, the per-pack amount in grams or millilitres, the pack count, the source, a free-extra flag and the exact matched text. Fractions are flagged, not parsed. Nine deliberate bugs were applied to scratch copies to check that the tests catch them; the one that was missed (the slash in the left-context rule) led to three new tests, after which all were caught.
- Extended `tests/test_source_policy.py`. It now also flags any non-ASCII character written literally in a string literal (checked on the source text, in `src/` and `tests/`; docstrings and comments are free) and requires a comment in readable Bangla beside every escaped Bangla literal and every `bn(...)` call that builds Bangla. Added the matching rule to `CLAUDE.md`. The comments were added by a one-off script that decodes each literal, with the parse trees checked identical. `ruff format` can move a comment away from its literal when it reflows a list, and the guard catches that.
- Pinned in a test the behaviour of a unit followed directly by a non-ASCII Latin letter (for example `1 kg` plus e-acute is read as 1 kg), with a comment explaining it.
- Updated the foodpanda (pandamart) entry in `docs/sources.md` after the owner's check on 2026-11-05: listings are viewable without logging in; collect only from the Gulshan-Banani pandamart store with the site language set to EN; the product page URL form does not match a disallowed robots.txt path; the numeric product ID is the `listing_id`. Titles are in Latin script (English plus romanised Bangla variety names such as "Miniket"), and no Bangla-script titles have been seen. There are no separate brand or size fields, so brand and size come from the title only.
- Step N4 (text clean-up): added `src/normalise/text_clean.py` (`clean_text`) and `tests/normalise/test_text_clean.py`. The steps are lower case, times sign or asterisk between digits to `x`, thousands comma removal, joining the dots inside dotted Bangla unit abbreviations, apostrophe removal, keeping only letters, marks and numbers (everything else, including every Unicode space, becomes a space; a decimal point between digits is kept), spacing around `x` between digits, and a space between a number and a unit. Two earlier orderings were not idempotent on 78 and 37 of 20,000 random strings; the final order, with deletions first and spacing last, gave 0 of 100,000, and the tests include the same random check. A deliberate-bug check showed the planned first step (convert Unicode spaces to a normal space) was redundant, because the later step already turns every non-letter, non-mark, non-number into a space; it was removed.
- Saved the preference that the owner makes all git commits to private memory. Claude previously ran `git commit` and `git push` on the owner's request (commits 900a540, 32f8f11 and 4288950) and will now only suggest commit messages.

### Next

- Normalisation steps still to do, in this order (N1 Unicode clean-up, N2 digits, N3 size parsing and N4 text clean-up are done): N5 promotional words. Each step is planned and approved before it is written. Missing values (None, NaN) are handled by the later DataFrame step, because the string functions accept `str` only.
- Word boundaries in N3 to N5 are detected with `WORD_CHARS` and the lookarounds in `src/normalise/patterns.py`, never with `\b` or `\w`, because Python does not treat Bangla vowel signs as word characters. `tests/test_source_policy.py` enforces this.
- The interim run reports counts by size status and by reason, how many titles contain the currency fraction signs U+09F4 to U+09F9, and the most frequent words that follow a number but are not in the unit table, so that the pilot shows what the table is missing.
- Build the normalisation steps in the agreed order, testing the NFC behaviour of য় on real strings first.
- Show the exact layout of the labelled data (one row per pair and labeller, plus an adjudication file, with re-checked labels kept as earlier rows) before the labelling tool is built.
- Check the current DVC documentation and propose the Google Drive remote setup, with sources, before the labelling tool is built.
- Re-check Chaldal (terms, robots.txt, availability) once the site is available. Check that pandamart listings are viewable without logging in. No listings are collected until the owner has confirmed both conditions recorded for foodpanda in `docs/sources.md`.

### Open questions

- Confirm in a clean VS Code terminal, with the repository folder as the workspace, that the environment activates automatically. Confirm that the Python extension is installed, and whether the PowerShell execution policy blocks `Activate.ps1`.
- Set up the DVC remote (Google Drive) before labelling starts. Credentials must never be committed; keep them in `.dvc/config.local` or outside the repository.
- Generate a Linux-compatible lock file for CI (stage A3).
- Record the final sampling mix and its rationale in `docs/dataset_card_notes.md` once pair generation is built.
- Find a third usable source. This does not block the pilot: two sources are accepted for A1 if Chaldal proves usable, with the limitation stated in `docs/dataset_card_notes.md`.
- Only one source (pandamart) is usable at present, so no cross-shop pairs can be built from real data until Chaldal or another source is cleared. Pair generation and the labelling tool are developed and tested on invented data in the meantime.
- Obtain written permission, or decide what the public dataset may contain, given that redistribution of pandamart listing text is treated as not permitted.
- Check the Bangla unit spellings in `src/normalise/units.py` against real listings during collection, and add any that are missing to the table. The owner will do this.
- Review with pilot data: a fraction in the title makes the size ambiguous even when the size field is clear. This was accepted for the pilot.
- Review with pilot data: accented Latin letters count as separators in word boundaries (see the pinned test for `1 kg` followed by an accented letter).
- Approve the wording of the four `script` values (english, romanised, bangla, mixed), then save it in the entry rules and in `docs/labelling_guidelines.md`. The owner will decide where the sheet entry rules are kept.
- pandamart titles are Latin script only so far, so the planned cross-script stratum of about 15 percent of the sampled pairs cannot be filled from pandamart alone. It needs Chaldal or another source with Bangla-script titles.
