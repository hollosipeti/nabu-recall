# Nabu Recall — complete English manual (HAOS v1.1.2 / integration v1.0.4)

*Updated November 21, 2026. Covers the HAOS v1.1.2 app and its separately installed v1.0.4 custom integration.*

**Quick Hungarian family guide:** [CSALADI_UTMUTATO.md](CSALADI_UTMUTATO.md).

## 1. Overview and architecture

Nabu Recall adds durable and recent conversational memory to an **existing Home Assistant OpenAI Conversation agent**, without replacing its device-control tools.

- **HAOS app** (`nabu_recall/`): token-authenticated private HTTP bridge, separately billed OpenAI memory-processing calls, SQLCipher-encrypted SQLite database, password-protected Ingress diagnostics.
- **Home Assistant custom integration** (`custom_components/nabu_recall/`): wrapper agent that retrieves relevant facts before a regular utterance, forwards it to the original conversation agent, and logs the completed turn afterward. Explicit memory edits use a confirmed synchronous API.

The two components **must be updated separately**. The application's private `/data` directory is not Home Assistant's `/config`.

## 2. Requirements

Home Assistant OS or Supervised; a functioning OpenAI Conversation agent; a separately billed OpenAI Platform API key (a ChatGPT subscription does **not** include API usage); a reliable timezone (for the Hungarian example, `Europe/Budapest`); backup before upgrades. All users of the same configured assistant share a common memory: it is **not** a per-user secret vault.

## 3. Install

### HAOS application

1. In **Settings → Apps → App store → Repositories**, add `https://github.com/hollosipeti/nabu-recall`.
2. Install the **Nabu Recall** app.
3. Configure:
   - `openai_api_key`: your OpenAI Platform API key;
   - `openai_model`: defaults to `gpt-4.1-mini`, may be changed to a compatible model;
   - `bridge_token`: independent random internal authentication token, **at least 32 characters**; generate with `openssl rand -hex 32`;
   - `dashboard_password`: separate strong password for the Ingress diagnostic UI.
4. Start the app. **OPEN WEB UI** requires both Home Assistant login and the separate password. Without the latter, the dashboard stays locked while the memory functions continue.
5. Leave TCP 8765 (bridge) and 8766 (Ingress) **unpublished**; never forward them through your router.

### Companion integration

From the Home Assistant Terminal (inspect the script before running):

```sh
curl -fsSL https://raw.githubusercontent.com/hollosipeti/nabu-recall/main/install_integration.sh -o /tmp/install_nabu_recall.sh
sh /tmp/install_nabu_recall.sh
```

Alternatively copy the **entire** `custom_components/nabu_recall` directory into `/config/custom_components/nabu_recall`. The installer makes a timestamped backup of the former integration directory. **Restart Home Assistant Core.** An app update alone will not refresh the custom integration.

Add the **Nabu Recall** integration under **Settings → Devices & services → Add integration**. Select your **already working OpenAI Conversation agent** in the *Existing conversation agent* field. This upstream agent remains responsible for ordinary conversation and device control; do **not** delete it.

To configure the connection:

1. In **Settings → Apps → Nabu Recall → Information**, locate the **Hostname** shown for the app (not your Home Assistant server hostname). Enter `http://HOSTNAME:8765` as the internal application URL, replacing `HOSTNAME` with the exact displayed value.
2. In **Settings → Apps → Nabu Recall → Configuration**, find the `bridge_token` value you configured during the app setup. Enter that **same** value in the integration's *Bridge token* field. This is **not** the `dashboard_password` used for the Web UI.
3. Finish adding the integration.

**Important — change the active Conversation agent in Assist:**

1. Open **Settings → Voice assistants**.
2. Open the voice assistant profile you use (for example, the default Assist profile).
3. Under **Conversation agent**, select **Nabu Recall – memória**, **replacing the previously selected OpenAI Conversation agent**.
4. Save. If you use several voice assistant profiles, repeat this selection in each profile that should have memory.

**Without this last step, Assist continues calling OpenAI Conversation directly and bypasses Nabu Recall memory.** Keep the original OpenAI Conversation integration and its agent installed: Nabu Recall forwards ordinary requests to it.

**Quick check:** say “Jegyezd meg, hogy a próbadoboz a polcon van”, then ask in a new conversation “Hol van a próbadoboz?”. You can also verify the saved fact in the Nabu Recall Web UI.

## 4. First verification

