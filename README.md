# 🧠 Nabu Recall — v1.1.1 (HAOS app) / v1.0.4 (HA integration)

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

## Preserved reference versions and current maintenance

No change to memory learning or recall, prompts used by the memory API, schema, SQLCipher migration, retention, background schedule, HA controls or the Google Calendar script. The HAOS app is v1.1.1; the integration is v1.0.4 with corrected assistant-response journal logging. The ALFA (`alpha-baseline-2026-11-20`) and v1.0.4 (`baseline-v1.0.4-2026-11-20`) Git branches are frozen code references. The documentation-only calendar YAML example handles `MM-DD` dates and needs testing in a live HA setup.

MIT License.

## Fejlesztés: biztonságos naplókarbantartás

A [biztonsági mentés és naplótisztítás útmutatója](docs/SAFE_CLEANUP_HU.md) bemutatja a kézi archiválást és visszavonást. A diagnosztikai nézetek változatlanul csak olvasnak; a külön karbantartási oldalon van mód jóváhagyott változtatásra.

**HAOS v1.0.4 manual maintenance:** authenticated Ingress page with archive, individual memory merge and undo. Run a verified Home Assistant app backup before installing. See [HAOS verification](docs/HAOS_AUDIT_TEST_HU.md).

## Kézi karbantartás — HAOS v1.0.4

A jelszóval védett Ingress Web UI **Kézi karbantartás** oldalán a feldolgozott, hiányos és a tartós emlékek által közvetlenül nem hivatkozott naplóbejegyzések **visszavonható archiválása** külön kattintásra fut. Az archív rekordok a SQLCipher adatbázisban maradnak, és ugyanúgy lejárnak 45 nap után. A **Memóriaoptimalizálás** gomb AI-javaslatokat készít; minden összevonáshoz külön felhasználói jóváhagyás kell, és az utolsó összevonás legfeljebb hét napig visszavonható. Éles telepítés előtt ellenőrzött Home Assistant alkalmazásmentés szükséges. A rendszer nem tartalmaz automatikus tömeges optimalizálást.

## HAOS v1.0.5 — tartós memória 100 000 bejegyzésig tesztelve

A tartós emlékek keresése a **teljes SQLCipher-adatbázisban** történik, és csak a találatok szűkülnek az AI-nak átadott rövid listára. A régi emlékek nem esnek ki pusztán azért, mert nem szerepelnek az utolsó 200-ban. A magyar ékezetes kis- és nagybetűk egyezése támogatott. A **Kézi karbantartás** oldalon a teljes állományból szövegszerkezet szerint hasonló duplikátumjelöltek kereshetők; a szélesebb szemantikai AI-ellenőrzés 160-as adagokban lapozható. **Ez nem garantálja minden átfogalmazott vagy ellentmondó emlék automatikus felismerését.** Az AI-javaslatok csak jóváhagyással módosíthatnak emléket.

## HAOS v1.0.6 — egyszerűbb memóriakezelés

A külön **Naplóellenőrzés** navigációs menüpont helyett az alapadatok a **Memóriakezelés** oldalon jelennek meg. A teljes, csak olvasható diagnosztikai útvonal technikai hibaelhárításhoz továbbra is elérhető. A duplikációkeresésből származó AI-javaslatok egyenként **jelölőnégyzetekkel választhatók ki**. A „Kijelöltek ellenőrzése” semmit nem módosít; megjeleníti a végső összefoglalót. A tényleges változáshoz újabb, kifejezett jóváhagyás szükséges. A kiválasztott javaslatok egyetlen adatbázis-tranzakcióban lépnek életbe vagy mind visszagörgetődnek. Az utolsó csoportos jóváhagyás egyben visszavonható a megőrzött, legfeljebb 7 napos visszavonási időn belül.
