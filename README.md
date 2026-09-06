# Vacuula Setup Wizard (No install scripts present yet)

Goals for this is to:
1. Look good
2. Unify installation for all supported neatos
3. Work on mac, windows, any resonable linux distro
4. Easy localisation
5. Be as much of "one click install" mantra as possible aka. KISS

Goals are NOT:
1. Server install walk-trough

For release it will be compiled, which would be nice to set up as github actions. For linux prob as appimage?
Have not decided on compiler, if you have experience with one lets use it!

## Current TODO:s in order of priority

1. Add logic (using serial) to separate out gen2 from gen3
2. Add actual installing scripts (they are to be called from installer.py in core). Everything the script needs should be in the session Class instance that main_window can pass it when start-install is requested..
3. Improve WiFi UX, using robots original procedure if computer running this app has wifi/bluetooth (show wifi networks robot can see only as a drop down menu) otherwise full ssid input as is now.
4. Release-ready? Then compile!
4. Separate start-install page from connect_screen, allowing to re-order pages, and let that have a page for install progress.
4. Get pretty name (Neato D7, Neato D10 etc. instead of just generation as is current)
4. Add translations (help wanted, what languages do yall speak?)
5. Prettyfy and unify scripts, for example creating another MTP folder for wifi config, vacuula version textfile and for example allowing to drop vacuula extensions/language packs w/e 'n etc.
5. Prettify the connect vacuula svg, remoing the WIP banner
6. Release-ready! Compile!

## Run it as dev

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

To pass server detection screen without a server (using avahi-utils):
```bash
avahi-publish -a vacuula-server.local <a-random-but-valid-ip>
```


## Adding a language

1. Copy `locales/en.json` to `locales/<code>.json` and translate the values.
2. Add one line to `LANGUAGES` in `app/constants.py`:
   ```python
   "fr": LanguageMeta(flag="🇫🇷", native_name="Français"),
   ```
NOTE! If you add or update strings increment strings version in the updated file(s)!!

Higest "strings-version" or english if all are same is the language to translate from. When "catching up"
a language, update its strings-version to the same as the language it caught up to.

NOTE! While locale.json with the higest "Strings-version" is technically the translation to translate from, lets keep it to en.json.


## Placeholders:
- **`app/core/installer.py`** — `InstallerLauncher.launch(model_id)`
  A placeholder draft, needs some refactoring but the working principle is there.
  Real scripts go into `_SCRIPTS` (paths per model) and replace the `TODO` with
  an actual (non-blocking) launch, e.g. `QProcess`.
