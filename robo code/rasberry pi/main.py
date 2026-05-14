import threading
import time
import sys
from datetime import datetime

# Import all modules

import pi_server
from saveData import LocalDataManager
from camera import CameraManager
from pi_server import app as flask_app

class RobotMain:
    def __init__(self):
        """Initialize all robot components"""
        print("=" * 50)
        print("🤖 Moisture Detection Robot - Starting up")
        print("=" * 50)
        
        self.client = None
        self.storage = LocalDataManager('./robot_inspection_data')
        self.camera = CameraManager()
        
        
        self.running = True
        self.threads = []
    
    def start_flask_server(self):
        """Start Flask web server"""
        print("[Flask] Starting web server on port 5000...")
        try:
            flask_app.run(host='0.0.0.0', port=5000, debug=False, threaded = True ,use_reloader=False)
        except Exception as e:
            print(f"[Flask] Error: {e}")

    def start_monitoring(self):
        """Monitor system health and log data"""
        print("[Monitor] Starting system monitoring...")
        while self.running:
            try:
                # Log system status every 30 seconds
                time.sleep(30)
                
                # Get storage info
                info = self.storage.get_storage_info()
                stats = self.storage.get_moisture_stats()
                
                print(f"\n[Monitor] System Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  Files: {info['total_files']}")
                print(f"  Storage: {info['total_size_mb']} MB")
                print(f"  Images: {info['images']}")
                
                if stats:
                    print(f"  Readings: {stats['count']}")
                    print(f"  Avg Moisture: {stats['average']:.1f}%")
                    print(f"  Critical Areas: {stats['critical_count']}")
                
            except Exception as e:
                print(f"[Monitor] Error: {e}")
    
    def start_all(self):
            # 1. Start the Camera (Internal thread)
            self.camera.start_streaming()
            
            # 2. Start Flask in a thread
            flask_thread = threading.Thread(target=self.start_flask_server, daemon=True)
            flask_thread.start()
            
            # 3. RUN EVERYTHING ELSE IN THE MAIN THREAD (No more extra threads)
            print("[Main] Logic loop starting...")
            while self.running:
                self.run_autonomous_logic() # Motors + Moisture check
                self.update_monitoring()    # System health
                time.sleep(0.5)             # CRITICAL: This gives the Pi time to breathe
    
    def shutdown(self):
        """Graceful shutdown"""
        print("[Main] Shutting down all components...")
        
        self.running = False
        
        # Release camera
        try:
            self.camera.release()
            print("[Main] ✓ Camera released")
        except:
            pass
        
        # Wait for threads
        print("[Main] Waiting for threads to finish...")
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=3)
        
        print("[Main] ✓ All components stopped")
        print("[Main] Robot system shutdown complete")
        sys.exit(0)

def main():
    """Main entry point"""
    
    
    robot = RobotMain()
    robot.start_all()

if __name__ == "__main__":
    main()
