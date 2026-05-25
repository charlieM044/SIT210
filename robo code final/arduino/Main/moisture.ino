

// Pin definitions
const int MOISTURE_PIN    = A0;   // analog moisture sensor
const int INTERRUPT_PIN   = 2;    // must be 2 or 3 on Uno/Nano (FALLING edge)

// Threshold values — tune these to your sensor
const int DRY_THRESHOLD   = 600;  // above this = dry soil
const int WET_THRESHOLD   = 300;  // below this = wet soil

// Volatile state (shared with ISR)
volatile int           moistureValue      = 0;
volatile bool          thresholdExceeded  = false;
volatile unsigned long lastInterruptTime  = 0;
const unsigned long    DEBOUNCE_DELAY     = 200;

void readMoisture() {
    moistureValue = analogRead(MOISTURE_PIN);

    // Send structured data to Pi (matches your WALL:/SAFE pattern)
    Serial.print("MOISTURE:");
    Serial.print(moistureValue);
    Serial.print(",");

    if (moistureValue >= DRY_THRESHOLD) {
        Serial.println("DRY");
    } else if (moistureValue <= WET_THRESHOLD) {
        Serial.println("WET");
    } else {
        Serial.println("MOIST");
    }

    // Handle interrupt flag set by ISR
    if (thresholdExceeded) {
        thresholdExceeded = false;
        Serial.println("MOISTURE:THRESHOLD_TRIGGERED");
    }
}

void moistureThresholdISR() {
    unsigned long now = millis();
    if (now - lastInterruptTime > DEBOUNCE_DELAY) {
        thresholdExceeded = true;
        lastInterruptTime = now;
    }
}