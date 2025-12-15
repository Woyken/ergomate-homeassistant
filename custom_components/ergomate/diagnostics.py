"""Diagnostics support for Ergomate."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .desk_api import ErgomateDesk

TO_REDACT = {CONF_ADDRESS}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    desk: ErgomateDesk = hass.data[DOMAIN][entry.entry_id]

    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(entry.data, TO_REDACT),
        },
        "desk": {
            "is_connected": desk.is_connected,
            "current_height": desk.current_height,
            "raw_height": desk.raw_height,
            "is_moving": desk.is_moving,
            "moving_direction": desk.moving_direction,
        },
    }
