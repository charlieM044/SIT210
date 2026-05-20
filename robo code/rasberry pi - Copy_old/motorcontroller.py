"""
motorcontroller.py  –  L298N / L293D dual H-bridge driver
Fix vs original:
  • stop() now also sets IN1/IN2 LOW so the motor is actively braked,
    not just coasting (PWM=0 with IN1/IN2 HIGH can still allow current flow
    on some drivers).
"""

import time
import platform

IS_RASPBERRY_PI = platform.machine() in ('armv7l', 'aarch64')

if IS_RASPBERRY_PI:
    import RPi.GPIO as GPIO
else:
    class MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        HIGH = 1
        LOW  = 0

        @staticmethod
        def setmode(mode): pass

        @staticmethod
        def setup(pin, mode): pass

        @staticmethod
        def output(pin, state):
            print(f"[MOCK GPIO] pin={pin} → {state}")

        @staticmethod
        def cleanup(): pass

        class PWM:
            def __init__(self, pin, freq):
                self.pin = pin
            def start(self, dc): pass
            def ChangeDutyCycle(self, dc):
                print(f"[MOCK GPIO] PWM pin={self.pin} duty={dc}%")
            def stop(self): pass

    GPIO = MockGPIO()

# ── Pin assignments ────────────────────────────────────────────────────────────
MOTOR1_IN1 = 17
MOTOR1_IN2 = 27
MOTOR1_PWM = 22
MOTOR2_IN1 = 23
MOTOR2_IN2 = 24
MOTOR2_PWM = 25


class MotorController:
    def __init__(self, max_speed=100):
        self.max_speed     = max_speed
        self.current_speed = 0

        GPIO.setmode(GPIO.BCM)
        for pin in [MOTOR1_IN1, MOTOR1_IN2, MOTOR1_PWM,
                    MOTOR2_IN1, MOTOR2_IN2, MOTOR2_PWM]:
            GPIO.setup(pin, GPIO.OUT)

        self.pwm1 = GPIO.PWM(MOTOR1_PWM, 1000)
        self.pwm2 = GPIO.PWM(MOTOR2_PWM, 1000)
        self.pwm1.start(0)
        self.pwm2.start(0)
        print("[Motors] ✓ initialised")

    # ── Internal ───────────────────────────────────────────────────────────────
    def _set_motor(self, in1, in2, pwm, speed):
        speed = max(-self.max_speed, min(self.max_speed, speed))
        if speed > 0:
            GPIO.output(in1, GPIO.HIGH)
            GPIO.output(in2, GPIO.LOW)
            pwm.ChangeDutyCycle(speed)
        elif speed < 0:
            GPIO.output(in1, GPIO.LOW)
            GPIO.output(in2, GPIO.HIGH)
            pwm.ChangeDutyCycle(-speed)
        else:
            GPIO.output(in1, GPIO.LOW)
            GPIO.output(in2, GPIO.LOW)
            pwm.ChangeDutyCycle(0)

    # ── Public API ─────────────────────────────────────────────────────────────
    def forward(self, speed=60):
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1,  speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2,  speed)
        self.current_speed = speed
        print(f"[Motors] forward {speed}%")

    def backward(self, speed=60):
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1, -speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2, -speed)
        self.current_speed = -speed
        print(f"[Motors] backward {speed}%")

    def left(self, speed=60):
        """Pivot left – left motor reverse, right motor forward."""
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1, -speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2,  speed)
        print(f"[Motors] left {speed}%")

    def right(self, speed=60):
        """Pivot right – left motor forward, right motor reverse."""
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1,  speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2, -speed)
        print(f"[Motors] right {speed}%")

    def turn_left_angle(self, angle):
        """Gradual left curve proportional to angle (from Arduino)."""
        base_speed = self.current_speed if self.current_speed != 0 else 60
        reduction = min(abs(angle) / 90.0 * self.max_speed, self.max_speed)
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1, base_speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2,
                        max(base_speed - reduction, 0))
        self.current_speed = base_speed
        print(f"[Motors] auto-turn left {angle}° (base {base_speed}%)")

    def turn_right_angle(self, angle):
        """Gradual right curve proportional to angle (from Arduino)."""
        base_speed = self.current_speed if self.current_speed != 0 else 60
        reduction = min(abs(angle) / 90.0 * self.max_speed, self.max_speed)
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1,
                        max(base_speed - reduction, 0))
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2, base_speed)
        self.current_speed = base_speed
        print(f"[Motors] auto-turn right {angle}° (base {base_speed}%)")

    def stop(self):
        """Actively brake both motors."""
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1, 0)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2, 0)
        self.current_speed = 0
        print("[Motors] stopped")

    def cleanup(self):
        self.stop()
        self.pwm1.stop()
        self.pwm2.stop()
        GPIO.cleanup()
        print("[Motors] GPIO cleaned up")
        
