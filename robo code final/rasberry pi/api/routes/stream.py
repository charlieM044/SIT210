"""
api/routes/stream.py  –  Camera stream endpoints.
"""

import time
from flask import Blueprint, Response, jsonify
from state import state
from hardware import camera

stream_bp = Blueprint('stream', __name__)


@stream_bp.route('/api/stream', methods=['POST'])
def stream_control():
    from flask import request
    action = request.json.get('action') if request.json else None
    if action not in ('start', 'stop'):
        return jsonify({'error': 'action must be start or stop'}), 400
    state['streaming'] = action == 'start'
    camera.start_streaming() if state['streaming'] else camera.stop_streaming()
    return jsonify({'streaming': state['streaming']})


@stream_bp.route('/video_feed')
def video_feed():
    def generate():
        while True:
            frame = camera.get_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.1)
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
