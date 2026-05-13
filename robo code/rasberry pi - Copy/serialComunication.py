import importlib
import time
import serial
import serial.tools.list_ports

# Find Arduino port
ports = serial.tools.list_ports.comports()
arduino_port = None

for port in ports:
    if 'Arduino' in port.description or 'CH340' in port.description:  # Adjust if needed
        arduino_port = port.device
        break

if arduino_port:
    try:
        arduino = serial.Serial(arduino_port, 9600, timeout=1)
        time.sleep(2)  # Wait for connection to establish
        print(f"Connected to {arduino_port}")
        print("Serial connection established")
    except Exception as e:
        print(f"Error connecting to Arduino: {e}")
else:
    print("Arduino not found. Available ports:")
    for port in ports:
        print(f"  {port.device}: {port.description}")


while True:
    if arduino.in_waiting > 0:
        data = arduino.readline().decode('utf-8').strip()
        
        if data.startswith("WALL:"):
            # Parse wall detection data
            values = data.replace("WALL:", "").split(",")
            remaining_turn = float(values[0])
            wall_angle = float(values[1])
            turn_amount = float(values[2])
            
            print(f"Wall detected! Turn: {remaining_turn}°")
            # Send motor control commands here
            # control_motors(remaining_turn)
            
        elif data == "SAFE":
            print("Path clear, moving forward")
            # Move forward
            # move_forward()
    
    time.sleep(0.1)