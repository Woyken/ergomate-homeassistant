# AGENTS.md - AI Agent Context Guide

## Project Overview

**ergomate-homeassistant** is a Home Assistant custom integration for controlling Ergomate standing desks via Bluetooth Low Energy (BLE).

**Integration Type**: Local BLE (no cloud dependency)
**Home Assistant Compatibility**: 2023.6.0+
**Version**: 0.1.0

## Architecture

```
custom_components/ergomate/
├── __init__.py              # Integration setup, coordinator
├── config_flow.py           # BLE device discovery and selection
├── const.py                 # Domain constants
├── cover.py                 # Cover entity (desk control)
├── sensor.py                # Sensor entity (height)
├── desk_api.py              # BLE communication layer
├── desk_const.py            # BLE protocol constants
├── manifest.json            # Integration metadata
├── strings.json             # UI strings
└── translations/
    └── en.json              # English translations
```

## BLE Protocol

### Service & Characteristics

| UUID | Purpose |
|------|---------|
| `0000ff00-0000-1000-8000-00805f9b34fb` | Primary Service |
| `0000ff02-0000-1000-8000-00805f9b34fb` | Write Characteristic (commands) |
| `0000ff01-0000-1000-8000-00805f9b34fb` | Read Characteristic (notifications) |

### Command Packets

**Simple Commands (5 bytes)**:
```
[0xA5, 0x00, CMD, CHECKSUM, 0xFF]
```
- `CMD`: `0x20` (up), `0x40` (down), `0x00` (stop)
- `CHECKSUM`: `0xFF ^ CMD`

**Height Command (9 bytes)**:
```
[0xA6, 0xA8, 0x01, HIGH_BYTE, LOW_BYTE, 0x00, 0x00, XOR_CHECKSUM, 0xFF]
```
- Height in mm (650-1300)
- `XOR_CHECKSUM`: `0x01 ^ HIGH_BYTE ^ LOW_BYTE ^ 0x00 ^ 0x00`

### Height Notifications

Height updates arrive as 4-byte ASCII strings on the read characteristic:
- Example: `0x30 0x37 0x32 0x30` → "0720" → 720mm → 72.0cm

## Key Classes

### `ErgomateDesk` (`desk_api.py`)

Core BLE communication class using `bleak` library.

**Key Methods**:
- `connect()` - Establish BLE connection
- `disconnect()` - Close connection
- `move_up()` - Send up command
- `move_down()` - Send down command
- `stop()` - Send stop command
- `move_to_height(height_cm)` - Move to absolute height
- `register_callback(callback)` - Register height update callback

**Features**:
- Auto-reconnect on connection loss
- Background connection monitoring
- Multiple callback support

### `ErgoMateCover` (`cover.py`)

Home Assistant cover entity representing the desk.

**Position Mapping**:
- 0% = 65cm (min height)
- 100% = 130cm (max height)
- Formula: `position = (height - 65) / 65 * 100`

**Device Class**: `blind` (provides up/down/stop controls)

### `ErgoMateHeightSensor` (`sensor.py`)

Home Assistant sensor entity for height reporting.

**Properties**:
- Unit: cm
- Device Class: distance
- State Class: measurement

### Config Flow (`config_flow.py`)

BLE device discovery and selection.

**Flow**:
1. Scan for BLE devices with prefix "BLT_"
2. Display dropdown of discovered desks
3. User selects desk
4. Store MAC address in config entry

## Entity Details

### Cover Entity

| Property | Value |
|----------|-------|
| Entity ID | `cover.ergomate_desk` |
| Unique ID | `{MAC_ADDRESS}_cover` |
| Device Class | `blind` |
| Supported Features | Open, Close, Stop, Set Position |

### Sensor Entity

| Property | Value |
|----------|-------|
| Entity ID | `sensor.ergomate_desk_height` |
| Unique ID | `{MAC_ADDRESS}_height` |
| Device Class | `distance` |
| State Class | `measurement` |
| Unit | `cm` |

## Cloud-Only Features (NOT Implementable)

Based on reverse engineering of the Ergomate app, these features use GraphQL API and require WiFi connectivity:

| Feature | GraphQL Mutation |
|---------|-----------------|
| Beep | `SetMyDeskBeep($id, $milliseconds)` |
| Child Lock | `SetMyDeskLocked($id, $locked)` |
| Factory Reset | `SetMyDeskFactoryReset($id)` |

**Reason**: These commands are sent App → Cloud → Desk WiFi, not via BLE.

## Implementation Rules

### 1. Async Pattern

All BLE operations must be async:
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    desk = ErgomateDesk(entry.data[CONF_ADDRESS])
    await desk.connect()
```

### 2. Connection Management

Always clean up connections on unload:
```python
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    desk = hass.data[DOMAIN][entry.entry_id]["desk"]
    await desk.disconnect()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

### 3. Entity Updates

Use callback pattern for real-time updates:
```python
def height_callback(height_cm: float):
    hass.async_create_task(
        coordinator.async_set_updated_data({"height": height_cm})
    )

desk.register_callback(height_callback)
```

### 4. Device Info

Group entities under single device:
```python
@property
def device_info(self) -> dict[str, Any]:
    return {
        "identifiers": {(DOMAIN, self._address)},
        "name": "Ergomate Desk",
        "manufacturer": "Ergomate",
        "model": "Standing Desk",
    }
```

## Common Pitfalls

### Pitfall 1: Blocking BLE Calls

**Wrong**:
```python
async def async_open_cover(self):
    self.desk.move_up()  # Blocks!
```

**Right**:
```python
async def async_open_cover(self):
    await self.desk.move_up()
```

### Pitfall 2: Not Handling Disconnection

**Wrong**:
```python
await desk.move_up()  # May fail if disconnected
```

**Right**:
```python
if not desk.is_connected:
    await desk.connect()
await desk.move_up()
```

### Pitfall 3: Forgetting Write With Response

The desk requires write-with-response, not write-without-response:
```python
await client.write_gatt_char(WRITE_UUID, data, response=True)
```

## Development Workflow

### Version Increment

Use `uv` for version management:
```bash
uv version 0.1.1
```

This updates `pyproject.toml` automatically.

### Testing

```bash
uv run pytest tests/
```

### Release

```bash
gh release create v0.1.0 --title "v0.1.0" --notes "Initial release"
```

## File Checksums

When modifying files, ensure `manifest.json` version matches `hacs.json` and `pyproject.toml`.

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| bleak | >=0.21.0 | BLE communication |
| homeassistant | >=2023.6.0 | HA framework |

## Debugging

Enable debug logging:
```yaml
logger:
  default: info
  logs:
    custom_components.ergomate: debug
    bleak: debug
```

## Resources

- [Home Assistant BLE Integration Guide](https://developers.home-assistant.io/docs/creating_platform_code_review/#bluetooth)
- [Bleak Documentation](https://bleak.readthedocs.io/)
- [HACS Documentation](https://hacs.xyz/)

---

**Last Updated**: December 8, 2025
**Integration Version**: 0.1.0
**Status**: Initial release - cover and sensor entities
