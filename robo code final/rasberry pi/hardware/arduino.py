"""
hardware/arduino.py  –  Arduino serial connection and message parsing.
Isolated here so the rest of the code never touches pyserial directly.
"""

import time
from config import SERIAL_PORT, SERIAL_BAUD

arduino = None

try:
    import serial
    arduino = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
    time.sleep(2)
    print(f"[Arduino] ✓ connected on {SERIAL_PORT}")
except Exception as e:
    print(f"[Arduino] ⚠ not connected ({e})")


def read_line():
    """Return the next decoded line from Arduino, or None."""
    try:
        if arduino and arduino.in_waiting:
            return arduino.readline().decode('utf-8', errors='replace').strip()
    except Exception as e:
        print(f"[Arduino] read error: {e}")
    return None

def parse(line):
    """
    Parse an Arduino message into a dict, or return None.

    Formats:
      'ULTRASONIC: SAFE'
      'ULTRASONIC: ERROR - Invalid Reading (d1: 36.2, d2: 0.0)'
      'ULTRASONIC: WALL:d1,d2,angle'
      'MOISTURE:327,MOIST'
      'GPS:NO_FIX'
      'GPS:lat,lng'
    """
    if not line:
        return None

    # ── Ultrasonic ─────────────────────────────────────────────
    if line.startswith('ULTRASONIC:'):
        body = line[11:].strip()
        if body == 'SAFE':
            return {'type': 'ultrasonic', 'status': 'safe', 'wall': False}
        if body.startswith('ERROR'):
            # Extract d1/d2 if present
            try:
                d1 = float(body.split('d1:')[1].split(',')[0].strip())
                d2 = float(body.split('d2:')[1].split(')')[0].strip())
            except Exception:
                d1, d2 = None, None
            return {'type': 'ultrasonic', 'status': 'error',
                    'wall': False, 'd1': d1, 'd2': d2}
        # WALL message: 'WALL:d1,d2,angle'
        if body.startswith('WALL:'):
            try:
                parts = body[5:].split(',')
                d1 = float(parts[0])
                d2 = float(parts[1])
                angle = float(parts[2])
                return {'type': 'ultrasonic', 'status': 'ok',
                        'wall': True, 'd1': d1, 'd2': d2, 'angle': angle,
                        'distance': min(d1, d2)}
            except Exception:
                pass

    # ── Moisture ───────────────────────────────────────────────
    if line.startswith('MOISTURE:'):
        body = line[9:].strip()
        if body == 'THRESHOLD_TRIGGERED':
            return {'type': 'moisture', 'status': 'threshold_triggered',
                    'triggered': True}
        try:
            parts = body.split(',')
            raw   = int(parts[0])
            label = parts[1].strip() if len(parts) > 1 else None
            # Convert raw ADC (0-1023) to percentage
            pct   = round((raw / 1023) * 100, 1)
            return {'type': 'moisture', 'status': 'ok',
                    'raw': raw, 'label': label, 'percent': pct,
                    'triggered': False}
        except Exception:
            pass

    # ── GPS ────────────────────────────────────────────────────
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
