#include <Arduino_LSM6DS3.h>

// Ultrasonic pins
const int TRIG_PIN1 = 6;
const int ECHO_PIN1 = 3;
const int TRIG_PIN2 = 8;
const int ECHO_PIN2 = 9;

// Gyro variables
float gx, gy, gz;
float currentGyroAngle = 0;
float lastTime = 0;

// Wall avoidance variables
const float L = 15.0;  // Sensor separation in cm
const float SAFE_DISTANCE = 20.0;  // Minimum safe distance in cm
const float MAX_TURN_ANGLE = 45.0;  // Max degrees to turn to avoid wall
float wallAngle = 0;  // Angle to the wall
float turnAmount = 0;  // How much we've already turned

void setup() {
  Serial.begin(9600);
  
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }
  
  pinMode(TRIG_PIN1, OUTPUT);
  pinMode(ECHO_PIN1, INPUT);
  pinMode(TRIG_PIN2, OUTPUT);
  pinMode(ECHO_PIN2, INPUT);
  
  lastTime = millis();
}

void loop() {
  // Get distances from both ultrasonic sensors
  float d1 = getDistance(TRIG_PIN1, ECHO_PIN1);
  float d2 = getDistance(TRIG_PIN2, ECHO_PIN2);
  
  // Calculate wall angle from ultrasonic sensors
  wallAngle = atan2(d2 - d1, L) * (180.0 / PI);
  
  // Update gyro tracking
  updateGyroAngle();
  
  // Check if wall is close
  float minDistance = min(d1, d2);
  
  if (minDistance < SAFE_DISTANCE) {
    // Wall detected - calculate how much we need to turn
    float requiredTurn = wallAngle;
    
    // How much more do we need to turn?
    float remainingTurn = requiredTurn - turnAmount;
    
    Serial.print("WALL DETECTED! Distance: ");
    Serial.print(minDistance);
    Serial.print(" cm | Wall at angle: ");
    Serial.print(wallAngle);
    Serial.print(" | Already turned: ");
    Serial.print(turnAmount);
    Serial.print(" | Need to turn: ");
    Serial.println(remainingTurn);
    
    // Signal robot to turn (remainingTurn tells motor controller direction/amount)
    avoidWall(remainingTurn);
  } else {
    Serial.print("Safe - Distance: ");
    Serial.print(minDistance);
    Serial.print(" cm | Gyro angle: ");
    Serial.println(currentGyroAngle);
    
    // Continue forward
    moveForward();
  }
  
  delay(100);
}

// Update gyro angle by integrating angular velocity
void updateGyroAngle() {
  if (IMU.gyroscopeAvailable()) {
    IMU.readGyroscope(gx, gy, gz);
    
    float currentTime = millis();
    float dt = (currentTime - lastTime) / 1000.0;
    lastTime = currentTime;
    
    // Integrate gyro to track actual rotation
    currentGyroAngle += gz * dt;
    
    // Update how much we've actually turned
    turnAmount = currentGyroAngle;
    
    // Normalize to -180 to 180
    if (turnAmount > 180) turnAmount -= 360;
    if (turnAmount < -180) turnAmount += 360;
  }
}

// Avoid wall - signal motor controller how much to turn
void avoidWall(float remainingTurn) {
  // remainingTurn: positive = turn left, negative = turn right
  // Pass this to your motor control code
  
  // Example: limit turn to max angle
  remainingTurn = constrain(remainingTurn, -MAX_TURN_ANGLE, MAX_TURN_ANGLE);
  
  // You'd call your motor function here with remainingTurn
  // motorTurn(remainingTurn);
}

// Move forward
void moveForward() {
  // Call your forward motor code here
  // motorForward();
}

// Get distance from single ultrasonic sensor
float getDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  unsigned long pulseDuration = pulseIn(echoPin, HIGH, 30000);
  float distance = (pulseDuration * 0.0343) / 2;
  
  return distance;
}