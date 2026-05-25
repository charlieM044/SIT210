"""
health.py  -  Hardware health monitor with functional gates.

Each check sets a capability flag. autonomous.py reads these before acting.

Capabilities:
  CAN_DRIVE        - motors + arduino wall avoidance both healthy
  CAN_AVOID_WALLS  - arduino sending valid ultrasonic data
  CAN_SAVE_DATA    - storage/DB writable
  CAN_CAPTURE      - camera working
  CAN_GPS          - GPS returning valid non-stub coordinates
"""

import threading
import time
import copy
from datetime import datetime

_lock = threading.Lock()

_health = {
    'arduino': {'ok': None, 'error': None, 'last_check': None, 'last_ok': None, 'detail': None},
    'camera':  {'ok': None, 'error': None, 'last_check': None, 'last_ok': None, 'detail': None},
    'motors':  {'ok': None, 'error': None, 'last_check': None, 'last_ok': None, 'detail': None},
    'storage': {'ok': None, 'error': None, 'last_check': None, 'last_ok': None, 'detail': None},
    'gps':     {'ok': None, 'error': None, 'last_check': None, 'last_ok': None, 'detail': None},
    'ultrasonic': {'ok': None, 'error': None, 'last_check': None, 'last_ok': None, 'detail': None},
}

# ── Capability flags (read by autonomous.py) ───────────────────────────────────
capabilities = {
    'CAN_DRIVE':       False,
    'CAN_AVOID_WALLS': False,
    'CAN_SAVE_DATA':   False,
    'CAN_CAPTURE':     False,
    'CAN_GPS':         False,
    'CAN_AVOID_WALLS': False,
}


def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _set(component, ok, detail=None, error=None):
    with _lock:
        _health[component]['ok']         = ok
        _health[component]['last_check'] = _now()
        _health[component]['detail']     = detail
        _health[component]['error']      = error
        if ok:
            _health[component]['last_ok'] = _now()
    _update_capabilities()


def _update_capabilities():
    with _lock:
        h = _health
        capabilities['CAN_AVOID_WALLS'] = bool(h['arduino']['ok'])
        capabilities['CAN_DRIVE']       = bool(h['motors']['ok'] and h['arduino']['ok'])
        capabilities['CAN_SAVE_DATA']   = bool(h['storage']['ok'])
        capabilities['CAN_CAPTURE']     = bool(h['camera']['ok'])
        capabilities['CAN_GPS']         = bool(h['gps']['ok'])


# ── Individual checks ──────────────────────────────────────────────────────────

def check_arduino():
    try:
        from hardware.arduino import arduino, read_line, parse
        if arduino is None:
            _set('arduino', False,
                 detail='Serial object is None',
                 error='Port failed to open — check SERIAL_PORT in config')
            return

        if not arduino.in_waiting:
            _set('arduino', False,
                 detail='Serial open but no data',
                 error='Arduino connected but silent — check power and baud rate')
            return

        line   = read_line()
        parsed = parse(line)
        if parsed is None:
            _set('arduino', False,
                 detail=f'Unparseable: {repr(line)}',
                 error='Data received but format not recognised — expected SAFE or WALL:...')
            return

        _set('arduino', True, detail=f'type={parsed["type"]} raw={repr(line)}')

    except Exception as e:
        _set('arduino', False, error=str(e))


def check_camera():
    try:
        from hardware.camera import camera
        if camera.use_picamera2 and camera.picamera2:
            _set('camera', True, detail='picamera2 active')
            return
        if camera.camera is not None:
            backend = 'picamera' if not hasattr(camera.camera, 'read') else 'OpenCV'
            _set('camera', True, detail=f'{backend} active')
            return
        frame = camera._get_frame()
        if frame is not None:
            _set('camera', True, detail='frame captured OK')
        else:
            _set('camera', False,
                 detail='No camera backend initialised',
                 error='All camera backends failed — check camera connection')
    except Exception as e:
        _set('camera', False, error=str(e))


