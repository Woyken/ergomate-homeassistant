"""Base entity for Ergomate integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN
from .desk_api import ErgomateDesk


class ErgomateEntity(Entity):
    """Base class for Ergomate entities."""

    _attr_has_entity_name = True

    def __init__(self, desk: ErgomateDesk, entry: ConfigEntry, entity_type: str) -> None:
        """Initialize the entity."""
        self._desk = desk
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{entity_type}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Ergomate",
            model="Classic",
            connections={("bluetooth", desk.address)},
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
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._desk.is_connected
