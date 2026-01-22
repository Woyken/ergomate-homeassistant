"""Test script to validate ErgoMate BLE library."""

import asyncio
import sys
from pathlib import Path

# Add custom_components to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components"))

from ergomate import ErgomateDesk, discover_desks
from ergomate.const import SERVICE_UUID, WRITE_CHARACTERISTIC_UUID, CMD_UP, CMD_DOWN, CMD_STOP
from ergomate.desk import _create_command, _create_height_command


def test_height_command_creation():
    """Test that height command packets are created correctly."""
    print("Testing height command creation...")

    # Test 80cm (800mm)
    # 800 = 0x0320
    # HB = 0x03, LB = 0x20
    # Checksum = 0x01 ^ 0x03 ^ 0x20 ^ 0x00 ^ 0x00
    #          = 1 ^ 3 ^ 32
    #          = 2 ^ 32
    #          = 34 (0x22)
    # Packet: [A6, A8, 01, 03, 20, 00, 00, 22, FF]

    cmd_80cm = _create_height_command(800)
    expected_80cm = bytes([0xA6, 0xA8, 0x01, 0x03, 0x20, 0x00, 0x00, 0x22, 0xFF])

    assert cmd_80cm == expected_80cm, f"80cm command mismatch: {cmd_80cm.hex()} != {expected_80cm.hex()}"
    print(f"  80cm command: {cmd_80cm.hex()} ✓")

    # Test Clamping (Min 650mm)
    # Input 500mm -> Should be 650mm (0x028A)
    # HB = 0x02, LB = 0x8A
    # Checksum = 0x01 ^ 0x02 ^ 0x8A ^ 0x00 ^ 0x00
    #          = 1 ^ 2 ^ 138
    #          = 3 ^ 138
    #          = 137 (0x89)
    # Packet: [A6, A8, 01, 02, 8A, 00, 00, 89, FF]

    cmd_min = _create_height_command(500)
    expected_min = bytes([0xA6, 0xA8, 0x01, 0x02, 0x8A, 0x00, 0x00, 0x89, 0xFF])

    assert cmd_min == expected_min, f"Min clamp command mismatch: {cmd_min.hex()} != {expected_min.hex()}"
    print(f"  Min clamp (50cm->65cm): {cmd_min.hex()} ✓")

    # Test Clamping (Max 1300mm)
    # Input 1500mm -> Should be 1300mm (0x0514)
    # HB = 0x05, LB = 0x14
    # Checksum = 0x01 ^ 0x05 ^ 0x14 ^ 0x00 ^ 0x00
    #          = 1 ^ 5 ^ 20
    #          = 4 ^ 20
    #          = 16 (0x10)
    # Packet: [A6, A8, 01, 05, 14, 00, 00, 10, FF]

    cmd_max = _create_height_command(1500)
    expected_max = bytes([0xA6, 0xA8, 0x01, 0x05, 0x14, 0x00, 0x00, 0x10, 0xFF])

    assert cmd_max == expected_max, f"Max clamp command mismatch: {cmd_max.hex()} != {expected_max.hex()}"
    print(f"  Max clamp (150cm->130cm): {cmd_max.hex()} ✓")

    print("Height command creation tests PASSED!\n")



def test_command_creation():
    """Test that command packets are created correctly."""
    print("Testing command creation...")

    # Test UP command: [0xA5, 0x00, 0x20, 0xDF, 0xFF]
    up_cmd = _create_command(CMD_UP)
    expected_up = bytes([0xA5, 0x00, 0x20, 0xDF, 0xFF])
    assert up_cmd == expected_up, f"UP command mismatch: {up_cmd.hex()} != {expected_up.hex()}"
    print(f"  UP command: {up_cmd.hex()} ✓")

    # Test DOWN command: [0xA5, 0x00, 0x40, 0xBF, 0xFF]
    down_cmd = _create_command(CMD_DOWN)
    expected_down = bytes([0xA5, 0x00, 0x40, 0xBF, 0xFF])
    assert down_cmd == expected_down, f"DOWN command mismatch: {down_cmd.hex()} != {expected_down.hex()}"
    print(f"  DOWN command: {down_cmd.hex()} ✓")

    # Test STOP command: [0xA5, 0x00, 0x00, 0xFF, 0xFF]
    stop_cmd = _create_command(CMD_STOP)
    expected_stop = bytes([0xA5, 0x00, 0x00, 0xFF, 0xFF])
    assert stop_cmd == expected_stop, f"STOP command mismatch: {stop_cmd.hex()} != {expected_stop.hex()}"
    print(f"  STOP command: {stop_cmd.hex()} ✓")

    print("Command creation tests PASSED!\n")


