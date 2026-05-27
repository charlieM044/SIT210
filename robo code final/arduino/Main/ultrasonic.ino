/*
  ultrasonic.ino  –  Wall avoidance state machine.

  The Arduino owns the full avoidance loop.  After every sensor cycle it
  sends ONE drive command to the Pi:

    CMD:FORWARD          clear path, resume full speed
    CMD:FORWARD:<speed>  proportional speed (30-100) during approach zone
    CMD:LEFT             turn left to avoid wall on the right
    CMD:RIGHT            turn right to avoid wall on the left
    CMD:STOP             obstacle too close / sensor error

  It still sends the raw sensor report so the Pi dashboard stays informed:

    ULTRASONIC: SAFE
    ULTRASONIC: WALL:<d1>,<d2>,<angle>
    ULTRASONIC: ERROR - Invalid Reading (d1: x, d2: y)

  State machine:
    CRUISING   → full speed, path clear (minDist >= APPROACH_DISTANCE)
    APPROACH   → proportional slowdown (STOP_DISTANCE < minDist < APPROACH_DISTANCE)
    AVOIDING   → stopped and turning; gyro tracks how far we have turned
    CONFIRM    → sensors clear after a turn; wait CONFIRM_MS before resuming
    STUCK      → AVOIDING timed out; send STOP and let Pi operator intervene
*/

#include "ultrasonic.h"
#include <Arduino_LSM6DS3.h>

// ── Pin assignments ────────────────────────────────────────────────────────────
const int TRIG_PIN1 = 12;
const int ECHO_PIN1 = 4;
const int TRIG_PIN2 = 8;
const int ECHO_PIN2 = 9;

// ── Tuning constants ───────────────────────────────────────────────────────────
const float L = 11.5;                        // sensor baseline (cm)
const float APPROACH_DISTANCE = 40.0;        // start slowing down (cm)
const float STOP_DISTANCE = 15.0;            // hard stop, start turning (cm)
const float CLEAR_DISTANCE = 30.0;           // both sensors must exceed this to confirm clear
const float TARGET_TURN_DEG = 60.0;          // degrees to turn before rechecking
const float MAX_TURN_ANGLE = 45.0;           // max angle for determineTurnAngle()
const unsigned long AVOID_TIMEOUT_MS = 8000; // bail out if stuck > 8 s
const unsigned long CONFIRM_MS = 800;        // ms both sensors must stay clear

// ── Gyro state ────────────────────────────────────────────────────────────────
float gx, gy, gz;
float currentGyroAngle = 0;
float lastTime = 0;

// ── Sensor state ──────────────────────────────────────────────────────────────
float wallAngle = 0;
float turnAmount = 0;
float minDistance = 0;

// ── Avoidance state machine ───────────────────────────────────────────────────
enum AvoidState
{
  CRUISING,
  APPROACH,
  AVOIDING,
  CONFIRM,
  STUCK
};
static AvoidState avoidState = CRUISING;
static int turnDir = 0;              // +1 = left, -1 = right
static float turnedSoFar = 0;        // accumulated gyro degrees this turn
static float gyroAtStart = 0;        // gyro reference when turn began
static unsigned long avoidStart = 0; // millis() when AVOIDING began
static unsigned long clearSince = 0; // millis() when sensors first went clear

// ── Init ──────────────────────────────────────────────────────────────────────
void initWallAvoidance()
{
  if (!IMU.begin())
  {
    Serial.println("IMU init failed!");
    while (1)
      ;
  }
  pinMode(TRIG_PIN1, OUTPUT);
  pinMode(ECHO_PIN1, INPUT);
  pinMode(TRIG_PIN2, OUTPUT);
  pinMode(ECHO_PIN2, INPUT);
  lastTime = millis();
}

