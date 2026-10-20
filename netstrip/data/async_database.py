"""
Async Database Module for NetStrip
High-performance SQLite with aiosqlite, dedicated event loop, and batch writes.
"""

import asyncio
import json
import threading
import time
from datetime import datetime, timezone
from queue import Empty, Queue
from typing import Any

import aiosqlite

from netstrip.core.observability import get_logger, traced

logger = get_logger(__name__)


class AsyncDatabase:
    """
    Thread-safe async SQLite database with:
    - Dedicated event loop in background thread
    - Batched writes for throughput
    - Connection pooling (WAL mode)
    - Automatic retry with backoff
    - Graceful shutdown with flush
    """
    
    def __init__(self, db_path: str | None = None, batch_size: int = 100, flush_interval: float = 0.1):
        if db_path is None:
            import os
            home = os.path.expanduser("~")
            db_dir = os.path.join(home, ".NetStrip")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "NetStrip.db")
        
        self.db_path = db_path
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # Thread-safe queues for async operations
        self._write_queue: Queue = Queue()
        
        # Event loop management
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._loop_ready = threading.Event()
        self._shutdown = False
        
        # Stats
        self._stats = {
            'writes': 0,
            'reads': 0,
            'errors': 0,
            'retries': 0,
        }
        
        # Periodic flush task handle
        self._flush_task: asyncio.Task | None = None
        
        # Start background loop
        self._start_loop()
        
        # Initialize schema
        self._init_db_sync()
        
        logger.info("async_db_initialized", path=db_path, batch_size=batch_size)
    
    def _start_loop(self):
        """Start dedicated event loop in background thread."""
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop_ready.set()
            try:
                self._loop.run_until_complete(self._loop_runner())
            finally:
                self._loop.close()
        
        self._loop_thread = threading.Thread(target=run_loop, daemon=True, name="AsyncDB-Loop")
        self._loop_thread.start()
        self._loop_ready.wait(timeout=5.0)
    
    async def _loop_runner(self):
        """Main loop runner - processes write queue and read futures."""
        self._flush_task = asyncio.create_task(self._periodic_flush())
        
        while not self._shutdown:
            try:
                # Process write queue
                await self._process_write_queue()
                
                # Process read requests
                await self._process_read_queue()
                
                await asyncio.sleep(0.01)  # Small yield
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001
                logger.error("async_db_loop_error", error=str(e))
                self._stats['errors'] += 1
                await asyncio.sleep(0.1)
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self._flush_batch()
    
    async def _process_write_queue(self):
        """Process batched writes from queue."""
        batch = []
        try:
            # Block for first item
            item = await asyncio.get_event_loop().run_in_executor(
                None, self._write_queue.get, True, 0.1
            )
            batch.append(item)
            
            # Drain up to batch_size
            while len(batch) < self.batch_size:
                try:
                    item = self._write_queue.get_nowait()
                    batch.append(item)
                except Empty:
                    break
        except Empty:
            return
        
        if batch:
            await self._execute_batch(batch)
    
    async def _process_read_queue(self):
        """Process pending read futures."""
        # This is handled via direct async calls now
    
    @traced("db.execute_batch")
    async def _execute_batch(self, batch: list[dict]):
        """Execute a batch of writes."""
        logs = [b['data'] for b in batch if b['type'] == 'log']
        stats = [b['data'] for b in batch if b['type'] == 'stat']
        settings = [b['data'] for b in batch if b['type'] == 'setting']
        
        if not logs and not stats and not settings:
            return
        
        retries = 0
        max_retries = 3
        
        while retries <= max_retries:
            try:
                async with aiosqlite.connect(self.db_path, timeout=30.0) as conn:
                    # WAL mode + durability flags configured at DB init (hot path stays light)
                    await conn.execute('PRAGMA busy_timeout=30000;')
                    await conn.execute('PRAGMA cache_size=-32768;')  # 32MB cache
                    
                    if logs:
                        await conn.executemany('''
                            INSERT INTO connection_log 
                            (process_name, process_path, pid, domain, ip, port, protocol, category, action, mode, resolved_name, original_exe)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', logs)
                    
                    for action_val, category_val in stats:
                        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                        await conn.execute('INSERT OR IGNORE INTO statistics (date) VALUES (?)', (today,))
                        
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
                        await conn.execute(query, (today,))
                    
                    for key, value in settings:
                        await conn.execute(
                            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                            (key, value)
                        )
                    
                    await conn.commit()
                    self._stats['writes'] += len(logs) + len(stats) + len(settings)
                    return
                    
            except aiosqlite.OperationalError as e:
                if "database is locked" in str(e) and retries < max_retries:
                    retries += 1
                    self._stats['retries'] += 1
                    await asyncio.sleep(0.1 * retries)  # Exponential backoff
                    continue
                raise
            except Exception as e:
                logger.error("db_batch_write_failed", error=str(e), batch_size=len(batch))
                self._stats['errors'] += 1
                raise
    
    async def _periodic_flush(self):
        """Periodic flush task."""
        while not self._shutdown:
            await asyncio.sleep(self.flush_interval)
            if not self._write_queue.empty():
                await self._flush_batch()
    
    async def _flush_batch(self):
        """Flush all pending writes."""
        batch = []
        while not self._write_queue.empty() and len(batch) < self.batch_size * 2:
            try:
                batch.append(self._write_queue.get_nowait())
            except Empty:
                break
        
        if batch:
            await self._execute_batch(batch)
    
    def _init_db_sync(self):
        """Initialize schema synchronously (called once at startup)."""
        import sqlite3
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute('PRAGMA journal_mode=WAL;')
            conn.execute('PRAGMA busy_timeout=30000;')
            conn.execute('PRAGMA synchronous=NORMAL;')
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
                CREATE INDEX IF NOT EXISTS idx_log_process ON connection_log(process_name);
                
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
                CREATE INDEX IF NOT EXISTS idx_rules_app ON user_rules(app_name);
                CREATE INDEX IF NOT EXISTS idx_rules_expires ON user_rules(expires_at);
                
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
                
                CREATE TABLE IF NOT EXISTS whitelisted_anomalies (
                    name TEXT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            conn.execute('INSERT OR IGNORE INTO statistics (date) VALUES (?)', (today,))
            
            # Migrations
            for col, ddl in [
                ("expires_at", "ALTER TABLE user_rules ADD COLUMN expires_at DATETIME;"),
                ("mode_scope", "ALTER TABLE user_rules ADD COLUMN mode_scope TEXT DEFAULT 'STANDARD';"),
                ("original_exe", "ALTER TABLE connection_log ADD COLUMN original_exe TEXT;"),
            ]:
                try:
                    conn.execute(ddl)
                except sqlite3.OperationalError:
                    pass
    
    # ──────────────────────────────────────────────
    #  Public Async API
    # ──────────────────────────────────────────────
    
    async def log_connection(self, data: dict[str, Any]):
        """Queue a connection log for async write."""
        row = (
            data.get('process_name'), data.get('process_path'), data.get('pid'),
            data.get('domain'), data.get('ip'), data.get('port'), data.get('protocol'),
            data.get('category'), data.get('action'), data.get('mode'), 
            data.get('resolved_name'), data.get('original_exe')
        )
        self._write_queue.put({'type': 'log', 'data': row})
    
    async def update_daily_stats(self, action: str, category: str):
        """Queue a stats update."""
        if action not in ("block", "allow"):
            logger.warning("invalid_stat_action", action=action)
            return
        if category not in ("ads", "trackers", "telemetry", "malware", None):
            logger.warning("invalid_stat_category", category=category)
            return
        self._write_queue.put({'type': 'stat', 'data': (action, category)})
    
    @traced("db.get_recent_connections")
    async def get_recent_connections(
        self, limit: int = 100, unique_only: bool = False, since_timestamp: str | None = None
    ) -> list[aiosqlite.Row]:
        """Get recent connections asynchronously."""
        self._stats['reads'] += 1
        async with aiosqlite.connect(self.db_path, timeout=30.0) as conn:
            conn.row_factory = aiosqlite.Row
            where_clause = ""
            params = []
            if since_timestamp:
                where_clause = "WHERE timestamp >= ?"
                params.append(since_timestamp)
            
            if unique_only:
                query = f'''
                    SELECT *, max(id) as max_id 
                    FROM (
                        SELECT * FROM connection_log {where_clause} ORDER BY id DESC LIMIT 5000
                    )
                    GROUP BY process_name, coalesce(domain, ip) 
                    ORDER BY max_id DESC LIMIT ?
                '''
                params.append(limit)
            else:
                query = f'SELECT * FROM connection_log {where_clause} ORDER BY id DESC LIMIT ?'
                params.append(limit)
            
            cursor = await conn.execute(query, params)
            return await cursor.fetchall()
    
    @traced("db.get_setting")
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Get setting asynchronously."""
        self._stats['reads'] += 1
        async with aiosqlite.connect(self.db_path, timeout=30.0) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = await cursor.fetchone()
            if row:
                try:
                    return json.loads(row['value'])
                except json.JSONDecodeError:
                    return row['value']
            return default
    
    @traced("db.set_setting")
    async def set_setting(self, key: str, value: Any):
        """Set setting asynchronously."""
        if isinstance(value, (dict, list, bool)):
            str_value = json.dumps(value)
        else:
            str_value = str(value)
        
        self._write_queue.put({'type': 'setting', 'data': (key, str_value)})
    
    async def flush(self, timeout: float = 5.0):
        """Flush all pending writes within the timeout budget."""
        start = time.monotonic()
        while not self._write_queue.empty() and (time.monotonic() - start) < timeout:
            await self._flush_batch()
        if not self._write_queue.empty():
            await self._flush_batch() # best-effort final drain
    
    def stop(self):
        """Stop the database and flush pending writes."""
        self._shutdown = True
        
        # Flush pending writes before stopping
        if self._loop and not self._loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(self.flush(), self._loop)
            try:
                future.result(timeout=10.0)
            except Exception:  # noqa: BLE001
                # best-effort flush; ignoring failures here
                logger.debug("async_db_stop_flush_failed")
        
        # Cancel periodic flush task if it exists
        # (The loop runner will exit naturally when _shutdown is True)
        
        # Wait for loop to finish
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=5.0)
        
        logger.info("async_db_stopped", stats=self._stats)
    
    def get_stats(self) -> dict[str, int]:
        """Get database statistics."""
        return self._stats.copy()


# ──────────────────────────────────────────────
#  Sync Wrapper for Compatibility
# ──────────────────────────────────────────────

class SyncDatabaseWrapper:
    """
    Synchronous wrapper around AsyncDatabase for gradual migration.
    Runs async methods in the background loop.
    """
    
    def __init__(self, async_db: AsyncDatabase):
        self.async_db = async_db
        self._loop = async_db._loop
        self._sync_db: "Database | None" = None
    
    def _run_async(self, coro):
        """Run coroutine in background loop and wait for result."""
        if self._loop is None or self._loop.is_closed():
            raise RuntimeError("Database loop not running")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30.0)

    def _get_sync_db(self) -> "Database":
        """Lazily create the synchronous Database handle for the same file.

        The async migration only ported a subset of the query surface onto
        AsyncDatabase. Anything the engine still calls on the sync handle
        (get_user_rules, prune_old_logs, add_user_rule, ...) is served by the
        original synchronous Database implementation, which points at the very
        same SQLite file.
        """
        if self._sync_db is None:
            from netstrip.data.database import Database
            self._sync_db = Database(self.async_db.db_path)
        return self._sync_db

    def __getattr__(self, name: str):
        """Delegate unknown attributes to the synchronous Database handle.

        Only reached when normal attribute lookup fails, so the explicitly
        defined methods above keep priority. Private/dunder names are not
        delegated to avoid masking real AttributeErrors.
        """
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._get_sync_db(), name)
    
    def log_connection(self, data: dict[str, Any]):
        self._run_async(self.async_db.log_connection(data))
    
    def update_daily_stats(self, action: str, category: str):
        self._run_async(self.async_db.update_daily_stats(action, category))
    
    def get_recent_connections(self, limit: int = 100, unique_only: bool = False, since_timestamp: str | None = None):
        return self._run_async(self.async_db.get_recent_connections(limit, unique_only, since_timestamp))
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        return self._run_async(self.async_db.get_setting(key, default))
    
    def set_setting(self, key: str, value: Any):
        self._run_async(self.async_db.set_setting(key, value))
    
    def flush(self, timeout: float = 5.0):
        self._run_async(self.async_db.flush(timeout))
    
    def stop(self):
        # Tear down the delegating sync handle FIRST: it owns a background
        # writer thread and its own SQLite connection, and `async_db.stop()`
        # knows nothing about it. Without this the thread/connection is orphaned
        # until GC (leaking one per wrapper lifecycle).
        sync_db = getattr(self, "_sync_db", None)
        if sync_db is not None:
            try:
                sync_db.stop()
            except Exception:  # noqa: BLE001
                logger.debug("sync_db_stop_failed")
            self._sync_db = None  # avoid double-stop via Database.__del__
        self.async_db.stop()
    
    def get_stats(self):
        return self.async_db.get_stats()


# Factory function
def create_async_database(db_path: str | None = None, **kwargs) -> tuple[AsyncDatabase, SyncDatabaseWrapper]:
    """Create async database and sync wrapper."""
    async_db = AsyncDatabase(db_path, **kwargs)
    sync_wrapper = SyncDatabaseWrapper(async_db)
    return async_db, sync_wrapper
