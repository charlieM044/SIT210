
#include "moisture.h"
#include "ultrasonic.h"

unsigned long lastSenseTime = 0;
const int interval = 1000;

void setup() {
  Serial.begin(9600);

  Serial1.begin(115200);  // To GPS
  while (!Serial);      // Wait for monitor to open
  Serial.println("Starting GPS Bridge...");
  initWallAvoidance();
  
  pinMode(MOISTURE_PIN, INPUT);
  pinMode(INTERRUPT_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(INTERRUPT_PIN), moistureThresholdISR, FALLING);
}

void loop() {
  // 1. Read GPS CONSTANTLY (No delays allowed here)
  while (Serial1.available()) {
    Serial.write(Serial1.read());
  }

  // 2. Perform other tasks only when the interval has passed
  if (millis() - lastSenseTime >= interval) {
    lastSenseTime = millis();
    
    readMoisture();
    updateWallAvoidance();
    
    if (isWallDetected()) {
      float remainingTurn = getWallAngle() - getTurnAmount();
      Serial.print("WALL:");
      Serial.print(remainingTurn);
      Serial.print(",");
      Serial.print(getWallAngle());
      Serial.print(",");
      Serial.println(getTurnAmount());
    } else {
      Serial.println("SAFE");
    }
  }
  
}
