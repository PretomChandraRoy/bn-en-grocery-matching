# bn-en-grocery-matching

## Setup (Windows PowerShell)

These steps assume Python 3.12 is installed (check with `py -3.12 --version`).

```powershell
git clone https://github.com/PretomChandraRoy/bn-en-grocery-matching.git
cd bn-en-grocery-matching
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
dvc --version
pytest
```

`requirements.txt` lists the direct dependencies. `requirements-lock.txt` pins the exact versions used in development. `pytest` runs the test suite; a few tests are skipped on a fresh clone because they need data that is not in Git (see "Getting the data").

In VS Code, run "Python: Select Interpreter" from the Command Palette and choose the `.venv` interpreter, so that new terminals activate the environment automatically.

### Troubleshooting

- If PowerShell reports that running scripts is disabled on this system, run this once to allow locally created scripts for your user account: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
- If `dvc` or `pytest` is "not recognised", the environment is not active. Check that the terminal is in the repository folder, then run `.venv\Scripts\Activate.ps1`.

## Getting the data

The collected data is not in Git. DVC tracks it, and the copy is kept in a private folder that only the project owner and invited labellers can open. The real listing text may not be republished, so the data is not public. Ask the project owner for access to the folder.

Each computer tells DVC where its copy of that folder is. The setting goes in `.dvc/config.local`, which Git ignores, because the path differs from one computer to another. For a folder in Google Drive for desktop, run this once with the path of your own synced folder, using forward slashes and quotation marks:

```powershell
dvc remote add --local --default storage "G:/My Drive/<folder name>"
dvc pull
dvc status -c
```

`dvc status -c` should report "Cache and remote 'storage' are in sync." If the drive letter or the folder changes, point DVC at the new path with `dvc remote modify --local storage url "<new path>"`. Never put a path or a credential in `.dvc/config`, which Git tracks.
