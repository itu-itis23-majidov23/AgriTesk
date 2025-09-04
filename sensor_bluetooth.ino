#include <Wire.h>
#include <U8g2lib.h>
#include "DHT.h"
#include <OneWire.h>
#include <DallasTemperature.h>
#include <SoftwareSerial.h>

// ----------------- Display (SH1106 I2C) -----------------
U8G2_SH1106_128X64_NONAME_1_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);

// ----------------- DHT22 -----------------
#define DHTPIN 7              // DHT22 on D7
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// ----------------- Soil Moisture -----------------
#define SOIL_PIN A0

// ----------------- DS18B20 -----------------
#define ONE_WIRE_BUS 6        // DS18B20 on D6
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);
DeviceAddress sensorAddress;

// ----------------- Relays (active LOW) -----------------
#define FAN_PIN 8             // Fan on D8
#define PUMP_PIN 9            // Pump on D9

// ----------------- Water Level Switch -----------------
#define LEVEL_SWITCH_PIN 4    // float/level switch on D4 (INPUT_PULLUP)

// ----------------- Bluetooth (HC-05) -----------------
#define BT_RX 10
#define BT_TX 11
SoftwareSerial BTSerial(BT_RX, BT_TX);

// ----------------- Data transmission variables -----------------
unsigned long lastTransmission = 0;
const unsigned long TRANSMISSION_INTERVAL = 2000; // Send data every 2 seconds

void setup() {
  Serial.begin(9600);
  BTSerial.begin(9600);

  pinMode(FAN_PIN, OUTPUT);
  pinMode(PUMP_PIN, OUTPUT);

  // Set relays OFF initially (active LOW logic)
  digitalWrite(FAN_PIN, HIGH);
  digitalWrite(PUMP_PIN, HIGH);

  // Level switch input (to GND when closed)
  pinMode(LEVEL_SWITCH_PIN, INPUT_PULLUP);

  dht.begin();
  sensors.begin();
  if (sensors.getDeviceCount() > 0 && sensors.getAddress(sensorAddress, 0)) {
    sensors.setResolution(sensorAddress, 12);
  }

  u8g2.begin();
  
  Serial.println("AgriTesk Sensor System Started");
  BTSerial.println("AgriTesk Sensor System Started");
}

void loop() {
  handleSerialCommands();  // check Serial input
  handleBluetoothCommands(); // check Bluetooth input

  // Read all sensors
  float humidity = dht.readHumidity();
  float tempDHT = dht.readTemperature();

  sensors.requestTemperatures();
  float tempDS = sensors.getTempCByIndex(0);

  int soilRaw = analogRead(SOIL_PIN);
  // Adjust these bounds after calibrating your sensor in air/water
  int soilPercent = map(soilRaw, 800, 400, 0, 100);
  soilPercent = constrain(soilPercent, 0, 100);

  // Relay states (active LOW)
  bool fanState = (digitalRead(FAN_PIN) == LOW);
  bool pumpState = (digitalRead(PUMP_PIN) == LOW);

  // Water level state (LOW means switch closed to GND)
  bool waterState = (digitalRead(LEVEL_SWITCH_PIN) == LOW);

  // Check if it's time to transmit data
  unsigned long currentTime = millis();
  if (currentTime - lastTransmission >= TRANSMISSION_INTERVAL) {
    transmitSensorData(tempDHT, tempDS, humidity, soilPercent, fanState, pumpState, waterState);
    lastTransmission = currentTime;
  }

  // --------- Print to Serial (for debugging) ----------
  Serial.print("DHT22 T: "); Serial.print(tempDHT); Serial.print(" H: "); Serial.println(humidity);
  Serial.print("DS18B20 T: "); Serial.println(tempDS);
  Serial.print("Soil: "); Serial.println(soilPercent);
  Serial.print("Fan: "); Serial.print(fanState ? "ON" : "OFF"); 
  Serial.print(" Pump: "); Serial.println(pumpState ? "ON" : "OFF");
  Serial.print("Water Level: "); Serial.println(waterState ? "FULL" : "EMPTY");

  // ----------------- Draw on OLED -----------------
  u8g2.firstPage();
  do {
    u8g2.setFont(u8g2_font_5x8_tr);

    u8g2.setCursor(0, 10);
    u8g2.print("DHT22: ");
    if (!isnan(tempDHT) && !isnan(humidity)) {
      u8g2.print(tempDHT, 1); u8g2.print("C ");
      u8g2.print(humidity, 1); u8g2.print("%");
    } else {
      u8g2.print("Err");
    }

    u8g2.setCursor(0, 22);
    u8g2.print("DS18B20: ");
    if (tempDS != DEVICE_DISCONNECTED_C) {
      u8g2.print(tempDS, 1); u8g2.print("C");
    } else {
      u8g2.print("Err");
    }

    u8g2.setCursor(0, 34);
    u8g2.print("Soil: "); u8g2.print(soilPercent); u8g2.print("%");

    u8g2.setCursor(0, 46);
    u8g2.print("Fan: "); u8g2.print(fanState ? "ON" : "OFF");

    u8g2.setCursor(0, 58);
    u8g2.print("Pump: "); u8g2.print(pumpState ? "ON" : "OFF");

    // Water Level line
    u8g2.setCursor(70, 58);
    u8g2.print("Water: "); u8g2.print(waterState ? "FULL" : "EMPTY");

  } while (u8g2.nextPage());

  delay(1000); // Main loop delay
}

