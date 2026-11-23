"""Complete identifier facts from ranked durable-memory candidates.

Never reads historical journal turns. No modifications to storage or AI rank.
"""
import re
import unicodedata

IDENTIFIER = re.compile(r'\b(?:taj|személyi|igazolvány)\b', re.I)
HEADING = re.compile(r'^([^\W\d_][\w-]*)(?:\s*\(([^()]*)\))?', re.I)

def norm(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold())
                   if not unicodedata.combining(c))

def enrich_selected_facts(query, selected, candidates):
    """Append requested person's missing durable identifier facts, max 16.

    If the subject is ambiguous, leave the AI-selected facts unchanged.
    """
    if not isinstance(query, str) or not IDENTIFIER.search(query):
        return selected
    words = set(re.findall(r'[^\W_]+', norm(query)))
    subjects = set()
    parsed = []
    for item in candidates:
        heading = HEADING.match(item["fact"])
        if not heading:
            continue
        name = heading.group(1)
        aliases = [name]
        if heading.group(2):
            aliases.append(heading.group(2))
        if any(norm(alias) in words for alias in aliases):
            subjects.add(norm(name))
        parsed.append((item, norm(name)))
    if len(subjects) != 1:
        return selected
    subject = next(iter(subjects))
    seen = {item["id"] for item in selected}
    extended = list(selected)
    for item, name in parsed:
        if name != subject or item["id"] in seen:
            continue
        if not IDENTIFIER.search(item["fact"]):
            continue
        extended.append(item)
        seen.add(item["id"])
        if len(extended) >= 16:
            break
    return extended
