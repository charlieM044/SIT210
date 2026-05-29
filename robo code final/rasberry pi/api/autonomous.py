"""
api/autonomous.py  –  The autonomous driving and sensor loop.
Reads real sensor data from Arduino serial messages.
"""

import time
import threading
from datetime import datetime
from config import (
    SENSOR_SAVE_INTERVAL,
    MOISTURE_DRY_RAW,
    MOISTURE_WET_RAW,
)
from state import state
from hardware import motors
from hardware.arduino import read_line, parse, clear_buffer
from saveData import storage


def _label_to_severity(label):
    mapping = {
        'WET': 'Critical',
        'MOIST': 'Moderate',
        'DRY': 'Minor',
        'THRESHOLD_TRIGGERED': 'Critical',
    }
    return mapping.get((label or '').strip().upper(), 'Minor')


def _raw_to_percent(raw_value):
    span = MOISTURE_WET_RAW - MOISTURE_DRY_RAW
    if span == 0:
        return 0.0
    percent = ((MOISTURE_WET_RAW - raw_value) / span) * 100.0
    return max(0.0, min(100.0, percent))


def _build_reading_snapshot(sensor):
    return {
        'moisture': sensor['moisture'],
        'moisture_instant': sensor.get('moisture_instant'),
        'moisture_label': sensor.get('moisture_label', ''),
        'moisture_raw': sensor.get('moisture_raw'),
        'severity': sensor.get('severity', 'Minor'),
        'gps_lat': sensor.get('gps_lat'),
        'gps_lng': sensor.get('gps_lng'),
        'timestamp': datetime.now().isoformat(),
    }


