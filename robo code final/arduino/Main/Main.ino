/*
  Main.ino  –  Entry point only.
  Hardware logic lives in ultrasonic.ino and moisture.ino.

  Serial output to Pi at 9600 baud:

    READY
    CMD:FORWARD              drive forward, full speed
    CMD:FORWARD:<speed>      drive forward at speed % (30-100)
    CMD:LEFT                 turn left
    CMD:LEFT:<speed>         turn left at speed %
    CMD:RIGHT                turn right
    CMD:RIGHT:<speed>        turn right at speed %
    CMD:STOP                 stop motors

    ULTRASONIC: SAFE
    ULTRASONIC: WALL:<d1>,<d2>,<angle>
    ULTRASONIC: ERROR - Invalid Reading (d1: x, d2: y)

    MOISTURE:<raw>,<DRY|MOIST|WET>
    GPS:<lat>,<lng>
    GPS:NO_FIX
    STATUS:STUCK             avoidance timed out, operator intervention needed
*/

#include "ultrasonic.h"
#include "moisture.h"
#include <TinyGPSPlus.h>

TinyGPSPlus gps;

// ── GPS helpers ───────────────────────────────────────────────────────────────
void feedGPS()
{
  unsigned long start = millis();
  // 50 ms budget — avoids blocking the sensor loop
  while (Serial1.available() && (millis() - start < 50))
  {
    gps.encode(Serial1.read());
  }
}

void sendGPS()
{
  if (gps.location.isValid())
  {
    Serial.print("GPS:");
    Serial.print(gps.location.lat(), 6);
    Serial.print(",");
    Serial.println(gps.location.lng(), 6);
  }
  else
  {
    Serial.println("GPS:NO_FIX");
  }
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup()
{
  Serial.begin(9600);
  Serial1.begin(115200); // GPS module
  initWallAvoidance();
  Serial.println("READY");
}

// ── Timing ────────────────────────────────────────────────────────────────────
unsigned long lastSensor = 0;
unsigned long lastReading = 0;

// Sensor cycle: 100 ms  (each getDistance blocks ~9 ms max + 15 ms gap = ~33 ms
// total sensor work; 100 ms period gives 67 ms of breathing room for GPS)
const unsigned long SONIC_INTERVAL = 100;
// Moisture + GPS: once per second
const unsigned long READING_INTERVAL = 1000;

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop()
{
  unsigned long now = millis();

  // GPS runs every iteration inside its own 50 ms budget
  feedGPS();

  // Ultrasonic + avoidance state machine at SONIC_INTERVAL
  if (now - lastSensor >= SONIC_INTERVAL)
  {
    lastSensor = now;
    updateWallAvoidance(); // reads sensors, updates state, sends CMD: + ULTRASONIC:
  }

  // Moisture + GPS report at READING_INTERVAL
  if (now - lastReading >= READING_INTERVAL)
  {
    lastReading = now;
    readMoisture();
    sendGPS();
  }
}
