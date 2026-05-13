from flask import Flask, render_template, jsonify, request, Response, stream_with_context
from flask_cors import CORS
import requests
import time
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
# Pi always has this IP when hosting its own hotspot
PI_SERVER = 'http://10.222.154.118:5000'

# ── Connection check (cached 5 s to avoid hammering the Pi) ───────────────────
_last_check  = 0
_connected   = False

def is_connected():
    global _last_check, _connected
    if time.time() - _last_check < 5:
        return _connected
    try:
        r = requests.get(f'{PI_SERVER}/api/stats', timeout=2)
        _connected = r.status_code == 200
    except Exception:
        _connected = False
    _last_check = time.time()
    return _connected

# ── Status ─────────────────────────────────────────────────────────────────────
@app.route('/api/status')
def status():
    connected = is_connected()
    return jsonify({
        'connected': connected,
        'pi_url':    PI_SERVER,
        'message':   'Connected to Pi ✓' if connected else 'Pi not reachable ✗',
    })

# ── Data endpoints ─────────────────────────────────────────────────────────────
@app.route('/api/readings')
def readings():
    since = request.args.get('since', 0)
    try:
        r = requests.get(f'{PI_SERVER}/api/readings?since={since}', timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        log.error(f"readings: {e}")
        return jsonify([]), 503

@app.route('/api/stats')
def stats():
    try:
        r = requests.get(f'{PI_SERVER}/api/stats', timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        log.error(f"stats: {e}")
        return jsonify({}), 503

@app.route('/api/critical')
def critical():
    try:
        r = requests.get(f'{PI_SERVER}/api/critical', timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        log.error(f"critical: {e}")
        return jsonify([]), 503

@app.route('/api/storage')
def storage():
    try:
        r = requests.get(f'{PI_SERVER}/api/storage', timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        log.error(f"storage: {e}")
        return jsonify({}), 503

# ── Mode switching ─────────────────────────────────────────────────────────────
@app.route('/api/mode')
def get_mode():
    try:
        r = requests.get(f'{PI_SERVER}/api/mode', timeout=2)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({'mode': 'unknown', 'error': str(e)}), 503

@app.route('/api/mode/<mode>', methods=['POST'])
def set_mode(mode):
    if mode not in ('manual', 'autonomous'):
        return jsonify({'error': 'invalid mode'}), 400
    try:
        r = requests.post(f'{PI_SERVER}/api/mode/{mode}', timeout=2)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 503

# ── Motor control (Pi will ignore if not in manual mode) ──────────────────────
@app.route('/api/control/<command>', methods=['POST'])
def control(command):
    valid = {'forward', 'backward', 'left', 'right', 'stop', 'stop-motors'}
    if command not in valid:
        return jsonify({'error': 'unknown command'}), 400
    try:
        r = requests.post(f'{PI_SERVER}/api/control/{command}', timeout=2)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        log.error(f"control/{command}: {e}")
        return jsonify({'error': str(e)}), 503

# ── Video stream ───────────────────────────────────────────────────────────────
@app.route('/api/stream/<action>', methods=['POST'])
def stream_control(action):
    try:
        r = requests.post(f'{PI_SERVER}/api/stream/{action}', timeout=2)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 503

@app.route('/video_feed')
def video_feed():
    """Proxy the MJPEG stream from the Pi."""
    try:
        r = requests.get(f'{PI_SERVER}/video_feed', stream=True, timeout=10)
        return Response(
            stream_with_context(r.iter_content(chunk_size=4096)),
            content_type=r.headers.get('content-type',
                         'multipart/x-mixed-replace; boundary=frame'),
        )
    except Exception as e:
        log.error(f"video_feed: {e}")
        return jsonify({'error': str(e)}), 503

# ── HTML pages ─────────────────────────────────────────────────────────────────
@app.route('/')
def index():    return render_template('index.html')

@app.route('/map')
def map_view(): return render_template('map.html')

@app.route('/report')
def report():   return render_template('report.html')

@app.route('/control')
def control_view(): return render_template('control.html')

if __name__ == '__main__':
    print("\n" + "=" * 55)
    print("🖥️  Frontend — connecting to Pi at:", PI_SERVER)
    print("   Open http://localhost:8000 in your browser")
    print("=" * 55 + "\n")
    app.run(host='0.0.0.0', port=8000, debug=True)
