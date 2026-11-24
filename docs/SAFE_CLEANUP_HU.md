# Nabu Recall — biztonsági mentés és naplókarbantartás

**Állapot:** a 2.0.x alkalmazáshoz tartozó biztonsági mentési és jóváhagyott karbantartási útmutató, beleértve a 2.0.1-es forgómemória-törlést. A HA-integráció külön naptárjavítása nem változtatja meg a mentési és karbantartási eljárást. A diagnosztikai nézetek csak olvasnak; a külön Kézi karbantartás oldalon titkosított naplóarchiválás, visszaállítás és ellenőrzött memóriaösszevonás lehetséges. A főverzió előtti állapot a `stable-2026-11-24-before-v2` ágon visszakereshető.

## 2.0.1 – Forgó memória kézzel kijelölt, VÉGLEGES törlése

A Web UI **Memóriakezelés → Forgó memória – végleges törlés** oldalán külön művelet jelent meg. Ez eltér az alább dokumentált, visszaállítható hiányosnapló-archiválástól: **a kijelölt beszélgetéseket ténylegesen törli a titkosított adatbázisból, nem archiválja, és nem ad hozzá visszavonási lehetőséget**.

Kereshetsz, dátum szerint szűrhetsz, 40 soros oldalakon pipálhatsz, majd teljes előnézetből kétlépcsős jóváhagyással törölhetsz. Az aktív tartós emlék forrásaként hivatkozott, illetve feldolgozatlan sorok védettek. Törlés előtt a rendszer újraellenőrzi minden kijelölt sor épségét és hivatkozását; eltérésnél az egész művelet meghiúsul. A felhasználói adatok nem kerülnek automatikusan kiválasztásra.

Törlés előtt készíts ellenőrzött, konzisztens HA-mentést. A biztonsági mentésekben megmaradhat a korábbi szöveg, ezek életciklusát a Nabu Recall nem kezeli. A törlés SQLite `secure_delete` és WAL-truncate műveletet használ, de **a teljes fájlrendszeres adattörlés garanciáját ez önmagában nem jelenti**. Visszaállítás csak külső, a törlés előtti adatmentésből lehetséges.

## Miért kell külön mentés?

A `/data/recall.sqlite3` SQLCipherrel titkosított adatbázis. A hozzá tartozó
`/data/recall.key` fájl nélkül a másolat nem olvasható. Az aktív SQLite WAL
(`recall.sqlite3-wal`, `recall.sqlite3-shm`) miatt **élő fájlrendszerből a
`recall.sqlite3` egyszerű kimásolása nem konzisztens biztonsági mentés**.

A tartós emlékek `memories.source_turn` mezője hivatkozhat a napló
`turns.id` mezőjére. A 45 napos automatikus lejárat is megszüntethet
ilyen hivatkozásokat, miközben maga az emlék megmarad.

## Biztonságos mentési ellenőrzőlista (kézi)

1. Home Assistant **Beállítások → Rendszer → Biztonsági mentések** felületén
   készíts új, a **Nabu Recall alkalmazást és adatait** is tartalmazó mentést.
   A felület és a mentési opciók HA-verziótól függően eltérhetnek.
2. Ellenőrizd, hogy a mentés elkészült és a fájl elérhető. Ha lehet, őrizd
   meg egy második, helyben biztonságosan tárolt példányban is.
3. Biztosítsd, hogy a mentésben a titkosított `recall.sqlite3` **és**
   a `recall.key` is benne van; a konzisztenciát a támogatott
   HA alkalmazásmentés kezelje. Ne hagyatkozz kizárólag a fájlméretre.
4. Egy elkülönített Home Assistant tesztkörnyezetben végezz visszaállítási
   próbát. Ellenőrizd a napló és az emlékek darabszámát, néhány
   naplóbejegyzést, a titkosított adatbázis olvashatóságát.
   **A mentés létezése önmagában nem bizonyítja a visszaállíthatóságot.**
