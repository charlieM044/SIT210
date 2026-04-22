import requests
import json
from saveData import LocalDataManager
import serial
import time

class RobotClient:
    def __init__(self, server_url='http://raspberrypi.local:5000'):
        self.server_url = server_url
        self.storage = LocalDataManager('./robot_inspection_data')
        self.arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
        time.sleep(2)
        print(f"Connected to server: {self.server_url}")
    
    def send_sensor_data(self, gps_lat, gps_lng, moisture, ir_temp=None, 
                        image_path=None, severity='Minor'):
        """Save locally and send to computer"""
        
        # Save locally first
        self.storage.add_moisture_reading(
            gps_lat, gps_lng, moisture, ir_temp, image_path, severity
        )
        
        # Send to computer server
        try:
            data = {
                'gps_lat': gps_lat,
                'gps_lng': gps_lng,
                'moisture': moisture,
                'ir_temp': ir_temp,
                'severity': severity,
                'timestamp': time.time()
            }
            
            response = requests.post(
                f'{self.server_url}/api/sensor-data',
                json=data,
                timeout=5
            )
            
            if response.status_code == 200:
                print("Data sent to computer ✓")
            else:
                print(f"Failed to send data: {response.status_code}")
        
        except requests.exceptions.ConnectionError:
            print("Computer not connected - data saved locally")
        except Exception as e:
            print(f"Error sending data: {e}")
    
    def get_control_commands(self):
        """Check computer for motor control commands"""
        try:
            response = requests.get(
                f'{self.server_url}/api/commands',
                timeout=2
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        
        except Exception as e:
            print(f"Error getting commands: {e}")
            return None
    
    def send_motor_command(self, command):
        """Send command to Arduino motors"""
        if command == 'forward':
            self.arduino.write(b'F')
        elif command == 'backward':
            self.arduino.write(b'B')
        elif command == 'left':
            self.arduino.write(b'L')
        elif command == 'right':
            self.arduino.write(b'R')
        elif command == 'stop':
            self.arduino.write(b'S')
    
    def run(self):
        """Main loop - collect data and check for commands"""
        while True:
            # Check for control commands from computer
            commands = self.get_control_commands()
            if commands:
                for cmd in commands:
                    self.send_motor_command(cmd)
            
            # Collect sensor data (from your existing code)
            # ... your sensor reading code ...
            
            time.sleep(0.5)

# Usage
if __name__ == "__main__":
    client = RobotClient('http://raspberrypi.local:5000')
    client.run()