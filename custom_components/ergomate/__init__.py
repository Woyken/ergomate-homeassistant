"""The Ergomate integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .desk_api import ErgomateDesk

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.COVER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ergomate from a config entry."""
    address = entry.data["address"]
    height_offset = entry.data.get("height_offset", 0.0)

    desk = ErgomateDesk(address, height_offset)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = desk

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        desk: ErgomateDesk = hass.data[DOMAIN].pop(entry.entry_id)
        if desk.is_connected:
            await desk.disconnect()

    return unload_ok
