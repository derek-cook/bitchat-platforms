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
        """Generate a fixed 8-byte sender ID matching the working implementation"""
        # Use a fixed sender ID like the working script
        return b"deadbeef"
    
    @staticmethod
    def parse_packet(data: bytes) -> dict:
        """Parse a received BitChat packet"""
        if len(data) < 2:
            return None
        
        packet_type = (data[0], data[1])
        result = {"raw_hex": data.hex()}
        
        try:
            if packet_type == (0x01, 0x01):
                # Announce packet
                result["type"] = "announce"
                offset = 2
                result["ttl"] = data[offset]
                offset += 1
                result["timestamp"] = struct.unpack('>Q', data[offset:offset+8])[0]
                offset += 8
                offset += 1  # Skip reserved byte
                name_length = struct.unpack('>H', data[offset:offset+2])[0]
                offset += 2
                result["sender_id"] = data[offset:offset+8]
                offset += 8
                result["sender_name"] = data[offset:offset+name_length].decode('utf-8', errors='ignore')
                
            elif packet_type == (0x01, 0x04):
                # Message packet
                result["type"] = "message"
                offset = 2
                result["ttl"] = data[offset]
                offset += 1
                result["timestamp"] = struct.unpack('>Q', data[offset:offset+8])[0]
                offset += 8
                offset += 1  # Skip message flag
                message_length = struct.unpack('>H', data[offset:offset+2])[0]
                offset += 2
                result["sender_id"] = data[offset:offset+8]
                offset += 8
                result["recipient_id"] = data[offset:offset+8]
                offset += 8
                
                # Parse inner message
                msg_offset = offset
                msg_flags = data[msg_offset]
                msg_offset += 1
                msg_timestamp = struct.unpack('>Q', data[msg_offset:msg_offset+8])[0]
                msg_offset += 8
                
                # UID
                uid_length = data[msg_offset]
                msg_offset += 1
                result["uid"] = data[msg_offset:msg_offset+uid_length].decode('utf-8', errors='ignore')
                msg_offset += uid_length
                
                # Sender name
                name_length = data[msg_offset]
                msg_offset += 1
                result["sender_name"] = data[msg_offset:msg_offset+name_length].decode('utf-8', errors='ignore')
                msg_offset += name_length
                
                # Content
                content_length = struct.unpack('>H', data[msg_offset:msg_offset+2])[0]
                msg_offset += 2
                result["content"] = data[msg_offset:msg_offset+content_length].decode('utf-8', errors='ignore')
                msg_offset += content_length
                
                # Sender ID in message
                sender_id_length = data[msg_offset]
                msg_offset += 1
                result["msg_sender_id"] = data[msg_offset:msg_offset+sender_id_length]
                
            else:
                result["type"] = "unknown"
                
        except Exception as e:
            result["parse_error"] = str(e)
            
        return result
    
    @staticmethod
    def generate_announce_packet(sender_id: bytes, sender_name: bytes, ttl: int = 3) -> bytes:
        """Generate an announce packet matching the working implementation"""
        announce_packet = bytes()
        announce_packet += bytes.fromhex("0101")
        announce_packet += struct.pack('>B', ttl)
        announce_packet += struct.pack('>Q', int(time.time()) * 1000)
        announce_packet += bytes.fromhex("00")
        announce_packet += struct.pack('>H', len(sender_name))
        announce_packet += sender_id
        announce_packet += sender_name
        return announce_packet
    
    @staticmethod
    def generate_message_packet(sender_id: bytes, sender_name: bytes, content: bytes, ttl: int = 3) -> bytes:
        """Generate a message packet matching the working implementation"""
        message = bytes()
        message += bytes.fromhex("10")  # setting senderPeerID flag
        message += struct.pack('>Q', int(time.time()) * 1000)
        uid = str(uuid.uuid4()).encode("utf-8")
        message += struct.pack('>B', len(uid))
        message += uid
        message += struct.pack('>B', len(sender_name))
        message += sender_name
        message += struct.pack('>H', len(content))
        message += content
        message += struct.pack('>B', len(sender_id))
        message += sender_id
        
        message_packet = bytes()
        message_packet += bytes.fromhex("0104")
        message_packet += struct.pack('>B', ttl)
        message_packet += struct.pack('>Q', int(time.time()) * 1000)
        message_packet += bytes.fromhex("01")
        message_packet += struct.pack('>H', len(message))
        message_packet += sender_id
        message_packet += bytes.fromhex("ffffffffffffffff")
        message_packet += message
        return message_packet

