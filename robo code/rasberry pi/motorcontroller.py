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
        LOW = 0
        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode): pass
        @staticmethod
        def output(pin, state):
            print(f"[MOCK GPIO] pin={pin} state={state}")
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

# Pin definitions
MOTOR1_IN1 = 17
MOTOR1_IN2 = 27
MOTOR1_PWM = 22
MOTOR2_IN1 = 23
MOTOR2_IN2 = 24
MOTOR2_PWM = 25

class MotorController:
    def __init__(self, max_speed=100):
        self.max_speed = max_speed
        self.current_speed = 0

        GPIO.setmode(GPIO.BCM)
        for pin in [MOTOR1_IN1, MOTOR1_IN2, MOTOR1_PWM,
                    MOTOR2_IN1, MOTOR2_IN2, MOTOR2_PWM]:
            GPIO.setup(pin, GPIO.OUT)

        self.pwm1 = GPIO.PWM(MOTOR1_PWM, 1000)
        self.pwm2 = GPIO.PWM(MOTOR2_PWM, 1000)
        self.pwm1.start(0)
        self.pwm2.start(0)
        print("[Motors] ✓ MotorController initialised")

    def _set_motor(self, in1, in2, pwm, speed):
        speed = max(-100, min(100, speed))
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

    def forward(self, speed=60):
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1, speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2, speed)
        self.current_speed = speed
        print(f"[Motors] Forward {speed}%")

    def backward(self, speed=60):
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1, -speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2, -speed)
        self.current_speed = -speed
        print(f"[Motors] Backward {speed}%")

    def left(self, speed=60):
        """Pivot left — left motor back, right motor forward"""
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1, -speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2, speed)
        print(f"[Motors] Left {speed}%")

    def right(self, speed=60):
        """Pivot right — left motor forward, right motor back"""
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1, speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2, -speed)
        print(f"[Motors] Right {speed}%")

    def turn_left_angle(self, angle):
        """Autonomous turn left by angle (from Arduino wall data)"""
        reduction = min(abs(angle) / 90.0 * 100, 100)
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1, self.current_speed)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2, self.current_speed - reduction)
        print(f"[Motors] Auto-turn left {angle}°")

    def turn_right_angle(self, angle):
        """Autonomous turn right by angle (from Arduino wall data)"""
        reduction = min(abs(angle) / 90.0 * 100, 100)
        self._set_motor(MOTOR1_IN1, MOTOR1_IN2, self.pwm1, self.current_speed - reduction)
        self._set_motor(MOTOR2_IN1, MOTOR2_IN2, self.pwm2, self.current_speed)
        print(f"[Motors] Auto-turn right {angle}°")

    def stop(self):
        self.pwm1.ChangeDutyCycle(0)
        self.pwm2.ChangeDutyCycle(0)
        self.current_speed = 0
        print("[Motors] Stopped")

    def cleanup(self):
        self.stop()
        self.pwm1.stop()
        self.pwm2.stop()
        GPIO.cleanup()
        print("[Motors] GPIO cleaned up")
