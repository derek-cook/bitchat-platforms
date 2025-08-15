# BitChat CLI

A command-line interface for the BitChat Bluetooth messaging protocol. This CLI application allows you to send messages over Bluetooth to other BitChat-compatible devices using Python and the bleak library.

## Installation

### Quick Setup (Recommended)

Run the setup script to create a virtual environment and install dependencies:

```bash
./setup.sh
```

Then activate the virtual environment:

```bash
source venv/bin/activate
```

### Manual Setup

1. Create a Python virtual environment:
```bash
python3 -m venv venv
```

2. Activate the virtual environment:
```bash
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Make the CLI executable (macOS/Linux):
```bash
chmod +x bitchat_cli.py
```

## Usage

### Basic Message Broadcasting

Send a message to all nearby BitChat devices:

```bash
python bitchat_cli.py --name "Your Name" --message "Hello, BitChat!"
```

### Send to Specific Device

First scan to see available devices, then send to a specific device by MAC address:

```bash
python bitchat_cli.py --name "Your Name" --message "Hello!" --device "AA:BB:CC:DD:EE:FF"
```

### Command Line Options

- `--name`, `-n`: Your sender name (required for sending)
- `--message`, `-m`: Message content to send (required for sending)
- `--scan-timeout`, `-t`: Device scan timeout in seconds (default: 10.0)
- `--device`, `-d`: Specific device MAC address to send to (optional, broadcasts to all if not specified)
- `--listen`, `-l`: Listen mode - receive messages from a device
- `--debug`: Enable debug output to show packet details

## Protocol Compatibility

This CLI implements the same Bluetooth protocol as the main BitChat apps:

- **Service UUID**: `f47b5e2d-4a9e-4c5a-9b3f-8e1d2c3a4b5c`
- **Characteristic UUID**: `a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d`
- **Packet Types**: 
  - Announce packets (0x01, 0x01)
  - Message packets (0x01, 0x04)

## Examples

```bash
# Broadcast a message to all devices
python bitchat_cli.py -n "Alice" -m "Hello everyone!"

# Send with longer scan timeout
python bitchat_cli.py -n "Bob" -m "Testing" -t 20

# Send to specific device
python bitchat_cli.py -n "Charlie" -m "Direct message" -d "12:34:56:78:9A:BC"

# Debug mode - see packet details
python bitchat_cli.py -n "Debug" -m "Test" --debug

# Listen for messages from a device
python bitchat_cli.py --listen -d "12:34:56:78:9A:BC" --debug
```

## Troubleshooting

If messages aren't being received on the other device:

1. **Use debug mode** to verify packet format:
   ```bash
   python bitchat_cli.py -n "Test" -m "Hello" --debug
   ```

2. **Try listening mode** to see if the iPhone is sending messages:
   ```bash
   python bitchat_cli.py --listen -d "YOUR_IPHONE_MAC" --debug
   ```

3. **Check both devices** are using the same service/characteristic UUIDs

## Requirements

- Python 3.7+
- bleak library for Bluetooth Low Energy communication
- Compatible Bluetooth adapter
- Linux, macOS, or Windows with Bluetooth support

## Limitations

- Send-only functionality (no message receiving in this version)
- No encryption or authentication (matches reference implementation)
- Requires compatible BitChat devices to be in range and discoverable