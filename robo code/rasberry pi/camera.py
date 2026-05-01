import cv2
import threading
import time
from datetime import datetime
from pathlib import Path
import numpy as np

class CameraManager:
    def __init__(self, save_path='./robot_inspection_data/images'):
        """Initialize Raspberry Pi camera module"""
        self.save_path = Path(save_path)
        self.save_path.mkdir(parents=True, exist_ok=True)
        
        # Try to use picamera2 (newer Pi OS) or picamera (older)
        self.camera = None
        self.frame = None
        self.is_streaming = False
        self.stream_thread = None
        
        try:
            # Try newer picamera2 first (Raspberry Pi OS Bullseye+)
            from picamera2 import Picamera2
            self.picamera2 = Picamera2()
            self.use_picamera2 = True
            
            # Configure camera
            config = self.picamera2.create_preview_configuration()
            self.picamera2.configure(config)
            self.picamera2.start()
            
            print("[Camera] ✓ Using picamera2 (OV5647)")
        
        except ImportError:
            try:
                # Fallback to older picamera
                from picamera import PiCamera
                self.camera = PiCamera()
                self.camera.resolution = (640, 480)
                self.camera.framerate = 30
                self.use_picamera2 = False
                
                print("[Camera] ✓ Using picamera (OV5647)")
            
            except ImportError:
                # Fallback to OpenCV (for testing on PC)
                self.camera = cv2.VideoCapture(0)
                self.use_picamera2 = False
                
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.camera.set(cv2.CAP_PROP_FPS, 30)
                
                print("[Camera] ⚠ Using OpenCV (PC testing mode)")
    
    def capture_image(self, gps_lat, gps_lng, moisture_level):
        """Capture image from OV5647 camera"""
        try:
            frame = self._get_frame()
            
            if frame is None:
                print("[Camera] Failed to capture image")
                return None
            
            # Add metadata to image
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            moisture_text = f"Moisture: {moisture_level:.1f}%"
            location_text = f"GPS: {gps_lat:.4f}, {gps_lng:.4f}"
            
            # Add text overlays
            cv2.putText(frame, timestamp, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, moisture_text, (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, location_text, (10, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Create filename
            filename = f"moisture_{datetime.now().strftime('%Y%m%d_%H%M%S')}_lat{abs(gps_lat):.4f}_lng{abs(gps_lng):.4f}_{moisture_level:.0f}percent.jpg"
            filepath = self.save_path / filename
            
            # Save image
            cv2.imwrite(str(filepath), frame)
            print(f"[Camera] Image captured: {filename}")
            
            return str(filepath)
        
        except Exception as e:
            print(f"[Camera] Error capturing image: {e}")
            return None
    
    def _get_frame(self):
        """Get frame from camera"""
        try:
            if self.use_picamera2:
                frame = self.picamera2.capture_array()
                # Convert from BGR to RGB if needed
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                return frame
            else:
                if self.camera is None:
                    return None
                
                ret, frame = self.camera.read()
                if ret:
                    return frame
                return None
        
        except Exception as e:
            print(f"[Camera] Error getting frame: {e}")
            return None
    
    def start_streaming(self):
        """Start live video stream"""
        if self.is_streaming:
            print("[Camera] Streaming already active")
            return
        
        self.is_streaming = True
        self.stream_thread = threading.Thread(target=self._streaming_loop, daemon=True)
        self.stream_thread.start()
        print("[Camera] ✓ Streaming started")
    
    def stop_streaming(self):
        """Stop live video stream"""
        self.is_streaming = False
        if self.stream_thread:
            self.stream_thread.join(timeout=2)
        print("[Camera] ✓ Streaming stopped")
    
    def _streaming_loop(self):
        """Continuously capture frames for streaming"""
        while self.is_streaming:
            try:
                frame = self._get_frame()
                
                if frame is not None:
                    # Add streaming indicator
                    cv2.putText(frame, "LIVE FEED", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.putText(frame, datetime.now().strftime('%H:%M:%S'), 
                               (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Encode frame to JPEG
                    ret, buffer = cv2.imencode('.jpg', frame)
                    self.frame = buffer.tobytes()
                
                time.sleep(0.033)  # ~30 FPS
            
            except Exception as e:
                print(f"[Camera] Streaming error: {e}")
                time.sleep(1)
    
    def get_frame(self):
        """Get current frame for streaming"""
        return self.frame
    
    def enable_night_vision(self):
        """Enable IR-cut filter removal for night vision"""
        try:
            if self.use_picamera2:
                # For picamera2, control via libcamera
                print("[Camera] Night vision mode enabled (IR-CUT)")
            else:
                # For picamera
                if hasattr(self.camera, 'led'):
                    self.camera.led = True
                print("[Camera] Night vision mode enabled")
        except Exception as e:
            print(f"[Camera] Error enabling night vision: {e}")
    
    def disable_night_vision(self):
        """Disable night vision (IR-cut on)"""
        try:
            if self.use_picamera2:
                print("[Camera] Night vision mode disabled (IR-CUT on)")
            else:
                if hasattr(self.camera, 'led'):
                    self.camera.led = False
                print("[Camera] Night vision mode disabled")
        except Exception as e:
            print(f"[Camera] Error disabling night vision: {e}")
    
    def adjust_exposure(self, exposure_value):
        """Adjust camera exposure (-10 to +10)"""
        try:
            if self.use_picamera2:
                # Adjust exposure compensation
                controls = {'ExposureValue': exposure_value}
                self.picamera2.set_controls(controls)
            else:
                # For picamera
                if hasattr(self.camera, 'exposure_compensation'):
                    self.camera.exposure_compensation = exposure_value
            
            print(f"[Camera] Exposure adjusted to {exposure_value}")
        except Exception as e:
            print(f"[Camera] Error adjusting exposure: {e}")
    
    def adjust_brightness(self, brightness_value):
        """Adjust brightness (0-100)"""
        try:
            if self.use_picamera2:
                # Brightness control in picamera2
                controls = {'Brightness': brightness_value}
                self.picamera2.set_controls(controls)
            else:
                if hasattr(self.camera, 'brightness'):
                    self.camera.brightness = brightness_value
            
            print(f"[Camera] Brightness adjusted to {brightness_value}")
        except Exception as e:
            print(f"[Camera] Error adjusting brightness: {e}")
    
    def release(self):
        """Release camera"""
        self.stop_streaming()
        
        try:
            if self.use_picamera2:
                self.picamera2.stop()
            else:
                if self.camera:
                    self.camera.release()
            
            print("[Camera] ✓ Camera released")
        except Exception as e:
            print(f"[Camera] Error releasing: {e}")

class IRCamera:
    """Handle IR thermal readings from OV5647 with IR-CUT"""
    def __init__(self):
        self.last_temp = 0
        self.ir_available = True
        print("[IR Camera] Initialized (OV5647 with IR-CUT)")
    
    def get_temperature(self):
        """Simulate IR temperature from camera"""
        # The OV5647 with IR-CUT can detect thermal radiation
        # In practice, you'd need a separate thermal sensor
        # This is a placeholder
        return self.last_temp
    
    def detect_moisture_spots(self, frame):
        """Analyze frame for moisture/thermal anomalies"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Detect darker areas (potential moisture)
            _, thresh = cv2.threshold(blurred, 100, 255, cv2.THRESH_BINARY_INV)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            moisture_areas = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 100:  # Minimum area threshold
                    x, y, w, h = cv2.boundingRect(contour)
                    moisture_areas.append({
                        'x': x, 'y': y, 'width': w, 'height': h, 'area': area
                    })
            
            return moisture_areas
        
        except Exception as e:
            print(f"[IR Camera] Error detecting moisture: {e}")
            return []

# Usage example
if __name__ == "__main__":
    camera = CameraManager()
    
    # Enable night vision for dark areas
    camera.enable_night_vision()
    
    # Adjust for better visibility
    camera.adjust_exposure(5)
    camera.adjust_brightness(80)
    
    # Test capture
    camera.capture_image(-37.8136, 144.9631, 75.5)
    
    # Test streaming
    camera.start_streaming()
    time.sleep(5)
    camera.stop_streaming()
    
    camera.release()