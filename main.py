import json
import time
import serial
import asyncio
import threading
import websockets
from serial.tools import list_ports

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

mp = {"strength": 0, "total": 0, "lost": 0, "water_level": 1}

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

ser = None
try:
    available_ports = list_ports.comports()
    if available_ports:
        arduino_port = available_ports[0].device
        ser = serial.Serial(arduino_port, baudrate=9600, timeout=1)
        print(f"connected to arduino on {arduino_port}")
    else:
        print("no serial ports found")
except serial.SerialException as e:
    print(f"failed to connect to arduino: {e}")

last = time.time()

def send_cmd(cmd):
    if ser and ser.is_open:
        ser.write(cmd.encode())
        ser.flush()
        print(f"Sent to serial: {cmd}")

def serial_reader():
    global last
    import random
    while True:
        print(mp["lost"], mp["total"])
        now = time.time()
        delta = now - last
        if delta > 0 and 138 / delta <= 100:
            mp["strength"] = 138 / delta
        if ser is None or not ser.is_open:
            time.sleep(0.2)
            continue
        try:
            raw = ser.readline()
            print(raw)
            mp["total"] += 1
            if not raw:
                mp["lost"] += 1
                continue
            text = raw.decode(errors='replace').strip()
            parse_data(text)
            # Simulate water level: randomly set to 1 (normal) or 0 (low)
            mp["water_level"] = random.choices([1, 0], weights=[0.8, 0.2])[0]
            last = now
        except serial.SerialException as e:
            print("Serial error:", e)
            break

threading.Thread(target=serial_reader, daemon=True).start()

parse_data("<12> <1> <120> <1> <123.4> <31.69> <25.3> <48> <1013.5> "
           "<-5.1,0.3,9.8> <0.0,0.0,0.1> <243> <0> <3.7>")
mp["water_level"] = 1

CLIENTS = set()

async def register(ws, path):
    CLIENTS.add(ws)
    try:
        async for msg in ws:
            send_cmd(msg)
            print("SENT")
            await ws.send(json.dumps({"status": "sent", "command": msg}))
    finally:
        CLIENTS.discard(ws)

async def broadcast():
    while True:
        if CLIENTS:
            msg = json.dumps(mp)
            closed_clients = set()
            for ws in CLIENTS:
                if not ws.closed:
                    await ws.send(msg)
                else:
                    closed_clients.add(ws)
            CLIENTS.difference_update(closed_clients)
        await asyncio.sleep(2)

async def main():
    host, port = "127.0.0.1", 8000
    server = await websockets.serve(register, host, port)
    print(f"WebSocket running on ws://{host}:{port}/")
    await broadcast()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped.")
