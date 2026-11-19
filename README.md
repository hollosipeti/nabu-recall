# 🧠 Nabu Recall v0.2.0

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
