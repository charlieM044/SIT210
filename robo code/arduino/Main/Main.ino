
#include "moisture.h"
#include "ultrasonic.h"

void setup() {
  Serial.begin(9600);

  initWallAvoidance();
  
  pinMode(MOISTURE_PIN, INPUT);
  pinMode(INTERRUPT_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(INTERRUPT_PIN), moistureThresholdISR, FALLING);
}

void loop() {
  readUltraSonic();
  readMoisture();

  updateWallAvoidance();
  
  if (isWallDetected()) {
    float remainingTurn = getWallAngle() - getTurnAmount();
   // Send wall detection data to Pi
    Serial.print("WALL:");
    Serial.print(remainingTurn);
    Serial.print(",");
    Serial.print(getWallAngle());
    Serial.print(",");
    Serial.println(getTurnAmount());
  } else {
    // Send safe status
    Serial.println("SAFE");
  }
  
  delay(100);
}
}