class BitChatCLI:
    """Main CLI application for BitChat"""
    
    def __init__(self, debug: bool = False):
        self.sender_id = BitChatProtocol.generate_sender_id()
        self.devices: List[BLEDevice] = []
        self.debug = debug
        
    async def scan_devices(self, timeout: float = 10.0) -> List[BLEDevice]:
        """Scan for BitChat devices using the same method as the working script"""
        print(f"Scanning for BitChat devices (timeout: {timeout}s)...")
        
        # Use the same scan method as the working script
        devices = await BleakScanner.discover(
            timeout=timeout,
            return_adv=True,
            service_uuids=[BITCHAT_SERVICE_UUID]
        )
        
        bitchat_devices = []
        
        if not devices:
            print("No BitChat devices found.")
        else:
            print(f"Found {len(devices)} device(s) advertising BitChat service:")
            for d, a in devices.values():
                print(f"  - {d.name or 'Unknown'} ({d.address})")
                bitchat_devices.append(d)
        
        self.devices = bitchat_devices
        
        if bitchat_devices:
            print("\nAttempting to send messages...")
        
        return bitchat_devices
    
    async def send_message_to_device(self, device: BLEDevice, sender_name: str, message: str) -> bool:
        """Send a message to a specific device using the same method as working script"""
        try:
            async with BleakClient(device.address, timeout=2) as client:
                # Check for BitChat characteristic exactly like the working script
                bitchat_device = False
                for service in client.services:
                    for char in service.characteristics:
                        if str(char.uuid).upper() == BITCHAT_CHAR_UUID.upper():
                            bitchat_device = True
                            break
                
                if not bitchat_device:
                    if self.debug:
                        print(f"  {device.name or device.address} is not a BitChat device")
                    return False
                
                print(f"Found BitChat device: {device.address} Sending Messages...")
                
                # Convert strings to bytes exactly like the working script
                sender_name_bytes = sender_name.encode('utf-8')
                message_bytes = message.encode('utf-8')
                
                # Send announce packet
                announce_packet = BitChatProtocol.generate_announce_packet(self.sender_id, sender_name_bytes)
                
                if self.debug:
                    print(f"  DEBUG: Announce packet ({len(announce_packet)} bytes): {announce_packet.hex()}")
                    print(f"  DEBUG: Sender ID: {self.sender_id.decode() if isinstance(self.sender_id, bytes) else self.sender_id}")
                
                await client.write_gatt_char(BITCHAT_CHAR_UUID, announce_packet, response=False)
                await asyncio.sleep(0.5)
                
                # Send message packet with TTL=5 like working script
                message_packet = BitChatProtocol.generate_message_packet(self.sender_id, sender_name_bytes, message_bytes, ttl=5)
                
                if self.debug:
                    print(f"  DEBUG: Message packet ({len(message_packet)} bytes): {message_packet.hex()}")
                
                await client.write_gatt_char(BITCHAT_CHAR_UUID, message_packet, response=False)
                await asyncio.sleep(0.5)
                
                print(f"✓ Message sent successfully")
                return True
                
        except Exception as e:
            error_msg = str(e)
            if "connect" in error_msg.lower():
                print(f"  Could not connect to {device.name or device.address}")
            elif "service" in error_msg.lower() or "uuid" in error_msg.lower():
                print(f"  {device.name or device.address} is not a BitChat device")
            else:
                print(f"  Error with {device.name or device.address}: {error_msg}")
            return False
    
    async def listen_for_messages(self, device: BLEDevice, duration: float = 60.0) -> None:
        """Listen for incoming messages from a device"""
        try:
            print(f"Connecting to {device.name or device.address} for listening...")
            
            async with BleakClient(device) as client:
                if not client.is_connected:
                    print(f"Failed to connect to {device.name or device.address}")
                    return
                
                # Find the BitChat characteristic
                char = None
                for service in client.services:
                    if service.uuid.lower() == BITCHAT_SERVICE_UUID.lower():
                        for characteristic in service.characteristics:
                            if characteristic.uuid.lower() == BITCHAT_CHAR_UUID.lower():
                                char = characteristic
                                break
                        break
                
                if not char:
                    print(f"BitChat service not found on {device.name or device.address}")
                    return
                
                print(f"Connected. Listening for messages for {duration} seconds...")
                print("Press Ctrl+C to stop listening\n")
                
                # Define callback for notifications
                def notification_handler(sender, data):
                    parsed = BitChatProtocol.parse_packet(data)
                    
                    if parsed is None:
                        print(f"Received invalid packet ({len(data)} bytes)")
                        return
                    
                    if self.debug:
                        print(f"DEBUG: Raw data ({len(data)} bytes): {data.hex()}")
                    
                    if parsed["type"] == "announce":
                        print(f"📢 {parsed['sender_name']} joined the chat")
                        if self.debug:
                            print(f"   Sender ID: {parsed['sender_id'].hex()}")
                            
                    elif parsed["type"] == "message":
                        timestamp = parsed.get("timestamp", 0)
                        time_str = time.strftime("%H:%M:%S", time.localtime(timestamp / 1000))
                        print(f"💬 [{time_str}] {parsed['sender_name']}: {parsed['content']}")
                        if self.debug:
                            print(f"   UID: {parsed.get('uid', 'unknown')}")
                            print(f"   Sender ID: {parsed['sender_id'].hex()}")
                            
                    elif parsed["type"] == "unknown":
                        print(f"❓ Unknown packet type: {data[0]:02x} {data[1]:02x}")
                        
                    if "parse_error" in parsed:
                        print(f"⚠️  Parse error: {parsed['parse_error']}")
                        if self.debug:
                            print(f"   Raw: {parsed['raw_hex']}")
                
                # Check if characteristic supports notifications
                if "notify" in char.properties or "indicate" in char.properties:
                    await client.start_notify(char, notification_handler)
                    
                    # Wait for the specified duration
                    await asyncio.sleep(duration)
                    
                    await client.stop_notify(char)
                    print(f"\nStopped listening after {duration} seconds")
                else:
                    print("This characteristic doesn't support notifications. Trying to read...")
                    
                    # Poll for messages
                    start_time = asyncio.get_event_loop().time()
                    while asyncio.get_event_loop().time() - start_time < duration:
                        try:
                            data = await client.read_gatt_char(char)
                            if data:
                                print(f"Read {len(data)} bytes")
                                if self.debug:
                                    print(f"DEBUG: {data.hex()}")
                        except Exception as e:
                            if self.debug:
                                print(f"DEBUG: Read error: {e}")
                        
                        await asyncio.sleep(2)  # Poll every 2 seconds
                        
        except Exception as e:
            print(f"Error listening to {device.name or device.address}: {e}")
    
    async def broadcast_message(self, sender_name: str, message: str) -> int:
        """Broadcast message to all discovered devices"""
        if not self.devices:
            print("No devices found.")
            return 0
        
        success_count = 0
        for device in self.devices:
            try:
                result = await self.send_message_to_device(device, sender_name, message)
                if result:
                    success_count += 1
            except Exception as e:
                if self.debug:
                    print(f"  Error with {device.address}: {e}")
                continue
        
        print(f"\nBroadcast complete: {success_count}/{len(self.devices)} devices reached")
        
        return success_count

