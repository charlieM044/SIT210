#include "DHT.h"
#include <Wire.h>
#include <BH1750.h>

#define DHTTYPE DHT22
#define DHTPIN 11
#define PIR_PIN 2      // must be pin 2 or 3 for interrupts on Uno/Nano
#define SWITCH_PIN 8
#define LED1 4
#define LED2 5

const float LIGHT_THRESHOLD = 50.0;

DHT dht(DHTPIN, DHTTYPE);
BH1750 lightMeter;

volatile bool motionDetected = false; // shared with ISR — must be volatile

// Interrupt Service Routine — keep it short, no Serial/delay here
void pirISR() {
  motionDetected = (digitalRead(PIR_PIN) == HIGH);
}

void setup() {
  Serial.begin(9600);
  Wire.begin();

  pinMode(PIR_PIN, INPUT);
  pinMode(SWITCH_PIN, INPUT_PULLUP);
  pinMode(LED1, OUTPUT);
  pinMode(LED2, OUTPUT);

  dht.begin();
  lightMeter.begin();

  // Attach interrupt to PIR pin, trigger on any change
  attachInterrupt(digitalPinToInterrupt(PIR_PIN), pirISR, CHANGE);

  Serial.println("Waiting for PIR to calibrate...");
  delay(20000);
  Serial.println("Ready.");
}

bool readSwitch() {
  int state = digitalRead(SWITCH_PIN);
  if (state == HIGH) {
    Serial.println("Switch: ON");
    return true;
  } else {
    Serial.println("Switch: OFF");
    return false;
  }
}

void readSensors() {
  float lux = lightMeter.readLightLevel();
  Serial.print("LUX: ");
  Serial.println(lux);

  Serial.print("PIR: ");
  Serial.println(motionDetected);

  if (lux <= LIGHT_THRESHOLD && motionDetected) {
    digitalWrite(LED1, HIGH);
    digitalWrite(LED2, HIGH);
  } else {
    digitalWrite(LED1, LOW);
    digitalWrite(LED2, LOW);
  }
}

void loop() {
  readSwitch();
  readSensors();
  delay(1000);
}


