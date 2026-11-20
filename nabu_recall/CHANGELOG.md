# Nabu Recall — maintained releases

Only the latest two software release notes are kept here. Documentation updates do not bump application or integration versions. Previous commits and development notes remain available in the Git history and [../HISTORY.md](../HISTORY.md).

Documentation maintenance (2026-11-20): calendar YAML example updated for yearless `MM-DD` dates, consistent timezone-aware values, user manuals synchronized with integration v1.0.4. No runtime code change.

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

