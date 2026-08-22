"""Sensor entities for the Inteno Router integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IntenoRouterCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: IntenoRouterCoordinator = hass.data[DOMAIN][entry.entry_id].coordinator

    async_add_entities([
        RouterCpuSensor(coordinator, entry.entry_id),
        RouterMemorySensor(coordinator, entry.entry_id),
        RouterUptimeSensor(coordinator, entry.entry_id),
        RouterActiveConnectionsSensor(coordinator, entry.entry_id),
        RouterMaxConnectionsSensor(coordinator, entry.entry_id),
    ])

    # Client sensors are created as clients are discovered, not just once
    # at setup: a client absent at startup (router mid-reboot, cable
    # unplugged, etc.) still needs its own entity the moment it shows up
    # in a later poll, rather than never getting one for the rest of this
    # run. known_macs tracks what's already been created so this only ever
    # adds new entities, never duplicates one for a MAC that's already got
    # one -- a client dropping off and coming back just flips its existing
    # entity's `available` property, handled separately below.
    known_macs: set[str] = set()

    def _add_new_clients() -> None:
        new_macs = set(coordinator.data["clients"]) - known_macs
        if not new_macs:
            return
        known_macs.update(new_macs)
        async_add_entities(
            entity
            for macaddr in new_macs
            for entity in (
                ClientLinkSpeedSensor(coordinator, entry.entry_id, macaddr),
                ClientIpAddressSensor(coordinator, entry.entry_id, macaddr),
            )
        )

    _add_new_clients()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_clients))


class _RouterSensorBase(CoordinatorEntity[IntenoRouterCoordinator], SensorEntity):
    """Shared device grouping for every entity this integration creates."""

    def __init__(self, coordinator: IntenoRouterCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": "Inteno Router",
            "manufacturer": "Inteno",
        }


class RouterCpuSensor(_RouterSensorBase):
    _attr_name = "Router CPU"
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:chip"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_cpu"

    @property
    def native_value(self):
        return self.coordinator.data["system"]["system"]["cpu_per"]


class RouterMemorySensor(_RouterSensorBase):
    _attr_name = "Router memory used"
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:memory"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_memory"

    @property
    def native_value(self):
        mem = self.coordinator.data["system"]["memoryKB"]
        return round(100 * mem["used"] / mem["total"], 1)

    @property
    def extra_state_attributes(self):
        mem = self.coordinator.data["system"]["memoryKB"]
        return {"total_kb": mem["total"], "used_kb": mem["used"], "free_kb": mem["free"]}


class RouterUptimeSensor(_RouterSensorBase):
    _attr_name = "Router uptime"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_uptime"

    @property
    def native_value(self):
        return self.coordinator.data["system"]["system"]["uptime"]


class RouterActiveConnectionsSensor(_RouterSensorBase):
    _attr_name = "Router active connections"
    _attr_icon = "mdi:swap-horizontal"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_active_connections"

    @property
    def native_value(self):
        return self.coordinator.data["load"]["active_connections"]


class RouterMaxConnectionsSensor(_RouterSensorBase):
    _attr_name = "Router max connections"
    _attr_icon = "mdi:swap-horizontal-bold"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_max_connections"

    @property
    def native_value(self):
        return self.coordinator.data["load"]["max_connections"]


class _ClientSensorBase(_RouterSensorBase):
    """Shared client lookup for entities keyed by MAC address (stable across
    hostname changes and across the API's own "client-N" numbering, which
    isn't confirmed stable).
    """

    def __init__(self, coordinator: IntenoRouterCoordinator, entry_id: str, macaddr: str) -> None:
        super().__init__(coordinator, entry_id)
        self._macaddr = macaddr

    @property
    def _client(self) -> dict | None:
        return self.coordinator.data["clients"].get(self._macaddr)

    @property
    def available(self) -> bool:
        # A client can drop off between polls (device off, DHCP lease
        # expired) -- report unavailable rather than a stale value.
        return super().available and self._client is not None


class ClientLinkSpeedSensor(_ClientSensorBase):
    """One entity per connected client, surfacing `linkspeed` as the state
    so a degraded link (e.g. a client stuck negotiating far below what the
    rest of the LAN gets) is visible and alertable in HA directly, rather
    than needing a manual ubus query to notice.
    """

    _attr_icon = "mdi:lan-connect"

    def __init__(self, coordinator: IntenoRouterCoordinator, entry_id: str, macaddr: str) -> None:
        super().__init__(coordinator, entry_id, macaddr)
        self._attr_unique_id = f"{entry_id}_client_{macaddr}"

    @property
    def name(self):
        client = self._client
        hostname = client["hostname"] if client else self._macaddr
        return f"{hostname} link speed"

    @property
    def native_value(self):
        client = self._client
        return client["linkspeed"] if client else None

    @property
    def extra_state_attributes(self):
        client = self._client
        if not client:
            return {}
        return {
            "ipaddr": client["ipaddr"],
            "macaddr": client["macaddr"],
            "connected": client["connected"],
            "wireless": client["wireless"],
            "ethport": client.get("ethport"),
            "active_connections": client["active_connections"],
        }


class ClientIpAddressSensor(_ClientSensorBase):
    """One entity per connected client exposing its current IP address as
    its own state, rather than only as an attribute tucked away on the
    link-speed sensor.
    """

    _attr_icon = "mdi:ip-network"

    def __init__(self, coordinator: IntenoRouterCoordinator, entry_id: str, macaddr: str) -> None:
        super().__init__(coordinator, entry_id, macaddr)
        self._attr_unique_id = f"{entry_id}_client_{macaddr}_ip"

    @property
    def name(self):
        client = self._client
        hostname = client["hostname"] if client else self._macaddr
        return f"{hostname} IP address"

    @property
    def native_value(self):
        client = self._client
        return client["ipaddr"] if client else None
