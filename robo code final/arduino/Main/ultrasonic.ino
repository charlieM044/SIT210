#include <Arduino_LSM6DS3.h>

const int TRIG_PIN1 = 12;
const int ECHO_PIN1 = 4;
const int TRIG_PIN2 = 8;
const int ECHO_PIN2 = 9;

float gx, gy, gz;
float currentGyroAngle = 0;
float lastTime         = 0;

const float L              = 11.5;
const float SAFE_DISTANCE  = 20.0;
const float MAX_TURN_ANGLE = 45.0;
float wallAngle   = 0;
float turnAmount  = 0;
float minDistance = 0;


void initWallAvoidance() {
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }
  pinMode(TRIG_PIN1, OUTPUT); pinMode(ECHO_PIN1, INPUT);
  pinMode(TRIG_PIN2, OUTPUT); pinMode(ECHO_PIN2, INPUT);
  lastTime = millis();
}



void updateGyroAngle() {
  if (IMU.gyroscopeAvailable()) {
    IMU.readGyroscope(gx, gy, gz);
    float currentTime = millis();
    float dt          = (currentTime - lastTime) / 1000.0;
    lastTime          = currentTime;
    currentGyroAngle += gz * dt;
    turnAmount        = currentGyroAngle;
    if (turnAmount >  180) turnAmount -= 360;
    if (turnAmount < -180) turnAmount += 360;
  }
}

float getDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH); delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  unsigned long duration = pulseIn(echoPin, HIGH, 30000);
  return (duration * 0.0343) / 2.0;
}
float determineTurnAngle(float dist1, float dist2) {
  // Dynamically calculate turn severity based on how close the obstacle is
  float base = ((SAFE_DISTANCE - minDistance) / SAFE_DISTANCE) * (MAX_TURN_ANGLE - 15.0) + 15.0;
  base = constrain(base, 15.0, MAX_TURN_ANGLE);

  if (dist1 < dist2) return -base;
  else if (dist2 < dist1) return  base;
  else return (currentGyroAngle < 0) ? -base : base;
}

bool isWallDetected() {
  return minDistance < SAFE_DISTANCE && minDistance > 0;
}

float getWallAngle()  { return wallAngle; }
float getTurnAmount() { return turnAmount; }
void updateWallAvoidance() {
 // 1. Fire and read Sensor 1 instantly
  float d1 = getDistance(TRIG_PIN1, ECHO_PIN1);
  
  // 2. TIMING DELAY: Wait 15ms so Sensor 1's sound waves die out faster
  delay(15);
  
  // 3. Fire and read Sensor 2 safely without crosstalk
  float d2 = getDistance(TRIG_PIN2, ECHO_PIN2);

 if (d1 < 1 || d2 < 1) {
    Serial.print("ULTRASONIC: ERROR - Invalid Reading (d1: ");
    Serial.print(d1, 1);
    Serial.print(", d2: ");
    Serial.print(d2, 1);
    Serial.println(")");
    return; 
  }

  // Fixed floating point trigonometry calculation
  wallAngle = atan((d2 - d1) / L) * (180.0 / M_PI);
  minDistance = min(d1, d2);


  if (isWallDetected()) {
    float angle = determineTurnAngle(d1, d2);
    Serial.print("ULTRASONIC: WALL:");
    Serial.print(d1, 1);
    Serial.print(",");
    Serial.print(d2, 1);
    Serial.print(",");
    Serial.println(angle, 1);
  } else {
    Serial.println("ULTRASONIC: SAFE");
    delay(100);
  }

}