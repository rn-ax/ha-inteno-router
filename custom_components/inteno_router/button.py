"""Button entities for the Inteno Router integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .ubus_client import UbusClient


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    client: UbusClient = hass.data[DOMAIN][entry.entry_id].client
    async_add_entities([RouterRebootButton(client, entry.entry_id)])


class RouterRebootButton(ButtonEntity):
    """Reboots the router via ubus's juci.system reboot method.

    Not tied to the coordinator's polling — a press opens its own short-lived
    ubus session, same as any other one-off action call.
    """

    _attr_name = "Reboot"
    _attr_device_class = ButtonDeviceClass.RESTART

    def __init__(self, client: UbusClient, entry_id: str) -> None:
        self._client = client
        self._attr_unique_id = f"{entry_id}_reboot"
        self._entry_id = entry_id

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": "Inteno Router",
            "manufacturer": "Inteno",
        }

    async def async_press(self) -> None:
        await self._client.call("juci.system", "reboot")
