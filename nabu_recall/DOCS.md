# Nabu Recall 2.0.0 — Home Assistant alkalmazás

Az alkalmazás és a Home Assistant-egyedi integráció **egyaránt 2.0.0**. A régi telepített `nabu_recall` alkalmazást kell frissíteni, nem új alkalmazást létrehozni.

- [Teljes magyar telepítési és frissítési útmutató](https://github.com/hollosipeti/nabu-recall/blob/main/README.md)
- [Az összes OpenAI-utasítás tényleges forrásfájlja és helye](https://github.com/hollosipeti/nabu-recall/blob/main/NABU_RECALL_PROMPT.md)
- [Családi használati útmutató](https://github.com/hollosipeti/nabu-recall/blob/main/CSALADI_UTMUTATO.md)
- [Biztonsági mentés és karbantartás](https://github.com/hollosipeti/nabu-recall/blob/main/docs/SAFE_CLEANUP_HU.md)
- [Kiadási változások](https://github.com/hollosipeti/nabu-recall/blob/main/nabu_recall/CHANGELOG.md)

## Biztonságos frissítés

1. Készíts és ellenőrizz teljes Home Assistant-mentést, benne a Nabu Recall alkalmazással és annak adataival.
2. Frissítsd a meglévő Nabu Recall alkalmazást 2.0.0-ra.
3. Frissítsd a Nabu Recall HA-integrációt a repó [`install_integration.sh`](https://github.com/hollosipeti/nabu-recall/blob/main/install_integration.sh) telepítőjével, majd indítsd újra a HA Core-t.
4. Ellenőrizd az alkalmazás és az integráció 2.0.0 verzióját, a tartós memória tartalmát, az Assist vezérlést, a naptárt és egy korábbi beszélgetés visszakeresését.

A titkosított adatbázis és kulcsa az alkalmazás saját `/data/recall.sqlite3` és `/data/recall.key` fájljában van. Ezeket együtt kell biztonságosan menteni. A 45 napos napló és a tartós emlékek változatlan formában maradnak; **nem kell és nem szabad új adatbázist létrehozni**.

## Képességek

- 45 napig tárolt, szó szerinti beszélgetési napló, amelyből kérésre visszakeres.
- AI által kezelt tartós emlékek, külön explicit mentés, módosítás és célzott törlés.
- Védett Web UI a megtekintéshez, karbantartási előnézethez, jóváhagyott műveletekhez és visszavonáshoz.
- Opcionális integrált HA naptárlekérdezés és eseménylétrehozás, külön YAML-szkriptek nélkül. Naptári eseménytörlés és -módosítás még nem támogatott.
- Az eredeti OpenAI Conversation ügynök továbbra is végrehajtja a HA eszközvezérlést.

## AI-utasítások

A Nabu Recall saját OpenAI-utasításai **csak a repóban vannak**, az alkalmazás/integráció telepített kódjából töltődnek be. A felhasználó saját OpenAI Conversation Instructions mezője érintetlen marad.

Az aktív források: `custom_components/nabu_recall/repo_instructions.py`, `custom_components/nabu_recall/llm.py` és `nabu_recall/ai.py`. A fenti [OpenAI-utasítástérkép](https://github.com/hollosipeti/nabu-recall/blob/main/NABU_RECALL_PROMPT.md) megmutatja az egyes függvényeket és a telepített fájlok helyét. A régi kézzel bemásolandó naptár- és Nabu-memóriapromptok már nem szükségesek.

## Elérési és adatvédelmi alapok

A Nabu Recall privát bridge szolgáltatása a 8765-ös, az Ingress UI a 8766-os portot használja. Ezeket nem kell a külső hálózatra publikálni. A HA integrációhoz a működő upstream OpenAI Conversation ügynököt válaszd, a Voice Assistban pedig a „Nabu Recall – memória” ügynököt. Az OpenAI API használata külön díjazású.

## Korábbi verziók

A régi kiadások dokumentációja és a kézi naptárszkript-példák a Git-előzményből visszakereshetők, **de a 2.0.0 aktív telepítéséhez nem tartoznak**. A visszaállítás előtti állapot külön `stable-2026-11-24-before-v2` ágon is rögzítve van.
