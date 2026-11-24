# Nabu Recall — családi használati útmutató

## Mi ez?

A Nabu Recall a Home Assistant hangasszisztensének **emlékezete**. Az asszisztens továbbra is képes a Home Assistantban elérhető eszközök vezérlésére, de korábbi beszélgetésekből is visszakereshet információkat, és fontos tényeket tartósan megjegyezhet. A meglévő OpenAI Conversation ügynököt egészíti ki, nem helyettesíti.

Nem kerül automatikusan minden mondat a tartós memóriába: az AI választja ki a később is hasznos tényeket. **Ha valamit biztosan szeretnél elmenteni, mondd ki, hogy „Jegyezd meg…”, és ellenőrizd a mentés megerősítését.**

## Példák — mit mondj neki?

| Helyzet | Példamondat |
| --- | --- |
| Fontos tény mentése | „Jegyezd meg, hogy a tartalék elemek a kamra felső polcán vannak.” |
| Visszakérdezés | „Hol vannak a tartalék elemek?” |
| Személyhez kötött információ | „Jegyezd meg, hogy Anna kedvenc teája a citromos tea.” |
| Változás bejelentése | „Javítsd: Anna már a gyömbérteát szereti legjobban.” |
| Egyetlen emlék törlése | „Töröld azt az emléket, hogy Anna kedvenc teája a gyömbértea.” |
| Korábbi beszélgetés felidézése | „Mit beszéltünk korábban a műhelyben lévő szerszámokról?” |
| Otthonvezérlés | „Kapcsold le a nappaliban a lámpát.” |

A példák nem garantált, szó szerint felismerendő parancsok. A válasz függ a korábbi adatoktól, a beszédfelismeréstől és a Home Assistant beállításaitól.

## Amit mindenkinek érdemes tudnia

- **45 napos napló:** a szó szerinti párbeszédek 45 nap után lejárnak. **Tartós memória:** a kiválasztott tényeknek nincs automatikus lejárata.
- **Nem mindentudó:** ha valamit nem mondtatok el, nem kellene tényként kitalálnia.
- **Számít, kié az információ:** „Anna autója” nem ugyanaz, mint „András autója”. A személyt érdemes kimondani.
- **Számít a változás:** „Vettem még egy biciklit” két biciklit jelenthet; „Lecseréltem a biciklimet” a korábbi adat módosulását jelenti.
- **A háttérfeldolgozás nem mindig azonnali:** hétköznapi beszélgetésekből később is keletkezhet tartós emlék. A kifejezett mentés külön visszaigazolást ad.
- **Közös háztartási memória:** a rendszer nem tudja biztosan felismerni, hogy ki beszél. Az ugyanazt az asszisztenst használók közös emlékeket kérdezhetnek le.
- Az érzékeny azonosítók hangos kezelését ez a verzió nem védi beszélőazonosítással.
- **A memória nem naptár:** a naptárkezelés külön, opcionális funkció. Csak akkor érhető el, ha a rendszergazda kiválasztott egy naptárt a Nabu Recall integráció beállításainál. A naptáresemények törlését és módosítását a naptár saját felületén kell elvégezni.

## Naptár használata

| Mit szeretnél? | Példamondat |
| --- | --- |
| Mai programok | „Mi van mára a naptáramban?” |
| Hétvégi programok | „Van valami programom a hétvégén?” |
| Új esemény | „Írd be a naptáramba, hogy holnap délután háromtól négyig megbeszélésem lesz.” |
| Jövő heti programok | „Milyen programjaim lesznek jövő héten?” |
| Keresés név szerint | „Mikor megyek fogorvoshoz?” |
| Egész napos esemény | „December 6-án egész nap szabadságon leszek. Írd be a naptáramba!” |
| Többnapos esemény | „December 11-től 14-ig szabadságon leszek. Írd be a naptáramba!” |

A jövő heti, név szerinti, egész napos és többnapos példákhoz a külön 2.0.2-es naptárjavítás szükséges. A pontos verzióállapotot a [telepítési útmutató](README.md) tartalmazza. Fontos időpontnál ne csak az asszisztens válaszát, hanem a tényleges naptárbejegyzést is ellenőrizd.

## Háromperces családi próba

1. „Jegyezd meg, hogy a próbadobozban három kék ceruza van.”
2. Egy új beszélgetésben: „Hány ceruza van a próbadobozban, és milyen színűek?”
3. „Javítsd: a próbadobozban most négy piros ceruza van.”
4. „Most hány ceruza van a próbadobozban?”
5. Végül töröld pontosan ezt az egy tesztemléket, majd ellenőrizd a Tartós emlékek felületen, hogy eltűnt.

Az elvárt válasz előbb három kék, majd négy piros ceruza. A régi állapotot nem szabad aktuálisnak mondania.

## A családi rendszergazdának

A jelszóval védett Nabu Recall Web UI-ján ellenőrizhetők a tartós emlékek, a 45 napos napló és a karbantartási javaslatok. Az archiválás és a memóriaösszevonás jóváhagyást igényel.

A 2.0.1-es APP-ban a **Memóriakezelés → Forgó memória** oldalon külön beszélgetéseket kézzel, előnézet és megerősítés után végleg törölhetsz. Ez nem ugyanaz, mint a tartós emlék törlése vagy a visszaállítható archiválás. A végleges törlés nem vonható vissza a felületen.

Módosítás előtt a titkosított adatbázist és a külön kulcsot **együtt** kell biztonságosan menteni. Lásd a [biztonsági mentési és karbantartási útmutatót](docs/SAFE_CLEANUP_HU.md).
