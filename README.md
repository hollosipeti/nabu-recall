# 🧠 Nabu Recall v1.0.0

**Egyszerű, AI-alapú beszélgetési memória a Home Assistant magyar hangasszisztenséhez.**

A teljes felhasználó–asszisztens párbeszédet szó szerint megőrzi egy **45 napos forgó SQLite-naplóban**. Az OpenAI API kiválasztja a tartós tényeket és visszakeresi a kérdéshez releváns korábbi párbeszédeket. A régi OpenAI Conversation agent és az eszközvezérlés megmarad; a memóriahiba nem akadályozhatja a válaszadást.

### Újdonság v0.2.0
- **Home Assistant Ingress diagnosztika:** napló, feldolgozatlan bejegyzések, tartós emlékek, utolsó keresés eredete.
- Automatikus 45 napos törlés és naplózott feldolgozási állapot; nincs archívum.
- Home Assistant alkalmazásboltban ikon és logó; amd64 és aarch64 támogatás.
- Magyar clean install és frissítési útmutató, könnyű HA-integráció-telepítő.

**Telepítés:** [TELEPITES_HU.md](TELEPITES_HU.md) · **Kiadási jegyzetek:** [nabu_recall/CHANGELOG.md](nabu_recall/CHANGELOG.md)

A HAOS alkalmazás és a külön Home Assistant custom integration **egyaránt szükséges**. Az OpenAI API kulcs csak az alkalmazás beállításában szerepelhet, a `bridge_token` belső kapcsolat hitelesítésére szolgál.

> **Kísérleti kiadás:** Home Assistant 2026.11 alatt a 0.1.2 memória-visszakeresése felhasználói tesztben működött; a 0.2.0 új diagnosztikája még HAOS-on ellenőrizendő. A v0.3.2 kiadástól a teljes SQLite fájl SQLCipherrel titkosított. Ne nyisd a 8765/8766 portot LAN-ra, és ne tedd GitHubra a kulcsokat.

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

### 0.3.0 – mélyebb regressziótesztelés

Kiterjesztett offline tesztek a HTTP bridge API-ra (mock AI), hitelesítésre, elutasított tömeges törlésre, sikeresen visszaigazolt SQLite mentés/javítás/törlésre, hibaágakra és ugyanazon beszélgetés közvetlen kontextusára. A kódellenőrzés nem bizonyítja, hogy az élő OpenAI modell minden természetes megfogalmazást mindig helyesen értelmez; a HAOS + HUN Assist integrációt külön kell ellenőrizni.

### 0.3.1 – tesztkörnyezet javítása

A HTTP integrációs tesztek a szerver importja előtt izolált ideiglenes DB_PATH értéket kapnak; így nem írnak a HAOS alkalmazás /data könyvtárába.

### 0.3.2 – titkosított SQLite, funkcionális változás nélkül

**Az alkalmazás SQLite fájlja SQLCipher AES-256 titkosítást kap** (nem csak mezőszinten). A független, 32 bájtos véletlen kulcs automatikusan az alkalmazás privát `/data/recall.key` fájljában jön létre, 0600 jogosultsággal. Nem a `bridge_token` és nem kell új mezőt beállítani. A meglévő `recall.sqlite3` első induláskor ellenőrzött, ideiglenes titkosított másolatba migrál, adatszám-egyezőséget ellenőriz, majd atomikusan cserél; hibánál nem nyit üres adatbázist. A titkosítás nem változtatja meg a 45 napos lejáratot, a mentést vagy az AI-feldolgozást.

**Frissítés előtt kötelező teljes HAOS alkalmazásmentést készíteni.** Őrizd meg biztonságosan a `recall.key` fájlt is: ha elveszik, az emlékek többé nem olvashatók. A Home Assistant teljes biztonsági mentése a kulcsot is tartalmazhatja, ezért védd a mentéseket. A titkosítás nem védi meg az adatokat attól, aki a futó alkalmazáshoz és a kulcsfájlhoz is hozzáfér.

### 0.3.3 – SQLCipher migrációs tesztek

Fájlkezelési figyelmeztetés megszüntetve; külön tesztek a korábbi SQLite WAL üzemmódjáról és a sérült régi adatbázis megőrzéséről. A titkosítási algoritmus és a memóriafunkciók változatlanok.

### 0.3.4 – TAJ-adatokkal kapcsolatos hibás beszédválasz javítása

Az alaprendszer továbbra is kezelheti a felhasználó által megadott személyes azonosítókat; az integráció most egyértelműen tiltja a hamis „TAJ-számokat nem tudok kezelni” állítást. Kifejezett visszakérdezésnél a kiválasztott, megfelelő személyhez tartozó emléket használhatja, találgatás nélkül; beszédfelismerési félrehallás esetén a kontextust veszi figyelembe. Egy TAJ-szám puszta bemondása továbbra sem jelent automatikus, tartós tárolási engedélyt; explicit kérésre menthető, vagy a 45 napos naplóból visszakereshető. A jelenlegi SQLCipher titkosítási állapotot a háttér AI-utasítás is helyesen írja le. A kulcs, adatbázisséma, 45 napos lejárat és a többi memóriafunkció változatlan.

### 0.3.6 – Naptárparancsok és UI verzió

A „mentsd el a naptárba” típusú mondatok nem memóriamentések: változtatás nélkül átmennek a beállított Home Assistant beszélgetőügynökhöz, amely csak ténylegesen elérhető naptáríró eszközzel tudja végrehajtani őket. A memória továbbra is tudja, melyik a megjegyzett alapértelmezett naptár; ez önmagában nem hoz létre eseményt és nem ad az ügynöknek naptárírási jogosultságot. A Web UI a futó alkalmazás aktuális verzióját mutatja.


### 1.0.0 – Első hivatalos kiadás

A Web UI-ban a **Memória és tárhely** fül a tartós emlékek és naplóbejegyzések számát, valamint az adatbázis és kísérő WAL/SHM fájlok tényleges méretét és az adatpartíció szabad helyét mutatja. Az emlékeknek **nincs 200 darabos tárolási limitje**; ez csak az AI-hívásba bevont tételek száma.

**Fontos új beállítás:** a Nabu Recall alkalmazás **Konfiguráció / dashboard_password** mezőjében adj meg külön, erős jelszót, majd indítsd újra az alkalmazást. Amíg nincs jelszó, a Web UI **zárolva marad**, de a memória és az eredeti hangasszisztens működése nem áll le. Bejelentkezés után 8 órás webes munkamenet keletkezik, amely az alkalmazás újraindításakor lejár. A panel megnyitásához továbbra is HA-bejelentkezés szükséges. Az alkalmazás portjait továbbra se nyisd ki a hálózatra.

**Frissítés előtt:** készíts teljes HAOS-alkalmazásmentést a titkosított adatbázissal **és a `recall.key` fájllal együtt**. Az adatbázis és a titkosítás működésén ez a kiadás nem változtat.
