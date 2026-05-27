"""
api/autonomous.py  -  Autonomous drive loop.

Architecture change: the Arduino now owns the wall-avoidance state machine
and sends CMD: drive commands over serial.  This module executes those
commands on the Pi's L298N GPIO via hardware.motors, and handles all
sensor data (moisture, GPS, status messages).

Serial messages consumed here:
  CMD:FORWARD[:<speed>]   execute motors.forward(speed)
  CMD:LEFT[:<speed>]      execute motors.left(speed)
  CMD:RIGHT[:<speed>]     execute motors.right(speed)
  CMD:STOP                execute motors.stop()
  ULTRASONIC: ...         update sensor state (dashboard / health)
  MOISTURE:<raw>,<label>  update sensor state, save if threshold exceeded
  GPS:<lat>,<lng>         update GPS state
  GPS:NO_FIX              update GPS state
  STATUS:STUCK            switch to manual, notify operator
"""

import time
import threading
from config import SENSOR_SAVE_INTERVAL, MOISTURE_MODERATE, MOTOR_DEFAULT_SPEED
from state import state
from hardware import motors
from hardware.arduino import read_line, parse
from saveData import storage


# ── Severity helper ───────────────────────────────────────────────────────────
def _determine_severity(moisture):
    from config import MOISTURE_CRITICAL, MOISTURE_MODERATE
    if moisture > MOISTURE_CRITICAL: return 'Critical'
    if moisture > MOISTURE_MODERATE: return 'Moderate'
    return 'Minor'


# ── Shared sensor state ───────────────────────────────────────────────────────
_sensor_state = {
    'gps_lat':             None,
    'gps_lng':             None,
    'moisture':            None,
    'moisture_raw':        None,
    'moisture_label':      None,
    'ultrasonic_status':   None,   # 'safe' | 'wall' | 'error'
    'ultrasonic_distance': None,
    'gps_status':          None,   # 'ok' | 'no_fix'
    'last_cmd':            None,   # last CMD: string from Arduino
}
_sensor_lock = threading.Lock()


def read_sensors():
    """Return a snapshot of the latest sensor state, or None if no data yet."""
    with _sensor_lock:
        if _sensor_state['moisture'] is None:
            return None
        return dict(_sensor_state)


# ── Message handlers ──────────────────────────────────────────────────────────

def _handle_cmd(parsed):
    """
    Execute a drive command sent by the Arduino state machine.
    Only runs when mode == 'autonomous'; CMD:STOP always executes.
    Returns True if a command was executed.
    """
    cmd   = parsed.get('cmd')       # 'FORWARD' | 'LEFT' | 'RIGHT' | 'STOP'
    speed = parsed.get('speed')     # int or None → use default

    if cmd is None:
        return False

    with _sensor_lock:
        _sensor_state['last_cmd'] = cmd

    is_stop = (cmd == 'STOP')

    # STOP always executes regardless of mode
    if not (state['mode'] == 'autonomous' or is_stop):
        return False

    kwargs = {} if speed is None else {'speed': speed}

    if cmd == 'FORWARD':
        motors.forward(**kwargs)
    elif cmd == 'LEFT':
        motors.left(**kwargs)
    elif cmd == 'RIGHT':
        motors.right(**kwargs)
    elif cmd == 'STOP':
        motors.stop()
    else:
        return False

    return True


def _handle_status(parsed):
    """Handle STATUS: messages (e.g. STUCK)."""
    status = parsed.get('status_msg')
    if status == 'STUCK':
        print("[Auto] ⚠ Arduino reports STUCK — switching to manual mode")
        motors.stop()
        state['mode'] = 'manual'


def _process_parsed(parsed):
    """Update shared sensor state from any parsed Arduino message."""
    if parsed is None:
        return

    t = parsed.get('type')

    if t == 'cmd':
        _handle_cmd(parsed)

    elif t == 'status':
        _handle_status(parsed)

    elif t == 'ultrasonic':
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
                _sensor_state['moisture_label'] = 'THRESHOLD_TRIGGERED'

    elif t == 'gps':
        with _sensor_lock:
            _sensor_state['gps_status'] = parsed.get('status')
            _sensor_state['gps_lat']    = parsed.get('lat')
            _sensor_state['gps_lng']    = parsed.get('lng')


# ── Main loop ─────────────────────────────────────────────────────────────────

def _loop():
    print("[Auto] loop started — Arduino is driving, Pi is executing")
    last_save = 0.0

    while state['running']:
        if state['mode'] != 'autonomous':
            motors.stop()
            time.sleep(0.1)
            continue

        # Read and dispatch one Arduino message per iteration
        line   = read_line()
        parsed = parse(line)

        if parsed:
            _process_parsed(parsed)

            if parsed.get('type') == 'gps':
                if parsed.get('status') == 'no_fix':
                    print("[Auto] GPS: no fix yet")
                else:
                    print(f"[Auto] GPS fix: {parsed['lat']:.5f}, {parsed['lng']:.5f}")

        else:
            if line and not line.startswith('READY'):
                print(f"[Auto] parse failed: {repr(line)}")

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

                storage.add_moisture_reading(
                    gps_lat    = sensor.get('gps_lat'),
                    gps_lng    = sensor.get('gps_lng'),
                    moisture   = sensor['moisture'],
                    image_path = image_path,
                    severity   = severity,
                )

                gps_str = (f"({sensor['gps_lat']:.5f}, {sensor['gps_lng']:.5f})"
                           if sensor.get('gps_lat') else "(NO FIX)")
                print(f"[Auto] saved: moisture={sensor['moisture']:.1f}%"
                      f" severity={severity} gps={gps_str}"
                      f" last_cmd={sensor.get('last_cmd')}")

                # Critical moisture: stop briefly, then let Arduino resume
                if severity == 'Critical' and state['mode'] == 'autonomous':
                    motors.stop()
                    time.sleep(1)

            except Exception as e:
                print(f"[Auto] sensor error: {e}")

        # Tight loop — Arduino sends at ~10 Hz, we want to keep up
        time.sleep(0.02)


def start():
    """Start the autonomous loop in a background daemon thread."""
    threading.Thread(target=_loop, daemon=True, name="AutonomousLoop").start()
    print("[Auto] started")