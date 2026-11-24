"""Lightweight Hungarian memory-command routing. No new memory layers."""
import re
import unicodedata

DELETE = re.compile(r"\b(?:töröld|törölj|felejtsd|felejts|távolítsd|távolíts)\b", re.I)
EDIT = re.compile(r"\b(?:javítsd|javítsuk|javíts|javítsam|módosítsd|módosítsuk|módosíts|változtasd|írd\s+át|helyesbítsd|helyesbíts|ki\s+kell\s+javítani|ezt\s+is\s+javítsuk)\b", re.I)
SAVE = re.compile(r"\b(?:jegyezd\s+meg|emlékezz\s+(?:rá|arra)|mentsd\s+el|mentsük\s+el|tárold\s+el|rögzítsd)\b", re.I)
BULK = re.compile(r"\b(?:mindent|mindet|minden|összes(?:et|t)?|valamennyit|teljes(?:en)?|reset|full\s*clean|ürítsd|minden\s+emlék)\b", re.I)

# Requests targeting the Home Assistant calendar are actions, not durable-memory commands.
CALENDAR_DESTINATION = re.compile(
    r"\b(?:naptárba|naptárban|naptárból|naptáramba|naptáramban|"
    r"naptáradba|naptáradban|naptáresemény\w*|naptárbejegyzés\w*)\b", re.I)

def calendar_action(text):
    if not isinstance(text, str):
        return False
    # An explicit "remember that..." is a memory fact even if it mentions a calendar.
    if re.search(r"\b(?:jegyezd\s+meg|emlékezz\s+(?:rá|arra))\b", text, re.I):
        return False
    return bool(CALENDAR_DESTINATION.search(text))

def operation_kind(text):
    if not isinstance(text, str) or len(text) > 2000:
        return None
    if calendar_action(text):
        return None
    if DELETE.search(text) or EDIT.search(text):
        if BULK.search(text):
            return "blocked"
        return "delete" if DELETE.search(text) else "update"
    if SAVE.search(text):
        return "add"
    return None

def validate_change(kind, operations, memories):
    if kind not in ("delete", "update", "add") or not isinstance(operations, list) or len(operations) != 1:
        return None
    op = operations[0]
    if not isinstance(op, dict) or op.get("action") != kind:
        return None
    if kind in ("update", "delete"):
        if type(op.get("id")) is not int or op["id"] not in {m["id"] for m in memories}:
            return None
    if kind in ("update", "add"):
        if not isinstance(op.get("fact"), str) or not op["fact"].strip() or len(op["fact"]) > 1500:
            return None
    return op

def context_needed(text):
    """Only elliptical imperative requests may consult the preceding conversation turn."""
    if not isinstance(text, str):
        return False
    compact = re.sub(r"[.!?\s]+", " ", text).strip().casefold()
    return compact in ("mentsd el", "mentsük el", "jegyezd meg", "tárold el",
                       "ezt mentsd el", "azt mentsd el", "ezt jegyezd meg")

def previous_context(turns, conversation_id, now, max_age=300):
    """Never infer an antecedent across conversations, missing IDs or old turns."""
    if not conversation_id or not isinstance(conversation_id, str):
        return None
    for item in turns:
        if item.get("conversation_id") != conversation_id:
            continue
        created = item.get("created")
        if type(created) is not int or not (0 <= now - created <= max_age):
            return None
        candidate = item.get("user_text", "")
        if not isinstance(candidate, str) or not candidate.strip():
            return None
        if operation_kind(candidate) in ("delete", "blocked"):
            return None
        if context_needed(candidate):
            return None
        return candidate[:2000]
    return None



def identical_existing_fact(candidate, memories):
    """Idempotent save acknowledgement only for a literal matching fact.

    Never claim a fuzzy/semantic match without verification. No database write.
    """
    if not isinstance(candidate, str):
        return False
    def normalize(value):
        value = unicodedata.normalize("NFKC", value).casefold()
        return re.sub(r"[.!?,;:\s]+", " ", value).strip()
    target = normalize(candidate)
    return bool(target) and any(
        isinstance(item.get("fact"), str) and
        normalize(item["fact"]) == target for item in memories
    )
