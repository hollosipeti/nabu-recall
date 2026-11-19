# 🧠 Nabu Recall v0.2.9

**Egyszerű, AI-alapú beszélgetési memória a Home Assistant magyar hangasszisztenséhez.**

A teljes felhasználó–asszisztens párbeszédet szó szerint megőrzi egy **45 napos forgó SQLite-naplóban**. Az OpenAI API kiválasztja a tartós tényeket és visszakeresi a kérdéshez releváns korábbi párbeszédeket. A régi OpenAI Conversation agent és az eszközvezérlés megmarad; a memóriahiba nem akadályozhatja a válaszadást.

### Újdonság v0.2.0
- **Home Assistant Ingress diagnosztika:** napló, feldolgozatlan bejegyzések, tartós emlékek, utolsó keresés eredete.
- Automatikus 45 napos törlés és naplózott feldolgozási állapot; nincs archívum.
- Home Assistant alkalmazásboltban ikon és logó; amd64 és aarch64 támogatás.
- Magyar clean install és frissítési útmutató, könnyű HA-integráció-telepítő.

**Telepítés:** [TELEPITES_HU.md](TELEPITES_HU.md) · **Kiadási jegyzetek:** [nabu_recall/CHANGELOG.md](nabu_recall/CHANGELOG.md)

A HAOS alkalmazás és a külön Home Assistant custom integration **egyaránt szükséges**. Az OpenAI API kulcs csak az alkalmazás beállításában szerepelhet, a `bridge_token` belső kapcsolat hitelesítésére szolgál.

> **Kísérleti kiadás:** Home Assistant 2026.11 alatt a 0.1.2 memória-visszakeresése felhasználói tesztben működött; a 0.2.0 új diagnosztikája még HAOS-on ellenőrizendő. A helyi SQLite nincs titkosítva. Ne nyisd a 8765/8766 portot LAN-ra, és ne tedd GitHubra a kulcsokat.

License: MIT.

### 0.2.1 – személyes adatok kezelése

- A személyes adatok megbeszélése nincs általánosan tiltva; a modell nem állíthatja tévesen, hogy telefonszámot egyáltalán nem képes kezelni.
- Kifejezetten kért telefonszám tartós memóriába kerülhet az AI döntésével. Ezt a megőrzést csak megbízható, hozzáférés-védett környezetben használd.
- TAJ-szám, egészségügyi azonosító és más kiemelten érzékeny azonosító **nem kerül automatikusan a tartós tárba**, mivel az adatbázis továbbra is titkosítatlan.
- **Fontos:** a 45 napos szó szerinti napló minden feldolgozott beszélgetést tartalmazhat, így az ilyen beírt vagy bemondott azonosítókat is. Ne használj valódi TAJ-számot próbához.
- A meglévő bejegyzések nem törlődnek ezzel a frissítéssel; a tárolt adatokhoz hozzáférést a HAOS biztonságos helyi mentéseinek is korlátozniuk kell.

### 0.2.2 – kifejezetten engedélyezett azonosítók

Kifejezett **„jegyezd meg”** kérés esetén a telefonszám, személyi igazolványszám és TAJ-szám az AI által tartós memóriaként kezelhető. Automatikus kiválasztásuk tilos. Bankszámla/IBAN, bankkártya, kriptotárca, seed phrase, privát kulcs, jelszó, PIN és hozzáférési kulcs tartós tárolása továbbra is tilos. A 45 napos szó szerinti napló ezek említését is tartalmazhatja; az adatbázis titkosítatlan, és a közös háztartási asszisztens memóriáját az engedélyezett felhasználók lekérdezhetik. Az AI kiválasztása nem helyettesít hozzáférésvédelmet vagy titkosítást.

### 0.2.3 — törlésvédelem

A hangasszisztens **nem rendelkezik teljes memóriaürítési művelettel**. Az AI által javasolt törlések közül egy feldolgozási adagban legfeljebb egy ID-alapú művelet engedélyezhető, kizárólag egy konkrét, kifejezett felhasználói törlési kéréssel. A teljes, összes, mindent törlő vagy reset jellegű kérések nem engedélyeznek memóriatörlést. A 45 napos automatikus lejárat ettől független. A napló és a tartós memória törlése továbbra sem kínál hangos „full clean” műveletet. A védelem nem alkalmas rosszindulatú rendszergazdai hozzáférés vagy az adatfájl kézi törlése ellen.

### 0.2.4 — ellenőrzött memóriaműveletek

A kifejezett „jegyezd meg”, „javítsd/módosítsd” és „töröld” kéréseket a HUN agent most már szinkron módban intézi: egyetlen AI-értelmezés, pontos célazonosító, SQLite-végrehajtás és csak ezután megerősített válasz. Nem ad hamis „nem tudok tárolni” visszajelzést egy sikeres műveletre. Teljes törlés továbbra is tiltott. A háttérnapló elmenti a párbeszédet, de nem futtatja újra ugyanazt a memóriamódosítást. A szokásos automatikus tartós tanulás változatlanul háttérben történik, és nem küld optimista mentési visszaigazolást.

### 0.2.5 – parancsfelismerési hotfix

Javítottuk a beszélgetőintegráció hibásan escape-elt reguláris kifejezését. A kifejezett „jegyezd meg”, „töröld”, „javítsuk” utasítások így beléphetnek a visszaigazolást kérő útvonalba. A normál kijelentésekre az alap beszélgetőügynöknek természetes visszajelzést kell adnia, és nem állíthatja, hogy semmilyen memóriát nem tud tárolni. A szinkron memóriamódosítás helyi, éles HAOS-tesztje továbbra is szükséges.

### 0.2.6 – magyar memóriaparancsok

Egységesítettük a magyar parancsfelismerést. A „Mentsd el”, „Jegyezd meg”, „Javítsd” és „Töröld” kifejezéseket a külön HA integráció a szinkron memóriakezelő API-nak továbbítja. A teljes tömeges törlés elleni korlát megmaradt. Az ugyanarról a háztartásról szóló emlékeket az AI nem keverheti össze a bevásárlólisták tulajdonosaival. A memóriát a HAOS add-on adatbázisa tárolja; frissítés előtt készíts biztonsági mentést.

### 0.2.7 – törlésvédelem hotfix

A „Töröld minden emlékemet” parancsot a szerver már biztosan tömeges törlési kísérletként ismeri fel. A v0.2.6 automatikus tesztje e hiányzó szóalak miatt sikertelen volt; javítva.

### 0.2.8 – kontextusos rövid parancsok és regressziótesztek

A „Mentsd el!” típusú rövid utasítás legfeljebb 5 percen belüli, **azonos beszélgetésből** származó előző felhasználói kijelentést használhatja. Másik beszélgetésből és a segéd válaszából nem találhat ki tényt. A kifejezett javítások változatlanul egyedi, ellenőrzött műveletek. A háttér AI-feldolgozás minden új naplózás után, és 15 percenként újrapróbálva fut; **nem napi egyszeri ütemezésű**. A 45 napos lejárat ettől független.

### 0.2.9 – tesztjavítás

Javítottuk az új adatalapú regresszióteszt Python literáljait. Az elliptikus „Mentsd el!” most csak a legközelebbi, azonos beszélgetésbeli felhasználói mondatot használhatja; kihagyott vagy lejárt köztes forduló esetén nem ugrik régebbi témára.
