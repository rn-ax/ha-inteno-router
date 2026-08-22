"""The Inteno Router integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .coordinator import IntenoRouterCoordinator
from .ubus_client import UbusClient

PLATFORMS = ["sensor", "button"]


@dataclass
class RuntimeData:
    coordinator: IntenoRouterCoordinator
    client: UbusClient


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = UbusClient(
        entry.data[CONF_HOST], entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )
    coordinator = IntenoRouterCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = RuntimeData(coordinator, client)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
