# AGENTS.md - AI Agent Context Guide

## Project Overview

**ergomate-homeassistant** is a Home Assistant custom integration for controlling Ergomate standing desks via Bluetooth Low Energy (BLE).

- **Type**: Local BLE integration (no cloud dependency)
- **Home Assistant**: 2023.6.0+ | **IoT Class**: `local_push` | **BLE Library**: `bleak>=0.19.0`

### Related Documentation

- [BLE_PROTOCOL.md](BLE_PROTOCOL.md) - Complete BLE protocol specification (commands, checksums, quirks)
- [REVERSE_ENGINEERING_GUIDE.md](REVERSE_ENGINEERING_GUIDE.md) - How to analyze the ErgoMate APK with JADX/hermes_rs

---

## Architecture

```
custom_components/ergomate/
├── __init__.py       # Integration entry point, platform setup
├── config_flow.py    # BLE device discovery UI with dropdown
├── const.py          # HA domain constants (DOMAIN, CONF_*)
├── cover.py          # CoverEntity (desk up/down/stop/position)
├── sensor.py         # SensorEntity (height in cm)
├── desk_api.py       # Core BLE communication (ErgomateDesk class)
├── desk_const.py     # BLE protocol constants (UUIDs, commands)
├── manifest.json     # HA integration manifest
└── strings.json      # Config flow UI strings
```

## BLE Protocol Quick Reference

**Device Discovery**: Name patterns `BLT_*` or `MX*`, Service UUID `0000ff00-0000-1000-8000-00805f9b34fb`

| UUID | Type | Purpose |
|------|------|---------|
| `0000ff00-...` | Service | Primary BLE service |
| `0000ff02-...` | Write | Send commands (MUST use `response=True`) |
| `0000ff01-...` | Notify | Receive height updates |

**Motor Commands (5 bytes)**: `[0xA5, 0x00, CMD, 0xFF^CMD, 0xFF]`
- UP: CMD=`0x20`, DOWN: CMD=`0x40`, STOP: CMD=`0x00`

**Height Command (9 bytes)**: `[0xA6, 0xA8, 0x01, HB, LB, 0x00, 0x00, XOR, 0xFF]`
- HB/LB = height in mm (650-1300), XOR = `0x01 ^ HB ^ LB`

**Height Notifications**: 4-byte ASCII. **Important**: Apply bitmask `0xCF` to each byte before decoding (e.g., `b & 0xCF`).
- Example: `"0720"` (bytes `0x30 0x37 0x32 0x30`) → 72.0cm

## Protocol Quirks (MUST Handle)

1. **Glitches**: Desk sends invalid values like `"2032"` (203.2cm) or `"0600"` (60.0cm). STRICTLY filter received height to **65cm - 130cm** (650mm - 1300mm). This handles all known glitches.
2. **Initial Silence**: No height on connect. Send `CMD_STOP` after subscribing to force status report.
3. **Precision**: Protocol supports 1mm but hardware often rounds to nearest cm.

## Key Classes

### `ErgomateDesk` (desk_api.py)

Core BLE communication class. Key methods:

| Method | Description |
|--------|-------------|
| `connect()` | Connect with auto-reconnect |
| `disconnect()` | Stop desk and disconnect |
| `move_up()` / `move_down()` / `stop()` | Motor control |
| `move_to_height(height_cm)` | Move to absolute height (65-130cm) |
| `register_callback(fn)` / `unregister_callback(fn)` | Height notification callbacks |
| `subscribe_notifications()` | Enable height updates |

**Properties**: `is_connected`, `is_moving`, `current_height`, `raw_height`

**Cloud-Only (NOT implementable via BLE)**: `beep()`, `lock()`, `unlock()`, `factory_reset()` - require GraphQL API

### `ErgomateDeskCover` (cover.py)

Home Assistant CoverEntity. Device class: `damper`. Features: OPEN, CLOSE, STOP, SET_POSITION.

**Position Mapping**: 0% = 65cm, 100% = 130cm

### `ErgomateHeightSensor` (sensor.py)

SensorEntity with device class `distance`, unit `cm`, state class `measurement`.

### `ConfigFlow` (config_flow.py)

BLE discovery UI. Matches devices with service UUID `0000ff00-...` OR name prefix `BLT_`.

**Config Options**: `address` (required), `name` (default: "Ergomate Desk"), `height_offset` (default: 0.0)

## Critical Implementation Rules

1. **All BLE operations must be async** with `await`
2. **Write with response**: `await client.write_gatt_char(UUID, data, response=True)` - NEVER use `response=False`
3. **Clean up on unload**: Call `desk.disconnect()` in `async_unload_entry()`
4. **Use callback pattern**: Register callbacks for real-time height updates, call `self.async_write_ha_state()` on update
5. **Group entities under device**: Use consistent `DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})`

## Common Pitfalls

| Pitfall | Wrong | Right |
|---------|-------|-------|
| Blocking BLE | `self.desk.move_up()` | `await self._desk.move_up()` |
| Write mode | `write_gatt_char(UUID, data)` | `write_gatt_char(UUID, data, response=True)` |
| Motor checksum | XOR all bytes | `0xFF ^ CMD` only |
| Height checksum | `0xFF ^ HB ^ LB` | `0x01 ^ HB ^ LB` |
| Position/Height | Mixing cm and % | Position: 0-100%, Height: 65-130cm, Protocol: 650-1300mm |

## Constants Reference (desk_const.py)

```python
SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb"
WRITE_CHARACTERISTIC_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"
READ_CHARACTERISTIC_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"
CMD_UP = 0x20; CMD_DOWN = 0x40; CMD_STOP = 0x00
HEADER = 0xA5; TERMINATOR = 0xFF
DEVICE_NAME_PATTERNS = ["^BLT_", "^MX"]  # Both use Classic protocol
DEFAULT_MIN_HEIGHT = 65; DEFAULT_MAX_HEIGHT = 130
```

## Known Limitations

- **No Cloud Features**: Beep, lock, factory reset require WiFi + cloud API
- **No Preset Support**: Memory presets not yet reverse engineered
- **BLE Range**: ~10m from Home Assistant host
- **WSL2/Podman**: Cannot access host Bluetooth (use ESPHome Bluetooth Proxy)

## Testing

```bash
uv run pytest tests/
uv run pytest --cov=custom_components/ergomate tests/
```
