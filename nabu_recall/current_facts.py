"""Prefer confirmed durable facts over 45-day dialogue for current preferences.

Narrow opt-in: only unambiguous named-person preference questions, not
conversation-history queries. Historical journal is never deleted or changed.
"""
import re
import unicodedata

PREFERENCE = re.compile(
    r"\b(?:kedvenc(?:e|ét|ei|ei[tr]|\w*)?|szeret\s+(?:inni|enni))\b", re.I
)
HISTORY = re.compile(
    r"\b(?:korábban|régebben|tegnap|múltkor|"
    r"beszéltünk|mondtam|mondtad|emlékszel|régen)\b", re.I
)
SUBJECT = re.compile(
    r"\b(?:mi|mit|milyen|mennyi)\s+"
    r"(?P<name>[A-ZÁÉÍÓÖŐÚÜŰ][\w-]+(?:\s+[A-ZÁÉÍÓÖŐÚÜŰ][\w-]+)?)\s+"
    r"(?:kedvenc\w*|szeret\s+(?:inni|enni))", re.I
)


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(c))


def current_preference_subject(query):
    """Return a precisely named subject, or None to preserve normal retrieval."""
    if not isinstance(query, str) or HISTORY.search(query) or not PREFERENCE.search(query):
        return None
    match = SUBJECT.search(query)
    return fold(match.group("name")) if match else None


def authoritative_preferences(query, memories):
    """Return current durable facts for a named person's requested preference.

    None means the query is outside this narrowly scoped safeguard. An empty
    list means the precise current attribute is not stored; old transcript
    text must not silently recreate a deleted or corrected preference.
    """
    name = current_preference_subject(query)
    if name is None:
        return None
    # Distinguish favourite fruit from favourite drink, even for one person.
    attribute = re.search(r"\bkedvenc\w*\s+(\w+)", query, re.I)
    attribute = fold(attribute.group(1)) if attribute else None
    result = []
    for item in memories:
        fact = item.get("fact", "")
        normalized = fold(fact)
        if not re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", normalized):
            continue
        if not PREFERENCE.search(fact):
            continue
        if attribute and not re.search(r"(?<!\w)" + re.escape(attribute) + r"(?!\w)", normalized):
            continue
        result.append(item)
    return result
