# Nabu Recall — maintained releases

The repository keeps the latest two release notes here. The development history is retained in [../HISTORY.md](../HISTORY.md) and Git commits/tags; previous working source code is not removed from Git history.

## 1.0.3 — 2026-11-20 (custom integration only)

- Clear, direct instructions for explicitly requested stored personal identifiers: provide only an exact, unambiguous retrieved value, never invent missing digits or automatically refuse solely by data type.
- If an identifier is not available, state that it could not be found rather than claiming it is forbidden.
- This does not authenticate the speaker of a shared home voice device.
- Only the HA integration prompt and the preserved sample user prompt were refined; memory AI, SQLCipher, API, and database remain unchanged. HAOS app remains v1.0.2.

## 1.0.2 — 2026-11-20

- HAOS app: dashboard password session lifetime reduced from 8 hours to **10 minutes**, measured from login; new requests require re-authentication after expiry.
- Complete maintained Hungarian and English manuals, accurate SQLCipher/backup/API/security documentation.
- Google Calendar creation YAML example and explanation of unsupported calendar deletion, natural Hungarian interaction examples, prompt guidance.
- Clean Home Assistant application Documentation tab and concise project README.
- Memory/AI processing, database schema, encryption, retention and device control **unchanged**.
- The separately installed companion integration remains v1.0.2; copying its files is necessary only when updating it.