// ================= Data Transmission =================
void transmitSensorData(float weatherTemp, float waterTemp, float humidity, int soilMoist, bool fanState, bool pumpState, bool waterLevel) {
  // Create structured JSON-like data string for transmission
  // Format: weatherTemp,waterTemp,humidity,soilMoist,waterLevel,fanState,pumpState
  String dataString = String(weatherTemp, 1) + "," + 
                     String(waterTemp, 1) + "," + 
                     String(humidity, 1) + "," + 
                     String(soilMoist) + "," + 
                     String(waterLevel ? 1 : 0) + "," +
                     String(fanState ? 1 : 0) + "," +
                     String(pumpState ? 1 : 0);
  
  // Send via Bluetooth
  BTSerial.println(dataString);
  
  // Also send a more readable format for debugging
  Serial.println("Transmitted: " + dataString);
}

// ================= Serial Command Handler =================
void handleSerialCommands() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toLowerCase();
    processCommand(command, "Serial");
  }
}

// ================= Bluetooth Command Handler =================
void handleBluetoothCommands() {
  if (BTSerial.available() > 0) {
    String command = BTSerial.readStringUntil('\n');
    command.trim();
    command.toLowerCase();
    processCommand(command, "Bluetooth");
  }
}

// ================= Command Processor =================
void processCommand(String command, String source) {
  if (command == "fan on") {
    digitalWrite(FAN_PIN, LOW);   // active LOW = ON
    String response = "Fan turned ON";
    Serial.println(response);
    BTSerial.println(response);
  } else if (command == "fan off") {
    digitalWrite(FAN_PIN, HIGH);  // active LOW = OFF
    String response = "Fan turned OFF";
    Serial.println(response);
    BTSerial.println(response);
  } else if (command == "pump on") {
    digitalWrite(PUMP_PIN, LOW);  // active LOW = ON
    String response = "Pump turned ON";
    Serial.println(response);
    BTSerial.println(response);
  } else if (command == "pump off") {
    digitalWrite(PUMP_PIN, HIGH); // active LOW = OFF
    String response = "Pump turned OFF";
    Serial.println(response);
    BTSerial.println(response);
  } else if (command == "status") {
    // Send current status
    bool fanState = (digitalRead(FAN_PIN) == LOW);
    bool pumpState = (digitalRead(PUMP_PIN) == LOW);
    bool waterState = (digitalRead(LEVEL_SWITCH_PIN) == LOW);
    
    String statusResponse = "STATUS: Fan=" + String(fanState ? "ON" : "OFF") + 
                           " Pump=" + String(pumpState ? "ON" : "OFF") + 
                           " Water=" + String(waterState ? "FULL" : "EMPTY");
    Serial.println(statusResponse);
    BTSerial.println(statusResponse);
  } else if (command.length() > 0) {
    String errorResponse = "Unknown command: " + command + ". Use: fan on/off, pump on/off, status";
    Serial.println(errorResponse);
    BTSerial.println(errorResponse);
  }
}
