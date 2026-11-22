# 🧠 Nabu Recall — v1.1.2 (HAOS app) / v1.0.4 (HA integration)

**Magyar nyelvű, AI-alapú tartós beszélgetési memória Home Assistant Assist mellé.** A meglévő OpenAI Conversation ügynök eszközvezérlését megtartja; a Nabu Recall kiegészíti történeti visszakereséssel és tartós emlékekkel.

## Dokumentáció / Documentation

- **[Magyar telepítési és használati útmutató](TELEPITES_HU.md)** — lépések, használat és hibaelhárítás.
- **[English installation and user guide](MANUAL_EN.md)** — setup, use and troubleshooting.
- **[Családi útmutató](CSALADI_UTMUTATO.md)** — példák mindennapi használatra.
- **[Nabu Recall system-prompt addendum](NABU_RECALL_PROMPT.md)** — opcionális, kizárólag memóriával kapcsolatos, személyes adatokat nem tartalmazó utasításminta.
- **[Google Calendar example](examples/README.md)** — külön telepítendő naptárszkript.
- **[Release notes](nabu_recall/CHANGELOG.md)** és [fejlesztési történet](HISTORY.md).

**Fontos:** A beszélgetésmemória az asszisztenst használók között közös. **Ne taníts be neki fontos, érzékeny személyes információkat**, például jelszavakat, hozzáférési kulcsokat, pénzügyi vagy személyazonosító adatokat. A memóriaműveletek OpenAI API-feldolgozást is igénybe vesznek.

## Architecture

`nabu_recall/` is the Home Assistant OS app: encrypted SQLCipher SQLite, API bridge, AI memory processing, password-protected Ingress Web UI. `custom_components/nabu_recall/` is a **separately installed** HA custom integration that wraps an existing OpenAI Conversation agent. Updating one does **not** automatically update the other.

- 45-day verbatim conversation journal; long-term facts have **no time-based expiry**.
- Private bridge: TCP 8765, token-protected; Ingress dashboard: TCP 8766, HA login **plus** separate password. Neither should be published to LAN/WAN.
- Web UI login expires after **10 minutes** (fixed lifetime, not rolling activity timeout).
- The encrypted database `/data/recall.sqlite3` and key `/data/recall.key` must always be backed up together.
- Home Assistant's calendar integration is separate from memory. A targeted Assist-exposed script supports Google Calendar creation; voice deletion is **not** implemented in this project.

## Installation / updates

Read the [Hungarian](TELEPITES_HU.md) or [English](MANUAL_EN.md) guide before installation. **Back up the HAOS app data first, especially the SQLite file and its key.** The integration installer keeps an on-disk backup of the previous integration folder:

```sh
curl -fsSL https://raw.githubusercontent.com/hollosipeti/nabu-recall/main/install_integration.sh -o /tmp/install_nabu_recall.sh && sh /tmp/install_nabu_recall.sh
```

Then restart **Home Assistant Core**. Updating only the HAOS app does not replace `/config/custom_components/nabu_recall`.

## Karbantartás

A Nabu Recall jelenlegi HAOS alkalmazása **1.1.2**, a Home Assistant-integráció **1.0.4**. Az alkalmazás és az integráció külön frissül. A memóriák a HAOS alkalmazás adatkönyvtárában vannak; frissítés előtt készíts alkalmazásmentést.

A részletes korábbi fejlesztési eredmények és karbantartási mechanizmusok a [változásnaplóban](nabu_recall/CHANGELOG.md), a [HISTORY.md](HISTORY.md) és a [biztonságos karbantartási leírásban](docs/SAFE_CLEANUP_HU.md) találhatók.

MIT License.
