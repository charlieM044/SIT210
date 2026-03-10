j#include "DHT.h"
#include <WiFi.h>
#include "ThingSpeak.h"

#define DHTTYPE DHT22
#define DHTPIN 11

DHT dht(DHTPIN, DHTTYPE);

int pirPin = A0;
int Temp;
int Humid;
int Pir;

WiFiClient client;
unsigned long myChannelNumber = 3286547; // Replace with your Channel ID
const char *myWriteAPIKey = "CK3HB4WORSVO66DS"; // Replace with your Write API Key

void setup() {
  Serial.begin(9600);
  pinMode(pirPin, INPUT);
  dht.begin();

  WiFi.begin("-----------", "-----------"); // Connect to Wi-Fi
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");

  ThingSpeak.begin(client); // Initialize ThingSpeak
}

void loop() {
  
  Temp = dht.readTemperature();
  Humid = dht.readHumidity();
  Pir = analogRead(pirPin);
  

  if (isnan(Temp) || isnan(Humid)) {
    Serial.println("Failed to read DHT sensor");
    return;
  }


  Serial.print("Temp: ");
  Serial.println(Temp);
  Serial.print("Humid: ");
  Serial.println(Humid);
  Serial.print("PIR: ");
  Serial.println(Pir);


  ThingSpeak.setField(1, Temp);
  ThingSpeak.setField(2, Humid);
  ThingSpeak.setField(3, Pir);

  int result = ThingSpeak.writeFields(myChannelNumber, myWriteAPIKey);
  if (result == 200) {
    Serial.println("ThingSpeak update successful");
  } else {
    Serial.print("ThingSpeak update failed. Code: ");
    Serial.println(result);
  }

  delay(30000); 
}