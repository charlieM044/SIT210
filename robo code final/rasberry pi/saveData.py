"""
saveData.py  –  LocalDataManager
In-memory ring buffer for fast reads; SQLite for persistence across reboots.
All path/size constants come from config.py.
"""

import os
import json
import shutil
import sqlite3
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from config import DATA_DIR, IMAGE_DIR, DB_PATH, RING_BUFFER_SIZE


class LocalDataManager:
    def __init__(self):
        self.base_path   = Path(DATA_DIR)
        self.images_path = Path(IMAGE_DIR)
        self.db_path     = Path(DB_PATH)

        self.images_path.mkdir(parents=True, exist_ok=True)
        (self.base_path / 'data').mkdir(parents=True, exist_ok=True)

        self._lock   = threading.Lock()
        self._buffer = deque(maxlen=RING_BUFFER_SIZE)

        self._init_database()
        self._warm_buffer()

    def _init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS moisture_readings (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp      DATETIME DEFAULT CURRENT_TIMESTAMP,
                    gps_lat        REAL,
                    gps_lng        REAL,
                    date           TEXT,
                    time           TEXT,
                    moisture       REAL,
                   
                    severity       TEXT,
                    image_filename TEXT
                )
            ''')
            conn.commit()

    def _warm_buffer(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    f'SELECT * FROM moisture_readings '
                    f'ORDER BY id DESC LIMIT {RING_BUFFER_SIZE}'
                ).fetchall()
            for row in reversed(rows):
                self._buffer.append(self._row_to_dict(row))
        except Exception as e:
            print(f"[Storage] warm-up error: {e}")

    # ── Write ──────────────────────────────────────────────────────────────────
    def add_moisture_reading(self, gps_lat, gps_lng, moisture,
                             image_path=None, severity='Minor'):
        if not self._validate(gps_lat, gps_lng, moisture):
            return False
        try:
            image_filename = None
            if image_path and os.path.exists(image_path):
                image_filename = self._save_image(image_path, gps_lat, gps_lng)

            now = datetime.now()
            row = {
                'id':        None,
                'timestamp': now.isoformat(sep=' ', timespec='seconds'),
                'gps_lat':   gps_lat,
                'gps_lng':   gps_lng,
                'date':      now.strftime('%Y-%m-%d'),
                'time':      now.strftime('%H:%M:%S'),
                'moisture':  moisture,
                'severity':  severity,
                'image_filename': image_filename,
            }
            threading.Thread(
                target=self._write_db,
                args=(gps_lat, gps_lng, moisture, image_filename, severity),
                daemon=True
            ).start()
            with self._lock:
                self._buffer.append(row)
            print(f"[Storage] saved @ {moisture:.1f}% {severity}")
            return True
        except Exception as e:
            print(f"[Storage] error: {e}")
            return False

    def _write_db(self, gps_lat, gps_lng, moisture,
                  image_filename, severity):
        try:
            now = datetime.now()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    '''INSERT INTO moisture_readings
                       (gps_lat, gps_lng, date, time, moisture, severity, image_filename)
                       VALUES (?,?,?,?,?,?,?)''',
                    (gps_lat, gps_lng,
                     now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'),
                     moisture, severity, image_filename)
                )
                conn.commit()
        except Exception as e:
            print(f"[Storage] DB write error: {e}")

    # ── Read ───────────────────────────────────────────────────────────────────
    def get_all_readings(self):
        with self._lock:
            return list(self._buffer)

    def get_moisture_stats(self):
        with self._lock:
            values = [r['moisture'] for r in self._buffer
                      if r['moisture'] is not None]
        if not values:
            return None
        return {
            'average':        sum(values) / len(values),
            'max':            max(values),
            'min':            min(values),
            'count':          len(values),
            'critical_count': sum(1 for v in values if v > 80),
        }

    def get_storage_info(self):
        total, count = 0, 0
        for p in self.base_path.rglob('*'):
            if p.is_file():
                total += p.stat().st_size
                count += 1
        return {
            'total_files':   count,
            'total_size_mb': round(total / (1024 * 1024), 2),
            'images':        len(list(self.images_path.glob('*.jpg'))),
            'data_path':     str(self.base_path),
            'buffer_size':   len(self._buffer),
        }

    def export_report(self, filename='inspection_report.json'):
        readings = self.get_all_readings()
        stats    = self.get_moisture_stats()
        report   = {
            'inspection_date':    datetime.now().isoformat(),
            'total_readings':     len(readings),
            'statistics':         stats,
            'readings':           readings,
            'critical_locations': [r for r in readings if r.get('severity') == 'Critical'],
        }
        path = self.base_path / filename
        with open(path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"[Storage] report → {path}")
        return path

    # ── Helpers ────────────────────────────────────────────────────────────────
    @staticmethod
    def _row_to_dict(row):
        return {
            'id': row[0], 'timestamp': row[1],
            'gps_lat': row[2], 'gps_lng': row[3],
            'date': row[4], 'time': row[5],
            'moisture': row[6],
            'severity': row[7], 'image_filename': row[8],
        }

    def _save_image(self, source, gps_lat, gps_lng):
        try:
            ts    = datetime.now().strftime('%Y%m%d_%H%M%S')
            fname = (f"moisture_{ts}"
                     f"_lat{abs(gps_lat):.4f}_lng{abs(gps_lng):.4f}.jpg"
                     .replace('.', '_', 2))
            shutil.copy(source, self.images_path / fname)
            return fname
        except Exception as e:
            print(f"[Storage] image copy error: {e}")
            return None

    @staticmethod
    def _validate(gps_lat, gps_lng, moisture):
        if gps_lat  is not None and not (-90  <= gps_lat  <= 90):
            print(f"[Storage] invalid lat: {gps_lat}");  return False
        if gps_lng  is not None and not (-180 <= gps_lng  <= 180):
            print(f"[Storage] invalid lng: {gps_lng}");  return False
        if moisture is not None and not (0    <= moisture <= 100):
            print(f"[Storage] invalid moisture: {moisture}"); return False
        return True


# Module-level singleton
storage = LocalDataManager()
