"""Constants for ErgoMate BLE protocol."""

# Classic Desk (BLT_BLTDESK) UUIDs
SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb"
WRITE_CHARACTERISTIC_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"
READ_CHARACTERISTIC_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"

# Additional characteristics discovered in app (purpose unknown)
# May be related to WiFi configuration or other features
CHAR_B002_UUID = "0000b002-0000-1000-8000-00805f9b34fb"  # Unknown - possibly config
CHAR_B003_UUID = "0000b003-0000-1000-8000-00805f9b34fb"  # Unknown - possibly status

# Command bytes for basic movement (5-byte packet with 0xA5 header)
CMD_UP = 0x20    # 32 - Move desk up
CMD_DOWN = 0x40  # 64 - Move desk down
CMD_STOP = 0x00  # 0  - Stop movement

# =============================================================================
# CLOUD-BASED FEATURES (NOT AVAILABLE VIA BLE)
# =============================================================================
# The following features are implemented via GraphQL API in the Ergomate app,
# NOT through BLE commands. They require:
#   1. Desk to be WiFi-connected to Ergomate cloud
#   2. App authenticated with Ergomate account
#   3. Cloud server to relay commands to desk
#
# GraphQL mutations identified:
#   - SetMyDeskBeep($id: String!, $milliseconds: Int!)
#   - SetMyDeskLocked($id: String!, $locked: Boolean!)  # Child lock
#   - SetMyDeskFactoryReset($id: String!)
#
# Internal constants used by desk firmware:
#   - "CHILDLOCK" - Child lock feature
#   - "FACTORYRESET" - Factory reset feature
#
# These CANNOT be implemented without reverse engineering the Ergomate cloud API.
# =============================================================================

# Protocol constants
HEADER = 0xA5      # 165 - Start marker
RESERVED = 0x00    # 0   - Always zero
TERMINATOR = 0xFF  # 255 - End marker

# Device name prefixes for discovery
DEVICE_NAME_PREFIX_CLASSIC = "BLT_"

# Default height range (cm) - typical values
DEFAULT_MIN_HEIGHT = 65
DEFAULT_MAX_HEIGHT = 130

# Connection settings
DEFAULT_SCAN_TIMEOUT = 10.0  # seconds
DEFAULT_DISCONNECT_TIMEOUT = 2.0  # seconds
