"""
Test ProcessingQueue functionality for production file watcher
"""
import pytest
import tempfile
import time
from pathlib import Path
from datetime import datetime, timedelta
from src.core.processing_queue import ProcessingQueue, QueueItem, Priority, Status


class TestProcessingQueue:
    """Test the persistent processing queue"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        Path(db_path).unlink(missing_ok=True)
        
    @pytest.fixture
    def queue(self, temp_db):
        """Create ProcessingQueue instance"""
        return ProcessingQueue(db_path=temp_db)
        
    def test_queue_creation(self, queue):
        """Test queue creates database and tables"""
        assert queue is not None
        assert Path(queue.db_path).exists()
        
    def test_add_item(self, queue):
        """Test adding items to queue"""
        item_id = queue.add_item("/path/to/test.pdf", Priority.NORMAL)
        assert item_id is not None
        assert item_id > 0
        
    def test_add_item_with_priority(self, queue):
        """Test adding items with different priorities"""
        high_id = queue.add_item("/path/high.pdf", Priority.HIGH)
        normal_id = queue.add_item("/path/normal.pdf", Priority.NORMAL)
        low_id = queue.add_item("/path/low.pdf", Priority.LOW)
        
        assert all(id is not None for id in [high_id, normal_id, low_id])
        
    def test_get_next_item_priority_order(self, queue):
        """Test items are retrieved in priority order"""
        # Add items in reverse priority order
        queue.add_item("/path/low.pdf", Priority.LOW)
        queue.add_item("/path/normal.pdf", Priority.NORMAL)
        queue.add_item("/path/high.pdf", Priority.HIGH)
        
        # Should get high priority first
        item = queue.get_next_item()
        assert item is not None
        assert item.pdf_path == "/path/high.pdf"
        assert item.priority == Priority.HIGH
        assert item.status == Status.PROCESSING
        
    def test_get_next_item_fifo_within_priority(self, queue):
        """Test FIFO order within same priority"""
        queue.add_item("/path/first.pdf", Priority.NORMAL)
        time.sleep(0.01)  # Ensure different timestamps
        queue.add_item("/path/second.pdf", Priority.NORMAL)
        
        item1 = queue.get_next_item()
        assert item1.pdf_path == "/path/first.pdf"
        
        item2 = queue.get_next_item()
        assert item2.pdf_path == "/path/second.pdf"
        
    def test_mark_completed(self, queue):
        """Test marking item as completed"""
        item_id = queue.add_item("/path/test.pdf", Priority.NORMAL)
        queue.get_next_item()  # Sets to processing
        
        queue.mark_completed(item_id)
        
        # Completed items shouldn't be returned
        assert queue.get_next_item() is None
        
    def test_mark_failed(self, queue):
        """Test marking item as failed"""
        item_id = queue.add_item("/path/test.pdf", Priority.NORMAL)
        queue.get_next_item()  # Sets to processing
        
        queue.mark_failed(item_id, "Test error")
        
        # Check status and error
        status = queue.get_item_status(item_id)
        assert status['status'] == Status.FAILED
        assert status['error_message'] == "Test error"
        assert status['attempts'] == 1
        
    def test_retry_failed_items(self, queue):
        """Test retry logic for failed items"""
        item_id = queue.add_item("/path/test.pdf", Priority.NORMAL)
        queue.get_next_item()
        queue.mark_failed(item_id, "First failure")
        
        # Should not get failed item immediately
        assert queue.get_next_item() is None
        
        # Mark for retry
        queue.mark_for_retry(item_id)
        
        # Now should get it
        item = queue.get_next_item()
        assert item is not None
        assert item.id == item_id
        assert item.attempts == 1
        
    def test_max_retry_attempts(self, queue):
        """Test maximum retry attempts"""
        item_id = queue.add_item("/path/test.pdf", Priority.NORMAL)
        
        # Fail multiple times
        for i in range(3):
            queue.get_next_item()
            queue.mark_failed(item_id, f"Failure {i+1}")
            if i < 2:  # Don't retry on last failure
                queue.mark_for_retry(item_id)
                
        # Should not retry after max attempts
        assert not queue.mark_for_retry(item_id)
        
    def test_prevent_duplicates(self, queue):
        """Test duplicate prevention"""
        queue.add_item("/path/test.pdf", Priority.NORMAL)
        
        # Adding same path should return None
        duplicate_id = queue.add_item("/path/test.pdf", Priority.NORMAL)
        assert duplicate_id is None
        
    def test_get_queue_stats(self, queue):
        """Test getting queue statistics"""
        # Add various items
        queue.add_item("/path/pending1.pdf", Priority.HIGH)
        queue.add_item("/path/pending2.pdf", Priority.NORMAL)
        
        item_id = queue.add_item("/path/processing.pdf", Priority.NORMAL)
        queue.get_next_item()  # Mark as processing
        
        completed_id = queue.add_item("/path/completed.pdf", Priority.LOW)
        item = queue.get_next_item()  # This gets pending1.pdf (HIGH priority)
        queue.mark_completed(item.id)
        
        stats = queue.get_stats()
        assert stats['pending'] == 2
        assert stats['processing'] == 1
        assert stats['completed'] == 1
        assert stats['failed'] == 0
        assert stats['total'] == 4
        
    def test_cleanup_old_completed(self, queue):
        """Test cleanup of old completed items"""
        # Add and complete an item
        item_id = queue.add_item("/path/old.pdf", Priority.NORMAL)
        queue.get_next_item()
        queue.mark_completed(item_id)
        
        # Should exist initially
        assert queue.get_item_status(item_id) is not None
        
        # Cleanup items older than 0 days (all items)
        deleted = queue.cleanup_old_items(days=0)
        assert deleted == 1
        
        # Should be gone now
        assert queue.get_item_status(item_id) is None
        
    def test_concurrent_access(self, queue):
        """Test thread-safe concurrent access"""
        import threading
        
        results = []
        
        def add_items():
            for i in range(10):
                item_id = queue.add_item(f"/path/thread_{i}.pdf", Priority.NORMAL)
                results.append(('add', item_id))
                
        def get_items():
            for i in range(10):
                item = queue.get_next_item()
                if item:
                    results.append(('get', item.id))
                    
        # Run concurrently
        t1 = threading.Thread(target=add_items)
        t2 = threading.Thread(target=get_items)
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        
        # Should have handled all operations without errors
        add_count = len([r for r in results if r[0] == 'add'])
        get_count = len([r for r in results if r[0] == 'get'])
        
        assert add_count == 10
        assert get_count <= 10  # May get less if timing doesn't align
        
    def test_crash_recovery(self, temp_db):
        """Test recovery from crash (stale processing items)"""
        # Create queue and mark item as processing
        queue1 = ProcessingQueue(db_path=temp_db)
        item_id = queue1.add_item("/path/crash.pdf", Priority.NORMAL)
        item = queue1.get_next_item()
        assert item.status == Status.PROCESSING
        
        # Simulate crash - create new queue instance
        queue2 = ProcessingQueue(db_path=temp_db)
        
        # Should recover stale processing items
        recovered = queue2.recover_stale_items(stale_minutes=0)
        assert recovered == 1
        
        # Should be available again
        item = queue2.get_next_item()
        assert item is not None
        assert item.pdf_path == "/path/crash.pdf"
        assert item.attempts == 1