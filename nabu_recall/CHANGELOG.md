# Nabu Recall — kiadási napló

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
