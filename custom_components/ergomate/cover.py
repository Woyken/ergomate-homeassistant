"""Cover entity for Ergomate Desk."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .desk_api import ErgomateDesk
from .desk_const import DEFAULT_MIN_HEIGHT, DEFAULT_MAX_HEIGHT

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ergomate cover."""
    desk: ErgomateDesk = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ErgomateDeskCover(desk, entry)])


class ErgomateDeskCover(CoverEntity):
    """Representation of an Ergomate Desk as a cover."""

    _attr_device_class = CoverDeviceClass.DAMPER  # Or BLIND/SHADE, but DAMPER is generic enough or just None
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, desk: ErgomateDesk, entry: ConfigEntry) -> None:
        """Initialize the cover."""
        self._desk = desk
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_cover"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Ergomate",
            model="Classic",
        )
        self._min_height = DEFAULT_MIN_HEIGHT
        self._max_height = DEFAULT_MAX_HEIGHT

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Subscribe to notifications to update position
        self._desk.register_callback(self._notification_callback)
        try:
            await self._desk.connect()
            await self._desk.subscribe_notifications()
        except Exception as err:
            _LOGGER.error("Failed to connect to desk: %s", err)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        self._desk.unregister_callback(self._notification_callback)
        await self._desk.disconnect()

    def _notification_callback(self, sender: int, data: bytearray) -> None:
        """Handle height updates."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._desk.is_connected

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed (at min height)."""
        if self._desk.current_height is None:
            return None
        return self._desk.current_height <= self._min_height + 1

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover.

        0 is closed (min height), 100 is open (max height).
        """
        if self._desk.current_height is None:
            return None

        # Map height to 0-100
        # Height range: 65 - 130
        # Position = (current - min) / (max - min) * 100

        range_cm = self._max_height - self._min_height
        if range_cm <= 0:
            return 0

        position = ((self._desk.current_height - self._min_height) / range_cm) * 100
        return int(max(0, min(100, position)))

    @property
    def is_opening(self) -> bool | None:
        """Return if the cover is opening or not."""
        return self._desk.is_moving and self._desk.moving_direction == 1

    @property
    def is_closing(self) -> bool | None:
        """Return if the cover is closing or not."""
        return self._desk.is_moving and self._desk.moving_direction == -1

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover (Move Up)."""
        await self._desk.move_up()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover (Move Down)."""
        await self._desk.move_down()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self._desk.stop()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position = kwargs.get("position", 0)

        # Map 0-100 to height
        range_cm = self._max_height - self._min_height
        target_height = self._min_height + (position / 100.0) * range_cm

        await self._desk.move_to_height(target_height)
