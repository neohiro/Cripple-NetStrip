"""
Database Module for NetStrip
Thread-safe SQLite database for logging connections, user rules, statistics, and settings.
"""

import sqlite3
import queue
import time
import threading
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to ~/.NetStrip/NetStrip.db
            home = os.path.expanduser("~")
            db_dir = os.path.join(home, ".NetStrip")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "NetStrip.db")
            
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_db()
        
        # Async Writer Queue for optimizations
        self.write_queue = queue.Queue()
        self._stop_writer = False
        self._writer_thread = threading.Thread(target=self._async_writer_loop, daemon=True)
        self._writer_thread.start()

    def _get_connection(self):
        """Get a thread-safe connection"""
        if not hasattr(self, '_local'):
            self._local = threading.local()
        if not hasattr(self._local, 'conn'):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            conn.execute('PRAGMA journal_mode=WAL')
            self._local.conn = conn
        return self._local.conn

    def _init_db(self):
        with self.lock:
            with self._get_connection() as conn:
                conn.executescript('''
                    CREATE TABLE IF NOT EXISTS connection_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        process_name TEXT,
                        process_path TEXT,
                        pid INTEGER,
                        domain TEXT,
                        ip TEXT,
                        port INTEGER,
                        protocol TEXT,
                        category TEXT,
                        action TEXT,
                        mode TEXT,
                        resolved_name TEXT,
                        original_exe TEXT
                    );
                    CREATE INDEX IF NOT EXISTS idx_log_timestamp ON connection_log(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_log_domain ON connection_log(domain);
                    
                    CREATE TABLE IF NOT EXISTS user_rules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pattern TEXT,
                        action TEXT,
                        scope TEXT,
                        app_name TEXT,
                        category TEXT,
                        mode_scope TEXT DEFAULT 'STANDARD',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        expires_at DATETIME,
                        note TEXT
                    );
                    
                    CREATE TABLE IF NOT EXISTS statistics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE UNIQUE,
                        total_queries INTEGER DEFAULT 0,
                        total_blocked INTEGER DEFAULT 0,
                        total_allowed INTEGER DEFAULT 0,
                        blocked_ads INTEGER DEFAULT 0,
                        blocked_trackers INTEGER DEFAULT 0,
                        blocked_telemetry INTEGER DEFAULT 0,
                        blocked_malware INTEGER DEFAULT 0
                    );
                    
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    );
                    
                    CREATE TABLE IF NOT EXISTS dns_cache (
                        ip TEXT PRIMARY KEY,
                        domain TEXT,
                        last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS bandwidth_stats (
                        hour DATETIME PRIMARY KEY,
                        bytes_sent INTEGER DEFAULT 0,
                        bytes_recv INTEGER DEFAULT 0
                    );
                ''')
                # Initialize today's stats if not exists
                today = datetime.now().strftime('%Y-%m-%d')
                conn.execute('INSERT OR IGNORE INTO statistics (date) VALUES (?)', (today,))
                
                # Attempt to add expires_at if upgrading from old DB
                try:
                    conn.execute("ALTER TABLE user_rules ADD COLUMN expires_at DATETIME;")
                except sqlite3.OperationalError:
                    pass # Column already exists
                    
                # Attempt to add mode_scope if upgrading from old DB
                try:
                    conn.execute("ALTER TABLE user_rules ADD COLUMN mode_scope TEXT DEFAULT 'STANDARD';")
                except sqlite3.OperationalError:
                    pass # Column already exists
                    
                # Attempt to add original_exe if upgrading from old DB
                try:
                    conn.execute("ALTER TABLE connection_log ADD COLUMN original_exe TEXT;")
                except sqlite3.OperationalError:
                    pass # Column already exists


    def stop(self):
        self._stop_writer = True
        if hasattr(self, '_writer_thread') and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=1.0)

    def _async_writer_loop(self):
        consecutive_errors = 0
        while not self._stop_writer:
            batch = []
            try:
                # Block until an item is available, but timeout to check _stop_writer
                item = self.write_queue.get(timeout=0.5)
                batch.append(item)
                
                # Try to pull up to 100 more items rapidly
                try:
                    for _ in range(100):
                        batch.append(self.write_queue.get_nowait())
                except queue.Empty:
                    pass
            except queue.Empty:
                pass
                
            if batch:
                logs = [b['data'] for b in batch if b['type'] == 'log']
                stats = [b['data'] for b in batch if b['type'] == 'stat']
                
                with self.lock:
                    try:
                        with self._get_connection() as conn:
                            if logs:
                                conn.executemany('''
                                    INSERT INTO connection_log 
                                    (process_name, process_path, pid, domain, ip, port, protocol, category, action, mode, resolved_name, original_exe)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', logs)
                                
                            for action_val, category_val in stats:
                                today = datetime.now().strftime('%Y-%m-%d')
                                # Ensure row exists
                                conn.execute('INSERT OR IGNORE INTO statistics (date) VALUES (?)', (today,))
                                
                                query = "UPDATE statistics SET total_queries = total_queries + 1"
                                if action_val == "block":
                                    query += ", total_blocked = total_blocked + 1"
                                    if category_val == "ads":
                                        query += ", blocked_ads = blocked_ads + 1"
                                    elif category_val == "trackers":
                                        query += ", blocked_trackers = blocked_trackers + 1"
                                    elif category_val == "telemetry":
                                        query += ", blocked_telemetry = blocked_telemetry + 1"
                                    elif category_val == "malware":
                                        query += ", blocked_malware = blocked_malware + 1"
                                else:
                                    query += ", total_allowed = total_allowed + 1"
                                    
                                query += " WHERE date = ?"
                                conn.execute(query, (today,))
                                
                            conn.commit()
                            consecutive_errors = 0
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"Error in async writer thread: {e}")
                        consecutive_errors += 1
                        if consecutive_errors > 5:
                            logging.getLogger(__name__).critical("DB Async writer circuit breaker triggered. Delaying writes.")
                            time.sleep(5)
                        else:
                            time.sleep(consecutive_errors)
                        # Re-queue batch to not lose data
                        for item in batch:
                            self.write_queue.put(item)

    def log_connection(self, data: Dict[str, Any]):
        
        """Log a connection event via async queue"""
        if hasattr(self, 'write_queue'):
            row = (
                data.get('process_name'), data.get('process_path'), data.get('pid'),
                data.get('domain'), data.get('ip'), data.get('port'), data.get('protocol'),
                data.get('category'), data.get('action'), data.get('mode'), data.get('resolved_name'), data.get('original_exe')
            )
            self.write_queue.put({'type': 'log', 'data': row})

    def prune_old_logs(self, hours: int = 24):
        """Keep only the latest logs within the last N hours to prevent SQLite bloat."""
        with self.lock:
            with self._get_connection() as conn:
                conn.execute(
                    f"DELETE FROM connection_log WHERE timestamp < datetime('now', '-{hours} hours')"
                )
                conn.execute(
                    f"DELETE FROM dns_cache WHERE last_seen < datetime('now', '-{hours} hours')"
                )

    def cache_domain_mapping(self, ip: str, domain: str):
        """Save a resolved DNS mapping to the cache."""
        with self.lock:
            with self._get_connection() as conn:
                try:
                    conn.execute('''
                        INSERT OR REPLACE INTO dns_cache (ip, domain, last_seen)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    ''', (ip, domain))
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Error caching domain mapping: {e}")

    def get_recent_connections(self, limit: int = 100) -> List[sqlite3.Row]:
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.execute('SELECT * FROM connection_log ORDER BY id DESC LIMIT ?', (limit,))
                return cursor.fetchall()

    def get_unique_allowed_today(self) -> int:
        """Returns the number of unique allowed connections (process + destination) for today."""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM (
                        SELECT DISTINCT process_name, coalesce(domain, ip) 
                        FROM connection_log 
                        WHERE action='allow' 
                        AND date(timestamp, 'localtime') = date('now', 'localtime')
                    )
                ''')
                row = cursor.fetchone()
                return row[0] if row else 0

    def get_setting(self, key: str, default: Any = None) -> Any:
        if not hasattr(self, '_settings_cache'):
            self._settings_cache = {}
            
        with self.lock:
            cached = self._settings_cache.get(key)
            if cached and (time.time() - cached[1]) < 2.0:
                return cached[0]
                
            with self._get_connection() as conn:
                cursor = conn.execute('SELECT value FROM settings WHERE key = ?', (key,))
                row = cursor.fetchone()
                if row:
                    try:
                        val = json.loads(row['value'])
                    except json.JSONDecodeError:
                        val = row['value']
                    self._settings_cache[key] = (val, time.time())
                    return val
                
                self._settings_cache[key] = (default, time.time())
                return default

    def set_setting(self, key: str, value: Any):
        if not hasattr(self, '_settings_cache'):
            self._settings_cache = {}
            
        if isinstance(value, (dict, list, bool)):
            str_value = json.dumps(value)
        else:
            str_value = str(value)
            
        with self.lock:
            self._settings_cache[key] = (value, time.time())
            with self._get_connection() as conn:
                conn.execute(
                    'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                    (key, str_value)
                )

    def delete_setting(self, key: str):
        if not hasattr(self, '_settings_cache'):
            self._settings_cache = {}
            
        with self.lock:
            if key in self._settings_cache:
                del self._settings_cache[key]
            with self._get_connection() as conn:
                conn.execute('DELETE FROM settings WHERE key = ?', (key,))

    def update_daily_stats(self, action: str, category: str):
        with self.lock:
            today = datetime.now().strftime('%Y-%m-%d')
            with self._get_connection() as conn:
                conn.execute('INSERT OR IGNORE INTO statistics (date) VALUES (?)', (today,))
                
                updates = ['total_queries = total_queries + 1']
                if action == 'block' or action == 'sinkhole':
                    updates.append('total_blocked = total_blocked + 1')
                    if category == 'ad':
                        updates.append('blocked_ads = blocked_ads + 1')
                    elif category == 'tracker':
                        updates.append('blocked_trackers = blocked_trackers + 1')
                    elif category == 'telemetry':
                        updates.append('blocked_telemetry = blocked_telemetry + 1')
                    elif category == 'malware':
                        updates.append('blocked_malware = blocked_malware + 1')
                else:
                    updates.append('total_allowed = total_allowed + 1')
                    
                query = f"UPDATE statistics SET {', '.join(updates)} WHERE date = ?"
                conn.execute(query, (today,))

    def add_user_rule(self, rule_data: Dict[str, Any]):
        """Add a custom user rule (allow/block)"""
        with self.lock:
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT INTO user_rules 
                    (pattern, action, scope, app_name, category, note, expires_at, mode_scope)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    rule_data.get('pattern'), rule_data.get('action'),
                    rule_data.get('scope', 'global'), rule_data.get('app_name'),
                    rule_data.get('category'), rule_data.get('note'), 
                    rule_data.get('expires_at'), rule_data.get('mode_scope', 'STANDARD')
                ))

    def get_user_rules(self, mode_scope: Optional[str] = None) -> List[sqlite3.Row]:
        """Get user rules filtered by mode_scope (or ALL/STANDARD defaults)"""
        with self.lock:
            with self._get_connection() as conn:
                if mode_scope:
                    cursor = conn.execute(
                        "SELECT * FROM user_rules WHERE mode_scope = 'ALL' OR mode_scope = ? ORDER BY id DESC", 
                        (mode_scope,)
                    )
                else:
                    cursor = conn.execute('SELECT * FROM user_rules ORDER BY id DESC')
                return cursor.fetchall()

    def delete_user_rule(self, rule_id: int):
        """Delete a user rule by ID"""
        with self.lock:
            with self._get_connection() as conn:
                conn.execute('DELETE FROM user_rules WHERE id = ?', (rule_id,))

    def cleanup_expired_rules(self) -> int:
        """Delete time bomb rules that have expired and return count."""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM user_rules WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP")
                conn.commit()
                return cursor.rowcount

    def get_statistics(self) -> List[sqlite3.Row]:
        """Get historical statistics"""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.execute('SELECT * FROM statistics ORDER BY date DESC LIMIT 30')
                return cursor.fetchall()

    def get_24h_statistics(self) -> dict:
        """Get accurate rolling statistics for the last 24 hours from the connection log."""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_queries,
                        SUM(CASE WHEN action IN ('block', 'sinkhole') THEN 1 ELSE 0 END) as total_blocked,
                        SUM(CASE WHEN action = 'allow' THEN 1 ELSE 0 END) as total_allowed,
                        SUM(CASE WHEN category = 'ad' AND action IN ('block', 'sinkhole') THEN 1 ELSE 0 END) as blocked_ads,
                        SUM(CASE WHEN category = 'tracker' AND action IN ('block', 'sinkhole') THEN 1 ELSE 0 END) as blocked_trackers,
                        SUM(CASE WHEN category = 'telemetry' AND action IN ('block', 'sinkhole') THEN 1 ELSE 0 END) as blocked_telemetry,
                        SUM(CASE WHEN category = 'malware' AND action IN ('block', 'sinkhole') THEN 1 ELSE 0 END) as blocked_malware
                    FROM connection_log 
                    WHERE timestamp >= datetime('now', '-24 hours')
                ''')
                row = cursor.fetchone()
                
                return {
                    'total_queries': row['total_queries'] or 0,
                    'total_blocked': row['total_blocked'] or 0,
                    'total_allowed': row['total_allowed'] or 0,
                    'blocked_ads': row['blocked_ads'] or 0,
                    'blocked_trackers': row['blocked_trackers'] or 0,
                    'blocked_telemetry': row['blocked_telemetry'] or 0,
                    'blocked_malware': row['blocked_malware'] or 0,
                }

    def log_bandwidth(self, bytes_sent: int, bytes_recv: int):
        """Log bandwidth deltas into an hourly bucket."""
        if bytes_sent == 0 and bytes_recv == 0:
            return
            
        with self.lock:
            current_hour = datetime.now().strftime('%Y-%m-%d %H:00:00')
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT INTO bandwidth_stats (hour, bytes_sent, bytes_recv)
                    VALUES (?, ?, ?)
                    ON CONFLICT(hour) DO UPDATE SET 
                        bytes_sent = bytes_sent + ?,
                        bytes_recv = bytes_recv + ?
                ''', (current_hour, bytes_sent, bytes_recv, bytes_sent, bytes_recv))

    def get_24h_bandwidth(self) -> tuple:
        """Get the sum of bytes sent and received over the last 24 hours. Returns (sent, recv)."""
        with self.lock:
            with self._get_connection() as conn:
                cutoff_time = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:00:00')
                cursor = conn.execute('''
                    SELECT SUM(bytes_sent) as total_sent, SUM(bytes_recv) as total_recv
                    FROM bandwidth_stats
                    WHERE hour >= ?
                ''', (cutoff_time,))
                row = cursor.fetchone()
                if row and row['total_sent'] is not None:
                    return (row['total_sent'], row['total_recv'])
                return (0, 0)

    def export_profile(self, filepath: str):
        """Export all settings and user rules to a JSON file"""
        with self.lock:
            with self._get_connection() as conn:
                # Get settings
                settings_rows = conn.execute('SELECT key, value FROM settings').fetchall()
                settings = {row['key']: row['value'] for row in settings_rows}
                
                # Get user rules
                rules_rows = conn.execute('SELECT pattern, action, scope, app_name, category, note FROM user_rules').fetchall()
                rules = [dict(row) for row in rules_rows]
                
                data = {
                    "version": "1.0",
                    "exported_at": datetime.now().isoformat(),
                    "settings": settings,
                    "user_rules": rules
                }
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)

    def import_profile(self, filepath: str):
        """Import settings and user rules from a JSON file, overwriting current config"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        settings = data.get("settings", {})
        rules = data.get("user_rules", [])
        
        with self.lock:
            with self._get_connection() as conn:
                # Import settings
                for key, value in settings.items():
                    conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
                    
                # Clear existing rules and import new ones
                conn.execute('DELETE FROM user_rules')
                for rule in rules:
                    conn.execute('''
                        INSERT INTO user_rules 
                        (pattern, action, scope, app_name, category, note)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        rule.get('pattern'), rule.get('action'),
                        rule.get('scope', 'global'), rule.get('app_name'),
                        rule.get('category'), rule.get('note')
                    ))



    def get_cached_domain(self, ip: str) -> Optional[str]:
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.execute('SELECT domain FROM dns_cache WHERE ip = ?', (ip,))
                row = cursor.fetchone()
                return row['domain'] if row else None