// ── Gyro ──────────────────────────────────────────────────────────────────────
void updateGyroAngle()
{
  if (IMU.gyroscopeAvailable())
  {
    IMU.readGyroscope(gx, gy, gz);
    float now = millis();
    float dt = (now - lastTime) / 1000.0;
    lastTime = now;
    currentGyroAngle += gz * dt;
    if (currentGyroAngle > 180)
      currentGyroAngle -= 360;
    if (currentGyroAngle < -180)
      currentGyroAngle += 360;
    turnAmount = currentGyroAngle;
  }
}

// ── Sensor read ───────────────────────────────────────────────────────────────
float getDistance(int trigPin, int echoPin)
{
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  // Timeout 8700 µs ≈ 150 cm max; keeps blocking time under 9 ms per sensor
  unsigned long dur = pulseIn(echoPin, HIGH, 8700);
  if (dur == 0)
    return 0;
  return (dur * 0.0343f) / 2.0f;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
float determineTurnAngle(float d1, float d2)
{
  float base = ((APPROACH_DISTANCE - minDistance) / APPROACH_DISTANCE) * (MAX_TURN_ANGLE - 15.0f) + 15.0f;
  base = constrain(base, 15.0f, MAX_TURN_ANGLE);
  if (d1 < d2)
    return -base; // left sensor closer → turn right (negative)
  if (d2 < d1)
    return base; // right sensor closer → turn left (positive)
  return (currentGyroAngle < 0) ? -base : base;
}

// Proportional speed: full at APPROACH_DISTANCE, minimum 30 at STOP_DISTANCE
int approachSpeed(float dist)
{
  float ratio = (dist - STOP_DISTANCE) / (APPROACH_DISTANCE - STOP_DISTANCE);
  ratio = constrain(ratio, 0.0f, 1.0f);
  return (int)(30 + ratio * 70); // 30..100
}

bool isValidReading(float d)
{
  return d > 1.0f && d < 300.0f;
}

float getWallAngle() { return wallAngle; }
float getTurnAmount() { return turnAmount; }
bool isWallDetected() { return minDistance < STOP_DISTANCE && minDistance > 0; }

// ── Main update — call from loop() once per sensor cycle ─────────────────────
void updateWallAvoidance()
{
  // 1. Read sensors (interleaved with 15 ms gap to prevent crosstalk)
  float d1 = getDistance(TRIG_PIN1, ECHO_PIN1);
  delay(15);
  float d2 = getDistance(TRIG_PIN2, ECHO_PIN2);

  updateGyroAngle();

  unsigned long now = millis();

  // 2. Validate readings
  if (!isValidReading(d1) || !isValidReading(d2))
  {
    Serial.print("ULTRASONIC: ERROR - Invalid Reading (d1: ");
    Serial.print(d1, 1);
    Serial.print(", d2: ");
    Serial.print(d2, 1);
    Serial.println(")");
    // Safe fallback: stop until we get good data
    Serial.println("CMD:STOP");
    return;
  }

  // 3. Update derived values
  wallAngle = atan((d2 - d1) / L) * (180.0f / M_PI);
  minDistance = min(d1, d2);

  // 4. Send raw sensor report (Pi uses this for dashboard / data logging)
  if (minDistance < APPROACH_DISTANCE)
  {
    float angle = determineTurnAngle(d1, d2);
    Serial.print("ULTRASONIC: WALL:");
    Serial.print(d1, 1);
    Serial.print(",");
    Serial.print(d2, 1);
    Serial.print(",");
    Serial.println(angle, 1);
  }
  else
  {
    Serial.println("ULTRASONIC: SAFE");
  }

  // 5. State machine
  switch (avoidState)
  {

  // ── CRUISING: full speed, path clear ────────────────────────────────────
  case CRUISING:
    if (minDistance < STOP_DISTANCE)
    {
      // Jump straight to AVOIDING — wall came up fast
      avoidState = AVOIDING;
      avoidStart = now;
      turnedSoFar = 0;
      gyroAtStart = currentGyroAngle;
      turnDir = (d1 <= d2) ? -1 : 1; // turn away from closer sensor
      Serial.println("CMD:STOP");
    }
    else if (minDistance < APPROACH_DISTANCE)
    {
      avoidState = APPROACH;
      Serial.print("CMD:FORWARD:");
      Serial.println(approachSpeed(minDistance));
    }
    else
    {
      Serial.println("CMD:FORWARD");
    }
    break;

  // ── APPROACH: slowing down, may steer gently ────────────────────────────
  case APPROACH:
    if (minDistance < STOP_DISTANCE)
    {
      avoidState = AVOIDING;
      avoidStart = now;
      turnedSoFar = 0;
      gyroAtStart = currentGyroAngle;
      turnDir = (d1 <= d2) ? -1 : 1;
      Serial.println("CMD:STOP");
    }
    else if (minDistance >= APPROACH_DISTANCE)
    {
      avoidState = CRUISING;
      Serial.println("CMD:FORWARD");
    }
    else
    {
      // Still in approach zone — proportional speed + gentle steer bias
      int spd = approachSpeed(minDistance);
      if (d1 < d2 - 5)
      {
        // Left sensor significantly closer — nudge right
        Serial.print("CMD:RIGHT:");
        Serial.println(spd);
      }
      else if (d2 < d1 - 5)
      {
        Serial.print("CMD:LEFT:");
        Serial.println(spd);
      }
      else
      {
        Serial.print("CMD:FORWARD:");
        Serial.println(spd);
      }
    }
    break;

  // ── AVOIDING: stopped and turning ───────────────────────────────────────
  case AVOIDING:
    // Timeout guard
    if (now - avoidStart > AVOID_TIMEOUT_MS)
    {
      avoidState = STUCK;
      Serial.println("CMD:STOP");
      Serial.println("STATUS:STUCK");
      break;
    }
    // Track how far we have turned using the gyro
    turnedSoFar = abs(currentGyroAngle - gyroAtStart);
    if (turnedSoFar > 180)
      turnedSoFar = 360 - turnedSoFar; // handle wrap

    if (turnedSoFar >= TARGET_TURN_DEG && minDistance >= CLEAR_DISTANCE)
    {
      // Turn complete AND sensors already clear — go straight to CONFIRM
      avoidState = CONFIRM;
      clearSince = now;
      Serial.println("CMD:STOP");
    }
    else if (turnedSoFar >= TARGET_TURN_DEG)
    {
      // Turn complete but still too close — keep turning
      if (turnDir > 0)
        Serial.println("CMD:LEFT");
      else
        Serial.println("CMD:RIGHT");
    }
    else
    {
      // Still working through the turn
      if (turnDir > 0)
        Serial.println("CMD:LEFT");
      else
        Serial.println("CMD:RIGHT");
    }
    break;

  // ── CONFIRM: sensors clear, holding briefly before resuming ─────────────
  case CONFIRM:
    if (minDistance < STOP_DISTANCE)
    {
      // Another wall appeared — go back to AVOIDING
      avoidState = AVOIDING;
      avoidStart = now;
      turnedSoFar = 0;
      gyroAtStart = currentGyroAngle;
      turnDir = (d1 <= d2) ? -1 : 1;
      Serial.println("CMD:STOP");
    }
    else if (minDistance < CLEAR_DISTANCE)
    {
      // Not clear enough yet — reset timer
      clearSince = now;
      Serial.println("CMD:STOP");
    }
    else if (now - clearSince >= CONFIRM_MS)
    {
      // Held clear for CONFIRM_MS → resume
      avoidState = CRUISING;
      Serial.println("CMD:FORWARD");
    }
    else
    {
      Serial.println("CMD:STOP");
    }
    break;

  // ── STUCK: operator must intervene ──────────────────────────────────────
  case STUCK:
    // Stay stopped. Pi will switch to manual mode.
    Serial.println("CMD:STOP");
    Serial.println("STATUS:STUCK");
    break;
  }
}
