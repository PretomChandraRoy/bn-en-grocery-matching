# Progress

## 2026-11-03

### Done

- Created the folder structure: `data/raw`, `data/interim`, `data/labelled`, `docs`, `src/collect`, `src/label`, `src/normalise`, `tests` and `notebooks`, each with a `.gitkeep` file.
- Created `docs/sources.md` and `docs/labelling_guidelines.md` as title-only placeholders.
- Created `.gitignore` covering `.venv/`, Python and tool caches, Jupyter checkpoints and `.env`.
- Created a Python 3.12.10 virtual environment in `.venv` and installed `pandas`, `dvc`, `pytest` and `ruff`. All four installed without errors, and `pip check` reported no broken requirements.
- Wrote `requirements.txt` (direct dependencies with minimum versions) and `requirements-lock.txt` (full `pip freeze` output, 104 packages).
- Ran `ruff check .`, which passed (there are no Python files yet). Ran `pytest`, which exited with code 5 because no tests exist yet.

### Next

- Initialise DVC (`dvc init`) and track `data/raw` (`dvc add data/raw`).
- Draft `CLAUDE.md` for review.
- Write the `docs/sources.md` template and the pilot plan.

### Open questions

- Choose a DVC remote before the pilot collection in December 2026. Until then, versioned data exists only on the local machine, and a clean clone cannot run `dvc pull`.
- Generate a Linux-compatible lock file for CI (stage A3). The current `requirements-lock.txt` was generated on Windows and pins `pywin32`, which is required only on Windows and is unlikely to install on Linux.
