"""Lightweight Hungarian memory-command routing. No new memory layers."""
import re

DELETE = re.compile(r"\b(?:töröld|törölj|felejtsd|felejts|távolítsd|távolíts)\b", re.I)
EDIT = re.compile(r"\b(?:javítsd|javítsuk|javíts|javítsam|módosítsd|módosítsuk|módosíts|változtasd|írd\s+át|helyesbítsd|helyesbíts|ezt\s+is\s+javítsuk)\b", re.I)
SAVE = re.compile(r"\b(?:jegyezd\s+meg|emlékezz\s+(?:rá|arra)|mentsd\s+el|mentsük\s+el|tárold\s+el|rögzítsd)\b", re.I)
BULK = re.compile(r"\b(?:mindent|mindet|összes(?:et|t)?|valamennyit|teljes(?:en)?|reset|full\s*clean|ürítsd|minden\s+emlék)\b", re.I)

def operation_kind(text):
    if not isinstance(text, str) or len(text) > 2000:
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
