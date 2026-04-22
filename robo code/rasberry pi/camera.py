import cv2  # type: ignore[import-not-found]
import threading
import time
from datetime import datetime
from pathlib import Path
import json

class CameraManager:
    def __init__(self, save_path='./robot_inspection_data/images'):
        """Initialize camera"""
        self.camera = cv2.VideoCapture(0)  # 0 = default camera
        self.save_path = Path(save_path)
        self.save_path.mkdir(parents=True, exist_ok=True)
        
        # Camera settings
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        # Streaming variables
        self.is_streaming = False
        self.current_frame = None
        self.stream_thread = None
        
        print("Camera initialized")
    
    def capture_image(self, gps_lat, gps_lng, moisture_level):
        """Capture and save image when moisture detected"""
        try:
            ret, frame = self.camera.read()
            
            if not ret:
                print("Failed to capture image")
                return None
            
            # Add timestamp and moisture info to image
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            moisture_text = f"Moisture: {moisture_level:.1f}%"
            location_text = f"GPS: {gps_lat:.4f}, {gps_lng:.4f}"
            
            # Add text to frame
            cv2.putText(frame, timestamp, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, moisture_text, (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, location_text, (10, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Create filename with location and moisture
            filename = f"moisture_{datetime.now().strftime('%Y%m%d_%H%M%S')}_lat{abs(gps_lat):.4f}_lng{abs(gps_lng):.4f}_{moisture_level:.0f}percent.jpg"
            filepath = self.save_path / filename
            
            # Save image
            cv2.imwrite(str(filepath), frame)
            print(f"Image captured: {filename}")
            
            return str(filepath)
        
        except Exception as e:
            print(f"Error capturing image: {e}")
            return None
    
    def start_streaming(self):
        """Start live video stream"""
        if self.is_streaming:
            print("Streaming already active")
            return
        
        self.is_streaming = True
        self.stream_thread = threading.Thread(target=self._streaming_loop, daemon=True)
        self.stream_thread.start()
        print("Streaming started")
    
    def stop_streaming(self):
        """Stop live video stream"""
        self.is_streaming = False
        if self.stream_thread:
            self.stream_thread.join(timeout=2)
        print("Streaming stopped")
    
    def _streaming_loop(self):
        """Continuously capture frames for streaming"""
        while self.is_streaming:
            try:
                ret, frame = self.camera.read()
                
                if ret:
                    # Add streaming indicator
                    cv2.putText(frame, "LIVE FEED", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.putText(frame, datetime.now().strftime('%H:%M:%S'), 
                               (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Encode frame to JPEG
                    ret, buffer = cv2.imencode('.jpg', frame)
                    self.current_frame = buffer.tobytes()
                
                time.sleep(0.033)  # ~30 FPS
            
            except Exception as e:
                print(f"Streaming error: {e}")
                time.sleep(1)
    
    def get_frame(self):
        """Get current frame for streaming"""
        return self.current_frame
    
    def release(self):
        """Release camera"""
        self.stop_streaming()
        self.camera.release()
        print("Camera released")

class IRCamera:
    """Handle IR thermal camera if available"""
    def __init__(self, port='/dev/ttyUSB0'):
        self.port = port
        self.connected = False
        self.last_temp = 0
        
        try:
            import serial
            self.serial = serial.Serial(port, 115200, timeout=1)
            self.connected = True
            print("IR camera connected")
        except Exception as e:
            print(f"IR camera not available: {e}")
    
    def get_temperature(self):
        """Read temperature from IR camera"""
        if not self.connected:
            return None
        
        try:
            if self.serial.in_waiting > 0:
                data = self.serial.readline().decode('utf-8').strip()
                self.last_temp = float(data)
                return self.last_temp
        except Exception as e:
            print(f"Error reading IR temperature: {e}")
        
        return self.last_temp
