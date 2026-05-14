import os
import json
import shutil
from datetime import datetime
from pathlib import Path
import sqlite3

class LocalDataManager:
    def __init__(self, base_path='./robot_data'):
        """Initialize local storage structure"""
        self.base_path = Path(base_path)
        self.images_path = self.base_path / 'images'
        self.data_path = self.base_path / 'data'
        self.db_path = self.base_path / 'robot_data.db'
        
        # Create directory structure
        self.images_path.mkdir(parents=True, exist_ok=True)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for sensor readings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moisture_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                gps_lat REAL,
                gps_lng REAL,
                date TEXT,
                time TEXT,
                moisture REAL,
                ir_temp REAL,
                severity TEXT,
                image_filename TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        
    def add_moisture_reading(self, gps_lat, gps_lng, moisture, ir_temp=None, 
                            image_path=None, severity='Minor'):
        # 1. Validate quickly
        if not self.validate_data(gps_lat, gps_lng, moisture):
            return False
        
        try:
            image_filename = None
            # 2. Only copy image if it actually exists and is needed
            if image_path and os.path.exists(image_path):
                image_filename = self.save_image(image_path, gps_lat, gps_lng)
            
            # 3. Save to database (This is your primary record)
            self.save_to_database(gps_lat, gps_lng, moisture, ir_temp, 
                                 image_filename, severity)
            
            # 4. Remove the print(reading_data) if it's huge, 
            # as printing to console also takes memory/time
            print(f"[Storage] Reading saved @ {moisture}%")
            return True
            
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def save_image(self, source_image_path, gps_lat, gps_lng):
        """Save image with metadata filename"""
        try:
            # Create filename with location and timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            lat_str = f"{abs(gps_lat):.4f}".replace('.', '_')
            lng_str = f"{abs(gps_lng):.4f}".replace('.', '_')
            
            filename = f"moisture_{timestamp}_lat{lat_str}_lng{lng_str}.jpg"
            dest_path = self.images_path / filename
            
            # Copy image
            shutil.copy(source_image_path, dest_path)
            
            print(f"Image saved: {filename}")
            return filename
        
        except Exception as e:
            print(f"Error saving image: {e}")
            return None
    
    def save_to_database(self, gps_lat, gps_lng, moisture, ir_temp, 
                        image_filename, severity):
        """Save reading to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO moisture_readings 
            (gps_lat, gps_lng, date, time, moisture, ir_temp, severity, image_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            gps_lat,
            gps_lng,
            datetime.now().strftime('%Y-%m-%d'),
            datetime.now().strftime('%H:%M:%S'),
            moisture,
            ir_temp,
            severity,
            image_filename
        ))
        conn.commit()
        conn.close()
    
    def save_json_record(self, data):
        """Save reading as individual JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.data_path / f"reading_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def validate_data(self, gps_lat, gps_lng, moisture):
        """Validate sensor data"""
        
        if gps_lat is not None:
            if not (-90 <= gps_lat <= 90):
                print(f"Invalid latitude: {gps_lat}")
                return False
        
        if gps_lng is not None:
            if not (-180 <= gps_lng <= 180):
                print(f"Invalid longitude: {gps_lng}")
                return False
        
        if moisture is not None:
            if not (0 <= moisture <= 100):
                print(f"Invalid moisture: {moisture}")
                return False
        
        return True
    
    def get_all_readings(self):
        """Get all moisture readings from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM moisture_readings ORDER BY timestamp DESC')
        rows = cursor.fetchall()
        conn.close()
        
        readings = []
        for row in rows:
            readings.append({
                'id': row[0],
                'timestamp': row[1],
                'gps_lat': row[2],
                'gps_lng': row[3],
                'date': row[4],
                'time': row[5],
                'moisture': row[6],
                'ir_temp': row[7],
                'severity': row[8],
                'image': row[9]
            })
        
        return readings
    
    def get_readings_by_date(self, date_str):
        """Get readings for specific date (YYYY-MM-DD)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM moisture_readings WHERE date = ? ORDER BY time DESC',
            (date_str,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return len(rows)
    
    def get_critical_readings(self):
        """Get all critical moisture readings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM moisture_readings WHERE severity = ? ORDER BY timestamp DESC',
            ('Critical',)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return rows
    
    def get_moisture_stats(self):
        """Get moisture statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT moisture FROM moisture_readings WHERE moisture IS NOT NULL')
        values = cursor.fetchall()
        conn.close()
        
        if not values:
            return None
        
        moisture_list = [v[0] for v in values]
        
        stats = {
            'average': sum(moisture_list) / len(moisture_list),
            'max': max(moisture_list),
            'min': min(moisture_list),
            'count': len(moisture_list),
            'critical_count': len([v for v in moisture_list if v > 80])
        }
        
        return stats
    
    def export_inspection_report(self, output_filename='inspection_report.json'):
        """Export all data as inspection report"""
        readings = self.get_all_readings()
        stats = self.get_moisture_stats()
        
        report = {
            'inspection_date': datetime.now().isoformat(),
            'total_readings': len(readings),
            'statistics': stats,
            'readings': readings,
            'critical_locations': [r for r in readings if r['severity'] == 'Critical']
        }
        
        output_path = self.base_path / output_filename
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Report exported: {output_path}")
        return output_path
    
    def get_storage_info(self):
        """Get storage usage information"""
        total_size = 0
        file_count = 0
        
        for filepath in self.base_path.rglob('*'):
            if filepath.is_file():
                total_size += filepath.stat().st_size
                file_count += 1
        
        info = {
            'total_files': file_count,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'images': len(list(self.images_path.glob('*.jpg'))),
            'data_path': str(self.base_path)
        }
        
        return info

# Example usage
if __name__ == "__main__":
    # Initialize local storage
    storage = LocalDataManager('./robot_inspection_data')
    
    # Add a moisture reading
    storage.add_moisture_reading(
        gps_lat=-37.8136,
        gps_lng=144.9631,
        moisture=75.5,
        ir_temp=18.2,
        image_path='./captured_image.jpg',
        severity='Moderate'
    )
    
    # Get all readings
    readings = storage.get_all_readings()
    print(f"Total readings: {len(readings)}")
    
    # Get statistics
    stats = storage.get_moisture_stats()
    print(f"Statistics: {stats}")
    
    # Get storage info
    info = storage.get_storage_info()
    print(f"Storage: {info}")
    
    # Export inspection report
    storage.export_inspection_report()