5. Jegyezd fel az ellenőrzés dátumát, az alkalmazás és az integráció
   verzióját, valamint az alábbi, érzékeny tartalmat nem tartalmazó számokat:
   összes napló, hiányos napló, hivatkozott hiányos napló, tartós emlék.
6. A mentés és a visszaállítási próba megerősítése nélkül **ne kezdj
   tisztítást**, ne ürítsd a táblákat, ne telepítsd újra az alkalmazást.

**Ne töltsd fel** a mentést, a `recall.key` fájlt vagy személyes
beszélgetésrészleteket nyilvános GitHub-repóba vagy hibajegybe.

## Visszaállítás — hiba esetén

- Előbb állítsd le a hibás folyamatot; ne futtass további naplótisztítást.
- A Home Assistant támogatott biztonsági mentés-visszaállító felületén
  állítsd vissza a korábban ellenőrzött Nabu Recall alkalmazásadatokat.
- Az adatbázis **és a hozzá tartozó eredeti kulcs** ugyanabból a
  mentési pillanatképből származzon.
- Ellenőrizd a memóriák és a napló sorainak darabszámát.
- A visszaállítás a mentés pillanatára visz vissza: a később írt naplók
  és emlékek elveszhetnek. Ne hajtsd végre ezt ellenőrizetlenül az éles
  rendszerben.

## Előnézet értelmezése

A Naplóellenőrzés három, egymást kizáró csoportot mutat:
- **Feldolgozatlan:** üres asszisztensválasz és `processed=0`. Védett.
- **Hivatkozott:** üres válasz, `processed=1`, és legalább egy
  `memories.source_turn` hivatkozik a naplóazonosítóra. Védett.
- **Nem hivatkozott:** üres válasz, `processed=1`, nem szerepel a
  jelenlegi memóriák közvetlen `source_turn` hivatkozásai között.
  Ez **nem jelenti**, hogy a napló biztosan érdektelen:
  az AI-visszakeresés továbbra is használhatja.

A **Naplóellenőrzés** jelentés kizárólag SELECT lekérdezéseket használ. A **Kézi karbantartás** oldalon viszont külön, tudatos kattintással a jelölt naplók archívumba helyezhetők; visszaállításuk lehetséges. Az archívum a 45 napos megőrzési szabály alá esik. A tartós emlékek összevonása AI-javaslat után egyenként jóváhagyandó.

## Karbantartási műveletek biztonsági feltételei

Karbantartás vagy új karbantartási funkció bevezetése előtt ellenőrizd, hogy:
- a mentés és a próba-visszaállítás dokumentáltan sikeres,
- a változtatandó napló-ID-k és a védett források külön láthatók,
- a jelöltek újraellenőrzése a végrehajtás pillanatában megtörténik,
- a végrehajtást külön, tudatos felhasználói megerősítés engedélyezi,
- a tartós emlékek megőrzése és a visszavonás tesztelve van.

**A normál 45 napos lejáraton kívül az alkalmazás nem futtat automatikus naplótisztítást vagy memória-összevonást.** A külön jóváhagyású műveletek visszavonási lehetősége a megőrzési határidőn és adatbázis-ütközésellenőrzésen belül él.

## Tesztterv

Az éles állapot érintetlenül hagyásával végzett HAOS ellenőrzéshez a
[fő telepítési útmutató](../README.md) frissítési szakaszát használd,
majd ellenőrizd a titkosított adatbázis és kulcs megőrzését, a napló és
a tartós emlékek számát, valamint az Assist működését.

Az `tests/test_audit_fixture.py` ellenőrzése valódi titkosított SQLCipher
próbaadatbázist használ: bizonyítja, hogy a lekérdezés nem módosítja a
`turns`, `memories` táblákat vagy a kulcsot. **Ez nem helyettesíti az
éles rendszer mentés-visszaállítási tesztjét.**
