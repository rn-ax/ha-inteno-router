"""Polling coordinator for the Inteno Router integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

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
        try:
            results = await self._client.fetch([
                ("router.network", "clients"),
                ("router.system", "info"),
            ])
        except UbusAuthError as err:
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
        }
