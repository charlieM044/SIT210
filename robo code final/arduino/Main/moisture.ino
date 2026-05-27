// Pin definitions

#include <Arduino.h> // Explicitly tells the Nano IoT to look at its pin maps

// Force the compiler to see A0 strictly as a local analog constant
#undef MOISTURE_PIN

const int MOISTURE_PIN    = A1;   // analog moisture sensor

// Threshold values — tune these based on your open-air vs water readings.
// This sensor is inverted: LOW reading = WET soil, HIGH reading = DRY soil.
const int WET_THRESHOLD   = 200;  // readings below this = wet soil
const int DRY_THRESHOLD   = 600;  // readings above this = dry soil

// Volatile state variables removed entirely

void readMoisture() {
    // 1. Read the raw voltage value from the SIG pin
    int moistureValue = analogRead(MOISTURE_PIN);
    
    // 2. Send structured data to the Pi
    Serial.print("MOISTURE:");
    Serial.print(moistureValue);
    Serial.print(",");

    if (moistureValue <= WET_THRESHOLD) {
        Serial.println("WET");
    } else if (moistureValue >= DRY_THRESHOLD) {
        Serial.println("DRY");
    } else {
        Serial.println("MOIST");
    }

    // REMOVED: The thresholdExceeded if-statement is gone!
}

// REMOVED: The moistureThresholdISR() function is completely gone!