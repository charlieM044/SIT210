"""
api/autonomous.py  –  The autonomous driving and sensor loop.
Reads real sensor data from Arduino serial messages.
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


# ── Shared sensor state (updated by Arduino messages) ─────────────────────────
_sensor_state = {
    'gps_lat':  None,
    'gps_lng':  None,
    'moisture': None,
    'moisture_raw': None,
    'moisture_label': None,
    'ultrasonic_status': None,  # 'safe' | 'wall' | 'error'
    'ultrasonic_distance': None,
    'gps_status': None,         # 'ok' | 'no_fix'
}
_sensor_lock = threading.Lock()


def read_sensors():
    """
    Return latest sensor state dict, or None if no data yet.
    Populated by _process_parsed() as Arduino messages arrive.
    Returns a deep copy to prevent race conditions.
    """
    with _sensor_lock:
        if _sensor_state['moisture'] is None:
            return None
        return dict(_sensor_state)


def _process_parsed(parsed):
    """
    Update shared sensor state from a parsed Arduino message.
    Called every loop iteration so state stays current.
    """
    if parsed is None:
        return

    t = parsed.get('type')

    if t == 'ultrasonic':
        with _sensor_lock:
            _sensor_state['ultrasonic_status']   = parsed.get('status')
            _sensor_state['ultrasonic_distance'] = parsed.get('distance')

    elif t == 'moisture':
        with _sensor_lock:
            if parsed.get('status') == 'ok':
                _sensor_state['moisture']       = parsed.get('percent')
                _sensor_state['moisture_raw']   = parsed.get('raw')
                _sensor_state['moisture_label'] = parsed.get('label')
            elif parsed.get('status') == 'threshold_triggered':
                # Keep last moisture value but flag it
                _sensor_state['moisture_label'] = 'THRESHOLD_TRIGGERED'

    elif t == 'gps':
        with _sensor_lock:
            _sensor_state['gps_status'] = parsed.get('status')
            _sensor_state['gps_lat']    = parsed.get('lat')
            _sensor_state['gps_lng']    = parsed.get('lng')


def _handle_wall_avoidance(parsed, now, last_turn_time):
    """
    Drive motors based on ultrasonic parsed message.
    Returns True if a wall action was taken.
    Prevents rapid repeated turns with 2-second debounce.
    """
    if parsed is None or parsed.get('type') != 'ultrasonic':
        return False

    status = parsed.get('status')

    if status == 'safe':
        motors.forward()
        return False

    if status == 'error':
        # One sensor failed — slow down but keep going
        d1 = parsed.get('d1')
        d2 = parsed.get('d2')
        print(f"[Auto] ultrasonic error d1={d1} d2={d2} — slowing")
        motors.forward(speed=30)
        return False

    if status == 'ok':
        dist = parsed.get('distance', 100)
        wall = parsed.get('wall', False)
        
        # Only turn if close AND haven't turned recently (2s debounce)
        if (wall or dist < 15) and (now - last_turn_time >= 2.0):
            print(f"[Auto] wall at {dist:.1f}cm — turning left")
            motors.turn_left_angle(20)  # Smaller turn (20° instead of 30°)
            return True
        else:
            motors.forward()  # Always move forward unless turning
            return False

    return False


def _loop():
    print("[Auto] loop started")
    last_save = 0.0
    last_motor_cmd = 0.0  # Debounce motor commands to 1 per second
    last_turn_time = 0.0  # Debounce wall turns to once every 2 seconds
    turning_until = 0.0   # Timestamp when turn finishes

    while state['running']:
        if state['mode'] != 'autonomous':
            time.sleep(0.1)
            continue

        # ── Read + parse Arduino message ───────────────────────────────────────
        line   = read_line()
        parsed = parse(line)

        if parsed:
            _process_parsed(parsed)
            
            # Debounce motor commands to prevent rapid stuttering
            now = time.time()
            if now - last_motor_cmd >= 1.0:  # Only update motors once per second
                # If currently turning, don't override until turn finishes
                if now < turning_until:
                    # Still turning, keep current motor state
                    pass
                else:
                    # Turn finished or not turning, handle wall avoidance
                    if _handle_wall_avoidance(parsed, now, last_turn_time):
                        last_turn_time = now
                        turning_until = now + 1.5  # Stay in turn for 1.5 seconds
                last_motor_cmd = now

            # Log moisture threshold triggers immediately
            if (parsed.get('type') == 'moisture'
                    and parsed.get('status') == 'threshold_triggered'):
                print("[Auto] ⚠ moisture threshold triggered by Arduino")

            # Log GPS fix status changes
            if parsed.get('type') == 'gps':
                if parsed.get('status') == 'no_fix':
                    print("[Auto] GPS: no fix yet")
                else:
                    print(f"[Auto] GPS fix: {parsed.get('lat'):.5f}, {parsed.get('lng'):.5f}")
        else:
            # Log parse failures for debugging
            if line and not line.startswith('READY'):
                print(f"[Auto] parse failed: {line}")

        # ── Periodic sensor save ───────────────────────────────────────────────
        now = time.time()
        if now - last_save >= SENSOR_SAVE_INTERVAL:
            last_save = now
            try:
                sensor = read_sensors()

                if sensor is None:
                    print("[Auto] no sensor data yet — waiting for Arduino")
                    continue

                severity   = _determine_severity(sensor['moisture'])
                image_path = None

                # Capture image regardless of GPS status
                # GPS coordinates can be null, but image is still valuable
                if sensor['moisture'] > MOISTURE_MODERATE:
                    from hardware import camera
                    try:
                        image_path = camera.capture_image(
                            sensor.get('gps_lat'),
                            sensor.get('gps_lng'),
                            sensor['moisture'],
                        )
                    except Exception as e:
                        print(f"[Auto] image capture failed: {e}")

                # Save regardless of GPS status — GPS can be null
                storage.add_moisture_reading(
                    gps_lat    = sensor.get('gps_lat'),  # May be None
                    gps_lng    = sensor.get('gps_lng'),  # May be None
                    moisture   = sensor['moisture'],
                    image_path = image_path,
                    severity   = severity,
                )

                gps_str = f"({sensor['gps_lat']}, {sensor['gps_lng']})" if sensor.get('gps_lat') else "(NO FIX)"
                print(f"[Auto] saved: moisture={sensor['moisture']:.1f}%"
                      f" ({sensor.get('moisture_label', '')}) "
                      f"severity={severity} gps={gps_str}")

                if severity == 'Critical':
                    motors.stop()
                    time.sleep(1)  # Reduced from 2s to 1s to minimize stutter
                    if state['mode'] == 'autonomous':
                        motors.forward()

            except Exception as e:
                print(f"[Auto] sensor error: {e}")

        time.sleep(0.05)  # tighter loop = faster ultrasonic response


def start():
    """Start the autonomous loop in a background daemon thread."""
    threading.Thread(target=_loop, daemon=True, name="AutonomousLoop").start()
    print("[Auto] started")
