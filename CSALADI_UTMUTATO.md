# Nabu Recall — családi használati útmutató

**Home Assistant Assist + Nabu Recall 1.1.1**

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
- **A memória nem naptár:** a naptárkezelés külön Home Assistant-eszközökkel történik; hangos naptáresemény-törlés ebben a verzióban nincs megvalósítva.

## Háromperces családi próba

1. „Jegyezd meg, hogy a próbadobozban három kék ceruza van.”
2. Egy új beszélgetésben: „Hány ceruza van a próbadobozban, és milyen színűek?”
3. „Javítsd: a próbadobozban most négy piros ceruza van.”
4. „Most hány ceruza van a próbadobozban?”
5. Végül töröld pontosan ezt az egy tesztemléket, majd ellenőrizd a Tartós emlékek felületen, hogy eltűnt.

Az elvárt válasz előbb három kék, majd négy piros ceruza. A régi állapotot nem szabad aktuálisnak mondania.

## A családi rendszergazdának

A Nabu Recall Web UI-ján ellenőrizhetők a tartós emlékek, a 45 napos napló és a karbantartási javaslatok. Az archiválás és memóriaösszevonás jóváhagyást igényel; a Web UI jelszóval védett. Módosítás előtt a titkosított adatbázist és a külön kulcsot **együtt** kell biztonságosan menteni.
