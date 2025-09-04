import json
import time
import asyncio
import threading
import websockets
from aiohttp import web, web_request
import aiohttp_cors

m = (
    "packet_id",
    "team_id",
    "uptime",
    "status_flags",
    "altitude",
    "velocity",
    "temperature",
    "humidity",
    "pressure",
    "acc",
    "gyro",
    "light",
    "parachute_detached",
    "battery_voltage"
)

# Global sensor data storage
mp = {
    "strength": 85, 
    "total": 0, 
    "lost": 0, 
    "water_level": 1,
    "weatherTemp": 25.0,
    "waterTemp": 18.0,
    "weatherHum": 60.0,
    "soilMoist": 45.0,
    "fanState": 0,
    "pumpState": 0,
    "timestamp": time.time()
}

def parse_data(s):
    global mp
    s = s.split()
    f = len(s) == 14
    for i in s:
        f &= len(i) > 2 and i[0] == '<' and i[-1] == '>'
    if not f:
        return []
    s = [i[1:-1] for i in s]
    for i in range(len(m)):
        if len(s[i].split(',')) != 1:
            mp[m[i]] = [float(j) for j in s[i].split(',')]
        else:
            mp[m[i]] = float(s[i])

# Global command queue for Bluetooth communication
command_queue = []
command_lock = threading.Lock()

last = time.time()

def queue_command(cmd):
    """Add command to queue for Bluetooth transmission"""
    with command_lock:
        command_queue.append(cmd)
        print(f"Queued command: {cmd}")

# Serial reader is no longer needed - data comes via Bluetooth through receive.py

parse_data("<12> <1> <120> <1> <123.4> <31.69> <25.3> <48> <1013.5> "
           "<-5.1,0.3,9.8> <0.0,0.0,0.1> <243> <0> <3.7>")
mp["water_level"] = 1

CLIENTS = set()

async def register(ws, path):
    CLIENTS.add(ws)
    print(f"Client connected. Total clients: {len(CLIENTS)}")
    try:
        async for msg in ws:
            print(f"Received command from web client: {msg}")
            
            # Queue command for Bluetooth transmission via receive.py
            queue_command(msg)
            
            # Send acknowledgment back to web client
            await ws.send(json.dumps({"status": "queued", "command": msg}))
    finally:
        CLIENTS.discard(ws)
        print(f"Client disconnected. Total clients: {len(CLIENTS)}")

async def broadcast():
    while True:
        if CLIENTS:
            msg = json.dumps(mp)
            closed_clients = set()
            for ws in CLIENTS:
                if not ws.closed:
                    try:
                        await ws.send(msg)
                    except websockets.exceptions.ConnectionClosed:
                        closed_clients.add(ws)
                else:
                    closed_clients.add(ws)
            CLIENTS.difference_update(closed_clients)
        await asyncio.sleep(1)  # Broadcast every second

# HTTP endpoint to receive sensor data from receive.py
async def handle_sensor_data(request):
    global mp
    try:
        data = await request.json()
        print(f"Received sensor data: {data}")
        
        # Update global sensor data
        mp.update({
            "weatherTemp": data.get("weatherTemp", mp["weatherTemp"]),
            "waterTemp": data.get("waterTemp", mp["waterTemp"]),
            "weatherHum": data.get("weatherHum", mp["weatherHum"]),
            "soilMoist": data.get("soilMoist", mp["soilMoist"]),
            "water_level": data.get("waterLevel", mp["water_level"]),
            "fanState": data.get("fanState", mp["fanState"]),
            "pumpState": data.get("pumpState", mp["pumpState"]),
            "timestamp": data.get("timestamp", time.time()),
            "total": mp["total"] + 1
        })
        
        return web.json_response({"status": "success", "message": "Data received"})
    except Exception as e:
        print(f"Error handling sensor data: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=400)

# HTTP endpoint to get commands for Bluetooth transmission
async def handle_get_command(request):
    """Get the next command from the queue"""
    with command_lock:
        if command_queue:
            command = command_queue.pop(0)
            return web.json_response({"command": command})
        else:
            return web.json_response({"command": None})

# HTTP endpoint to acknowledge command execution
async def handle_ack_command(request):
    """Acknowledge command execution"""
    try:
        data = await request.json()
        command = data.get("command")
        success = data.get("success", False)
        print(f"Command '{command}' {'executed successfully' if success else 'failed'}")
        return web.json_response({"status": "acknowledged"})
    except Exception as e:
        print(f"Error handling command acknowledgment: {e}")
        return web.json_response({"status": "error"}, status=400)

# HTTP endpoint to queue commands directly (for testing)
async def handle_queue_command(request):
    """Queue a command for Bluetooth transmission"""
    try:
        data = await request.json()
        command = data.get("command")
        if command:
            queue_command(command)
            return web.json_response({"status": "queued", "command": command})
        else:
            return web.json_response({"status": "error", "message": "No command provided"}, status=400)
    except Exception as e:
        print(f"Error queueing command: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=400)

# HTTP endpoint to serve the web application
async def handle_index(request):
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            content = f.read()
        return web.Response(text=content, content_type="text/html")
    except FileNotFoundError:
        return web.Response(text="index.html not found", status=404)

async def main():
    # Create aiohttp app for HTTP endpoints
    app = web.Application()
    
    # Add CORS support
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Add routes
    app.router.add_post("/sensor_data", handle_sensor_data)
    app.router.add_get("/get_command", handle_get_command)
    app.router.add_post("/ack_command", handle_ack_command)
    app.router.add_post("/queue_command", handle_queue_command)
    app.router.add_get("/", handle_index)
    
    # Add CORS to all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    # Start HTTP server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8000)
    await site.start()
    
    # Start WebSocket server
    host, port = "127.0.0.1", 8001
    ws_server = await websockets.serve(register, host, port)
    print(f"HTTP server running on http://{host}:8000/")
    print(f"WebSocket server running on ws://{host}:{port}/")
    
    # Start broadcasting
    await broadcast()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped.")
