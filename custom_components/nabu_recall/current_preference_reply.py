"""Deterministic single-fact readback of current durable preference snapshots.

Avoid stale upstream OpenAI chat history overriding a confirmed update.
This path is deliberately limited to a simple, named-person question.
All other queries keep the existing HA OpenAI conversation path.
"""
import re
import unicodedata

_QUERY = re.compile(
    r"^\s*Mi\s+(?P<name>[A-ZÁÉÍÓÖŐÚÜŰ][\w-]+\s+"
    r"[A-ZÁÉÍÓÖŐÚÜŰ][\w-]+)\s+kedvenc\s+"
    r"(?P<attribute>gyümölcse|itala|étele|színe)\s*\?\s*$", re.I
)
_MISSING = "NO CURRENT FACT STORED FOR REQUESTED PERSON AND PREFERENCE."


def _fold(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold())
                   if not unicodedata.combining(c))


def extract_current_preference(query, context):
    """Answer only a single clearly identified fact, never from journal text."""
    if not isinstance(query, str) or not isinstance(context, str):
        return None
    match = _QUERY.fullmatch(query)
    if match is None or not context.startswith("CURRENT CONFIRMED DURABLE FACTS ONLY."):
        return None
    fact_lines = [line[6:].strip() for line in context.splitlines()
                  if line.startswith("Fact: ")]
    if not fact_lines and _MISSING in context:
        return "Ezt az adatot most nem találom a memóriámban."
    name, attribute = _fold(match.group("name")), _fold(match.group("attribute"))
    valid = []
    for fact in fact_lines:
        m = re.fullmatch(
            r"(?P<name>.+?)\s+kedvenc\s+"
            r"(?P<attribute>gyümölcse|itala|étele|színe)\s+"
            r"(?P<value>.+?)[.!]?", fact, flags=re.I)
        if (m and _fold(m.group("name")) == name and
                _fold(m.group("attribute")) == attribute and
                m.group("value").strip()):
            valid.append(fact.rstrip(".! ") + ".")
    if len(valid) == 1:
        return valid[0]
    return None
