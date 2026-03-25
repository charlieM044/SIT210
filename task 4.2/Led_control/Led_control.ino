#include "thingProperties.h"


const int ledPin2 = 3;  
const int ledPin3 = 4;  
const int ledPin4 = 5;  


int ledLivingroom = LOW; 
int ledBathroom = LOW; 
int ledCloset = LOW; 


unsigned long previousMillis = 0; 



void setup() {

  pinMode(ledPin2, OUTPUT);
  pinMode(ledPin3, OUTPUT);
  pinMode(ledPin4, OUTPUT);

  Serial.begin(9600);

    initProperties();

  // Connect to Arduino IoT Cloud
  ArduinoCloud.begin(ArduinoIoTPreferredConnection);
  
  setDebugMessageLevel(2);
  ArduinoCloud.printDebugInfo();

}



void loop() {
  ArduinoCloud.update();
}

void onLivingRoomChange() {
  ledLivingroom = LivingRoom ? HIGH : LOW;
  digitalWrite(ledPin2, ledLivingroom);
  Serial.print("Living Room -> ");
  Serial.println(ledLivingroom == HIGH ? "ON" : "OFF");
}

void onBathroomChange() {
  ledBathroom = Bathroom ? HIGH : LOW;
  digitalWrite(ledPin3, ledBathroom);
  Serial.print("Bathroom -> ");
  Serial.println(ledBathroom == HIGH ? "ON" : "OFF");
}

void onClosetChange() {
  ledCloset = Closet ? HIGH : LOW;
  digitalWrite(ledPin4, ledCloset);
  Serial.print("Closet -> ");
  Serial.println(ledCloset == HIGH ? "ON" : "OFF");
}