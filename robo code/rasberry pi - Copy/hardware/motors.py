"""
hardware/motors.py  –  L298N dual H-bridge driver.
Imports config for pin assignments so nothing is hardcoded here.
"""

import platform
from config import (
    MOTOR1_IN1, MOTOR1_IN2, MOTOR1_PWM,
    MOTOR2_IN1, MOTOR2_IN2, MOTOR2_PWM,
    MOTOR_DEFAULT_SPEED, MOTOR_PWM_FREQ, IS_PI,
)

if IS_PI:
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
        def setup(pin, mode, initial=0): pass
        @staticmethod
        def output(pin, state):
            print(f"[MOCK GPIO] pin={pin} → {state}")
        @staticmethod
        def cleanup(): pass
        class PWM:
            def __init__(self, pin, freq): self.pin = pin
            def start(self, dc): pass
            def ChangeDutyCycle(self, dc):
                print(f"[MOCK GPIO] PWM pin={self.pin} duty={dc}%")
            def stop(self): pass
    GPIO = MockGPIO()


class MotorController:
    def __init__(self):
        self.max_speed     = 100
        self.current_speed = 0

        GPIO.setmode(GPIO.BCM)
        
        # FIX 1: Set up direction pins with explicit initial LOW states to prevent startup spin.
        # DO NOT include MOTOR1_PWM or MOTOR2_PWM in this digital output loop.
        all_output_pins = [MOTOR1_IN1, MOTOR1_IN2, MOTOR1_PWM,
                           MOTOR2_IN1, MOTOR2_IN2, MOTOR2_PWM]
        for pin in all_output_pins:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

                # FIX 2: Under Bookworm, initializing GPIO.PWM handles pin setup automatically.
        self.pwm1 = GPIO.PWM(MOTOR1_PWM, MOTOR_PWM_FREQ)
        self.pwm2 = GPIO.PWM(MOTOR2_PWM, MOTOR_PWM_FREQ)
        
        # Start at 0 duty cycle safely
        self.pwm1.start(0)
        self.pwm2.start(0)
        print("[Motors] ✓ initialised")

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

    def forward(self, speed=MOTOR_DEFAULT_SPEED):
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1,  speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2,  speed)
        self.current_speed = speed
        print(f"[Motors] forward {speed}%")

    def backward(self, speed=MOTOR_DEFAULT_SPEED):
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1, -speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2, -speed)
        self.current_speed = -speed
        print(f"[Motors] backward {speed}%")

    def left(self, speed=MOTOR_DEFAULT_SPEED):
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1, -speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2,  speed)
        print(f"[Motors] left {speed}%")

    def right(self, speed=MOTOR_DEFAULT_SPEED):
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1,  speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2, -speed)
        print(f"[Motors] right {speed}%")

    def turn_left_angle(self, angle):
        reduction = min(abs(angle) / 90.0 * self.max_speed, self.max_speed)
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1, self.current_speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2,
                        max(self.current_speed - reduction, 0))
        print(f"[Motors] auto-turn left {angle}°")

    def turn_right_angle(self, angle):
        reduction = min(abs(angle) / 90.0 * self.max_speed, self.max_speed)
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1,
                        max(self.current_speed - reduction, 0))
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2, self.current_speed)
        print(f"[Motors] auto-turn right {angle}°")

    def stop(self):
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1, 0)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2, 0)
        self.current_speed = 0
        print("[Motors] stopped")
        
    def test_raw_forward(self):
        GPIO.output(MOTOR1_IN1, GPIO.HIGH)
        GPIO.output(MOTOR1_IN2, GPIO.LOW)
        self.pwm1.ChangeDutyCycle(60)
        print("[Raw] M1 IN1=HIGH IN2=LOW")

    def test_raw_backward(self):
        GPIO.output(MOTOR1_IN1, GPIO.LOW)
        GPIO.output(MOTOR1_IN2, GPIO.HIGH)
        self.pwm1.ChangeDutyCycle(60)
        print("[Raw] M1 IN1=LOW IN2=HIGH")

    def cleanup(self):
        self.shutdown()
        
    def shutdown(self):
        # FIX 3: Force duty cycles to 0 explicitly before stopping objects
        # to cleanly untangle the lgpio backend thread wrappers.
        try:
            if hasattr(self, 'pwm1') and self.pwm1:
                self.pwm1.ChangeDutyCycle(0)
                self.pwm1.stop()
            if hasattr(self, 'pwm2') and self.pwm2:
                self.pwm2.ChangeDutyCycle(0)
                self.pwm2.stop()
        except Exception:
            pass
            
        try:
            GPIO.cleanup()
            print("[Motors] GPIO cleaned up")
        except Exception as e:
            print(f"[Motors] GPIO cleanup warning: {e}")


# Module-level singleton — import this everywhere
motors = MotorController()
