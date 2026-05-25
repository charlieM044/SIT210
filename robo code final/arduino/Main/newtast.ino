// /*
//   Ultrasonic sensors use pin-change interrupts to time echo pulses
//   so the main loop is never blocked waiting for a pulse to return.

//   Wall avoidance is strictly enforced: the robot will not resume
//   forward motion until BOTH sensors report clear AND the IMU
//   confirms the turn angle has been completed.

//   Serial output to Pi (9600 baud):
//     "SAFE"                         both sensors clear
//     "WALL:<remaining>,<angle>,<amount>"
//       remaining  cm until wall (minimum of both sensors)
//       angle      degrees from wall normal (+ = left, - = right)
//       amount     suggested turn magnitude 0-90
// */

// #include "ultrasonic.h"
// #include "moisture.h"

// // ── Interrupt state for sensor 1 ──────────────────────────────────────────────
// volatile unsigned long _echo1_start = 0;
// volatile unsigned long _echo1_dur   = 0;
// volatile bool          _echo1_ready = false;

// // ── Interrupt state for sensor 2 ──────────────────────────────────────────────
// volatile unsigned long _echo2_start = 0;
// volatile unsigned long _echo2_dur   = 0;
// volatile bool          _echo2_ready = false;

// // ── Timing ────────────────────────────────────────────────────────────────────
// unsigned long lastReport    = 0;
// const int     REPORT_MS     = 100;   // send to Pi every 100 ms

// // ── Wall state machine ────────────────────────────────────────────────────────
// // CLEAR      : both sensors show > SAFE_DISTANCE
// // AVOIDING   : wall detected, turn in progress
// // CONFIRMING : turn done, waiting for both sensors to read clear before moving
// enum WallState { CLEAR, AVOIDING, CONFIRMING };
// WallState wallState  = CLEAR;

// float targetAngle    = 0.0;   // how many degrees we need to turn
// float turnedSoFar    = 0.0;   // accumulated from gyro
// int   turnDirection  = 0;     // +1 = left, -1 = right


// // ── ISRs ──────────────────────────────────────────────────────────────────────
// void echo1ISR() {
//     if (digitalRead(ECHO_PIN1) == HIGH) {
//         _echo1_start = micros();
//     } else {
//         if (_echo1_start > 0) {
//             _echo1_dur   = micros() - _echo1_start;
//             _echo1_ready = true;
//             _echo1_start = 0;
//         }
//     }
// }

// void echo2ISR() {
//     if (digitalRead(ECHO_PIN2) == HIGH) {
//         _echo2_start = micros();
//     } else {
//         if (_echo2_start > 0) {
//             _echo2_dur   = micros() - _echo2_start;
//             _echo2_ready = true;
//             _echo2_start = 0;
//         }
//     }
// }


// // ── Trigger a pulse on one sensor ─────────────────────────────────────────────
// void triggerSensor(int trigPin) {
//     digitalWrite(trigPin, LOW);
//     delayMicroseconds(2);
//     digitalWrite(trigPin, HIGH);
//     delayMicroseconds(10);
//     digitalWrite(trigPin, LOW);
// }


// // ── Read latest interrupt-captured distance (cm) ──────────────────────────────
// float readDistance1() {
//     if (!_echo1_ready) return -1.0;   // no new reading yet
//     noInterrupts();
//     unsigned long dur = _echo1_dur;
//     _echo1_ready = false;
//     interrupts();
//     return dur / 58.0;
// }

// float readDistance2() {
//     if (!_echo2_ready) return -1.0;
//     noInterrupts();
//     unsigned long dur = _echo2_dur;
//     _echo2_ready = false;
//     interrupts();
//     return dur / 58.0;
// }


// // ── Determine best turn direction and magnitude from sensor readings ───────────
// /*
//   Logic:
//     If LEFT sensor is closer  -> turn RIGHT (away from left wall)
//     If RIGHT sensor is closer -> turn LEFT  (away from right wall)
//     If both equal             -> use gyro wall angle to decide

//   Turn magnitude scales with how close the wall is:
//     0 cm remaining -> 90 deg turn
//     SAFE_DISTANCE  -> 0 deg turn  (smooth ramp)
// */
// void computeTurn(float distL, float distR, float wallAngleDeg) {
//     float closest = min(distL, distR);
//     if (closest < 0) closest = SAFE_DISTANCE;   // sensor not ready, be safe

