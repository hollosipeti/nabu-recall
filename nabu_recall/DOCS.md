# Nabu Recall 2.0.1 — Home Assistant alkalmazás

Az alkalmazás **2.0.1**. A GitHub `main` ágáról a HA-integráció **2.0.0** telepíthető; a külön átadott **2.0.2** naptárjavítás ugyanezzel a 2.0.1-es APP-pal működik. A meglévő `nabu_recall` alkalmazást kell frissíteni, nem új alkalmazást létrehozni. Az APP és az integráció frissítése külön történik.

- [Teljes magyar telepítési és frissítési útmutató](https://github.com/hollosipeti/nabu-recall/blob/main/README.md)
- [Az összes OpenAI-utasítás tényleges forrásfájlja és helye](https://github.com/hollosipeti/nabu-recall/blob/main/NABU_RECALL_PROMPT.md)
- [Családi használati útmutató](https://github.com/hollosipeti/nabu-recall/blob/main/CSALADI_UTMUTATO.md)
- [Biztonsági mentés és karbantartás](https://github.com/hollosipeti/nabu-recall/blob/main/docs/SAFE_CLEANUP_HU.md)
- [Kiadási változások](https://github.com/hollosipeti/nabu-recall/blob/main/nabu_recall/CHANGELOG.md)

## Biztonságos frissítés

1. Készíts és ellenőrizz teljes Home Assistant-mentést, benne a Nabu Recall alkalmazással, annak adataival és az integráció konfigurációjával.
2. Ha az APP régebbi, frissítsd a meglévő Nabu Recall alkalmazást 2.0.1-re.
3. Az integrációt csak akkor frissítsd, ha a kívánt új verzió ténylegesen elérhető. A repó [`install_integration.sh`](https://github.com/hollosipeti/nabu-recall/blob/main/install_integration.sh) telepítője jelenleg 2.0.0-t telepít; ha már a külön 2.0.2-es naptárjavítást használod, ne írd felül ezzel. Integrációfrissítés után indítsd újra a HA Core-t. Az APP frissítése önmagában nem igényel integrációfrissítést.
4. Ellenőrizd a két verziószámot, a tartós memóriát, a forgó memória kezelését, az Assist-eszközvezérlést és a naptárat, ha beállítottad.

A titkosított adatbázis és kulcsa az alkalmazás saját `/data/recall.sqlite3` és `/data/recall.key` fájljában van. Ezeket együtt kell biztonságosan menteni. A 45 napos napló és a tartós emlékek változatlan formában maradnak; **nem kell és nem szabad új adatbázist létrehozni**.

## Újdonság a 2.0.1-es alkalmazásban

**Forgó memória – kézi, végleges törlés:** Web UI → Memóriakezelés → Forgó memória. Kereshető, dátumra szűrhető és lapozható lista, minden bejegyzésnél jelölőnégyzettel. A rendszer semmit nem választ ki és nem töröl automatikusan; a felhasználó kiválaszt legfeljebb 40 törölhető, feldolgozott bejegyzést, átnézi a teljes előnézetet, majd külön jelöléssel és megerősítéssel végleg törli azokat.

Ez **nem archiválás**; nincs visszavonás a felületen, a tartós emlékhez forrásként kötött vagy még feldolgozatlan naplók védettek. A régi mentések továbbra is őrizhetik a törölt szövegeket. A biztonságos teljes HA-mentés a törlés előtt kötelező elővigyázatosság.

## Képességek

- 45 napig tárolt, szó szerinti beszélgetési napló, amelyből kérésre visszakeres.
- AI által kezelt tartós emlékek, külön explicit mentés, módosítás és célzott törlés.
- Védett Web UI a megtekintéshez, karbantartási előnézethez, jóváhagyott műveletekhez és visszavonáshoz.
- Opcionális integrált HA naptárlekérdezés és eseménylétrehozás, külön YAML-szkriptek nélkül. A külön 2.0.2-es HA-integráció javítja a magyar dátum- és időkezelést, és támogatja a tetszőleges dátumtartományt, a név szerinti keresést, az egész napos, többnapos és éjfélen átnyúló eseményeket. Naptári eseménytörlés és -módosítás nem támogatott. A verziónkénti képességeket a [teljes útmutató naptárszakasza](https://github.com/hollosipeti/nabu-recall/blob/main/README.md#10-opcionális-beépített-naptár) részletezi.
- Az eredeti OpenAI Conversation ügynök továbbra is végrehajtja a HA eszközvezérlést.

## AI-utasítások

A Nabu Recall saját OpenAI-utasításai **csak a repóban vannak**, az alkalmazás/integráció telepített kódjából töltődnek be. A felhasználó saját OpenAI Conversation Instructions mezője érintetlen marad.

Az aktív források: `custom_components/nabu_recall/repo_instructions.py`, `custom_components/nabu_recall/llm.py` és `nabu_recall/ai.py`. A fenti [OpenAI-utasítástérkép](https://github.com/hollosipeti/nabu-recall/blob/main/NABU_RECALL_PROMPT.md) megmutatja az egyes függvényeket és a telepített fájlok helyét. A régi kézzel bemásolandó naptár- és Nabu-memóriapromptok már nem szükségesek.

## Elérési és adatvédelmi alapok

A Nabu Recall privát bridge szolgáltatása a 8765-ös, az Ingress UI a 8766-os portot használja. Ezeket nem kell a külső hálózatra publikálni. A HA integrációhoz a működő upstream OpenAI Conversation ügynököt válaszd, a Voice Assistban pedig a „Nabu Recall – memória” ügynököt. Az OpenAI API használata külön díjazású.

## Korábbi verziók

A régi kiadások dokumentációja és a kézi naptárszkript-példák a Git-előzményből visszakereshetők, **de a jelenlegi telepítéshez nem tartoznak**. A visszaállítás előtti állapot külön `stable-2026-11-24-before-v2` ágon is rögzítve van.
