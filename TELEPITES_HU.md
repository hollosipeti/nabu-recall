# Nabu Recall v0.1.0 – telepítés, fejlesztői verzió

**Ez az első fejlesztői kiadás; a HAOS alatti teljes működés még nincs igazolva.**

1. HA → Beállítások → Alkalmazások → Alkalmazásbolt → Adattárak: add hozzá a `https://github.com/hollosipeti/nabu-recall` repót.
2. Telepítsd a **Nabu Recall** alkalmazást. Add meg a saját OpenAI API-kulcsodat és egy legalább 32 karakteres **bridge_token** értéket (például: `openssl rand -hex 32`). A tokent nem szabad a GitHubba feltölteni. **Ne nyisd ki a 8765-ös portot a LAN felé.**
3. Másold a `custom_components/nabu_recall/` mappát a HA `/config/custom_components/nabu_recall/` mappájába, majd indítsd újra a Home Assistantot.
4. HA → Beállítások → Eszközök és szolgáltatások → Integráció hozzáadása → **Nabu Recall**. Válaszd ki a meglévő **HUN OpenAI Conversation** beszélgetőügynököt. Add meg a Nabu Recall alkalmazás tényleges belső `http://...:8765` címét és a bridge tokent. A belső hosztnév a HA által kiosztott repóazonosítótól függ.
5. HA → Beállítások → Hangasszisztensek → HUN: válaszd a **Nabu Recall – memória** beszélgetőügynököt. A régi ügynök maradjon meg! A korábbi memória-MCP-eszközöket távolítsd el az upstream ügynöktől a dupla feldolgozás elkerülésére. Az eszközvezérlés maradjon aktív.
6. Teszt: „Jegyezd meg, hogy a tesztitalom gyömbértea.” Majd: „Melyik italt mondtam?” Ha nem működik, az app és a HA integráció naplóit ellenőrizd.

## Fontos

- A szó szerinti napló **45 napig** él. Nincs archívum; a lejárt bejegyzés API-hiba esetén is törlődik.
- Minden sikeresen továbbított, lezárt párbeszéd mentésre kerül; nem figyeljük az egész HA rendszert.
- A SQLite-adatbázis ebben a változatban **nem titkosított**.
- Nincs még webes emlékkezelő.
- Az OpenAI API kiválasztja a releváns memóriákat; az egyszerű kereső szóalakokat időnként nem találja meg.
