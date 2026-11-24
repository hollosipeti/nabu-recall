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
