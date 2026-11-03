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

`requirements.txt` lists the direct dependencies. `requirements-lock.txt` pins the exact versions used in development. Until tests are added, `pytest` reports "no tests ran" and exits with code 5.

In VS Code, run "Python: Select Interpreter" from the Command Palette and choose the `.venv` interpreter, so that new terminals activate the environment automatically.

### Troubleshooting

- If PowerShell reports that running scripts is disabled on this system, run this once to allow locally created scripts for your user account: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
- If `dvc` or `pytest` is "not recognised", the environment is not active. Check that the terminal is in the repository folder, then run `.venv\Scripts\Activate.ps1`.
