/*
  Main.ino — entry point only.
  Hardware logic lives in ultrasonic.ino and moisture.ino.

  Serial output to Pi at 9600:
    READY
    SAFE
    WALL:<dist1>,<dist2>,<angle>
    MOISTURE:<raw>,<DRY|MOIST|WET>
    MOISTURE:THRESHOLD_TRIGGERED
    GPS:<lat>,<lng>
    GPS:NO_FIX
*/

#include "ultrasonic.h"
#include "moisture.h"
#include <TinyGPSPlus.h>

TinyGPSPlus gps;

void feedGPS() {
  while (Serial1.available()) gps.encode(Serial1.read());
}

void sendGPS() {
  if (gps.location.isValid()) {
    Serial.print("GPS:");
    Serial.print(gps.location.lat(), 6);
    Serial.print(",");
    Serial.println(gps.location.lng(), 6);
  } else {
    Serial.println("GPS:NO_FIX");
  }
}

void setup() {
  Serial.begin(9600);
  Serial1.begin(115200);
  initWallAvoidance();
  pinMode(MOISTURE_PIN,  INPUT);
  pinMode(INTERRUPT_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(INTERRUPT_PIN), moistureThresholdISR, FALLING);
  Serial.println("READY");

 

}

unsigned long lastReading    = 0;
unsigned long readingInterval = 1000;
unsigned long lastSonicTime   = 0;
unsigned long sonicInterval   = 100;  // Ultrasonic checks every 100ms

void loop() {
  unsigned long now = millis();

  feedGPS();
  updateWallAvoidance();
  // 2. Rate-limit the ultrasonic sensor to stop pulseIn from blocking GPS data
  if (now - lastSonicTime >= sonicInterval) {
    lastSonicTime = now;
    updateWallAvoidance(); 
  }

  if (now - lastReading >= readingInterval) {
    lastReading = now;
    readMoisture();
    sendGPS();
  }
}
