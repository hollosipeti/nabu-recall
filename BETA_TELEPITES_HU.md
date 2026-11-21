# Nabu Recall 1.1.0b1 — elkülönített Home Assistant béta

Ez a béta a stabil HAOS 1.0.6 rendszer mellett **külön alkalmazásként** telepíthető.
Az alkalmazás neve `Nabu Recall (Beta)`, azonosítója `nabu_recall_beta`, verziója `1.1.0b1`.
A meglévő `Nabu Recall` alkalmazás és a `main` ág változatlan.

## Telepítés (HAOS / Supervisor)

1. Készíts teljes HA-mentést; őrizd meg a stabil Nabu Recall `/data/recall.sqlite3` és `/data/recall.key` fájlját **együtt**.
2. Beállítások → Alkalmazások → Alkalmazásbolt → ⋮ → Tárolók, add hozzá **pontosan**:
   `https://github.com/hollosipeti/nabu-recall#beta-1.1.0b1`
3. Frissítsd az alkalmazásbolt kínálatát, és keresd a **Nabu Recall (Beta)** alkalmazást. Ha nem jelenik meg, nézd meg a Supervisor naplóját, ne töröld a stabil appot.
4. Telepítsd a bétát, az alkalmazás saját beállításaiban adj meg külön `openai_api_key`, legalább 32 karakteres `bridge_token` és erős `dashboard_password` értéket, majd indítsd el.
5. A béta **külön üres memóriával** indul: nem másolja és nem módosítja automatikusan a stabil adatbázist. Ez szándékos. A béta tesztjében külön tesztemlékeket használj.
6. A meglévő HA `custom_components/nabu_recall` integráció marad v1.0.4, **nem kell újratelepíteni**. Csak akkor tudod hanggal tesztelni a béta emlékeit, ha az integráció bridge URL-je és tokenje **ténylegesen a béta alkalmazásra mutat**. A már működő HUN Assist-ügynök átállítása a stabil app működését érinti; erre külön próbaalkalmat válassz, és jegyezd fel a korábbi URL/token beállításokat. Az app saját Web UI-ja külön is ellenőrizhető.
7. A béta portjait (8765/8766) ne publikáld LAN/WAN felé. A bridge címét a Supervisor adott telepítésében ellenőrizd; ne feltételezd, hogy ugyanaz, mint a stabil alkalmazásé.

## Próbák

- A béta Web UI megnyílik; verziójelzés `1.1.0b1`.
- A stabil app saját emlékei nem jelennek meg az üres béta alkalmazásban.
- Emlék mentése és visszakeresése: `A műhelyben kék csavarbehajtóm van.` → `Milyen eszköz van a muhelyben?`
- Több gyors párbeszéd után a feldolgozatlan naplóbejegyzések száma később csökken.
- Ha az OpenAI API átmenetileg nem érhető el, a naplózott, feldolgozatlan bejegyzések megmaradnak, a feldolgozás később újraindul.
- A Home Assistant eredeti eszközvezérlése továbbra is működik (csak a béta bridge-re átállított integrációval teszteld).

## Visszaállás

1. Ha átállítottad az integrációt a béta bridge-re, állítsd vissza az eredeti stabil bridge URL-t és tokent.
2. Válaszd újra a stabil Nabu Recall ügynököt, ha megváltoztattad az Assist pipeline-t.
3. Állítsd le a **Nabu Recall (Beta)** alkalmazást. Csak ellenőrzés után távolítsd el.
4. A stabil alkalmazás saját adatbázisát, kulcsát és beállításait ne írd felül a bétával.

## Kiadási státusz

A Python unit/API/szintaxis tesztek GitHub Actions alatt futnak. A valós HAOS telepítés, container build, Supervisor bolt-felfedezés és élő Assistant-környezet még felhasználói próbát igényel.

**Nem változik:** személyes azonosítók hozzáférés-kezelése, HA integráció 1.0.4, 45 napos naplómegőrzés, SQLCipher adatséma.
