"""
main.py  –  Entry point for the Raspberry Pi robot.
Boots hardware, starts the autonomous loop, then runs Flask.
"""

import signal
import sys
import threading
import time
from datetime import datetime

from config import PI_HOST, PI_PORT
from state import state
from hardware import camera, motors
from saveData import storage
from api.app import app
from api import autonomous


class RobotMain:
    def __init__(self):
        print("=" * 50)
        print("  Moisture Detection Robot – starting")
        print("=" * 50)
        self.running = True
        signal.signal(signal.SIGINT,  self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, sig, frame):
        print(f"\n[Main] signal {sig} – shutting down")
        self.shutdown()

    def _start_flask(self):
        print(f"[Flask] starting on {PI_HOST}:{PI_PORT}")
        try:
            app.run(host=PI_HOST, port=PI_PORT,
                    debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            print(f"[Flask] error: {e}")

    def _log_status(self):
        info  = storage.get_storage_info()
        stats = storage.get_moisture_stats()
        print(f"\n[Monitor] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Buffer : {info['buffer_size']} readings")
        print(f"  Storage: {info['total_size_mb']} MB  |  images: {info['images']}")
        if stats:
            print(f"  Avg moisture:   {stats['average']:.1f}%")
            print(f"  Critical areas: {stats['critical_count']}")

    def start_all(self):
        camera.start_streaming()
        autonomous.start()

        flask_thread = threading.Thread(
            target=self._start_flask, daemon=True, name="FlaskServer"
        )
        flask_thread.start()

        print("[Main] running  (Ctrl-C to stop)")
        last_log = 0.0
        while self.running:
            now = time.time()
            if now - last_log >= 30:
                last_log = now
                try:
                    self._log_status()
                except Exception as e:
                    print(f"[Monitor] error: {e}")
            time.sleep(1)

    def shutdown(self):
        print("[Main] shutting down …")
        self.running     = False
        state['running'] = False
        motors.stop()
        motors.cleanup()
        camera.release()
        print("[Main] ✓ done")
        sys.exit(0)


if __name__ == "__main__":
    RobotMain().start_all()