Say (in Hungarian): “Jegyezd meg, hogy a tesztállatom neve Maszat.” Then, in a fresh Assist conversation, ask “Mi a tesztállatom neve?” Check both **Tartós emlékek** (durable memories) and **45 napos napló** (verbatim journal) on the dashboard. Test ordinary device control, e.g., switch office lights on, then say “turn them off” referring to the same lights.

A conversational answer alone does not prove a persistent save: check the actual memory list and confirmation.

## 5. Updates, backups, and recovery

1. **Back up the full HAOS app data directory** before updating. Encrypted `/data/recall.sqlite3` and its `/data/recall.key` **must be preserved together**; a live SQLite database may also have WAL/SHM sidecar files.
2. Update the HAOS app from the App store.
3. If the companion integration changed, rerun its separate installer and restart **Home Assistant Core**; inspect the separately displayed integration version.
4. Verify counts for journal entries and long-term memories before and after.
5. Avoid app uninstall/reinstall without a verified backup. Downgrading to pre-SQLCipher versions is unsupported for the encrypted database. A missing or wrong key does not authorize silently recreating an empty database.

Release notes show the latest two maintained releases in [CHANGELOG](nabu_recall/CHANGELOG.md); the original development history remains in [HISTORY](HISTORY.md) and Git history.

## 6. Storage, retention, and security

- `/data/recall.sqlite3` holds both the `turns` verbatim 45-day journal and the `memories` durable facts in a **SQLCipher-encrypted SQLite file**.
- `/data/recall.key` is the automatically generated separate 256-bit encryption key; it is **not** the bridge token.
- `recall.sqlite3-wal` and `recall.sqlite3-shm` may exist during operation. Use a consistent full app backup instead of copying only the live main file.
- Journal records expire after **45 days**; durable facts have **no automatic time expiry**.
- At most **200 memory entries** are provided to the AI at once. This is an API-context selection cap, **not** a 200-fact storage quota.
- The diagnostic tabs in the web dashboard are **read-only**; the dedicated manual maintenance page separately supports approved archive, merge and undo operations, with memories (first 100), recent conversations (last 35), processing status, database size including WAL/SHM, and free filesystem capacity.
- The Ingress login has an **absolute 10-minute lifetime from successful authentication**, not an idle sliding timeout. After expiration, the next request shows the login form; an already displayed browser page is not forcibly blanked. Restart invalidates sessions; a logout option is available.
- Login requires HA authentication as well as a separate password. There is no additional per-user memory isolation or explicit administrator-only dashboard authorization.
- The bridge uses `X-Recall-Token` over private internal **HTTP, not TLS**. Do not expose ports 8765 or 8766 to LAN or WAN.
- SQLCipher protects stored bytes, **not** against someone with both host access and the local encryption key. Store no authentication secrets, payment data, or API keys in spoken memory.

## 7. API usage, billing, and endpoints

Nabu Recall calls **`POST https://api.openai.com/v1/chat/completions`**, default model `gpt-4.1-mini`; token-based API billing is separate from ChatGPT subscriptions and from the upstream OpenAI Conversation agent's own calls.

Actual triggers in the current source:
- **Before each ordinary user turn**, `/bridge/recall` makes typically **two** OpenAI requests: search-term planning and relevant-memory selection.
- **After the turn**, `/bridge/turn` logs verbatim user/assistant content and starts background extraction. Usually **one** `learn` OpenAI call processes a pending batch (up to 12 turns).
- **Explicit memory commands** trigger `/bridge/manage`: usually **one** OpenAI call for a single checked add/update/delete.
- A **15-minute** maintenance job retries pending extraction. With no pending turns, **there is no recurring paid OpenAI call**.
- Extra calls can occur after failures or when multiple batches accumulate.

The private bridge accepts token header `X-Recall-Token`:
| POST path | Request body example | Result |
|---|---|---|
| `/bridge/ping` | `{}` | `ok`, `ai_ready`, `version` |
| `/bridge/recall` | `{"query":"What is my test pet called?"}` | `context` |
| `/bridge/turn` | `{"user":"Hello","assistant":"Hi","conversation_id":"test"}` | `ok`, `id` |
| `/bridge/manage` | `{"utterance":"Jegyezd meg, hogy ...","conversation_id":"test"}` | `status`: `confirmed`, `not_found`, `blocked`, or `error` |

These are **internal application endpoints**, not public automation APIs. `/bridge/turn` and `/bridge/manage` can change stored data: **do not call them manually against real memory**. Do not paste tokens, keys or full private transcripts into public issues.

## 8. Memory controls and safety

