
#include "moisture.h"
#include "ultrasonic.h"

unsigned long lastSenseTime = 0;
const int interval = 1000;

int test_led = 2;

void setup() {
  Serial.begin(9600);

  Serial1.begin(115200);  // To GPS
  pinMode(test_led, OUTPUT);
 // while (!Serial);      // Wait for monitor to open
 unsigned long start = millis();
 while (!Serial && millis() - start < 3000){}
 // Serial.println("Starting GPS Bridge...");
  initWallAvoidance();
  
  pinMode(MOISTURE_PIN, INPUT);
  pinMode(INTERRUPT_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(INTERRUPT_PIN), moistureThresholdISR, FALLING);
}

void loop() {
  // 1. Read GPS CONSTANTLY (No delays allowed here)
//   while (Serial1.available()) { 
//   char c = Serial1.read();
//   if (Serial) {           // Only write to USB if a PC is connected
//     Serial.write(c); 
//   }
// }

  // 2. Perform other tasks only when the interval has passed
  if (millis() - lastSenseTime >= interval) {
    lastSenseTime = millis();
    
    readMoisture();
    updateWallAvoidance();
    
    if (isWallDetected()) {

      pinMode(test_led, HIGH);

      float remainingTurn = getWallAngle() - getTurnAmount();
      Serial.print("WALL:");
      Serial.print(remainingTurn);
      Serial.print(",");
      Serial.print(getWallAngle());
      Serial.print(",");
      Serial.println(getTurnAmount());
    } else {
      pinMode(test_led,LOW);
      Serial.println("SAFE");
    }
  }
  
}
