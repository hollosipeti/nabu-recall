"""Read-only diagnostics, only from HA Supervisor ingress on its dedicated port."""
from aiohttp import web
from datetime import datetime, timezone
from html import escape

def _time(value):
    return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if value else "—"

def render(store, state, tab="memories"):
    stats = store.statistics()
    title = "Nabu Recall — állapot"
    nav = '<nav><a href="./?tab=memories">Tartós emlékek</a> · <a href="./?tab=turns">45 napos napló</a> · <a href="./">Állapot</a></nav>'
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
    css = """
    body{background:#101722;color:#e9eef8;font:15px system-ui,sans-serif;
      max-width:900px;margin:20px auto;padding:0 16px}
    a{color:#59d9db}h1{color:#64dbd4}header{display:flex;align-items:center;gap:16px}
    .brain{font-size:42px}.metrics{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
    .metric,article{background:#1c2837;border:1px solid #304052;border-radius:12px;padding:14px}
    .metric strong{display:block;font-size:27px;color:#7fe7df}.metric span,small{color:#b3bdc9}
    article{margin:12px 0;overflow-wrap:anywhere}nav{margin:18px 0;line-height:2}
    p{white-space:pre-wrap}footer{color:#98a7b6;margin:24px 0}
    """
    return ("<!doctype html><html lang='hu'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<meta http-equiv='Cache-Control' content='no-store'>"
            "<title>Nabu Recall</title><style>%s</style></head><body>"
            "<header><span class='brain'>🧠</span><div><h1>%s</h1>"
            "<small>v0.2.0 · HAOS ingress · csak olvasható diagnosztika</small></div></header>"
            "<section class='metrics'>%s</section>%s<main>%s</main>"
            "<footer>Adatvédelem: a tartalom csak Home Assistant bejelentkezés után érhető el."
            " A felület nem továbbít naplóadatot az OpenAI API-hoz.</footer></body></html>"
            % (css, title, summary, nav, body))

def create_dashboard(store, state):
    async def home(request):
        # The Supervisor ingress proxy uses 172.30.32.2; never trust a spoofable header.
        if request.remote not in ("172.30.32.2", "127.0.0.1", "::1"):
            raise web.HTTPForbidden()
        tab = request.query.get("tab", "")
        response = web.Response(text=render(store, state, tab), content_type="text/html")
        response.headers.update({"Cache-Control": "no-store",
                                 "X-Content-Type-Options": "nosniff",
                                 "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"})
        return response
    app = web.Application()
    app.router.add_get("/", home)
    return app
