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
- Az Ingress Web UI alapvető diagnosztikai oldalai olvasásra szolgálnak; a külön **Kézi karbantartás** oldalon jelszóval védett, egyenként jóváhagyott archiválás és memória-összevonás, valamint visszavonás érhető el.
- Naptárhoz a [frissített, külön éles tesztelendő Google Calendar script példát](https://github.com/hollosipeti/nabu-recall/tree/main/examples) külön kell konfigurálni. **Év nélküli dátumot `MM-DD` formátumban adj át; az évet a HA számolja. Hangos naptáresemény-törlés még nincs.**

## English quick start

Install the HAOS app **and** the separate custom integration. Configure the OpenAI API key, bridge token, and distinct dashboard password. Update the integration files separately and restart Home Assistant Core. The web session lasts 10 minutes. The SQLCipher database and its key must be backed up together. See the [complete English manual](https://github.com/hollosipeti/nabu-recall/blob/main/MANUAL_EN.md).

## Biztonságos naplókarbantartás (fejlesztői ág)

A napló biztonságos, kézzel jóváhagyott archiválásának és visszavonásának ellenőrzőlistája: [biztonsági mentés és naplótisztítás](../docs/SAFE_CLEANUP_HU.md). Az alkalmazásban a teljes adatbázis és a külön titkosítási kulcs együtt szükséges; a puszta élő SQLite-fájl másolása nem elég. A diagnosztikai előnézet nem módosít adatot, csak a külön karbantartási oldal végezhet kézzel jóváhagyott módosítást.

## Kézi karbantartás — 1.0.4

Az **OPEN WEB UI → Kézi karbantartás** oldalon a hiányos, feldolgozott és tartós emlék forrásaként nem hivatkozott naplók titkosított archiválása engedélyezhető, majd az archívum visszaállítható (ha a sorok nem jártak le és nincs azonosítóütközés). Az archívumra is vonatkozik a 45 napos eredeti adatmegőrzés. A tartós emlékek AI-alapú optimalizálása csak javaslatokat készít; minden módosítás külön jóváhagyandó, és visszavonási lehetőséget ad. A visszavonási előzmények hét napig maradnak. **Művelet előtt készíts ellenőrzött Home Assistant biztonsági mentést az alkalmazás adatairól.**

## HAOS v1.0.5 — nagy tartós memóriatáblák

A lekérdezés nem csak az utolsó 200 tartós emléket vizsgálja: a teljes titkosított állományban keres, és a megfelelő találatokat adja át az AI-nak. A külön karbantartási lapon a gyors **Teljes állomány duplikátumjelöltjei** és a lapozható **Következő adag szemantikai AI-elemzése** is elérhető. A találatok csak javaslatok, az összevonáshoz továbbra is kézi jóváhagyás szükséges. A szemantikailag eltérő megfogalmazások teljes körű feltárására nincs garancia; az AI-feldolgozás kötegekben történik.
