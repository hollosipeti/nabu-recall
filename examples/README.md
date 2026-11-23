# Google Calendar + Nabu Recall — működési példa

Az [eseménylétrehozó szkript](google_calendar_create_event.yaml) **külön Home Assistant-szkript**. Nem a Nabu Recall kódja, és telepítéskor **nem kerül automatikusan** az otthoni HA-ba. A Home Assistant szkript YAML-szerkesztőjében másold be, mentsd, majd tedd elérhetővé a hangasszisztens számára (**Voice assistants / Expose**).

## Hétvégi naptárlekérdezés (csak olvasás)

A [külön hétvégi lekérdező szkript](google_calendar_weekend_events.yaml) a Home Assistant saját órájával számolja a szombat 00:00–hétfő 00:00 időablakot. Hétfőtől péntekig a közelgő hétvégét, szombaton és vasárnap az aktuális hétvégét választja. A `calendar.get_events` akció visszakapott eredményét adja tovább; nem ír a naptárba.

A HA felületen **külön szkriptként** telepítsd, ne az eseménylétrehozó helyére; a hangasszisztens számára tedd elérhetővé (Expose). Az eredeti OpenAI Conversation Instructions mezőbe másold át a `CALENDAR EVENT QUERY` frissített utasításait is. Csak a GitHub-fájl frissítése önmagában nem befolyásolja az éles asszisztenst.

A szkript nem módosítja és nem törli a naptáreseményeket. Éles ellenőrzéshez nézd meg, hogy egy pénteki egynapos esemény kimarad, a szombati/vasárnapi szerepel, egy pénteken kezdődő, szombatra átnyúló esemény pedig helyesen bent marad. Az időszak végét a Home Assistant naptár API-ja kizárólagosnak tekinti.

## Miért kell külön szkript?

A tapasztalat szerint a HUN OpenAI Conversation a `calendar__get_events` eszközzel el tudja olvasni a Google naptárat, de az olvasás **nem** jogosít eseménylétrehozásra. A közvetlen `calendar.create_event` HA-művelet működött, ezért célzott, csak a `calendar.esemenyek` entitásra író szkriptet készítettünk. A szélesebb rendszergazdai AI-hozzáférés nem szükséges.

## Mit ad át az asszisztens?

- `esemeny`: esemény címe, pl. `Próba esemény`
- `nap`: `holnap`, `holnapután`, következő hétköznap neve, év nélküli `MM-DD` vagy pontos `YYYY-MM-DD`
- `ora`: kötelező kezdőóra 0–23
- `perc`: opcionális; hiány esetén 0
- `idotartam`: opcionális; hiány esetén 30 perc
- `vege_ora`, `vege_perc`: opcionális befejezési idő; ha adott az intervallum (pl. 10 és 11 között), ezt add át, így nem veszik el az időtartam

Ha a felhasználó csak hónapot és napot mond, az AI **`MM-DD`-t adjon át, soha ne találjon ki évszámot**. A Home Assistant a következő még jövőbeli előfordulást választja; teljes évszám esetén azt változtatás nélkül használja, és elutasítja a múltbeli dátumot. Az AI **nem** találhat ki dátumot vagy kezdőórát. Kérdés hiányában a szkriptet meg sem hívhatja. A Home Assistant a `now()` időből számítja a relatív napokat, és elutasítja az érvénytelen/múltbeli időpontokat. A helyi időzónát Home Assistantban **Europe/Budapest** értékre állítsd. A jelenlegi szkript az `MM-DD` formátummal évváltáskor is működik. A „jövő hét kedd” eltér a „következő kedd”-től: előbbihez a `llm__GetDateTime` alapján pontos ISO-napot kell számolnia az AI-nak. A szkript egyszerű hétköznapnevei mindig a legközelebbi következő előfordulást jelölik.

