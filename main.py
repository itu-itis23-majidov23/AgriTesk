import json
import time
import asyncio
import threading
import websockets
from aiohttp import web, web_request
import aiohttp_cors
import google.generativeai as genai
import os

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

# Gemini AI Configuration
GEMINI_API_KEY = "AIzaSyDEOSeV6_wAhztlNSfi2a9c0WhkzY4FfyQ"
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini model
model = genai.GenerativeModel('gemini-1.5-flash')

# Agricultural context for the chatbot
AGRICULTURAL_CONTEXT = """
Sen bir tarım uzmanı asistanısın ve AgriTesk akıllı tarım sistemi için çalışıyorsun. 
Kullanıcılara tarımsal konularda yardım ediyorsun. Şu anda sisteme bağlı sensörlerden gelen veriler:

- Hava Sıcaklığı: {weatherTemp}°C
- Su Sıcaklığı: {waterTemp}°C  
- Hava Nemi: {weatherHum}%
- Toprak Nemi: {soilMoist}%
- Su Seviyesi: {water_level_text}
- Fan Durumu: {fan_status}
- Pompa Durumu: {pump_status}

Türkçe cevap ver ve tarımsal önerilerde bulun. Sensör verilerini dikkate alarak öneriler yap.
Kısa ve net cevaplar ver. Emoji kullanarak cevaplarını daha anlaşılır hale getir.
"""

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

# Automatic control settings
AUTO_CONTROL_ENABLED = True
HUMIDITY_THRESHOLD = 56.0  # Turn on fan when humidity > 56%
last_auto_fan_state = None  # Track last automatic fan state to avoid spam

last = time.time()

def queue_command(cmd):
    """Add command to queue for Bluetooth transmission"""
    with command_lock:
        command_queue.append(cmd)
        print(f"Queued command: {cmd}")

def check_automatic_controls():
    """Check sensor values and apply automatic controls"""
    global last_auto_fan_state
    
    if not AUTO_CONTROL_ENABLED:
        return
    
    current_humidity = mp.get("weatherHum", 0)
    current_fan_state = mp.get("fanState", 0)
    
    # Automatic fan control based on humidity
    should_fan_be_on = current_humidity > HUMIDITY_THRESHOLD
    
    # Only change fan state if needed and different from last automatic action
    if should_fan_be_on and current_fan_state == 0 and last_auto_fan_state != 1:
        queue_command('fan on')
        mp['fanState'] = 1
        last_auto_fan_state = 1
        notification_message = f"🤖 Hava nemi %{current_humidity:.1f} olduğu için fanı açtım. Yüksek nem fungal hastalık riskini artırır. 🌀💨"
        print(f"🌀 AUTO: Fan turned ON - Humidity: {current_humidity:.1f}% > {HUMIDITY_THRESHOLD}%")
        # Send notification to all connected clients
        asyncio.create_task(send_auto_notification(notification_message))
        
    elif not should_fan_be_on and current_fan_state == 1 and last_auto_fan_state != 0:
        # Only turn off automatically if humidity drops significantly (hysteresis)
        if current_humidity < (HUMIDITY_THRESHOLD - 5):  # 5% hysteresis to prevent oscillation
            queue_command('fan off')
            mp['fanState'] = 0
            last_auto_fan_state = 0
            notification_message = f"🤖 Hava nemi %{current_humidity:.1f} seviyesine düştü, fanı kapattım. Artık havalandırma gerekmiyor. 🌀✅"
            print(f"🌀 AUTO: Fan turned OFF - Humidity: {current_humidity:.1f}% < {HUMIDITY_THRESHOLD - 5}%")
            # Send notification to all connected clients
            asyncio.create_task(send_auto_notification(notification_message))