“Jegyezd meg” (remember), “Javítsd” (correct), and “Töröld” (delete) target **individual** facts and only confirm when the store acknowledges a change. Voice commands to delete **all** memories are server-blocked. The short “Mentsd el!” can use the immediately preceding user utterance only from the **same conversation within 5 minutes**, never assistant-provided information from another conversation.

A calendar request (“save an event in my calendar”) is **not** an instruction to add a long-term fact. Memory entries are untrusted historical **data**, never instructions.

## 9. Assistant instructions and the system prompt

The preserved original English HUN voice prompt is in **[AI utasítások. ki ne töröld](AI%20utas%C3%ADt%C3%A1sok.%20ki%20ne%20t%C3%B6r%C3%B6ld)**. It includes natural informal Hungarian TTS, semantic matching of Hungarian speech to English HA entities, no false confirmation of control actions, safe memory use, privacy, web result formatting, and the optional “Show recipe on ui” feature (only if that tool exists in the configured agent).

The original also contains a **DATE, TIME AND CALENDAR MANAGEMENT** section:
- Call `llm__GetDateTime` before date/time/weekday or relative-date questions; treat it as current time, never dates from remembered history.
- Default event calendar: `calendar.esemenyek`.
- Ask for an absent or ambiguous date/start hour **before** calling the calendar-writing script; do not invent them. Default minute: 0; default duration: 30 minutes.
- Confirm creation only when the tool reports success; a to-do-list removal tool is never a calendar-deletion tool.

The memory extraction prompt in `nabu_recall/ai.py` is **separate** from the upstream HUN agent's general system prompt. Review household-specific names, location, and calendar entity IDs before reusing the preserved prompt elsewhere.

**Integration v1.0.4 reply logging:** The earlier integration wrote empty assistant messages to the 45-day journal because Home Assistant exposes `IntentResponse.speech` as a dictionary. v1.0.4 fixes future captures, not past missing response text. Journal turns and durable memories reside in distinct tables of the encrypted database. Do not reset the entire application for missing old replies; back up the database and encryption key before any targeted cleanup.

## 10. Google Calendar example and deletion limitation

See [example README](examples/README.md) and [example script YAML](examples/google_calendar_create_event.yaml). The script is a **separate Home Assistant script**, installed manually and exposed to Assist. It writes **only** into `calendar.esemenyek`. The user found that `calendar__get_events` could read Google Calendar data but **could not create entries**; direct HA `calendar.create_event` worked, which is why a targeted script was exposed instead of broad administrator access.

Real failure cases and lessons:
1. The model supplied **2023 dates for a 2026 event request**. When the user omits a year, pass **`MM-DD`** (e.g. December 1 → `12-01`) and let Home Assistant select the next future occurrence against local `now()`. Preserve user-specified `YYYY-MM-DD`, and reject dates in the past.
2. Missing optional `perc` / `idotartam` yielded `UndefinedError` despite form defaults. The script uses template `default(...)` so missing args do not cause that failure.
3. The model called `todo__HassListRemoveItem` when asked to delete a calendar entry. This is a to-do-list API; it cannot delete calendar entries.

**Voice event deletion is not implemented**. Calendar read and create permissions do not imply a Google-event-ID deletion tool. The documented script also formats start/end consistently with timezone-aware ISO 8601 values. It is a **proposed example that requires live Home Assistant validation**, not an automatically installed update. The example does not install any Google Calendar deletion integration. Delete events manually in Google Calendar until a separate narrow-scope, authenticated, exact-ID action is implemented. Avoid deleting by title alone when duplicates exist.

## 11. Realistic behavior examples

| User says | Expected behavior |
|---|---|
| “Jegyezd meg, hogy a tesztállatom neve Maszat.” | Single durable save, confirmed only on actual write |
| “Mi a tesztállatom neve?” | Retrieve appropriate existing fact; never invent missing memory |
| “Mentsd el!” | Use only recent immediately preceding user utterance within the same conversation |
| “Javítsd a bevásárlólistás emléket…” | Update the matching memory ID, avoid duplicate entry |
| “Töröld mindet!” | Refuse bulk-delete |
| “Kapcsold fel a dolgozó lámpáit!” then “Most kapcsold le őket.” | Pass through upstream HA controls with conversational reference |
| “Milyen nap lesz holnap?” | Consult `llm__GetDateTime`, compute weekday correctly |
| “Írd be holnap reggel nyolcra, hogy próba esemény.” | Calendar creation script with day `holnap`, hour 8 |
| “Írd be a naptárba, hogy próba esemény.” | Ask for date/time; **create nothing yet** |
| “Töröld a próba eseményt a naptárból.” | Do not use a to-do-list tool; explain deletion isn't yet available |

