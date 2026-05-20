"""
hardware/__init__.py
Exposes the three singletons so the rest of the codebase imports cleanly:

    from hardware import camera, motors, arduino
"""

from hardware.camera  import camera
from hardware.motors  import motors
from hardware.arduino import arduino, read_line, parse
