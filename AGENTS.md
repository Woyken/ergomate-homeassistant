# AGENTS.md - AI Agent Context Guide

## Project Overview

**ergomate-homeassistant** is a Home Assistant custom integration for controlling Ergomate standing desks via Bluetooth Low Energy (BLE).

| Property | Value |
|----------|-------|
| Integration Type | Local BLE (no cloud dependency) |
| Home Assistant Compatibility | 2023.6.0+ |
| IoT Class | `local_push` |
| Version | 1.0.0 |
| HACS Compatible | Yes |
| BLE Library | `bleak>=0.19.0` |

## Architecture

```
ergomate-homeassistant/
├── custom_components/ergomate/
│   ├── __init__.py          # Integration entry point, platform setup
│   ├── config_flow.py       # BLE device discovery UI with dropdown
│   ├── const.py             # HA domain constants (DOMAIN, CONF_*)
│   ├── cover.py             # CoverEntity (desk control: up/down/stop/position)
│   ├── sensor.py            # SensorEntity (height in cm)
│   ├── desk_api.py          # Core BLE communication (ErgomateDesk class)
│   ├── desk_const.py        # BLE protocol constants (UUIDs, commands)
│   ├── manifest.json        # HA integration manifest
│   ├── strings.json         # Config flow UI strings
│   └── translations/
│       └── en.json          # English translations
├── AGENTS.md                # This file - AI context guide
├── README.md                # User documentation
├── hacs.json                # HACS configuration
├── pyproject.toml           # Python project config (uv compatible)
├── LICENSE                  # MIT License
└── .gitignore               # Git ignore patterns
```

## BLE Protocol

### Device Discovery

Ergomate Classic desks advertise with:
- **Name Prefix**: `BLT_` (e.g., `BLT_BLTDESK`)
- **Service UUID**: `0000ff00-0000-1000-8000-00805f9b34fb`

### Service & Characteristics

| UUID | Type | Purpose |
|------|------|---------|
| `0000ff00-0000-1000-8000-00805f9b34fb` | Service | Primary BLE service |
| `0000ff02-0000-1000-8000-00805f9b34fb` | Write (with response) | Send commands to desk |
| `0000ff01-0000-1000-8000-00805f9b34fb` | Notify | Receive height updates |

**Important**: Commands MUST use write-with-response (`response=True`), not write-without-response.

### Command Packet Formats

**Motor Commands (5 bytes)**:
```
[HEADER, RESERVED, CMD, CHECKSUM, TERMINATOR]
[0xA5,   0x00,     CMD, 0xFF^CMD, 0xFF      ]
```

| Command | CMD Byte | Full Packet |
|---------|----------|-------------|
| Move Up | `0x20` | `[0xA5, 0x00, 0x20, 0xDF, 0xFF]` |
| Move Down | `0x40` | `[0xA5, 0x00, 0x40, 0xBF, 0xFF]` |
| Stop | `0x00` | `[0xA5, 0x00, 0x00, 0xFF, 0xFF]` |

**Height Command (9 bytes)**:
```
[0xA6, 0xA8, 0x01, HB, LB, 0x00, 0x00, XOR, 0xFF]
```
- `HB`: High byte of height in mm
- `LB`: Low byte of height in mm
- `XOR`: `0x01 ^ HB ^ LB ^ 0x00 ^ 0x00`
- Height range: 650-1300mm (clamped by firmware)

Example: Move to 100cm (1000mm = 0x03E8):
```
[0xA6, 0xA8, 0x01, 0x03, 0xE8, 0x00, 0x00, 0xEA, 0xFF]
```

### Height Notifications

Height updates arrive as 4-byte ASCII strings:
- Format: 4 ASCII digits representing mm
- Example: `0x30 0x37 0x32 0x30` → "0720" → 720mm → 72.0cm

## Key Classes

### `ErgomateDesk` (`desk_api.py`)

Core BLE communication class using `bleak` library. Handles connection management, command sending, and height parsing.

**Constructor**:
```python
ErgomateDesk(address: str, height_offset: float = 0.0)
```
- `address`: BLE MAC address (e.g., "AA:BB:CC:DD:EE:FF")
- `height_offset`: Calibration offset in cm (default: 0.0)

**Properties**:
| Property | Type | Description |
|----------|------|-------------|
| `is_connected` | `bool` | Current connection state |
| `is_moving` | `bool` | Whether desk is in motion |
| `current_height` | `float \| None` | Current height in cm (with offset) |
| `raw_height` | `float \| None` | Raw height without offset |

