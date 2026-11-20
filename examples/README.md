# Google Calendar + Nabu Recall — működési példa

Az [eseménylétrehozó szkript](google_calendar_create_event.yaml) **külön Home Assistant-szkript**. Nem a Nabu Recall kódja, és telepítéskor **nem kerül automatikusan** az otthoni HA-ba. A Home Assistant szkript YAML-szerkesztőjében másold be, mentsd, majd tedd elérhetővé a hangasszisztens számára (**Voice assistants / Expose**).

## Miért kell külön szkript?

A tapasztalat szerint a HUN OpenAI Conversation a `calendar__get_events` eszközzel el tudja olvasni a Google naptárat, de az olvasás **nem** jogosít eseménylétrehozásra. A közvetlen `calendar.create_event` HA-művelet működött, ezért célzott, csak a `calendar.esemenyek` entitásra író szkriptet készítettünk. A szélesebb rendszergazdai AI-hozzáférés nem szükséges.

## Mit ad át az asszisztens?

- `esemeny`: esemény címe, pl. `Próba esemény`
- `nap`: `holnap`, `holnapután`, következő hétköznap neve vagy pontos `YYYY-MM-DD`
- `ora`: kötelező kezdőóra 0–23
- `perc`: opcionális; hiány esetén 0
- `idotartam`: opcionális; hiány esetén 30 perc

Az AI **nem** találhat ki dátumot vagy kezdőórát. Kérdés hiányában a szkriptet meg sem hívhatja. A Home Assistant a `now()` időből számítja a relatív napokat, és elutasítja az érvénytelen/múltbeli időpontokat. A helyi időzónát Home Assistantban **Europe/Budapest** értékre állítsd. A „jövő hét kedd” eltér a „következő kedd”-től: előbbihez a `llm__GetDateTime` alapján pontos ISO-napot kell számolnia az AI-nak. A szkript egyszerű hétköznapnevei mindig a legközelebbi következő előfordulást jelölik.

A szkript példa, **nem teljes, kipróbált Google Calendar-integrációs csomag**. Éles használat előtt ellenőrizd a mentett eseményt a Google naptárban, különösen DST/óraátállás, hiányos dátum és több azonos nevű esemény esetén.

## Példák a korábbi tesztekből

| Magyar kérés | Elvárt viselkedés |
|---|---|
| „Írd be holnap reggel nyolcra, hogy próba esemény.” | `llm__GetDateTime` szükség szerint → `script__naptaresemeny_letrehozasa` `nap=holnap, ora=8`; 30 perc alapérték |
| „Írd be december 15-re 16 órára ...” | A dátum a következő releváns évben, pontos idővel; múltba írás tilos |
| „Jövő hét keddre reggel kilencre ...” | Aktuális idő lekérdezése és pontos dátum ellenőrzése |
| „Írd be a naptárba, hogy próba esemény.” | „Mikorra írjam be?” — **semmit sem ment** |
| „Töröld a próba eseményt.” | Nincs beépített törlőszkript; **nem** használható `todo__HassListRemoveItem` |
| „Kapcsold fel a dolgozó lámpáit. Most kapcsold őket le.” | Az eredeti HA-ügynök intézi; Nabu Recall nem veszi át a vezérlést |

## Miért nincs naptár-törlés?

A Google Calendar integráció HA-n keresztüli eseményolvasása és -létrehozása nem azonos egy tetszőleges esemény törlését támogató AI-eszközzel. A próbán az AI tévesen a `todo__HassListRemoveItem` teendőlista-eszközt választotta, ami nem naptár. A példaprojekt **nem valósít meg Google Calendar API-s eseménykeresést és -törlést**; a Google naptárból a törlés egyelőre manuális. Biztonságos későbbi megoldás pontos Google-event-ID-val, célzott jogosultsággal és egyértelmű találattal működhetne; puszta cím alapján vak törlés nem biztonságos.

A Home Assistant-szkript `calendar.create_event` hívása a naptárba ír, **nem** módosítja a Nabu Recall tartós memóriáját. A teljes naptárpéldához olvasd el a [HU kézikönyvet](../TELEPITES_HU.md) és [EN manualt](../MANUAL_EN.md).
