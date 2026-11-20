# 🧠 Nabu Recall — v1.0.2 (HAOS app) / v1.0.2 (HA integration)

**Magyar nyelvű, AI-alapú tartós beszélgetési memória Home Assistant Assist mellé.** A meglévő OpenAI Conversation ügynök eszközvezérlését megtartja; a Nabu Recall kiegészíti történeti visszakereséssel és tartós emlékekkel.

## Dokumentáció / Documentation

- **[Teljes magyar kézikönyv](TELEPITES_HU.md)** — telepítés, frissítés, API, adatvédelem, rendszerutasítások, hibakeresés, valós működési példák.
- **[Complete English manual](MANUAL_EN.md)** — setup, upgrades, API calls, security, prompts, troubleshooting, examples.
- **[Google Calendar scripts / naptárszkriptek](examples/README.md)** and [example YAML](examples/google_calendar_create_event.yaml).
- **[Original, preserved assistant instructions](AI%20utas%C3%ADt%C3%A1sok.%20ki%20ne%20t%C3%B6r%C3%B6ld)** — an environment-specific working sample; adjust personal details before reuse.
- **[Current releases and history](nabu_recall/CHANGELOG.md)** — last two maintained versions; detailed old development history in [HISTORY.md](HISTORY.md).

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
curl -fsSL https://raw.githubusercontent.com/hollosipeti/nabu-recall/main/install_integration.sh -o /tmp/install_nabu_recall.sh
sh /tmp/install_nabu_recall.sh
```

Then restart **Home Assistant Core**. Updating only the HAOS app does not replace `/config/custom_components/nabu_recall`.

## What is deliberately unchanged in v1.0.2

No change to memory learning or recall, prompts used by the memory API, schema, SQLCipher migration, retention, background schedule, HA controls or the Google Calendar script. Only UI session expiry and documentation/repo organization changed.

MIT License.
