import serial
import time
import sys
import platform
import py_compile
import os

# Syntax check - compile the script to ensure it's valid Python
try:
    script_path = os.path.abspath(__file__)
    py_compile.compile(script_path, doraise=True)
    print(f"✓ Syntax check passed for {os.path.basename(script_path)}")
except py_compile.PyCompileError as e:
    print(f"✗ Syntax error in script: {e}")
    sys.exit(1)

# Platform detection
IS_RASPBERRY_PI = platform.machine() == 'armv7l' or platform.machine() == 'aarch64'
IS_WINDOWS = platform.system() == 'Windows'

# GPIO setup - use mock on Windows, real on Pi
if IS_RASPBERRY_PI:
    import RPi.GPIO as GPIO
    GPIO_MODE = GPIO
else:
    # Mock GPIO for Windows testing
    class MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        HIGH = 1
        LOW = 0
        
        @staticmethod
        def setmode(mode):
            print(f"[MOCK GPIO] setmode({mode})")
        
        @staticmethod
        def setup(pin, mode):
            print(f"[MOCK GPIO] setup(pin={pin}, mode={mode})")
        
        @staticmethod
        def output(pin, state):
            print(f"[MOCK GPIO] output(pin={pin}, state={state})")
        
        @staticmethod
        def cleanup():
            print("[MOCK GPIO] cleanup()")
        
        class PWM:
            def __init__(self, pin, frequency):
                self.pin = pin
                self.frequency = frequency
                print(f"[MOCK GPIO] PWM(pin={pin}, freq={frequency}Hz)")
            
            def start(self, duty_cycle):
                print(f"[MOCK GPIO] PWM.start(duty_cycle={duty_cycle}%)")
            
            def ChangeDutyCycle(self, duty_cycle):
                print(f"[MOCK GPIO] PWM.ChangeDutyCycle({duty_cycle}%)")
            
            def stop(self):
                print("[MOCK GPIO] PWM.stop()")
    
    GPIO_MODE = MockGPIO()

# GPIO setup for motors
GPIO_MODE.setmode(GPIO_MODE.BCM)


# Motor 1 pins
MOTOR1_IN1 = 17
MOTOR1_IN2 = 27
MOTOR1_PWM = 22

# Motor 2 pins
MOTOR2_IN1 = 23
MOTOR2_IN2 = 24
MOTOR2_PWM = 25

# Setup GPIO pins
for pin in [MOTOR1_IN1, MOTOR1_IN2, MOTOR1_PWM, MOTOR2_IN1, MOTOR2_IN2, MOTOR2_PWM]:
    GPIO_MODE.setup(pin, GPIO_MODE.OUT)

# Create PWM objects for speed control
pwm1 = GPIO_MODE.PWM(MOTOR1_PWM, 1000)  # 1kHz frequency
pwm2 = GPIO_MODE.PWM(MOTOR2_PWM, 1000)
pwm1.start(0)
pwm2.start(0)

# Open serial connection - use appropriate port based on platform
if IS_RASPBERRY_PI:
    SERIAL_PORT = '/dev/ttyACM0'
elif IS_WINDOWS:
    SERIAL_PORT = 'COM6'  # Change to your COM port
else:
    SERIAL_PORT = '/dev/ttyUSB0'  # Generic Linux fallback

try:
    arduino = serial.Serial(SERIAL_PORT, 9600, timeout=1)
    time.sleep(2)
    print(f"✓ Connected to Arduino on {SERIAL_PORT}")
except Exception as e:
    print(f"✗ Failed to connect to {SERIAL_PORT}: {e}")
    if IS_WINDOWS:
        print("  Tip: Check Device Manager for the correct COM port")
    arduino = None