def check_motors():
    try:
        from hardware.motors import motors
        from config import IS_PI
        if not IS_PI:
            _set('motors', True, detail='Mock GPIO (not on Pi)')
            return
        if motors.pwm1 is None or motors.pwm2 is None:
            _set('motors', False,
                 detail='PWM objects missing',
                 error='GPIO PWM not initialised — motors will not move')
            return
        _set('motors', True, detail=f'GPIO OK  current_speed={motors.current_speed}')
    except Exception as e:
        _set('motors', False, error=str(e))


def check_storage():
    try:
        import sqlite3
        from config import DB_PATH
        from saveData import storage
        with sqlite3.connect(DB_PATH, timeout=2) as conn:
            count = conn.execute(
                'SELECT COUNT(*) FROM moisture_readings'
            ).fetchone()[0]
        info = storage.get_storage_info()
        _set('storage', True,
             detail=(f'rows={count}  buffer={info["buffer_size"]}'
                     f'  {info["total_size_mb"]}MB  images={info["images"]}'))
    except Exception as e:
        _set('storage', False, error=str(e))


def check_gps():
    """
    Reads latest sensor data and validates GPS coordinates are real
    (not the stub -37.81, 144.96 placeholder in autonomous.py).
    Replace STUB_LAT/STUB_LNG if your stub values differ.
    """
    STUB_LAT, STUB_LNG = -37.81, 144.96
    try:
        from autonomous import read_sensors
        sensor = read_sensors()
        if sensor is None:
            _set('gps', False,
                 detail='read_sensors() returned None',
                 error='No sensor data available')
            return

        lat = sensor.get('gps_lat')
        lng = sensor.get('gps_lng')

        if lat is None or lng is None:
            _set('gps', False,
                 detail='lat/lng missing from sensor dict',
                 error='GPS fields not present in sensor data')
            return

        if lat == STUB_LAT and lng == STUB_LNG:
            _set('gps', False,
                 detail=f'Stub coordinates ({lat}, {lng})',
                 error='GPS returning placeholder values — no real fix acquired')
            return

        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            _set('gps', False,
                 detail=f'Out of range: ({lat}, {lng})',
                 error='GPS values outside valid range')
            return

        _set('gps', True, detail=f'fix=({lat:.5f}, {lng:.5f})')

    except Exception as e:
        _set('gps', False, error=str(e))

def check_ultrasonic():
    try:
        from hardware.arduino import arduino, read_line, parse
        if arduino is None:
            return False, 'Serial object is None'
        if not arduino.in_waiting:
            return False, 'Serial open but no data'
        line   = read_line()
        parsed = parse(line)
        if parsed is None or parsed.get('type') != 'wall':
            return False, f'Unparseable or wrong type: {repr(line)}'
        return True, f'type={parsed["type"]} raw={repr(line)}'
    except Exception as e:
        return False, str(e)
    
    
    
# ── Public API ─────────────────────────────────────────────────────────────────

def check_all():
    check_arduino()
    check_camera()
    check_ultrasonic()
    check_motors()
    check_storage()
    check_gps()


def get_health():
    with _lock:
        return copy.deepcopy(_health)


def get_capabilities():
    with _lock:
        return copy.deepcopy(capabilities)


def get_summary():
    h    = get_health()
    caps = get_capabilities()
    return {
        'hardware':     {k: v['ok']    for k, v in h.items()},
        'capabilities': caps,
        'all_ok':       all(v for v in caps.values()),
        'checked_at':   _now(),
    }


def can(capability):
    """Quick boolean gate. Usage: if health.can('CAN_DRIVE'): ..."""
    with _lock:
        return capabilities.get(capability, False)


# ── Background polling ─────────────────────────────────────────────────────────

def start_polling(interval=10):
    def _loop():
        while True:
            try:
                check_all()
            except Exception as e:
                print(f"[Health] poll error: {e}")
            time.sleep(interval)

    check_all()  # run immediately on start
    threading.Thread(target=_loop, daemon=True, name="HealthMonitor").start()
    print(f"[Health] monitoring every {interval}s")
