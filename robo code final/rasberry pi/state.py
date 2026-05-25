"""
state.py  –  Single shared robot state.
Import this anywhere instead of passing dicts around.
"""

import time

state = {
    'mode':       'autonomous',   # 'autonomous' | 'manual'
    'running':    True,
    'streaming':  False,
    'start_time': time.time(),
}
