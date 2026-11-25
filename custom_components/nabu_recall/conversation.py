"""Transparent wrapper retaining the actual assistant speech and device control."""
import logging
from contextlib import contextmanager
from homeassistant.components import conversation
from homeassistant.components.conversation import ConversationEntity
from homeassistant.components.conversation.const import ConversationEntityFeature
from homeassistant.const import MATCH_ALL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .gateway import Bridge
from .exact_recall import extract_precise
from .current_preference_reply import extract_current_preference
from .repo_instructions import compose_instructions
import re

_LOGGER = logging.getLogger(__name__)

@contextmanager
def suppress_nested_text():
    """Suppress only nested assistant text; retain tool diagnostics and restore listener."""
    try:
        from homeassistant.components.conversation.chat_log import current_chat_log
    except ImportError:
        yield
        return
    chat_log = current_chat_log.get()
    listener = getattr(chat_log, "delta_listener", None)
    if listener is None:
        yield
        return

    def filtered(log, delta):
        if delta.get("role") == "tool_result" or delta.get("tool_calls"):
            listener(log, {k: v for k, v in delta.items() if k != "content"})
    chat_log.delta_listener = filtered
    try:
        yield
    finally:
        chat_log.delta_listener = listener


def extract_spoken_answer(result):
    """Read Home Assistant IntentResponse speech in dict or attribute form."""
    response = getattr(result, "response", None)
    speech = getattr(response, "speech", None)
    if isinstance(speech, dict):
        plain = speech.get("plain")
    else:
        plain = getattr(speech, "plain", None)
    if isinstance(plain, dict):
        answer = plain.get("speech")
    else:
        answer = getattr(plain, "speech", None)
    return answer if isinstance(answer, str) else ""



# Calendar requests are routed to the original HA agent, not to memory management.
CALENDAR_DESTINATION = re.compile(
    r"\b(?:naptárba|naptárban|naptárból|naptáramba|naptáramban|"
    r"naptáradba|naptáradban|naptáresemény\w*|naptárbejegyzés\w*)\b", re.I)

def calendar_action(text):
    if not isinstance(text, str):
        return False
    if re.search(r"\b(?:jegyezd\s+meg|emlékezz\s+(?:rá|arra))\b", text, re.I):
        return False
    return bool(CALENDAR_DESTINATION.search(text))


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([RecallAgent(entry)])

