"""
api/routes/control.py  –  Motor control and mode switching endpoints.
"""

from click import command
from flask import Blueprint, jsonify, request
from state import state
from hardware import motors
from hardware.arduino import read_line, parse



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
    data    = request.json or {}
    command = data.get('command')
    speed   = data.get('speed')          # new — optional int 0-100

    if command not in COMMANDS:
        return jsonify({'error': f'unknown command: {command}',
                        'valid': list(COMMANDS)}), 400

    executed = (state['mode'] == 'manual') or (command in ALWAYS_EXECUTE)
    if executed:
        if speed is not None and command != 'stop':
            COMMANDS[command](speed=int(speed))
        else:
            COMMANDS[command]()

    return jsonify({'mode': state['mode'], 'command': command,
                    'executed': executed, 'speed': speed})

@control_bp.route('/api/speed', methods=['GET'])
def get_speed():
    return jsonify({'speed': motors.current_speed})

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



@control_bp.route('/api/arduino', methods=['GET'])
def arduino_status():
    try:
        line   = read_line()
        parsed = parse(line)
        return jsonify({
            'connected': True,
            'raw':       line,
            'parsed':    parsed,
            'ok':        parsed is not None,
        })
    except Exception as e:
        return jsonify({
            'connected': False,
            'raw':       None,
            'parsed':    None,
            'ok':        False,
            'error':     str(e),
        }), 503
