import threading
import time
import sys
from datetime import datetime

from saveData import LocalDataManager
from camera import CameraManager, IRCamera
from pi_server import app as flask_app

class RobotMain:
    def __init__(self):
        print("=" * 50)
        print("🤖 Moisture Detection Robot - Starting up")
        print("=" * 50)

        # These are already initialised inside pi_server.py,
        # but we keep references here for the shutdown/monitor thread.
        self.storage  = LocalDataManager('./robot_inspection_data')
        self.running  = True
        self.threads  = []

    def start_flask_server(self):
        print("[Flask] Starting on port 5000...")
        try:
            flask_app.run(host='0.0.0.0', port=5000,
                          debug=False, use_reloader=False)
        except Exception as e:
            print(f"[Flask] Error: {e}")

    def start_monitoring(self):
        print("[Monitor] System monitor started")
        while self.running:
            try:
                time.sleep(30)
                info  = self.storage.get_storage_info()
                stats = self.storage.get_moisture_stats()
                print(f"\n[Monitor] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  Files:   {info['total_files']}  |  "
                      f"Storage: {info['total_size_mb']} MB  |  "
                      f"Images: {info['images']}")
                if stats:
                    print(f"  Readings: {stats['count']}  |  "
                          f"Avg moisture: {stats['average']:.1f}%  |  "
                          f"Critical: {stats['critical_count']}")
            except Exception as e:
                print(f"[Monitor] Error: {e}")

    def start_all(self):
        print("\n[Main] Starting components...\n")

        # Flask in a non-daemon thread so it keeps the process alive
        flask_thread = threading.Thread(
            target=self.start_flask_server,
            daemon=False, name="Flask-Server"
        )
        flask_thread.start()
        self.threads.append(flask_thread)
        time.sleep(2)   # give Flask a moment to bind
        print("[Main] ✓ Flask server running\n")

        # Monitoring thread
        monitor_thread = threading.Thread(
            target=self.start_monitoring,
            daemon=True, name="System-Monitor"
        )
        monitor_thread.start()
        self.threads.append(monitor_thread)
        print("[Main] ✓ System monitor running\n")

        print("=" * 50)
        print("✓ Robot system fully operational!")
        print("  Web interface : http://192.168.4.1:5000")
        print("  Press Ctrl+C to shutdown")
        print("=" * 50 + "\n")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Main] Shutdown signal received...")
            self.shutdown()

    def shutdown(self):
        print("[Main] Shutting down...")
        self.running = False
        for t in self.threads:
            if t.is_alive():
                t.join(timeout=3)
        print("[Main] Shutdown complete")
        sys.exit(0)

if __name__ == "__main__":
    RobotMain().start_all()
