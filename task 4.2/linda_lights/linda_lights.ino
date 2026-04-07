#include <WiFiNINA.h>
#include <ArduinoMqttClient.h>
#include "secrets.h"


const char* topicLivingRoom = "linda/lights/livingRoom";
const char* topicBathroom   = "linda/lights/bathroom";
const char* topicCloset     = "linda/lights/closet";


const int ledPin2 = 12;  // Living Room
const int ledPin3 = 11;  // Bathroom
const int ledPin4 = 9;  // Closet

// Source of truth: only ever set from the MQTT state topic
bool livingRoom = false;
bool bathroom   = false;
bool closet     = false;
bool stateLoaded = false; // true once we've read the retained state from broker

WiFiSSLClient wifiClient;
MqttClient mqttClient(wifiClient);

// Apply bool states to physical LEDs 
void applyLEDs() 
{
  digitalWrite(ledPin2, livingRoom ? HIGH : LOW);
  digitalWrite(ledPin3, bathroom   ? HIGH : LOW);
  digitalWrite(ledPin4, closet     ? HIGH : LOW);
  Serial.println("LEDs applied  LR:" + String(livingRoom) + " BA:" + String(bathroom) + " CL:" + String(closet));
}

// Toggle LED 
void toggleLight(String room, bool state) {
  if (room == "livingRoom")    livingRoom = state;
  else if (room == "bathroom") bathroom   = state;
  else if (room == "closet")   closet     = state;
  else if (room == "all") {
    livingRoom = bathroom = closet = state;
  } else {
    Serial.println("Unknown room: [" + room + "]");
    return;
  }
  applyLEDs();

}
//-------------------------used for old json format--------------------
// //  Publish current bool state as JSON to broker
// void publishState() 
// {
//   String payload = "{";
//   payload += "\"livingRoom\":" + String(livingRoom ? "true" : "false") + ",";
//   payload += "\"bathroom\":"   + String(bathroom   ? "true" : "false") + ",";
//   payload += "\"closet\":"     + String(closet     ? "true" : "false");
//   payload += "}";

//   mqttClient.beginMessage(topicState, true); // retained = true
//   mqttClient.print(payload);
//   mqttClient.endMessage();
//   Serial.println("Published state: " + payload);
// }

// // Parse a JSON bool value from a payload string
// bool parseJsonBool(String json, String key)
//  {
//   String search = "\"" + key + "\":";
//   int idx = json.indexOf(search);
//   if (idx < 0) return false;
//   idx += search.length();
//   return json.substring(idx, idx + 4) == "true";
// }

// Called on every incoming MQTT message
void onMqttMessage(int messageSize) 
{
   String topic = mqttClient.messageTopic();
  String msg   = "";
  while (mqttClient.available()) msg += (char)mqttClient.read();
  msg.trim();

  Serial.println("Message on [" + topic + "]: " + msg);

  bool state = msg == "1";

  if      (topic == topicLivingRoom) toggleLight("livingRoom", state);
  else if (topic == topicBathroom)   toggleLight("bathroom",   state);
  else if (topic == topicCloset)     toggleLight("closet",     state);
}

void connectMQTT() 
{
  mqttClient.setUsernamePassword(mqttUser, mqttPassword);
  mqttClient.onMessage(onMqttMessage); // calls method apon new message from the cloud

  Serial.print("Connecting to HiveMQ...");
  while (!mqttClient.connect(mqttHost, mqttPort)) {
    Serial.print(".");
    delay(1000);
  }
  Serial.println("\nMQTT Connected!");


  mqttClient.subscribe(topicBathroom);
    Serial.println("Subscribed to bathroom topic, waiting for retained state...");
    delay(500);
  mqttClient.subscribe(topicCloset);
    Serial.println("Subscribed to closet topic, waiting for retained state...");
    delay(500);
  mqttClient.subscribe(topicLivingRoom);
    Serial.println("Subscribed to living room topic, waiting for retained state...");
    delay(500);



}


void setup() 
{
  Serial.begin(9600);
  delay(1500);

  pinMode(ledPin2, OUTPUT);
  pinMode(ledPin3, OUTPUT);
  pinMode(ledPin4, OUTPUT);

  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  //Serial.println("\nWiFi Connected! IP: " + WiFi.localIP().toString());

  connectMQTT();
}

void loop() 
{
  if (!mqttClient.connected()) {
    Serial.println("MQTT disconnected, reconnecting...");
    stateLoaded = false; // force re-read of state on reconnect
    connectMQTT();
  }
  mqttClient.poll(); //checks for new mqtt messages
  delay(100);
}