# Nabu Recall — stabilizációs fejlesztési ág (2026-11-21)

## Cél
A HAOS 1.0.6 / Home Assistant integráció 1.0.4 stabil alapjának megőrzése mellett gyorsabb, megbízhatóbb és rugalmasabb memória. Nem építünk új szabályrendszert minden beszédforduló köré.

## Most elkészült a fejlesztői ágon
- A tartós emlékek keresése a magyar ékezetes és ékezet nélkül felismert formák között is talál egyezést (pl. `műhelyben` ↔ `muhelyben`, `áramszünet` ↔ `aramszunet`). A pontos ékezetes egyezés a rangsorolásban előnyt élvez. A tárolt tényeket nem módosítjuk.
- A háttérmemória feldolgozásának indítását nem hagyjuk el pusztán azért, mert egy másik memóriaművelet fogja a zárat. A munkák sorban futnak.
- Hozzáadott regressziós tesztek a magyar kereséshez.

## Megőrzött működés
- 45 napos szó szerinti napló, időkorlát nélküli tartós emlékek.
- SQLCipher adatbázis és külön kulcs, azonos adatséma.
- Meglévő HUN OpenAI Conversation agent, eszközvezérlés és naptárútvonal.
- Csak a felhasználó által jóváhagyott kézi memóriakarbantartás.
- Meglévő személyesadat- és azonosítókezelési viselkedés: **ebben a fejlesztési ütemben nem változik**.

## Ellenőrzés éles telepítés előtt
1. A teljes pytest csomag és a HAOS integráció végponttól végpontig tesztelése.
2. Ékezetes/ékezet nélküli keresés, pontos találat előresorolása, sok emlék.
3. Egyidejű memória-módosítás és új naplóbejegyzés feldolgozása.
4. OpenAI kiesés, újrapróbálás, az eszközvezérlés függetlensége.
5. Mentés és visszaállítás próbája (recall.sqlite3 + recall.key).
6. Éles verziószámot csak sikeres ellenőrzés után növeljünk.

## Külön későbbi mérföldkő
Az érzékeny azonosítók hangos visszaolvasásának hozzáférés-kezelését a felhasználó kérésére külön főverziós tervezés és dokumentáció előzi meg. Ez nem része ennek az ágnak.
