#!/usr/bin/env python3
"""
Test script for AgriTesk system
Tests the complete data flow from Arduino to web application
"""

import requests
import time
import json

def test_websocket_server():
    """Test if the WebSocket server is running"""
    try:
        response = requests.get("http://127.0.0.1:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ WebSocket server is running")
            return True
        else:
            print(f"❌ WebSocket server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ WebSocket server not accessible: {e}")
        return False

def test_sensor_data_endpoint():
    """Test the sensor data endpoint"""
    try:
        test_data = {
            "weatherTemp": 25.5,
            "waterTemp": 18.2,
            "weatherHum": 65.0,
            "soilMoist": 45.0,
            "waterLevel": 1,
            "timestamp": time.time()
        }
        
        response = requests.post("http://127.0.0.1:8000/sensor_data", 
                               json=test_data, timeout=5)
        if response.status_code == 200:
            print("✅ Sensor data endpoint is working")
            return True
        else:
            print(f"❌ Sensor data endpoint returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Sensor data endpoint error: {e}")
        return False

def test_bluetooth_connection():
    """Test if Bluetooth device is available"""
    import os
    if os.path.exists("/dev/rfcomm0"):
        print("✅ Bluetooth device /dev/rfcomm0 is available")
        return True
    else:
        print("❌ Bluetooth device /dev/rfcomm0 not found")
        return False

def main():
    """Run all tests"""
    print("=== AgriTesk System Test ===")
    print()
    
    tests = [
        ("WebSocket Server", test_websocket_server),
        ("Sensor Data Endpoint", test_sensor_data_endpoint),
        ("Bluetooth Connection", test_bluetooth_connection)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        result = test_func()
        results.append((test_name, result))
        print()
    
    print("=== Test Results ===")
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("🎉 All tests passed! Your system is ready.")
    else:
        print("⚠️  Some tests failed. Check the issues above.")
    
    print("\nTo start the system, run:")
    print("  ./start_agritesk.sh")
    print("  or")
    print("  python start_agritesk.py")

if __name__ == "__main__":
    main()
