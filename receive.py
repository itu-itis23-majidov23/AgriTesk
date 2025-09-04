import serial
import json
import requests
import time

# WebSocket server URL
WEBSOCKET_SERVER = "http://127.0.0.1:8000"
COMMAND_SERVER = "http://127.0.0.1:8000"

def send_to_websocket(sensor_data):
    """Send sensor data to the WebSocket server"""
    try:
        # Send data via HTTP POST to the WebSocket server
        response = requests.post(f"{WEBSOCKET_SERVER}/sensor_data", 
                               json=sensor_data, 
                               timeout=1)
        if response.status_code == 200:
            print("Data sent to WebSocket server successfully")
        else:
            print(f"Failed to send data: {response.status_code}")
    except Exception as e:
        print(f"Error sending to WebSocket: {e}")

def send_command_to_arduino(command):
    """Send command to Arduino via Bluetooth"""
    global ser
    try:
        if ser and ser.is_open:
            command_with_newline = command + '\n'
            ser.write(command_with_newline.encode())
            ser.flush()
            print(f"Command sent to Arduino via Bluetooth: {command}")
            return True
        else:
            print("Bluetooth connection not available for sending commands")
            return False
    except Exception as e:
        print(f"Error sending command to Arduino: {e}")
        return False

def check_for_commands():
    """Check for commands from the web server"""
    try:
        response = requests.get(f"{COMMAND_SERVER}/get_command", timeout=1)
        if response.status_code == 200:
            data = response.json()
            if data.get('command'):
                command = data['command']
                print(f"Received command from web server: {command}")
                success = send_command_to_arduino(command)
                
                # Acknowledge the command
                requests.post(f"{COMMAND_SERVER}/ack_command", 
                            json={"command": command, "success": success}, 
                            timeout=1)
                return True
        return False
    except Exception as e:
        # Silently handle connection errors (server might not be ready)
        return False



def parse_sensor_data(data_string):
    """Parse the comma-separated sensor data from Arduino"""
    try:
        parts = data_string.strip().split(',')
        if len(parts) == 7:
            # New format: weatherTemp,waterTemp,humidity,soilMoist,waterLevel,fanState,pumpState
            return {
                "weatherTemp": float(parts[0]),
                "waterTemp": float(parts[1]),
                "weatherHum": float(parts[2]),
                "soilMoist": float(parts[3]),
                "waterLevel": int(parts[4]),
                "fanState": int(parts[5]),
                "pumpState": int(parts[6]),
                "timestamp": time.time()
            }
        elif len(parts) == 5:
            # Legacy format: weatherTemp,waterTemp,weatherHum,soilMoist,waterLevel
            return {
                "weatherTemp": float(parts[0]),
                "waterTemp": float(parts[1]),
                "weatherHum": float(parts[2]),
                "soilMoist": float(parts[3]),
                "waterLevel": int(parts[4]),
                "fanState": 0,  # Default values for missing relay states
                "pumpState": 0,
                "timestamp": time.time()
            }
        else:
            print(f"Invalid data format (expected 5 or 7 parts, got {len(parts)}): {data_string}")
            return None
    except ValueError as e:
        print(f"Error parsing data: {e}")
        return None

# Global serial connection
ser = None

def connect_bluetooth():
    """Attempt to connect to Bluetooth device"""
    global ser
    try:
        if ser and ser.is_open:
            ser.close()
        
        ser = serial.Serial("/dev/rfcomm0", 9600, timeout=1)
        print("Connected to HC-05 Bluetooth module")
        return True
    except serial.SerialException as e:
        print(f"Failed to connect to Bluetooth: {e}")
        return False

def reconnect_bluetooth():
    """Attempt to reconnect to Bluetooth device"""
    global ser
    print("Attempting to reconnect to Bluetooth...")
    
    # Try to release and rebind the rfcomm device
    try:
        import subprocess
        subprocess.run(["sudo", "rfcomm", "release", "0"], capture_output=True)
        time.sleep(1)
        subprocess.run(["sudo", "rfcomm", "bind", "0"], capture_output=True)
        time.sleep(2)
    except Exception as e:
        print(f"Error during rfcomm operations: {e}")
    
    return connect_bluetooth()

# Initial connection attempt
if not connect_bluetooth():
    print("Make sure your HC-05 is paired and connected")
    print("You can try: sudo rfcomm bind 0 <HC-05_MAC_ADDRESS>")
    print("Will attempt to reconnect automatically...")

print("Waiting for sensor data from Arduino...")
print("Data format: weatherTemp,waterTemp,weatherHum,soilMoist,waterLevel,fanState,pumpState")
print("Legacy format: weatherTemp,waterTemp,weatherHum,soilMoist,waterLevel")

# Connection monitoring variables
last_data_time = time.time()
reconnect_attempts = 0
max_reconnect_attempts = 5

while True:
    try:
        # Check if we have a valid connection
        if ser is None or not ser.is_open:
            print("No active Bluetooth connection")
            if reconnect_attempts < max_reconnect_attempts:
                if reconnect_bluetooth():
                    reconnect_attempts = 0
                    print("Successfully reconnected to Bluetooth")
                else:
                    reconnect_attempts += 1
                    print(f"Reconnection attempt {reconnect_attempts}/{max_reconnect_attempts} failed")
                    time.sleep(5)
                    continue
            else:
                print("Max reconnection attempts reached. Waiting before trying again...")
                time.sleep(30)
                reconnect_attempts = 0
                continue
        
        # Check for commands from web server
        check_for_commands()
        
        # Try to read data
        data = ser.readline().decode().strip()
        if data:
            last_data_time = time.time()
            reconnect_attempts = 0  # Reset counter on successful data
            print(f"Received: {data}")
            
            # Parse the sensor data
            sensor_data = parse_sensor_data(data)
            if sensor_data:
                print(f"Parsed data: {sensor_data}")
                
                # Send to WebSocket server
                send_to_websocket(sensor_data)
            else:
                print("Failed to parse sensor data")
        else:
            # No data received, check if connection is still alive
            if time.time() - last_data_time > 10:  # 10 seconds without data
                print("No data received for 10 seconds, checking connection...")
                if ser and ser.is_open:
                    try:
                        # Try to write something to test connection
                        ser.write(b"test\n")
                        ser.flush()
                    except:
                        print("Connection appears to be lost")
                        ser.close()
                        ser = None
                
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        if ser:
            ser.close()
            ser = None
        time.sleep(2)
    except KeyboardInterrupt:
        print("Stopping receiver...")
        break
    except Exception as e:
        print(f"Unexpected error: {e}")
        time.sleep(1)

if ser and ser.is_open:
    ser.close()
    print("Serial connection closed")