**Fontos frissítés:** a "jövő hét kedden" típusú relatív napokat a szkript számolja ki a HA helyi idejéből, ezért az AI-nak a nap mezőbe **szó szerint ezt a kifejezést** kell átadnia, nem egy becsült `MM-DD` dátumot. Egyszerű "pénteken" kérésnél a következő jövőbeli pénteket választja. A megadott befejezési idő elsőbbséget élvez; ha időtartamot is adtak, és a kettő nem egyezik, a szkript elutasítja a kérést. Sikeres írás után az esemény tényleges kezdő és befejező idejét visszaadja az AI-nak. A szkript `mode: parallel` üzemmódban várja meg a válaszüzenetet.

**Telepítéskor a meglévő HA-szkriptet külön frissíteni kell a YAML-szerkesztőjében**, mivel a GitHub fájl módosítása nem frissíti automatikusan a Home Assistantban már létrehozott szkriptet. Ugyanez igaz a `NABU_RECALL_PROMPT.md` fájlra: a módosított szöveg nem jelenik meg automatikusan a tényleges OpenAI Conversation Instructions mezőben.

A szkript **dokumentációs példa**, nem a telepített éles szkript automatikus frissítése. Az itt közzétett `MM-DD` változatot még külön ellenőrizni kell a tényleges HA-sablonmotorban és Google Naptárban; a korábbi beszélgetésben szereplő helyi teszteredmény nem bizonyít HAOS-integrációs futást. A szkript **nem teljes Google Calendar-integrációs csomag**. Éles használat előtt ellenőrizd a mentett eseményt a Google naptárban, különösen DST/óraátállás, hiányos dátum és több azonos nevű esemény esetén.

## Fontos, hogy a naptár entitást mindenkinek a sajátjára át kell állítania!!!

```yaml
  - action: calendar.create_event
    target:
    # FIGYELEM!!! az entity_id mindenkinél más lehet!!! Ellenőrizd a saját naptáradat!
      entity_id: calendar.esemenyek
```

## Példák a korábbi tesztekből

| Magyar kérés | Elvárt viselkedés |
|---|---|
| „Írd be holnap reggel nyolcra, hogy próba esemény.” | `llm__GetDateTime` szükség szerint → `script__naptaresemeny_letrehozasa` `nap=holnap, ora=8`; 30 perc alapérték |
| „Írd be december 15-re 16 órára ...” | `nap=12-15`, `ora=16`; a HA választja ki a következő jövőbeli évet |
| „December 1-jén reggel 6-ra körmös.” | `nap=12-01`, `ora=6`; 2026. november 20-án a dátum 2026-12-01 |
| „2023. december 1-jén reggel 6-ra ...” | `nap=2023-12-01`; múltbeli időpont, elutasítás |
| „Jövő hét keddre reggel kilencre ...” | Aktuális idő lekérdezése és pontos dátum ellenőrzése |
| „Írd be a naptárba, hogy próba esemény.” | „Mikorra írjam be?” — **semmit sem ment** |
| „Töröld a próba eseményt.” | Nincs beépített törlőszkript; **nem** használható `todo__HassListRemoveItem` |
| „Kapcsold fel a dolgozó lámpáit. Most kapcsold őket le.” | Az eredeti HA-ügynök intézi; Nabu Recall nem veszi át a vezérlést |

## Miért nincs naptár-törlés?

A Google Calendar integráció HA-n keresztüli eseményolvasása és -létrehozása nem azonos egy tetszőleges esemény törlését támogató AI-eszközzel. A próbán az AI tévesen a `todo__HassListRemoveItem` teendőlista-eszközt választotta, ami nem naptár. A példaprojekt **nem valósít meg Google Calendar API-s eseménykeresést és -törlést**; a Google naptárból a törlés egyelőre manuális. Biztonságos későbbi megoldás pontos Google-event-ID-val, célzott jogosultsággal és egyértelmű találattal működhetne; puszta cím alapján vak törlés nem biztonságos.

A Home Assistant-szkript `calendar.create_event` hívása a naptárba ír, **nem** módosítja a Nabu Recall tartós memóriáját.
