"""Relevance-safe completion of structured identifier facts.

The AI shortlist may omit a second fact for the *same* person. This helper
adds matching facts but cannot turn a shared first-name token into an identity.
Unknown subjects do not inherit other people's identifier records.
"""
import re
import unicodedata

IDENTIFIER = re.compile(r'\b(?:TAJ|személyi|igazolvány)\b', re.I)
SUBJECT = re.compile(
    r'^\s*(.+?)\s+(?=(?:születési|TAJ|személyi|igazolvány)\b)', re.I
)
PAREN_ALIAS = re.compile(r'^(.*?)\s*\(([^()]+)\)\s*$', re.I)


def norm(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold())
                   if not unicodedata.combining(c))


def _parse(fact):
    match = SUBJECT.match(fact)
    if match is None:
        return None
    heading = match.group(1).strip(' ,:')
    alias_match = PAREN_ALIAS.fullmatch(heading)
    name = alias_match.group(1).strip() if alias_match else heading
    aliases = {name}
    if alias_match:
        aliases.add(alias_match.group(2).strip())
    if len(name.split()) == 1 and norm(name).endswith(('nak', 'nek')):
        name = name[:-3]
        aliases.add(name)
    return norm(name), aliases


def _named(query, aliases):
    q = norm(query)
    for alias in aliases:
        a = re.escape(norm(alias))
        if re.search(r'(?<!\w)' + a +
                     r'(?:nak|nek|rol|tol|hoz|hez|t)?(?!\w)', q):
            return True
    return False


def enrich_selected_facts(query, selected, candidates):
    """Complete one unambiguous person's record without copying other IDs."""
    if not isinstance(query, str) or not IDENTIFIER.search(query):
        return selected
    requested = set()
    for item in candidates:
        parsed = _parse(item['fact'])
        if parsed and _named(query, parsed[1]):
            requested.add(parsed[0])
    if len(requested) != 1:
        # No reliable single subject: do not provide an unrelated identifier
        # selected by the relevance model as authoritative evidence.
        return [item for item in selected if not IDENTIFIER.search(item['fact'])]
    subject = next(iter(requested))
    result = []
    ids = set()
    for item in selected:
        parsed = _parse(item['fact'])
        if IDENTIFIER.search(item['fact']) and (not parsed or parsed[0] != subject):
            continue
        result.append(item)
        ids.add(item['id'])
    for item in candidates:
        parsed = _parse(item['fact'])
        if (parsed and parsed[0] == subject and
                IDENTIFIER.search(item['fact']) and item['id'] not in ids):
            if len(result) >= 16:
                break
            result.append(item)
            ids.add(item['id'])
    return result
