"""
hardware/camera.py  –  OV5647 camera manager.
All camera constants come from config.py.
"""

import cv2
import threading
import time
from datetime import datetime
from pathlib import Path
from config import (
    IMAGE_DIR, CAMERA_WIDTH, CAMERA_HEIGHT,
    CAMERA_FPS, JPEG_QUALITY,
)


class CameraManager:
    def __init__(self):
        self.save_path     = Path(IMAGE_DIR)
        self.save_path.mkdir(parents=True, exist_ok=True)

        self.use_picamera2 = False
        self.picamera2     = None
        self.camera        = None
        self._frame        = None
        self._frame_lock   = threading.Lock()
        self.is_streaming  = False
        self.stream_thread = None
        self._released     = False

        self._init_camera()

    def _init_camera(self):
        try:
            import subprocess
            subprocess.run(["sudo", "fuser", "-k", "/dev/video0"],
                           stderr=subprocess.DEVNULL, timeout=3)
        except Exception:
            pass

        try:
            from picamera2 import Picamera2
            cam = Picamera2()
            cfg = cam.create_video_configuration(
                main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT), "format": "BGR888"}
            )
            cam.configure(cfg)
            cam.start()
            self.picamera2     = cam
            self.use_picamera2 = True
            print("[Camera] ✓ picamera2")
            return
        except Exception as e:
            print(f"[Camera] picamera2 failed: {e}")

        try:
            from picamera import PiCamera
            cam = PiCamera()
            cam.resolution = (CAMERA_WIDTH, CAMERA_HEIGHT)
            cam.framerate  = 30
            self.camera    = cam
            print("[Camera] ✓ picamera")
            return
        except Exception as e:
            print(f"[Camera] picamera failed: {e}")

        try:
            cam = cv2.VideoCapture(0)
            cam.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            cam.set(cv2.CAP_PROP_FPS,          30)
            if cam.isOpened():
                self.camera = cam
                print("[Camera] ⚠ OpenCV (PC testing mode)")
            else:
                cam.release()
        except Exception as e:
            print(f"[Camera] OpenCV failed: {e}")

    def _get_frame(self):
        try:
            if self.use_picamera2 and self.picamera2:
                return self.picamera2.capture_array()
            if self.camera is not None:
                if hasattr(self.camera, 'read'):
                    ret, frame = self.camera.read()
                    return frame if ret else None
                else:
                    import io, numpy as np
                    stream = io.BytesIO()
                    self.camera.capture(stream, format='jpeg', use_video_port=True)
                    stream.seek(0)
                    data = np.frombuffer(stream.read(), dtype=np.uint8)
                    return cv2.imdecode(data, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"[Camera] _get_frame error: {e}")
        return None

    def capture_image(self, gps_lat, gps_lng, moisture):
        try:
            frame = self._get_frame()
            if frame is None:
                return None
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cv2.putText(frame, ts,                          (10, 30),  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            cv2.putText(frame, f"Moisture: {moisture:.1f}%",(10, 70),  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            
            # GPS coordinates optional — can be None if no fix yet
            if gps_lat is not None and gps_lng is not None:
                cv2.putText(frame, f"GPS: {gps_lat:.4f}, {gps_lng:.4f}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                fname = (f"moisture_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                         f"_lat{abs(gps_lat):.4f}_lng{abs(gps_lng):.4f}_{moisture:.0f}pct.jpg")
            else:
                cv2.putText(frame, "GPS: NO FIX", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                fname = (f"moisture_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                         f"_nofixgps_{moisture:.0f}pct.jpg")
            
            fpath = self.save_path / fname
            cv2.imwrite(str(fpath), frame)
            del frame
            print(f"[Camera] saved: {fname}")
            return str(fpath)
        except Exception as e:
            print(f"[Camera] capture error: {e}")
            return None

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
        interval = 1.0 / CAMERA_FPS
        while self.is_streaming:
            try:
                frame = self._get_frame()
                if frame is not None:
                    cv2.putText(frame, "LIVE", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
                    cv2.putText(frame, datetime.now().strftime('%H:%M:%S'),
                                (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                    ret, buf = cv2.imencode(
                        '.jpg', frame,
                        [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
                    )
                    del frame
                    if ret:
                        with self._frame_lock:
                            self._frame = buf.tobytes()
                        del buf
            except Exception as e:
                print(f"[Camera] stream error: {e}")
            time.sleep(interval)

    def get_frame(self):
        with self._frame_lock:
            return self._frame

    def release(self):
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
            print("[Camera] ✓ released")
        except Exception as e:
            print(f"[Camera] release error: {e}")
        finally:
            # Wait briefly for stream thread to finish
            if self.stream_thread and self.stream_thread.is_alive():
                self.stream_thread.join(timeout=2)


# Module-level singleton
camera = CameraManager()
