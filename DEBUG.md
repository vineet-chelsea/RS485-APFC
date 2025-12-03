# Modbus Float Debugging Guide

## Quick One-Liners for Testing

### 1. Read Raw Register Values

```python
from pymodbus.client import ModbusSerialClient; import struct; c = ModbusSerialClient(port='/dev/ttyACM0', baudrate=9600); c.connect(); r = c.read_holding_registers(2, 2, slave=1); print(f"Reg[0]={r.registers[0]}, Reg[1]={r.registers[1]}"); c.close()
```

### 2. Decode Float (ABCD order)

```python
from pymodbus.client import ModbusSerialClient; import struct; c = ModbusSerialClient(port='/dev/ttyACM0', baudrate=9600); c.connect(); r = c.read_holding_registers(2, 2, slave=1); b = struct.pack('>HH', r.registers[0], r.registers[1]); f = struct.unpack('>f', b)[0]; print(f"Value: {f}"); c.close()
```

### 3. Decode Float (CDAB order - word swap)

```python
from pymodbus.client import ModbusSerialClient; import struct; c = ModbusSerialClient(port='/dev/ttyACM0', baudrate=9600); c.connect(); r = c.read_holding_registers(2, 2, slave=1); b = struct.pack('>HH', r.registers[1], r.registers[0]); f = struct.unpack('>f', b)[0]; print(f"Value: {f}"); c.close()
```

### 4. Read All Parameters

```python
from pymodbus.client import ModbusSerialClient; import struct; c = ModbusSerialClient(port='/dev/ttyACM0', baudrate=9600); c.connect(); regs = [(2,'PF'),(32,'I'),(38,'V'),(62,'SetPF')]; [print(f"{n}: Reg={c.read_holding_registers(a,2,slave=1).registers}, ABCD={struct.unpack('>f',struct.pack('>HH',*c.read_holding_registers(a,2,slave=1).registers))[0]:.3f}") for a,n in regs]; c.close()
```

### 5. Write and Verify

```python
from pymodbus.client import ModbusSerialClient; import struct; c = ModbusSerialClient(port='/dev/ttyACM0', baudrate=9600); c.connect(); val=-0.8; b=struct.pack('>f',val); w=[struct.unpack('>H',b[0:2])[0],struct.unpack('>H',b[2:4])[0]]; c.write_registers(62,w,slave=1); r=c.read_holding_registers(62,2,slave=1); print(f"Wrote: {val}, Read back: {struct.unpack('>f',struct.pack('>HH',*r.registers))[0]}"); c.close()
```

## Using the Debug Script

Run the comprehensive debug script:

```bash
cd ~/RS485-APFC
source venv/bin/activate
python3 debug_modbus.py
```

This will:
- Show raw register values for all parameters
- Try both ABCD and CDAB decoding
- Test writing a value and reading it back
- Help identify which byte order your device uses

## Manual Testing in Python REPL

```bash
cd ~/RS485-APFC
source venv/bin/activate
python3
```

Then in Python:

```python
from pymodbus.client import ModbusSerialClient
import struct
import os
from dotenv import load_dotenv

load_dotenv()
COM_PORT = os.getenv('COM_PORT', '/dev/ttyACM0')

# Connect
client = ModbusSerialClient(port=COM_PORT, baudrate=9600)
client.connect()

# Read register 2 (PF)
result = client.read_holding_registers(2, 2, slave=1)
print(f"Raw registers: {result.registers}")

# Try ABCD (high word first)
high, low = result.registers[0], result.registers[1]
bytes_abcd = struct.pack('>HH', high, low)
float_abcd = struct.unpack('>f', bytes_abcd)[0]
print(f"ABCD decode: {float_abcd}")

# Try CDAB (word swap)
bytes_cdab = struct.pack('>HH', low, high)
float_cdab = struct.unpack('>f', bytes_cdab)[0]
print(f"CDAB decode: {float_cdab}")

# Test write
test_val = -0.8
write_bytes = struct.pack('>f', test_val)
write_regs = [struct.unpack('>H', write_bytes[0:2])[0], 
              struct.unpack('>H', write_bytes[2:4])[0]]
client.write_registers(62, write_regs, slave=1)

# Read back
read_back = client.read_holding_registers(62, 2, slave=1)
print(f"Read back: {read_back.registers}")

client.close()
```

## What to Look For

1. **Raw register values** - Check if they're reasonable (typically 0-65535)
2. **Decoded values** - One of ABCD or CDAB should give reasonable values
3. **Write/Read back** - The value you write should match what you read back

## Common Issues

- If both ABCD and CDAB give garbage: Check if device uses different byte order within words
- If write doesn't work: Check register address and permissions
- If values are always 0: Check Modbus unit ID and register addresses

