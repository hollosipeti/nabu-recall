"""Read-only ingress diagnostics, with an independent password gate."""
import hashlib
import hmac
import os
import secrets
import shutil
import time
from aiohttp import web
from datetime import datetime, timezone
from html import escape
from pathlib import Path

SESSION_AGE = 10 * 60  # Absolute lifetime since successful login, not idle timeout.

# Reuse the existing HA integration brand icon directly in the Ingress header.
# Data URL avoids extra network routes and works behind HA Supervisor Ingress.
BRAND_ICON_DATA_URI = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACABAMAAAAxEHz4AAAAMFBMVEUAAADyXt0L5N/3mOfqKaGgUekPGRzhNdLy5PZiUeFZI6SjMNHzT7KhGqElKpkEp6jZR5kqAAAAEHRSTlMA/Pv8/Pz8/Pz8/Pz7+/z8DZEZKgAACWlJREFUeNrtmG1sW9UZx3++vrlN4sRxwobYNJWLy5t4aS81FLQCvWNumeg0mU5BagrlanTuBBNzYdO8sVVWB132pbJgyxSPbbfQhraWigV0DByotVYTYngzVcfUlt4dGBRpUOetiV3HPt4HJ03axk26fVyeT5afe/7n+T/neTsH5mVe5mVe/p/EHbiQ1jXr+gBS6SSZraNWZt2fkBApZOC/sOC21dsYaFdcFfwOysmLtiAQ6g0sDyIN6AR50RRuEq8YA58MoAFJwoQuEsAlZPwT6NRLGABW068u0oJ0uiBFJ5DVcDQ0tM6ZPlPrrT8QZUD42S3AeJsS8L3k8sjcAVpivGHAuIBwAjS4/+7NlYugUBg4mREI6Q6HS4AFje8KtzFngMBTnUoESJED0Ej0d2nSuWquAO4GkiggqVSyNlpXP+KKzDIrE5pbJLoNpMAPOLiNAPRLgXLVx28etZNzsaDFQArPSyHgMX8lA9ulAHksrGiEtswBYB+QNn6QQjr7JN/Nvv2IAFifMvVMw2Z91mN0KTgeCuM4cExnx+DnBgE0LZigfN6OM1kgIVWM4XheNnSARwSgPZDDErBNmRVgucdJU5aO59rYISRWcC+KTum3h00Na27HmIYY6V3lqg7wqVAWCqC4I4hNk9BnAXCJKEQzX43+5GAOhJaVLPx9ZxnW75xbNioQjTYeWDJQRiJ5YAvK33pYu44+n9CxCnKWU3DHXqP/q7dnOpNlozUHuf3i+uv6Gngn2VV97G1t1mx038Ko2rKSFIzjBndFcjjXADeHkRV1A0A8LupTMEIp8eQNJCEEMcNtbFFwNQDYlFcppgriRx/WzwW3gfz0hQhwdOTAo+7LigzI2nZhYNU3V++M+x6uFuoDBHDSsc9CSbJhxlMEqAxLAbg/4/DzlOwB4l8YSk+vTK5zS7HnygNPjacqyxK4fLhvcJvbAEYtSt9/Ho6YXxzz7Bk3YnWc6Baea7vLGXjv/QBSUCH2KEDVSqC1NsO3O+kBYn5nZidKdlVfjbC30nUNUgCHax4YS2CVei1gbOxhLLNuIPlgFHaLE8870zUtXTGrL1zqQdXizWOdx5rqOrHdY3wCDi/eO8npxhxQLRa7izHL3tRsOs3HY/QWnpaiTiCNgoQWXm4xWlWouAGW/akRwmAFTVIKSvwf/pkptLALAaR5uaUnvHYdkAsAr8dgKwnLwH5VoXPbaUS9UC6D/DRNtHx1ArS/mFRyAEWraNFmt2rW6E7UJlHXiZ4YUqSiUf5cIkbpWaACWiPFrXDvIOABE/Q6AKd40pNKF6kcsXZ1byXcW/u7UmtNGFiwLhlBMsXhLAruL73Bz6A6vKgUKyrdm63f+GpTDjZhaBMw4Fl7a6RuQbkllP4jMOj0NLI1BjwyqWnT4LkhqF6z+YXIz6dzUM6ap7i7THm/9Bg2JbA4BUAJ+DclcLHoWx92huKIqcI4HcAgSaY/Y4giMSw2U+qrKd5qxJew9TbuOuyYNH2IVyr6+QBuxkXq8YxLQhdFLWqhlVIARED388G7xu8yKuH7t/nFlBOnW+A4soHHDUEKKIVtGPRNmLZJfHCTt/2fOz8y1328owl9auE0AC8pjoUcQRqABOCrTRTbY+6AV0BDKDVe2gdOh5ByBgs8nrTchidNrVxYlM5kacoBMJt+eU8Sk7gCjecDeHZFo4F0YOfKItBIFdomc2bcmYyZdtSNIHSKynkAu2JAtBICbLBdicQz09otqCa4ShDfCDB5DMr0uQzIDOKZKHiKfypcdmZQTTAjPmhKRPDOEEhFKPf3rxD6LjBjxBTpOM7kWBYSqglJl706aTImGJ4hncsA/JV/xUAF901SoEwc9wqfFSQ8us/3YK9Ls+KLJcrk9D0tmcoZNZhxVwzKmeBbDzVIcWZEX3HpAgjT1XNfbCPNex4s1Eum/QN3pNyUDwZ5vCEE8GIKYP+lnAKq9ne6QbnM+jWgT8biNICDrkjIEzPItA2syIV2C8C34p3y/tEesIHB+2LFLX6dS7/BFIOzKFzC3kug7NLZy24BsF37xdoeK4GGqlXHGos2Jz9YquhCR84QyixEAJkOEBNV226GUkI9WPKZDBLbcqgy2JZDBynE+QAu4VAGVUonDBC2wAX2199qBB7Eit642OXySYbx5usVVTLlCkLLhrVwGA1IldQYRbeqDY6hHBAw1Iai1x0wipRr43n2xmw2hwXj9tdGQ92LzVFALp5ofzW+5xfVh9xkyUQIV47EAZzSR/3c/krxyh+uufL1LpSFOZ/3UC28Z4pEVuXcBgTdYYgvas2BfpQg/YHuwmPmuF0rGc9681cA6MoMTqxApUk9UiF7hK+oN3/5TkUDggtXrtF5HdAV3/sT+w1PXSOnAWSo5EayBbJN8VMFXesauw0LUIMmy20wkagmCKT3AoNmxN3bFC/ddZoNtmomJmgGm1XQUbwdHR0doKDP3BfobYrnys9kCl1SnDAxaxGsBm9tX3U7KuudYYB2x+lQ6nTnkYzRzvYNGwDVP6EJssletvh9lnafKUL1ZuWywQhI7HGBamPDytVqkIKt6mTUa4lOrhdnguAcCs+00qqFwziofWQ1ghFC8GPMPFCcrKLI1nrN9fTGXK2cq31cPja4AZpdC4irZIS6lC068NGdADmlzrDd3wpBuAeUnNXcs8lOqvc2Yw6vEWtqXpMW59w3zjnGRXQBcPlJ/k6zPS7KAwRfeu3Mhydqk4avLkArKH6///NXuxesv56xlK4ykDxdgHybDjAIIIa4wLjf8iZgHG/c4ddPPAwmUKi1AQlcV7JtQB+sd+EYOW5bQh/xOBoEXeOqCRtBaaFDoDuKrvR1Peecvek5FhilUb1i5MAKMhY3KWwEZaHoQKetKsW0OlBnThyJhxeBgNXQC0SETt7XUWNQdbVaJapDSy94a7OP0wwrm22Aglf3Cl9eAG1AlVLfIdoueOk6XeD4AUb3LNOJxImQH16cx8vEqiHNmvXpbMETb/DE0T3NTfT2onjBK8jn8yxZUq1Wq0B12O8fvgCF009fggl2obewUVl4CIZ1Ojo6YATA76/WwuUCN9eRO2wdaCKCnl889UHOAI4fZ8RgyDvLE8iC97JwIqLnxbA+2QOUfMdkFrSKdjGLI356dM/evMjn89MsXHLmV5sy63Pggj+cJAh0TCern2mozuzvicequROR/+khtZX4/GvyvMzLvMzLvFy8/Ackrq7GzTewCgAAAABJRU5ErkJggg=="

