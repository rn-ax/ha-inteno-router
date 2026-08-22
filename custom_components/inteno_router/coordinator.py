"""Polling coordinator for the Inteno Router integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import websockets
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL_SECONDS
from .ubus_client import UbusAuthError, UbusClient

_LOGGER = logging.getLogger(__name__)


class IntenoRouterCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches router.network clients + router.system info on an interval.

    Each poll opens a fresh ubus session rather than reusing one across
    cycles — ubus sessions expire in ~300s, well inside any reasonable
    polling interval, so there is no session worth keeping alive between
    updates.
    """

    def __init__(self, hass: HomeAssistant, client: UbusClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self._client = client

    async def _async_update_data(self) -> dict[str, Any]:
        # DataUpdateCoordinator only auto-reschedules the next poll for a
        # failure it recognizes as UpdateFailed -- any other exception type
        # is treated as an integration bug and halts polling entirely rather
        # than retrying. A router reboot (or any transient network blip)
        # surfaces as a raw ConnectionRefusedError/OSError or a websockets
        # protocol exception, neither of which is UpdateFailed on its own,
        # so both need converting here or a single reboot permanently kills
        # every entity until the integration is manually reloaded.
        try:
            results = await self._client.fetch([
                ("router.network", "clients"),
                ("router.system", "info"),
                ("juci.network", "load"),
            ])
        except (UbusAuthError, OSError, TimeoutError, websockets.exceptions.WebSocketException) as err:
            raise UpdateFailed(f"Failed talking to router: {err}") from err

        # Re-key clients by MAC address rather than the API's own "client-N"
        # dict key: MAC is the actually-stable hardware identifier, while
        # "client-N" numbering isn't confirmed stable across a device
        # dropping off and reconnecting in a different order.
        clients_by_mac = {
            client["macaddr"]: client
            for client in results[("router.network", "clients")].values()
        }

        return {
            "clients": clients_by_mac,
            "system": results[("router.system", "info")],
            "load": results[("juci.network", "load")],
        }
