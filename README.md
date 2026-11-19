# 🧠 Nabu Recall v0.1.2

**Independent Home Assistant Voice memory**: 45-day verbatim rolling transcript and AI-curated durable facts. Built as a new project; the earlier Nabu Memory repositories remain unchanged.

## How it works

Every completed exchange (user utterance and actual assistant reply) is kept in local SQLite for **45 days**, then permanently deleted, without archive. An OpenAI API worker chooses long-term facts, merges updates, and makes relevance decisions. On each question, OpenAI proposes search expressions and selects the most relevant matching transcripts and durable memories. The existing HUN OpenAI Conversation agent remains responsible for device control.

- Explicit “jegyezd meg” requests receive processing as soon as they are logged.
- Background AI errors never intentionally block the voice assistant.
- All 45-day transcripts are kept even when the content is not worth long-term remembering.
- Logs older than 45 days are deleted even if not analyzed; this enforces strict retention but may lose unextracted memories.

## Install

See [TELEPITES_HU.md](TELEPITES_HU.md) for a Hungarian step-by-step guide. The initial developer build has **not been tested end-to-end on a live Home Assistant OS installation**.

## Limitations

Plaintext local SQLite in this version; no management UI or encrypted database yet. Relevance recall uses AI-generated keyword/phrase search, not embeddings, and may miss implicit matches. Fail-open turn writes can be lost on an abrupt Home Assistant shutdown. The app records only turns routed through the Nabu Recall conversation entity. Do not expose port 8765 or commit credentials. Keep the original upstream agent installed.

## Tests

Run `python -m unittest discover -s tests -v`.

MIT License.

## v0.1.2 fix

Fixed a repeated OpenAI HTTP 400 during search-term generation: JSON mode now always has explicit JSON output instructions. Removed the optional temperature parameter for broader chat-model compatibility. Existing SQLite data is not intentionally changed by this update.
