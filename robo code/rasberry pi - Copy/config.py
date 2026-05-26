"""
config.py  –  Every tunable constant in one place.
Change hardware pins, thresholds, or paths here without touching anything else.
"""

import platform

IS_PI = platform.machine() in ('armv7l', 'aarch64')

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR   = './robot_inspection_data'
IMAGE_DIR  = f'{DATA_DIR}/images'
DB_PATH    = f'{DATA_DIR}/robot_data.db'

# ── Storage ────────────────────────────────────────────────────────────────────
RING_BUFFER_SIZE   = 500    # readings kept in RAM
SENSOR_SAVE_INTERVAL = 5.0  # seconds between sensor saves

# ── Moisture thresholds ────────────────────────────────────────────────────────
MOISTURE_CRITICAL  = 80     # above this → Critical
MOISTURE_MODERATE  = 60     # above this → Moderate, capture image

# ── Motor GPIO pins (BCM numbering) ───────────────────────────────────────────
MOTOR1_IN1 = 17
MOTOR1_IN2 = 27
MOTOR1_PWM = 22
MOTOR2_IN1 = 23
MOTOR2_IN2 = 24
MOTOR2_PWM = 25
MOTOR_DEFAULT_SPEED = 60    # %
MOTOR_PWM_FREQ      = 100  # Hz

# ── Arduino serial ─────────────────────────────────────────────────────────────
SERIAL_PORT = '/dev/ttyACM0' if IS_PI else 'COM6'
SERIAL_BAUD = 9600

# ── Camera ─────────────────────────────────────────────────────────────────────
CAMERA_WIDTH   = 640
CAMERA_HEIGHT  = 480
CAMERA_FPS     = 10     # streaming FPS (easy on Pi RAM)
JPEG_QUALITY   = 70     # lower = smaller frames in RAM

# ── Flask ──────────────────────────────────────────────────────────────────────
PI_PORT       = 5000
FRONTEND_PORT = 8000
PI_HOST       = '0.0.0.0'
