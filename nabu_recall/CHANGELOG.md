# Nabu Recall — maintained releases

Only the latest two release notes are kept here. Previous commits and development notes remain available in the Git history and [../HISTORY.md](../HISTORY.md).

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