# ── Shared sensor state (updated by Arduino messages) ─────────────────────────
_sensor_state = {
    'gps_lat':  None,
    'gps_lng':  None,
    'moisture': None,
    'moisture_instant': None,
    'moisture_raw': None,
    'moisture_label': None,
    'severity': 'Minor',
    'moisture_updated_at': 0.0,
    'gps_updated_at': 0.0,
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
                raw = parsed.get('raw')
                if raw is not None:
                    _sensor_state['moisture_raw'] = raw
                    _sensor_state['moisture_instant'] = round(_raw_to_percent(raw), 1)
                    _sensor_state['moisture'] = _sensor_state['moisture_instant']
                _sensor_state['moisture_label'] = parsed.get('label')
                _sensor_state['severity'] = _label_to_severity(parsed.get('label'))
                _sensor_state['moisture_updated_at'] = time.time()
            elif parsed.get('status') == 'threshold_triggered':
                # Keep last moisture value but flag it
                _sensor_state['moisture_label'] = 'THRESHOLD_TRIGGERED'
                _sensor_state['severity'] = 'Critical'

    elif t == 'gps':
        with _sensor_lock:
            _sensor_state['gps_status'] = parsed.get('status')
            _sensor_state['gps_lat']    = parsed.get('lat')
            _sensor_state['gps_lng']    = parsed.get('lng')
            _sensor_state['gps_updated_at'] = time.time()

            if _sensor_state['moisture'] is not None:
                state['latest_reading'] = _build_reading_snapshot(_sensor_state)


def _handle_wall_avoidance(parsed, now, avoiding_wall, safe_since):
    """
    Simpler wall avoidance: Stop and turn until safe for 3 seconds, then resume.
    
    Returns: (avoiding_wall, safe_since) — updated state flags
    """
    if parsed is None or parsed.get('type') != 'ultrasonic':
        return avoiding_wall, safe_since

    status = parsed.get('status')

    if status == 'error':
        # Sensor error — slow down but keep going
        print(f"[Auto] ultrasonic error, slowing")
        motors.forward(speed=30)
        return avoiding_wall, safe_since

    if status in ('safe', 'ok'):
        dist = parsed.get('distance', 100)
        
        # WALL DETECTED: Stop and turn
        if dist < 15:
            if not avoiding_wall:
                print(f"[Auto] WALL DETECTED at {dist:.1f}cm — STOP and TURN")
                avoiding_wall = True
                safe_since = 0
            motors.stop()
            motors.left(speed=40)  # Gentle left turn to find safe path
            return avoiding_wall, safe_since
        
        # SAFE DISTANCE: Check if we've been safe long enough
        if avoiding_wall:
            # Still avoiding, waiting to confirm safe
            if dist >= 20:  # Need 20cm+ to be sure it's safe
                if safe_since == 0:
                    # First time seeing safe distance
                    safe_since = now
                    print(f"[Auto] Distance safe at {dist:.1f}cm — waiting 3 sec to confirm...")
                elif (now - safe_since) >= 3.0:
                    # Been safe for 3 seconds, resume motion
                    print(f"[Auto] Safe for 3 sec — RESUME FORWARD")
                    avoiding_wall = False
                    safe_since = 0
                    motors.forward()
                else:
                    # Still counting down safety timer
                    remaining = 3.0 - (now - safe_since)
                    print(f"[Auto] Waiting... {remaining:.1f}s remaining (distance: {dist:.1f}cm)")
                    motors.stop()
            else:
                # Dropped below 20cm again, reset timer
                print(f"[Auto] Distance dropped to {dist:.1f}cm — resetting safety timer")
                safe_since = 0
                motors.stop()
                motors.left(speed=40)
        else:
            # Not avoiding, path is clear
            motors.forward()
        
        return avoiding_wall, safe_since

    # Default safe behavior
    motors.forward()
    return avoiding_wall, safe_since


def _loop():
    print("[Auto] loop started")
    last_save = 0.0
    last_saved_moisture_at = 0.0
    last_motor_cmd = 0.0  # Debounce motor commands to 1 per second
    avoiding_wall = False  # Currently in wall avoidance
    safe_since = 0.0       # When we last detected "safe" distance

    while state['running']:
        
          # ── Read + parse Arduino message ───────────────────────────────────────
        line   = read_line()
        parsed = parse(line)
        
        
     

        if parsed:
            _process_parsed(parsed)
            if state['mode'] == 'autonomous':
            
                # Debounce motor commands to prevent rapid stuttering
                now = time.time()
                if now - last_motor_cmd >= 1.0:  # Only update motors once per second
                    avoiding_wall, safe_since = _handle_wall_avoidance(parsed, now, avoiding_wall, safe_since)
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
        if now - last_save >= SENSOR_SAVE_INTERVAL and parsed:
            should_save = (
                parsed.get('type') == 'gps'
                and parsed.get('status') in ('ok', 'no_fix')
            )

            if should_save:
                with _sensor_lock:
                    sensor = dict(_sensor_state)

                if sensor['moisture'] is not None and sensor['moisture_updated_at'] > last_saved_moisture_at:
                    last_save = now
                    try:
                        reading_time = datetime.now()
                        severity   = sensor.get('severity', 'Minor')
                        image_path = None

                        # Capture image regardless of GPS status
                        # GPS coordinates can be null, but image is still valuable
                        if sensor.get('severity') != 'Minor':
                            from hardware import camera
                            try:
                                image_path = camera.capture_image(
                                    sensor.get('gps_lat'),
                                    sensor.get('gps_lng'),
                                    sensor['moisture'],
                                    captured_at=reading_time,
                                )
                            except Exception as e:
                                print(f"[Auto] image capture failed: {e}")

                        latest_reading = _build_reading_snapshot(sensor)
                        latest_reading['timestamp'] = reading_time.isoformat(sep=' ', timespec='seconds')
                        state['latest_reading'] = latest_reading

                        # Save to disk database in the background
                        storage.add_moisture_reading(
                            gps_lat    = sensor.get('gps_lat'),
                            gps_lng    = sensor.get('gps_lng'),
                            moisture   = sensor['moisture'],
                            image_path = image_path,
                            severity   = severity,
                            reading_time = reading_time,
                        )
                        last_saved_moisture_at = sensor['moisture_updated_at']

                        gps_str = f"({sensor['gps_lat']}, {sensor['gps_lng']})" if sensor.get('gps_lat') else "(NO FIX)"
                        print(f"[Auto] saved: moisture={sensor['moisture']:.1f}%"
                              f" ({sensor.get('moisture_label', '')}) "
                              f"severity={severity} gps={gps_str}")

                        if severity == 'Critical' and state['mode'] == 'autonomous':
                            motors.stop()
                            time.sleep(1)
                            motors.forward()
                            clear_buffer()  # Clear buffer to prevent old messages from triggering again
                            print("[Auto] CRITICAL moisture level — stopping briefly and resuming")
                    except Exception as e:
                        print(f"[Auto] sensor error: {e}")

        time.sleep(0.05)  # tighter loop = faster ultrasonic response


def start():
    """Start the autonomous loop in a background daemon thread."""
    threading.Thread(target=_loop, daemon=True, name="AutonomousLoop").start()
    print("[Auto] started")