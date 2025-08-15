# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains experimental Bluetooth communication apps that aim to be interoperable with the bitchat mobile app. The project explores decentralized, offline messaging over Bluetooth using minimal dependencies.

Use `/bitchat` as the reference implementation for other apps. It is a fork from the main mobile app that contains the source of truth for the architecture and features that other apps should aim to provide. Changes should not be made in `/bitchat`.

## Development Commands

### Electron App
```bash
# Run the Electron app locally
npx electron ./bitchat-electron/main.js
```

### PWA (Progressive Web App)
```bash
# Start HTTPS server on port 8443 (required for Web Bluetooth)
./bitchat-pwa/server.py

# Start HTTP server on port 8000 (Web Bluetooth won't work)
./bitchat-pwa/server.py --http

# Install cryptography module for HTTPS support
pip install cryptography
```

## Architecture Overview

### Core Components

1. **Bluetooth Protocol Implementation**
   - Service UUID: `f47b5e2d-4a9e-4c5a-9b3f-8e1d2c3a4b5c`
   - Characteristic UUID: `a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d`
   - Packet types: Announce (0x01, 0x01) and Message (0x01, 0x04)
   - Message format includes sender ID, name, content, timestamp, and TTL

2. **Electron App** (`bitchat-electron/`)
   - `main.js`: Electron main process handling window creation and Bluetooth pairing
   - `preload.js`: Bridge between main and renderer processes
   - `renderer.js`: UI logic and event handling
   - `bitchatFunctions.js`: Core Bluetooth communication logic (shared with PWA)
   - Uses Web Bluetooth API through Electron's chromium engine
   - Supports automatic device connection without user prompt

3. **PWA** (`bitchat-pwa/`)
   - `server.py`: Python HTTPS server with self-signed certificates for Web Bluetooth
   - `sw.js`: Service worker for offline functionality
   - `bitchatFunctions.js`: Duplicated from Electron app for isolation
   - `manifest.json`: PWA configuration
   - Browser limitations: Can only act as Bluetooth client, requires explicit device selection

### Key Implementation Details

- **Message Broadcasting**: Connects to each device individually (not true mesh networking)
- **Packet Generation**: Custom binary protocol with specific byte layouts for announce and message packets
- **Device Discovery**: Uses Web Bluetooth API's `requestDevice` with service UUID filter
- **Connection Management**: Handles GATT server connections and characteristic read/write operations
- **No encryption/authentication** currently implemented (experimental proof of concept)

### Current Limitations

- Direct messages show in main chat (no separate DM window)
- PWA requires manual device selection due to browser security
- Broadcast requires individual connections to each device
- No saved contacts/network management
- Service workers cannot access Bluetooth API