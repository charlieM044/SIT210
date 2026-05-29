"""
hardware/arduino.py  -  Arduino serial connection and message parsing.
 
Added in this revision:
  • threading.Lock() around all serial reads — prevents races between the
    autonomous loop, health checks, and the /api/arduino endpoint.
  • Parsing for CMD:<verb>[:<speed>] messages from the Arduino state machine.
  • Parsing for STATUS:<msg> messages (e.g. STATUS:STUCK).
"""
 
import time
import threading
from config import SERIAL_PORT, SERIAL_BAUD
 
arduino   = None
_serial_lock = threading.Lock()
 
try:
    import serial
    arduino = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
    time.sleep(2)
    print(f"[Arduino] ✓ connected on {SERIAL_PORT}")
except Exception as e:
    print(f"[Arduino] ⚠ not connected ({e})")
 
 
def read_line():
    """Return the next decoded line from Arduino, or None.  Thread-safe."""
    with _serial_lock:
        try:
            if arduino and arduino.in_waiting:
                return arduino.readline().decode('utf-8', errors='replace').strip()
        except Exception as e:
            print(f"[Arduino] read error: {e}")
    return None
 
 
def parse(line):
    """
    Parse an Arduino message into a dict, or return None.
 
    Supported formats:
      CMD:FORWARD
      CMD:FORWARD:75
      CMD:LEFT
      CMD:LEFT:40
      CMD:RIGHT
      CMD:RIGHT:40
      CMD:STOP
 
      STATUS:STUCK
 
      ULTRASONIC: SAFE
      ULTRASONIC: ERROR - Invalid Reading (d1: 36.2, d2: 0.0)
      ULTRASONIC: WALL:d1,d2,angle
 
      MOISTURE:327,MOIST
      MOISTURE:THRESHOLD_TRIGGERED
 
      GPS:NO_FIX
      GPS:lat,lng
    """
    if not line:
        return None
 
    # ── CMD (drive commands from Arduino state machine) ──────────────────────
    if line.startswith('CMD:'):
        body  = line[4:].strip()
        parts = body.split(':')
        verb  = parts[0].upper()
        speed = None
        if len(parts) > 1:
            try:
                speed = int(parts[1])
            except ValueError:
                pass
        if verb in ('FORWARD', 'LEFT', 'RIGHT', 'STOP'):
            return {'type': 'cmd', 'cmd': verb, 'speed': speed}
        return None
 
    # ── STATUS ────────────────────────────────────────────────────────────────
    if line.startswith('STATUS:'):
        return {'type': 'status', 'status_msg': line[7:].strip()}
 
    # ── Ultrasonic ────────────────────────────────────────────────────────────
    if line.startswith('ULTRASONIC:'):
        body = line[11:].strip()
        if body == 'SAFE':
            return {'type': 'ultrasonic', 'status': 'safe', 'wall': False}
        if body.startswith('ERROR'):
            try:
                d1 = float(body.split('d1:')[1].split(',')[0].strip())
                d2 = float(body.split('d2:')[1].split(')')[0].strip())
            except Exception:
                d1, d2 = None, None
            return {'type': 'ultrasonic', 'status': 'error',
                    'wall': False, 'd1': d1, 'd2': d2}
        if body.startswith('WALL:'):
            try:
                parts = body[5:].split(',')
                d1    = float(parts[0])
                d2    = float(parts[1])
                angle = float(parts[2])
                return {'type': 'ultrasonic', 'status': 'ok',
                        'wall': True, 'd1': d1, 'd2': d2, 'angle': angle,
                        'distance': min(d1, d2)}
            except Exception:
                pass
 
    # ── Moisture ──────────────────────────────────────────────────────────────
    if line.startswith('MOISTURE:'):
        body = line[9:].strip()
        if body == 'THRESHOLD_TRIGGERED':
            return {'type': 'moisture', 'status': 'threshold_triggered',
                    'triggered': True}
        try:
            parts = body.split(',')
            raw   = int(parts[0])
            label = parts[1].strip() if len(parts) > 1 else None
            return {'type': 'moisture', 'status': 'ok',
                    'raw': raw, 'label': label,
                    'triggered': False}
        except Exception:
            pass
 
    # ── GPS ───────────────────────────────────────────────────────────────────
    if line.startswith('GPS:'):
        body = line[4:].strip()
        if body == 'NO_FIX':
            return {'type': 'gps', 'status': 'no_fix',
                    'lat': None, 'lng': None}
        try:
            lat, lng = body.split(',')
            return {'type': 'gps', 'status': 'ok',
                    'lat': float(lat), 'lng': float(lng)}
        except Exception:
            pass
 
    return None

def clear_buffer():
    """Instantly discard any stale messages in the serial queue."""
    with _serial_lock:
        try:
            if arduino:
                arduino.reset_input_buffer()
        except Exception as e:
            print(f"[Arduino] buffer clear error: {e}")