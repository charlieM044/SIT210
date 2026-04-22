from flask import Flask, render_template, jsonify, request
import requests

app = Flask(__name__)

# Raspberry Pi server URL
PI_SERVER = 'http://localhost:5000'

# Track connection status
connection_status = {'connected': False}

def check_pi_connection():
    """Check if Pi server is reachable"""
    try:
        response = requests.get(f'{PI_SERVER}/api/stats', timeout=2)
        connection_status['connected'] = response.status_code == 200
        return connection_status['connected']
    except:
        connection_status['connected'] = False
        return False

# API: Check Pi connection status
@app.route('/api/status', methods=['GET'])
def get_status():
    is_connected = check_pi_connection()
    status = {
        'connected': is_connected,
        'pi_url': PI_SERVER,
        'message': 'Connected to Pi ✓' if is_connected else 'Pi not connected ✗'
    }
    print(f"[Computer] Status: {status['message']}")
    return jsonify(status), 200

# API: Forward requests to Pi
@app.route('/api/readings', methods=['GET'])
def get_readings():
    try:
        if not check_pi_connection():
            return jsonify([]), 503
        
        response = requests.get(f'{PI_SERVER}/api/readings', timeout=5)
        readings = response.json()
        print(f"[Computer] Retrieved {len(readings)} readings from Pi")
        return jsonify(readings), 200
    except requests.exceptions.Timeout:
        print("[Computer] Pi connection timeout")
        return jsonify([]), 504
    except Exception as e:
        print(f"[Computer] Error getting readings: {e}")
        return jsonify([]), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        if not check_pi_connection():
            return jsonify({}), 503
        
        response = requests.get(f'{PI_SERVER}/api/stats', timeout=5)
        stats = response.json()
        print(f"[Computer] Retrieved stats from Pi")
        return jsonify(stats), 200
    except Exception as e:
        print(f"[Computer] Error getting stats: {e}")
        return jsonify({}), 500

@app.route('/api/critical', methods=['GET'])
def get_critical():
    try:
        if not check_pi_connection():
            return jsonify([]), 503
        
        response = requests.get(f'{PI_SERVER}/api/critical', timeout=5)
        critical = response.json()
        print(f"[Computer] Retrieved critical readings from Pi")
        return jsonify(critical), 200
    except Exception as e:
        print(f"[Computer] Error getting critical: {e}")
        return jsonify([]), 500

@app.route('/api/storage', methods=['GET'])
def get_storage():
    try:
        if not check_pi_connection():
            return jsonify({}), 503
        
        response = requests.get(f'{PI_SERVER}/api/storage', timeout=5)
        storage = response.json()
        print(f"[Computer] Retrieved storage info from Pi")
        return jsonify(storage), 200
    except Exception as e:
        print(f"[Computer] Error getting storage: {e}")
        return jsonify({}), 500

# Control endpoints - forward to Pi
@app.route('/api/control/start', methods=['POST'])
def control_start():
    try:
        response = requests.post(f'{PI_SERVER}/api/control/start', timeout=5)
        print("[Computer] Started control on Pi")
        return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"[Computer] Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/control/stop', methods=['POST'])
def control_stop():
    try:
        response = requests.post(f'{PI_SERVER}/api/control/stop', timeout=5)
        print("[Computer] Stopped control on Pi")
        return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"[Computer] Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/control/forward', methods=['POST'])
def control_forward():
    try:
        requests.post(f'{PI_SERVER}/api/control/forward', timeout=5)
        print("[Computer] Command: Forward")
        return jsonify({'status': 'sent'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/control/backward', methods=['POST'])
def control_backward():
    try:
        requests.post(f'{PI_SERVER}/api/control/backward', timeout=5)
        print("[Computer] Command: Backward")
        return jsonify({'status': 'sent'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/control/left', methods=['POST'])
def control_left():
    try:
        requests.post(f'{PI_SERVER}/api/control/left', timeout=5)
        print("[Computer] Command: Left")
        return jsonify({'status': 'sent'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/control/right', methods=['POST'])
def control_right():
    try:
        requests.post(f'{PI_SERVER}/api/control/right', timeout=5)
        print("[Computer] Command: Right")
        return jsonify({'status': 'sent'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/control/stop-motors', methods=['POST'])
def control_stop_motors():
    try:
        requests.post(f'{PI_SERVER}/api/control/stop-motors', timeout=5)
        print("[Computer] Command: Stop Motors")
        return jsonify({'status': 'sent'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/commands', methods=['GET'])
def get_commands():
    try:
        response = requests.get(f'{PI_SERVER}/api/commands', timeout=5)
        commands = response.json()
        print(f"[Computer] Retrieved {len(commands) if isinstance(commands, list) else 0} commands from Pi")
        return jsonify(commands), 200
    except Exception as e:
        print(f"[Computer] Error getting commands: {e}")
        return jsonify([]), 500

# Video streaming - proxy from Pi
@app.route('/video_feed')
def video_feed():
    try:
        response = requests.get(f'{PI_SERVER}/video_feed', stream=True, timeout=5)
        return response.iter_content(chunk_size=1024)
    except Exception as e:
        print(f"[Computer] Error getting video feed: {e}")
        return jsonify({'status': 'error'}), 500

# HTML routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/map')
def map_view():
    return render_template('map.html')

@app.route('/report')
def report_view():
    return render_template('report.html')

@app.route('/control')
def control_view():
    return render_template('control.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)