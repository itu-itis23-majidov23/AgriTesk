#!/bin/bash

# AgriTesk System Startup Script (Shell Version)
# Automatically starts all components of the agricultural monitoring system

echo "=== AgriTesk System Launcher ==="
echo "Starting agricultural monitoring system..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[$(date +%H:%M:%S)] [SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[$(date +%H:%M:%S)] [WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[$(date +%H:%M:%S)] [ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "main.py" ] || [ ! -f "receive.py" ]; then
    print_error "Please run this script from the AgriTesk project directory"
    print_error "Make sure main.py and receive.py are in the current directory"
    exit 1
fi

# Check Python installation
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not installed or not in PATH"
    exit 1
fi

# Check if requirements.txt exists
if [ -f "requirements.txt" ]; then
    print_status "Installing/updating Python dependencies..."
    pip3 install -r requirements.txt
    if [ $? -eq 0 ]; then
        print_success "Dependencies installed successfully"
    else
        print_warning "Some dependencies may not have installed properly"
    fi
else
    print_warning "requirements.txt not found, skipping dependency installation"
fi

# Check Bluetooth connection
print_status "Checking Bluetooth connection..."
if [ -e "/dev/rfcomm0" ]; then
    print_success "Bluetooth device /dev/rfcomm0 found"
else
    print_warning "Bluetooth device /dev/rfcomm0 not found"
    print_status "Attempting to auto-bind HC-05..."
    
    # Try to find and bind HC-05 automatically
    HC05_MAC=$(hcitool scan | grep -i "HC-05\|HC05" | awk '{print $1}' | head -1)
    if [ ! -z "$HC05_MAC" ]; then
        print_status "Found HC-05 with MAC: $HC05_MAC"
        if sudo rfcomm bind 0 $HC05_MAC 2>/dev/null; then
            print_success "Successfully bound HC-05 to rfcomm0"
            sleep 2
        else
            print_warning "Failed to bind HC-05 automatically"
        fi
    else
        print_warning "Could not find HC-05 in scan results"
        print_warning "Make sure to pair your HC-05 module first:"
        print_warning "  sudo rfcomm bind 0 <HC-05_MAC_ADDRESS>"
    fi
    print_status "The system will attempt to reconnect automatically when Arduino is available"
fi

# Function to cleanup processes on exit
cleanup() {
    print_status "Shutting down AgriTesk system..."
    if [ ! -z "$WEBSOCKET_PID" ]; then
        kill $WEBSOCKET_PID 2>/dev/null
        print_status "Stopped WebSocket server"
    fi
    if [ ! -z "$RECEIVER_PID" ]; then
        kill $RECEIVER_PID 2>/dev/null
        print_status "Stopped data receiver"
    fi
    print_success "AgriTesk system stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start WebSocket server
print_status "Starting WebSocket server..."
python3 main.py &
WEBSOCKET_PID=$!

# Wait for server to start
sleep 3

# Check if server is running
if curl -s http://127.0.0.1:8000/ > /dev/null; then
    print_success "WebSocket server started successfully"
else
    print_warning "WebSocket server may not have started properly"
fi

# Start data receiver
print_status "Starting data receiver..."
python3 receive.py &
RECEIVER_PID=$!

# Wait a moment for receiver to start
sleep 2
print_success "Data receiver started"

# Open web browser
print_status "Opening web application..."
if command -v xdg-open &> /dev/null; then
    xdg-open http://127.0.0.1:8000/
elif command -v open &> /dev/null; then
    open http://127.0.0.1:8000/
else
    print_warning "Could not automatically open browser"
    print_status "Please manually open: http://127.0.0.1:8000/"
fi

print_success "=== AgriTesk System Started Successfully ==="
print_status "Web application: http://127.0.0.1:8000/"
print_status "Press Ctrl+C to stop the system"

# Wait for user interrupt
wait
