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

    Expected formats:
      'SAFE'                    → {'type': 'safe'}
      'WALL:remaining,angle,amount' → {'type': 'wall', 'remaining': float, ...}
    """
    if not line:
        return None
    if line == 'SAFE':
        return {'type': 'safe'}
    if line.startswith('WALL:'):
        try:
            parts = line[5:].split(',')
            return {
                'type':      'wall',
                'remaining': float(parts[0]),
                'angle':     float(parts[1]),
                'amount':    float(parts[2]),
            }
        except Exception:
            pass
    return None
