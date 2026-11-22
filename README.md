# 🧠 Nabu Recall — 1.1.2 (HAOS alkalmazás) / 1.0.4 (HA-integráció)

**Magyar nyelvű, AI-alapú tartós beszélgetési memória Home Assistant Assist mellé.** A meglévő OpenAI Conversation ügynök eszközvezérlését megtartja; a Nabu Recall kiegészíti történeti visszakereséssel és tartós emlékekkel.

## Dokumentáció

- **[Magyar telepítési és használati útmutató](TELEPITES_HU.md)** — lépések, használat és hibaelhárítás.
- **[Angol telepítési és használati útmutató](MANUAL_EN.md)** — telepítés, használat és hibaelhárítás angolul.
- **[Családi útmutató](CSALADI_UTMUTATO.md)** — példák mindennapi használatra.
- **[Nabu Recall rendszerutasítás-minta](NABU_RECALL_PROMPT.md)** — opcionális, kizárólag memóriával kapcsolatos, személyes adatokat nem tartalmazó utasításminta.
- **[Google Naptár-példa](examples/README.md)** — külön telepítendő naptárszkript.
- **[Változásnapló](nabu_recall/CHANGELOG.md)** és [fejlesztési történet](HISTORY.md).

**Fontos:** A beszélgetésmemória az asszisztenst használók között közös. **Ne taníts be neki fontos, érzékeny személyes információkat**, például jelszavakat, hozzáférési kulcsokat, pénzügyi vagy személyazonosító adatokat. A memóriaműveletek OpenAI API-feldolgozást is igénybe vesznek.

## Felépítés és működés

A Nabu Recall két külön összetevőből áll:

- **HAOS alkalmazás (`nabu_recall/`):** az emlékek tárolását és feldolgozását végzi. SQLCipherrel titkosított SQLite-adatbázist, belső kapcsolati szolgáltatást és jelszóval védett Web UI kezelőfelületet tartalmaz.
- **Home Assistant-integráció (`custom_components/nabu_recall/`):** a meglévő OpenAI Conversation beszélgetési ügynökhöz kapcsolódik, így a megszokott eszközvezérlés megmarad, és az asszisztens a korábbi emlékeket is felhasználhatja.

**A két összetevőt külön kell telepíteni és frissíteni.**

- A beszélgetésnapló **45 napig** őrzi meg a párbeszédeket; a tartós emlékek nem járnak le automatikusan.
- A belső kapcsolat tokennel védett (8765-ös port); a Web UI a Home Assistanton keresztül érhető el (8766-os port), külön jelszóval. Egyik portot se tedd közvetlenül elérhetővé az internet felől.
- A Web UI-ba történő bejelentkezés **10 percig** érvényes.
- Az alkalmazás mentésekor a titkosított adatbázis és a hozzá tartozó kulcs együttes megőrzése szükséges.

  
A Google Naptár kezelése külön Home Assistant-funkció. A példaként mellékelt szkripttel eseményt lehet létrehozni; hangutasításos eseménytörlés jelenleg nincs beépítve.

## Telepítés és frissítés

A részletes lépésekhez kövesd a [magyar](TELEPITES_HU.md) vagy az [angol](MANUAL_EN.md) útmutatót. **Telepítés vagy frissítés előtt készíts Home Assistant-alkalmazásmentést.**

## Karbantartás

A Nabu Recall jelenlegi HAOS alkalmazása **1.1.2**, a Home Assistant-integráció **1.0.4**. Az alkalmazás és az integráció külön frissül. A memóriák a HAOS alkalmazás adatkönyvtárában vannak; frissítés előtt készíts alkalmazásmentést.

A részletes korábbi fejlesztési eredmények és karbantartási mechanizmusok a [változásnaplóban](nabu_recall/CHANGELOG.md), a [HISTORY.md](HISTORY.md) és a [biztonságos karbantartási leírásban](docs/SAFE_CLEANUP_HU.md) találhatók.

Licenc: MIT.
