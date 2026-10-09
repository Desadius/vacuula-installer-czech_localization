# Vacuula Installer

Goals for this is to:
1. Look good
2. Unify installation for all supported neatos
3. Work on mac, windows, any resonable linux distro
4. Easy localisation
5. Be as much of "one click install" mantra as possible aka. KISS

Goals are NOT:
1. Server install walk-trough, you can find that [here]()
2. Un-rainbower, for that we need to help you via the [discord]() 


## Before release
- Add translations (help wanted, what languages do yall speak?) ?
- Prettify the connect vacuula svg, remoing the WIP banner (robot->out with dustbin + robot<->computer)
- Release-ready! Compile!




## Run it as dev

```bash
uv run vacuula-installer
```

To pass server detection screen without a server:
```bash
uv run fake-server.py
```

## Adding a language

1. Copy `src/locales/en.json` to `src/locales/<code>.json` and translate the values.
2. Get svg for flag you want to use from `https://github.com/lipis/flag-icons` and put into `/src/assets/flags`. Use the 3x4 flags!
2. Add one line to `LANGUAGES` in `src/vacuula_installer/constants.py`:
   ```python
   "fr": LanguageMeta(flag_svg=FLAGS_DIR / "fr.svg", native_name="Français"),
   ```
NOTE! If you add or update strings increment strings version in the updated file(s)!!

Higest "strings-version" or english if all are same is the language to translate from. When "catching up"
a language, update its strings-version to the same as the language it caught up to.

NOTE! While locale.json with the higest "Strings-version" is technically the translation to translate from, lets keep it to en.json.


## Future ideas
- Prettify and unify scripts, for example creating another MTP folder for wifi config, vacuula version textfile and for example allowing to drop vacuula extensions/language packs w/e 'n etc.
