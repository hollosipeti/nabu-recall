# Nabu Recall — HAOS próba menetrend (csak olvasás)

Ez az eljárás a `dev-journal-audit-2026-11-20` fejlesztői ághoz készült.
**Nincs automatikus éles telepítés, mentés, adatbázistörlés vagy tisztítás.**

## 1. Mentés az eredeti HAOS-rendszerben

1. Home Assistant → **Beállítások → Rendszer → Biztonsági mentések**.
2. Készíts egy új, a **Nabu Recall alkalmazást és annak adatait** tartalmazó mentést.
3. A mentés készülte után ellenőrizd a mentés részleteit; tárold biztonságos,
   nem nyilvános helyen. Ha lehet, készíts második offline példányt.
4. **Ne** másold ki külön az élő `recall.sqlite3` fájlt; a SQLCipher
   `recall.key` és a WAL pillanatkép is számít.
5. Jegyezd fel a mentés időpontját, a napló- és emlékszámot,
   az alkalmazás 1.0.2 és az integráció 1.0.4 verzióját.

## 2. Visszaállíthatósági próba külön környezetben

- Elkülönített Home Assistant tesztpéldányban állítsd vissza a mentést
  a Home Assistant támogatott helyreállítási folyamatával.
- Ellenőrizd, hogy a Nabu Recall nem hozott létre üres új adatbázist,
  hogy a tartós emlékek és a napló darabszáma egyezik a mentési pillanattal,
  és hogy az eredeti titkosítási kulccsal olvasható az adatbázis.
- Ne kapcsold a tesztpéldányt ugyanahhoz az éles hangasszisztenshez,
  és ne engedd, hogy az új felhasználói üzenetek a másolatra kerüljenek.
- A visszaállítási teszt **nem bizonyított**, amíg ezek nem teljesülnek.

## 3. Miért nem telepíthető érdemben a tesztalkalmazás második példányként?

A HAOS alkalmazások külön saját `/data` könyvtárat használnak.
Egy új azonosítójú tesztalkalmazás nem fér hozzá az eredeti Nabu Recall
SQLCipher-adatbázisához; üres adatbázison a 200+ hiányos beszélgetés
auditálása hamis eredményt adna.

Az azonos `slug` melletti fejlesztői frissítés pedig az éles alkalmazást
helyettesítené. Ez a mentés és elkülönített próba nélkül **nem javasolt**.

## 4. Mit várunk az audittól?

A fejlesztői kód a Web UI-ban a **Naplóellenőrzés** oldalon számokat és
azonosítókat mutat, nem szöveges beszélgetéstartalmat. A hiányos rekordokat
három egymást kizáró kategóriába sorolja:

1. feldolgozatlan (védelem);
2. tartós emlék forrása (védelem);
3. feldolgozott és közvetlen emlékhivatkozás nélküli (felülvizsgálat).

A három darabszám összegének egyeznie kell az üres asszisztensválaszú
sorok összesített számával.

## 5. Továbbhaladás kapuja

Tényleges adattisztítás kizárólag mentés-visszaállítási próba,
élő audit, a pontos rekord-ID-k felülvizsgálata és külön megerősítés után.

**Ne küldd el nyilvánosan** a mentés fájlját, `recall.key` tartalmát,
API-kulcsot, belső tokent vagy teljes beszélgetésnaplót.
