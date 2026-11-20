"""Explicit Home Assistant Ingress maintenance UI; no voice or bridge writes."""
import hashlib
import hmac
import secrets
import time
from html import escape
from aiohttp import web
from maintenance import (
    cleanup_preview, cleanup_commit, cleanup_restore, latest_cleanup,
    validate_proposal, memory_apply, memory_restore, recent_memory_undo,
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
    messages = {}

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
        body = (
            '<nav><a href="./">Vissza a Nabu Recallhoz</a></nav>'
            '<h2>Kézi memóriakarbantartás</h2>'
            '<p>Csak a Web UI-ban, külön jóváhagyással. '
            'Minden művelet az adatok aktuális állapotát újraellenőrzi.</p>'
        )
        if notice:
            body += '<article><p>%s</p></article>' % _html(notice)
        body += (
            '<article><h3>Hiányos naplók archiválása</h3>'
            '<p><b>Feldolgozott, közvetlenül nem hivatkozott rekord:</b> %d</p>'
            '<p>Az archiválás az eredeti szövegeket ugyanabban a SQLCipher '
            'adatbázisban őrzi meg. A napló visszakeresése nem látja őket, '
            'de a művelet külön visszavonható. '
            'A teljes és a tartós emlékekből hivatkozott naplók védettek.</p>'
            '%s</article>'
            % (snap["count"], form_button(
                "cleanup", "Archiválás jóváhagyása", csrf,
                {"digest": snap["digest"], "count": snap["count"]})
               if snap["count"] else "<p>Nincs jelölt.</p>")
        )
        if rec:
            body += ('<article><p>Legutóbbi archiválás: %d rekord.</p>%s</article>'
                     % (rec["count"], form_button(
                         "undo-cleanup", "Naplók visszaállítása", csrf,
                         {"history_id": rec["history_id"]})))
        body += '<article><h3>Tartós emlékek optimalizálása</h3>'
        body += '<p>Az elemzés legfeljebb 160 emléket vizsgál egy adagban. '
        body += 'Az adagok sorban, növekvő memória-ID szerint haladnak; '
        body += 'a korábbi emlékek sem maradnak ki.</p>'
        cursor = progress.get(request.cookies.get("recall_ui", ""), 0)
        if cursor:
            body += '<p><b>Következő adag kezdőazonosítója:</b> #%d</p>' % cursor
            body += form_button("restart-analysis", "Újrakezdés az első emléktől", csrf)
        if ai is None:
            body += '<p>AI API-kulcs nélkül a javaslatkészítés nem elérhető.</p>'
        else:
            body += form_button("analyze", "Következő adag AI-elemzése",
                                csrf, {"after_id": cursor})
        body += '</article>'
        if plan:
            body += '<h3>Jóváhagyásra váró javaslatok</h3>'
            if not plan["items"]:
                body += '<article><p>Nincs egyértelmű összevonási javaslat.</p></article>'
            for i, item in enumerate(plan["items"]):
                original = store.db.execute(
                    "SELECT id,fact FROM memories WHERE id IN (%s) ORDER BY id" %
                    ",".join("?" * (1 + len(item["remove_ids"]))),
                    [item["keeper_id"]] + item["remove_ids"]
                ).fetchall()
                details = "".join("<p><b>#%d:</b> %s</p>" %
                                  (x["id"], _html(x["fact"])) for x in original)
                body += (
                    '<article><h3>%s</h3>%s'
                    '<p><b>Javasolt új tény (#%d):</b> %s</p>'
                    '<p><b>Indok:</b> %s</p>%s</article>'
                    % (_html(item["type"]), details, item["keeper_id"],
                       _html(item["new_fact"]), _html(item["reason"]),
                       form_button("apply", "Egyetlen javaslat jóváhagyása",
                                   csrf, {"index": i,
                                          "nonce": plan["nonce"]}))
                )
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
            elif name == "analyze":
                if ai is None:
                    raise MaintenanceConflict("AI API is unavailable")
                cursor = int(form.get("after_id", 0))
                if cursor < 0:
                    raise MaintenanceConflict("Invalid cursor")
                memories = store.memory_page(after_id=cursor, limit=160)
                if not memories:
                    raise MaintenanceConflict("No durable memories")
                if lock is not None:
                    async with lock:
                        raw = await ai.optimize_memories(memories)
                else:
                    raw = await ai.optimize_memories(memories)
                candidates = []
                used = set()
                for item in raw[:12]:
                    proposal = validate_proposal(item, store)
                    if proposal is None:
                        continue
                    ids = {proposal["keeper_id"], *proposal["remove_ids"]}
                    if used.intersection(ids):
                        continue
                    used.update(ids)
                    candidates.append(proposal)
                progress[session] = memories[-1]["id"]
                plans[session] = {"nonce": secrets.token_hex(16),
                                  "at": time.monotonic(), "items": candidates,
                                  "next_cursor": memories[-1]["id"]}
                notice = "%d ellenőrzött javaslat; semmit nem módosítottam." % len(candidates)
            elif name == "restart-analysis":
                progress[session] = 0
                plans.pop(session, None)
                notice = "Az optimalizálási áttekintés az elejéről indul."
            elif name == "apply":
                plan = plans.get(session)
                if not plan or time.monotonic() - plan["at"] > MAX_AGE:
                    raise MaintenanceConflict("Preview expired")
                if not hmac.compare_digest(form.get("nonce", ""),
                                           plan["nonce"]):
                    raise MaintenanceConflict("Preview mismatch")
                index = int(form.get("index", -1))
                if index < 0 or index >= len(plan["items"]):
                    raise MaintenanceConflict("Invalid proposal")
                history_id = memory_apply(store, plan["items"][index])
                plans.pop(session, None)
                notice = "Memóriaösszevonás mentve; visszavonási azonosító: #%d." % history_id
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
