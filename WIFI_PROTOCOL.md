# ErgoMate WiFi Desk Protocol

> **Source:** Reverse-engineered from ErgoMate Android app v1.4.3 (React Native + Hermes bytecode)
> **Status:** Partially documented - contributions welcome

This document describes the protocol used by ErgoMate WiFi-enabled standing desks (H76 series). These desks use a different BLE protocol and also connect to ErgoMate cloud servers for advanced features.

---

## Table of Contents

1. [Overview](#overview)
2. [BLE Services & Characteristics](#ble-services--characteristics)
3. [Device Discovery](#device-discovery)
4. [BLE Transport Layer](#ble-transport-layer)
5. [WiFi Configuration](#wifi-configuration)
6. [Cloud Synchronization](#cloud-synchronization)
7. [Cloud-Only Features](#cloud-only-features)
8. [Desk Type Variants](#desk-type-variants)
9. [Known Limitations](#known-limitations)

---

## Overview

WiFi desk variants (H76 series) differ from Classic BLE desks in several ways:

| Feature | Classic (BLT_) | WiFi (H76_) |
|---------|----------------|-------------|
| BLE Protocol | Binary packets | JSON over Base64 |
| Cloud Connection | None | Persistent WebSocket |
| Activity Tracking | ❌ No | ✅ Yes |
| Remote Control | ❌ No | ✅ Yes (via cloud) |
| LED Control | ❌ No | ✅ Yes |
| Min/Max Height Config | ❌ No | ✅ Yes |

---

## BLE Services & Characteristics

### WiFi Desk (H76 Series)

**Models:** H76_WIFIDESK (1-9), H76_TIMDESK, H76_RAMONDESK

| Type | UUID |
|------|------|
| **Service** | `0000a00a-0000-1000-8000-00805f9b34fb` |
| **Write Characteristic** | `0000b003-0000-1000-8000-00805f9b34fb` |
| **Read Characteristic** | `0000b002-0000-1000-8000-00805f9b34fb` |

---

## Device Discovery

| Property | Value |
|----------|-------|
| Name Pattern | Starts with `H76_` |
| Service Filter | `0000a00a-*` |
| Examples | `H76_WIFIDESK`, `H76_TIMDESK`, `H76_RAMONDESK` |

---

## BLE Transport Layer

Commands are sent as **JSON payloads encoded in Base64**:

```javascript
// Conceptual structure (exact fields not fully documented)
const payload = {
    cmd: "move" | "stop" | "position",
    direction?: "up" | "down",
    height?: number
};

// Encode and send
const json = JSON.stringify(payload);
const buffer = Buffer.from(json);
const base64 = buffer.toString("base64");

await writeCharacteristic(base64);
```

### Response Handling

```javascript
// Receive base64 response
const base64 = await readCharacteristic();

// Decode
const buffer = Buffer.from(base64, "base64");
const json = buffer.toString("utf-8");
const data = JSON.parse(json);
```

> ⚠️ **Status:** The exact JSON schema for WiFi desk BLE commands is **not fully reverse-engineered**. If you have a WiFi desk, BLE packet captures would help complete this documentation.

---

## WiFi Configuration

### Sending WiFi Credentials

WiFi credentials are sent to the desk during initial setup via BLE:

```javascript
// WiFi configuration object
const wifiConfig = {
    ssid: "network_name",
    password: "network_password"
};
```

### Static IP Configuration (Optional)

The app supports static IP configuration with these fields:

| Field | Description |
|-------|-------------|
| `ipAddress` | Static IP address |
| `gateway` | Network gateway |
| `subnetMask` | Subnet mask |
| `primaryDns` | Primary DNS server |

### WiFi Connection Response

The desk responds with a simple string indicating success or failure:

| Response | Meaning |
|----------|---------|
| `wifi_connect:true` | Successfully connected to WiFi |
| `wifi_connect:false` | Failed to connect to WiFi |

### Post-Connection Behavior

After successful WiFi connection:
1. Desk automatically reboots
2. Connects to ErgoMate cloud servers
3. BLE remains available for local control

> ⚠️ **Important:** Stay within 5 meters during WiFi setup to maintain BLE connection.

---

## Cloud Synchronization

WiFi desks maintain a persistent connection to ErgoMate servers via WebSocket.

### Live Status Subscription

The app uses a GraphQL subscription for real-time desk status:

```graphql
subscription LiveDeskStatus($id: String!) {
    liveDeskStatus(id: $id) {
        id
        uniqueId
        currentHeight
        minHeight
        maxHeight
        networkConnected
        lastErrorCode
        lastErrorDetectedAt
    }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `currentHeight` | Int | Current desk height in cm |
| `minHeight` | Int | Configured minimum height |
| `maxHeight` | Int | Configured maximum height |
| `networkConnected` | Boolean | WiFi connection status |
| `lastErrorCode` | String | Last hardware error code (E01-E91) |
| `lastErrorDetectedAt` | DateTime | When error occurred |

### Update WiFi Credentials Remotely

```graphql
mutation OverwriteMyDeskWiFiCredentials(
    $id: String!,
    $ssid: String!,
    $password: String!
) {
    overwriteMyDeskWiFiCredentials(
        id: $id,
        ssid: $ssid,
        password: $password
    )
}
```

---

## Cloud-Only Features

These features require cloud connectivity and are NOT available via BLE:

### Beep

```graphql
mutation SetMyDeskBeep($id: String!, $milliseconds: Int!) {
    setMyDeskBeep(id: $id, milliseconds: $milliseconds)
}
```

### Child Lock

```graphql
mutation SetMyDeskLocked($id: String!, $locked: Boolean!) {
    setMyDeskLocked(id: $id, locked: $locked)
}
```

### Factory Reset

```graphql
mutation SetMyDeskFactoryReset($id: String!) {
    setMyDeskFactoryReset(id: $id)
}
```

### LED Control

LED on connection can be enabled during desk registration:

```graphql
mutation LinkDeskToMyAccount(
    $input: DeskLinkInput!
    $enableLedOnConnection: Boolean
    $triggerProximityChange: Boolean
    $linkUserToDesk: Boolean
) {
    linkDeskToMyAccount(
        input: $input
        enableLedOnConnection: $enableLedOnConnection
        triggerProximityChange: $triggerProximityChange
        linkUserToDesk: $linkUserToDesk
    ) {
        ...DeskFragment
    }
}
```

> **Note:** The `input` parameter uses `DeskLinkInput` type containing `uniqueId` and `deskType`.

#### Available LED Colors

| Color | Name |
|-------|------|
| Red | Red |
| Blue | Blue |
| Green | Green |
| Purple | Purple |
| Yellow | Yellow |
| White | White |
| Orange | Orange |
| Magenta | Magenta |
| Cyan | Cyan |

### Desktop Configuration

| Feature | GraphQL Field | Description |
|---------|---------------|-------------|
| Min Height | `minHeight` | Minimum allowed height (default: 65cm) |
| Max Height | `maxHeight` | Maximum allowed height (default: 165cm) |
| Surface Thickness | `surfaceThickness` | Desktop thickness in mm |

---

## Desk Type Variants

### WiFi-Enabled Models

The following 12 desk variants are defined in the app code:

| Internal Name | Display Name |
|---------------|-------------|
| `H76_WIFIDESK` | WiFi Desk (Standard) |
| `H76_WIFIDESK_2` | WiFi Desk 2 |
| `H76_WIFIDESK_3` | WiFi Desk 3 |
| `H76_WIFIDESK_4` | WiFi Desk 4 |
| `H76_WIFIDESK_5` | WiFi Desk 5 |
| `H76_WIFIDESK_6` | WiFi Desk 6 |
| `H76_WIFIDESK_7` | WiFi Desk 7 |
| `H76_WIFIDESK_8` | WiFi Desk 8 |
| `H76_WIFIDESK_9` | WiFi Desk 9 |
| `H76_TIMDESK` | Tim Desk (Custom variant) |
| `H76_RAMONDESK` | Ramon Desk (Custom variant) |

> **Note:** The naming uses underscores (e.g., `H76_WIFIDESK_2`) not concatenated (e.g., `H76_WIFIDESK2`).

### Frame Types

The app supports multiple desk frame configurations:

| Type | Description |
|------|-------------|
| Dual motor desk | Standard 2-leg desk |
| Dual motor DUO desk | 2-leg DUO variant |
| Triple motor 90° desk | 3-leg, 90° configuration |
| Triple motor 120° desk | 3-leg, 120° configuration |
| Triple motor 180° desk | 3-leg, 180° configuration |

> **Note:** Frame type affects motor error codes (E11-E18 for Motor 1, E21-E28 for Motor 2, E31-E38 for Motor 3 on triple motor desks).

---

## Known Limitations

### Activity Tracking

Activity tracking (standing time, calories) is **only available for WiFi desks**:

> "It looks like you're using a Bluetooth desk. Activity tracking is only available for WiFi desks."

### BLE Protocol Documentation

The WiFi desk BLE protocol is not fully documented. Known gaps:

- Exact JSON command schema for motor control
- Height notification format over BLE
- Complete list of BLE response types

### Cloud Dependency

Most advanced features require:
1. Desk connected to WiFi
2. Persistent internet connection
3. ErgoMate account authentication
4. Cloud server availability

---

## Contributing

If you have a WiFi desk and can capture BLE packets, please contribute:

1. Use a BLE sniffer (e.g., nRF Connect, Wireshark with BLE adapter)
2. Capture command/response pairs during desk operations
3. Document the JSON structure
4. Submit findings via GitHub issue or PR

---

## Related Documentation

- [BLE_PROTOCOL.md](BLE_PROTOCOL.md) - Classic desk BLE protocol (fully documented)
- [REVERSE_ENGINEERING_GUIDE.md](REVERSE_ENGINEERING_GUIDE.md) - How to decompile the ErgoMate app
