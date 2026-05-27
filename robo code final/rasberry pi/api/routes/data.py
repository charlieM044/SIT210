"""
api/routes/data.py  –  Sensor data and storage endpoints.
"""

import time
from datetime import datetime
from flask import Blueprint, jsonify, request
from state import state
from saveData import storage

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
    readings = storage.get_all_readings()
    if since:
        cutoff   = datetime.fromtimestamp(since).isoformat()
        readings = [r for r in readings if r.get('timestamp', '') > cutoff]
    return jsonify(readings)


@data_bp.route('/api/latest-reading')

def get_latest_reading():  
    """Return just the most recent sensor reading (fast, for live updates)."""
    # 2. Query the live sensor state instead of the slow storage buffer
    live_sensor = read_sensors()
    
    if live_sensor:
        # 3. Inject current timestamps so the frontend UI doesn't display a blank time
        now = datetime.now()
        live_sensor['timestamp'] = now.isoformat(sep=' ', timespec='seconds')
        live_sensor['time']      = now.strftime('%H:%M:%S')
        live_sensor['date']      = now.strftime('%Y-%m-%d')
        
        return jsonify(live_sensor)
        
    return jsonify(None)

@data_bp.route('/api/stats')
def get_stats():
    stats  = storage.get_moisture_stats() or {}
    stats['uptime'] = int(time.time() - state['start_time'])
    return jsonify(stats)


@data_bp.route('/api/critical')
def get_critical():
    return jsonify([r for r in storage.get_all_readings()
                    if r.get('severity') == 'Critical'])


@data_bp.route('/api/storage')
def get_storage():
    return jsonify(storage.get_storage_info())
