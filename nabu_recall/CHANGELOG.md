# Nabu Recall – változások

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