**Public Methods**:
| Method | Signature | Description |
|--------|-----------|-------------|
| `connect()` | `async` | Connect and start auto-reconnect |
| `disconnect()` | `async` | Stop desk and disconnect |
| `move_up()` | `async` | Move desk up continuously |
| `move_down()` | `async` | Move desk down continuously |
| `stop()` | `async` | Stop desk movement |
| `move_to_height(height_cm)` | `async` | Move to absolute height (65-130cm) |
| `move_up_for(duration)` | `async` | Move up for N seconds |
| `move_down_for(duration)` | `async` | Move down for N seconds |
| `register_callback(fn)` | `sync` | Add notification callback |
| `unregister_callback(fn)` | `sync` | Remove notification callback |
| `subscribe_notifications()` | `async` | Enable height notifications |
| `unsubscribe_notifications()` | `async` | Disable height notifications |

**Not Implemented Methods** (Cloud-Only Features):
| Method | Reason |
|--------|--------|
| `beep(duration_ms)` | GraphQL API only |
| `lock()` | GraphQL API only |
| `unlock()` | GraphQL API only |
| `factory_reset()` | GraphQL API only |

**Features**:
- Auto-reconnect: Background task monitors connection and reconnects
- Multi-callback: Multiple entities can register for height updates
- Async context manager: `async with ErgomateDesk(...) as desk:`

**Helper Functions**:
```python
async def discover_desks(timeout: float = 10.0) -> list[BLEDevice]
async def discover_desk_by_address(address: str, timeout: float = 10.0) -> BLEDevice | None
```

### `ErgomateDeskCover` (`cover.py`)

Home Assistant CoverEntity representing the desk.

**Entity Attributes**:
| Attribute | Value |
|-----------|-------|
| `_attr_device_class` | `CoverDeviceClass.DAMPER` |
| `_attr_supported_features` | `OPEN \| CLOSE \| STOP \| SET_POSITION` |
| `_attr_has_entity_name` | `True` |
| `_attr_name` | `None` (uses device name) |

**Position Mapping**:
```
Position 0%   = 65cm  (DEFAULT_MIN_HEIGHT)
Position 100% = 130cm (DEFAULT_MAX_HEIGHT)

position = ((height - min) / (max - min)) * 100
height = min + (position / 100) * (max - min)
```

**Lifecycle**:
- `async_added_to_hass()`: Connect to desk, subscribe notifications
- `async_will_remove_from_hass()`: Unregister callback, disconnect

### `ErgomateHeightSensor` (`sensor.py`)

Home Assistant SensorEntity for height reporting.

**Entity Attributes**:
| Attribute | Value |
|-----------|-------|
| `_attr_device_class` | `SensorDeviceClass.DISTANCE` |
| `_attr_native_unit_of_measurement` | `UnitOfLength.CENTIMETERS` |
| `_attr_state_class` | `SensorStateClass.MEASUREMENT` |
| `_attr_name` | `"Height"` |

### `ConfigFlow` (`config_flow.py`)

BLE device discovery and selection UI.

**Steps**:
1. `async_step_user`: Manual setup with dropdown
2. `async_step_bluetooth`: Auto-discovery when device found

**Device Detection**:
- Matches devices where:
  - Service UUID `0000ff00-...` is advertised, OR
  - Device name starts with `BLT_`

**Configuration Options**:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `address` | `str` | Required | BLE MAC address |
| `name` | `str` | "Ergomate Desk" | Display name |
| `height_offset` | `float` | 0.0 | Height calibration offset (cm) |

## Entity Details

### Cover Entity

| Property | Value |
|----------|-------|
| Entity ID | `cover.{device_name}` |
| Unique ID | `{entry_id}_cover` |
| Device Class | `damper` |
| Supported Features | Open, Close, Stop, Set Position |

**Actions**:
| Action | Method | Description |
|--------|--------|-------------|
| Open | `async_open_cover()` | Calls `desk.move_up()` |
| Close | `async_close_cover()` | Calls `desk.move_down()` |
| Stop | `async_stop_cover()` | Calls `desk.stop()` |
| Set Position | `async_set_cover_position(position)` | Calls `desk.move_to_height(cm)` |

### Sensor Entity

