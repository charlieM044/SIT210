#ifndef ULTRASONIC_H
#define ULTRASONIC_H

#include <Arduino_LSM6DS3.h>

// Ultrasonic pins
extern const int TRIG_PIN1;
extern const int ECHO_PIN1;
extern const int TRIG_PIN2;
extern const int ECHO_PIN2;

// Wall avoidance variables
extern float gx, gy, gz;
extern float currentGyroAngle;
extern float lastTime;
extern const float L;
extern const float SAFE_DISTANCE;
extern const float MAX_TURN_ANGLE;
extern float wallAngle;
extern float turnAmount;

void initWallAvoidance();
void updateWallAvoidance();
void updateGyroAngle();
float getDistance(int trigPin, int echoPin);
float getWallAngle();
float getTurnAmount();
bool isWallDetected();

#endif