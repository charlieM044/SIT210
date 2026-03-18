#include "DHT.h"
#include <WiFi.h>
#include "ThingSpeak.h"
#include "secrets.h"

#define DHTTYPE DHT22
#define DHTPIN 11

DHT dht(DHTPIN, DHTTYPE);

int pirPin = A0;
int Temp;
int Humid;
int Pir;

WiFiClient client;

int readdht() // handles temperature and Humidity logic
{
  Temp = dht.readTemperature();
  Humid = dht.readHumidity();

  

  if (isnan(Temp) || isnan(Humid)) {
    Serial.println("Failed to read DHT sensor");
    return 0;
  }

  Serial.print("Temp: ");
  Serial.println(Temp);
  Serial.print("Humid: ");
  Serial.println(Humid);
 

  return Temp, Humid;
}

int readPir() // handles Pir sensor
{

    Pir = analogRead(pirPin);

    if (isnan(Pir))
    {
      Serial.print("faild to red Pir");
      return 0;
     }
    Serial.print("PIR: ");
    Serial.println(Pir);

  return Pir;
}

void dothingspeak()  // handles thing speak logic 
{
  ThingSpeak.setField(1,Temp);
  ThingSpeak.setField(2,Humid);
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


void loop()  // main loop
{
  readdht();
  readPir();
  dothingspeak();
}