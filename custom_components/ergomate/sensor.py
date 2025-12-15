"""Sensor entity for Ergomate Desk."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .desk_api import ErgomateDesk
from .entity import ErgomateEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ergomate sensor."""
    desk: ErgomateDesk = entry.runtime_data
    async_add_entities([ErgomateHeightSensor(desk, entry)])


class ErgomateHeightSensor(ErgomateEntity, SensorEntity):
    """Representation of an Ergomate Desk height sensor."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "height"

    def __init__(self, desk: ErgomateDesk, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(desk, entry, "height")

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self._desk.current_height
