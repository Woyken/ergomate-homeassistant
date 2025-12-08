"""ErgoMate Standing Desk BLE controller."""

import asyncio
import logging
from typing import Callable, Optional

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from .desk_const import (
    WRITE_CHARACTERISTIC_UUID,
    READ_CHARACTERISTIC_UUID,
    CMD_UP,
    CMD_DOWN,
    CMD_STOP,
    HEADER,
    RESERVED,
    TERMINATOR,
    DEVICE_NAME_PREFIX_CLASSIC,
    DEFAULT_SCAN_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


def _create_command(cmd_byte: int) -> bytes:
    """
    Create a 5-byte command packet with XOR checksum.

    Packet format: [Header, Reserved, Command, Checksum, Terminator]
    - Header: 0xA5 (165)
    - Reserved: 0x00
    - Command: 0x20 (up), 0x40 (down), 0x00 (stop)
    - Checksum: 0xFF XOR Command
    - Terminator: 0xFF (255)

    Args:
        cmd_byte: Command byte (CMD_UP, CMD_DOWN, or CMD_STOP)

    Returns:
        5-byte command packet
    """
    checksum = TERMINATOR ^ cmd_byte  # 0xFF XOR cmd
    return bytes([HEADER, RESERVED, cmd_byte, checksum, TERMINATOR])


def _create_height_command(height_mm: int) -> bytes:
    """
    Create a 9-byte command packet to move desk to specific height.

    Packet format: [0xA6, 0xA8, 0x01, HB, LB, 0x00, 0x00, Checksum, 0xFF]
    - Header: 0xA6 (166)
    - Command: 0xA8 (168)
    - Param 1: 0x01 (1)
    - High Byte: Height >> 8
    - Low Byte: Height & 0xFF
    - Zero 1: 0x00
    - Zero 2: 0x00
    - Checksum: XOR of bytes 1-6 (Command through Zero 2)
    - Terminator: 0xFF (255)

    Args:
        height_mm: Target height in millimeters (clamped 650-1300)

    Returns:
        9-byte command packet
    """
    # Clamp height between 650mm and 1300mm
    height_mm = max(650, min(1300, height_mm))

    header = 0xA6
    cmd = 0xA8
    param1 = 0x01
    high_byte = (height_mm >> 8) & 0xFF
    low_byte = height_mm & 0xFF
    zero1 = 0x00
    zero2 = 0x00
    terminator = 0xFF

    # Checksum is XOR of bytes 2-6 (indices, 0-based from param1)
    # param1 ^ high_byte ^ low_byte ^ zero1 ^ zero2
    # Note: Command byte (0xA8) is NOT included in checksum for this packet type
    checksum = param1 ^ high_byte ^ low_byte ^ zero1 ^ zero2

    return bytes([
        header, cmd, param1, high_byte, low_byte,
        zero1, zero2, checksum, terminator
    ])
class ErgomateDesk:
    """BLE wrapper for ErgoMate Classic standing desk control."""

    def __init__(self, address: str, height_offset: float = 0.0) -> None:
        """
        Initialize desk controller.

        Args:
            address: BLE MAC address of the desk (e.g., "AA:BB:CC:DD:EE:FF")
            height_offset: Offset to apply to raw height reading (default: 0.0 cm)
                          Adjust this if BLE height differs from control module display.
        """
        self._address = address
        self._height_offset = height_offset
        self._client: Optional[BleakClient] = None
        self._is_connected = False
        self._callbacks: list[Callable[[int, bytearray], None]] = []
        self._current_height: Optional[float] = None
        self._raw_height: Optional[float] = None
        self._is_moving = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._shutdown = False

    @property
    def address(self) -> str:
        """Return the BLE address of the desk."""
        return self._address

    @property
    def is_connected(self) -> bool:
        """Return True if connected to the desk."""
        return (
            self._is_connected
            and self._client is not None
            and self._client.is_connected
        )

    @property
    def raw_height(self) -> Optional[float]:
        """Return raw height from BLE in cm."""
        return self._raw_height

    @property
    def current_height(self) -> Optional[float]:
        """Return current desk height in cm."""
        return self._current_height

    @property
    def is_moving(self) -> bool:
        """Return True if the desk is currently moving."""
        return self._is_moving

    async def _establish_connection(self) -> None:
        """Internal method to establish connection."""
        if self.is_connected:
            return

        _LOGGER.debug("Connecting to desk at %s", self._address)
        self._client = BleakClient(self._address, disconnected_callback=self._on_disconnected)
        await self._client.connect()
        self._is_connected = True
        _LOGGER.info("Connected to desk at %s", self._address)

    async def connect(self) -> None:
        """
        Connect to the desk via BLE and start auto-reconnect loop.

        Raises:
            BleakError: If initial connection fails
        """
        self._shutdown = False
        await self._establish_connection()

        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._monitor_connection())

    async def _monitor_connection(self) -> None:
        """Keep connection alive."""
        while not self._shutdown:
            if not self.is_connected:
                _LOGGER.debug("Connection lost, attempting to reconnect...")
                try:
                    await self._establish_connection()
                    if self._callbacks:
                        await self.subscribe_notifications()
                except Exception as err:
                    _LOGGER.debug("Reconnect failed: %s", err)
                    await asyncio.sleep(5)  # Wait before retry
                    continue

            await asyncio.sleep(5)

    def _on_disconnected(self, client: BleakClient) -> None:
        """Handle disconnection."""
        _LOGGER.info("Disconnected from desk at %s", self._address)
        self._is_connected = False
        self._is_moving = False

    async def disconnect(self) -> None:
        """Disconnect from the desk."""
        self._shutdown = True
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None

        # Ensure desk is stopped before disconnecting
        if self._is_moving and self.is_connected:
            try:
                await self.stop()
            except Exception as err:
                _LOGGER.warning("Failed to stop desk before disconnect: %s", err)

        _LOGGER.debug("Disconnecting from desk at %s", self._address)
        if self._client:
            try:
                await self._client.disconnect()
            except BleakError as err:
                _LOGGER.warning("Error during disconnect: %s", err)
        self._is_connected = False
        self._is_moving = False
        _LOGGER.info("Disconnected from desk at %s", self._address)

    async def __aenter__(self) -> "ErgomateDesk":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def _send_command(self, cmd_byte: int) -> None:
        """
        Send a command to the desk.

        Args:
            cmd_byte: Command byte to send

        Raises:
            ConnectionError: If not connected
            BleakError: If write fails
        """
        if not self.is_connected:
            # Try to reconnect once
            _LOGGER.debug("Not connected, attempting to reconnect...")
            try:
                await self.connect()
                # Re-subscribe to notifications if we have callbacks
                if self._callbacks:
                    await self.subscribe_notifications()
            except Exception as err:
                raise ConnectionError(f"Failed to reconnect: {err}") from err

        command = _create_command(cmd_byte)
        _LOGGER.debug(
            "Sending command 0x%02X to desk: %s",
            cmd_byte,
            command.hex()
        )
        # Use write-with-response as per native app bytecode
        await self._client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, command, response=True)

    async def move_up(self) -> None:
        """
        Move the desk up.

        The desk will move up until stop() is called or it reaches max height.
        """
        _LOGGER.debug("Moving desk up")
        self._is_moving = True
        await self._send_command(CMD_UP)

    async def move_down(self) -> None:
        """
        Move the desk down.

        The desk will move down until stop() is called or it reaches min height.
        """
        _LOGGER.debug("Moving desk down")
        self._is_moving = True
        await self._send_command(CMD_DOWN)

    async def stop(self) -> None:
        """Stop desk movement."""
        _LOGGER.debug("Stopping desk")
        await self._send_command(CMD_STOP)
        self._is_moving = False

    async def move_up_for(self, duration: float) -> None:
        """
        Move the desk up for a specified duration.

        Args:
            duration: Time in seconds to move up
        """
        await self.move_up()
        await asyncio.sleep(duration)
        await self.stop()

    async def move_down_for(self, duration: float) -> None:
        """
        Move the desk down for a specified duration.

        Args:
            duration: Time in seconds to move down
        """
        await self.move_down()
        await asyncio.sleep(duration)
        await self.stop()

    async def move_to_height(self, height_cm: float) -> None:
        """
        Move the desk to a specific height.

        The desk will move until it reaches the target height or stop() is called.
        Target height is clamped between 65.0 cm and 130.0 cm.

        Args:
            height_cm: Target height in centimeters
        """
        if not self.is_connected:
            # Try to reconnect once
            _LOGGER.debug("Not connected, attempting to reconnect...")
            try:
                await self.connect()
                if self._callbacks:
                    await self.subscribe_notifications()
            except Exception as err:
                raise ConnectionError(f"Failed to reconnect: {err}") from err

        # Convert to mm for the command
        height_mm = int(height_cm * 10)

        command = _create_height_command(height_mm)
        _LOGGER.debug(
            "Moving to height %.1f cm (cmd: %s)",
            height_cm,
            command.hex()
        )

        self._is_moving = True
        await self._client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, command, response=True)

    def _parse_height(self, data: bytearray) -> Optional[float]:
        """
        Parse height from notification data.

        The desk sends height as 4-byte ASCII string representing mm.
        Example: b'0720' = 720mm = 72.0cm

        Args:
            data: Raw notification data

        Returns:
            Height in cm, or None if parsing fails
        """
        try:
            if len(data) == 4:
                # Data is ASCII digits representing height in mm
                height_mm = int(data.decode('ascii'))
                height_cm = height_mm / 10.0
                return height_cm
        except (ValueError, UnicodeDecodeError) as err:
            _LOGGER.debug("Failed to parse height: %s", err)
        return None

    def _handle_notification(self, sender: int, data: bytearray) -> None:
        """
        Internal notification handler to parse height data.

        Args:
            sender: Characteristic handle
            data: Notification data
        """
        _LOGGER.debug("Received notification from %s: %s", sender, data.hex())

        # Parse height from ASCII data (e.g., "0720" = 72.0 cm)
        raw_height = self._parse_height(data)
        if raw_height is not None:
            self._raw_height = raw_height
            self._current_height = raw_height
            _LOGGER.debug("Height: %.1f cm", self._current_height)

        # Forward to user callbacks
        for callback in self._callbacks:
            try:
                callback(sender, data)
            except Exception as err:
                _LOGGER.error("Error in notification callback: %s", err)

    def register_callback(self, callback: Callable[[int, bytearray], None]) -> None:
        """Register a callback for notifications."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[int, bytearray], None]) -> None:
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def subscribe_notifications(self) -> None:
        """
        Subscribe to desk notifications for height updates.

        Raises:
            ConnectionError: If not connected
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to desk")

        await self._client.start_notify(
            READ_CHARACTERISTIC_UUID,
            self._handle_notification
        )
        _LOGGER.debug("Subscribed to notifications")

    async def unsubscribe_notifications(self) -> None:
        """Unsubscribe from desk notifications."""
        if self.is_connected:
            try:
                await self._client.stop_notify(READ_CHARACTERISTIC_UUID)
            except BleakError as err:
                _LOGGER.warning("Error unsubscribing: %s", err)
        _LOGGER.debug("Unsubscribed from notifications")

    # =========================================================================
    # Extended Features (Protocol Not Yet Captured)
    # =========================================================================
    # The following methods are based on GraphQL API analysis of the Ergomate app.
    # The actual BLE packet format is UNKNOWN and needs to be captured.
    #
    # To capture these packets:
    # 1. Use Android's HCI Snoop Log or nRF Connect app
    # 2. Trigger the feature in the Ergomate app
    # 3. Find the write to 0000ff02 characteristic
    # 4. Update the command bytes in desk_const.py
    # =========================================================================

    async def beep(self, duration_ms: int = 500) -> None:
        """
        Make the desk emit a beep sound.

        ⚠️ NOT IMPLEMENTED - This is a CLOUD-BASED feature.

        Based on reverse engineering, the Ergomate app sends beep commands
        via GraphQL API to the cloud server, which then communicates with
        the desk over WiFi (not BLE). The desk must be network-connected.

        GraphQL mutation: SetMyDeskBeep($id: String!, $milliseconds: Int!)

        This feature cannot be implemented via BLE without knowing
        the Ergomate cloud API credentials/authentication.

        Args:
            duration_ms: Beep duration in milliseconds (default: 500)

        Raises:
            NotImplementedError: Always - cloud API not accessible
        """
        raise NotImplementedError(
            "Beep command is a cloud-based feature in the Ergomate app. "
            "It uses GraphQL API (SetMyDeskBeep) and requires WiFi connectivity, "
            "not BLE. Cannot be implemented without cloud API access."
        )

    async def lock(self) -> None:
        """
        Lock the desk to prevent physical button operation (child lock).

        ⚠️ NOT IMPLEMENTED - This is a CLOUD-BASED feature.

        Based on reverse engineering, the Ergomate app sends lock commands
        via GraphQL API to the cloud server (SetMyDeskLocked mutation).
        The desk uses the constant 'CHILDLOCK' internally.

        GraphQL mutation: SetMyDeskLocked($id: String!, $locked: Boolean!)

        This feature cannot be implemented via BLE without knowing
        the Ergomate cloud API credentials/authentication.

        Raises:
            NotImplementedError: Always - cloud API not accessible
        """
        raise NotImplementedError(
            "Lock command is a cloud-based feature in the Ergomate app. "
            "It uses GraphQL API (SetMyDeskLocked) and requires WiFi connectivity, "
            "not BLE. Cannot be implemented without cloud API access."
        )

    async def unlock(self) -> None:
        """
        Unlock the desk to allow physical button operation.

        ⚠️ NOT IMPLEMENTED - This is a CLOUD-BASED feature.

        Based on reverse engineering, the Ergomate app sends unlock commands
        via GraphQL API to the cloud server (SetMyDeskLocked mutation with locked=false).

        GraphQL mutation: SetMyDeskLocked($id: String!, $locked: Boolean!)

        This feature cannot be implemented via BLE without knowing
        the Ergomate cloud API credentials/authentication.

        Raises:
            NotImplementedError: Always - cloud API not accessible
        """
        raise NotImplementedError(
            "Unlock command is a cloud-based feature in the Ergomate app. "
            "It uses GraphQL API (SetMyDeskLocked) and requires WiFi connectivity, "
            "not BLE. Cannot be implemented without cloud API access."
        )

    async def factory_reset(self) -> None:
        """
        Perform a factory reset of the desk controller.

        ⚠️ NOT IMPLEMENTED - This is a CLOUD-BASED feature.
        ⚠️ USE WITH CAUTION - This would reset all desk settings!

        Based on reverse engineering, the Ergomate app sends factory reset
        via GraphQL API to the cloud server. The desk uses the constant
        'FACTORYRESET' internally.

        GraphQL mutation: SetMyDeskFactoryReset($id: String!)

        This feature cannot be implemented via BLE without knowing
        the Ergomate cloud API credentials/authentication.

        Raises:
            NotImplementedError: Always - cloud API not accessible
        """
        raise NotImplementedError(
            "Factory reset is a cloud-based feature in the Ergomate app. "
            "It uses GraphQL API (SetMyDeskFactoryReset) and requires WiFi connectivity, "
            "not BLE. Cannot be implemented without cloud API access."
        )


