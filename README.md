# 🌱 AgriTesk - Agricultural Monitoring System

A complete IoT solution for real-time agricultural monitoring using Arduino, Bluetooth, and web technologies.

## 🎯 Features

- **Real-time sensor monitoring**: Temperature, humidity, soil moisture, water level
- **Live dashboard**: Beautiful web interface with charts and recommendations
- **Bluetooth communication**: Wireless data transmission from Arduino to computer
- **Smart recommendations**: AI-powered suggestions based on sensor readings
- **Data logging**: Automatic recording of sensor data
- **One-click startup**: Automated system launcher

## 🏗️ System Architecture

```
Arduino Uno + HC-05 → Bluetooth → Python Receiver → WebSocket Server → Web Dashboard
```

## 📋 Prerequisites

### Hardware
- Arduino Uno
- HC-05 Bluetooth module
- DHT22 temperature and humidity sensor
- DS18B20 waterproof temperature sensor
- Soil moisture sensor (analog)
- Water level switch
- Relay modules (for fan and pump control)
- OLED display (SH1106)
- Jumper wires
- Breadboard (optional)

### Software
- Python 3.7+
- Arduino IDE
- Bluetooth support on your computer

## 🚀 Quick Start

### Option 1: Automated Startup (Recommended)

**For Linux/Mac:**
```bash
./start_agritesk.sh
```

**For Windows:**
```cmd
start_agritesk.bat
```

**For Python (Cross-platform):**
```bash
python start_agritesk.py
```

### Option 2: Manual Startup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Upload Arduino code:**
   - Open `sensor_read.ino` in Arduino IDE
   - Install required libraries: DHT sensor library, OneWire, DallasTemperature, U8g2
   - Upload to your Arduino Uno
   - Connect sensors and HC-05 according to the pin definitions in the code

3. **Pair Bluetooth:**
   ```bash
   # Find your HC-05 MAC address
   hcitool scan
   
   # Bind the device (replace XX:XX:XX with your MAC)
   sudo rfcomm bind 0 XX:XX:XX:XX:XX:XX
   ```

4. **Start the system:**
   ```bash
   # Terminal 1: Start WebSocket server
   python main.py
   
   # Terminal 2: Start data receiver
   python receive.py
   ```

5. **Open web application:**
   - Navigate to `http://127.0.0.1:8000/`

## 📁 Project Structure

```
AgriTesk/
├── sender.ino              # Arduino code for sensor simulation
├── receive.py              # Bluetooth data receiver
├── main.py                 # WebSocket server and web app
├── index.html              # Web dashboard interface
├── start_agritesk.py       # Python automation script
├── start_agritesk.sh       # Linux/Mac automation script
├── start_agritesk.bat      # Windows automation script
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🔧 Configuration

### Arduino Configuration
- **Baud Rate**: 9600
- **Bluetooth Pins**: 10 (RX), 11 (TX)
- **Update Frequency**: 2 seconds

### WebSocket Server
- **HTTP Port**: 8000
- **WebSocket Port**: 8001
- **CORS**: Enabled for all origins

### Data Format
Arduino sends comma-separated values:
```
weatherTemp,waterTemp,weatherHum,soilMoist,waterLevel
```

Example: `25.3,18.7,60.1,45.8,1`

### Sensor Mapping
- **weatherTemp**: DHT22 air temperature sensor
- **waterTemp**: DS18B20 waterproof temperature sensor
- **weatherHum**: DHT22 humidity sensor
- **soilMoist**: Analog soil moisture sensor (0-100%)
- **waterLevel**: Digital water level switch (1=FULL, 0=EMPTY)

### Control Commands
The web application can send commands to control:
- **Fan**: `fan on` / `fan off`
- **Pump**: `pump on` / `pump off`
- **Status**: `status` (returns current device states)

## 📊 Web Dashboard Features

### Real-time Metrics
- **Air Temperature**: Current and historical data
- **Water Temperature**: Irrigation water monitoring
- **Air Humidity**: Environmental humidity tracking
- **Soil Moisture**: Ground moisture levels

### Smart Recommendations
- **Irrigation suggestions**: Based on soil moisture and weather
- **Temperature alerts**: High/low temperature warnings
- **Water level monitoring**: Tank level notifications
- **Optimal timing**: Best times for watering

### Data Visualization
- **Live charts**: Real-time sensor data graphs
- **Historical trends**: Long-term data analysis
- **System status**: Connection and health monitoring

## 🛠️ Troubleshooting

### Common Issues

**Arduino Disconnect/Reconnect Issue:**
The system now automatically handles Arduino disconnections and reconnections:
- **Automatic reconnection**: The receiver will attempt to reconnect every 5 seconds
- **Connection monitoring**: Detects when data stops flowing and reconnects
- **Auto-bind**: Startup scripts can automatically find and bind HC-05

**Bluetooth Connection Failed:**
```bash
# Use the Bluetooth helper script
python bluetooth_helper.py

# Or manually check if device is paired
rfcomm -a

# Rebind if necessary
sudo rfcomm release 0
sudo rfcomm bind 0 XX:XX:XX:XX:XX:XX
```

**Manual Bluetooth Management:**
```bash
# Use the helper script for easy management
python bluetooth_helper.py

# Options available:
# 1. Scan for Bluetooth devices
# 2. Find and bind HC-05 automatically
# 3. Check connection status
# 4. Unbind HC-05
```

**WebSocket Connection Failed:**
- Ensure ports 8000 and 8001 are not in use
- Check firewall settings
- Verify Python dependencies are installed

**Arduino Not Sending Data:**
- Check HC-05 connections (TX→RX, RX→TX)
- Verify baud rate is 9600
- Ensure HC-05 is in data mode (not AT mode)

**Web Application Not Loading:**
- Check if main.py is running
- Verify http://127.0.0.1:8000/ is accessible
- Check browser console for errors

### Debug Mode

Enable debug logging by modifying the scripts:
- Add `print()` statements in Python files
- Use Arduino Serial Monitor to debug Arduino code
- Check browser Developer Tools for web issues

## 🔄 System Flow

1. **Arduino** simulates sensor readings and sends via HC-05
2. **receive.py** receives Bluetooth data and parses sensor values
3. **main.py** receives data via HTTP and broadcasts via WebSocket
4. **index.html** connects to WebSocket and displays real-time data
5. **Dashboard** shows live metrics, charts, and recommendations

## 📈 Future Enhancements

- [ ] Real sensor integration (DHT22, soil moisture sensors)
- [ ] Database storage for historical data
- [ ] Mobile app development
- [ ] Cloud deployment
- [ ] Machine learning for predictive analytics
- [ ] Multi-zone monitoring support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the code comments
3. Open an issue on GitHub
4. Contact the development team

---

**Happy Farming! 🌾**
