"""The Ergomate integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .desk_api import ErgomateDesk

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.COVER, Platform.SENSOR, Platform.NUMBER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ergomate from a config entry."""
    address = entry.data["address"]

    desk = ErgomateDesk(address)

    # Test connection before setup
    try:
        await desk.connect()
        _LOGGER.info("Successfully connected to Ergomate desk at %s", address)
    except Exception as err:
        _LOGGER.error("Failed to connect to desk at %s: %s", address, err)
        raise ConfigEntryNotReady(f"Failed to connect to desk: {err}") from err

    # Use runtime_data instead of hass.data
    entry.runtime_data = desk

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        desk: ErgomateDesk = entry.runtime_data
        if desk.is_connected:
            await desk.disconnect()

    return unload_ok
