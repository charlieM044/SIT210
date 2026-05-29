"""
api/routes/data.py  –  Sensor data and storage endpoints.
"""

import time
from datetime import datetime
from pathlib import Path
from flask import Blueprint, Response, jsonify, request
from state import state
from saveData import storage
from config import IMAGE_DIR

data_bp = Blueprint('data', __name__)


@data_bp.route('/api/status')
def status():
    return jsonify({
        'connected': True,
        'mode':      state['mode'],
        'uptime_s':  int(time.time() - state['start_time']),
        'message':   'Pi server running',
    })


@data_bp.route('/api/readings')
def get_readings():
    since    = request.args.get('since', 0, type=float)
    readings = storage.get_all_readings_history()
    if since:
        cutoff   = datetime.fromtimestamp(since).isoformat()
        readings = [r for r in readings if r.get('timestamp', '') > cutoff]
    return jsonify(readings)



@data_bp.route('/api/latest-reading')
def get_latest_reading():
    """Return just the most recent live sensor reading from memory (fast for live updates)."""
    # 1. Try to grab the ultra-fresh live reading from memory cache
    live_reading = state.get('latest_reading')
    if live_reading:
        return jsonify(live_reading)
        
    # 2. Fallback to database only if the background loop hasn't started yet
    readings = storage.get_all_readings()
    if readings:
        return jsonify(readings[-1])  # Most recent is last
    return jsonify(None)
@data_bp.route('/api/stats')
def get_stats():
    scope = request.args.get('scope', 'live')
    if scope == 'history':
        stats = storage.get_moisture_stats_history() or {}
    else:
        stats = storage.get_moisture_stats() or {}
    stats['uptime'] = int(time.time() - state['start_time'])
    return jsonify(stats)


@data_bp.route('/api/critical')
def get_critical():
    return jsonify([r for r in storage.get_all_readings()
                    if r.get('severity') == 'Critical'])


@data_bp.route('/api/storage')
def get_storage():
    data_type = request.args.get('type')

    if data_type not in ('images', 'sensor_data'):
        return jsonify({'error': 'type must be images or sensor_data'}), 400

    if data_type == 'images':
        image_bytes = storage.get_image()
        if image_bytes is None:
            return jsonify({'error': 'no images available'}), 404
        return Response(image_bytes, mimetype='image/jpeg')
 
    return jsonify(storage.get_all_readings())


@data_bp.route('/api/image/<path:filename>')
def get_image_by_filename(filename):
    # Resolve and validate path to prevent traversal outside IMAGE_DIR.
    image_root = Path(IMAGE_DIR).resolve()
    image_path = (image_root / filename).resolve()

    if image_root not in image_path.parents or image_path.suffix.lower() != '.jpg':
        return jsonify({'error': 'invalid image path'}), 400
    if not image_path.exists() or not image_path.is_file():
        return jsonify({'error': 'image not found'}), 404

    return Response(image_path.read_bytes(), mimetype='image/jpeg')
  