def _time(value):
    return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if value else "—"

def _bytes(value):
    if value is None:
        return "nem elérhető"
    if value < 1024 * 1024:
        return "%.1f KiB" % (value / 1024)
    return "%.2f MiB" % (value / (1024 * 1024))

def storage_metrics(store):
    """Read filesystem sizes, never alter SQLite, WAL or memory records."""
    try:
        row = store.db.execute("PRAGMA database_list").fetchone()
        path = Path(row[2])
        if not path.is_file():
            return {"database": None, "free": None}
        files = [path, Path(str(path) + "-wal"), Path(str(path) + "-shm")]
        size = sum(p.stat().st_size for p in files if p.is_file())
        free = shutil.disk_usage(path.parent).free
        return {"database": size, "free": free}
    except (OSError, ValueError, IndexError, TypeError):
        return {"database": None, "free": None}

CSS = """
body{background:#101722;color:#e9eef8;font:15px system-ui,sans-serif;
 max-width:900px;margin:20px auto;padding:0 16px}
a{color:#59d9db}h1{color:#64dbd4}header{display:flex;align-items:center;gap:16px}
.brain{width:42px;height:42px;object-fit:contain;flex-shrink:0}.metrics{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.metric,article{background:#1c2837;border:1px solid #304052;border-radius:12px;padding:14px}
.metric strong{display:block;font-size:27px;color:#7fe7df}
.metric span,small{color:#b3bdc9}
article{margin:12px 0;overflow-wrap:anywhere}nav{margin:18px 0;line-height:2}
p{white-space:pre-wrap}footer{color:#98a7b6;margin:24px 0}
input{background:#101722;color:#fff;border:1px solid #536171;padding:12px;
 border-radius:8px;width:100%;box-sizing:border-box;font-size:16px}
button{background:#59d9db;color:#10202b;padding:10px 18px;border:0;
 border-radius:8px;font-weight:bold;cursor:pointer}
form{max-width:380px} form.approvals{max-width:none} .warn{color:#ffb2a8}
"""

