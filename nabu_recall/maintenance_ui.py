"""Explicit Home Assistant Ingress maintenance UI; no voice or bridge writes."""
import hashlib
import hmac
import secrets
import time
from html import escape
from aiohttp import web
from maintenance import (
    cleanup_preview, cleanup_commit, cleanup_restore, latest_cleanup,
    validate_proposal, memory_apply, memory_apply_many, memory_restore, memory_restore_many, recent_memory_undo,
    MaintenanceConflict,
)

MAX_AGE = 600


def _html(text):
    return escape(str(text), quote=True)


def _csrf(key, session):
    return hmac.new(key, ("maintenance:" + session).encode(),
                    hashlib.sha256).hexdigest()


def setup_maintenance(app, store, state, key, authorized, headers, page, ai=None,
                      lock=None):
    plans = {}
    progress = {}
    duplicate_progress = {}
    messages = {}
    confirmations = {}
    batch_undo = {}

    def token(request):
        return _csrf(key, request.cookies.get("recall_ui", ""))

    def guard(request, form):
        if not authorized(request):
            raise web.HTTPForbidden()
        provided = form.get("csrf", "")
        if not isinstance(provided, str) or not hmac.compare_digest(
                provided, token(request)):
            raise web.HTTPForbidden()

    def form_button(action, label, csrf, fields=None, caution=False):
        fields = fields or {}
        entries = "".join('<input type="hidden" name="%s" value="%s">' %
                          (_html(k), _html(v)) for k, v in fields.items())
        return ('<form action="./maintenance/%s" method="post">'
                '<input type="hidden" name="csrf" value="%s">%s'
                '<button type="submit">%s</button></form>' %
                (_html(action), _html(csrf), entries, _html(label)))

    def render_page(request, notice=""):
        from dashboard import _page
        session_id = request.cookies.get("recall_ui", "")
        notice = notice or messages.pop(session_id, "")
        csrf = token(request)
        snap = cleanup_preview(store)
        rec = latest_cleanup(store)
        undo = recent_memory_undo(store)
        plan = plans.get(request.cookies.get("recall_ui", ""))
        if plan and time.monotonic() - plan["at"] > MAX_AGE:
            plan = None
        audit = store.journal_integrity_summary()
        body = (
            '<nav><a href="./">Vissza a Nabu Recallhoz</a></nav>'
            '<h2>Memóriakezelés</h2>'
            '<p><b>1.</b> A naplókarbantartás a hibás, üres válaszú '
            'beszélgetések áthelyezése egy titkosított archívumba.</p>'
            '<p><b>2.</b> Az emlékellenőrzés az ismétlődő vagy ütköző '
            'tartós tényekből készít javaslatokat. Az AI csak javasol.</p>'
            '<p><b>3.</b> Pipáld ki kizárólag a helyes összevonásokat, '
            'ellenőrizd az összegzést, majd hagyd jóvá a kijelölteket.</p>'
            '<p>A tartós memória soha nem tisztul automatikusan az itt '
            'megjelenő javaslatok alapján.</p>'
        )
        if notice:
            body += '<article><p>%s</p></article>' % _html(notice)
        body += (
            '<article><h3>Beszélgetésnapló — 45 napos forgó tároló</h3>'
            '<p>Összes: %d · teljes: %d · hiányos: %d · '
            'tartós emlékhez kötött hiányos: %d · feldolgozatlan hiányos: %d.</p>'
            '<p>Ez a korábbi „Naplóellenőrzés” összefoglalója.</p>'
            '<h3>Hiányos naplók archiválása</h3>'
            '<p><b>Feldolgozott, közvetlenül nem hivatkozott rekord:</b> %d</p>'
            '<p>Az archiválás az eredeti szövegeket ugyanabban a SQLCipher '
            'adatbázisban őrzi meg. A napló visszakeresése nem látja őket, '
            'de a művelet külön visszavonható. '
            'A teljes és a tartós emlékekből hivatkozott naplók védettek.</p>'
            '%s</article>'
            % (audit["total"], audit["complete"], audit["missing"],
               audit["referenced_turns"], audit["missing_pending"],
               snap["count"], form_button(
                "cleanup", "Archiválás jóváhagyása", csrf,
                {"digest": snap["digest"], "count": snap["count"]})
               if snap["count"] else "<p>Nincs jelölt.</p>")
        )
        if rec:
            body += ('<article><p>Legutóbbi archiválás: %d rekord.</p>%s</article>'
                     % (rec["count"], form_button(
                         "undo-cleanup", "Naplók visszaállítása", csrf,
                         {"history_id": rec["history_id"]})))
        body += '<article><h3>Tartós emlékek — ismétlések keresése</h3>'
        body += '<p>Az elemzés legfeljebb 160 emléket vizsgál egy adagban. '
        body += 'Az adagok sorban, növekvő memória-ID szerint haladnak; '
        body += 'a korábbi emlékek sem maradnak ki.</p>'
        cursor = progress.get(request.cookies.get("recall_ui", ""), 0)
        if cursor:
            body += '<p><b>Következő adag kezdőazonosítója:</b> #%d</p>' % cursor
            body += form_button("restart-analysis", "Újrakezdés az első emléktől", csrf)
        duplicate_cursor = duplicate_progress.get(
            request.cookies.get("recall_ui", ""), 0)
        if ai is None:
            body += '<p>AI API-kulcs nélkül a javaslatkészítés nem elérhető.</p>'
        else:
            body += form_button(
                "scan-duplicates", "Teljes állomány duplikátumjelöltjei",
                csrf, {"after_id": duplicate_cursor})
            body += form_button("analyze", "Következő adag szemantikai AI-elemzése",
                                csrf, {"after_id": cursor})
        body += '</article>'
        if plan:
            body += '<h3>Talált összevonási javaslatok</h3>'
            body += '<p>Mindegyiknél az AI által javasolt végleges tény látható. '
            body += 'A pipa nélkül egyetlen emlék sem változik. '
            body += 'Az eredeti tények és az indok megmaradnak az előnézetben.</p>'
            if not plan["items"]:
                body += '<article><p>Nincs egyértelmű összevonási javaslat.</p></article>'
            else:
                body += ('<form class="approvals" action="./maintenance/select" method="post">'
                         '<input type="hidden" name="csrf" value="%s">'
                         '<input type="hidden" name="nonce" value="%s">' %
                         (_html(csrf), _html(plan["nonce"])))
            for i, item in enumerate(plan["items"]):
                original = store.db.execute(
                    "SELECT id,fact FROM memories WHERE id IN (%s) ORDER BY id" %
                    ",".join("?" * (1 + len(item["remove_ids"]))),
                    [item["keeper_id"]] + item["remove_ids"]
                ).fetchall()
                details = "".join("<p><b>#%d:</b> %s</p>" %
                                  (x["id"], _html(x["fact"])) for x in original)
                body += (
                    '<article><label><input type="checkbox" name="selected" '
                    'value="%d" style="width:auto; margin-right:10px">'
                    '<b>Összevonás kijelölése — %s</b></label>%s'
                    '<p><b>Megmaradó emlék (#%d):</b> %s</p>'
                    '<p><b>Miért?</b> %s</p></article>'
                    % (i, _html({"duplicate": "Ismétlés",
                                   "overlap": "Átfedés",
                                   "conflict": "Lehetséges ellentmondás"}.get(
                                       item["type"], item["type"])),
                       details, item["keeper_id"],
                       _html(item["new_fact"]), _html(item["reason"]))
                )
            if plan["items"]:
                body += ('<button type="submit">Kijelöltek ellenőrzése</button>'
                         '</form>')
        confirm = confirmations.get(session_id)
        if confirm and plan and confirm["nonce"] == plan["nonce"]:
            body += ('<article><h3>Végső ellenőrzés — még nem történt módosítás</h3>'
                     '<p><b>%d kijelölt összevonás</b>. '
                     'A felsorolt módosítások egyetlen tranzakcióban történnek: '
                     'ha bármelyik sikertelen, egyik sem lép életbe.</p>' %
                     len(confirm["indices"]))
            for idx in confirm["indices"]:
                item = plan["items"][idx]
                body += ('<p><b>#%d marad:</b> %s '
                         '(megszűnő ID-k: %s)</p>' %
                         (item["keeper_id"], _html(item["new_fact"]),
                          ", ".join("#%d" % x for x in item["remove_ids"])))
            body += form_button(
                "apply-selected", "Kijelölt összevonások végleges jóváhagyása",
                csrf, {"nonce": plan["nonce"], "confirm": confirm["token"]})
            body += '</article>'
        last_batch = batch_undo.get(session_id)
        if last_batch:
            body += ('<article><h3>Legutóbbi csoportos összevonás visszavonása</h3>'
                     '<p>%d korábban jóváhagyott összevonás, egyben visszavonható '
                     'a 7 napos határidőn belül.</p>%s</article>' %
                     (len(last_batch["ids"]), form_button(
                         "undo-selected", "Teljes csoport visszavonása",
                         csrf, {"token": last_batch["token"]})))
        if undo:
            body += ('<article><h3>Utolsó memóriaösszevonás visszavonása</h3>'
                     '%s</article>' % form_button(
                         "undo-memory", "Összevonás visszavonása", csrf,
                         {"history_id": undo["id"]}))
        body += (
            '<p><b>Biztonság:</b> friss Home Assistant mentés szükséges. '
            'Az archivált rekordok és a visszavonási előzmények '
            'ugyanabban a titkosított adatbázisban maradnak. '
            'Egy későbbi teljes adatbázis-visszaállítás a mentés időpontjára '
            'állítja vissza az összes adatot.</p>'
        )
        return headers(web.Response(
            text=_page(body, state.get("version", "?"),
                       "Nabu Recall — kézi karbantartás"),
            content_type="text/html"))

    async def home(request):
        if not authorized(request):
            raise web.HTTPForbidden()
        return render_page(request)

    async def perform(request):
        if not authorized(request):
            raise web.HTTPForbidden()
        form = await request.post()
        guard(request, form)
        name = request.match_info["action"]
        session = request.cookies.get("recall_ui", "")
        notice = ""
        try:
            if name == "cleanup":
                result = cleanup_commit(store, form.get("digest", ""),
                                        int(form.get("count", 0)))
                notice = "%d naplóbejegyzés archiválva." % result["count"]
            elif name == "undo-cleanup":
                count = cleanup_restore(store, int(form.get("history_id", 0)))
                notice = "%d naplóbejegyzés visszaállítva." % count
            elif name in ("analyze", "scan-duplicates"):
                if ai is None:
                    raise MaintenanceConflict("AI API is unavailable")
                cursor = int(form.get("after_id", 0))
                if cursor < 0:
                    raise MaintenanceConflict("Invalid cursor")
                if name == "scan-duplicates":
                    batch = store.memory_duplicate_page(
                        after_id=cursor, max_memories=120)
                    memories = batch["memories"]
                    duplicate_progress[session] = (
                        batch["cursor"] if batch["more"] else 0)
                else:
                    memories = store.memory_page(after_id=cursor, limit=160)
                    if memories:
                        progress[session] = memories[-1]["id"]
                if not memories:
                    raise MaintenanceConflict("No matching durable memories")
                if lock is not None:
                    async with lock:
                        raw = await ai.optimize_memories(memories)
                else:
                    raw = await ai.optimize_memories(memories)
                candidates = []
                used = set()
                eligible = {m["id"] for m in memories}
                for item in raw[:12]:
                    proposal = validate_proposal(item, store)
                    if proposal is None:
                        continue
                    ids = {proposal["keeper_id"], *proposal["remove_ids"]}
                    if not ids.issubset(eligible) or used.intersection(ids):
                        continue
                    used.update(ids)
                    candidates.append(proposal)
                confirmations.pop(session, None)
                plans[session] = {"nonce": secrets.token_hex(16),
                                  "at": time.monotonic(), "items": candidates,
                                  "next_cursor": memories[-1]["id"]}
                notice = "%d ellenőrzött javaslat; semmit nem módosítottam." % len(candidates)
            elif name == "restart-analysis":
                progress[session] = 0
                duplicate_progress[session] = 0
                plans.pop(session, None)
                confirmations.pop(session, None)
                notice = "Az optimalizálási áttekintés az elejéről indul."
            elif name in ("apply", "select", "apply-selected"):
                plan = plans.get(session)
                if not plan or time.monotonic() - plan["at"] > MAX_AGE:
                    raise MaintenanceConflict("Preview expired")
                if not hmac.compare_digest(form.get("nonce", ""),
                                           plan["nonce"]):
                    raise MaintenanceConflict("Preview mismatch")
                if name == "select":
                    raw_indices = form.getall("selected", [])
                    if not 1 <= len(raw_indices) <= 12:
                        raise MaintenanceConflict("Select 1–12 items")
                    indices = [int(x) for x in raw_indices]
                    if (len(set(indices)) != len(indices) or
                            any(i < 0 or i >= len(plan["items"]) for i in indices)):
                        raise MaintenanceConflict("Invalid selection")
                    confirmations[session] = {
                        "indices": indices, "nonce": plan["nonce"],
                        "token": secrets.token_hex(16)}
                    notice = "%d javaslat kijelölve. A végső jóváhagyás még szükséges." % len(indices)
                elif name == "apply-selected":
                    confirm = confirmations.get(session)
                    if not confirm or confirm["nonce"] != plan["nonce"]:
                        raise MaintenanceConflict("Selection missing")
                    if not hmac.compare_digest(
                            str(form.get("confirm", "")), confirm["token"]):
                        raise MaintenanceConflict("Confirmation mismatch")
                    approved = [plan["items"][i] for i in confirm["indices"]]
                    history_ids = memory_apply_many(store, approved)
                    plans.pop(session, None)
                    confirmations.pop(session, None)
                    batch_undo[session] = {
                        "ids": history_ids, "token": secrets.token_hex(16)}
                    notice = "%d kijelölt összevonás sikeresen végrehajtva." % len(history_ids)
                else:
                    index = int(form.get("index", -1))
                    if index < 0 or index >= len(plan["items"]):
                        raise MaintenanceConflict("Invalid proposal")
                    history_id = memory_apply(store, plan["items"][index])
                    plans.pop(session, None)
                    confirmations.pop(session, None)
                    notice = "Memóriaösszevonás mentve; visszavonási azonosító: #%d." % history_id
            elif name == "undo-selected":
                last = batch_undo.get(session)
                if not last or not hmac.compare_digest(
                        str(form.get("token", "")), last["token"]):
                    raise MaintenanceConflict("Undo selection missing")
                count = memory_restore_many(store, last["ids"])
                batch_undo.pop(session, None)
                plans.pop(session, None)
                notice = "%d eredeti emlék visszaállítva az egész csoportból." % count
            elif name == "undo-memory":
                count = memory_restore(store, int(form.get("history_id", 0)))
                plans.pop(session, None)
                notice = "%d memóriaeredeti visszaállítva." % count
            else:
                raise web.HTTPNotFound()
        except (MaintenanceConflict, ValueError, TypeError, KeyError,
                IndexError) as exc:
            notice = "Művelet elutasítva. Ellenőrizd és frissítsd az előnézetet."
        except Exception:
            notice = "A művelet nem sikerült. Adatok ellenőrzése szükséges."
        # Post/redirect/get: preserve one-time success or error feedback.
        messages[session] = notice
        response = web.HTTPSeeOther(location="../maintenance")
        return headers(response)

    app.router.add_get("/maintenance", home)
    app.router.add_post("/maintenance/{action}", perform)
