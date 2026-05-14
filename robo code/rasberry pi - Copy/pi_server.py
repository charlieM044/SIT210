"""
pi_server.py  –  Flask API that runs directly on the Raspberry Pi
Fixes vs original:
  • Only ONE CameraManager instance ever created (passed in from main.py).
    The old code created two instances at module level, both grabbing /dev/video0.
  • autonomous_loop: 'severity' NameError fixed (was referenced outside
    'if sensor:' block).
  • autonomous_loop: motors.forward() is guarded by mode check at the top
    of each iteration rather than blindly on startup.
  • Storage writes are guarded so a None sensor doesn't cause a crash.
  • /api/status endpoint added (index.html polls it).
"""

from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from saveData import LocalDataManager
from motorcontroller import MotorController
from datetime import datetime
import threading
import time
import platform

app = Flask(__name__)
CORS(app)

# ── Singletons – camera is injected by main.py after import ───────────────────
_camera  = None          # set by set_camera() below
storage  = LocalDataManager('./robot_inspection_data')
motors   = MotorController()

def set_camera(cam):
    """Called by main.py to inject the shared CameraManager."""
    global _camera
    _camera = cam

# ── Arduino serial ─────────────────────────────────────────────────────────────
arduino     = None
SERIAL_PORT = '/dev/ttyACM0' if platform.machine() in ('armv7l', 'aarch64') else 'COM6'
try:
    import serial
    arduino = serial.Serial(SERIAL_PORT, 9600, timeout=1)
    time.sleep(2)
    print(f"[Pi] ✓ Arduino on {SERIAL_PORT}")
except Exception as e:
    print(f"[Pi] ⚠ No Arduino ({e})")

