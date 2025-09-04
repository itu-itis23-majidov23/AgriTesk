#include <Wire.h>
#include <U8g2lib.h>
#include "DHT.h"
#include <OneWire.h>
#include <DallasTemperature.h>
#include <SoftwareSerial.h>

// ----------------- Display (SH1106 I2C) -----------------
U8G2_SH1106_128X64_NONAME_1_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);

// ----------------- DHT22 -----------------
#define DHTPIN 7              // <- moved to D7
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// ----------------- Soil Moisture -----------------
#define SOIL_PIN A0

// ----------------- DS18B20 -----------------
#define ONE_WIRE_BUS 6        // <- moved to D6
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);
DeviceAddress sensorAddress;

// ----------------- Relays (active LOW) -----------------
#define FAN_PIN 8             // Fan on D8
#define PUMP_PIN 9            // Pump on D3

// ----------------- Water Level Switch -----------------
#define LEVEL_SWITCH_PIN 4    // float/level switch on D4 (INPUT_PULLUP)

// ----------------- Bluetooth (HC-05) -----------------
#define BT_RX 10
#define BT_TX 11
SoftwareSerial BTSerial(BT_RX, BT_TX);

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
}

void loop() {
  handleSerialCommands();  // check Serial input

  float humidity = dht.readHumidity();
  float tempDHT = dht.readTemperature();

  sensors.requestTemperatures();
  float tempDS = sensors.getTempCByIndex(0);

  int soilRaw = analogRead(SOIL_PIN);
  // Adjust these bounds after calibrating your sensor in air/water
  int soilPercent = map(soilRaw, 800, 400, 0, 100);
  soilPercent = constrain(soilPercent, 0, 100);

  // Relay states (active LOW)
  String fanState  = (digitalRead(FAN_PIN)  == LOW) ? "ON" : "OFF";
  String pumpState = (digitalRead(PUMP_PIN) == LOW) ? "ON" : "OFF";

  // Water level state (LOW means switch closed to GND)
  String waterState = (digitalRead(LEVEL_SWITCH_PIN) == LOW) ? "FULL" : "EMPTY";

  // --------- Print to Serial and Bluetooth ----------
  Serial.print("DHT22 T: "); Serial.print(tempDHT); Serial.print(" H: "); Serial.println(humidity);
  Serial.print("DS18B20 T: "); Serial.println(tempDS);
  Serial.print("Soil: "); Serial.println(soilPercent);
  Serial.print("Fan: "); Serial.print(fanState); Serial.print(" Pump: "); Serial.println(pumpState);
  Serial.print("Water Level: "); Serial.println(waterState);

  BTSerial.print("DHT22 T: "); BTSerial.print(tempDHT); BTSerial.print(" H: "); BTSerial.println(humidity);
  BTSerial.print("DS18B20 T: "); BTSerial.println(tempDS);
  BTSerial.print("Soil: "); BTSerial.println(soilPercent);
  BTSerial.print("Fan: "); BTSerial.print(fanState); BTSerial.print(" Pump: "); BTSerial.println(pumpState);
  BTSerial.print("Water Level: "); BTSerial.println(waterState);

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
    u8g2.print("Fan: "); u8g2.print(fanState);

    u8g2.setCursor(0, 58);
    u8g2.print("Pump: "); u8g2.print(pumpState);

    // Water Level line
    u8g2.setCursor(70, 58);
    u8g2.print("Water: "); u8g2.print(waterState);

  } while (u8g2.nextPage());

  delay(2000);
}

// ================= Serial Command Handler =================
void handleSerialCommands() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toLowerCase();

    if (command == "fan on") {
      digitalWrite(FAN_PIN, LOW);   // active LOW = ON
      Serial.println("Fan turned ON");
      BTSerial.println("Fan turned ON");
    } else if (command == "fan off") {
      digitalWrite(FAN_PIN, HIGH);  // active LOW = OFF
      Serial.println("Fan turned OFF");
      BTSerial.println("Fan turned OFF");
    } else if (command == "pump on") {
      digitalWrite(PUMP_PIN, LOW);  // active LOW = ON
      Serial.println("Pump turned ON");
      BTSerial.println("Pump turned ON");
    } else if (command == "pump off") {
      digitalWrite(PUMP_PIN, HIGH); // active LOW = OFF
      Serial.println("Pump turned OFF");
      BTSerial.println("Pump turned OFF");
    } else {
      Serial.println("Unknown command. Use: fan on/off, pump on/off");
      BTSerial.println("Unknown command. Use: fan on/off, pump on/off");
    }
  }
}