def test_motor_controller():
    print("\n=== STARTING MOTOR CONTROLLER TEST SEQUENCE ===")
    
    # 1. Initialize the controller
    # Adjust max_speed here if you want to test capping limits (e.g., max_speed=80)
    controller = MotorController(max_speed=100)
    
    try:
        # 2. Test Forward Drive
        print("\n--- Testing: Forward (50% speed for 2 seconds) ---")
        controller._set_motor(MOTOR1_IN1, MOTOR1_IN2, controller.pwm1, 50)
        controller._set_motor(MOTOR2_IN1, MOTOR2_IN2, controller.pwm2, 50)
        time.sleep(2)

        # 3. Test Backward Drive
        print("\n--- Testing: Reverse (50% speed for 2 seconds) ---")
        controller._set_motor(MOTOR1_IN1, MOTOR1_IN2, controller.pwm1, -50)
        controller._set_motor(MOTOR2_IN1, MOTOR2_IN2, controller.pwm2, -50)
        time.sleep(2)

        # 4. Test Zero / Stop Condition
        print("\n--- Testing: Full Stop (1 second) ---")
        controller._set_motor(MOTOR1_IN1, MOTOR1_IN2, controller.pwm1, 0)
        controller._set_motor(MOTOR2_IN1, MOTOR2_IN2, controller.pwm2, 0)
        time.sleep(1)

        # 5. Test Tank Turn / Opposite Directions
        print("\n--- Testing: Spin Turn Right (Left forward 40%, Right reverse 40% for 1.5 seconds) ---")
        controller._set_motor(MOTOR1_IN1, MOTOR1_IN2, controller.pwm1, 40)    # Motor 1 Forward
        controller._set_motor(MOTOR2_IN1, MOTOR2_IN2, controller.pwm2, -40)   # Motor 2 Reverse
        time.sleep(1.5)

        # 6. Test Safeguards (Speed Clipping)
        print("\n--- Testing: Speed Cap Safeguard (Requesting 150% speed) ---")
        print("Expected behavior: PWM duty cycle should cap tightly at the max_speed ceiling.")
        controller._set_motor(MOTOR1_IN1, MOTOR1_IN2, controller.pwm1, 150)
        time.sleep(1)

    except KeyboardInterrupt:
        print("\n[Test] Sequence interrupted by user.")
        
    finally:
        # 7. Safety Cleanup
        print("\n--- Testing: Cleanup & Emergency Stop ---")
        # Explicitly zero out the motors first
        controller._set_motor(MOTOR1_IN1, MOTOR1_IN2, controller.pwm1, 0)
        controller._set_motor(MOTOR2_IN1, MOTOR2_IN2, controller.pwm2, 0)
        
        # Stop PWM streams
        controller.pwm1.stop()
        controller.pwm2.stop()
        
        # Release the GPIO pins back to the system safely
        GPIO.cleanup()
        print("=== TEST SEQUENCE COMPLETE: GPIO Cleaned Up ===")

if __name__ == "__main__":
    test_motor_controller()