| Property | Value |
|----------|-------|
| Entity ID | `sensor.{device_name}_height` |
| Unique ID | `{entry_id}_height` |
| Device Class | `distance` |
| State Class | `measurement` |
| Unit | `cm` |

### Device Info

Both entities share a device:
```python
DeviceInfo(
    identifiers={(DOMAIN, entry.entry_id)},
    name=entry.title,
    manufacturer="Ergomate",
    model="Classic",
)
```

## Cloud-Only Features (NOT Implementable via BLE)

Based on reverse engineering of the decompiled Ergomate React Native app, these features are implemented via GraphQL API to the Ergomate cloud server. They require:
1. Desk connected to WiFi
2. App authenticated with Ergomate account
3. Cloud server to relay commands

| Feature | GraphQL Mutation | Internal Constant |
|---------|-----------------|-------------------|
| Beep | `SetMyDeskBeep($id: String!, $milliseconds: Int!)` | - |
| Child Lock | `SetMyDeskLocked($id: String!, $locked: Boolean!)` | `CHILDLOCK` |
| Factory Reset | `SetMyDeskFactoryReset($id: String!)` | `FACTORYRESET` |

**Why Not BLE**: Commands flow App → Cloud → Desk (WiFi), bypassing BLE entirely.

**Implementation Status**: Methods exist in `desk_api.py` but raise `NotImplementedError` with explanation.

## Implementation Rules

### 1. Async Pattern

