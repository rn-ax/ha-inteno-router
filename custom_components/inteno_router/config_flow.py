"""Config flow for the Inteno Router integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
import websockets
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, DEFAULT_HOST, DOMAIN
from .ubus_client import UbusAuthError, UbusClient

STEP_USER_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
})


async def _validate_login(host: str, username: str, password: str) -> None:
    """Raise on failure; a bare successful call means the credentials work."""
    client = UbusClient(host, username, password)
    await client.fetch([("system", "info")])


class IntenoRouterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Inteno Router integration."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()

            try:
                await _validate_login(
                    user_input[CONF_HOST], user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except UbusAuthError:
                errors["base"] = "invalid_auth"
            except (OSError, websockets.exceptions.WebSocketException):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Inteno Router ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
