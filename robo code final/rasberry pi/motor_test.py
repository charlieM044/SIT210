"""


Run with:
    python3 motor_test.py
"""

import time
import sys
import os

# Allow running from any directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hardware.motors import motors

DURATION = 2   # seconds per test

def test(label, fn):
    print(f"\n[Test] {label} ...", flush=True)
    fn()
    time.sleep(DURATION)
    motors.stop()
    time.sleep(0.5)   # brief pause between tests

try:
    print("=" * 40)
    print("  Motor Test  –  Ctrl-C to abort")
    print("=" * 40)

    test("FORWARD",  motors.forward)
    test("BACKWARD", motors.backward)
    test("LEFT",     motors.left)
    test("RIGHT",    motors.right)

    # Individual motor test – useful for checking wiring polarity
    print("\n[Test] MOTOR 1 only (forward) ...")
    from config import MOTOR1_IN1, MOTOR1_IN2, IS_PI
    if IS_PI:
        import RPi.GPIO as GPIO
        GPIO.output(MOTOR1_IN1, GPIO.HIGH)
        GPIO.output(MOTOR1_IN2, GPIO.LOW)
        from hardware.motors import motors as m
        m.pwm1.ChangeDutyCycle(60)
    time.sleep(DURATION)
    motors.stop()
    time.sleep(0.5)

    print("\n[Test] MOTOR 2 only (forward) ...")
    if IS_PI:
        GPIO.output(MOTOR2_IN1, GPIO.HIGH)
        GPIO.output(MOTOR2_IN2, GPIO.LOW)
        from config import MOTOR2_IN1, MOTOR2_IN2
        m.pwm2.ChangeDutyCycle(60)
    time.sleep(DURATION)
    motors.stop()

    print("\n✓ All tests complete — motors OK")

except KeyboardInterrupt:
    print("\n[Test] Aborted by user")

finally:
    motors.cleanup()
    print("[Test] GPIO cleaned up")
