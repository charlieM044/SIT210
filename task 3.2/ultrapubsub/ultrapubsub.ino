
#include <WiFiNINA.h>
#include <PubSubClient.h>
#include <Wire.h>
#include "secrets.h"


const int trigger = 12;
const int echo = 11;

int distance = 0;
int Dist = -1;

int LED1 = 6;
int LED2 = 7;

WiFiSSLClient wifiClient;
PubSubClient client(wifiClient);


void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
}

void connectMQTT() {
  while (!client.connected()) {
    Serial.print("Connecting to HiveMQ...");
    if (client.connect("ArduinoClient", mqtt_user, mqtt_password)) {
      Serial.println("Connected!");
      client.subscribe("ES/Wave");
      client.subscribe("ES/Pat");
    } else {
      Serial.print("Failed, rc=");
      Serial.println(client.state());
      delay(3000);
    }
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  
  // Convert payload bytes to a readable string
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  // Print to Serial Monitor
  Serial.print("Message received on: ");
  Serial.println(topic);
  Serial.print("Message: ");
  Serial.println(message);

  // React based on which topic it came from
  if (String(topic) == "ES/Wave") {
    digitalWrite(LED1, HIGH);
    digitalWrite(LED2, HIGH);
  } 
  else if (String(topic) == "ES/Pat") {
    digitalWrite(LED1, LOW);
    digitalWrite(LED2, LOW);
  }
}
int getUltrasonicDistance() {
  // Function to retreive the distance reading of the ultrasonic sensor
  long duration;
  int distance;

  // Assure the trigger pin is LOW:
  digitalWrite(trigger, LOW);
  // Brief pause:
  delayMicroseconds(50);

  // Trigger the sensor by setting the trigger to HIGH:
  digitalWrite(trigger, HIGH);
  // Wait a moment before turning off the trigger:
  delayMicroseconds(10);
  // Turn off the trigger:
  digitalWrite(trigger, LOW);
  // Read the echo pin:


  // Correct - HIGH is the state, 30000 is the timeout
  duration = pulseIn(echo, HIGH);

 if (duration == 0) return -1;  // Explicitly handle timeouts
  // Calculate the distance in cent:
  distance = duration * 0.034 / 2;

  // Return the distance
  return distance;
}

void setup() {
  // Define inputs and outputs:
  pinMode(trigger, OUTPUT);
  pinMode(echo, INPUT);
  
  pinMode(LED1, OUTPUT);
  pinMode(LED2, OUTPUT);


  Wire.begin();

  connectWiFi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);  // put this in setup()

  // Start the serial monitor:
  Serial.begin(9600);
  Serial.print("start");
}


void loop() {
  // put your main code here, to run repeatedly:
      if (!client.connected()) connectMQTT();
  client.loop();

   
   Serial.print("Distance: ");


  distance = getUltrasonicDistance();
  String DistanceString = String(distance);
   
    client.publish(mqtt_topic,  DistanceString.c_str() );
    Serial.println(distance);

if (distance > 0 && distance <= 5)
    {
      client.publish("ES/Pat", mqtt_user);
    }
    else if (distance > 5 &&  distance <=15)
    {
      client.publish("ES/Wave",mqtt_user);
    }

    client.loop();

   

  
}
