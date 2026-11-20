# Nabu Recall — Home Assistant alkalmazás

**Magyar részletes útmutató:** [TELEPITES_HU.md](https://github.com/hollosipeti/nabu-recall/blob/main/TELEPITES_HU.md)

**Complete English documentation:** [MANUAL_EN.md](https://github.com/hollosipeti/nabu-recall/blob/main/MANUAL_EN.md)

## Telepítés röviden

1. A Home Assistant alkalmazásbolthoz add hozzá a `https://github.com/hollosipeti/nabu-recall` adattárat, majd telepítsd a Nabu Recall alkalmazást.
2. Konfiguráció: `openai_api_key` (külön OpenAI API-kulcs), `openai_model` (alap: `gpt-4.1-mini`), `bridge_token` (legalább 32 karakter), `dashboard_password` (külön erős Web UI-jelszó).
3. Indítsd el az alkalmazást. Az **OPEN WEB UI** az Ingress diagnosztikát nyitja meg; a HA-belépés mellett külön jelszó is kell. A munkamenet a belépéstől számított **10 perc** után lejár. Jelszó nélkül a felület zárolt.
4. Telepítsd **külön** a `custom_components/nabu_recall` integrációt a HA `/config/custom_components/` könyvtárába. A telepítő parancsát a részletes kézikönyvben találod. Indítsd újra a **Home Assistant Core-t**.
5. Az új Nabu Recall integrációnál válaszd ki a meglévő OpenAI Conversation HUN ügynököt, add meg a helyes belső app URL-t és a `bridge_token` értéket. Az Assistban válaszd a „Nabu Recall – memória” ügynököt.

## Mire figyelj?

- A napló **45 nap után lejár**; a tartós emlékek nem járnak le automatikusan.
- A teljes SQLite fájl **SQLCipherrel titkosított**, kulcsa az alkalmazás saját `/data/recall.key` fájljában van. **Mindkét fájlt együtt mentsd!**
- Az alkalmazás saját `/data` könyvtára **nem** a HA `/config` mappája. Frissítésnél ne töröld vagy telepítsd újra az alkalmazást biztonsági mentés nélkül.
- A 8765-ös bridge és a 8766-os Ingress portot **ne publikáld** LAN-ra vagy WAN-ra.
- Az OpenAI API-hívások használatalapúan számlázottak, a ChatGPT-előfizetés ezt nem váltja ki.
- Az Ingress Web UI **csak olvasható**: emlékek, 45 napos napló, státusz, Memória és tárhely.
- Naptárhoz a [frissített, külön éles tesztelendő Google Calendar script példát](https://github.com/hollosipeti/nabu-recall/tree/main/examples) külön kell konfigurálni. **Év nélküli dátumot `MM-DD` formátumban adj át; az évet a HA számolja. Hangos naptáresemény-törlés még nincs.**

## English quick start

Install the HAOS app **and** the separate custom integration. Configure the OpenAI API key, bridge token, and distinct dashboard password. Update the integration files separately and restart Home Assistant Core. The web session lasts 10 minutes. The SQLCipher database and its key must be backed up together. See the [complete English manual](https://github.com/hollosipeti/nabu-recall/blob/main/MANUAL_EN.md).
