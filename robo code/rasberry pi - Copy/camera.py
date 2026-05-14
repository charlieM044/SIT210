"""
camera.py  –  CameraManager for OV5647 on Raspberry Pi
Fixes vs original:
  • picamera2 initialisation was referencing self.picamera2 before assignment
  • self.use_picamera2 was never set True in the success path
  • Streaming loop held old JPEG in memory while building the new one;
    now swapped atomically and capped at one frame in memory at a time
  • release() is idempotent (safe to call multiple times)
"""

import cv2
import threading
import time
from datetime import datetime
from pathlib import Path


class CameraManager:
    def __init__(self, save_path='./robot_inspection_data/images'):
        self.save_path = Path(save_path)
        self.save_path.mkdir(parents=True, exist_ok=True)

        self.use_picamera2 = False
        self.picamera2     = None
        self.camera        = None          # OpenCV / picamera fallback
        self._frame        = None          # single JPEG bytes, swapped atomically
        self._frame_lock   = threading.Lock()
        self.is_streaming  = False
        self.stream_thread = None
        self._released     = False

        self._init_camera()

    # ── Initialisation ─────────────────────────────────────────────────────────
    def _init_camera(self):
        """Try picamera2 → picamera → OpenCV, in that order."""
        # 1. Release /dev/video0 if another process left it locked
        try:
            import subprocess
            subprocess.run(
                ["sudo", "fuser", "-k", "/dev/video0"],
                stderr=subprocess.DEVNULL, timeout=3
            )
        except Exception:
            pass

        # 2. Try picamera2 (Bullseye / Bookworm)
        try:
            from picamera2 import Picamera2
            cam = Picamera2()
            cfg = cam.create_video_configuration(
                main={"size": (640, 480), "format": "BGR888"}
            )
            cam.configure(cfg)
            cam.start()
            self.picamera2    = cam
            self.use_picamera2 = True
            print("[Camera] ✓ picamera2 (OV5647)")
            return
        except Exception as e:
            print(f"[Camera] picamera2 failed: {e}")

        # 3. Try legacy picamera
        try:
            from picamera import PiCamera
            cam = PiCamera()
            cam.resolution  = (640, 480)
            cam.framerate   = 30
            self.camera     = cam
            print("[Camera] ✓ picamera (OV5647)")
            return
        except Exception as e:
            print(f"[Camera] picamera failed: {e}")

        # 4. Fallback: OpenCV (useful for PC testing)
        try:
            cam = cv2.VideoCapture(0)
            cam.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cam.set(cv2.CAP_PROP_FPS,          30)
            if cam.isOpened():
                self.camera = cam
                print("[Camera] ⚠ OpenCV (PC testing mode)")
            else:
                cam.release()
                print("[Camera] ⚠ No camera found – running headless")
        except Exception as e:
            print(f"[Camera] OpenCV failed: {e}")

    # ── Frame capture ──────────────────────────────────────────────────────────
    def _get_frame(self):
        """Return a fresh BGR numpy array, or None."""
        try:
            if self.use_picamera2 and self.picamera2:
                frame = self.picamera2.capture_array()
                # picamera2 BGR888 → already BGR; RGB output would need conversion
                if frame.ndim == 3 and frame.shape[2] == 3:
                    return frame
                return None

            if self.camera is not None:
                if hasattr(self.camera, 'read'):          # OpenCV
                    ret, frame = self.camera.read()
                    return frame if ret else None
                else:                                      # legacy picamera
                    import io
                    import numpy as np
                    stream = io.BytesIO()
                    self.camera.capture(stream, format='jpeg', use_video_port=True)
                    stream.seek(0)
                    data = np.frombuffer(stream.read(), dtype=np.uint8)
                    return cv2.imdecode(data, cv2.IMREAD_COLOR)

        except Exception as e:
            print(f"[Camera] _get_frame error: {e}")
        return None

    # ── Capture to disk ────────────────────────────────────────────────────────
    def capture_image(self, gps_lat, gps_lng, moisture_level):
        """Capture one image, annotate it, save to disk. Returns path or None."""
        try:
            frame = self._get_frame()
            if frame is None:
                print("[Camera] capture failed – no frame")
                return None

            ts  = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cv2.putText(frame, ts,
                        (10, 30),  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Moisture: {moisture_level:.1f}%",
                        (10, 70),  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"GPS: {gps_lat:.4f}, {gps_lng:.4f}",
                        (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            fname    = (f"moisture_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        f"_lat{abs(gps_lat):.4f}_lng{abs(gps_lng):.4f}"
                        f"_{moisture_level:.0f}pct.jpg")
            fpath    = self.save_path / fname
            cv2.imwrite(str(fpath), frame)
            print(f"[Camera] image saved: {fname}")
            del frame          # explicit free
            return str(fpath)

        except Exception as e:
            print(f"[Camera] capture_image error: {e}")
            return None

    # ── Live stream ────────────────────────────────────────────────────────────
    def start_streaming(self):
        if self.is_streaming:
            return
        self.is_streaming  = True
        self.stream_thread = threading.Thread(
            target=self._stream_loop, daemon=True, name="CameraStream"
        )
        self.stream_thread.start()
        print("[Camera] ✓ streaming started")

    def stop_streaming(self):
        self.is_streaming = False
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=3)
        with self._frame_lock:
            self._frame = None
        print("[Camera] streaming stopped")

    def _stream_loop(self):
        """
        Capture → annotate → JPEG-encode → swap into self._frame.
        Old buffer is dereferenced immediately so GC can reclaim it.
        Target ~10 FPS (0.1 s sleep) – sufficient for telemetry and easy on RAM.
        """
        while self.is_streaming:
            try:
                frame = self._get_frame()
                if frame is not None:
                    cv2.putText(frame, "LIVE",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.putText(frame, datetime.now().strftime('%H:%M:%S'),
                                (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    ret, buf = cv2.imencode(
                        '.jpg', frame,
                        [cv2.IMWRITE_JPEG_QUALITY, 70]   # lower quality = less RAM
                    )
                    del frame      # free numpy array before storing JPEG
                    if ret:
                        new_bytes = buf.tobytes()
                        del buf    # free the imencode buffer
                        with self._frame_lock:
                            self._frame = new_bytes
            except Exception as e:
                print(f"[Camera] stream error: {e}")
            time.sleep(0.1)   # 10 FPS – enough for live view, easy on the Pi

    def get_frame(self):
        """Return the latest JPEG bytes (thread-safe), or None."""
        with self._frame_lock:
            return self._frame

    # ── Camera settings ────────────────────────────────────────────────────────
    def adjust_exposure(self, value):
        try:
            if self.use_picamera2 and self.picamera2:
                self.picamera2.set_controls({'ExposureValue': value})
            elif self.camera and hasattr(self.camera, 'exposure_compensation'):
                self.camera.exposure_compensation = value
            print(f"[Camera] exposure → {value}")
        except Exception as e:
            print(f"[Camera] exposure error: {e}")

    def adjust_brightness(self, value):
        try:
            if self.use_picamera2 and self.picamera2:
                self.picamera2.set_controls({'Brightness': value})
            elif self.camera and hasattr(self.camera, 'brightness'):
                self.camera.brightness = value
            print(f"[Camera] brightness → {value}")
        except Exception as e:
            print(f"[Camera] brightness error: {e}")

    # ── Release ────────────────────────────────────────────────────────────────
    def release(self):
        """Idempotent: safe to call multiple times."""
        if self._released:
            return
        self._released = True

        self.stop_streaming()

        try:
            if self.use_picamera2 and self.picamera2:
                self.picamera2.stop()
                self.picamera2.close()
                self.picamera2 = None
            elif self.camera is not None:
                if hasattr(self.camera, 'release'):
                    self.camera.release()
                elif hasattr(self.camera, 'close'):
                    self.camera.close()
                self.camera = None
            print("[Camera] ✓ hardware released")
        except Exception as e:
            print(f"[Camera] release error: {e}")


# ── Quick smoke-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    cam = CameraManager()
    cam.start_streaming()
    time.sleep(5)
    frame = cam.get_frame()
    print(f"[Test] frame size: {len(frame) if frame else 'None'} bytes")
    cam.stop_streaming()
    cam.release()