class MotorController:
    def __init__(self, max_speed=100):
        self.max_speed = max_speed
        self.current_speed = 0
    
    def forward(self, speed=100):
        """Move both motors forward"""
        self.set_motor(MOTOR1_IN1, MOTOR1_IN2, pwm1, speed)
        self.set_motor(MOTOR2_IN1, MOTOR2_IN2, pwm2, speed)
        self.current_speed = speed
        print(f"Moving forward at {speed}%")
    
    def backward(self, speed=100):
        """Move both motors backward"""
        self.set_motor(MOTOR1_IN1, MOTOR1_IN2, pwm1, -speed)
        self.set_motor(MOTOR2_IN1, MOTOR2_IN2, pwm2, -speed)
        self.current_speed = -speed
        print(f"Moving backward at {speed}%")
    
    def turn_left(self, turn_angle):
        """Turn left based on angle from Arduino"""
        # Convert angle to speed difference
        speed_reduction = abs(turn_angle) / 90.0 * 100  # 90° = full stop on one side
        speed_reduction = min(speed_reduction, 100)
        
        # Slow down right motor, keep left faster
        self.set_motor(MOTOR1_IN1, MOTOR1_IN2, pwm1, self.current_speed)
        self.set_motor(MOTOR2_IN1, MOTOR2_IN2, pwm2, self.current_speed - speed_reduction)
        print(f"Turning left {turn_angle}°")
    
    def turn_right(self, turn_angle):
        """Turn right based on angle from Arduino"""
        # Convert angle to speed difference
        speed_reduction = abs(turn_angle) / 90.0 * 100
        speed_reduction = min(speed_reduction, 100)
        
        # Slow down left motor, keep right faster
        self.set_motor(MOTOR1_IN1, MOTOR1_IN2, pwm1, self.current_speed - speed_reduction)
        self.set_motor(MOTOR2_IN1, MOTOR2_IN2, pwm2, self.current_speed)
        print(f"Turning right {turn_angle}°")
    
    def stop(self):
        """Stop all motors"""
        pwm1.ChangeDutyCycle(0)
        pwm2.ChangeDutyCycle(0)
        self.current_speed = 0
        print("Motors stopped")
    
    def set_motor(self, in1, in2, pwm, speed):
        """Set individual motor speed (-100 to 100)"""
        speed = max(-100, min(100, speed))  # Clamp speed
        
        if speed > 0:
            GPIO_MODE.output(in1, GPIO_MODE.HIGH)
            GPIO_MODE.output(in2, GPIO_MODE.LOW)
            pwm.ChangeDutyCycle(speed)
        elif speed < 0:
            GPIO_MODE.output(in1, GPIO_MODE.LOW)
            GPIO_MODE.output(in2, GPIO_MODE.HIGH)
            pwm.ChangeDutyCycle(-speed)
        else:
            GPIO_MODE.output(in1, GPIO_MODE.LOW)
            GPIO_MODE.output(in2, GPIO_MODE.LOW)
            pwm.ChangeDutyCycle(0)

# Create motor controller instance
motors = MotorController(max_speed=100)

# Main loop - read Arduino data and control motors
print("\n" + "="*50)
print("Motor Controller Started")
print(f"Platform: {platform.system()} ({platform.machine()})")
print(f"Mode: {'Raspberry Pi' if IS_RASPBERRY_PI else 'Windows/Mock GPIO' if IS_WINDOWS else 'Linux'}")
print("="*50 + "\n")

try:
    motors.forward(50)  # Start moving forward at 50% speed
    
    if arduino is None:
        print("[INFO] No Arduino connected - running in test/simulation mode")
        print("[INFO] Waiting for user input to simulate motor commands...")
        time.sleep(3)
    
    while True:
        if arduino and arduino.in_waiting > 0:
            try:
                data = arduino.readline().decode('utf-8').strip()
                
                if data.startswith("WALL:"):
                    # Parse wall detection data
                    values = data.replace("WALL:", "").split(",")
                    remaining_turn = float(values[0])
                    wall_angle = float(values[1])
                    turn_amount = float(values[2])
                    
                    print(f"Wall detected! Need to turn: {remaining_turn}°")
                    
                    # Avoid wall based on remaining turn
                    if remaining_turn > 5:  # Threshold to avoid noise
                        if remaining_turn > 0:
                            motors.turn_left(remaining_turn)
                        else:
                            motors.turn_right(abs(remaining_turn))
                    else:
                        motors.forward(50)  # Continue forward if properly angled
                
                elif data == "SAFE":
                    print("Path clear, moving forward")
                    motors.forward(50)
            except ValueError as e:
                print(f"✗ Error parsing Arduino data: {e}")
            except Exception as e:
                print(f"✗ Error reading from Arduino: {e}")
        else:
            # Simulation mode when no Arduino data available
            if not arduino:
                time.sleep(1)  # Simulate some delay
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\nShutting down...")
    motors.stop()
    if arduino:
        arduino.close()
    if hasattr(GPIO_MODE, 'cleanup'):
        GPIO_MODE.cleanup()
    print("✓ Cleanup complete")
    sys.exit(0)
except Exception as e:
    print(f"✗ Fatal error: {e}")
    import traceback
    traceback.print_exc()
    if arduino:
        arduino.close()
    if hasattr(GPIO_MODE, 'cleanup'):
        GPIO_MODE.cleanup()
    sys.exit(1)