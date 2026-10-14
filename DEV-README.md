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
flowchart TD
    subgraph FU ["Firmware update screen"]
        direction TB
        Fpick["Pick version<br/>gen3: factory-reset link + acknowledgement"]
        Freset["gen3: factory-reset instructions"]
        Fdl["Download"]
        Fprompt["Install prompt"]
        Finst["Install + robot reboot"]
        Ffail["Download/install failed, retry"]
        Fpick --> Fdl
        Fdl --> Fprompt
        Fprompt --> Finst
        Fdl --> Ffail
        Finst --> Ffail
        Ffail -->|download retry| Fpick
        Ffail -->|install retry| Fprompt
        Fpick --> Freset
        Freset --> Fpick
    end

    subgraph WIFI ["Wifi setup"]
        direction TB
        W4["gen4: enter SSID + password"]
        W3pre["gen3: connect PC to robot's own access point"]
        W3["gen3: pick scanned network, or type SSID manually"]
        W3pre -->|connection succeeds| W3
    end

    subgraph PROV ["Install"]
        direction TB
        P4["gen4 instructions<br/>+ power-cycle instructions"]
        P3["gen3 instructions<br/>+ serial log viewer"]
    end

    A["Welcome screen<br/>language picker + find-help link"]
    B["Disclaimer<br/>+ acknowledgements"]
    C["Server search<br/>auto-detect server, or enter IP manually"]
    D["Connect robot<br/>waiting for USB robot"]
    E{"Firmware check"}
    G{"Robot generation"}
    FIN["Finished<br/>+ project links"]
    ERR["Error screen"]

    A -->|continue| B
    B -->|understand| C
    C -->|server found| D
    D -->|robot detected| E
    D -->|multiple robots| ERR

    E -->|valid firmware| G
    E -->|old or unsupported firmware, incl. gen2| Fpick
    E -->|read error| ERR

    G -->|gen4| W4
    G -->|gen3| W3pre

    W4 -->|SSID + password| P4
    W3 -->|SSID + password| P3

    FU -->|robot unplugged| ERR
    WIFI -->|wifi fix failed or robot unplugged| ERR
    P4 -->|finished, robot reboots| FIN
    P3 -->|finished, robot reboots| FIN
    P4 -->|failed| ERR
    P3 -->|failed| W3

    ERR -->|restart| A

    style A fill:#90EE90,stroke:#2e7d32,color:#000
    style B fill:#90EE90,stroke:#2e7d32,color:#000
    style C fill:#90EE90,stroke:#2e7d32,color:#000
    style D fill:#90EE90,stroke:#2e7d32,color:#000
    style W4 fill:#90EE90,stroke:#2e7d32,color:#000
    style W3pre fill:#90EE90,stroke:#2e7d32,color:#000
    style W3 fill:#90EE90,stroke:#2e7d32,color:#000
    style P4 fill:#90EE90,stroke:#2e7d32,color:#000
    style P3 fill:#90EE90,stroke:#2e7d32,color:#000
    style FIN fill:#90EE90,stroke:#2e7d32,color:#000
```

- Fix a more direct link in error.firmware.help
- Go trough the TODO:s that are sprinkled as comments in the code
- Add translations (help wanted, what languages do yall speak?) __<-- prio!__
- Prettify and unify scripts, for example creating another MTP folder for wifi config, vacuula version textfile and for example allowing to drop vacuula extensions/language packs w/e 'n etc.
- Test on osx __<-- prio!__
- Figure out why gen4 does not work on mac __<-- prio!__
- Show/hide passwordfield (eye) wifisection(s)
- Clean up the firmware.install.done.disconnected. error page building to a ifstatement, removing the duplicate strings in the lang.json as well (same for firmware.genx-x.x.x.description)
- gen23 feedback if people click "i have connected" when they havent on prewifi page
- "🛈" ruins rowspacing in details texts
- Skip firmware seelction if only one option
- Preselect recommended firmware
- Radio buttons larger in firmware selector
- When restarting after firmware update, skip welcome and disclaimer pages __<-- prio!__


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

