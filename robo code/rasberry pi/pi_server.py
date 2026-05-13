from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from saveData import LocalDataManager
from camera import CameraManager
from motorcontroller import MotorController
from datetime import datetime
import threading
import serial
import time
import platform

# You need a way to access the camera instance created in RobotMain
# A common way is to pass it to the app or use a singleton
global_camera = None
app = Flask(__name__)
CORS(app)

# ── Hardware init ──────────────────────────────────────────────────────────────
storage = LocalDataManager('./robot_inspection_data')
camera  = CameraManager()
global_camera = camera
motors  = MotorController()


# Try to connect to Arduino (won't crash if not present)
arduino = None
SERIAL_PORT = '/dev/ttyACM0' if platform.machine() in ('armv7l', 'aarch64') else 'COM6'
try:
    arduino = serial.Serial(SERIAL_PORT, 9600, timeout=1)
    time.sleep(2)
    print(f"[Pi] ✓ Arduino connected on {SERIAL_PORT}")
except Exception as e:
    print(f"[Pi] ⚠ Arduino not connected ({e}) — running without wall avoidance")

# ── Robot state ────────────────────────────────────────────────────────────────
state = {
    'mode':      'autonomous',   # 'autonomous' | 'manual'
    'running':   True,
    'streaming': False,
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def parse_arduino(line):
    """Parse 'WALL:remaining,angle,amount' or 'SAFE' from Arduino."""
    if line == 'SAFE':
        return {'type': 'safe'}
    if line.startswith('WALL:'):
        try:
            parts = line.replace('WALL:', '').split(',')
            return {
                'type':      'wall',
                'remaining': float(parts[0]),
                'angle':     float(parts[1]),
                'amount':    float(parts[2]),
            }
        except Exception:
            pass
    return None

def determine_severity(moisture):
    if moisture > 80:
        return 'Critical'
    if moisture > 60:
        return 'Moderate'
    return 'Minor'

# ── Autonomous loop ────────────────────────────────────────────────────────────
def autonomous_loop():
    """Runs forever in a background thread.
    Reads Arduino wall data and sensor data, saves locally, drives the robot.
    Pauses actuation when PC switches to manual mode."""
    print("[Auto] Autonomous loop started")
    motors.forward()
    last_save_time = 0

    while state['running']:
        if state['mode'] != 'autonomous':
            time.sleep(0.1)
            continue
        time.sleep(0.1)

        # ── Wall avoidance from Arduino ────────────────────────────────────────
        if arduino and arduino.in_waiting:
            try:
                raw = arduino.readline().decode('utf-8').strip()
                parsed = parse_arduino(raw)
                if parsed:
                    if parsed['type'] == 'wall':
                        remaining = parsed['remaining']
                        if remaining > 5:
                            if remaining > 0:
                                motors.turn_left_angle(remaining)
                            else:
                                motors.turn_right_angle(abs(remaining))
                        else:
                            motors.forward()
                    elif parsed['type'] == 'safe':
                        motors.forward()
            except Exception as e:
                print(f"[Auto] Arduino read error: {e}")

        # ── Sensor data collection ─────────────────────────────────────────────
        # Replace the block below with your real sensor reading logic.
        # This stub shows the expected structure.
        try:
            current_time = time.time()
            if current_time - last_save_time > 5.0:  # Only save every 5 seconds
                sensor = read_sensors()   # <-- implement this for your hardware
                if sensor:
                    severity   = determine_severity(sensor['moisture'])
                    image_path = None
                    if sensor['moisture'] > 60:
                        image_path = camera.capture_image(
                            sensor['gps_lat'], sensor['gps_lng'], sensor['moisture']
                        )
                   # storage.add_moisture_reading(
                     #   gps_lat    = sensor['gps_lat'],
                     #   gps_lng    = sensor['gps_lng'],
                     #   moisture   = sensor['moisture'],
                       # ir_temp    = sensor.get('ir_temp'),
                      #  image_path = image_path,
                      #  severity   = severity,
                  #  )
                if severity == 'Critical':
                    motors.stop()
                    time.sleep(2)
                    motors.forward()
        except NotImplementedError:
            pass   # Sensor stub not yet wired up
        except Exception as e:
            print(f"[Auto] Sensor error: {e}")

        time.sleep(0.1)

def read_sensors():
    """
    STUB — replace with your actual sensor reading code.
    Should return a dict like:
      {'gps_lat': -37.81, 'gps_lng': 144.96, 'moisture': 45.0, 'ir_temp': 22.1}
    or None if no data is ready.
    """
    return{'gps_lat': -37.81,'gps_lng':12,'moisture':52.2,'ir_temp':22.1}
 

# Start autonomous loop immediately — PC connection is irrelevant
threading.Thread(target=autonomous_loop, daemon=True, name="Autonomous").start()

# ── Mode endpoints ─────────────────────────────────────────────────────────────
@app.route('/api/mode', methods=['GET'])
def get_mode():
    return jsonify({'mode': state['mode']})

@app.route('/api/mode/manual', methods=['POST'])
def set_manual():
    state['mode'] = 'manual'
    motors.stop()
    print("[Pi] → MANUAL mode")
    return jsonify({'mode': 'manual'})

@app.route('/api/mode/autonomous', methods=['POST'])
def set_autonomous():
    state['mode'] = 'autonomous'
    motors.forward()
    print("[Pi] → AUTONOMOUS mode")
    return jsonify({'mode': 'autonomous'})

# ── Manual motor control (only acts in manual mode) ────────────────────────────
@app.route('/api/control/forward',    methods=['POST'])
def ctrl_forward():
    if state['mode'] == 'manual': motors.forward()
    return jsonify({'mode': state['mode']})

@app.route('/api/control/backward',   methods=['POST'])
def ctrl_backward():
    if state['mode'] == 'manual': motors.backward()
    return jsonify({'mode': state['mode']})

@app.route('/api/control/left',       methods=['POST'])
def ctrl_left():
    if state['mode'] == 'manual': motors.left()
    return jsonify({'mode': state['mode']})

@app.route('/api/control/right',      methods=['POST'])
def ctrl_right():
    if state['mode'] == 'manual': motors.right()
    return jsonify({'mode': state['mode']})

@app.route('/api/control/stop',       methods=['POST'])
@app.route('/api/control/stop-motors',methods=['POST'])
def ctrl_stop():
    if state['mode'] == 'manual': motors.stop()
    return jsonify({'mode': state['mode']})

# ── Data endpoints ─────────────────────────────────────────────────────────────
@app.route('/api/readings', methods=['GET'])
def get_readings():
    since    = request.args.get('since', 0, type=float)
    readings = storage.get_all_readings()
    if since:
        readings = [r for r in readings if r['timestamp'] > since]
    return jsonify(readings)

@app.route('/api/stats',    methods=['GET'])
def get_stats():
    return jsonify(storage.get_moisture_stats())

@app.route('/api/critical', methods=['GET'])
def get_critical():
    return jsonify([r for r in storage.get_all_readings() if r['severity'] == 'Critical'])

@app.route('/api/storage',  methods=['GET'])
def get_storage():
    return jsonify(storage.get_storage_info())

# ── Video stream ───────────────────────────────────────────────────────────────
@app.route('/api/stream/start', methods=['POST'])
def stream_start():
    state['streaming'] = True
    camera.start_streaming()
    return jsonify({'streaming': True})

@app.route('/api/stream/stop', methods=['POST'])
def stream_stop():
    state['streaming'] = False
    camera.stop_streaming()
    return jsonify({'streaming': False})

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            if global_camera:
                frame = global_camera.get_frame() # This gets the JPEG bytes
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.04) # Match the camera FPS (~25fps)
            
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
