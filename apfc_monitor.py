"""
APFC Relay Monitoring Service

Monitors Power Factor, Current, Voltage, and Set PF from APFC relay via Modbus
"""

import os
import time
import sys
import math
from datetime import datetime
from collections import deque
from pymodbus.client import ModbusSerialClient
import struct
from dotenv import load_dotenv

load_dotenv()

# Modbus configuration
COM_PORT = os.getenv('COM_PORT', '/dev/ttyACM0')  # Default to Linux serial port
BAUD_RATE = int(os.getenv('BAUD_RATE', '9600'))
SLAVE_ID = int(os.getenv('SLAVE_ID', '1'))
TIMEOUT = 2

# Register addresses (holding registers for APFC relay)
PF_REGISTER = 0          # Power Factor
CURRENT_REGISTER = 30    # Current
VOLTAGE_REGISTER = 36    # Voltage
SET_PF_REGISTER = 118    # Set Power Factor

# Reading interval
READ_INTERVAL = 1  # Read every second
CONTROL_INTERVAL = 6  # Run control logic every 6 seconds
MAX_HISTORY = 10   # Keep last 10 values for each parameter

# PF Control parameters
INITIAL_PF = -0.8  # Initial PF value when program starts
MIN_PF = -0.9      # Minimum PF limit (restricted to -0.9 at upwards)
PF_STEP = 0.01     # PF adjustment step
KW_THRESHOLD = 56000  # kW threshold for different control logic
KW_MIN_THRESHOLD = 5000  # Minimum kW threshold - skip control if below this

