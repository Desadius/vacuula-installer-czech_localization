# Vacuula Setup Wizard (No install scripts present yet)

Goals for this is to:
1. Look good
2. Unify installation for all supported neatos
3. Work on mac, windows, any resonable linux distro
4. Easy localisation
5. Be as much of "one click install" mantra as possible

Goals are NOT:
1. Server install walk-trough

I have actually not tried but I assume one can "compile" this to a executable so people dont have to learn making venvs

## Run it as dev

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Adding a language

1. Copy `locales/en.json` to `locales/<code>.json` and translate the values.
2. Add one line to `LANGUAGES` in `app/constants.py`:
   ```python
   "fr": LanguageMeta(flag="🇫🇷", native_name="Français"),
   ```
NOTE! If you add or update strings increment strings version in the updated file(s)!!

NOTE! The locale.json with the higest "String-version" is technically the translation to translate from, but lets keep it to en.json.


## Placeholders:
- **`app/core/installer.py`** — `InstallerLauncher.launch(model_id)`
  currently just logs which script *would* (based on rng from robot 
  detector placeholder). Real scripts go into `_SCRIPTS` (paths per model)
  and replace the `TODO` with an actual (non-blocking) launch, e.g. `QProcess`.
- **`app/core/installer.py`** — ServerDetector.serverDetected.emit()
  is just emmiting a hardcoded placeholder after fake delay. It is to be
  replaced with MTP call and detection, and server fetch. THis `TODO` is next 
  on the list.
