# Nabu Recall — korábbi fejlesztési történet / Previous development history

Ez **történeti archívum**, nem a jelenlegi telepítési útmutató. A korabeli állítások (például titkosítatlan SQLite) a régi kiadásokra vonatkoznak; 

# Nabu Recall – változások

## 1.0.2 — 2026-11-19 (csak custom integration)
- Helyi ikon és logó a custom integration brand/ mappájában.
- Telepítő visszajelzi a bemásolt integráció pontos manifest-verzióját és az ikon jelenlétét.
- A HAOS alkalmazás és a memória/AI feldolgozás változatlan (alkalmazás v1.0.1).


## 1.0.1 — 2026-11-19
- Első hivatalos kiadás automatikus UI-verziótesztjének javítása. A memóriafeldolgozás változatlan.


## 1.0.0 — 2026-11-19 (első hivatalos kiadás)
- Új, csak olvasható „Memória és tárhely” panel: memóriák, naplóbejegyzések, titkosított adatbázis/WAL/SHM lemezmérete, szabad adatpartíció-tárhely.
- Külön, jelszóval védett Ingress Web UI. Jelszó nélkül zárolva; 8 órás, újraindításkor érvénytelenedő munkamenet; kijelentkezés.
- A jelszó a Home Assistant alkalmazás opciói között található, nem az emlékekben. Ne adj meg valódi jelszót hangparancsban.
- A memóriafeldolgozás, visszakeresés, adatbázisséma és SQLCipher titkosítás nem változott.


## 0.3.6 — 2026-11-19
- A naptárba mentési, naptáresemény-létrehozási és naptárból törlési kérések átmennek az eredeti Home Assistant ügynökhöz, nem kapnak téves memória-mentési visszajelzést.
- Kifejezett naptár-preferencia megjegyzése továbbra is memória utasítás.
- A 45 napos napló háttértanulása nem tekintheti a naptáresemény-létrehozást tartós ténynek.
- A webes állapotlap verziója a futó kiszolgáló verzióját követi.
- Adatbázis-séma és titkosítás változatlan.


## 0.3.5 — 2026-11-19
- Beszélgetőügynök személyes és hétköznapi családi adatokat általánosan kezelő utasítása, TAJ-specifikus szűkítés helyett.
- A beszélgetés, memóriafeldolgozás, tároló, titkosítás és hálózati API logikája változatlan.


## 0.3.4 – 2026-11-19
- HAMIS TAJ-kezelési elutasítás elleni explicit HUN agent útmutatás, célzott visszakeresési viselkedés.
- Elírt/hibásan felismert TAJ kérdések kontextusfüggő értelmezése, számok kitalálása nélkül.
- Háttér AI prompt helyes SQLCipher leírása; a puszta bemondás nem automatikus tartós mentési engedély.
- Sem adatbázis-, sem memória-API módosítás nincs.


## 0.3.3 — 2026-11-19
- SQLCipher migráció: fájlkezelési figyelmeztetés javítása.
- WAL és sérült régi adatbázis regresszióteszt.


## 0.3.2 — 2026-11-19
- SQLCipher AES-256 titkosítás a teljes SQLite fájlon.
- Automatikusan generált független kulcs /data/recall.key, 0600 jogosultsággal.
- Ellenőrzött régi DB migráció; fail-closed hiányzó kulcs esetén.
- Memória- és AI-logika változatlan.


## 0.3.1 – 2026-11-19
- HTTP integration test isolated DB_PATH fix.


## 0.3.0 – 2026-11-19
- Offline HTTP bridge integrációs tesztek mock AI-val, biztonsági és adatbázis-hibaforgatókönyvekkel.
- A felhasználói adatokat és OpenAI-kulcsot nem használó tesztfuttatás.


## 0.2.9 — 2026-11-19
- Kontextusteszt Python-literál javítása.
- Közvetlen előzményre korlátozott elliptikus parancsok.


## 0.2.8 – 2026-11-19
- A „Mentsd el!” kifejezés megkapja a friss, azonos beszélgetésből származó előző mondatot, ha egyértelmű.
- Korlátozás: maximum 5 perc; másik beszélgetés és asszisztensszöveg nem forrás.
- „ki kell javítani” parancsalak felismerése; részletesebb kontextus-regressziótesztek.


## 0.2.7 — 2026-11-19
- Szerveroldali teljes törlés elleni védelem: a „minden” szóalak felismerése.
- Automatikus teszthiba javítása.


## 0.2.6 — 2026-11-19
- Magyar mentés/javítás/törlés parancsalakok bővítése, szabályos reguláris kifejezésekkel.
- Javító AI részletesebb személy–tárgy kapcsolatmegőrzési utasítása.
- Kevesebb téves „nem tudom menteni” válasz a parancsoknál.


## 0.2.5 — 2026-11-19
- Memóriaparancsok reguláris kifejezésének javítása (escape-hiba).
- Természetes válasz a háttérben tanult kijelentésekre, hamis tárolási tiltás nélkül.


## 0.2.4 — 2026-11-19
- Egyedi kifejezett mentés, javítás és törlés szinkron API-val és megerősített SQLite-visszajelzéssel.
- Az explicit műveleteket a háttérfeldolgozó nem hajtja végre másodszor.
- Teljes memóriatörlés továbbra sincs engedélyezve.


## 0.2.3 — 2026-11-19
- Szerveroldali védelem a tömeges hangos memóriatörlés ellen.
- Egy feldolgozási adagban maximum egy konkrét, kifejezetten kért azonosító szerinti törlés engedélyezett.
- A 45 napos napló lejárata továbbra is automatikus.


## 0.2.2 — 2026-11-19
- A felhasználó kifejezett kérésére megengedett telefonszám, TAJ és személyi igazolványszám tartós tárolása.
- Bankszámla, bankkártya, kripto és hitelesítési titkok továbbra is kizárva a tartós memóriából.
- Az adatok változatlanul 45 napos szó szerinti, titkosítatlan naplóba is bekerülhetnek.


## 0.2.1 — 2026-11-19
- Megszüntettük a személyes adatok általános elutasítását a beszélgetőügynök utasításában.
- Telefonszám mentése kifejezett felhasználói kérésre az AI döntése alapján megengedett.
- TAJ- és egészségügyi azonosítók automatikus tartós megőrzése továbbra sem engedélyezett titkosítás nélkül.
- A 45 napos nyers napló továbbra is szó szerinti, így érzékeny adatot is tartalmazhat.

## 0.2.0
- Állapotlap, napló- és tartós memórialista, telepítés, ikon.
