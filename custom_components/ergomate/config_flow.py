"""Config flow for Ergomate integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from bleak import BleakScanner

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_HEIGHT_OFFSET
from .desk_const import SERVICE_UUID, DEVICE_NAME_PREFIX_CLASSIC

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ADDRESS): str,
        vol.Optional(CONF_NAME, default="Ergomate Desk"): str,
        vol.Optional(CONF_HEIGHT_OFFSET, default=0.0): float,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ergomate."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input.get(CONF_NAME, "Ergomate Desk"),
                data=user_input,
            )

        # Find discovered devices to populate the list
        current_discovered = async_discovered_service_info(self.hass)
        valid_devices = {}
        for info in current_discovered:
            # Log all devices for debugging
            _LOGGER.debug(
                "Discovered BLE device: %s (%s) - UUIDs: %s",
                info.name,
                info.address,
                info.service_uuids
            )

            if (
                SERVICE_UUID in info.service_uuids
                or info.name.startswith(DEVICE_NAME_PREFIX_CLASSIC)
            ):
                valid_devices[info.address] = f"{info.name} ({info.address})"

        if valid_devices:
            schema = vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(valid_devices),
                    vol.Optional(CONF_NAME, default="Ergomate Desk"): str,
                    vol.Optional(CONF_HEIGHT_OFFSET, default=0.0): float,
                }
            )
        else:
            schema = STEP_USER_DATA_SCHEMA

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        # Check if it's an Ergomate desk
        # We can check service UUID or name
        is_ergomate = False
        if SERVICE_UUID in discovery_info.service_uuids:
            is_ergomate = True
        elif discovery_info.name.startswith(DEVICE_NAME_PREFIX_CLASSIC):
            is_ergomate = True

        if not is_ergomate:
            return self.async_abort(reason="not_supported")

        return self.async_create_entry(
            title=discovery_info.name,
            data={
                CONF_ADDRESS: discovery_info.address,
                CONF_NAME: discovery_info.name,
            },
        )
