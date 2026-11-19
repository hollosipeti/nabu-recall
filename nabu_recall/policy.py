"""Conservative voice-memory deletion policy. No bulk delete capability."""
import re

# The AI may suggest a deletion, but only a user's specific request authorizes it.
DELETE_WORDS = re.compile(r"\b(?:felejtsd|felejts|töröld|törölj|távolítsd|távolíts)\b", re.IGNORECASE)
BULK_WORDS = re.compile(
    r"\b(?:mindent|mindet|összes(?:et|t)?|valamennyi(?:t)?|teljes(?:en)?|"
    r"minden\s+(?:emléket|memóriát|adatot|beszélgetést)|"
    r"összes\s+(?:emlék(?:et|em)|memóri(?:át|a)|adat(?:ot|om))|"
    r"gyári\s+visszaállítás|full\s+clean|reset|ürítsd)\b",
    re.IGNORECASE,
)

def permitted_deletion(utterances):
    """Permit at most one ID deletion only after a specific explicit user instruction."""
    for speech in utterances:
        if not isinstance(speech, str):
            continue
        if DELETE_WORDS.search(speech) and not BULK_WORDS.search(speech):
            return True
    return False

def filter_memory_operations(operations, utterances):
    """Reject every batch-wide or ambiguous deletion, including two or more deletes."""
    if not isinstance(operations, list):
        return []
    safe = [op for op in operations if isinstance(op, dict)
            and op.get("action") in ("add", "update", "delete")]
    deletes = [op for op in safe if op["action"] == "delete"]
    if not deletes:
        return safe
    if len(deletes) != 1 or not permitted_deletion(utterances) or any(
        BULK_WORDS.search(s) for s in utterances if isinstance(s, str)
    ):
        return [op for op in safe if op["action"] != "delete"]
    # Reject delete requests without a concrete integer memory id.
    if type(deletes[0].get("id")) is not int:
        return [op for op in safe if op["action"] != "delete"]
    return safe
