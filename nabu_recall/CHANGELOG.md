# Nabu Recall — maintained releases

## 1.1.9 — 2026-11-24 (HAOS app only; HA integration stays 1.0.10)
- Prefer verified current durable memories for unambiguous named-person preference questions, preventing obsolete 45-day journal dialogue from overriding corrected facts.
- After deletion, an old conversation cannot be used as an active preference.
- Keep the full 45-day conversation journal and its historical lookup unchanged; no database migration or data deletion.
- Add exact-person and preference-attribute isolation tests and HTTP correction/deletion regressions.
- Home Assistant integration, calendar tools, device controls and privacy policy unchanged.


## 1.1.8 — 2026-11-24 (HAOS app + companion integration 1.0.10)
- Integrated optional calendar selector and calendar tools; no separately installed calendar scripts.
- Corrected weekend/all-day calendar display and added exact per-day agenda queries.
- Automatic durable-memory learning ignores questions and missing-information statements; explicit memory editing remains separate.
- Idempotent repeated 'Mentsd el' when the previous fact is already stored verbatim.
- Timestamp-filtered yesterday-journal recall without treating timeless facts as dated conversations.
- Improved correction/deletion AI guidance and added privacy-safe diagnostics for unconfirmed operations.
- Added isolated, HTTP-level, packaging and date-window regression tests.
- Prior stable main preserved in branch stable-2026-11-24-before-memory-fixes; database format and encryption unchanged.


## 1.1.7 — 2026-11-23 (HAOS app + companion integration 1.0.9)
- Prevent ambiguous full-name collisions in exact identifier readback and selected-context enrichment.
- Add synthetic adversarial name-collision HTTP tests and calendar YAML/Jinja date/duration tests.
- Update the separately installed calendar-script example with deterministic next-week weekdays, explicit end times and actual start/end response data.
- Clarify the human-editable HA OpenAI prompt; these document/script changes require manual application in HA.
- Stable 1.1.6 / 1.0.8 snapshot: stable-2026-11-23-before-qa-fixes. Existing database and device-control routing unchanged.

## 1.1.6 — 2026-11-23 (HAOS app only)
- Fix critical startup failure: package structured_context.py into the add-on Docker image.
- Add release regression ensuring every local server import is copied to /app.
- No change to SQLCipher data, integration version or conversation logic.

## 1.1.5 — 2026-11-23 (HAOS app + companion integration 1.0.8)
- Strukturált adatkérésekhez hiányzó, ugyanazon személyhez tartozó tartós tények hozzáadása a keresési jelöltek közül; naplóbejegyzések kizárva.
- Az integráció egyetlen, teljes választ ad az egyértelmű születési dátum / TAJ / személyi igazolvány lekérdezésekre; nem módosítja az OpenAI streamelt válaszát.
- Hiányos, ellentmondásos vagy nyitott kérdés az eredeti OpenAI Conversation ügynökhöz kerül; a memóriatár, titkosítás és eszközvezérlés változatlan.

## 1.1.4 — 2026-11-23 (HAOS app only)
- Recall diagnosztika: a keresés jelölt és kiválasztott memória-/naplóazonosítóinak naplózása, személyes adatok nélkül.
- A keresési és memóriafeldolgozási működés nem változott.

## 1.1.3 — 2026-11-22 (HAOS app only)

- Replace the default brain emoji in the Ingress Web UI header with the existing Nabu Recall brand icon.
- No change to memory learning, database, privacy behavior, or Home Assistant integration 1.0.4.


## 1.1.2 — 2026-11-21 (HAOS app only)

- Shopping-list add/remove operations and their assistant confirmations are excluded from durable learning, but retained in the 45-day journal.
- Mixed dialogue batches still learn independent useful facts; explicit requests to remember enduring shopping preferences remain eligible.
- No existing memory is removed automatically. Review prior shopping-list task facts individually under Memóriakezelés.
- No changes to SQLCipher schema, private-data rules, Home Assistant integration v1.0.4, or device control.


## 1.1.1 — 2026-11-21 (HAOS app only)

- Atomic transaction: AI learned facts and processed conversation acknowledgments are committed together; rollback is verified on simulated SQLCipher write failure.
- More precise memory model guidance for same-person corrections, ownership, distinct additional items and selection of multiple relevant facts.
- No extra rules engine, schema changes, search index, changes to sensitive-identifier policy, or integration updates. Existing encrypted data is preserved.
- Full CI unit/API regression plus isolated database failure-injection tests; live model semantics still require HA validation.


## 1.1.0 — 2026-11-21 (HAOS app only)

- Hungarian accent-insensitive durable-memory lookup, prioritizing exact-accent matches while preserving stored original facts.
- One coalesced background learning worker; incoming turns remain pending until processed even during concurrent memory operations.
- Regression coverage for SQLCipher search, busy worker lock, authenticated bridge, OpenAI outage and recovery.
- Stable `nabu_recall` application slug and existing `/data` memory retained, no data migration.
- Custom Home Assistant conversation integration stays at 1.0.4; data/privacy policies unchanged.
- This release does not install the separate beta app or import its isolated test memory.


