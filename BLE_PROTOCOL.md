# ErgoMate Standing Desk BLE Protocol

> **Source:** Reverse-engineered from ErgoMate Android app v1.4.3 (React Native + Hermes bytecode)

This document describes the Bluetooth Low Energy (BLE) protocol used by ErgoMate standing desks. It covers service discovery, command packets, height notifications, and known limitations.

---

## Table of Contents

1. [Overview](#overview)
2. [BLE Services & Characteristics](#ble-services--characteristics)
   - [Protocol Selection](#protocol-selection)
   - [HandsetVariant Enum](#handsetvariant-enum)
   - [Classic Desk (BLT_ and MX Series)](#classic-desk-blt_-and-mx-series)
   - [WiFi Desk Variants (H76 Series)](#wifi-desk-variants-h76-series)
3. [Classic Desk Protocol](#classic-desk-protocol)
   - [Command Packet Structure (5 bytes)](#command-packet-structure-5-bytes)
   - [Movement Commands](#movement-commands)
   - [Move to Height Command (9 bytes)](#move-to-height-command-9-bytes)
   - [Height Notifications](#height-notifications)
4. [Connection & Discovery](#connection--discovery)
5. [Error Codes](#error-codes)
   - [BLE Library Error Codes](#general-errors)
   - [Desk Hardware Error Codes (E01-E91)](#desk-hardware-error-codes-e01-e91)
6. [Implementation Notes](#implementation-notes)
7. [Known Issues & Workarounds](#known-issues--workarounds)
8. [Reference Implementation](#reference-implementation)
9. [Appendix: Verified Test Results](#appendix-verified-test-results)

> 📘 **WiFi Desks:** For WiFi-enabled desks (H76 series), see [WIFI_PROTOCOL.md](WIFI_PROTOCOL.md)

---

## Overview

ErgoMate desks use BLE for direct motor control. The protocol supports:

| Feature | BLE Support | Notes |
|---------|-------------|-------|
| Move Up/Down | ✅ Yes | Continuous until stopped |
| Stop | ✅ Yes | Immediate halt |
| Move to Height | ✅ Yes | Absolute positioning |
| Height Notifications | ✅ Yes | Real-time during movement |
| Beep | ❌ No | Cloud API only |
| Child Lock | ❌ No | Cloud API only |
| Factory Reset | ❌ No | Cloud API only |

---

## BLE Services & Characteristics

### Protocol Selection

The ErgoMate app supports two distinct BLE protocols, determined by the **Service UUID advertised** by the device:

| Service UUID | Protocol | Name Patterns |
|--------------|----------|---------------|
| `0000ff00-...` | Classic | `^BLT_` (e.g., `BLT_F0F9F1`), `^MX` (e.g., `MX1234`) |
| `0000a00a-...` | WiFi | `^H\d+` (e.g., `H76_WIFIDESK`) |

> **Note:** The protocol is determined by the Service UUID, not the device name. MX-series devices use the same Classic protocol as BLT_ devices.

### HandsetVariant Enum

The app internally classifies devices using `HandsetVariant`:
- **`Classic`**: Uses Classic BLE protocol (0000ff00 service)
- **`Wifi`**: Uses WiFi BLE protocol (0000a00a service)

### Classic Desk (BLT_ and MX Series)

Devices advertising the Classic service UUID. Common name patterns:
- `BLT_XXXXXX` - Original classic desk series (6-character hex suffix)
- `MXNNNN` - Newer MX series (uses same protocol as BLT_)

| Type | UUID |
|------|------|
| **Service** | `0000ff00-0000-1000-8000-00805f9b34fb` |
| **Write Characteristic** | `0000ff02-0000-1000-8000-00805f9b34fb` |
| **Read/Notify Characteristic** | `0000ff01-0000-1000-8000-00805f9b34fb` |

> **MX Series:** These appear to be a newer product line that uses the identical Classic BLE protocol. The app accepts them via the `^MX` name pattern but handles them exactly like BLT_ devices.

### Frame Types (Product Variants)

The app recognizes several desk frame configurations (purely cosmetic/UI information, does not affect BLE protocol):

| Frame Type | Description |
|------------|-------------|
| Dual motor desk | Standard 2-leg desk |
| Dual motor DUO desk | 2-leg desk variant |
| Triple motor 90° desk | 3-leg desk (corner/L-shaped, 90° angle) |
| Triple motor 120° desk | 3-leg desk (120° angle) |
| Triple motor 180° desk | 3-leg desk (linear 180° configuration) |

> **Note:** Frame type affects the app's UI positioning but does **not** change the BLE protocol. All frames use the same command structure.

### WiFi Desk Variants (H76 Series)

> 📘 **See:** [WIFI_PROTOCOL.md](WIFI_PROTOCOL.md) for complete WiFi desk documentation.

**Models (12 variants defined in app):**
- `H76_WIFIDESK` (standard)
- `H76_WIFIDESK_2` through `H76_WIFIDESK_9`
- `H76_TIMDESK` (custom variant)
- `H76_RAMONDESK` (custom variant)

| Type | UUID |
|------|------|
| **Service** | `0000a00a-0000-1000-8000-00805f9b34fb` |
| **Write Characteristic** | `0000b003-0000-1000-8000-00805f9b34fb` |
| **Read Characteristic** | `0000b002-0000-1000-8000-00805f9b34fb` |

---

## Classic Desk Protocol

### Command Packet Structure (5 bytes)

All basic commands use a 5-byte packet format:

```
┌────────┬──────────┬─────────┬──────────┬────────────┐
│ Byte 0 │  Byte 1  │ Byte 2  │  Byte 3  │   Byte 4   │
├────────┼──────────┼─────────┼──────────┼────────────┤
│ Header │ Reserved │ Command │ Checksum │ Terminator │
│  0xA5  │   0x00   │   CMD   │   CHK    │    0xFF    │
└────────┴──────────┴─────────┴──────────┴────────────┘
```

| Byte | Name | Value | Description |
|------|------|-------|-------------|
| 0 | Header | `0xA5` (165) | Start marker, always fixed |
| 1 | Reserved | `0x00` (0) | Always zero |
| 2 | Command | varies | Action to perform |
| 3 | Checksum | `0xFF ^ CMD` | XOR of 0xFF and command byte |
| 4 | Terminator | `0xFF` (255) | End marker, always fixed |

#### Checksum Calculation

```python
checksum = 0xFF ^ command_byte
```

**Examples:**
- UP: `0xFF ^ 0x20 = 0xDF` (223)
- DOWN: `0xFF ^ 0x40 = 0xBF` (191)
- STOP: `0xFF ^ 0x00 = 0xFF` (255)

---

### Movement Commands

| Action | Command Byte | Hex Packet | Decimal Packet |
|--------|-------------|------------|----------------|
| **Move Up** | `0x20` (32) | `A5 00 20 DF FF` | `[165, 0, 32, 223, 255]` |
| **Move Down** | `0x40` (64) | `A5 00 40 BF FF` | `[165, 0, 64, 191, 255]` |
| **Stop** | `0x00` (0) | `A5 00 00 FF FF` | `[165, 0, 0, 255, 255]` |

#### Movement Behavior

- Commands are **continuous** - the desk moves until:
  1. A STOP command is received
  2. Physical limit is reached (min/max height)
  3. Obstacle detected (motor protection triggers)
- Only **one command** is needed to start movement; do not spam commands
- Always send STOP to halt movement

---

### Move to Height Command (9 bytes)

For absolute positioning, use the extended 9-byte packet:

```
┌────────┬─────────┬────────┬──────────┬─────────┬───────┬───────┬──────────┬────────────┐
│ Byte 0 │ Byte 1  │ Byte 2 │  Byte 3  │ Byte 4  │ Byte 5│ Byte 6│  Byte 7  │   Byte 8   │
├────────┼─────────┼────────┼──────────┼─────────┼───────┼───────┼──────────┼────────────┤
│ Header │ Command │ Param1 │ High Byte│ Low Byte│ Zero  │ Zero  │ Checksum │ Terminator │
│  0xA6  │  0xA8   │  0x01  │    HB    │   LB    │ 0x00  │ 0x00  │   CHK    │    0xFF    │
└────────┴─────────┴────────┴──────────┴─────────┴───────┴───────┴──────────┴────────────┘
```

| Byte | Name | Value | Description |
|------|------|-------|-------------|
| 0 | Header | `0xA6` (166) | Height command header |
| 1 | Command ID | `0xA8` (168) | Move absolute command |
| 2 | Param1 | `0x01` (1) | Always 1 |
| 3 | High Byte | `height >> 8` | Target height high byte |
| 4 | Low Byte | `height & 0xFF` | Target height low byte |
| 5 | Zero 1 | `0x00` | Padding |
| 6 | Zero 2 | `0x00` | Padding |
| 7 | Checksum | XOR of bytes 2-6 | See calculation below |
| 8 | Terminator | `0xFF` (255) | End marker |

#### Height Range

| Property | Value |
|----------|-------|
| Minimum | 650mm (65.0 cm) |
| Maximum | 1300mm (130.0 cm) |

> ⚠️ The firmware clamps values outside this range.

#### Checksum Calculation (Height Command)

```python
# XOR of bytes 2 through 6 (Param1, HB, LB, Zero1, Zero2)
# Note: Command byte (0xA8) is NOT included
checksum = param1 ^ high_byte ^ low_byte ^ 0x00 ^ 0x00
checksum = 0x01 ^ high_byte ^ low_byte
```

#### Example: Move to 80cm (800mm)

```python
height_mm = 800        # 0x0320
high_byte = 0x03       # 800 >> 8
low_byte = 0x20        # 800 & 0xFF
checksum = 0x01 ^ 0x03 ^ 0x20 ^ 0x00 ^ 0x00 = 0x22

# Final packet:
[0xA6, 0xA8, 0x01, 0x03, 0x20, 0x00, 0x00, 0x22, 0xFF]
```

#### Python Implementation

```python
def create_height_command(height_mm: int) -> bytes:
    """Create 9-byte packet to move desk to specific height."""
    height_mm = max(650, min(1300, height_mm))  # Clamp

    high_byte = (height_mm >> 8) & 0xFF
    low_byte = height_mm & 0xFF
    checksum = 0x01 ^ high_byte ^ low_byte

    return bytes([
        0xA6, 0xA8, 0x01,
        high_byte, low_byte,
        0x00, 0x00,
        checksum, 0xFF
    ])
```

---

### Height Notifications

The desk sends height updates via BLE notifications on the read characteristic (`0000ff01`).

- **Format**: 4 bytes
- **Encoding**: Classic ASCII digits (0-9) representing height in decimeters (e.g., `0720` = 72.0 cm).
- **Masking Detail**: The official app applies a bitwise mask `0xCF` (207) to each byte. This effectively converts ASCII characters '0'-'9' (0x30-0x39) directly into their integer values (0-9) by clearing bits 4 and 5.
  - Example: Received `0x30 0x37 0x32 0x30` (ASCII "0720")
  - Masked: `0x00 0x07 0x02 0x00` (Ints 0, 7, 2, 0)
  - Joined: "0720" → 72.0 cm

**Standard Parsing:**
Since the masking produces the same digits as the ASCII characters themselves, you can simply decode as ASCII string and parse as float/int.

**Example Payload:**
`30 37 32 30` (Hex) → "0720" (ASCII) → 72.0 cm

#### Format

| Property | Value |
|----------|-------|
| Data Length | 4 bytes |
| Encoding | ASCII digits |
| Unit | Millimeters |

#### Example

```
Raw bytes:  [0x30, 0x37, 0x35, 0x30]
Hex:        30 37 35 30
ASCII:      "0750"
Height:     750mm = 75.0 cm
```

#### Decoding

| Hex | ASCII | Meaning |
|-----|-------|---------|
| `30 37 31 30` | "0710" | 710mm = 71.0 cm |
| `30 38 30 30` | "0800" | 800mm = 80.0 cm |
| `31 33 30 30` | "1300" | 1300mm = 130.0 cm |

#### Python Implementation

```python
def parse_height(data: bytearray) -> float | None:
    """Parse height from notification data."""
    if len(data) == 4:
        try:
            height_mm = int(data.decode('ascii'))
            height_cm = height_mm / 10.0
            if 60.0 <= height_cm <= 135.0:  # Valid range check
                return height_cm
        except (ValueError, UnicodeDecodeError):
            pass
    return None
```

#### Native App Parsing Detail

The native app applies a bit mask (`0xCF` / 207) to each byte before joining:

```javascript
// App's internal parsing (for reference)
buffer.map(byte => byte & 0xCF).join('')
```

This mask (`0b11001111`) clears bits 4 and 5, which may help filter noise. In practice, valid ASCII digit bytes (`0x30`-`0x39`) are unaffected by this mask, so standard ASCII decoding works correctly.

#### Notification Behavior

| Behavior | Description |
|----------|-------------|
| During Movement | Multiple notifications per second (~5-10 Hz) |
| Stationary | **No notifications sent** |
| After Connection | No automatic notification; must read or send command |

> ⚠️ **Important:** The desk does not send notifications when stationary. To get the initial height after connecting, either:
> 1. Read the characteristic directly with `read_gatt_char()`
> 2. Send a STOP command to trigger a notification

---

## Connection & Discovery

### Device Discovery

The app uses regex patterns to identify desk types during BLE scanning:

| Desk Type | Name Pattern (Regex) | Service Filter |
|-----------|---------------------|----------------|
| Classic | `^BLT_` | `0000ff00-*` |
| WiFi | `^H\d+` (e.g., H76_*) | `0000a00a-*` |
| MX Series | `^MX` | Unknown (not fully documented) |

> ⚠️ **MX Series:** Devices starting with `MX` are recognized by the app but their protocol is not yet documented. They may use the same protocol as Classic or WiFi desks.

### Scan Configuration

The app uses the following BLE scan settings:

| Setting | Value | Description |
|---------|-------|-------------|
| `allowDuplicates` | `true` | Report same device multiple times |
| `scanMode` | `LowLatency` (2) | Fastest scan interval, highest power |
| `callbackType` | `AllMatches` (1) | Report all matching advertisements |

#### Scan Mode Options (Android)

| Mode | Value | Description |
|------|-------|-------------|
| Opportunistic | -1 | Scan only when other apps scan |
| LowPower | 0 | ~5000ms interval, lowest power |
| Balanced | 1 | ~2500ms interval, balanced |
| LowLatency | 2 | ~100ms interval, highest power |

#### Callback Type Options

| Type | Value | Description |
|------|-------|-------------|
| AllMatches | 1 | All advertisements |
| FirstMatch | 2 | Only first match per device |
| MatchLost | 4 | When device stops advertising |

### Discovery Process

The app follows this sequence to discover and validate desks:

```
1. Start BLE Scan
   └─> allowDuplicates: true, scanMode: LowLatency

2. For each discovered device:
   ├─> Clean device name (trim, remove control chars)
   ├─> Test name against patterns: [/^BLT_/, /^H\d+/, /^MX/]
   ├─> If no match → skip device
   └─> If match → check for duplicates

3. Duplicate Detection:
   ├─> Compare by name (trimmed)
   ├─> Compare by localName (trimmed)
   └─> Compare by device id
   └─> If duplicate → update existing entry

4. Auto-connect (if enabled):
   └─> If device name matches saved auto-connect name → connect
```

### Name Cleaning

Device names are sanitized before pattern matching:

```javascript
function cleanupDeviceName(name) {
    if (!name) return '';
    return name.trim().replace(/[\x00-\x1F\x7F]/g, '');
}
```

This removes:
- Leading/trailing whitespace
- Control characters (0x00-0x1F, 0x7F)

### Connection Validation

After connecting, the app validates the device:

```
1. Connect to device
2. Wait 1 second (for stability)
3. Check device.isConnected → if false, throw error
4. Discover all services and characteristics
5. Check device.serviceUUIDs.length > 0 → if false, throw error
6. Determine desk type by checking serviceUUIDs:
   ├─> If includes '0000a00a-...' → WiFi desk
   └─> If includes '0000ff00-...' → Classic desk
7. Subscribe to notifications on read characteristic
```

### Error Handling During Discovery

| Error | Cause |
|-------|-------|
| "BLE device is empty after connection attempt, probably timed out" | Device not responding |
| "BLE device exposed no services" | Service discovery failed |
| "Bluetooth is uninitialized or not available on this device" | BT adapter unavailable |

### Connection Notes

| Property | Value |
|----------|-------|
| Pairing Required | No (for commands) |
| Authentication | None |
| Write Type | Write With Response |
| Connection Delay | ~1 second before subscribing |

### Recommended Connection Sequence

```python
# 1. Connect to device
await client.connect()

# 2. Wait briefly for service discovery
await asyncio.sleep(0.5)

# 3. Subscribe to notifications
await client.start_notify(READ_UUID, callback)

# 4. Read initial height (notifications don't auto-send)
initial = await client.read_gatt_char(READ_UUID)

# 5. If empty, send STOP to trigger notification
if not initial or initial == b'\x00':
    await client.write_gatt_char(WRITE_UUID, STOP_CMD)
```

---

## Error Codes

BLE error codes from the bleshadow library used by the ErgoMate app:

### General Errors

| Code | Name | Description |
|------|------|-------------|
| 0 | UnknownError | Generic/unknown error |
| 1 | BluetoothManagerDestroyed | BLE manager was destroyed |
| 2 | OperationCancelled | Operation was cancelled |
| 3 | OperationTimedOut | Operation timed out |
| 4 | OperationStartFailed | Failed to start operation |
| 5 | InvalidIdentifiers | Invalid UUIDs or identifiers |

### Bluetooth State Errors (100-105)

| Code | Name | Description |
|------|------|-------------|
| 100 | BluetoothUnsupported | BLE not supported on device |
| 101 | BluetoothUnauthorized | Bluetooth permission denied |
| 102 | BluetoothPoweredOff | Bluetooth is turned off |
| 103 | BluetoothInUnknownState | Unknown Bluetooth state |
| 104 | BluetoothResetting | Bluetooth is resetting |
| 105 | BluetoothStateChangeFailed | Failed to change BT state |

### Device Errors (200-206)

| Code | Name | Description |
|------|------|-------------|
| 200 | DeviceConnectionFailed | Failed to connect to device |
| 201 | DeviceDisconnected | Device disconnected unexpectedly |
| 202 | DeviceRSSIReadFailed | Failed to read RSSI |
| 203 | DeviceAlreadyConnected | Device is already connected |
| 204 | DeviceNotFound | Device not found during scan |
| 205 | DeviceNotConnected | Device is not connected |
| 206 | DeviceMTUChangeFailed | Failed to change MTU |

### Service Errors (300-303)

| Code | Name | Description |
|------|------|-------------|
| 300 | ServicesDiscoveryFailed | Failed to discover services |
| 301 | IncludedServicesDiscoveryFailed | Failed to discover included services |
| 302 | ServiceNotFound | Service UUID not found |
| 303 | ServicesNotDiscovered | Services not yet discovered |

### Characteristic Errors (400-406)

| Code | Name | Description |
|------|------|-------------|
| 400 | CharacteristicsDiscoveryFailed | Failed to discover characteristics |
| 401 | CharacteristicWriteFailed | Write to characteristic failed |
| 402 | CharacteristicReadFailed | Read from characteristic failed |
| 403 | CharacteristicNotifyChangeFailed | Failed to enable/disable notifications |
| 404 | CharacteristicNotFound | Characteristic UUID not found |
| 405 | CharacteristicsNotDiscovered | Characteristics not yet discovered |
| 406 | CharacteristicInvalidDataFormat | Invalid data format |

### Descriptor Errors (500-502)

| Code | Name | Description |
|------|------|-------------|
| 500 | DescriptorsDiscoveryFailed | Failed to discover descriptors |
| 501 | DescriptorWriteFailed | Write to descriptor failed |
| 502 | DescriptorReadFailed | Read from descriptor failed |

### Desk Hardware Error Codes (E01-E91)

The desk firmware can report hardware error codes via the handset display and GraphQL API (`lastErrorCode` field). These are NOT sent over BLE but are documented here for completeness:

#### Power & System Errors

| Code | Description | Resolution |
|------|-------------|------------|
| E01 | Main power supply voltage is above 45V | Check main power supply |
| E02 | Rod height difference between legs > 1 cm | Initialize the frame |
| E04 | Handset connection or communication error | Check handset power cable |
| E05 | Obstruction detected / Power startup failed (< 20V) | Release button and restart |
| E06 | Power protection triggered (< 20V) | Change or check main power cable |
| E07 | Power reconnection required | Reconnect power |
| E08 | Tilt detected during frame operation | Initialize the frame |
| E09 | Motor overheated, wait 18 minutes | Let system rest for at least 18 minutes |

#### Motor 1 Errors (E11-E18)

| Code | Description | Resolution |
|------|-------------|------------|
| E11 | Motor 1 not connected | Check motor 1 power cable |
| E12 | Motor 1 current sampling error | Replace control box |
| E13 | Motor 1 phase line disconnected | Verify motor 1 phase line connection |
| E14 | Motor 1 sensor error / wire disconnected | Check signal or change motor 1 power cable |
| E15 | Short circuit in motor 1 | Replace motor |
| E16 | Blocked rotor in motor 1 | Initialize the frame |
| E17 | Motor 1 running in wrong direction | Change motor wire |
| E18 | Motor 1 overload | Reduce desk weight |

#### Motor 2 Errors (E21-E28)

| Code | Description | Resolution |
|------|-------------|------------|
| E21 | Motor 2 not connected | Check motor 2 power cable |
| E22 | Motor 2 current sampling error | Replace control box |
| E23 | Motor 2 phase line disconnected | Verify motor 2 phase line connection |
| E24 | Motor 2 sensor error / wire disconnected | Check signal or change motor 2 power cable |
| E25 | Short circuit in motor 2 | Replace motor |
| E26 | Blocked rotor in motor 2 | Initialize the frame |
| E27 | Motor 2 running in wrong direction | Change motor wire |
| E28 | Motor 2 overload | Reduce desk weight |

#### Motor 3 Errors (E31-E38) - Triple Motor Desks Only

| Code | Description | Resolution |
|------|-------------|------------|
| E31 | Motor 3 not connected | Check motor 3 connection cable |
| E32 | Motor 3 current/phase sampling error | Release button and restart |
| E33 | Motor 3 Hall sensor error / wire disconnected | Verify motor 3 phase line connection |
| E34 | Check motor 3 Hall signal / wire | Check Hall signal or replace motor 3 cable |
| E35 | Short circuit in motor 3 | Replace motor |
| E36 | Reset required | Reset operation |
| E37 | Motor 3 running in wrong direction | Change motor or Hall wire |
| E38 | Motor 3 overload | Reduce desk weight |

#### Control Box Errors (E40-E43)

| Code | Description | Resolution |
|------|-------------|------------|
| E40 | Control box disconnected | Check connection wires |
| E41 | Serial signal error | Check connection wires or change control box |
| E42 | EEPROM error | Replace control box |
| E43 | Anti-collision sensor error | Replace control box |

#### General Motor Error

| Code | Description | Resolution |
|------|-------------|------------|
| E91 | One or more motors defective or not connected | Check all motor connection cables |

> **Note:** These error codes are displayed on the physical handset and can be retrieved via the GraphQL API through `lastErrorCode` and `lastErrorDetectedAt` fields. They are not transmitted via BLE.

---

## Implementation Notes

### Write Mode

Always use **Write With Response** (`writeCharacteristicWithResponseForService`). The native app uses this mode, and using "Write Without Response" may result in commands being ignored.

### Data Encoding (Native App)

The native app (React Native) uses this encoding chain:

```javascript
// 1. Create command array
const cmd = [165, 0, 32, 223, 255];

// 2. Convert to Uint8Array
const uint8 = new Uint8Array(cmd);

// 3. Convert to Buffer
const buffer = Buffer.from(uint8.buffer);

// 4. Encode to base64 (required by bleshadow library)
const base64 = buffer.toString("base64");

// 5. Write to characteristic
await writeCharacteristic(serviceUUID, writeUUID, base64);
```

> **Note:** Most BLE libraries (like Python's `bleak`) accept raw bytes directly, so the base64 step is typically not needed.

### Height Range Validation

Always validate and clamp height values:

```python
MIN_HEIGHT_MM = 650   # 65.0 cm
MAX_HEIGHT_MM = 1300  # 130.0 cm

height_mm = max(MIN_HEIGHT_MM, min(MAX_HEIGHT_MM, height_mm))
```

---

## Known Issues & Workarounds

### 1. Glitch Height Values

**Problem:** The desk occasionally sends erroneous height values (e.g., `0xCB` = 203, or "2032" = 203.2 cm) that are outside the physical range.

**Cause:** Likely transient firmware glitches or electrical noise.

**Workaround:** Implement glitch filtering:

```python
# 1. Range check (primary filter)
if not (60.0 <= height_cm <= 135.0):
    return None  # Ignore

# 2. Jump detection (secondary filter)
if previous_height is not None:
    if abs(height_cm - previous_height) > 5.0:
        # Require 3 consecutive readings to accept large jump
        pending_count += 1
        if pending_count < 3:
            return None  # Ignore suspicious jump
```

### 2. No Initial Height After Connection

**Problem:** Home Assistant shows "Unknown" height after restart because the desk doesn't send notifications until moved.

**Solution:** Read the characteristic directly after connecting:

```python
await client.start_notify(READ_UUID, callback)
initial = await client.read_gatt_char(READ_UUID)
if initial and initial != b'\x00':
    process_height(initial)
else:
    # Send STOP to trigger a notification
    await client.write_gatt_char(WRITE_UUID, STOP_COMMAND)
```

### 3. Connection Loss During Sleep

**Problem:** BLE connection may drop when the desk enters sleep mode.

**Solution:** Implement auto-reconnection with exponential backoff:

```python
async def monitor_connection():
    while not shutdown:
        if not client.is_connected:
            try:
                await client.connect()
                await subscribe_notifications()
            except BleakError:
                await asyncio.sleep(5)  # Wait and retry
        await asyncio.sleep(5)
```

---

## Reference Implementation

See the Home Assistant custom component for a complete implementation:

| File | Description |
|------|-------------|
| `desk_const.py` | UUIDs and protocol constants |
| `desk_api.py` | BLE client implementation |
| `cover.py` | Home Assistant cover entity |
| `sensor.py` | Height sensor entity |
| `number.py` | Target height number entity |

### Quick Start (Python)

```python
import asyncio
from bleak import BleakClient

SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb"
WRITE_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"
READ_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"

def create_command(cmd: int) -> bytes:
    return bytes([0xA5, 0x00, cmd, 0xFF ^ cmd, 0xFF])

CMD_UP = create_command(0x20)
CMD_DOWN = create_command(0x40)
CMD_STOP = create_command(0x00)

async def main():
    async with BleakClient("AA:BB:CC:DD:EE:FF") as client:
        # Subscribe to height updates
        def on_notify(sender, data):
            height = int(data.decode('ascii')) / 10
            print(f"Height: {height} cm")

        await client.start_notify(READ_UUID, on_notify)

        # Move up for 2 seconds
        await client.write_gatt_char(WRITE_UUID, CMD_UP, response=True)
        await asyncio.sleep(2)
        await client.write_gatt_char(WRITE_UUID, CMD_STOP, response=True)

asyncio.run(main())
```

---

## Appendix: Verified Test Results

Testing performed with device `BLT_F0F9F1` (December 2025):

| Test | Result |
|------|--------|
| BLE Discovery | ✅ Device found |
| Connection | ✅ Successful |
| Move Up Command | ✅ Desk moved up |
| Move Down Command | ✅ Desk moved down |
| Stop Command | ✅ Desk stopped |
| Move to Height | ✅ Desk moved to target |
| Height Notification | ✅ Received correctly |
| Notification Format | ✅ ASCII confirmed |
| Checksum Formula | ✅ 0xFF ^ CMD verified |

---

## Legal Notice

This documentation is provided for educational and interoperability purposes.

---

## Related Documentation

- [WIFI_PROTOCOL.md](WIFI_PROTOCOL.md) - WiFi desk protocol and cloud features
- [REVERSE_ENGINEERING_GUIDE.md](REVERSE_ENGINEERING_GUIDE.md) - How to decompile the ErgoMate app
- [AGENTS.md](AGENTS.md) - AI agent context guide
