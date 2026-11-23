"""Conservative readback of structured facts from durable memories.

Never use journal turns. If any question part is not understood or values
conflict, leave the entire request to the original HA conversation agent.
"""
import re
import unicodedata

TAJ = re.compile(r'\bTAJ(?:[\s-]*sz[aá]m\w*)?\s*[:=]?\s*(\d{9})\b', re.I)
CARD = re.compile(r'\bszemélyi(?:\s+igazolvány)?(?:[\s-]*sz[aá]m\w*)?\s*[:=]?\s*([A-Z0-9]{7,12})\b', re.I)
BIRTH = re.compile(r'\bszület(?:ési|ett)\s+(?:dátuma|ideje|napja)?\s*[:=]?\s*(\d{4}\.\s*[a-záéíóöőúüű]+\s+\d{1,2}\.)', re.I)
TAJ_REQUEST = re.compile(r'\btaj(?:[\s-]*sz[aá]m\w*)?\b', re.I)
CARD_REQUEST = re.compile(r'\bszemélyi(?:\s+igazolvány)?(?:[\s-]*sz[aá]m\w*)?\b|\bigazolvány(?:[\s-]*sz[aá]m\w*)?\b', re.I)
BIRTH_REQUEST = re.compile(r'\b(?:szület\w*|szülinap\w*)\b', re.I)
OPEN_REQUEST = re.compile(r'\b(?:mit\s+tudsz|mesél\w*|mondj\s+el|jellem\w*|miért|hogyan|milyen|hány|kapcsold|állítsd|töröld|módosítsd|jegyezd|mentsd|ne\s+(?:mondd|add))\b', re.I)
# A person's full name is the complete prefix before a structured attribute.
# Do not treat the first token of a multiword name as a separate identity.
SUBJECT = re.compile(
    r'^\s*(.+?)\s+(?=(?:születési|TAJ|személyi|igazolvány)\b)', re.I
)
PAREN_ALIAS = re.compile(r'^(.*?)\s*\(([^()]+)\)\s*$', re.I)


def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold())
                   if not unicodedata.combining(c))


def _matches_name(query, aliases):
    normalized = norm(query)
    for alias in aliases:
        escaped = re.escape(norm(alias))
        # Optional Hungarian case suffix on the complete name, not its first word.
        for found in re.finditer(
                r'(?<!\w)' + escaped +
                r'(?:nak|nek|rol|tol|hoz|hez|hon|ban|ben|t)?(?!\w)',
                normalized):
            # Do not mistake the first word of a capitalized full name
            # for a distinct person: "Teszt Géza" != "Teszt".
            if len(alias.split()) == 1:
                after = query[found.end():]
                next_word = re.match(r'\s+([A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüű]+)', after)
                if next_word and norm(next_word.group(1)) not in (
                    'taj', 'szemelyi', 'igazolvany'):
                    continue
            return True
    return False


def _fact_aliases(fact):
    match = SUBJECT.match(fact)
    if match is None:
        return None
    full_subject = match.group(1).strip(' ,:')
    if parenthesized := PAREN_ALIAS.fullmatch(full_subject):
        primary = parenthesized.group(1).strip()
        aliases = {primary, parenthesized.group(2).strip()}
    else:
        primary = full_subject
        aliases = {primary}
    # "Enikőnek születési dátuma..." is an inflected name.
    if len(primary.split()) == 1 and primary.casefold().endswith(('nak', 'nek')):
        primary = primary[:-3]
        aliases.add(primary)
    if not primary or any(not part or not part[0].isalpha()
                          for part in primary.split()):
        return None
    return primary, aliases


def extract_precise(query, context):
    """One final reply only when every requested field has one grounded value."""
    if not isinstance(query, str) or not isinstance(context, str):
        return None
    if OPEN_REQUEST.search(query):
        return None
    field_matches = []
    for key, pattern in (('taj', TAJ_REQUEST), ('card', CARD_REQUEST),
                         ('birth', BIRTH_REQUEST)):
        if match := pattern.search(query):
            field_matches.append((match.start(), key))
    if not field_matches:
        return None
    fields = [key for _, key in sorted(field_matches)]
    # Never silently answer only half of a compound question.
    if re.search(r'\bés\b', query, re.I):
        for clause in re.split(r'\bés\b', query, flags=re.I):
            if not any(pattern.search(clause) for pattern in
                       (TAJ_REQUEST, CARD_REQUEST, BIRTH_REQUEST)):
                return None
    people = {}
    for line in context.splitlines():
        if not line.startswith('Fact: '):
            continue
        fact = line[6:]
        names = _fact_aliases(fact)
        if names is None:
            continue
        subject, aliases = names
        if not _matches_name(query, aliases):
            continue
        entry = people.setdefault(norm(subject), {
            'name': subject, 'values': {'taj': set(), 'card': set(), 'birth': set()}
        })
        for field, pattern in (('taj', TAJ), ('card', CARD), ('birth', BIRTH)):
            for hit in pattern.finditer(fact):
                entry['values'][field].add(hit.group(1).strip())
    if len(people) != 1:
        return None
    person = next(iter(people.values()))
    if any(len(person['values'][field]) != 1 for field in fields):
        return None
    result = []
    for field in fields:
        value = next(iter(person['values'][field]))
        if field == 'taj':
            result.append(f"{person['name']} TAJ-száma: {', '.join(value)}.")
        elif field == 'card':
            result.append(f"{person['name']} személyi igazolvány száma: {value}.")
        else:
            result.append(f"{person['name']} születési dátuma: {value}")
    return ' '.join(result)
