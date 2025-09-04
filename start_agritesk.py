#!/usr/bin/env python3
"""
AgriTesk System Startup Script
Automatically starts all components of the agricultural monitoring system
"""

import subprocess
import time
import sys
import os
import signal
import threading
import requests
from pathlib import Path

class AgriTeskLauncher:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def log(self, message, level="INFO"):
        """Print formatted log messages"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def check_dependencies(self):
        """Check if required Python packages are installed"""
        self.log("Checking dependencies...")
        required_packages = [
            'pyserial', 'websockets', 'aiohttp', 'aiohttp_cors', 'requests'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            self.log(f"Missing packages: {', '.join(missing_packages)}", "ERROR")
            self.log("Installing missing packages...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install"] + missing_packages, 
                             check=True, capture_output=True)
                self.log("Dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                self.log(f"Failed to install dependencies: {e}", "ERROR")
                return False
        else:
            self.log("All dependencies are available")
        
        return True
    
    def check_bluetooth_connection(self):
        """Check if Bluetooth device is available"""
        self.log("Checking Bluetooth connection...")
        try:
            # Check if rfcomm0 exists
            if os.path.exists("/dev/rfcomm0"):
                self.log("Bluetooth device /dev/rfcomm0 found")
                self.log("Ready to receive sensor data from Arduino", "INFO")
                self.log("Expected data format: weatherTemp,waterTemp,humidity,soilMoist,waterLevel,fanState,pumpState", "INFO")
                return True
            else:
                self.log("Bluetooth device /dev/rfcomm0 not found", "WARNING")
                self.log("Make sure to pair your HC-05 module first:", "INFO")
                self.log("  sudo rfcomm bind 0 <HC-05_MAC_ADDRESS>", "INFO")
                self.log("Upload sensor_bluetooth.ino to your Arduino", "INFO")
                self.log("The system will attempt to reconnect automatically", "INFO")
                return False
        except Exception as e:
            self.log(f"Error checking Bluetooth: {e}", "ERROR")
            return False
    
    def setup_bluetooth_auto_bind(self):
        """Try to automatically bind the HC-05 if not already bound"""
        self.log("Attempting to setup Bluetooth auto-bind...")
        try:
            # Try to find and bind HC-05 automatically
            result = subprocess.run(["hcitool", "scan"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'HC-05' in line or 'HC05' in line:
                        # Extract MAC address
                        parts = line.split()
                        if len(parts) >= 2:
                            mac_address = parts[1]
                            self.log(f"Found HC-05 with MAC: {mac_address}")
                            
                            # Try to bind it
                            bind_result = subprocess.run(
                                ["sudo", "rfcomm", "bind", "0", mac_address],
                                capture_output=True, text=True
                            )
                            if bind_result.returncode == 0:
                                self.log("Successfully bound HC-05 to rfcomm0")
                                time.sleep(2)  # Wait for device to be ready
                                return True
                            else:
                                self.log(f"Failed to bind HC-05: {bind_result.stderr}", "WARNING")
            
            self.log("Could not automatically bind HC-05", "WARNING")
            return False
        except Exception as e:
            self.log(f"Error in auto-bind setup: {e}", "WARNING")
            return False
    
    def start_websocket_server(self):
        """Start the WebSocket server"""
        self.log("Starting WebSocket server...")
        try:
            process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes.append(("WebSocket Server", process))
            
            # Wait a moment for server to start
            time.sleep(3)
            
            # Check if server is running
            try:
                response = requests.get("http://127.0.0.1:8000/", timeout=5)
                if response.status_code == 200:
                    self.log("WebSocket server started successfully")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            self.log("WebSocket server may not have started properly", "WARNING")
            return True
            
        except Exception as e:
            self.log(f"Failed to start WebSocket server: {e}", "ERROR")
            return False
    
    def start_data_receiver(self):
        """Start the data receiver"""
        self.log("Starting data receiver...")
        try:
            process = subprocess.Popen(
                [sys.executable, "receive.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes.append(("Data Receiver", process))
            self.log("Data receiver started")
            return True
        except Exception as e:
            self.log(f"Failed to start data receiver: {e}", "ERROR")
            return False
    
    def check_data_flow(self):
        """Check if data is flowing through the system"""
        self.log("Checking data flow...")
        try:
            # Wait a bit for system to stabilize
            time.sleep(5)
            
            # Try to get data from the WebSocket server
            response = requests.get("http://127.0.0.1:8000/", timeout=5)
            if response.status_code == 200:
                self.log("WebSocket server is responding", "SUCCESS")
                
                # Check if we're receiving real sensor data
                self.log("Monitor the web interface for incoming sensor data")
                self.log("Expected data includes: temperature, humidity, soil moisture, relay states")
                return True
            else:
                self.log("WebSocket server not responding properly", "WARNING")
                return False
        except Exception as e:
            self.log(f"Error checking data flow: {e}", "WARNING")
            return False
    
    def open_web_browser(self):
        """Open the web application in browser"""
        self.log("Opening web application...")
        try:
            import webbrowser
            webbrowser.open("http://127.0.0.1:8000/")
            self.log("Web application opened in browser")
        except Exception as e:
            self.log(f"Failed to open browser: {e}", "WARNING")
            self.log("Please manually open: http://127.0.0.1:8000/", "INFO")
    
    def monitor_processes(self):
        """Monitor running processes"""
        while self.running:
            for name, process in self.processes:
                if process.poll() is not None:
                    self.log(f"{name} has stopped unexpectedly", "ERROR")
                    # Try to restart the process
                    if name == "WebSocket Server":
                        self.log("Attempting to restart WebSocket server...")
                        if self.start_websocket_server():
                            self.processes.remove((name, process))
                    elif name == "Data Receiver":
                        self.log("Attempting to restart data receiver...")
                        if self.start_data_receiver():
                            self.processes.remove((name, process))
            time.sleep(5)
    
    def cleanup(self):
        """Clean up running processes"""
        self.log("Shutting down AgriTesk system...")
        self.running = False
        
        for name, process in self.processes:
            try:
                self.log(f"Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.log(f"Force killing {name}...")
                process.kill()
            except Exception as e:
                self.log(f"Error stopping {name}: {e}", "WARNING")
        
        self.log("AgriTesk system stopped")
    
    def show_arduino_setup_info(self):
        """Display Arduino setup information"""
        self.log("=== Arduino Setup Information ===", "INFO")
        self.log("1. Upload sensor_bluetooth.ino to your Arduino", "INFO")
        self.log("2. Hardware connections:", "INFO")
        self.log("   - DHT22: Pin D7", "INFO")
        self.log("   - DS18B20: Pin D6", "INFO")
        self.log("   - Soil Moisture: Pin A0", "INFO")
        self.log("   - Water Level Switch: Pin D4", "INFO")
        self.log("   - Fan Relay: Pin D8 (Active LOW)", "INFO")
        self.log("   - Pump Relay: Pin D9 (Active LOW)", "INFO")
        self.log("   - HC-05 Bluetooth: RX=D10, TX=D11", "INFO")
        self.log("   - OLED Display: I2C (SDA/SCL)", "INFO")
        self.log("3. Data will be sent every 2 seconds", "INFO")
        self.log("4. Control relays via web interface or commands", "INFO")
        self.log("=====================================", "INFO")
    
    def run(self):
        """Main execution function"""
        self.log("=== AgriTesk System Launcher ===")
        self.log("Starting agricultural monitoring system with real sensor data...")
        
        # Show Arduino setup info
        self.show_arduino_setup_info()
        
        # Check dependencies
        if not self.check_dependencies():
            return False
        
        # Check Bluetooth connection
        bluetooth_ok = self.check_bluetooth_connection()
        if not bluetooth_ok:
            self.log("Attempting to auto-bind HC-05...", "INFO")
            if self.setup_bluetooth_auto_bind():
                bluetooth_ok = True
                self.log("Bluetooth auto-bind successful", "SUCCESS")
            else:
                self.log("Continuing without Bluetooth connection...", "WARNING")
                self.log("The system will attempt to reconnect when Arduino is available", "INFO")
        
        # Start WebSocket server
        if not self.start_websocket_server():
            return False
        
        # Start data receiver
        if not self.start_data_receiver():
            return False
        
        # Check data flow
        self.check_data_flow()
        
        # Open web browser
        self.open_web_browser()
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        monitor_thread.start()
        
        self.log("=== AgriTesk System Started Successfully ===")
        self.log("Web application: http://127.0.0.1:8000/")
        self.log("Arduino code: Use sensor_bluetooth.ino for real sensor data")
        self.log("Data format: weatherTemp,waterTemp,humidity,soilMoist,waterLevel,fanState,pumpState")
        self.log("Features: Real-time sensor readings, relay control, smart recommendations")
        self.log("Press Ctrl+C to stop the system")
        
        try:
            # Keep the main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
        
        return True

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    print("\nReceived interrupt signal. Shutting down...")
    sys.exit(0)

def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check if we're in the right directory
    if not Path("main.py").exists() or not Path("receive.py").exists():
        print("ERROR: Please run this script from the AgriTesk project directory")
        print("Make sure main.py and receive.py are in the current directory")
        sys.exit(1)
    
    # Check if the new Arduino file exists
    if Path("sensor_bluetooth.ino").exists():
        print("✓ Found sensor_bluetooth.ino - Ready for real sensor data!")
    else:
        print("⚠ sensor_bluetooth.ino not found in current directory")
        print("  This file combines sensor reading with Bluetooth transmission")
        print("  Make sure to upload it to your Arduino for real sensor data")
    
    # Launch the system
    launcher = AgriTeskLauncher()
    success = launcher.run()
    
    if not success:
        print("Failed to start AgriTesk system")
        sys.exit(1)

if __name__ == "__main__":
    main()