# ── Shared state ───────────────────────────────────────────────────────────────
state = {
    'mode':      'autonomous',
    'running':   True,
    'streaming': False,
    'start_time': time.time(),
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def _parse_arduino(line):
    if line == 'SAFE':
        return {'type': 'safe'}
    if line.startswith('WALL:'):
        try:
            parts = line[5:].split(',')
            return {
                'type':      'wall',
                'remaining': float(parts[0]),
                'angle':     float(parts[1]),
                'amount':    float(parts[2]),
            }
        except Exception:
            pass
    return None

def _determine_severity(moisture):
    if moisture > 80: return 'Critical'
    if moisture > 60: return 'Moderate'
    return 'Minor'

# ── Sensor stub – replace with real hardware reads ────────────────────────────
def read_sensors():
    """
    Replace with real ADC / I2C / UART sensor read.
    Return dict or None if not ready.
    """
    return {
        'gps_lat':  -37.81,
        'gps_lng':  144.96,
        'moisture': 52.2,
        'ir_temp':  22.1,
    }

# ── Autonomous loop ────────────────────────────────────────────────────────────
def autonomous_loop():
    print("[Auto] loop started")
    last_save_time = 0

    while state['running']:
        # Only drive in autonomous mode
        if state['mode'] != 'autonomous':
            time.sleep(0.1)
            continue

        # ── Wall avoidance ─────────────────────────────────────────────────────
        if arduino and arduino.in_waiting:
            try:
                raw    = arduino.readline().decode('utf-8', errors='replace').strip()
                parsed = _parse_arduino(raw)
                if parsed:
                    if parsed['type'] == 'wall':
                        rem = parsed['remaining']
                        if rem > 5:
                            if rem > 0:
                                motors.turn_left_angle(rem)
                            else:
                                motors.turn_right_angle(abs(rem))
                        else:
                            motors.forward()
                    elif parsed['type'] == 'safe':
                        motors.forward()
            except Exception as e:
                print(f"[Auto] Arduino error: {e}")

        # ── Sensor data ────────────────────────────────────────────────────────
        now = time.time()
        if now - last_save_time >= 5.0:
            last_save_time = now
            try:
                sensor = read_sensors()
                if sensor:
                    severity   = _determine_severity(sensor['moisture'])
                    image_path = None

                    if sensor['moisture'] > 60 and _camera:
                        image_path = _camera.capture_image(
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

# Start the autonomous loop (motors don't move until mode == 'autonomous')
threading.Thread(target=autonomous_loop, daemon=True, name="AutonomousLoop").start()

# ── Status ─────────────────────────────────────────────────────────────────────
@app.route('/api/status')
def api_status():
    return jsonify({
        'connected': True,
        'mode':      state['mode'],
        'uptime_s':  int(time.time() - state['start_time']),
        'message':   'Pi server running',
    })

# ── Mode ───────────────────────────────────────────────────────────────────────
@app.route('/api/mode', methods=['GET'])
def get_mode():
    return jsonify({'mode': state['mode']})

@app.route('/api/mode/manual', methods=['POST'])
def set_manual():
    state['mode'] = 'manual'
    motors.stop()
    print("[Pi] → MANUAL")
    return jsonify({'mode': 'manual'})

@app.route('/api/mode/autonomous', methods=['POST'])
def set_autonomous():
    state['mode'] = 'autonomous'
    motors.forward()
    print("[Pi] → AUTONOMOUS")
    return jsonify({'mode': 'autonomous'})

# ── Manual motor control ───────────────────────────────────────────────────────
def _manual_only(fn):
    if state['mode'] == 'manual':
        fn()
    return jsonify({'mode': state['mode']})

@app.route('/api/control/forward',    methods=['POST'])
def ctrl_forward():   return _manual_only(motors.forward)

@app.route('/api/control/backward',   methods=['POST'])
def ctrl_backward():  return _manual_only(motors.backward)

@app.route('/api/control/left',       methods=['POST'])
def ctrl_left():      return _manual_only(motors.left)

@app.route('/api/control/right',      methods=['POST'])
def ctrl_right():     return _manual_only(motors.right)

@app.route('/api/control/stop',       methods=['POST'])
@app.route('/api/control/stop-motors',methods=['POST'])
def ctrl_stop():      return _manual_only(motors.stop)

# ── Data endpoints ─────────────────────────────────────────────────────────────
@app.route('/api/readings')
def get_readings():
    since    = request.args.get('since', 0, type=float)
    readings = storage.get_all_readings()
    if since:
        readings = [r for r in readings
                    if r.get('timestamp', '') > datetime.fromtimestamp(since).isoformat()]
    return jsonify(readings)

@app.route('/api/stats')
def get_stats():
    stats = storage.get_moisture_stats()
    uptime = int(time.time() - state['start_time'])
    if stats is None:
        return jsonify({'count': 0, 'uptime': uptime})
    stats['uptime'] = uptime
    return jsonify(stats)

@app.route('/api/critical')
def get_critical():
    return jsonify([r for r in storage.get_all_readings()
                    if r.get('severity') == 'Critical'])

@app.route('/api/storage')
def get_storage():
    return jsonify(storage.get_storage_info())

# ── Video stream ───────────────────────────────────────────────────────────────
@app.route('/api/stream/start', methods=['POST'])
def stream_start():
    state['streaming'] = True
    if _camera:
        _camera.start_streaming()
    return jsonify({'streaming': True})

@app.route('/api/stream/stop', methods=['POST'])
def stream_stop():
    state['streaming'] = False
    if _camera:
        _camera.stop_streaming()
    return jsonify({'streaming': False})

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            if _camera:
                frame = _camera.get_frame()
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.1)   # 10 FPS cap to reduce bandwidth pressure

    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# ── Direct run (without main.py) ───────────────────────────────────────────────
if __name__ == '__main__':
    # In direct-run mode we create the camera here so the server still works
    from camera import CameraManager
    cam = CameraManager()
    set_camera(cam)
    cam.start_streaming()
    motors.forward()   # start moving in autonomous mode
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
