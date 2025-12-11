"""Number entity for Ergomate Desk."""
from __future__ import annotations

import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .desk_api import ErgomateDesk
from .desk_const import DEFAULT_MIN_HEIGHT, DEFAULT_MAX_HEIGHT

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ergomate number."""
    desk: ErgomateDesk = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ErgomateDeskHeightNumber(desk, entry)])


class ErgomateDeskHeightNumber(NumberEntity):
    """Representation of an Ergomate Desk height number control."""

    _attr_device_class = NumberDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS
    _attr_mode = NumberMode.SLIDER
    _attr_has_entity_name = True
    _attr_name = "Target Height"
    _attr_native_step = 0.1

    def __init__(self, desk: ErgomateDesk, entry: ConfigEntry) -> None:
        """Initialize the number."""
        self._desk = desk
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_target_height"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Ergomate",
            model="Classic",
        )
        self._attr_native_min_value = float(DEFAULT_MIN_HEIGHT)
        self._attr_native_max_value = float(DEFAULT_MAX_HEIGHT)

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
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._desk.is_connected

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._desk.current_height

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self._desk.move_to_height(value)