def _page(body, version, header="Nabu Recall — állapot"):
    return ("<!doctype html><html lang='hu'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>Nabu Recall</title><style>%s</style></head><body>"
            "<header><img class='brain' src='%s' alt='Nabu Recall ikon'><div><h1>%s</h1>"
            "<small>v%s · HAOS ingress · jelszóval védett diagnosztika</small>"
            "</div></header>%s</body></html>" %
            (CSS, BRAND_ICON_DATA_URI, escape(header), escape(str(version)), body))

def login_page(version, configured=True, failed=False):
    if not configured:
        content = ("<article><h2>A diagnosztika zárolva</h2><p>Állíts be "
                   "Web UI jelszót a Nabu Recall alkalmazás konfigurációjában "
                   "(dashboard_password), majd indítsd újra az alkalmazást.</p>"
                   "<p>A memória és a beszélgetőasszisztens ettől függetlenül működik."
                   "</p></article>")
    else:
        message = "<p class='warn'>Hibás jelszó vagy túl sok próbálkozás.</p>" if failed else ""
        content = ("<article><h2>Web UI belépés</h2>%s"
                   "<form method='post' action='./login'>"
                   "<label for='password'>Jelszó</label><p>"
                   "<input id='password' type='password' name='password' "
                   "autocomplete='current-password' required maxlength='256'></p>"
                   "<button type='submit'>Belépés</button></form></article>" % message)
    return _page(content, version)

