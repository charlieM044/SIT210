#include <WiFiNINA.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <BH1750.h>
//#include "secrets.h"


const char* ssid        = "Telstra ai";
const char* password    = "Hoi123456789";
const char* mqtt_server = "6f3605820d7e4e06a91e9c9f08a214e3.s1.eu.hivemq.cloud";
const int   mqtt_port   = 8883;
const char* mqtt_user   = "testing";
const char* mqtt_password = "*Testing1";


// Light threshold (lux) - adjust based on your environment
const float LIGHT_THRESHOLD = 50;

WiFiSSLClient wifiClient;
PubSubClient client(wifiClient);
BH1750 lightMeter;

bool sunlightActive = false;

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
   delay(1500);
}

void connectMQTT() {
  while (!client.connected()) {
    Serial.print("Connecting to HiveMQ...");
    if (client.connect("ArduinoClient", mqtt_user, mqtt_password)) {
      Serial.println("Connected!");
    } else {
      Serial.print("Failed, rc=");
      Serial.println(client.state());
      delay(3000);

    }
  }
}

void setup() {
  Serial.begin(9600);
  Wire.begin();
  lightMeter.begin();
  connectWiFi();
  client.setServer(mqtt_server, mqtt_port);
}

void publishtopic(float lux)
{
  // Trigger logic - publish status only on state CHANGE
  if (lux >= LIGHT_THRESHOLD && !sunlightActive) {
    sunlightActive = true;
    client.publish("terrarium/status", "SUNLIGHT_START");
    Serial.println("Trigger: Sunlight started!");
  } else if (lux < LIGHT_THRESHOLD && sunlightActive) {
    sunlightActive = false;
    client.publish("terrarium/status", "SUNLIGHT_STOP");
    Serial.println("Trigger: Sunlight stopped!");
  }
}

void loop() {
  if (!client.connected()) connectMQTT();
  client.loop();

  float lux = lightMeter.readLightLevel();
  Serial.print("Light: ");
  Serial.print(lux);
  Serial.println(" lux");

  publishtopic(lux);

  delay(5000); // Read every 5 seconds
}
