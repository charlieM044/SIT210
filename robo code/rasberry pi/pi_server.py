from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS



from saveData import LocalDataManager
from camera import CameraManager, IRCamera
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)  
storage = LocalDataManager('./robot_inspection_data')
camera = CameraManager()
ir_camera = IRCamera()

# Store control state
control_active = False
pending_commands = []

# API: Receive sensor data from Arduino
@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    """Receive sensor data from Arduino/sensors"""
    data = request.json
    
    # If moisture is high, capture image
    image_path = None
    if data['moisture'] > 60:
        image_path = camera.capture_image(
            data['gps_lat'],
            data['gps_lng'],
            data['moisture']
        )
    
    # Save to local database
    storage.add_moisture_reading(
        gps_lat=data['gps_lat'],
        gps_lng=data['gps_lng'],
        moisture=data['moisture'],
        ir_temp=data.get('ir_temp'),
        image_path=image_path,
        severity=data.get('severity', 'Minor')
    )
    
    print(f"Sensor data received: {data}")
    return jsonify({'status': 'received'}), 200

# API: Get all readings
@app.route('/api/readings', methods=['GET'])
def get_readings():
    readings = storage.get_all_readings()
    return jsonify(readings)

# API: Get statistics
@app.route('/api/stats', methods=['GET'])
def get_stats():
    stats = storage.get_moisture_stats()
    return jsonify(stats)

# API: Get critical readings
@app.route('/api/critical', methods=['GET'])
def get_critical():
    readings = storage.get_all_readings()
    critical = [r for r in readings if r['severity'] == 'Critical']
    return jsonify(critical)

# API: Storage info
@app.route('/api/storage', methods=['GET'])
def get_storage():
    info = storage.get_storage_info()
    return jsonify(info)

# Control API: Start streaming and control
@app.route('/api/control/start', methods=['POST'])
def control_start():
    global control_active
    control_active = True
    camera.start_streaming()
    return jsonify({'status': 'control active'}), 200

@app.route('/api/control/stop', methods=['POST'])
def control_stop():
    global control_active
    control_active = False
    camera.stop_streaming()
    return jsonify({'status': 'control stopped'}), 200

# Motor commands
@app.route('/api/commands', methods=['GET'])
def get_commands():
    global pending_commands
    commands = pending_commands.copy()
    pending_commands = []
    return jsonify(commands), 200

@app.route('/api/control/forward', methods=['POST'])
def control_forward():
    pending_commands.append('forward')
    return jsonify({'status': 'command sent'}), 200

@app.route('/api/control/backward', methods=['POST'])
def control_backward():
    pending_commands.append('backward')
    return jsonify({'status': 'command sent'}), 200

@app.route('/api/control/left', methods=['POST'])
def control_left():
    pending_commands.append('left')
    return jsonify({'status': 'command sent'}), 200

@app.route('/api/control/right', methods=['POST'])
def control_right():
    pending_commands.append('right')
    return jsonify({'status': 'command sent'}), 200

@app.route('/api/control/stop-motors', methods=['POST'])
def control_stop_motors():
    pending_commands.append('stop')
    return jsonify({'status': 'command sent'}), 200

# Video streaming
@app.route('/video_feed')
def video_feed():
    def generate():
        while control_active:
            frame = camera.get_frame()
            if frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)