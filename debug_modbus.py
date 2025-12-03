#!/usr/bin/env python3
"""
Quick debug script for Modbus float reading/writing
Use this to test and debug float register operations
"""

import os
import struct
from pymodbus.client import ModbusSerialClient
from dotenv import load_dotenv

load_dotenv()

COM_PORT = os.getenv('COM_PORT', '/dev/ttyACM0')
BAUD_RATE = int(os.getenv('BAUD_RATE', '9600'))
SLAVE_ID = int(os.getenv('SLAVE_ID', '1'))

# Register addresses
PF_REGISTER = 2
CURRENT_REGISTER = 32
VOLTAGE_REGISTER = 38
SET_PF_REGISTER = 62

def read_raw_registers(client, address, count=2, unit_id=1):
    """Read raw register values"""
    try:
        result = client.read_holding_registers(address, count=count, slave=unit_id)
    except TypeError:
        try:
            result = client.read_holding_registers(address, count=count, unit=unit_id)
        except TypeError:
            result = client.read_holding_registers(address, count=count)
    
    if result and not result.isError():
        return result.registers
    return None

def decode_float_abcd(registers):
    """Decode float using ABCD order (Most Significant Register First)"""
    high_word = registers[0]
    low_word = registers[1]
    raw_bytes = struct.pack('>HH', high_word, low_word)
    return struct.unpack('>f', raw_bytes)[0]

def decode_float_cdab(registers):
    """Decode float using CDAB order (word swap)"""
    low_word = registers[0]
    high_word = registers[1]
    raw_bytes = struct.pack('>HH', high_word, low_word)
    return struct.unpack('>f', raw_bytes)[0]

def encode_float_abcd(float_value):
    """Encode float using ABCD order"""
    raw_bytes = struct.pack('>f', float_value)
    high_word = struct.unpack('>H', raw_bytes[0:2])[0]
    low_word = struct.unpack('>H', raw_bytes[2:4])[0]
    return [high_word, low_word]

def encode_float_cdab(float_value):
    """Encode float using CDAB order"""
    raw_bytes = struct.pack('>f', float_value)
    high_word = struct.unpack('>H', raw_bytes[0:2])[0]
    low_word = struct.unpack('>H', raw_bytes[2:4])[0]
    return [low_word, high_word]

# Connect to Modbus
print(f"Connecting to {COM_PORT} at {BAUD_RATE} baud, unit ID {SLAVE_ID}...")
client = ModbusSerialClient(
    port=COM_PORT,
    baudrate=BAUD_RATE,
    parity='N',
    stopbits=1,
    bytesize=8,
    timeout=2
)

if not client.connect():
    print(f"ERROR: Failed to connect to {COM_PORT}")
    exit(1)

print("Connected!\n")

# Test reading registers
print("=" * 60)
print("READING REGISTERS (Raw Values)")
print("=" * 60)

registers_to_test = [
    ("Power Factor", PF_REGISTER),
    ("Current", CURRENT_REGISTER),
    ("Voltage", VOLTAGE_REGISTER),
    ("Set PF", SET_PF_REGISTER),
]

for name, addr in registers_to_test:
    regs = read_raw_registers(client, addr, 2, SLAVE_ID)
    if regs:
        print(f"{name:12} (addr {addr:2d}): Reg[0]={regs[0]:5d} (0x{regs[0]:04X}), Reg[1]={regs[1]:5d} (0x{regs[1]:04X})")
        # Try both decoding methods
        val_abcd = decode_float_abcd(regs)
        val_cdab = decode_float_cdab(regs)
        print(f"              ABCD decode: {val_abcd:12.6f}")
        print(f"              CDAB decode: {val_cdab:12.6f}")
    else:
        print(f"{name:12} (addr {addr:2d}): FAILED to read")
    print()

print("=" * 60)
print("TESTING WRITE (Set PF to -0.8)")
print("=" * 60)

test_value = -0.8
encoded_abcd = encode_float_abcd(test_value)
encoded_cdab = encode_float_cdab(test_value)

print(f"Value to write: {test_value}")
print(f"ABCD encoding: [{encoded_abcd[0]}, {encoded_abcd[1]}] (0x{encoded_abcd[0]:04X}, 0x{encoded_abcd[1]:04X})")
print(f"CDAB encoding: [{encoded_cdab[0]}, {encoded_cdab[1]}] (0x{encoded_cdab[0]:04X}, 0x{encoded_cdab[1]:04X})")
print()

# Try writing with ABCD
print("Writing with ABCD order...")
try:
    result = client.write_registers(SET_PF_REGISTER, encoded_abcd, slave=SLAVE_ID)
except TypeError:
    try:
        result = client.write_registers(SET_PF_REGISTER, encoded_abcd, unit=SLAVE_ID)
    except TypeError:
        result = client.write_registers(SET_PF_REGISTER, encoded_abcd)

if result and not result.isError():
    print("Write successful!")
    # Read back
    regs = read_raw_registers(client, SET_PF_REGISTER, 2, SLAVE_ID)
    if regs:
        print(f"Read back: Reg[0]={regs[0]}, Reg[1]={regs[1]}")
        val_abcd = decode_float_abcd(regs)
        val_cdab = decode_float_cdab(regs)
        print(f"ABCD decode: {val_abcd:.6f}")
        print(f"CDAB decode: {val_cdab:.6f}")
else:
    print("Write failed!")

client.close()
print("\nDone!")