async def main():
    parser = argparse.ArgumentParser(description='BitChat CLI - Bluetooth messaging client')
    parser.add_argument('--name', '-n', help='Your sender name')
    parser.add_argument('--message', '-m', help='Message to send')
    parser.add_argument('--scan-timeout', '-t', type=float, default=10.0, help='Device scan timeout (seconds)')
    parser.add_argument('--device', '-d', help='Specific device address to send to (if not provided, broadcasts to all)')
    parser.add_argument('--listen', '-l', action='store_true', help='Listen mode - receive messages instead of sending')
    parser.add_argument('--debug', action='store_true', help='Enable debug output to show packet details')
    
    args = parser.parse_args()
    
    # Validate arguments based on mode
    if args.listen:
        if not args.device:
            parser.error("Listen mode requires --device to specify which device to listen from")
    else:
        if not args.name or not args.message:
            parser.error("Sending mode requires both --name and --message")
    
    cli = BitChatCLI(debug=args.debug)
    
    # Scan for devices
    devices = await cli.scan_devices(args.scan_timeout)
    
    if not devices:
        print("No Bluetooth devices found")
        return
    
    if args.listen:
        # Listen mode
        target_device = None
        for device in devices:
            if device.address.lower() == args.device.lower():
                target_device = device
                break
        
        if not target_device:
            print(f"Device {args.device} not found")
            return
        
        await cli.listen_for_messages(target_device, duration=60.0)
    else:
        # Send mode
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