def render(store, state, tab="memories"):
    stats = store.statistics()
    title = "Nabu Recall — állapot"
    nav = ('<nav><a href="./?tab=memories">Tartós emlékek</a> · '
           '<a href="./?tab=turns">45 napos napló</a> · '
           '<a href="./?tab=storage">Memória és tárhely</a> · <a href="./maintenance">Memóriakezelés</a> · '
           '<a href="./">Állapot</a></nav>'
           '<form action="./logout" method="post">'
           '<button type="submit">Kijelentkezés</button></form>')
    body = ""
    if tab == "memories":
        items = store.memory_list(100)
        body = "<h2>Tartós emlékek</h2>" + (
            "".join("<article><small>#%d · %s</small><p>%s</p></article>" %
                    (x["id"], escape(_time(x["updated"])), escape(x["fact"])) for x in items)
            or "<p>Még nincs tartós emlék.</p>")
    elif tab == "turns":
        items = store.recent_turns(35)
        body = "<h2>Legutóbbi beszélgetések (maximum 35)</h2>" + (
            "".join("<article><small>#%d · %s · %s</small><p><b>Kérdés:</b> %s</p>"
                    "<p><b>Válasz:</b> %s</p></article>" %
                    (x["id"], escape(_time(x["created"])),
                     "feldolgozva" if x["processed"] else "feldolgozásra vár",
                     escape(x["user_text"][:2000]), escape(x["assistant_text"][:2000]))
                    for x in items) or "<p>Nincs naplóbejegyzés.</p>")
    elif tab == "audit":
        audit = store.journal_integrity_summary()
        preview = store.journal_cleanup_preview()
        body = (
            "<h2>Naplóellenőrzés — csak előnézet</h2>"
            "<article><p>Hiányos sor: az asszisztens válasza üres, vagy csak szóközökből áll.</p>"
            "<p>A nézet kizárólag SELECT lekérdezést végez; nem töröl, nem javít.</p>"
            "<p><b>Összes napló:</b> %d</p>"
            "<p><b>Teljes kérdés–válasz:</b> %d</p>"
            "<p><b>Hiányzó válasz:</b> %d</p>"
            "<p><b>Ebből feldolgozott:</b> %d</p>"
            "<p><b>Ebből feldolgozásra vár:</b> %d</p>"
            "<p><b>Legfeljebb 20 érintett ID:</b> %s</p></article>"
            "<article><h3>Tartós emlékek forráshivatkozásai</h3>"
            "<p><b>Hiányos naplóhoz kötött emlékek:</b> %d</p>"
            "<p><b>Hivatkozott hiányos naplóbejegyzések:</b> %d</p>"
            "<p><b>Feldolgozott, hiányos, nem hivatkozott naplók:</b> %d</p>"
            "<p><b>Már hiányzó naplóra hivatkozó emlékek:</b> %d</p>"
            "<article><h3>Előzetes tisztítási besorolás</h3>"
            "<p><b>Feldolgozatlan: </b>%d (nem tisztítható)</p>"
            "<p><b>Tartós emlék forrása: </b>%d (forrásmegőrzést igényel)</p>"
            "<p><b>Feldolgozott, közvetlen hivatkozás nélkül: </b>%d (felülvizsgálandó)</p>"
            "<p><b>Minták — feldolgozatlan:</b> %s</p>"
            "<p><b>Minták — hivatkozott:</b> %s</p>"
            "<p><b>Minták — hivatkozás nélkül:</b> %s</p>"
            "<p>Ez nem törlési javaslat. A nem hivatkozott bejegyzések "
            "a beszélgetési előzmény miatt továbbra is hasznosak lehetnek.</p></article>"
            "<p><b>Legfeljebb 20 hivatkozott napló ID:</b> %s</p>"
            "<p>A nem hivatkozott bejegyzések sem automatikusan törölhetők; "
            "beszélgetési kontextust tartalmazhatnak.</p></article>"
            "<article><p><b>NINCS VÉGREHAJTÁS.</b> Tisztítás előtt konzisztens "
            "SQLCipher mentés és a recall.key megőrzése szükséges. A tartós emlékek "
            "source_turn hivatkozásait külön ellenőrizni kell.</p></article>"
            % (audit["total"], audit["complete"], audit["missing"],
               audit["missing_processed"], audit["missing_pending"],
               ", ".join("#%d" % x for x in audit["sample_missing_ids"]) or "—",
               audit["referenced_memories"], audit["referenced_turns"],
               audit["unreferenced_processed"], audit["orphan_sources"],
               preview["pending"]["count"],
               preview["linked"]["count"],
               preview["unlinked"]["count"],
               ", ".join("#%d" % x for x in preview["pending"]["sample_ids"]) or "—",
               ", ".join("#%d" % x for x in preview["linked"]["sample_ids"]) or "—",
               ", ".join("#%d" % x for x in preview["unlinked"]["sample_ids"]) or "—",
               ", ".join("#%d" % x for x in audit["sample_referenced_ids"]) or "—")
        )
    elif tab == "storage":
        disk = storage_metrics(store)
        body = ("<h2>Memória és tárhely</h2><div class='metrics'>"
                "<div class='metric'><strong>%d</strong><span>Tartós emlék</span></div>"
                "<div class='metric'><strong>%d</strong><span>45 napos naplóbejegyzés</span></div>"
                "<div class='metric'><strong>%s</strong><span>Adatbázis + WAL/SHM</span></div>"
                "<div class='metric'><strong>%s</strong><span>Szabad tárhely</span></div>"
                "</div><article><p>A tartós emlékeknek nincs rögzített darabszámkorlátja. "
                "A szabad hely a teljes adatpartícióra vonatkozik, nem külön "
                "Nabu Recall-kvóta. A méretek tájékoztató adatok.</p></article>" %
                (stats["memories"], stats["turns"],
                 escape(_bytes(disk["database"])),
                 escape(_bytes(disk["free"]))))
    else:
        body = "<h2>Utolsó visszakeresés</h2><article>%s</article>" % escape(
            state.get("last_recall", "Még nem történt visszakeresés."))
        body += "<h2>Utolsó AI-feldolgozás</h2><article>%s</article>" % escape(
            state.get("last_learn", "Még nem történt feldolgozás."))
        body += "<p>A napló szó szerinti, és 45 nap után törlődik. "
        body += "A tartós emlékek ettől függetlenül megmaradnak.</p>"
    summary = "".join(
        "<div class='metric'><strong>%s</strong><span>%s</span></div>" % (v, label)
        for v,label in [(stats["turns"], "Naplózott párbeszéd"),
                        (stats["pending"], "Feldolgozatlan"),
                        (stats["memories"], "Tartós emlék"),
                        (45, "Megőrzés (nap)")])
    content = ("<section class='metrics'>%s</section>%s<main>%s</main>"
               "<footer>A tartalomhoz Home Assistant bejelentkezés és "
               "külön Nabu Recall Web UI jelszó szükséges. "
               "A Web UI nem továbbít naplóadatot az OpenAI API-hoz.</footer>" %
               (summary, nav, body))
    return _page(content, state.get("version", "ismeretlen"), title)

