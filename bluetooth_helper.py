#!/usr/bin/env python3
"""
Bluetooth Helper Script for AgriTesk
Helps with HC-05 Bluetooth module management
"""

import subprocess
import time
import sys
import os

def run_command(cmd, capture_output=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def scan_bluetooth_devices():
    """Scan for available Bluetooth devices"""
    print("Scanning for Bluetooth devices...")
    success, stdout, stderr = run_command("hcitool scan")
    
    if not success:
        print(f"Error scanning: {stderr}")
        return []
    
    devices = []
    lines = stdout.strip().split('\n')
    for line in lines:
        if line.strip():
            parts = line.split()
            if len(parts) >= 2:
                mac = parts[0]
                name = ' '.join(parts[1:])
                devices.append((mac, name))
                print(f"Found: {name} ({mac})")
    
    return devices

def find_hc05():
    """Find HC-05 device in scan results"""
    devices = scan_bluetooth_devices()
    for mac, name in devices:
        if 'HC-05' in name.upper() or 'HC05' in name.upper():
            return mac, name
    return None, None

def bind_hc05(mac_address):
    """Bind HC-05 to rfcomm0"""
    print(f"Binding HC-05 ({mac_address}) to rfcomm0...")
    
    # First release any existing binding
    run_command("sudo rfcomm release 0")
    time.sleep(1)
    
    # Bind the device
    success, stdout, stderr = run_command(f"sudo rfcomm bind 0 {mac_address}")
    
    if success:
        print("Successfully bound HC-05 to rfcomm0")
        time.sleep(2)
        
        # Check if device is available
        if os.path.exists("/dev/rfcomm0"):
            print("Device /dev/rfcomm0 is now available")
            return True
        else:
            print("Warning: Device /dev/rfcomm0 not found after binding")
            return False
    else:
        print(f"Failed to bind HC-05: {stderr}")
        return False

def unbind_hc05():
    """Unbind HC-05 from rfcomm0"""
    print("Unbinding HC-05 from rfcomm0...")
    success, stdout, stderr = run_command("sudo rfcomm release 0")
    
    if success:
        print("Successfully unbound HC-05")
    else:
        print(f"Failed to unbind: {stderr}")
    
    return success

def check_connection():
    """Check if rfcomm0 is available and working"""
    if not os.path.exists("/dev/rfcomm0"):
        print("Device /dev/rfcomm0 not found")
        return False
    
    print("Device /dev/rfcomm0 found")
    
    # Try to test the connection
    try:
        import serial
        ser = serial.Serial("/dev/rfcomm0", 9600, timeout=1)
        ser.close()
        print("Connection test successful")
        return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False

def main():
    """Main function"""
    print("=== AgriTesk Bluetooth Helper ===")
    print()
    
    while True:
        print("\nOptions:")
        print("1. Scan for Bluetooth devices")
        print("2. Find and bind HC-05")
        print("3. Check connection status")
        print("4. Unbind HC-05")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            devices = scan_bluetooth_devices()
            if not devices:
                print("No devices found")
        
        elif choice == "2":
            mac, name = find_hc05()
            if mac:
                print(f"Found HC-05: {name} ({mac})")
                bind_hc05(mac)
            else:
                print("HC-05 not found in scan results")
                print("Make sure your HC-05 is powered on and in pairing mode")
        
        elif choice == "3":
            check_connection()
        
        elif choice == "4":
            unbind_hc05()
        
        elif choice == "5":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please enter 1-5.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