async def send_auto_notification(message):
    """Send automatic control notifications to all connected chatbot clients"""
    import json
    
    # Create notification data
    notification_data = {
        "type": "auto_notification",
        "message": message,
        "timestamp": time.time()
    }
    
    print(f"📢 Sending auto notification: {message}")
    
    # Send to all WebSocket clients
    if CLIENTS:
        clients_copy = CLIENTS.copy()
        closed_clients = set()
        for ws in clients_copy:
            if not ws.closed:
                try:
                    await ws.send(json.dumps(notification_data))
                    print(f"✅ Notification sent to client")
                except Exception as e:
                    print(f"❌ Failed to send notification to client: {e}")
                    closed_clients.add(ws)
            else:
                closed_clients.add(ws)
        
        # Remove closed clients
        CLIENTS.difference_update(closed_clients)

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
        # Check automatic controls periodically
        check_automatic_controls()
        
        if CLIENTS:
            msg = json.dumps(mp)
            closed_clients = set()
            # Create a copy of CLIENTS to avoid concurrent modification
            clients_copy = CLIENTS.copy()
            for ws in clients_copy:
                if not ws.closed:
                    try:
                        await ws.send(msg)
                    except (websockets.exceptions.ConnectionClosed, ConnectionResetError):
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
        
        # Check for automatic controls after updating sensor data
        check_automatic_controls()
        
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

# HTTP endpoint for Gemini chatbot
async def handle_chat(request):
    """Handle chat requests with Gemini AI"""
    try:
        data = await request.json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return web.json_response({"status": "error", "message": "No message provided"}, status=400)
        
        # Get current sensor data for context
        water_level_text = "Normal" if mp["water_level"] >= 1 else "Düşük"
        fan_status = "Açık" if mp["fanState"] else "Kapalı"
        pump_status = "Açık" if mp["pumpState"] else "Kapalı"
        
        # Try to get response from Gemini with retry logic
        response_text = await get_gemini_response(user_message, mp, water_level_text, fan_status, pump_status)
        
        return web.json_response({
            "status": "success", 
            "response": response_text,
            "timestamp": time.time()
        })
        
    except Exception as e:
        print(f"Error in chatbot: {e}")
        return web.json_response({
            "status": "error", 
            "message": "Üzgünüm, şu anda yanıt veremiyorum. Lütfen daha sonra tekrar deneyin.",
            "error": str(e)
        }, status=500)

async def handle_test_notification(request):
    """Test endpoint to send a notification to all clients"""
    try:
        test_message = "🧪 Test Bildirimi: Bu bir test bildirimidir. Sistem çalışıyor! ✅"
        await send_auto_notification(test_message)
        return web.json_response({
            "status": "success", 
            "message": "Test notification sent",
            "clients_count": len(CLIENTS)
        })
    except Exception as e:
        print(f"Error sending test notification: {e}")
        return web.json_response({
            "status": "error", 
            "message": str(e)
        }, status=500)