Only the latest two software release notes are kept here. Documentation updates do not bump application or integration versions. Previous commits and development notes remain available in the Git history and [../HISTORY.md](../HISTORY.md).

Documentation maintenance (2026-11-20): calendar YAML example updated for yearless `MM-DD` dates, consistent timezone-aware values, user manuals synchronized with integration v1.0.4. No runtime code change.

## 1.0.6 — 2026-11-21 (HAOS app only)

- Reorganizes Ingress diagnostics: separate journal-audit link removed from primary navigation; summary incorporated into the now clearer Memóriakezelés page, while the original read-only audit URL remains available for troubleshooting.
- Durable memory optimization shows the original facts, the proposed retained fact and the reason; every proposal has an unchecked checkbox.
- An explicit selection review screen precedes final approval. One to twelve selected independent merges are applied together in a single SQLCipher transaction or all rolled back on conflict.
- Entire most-recent approved checkbox batch can be undone transactionally, subject to the existing seven-day undo horizon and conflict checks.
- Selection and approval require the authenticated session, CSRF, a current nonce and a separate confirmation token.
- No automatic memory merging, no bulk-delete voice endpoint, no change to the HA custom integration v1.0.4 or the 45-day retention.
- Offline regression covers multiple selected merges, undo, stale/missing authorization and all-or-nothing rollback.

## 1.0.5 — 2026-11-20 (HAOS app only)

- 100,000-entry synthetic SQLCipher scale regression: storage, old fact retrieval, stable keyset paging, distant duplicate prefiltering.
- Recall and ongoing learning search the entire durable-memory corpus before sending a bounded relevant selection to the OpenAI model. No latest-200-only visibility limitation for lexical search.
- Voice-based explicit memory editing searches all stored facts by Hungarian query terms while retaining recent context.
- Hungarian Unicode casefold for accented-term matches; deterministic newest-first ordering on equal timestamps.
- Manual memory optimizer now offers whole-corpus lexical duplicate candidate scanning and separately paginated semantic AI review (up to 160 memories per request). Every suggestion requires individual confirmation; no autonomous consolidation.
- No guarantee of catching every semantic paraphrase. All memory AI calls remain bounded, and duplicate prefiltering is conservative.
- Existing archive retention, SQLCipher encryption, authenticated Ingress approval, undo and integration v1.0.4 remain unchanged.
- Full regression suite includes end-to-end HTTP recall of old facts and 100k synthetic SQLCipher records.

## 1.0.4 — 2026-11-20 (HAOS app only)

- Protected Ingress "Kézi karbantartás" page with a deliberate, manual approval flow.
- Journal cleanup archives only processed, unreferenced, blank-assistant rows in the existing SQLCipher DB. A stable snapshot digest is checked again inside a transaction; undo restores exact IDs and contents if no conflict.
- Archived transcripts obey the original 45-day retention period; the 27 referenced and 48 complete sample records remain untouched in the synthetic regression.
- New advisory AI memory optimizer suggests duplicate/overlap/conflict merges; each suggestion shows original facts, proposed text, reasoning and requires separate acceptance.
- Each approved merge is transactional and recorded for seven-day undo. Stale previews and conflicts are rejected.
- CSRF-bound authenticated maintenance POST endpoints exist only in the ingress UI; the bridge and voice agent do not gain cleanup tools.
- Tested with a 286-record synthetic fixture matching the supplied aggregate classification (211 eligible, 27 linked, 48 complete), undo and authentication scenarios.
- Companion integration remains v1.0.4. The baseline branches remain unchanged.

## 1.0.3 — 2026-11-20 (HAOS app only)

- Adds a password-protected, read-only journal audit with incomplete assistant replies, durable-memory source references, and disjoint cleanup preview categories.
- No deletion, archiving, edit or mutation controls were introduced. The diagnostic queries use SQL SELECT.
- Offline tests include 320 randomized synthetic journal rows, source links, a SQLCipher encrypted cold backup and restore validation.
- Separate app 1.0.3 / integration 1.0.4. The baseline and ALFA branches remain unchanged.
- Live deployment requires a verified HA backup. The test fixture is not a substitute for a real HA backup.

## 1.0.4 — 2026-11-20 (custom integration only)

- Fix HA IntentResponse assistant reply extraction: Home Assistant returns `response.speech` as a dictionary, while the previous integration accessed it as object attributes.
- Read either dictionary-style or attribute-style plain speech. No logging of user text or assistant responses.
- Regression tests cover both response representations and absent/non-string values.
- No modifications to the memory DB, SQLCipher encryption, bridge, memory extraction, retention, or HA device control.
- HAOS application remains v1.0.2; companion integration now v1.0.4.
- The frozen ALFA reference branch remains unchanged.

## 1.0.3 — 2026-11-20 (custom integration only)

- Clear, direct instructions for explicitly requested stored personal identifiers: provide only an exact, unambiguous retrieved value, never invent missing digits or automatically refuse solely by data type.
- If an identifier is not available, state that it could not be found rather than claiming it is forbidden.
- This does not authenticate the speaker of a shared home voice device.
- Only the HA integration prompt and the preserved sample user prompt were refined; memory AI, SQLCipher, API, and database remain unchanged. HAOS app remains v1.0.2.

