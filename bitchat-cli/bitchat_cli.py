#!/usr/bin/env python3
"""
BitChat CLI - A command-line Bluetooth messaging client
Implements the same protocol as the main BitChat app
"""

import asyncio
import struct
import time
import uuid
import os
from typing import Optional, List
import argparse

try:
    from bleak import BleakClient, BleakScanner, BLEDevice
    from bleak.backends.characteristic import BleakGATTCharacteristic
except ImportError:
    print("Error: bleak library not found. Please install it with: pip install bleak")
    exit(1)

# Protocol constants from bitchat reference implementation
BITCHAT_SERVICE_UUID = "f47b5e2d-4a9e-4c5a-9b3f-8e1d2c3a4b5c"
BITCHAT_CHAR_UUID = "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"

class BitChatProtocol:
    """Handles BitChat protocol packet generation and parsing"""
    
    @staticmethod
    def generate_sender_id() -> bytes:
        """Generate a random 8-byte sender ID"""
        return os.urandom(8)
    
    @staticmethod
    def generate_announce_packet(sender_id: bytes, sender_name: str, ttl: int = 3) -> bytes:
        """Generate an announce packet"""
        name_bytes = sender_name.encode('utf-8')
        timestamp = int(time.time() * 1000)  # milliseconds
        
        packet_size = 15 + len(sender_id) + len(name_bytes)
        packet = bytearray(packet_size)
        
        offset = 0
        # Packet type: announce (0x01, 0x01)
        packet[offset:offset+2] = struct.pack('BB', 0x01, 0x01)
        offset += 2
        
        # TTL
        packet[offset] = ttl
        offset += 1
        
        # Timestamp (big-endian 64-bit)
        packet[offset:offset+8] = struct.pack('>Q', timestamp)
        offset += 8
        
        # Reserved byte
        packet[offset] = 0x00
        offset += 1
        
        # Name length (big-endian 16-bit)
        packet[offset:offset+2] = struct.pack('>H', len(name_bytes))
        offset += 2
        
        # Sender ID
        packet[offset:offset+len(sender_id)] = sender_id
        offset += len(sender_id)
        
        # Sender name
        packet[offset:offset+len(name_bytes)] = name_bytes
        
        return bytes(packet)
    
    @staticmethod
    def generate_message_packet(sender_id: bytes, sender_name: str, content: str, ttl: int = 3) -> bytes:
        """Generate a message packet"""
        name_bytes = sender_name.encode('utf-8')
        content_bytes = content.encode('utf-8')
        timestamp = int(time.time() * 1000)  # milliseconds
        
        message_uid = str(uuid.uuid4())
        uid_bytes = message_uid.encode('utf-8')
        
        # Calculate message section length
        message_length = (1 +  # flags
                         8 +   # timestamp
                         1 +   # uid length
                         len(uid_bytes) +
                         1 +   # name length
                         len(name_bytes) +
                         2 +   # content length
                         len(content_bytes) +
                         1 +   # sender id length
                         len(sender_id))
        
        # Build message section
        message = bytearray(message_length)
        msg_offset = 0
        
        # Message flags
        message[msg_offset] = 0x10
        msg_offset += 1
        
        # Message timestamp
        message[msg_offset:msg_offset+8] = struct.pack('>Q', timestamp)
        msg_offset += 8
        
        # UID length and UID
        message[msg_offset] = len(uid_bytes)
        msg_offset += 1
        message[msg_offset:msg_offset+len(uid_bytes)] = uid_bytes
        msg_offset += len(uid_bytes)
        
        # Name length and name
        message[msg_offset] = len(name_bytes)
        msg_offset += 1
        message[msg_offset:msg_offset+len(name_bytes)] = name_bytes
        msg_offset += len(name_bytes)
        
        # Content length and content
        message[msg_offset:msg_offset+2] = struct.pack('>H', len(content_bytes))
        msg_offset += 2
        message[msg_offset:msg_offset+len(content_bytes)] = content_bytes
        msg_offset += len(content_bytes)
        
        # Sender ID length and sender ID
        message[msg_offset] = len(sender_id)
        msg_offset += 1
        message[msg_offset:msg_offset+len(sender_id)] = sender_id
        
        # Build full packet
        packet_length = 15 + len(sender_id) + 8 + message_length
        packet = bytearray(packet_length)
        
        offset = 0
        # Packet type: message (0x01, 0x04)
        packet[offset:offset+2] = struct.pack('BB', 0x01, 0x04)
        offset += 2
        
        # TTL
        packet[offset] = ttl
        offset += 1
        
        # Timestamp
        packet[offset:offset+8] = struct.pack('>Q', timestamp)
        offset += 8
        
        # Message flag
        packet[offset] = 0x01
        offset += 1
        
        # Message length
        packet[offset:offset+2] = struct.pack('>H', message_length)
        offset += 2
        
        # Sender ID
        packet[offset:offset+len(sender_id)] = sender_id
        offset += len(sender_id)
        
        # Recipient ID (broadcast: all 0xff)
        packet[offset:offset+8] = b'\xff' * 8
        offset += 8
        
        # Message payload
        packet[offset:offset+message_length] = message
        
        return bytes(packet)

