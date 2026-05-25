"""
api/autonomous.py  –  The autonomous driving and sensor loop.
Extracted from pi_server so routes stay focused on HTTP concerns.
"""

import time
import threading
from config import SENSOR_SAVE_INTERVAL, MOISTURE_MODERATE
from state import state
from hardware import motors
from hardware.arduino import read_line, parse
from saveData import storage


def _determine_severity(moisture):
    from config import MOISTURE_CRITICAL, MOISTURE_MODERATE
    if moisture > MOISTURE_CRITICAL: return 'Critical'
    if moisture > MOISTURE_MODERATE: return 'Moderate'
    return 'Minor'


def read_sensors():
    """
    STUB — replace with real sensor reads.
    Return a dict or None if not ready.
    Expected keys: gps_lat, gps_lng, moisture, ir_temp
    """
    return {
        'gps_lat':  -37.81,
        'gps_lng':  144.96,
        'moisture': 52.2,
        'ir_temp':  22.1,
    }


def _loop():
    print("[Auto] loop started")
    last_save = 0.0

    while state['running']:
        if state['mode'] != 'autonomous':
            time.sleep(0.1)
            continue

        # ── Wall avoidance ─────────────────────────────────────────────────────
        line   = read_line()
        parsed = parse(line)
        if parsed:
            if parsed['type'] == 'wall':
                rem = parsed['remaining']
                if rem > 5:
                    motors.turn_left_angle(rem) if rem > 0 else motors.turn_right_angle(abs(rem))
                else:
                    motors.forward()
            elif parsed['type'] == 'safe':
                motors.forward()

        # ── Sensor save ────────────────────────────────────────────────────────
        now = time.time()
        if now - last_save >= SENSOR_SAVE_INTERVAL:
            last_save = now
            try:
                sensor = read_sensors()
                if sensor:
                    severity   = _determine_severity(sensor['moisture'])
                    image_path = None

                    if sensor['moisture'] > MOISTURE_MODERATE:
                        from hardware import camera
                        image_path = camera.capture_image(
                            sensor['gps_lat'],
                            sensor['gps_lng'],
                            sensor['moisture'],
                        )

                    storage.add_moisture_reading(
                        gps_lat    = sensor['gps_lat'],
                        gps_lng    = sensor['gps_lng'],
                        moisture   = sensor['moisture'],
                        ir_temp    = sensor.get('ir_temp'),
                        image_path = image_path,
                        severity   = severity,
                    )

                    if severity == 'Critical':
                        motors.stop()
                        time.sleep(2)
                        if state['mode'] == 'autonomous':
                            motors.forward()

            except Exception as e:
                print(f"[Auto] sensor error: {e}")

        time.sleep(0.1)


def start():
    """Start the autonomous loop in a background daemon thread."""
    threading.Thread(target=_loop, daemon=True, name="AutonomousLoop").start()
