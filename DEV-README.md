# Vacuula Setup Wizard

Goals for this is to:
1. Look good
2. Unify installation for all supported neatos
3. Work on mac, windows, any resonable linux distro
4. Easy localisation
5. Be as much of "one click install" mantra as possible aka. KISS

Goals are NOT:
1. Server install walk-trough, that can be found [here]()
2. Un-rainbower, the [discord]() will serve that purpose

## Current TODO:s in random order

```mermaid
flowchart LR
    A["Welcome Screen</br>Språk, var man får hjälp"] -->|Frozen, compiled| B[Server search screen]
    A -->|Not compiled| C[Dev screen]
    C --> B
    B --> D

    subgraph D [Connect robot screen]
        direction TB
        Da(Step 1: Please connect robot)
        Db(Step 2: Firmware check)
        Da --> Db
    end

    Db -->|gen4| E
    Db -->|gen2/3| F

    subgraph WIFI [Wifi setup]
        direction TB
        E[Enter SSID/PW]
        F[Connect to robot own Wifi]
        Fb[Choose Wifi from drop-down]
        F --> Fb
    end

    E --> G
    Fb --> G

    subgraph G [Install screen]
        direction TB
        H[Fail page]
    end

    G --> I[Success page]

    style A fill:#90EE90,stroke:#2e7d32,color:#000
    style B fill:#90EE90,stroke:#2e7d32,color:#000
    style E fill:#90EE90,stroke:#2e7d32,color:#000
    style Da fill:#90EE90,stroke:#2e7d32,color:#000
    style Fb fill:#90EE90,stroke:#2e7d32,color:#000
```

- Prettify the connect vacuula svg, removing the WIP banner (robot->out with dustbin + robot<->computer) __<-- prio!__
- Fix a more direct link in error.firmware.help
- Go trough the TODO:s that are sprinkled as comments in the code
- Add translations (help wanted, what languages do yall speak?) __<-- prio!__
- Prettify and unify scripts, for example creating another MTP folder for wifi config, vacuula version textfile and for example allowing to drop vacuula extensions/language packs w/e 'n etc.
- Test on osx __<-- prio!__
- Show/hide passwordfield (eye) wifisection(s)
- Clean up the firmware.install.done.disconnected. error page building to a ifstatement, removing the duplicate strings in the lang.json as well (same for firmware.genx-x.x.x.description)


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
