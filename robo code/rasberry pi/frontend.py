from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
import requests
import logging
import sys
import os

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ===== CONFIGURATION =====
# Update this to match your Raspberry Pi's IP address or hostname
# Options:
#   - 'http://raspberrypi.local:5000'  (mDNS name - works on Mac/Linux, may not work on Windows)
#   - 'http://192.168.1.XXX:5000'      (IP address - replace with your Pi's IP)
#   - 'http://192.168.0.XXX:5000'      (if on different subnet)

PI_SERVER = 'http://raspberrypi.local:5000'

# Test connection on startup
logger.info(f"Frontend configured to connect to: {PI_SERVER}")

# ===== HEALTH CHECK =====
@app.route('/api/health', methods=['GET'])
def health_check():
    """Check connection to Pi server"""
    try:
        response = requests.get(f'{PI_SERVER}/api/readings', timeout=2)
        logger.info("✓ Connected to Pi server")
        return jsonify({'status': 'connected', 'server': PI_SERVER}), 200
    except requests.exceptions.ConnectionError as e:
        logger.error(f"✗ Cannot connect to Pi: {e}")
        return jsonify({'status': 'disconnected', 'error': f'Cannot reach {PI_SERVER}', 'server': PI_SERVER}), 503
    except Exception as e:
        logger.error(f"✗ Health check failed: {e}")
        return jsonify({'status': 'error', 'error': str(e), 'server': PI_SERVER}), 500

# ===== DATA ENDPOINTS =====
@app.route('/api/readings', methods=['GET'])
def get_readings():
    try:
        response = requests.get(f'{PI_SERVER}/api/readings', timeout=5)
        response.raise_for_status()
        logger.debug(f"Readings: {response.json()}")
        return jsonify(response.json()), 200
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to {PI_SERVER}")
        return jsonify({"error": f"Cannot connect to {PI_SERVER}", "data": []}), 503
    except Exception as e:
        logger.error(f"Error fetching readings: {e}")
        return jsonify({"error": str(e), "data": []}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        response = requests.get(f'{PI_SERVER}/api/stats', timeout=5)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to {PI_SERVER}")
        return jsonify({"error": f"Cannot connect to {PI_SERVER}"}), 503
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/critical', methods=['GET'])
def get_critical():
    try:
        response = requests.get(f'{PI_SERVER}/api/critical', timeout=5)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to {PI_SERVER}")
        return jsonify({"error": f"Cannot connect to {PI_SERVER}", "data": []}), 503
    except Exception as e:
        logger.error(f"Error fetching critical: {e}")
        return jsonify({"error": str(e), "data": []}), 500

@app.route('/api/storage', methods=['GET'])
def get_storage():
    try:
        response = requests.get(f'{PI_SERVER}/api/storage', timeout=5)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to {PI_SERVER}")
        return jsonify({"error": f"Cannot connect to {PI_SERVER}"}), 503
    except Exception as e:
        logger.error(f"Error fetching storage: {e}")
        return jsonify({"error": str(e)}), 500

# ===== CONTROL ENDPOINTS =====
@app.route('/api/control/start', methods=['POST'])
def control_start():
    try:
        response = requests.post(f'{PI_SERVER}/api/control/start', timeout=5)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except Exception as e:
        logger.error(f"Control error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/control/stop', methods=['POST'])
def control_stop():
    try:
        response = requests.post(f'{PI_SERVER}/api/control/stop', timeout=5)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except Exception as e:
        logger.error(f"Control error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/control/forward', methods=['POST'])
def control_forward():
    try:
        response = requests.post(f'{PI_SERVER}/api/control/forward', timeout=5)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except Exception as e:
        logger.error(f"Control error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/control/backward', methods=['POST'])
def control_backward():
    try:
        response = requests.post(f'{PI_SERVER}/api/control/backward', timeout=5)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except Exception as e:
        logger.error(f"Control error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/control/left', methods=['POST'])
def control_left():
    try:
        response = requests.post(f'{PI_SERVER}/api/control/left', timeout=5)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except Exception as e:
        logger.error(f"Control error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/control/right', methods=['POST'])
def control_right():
    try:
        response = requests.post(f'{PI_SERVER}/api/control/right', timeout=5)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except Exception as e:
        logger.error(f"Control error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/control/stop-motors', methods=['POST'])
def control_stop_motors():
    try:
        response = requests.post(f'{PI_SERVER}/api/control/stop-motors', timeout=5)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except Exception as e:
        logger.error(f"Control error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/commands', methods=['GET'])
def get_commands():
    try:
        response = requests.get(f'{PI_SERVER}/api/commands', timeout=5)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to {PI_SERVER}")
        return jsonify({"error": f"Cannot connect to {PI_SERVER}", "data": []}), 503
    except Exception as e:
        logger.error(f"Error fetching commands: {e}")
        return jsonify({"error": str(e), "data": []}), 500

# ===== VIDEO STREAMING =====
@app.route('/video_feed')
def video_feed():
    try:
        response = requests.get(f'{PI_SERVER}/video_feed', stream=True, timeout=30)
        return Response(response.iter_content(chunk_size=1024), mimetype='video/mp4')
    except Exception as e:
        logger.error(f"Video feed error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

# ===== HTML ROUTES =====
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
    print("\n" + "="*60)
    print("🖥️  FRONTEND SERVER (Windows)")
    print("="*60)
    print(f"Connecting to Pi backend: {PI_SERVER}")
    print("Running on: http://localhost:8000")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=8000, debug=True)
