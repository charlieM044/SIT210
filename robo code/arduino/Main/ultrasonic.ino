

// Ultrasonic pins
const int TRIG_PIN1 = 5;
const int ECHO_PIN1 = 3;
const int TRIG_PIN2 = 8;
const int ECHO_PIN2 = 9;

// Gyro variables
float gx, gy, gz;
float currentGyroAngle = 0;
float lastTime = 0;

// Wall avoidance variables
const float L = 15.0;
const float SAFE_DISTANCE = 20.0;
const float MAX_TURN_ANGLE = 45.0;
float wallAngle = 0;
float turnAmount = 0;
float minDistance = 0;


void initWallAvoidance() {
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

void updateWallAvoidance() {
  // Get distances
  float d1 = getDistance(TRIG_PIN1, ECHO_PIN1);
  float d2 = getDistance(TRIG_PIN2, ECHO_PIN2);
   if (d1 <1 || d2 <1)
   {return;}
  
  // Calculate wall angle
  wallAngle = atan2(d2 - d1, L) * (180.0 / PI);
  
  // Update gyro
  updateGyroAngle();
  
  // Check distance
  minDistance = min(d1, d2);
  
  if (isWallDetected()) {
    float requiredTurn = wallAngle;
    float remainingTurn = requiredTurn - turnAmount;

    Serial.println(d1);
  
    Serial.println(d2);
    
    Serial.print("WALL DETECTED! Distance: ");
    Serial.print(minDistance);
    Serial.print(" cm | Turn needed: ");
    Serial.println(remainingTurn);
  } else {
    Serial.print("Safe - Distance: ");
    Serial.println(minDistance);
  }
}

void updateGyroAngle() {
  if (IMU.gyroscopeAvailable()) {
    IMU.readGyroscope(gx, gy, gz);
    
    float currentTime = millis();
    float dt = (currentTime - lastTime) / 1000.0;
    lastTime = currentTime;
    
    currentGyroAngle += gz * dt;
    turnAmount = currentGyroAngle;
    
    if (turnAmount > 180) turnAmount -= 360;
    if (turnAmount < -180) turnAmount += 360;
  }
}

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

float getWallAngle() {
  return wallAngle;
}

float getTurnAmount() {
  return turnAmount;
}

bool isWallDetected() {
  return minDistance < SAFE_DISTANCE;
}