//     // Magnitude: 0 at SAFE_DISTANCE, 90 at 0 cm
//     targetAngle = constrain(
//         map(closest, 0, (int)SAFE_DISTANCE, 90, 0), 0, 90
//     );

//     // Direction: move away from the closer sensor
//     if (distL >= 0 && distR >= 0) {
//         turnDirection = (distL < distR) ? -1 : 1;   // -1=right, +1=left
//     } else {
//         // Only one sensor valid — use wall angle from IMU
//         turnDirection = (wallAngleDeg >= 0) ? 1 : -1;
//     }

//     turnedSoFar = 0.0;
// }


// void setup() {
//     Serial.begin(9600);

//     // Ultrasonic pins
//     pinMode(TRIG_PIN1, OUTPUT);
//     pinMode(TRIG_PIN2, OUTPUT);
//     pinMode(ECHO_PIN1, INPUT);
//     pinMode(ECHO_PIN2, INPUT);

//     // Attach interrupts to echo pins
//     attachInterrupt(digitalPinToInterrupt(ECHO_PIN1), echo1ISR, CHANGE);
//     attachInterrupt(digitalPinToInterrupt(ECHO_PIN2), echo2ISR, CHANGE);

//     // Moisture interrupt
//     pinMode(INTERRUPT_PIN, INPUT_PULLUP);
//     attachInterrupt(digitalPinToInterrupt(INTERRUPT_PIN),
//                     moistureThresholdISR, FALLING);

//     initWallAvoidance();   // starts IMU

//     Serial.println("READY");
// }


// void loop() {
//     // Trigger sensors on alternate ticks to avoid interference
//     static bool trigToggle = false;
//     trigToggle = !trigToggle;
//     triggerSensor(trigToggle ? TRIG_PIN1 : TRIG_PIN2);

//     // Read latest interrupt-captured distances
//     static float distL = SAFE_DISTANCE + 1;
//     static float distR = SAFE_DISTANCE + 1;
//     float d1 = readDistance1();
//     float d2 = readDistance2();
//     if (d1 > 0) distL = d1;
//     if (d2 > 0) distR = d2;

//     // Update gyro angle
//     updateGyroAngle();
//     float wallAngleDeg = getWallAngle();

//     // ── Wall avoidance state machine ──────────────────────────────────────────
//     float minDist = min(distL, distR);

//     switch (wallState) {

//         case CLEAR:
//             if (minDist <= SAFE_DISTANCE) {
//                 // Wall detected — compute turn and enter AVOIDING
//                 computeTurn(distL, distR, wallAngleDeg);
//                 wallState = AVOIDING;
//             }
//             break;

//         case AVOIDING:
//             // Accumulate how far we have turned using gyro
//             updateGyroAngle();
//             turnedSoFar += abs(wallAngleDeg);   // crude integration; replace with
//                                                  // proper gyro delta if available

//             if (turnedSoFar >= targetAngle) {
//                 // Turn complete — wait for sensors to confirm clear
//                 wallState = CONFIRMING;
//                 turnedSoFar = 0.0;
//             }
//             break;

//         case CONFIRMING:
//             if (distL > SAFE_DISTANCE && distR > SAFE_DISTANCE) {
//                 // Both sensors clear — safe to go forward
//                 wallState = CLEAR;
//             }
//             // If still too close, hold here (report will keep telling Pi WALL)
//             break;
//     }

//     // Read moisture (interrupt-driven, just read the volatile)
//     readMoisture();

//     // ── Serial report to Pi ───────────────────────────────────────────────────
//     if (millis() - lastReport >= REPORT_MS) {
//         lastReport = millis();

//         if (wallState == CLEAR) {
//             Serial.println("SAFE");
//         } else {
//             float remaining = max(minDist, 0.0f);
//             float angle     = turnDirection * targetAngle;
//             float amount    = targetAngle;
//             Serial.print("WALL:");
//             Serial.print(remaining, 1);
//             Serial.print(",");
//             Serial.print(angle, 1);
//             Serial.print(",");
//             Serial.println(amount, 1);
//         }
//     }

//     delay(10);
// }