async def discover_desks(timeout: float = DEFAULT_SCAN_TIMEOUT) -> list[BLEDevice]:
    """
    Scan for ErgoMate Classic desks.

    Args:
        timeout: Scan duration in seconds (default: 10)

    Returns:
        List of discovered desk BLE devices
    """
    _LOGGER.debug("Scanning for desks (timeout: %ss)", timeout)
    devices = await BleakScanner.discover(timeout=timeout)

    desks = []
    for device in devices:
        # Filter by name prefix - Classic desks use "BLT_"
        if device.name and device.name.startswith(DEVICE_NAME_PREFIX_CLASSIC):
            _LOGGER.info("Found desk: %s (%s)", device.name, device.address)
            desks.append(device)

    _LOGGER.debug("Found %d desk(s)", len(desks))
    return desks


async def discover_desk_by_address(
    address: str,
    timeout: float = DEFAULT_SCAN_TIMEOUT
) -> Optional[BLEDevice]:
    """
    Find a specific desk by its BLE address.

    Args:
        address: BLE MAC address to find
        timeout: Scan duration in seconds

    Returns:
        BLEDevice if found, None otherwise
    """
    _LOGGER.debug("Searching for desk at %s", address)
    device = await BleakScanner.find_device_by_address(address, timeout=timeout)
    if device:
        _LOGGER.info("Found desk: %s (%s)", device.name, device.address)
    else:
        _LOGGER.warning("Desk not found at %s", address)
    return device
