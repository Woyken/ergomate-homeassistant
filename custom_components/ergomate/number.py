"""Number entity for Ergomate Desk."""
from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .desk_api import ErgomateDesk
from .desk_const import DEFAULT_MIN_HEIGHT, DEFAULT_MAX_HEIGHT
from .entity import ErgomateEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ergomate number."""
    desk: ErgomateDesk = entry.runtime_data
    async_add_entities([ErgomateDeskHeightNumber(desk, entry)])


class ErgomateDeskHeightNumber(ErgomateEntity, NumberEntity):
    """Representation of an Ergomate Desk height number control."""

    _attr_device_class = NumberDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS
    _attr_mode = NumberMode.SLIDER
    _attr_translation_key = "target_height"
    _attr_native_step = 0.1

    def __init__(self, desk: ErgomateDesk, entry: ConfigEntry) -> None:
        """Initialize the number."""
        super().__init__(desk, entry, "target_height")
        self._attr_native_min_value = float(DEFAULT_MIN_HEIGHT)
        self._attr_native_max_value = float(DEFAULT_MAX_HEIGHT)

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._desk.current_height

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        try:
            await self._desk.move_to_height(value)
        except Exception as err:
            raise HomeAssistantError(f"Failed to set desk height to {value}: {err}") from err
