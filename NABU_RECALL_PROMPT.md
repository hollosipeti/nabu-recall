# Nabu Recall — OpenAI-utasítások pontos helye

A Nabu Recall **saját** AI-utasításait kizárólag a repó szállítja. A Home Assistant felületén nem szükséges és nem javasolt a memória- vagy naptárszabályokat bemásolni. Az alábbi fájlok a **ténylegesen futó** implementációk, nem másolandó promptminták.

| Felelősség | Aktív forrás a repóban | Telepítés utáni hely |
| --- | --- | --- |
| Válaszadó AI Nabu-szabályai | [`custom_components/nabu_recall/repo_instructions.py`](custom_components/nabu_recall/repo_instructions.py) — `NABU_RULES` | `/config/custom_components/nabu_recall/repo_instructions.py` |
| Ugyanezek hozzáfűzése és HA-ügynök hívása | [`custom_components/nabu_recall/conversation.py`](custom_components/nabu_recall/conversation.py) — `compose_instructions`, `async_process` | `/config/custom_components/nabu_recall/conversation.py` |
| Naptár LLM-eszközök promptja, paraméterei és használata | [`custom_components/nabu_recall/llm.py`](custom_components/nabu_recall/llm.py) — `QueryCalendarTool`, `CreateCalendarTool`, `async_get_tools` | `/config/custom_components/nabu_recall/llm.py` |
| Automatikus memóriafeldolgozó OpenAI-rendszerutasítás | [`nabu_recall/ai.py`](nabu_recall/ai.py) — `AI.learn` | A HAOS Nabu Recall alkalmazáskonténerében: `/app/ai.py` |
| Explicit emlékmentés/-javítás/-törlés OpenAI-utasítás | [`nabu_recall/ai.py`](nabu_recall/ai.py) — `AI.manage` | `/app/ai.py` |
| Memóriavisszakeresés, keresőkifejezések, optimalizálási javaslatok OpenAI-utasításai | [`nabu_recall/ai.py`](nabu_recall/ai.py) — `AI.recall`, `AI.search_terms`, `AI.optimize_memories` | `/app/ai.py` |

**A GitHub `main` ágán ezek az APP 2.0.1 és a HA-integráció 2.0.2 aktív forrásai.** A 2.0.2-es naptárjavítás a naptáreszközök szabályait ugyanabban a `llm.py` fájlban pontosítja. A Python-fájlokban található szövegek az aktív rendszerutasítások. Ennek a dokumentumnak a célja, hogy pontosan megmutassa a helyüket; nem tartalmaz külön, elavuló másolatot.

## Mit szerkeszthet a felhasználó?

Az eredeti **Home Assistant → OpenAI Conversation → Instructions** mező **megmarad és szabadon szerkeszthető**. Ide tartozhatnak a felhasználó saját stílus-, személyiség-, beszéd-, otthon- és eszközvezérlési szokásai.

A Nabu Recall saját memória- és naptárutasításait **ne duplikáld ebben a mezőben**. Ezeket automatikusan betölti az integráció: a `repo_instructions.py` a válaszadó beszélgetéshez, az `llm.py` a HA Assist naptáreszközeihez, az `ai.py` a külön memóriafeldolgozó OpenAI API-hívásaihoz tartozik.

**Határ:** a Home Assistant eredeti OpenAI Conversation rendszere a saját általános promptját továbbra is hozzáadja. A Nabu Recall ezt nem írja át vagy törli: csak a saját szabályai vannak a GitHubban. A modellhez az utasítások együttesen jutnak el, ezért a két forrás között lehet logikai ellentmondás, ha a felhasználó maga olyan szabályt ad meg.

## Mi történik egy kérdésnél?

1. A Nabu Recall a kért tényeket a tartós memóriából és szükség esetén a 45 napos beszélgetési naplóból keresi.
2. Egyértelmű aktuális kedvenc-tényeknél a megerősített tartós érték elsőbbséget kap; a régi naplóbeli állítás nem válik aktuális ténnyé.
3. A HA-integráció hozzáadja a repóban tárolt Nabu-válaszadási utasításokat, és átadja a kérést a meglévő OpenAI Conversation ügynöknek. Egyes strukturált vagy pontosan azonosított aktuális tényekre az integráció közvetlen választ ad.
4. Kifejezett mentés/javítás/törlés esetén a Nabu Recall külön megerősített memóriaműveletet végez. A naptár- és eszközvezérlési műveleteket az adott HA-eszközök végzik.

Az integráció csak a felhasználó által konfigurált upstream OpenAI Conversation ügynökkel működik. Nincs külön második telepítendő naptárszkript.

## Biztonságos ellenőrzés

Ha össze szeretnéd vetni a saját utasításaiddal, nyisd meg először a fenti **`NABU_RULES`** fájlt, utána a **`llm.py`** és **`ai.py`** vonatkozó részeit. A régi kézi `CALENDAR EVENT CREATION`, `CALENDAR EVENT QUERY` és `NABU RECALL MEMORY` blokkokat távolítsd el a HA OpenAI Instructions mezőjéből, amennyiben korábban bemásoltad őket. Az egyedi felhasználói beállításaid maradjanak meg.

Frissítéskor a GitHub-fájlok automatikusan az új integrációba/alkalmazásba kerülnek; a HA saját Instructions mezőjét a telepítő **nem módosítja**.

A korábbi kézzel másolandó promptminták és a két régi naptár-YAML a 2.0.0 főverzió aktív fájljai közül eltávolításra kerültek; szükség esetén a Git-előzményekből még visszakereshetők.