async def get_gemini_response(user_message, sensor_data, water_level_text, fan_status, pump_status):
    """Get response from Gemini with retry logic and fallback"""
    
    message_lower = user_message.lower()
    
    # Check for control commands first - handle these immediately without Gemini
    # Control commands - Fan ON
    if any(phrase in message_lower for phrase in ['fan aç', 'fanı aç', 'fan çalıştır', 'fanı çalıştır', 'fan on']):
        queue_command('fan on')
        # Update global state immediately for UI feedback
        mp['fanState'] = 1
        return f"🌀 Fan açılıyor... Havalandırma başlatıldı! Mevcut hava sıcaklığı: {sensor_data['weatherTemp']:.1f}°C 💨"
    
    # Control commands - Fan OFF
    elif any(phrase in message_lower for phrase in ['fan kapat', 'fanı kapat', 'fan durdur', 'fanı durdur', 'fan off']):
        queue_command('fan off')
        # Update global state immediately for UI feedback
        mp['fanState'] = 0
        return f"🌀 Fan kapatılıyor... Havalandırma durduruldu. 🔄"
    
    # Control commands - Pump ON
    elif any(phrase in message_lower for phrase in ['pompa aç', 'pompayı aç', 'pompa çalıştır', 'pompayı çalıştır', 'pump on', 'sulama başlat', 'sulamayı başlat']):
        if sensor_data.get('water_level', 1) < 1:
            return f"⚠️ Su seviyesi düşük! Pompa çalıştırılamaz. Önce su deposunu doldurun. 💧"
        queue_command('pump on')
        # Update global state immediately for UI feedback
        mp['pumpState'] = 1
        return f"💧 Su pompası açılıyor... Sulama başlatıldı! Toprak nemi: {sensor_data['soilMoist']:.1f}% 🌱"
    
    # Control commands - Pump OFF
    elif any(phrase in message_lower for phrase in ['pompa kapat', 'pompayı kapat', 'pompa durdur', 'pompayı durdur', 'pump off', 'sulama durdur', 'sulamayı durdur']):
        queue_command('pump off')
        # Update global state immediately for UI feedback
        mp['pumpState'] = 0
        return f"💧 Su pompası kapatılıyor... Sulama durduruldu. Toprak nemi: {sensor_data['soilMoist']:.1f}% 🌿"
    
    # If not a control command, try Gemini for other questions
    try:
        # Configure generation settings for faster response
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=200,  # Shorter responses
            top_p=0.8,
            top_k=40
        )
        
        # Format context with current sensor data
        context = AGRICULTURAL_CONTEXT.format(
            weatherTemp=sensor_data["weatherTemp"],
            waterTemp=sensor_data["waterTemp"],
            weatherHum=sensor_data["weatherHum"],
            soilMoist=sensor_data["soilMoist"],
            water_level_text=water_level_text,
            fan_status=fan_status,
            pump_status=pump_status
        )
        
        # Add control command information to context
        enhanced_context = context + """

Ayrıca kullanıcı şu komutlarla cihazları kontrol edebilir:
- Fan kontrolü: 'Fan aç', 'Fan kapat'  
- Pompa kontrolü: 'Pompa aç', 'Pompa kapat', 'Sulama başlat', 'Sulama durdur'

Eğer kullanıcı kontrol komutu verirse, bunu belirt ve nasıl yapacağını açıkla."""
        
        # Combine context with user message
        full_prompt = f"{enhanced_context}\n\nKullanıcı sorusu: {user_message}"
        
        # Try with timeout
        import asyncio
        response = await asyncio.wait_for(
            asyncio.to_thread(model.generate_content, full_prompt, generation_config=generation_config),
            timeout=10.0  # 10 second timeout
        )
        
        if response and response.text:
            return response.text
        else:
            raise Exception("Empty response from Gemini")
            
    except asyncio.TimeoutError:
        print("Gemini API timeout, using fallback response")
        return get_fallback_response(user_message, sensor_data, water_level_text, fan_status, pump_status)
    except Exception as e:
        print(f"Gemini API error: {e}")
        return get_fallback_response(user_message, sensor_data, water_level_text, fan_status, pump_status)

