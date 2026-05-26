"""


Run with:
    python3 motor_test.py
"""
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hardware.motors import motors

DURATION = 2.0

def test(label, fn, *args):
    print(f"\n[Test] {label} ...", flush=True)
    try:
        fn(*args)
    except Exception as e:
        print(f"  ↳ Error: {e}")
    time.sleep(DURATION)
    motors.stop()
    time.sleep(0.5)

try:
    print("=" * 40)
    print("  Motor Test — Ctrl-C to abort")
    print("=" * 40)

    test("FORWARD",  motors.forward)
    test("BACKWARD", motors.backward)
    test("LEFT",     motors.left)
    test("RIGHT",    motors.right)
    test("forward test", motors.test_raw_forward)
    test("backward test", motors.test_raw_backward)

    print("\n✓ All tests complete")

except KeyboardInterrupt:
    print("\n[Test] Aborted by user")
finally:
    print("\n[Cleanup] Shutting down...")
    try:
        motors.shutdown()
    except Exception as e:
        print(f"  ↳ {e}")