class BitChatCLI:
    """Main CLI application for BitChat"""
    
    def __init__(self):
        self.sender_id = BitChatProtocol.generate_sender_id()
        self.devices: List[BLEDevice] = []
        
    async def scan_devices(self, timeout: float = 10.0) -> List[BLEDevice]:
        """Scan for BitChat devices"""
        print(f"Scanning for BitChat devices (timeout: {timeout}s)...")
        
        devices = await BleakScanner.discover(
            timeout=timeout,
            service_uuids=[BITCHAT_SERVICE_UUID]
        )
        
        bitchat_devices = []
        for device in devices:
            if BITCHAT_SERVICE_UUID.lower() in [s.lower() for s in (device.metadata.get('uuids', []) or [])]:
                bitchat_devices.append(device)
                print(f"Found: {device.name or 'Unknown'} ({device.address})")
        
        self.devices = bitchat_devices
        return bitchat_devices
    
    async def send_message_to_device(self, device: BLEDevice, sender_name: str, message: str) -> bool:
        """Send a message to a specific device"""
        try:
            print(f"Connecting to {device.name or device.address}...")
            
            async with BleakClient(device) as client:
                if not client.is_connected:
                    print(f"Failed to connect to {device.name or device.address}")
                    return False
                
                # Get the characteristic
                char = None
                for service in client.services:
                    if service.uuid.lower() == BITCHAT_SERVICE_UUID.lower():
                        for characteristic in service.characteristics:
                            if characteristic.uuid.lower() == BITCHAT_CHAR_UUID.lower():
                                char = characteristic
                                break
                        break
                
                if not char:
                    print(f"BitChat characteristic not found on {device.name or device.address}")
                    return False
                
                # Send announce packet first
                print(f"Sending announce packet to {device.name or device.address}...")
                announce_packet = BitChatProtocol.generate_announce_packet(self.sender_id, sender_name)
                await client.write_gatt_char(char, announce_packet, response=False)
                await asyncio.sleep(0.5)
                
                # Send message packet
                print(f"Sending message to {device.name or device.address}...")
                message_packet = BitChatProtocol.generate_message_packet(self.sender_id, sender_name, message)
                await client.write_gatt_char(char, message_packet, response=False)
                
                print(f"✓ Message sent to {device.name or device.address}")
                return True
                
        except Exception as e:
            print(f"Error sending to {device.name or device.address}: {e}")
            return False
    
    async def broadcast_message(self, sender_name: str, message: str) -> int:
        """Broadcast message to all discovered devices"""
        if not self.devices:
            print("No devices found. Run scan first.")
            return 0
        
        print(f"Broadcasting message to {len(self.devices)} device(s)...")
        
        tasks = []
        for device in self.devices:
            task = self.send_message_to_device(device, sender_name, message)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for result in results if result is True)
        print(f"Message broadcast complete: {success_count}/{len(self.devices)} devices reached")
        
        return success_count

async def main():
    parser = argparse.ArgumentParser(description='BitChat CLI - Bluetooth messaging client')
    parser.add_argument('--name', '-n', required=True, help='Your sender name')
    parser.add_argument('--message', '-m', required=True, help='Message to send')
    parser.add_argument('--scan-timeout', '-t', type=float, default=10.0, help='Device scan timeout (seconds)')
    parser.add_argument('--device', '-d', help='Specific device address to send to (if not provided, broadcasts to all)')
    
    args = parser.parse_args()
    
    cli = BitChatCLI()
    
    # Scan for devices
    devices = await cli.scan_devices(args.scan_timeout)
    
    if not devices:
        print("No BitChat devices found")
        return
    
    if args.device:
        # Send to specific device
        target_device = None
        for device in devices:
            if device.address.lower() == args.device.lower():
                target_device = device
                break
        
        if not target_device:
            print(f"Device {args.device} not found")
            return
        
        await cli.send_message_to_device(target_device, args.name, args.message)
    else:
        # Broadcast to all devices
        await cli.broadcast_message(args.name, args.message)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled")
    except Exception as e:
        print(f"Error: {e}")