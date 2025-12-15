"""Config flow for Ergomate integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from bleak import BleakClient
from bleak.exc import BleakError

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .desk_const import SERVICE_UUID, DEVICE_NAME_PREFIX_CLASSIC

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ergomate."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_address: str | None = None
        self._discovered_name: str | None = None

    async def _test_connection(self, address: str) -> bool:
        """Test connection to the desk."""
        try:
            client = BleakClient(address, timeout=10.0)
            await client.connect()
            await client.disconnect()
            return True
        except BleakError as err:
            _LOGGER.error("Failed to connect to desk at %s: %s", address, err)
            return False
        except Exception as err:
            _LOGGER.exception("Unexpected error connecting to desk: %s", err)
            return False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            # Test connection before creating entry
            if not await self._test_connection(address):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, "Ergomate Desk"),
                    data={
                        CONF_ADDRESS: address,
                        CONF_NAME: user_input.get(CONF_NAME, "Ergomate Desk"),
                    },
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

        if not valid_devices:
            return self.async_abort(reason="no_devices_found")

        schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(valid_devices),
                vol.Optional(CONF_NAME, default="Ergomate Desk"): str,
            }
        )

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
        is_ergomate = False
        if SERVICE_UUID in discovery_info.service_uuids:
            is_ergomate = True
        elif discovery_info.name.startswith(DEVICE_NAME_PREFIX_CLASSIC):
            is_ergomate = True

        if not is_ergomate:
            return self.async_abort(reason="not_supported")

        # Store discovery info for confirmation step
        self._discovery_info = discovery_info
        self._discovered_address = discovery_info.address
        self._discovered_name = discovery_info.name

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        assert self._discovery_info is not None

        if user_input is not None:
            # Test connection before creating entry
            if not await self._test_connection(self._discovered_address):
                return self.async_abort(reason="cannot_connect")

            return self.async_create_entry(
                title=self._discovered_name,
                data={
                    CONF_ADDRESS: self._discovered_address,
                    CONF_NAME: self._discovered_name,
                },
            )

        self.context["title_placeholders"] = {"name": self._discovered_name}
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovered_name},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]

            # Test connection to new address
            if not await self._test_connection(address):
                errors["base"] = "cannot_connect"
            else:
                # Update the config entry with new data
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(),
                    data={
                        CONF_ADDRESS: address,
                        CONF_NAME: user_input.get(CONF_NAME, "Ergomate Desk"),
                    },
                )

        # Get current discovered devices for dropdown
        current_discovered = async_discovered_service_info(self.hass)
        valid_devices = {}
        for info in current_discovered:
            if (
                SERVICE_UUID in info.service_uuids
                or info.name.startswith(DEVICE_NAME_PREFIX_CLASSIC)
            ):
                valid_devices[info.address] = f"{info.name} ({info.address})"

        entry = self._get_reconfigure_entry()

        if valid_devices:
            schema = vol.Schema(
                {
                    vol.Required(
                        CONF_ADDRESS,
                        default=entry.data.get(CONF_ADDRESS)
                    ): vol.In(valid_devices),
                    vol.Optional(
                        CONF_NAME,
                        default=entry.data.get(CONF_NAME, "Ergomate Desk"),
                    ): str,
                }
            )
        else:
            schema = vol.Schema(
                {
                    vol.Required(
                        CONF_ADDRESS,
                        default=entry.data.get(CONF_ADDRESS)
                    ): str,
                    vol.Optional(
                        CONF_NAME,
                        default=entry.data.get(CONF_NAME, "Ergomate Desk"),
                    ): str,
                }
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Ergomate."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update the config entry title if name changed
            if user_input.get(CONF_NAME) != self.config_entry.data.get(CONF_NAME):
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    title=user_input[CONF_NAME],
                    data={**self.config_entry.data, CONF_NAME: user_input[CONF_NAME]},
                )
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NAME,
                        default=self.config_entry.data.get(CONF_NAME, "Ergomate Desk"),
                    ): str,
                }
            ),
        )
