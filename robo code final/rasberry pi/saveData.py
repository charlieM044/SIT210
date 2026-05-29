"""
saveData.py  –  LocalDataManager
In-memory ring buffer for fast reads; SQLite for persistence across reboots.
All path/size constants come from config.py.

Rows are always accessed by column NAME (via sqlite3.Row), never by index,
so adding or removing columns in the future cannot silently break anything.
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


def _named_conn(db_path):
    """Return a connection whose rows support both dict-style and attr access."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row   # row['severity'] instead of row[8]
    return conn


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
        self._migrate_database()
        self._warm_buffer()

    # ── Schema ─────────────────────────────────────────────────────────────────
    def _init_database(self):
        with _named_conn(self.db_path) as conn:
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

    def _migrate_database(self):
        """
        Remove legacy columns that no longer exist in the schema.
        SQLite doesn't support DROP COLUMN before 3.35.0, so we use the
        canonical table-rebuild approach for older Pi SQLite versions too.
        """
        with _named_conn(self.db_path) as conn:
            cols = {row['name'] for row in conn.execute(
                "PRAGMA table_info(moisture_readings)"
            ).fetchall()}

        legacy = {'ir_temp'}   # add any future removed columns here
        if not (legacy & cols):
            return  # nothing to do

        print(f"[Storage] migrating DB — dropping legacy columns: {legacy & cols}")
        with _named_conn(self.db_path) as conn:
            conn.executescript('''
                BEGIN;
                CREATE TABLE IF NOT EXISTS moisture_readings_new (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp      DATETIME DEFAULT CURRENT_TIMESTAMP,
                    gps_lat        REAL,
                    gps_lng        REAL,
                    date           TEXT,
                    time           TEXT,
                    moisture       REAL,
                    severity       TEXT,
                    image_filename TEXT
                );
                INSERT INTO moisture_readings_new
                    (id, timestamp, gps_lat, gps_lng, date, time,
                     moisture, severity, image_filename)
                SELECT  id, timestamp, gps_lat, gps_lng, date, time,
                        moisture, severity, image_filename
                FROM    moisture_readings;
                DROP TABLE moisture_readings;
                ALTER TABLE moisture_readings_new RENAME TO moisture_readings;
                COMMIT;
            ''')
        print("[Storage] migration complete")

    # ── Buffer warm-up ─────────────────────────────────────────────────────────
    def _warm_buffer(self):
        try:
            with _named_conn(self.db_path) as conn:
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
                             image_path=None, severity='Minor', reading_time=None):
        if not self._validate(gps_lat, gps_lng, moisture):
            return False
        try:
            image_filename = None
            if image_path and os.path.exists(image_path):
                image_filename = self._save_image(image_path, gps_lat, gps_lng)

            now = reading_time or datetime.now()
            record = {
                'id':             None,
                'timestamp':      now.isoformat(sep=' ', timespec='seconds'),
                'gps_lat':        gps_lat,
                'gps_lng':        gps_lng,
                'date':           now.strftime('%Y-%m-%d'),
                'time':           now.strftime('%H:%M:%S'),
                'moisture':       moisture,
                'severity':       severity,
                'image_filename': image_filename,
            }
            threading.Thread(
                target=self._write_db,
                args=(gps_lat, gps_lng, moisture, image_filename, severity, now),
                daemon=True
            ).start()
            with self._lock:
                self._buffer.append(record)
            print(f"[Storage] saved @ {moisture:.1f}% {severity}")
            return True
        except Exception as e:
            print(f"[Storage] error: {e}")
            return False

    def _write_db(self, gps_lat, gps_lng, moisture,
                  image_filename, severity, reading_time=None):
        try:
            now = reading_time or datetime.now()
            with _named_conn(self.db_path) as conn:
                conn.execute(
                    '''INSERT INTO moisture_readings
                       (gps_lat, gps_lng, date, time, moisture, severity, image_filename)
                       VALUES (:gps_lat, :gps_lng, :date, :time,
                               :moisture, :severity, :image_filename)''',
                    {
                        'gps_lat':        gps_lat,
                        'gps_lng':        gps_lng,
                        'date':           now.strftime('%Y-%m-%d'),
                        'time':           now.strftime('%H:%M:%S'),
                        'moisture':       moisture,
                        'severity':       severity,
                        'image_filename': image_filename,
                    }
                )
                conn.commit()
        except Exception as e:
            print(f"[Storage] DB write error: {e}")

    # ── Read ───────────────────────────────────────────────────────────────────
    def get_all_readings(self):
        with self._lock:
            return list(self._buffer)

    def get_all_readings_history(self):
        with _named_conn(self.db_path) as conn:
            rows = conn.execute(
                'SELECT * FROM moisture_readings ORDER BY id ASC'
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_moisture_stats(self):
        with self._lock:
            readings = list(self._buffer)
        return self._stats_from_readings(readings)

    def get_moisture_stats_history(self):
        with _named_conn(self.db_path) as conn:
            rows = conn.execute(
                'SELECT * FROM moisture_readings ORDER BY id ASC'
            ).fetchall()
        readings = [self._row_to_dict(row) for row in rows]
        return self._stats_from_readings(readings)

    @staticmethod
    def _stats_from_readings(readings):
        values = [r['moisture'] for r in readings if r['moisture'] is not None]
        if not values:
            return None
        return {
            'average':        sum(values) / len(values),
            'max':            max(values),
            'min':            min(values),
            'count':          len(values),
            'critical_count': sum(1 for r in readings if r.get('severity') == 'Critical'),
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
        readings = self.get_all_readings_history()
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
        """
        Convert a sqlite3.Row to a plain dict using column names — never indices.
        Adding or removing DB columns cannot break this.
        """
        return dict(row)

    def _save_image(self, source, gps_lat, gps_lng):
        try:
            source_path = Path(source)
            if source_path.parent.resolve() == self.images_path.resolve():
                return source_path.name
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            if gps_lat is not None and gps_lng is not None:
                fname = (f"moisture_{ts}"
                         f"_lat{abs(gps_lat):.4f}_lng{abs(gps_lng):.4f}.jpg"
                         .replace('.', '_', 2))
            else:
                fname = f"moisture_{ts}_nofixgps.jpg"
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

    @staticmethod
    def get_image():
        images = list(Path(IMAGE_DIR).glob('*.jpg'))
        if not images:
            return None
        latest_image = max(images, key=lambda p: p.stat().st_mtime)
        return latest_image.read_bytes()


# Module-level singleton
storage = LocalDataManager()
