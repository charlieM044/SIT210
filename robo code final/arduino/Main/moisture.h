#ifndef MOISTURE_H
#define MOISTURE_H

extern const int MOISTURE_PIN;
extern const int INTERRUPT_PIN;
extern const int DRY_THRESHOLD;
extern const int WET_THRESHOLD;

extern volatile int moistureValue;
extern volatile bool thresholdExceeded;
extern volatile unsigned long lastInterruptTime;
extern const unsigned long DEBOUNCE_DELAY;

void readMoisture();
void moistureThresholdISR();

#endif