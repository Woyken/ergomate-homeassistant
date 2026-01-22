# ErgoMate App Reverse Engineering Guide

> **Latest Analyzed Version:** 1.4.3 (January 2026)
> **Previous Versions:** 1.3.9 (December 2025)
> **BLE Protocol Status:** Unchanged between versions

This guide explains how to extract and analyze the ErgoMate Android app to discover BLE protocol details, command formats, and other implementation specifics.

---

## Quick Start

For quick APK decompilation:

**Tools Required:**
- [apkeep](https://github.com/EFForg/apkeep) - Download APKs from Google Play
- [JADX](https://github.com/skylot/jadx) - Decompile APK to Java/resources
- [hermes-dec](https://github.com/AHinMaine/hermes-dec) - **Recommended** Hermes decompiler (produces readable JS)
- [hermes_rs](https://github.com/Pilfer/hermes_rs) - Alternative bytecode disassembler

**Download APK:**
```bash
# Install apkeep (requires Rust/Cargo)
cargo install apkeep

# Download ErgoMate APK
apkeep -a nl.gravity.ergomate .

# Extract XAPK (it's a ZIP containing multiple APKs)
unzip nl.gravity.ergomate.xapk -d nl.gravity.ergomate_extracted
```

**Decompile with JADX:**
```bash
jadx -d "jadx_sources" nl.gravity.ergomate_extracted/nl.gravity.ergomate.apk
```

**Decompile Hermes Bundle (Recommended - hermes-dec):**
```bash
# Install hermes-dec (Python)
pip install git+https://github.com/P1sec/hermes-dec

# Decompile to readable JavaScript-like output (~70MB)
hbc-decompiler "jadx_sources/resources/assets/index.android.bundle" hermes_dec_output.js
```

**Alternative - Disassemble with hermes_rs:**
```bash
# Clone hermes_rs
git clone https://github.com/Pilfer/hermes_rs
cd hermes_rs

# Dump bytecode and strings
cargo run --release --bin bytecode "jadx_sources/resources/assets/index.android.bundle" > bytecode_output.txt
cargo run --release --bin strings "jadx_sources/resources/assets/index.android.bundle" > strings_output.txt
```

See detailed steps below.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Obtain the APK](#step-1-obtain-the-apk)
4. [Step 2: Decompile with JADX](#step-2-decompile-with-jadx)
5. [Step 3: Extract Hermes Bytecode](#step-3-extract-hermes-bytecode)
6. [Step 4: Decompile Hermes Bundle](#step-4-decompile-hermes-bundle)
7. [Directory Structure](#directory-structure)
8. [Searching the Decompiled Output](#searching-the-decompiled-output)
9. [Key Files & Locations](#key-files--locations)
10. [Search Patterns](#search-patterns)
11. [Useful Tools](#useful-tools)

---

## Overview

The ErgoMate app is built with:

| Component | Technology |
|-----------|------------|
| Framework | React Native |
| JavaScript Engine | Hermes (compiled bytecode) |
| BLE Library | bleshadow (React Native BLE PLX wrapper) |
| API | GraphQL (for cloud features) |

The app bundles JavaScript as **Hermes bytecode** (`index.android.bundle`), not plain JavaScript. This requires specialized tools to decompile.

---

## Prerequisites

### Required Tools

| Tool | Purpose | Download |
|------|---------|----------|
| **apkeep** | Download APKs from Google Play | [github.com/EFForg/apkeep](https://github.com/EFForg/apkeep) |
| **JADX** | APK decompilation | [github.com/skylot/jadx](https://github.com/skylot/jadx/releases) |
| **hermes-dec** | Hermes bytecode decompiler (recommended) | `pip install git+https://github.com/P1sec/hermes-dec` |
| **hermes_rs** | Hermes bytecode disassembler (alternative) | [github.com/Pilfer/hermes_rs](https://github.com/Pilfer/hermes_rs) |
| **Rust/Cargo** | Building hermes_rs | [rustup.rs](https://rustup.rs) |


---

## Step 1: Obtain the APK

Use [apkeep](https://github.com/EFForg/apkeep) to download APKs directly from Google Play.

```bash
# Install apkeep (requires Rust/Cargo)
cargo install apkeep

# Download ErgoMate APK (package: nl.gravity.ergomate)
apkeep -a nl.gravity.ergomate .

# Extract XAPK (it's a ZIP file containing split APKs)
unzip nl.gravity.ergomate.xapk -d nl.gravity.ergomate_extracted

# The main APK is: nl.gravity.ergomate_extracted/nl.gravity.ergomate.apk
```

---

## Step 2: Decompile with JADX

Use [JADX](https://github.com/skylot/jadx) to extract and decompile the APK contents.

```bash
# Decompile to 'jadx_sources' directory
jadx -d "jadx_sources" nl.gravity.ergomate_extracted/nl.gravity.ergomate.apk
```

### Output Structure

```
jadx sources/
├── resources/
│   ├── AndroidManifest.xml      # App permissions & components
│   ├── assets/
│   │   ├── index.android.bundle # Hermes bytecode (main app logic)
│   │   ├── app.config           # Expo/React Native config
│   │   └── ...
│   ├── classes.dex              # Native Android code
│   ├── classes2.dex
│   └── res/                     # Resources (images, layouts)
└── sources/
    └── com/                     # Decompiled Java classes
```

---

## Step 3: Extract Hermes Bytecode

The main app logic is in `index.android.bundle` - a compiled Hermes bytecode file.

### Locate the Bundle

```
jadx sources/resources/assets/index.android.bundle
```

### Verify It's Hermes Format

```bash
# Check file header (should show "Hermes" or HBC magic bytes)
xxd -l 16 "jadx sources/resources/assets/index.android.bundle"
```

Expected output starts with Hermes magic: `c6 1f bc 03` or similar.

---

## Step 4: Decompile Hermes Bundle

### Recommended: hermes-dec (Python)

[hermes-dec](https://github.com/P1sec/hermes-dec) produces **readable JavaScript-like code** that's much easier to analyze than raw bytecode.

```bash
# Install hermes-dec
pip install git+https://github.com/P1sec/hermes-dec

# Decompile the bundle
hbc-decompiler "jadx_sources/resources/assets/index.android.bundle" hermes_dec_output.js
```

**Output quality:**
- Produces ~70MB of readable JavaScript-like pseudo code
- Preserves function names like `moveAbsolute`, `writeCharacteristicWithResponseForService`
- Shows clear data structures: `r5 = [165, 0, 32, 223, 255]` for UP command
- Much easier to search and understand than raw bytecode

### Alternative: hermes_rs (Rust)

Use [hermes_rs](https://github.com/Pilfer/hermes_rs) to disassemble Hermes bytecode to instructions with function names and string literals.

```bash
# Clone the repository
git clone https://github.com/Pilfer/hermes_rs
cd hermes_rs

# Dump bytecode (disassembled instructions)
cargo run --release --bin bytecode "jadx_sources/resources/assets/index.android.bundle" > bytecode_output.txt

# Dump strings (all string literals)
cargo run --release --bin strings "jadx_sources/resources/assets/index.android.bundle" > strings_output.txt
```

This produces:
- `bytecode_output.txt` - Disassembled bytecode with function names and instructions (~70MB)
- `strings_output.txt` - All string literals including UUIDs, messages, GraphQL queries (~20MB)

---

## Directory Structure

After complete decompilation:

```
ergomate-homeassistant/
├── nl.gravity.ergomate.xapk           # Downloaded XAPK
├── nl.gravity.ergomate_extracted/     # Extracted XAPK contents
│   └── nl.gravity.ergomate.apk        # Main APK
├── jadx_sources/
│   ├── resources/
│   │   ├── AndroidManifest.xml
│   │   ├── assets/
│   │   │   ├── index.android.bundle   # Original Hermes bytecode
│   │   │   └── app.config
│   │   ├── classes.dex
│   │   └── res/
│   └── sources/
│       └── nl/                        # Decompiled Java classes
├── hermes_dec_output.js               # **RECOMMENDED** Decompiled JS (~70MB)
├── bytecode_output.txt                # Alternative: Disassembled bytecode (~70MB)
├── strings_output.txt                 # String literals (~20MB)
└── hermes_rs/                         # Hermes disassembler (cloned)
```

---

## Searching the Decompiled Output

The decompiled output file is **very large** (~70MB, 1M+ lines). Use search tools:

### PowerShell Search (Recommended on Windows)

```powershell
# Search hermes_dec_output.js with context
Select-String -Path "hermes_dec_output.js" -Pattern "0000ff00" -Context 2,5

# Find BLE service definitions
Select-String -Path "hermes_dec_output.js" -Pattern "ServiceUUID|CharacteristicWrite" -Context 2,5

# Find command byte arrays
Select-String -Path "hermes_dec_output.js" -Pattern "165,\s*0,\s*32|165,\s*0,\s*64" -Context 3,10

# Read specific lines (e.g., around line 1188850)
Get-Content "hermes_dec_output.js" | Select-Object -Skip 1188849 -First 100
```

### Python Search Script

```python
# search_bundle.py
import re

file_path = "hermes_dec_output.js"  # or "bytecode_output.txt"

patterns = [
    r"165,\s*0,\s*32",      # UP command bytes
    r"165,\s*0,\s*64",      # DOWN command bytes
    r"0000ff00",            # Service UUID
    r"writeCharacteristic", # BLE write calls
    r"moveToHeight",        # Height function
]

with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

for pattern in patterns:
    print(f"\n--- Searching: {pattern} ---")
    for match in re.finditer(pattern, content):
        start = max(0, match.start() - 100)
        end = min(len(content), match.end() + 200)
        print(f"Line ~{content[:match.start()].count(chr(10))}:")
        print(content[start:end])
        print("-" * 40)
```

### Command Line Search

```bash
# Find BLE UUIDs
grep -n "0000ff00" bytecode_output.txt

# Find command byte arrays
grep -n "165, 0, 32" bytecode_output.txt

# Find GraphQL mutations
grep -n "mutation Set" bytecode_output.txt

# Find all string literals containing "desk"
grep -i "desk" strings_output.txt
```

### PowerShell Search

```powershell
# Search with context
Select-String -Path "bytecode_output.txt" -Pattern "0000ff00" -Context 2,5

# Find line numbers
Select-String -Path "bytecode_output.txt" -Pattern "165, 0, 32" |
    ForEach-Object { $_.LineNumber }
```

---

## Key Files & Locations

### In hermes_dec_output.js (Recommended)

| Content | Search Pattern | Typical Line Range (v1.4.3) |
|---------|----------------|----------------------------|
| BLE Service Config | `ServiceUUID.*CharacteristicWrite` | ~1,187,433 |
| UP/DOWN/STOP Commands | `165, 0, 32`, `165, 0, 64`, `165, 0, 0` | ~1,188,852 |
| Height Command | `166, 168, 1` | ~1,189,006 |
| Height Limits | `650`, `1300` | ~1,189,014-1,189,016 |
| Desk Types | `BLT_BLTDESK`, `H76_WIFIDESK` | ~1,189,754 |
| HandsetVariant | `Classic`, `Wifi` | ~463,366 |
| BLE Notification Handler | `monitorCharacteristicForService` | ~1,188,577 |
| moveAbsolute | `Original name: moveAbsolute` | ~1,189,138 |
| writeCharacteristic | `writeCharacteristicWithResponseForService` | ~1,188,881 |

### Example Output from hermes_dec_output.js

```javascript
// Line ~1,187,433 - BLE Service definitions
r5 = {'ServiceUUID': '0000ff00-0000-1000-8000-00805f9b34fb',
      'CharacteristicWrite': '0000ff02-0000-1000-8000-00805f9b34fb',
      'CharacteristicRead': '0000ff01-0000-1000-8000-00805f9b34fb'};
r3['Classic'] = r5;
r5 = {'ServiceUUID': '0000a00a-0000-1000-8000-00805f9b34fb',
      'CharacteristicWrite': '0000b003-0000-1000-8000-00805f9b34fb',
      'CharacteristicRead': '0000b002-0000-1000-8000-00805f9b34fb'};
r3['Wifi'] = r5;

// Line ~1,188,852 - Movement commands
r5 = [165, 0, 32, 223, 255];   // UP
r6['up'] = r5;
r5 = [165, 0, 64, 191, 255];   // DOWN
r6['down'] = r5;
r5 = [165, 0, 0, 255, 255];    // STOP
r6['stop'] = r5;

// Line ~1,189,006 - Height command structure
r9 = [166, 168, 1];
r7 = 650;  // MIN height
r7 = 1300; // MAX height
// Height bytes: (height & 0xFF00) >> 8, height & 0xFF
// Then XOR checksum of bytes[2:], then 0xFF
```

### In Decompiled Bytecode (Alternative)

| Content | Search Pattern | Typical Line Range (v1.4.3) |
|---------|----------------|----------------------------|
| BLE Service UUIDs | `0000ff00`, `0000a00a` | ~67,000 (strings_output.txt) |
| Command Arrays | `165, 0, 32`, `165, 0, 64` | ~1,193,000 |
| Desk Types | `BLT_BLTDESK`, `H76_WIFIDESK` | ~68,000-69,000 (strings) |
| GraphQL Mutations | `mutation SetMyDesk` | ~66,000-68,000 (strings) |
| BLE Error Codes | `UnknownError`, `DeviceConnectionFailed` | ~1,186,000 |
| Height Functions | `moveAbsolute`, `moveToHeight` | ~1,193,200 |

### In String Literals

```bash
# strings_output.txt contains all string constants
grep -E "UUID|Service|Characteristic" strings_output.txt
grep -E "BLT_|H76_" strings_output.txt
```

### In AndroidManifest.xml

```xml
<!-- Check for BLE permissions -->
<uses-permission android:name="android.permission.BLUETOOTH"/>
<uses-permission android:name="android.permission.BLUETOOTH_ADMIN"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
```

---

## Search Patterns

### BLE Protocol Discovery

| What to Find | Search Pattern |
|--------------|----------------|
| Service UUIDs | `0000ff00-0000-1000-8000` |
| Characteristic UUIDs | `0000ff01`, `0000ff02`, `0000b002`, `0000b003` |
| Command bytes | `165, 0,` or `0xA5` |
| Height commands | `166, 168` or `0xA6.*0xA8` |
| Write functions | `writeCharacteristicWithResponseForService` |
| Notification handlers | `monitorCharacteristic`, `startNotify` |

### Cloud API Discovery

| What to Find | Search Pattern |
|--------------|----------------|
| GraphQL mutations | `mutation ` |
| GraphQL queries | `query ` |
| API endpoints | `graphql`, `api.ergomate` |
| Feature names | `SetMyDeskBeep`, `SetMyDeskLocked` |

### App Constants

| What to Find | Search Pattern |
|--------------|----------------|
| Desk models | `BLT_BLTDESK`, `H76_WIFIDESK` |
| Height limits | `650`, `1300`, `MIN_HEIGHT`, `MAX_HEIGHT` |
| Error messages | `Error`, `Failed`, `Invalid` |

---

## Useful Tools

### For APK Analysis

| Tool | Purpose | URL |
|------|---------|-----|
| JADX | APK decompiler (GUI + CLI) | [skylot/jadx](https://github.com/skylot/jadx) |

### For Hermes/React Native

| Tool | Purpose | URL |
|------|---------|-----|
| hermes-dec | Hermes bytecode decompiler (recommended) | `pip install git+https://github.com/P1sec/hermes-dec` |
| hermes_rs | Hermes bytecode disassembler | [Pilfer/hermes_rs](https://github.com/Pilfer/hermes_rs) |

### For BLE Testing

```bash
# BLE library for testing commands against real device
pip install bleak
```

---

## Example Workflow

1. **Obtain APK** → Download with apkeep
2. **Decompile** → `jadx -d "jadx_sources" nl.gravity.ergomate.apk`
3. **Decompile Hermes** → `hbc-decompiler index.android.bundle hermes_dec_output.js`
4. **Search for UUIDs** → Find BLE service/characteristic UUIDs
5. **Search for Commands** → Find byte arrays near `writeCharacteristic` calls
6. **Write Test Files** → Create Python scripts using bleak to test commands against real device
7. **Verify & Iterate** → Test findings, observe responses, refine understanding
8. **Document** → Update protocol documentation

---

## Legal Notice

This documentation is provided for educational and interoperability purposes.
