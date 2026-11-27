## 3.0.1

Közvetlen, friss lekérdezés többhetes időszakokra és további természetes napirendi kérdésekre. Egyértelmű heti STT-hibák kezelése kizárólag naptári összefüggésben. Pontosabb saját naptáreszköz-utasítások, beszélgetésre korlátozott natív naptáreszköz-szűrés és friss lekérdezés ellenőrzése egyértelmű naptárkérdéseknél. A naptári írás, törlés és a memóriatárolás változatlan. Éles ellenőrzés szükséges.

## 3.0.0

Rövidebb, elkülönített naptárutasítások és teljes megjelenítési időtartam. Natív naptárképességek szerinti egyedi eseménymódosítás és törlés, friss azonosító-feloldással. Közvetlen, friss, AI nélküli naptárolvasás egyértelmű időszakos napirendi kérdésekhez. Fejlesztési ág, éles ellenőrzés szükséges.

## 2.0.6

Szemantikus naptárjelöltek, alapértelmezett naptár nélküli olvasás, szűk élő napirend gyorsút és munkamenetenkénti APP tokenstatisztika. A memória teljes visszakeresési útja bizonytalan kérdéseknél megmarad. Egyértelmű világítási parancsok kihagyása, kis emléktárnál egyetlen tanulási hívás, szűk helyi preferencia-gyorsút és tömörített AI-adatmezők.

## 2.0.5 — HA-integráció (APP változatlanul 2.0.4)

Több naptár automatikus felismerése, közös időrendi lekérdezése és célzott írása. A meglévő alapértelmezett naptár és időkezelés megmarad.

## 2.0.4 — célzott hibajavítás

Befoglaló naptári zárónap, összetett kérdések köztes szövegének szűrése, hiányzó új érték bekérése és kontextusfüggő mentés javítása. Éles ellenőrzés szükséges.

## 2.0.3 — fejlesztési tesztverzió

Memóriamentés és módosítás, többes mentés tranzakcióban, ismételt mentés, kontextus, összetett kérdések és naptári határnapok javítása. Éles HA-ellenőrzés szükséges.

# Nabu Recall — kiadási napló

## 2.0.2 — 2026-11-25 (HA-integráció; APP 2.0.1)

Éles használatban ellenőrzött naptárjavítás: jövő hét, tetszőleges dátumtartomány, havi lekérdezés, név szerinti eseménykeresés, egész napos, többnapos és éjfélen átnyúló események, magyar dátumok és percpontosságú időkezelés. A 35 magyar nyelvű éles teszt és a 4 végső rendszerellenőrzés a felhasználói visszajelzés szerint sikeres. Az APP 2.0.1 és a forgó memória törlése változatlan; a naptári módosítás és törlés továbbra sem támogatott. A GitHub `main` ága a tesztelt integrációfájlokat tartalmazza.

## 2.0.1 — 2026-11-24 (HAOS alkalmazás; HA-integráció továbbra is 2.0.0)

- **Kézi, visszavonhatatlan beszélgetéstörlés:** Web UI → Memóriakezelés → Forgó memória – végleges törlés. Pipa minden teljes kérdés–válasz párhoz, keresés, magyar időzónás dátumszűrés, lapozás, az aktuális oldalon törölhető sorok kézi kijelölése.
- A kijelölés után a teljes szövegű előnézet külön megerősítést és jelölőnégyzetet igényel, majd a törlés egyetlen SQLCipher-tranzakcióban történik. Egy művelet legfeljebb 40 sort töröl, 10 perc után lejár.
- A feldolgozatlan vagy bármely aktív tartós emlékhez `source_turn` kapcsolattal kötött naplósorok védettek. Az adatbázis minden sort újraellenőriz, így változás vagy védett rekord esetén semmit nem töröl.
- **Nem archiválás:** a törölt sor nem kerül a `journal_archive` táblába, nem állítható vissza a Nabu Recall UI-ján. SQLite `secure_delete` és WAL-checkpoint alkalmazva. Korábbi rendszermentés külön tartalmazhatja az adatokat.
- A meglévő 45 napos lejárat, automatikus tanulás, tartós emlékek, memóriaoptimalizálás és annak visszavonása, naptár, HA eszközvezérlés, a 2.0.0 HA-integráció és az AI-utasítások változatlanok.
- Új adatbázis-/UI-regressziók: jogosultság, CSRF, XSS, kézi megerősítés, törlési versenyhelyzet, véglegesség, referencia-védelem és 426 soros lapozás.


## 2.0.0 — 2026-11-24 (HAOS alkalmazás és HA-integráció)

**Főverzió, meglévő telepítésre frissíthető.** Az alkalmazás és az integráció ugyanazt a 2.0.0 verziót kapta.

- **Megőrzött működés:** azonos `nabu_recall` alkalmazás és HA-integráció; ugyanaz a SQLCipher titkosított `/data/recall.sqlite3` és `/data/recall.key`, adatbázis-migráció nélkül. A 45 napos forgó napló és a tartós emlékek nem törlődnek vagy konvertálódnak.
- **Aktív AI-utasítások kizárólag a repóból:** `custom_components/nabu_recall/repo_instructions.py` (beszélgető AI), `custom_components/nabu_recall/llm.py` (naptáreszközök), `nabu_recall/ai.py` (memóriatanulás, keresés, explicit memória-módosítások). A felhasználói HA OpenAI Conversation Instructions szöveget a telepítő nem módosítja. Pontos lista: [`NABU_RECALL_PROMPT.md`](../NABU_RECALL_PROMPT.md).
- **Aktuális emlékek:** a tartós memóriában megerősített aktuális preferencia elsőbbséget élvez a régi beszélgetési állítással szemben; a korábbi naplórészletek időbélyeggel továbbra is visszakereshetők.
- **Kezelés:** explicit emlékmentés, módosítás, célzott törlés, Web UI diagnosztika/karbantartás megmaradt. A memóriafeldolgozó kiszűri az információhiányos és puszta kérdésből született hamis tényeket.
- **Naptár:** a kiválasztott naptár friss lekérdezése, konkrét nap és hétvége kezelése, eseménylétrehozás változatlan. Nem támogatott: naptáresemény törlése vagy módosítása.
- **HA eszközvezérlés:** továbbra is a meglévő upstream OpenAI Conversation-ön és Assist LLM API-n keresztül; a felhasználó saját stílus- és eszközutasításai megmaradnak.
- **Takarítás:** a két régi naptár-YAML és hozzájuk tartozó szkripttesztek, korábbi fejlesztési állapotú dokumentumok, valamint a másolható, elavult HA promptminta eltávolítva. A Git-előzmény megőrzi őket.
- **Telepítő:** kizárólag a `main` kiadási ágat és az ellenőrzött `stable-2026-11-24-before-v2` visszaállítási ágat fogadja.
- **Tesztkapu:** teljes Python/HTTP/HA-wrapper regresszió, shell-szintaxis, a tényleges Docker-image és szerverimport ellenőrzése; a HAOS éles Assist-viselkedését telepítés után külön kell ellenőrizni.

A kiadás előtti pontos állapot: `stable-2026-11-24-before-v2`. A Git történetében megmaradnak a régi részletes kiadási jegyzetek és az eltávolított fájlok.

## Korábbi kiadások

Az 1.1.9 / 1.0.11 és korábbi verziók részletes dokumentációja a Git korábbi commitjaiban, valamint a [fejlesztési történetben](../HISTORY.md) található. Ez az aktív fájl kizárólag az aktuális főverzió kiadási megjegyzéseit tartalmazza, hogy ne legyenek megtévesztő „jelenlegi” verzióhivatkozások.
