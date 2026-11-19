# 🧠 Nabu Recall v0.2.1 — tiszta telepítés és frissítés

## 0. Fontos előfeltételek

- Home Assistant OS vagy Supervised, alkalmazásbolt hozzáféréssel; az eredeti **OpenAI Conversation HUN** működjön.
- Saját OpenAI API-kulcs, aktív API-számlázás. A ChatGPT előfizetés ettől különbözik.
- A Nabu Recall **külön HAOS alkalmazásból és külön custom integrationből** áll.
- Az eredeti Nabu Memory / Next appokat és memóriás MCP-eszközeiket állítsd le/tiltsd le, de az OpenAI Conversation ügynököt ne töröld.
- Frissítésnél az app `/data` adatbázisát **ne töröld**; eltávolítás/újratelepítés előtt legyen HAOS biztonsági mentés.

## 1. Új telepítés – HAOS alkalmazás

1. HA → **Beállítások → Alkalmazások → Alkalmazásbolt → Adattárak**: add hozzá:
   `https://github.com/hollosipeti/nabu-recall`
2. Frissítsd az alkalmazásboltot, keresd a **Nabu Recall** alkalmazást, és telepítsd.
3. Állítsd be az alábbiakat az alkalmazás Konfiguráció lapján:
   - `openai_api_key`: az OpenAI Platformon létrehozott **új vagy már ismert** API-kulcs.
   - `openai_model`: alapérték `gpt-4.1-mini`; ne változtasd az első teszt előtt.
   - `bridge_token`: legalább 32 véletlenszerű karakter. Például HA Terminal: `openssl rand -hex 32`.
4. Indítsd el a Nabu Recall alkalmazást. A **Open Web UI / Webes felület** gomb megnyitja a beépített állapotlapot.
5. **Ne állíts be porttovábbítást:** a 8765 belső bridge és a 8766 ingress port nincs LAN-ra publikálva.

## 2. Külön Home Assistant-integráció

A HACS önmagában jelenleg **nem** telepíti automatikusan ezt a vegyes (alkalmazás + integráció) repót.

Az integráció telepítése kézzel:

1. Nyisd meg a GitHub `custom_components/nabu_recall` könyvtárát.
2. Másold a teljes mappát a Home Assistant `/config/custom_components/nabu_recall` alá. A `manifest.json` közvetlenül ebben a mappában legyen.
3. **Indítsd újra a Home Assistant Core-t**.
4. Beállítások → Eszközök és szolgáltatások → Integráció hozzáadása → **Nabu Recall**.
5. Válaszd ki a **meglévő OpenAI Conversation HUN** `conversation.*` ügynököt.
6. `url`: a Nabu Recall app **tényleges belső neve**, így például `http://<repoazonosító>_nabu_recall:8765` (a pontos repoazonosító installációnként eltér).
7. `token`: pontosan ugyanaz a `bridge_token`, amely az app beállításában szerepel.
8. A ping ellenőrzés után a HUN Voice Assistant / Beszélgetőügynök mezőben válaszd a **Nabu Recall – memória** ügynököt.
9. Az eredeti OpenAI ügynök maradjon aktív. A régi memória-MCP eszközöket kapcsold ki.

**Terminálos kényelmi telepítő** (előbb tekintsd át a szkriptet):

```sh
curl -fsSL https://raw.githubusercontent.com/hollosipeti/nabu-recall/main/install_integration.sh -o /tmp/install_nabu_recall.sh
sh /tmp/install_nabu_recall.sh
```

A szkript a régi `custom_components/nabu_recall` mappát időbélyeges biztonsági másolatként őrzi meg. Nem telepíti és nem konfigurálja az alkalmazást.

## 3. Ellenőrzés — a memória valóban működik?

1. Indíts **új beszélgetést**. Mondd: „Jegyezd meg, hogy a tesztdoboz neve Boróka 812.”
2. Új Assist beszélgetésben kérdezd: „Mi a tesztdoboz neve?”
3. Másik, ugyanahhoz a HUN agenthez kapcsolt eszközön is próbáld ki.
4. Az alkalmazás **Web UI** felületén: a „45 napos napló” listában mindkét párbeszéd látszódjon.
5. „Tartós emlékek” alatt ellenőrizd, hogy a feldolgozó AI kivette-e a tartós tényt.
6. Az „Állapot” lapon az „Utolsó visszakeresés” megmutatja, mennyi rövid távú és tartós találatot adott az utolsó lekérdezés.
7. Ha `Feldolgozatlan > 0`, és nem csökken, ellenőrizd az app naplójában az `AI memory extraction failed` üzenetet.

**A helyes, friss beszélgetésből kapott válasz önmagában nem bizonyít tartós mentést:** ezért fontos a két külön lista.

## 4. Frissítés 0.1.2 → 0.2.0 (meglévő adatokkal)

1. Készíts Home Assistant biztonsági mentést az Nabu Recall alkalmazásról. **Ne töröld és ne telepítsd újra az appot**, mert adatvesztés történhet.
2. Alkalmazásbolt → adattárak frissítése → Nabu Recall **frissítés 0.2.0-ra**.
3. Indítsd újra az alkalmazást, és nyisd meg az új Web UI diagnosztikát.
4. Ha az integrációt is frissíted, futtasd újra a fenti telepítőt, majd indítsd újra a HA Core-t.
5. Nézd meg, hogy a naplóbejegyzések és tartós emlékek darabszáma megmaradt-e.

## 5. Adatvédelem és helyreállítás

- A napló **45 nap után automatikusan és véglegesen törlődik**. Nincs archívum, még feldolgozási hiba esetén sem; a nem kivont tény elveszhet.
- A hosszú távú `memories` tábla külön, lejárat nélkül megmarad.
- A beszélgetések helyben, **jelenleg titkosítatlan** SQLite-adatbázisban vannak. Az OpenAI API csak a feldolgozáshoz szükséges szövegeket kapja meg.
- **Minden helyszíni felhasználó közös memóriát használ**; nincs külön felhasználó-azonosítás.
- Ha az app nem elérhető, az eredeti OpenAI hangasszisztens eszközvezérlése tovább működik, de memoria nélkül.
- Eltávolítás előtt exportálj HAOS backupot. A `/data/recall.sqlite3` fájl a helyi naplót és tartós memóriát együtt tartalmazza.
- Ne írd be a titkos kulcsot vagy a bridge tokent a GitHubra vagy nyilvános naplóba.

## Személyes adatok — v0.2.1

A Nabu Recall nem tiltja általánosan a személyes adatok megbeszélését. Kifejezett felhasználói kérésre a telefonszám és a szokásos kapcsolatfelvételi preferenciák megjegyezhetők. A kiemelten érzékeny TAJ-szám és egészségügyi azonosítók nem kerülnek automatikusan a tartós tárba. A **45 napos szó szerinti naplóban azonban a bemondott adat ugyanúgy megjelenhet**, és a napló jelenleg nincs titkosítva. Éles azonosítószámot ne használj teszthez; a korábbi naplóbejegyzéseket a frissítés nem törli.
