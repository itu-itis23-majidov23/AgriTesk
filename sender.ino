#include <SoftwareSerial.h>

// RX, TX pins for HC-05
SoftwareSerial BTSerial(10, 11); // RX, TX

// Simulated sensor data
float weatherTemp = 25.0;
float waterTemp = 18.0;
float weatherHum = 60.0;
float soilMoist = 45.0;
int waterLevel = 1;

void setup() {
  Serial.begin(9600);     // Arduino USB serial
  BTSerial.begin(9600);   // HC-05 baud rate (default 9600)
  
  // Initialize random seed
  randomSeed(analogRead(0));
}

void loop() {
  // Simulate realistic sensor data with small variations
  weatherTemp += random(-20, 21) / 100.0;  // ±0.2°C change
  waterTemp += random(-15, 16) / 100.0;    // ±0.15°C change
  weatherHum += random(-30, 31) / 10.0;    // ±3% change
  soilMoist += random(-20, 21) / 10.0;     // ±2% change
  
  // Keep values in realistic ranges
  weatherTemp = constrain(weatherTemp, 15.0, 40.0);
  waterTemp = constrain(waterTemp, 10.0, 30.0);
  weatherHum = constrain(weatherHum, 30.0, 90.0);
  soilMoist = constrain(soilMoist, 20.0, 80.0);
  
  // Occasionally change water level
  if (random(100) < 5) {  // 5% chance
    waterLevel = random(2);  // 0 or 1
  }
  
  // Create sensor data string
  String sensorData = String(weatherTemp, 1) + "," + 
                     String(waterTemp, 1) + "," + 
                     String(weatherHum, 1) + "," + 
                     String(soilMoist, 1) + "," + 
                     String(waterLevel);
  
  // Send data via Bluetooth
  BTSerial.println(sensorData);
  
  // Also print to serial monitor for debugging
  Serial.println("Sent: " + sensorData);
  
  delay(2000);  // Send data every 2 seconds
}
