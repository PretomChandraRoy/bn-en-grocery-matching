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

### Next

- Confirm that new VS Code terminals activate the environment (`Get-Command dvc`, `dvc status`, `pytest`, `ruff check`).
- Complete `docs/sources.md` for each source. No automated collection may start until a source is recorded as allowed.
- Review the pilot plan (task 5) and answer its open questions about what counts as a match.

### Open questions

- Confirm whether the PowerShell execution policy blocks `Activate.ps1` in a VS Code terminal. If it does, run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once.
- Confirm that the Python extension (`ms-python.python`) is installed in VS Code.
- DVC enables anonymous usage analytics by default. Decide whether to disable it with `dvc config core.analytics false`.
- Choose a DVC remote before the pilot collection in December 2026. Until then, versioned data exists only on the local machine, and a clean clone cannot run `dvc pull`.
- Generate a Linux-compatible lock file for CI (stage A3). The current `requirements-lock.txt` was generated on Windows and pins `pywin32`, which is required only on Windows and is unlikely to install on Linux.
