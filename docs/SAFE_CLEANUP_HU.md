# Nabu Recall — biztonsági mentés és naplótisztítás (fejlesztési terv)

**Állapot:** csak tervezés és olvasható előnézet. Ez az útmutató **nem engedélyez törlést**.
Az ALFA és a v1.0.4 referenciaágakat tilos módosítani.

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
   készíts új, az **Nabu Recall alkalmazást és adatait** is tartalmazó mentést.
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

A jelentés kizárólag **SELECT** lekérdezésekkel készül. Nincs mentési,
archiválási vagy törlési végpont, és nincs "Törlés" gomb.

## Jövőbeli tisztító végrehajtás kötelező feltételei

A további fejlesztés csak akkor kerülhet éles rendszerbe, ha:
- a mentés és a próba-visszaállítás dokumentáltan sikeres,
- a változtatandó napló-ID-k és a védett források külön láthatók,
- a jelöltek újraellenőrzése a végrehajtás pillanatában megtörténik,
- a végrehajtást külön, tudatos felhasználói megerősítés engedélyezi,
- a tartós emlékek megőrzése és a visszavonás tesztelve van.

**A jelenlegi fejlesztési ág semmilyen adatot nem töröl.**

## Tesztterv

Az éles állapot érintetlenül hagyásával végzett HAOS ellenőrzés lépései:
[HAOS_AUDIT_TEST_HU.md](HAOS_AUDIT_TEST_HU.md).

Az `tests/test_audit_fixture.py` ellenőrzése valódi titkosított SQLCipher
próbaadatbázist használ: bizonyítja, hogy a lekérdezés nem módosítja a
`turns`, `memories` táblákat vagy a kulcsot. **Ez nem helyettesíti az
éles rendszer mentés-visszaállítási tesztjét.**