class APFCMonitorService:
    def __init__(self):
        """Initialize APFC monitoring service"""
        # Check if port exists
        if not os.path.exists(COM_PORT):
            print(f"[ERROR] Serial port {COM_PORT} does not exist!")
            print(f"[INFO] Available serial ports:")
            import glob
            ports = glob.glob('/dev/tty[A-Z]*')
            if ports:
                for p in sorted(ports):
                    print(f"  - {p}")
            else:
                print("  No serial ports found")
            print(f"\n[INFO] To fix:")
            print(f"  1. Check if device is connected")
            print(f"  2. Check .env file has correct COM_PORT")
            print(f"  3. Run: ls -l /dev/tty* to see available ports")
            raise FileNotFoundError(f"Serial port {COM_PORT} not found")
        
        # Check port permissions
        if not os.access(COM_PORT, os.R_OK | os.W_OK):
            print(f"[ERROR] Permission denied accessing {COM_PORT}")
            print(f"[INFO] To fix, add user to dialout group:")
            print(f"  sudo usermod -a -G dialout $USER")
            print(f"  Then logout and login again (or reboot)")
            raise PermissionError(f"Permission denied for {COM_PORT}")
        
        # Initialize PLC client (shared connection)
        self.plc_client = ModbusSerialClient(
            port=COM_PORT,
            baudrate=BAUD_RATE,
            parity='N',
            stopbits=1,
            bytesize=8,
            timeout=TIMEOUT
        )
        self.slave_id = SLAVE_ID
        # Try to set unit_id on client (for some pymodbus versions)
        try:
            self.plc_client.unit_id = SLAVE_ID
        except:
            pass
        
        # Initialize arrays to store last 10 values for each parameter
        self.power_factor_history = deque(maxlen=MAX_HISTORY)
        self.current_history = deque(maxlen=MAX_HISTORY)
        self.voltage_history = deque(maxlen=MAX_HISTORY)
        self.set_pf_history = deque(maxlen=MAX_HISTORY)
        
        # Current set PF value
        self.current_set_pf = INITIAL_PF
        self.control_count = 0
    
    def read_float_register(self, register_address):
        """
        Read a float value from Modbus holding register
        Floats in Modbus are typically 32-bit IEEE 754, requiring 2 registers
        """
        try:
            # Try different parameter names for different pymodbus versions
            try:
                result = self.plc_client.read_holding_registers(
                    register_address,
                    count=2,  # Read 2 registers for 32-bit float
                    slave=self.slave_id
                )
            except TypeError:
                # Try with 'unit' parameter (pymodbus 3.x)
                try:
                    result = self.plc_client.read_holding_registers(
                        register_address,
                        count=2,
                        unit=self.slave_id
                    )
                except TypeError:
                    # Try without parameter (uses client's unit_id)
                    result = self.plc_client.read_holding_registers(
                        register_address,
                        count=2
                    )
            
            if result and not result.isError():
                # Decode as 32-bit float (IEEE 754)
                # Modbus floating point: CDAB order (word swap)
                # Swap the register order: use register[1] first, then register[0]
                # This is equivalent to: low_word = reg[0], high_word = reg[1], pack(high, low)
                raw_bytes = struct.pack('>HH', result.registers[1], result.registers[0])
                float_value = struct.unpack('>f', raw_bytes)[0]
                
                # Validate the float value (check for reasonable range)
                if math.isfinite(float_value) and abs(float_value) < 1e10:
                    return round(float_value, 3)
                else:
                    # Invalid value, return None
                    return None
            return None
        except Exception as e:
            print(f"[ERROR] Failed to read register {register_address}: {e}")
            return None
    
    def read_power_factor(self):
        """Read current Power Factor from register 2"""
        return self.read_float_register(PF_REGISTER)
    
    def read_current(self):
        """Read current value from register 32"""
        return self.read_float_register(CURRENT_REGISTER)
    
    def read_voltage(self):
        """Read voltage value from register 38"""
        return self.read_float_register(VOLTAGE_REGISTER)
    
    def read_set_pf(self):
        """Read set Power Factor from register 62"""
        return self.read_float_register(SET_PF_REGISTER)
    
    def write_float_register(self, register_address, float_value):
        """
        Write a float value to Modbus holding register
        Floats in Modbus are typically 32-bit IEEE 754, requiring 2 registers
        """
        try:
            # Pack float as 32-bit IEEE 754 (big-endian)
            raw_bytes = struct.pack('>f', float_value)
            # Split into two 16-bit words (big-endian)
            high_word = struct.unpack('>H', raw_bytes[0:2])[0]
            low_word = struct.unpack('>H', raw_bytes[2:4])[0]
            # Modbus floating point: CDAB order (word swap)
            # Write low word first, then high word
            payload = [low_word, high_word]
            
            # Try different parameter names for different pymodbus versions
            try:
                result = self.plc_client.write_registers(
                    register_address,
                    payload,
                    slave=self.slave_id
                )
            except TypeError:
                # Try with 'unit' parameter (pymodbus 3.x)
                try:
                    result = self.plc_client.write_registers(
                        register_address,
                        payload,
                        unit=self.slave_id
                    )
                except TypeError:
                    # Try without parameter (uses client's unit_id)
                    result = self.plc_client.write_registers(
                        register_address,
                        payload
                    )
            
            if result and not result.isError():
                return True
            return False
        except Exception as e:
            print(f"[ERROR] Failed to write register {register_address}: {e}")
            return False
    
    def set_power_factor(self, pf_value):
        """Set Power Factor to register 62"""
        # Ensure PF is always >= -0.9 (never falls below -0.9)
        if pf_value < MIN_PF:
            pf_value = MIN_PF
            print(f"[WARNING] PF would be below minimum ({pf_value:.3f} < {MIN_PF}), clamped to {MIN_PF}")
        
        # Double check: PF must be >= -0.9
        if pf_value < MIN_PF:
            print(f"[ERROR] PF validation failed: {pf_value:.3f} is below minimum {MIN_PF}")
            return False
        
        success = self.write_float_register(SET_PF_REGISTER, pf_value)
        if success:
            self.current_set_pf = pf_value
            return True
        return False
    
    def calculate_kw(self, voltage, current, power_factor):
        """Calculate kW = sqrt(3) * V * I * pf"""
        if voltage is None or current is None or power_factor is None:
            return None
        kw = math.sqrt(3) * voltage * current * power_factor
        return round(kw, 2)
    
    def control_power_factor(self, voltage, current, power_factor):
        """
        Control logic for adjusting Power Factor based on kW and current
        (Reversed logic since PF tends to 1 in reality)
        
        Logic:
        - If kW < 5000: Set PF to -0.8 and skip control
        1. If kW >= 5000 and kW < 56000:
           - If I < (kw/V/SQRT(3)+28+(V-404)*2): pf += 0.01
           - If I > (kw/V/SQRT(3)+28+(V-404)*2): pf -= 0.01
        2. If kW >= 56000:
           - If I < (kw/V/SQRT(3)+(V-404)*2): pf += 0.01
           - If I > (kw/V/SQRT(3)+(V-404)*2): pf -= 0.01
        """
        if voltage is None or current is None or power_factor is None:
            return False
        
        # Validate voltage to prevent division by zero
        if voltage is None or voltage == 0 or abs(voltage) < 0.1:
            print(f"[CONTROL] Skipping control: voltage is invalid ({voltage})")
            return False
        
        # Calculate kW
        kw = self.calculate_kw(voltage, current, power_factor)
        if kw is None:
            return False
        
        # Additional safety check - ensure voltage is still valid after kW calculation
        if voltage == 0 or abs(voltage) < 0.1:
            print(f"[CONTROL] Skipping control: voltage became invalid ({voltage})")
            return False
        
        # If kW < 5000, set PF to -0.8 and skip control logic
        if kw < KW_MIN_THRESHOLD:
            if abs(self.current_set_pf - INITIAL_PF) > 0.001:
                print(f"[CONTROL] kW ({kw:.2f}) < {KW_MIN_THRESHOLD}, setting PF to {INITIAL_PF}")
                self.set_power_factor(INITIAL_PF)
            return False
        
        # Calculate threshold current based on kW
        sqrt3 = math.sqrt(3)
        
        try:
            if kw < KW_THRESHOLD:
                # Case 1: kW < 56000
                threshold_current = (kw / voltage / sqrt3) + 28 + (voltage - 404) * 2
            else:
                # Case 2: kW >= 56000
                threshold_current = (kw / voltage / sqrt3) + (voltage - 404) * 2
        except ZeroDivisionError:
            print(f"[CONTROL] Division by zero error: voltage={voltage}, kw={kw}")
            return False
        
        # Adjust PF based on current comparison (reversed logic since PF tends to 1)
        new_pf = self.current_set_pf
        
        if current < threshold_current:
            new_pf += PF_STEP
            print(f"[CONTROL] Current ({current:.3f} A) < threshold ({threshold_current:.3f} A), increasing PF")
        elif current > threshold_current:
            new_pf -= PF_STEP
            print(f"[CONTROL] Current ({current:.3f} A) > threshold ({threshold_current:.3f} A), decreasing PF")
        else:
            # Current is within tolerance, no adjustment needed
            return False
        
        # Ensure PF is always >= -0.9 (never falls below -0.9)
        if new_pf < MIN_PF:
            new_pf = MIN_PF
            print(f"[CONTROL] PF would go below minimum, clamped to {MIN_PF}")
        
        # Only update if PF changed
        if abs(new_pf - self.current_set_pf) > 0.001:
            success = self.set_power_factor(new_pf)
            if success:
                print(f"[CONTROL] PF adjusted: {self.current_set_pf:.3f} -> {new_pf:.3f} (kW: {kw:.2f})")
                return True
        
        return False
    
    def update_history(self, power_factor, current, voltage, set_pf):
        """Update history arrays with new readings (keeps last 10 values)"""
        if power_factor is not None:
            self.power_factor_history.append(power_factor)
        if current is not None:
            self.current_history.append(current)
        if voltage is not None:
            self.voltage_history.append(voltage)
        if set_pf is not None:
            self.set_pf_history.append(set_pf)
    
    def get_latest_values(self):
        """Get the latest values for each parameter"""
        return {
            'power_factor': self.power_factor_history[-1] if self.power_factor_history else None,
            'current': self.current_history[-1] if self.current_history else None,
            'voltage': self.voltage_history[-1] if self.voltage_history else None,
            'set_pf': self.set_pf_history[-1] if self.set_pf_history else None
        }
    
    def get_all_history(self):
        """Get all history arrays"""
        return {
            'power_factor': list(self.power_factor_history),
            'current': list(self.current_history),
            'voltage': list(self.voltage_history),
            'set_pf': list(self.set_pf_history)
        }
    
    def run(self):
        """Main service loop"""
        print(f"\n{'='*60}")
        print("APFC Relay Monitoring Service")
        print(f"{'='*60}")
        print(f"Reading APFC parameters every {READ_INTERVAL} second")
        print(f"Control logic runs every {CONTROL_INTERVAL} seconds")
        print(f"Registers: PF={PF_REGISTER}, Current={CURRENT_REGISTER}, Voltage={VOLTAGE_REGISTER}, Set PF={SET_PF_REGISTER}")
        print(f"PF Control: Initial={INITIAL_PF}, Min={MIN_PF}, Step={PF_STEP}, kW Threshold={KW_THRESHOLD}")
        print(f"{'='*60}\n")
        
        # Connect to PLC
        print(f"[INFO] Attempting to connect to {COM_PORT}...")
        try:
            if not self.plc_client.connect():
                print(f"[ERROR] Failed to connect to APFC relay on {COM_PORT}")
                print(f"[INFO] Troubleshooting:")
                print(f"  1. Check if device is connected: ls -l {COM_PORT}")
                print(f"  2. Check permissions: ls -l {COM_PORT}")
                print(f"  3. Check if port is in use: lsof {COM_PORT}")
                print(f"  4. Add user to dialout: sudo usermod -a -G dialout $USER")
                return
        except Exception as e:
            print(f"[ERROR] Connection error: {e}")
            print(f"[INFO] Check:")
            print(f"  - Port exists: ls -l {COM_PORT}")
            print(f"  - Permissions: sudo chmod 666 {COM_PORT} (temporary fix)")
            print(f"  - User in dialout group: groups")
            return
        
        print(f"[OK] Connected to APFC relay on {COM_PORT}\n")
        
        # Initialize PF to -0.8 at startup
        print(f"[INIT] Setting initial PF to {INITIAL_PF}")
        if self.set_power_factor(INITIAL_PF):
            print(f"[OK] Initial PF set to {INITIAL_PF}")
        else:
            print(f"[WARNING] Failed to set initial PF")
        
        reading_count = 0
        
        try:
            while True:
                try:
                    # Read all parameters
                    power_factor = self.read_power_factor()
                    current = self.read_current()
                    voltage = self.read_voltage()
                    set_pf = self.read_set_pf()
                    
                    if power_factor is not None or current is not None or voltage is not None:
                        reading_count += 1
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        
                        # Update history arrays (keeps last 10 values)
                        self.update_history(power_factor, current, voltage, set_pf)
                        
                        # Run control logic every CONTROL_INTERVAL seconds
                        self.control_count += 1
                        if self.control_count >= CONTROL_INTERVAL:
                            self.control_count = 0
                            # Execute PF control logic (only if we have valid readings)
                            # Ensure voltage is not None, not zero, and reasonable (> 100V)
                            if (voltage is not None and current is not None and power_factor is not None and
                                voltage != 0 and abs(voltage) >= 100):  # Ensure voltage is valid and reasonable
                                try:
                                    self.control_power_factor(voltage, current, power_factor)
                                except ZeroDivisionError as e:
                                    print(f"[ERROR] Division by zero in control logic: voltage={voltage}, current={current}, pf={power_factor}")
                                    import traceback
                                    traceback.print_exc()
                                except Exception as e:
                                    print(f"[ERROR] Control logic error: {e}")
                                    import traceback
                                    traceback.print_exc()
                        
                        # Calculate and display kW
                        kw = self.calculate_kw(voltage, current, power_factor)
                        kw_str = f"{kw:.2f}" if kw is not None else "N/A"
                        
                        # Display
                        pf_str = f"{power_factor:.3f}" if power_factor is not None else "N/A"
                        current_str = f"{current:.3f}" if current is not None else "N/A"
                        voltage_str = f"{voltage:.3f}" if voltage is not None else "N/A"
                        set_pf_str = f"{set_pf:.3f}" if set_pf is not None else "N/A"
                        
                        print(f"[{timestamp}] Reading #{reading_count} - "
                              f"PF: {pf_str} | Current: {current_str} A | "
                              f"Voltage: {voltage_str} V | Set PF: {set_pf_str} | kW: {kw_str}")
                    else:
                        print(f"[WARNING] Failed to read values from APFC relay")
                    
                    time.sleep(READ_INTERVAL)
                    
                except Exception as e:
                    print(f"[ERROR] Error in main loop: {e}")
                    print(f"[INFO] Continuing after error...")
                    time.sleep(READ_INTERVAL)
                    continue
                
        except KeyboardInterrupt:
            print("\n[STOPPED] Service stopped by user")
        except Exception as e:
            print(f"\n[FATAL ERROR] Service crashed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                self.plc_client.close()
            except:
                pass
            print("\n[OK] Service stopped")

def main():
    """Main entry point"""
    service = APFCMonitorService()
    service.run()

if __name__ == "__main__":
    main()