def get_fallback_response(user_message, sensor_data, water_level_text, fan_status, pump_status):
    """Generate fallback response when Gemini is unavailable"""
    
    message_lower = user_message.lower()
    
    # Control commands - Fan ON
    if any(phrase in message_lower for phrase in ['fan aç', 'fanı aç', 'fan çalıştır', 'fanı çalıştır', 'fan on']):
        queue_command('fan on')
        # Update global state immediately for UI feedback
        mp['fanState'] = 1
        return f"🌀 Fan açılıyor... Havalandırma başlatıldı! Mevcut hava sıcaklığı: {sensor_data['weatherTemp']:.1f}°C 💨"
    
    # Control commands - Fan OFF
    elif any(phrase in message_lower for phrase in ['fan kapat', 'fanı kapat', 'fan durdur', 'fanı durdur', 'fan off']):
        queue_command('fan off')
        # Update global state immediately for UI feedback
        mp['fanState'] = 0
        return f"🌀 Fan kapatılıyor... Havalandırma durduruldu. 🔄"
    
    # Control commands - Pump ON
    elif any(phrase in message_lower for phrase in ['pompa aç', 'pompayı aç', 'pompa çalıştır', 'pompayı çalıştır', 'pump on', 'sulama başlat', 'sulamayı başlat']):
        if sensor_data.get('water_level', 1) < 1:
            return f"⚠️ Su seviyesi düşük! Pompa çalıştırılamaz. Önce su deposunu doldurun. 💧"
        queue_command('pump on')
        # Update global state immediately for UI feedback
        mp['pumpState'] = 1
        return f"💧 Su pompası açılıyor... Sulama başlatıldı! Toprak nemi: {sensor_data['soilMoist']:.1f}% 🌱"
    
    # Control commands - Pump OFF
    elif any(phrase in message_lower for phrase in ['pompa kapat', 'pompayı kapat', 'pompa durdur', 'pompayı durdur', 'pump off', 'sulama durdur', 'sulamayı durdur']):
        queue_command('pump off')
        # Update global state immediately for UI feedback
        mp['pumpState'] = 0
        return f"💧 Su pompası kapatılıyor... Sulama durduruldu. Toprak nemi: {sensor_data['soilMoist']:.1f}% 🌿"
    
    # Soil moisture related questions
    elif any(word in message_lower for word in ['toprak', 'nem', 'sulama', 'su']):
        soil_moisture = sensor_data["soilMoist"]
        if soil_moisture < 30:
            return f"🌱 Toprak nemi düşük ({soil_moisture:.1f}%). Acil sulama gerekli! 💧 'Pompa aç' diyerek sulamayı başlatabilirsiniz."
        elif soil_moisture < 40:
            return f"🌿 Toprak nemi orta seviyede ({soil_moisture:.1f}%). Sulama düşünülebilir. 'Pompa aç' komutuyla sulamayı başlatabilirsiniz. 💦"
        else:
            return f"✅ Toprak nemi iyi durumda ({soil_moisture:.1f}%). Şu an sulama gerekmiyor. 🌱"
    
    # Temperature related questions
    elif any(word in message_lower for word in ['sıcaklık', 'sicak', 'soğuk', 'ısı']):
        air_temp = sensor_data["weatherTemp"]
        water_temp = sensor_data["waterTemp"]
        if air_temp > 30:
            return f"🌡️ Hava sıcaklığı yüksek ({air_temp:.1f}°C)! 'Fan aç' diyerek havalandırmayı başlatın ve sulama sıklığını artırın. 🌀💧"
        elif air_temp < 15:
            return f"❄️ Hava sıcaklığı düşük ({air_temp:.1f}°C). Bitkileri soğuktan koruyun. 🛡️"
        else:
            return f"🌡️ Hava sıcaklığı normal ({air_temp:.1f}°C). Su sıcaklığı: {water_temp:.1f}°C. 👍"
    
    # Humidity related questions
    elif any(word in message_lower for word in ['nem', 'hava', 'rutubet']):
        humidity = sensor_data["weatherHum"]
        auto_status = "🤖 Otomatik kontrol aktif" if AUTO_CONTROL_ENABLED else "📱 Manuel kontrol"
        
        if humidity < 40:
            return f"🏜️ Hava nemi düşük ({humidity:.1f}%)! Nem artırıcı önlemler alın. 'Pompa aç' ile sulama yapabilirsiniz. 💨\n{auto_status}: Fan {HUMIDITY_THRESHOLD}% üzerinde otomatik açılır."
        elif humidity > HUMIDITY_THRESHOLD:
            return f"💨 Hava nemi yüksek ({humidity:.1f}%)! Fan otomatik olarak çalışmalı. Fungal hastalık riski var. 🌬️\n{auto_status}: {HUMIDITY_THRESHOLD}% üzerinde fan otomatik açılır."
        else:
            return f"🌬️ Hava nemi normal ({humidity:.1f}%). Bitkiler için uygun koşullar. ✅\n{auto_status}: Fan {HUMIDITY_THRESHOLD}% üzerinde otomatik açılır."
    
    # Fan related questions
    elif any(word in message_lower for word in ['fan', 'havalandırma', 'rüzgar']):
        return f"🌀 Fan şu anda {fan_status.lower()}. 'Fan aç' veya 'Fan kapat' diyerek kontrol edebilirsiniz. 💨"
    
    # Pump related questions
    elif any(word in message_lower for word in ['pompa', 'pump']):
        return f"💧 Su pompası şu anda {pump_status.lower()}. Su seviyesi: {water_level_text}. 'Pompa aç' veya 'Pompa kapat' diyerek kontrol edebilirsiniz. Toprak nemi: {sensor_data['soilMoist']:.1f}% 🌱"
    
    # General system status
    elif any(word in message_lower for word in ['durum', 'sistem', 'nasıl', 'merhaba', 'selam']):
        auto_status = "🤖 AKTIF" if AUTO_CONTROL_ENABLED else "📱 KAPALI"
        humidity = sensor_data['weatherHum']
        return f"""🌱 **Sistem Durumu:**
• Hava Sıcaklığı: {sensor_data['weatherTemp']:.1f}°C 🌡️
• Su Sıcaklığı: {sensor_data['waterTemp']:.1f}°C 💧
• Hava Nemi: {humidity:.1f}% 🌬️
• Toprak Nemi: {sensor_data['soilMoist']:.1f}% 🌿
• Su Seviyesi: {water_level_text} 💦
• Fan: {fan_status} 🌀
• Pompa: {pump_status} ⚡

**Otomatik Kontrol: {auto_status}**
• Fan otomatik açılma: >{HUMIDITY_THRESHOLD}% nem
• Mevcut nem: {humidity:.1f}% {"(Otomatik fan aktif olmalı!)" if humidity > HUMIDITY_THRESHOLD else "(Normal)"}

**Manuel Kontrol Komutları:**
• 'Fan aç' / 'Fan kapat' 🌀
• 'Pompa aç' / 'Pompa kapat' 💧

Başka sorularınız varsa sormaktan çekinmeyin! 😊"""
    
    # Default response
    else:
        return f"""🤖 Merhaba! Ben AgriTesk tarım uzmanı asistanınızım. 
        
**Şu anda sensör verileriniz:**
• Toprak Nemi: {sensor_data['soilMoist']:.1f}% 
• Hava Sıcaklığı: {sensor_data['weatherTemp']:.1f}°C
• Hava Nemi: {sensor_data['weatherHum']:.1f}%

**Kontrol komutları:**
• 'Fan aç' / 'Fan kapat' 🌀
• 'Pompa aç' / 'Pompa kapat' 💧

Size nasıl yardımcı olabilirim? 🌱"""

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
    app.router.add_post("/chat", handle_chat)
    app.router.add_post("/test_notification", handle_test_notification)
    app.router.add_get("/", handle_index)
    
    # Add CORS to all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    # Start HTTP server - Listen on all interfaces (0.0.0.0)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()
    
    # Start WebSocket server - Listen on all interfaces
    host, port = "0.0.0.0", 8001
    ws_server = await websockets.serve(register, host, port)
    
    # Get local IP address for display
    import socket
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
    except:
        local_ip = "localhost"
    
    print(f"🌐 HTTP server running on:")
    print(f"   Local:    http://127.0.0.1:8000/")
    print(f"   Network:  http://{local_ip}:8000/")
    print(f"🔗 WebSocket server running on ws://{local_ip}:{port}/")
    print(f"📱 Other devices can access via: http://{local_ip}:8000/")
    
    # Start broadcasting
    await broadcast()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped.")
