"""Sensor entity for Ergomate Desk."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .desk_api import ErgomateDesk

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ergomate sensor."""
    desk: ErgomateDesk = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ErgomateHeightSensor(desk, entry)])


class ErgomateHeightSensor(SensorEntity):
    """Representation of an Ergomate Desk height sensor."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True
    _attr_name = "Height"

    def __init__(self, desk: ErgomateDesk, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._desk = desk
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_height"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Ergomate",
            model="Classic",
        )

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._desk.register_callback(self._notification_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        self._desk.unregister_callback(self._notification_callback)

    def _notification_callback(self, sender: int, data: bytearray) -> None:
        """Handle height updates."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self._desk.current_height
