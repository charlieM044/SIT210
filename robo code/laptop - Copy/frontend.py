"""
frontend.py  –  Runs on your PC (port 8000).
Proxies all requests to the Pi (port 5000) over WiFi.
"""

from flask import Flask, render_template, jsonify, request, Response, stream_with_context
from flask_cors import CORS
import requests
import time
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

PI_SERVER = 'http://10.222.154.118:5000'

# ── Connection cache (5 s) ─────────────────────────────────────────────────────
_last_check = 0
_connected  = False

def is_connected():
    global _last_check, _connected
    if time.time() - _last_check < 5:
        return _connected
    try:
        r = requests.get(f'{PI_SERVER}/api/status', timeout=2)
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
        'message':   'Connected to Pi' if connected else 'Pi not reachable',
    })

# ── Generic GET proxy for data endpoints ──────────────────────────────────────
PROXIED_GET = {'readings', 'stats', 'critical', 'storage', 'mode'}

@app.route('/api/<endpoint>')
def proxy_get(endpoint):
    if endpoint not in PROXIED_GET:
        return jsonify({'error': 'not found'}), 404
    try:
        r = requests.get(f'{PI_SERVER}/api/{endpoint}',
                         params=request.args, timeout=5)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        log.error(f'GET {endpoint}: {e}')
        return jsonify({}), 503

# ── Motor control ──────────────────────────────────────────────────────────────
@app.route('/api/control/<command>', methods=['POST'])
def control(command):
    valid = {'forward', 'backward', 'left', 'right', 'stop'}
    if command not in valid:
        return jsonify({'error': 'unknown command'}), 400
    try:
        r = requests.post(f'{PI_SERVER}/api/control',
                          json={'command': command}, timeout=2)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        log.error(f'control/{command}: {e}')
        return jsonify({'error': str(e)}), 503

# ── Mode switching ─────────────────────────────────────────────────────────────
@app.route('/api/mode/<new_mode>', methods=['POST'])
def set_mode(new_mode):
    if new_mode not in ('manual', 'autonomous'):
        return jsonify({'error': 'invalid mode'}), 400
    try:
        r = requests.post(f'{PI_SERVER}/api/mode',
                          json={'mode': new_mode}, timeout=2)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 503

# ── Stream control ─────────────────────────────────────────────────────────────
@app.route('/api/stream/<action>', methods=['POST'])
def stream_control(action):
    if action not in ('start', 'stop'):
        return jsonify({'error': 'invalid action'}), 400
    try:
        r = requests.post(f'{PI_SERVER}/api/stream',
                          json={'action': action}, timeout=2)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 503

# ── Video stream proxy ─────────────────────────────────────────────────────────
@app.route('/video_feed')
def video_feed():
    try:
        r = requests.get(f'{PI_SERVER}/video_feed', stream=True, timeout=None)
        return Response(
            stream_with_context(r.iter_content(chunk_size=1024)),
            content_type=r.headers.get('content-type')
        )
    except Exception as e:
        log.error(f'video_feed: {e}')
        return jsonify({'error': str(e)}), 503

# ── HTML pages ─────────────────────────────────────────────────────────────────
@app.route('/')
def index():        return render_template('index.html')

@app.route('/map')
def map_view():     return render_template('map.html')

@app.route('/report')
def report():       return render_template('report.html')

@app.route('/control')
def control_view(): return render_template('control.html')


if __name__ == '__main__':
    print(f"\n  Frontend → Pi at {PI_SERVER}")
    print("  Open http://localhost:8000\n")
    app.run(host='0.0.0.0', port=8000, debug=True)
