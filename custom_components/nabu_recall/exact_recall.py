"""Exact, unambiguous readback of explicitly requested stored TAJ numbers.

Only consumes already selected durable Fact lines. Never searches transcripts
or guesses a person's identity from a conversation or device.
"""
import re

_TAJ_QUESTION = re.compile(r"\btaj(?:[\s-]*sz[aá]m\w*)?\b", re.I)
_TAJ_VALUE = re.compile(r"\bTAJ[\s-]*sz[aá]m\w*\s*[:=]?\s*(\d{9})\b", re.I)
_PERSON = re.compile(r"^Fact:\s*([^\W\d_][\w-]*)(?:\s*\(([^()]+)\))?", re.I)
_BIRTH = re.compile(r"születési dátuma\s+(\d{4}\.\s*[\wáéíóöőúüű]+\s+\d{1,2}\.)", re.I)


def exact_taj_answer(query, context):
    """Return a readback only for one clearly identified durable record."""
    if not isinstance(query, str) or not isinstance(context, str):
        return None
    if not _TAJ_QUESTION.search(query):
        return None
    if re.search(r"\b(?:ne\s+(?:mondd|add)|nem\s+kérem)\b", query, re.I):
        return None
    query_words = set(re.findall(r"[^\W_]+", query.casefold()))
    # Never answer a multiple-person request with a single person's number.
    if "apa" in query_words and "anya" in query_words:
        return None
    matches = set()
    for line in context.splitlines():
        if not line.startswith("Fact: "):
            continue
        person = _PERSON.match(line)
        number = _TAJ_VALUE.search(line)
        if person is None or number is None:
            continue
        aliases = [person.group(1), person.group(2)]
        if not any(alias and alias.casefold() in query_words for alias in aliases):
            continue
        # Number is read digit by digit for unambiguous Hungarian TTS.
        birth = _BIRTH.search(line)
        matches.add((person.group(1), number.group(1),
                     birth.group(1) if birth else ""))
    if len(matches) != 1:
        return None
    subject, digits, birth = matches.pop()
    prefix = f"{subject} születési dátuma: {birth} " if (
        birth and re.search(r"\bszület\w*\b", query, re.I)) else ""
    return f"{prefix}{subject} TAJ-száma: {', '.join(digits)}."