class RecallAgent(ConversationEntity):
    _attr_name = "Nabu Recall – memória"
    _attr_should_poll = False
    _attr_supported_features = ConversationEntityFeature.CONTROL
    _attr_supports_streaming = False

    def __init__(self, entry):
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_recall"

    @property
    def supported_languages(self):
        return MATCH_ALL

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self):
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def async_process(self, user_input):
        opts = self.entry.data
        upstream = opts["upstream"]
        if upstream in (self.entity_id, user_input.agent_id):
            raise ValueError("Nabu Recall cannot call itself as upstream agent")
        bridge = Bridge(async_get_clientsession(self.hass), opts["url"], opts["token"])
        # Handle explicit memory commands synchronously. Ordinary speech still
        # flows to the original OpenAI agent, preserving device-control tools.
        memory_command = re.search(
            r"\b(?:töröld|törölj|felejtsd|felejts|távolítsd|"
            r"javítsd|javítsuk|javíts|módosítsd|módosítsuk|módosíts|"
            r"változtasd|írd\s+át|helyesbítsd|ki\s+kell\s+javítani|jegyezd\s+meg|"
            r"emlékezz\s+(?:rá|arra)|mentsd\s+el|mentsük\s+el|"
            r"tárold\s+el|rögzítsd)\b",
            user_input.text, re.IGNORECASE)
        if memory_command and not calendar_action(user_input.text):
            # Only forward an explicitly separate question; never replay the memory command.
            tail = re.search(r"(?:[,;.]\s*|\s+és\s+)(?:és\s+)?(?:mondd meg,?\s+)?((?:mikor|meddig|hol|mennyi|mi|milyen|hány)\b.+)$", user_input.text, re.I)
            followup = tail.group(1).strip() if tail else ""
            memory_text = user_input.text[:tail.start()].strip(" ,;.") if tail else user_input.text
            try:
                outcome = await bridge.manage(memory_text, user_input.conversation_id or "")
            except Exception:
                outcome = {"status": "error", "message": "A memóriaműveletet nem sikerült ellenőrizni."}
            if outcome.get("status") in ("confirmed", "blocked", "not_found", "error", "not_command"):
                from homeassistant.helpers import intent
                response = intent.IntentResponse(language=user_input.language)
                spoken = outcome.get("message") or "Ez nem egyértelmű memóriaművelet."
                if followup and outcome.get("status") == "confirmed":
                    try:
                        context = await bridge.recall(user_input.text)
                        extra = compose_instructions(user_input.extra_system_prompt, context)
                        extra += "\\nThe memory operation is already complete. Answer only the separate question; do not repeat the memory action. The original user request was: " + user_input.text
                        with suppress_nested_text():
                            answer = await conversation.async_converse(
                                self.hass, text=followup, conversation_id=user_input.conversation_id,
                                context=user_input.context, language=user_input.language,
                                agent_id=upstream, device_id=user_input.device_id,
                                satellite_id=user_input.satellite_id, extra_system_prompt=extra)
                        spoken += " " + (extract_spoken_answer(answer) or "A további kérdésre nem kaptam választ.")
                    except Exception:
                        spoken += " A további kérdés feldolgozása sikertelen."
                response.async_set_speech(spoken)
                result = conversation.ConversationResult(
                    response=response, conversation_id=user_input.conversation_id or "")
                try:
                    await bridge.log(user_input.text, spoken, result.conversation_id)
                except Exception:
                    _LOGGER.warning("Nabu Recall management transcript logging failed")
                return result
        try:
            memory = await bridge.recall(user_input.text)
        except Exception:
            memory = ""
            _LOGGER.warning("Nabu Recall lookup unavailable; original agent continues")
        # Read back only uniquely identified, selected durable identifiers.
        # All other requests retain the upstream HA/OpenAI control and chat path.
        exact_answer = extract_precise(user_input.text, memory)
        if exact_answer is None:
            exact_answer = extract_current_preference(user_input.text, memory)
        if exact_answer is not None:
            from homeassistant.helpers import intent
            response = intent.IntentResponse(language=user_input.language)
            response.async_set_speech(exact_answer)
            result = conversation.ConversationResult(
                response=response, conversation_id=user_input.conversation_id or "")
            self.hass.async_create_background_task(
                self._log(bridge, user_input.text, exact_answer,
                          result.conversation_id),
                "Nabu Recall: store exact memory readback")
            return result
        # Nabu Recall behavioral instructions are shipped with this integration
        # and are never copied into the user's editable OpenAI Instructions field.
        # The upstream HA OpenAI agent still controls HA tools and chat behavior.
        extra = compose_instructions(user_input.extra_system_prompt, memory)
        result = await conversation.async_converse(
            self.hass, text=user_input.text,
            conversation_id=user_input.conversation_id,
            context=user_input.context, language=user_input.language,
            agent_id=upstream, device_id=user_input.device_id,
            satellite_id=user_input.satellite_id, extra_system_prompt=extra)
        answer = extract_spoken_answer(result)
        self.hass.async_create_background_task(
            self._log(bridge, user_input.text, answer,
                      result.conversation_id or user_input.conversation_id or ""),
            "Nabu Recall: store conversation turn")
        return result

    async def _log(self, bridge, user, assistant, conversation_id):
        try:
            await bridge.log(user, assistant, conversation_id)
        except Exception:
            _LOGGER.warning("Nabu Recall transcript logging failed; assistant remained available")
