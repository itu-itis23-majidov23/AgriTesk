#!/usr/bin/env python3
"""
Test script to verify command flow from web interface to Arduino
"""

import requests
import time
import json

def test_command_flow():
    """Test sending commands through the system"""
    print("=== AgriTesk Command Flow Test ===")
    
    # Test commands
    test_commands = [
        "fan on",
        "pump on", 
        "status",
        "fan off",
        "pump off"
    ]
    
    server_url = "http://127.0.0.1:8000"
    
    print(f"Testing command flow to {server_url}")
    
    for command in test_commands:
        print(f"\nTesting command: '{command}'")
        
        try:
            # Queue the command
            response = requests.post(f"{server_url}/queue_command", 
                                   json={"command": command}, 
                                   timeout=5)
            
            if response.status_code == 200:
                print(f"✓ Command '{command}' queued successfully")
                
                # Check if command was picked up
                time.sleep(1)
                check_response = requests.get(f"{server_url}/get_command", timeout=5)
                if check_response.status_code == 200:
                    data = check_response.json()
                    if data.get('command') == command:
                        print(f"✓ Command '{command}' retrieved from queue")
                    elif data.get('command') is None:
                        print(f"⚠ Command queue is empty (already processed?)")
                    else:
                        print(f"⚠ Different command in queue: {data.get('command')}")
                else:
                    print(f"✗ Failed to check command queue: {check_response.status_code}")
            else:
                print(f"✗ Failed to queue command: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("✗ Cannot connect to server. Make sure main.py is running.")
            break
        except Exception as e:
            print(f"✗ Error testing command '{command}': {e}")
        
        time.sleep(2)  # Wait between commands
    
    print("\n=== Test Complete ===")
    print("If commands are working properly, you should see them being")
    print("processed by receive.py and sent to your Arduino via Bluetooth.")

if __name__ == "__main__":
    test_command_flow()
