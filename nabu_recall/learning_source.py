"""Small source-of-truth guards for automatic memory learning.

The model is useful at extracting facts, but only USER assertions can justify
automatic memories. Assistant answers and absence-of-data statements cannot.
Explicit commands continue to use the separate synchronous management path.
"""
import re

_QUESTION = re.compile(
    r"^\s*(?:mi(?:t|kor|ért)?|ki|kik|hol|hogy(?:an)?|melyik|"
    r"mennyi|hány|van[- ]e|tudod|tudsz|emlékszel|"
    r"biztosan|más|és\s+mi)\b", re.I
)
_ABSENCE = re.compile(
    r"\b(?:nincs\s+megadva|nem\s+ismert|ismeretlen|"
    r"nincs\s+(?:erről\s+)?információ|nem\s+tudjuk)\b", re.I
)


def assertion_turn(user_text: str) -> bool:
    """Questions, short challenges and uncertainty aren't new durable facts."""
    if not isinstance(user_text, str) or not user_text.strip():
        return False
    text = user_text.strip()
    if _QUESTION.search(text):
        return False
    if "?" in text and not re.search(r"\b(?:jegyezd\s+meg|emlékezz\s+rá)\b",
                                      text, re.I):
        return False
    return True


def credible_extracted_fact(fact: str) -> bool:
    if not isinstance(fact, str) or not fact.strip():
        return False
    return not _ABSENCE.search(fact)


# Narrow, fail-open optimization: only generic agenda questions without a
# named person, object, compound clause or reference to earlier conversation.
_AGENDA_ONLY = re.compile(
    r"^\s*(?:mi|mik|milyen események|milyen programok|milyen programjaim)"
    r"\s+(?:van|vannak|lesz|lesznek)\s+(?:(?:a|az)\s+)?"
    r"(?:naptárban|naptáramban|ma|mára|holnap|holnapra|hétvégén|jövő héten|"
    r"a következő két hétben|a következő héten|decemberben|januárban|februárban|"
    r"márciusban|áprilisban|májusban|júniusban|júliusban|augusztusban|"
    r"szeptemberben|októberben|novemberben)"
    r"(?:\s+a naptárban)?[?!. ]*$", re.I)


def live_agenda_only(text):
    return isinstance(text, str) and bool(_AGENDA_ONLY.fullmatch(text))


# Only standalone, unqualified commands on ordinary lighting entities qualify.
# Other devices, preferences, compound instructions and contextual follow-ups
# remain on the existing semantic path. This is intentionally conservative.
_LIGHT_CONTROL = re.compile(
    r"^\s*(?:kapcsold\s+(?:fel|le|be|ki)|oltsd\s+(?:el|le))\s+"
    r"(?:a|az)\s+(?:(?:nappali|konyhai|hálószobai|fürdőszobai|"
    r"garázsban\s+lévő|dolgozószobai|műhelyi)\s+)?"
    r"(?:lámpát|világítást|villanyt|fényt)[!.? ]*$", re.I)


def routine_control_only(text):
    return isinstance(text, str) and bool(_LIGHT_CONTROL.fullmatch(text))
