import threading
import time
import sys
from datetime import datetime

# Import all modules

import pi_server
from saveData import LocalDataManager
from camera import CameraManager, IRCamera
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
        self.ir_camera = IRCamera()
        
        self.running = True
        self.threads = []
    
    def start_flask_server(self):
        """Start Flask web server"""
        print("[Flask] Starting web server on port 5000...")
        try:
            flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
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
        """Start all components in separate threads"""
        print("\n[Main] Starting all components...\n")
        
        self.camera.start_streaming()
        import pi_server
        pi_server.global_camera = self.camera  # Make camera accessible to Flask routes
        
        # Flask server thread
        flask_thread = threading.Thread(
            target=self.start_flask_server,
            daemon=False,
            name="Flask-Server"
        )
        flask_thread.start()
        self.threads.append(flask_thread)
        time.sleep(2)  # Wait for Flask to start
        
        # Sensor client thread
        client_thread = threading.Thread(
            target=self.start_client,
            daemon=True,
            name="Sensor-Client"
        )
        client_thread.start()
        self.threads.append(client_thread)
        print("[Main] ✓ Sensor client started\n")
        
        # Monitoring thread
        monitor_thread = threading.Thread(
            target=self.start_monitoring,
            daemon=True,
            name="System-Monitor"
        )
        monitor_thread.start()
        self.threads.append(monitor_thread)
        print("[Main] ✓ System monitor started\n")
        
        print("=" * 50)
        print("✓ Robot system fully operational!")
        print("=" * 50)
        print("\nAccess the web interface at:")
        print("  http://raspberrypi.local:5000")
        print("\nPress Ctrl+C to shutdown\n")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Main] Shutdown signal received...")
            self.shutdown()
    
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