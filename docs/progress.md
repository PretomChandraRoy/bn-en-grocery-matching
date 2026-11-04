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
- Entered the four source entries in `docs/sources.md` as supplied by the owner: Shwapno and Daraz (automated collection: no; redistribution: no), foodpanda (grocery) restricted to pandamart (both unclear) and Chaldal (incomplete, site unavailable on 2026-11-04). The entries were recorded verbatim and have not been independently checked.
- Changed the A1 stage description in `CLAUDE.md` from "three or more sources" to "two or more sources". Added the source-count limitation and the redistribution position (pandamart: unclear, treated as not permitted) to `docs/dataset_card_notes.md`.
- Created `pyproject.toml` with pytest settings (`src` importable from tests) and ruff settings (line length 100; style, error, import-order, docstring, type-hint and encoding rules; tests are exempt from docstring and type-hint rules only).

### Next

- Approve the plan for the first normalisation step (Unicode NFC), after the check of how NFC treats য় on invented strings.
- Build the normalisation steps in the agreed order, testing the NFC behaviour of য় on real strings first.
- Show the exact layout of the labelled data (one row per pair and labeller, plus an adjudication file, with re-checked labels kept as earlier rows) before the labelling tool is built.
- Check the current DVC documentation and propose the Google Drive remote setup, with sources, before the labelling tool is built.
- Re-check Chaldal (terms, robots.txt, availability) once the site is available. Check that pandamart listings are viewable without logging in. No listings are collected until the owner has confirmed both conditions recorded for foodpanda in `docs/sources.md`.

### Open questions

- Confirm in a clean VS Code terminal, with the repository folder as the workspace, that the environment activates automatically. Confirm that the Python extension is installed, and whether the PowerShell execution policy blocks `Activate.ps1`.
- DVC enables anonymous usage analytics by default. Decide whether to disable it with `dvc config core.analytics false`.
- Set up the DVC remote (Google Drive) before labelling starts. Credentials must never be committed; keep them in `.dvc/config.local` or outside the repository.
- Generate a Linux-compatible lock file for CI (stage A3).
- Record the final sampling mix and its rationale in `docs/dataset_card_notes.md` once pair generation is built.
- Find a third usable source. This does not block the pilot: two sources are accepted for A1 if Chaldal proves usable, with the limitation stated in `docs/dataset_card_notes.md`.
- Only one source (pandamart) is usable at present, so no cross-shop pairs can be built from real data until Chaldal or another source is cleared. Pair generation and the labelling tool are developed and tested on invented data in the meantime.
- Obtain written permission, or decide what the public dataset may contain, given that redistribution of pandamart listing text is treated as not permitted.