def _signed_session(key, now=None):
    expiry = int(time.time() if now is None else now) + SESSION_AGE
    stamp = str(expiry)
    signature = hmac.new(key, stamp.encode(), hashlib.sha256).hexdigest()
    return stamp + "." + signature

def _valid_session(value, key, now=None):
    try:
        stamp, signature = value.split(".", 1)
        if not stamp.isdecimal() or len(stamp) > 12:
            return False
        if int(stamp) <= int(time.time() if now is None else now):
            return False
        expected = hmac.new(key, stamp.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    except (TypeError, ValueError, AttributeError):
        return False

def create_dashboard(store, state, password=None, ai=None, lock=None):
    """HA ingress restriction plus independent fail-closed password session."""
    password = password if password is not None else os.getenv("DASHBOARD_PASSWORD", "")
    key = secrets.token_bytes(32)  # Restart revokes all web sessions.
    attempts = []

    def headers(response):
        response.headers.update({
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "X-Frame-Options": "SAMEORIGIN",
            "Content-Security-Policy": (
                "default-src 'none'; style-src 'unsafe-inline'; "
                "form-action 'self'; base-uri 'none'; frame-ancestors 'self'")})
        return response

    @web.middleware
    async def ingress_only(request, handler):
        if request.remote not in ("172.30.32.2", "127.0.0.1", "::1"):
            raise web.HTTPForbidden()
        return await handler(request)

    def authorized(request):
        return bool(password) and _valid_session(
            request.cookies.get("recall_ui", ""), key)

    async def home(request):
        if not authorized(request):
            return headers(web.Response(
                text=login_page(state.get("version"), bool(password)),
                content_type="text/html"))
        tab = request.query.get("tab", "")
        return headers(web.Response(
            text=render(store, state, tab), content_type="text/html"))

    async def login(request):
        if not password:
            return headers(web.Response(
                text=login_page(state.get("version"), False),
                content_type="text/html", status=403))
        now = time.monotonic()
        attempts[:] = [x for x in attempts if now - x < 60]
        if len(attempts) >= 10:
            return headers(web.Response(
                text=login_page(state.get("version"), True, True),
                content_type="text/html", status=429))
        try:
            form = await request.post()
            supplied = form.get("password", "")
        except (ValueError, web.HTTPException):
            supplied = ""
        if not isinstance(supplied, str) or not hmac.compare_digest(
                supplied.encode("utf-8")[:1024], password.encode("utf-8")):
            attempts.append(now)
            return headers(web.Response(
                text=login_page(state.get("version"), True, True),
                content_type="text/html", status=401))
        attempts.clear()
        response = web.HTTPSeeOther(location="./")
        response.set_cookie("recall_ui", _signed_session(key),
                            max_age=SESSION_AGE, httponly=True,
                            samesite="Strict", path="/")
        headers(response)
        return response

    async def logout(request):
        response = web.HTTPSeeOther(location="./")
        response.del_cookie("recall_ui", path="/")
        headers(response)
        return response

    app = web.Application(middlewares=[ingress_only], client_max_size=4096)
    app.router.add_get("/", home)
    app.router.add_post("/login", login)
    app.router.add_post("/logout", logout)
    from maintenance_ui import setup_maintenance
    setup_maintenance(app, store, state, key, authorized, headers, _page, ai, lock)
    return app
