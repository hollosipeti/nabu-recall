"""Create an agent that wraps the existing OpenAI Conversation agent."""
import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .gateway import Bridge

DOMAIN = "nabu_recall"

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            url = user_input["url"].rstrip("/")
            token = user_input["token"]
            upstream = user_input["upstream"]
            calendar_entity = user_input.get("calendar_entity", "")
            if not re.fullmatch(r"http://[a-zA-Z0-9._-]+:\d{2,5}", url):
                errors["url"] = "invalid_url"
            elif len(token) < 32:
                errors["token"] = "invalid_token"
            elif calendar_entity and not calendar_entity.startswith("calendar."):
                errors["calendar_entity"] = "invalid_calendar"
            elif not upstream.startswith("conversation."):
                errors["upstream"] = "invalid_agent"
            else:
                try:
                    bridge = Bridge(async_get_clientsession(self.hass), url, token)
                    if await bridge.ping():
                        await self.async_set_unique_id(url + "/" + upstream)
                        self._abort_if_unique_id_configured()
                        return self.async_create_entry(
                            title="Nabu Recall (" + upstream + ")", data=user_input)
                    errors["base"] = "cannot_connect"
                except Exception:
                    errors["base"] = "cannot_connect"
        schema = vol.Schema({
            vol.Required("upstream"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="conversation")),
            vol.Required("url", default="http://YOUR_ADDON_HOST:8765"): str,
            vol.Required("token"): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
            vol.Optional("calendar_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="calendar")),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return CalendarOptionsFlow(config_entry)


class CalendarOptionsFlow(config_entries.OptionsFlow):
    """Change the optional calendar without reinstalling the integration."""

    def __init__(self, config_entry):
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            calendar_entity = user_input.get("calendar_entity") or ""
            if calendar_entity and not calendar_entity.startswith("calendar."):
                return self.async_show_form(
                    step_id="init", data_schema=self._schema(),
                    errors={"calendar_entity": "invalid_calendar"},
                )
            return self.async_create_entry(
                title="", data={"calendar_entity": calendar_entity}
            )
        return self.async_show_form(step_id="init", data_schema=self._schema())

    def _schema(self):
        current = self._entry.options.get(
            "calendar_entity", self._entry.data.get("calendar_entity", "")
        )
        return vol.Schema({
            vol.Optional("calendar_entity", default=current or vol.UNDEFINED):
                selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
        })
