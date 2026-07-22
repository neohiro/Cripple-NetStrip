"""
Notification Manager for NetStrip
Silently queues unknown connections for the user to review in the GUI.
No more popup storms.
"""

import threading
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from netstrip.data.database import Database


class PendingConnection:
    """A single pending connection awaiting user decision."""
    def __init__(self, conn_data: Dict[str, Any]):
        self.conn_data = conn_data
        self.process_name = conn_data.get('process_name', 'Unknown')
        self.process_path = conn_data.get('process_path', '')
        self.domain = conn_data.get('domain', '')
        self.ip = conn_data.get('ip', '')
        self.port = conn_data.get('port', 0)
        self.protocol = conn_data.get('protocol', '')
        self.category = conn_data.get('category', 'unknown')
        self.timestamp = datetime.now()
        self.target = self.domain or self.ip


class NotificationManager:
    def __init__(self, db: Database):
        self.db = db
        self.lock = threading.Lock()
        self.pending_items: List[PendingConnection] = []
        self._seen_targets: set = set()
        self.on_count_changed: Optional[Callable[[int], None]] = None

    @property
    def pending_count(self) -> int:
        with self.lock:
            return len(self.pending_items)

    def push(self, conn_data: Dict[str, Any]):
        """Silently queue a connection for later review. Deduplicates."""
        target = conn_data.get('domain') or conn_data.get('ip', '')
        process = conn_data.get('process_name', '')
        key = (process, target)

        with self.lock:
            if key in self._seen_targets:
                return
            self._seen_targets.add(key)
            self.pending_items.append(PendingConnection(conn_data))

        if self.on_count_changed:
            try:
                self.on_count_changed(self.pending_count)
            except Exception:
                pass

    def get_pending(self) -> List[PendingConnection]:
        """Get all pending items (thread-safe copy)."""
        with self.lock:
            return list(self.pending_items)

    def resolve(self, pending: PendingConnection, action: str, scope: str = 'global'):
        """User made a decision. Save rule and remove from pending."""
        with self.lock:
            if pending in self.pending_items:
                self.pending_items.remove(pending)
                key = (pending.process_name, pending.target)
                self._seen_targets.discard(key)

        if action in ['allow', 'block']:
            self.db.add_user_rule({
                'pattern': pending.target,
                'action': action,
                'scope': scope,
                'app_name': pending.process_name if scope == 'per-app' else None,
                'category': 'user_allowed' if action == 'allow' else 'user_blocked',
                'note': f"User decision for {pending.process_name}"
            })

        if self.on_count_changed:
            try:
                self.on_count_changed(self.pending_count)
            except Exception:
                pass

    def resolve_all(self, action: str):
        """Resolve ALL pending items with the same action."""
        with self.lock:
            items = list(self.pending_items)
            self.pending_items.clear()
            self._seen_targets.clear()

        for item in items:
            if action in ['allow', 'block']:
                self.db.add_user_rule({
                    'pattern': item.target,
                    'action': action,
                    'scope': 'global',
                    'app_name': None,
                    'category': 'user_allowed' if action == 'allow' else 'user_blocked',
                    'note': f"Bulk {action} for {item.process_name}"
                })

        if self.on_count_changed:
            try:
                self.on_count_changed(self.pending_count)
            except Exception:
                pass