def test_checksum_calculation():
    """Test XOR checksum calculation."""
    print("Testing checksum calculation...")

    # Checksum = 0xFF ^ cmd
    # UP:   0xFF ^ 0x20 = 0xDF (223)
    # DOWN: 0xFF ^ 0x40 = 0xBF (191)
    # STOP: 0xFF ^ 0x00 = 0xFF (255)

    assert 0xFF ^ 0x20 == 0xDF, "UP checksum incorrect"
    print(f"  UP checksum: 0xFF ^ 0x20 = 0x{0xFF ^ 0x20:02X} ✓")

    assert 0xFF ^ 0x40 == 0xBF, "DOWN checksum incorrect"
    print(f"  DOWN checksum: 0xFF ^ 0x40 = 0x{0xFF ^ 0x40:02X} ✓")

    assert 0xFF ^ 0x00 == 0xFF, "STOP checksum incorrect"
    print(f"  STOP checksum: 0xFF ^ 0x00 = 0x{0xFF ^ 0x00:02X} ✓")

    print("Checksum tests PASSED!\n")


def test_desk_initialization():
    """Test ErgomateDesk class initialization."""
    print("Testing desk initialization...")

    test_address = "AA:BB:CC:DD:EE:FF"
    desk = ErgomateDesk(test_address)

    assert desk.address == test_address, "Address mismatch"
    print(f"  Address: {desk.address} ✓")

    assert desk.is_connected == False, "Should not be connected initially"
    print(f"  is_connected: {desk.is_connected} ✓")

    assert desk.current_height is None, "Height should be None initially"
    print(f"  current_height: {desk.current_height} ✓")

    assert desk.is_moving == False, "Should not be moving initially"
    print(f"  is_moving: {desk.is_moving} ✓")

    print("Desk initialization tests PASSED!\n")


def test_constants():
    """Test that constants are correct."""
    print("Testing constants...")

    assert SERVICE_UUID == "0000ff00-0000-1000-8000-00805f9b34fb"
    print(f"  SERVICE_UUID: {SERVICE_UUID} ✓")

    assert WRITE_CHARACTERISTIC_UUID == "0000ff02-0000-1000-8000-00805f9b34fb"
    print(f"  WRITE_UUID: {WRITE_CHARACTERISTIC_UUID} ✓")

    assert CMD_UP == 0x20
    print(f"  CMD_UP: 0x{CMD_UP:02X} ✓")

    assert CMD_DOWN == 0x40
    print(f"  CMD_DOWN: 0x{CMD_DOWN:02X} ✓")

    assert CMD_STOP == 0x00
    print(f"  CMD_STOP: 0x{CMD_STOP:02X} ✓")

    print("Constants tests PASSED!\n")


async def test_discovery_no_crash():
    """Test that discovery runs without crashing (may find 0 devices)."""
    print("Testing BLE discovery (5 second scan)...")
    print("  Note: This tests that the scan runs, not that devices are found")

    try:
        desks = await discover_desks(timeout=5.0)
        print(f"  Scan completed, found {len(desks)} desk(s) ✓")
        for desk in desks:
            print(f"    - {desk.name} ({desk.address})")
    except Exception as e:
        print(f"  Scan failed with error: {e}")
        raise

    print("Discovery test PASSED!\n")


def main():
    """Run all tests."""
    print("=" * 50)
    print("ErgoMate BLE Library Tests")
    print("=" * 50)
    print()

    # Run synchronous tests
    test_constants()
    test_checksum_calculation()
    test_command_creation()
    test_height_command_creation()
    test_desk_initialization()

    # Run async test
    asyncio.run(test_discovery_no_crash())

    print("=" * 50)
    print("All tests PASSED!")
    print("=" * 50)


if __name__ == "__main__":
    main()