All BLE operations must be async:
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    desk = ErgomateDesk(
        address=entry.data[CONF_ADDRESS],
        height_offset=entry.data.get(CONF_HEIGHT_OFFSET, 0.0)
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = desk
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
```

### 2. Connection Management

Always clean up connections on unload:
```python
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    desk: ErgomateDesk = hass.data[DOMAIN][entry.entry_id]
    await desk.disconnect()
    hass.data[DOMAIN].pop(entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

### 3. Entity Updates via Callbacks

Use callback pattern for real-time updates:
```python
async def async_added_to_hass(self) -> None:
    """Subscribe to desk notifications."""
    self._desk.register_callback(self._notification_callback)

async def async_will_remove_from_hass(self) -> None:
    """Unsubscribe from desk notifications."""
    self._desk.unregister_callback(self._notification_callback)

def _notification_callback(self, sender: int, data: bytearray) -> None:
    """Handle height updates - trigger HA state update."""
    self.async_write_ha_state()
```

### 4. Device Info Grouping

Group entities under single device using consistent identifiers:
```python
@property
def device_info(self) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, self._entry.entry_id)},
        name=self._entry.title,
        manufacturer="Ergomate",
        model="Classic",
    )
```

### 5. Write With Response

The desk firmware requires write-with-response:
```python
await self._client.write_gatt_char(
    WRITE_CHARACTERISTIC_UUID,
    command,
    response=True  # CRITICAL: Must be True!
)
```

## Common Pitfalls

### Pitfall 1: Blocking BLE Calls

**Wrong**:
```python
async def async_open_cover(self):
    self.desk.move_up()  # Missing await - blocks event loop!
```

**Right**:
```python
async def async_open_cover(self):
    await self._desk.move_up()
```

### Pitfall 2: Not Handling Disconnection

The `ErgomateDesk` class handles this internally with auto-reconnect, but manual reconnection is also available:

```python
# Auto-handled by _send_command:
if not self.is_connected:
    await self.connect()
    if self._callbacks:
        await self.subscribe_notifications()
```

### Pitfall 3: Forgetting Write With Response

The desk **requires** write-with-response, not write-without-response:
```python
# WRONG:
await client.write_gatt_char(WRITE_UUID, data)  # response defaults to False!

# RIGHT:
await client.write_gatt_char(WRITE_UUID, data, response=True)
```

### Pitfall 4: Wrong Checksum Calculation

**Motor Commands**: Checksum = `0xFF ^ CMD`
```python
checksum = 0xFF ^ cmd_byte  # NOT XOR of all bytes
```

**Height Commands**: Checksum = XOR of payload bytes
```python
checksum = 0x01 ^ high_byte ^ low_byte ^ 0x00 ^ 0x00
```

### Pitfall 5: Position vs Height Confusion

- **Position**: 0-100% (Home Assistant cover)
- **Height**: 65-130cm (physical desk)
- **Protocol**: 650-1300mm (BLE commands)

Always convert appropriately:
```python
height_mm = int(height_cm * 10)  # cm → mm for protocol
height_cm = height_mm / 10.0     # mm → cm from notifications
```

## Development Workflow

### Version Management

Use `uv` tool for version incrementation:
```bash
# Bump patch version (0.1.0 → 0.1.1)
uv version --bump patch

# Bump minor version (0.1.0 → 0.2.0)
uv version --bump minor

# Set specific version
uv version 1.0.0
```

**Important**: Keep versions synchronized across:
- `pyproject.toml` (project.version)
- `custom_components/ergomate/manifest.json` (version)
- `hacs.json` (if version specified)

### Testing

```bash
# Run tests
uv run pytest tests/

# With coverage
uv run pytest --cov=custom_components/ergomate tests/
```

### GitHub Release

```bash
# Create release
gh release create v1.0.0 --title "v1.0.0" --notes "Release notes here"

# Or generate notes automatically
gh release create v1.0.0 --generate-notes
```

### HACS Validation

The repository includes `hacs.json`:
```json
{
  "name": "Ergomate Standing Desk",
  "render_readme": true
}
```

## File Constants Reference

### `const.py`
```python
DOMAIN = "ergomate"
CONF_ADDRESS = "address"
CONF_HEIGHT_OFFSET = "height_offset"
DEFAULT_NAME = "Ergomate Desk"
```

### `desk_const.py`
```python
SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb"
WRITE_CHARACTERISTIC_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"
READ_CHARACTERISTIC_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"

CMD_UP = 0x20
CMD_DOWN = 0x40
CMD_STOP = 0x00

HEADER = 0xA5
RESERVED = 0x00
TERMINATOR = 0xFF

DEVICE_NAME_PREFIX_CLASSIC = "BLT_"
DEFAULT_MIN_HEIGHT = 65
DEFAULT_MAX_HEIGHT = 130
DEFAULT_SCAN_TIMEOUT = 10.0
```

### `manifest.json`
```json
{
  "domain": "ergomate",
  "name": "Ergomate Standing Desk",
  "config_flow": true,
  "dependencies": ["bluetooth"],
  "iot_class": "local_push",
  "requirements": ["bleak>=0.19.0"],
  "version": "1.0.0"
}
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| bleak | >=0.19.0 | BLE communication library |
| homeassistant | >=2023.6.0 | Home Assistant framework |

## Platforms

| Platform | Entity Class | Purpose |
|----------|--------------|---------|
| `cover` | `ErgomateDeskCover` | Desk control (up/down/stop/position) |
| `sensor` | `ErgomateHeightSensor` | Height reporting in cm |

## Debugging

Enable debug logging in Home Assistant `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.ergomate: debug
    custom_components.ergomate.desk_api: debug
    bleak: debug
```

**Key Log Messages**:
- `"Connecting to desk at %s"` - Connection attempt
- `"Connected to desk at %s"` - Successful connection
- `"Disconnected from desk at %s"` - Connection lost
- `"Connection lost, attempting to reconnect..."` - Auto-reconnect triggered
- `"Sending command 0x%02X to desk: %s"` - Command being sent
- `"Moving to height %.1f cm (cmd: %s)"` - Height command
- `"Received notification from %s: %s"` - Height update received
- `"Height: %.1f cm (raw: %.1f cm)"` - Parsed height

## Known Limitations

1. **No Cloud Features**: Beep, lock, factory reset require cloud API
2. **Single Desk Per Entry**: Each config entry is one desk
3. **No Preset Support**: Memory presets not yet reverse engineered
4. **BLE Range**: Limited to ~10m from Home Assistant host
5. **WSL2/Podman**: Cannot access host Bluetooth (use ESPHome Bluetooth Proxy)

## Future Enhancements

If capturing additional BLE packets:
1. Memory preset commands (set/recall positions)
2. Anti-collision settings
3. Movement speed configuration

To capture:
1. Use Android HCI Snoop Log or nRF Connect
2. Trigger feature in Ergomate app
3. Find write to `0000ff02` characteristic
4. Update `desk_const.py` with new command bytes

## Resources

- [Home Assistant BLE Integration Guide](https://developers.home-assistant.io/docs/creating_platform_code_review/#bluetooth)
- [Bleak Documentation](https://bleak.readthedocs.io/)
- [HACS Documentation](https://hacs.xyz/)
- [ESPHome Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy.html)

---

**Last Updated**: 2025-06-10
**Integration Version**: 1.0.0
**Status**: Production ready - cover and sensor entities with auto-reconnect
