"""Turn-local calendar verification; no global HA API mutation or replay of writes."""
import re
from contextlib import contextmanager

_QUERY = "nabu_recall__calendar_query"
_NATIVE = "calendar__get_events"
_WRITES = {"nabu_recall__calendar_create", "nabu_recall__calendar_edit"}

def calendar_read_question(text):
    """Recognize explicit calendar questions, not general knowledge or actions."""
    text = " ".join(text.casefold().strip().rstrip("?! .").split())
    if not re.match(r"^(?:és )?(?:mi(?:k|kor|lyen|t)?|meddig|van(?:-e)?|benne van|hány)\b", text):
        return False
    if re.search(r"\b(?:kapcsold|töröld|írd be|mentsd|hozz létre|módosítsd)\b", text):
        return False
    if re.search(r"\b(?:naptár\w*|naptáresemény\w*)\b", text):
        return True
    # Explicit next appointments and calendar occurrences, not arbitrary future facts.
    return bool(re.match(r"^(?:és )?mikor (?:lesz|van|kezdődik) (?:a |az )?következő (?:névnap|születésnap|körmös|fodrász|vízóra[- ]leolvasás|villanyóra[- ]leolvasás)\b", text)
                or re.match(r"^mikor kell leolvasni (?:a |az )?(?:vízórát|villanyórát)\b", text))

def fresh_calendar_result(contents):
    """Only results produced in this turn, not previous assistant claims."""
    return any(getattr(item, "role", None) == "tool_result"
               and getattr(item, "tool_name", None) == _QUERY
               and not getattr(getattr(item, "result", None), "error", True)
               for item in contents)

def has_write(contents):
    return any(getattr(item, "role", None) == "tool_result"
               and getattr(item, "tool_name", None) in _WRITES for item in contents)

@contextmanager
def calendar_tool_scope(chat_log):
    """Filter only the current chat's API object, after HA prepares its tools.

    HA 2026.11 ChatLog is per conversation. Restore the instance method and
    original tool list, even if the upstream request fails.
    """
    if chat_log is None:
        yield
        return
    original = chat_log.async_provide_llm_data
    own = chat_log.__dict__.get("async_provide_llm_data")
    changed = []
    async def provide(*args, **kwargs):
        await original(*args, **kwargs)
        api = chat_log.llm_api
        if api is not None and any(tool.name == _QUERY for tool in api.tools):
            before = api.tools
            after = [tool for tool in before if tool.name != _NATIVE]
            if len(after) != len(before):
                changed.append((api, before))
                api.tools = after
    chat_log.async_provide_llm_data = provide
    try:
        yield
    finally:
        for api, before in reversed(changed):
            api.tools = before
        if own is None:
            del chat_log.async_provide_llm_data
        else:
            chat_log.async_provide_llm_data = own
