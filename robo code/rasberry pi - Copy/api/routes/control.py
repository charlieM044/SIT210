"""
api/routes/control.py  –  Motor control and mode switching endpoints.
"""

from click import command
from flask import Blueprint, jsonify, request
from state import state
from hardware import motors

control_bp = Blueprint('control', __name__)

COMMANDS = {
    'forward':  motors.forward,
    'backward': motors.backward,
    'left':     motors.left,
    'right':    motors.right,
    'stop':     motors.stop,
}

ALWAYS_EXECUTE = {'stop'}

@control_bp.route('/api/control', methods=['POST'])
def control():
    command = request.json.get('command') if request.json else None
    if command not in COMMANDS:
        return jsonify({'error': f'unknown command: {command}',
                        'valid': list(COMMANDS)}), 400
    executed = (state['mode'] == 'manual') or (command in ALWAYS_EXECUTE)
    if executed:
        COMMANDS[command]()
    return jsonify({'mode': state['mode'], 'command': command, 'executed': executed})

@control_bp.route('/api/mode', methods=['GET', 'POST'])
def mode():
    if request.method == 'POST':
        new_mode = request.json.get('mode') if request.json else None
        if new_mode not in ('manual', 'autonomous'):
            return jsonify({'error': 'mode must be manual or autonomous'}), 400
        state['mode'] = new_mode
        if new_mode == 'manual':
             motors.stop()
        print(f"[Pi] → {new_mode.upper()}")
        return jsonify({'mode': new_mode})
    return jsonify({'mode': state['mode']})
