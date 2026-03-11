#include "arduino_secrets.h"
#include "thingProperties.h"


void setup() {
  // Start the serial monitor:
  Serial.begin(9600);

  // Defined in thingProperties.h
  initProperties();

  // Connect to Arduino IoT Cloud
  ArduinoCloud.begin(ArduinoIoTPreferredConnection);

  setDebugMessageLevel(2);
  ArduinoCloud.printDebugInfo();
}

void loop() {

  ArduinoCloud.update();

}


void onTestChange() {
  Serial.println("test changed");
}


