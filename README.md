# Vacuula Setup Wizard (UI only initially)

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
NOTE! If you add strings (do it in english) increment strings version! I dont wanna be botherd figuring out which languages are outdated at runtime


## Placeholders:

- **`app/core/robot_detector.py`** — `RobotDetector` currently waits a
  fixed delay and then emits a fake model via `robotDetected(model_id,
  display_name)`. Replace `_simulate_detection` but keep signal(s).
- **`app/core/installer.py`** — `InstallerLauncher.launch(model_id)`
  currently just logs which script *would* (based on rng from robot 
  detector placeholder). Real scripts go into `_SCRIPTS` (paths per model)
  and replace the `TODO` with an actual (non-blocking) launch, e.g. `QProcess`.
- **`assets/wireframe_connect.svg`** — ai generated placeholder cause im lazy
its ugly and will be replaced with something more instructive.
