"""
main.py  –  Entry point for the Raspberry Pi robot
Fixes vs original:
  • Only ONE CameraManager is created here; it is injected into pi_server
    via pi_server.set_camera() so the module never creates its own.
  • Removed calls to self.run_autonomous_logic() / self.update_monitoring()
    which didn't exist (instant AttributeError → crash).
  • Flask runs in a daemon thread; the main thread just does a heartbeat
    loop so the process stays alive and can be cleanly interrupted.
  • SIGINT / KeyboardInterrupt triggers a graceful shutdown.
"""

import signal
import sys
import threading
import time
from datetime import datetime

import pi_server                        # import the module (does NOT create a camera)
from pi_server import app as flask_app, set_camera, motors, state
from saveData import LocalDataManager
from camera import CameraManager


class RobotMain:
    def __init__(self):
        print("=" * 50)
        print("🤖 Moisture Detection Robot – starting")
        print("=" * 50)

        # ONE camera instance – shared with pi_server via set_camera()
        self.camera  = CameraManager()
        set_camera(self.camera)          # inject into pi_server

        self.storage = LocalDataManager('./robot_inspection_data')
        self.running = True

        # Graceful shutdown on Ctrl-C or SIGTERM
        signal.signal(signal.SIGINT,  self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, sig, frame):
        print(f"\n[Main] signal {sig} received – shutting down")
        self.shutdown()

    # ── Flask thread ───────────────────────────────────────────────────────────
    def _start_flask(self):
        print("[Flask] starting on port 5000 …")
        try:
            flask_app.run(
                host='0.0.0.0', port=5000,
                debug=False, use_reloader=False, threaded=True
            )
        except Exception as e:
            print(f"[Flask] error: {e}")

    # ── Monitoring helper (called from main loop) ──────────────────────────────
    def _log_status(self):
        info  = self.storage.get_storage_info()
        stats = self.storage.get_moisture_stats()
        print(f"\n[Monitor] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Buffer : {info['buffer_size']} readings in RAM")
        print(f"  Storage: {info['total_size_mb']} MB  |  images: {info['images']}")
        if stats:
            print(f"  Avg moisture : {stats['average']:.1f}%")
            print(f"  Critical areas: {stats['critical_count']}")

    # ── Main entry ─────────────────────────────────────────────────────────────
    def start_all(self):
        # 1. Start streaming
        self.camera.start_streaming()

        # 2. Start Flask in a background daemon thread
        flask_thread = threading.Thread(
            target=self._start_flask, daemon=True, name="FlaskServer"
        )
        flask_thread.start()

        # 2.5 Ensure motors start moving when in autonomous mode
        try:
            if state.get('mode') == 'autonomous':
                motors.forward()
                print("[Main] motors started (autonomous mode)")
        except Exception as e:
            print(f"[Main] could not start motors: {e}")

        # 3. Main thread: heartbeat + periodic status log
        print("[Main] running  (Ctrl-C to stop)")
        last_log = 0
        while self.running:
            now = time.time()
            if now - last_log >= 30:
                last_log = now
                try:
                    self._log_status()
                except Exception as e:
                    print(f"[Monitor] error: {e}")
            time.sleep(1)

    # ── Shutdown ───────────────────────────────────────────────────────────────
    def shutdown(self):
        print("[Main] shutting down …")
        self.running       = False
        state['running']   = False

        motors.stop()
        motors.cleanup()

        self.camera.release()

        print("[Main] ✓ done")
        sys.exit(0)


def main():
    robot = RobotMain()
    robot.start_all()


if __name__ == "__main__":
    main()
