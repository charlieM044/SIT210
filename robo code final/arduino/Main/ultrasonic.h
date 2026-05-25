#ifndef ULTRASONIC_H
#define ULTRASONIC_H

#include <Arduino_LSM6DS3.h>

extern const int TRIG_PIN1;
extern const int ECHO_PIN1;
extern const int TRIG_PIN2;
extern const int ECHO_PIN2;

extern float gx, gy, gz;
extern float currentGyroAngle;
extern float lastTime;
extern const float L;
extern const float SAFE_DISTANCE;
extern const float MAX_TURN_ANGLE;
extern float wallAngle;
extern float turnAmount;

// Interrupt echo state — ISRs in Main.ino write these
extern volatile unsigned long echo1Start, echo1End;
extern volatile unsigned long echo2Start, echo2End;
extern volatile bool echo1Done, echo2Done;

void initWallAvoidance();
void updateWallAvoidance();
void updateGyroAngle();
float getDistance(int trigPin, int echoPin);
float getDistanceISR1();
float getDistanceISR2();
float determineTurnAngle(float dist1, float dist2);
float getWallAngle();
float getTurnAmount();
bool isWallDetected();

#endif
