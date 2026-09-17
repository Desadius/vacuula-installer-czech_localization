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

1. ~~Add logic (using serial) to separate out gen2 from gen3~~
2. Separate start-install page from connect_screen, allowing to re-order pages, and let that have a page for install progress.
3. For gen 2 & 3 ask user to connect to robots wifi then allow to select available wifi networks from robot directly - gen4 uses current wifi page 
4. Add actual installing scripts (they are to be called from installer.py in core). Everything the script needs should be in the session Class instance that main_window can pass it when start-install is requested..
5. ~~Release-ready? Then compile (multiplatform)!~~
6. ~~Get pretty name (Neato D7, Neato D10 etc. instead of just generation as is current)~~
7. Add translations (help wanted, what languages do yall speak?)
7. Prettify and unify scripts, for example creating another MTP folder for wifi config, vacuula version textfile and for example allowing to drop vacuula extensions/language packs w/e 'n etc.
7. Prettify the connect vacuula svg, remoing the WIP banner (robot->out with dustbin + robot<->computer)
8. Release-ready! Compile!

## Run it as dev

```bash
uv run vacuula-installer
```

To pass server detection screen without a server (using avahi-utils):
```bash
avahi-publish -a vacuula-server.local <a-random-but-valid-ip>
```


## Adding a language

1. Copy `src/locales/en.json` to `src/locales/<code>.json` and translate the values.
2. Add one line to `LANGUAGES` in `src/vacuula_installer/constants.py`:
   ```python
   "fr": LanguageMeta(flag="🇫🇷", native_name="Français"),
   ```
NOTE! If you add or update strings increment strings version in the updated file(s)!!

Higest "strings-version" or english if all are same is the language to translate from. When "catching up"
a language, update its strings-version to the same as the language it caught up to.

NOTE! While locale.json with the higest "Strings-version" is technically the translation to translate from, lets keep it to en.json.


## Placeholders:
- **`src/vacuula_installer/core/installer.py`** — `InstallerLauncher.launch(model_id)`
  A placeholder draft, needs some refactoring but the working principle is there.
  Real scripts go into `_SCRIPTS` (paths per model) and replace the `TODO` with
  an actual (non-blocking) launch, e.g. `QProcess`.
