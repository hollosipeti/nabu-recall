"""Manual checkbox-and-confirm permanent journal deletion UI.

Only password-authenticated HA Ingress; no voice/bridge operation exists.
All selection and confirmation state lives in RAM and is bound to the session.
"""
import hashlib
import hmac
import secrets
import time
from datetime import datetime
from html import escape
from urllib.parse import quote
from zoneinfo import ZoneInfo

from aiohttp import web

from journal_delete import (
    MAX_SELECT, PAGE_SIZE, JournalDeletionConflict,
    deletion_commit, deletion_preview, journal_page,
)

SESSION_PLAN_SECONDS = 600
TIMEZONE = ZoneInfo("Europe/Budapest")


def _h(value):
    return escape(str(value), quote=True)


def setup_journal_delete(app, store, state, authorized, headers, page,
                         token, lock=None):
    pending = {}
    messages = {}

    def session_key(request):
        return request.cookies.get("recall_ui", "")

    def guard(request, data):
        if not authorized(request):
            raise web.HTTPForbidden()
        provided = str(data.get("csrf", ""))
        if not hmac.compare_digest(provided, token(request)):
            raise web.HTTPForbidden()

    def target(search="", day="", page_number=0):
        args = []
        if search:
            args.append("search=" + quote(search))
        if day:
            args.append("day=" + quote(day))
        if page_number:
            args.append("page=" + str(page_number))
        return "./journal" + ("?" + "&".join(args) if args else "")

    def row_time(value):
        return datetime.fromtimestamp(value, TIMEZONE).strftime("%Y-%m-%d %H:%M")

    async def view(request):
        if not authorized(request):
            raise web.HTTPForbidden()
        search = request.query.get("search", "")
        day = request.query.get("day", "")
        try:
            page_number = int(request.query.get("page", "0"))
            listing = journal_page(store, search, day, page_number)
        except (ValueError, TypeError):
            raise web.HTTPBadRequest(text="Érvénytelen szűrés vagy oldalszám")
        session = session_key(request)
        plan = pending.get(session)
        if plan and time.monotonic() - plan["at"] > SESSION_PLAN_SECONDS:
            pending.pop(session, None)
            plan = None
        csrf = token(request)
        notice = messages.pop(session, "")
        body = (
            '<nav><a href="../maintenance">← Memóriakezelés</a> · '
            '<a href="../">Nabu Recall</a></nav>'
            '<h2>Forgó memória – kézi végleges törlés</h2>'
            '<article><p><b>Figyelem:</b> ez NEM archiválás. '
            'A jóváhagyott beszélgetéseket végleg töröljük az aktív SQLCipher '
            'adatbázisból. Nincs visszavonás. Előbb készíts ellenőrzött HA-mentést.</p>'
            '<p>Csak a kijelölt, már feldolgozott és tartós emlék által '
            'nem hivatkozott párbeszédek törölhetők. '
            'A többi bejegyzés védett. A naplókeresés nem jelöl ki semmit.</p></article>'
        )
        if notice:
            body += '<article><p>%s</p></article>' % _h(notice)
        body += (
            '<article><form action="./journal" method="get">'
            '<label>Keresés a kérdésben vagy válaszban '
            '<input type="search" name="search" maxlength="120" value="%s"></label>'
            '<label>Nap (magyar helyi dátum, opcionális) '
            '<input type="date" name="day" value="%s"></label>'
            '<button type="submit">Szűrés</button>'
            '</form><p>Találatok: %d · oldal: %d · legfeljebb %d / oldal.</p></article>'
            % (_h(search), _h(day), listing["total"], page_number + 1, PAGE_SIZE)
        )
        if plan:
            body += (
                '<article><h3>Végső ellenőrzés – még nem történt törlés</h3>'
                '<p><strong>%d kijelölt párbeszéd</strong> törlése. '
                'Ez végleges, nem vonható vissza. A pontos kijelölés és minden '
                'rekord változatlanságát a művelet ismét ellenőrzi.</p>'
                % plan["preview"]["count"]
            )
            for item in plan["preview"]["rows"]:
                body += ('<p><b>#%d · %s</b> · %s</p>'
                         '<p><b>Kérdés:</b> %s</p><p><b>Válasz:</b> %s</p>' %
                         (item["id"], _h(row_time(item["created"])),
                          "feldolgozva", _h(item["user_text"]),
                          _h(item["assistant_text"])))
            body += (
                '<form method="post" action="./journal/confirm">'
                '<input type="hidden" name="csrf" value="%s">'
                '<input type="hidden" name="confirm" value="%s">'
                '<label><input type="checkbox" name="ack" value="yes" required '
                'style="width:auto"> Tudomásul veszem, hogy a törlés végleges.</label>'
                '<button type="submit">Kijelölt %d párbeszéd VÉGLEGES törlése</button>'
                '</form><form method="post" action="./journal/cancel">'
                '<input type="hidden" name="csrf" value="%s">'
                '<button type="submit">Mégse – kijelölés elvetése</button></form></article>'
                % (_h(csrf), _h(plan["confirmation"]),
                   plan["preview"]["count"], _h(csrf))
            )
        body += (
            '<article><h3>Beszélgetések kiválasztása</h3>'
            '<form method="post" action="./journal/select">'
            '<input type="hidden" name="csrf" value="%s">'
            '<button type="submit" name="mode" value="page">'
            'Az oldal összes törölhető sorának ellenőrzése</button> '
            '<button type="reset">Pipák törlése</button>'
            % _h(csrf)
        )
        for item in listing["rows"]:
            protected = not item["processed"] or bool(item["linked"])
            reason = ("Feldolgozásra vár" if not item["processed"]
                      else "Tartós emlék forrása" if item["linked"]
                      else "Kijelölhető")
            checkbox = (
                '<input type="checkbox" name="journal_id" value="%d" '
                'style="width:auto" %s>' %
                (item["id"], "disabled" if protected else "")
            )
            if not protected:
                body += ('<input type="hidden" name="visible_id" value="%d">' %
                         item["id"])
            body += (
                '<article><label>%s <strong>#%d · %s · %s</strong></label>'
                '<p><b>Kérdés:</b> %s</p><p><b>Válasz:</b> %s</p></article>' %
                (checkbox, item["id"], _h(row_time(item["created"])),
                 _h(reason), _h(item["user_text"]), _h(item["assistant_text"]))
            )
        body += ('<button type="submit" name="mode" value="selected">'
                 'Bepipáltak ellenőrzése (még nincs törlés)</button>'
                 '</form></article>')
        if page_number:
            body += '<a href="%s">← Előző oldal</a> ' % _h(
                target(search, day, page_number - 1))
        if (page_number + 1) * PAGE_SIZE < listing["total"]:
            body += '<a href="%s">Következő oldal →</a>' % _h(
                target(search, day, page_number + 1))
        return headers(web.Response(
            text=page(body, state.get("version", "?"),
                      "Nabu Recall — végleges naplótörlés"),
            content_type="text/html"
        ))

    async def select(request):
        if not authorized(request):
            raise web.HTTPForbidden()
        form = await request.post()
        guard(request, form)
        session = session_key(request)
        try:
            mode = str(form.get("mode", "selected"))
            if mode not in ("selected", "page"):
                raise JournalDeletionConflict("Invalid selection mode")
            raw = form.getall("visible_id" if mode == "page" else "journal_id", [])
            if not 1 <= len(raw) <= MAX_SELECT:
                raise JournalDeletionConflict("Invalid selection count")
            if any(not text.isdigit() for text in raw):
                raise JournalDeletionConflict("Invalid journal ID")
            ids = [int(v) for v in raw]
            preview = deletion_preview(store, ids)
            pending[session] = {"preview": preview, "confirmation": secrets.token_hex(16),
                                "at": time.monotonic()}
            messages[session] = "%d rekord kijelölve. Még semmit nem töröltünk." % len(ids)
        except (JournalDeletionConflict, ValueError, TypeError):
            pending.pop(session, None)
            messages[session] = "A kijelölés elutasítva: hiányzó vagy védett bejegyzés."
        return headers(web.HTTPSeeOther(location="../journal"))

    async def confirm(request):
        if not authorized(request):
            raise web.HTTPForbidden()
        form = await request.post()
        guard(request, form)
        session = session_key(request)
        plan = pending.pop(session, None)  # One-time, even on failure.
        if (not plan or time.monotonic() - plan["at"] > SESSION_PLAN_SECONDS
                or form.get("ack") != "yes"
                or not hmac.compare_digest(str(form.get("confirm", "")),
                                           plan["confirmation"])):
            messages[session] = "A törlés nem történt meg. A jóváhagyás hiányzik vagy lejárt."
            return headers(web.HTTPSeeOther(location="../journal"))
        try:
            if lock is not None:
                async with lock:
                    count = deletion_commit(store, plan["preview"]["ids"],
                                            plan["preview"]["digest"])
            else:
                count = deletion_commit(store, plan["preview"]["ids"],
                                        plan["preview"]["digest"])
            messages[session] = "%d párbeszéd végleg törölve." % count
        except (JournalDeletionConflict, ValueError, TypeError):
            messages[session] = "A napló megváltozott vagy egy rekord védett. Nem töröltünk semmit."
        except Exception:
            messages[session] = "Törlési hiba. Ellenőrizd a napló darabszámát."
        return headers(web.HTTPSeeOther(location="../journal"))

    async def cancel(request):
        if not authorized(request):
            raise web.HTTPForbidden()
        form = await request.post()
        guard(request, form)
        pending.pop(session_key(request), None)
        messages[session_key(request)] = "Kijelölés elvetve, nem történt törlés."
        return headers(web.HTTPSeeOther(location="../journal"))

    app.router.add_get("/maintenance/journal", view)
    app.router.add_post("/maintenance/journal/select", select)
    app.router.add_post("/maintenance/journal/confirm", confirm)
    app.router.add_post("/maintenance/journal/cancel", cancel)
