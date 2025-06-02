"""Test thread safety in FileWatcher for concurrent PDF processing."""
import pytest
import threading
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import queue

from src.core.file_watcher import FileWatcher, PDFHandler


class TestFileWatcherConcurrency:
    """Test FileWatcher thread safety with concurrent PDFs."""
    
    @pytest.fixture
    def temp_inbox(self):
        """Create temporary inbox directory."""
        temp_dir = tempfile.mkdtemp()
        inbox = Path(temp_dir) / "inbox"
        inbox.mkdir()
        yield inbox
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_processor(self):
        """Create mock PDF processor."""
        processor = Mock()
        processor.extract_text.return_value = "Test content"
        return processor
    
    @pytest.fixture
    def mock_analyzer(self):
        """Create mock Claude analyzer."""
        analyzer = Mock()
        analyzer.analyze_directory.return_value = {
            'problems': [{'id': 1, 'text': 'Test problem'}]
        }
        return analyzer
    
    def test_concurrent_pdf_processing(self, temp_inbox, mock_processor, mock_analyzer):
        """Test that multiple PDFs can be processed concurrently without race conditions."""
        # Track processing order
        processing_queue = queue.Queue()
        process_times = {}
        
        def track_processing(pdf_path):
            processing_queue.put(pdf_path)
            # Simulate processing time
            time.sleep(0.1)
            process_times[pdf_path] = time.time()
        
        # Patch the handler to track processing
        with patch('src.core.file_watcher.PDFProcessor', return_value=mock_processor), \
             patch('src.core.file_watcher.ClaudeDirectoryAnalyzer', return_value=mock_analyzer):
            
            handler = PDFHandler(
                str(temp_inbox), 
                str(temp_inbox.parent / "processed"),
                Mock()  # queue
            )
            
            # Override process_pdf to track calls
            original_process = handler.process_pdf
            handler.process_pdf = lambda path: (track_processing(path), original_process(path))
            
            # Create multiple PDFs
            pdf_files = []
            for i in range(10):
                pdf_path = temp_inbox / f"test_{i}.pdf"
                pdf_path.write_text("dummy pdf content")
                pdf_files.append(str(pdf_path))
            
            # Process all PDFs concurrently
            threads = []
            for pdf_path in pdf_files:
                thread = threading.Thread(target=handler.process_pdf, args=(pdf_path,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Verify all PDFs were processed
            assert processing_queue.qsize() == 10
            
            # Verify no race conditions - all files should have different process times
            unique_times = set(process_times.values())
            assert len(unique_times) == 10, "Race condition detected - files processed at same time"
    
    def test_queue_thread_safety(self, temp_inbox):
        """Test that the processing queue is thread-safe."""
        from src.core.processing_queue import ProcessingQueue
        
        # Create processing queue with temp file (not :memory: which is connection-specific)
        import tempfile
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        pq = ProcessingQueue(temp_db.name)
        
        # Add items from multiple threads
        def add_items(start_id):
            for i in range(100):
                pq.add_item(f"test_{start_id}_{i}.pdf", priority=1)  # Use integer priority
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_items, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify all items were added
        items = []
        while True:
            item = pq.get_next_item()
            if item is None:
                break
            items.append(item)
            pq.mark_completed(item.id)  # Use attribute access, not subscript
        
        assert len(items) == 500, f"Expected 500 items, got {len(items)}"
        
        # Cleanup
        import os
        os.unlink(temp_db.name)
    
    def test_file_move_atomicity(self, temp_inbox):
        """Test that file moves are atomic and thread-safe."""
        processed_dir = temp_inbox.parent / "processed"
        processed_dir.mkdir()
        
        # Create test PDF
        pdf_path = temp_inbox / "test.pdf"
        pdf_path.write_text("content")
        
        # Try to move the same file from multiple threads
        move_count = 0
        move_lock = threading.Lock()
        
        def try_move():
            nonlocal move_count
            try:
                if pdf_path.exists():
                    # Use atomic rename
                    dest = processed_dir / pdf_path.name
                    pdf_path.rename(dest)
                    with move_lock:
                        move_count += 1
            except FileNotFoundError:
                pass  # File already moved
        
        # Launch multiple threads trying to move
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=try_move)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Only one thread should succeed
        assert move_count == 1
        assert (processed_dir / "test.pdf").exists()
        assert not pdf_path.exists()
    
    def test_watcher_start_stop_thread_safety(self, temp_inbox):
        """Test that FileWatcher can be safely started and stopped."""
        watcher = FileWatcher(str(temp_inbox), str(temp_inbox.parent / "processed"))
        
        # Start watcher
        watcher_thread = threading.Thread(target=watcher.start)
        watcher_thread.start()
        
        # Give it time to initialize
        time.sleep(0.1)
        
        # Create a PDF while running
        pdf_path = temp_inbox / "test.pdf"
        pdf_path.write_text("content")
        
        # Stop watcher
        time.sleep(0.1)
        watcher.stop()
        watcher_thread.join(timeout=2.0)
        
        # Verify thread stopped
        assert not watcher_thread.is_alive()
    
    def test_concurrent_event_handling(self, temp_inbox):
        """Test handling of rapid file creation events."""
        from watchdog.events import FileSystemEvent
        
        handler = PDFHandler(str(temp_inbox), str(temp_inbox.parent / "processed"), Mock())
        
        # Track events
        events_processed = []
        
        original_on_created = handler.on_created
        def track_event(event):
            events_processed.append(event.src_path)
            original_on_created(event)
        
        handler.on_created = track_event
        
        # Simulate rapid events
        threads = []
        for i in range(20):
            event = FileSystemEvent(str(temp_inbox / f"test_{i}.pdf"))
            thread = threading.Thread(target=handler.on_created, args=(event,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All events should be processed
        assert len(events_processed) == 20