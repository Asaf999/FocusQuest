"""
Thread-safe persistent processing queue for PDF files
Uses SQLite for crash recovery and concurrent access
"""
import sqlite3
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from enum import IntEnum, Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Configure SQLite to use string adapter for datetime
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_converter("timestamp", lambda b: datetime.fromisoformat(b.decode()))


class Priority(IntEnum):
    """Processing priority levels"""
    HIGH = 0
    NORMAL = 1
    LOW = 2


class Status(str, Enum):
    """Queue item status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class QueueItem:
    """Queue item data class"""
    id: int
    pdf_path: str
    priority: Priority
    status: Status
    attempts: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ProcessingQueue:
    """Thread-safe persistent processing queue"""
    
    MAX_RETRIES = 3
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            project_root = Path("/home/puncher/focusquest")
            db_path = str(project_root / "data" / "processing_queue.db")
            
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_database()
        
    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queue_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pdf_path TEXT NOT NULL UNIQUE,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    created_at TIMESTAMP NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT
                )
            """)
            
            # Create indices for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status_priority 
                ON queue_items(status, priority, created_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pdf_path 
                ON queue_items(pdf_path)
            """)
            
            conn.commit()
            
    def add_item(self, pdf_path: str, priority: Priority = Priority.NORMAL) -> Optional[int]:
        """Add item to queue, returns item ID or None if duplicate"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                    cursor = conn.execute("""
                        INSERT INTO queue_items 
                        (pdf_path, priority, status, attempts, created_at)
                        VALUES (?, ?, ?, 0, ?)
                    """, (
                        pdf_path,
                        int(priority),
                        Status.PENDING,
                        datetime.now()
                    ))
                    conn.commit()
                    return cursor.lastrowid
                    
            except sqlite3.IntegrityError:
                # Duplicate path
                logger.warning(f"Duplicate PDF path ignored: {pdf_path}")
                return None
                
    def get_next_item(self) -> Optional[QueueItem]:
        """Get next item to process (highest priority, oldest first)"""
        with self._lock:
            with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get next pending item
                cursor = conn.execute("""
                    SELECT * FROM queue_items
                    WHERE status = ?
                    ORDER BY priority ASC, created_at ASC
                    LIMIT 1
                """, (Status.PENDING,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                    
                # Mark as processing
                conn.execute("""
                    UPDATE queue_items
                    SET status = ?, started_at = ?
                    WHERE id = ?
                """, (Status.PROCESSING, datetime.now(), row['id']))
                
                conn.commit()
                
                # Return the item with updated status
                item = self._row_to_item(row)
                item.status = Status.PROCESSING
                return item
                
    def mark_completed(self, item_id: int):
        """Mark item as completed"""
        with self._lock:
            with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                conn.execute("""
                    UPDATE queue_items
                    SET status = ?, completed_at = ?
                    WHERE id = ?
                """, (Status.COMPLETED, datetime.now(), item_id))
                conn.commit()
                
    def mark_failed(self, item_id: int, error_message: str):
        """Mark item as failed with error message"""
        with self._lock:
            with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                conn.execute("""
                    UPDATE queue_items
                    SET status = ?, 
                        error_message = ?,
                        attempts = attempts + 1
                    WHERE id = ?
                """, (Status.FAILED, error_message, item_id))
                conn.commit()
                
    def mark_for_retry(self, item_id: int) -> bool:
        """Mark failed item for retry if under max attempts"""
        with self._lock:
            with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                conn.row_factory = sqlite3.Row
                
                # Check current attempts
                cursor = conn.execute("""
                    SELECT attempts FROM queue_items
                    WHERE id = ?
                """, (item_id,))
                
                row = cursor.fetchone()
                if not row or row['attempts'] >= self.MAX_RETRIES:
                    return False
                    
                # Reset to pending for retry
                conn.execute("""
                    UPDATE queue_items
                    SET status = ?, started_at = NULL
                    WHERE id = ?
                """, (Status.PENDING, item_id))
                
                conn.commit()
                return True
                
    def get_item_status(self, item_id: int) -> Optional[Dict]:
        """Get status info for specific item"""
        with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM queue_items WHERE id = ?
            """, (item_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            return dict(row)
            
    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM queue_items
                GROUP BY status
            """)
            
            stats = {
                'pending': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0,
                'total': 0
            }
            
            for row in cursor:
                status = row[0]
                count = row[1]
                if status in stats:
                    stats[status] = count
                stats['total'] += count
                
            return stats
            
    def cleanup_old_items(self, days: int = 7) -> int:
        """Remove completed items older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self._lock:
            with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.execute("""
                    DELETE FROM queue_items
                    WHERE status = ? AND completed_at < ?
                """, (Status.COMPLETED, cutoff_date))
                
                conn.commit()
                return cursor.rowcount
                
    def recover_stale_items(self, stale_minutes: int = 30) -> int:
        """Recover items stuck in processing state"""
        cutoff_time = datetime.now() - timedelta(minutes=stale_minutes)
        
        with self._lock:
            with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.execute("""
                    UPDATE queue_items
                    SET status = ?, attempts = attempts + 1
                    WHERE status = ? AND started_at < ?
                """, (Status.PENDING, Status.PROCESSING, cutoff_time))
                
                conn.commit()
                return cursor.rowcount
                
    def _row_to_item(self, row: sqlite3.Row) -> QueueItem:
        """Convert database row to QueueItem"""
        return QueueItem(
            id=row['id'],
            pdf_path=row['pdf_path'],
            priority=Priority(row['priority']),
            status=Status(row['status']),
            attempts=row['attempts'],
            created_at=row['created_at'] if isinstance(row['created_at'], datetime) else datetime.fromisoformat(row['created_at']),
            started_at=row['started_at'] if isinstance(row['started_at'], datetime) else datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
            completed_at=row['completed_at'] if isinstance(row['completed_at'], datetime) else datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            error_message=row['error_message']
        )