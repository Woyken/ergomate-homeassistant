# Ergomate Standing Desk Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Control your Ergomate standing desk via Bluetooth Low Energy (BLE) from Home Assistant.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Woyken&repository=ergomate-homeassistant&category=integration)

## Features

- **Cover Entity**: Control desk height with up/down/stop commands
- **Height Sensor**: Real-time height monitoring in centimeters
- **Position Presets**: Set desk to any position between 0-100%
- **Auto-Reconnect**: Automatic reconnection on connection loss
- **Device Discovery**: Scan and select from nearby Ergomate desks

## Supported Desks

- Ergomate Classic (BLT_BLTDESK)
- Any Bluetooth-enabled Ergomate standing desk

## Requirements

- Home Assistant 2023.6.0 or newer
- Bluetooth adapter on your Home Assistant host
- Ergomate standing desk with BLE capability

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots menu → "Custom repositories"
4. Add this repository URL with category "Integration"
5. Search for "Ergomate" and install
6. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy `custom_components/ergomate` to your Home Assistant's `custom_components` folder
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Ergomate"
4. Select your desk from the discovered devices
5. Done!

## Entities

### Cover: `cover.ergomate_desk`

| Attribute | Description |
|-----------|-------------|
| State | `open` (above 50%), `closed` (at/below 50%) |
| Position | 0-100% (maps to 65-130cm) |

**Services:**
- `cover.open_cover` - Move desk up
- `cover.close_cover` - Move desk down
- `cover.stop_cover` - Stop movement
- `cover.set_cover_position` - Move to specific height

### Sensor: `sensor.ergomate_desk_height`

| Attribute | Description |
|-----------|-------------|
| State | Current height in cm |
| Unit | cm |
| Device Class | distance |

## BLE Protocol

This integration communicates directly with the desk via BLE:

- **Service UUID**: `0000ff00-0000-1000-8000-00805f9b34fb`
- **Write Characteristic**: `0000ff02-0000-1000-8000-00805f9b34fb`
- **Read Characteristic**: `0000ff01-0000-1000-8000-00805f9b34fb`

### Commands

| Command | Bytes |
|---------|-------|
| Move Up | `[0xA5, 0x00, 0x20, 0xDF, 0xFF]` |
| Move Down | `[0xA5, 0x00, 0x40, 0xBF, 0xFF]` |
| Stop | `[0xA5, 0x00, 0x00, 0xFF, 0xFF]` |
| Move to Height | `[0xA6, 0xA8, 0x01, HB, LB, 0x00, 0x00, XOR, 0xFF]` |

## Limitations

The following features are **cloud-only** in the Ergomate app and cannot be implemented via BLE:

- Beep command
- Child lock
- Factory reset
- Standing reminders
- Usage statistics

These require the desk to be WiFi-connected to Ergomate's cloud servers.

## Troubleshooting

### Desk not discovered

1. Ensure your desk is powered on
2. Check that Bluetooth is enabled on your HA host
3. Make sure the desk isn't connected to another device

### Connection drops frequently

Consider using an [ESPHome Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy.html) for more reliable BLE connections.

### Running in Docker/VM

If running Home Assistant in Docker or a VM, ensure the Bluetooth adapter is properly passed through. Alternatively, use an ESPHome Bluetooth Proxy.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial integration. Ergomate is a trademark of its respective owner. This project is not affiliated with, endorsed by, or connected to Ergomate.
