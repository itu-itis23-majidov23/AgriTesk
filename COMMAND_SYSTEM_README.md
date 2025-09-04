# AgriTesk Command System

This document explains how the command system works to control your Arduino relays (Fan and Pump) from the web interface via Bluetooth.

## How Commands Flow

```
Web Interface → WebSocket → main.py → Command Queue → receive.py → Bluetooth → Arduino
```

### Detailed Flow:

1. **Web Interface**: User clicks buttons to control Fan/Pump
2. **WebSocket**: Commands sent to main.py via WebSocket connection
3. **Command Queue**: main.py queues commands for Bluetooth transmission
4. **receive.py**: Polls for queued commands and sends them via Bluetooth
5. **Arduino**: Receives commands via HC-05 and controls relays

## Supported Commands

The Arduino accepts these exact commands:

- `fan on` - Turn fan ON (relay goes LOW)
- `fan off` - Turn fan OFF (relay goes HIGH)
- `pump on` - Turn pump ON (relay goes LOW)  
- `pump off` - Turn pump OFF (relay goes HIGH)
- `status` - Get current relay states

## System Components

### 1. Web Interface (`index.html`)
- **Function**: `sendCmd()` - Converts dropdown selections to Arduino commands
- **Commands sent**: Based on dropdown values (AÇIK/KAPALI → fan on/off, etc.)
- **Transport**: WebSocket to main.py

### 2. Main Server (`main.py`)
- **WebSocket Handler**: `register()` - Receives commands from web interface
- **Command Queue**: Thread-safe queue for storing commands
- **HTTP Endpoints**:
  - `GET /get_command` - Returns next command from queue
  - `POST /ack_command` - Acknowledges command execution
  - `POST /queue_command` - Direct command queueing (for testing)

### 3. Bluetooth Handler (`receive.py`)
- **Command Polling**: Checks for new commands every loop iteration
- **Bluetooth Transmission**: Sends commands to Arduino via HC-05
- **Acknowledgment**: Reports success/failure back to main.py

### 4. Arduino (`sensor_bluetooth.ino`)
- **Command Processing**: `handleBluetoothCommands()` and `processCommand()`
- **Relay Control**: Active LOW logic (LOW = ON, HIGH = OFF)
- **Response**: Sends confirmation back via Bluetooth

## Testing the Command System

### Method 1: Web Interface
1. Start the system: `python start_agritesk.py`
2. Open http://127.0.0.1:8000/
3. Use the "KOMUT MERKEZİ" panel
4. Select Fan/Pump states and click "KOMUT GÖNDER"

### Method 2: Direct API Testing
```bash
# Test command queueing
python test_commands.py
```

### Method 3: Manual Testing
```bash
# Queue a command directly
curl -X POST http://127.0.0.1:8000/queue_command \
  -H "Content-Type: application/json" \
  -d '{"command": "fan on"}'

# Check command queue
curl http://127.0.0.1:8000/get_command
```

## Troubleshooting Commands

### Commands Not Working?

1. **Check WebSocket Connection**:
   - Look for "WebSocket bağlantısı kuruldu" in browser console
   - Verify main.py is running on port 8001

2. **Check Command Queue**:
   - Commands should appear in main.py console: "Queued command: fan on"
   - Check with: `curl http://127.0.0.1:8000/get_command`

3. **Check Bluetooth Connection**:
   - receive.py should show: "Command sent to Arduino via Bluetooth: fan on"
   - Verify HC-05 is connected: `ls -la /dev/rfcomm0`

4. **Check Arduino Response**:
   - Arduino Serial Monitor should show: "Fan turned ON" (via Bluetooth)
   - OLED should update relay states immediately

### Debug Steps:

1. **Enable Verbose Logging**:
   ```bash
   # In receive.py, commands are logged when sent
   # In main.py, commands are logged when queued
   # In Arduino, responses are sent via Serial and Bluetooth
   ```

2. **Test Each Component**:
   ```bash
   # Test web interface → main.py
   # Check browser console for WebSocket messages
   
   # Test main.py → receive.py  
   python test_commands.py
   
   # Test receive.py → Arduino
   # Check receive.py console output
   
   # Test Arduino response
   # Check Arduino Serial Monitor
   ```

3. **Manual Arduino Test**:
   - Open Arduino Serial Monitor
   - Type: `fan on` (should work via USB)
   - Type commands via Bluetooth terminal

## Command Response Flow

When a command is executed:

1. **Arduino** processes command and sends response
2. **receive.py** receives response via Bluetooth
3. **Response logged** in receive.py console
4. **Web interface** shows command status in log area
5. **Next sensor data** includes updated relay states

## Real-time Feedback

- **Immediate**: Web interface shows command was sent
- **~2 seconds**: Next sensor data packet shows actual relay states
- **Smart recommendations**: Updated based on new relay states

## Example Command Session

```
[Web] User selects "Fan: AÇIK" and clicks "KOMUT GÖNDER"
[WebSocket] Command "fan on" sent to main.py
[main.py] Command queued: "fan on"
[receive.py] Received command from web server: fan on
[receive.py] Command sent to Arduino via Bluetooth: fan on
[Arduino] Fan turned ON (logged to Serial and Bluetooth)
[receive.py] Next sensor data: ...,...,...,...,1,... (fanState=1)
[Web] Recommendations updated: "🌀 Fan: AÇIK"
```

This system ensures reliable command transmission even if there are temporary connection issues, as commands are queued and retried automatically.