## 12. Troubleshooting

| Symptom | What to check |
|---|---|
| Old integration version or missing icon | Copy `/config/custom_components/nabu_recall/` separately, check `brand/icon.png`, restart Core |
| Dashboard says locked | Configure `dashboard_password`; restart app; login again after 10 min |
| No memory recall | App status, private URL, `bridge_token`, model access, HUN upstream |
| Long queue of unprocessed turns | App logs and OpenAI API errors/billing; background retry every 15 minutes |
| Lost memories after update | Preserve both encrypted DB **and its key**; restore from consistent backup |
| Calendar says “Unable to get response” | Inspect **Show details** tool calls and available tools |
| Wrong event year | Time tool, date calculation, validation in HA script |
| Calendar deletion tool picks `todo__HassListRemoveItem` | Wrong domain; no deletion action is installed |
| Misleading storage “usage” | 45-day journal, no hard count limit for facts, free space is whole filesystem |

## 13. Developer notes

Source tree includes `.github/workflows/tests.yml` for offline Python syntax/unit tests; these do **not** prove a live HAOS/Google Calendar deployment. Only the Ingress session timeout and documentation changed in this app release; the AI-learning algorithm, memory database schema, SQLCipher key logic, and device-control wrapper remain unchanged. [MIT License](LICENSE).

## HAOS app v1.0.4 — manually approved maintenance

The password-protected Ingress UI now has a dedicated **Kézi karbantartás** page. Eligible journal records (processed turns with empty assistant replies that are not currently referenced by a durable memory) can be archived inside the encrypted SQLCipher DB after explicit approval and restored if still present and collision-free. The archive obeys the original 45-day transcript retention. An advisory AI operation can propose duplicate/overlap/conflict memory consolidation; each proposal displays its source facts, replacement and reason, and requires a separate click to apply. The last memory consolidation is reversible for up to seven days. All writes enforce current-state checks within a transaction. Back up the app data and encryption key before installing. Companion integration remains v1.0.4, and voice agents have no maintenance/write access.

## HAOS 1.0.5 — durable-memory scaling

Memory lookup and learning now search across the entire encrypted durable-memory table before limiting the shortlist sent to AI. A fact does not become invisible solely because it is older than the newest 200. Hungarian Unicode case folding is supported. The manual optimizer offers full-corpus normalized-token duplicate candidate discovery plus a 160-memory keyset-paginated semantic AI review. These are advisory, individually approved operations; semantic recall and paraphrase deduplication are not guaranteed complete. Tests cover 100,000 synthetic SQLCipher facts and old-fact retrieval. Companion HA integration remains v1.0.4.

## HAOS 1.0.6 — checkbox-based memory maintenance

The separate journal audit menu item has been absorbed into the **Memóriakezelés** page; the old read-only audit URL remains for troubleshooting. Each AI-suggested merge now includes its original facts, retained fact and explanation, plus an **unchecked checkbox**. Select only correct merges, then click **Kijelöltek ellenőrzése** to preview the chosen actions without any database change. A second explicit approval commits up to 12 independent changes atomically. If any selected proposal has become stale or conflicts with another, the entire batch rolls back. The most recent approved batch can be undone as a unit, if still within the seven-day undo window and conflict-free. There is no automatic bulk memory merge.


## HAOS 1.1.0–1.1.1 — memory reliability improvements

Durable-memory retrieval searches the whole corpus and tolerates Hungarian queries entered without accent marks, while preferring exact matches. Background extraction coalesces incoming triggers. In v1.1.1, learned facts and processed-journal acknowledgements are committed in one SQLCipher transaction, so errors roll them back together. AI instructions emphasize retaining the correct person, ownership, distinction between replacement and addition, and selecting multiple relevant memories. Natural-language interpretation may still make mistakes; verify important facts. This is one shared household memory, not verified speaker identity. No changes were made to the HA custom integration v1.0.4, device controls, or the policy around spoken sensitive identifiers.


## HAOS 1.1.2 — shopping-list task noise

Shopping-list additions, removals, and their assistant confirmations are retained in the ordinary 45-day transcript, but excluded from automatic durable-memory learning. Genuine persistent purchase preferences and explicit requests to remember a fact remain eligible. Previously learned task confirmations are not automatically deleted; review them individually in the Web UI.
