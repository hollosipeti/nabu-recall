"""Small deterministic guard against storing shopping-list task results as facts.

Only clearly identified shopping-list actions are skipped during background
learning. They remain in the 45-day verbatim journal; genuine preferences and
explicit durable-memory requests are not suppressed.
"""
import re

SHOPPING_LIST = re.compile(
    r"\b(?:bev[aá]s[aá]rl[oó]\s*list[aá]\w*|shopping\s+list\w*)",
    re.IGNORECASE,
)
LIST_ACTION = re.compile(
    r"\b(?:tegy[eé]l|tegy[eé]tek|tedd|rakj|rakd|[ií]rj|[ií]rd|"
    r"add|hozz[aá]ad\w*|t[oö]r[oö]l\w*|vegy[eé]l\s+le|"
    r"vegy[eé]tek\s+le|v[eé]gy\s+le|vegy[eé]l\s+fel|vedd\s+fel|pip[aá]l\w*|jel[oö]l\w*|"
    r"ker[uü]lj[oö]n|felvesz\w*|felvettem)",
    re.IGNORECASE,
)
CONFIRMED = re.compile(
    r"(?:bev[aá]s[aá]rl[oó]\s*list[aá]\w*[^.!?\n]{0,100}"
    r"(?:hozz[aá]adva|hozz[aá]adtam|felv[eé]ve|t[oö]r[oö]lve|elt[aá]vol[ií]tva)"
    r"|(?:hozz[aá]adva|hozz[aá]adtam|felv[eé]ve|t[oö]r[oö]lve|elt[aá]vol[ií]tva)"
    r"[^.!?\n]{0,60}bev[aá]s[aá]rl[oó]\s*list[aá])",
    re.IGNORECASE,
)
EXPLICIT_MEMORY = re.compile(
    r"\b(?:jegyezd\s+meg|jegyezz\w*\s+meg|eml[eé]kezz\w*|"
    r"mentsd\s+el\s+(?:eml[eé]kk[eé]nt|a\s+mem[oó]ri[aá]ba)|"
    r"t[aá]rold\s+el\s+(?:eml[eé]kk[eé]nt|a\s+mem[oó]ri[aá]ba))\b",
    re.IGNORECASE,
)


def is_shopping_list_action(user_text, assistant_text):
    """True only for shopping-list operations, not enduring shopping preferences."""
    if not isinstance(user_text, str):
        return False
    if EXPLICIT_MEMORY.search(user_text):
        return False
    if SHOPPING_LIST.search(user_text) and LIST_ACTION.search(user_text):
        return True
    return isinstance(assistant_text, str) and bool(CONFIRMED.search(assistant_text))
