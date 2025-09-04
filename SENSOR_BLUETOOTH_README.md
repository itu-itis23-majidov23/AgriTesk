# AgriTesk Sensor Bluetooth System

This document explains how to use the new `sensor_bluetooth.ino` code that combines real sensor reading with Bluetooth data transmission.

## What's New

The new `sensor_bluetooth.ino` file combines the functionality of:
- `sensor_read.ino` - reads real sensors (DHT22, DS18B20, soil moisture, water level)
- `sender.ino` - sends data via Bluetooth to your computer

## Hardware Setup

Make sure your Arduino is connected with:
- **DHT22**: Pin D7
- **DS18B20**: Pin D6  
- **Soil Moisture Sensor**: Pin A0
- **Water Level Switch**: Pin D4 (INPUT_PULLUP)
- **Fan Relay**: Pin D8 (Active LOW)
- **Pump Relay**: Pin D9 (Active LOW)
- **HC-05 Bluetooth**: RX=Pin D10, TX=Pin D11
- **OLED Display**: I2C (SDA/SCL)

## Data Format

The Arduino now sends data in this format via Bluetooth:
```
weatherTemp,waterTemp,humidity,soilMoist,waterLevel,fanState,pumpState
```

Example:
```
25.4,18.7,62.3,45,1,0,1
```

This means:
- Weather Temperature: 25.4°C
- Water Temperature: 18.7°C  
- Humidity: 62.3%
- Soil Moisture: 45%
- Water Level: 1 (FULL), 0 (EMPTY)
- Fan State: 0 (OFF), 1 (ON)
- Pump State: 1 (ON), 0 (OFF)

## How to Use

### 1. Upload Arduino Code
1. Upload `sensor_bluetooth.ino` to your Arduino
2. Make sure all sensors are connected properly
3. The OLED will show sensor readings locally
4. Data will be transmitted via Bluetooth every 2 seconds

### 2. Run the Receiver
```bash
python receive.py
```
This will:
- Connect to HC-05 via `/dev/rfcomm0`
- Parse incoming sensor data
- Send data to the web application

### 3. Run the Web Application
```bash
python main.py
```
Then open: http://127.0.0.1:8000/

### 4. View Real-Time Data
The web interface now shows:
- **Real sensor readings** from your Arduino
- **Current relay states** (Fan ON/OFF, Pump ON/OFF)
- **Smart recommendations** based on actual conditions
- **Remote control** of relays via web interface

## Commands

You can control relays through:

### Via Serial Monitor:
- `fan on` - Turn fan ON
- `fan off` - Turn fan OFF  
- `pump on` - Turn pump ON
- `pump off` - Turn pump OFF
- `status` - Get current relay states

### Via Web Interface:
- Use the "KOMUT MERKEZİ" panel to send commands
- Commands are sent via WebSocket to Arduino

### Via Bluetooth:
- Send same commands as serial (fan on/off, pump on/off, status)

## Troubleshooting

### Bluetooth Connection Issues:
```bash
# Check if HC-05 is paired
bluetoothctl

# Bind HC-05 to rfcomm0 (replace MAC with your HC-05 address)
sudo rfcomm bind 0 XX:XX:XX:XX:XX:XX

# Check connection
ls -la /dev/rfcomm0
```

### Sensor Reading Issues:
- Check wiring connections
- Monitor Serial output for error messages
- Verify sensor power supply (3.3V or 5V as needed)

### Web Interface Issues:
- Make sure both `main.py` and `receive.py` are running
- Check browser console for WebSocket connection errors
- Verify ports 8000 and 8001 are not blocked

## File Overview

- **sensor_bluetooth.ino** - New combined Arduino code
- **receive.py** - Updated to handle new data format with relay states
- **main.py** - Updated to store and broadcast relay states
- **index.html** - Updated to display relay states and smart recommendations

## Smart Recommendations

The system now provides intelligent recommendations based on:
- Current sensor readings
- Relay states (what's currently running)
- Time of day
- Weather conditions
- Water level status

Examples:
- "⚠️ Pompa kapalı - sulama başlatılmalı!" (when soil is dry but pump is off)
- "🌡️ Sıcak hava: Fan çalıştırılmalı" (when temperature is high but fan is off)
- "⚠️ DİKKAT: Su seviyesi düşük ama pompa çalışıyor!" (safety warning)

Enjoy your upgraded AgriTesk system with real sensor data and intelligent monitoring!
