"""
Test QueueProcessor functionality for concurrent PDF processing
"""
import pytest
import tempfile
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.core.queue_processor import QueueProcessor
from src.core.processing_queue import ProcessingQueue, Priority


class TestQueueProcessor:
    """Test the queue processor with threading"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        Path(db_path).unlink(missing_ok=True)
        
    @pytest.fixture
    def processor(self, temp_db):
        """Create QueueProcessor instance"""
        return QueueProcessor(
            db_path=temp_db,
            max_workers=2,
            poll_interval=0.1
        )
        
    def test_processor_creation(self, processor):
        """Test processor initialization"""
        assert processor is not None
        assert processor.max_workers == 2
        assert processor.poll_interval == 0.1
        assert not processor.is_running
        
    def test_start_stop_processor(self, processor):
        """Test starting and stopping processor"""
        processor.start()
        assert processor.is_running
        
        time.sleep(0.2)  # Let it run briefly
        
        processor.stop()
        assert not processor.is_running
        
    def test_process_single_item(self, processor):
        """Test processing a single queue item"""
        # Setup mocks
        mock_pdf_processor = Mock()
        mock_pdf_processor.process_pdf.return_value = {
            'problems': [{'hebrew_text': 'Test problem'}]
        }
        processor.pdf_processor = mock_pdf_processor
        
        mock_analyzer = Mock()
        mock_analyzer.analyze_problem_async.return_value = 'session_123'
        processor.claude_analyzer = mock_analyzer
        
        # Add item to queue
        processor.queue.add_item("/path/test.pdf", Priority.NORMAL)
        
        # Process one item
        processor._process_next_item()
        
        # Verify processing
        mock_pdf_processor.process_pdf.assert_called_once_with("/path/test.pdf")
        mock_analyzer.analyze_problem_async.assert_called_once()
        
        # Check item marked complete
        stats = processor.queue.get_stats()
        assert stats['completed'] == 1
        
    def test_handle_processing_error(self, processor):
        """Test error handling during processing"""
        # Setup mock to raise error
        mock_pdf_processor = Mock()
        mock_pdf_processor.process_pdf.side_effect = Exception("PDF processing failed")
        processor.pdf_processor = mock_pdf_processor
        
        # Add item to queue
        item_id = processor.queue.add_item("/path/error.pdf", Priority.NORMAL)
        
        # Process item (should fail)
        processor._process_next_item()
        
        # Check item marked for retry (since attempts < max)
        status = processor.queue.get_item_status(item_id)
        assert status['status'] == 'pending'  # Marked for retry automatically
        assert 'PDF processing failed' in status['error_message']
        assert status['attempts'] == 1
        
    def test_concurrent_processing(self, processor):
        """Test concurrent processing with multiple workers"""
        processed_items = []
        process_lock = threading.Lock()
        
        def mock_process_item(item):
            """Mock processing that tracks items"""
            time.sleep(0.1)  # Simulate work
            with process_lock:
                processed_items.append(item.pdf_path)
            processor.queue.mark_completed(item.id)
            
        # Patch the process method
        with patch.object(processor, '_process_item', side_effect=mock_process_item):
            # Add multiple items
            for i in range(5):
                processor.queue.add_item(f"/path/pdf_{i}.pdf", Priority.NORMAL)
                
            # Start processor
            processor.start()
            
            # Wait for processing
            timeout = time.time() + 2
            while len(processed_items) < 5 and time.time() < timeout:
                time.sleep(0.1)
                
            processor.stop()
            
        # Verify all items processed
        assert len(processed_items) == 5
        assert all(f"/path/pdf_{i}.pdf" in processed_items for i in range(5))
        
    def test_priority_processing_order(self, processor):
        """Test that high priority items are processed first"""
        processed_order = []
        
        def mock_process_item(item):
            """Track processing order"""
            processed_order.append(item.pdf_path)
            processor.queue.mark_completed(item.id)
            
        with patch.object(processor, '_process_item', side_effect=mock_process_item):
            # Add items in mixed priority order
            processor.queue.add_item("/path/low.pdf", Priority.LOW)
            processor.queue.add_item("/path/high.pdf", Priority.HIGH)
            processor.queue.add_item("/path/normal.pdf", Priority.NORMAL)
            
            # Process all items
            for _ in range(3):
                processor._process_next_item()
                
        # Verify priority order
        assert processed_order == ["/path/high.pdf", "/path/normal.pdf", "/path/low.pdf"]
        
    def test_retry_mechanism(self, processor):
        """Test automatic retry for failed items"""
        attempt_count = 0
        
        # Mock the PDF processor to fail first, succeed second
        mock_pdf_processor = Mock()
        def side_effect(*args):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise Exception("First attempt failed")
            return {'problems': [{'hebrew_text': 'Test problem'}]}
            
        mock_pdf_processor.process_pdf.side_effect = side_effect
        processor.pdf_processor = mock_pdf_processor
        
        # Mock analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze_problem_async.return_value = 'session_123'
        processor.claude_analyzer = mock_analyzer
        
        item_id = processor.queue.add_item("/path/retry.pdf", Priority.NORMAL)
        
        # First attempt (fails)
        processor._process_next_item()
        
        # Check marked for retry
        status = processor.queue.get_item_status(item_id)
        assert status['status'] == 'pending'  # Should be retrying
        assert status['attempts'] == 1
        
        # Second attempt (succeeds)
        processor._process_next_item()
        
        # Verify success after retry
        status = processor.queue.get_item_status(item_id)
        assert status['status'] == 'completed'
        assert attempt_count == 2
        
    def test_graceful_shutdown(self, processor):
        """Test graceful shutdown during processing"""
        processing_started = threading.Event()
        
        def slow_process_item(item):
            """Simulate slow processing"""
            processing_started.set()
            time.sleep(1)  # Longer than test timeout
            processor.queue.mark_completed(item.id)
            
        with patch.object(processor, '_process_item', side_effect=slow_process_item):
            processor.queue.add_item("/path/slow.pdf", Priority.NORMAL)
            
            # Start processing in background
            processor.start()
            
            # Wait for processing to start
            processing_started.wait(timeout=1)
            
            # Stop processor (should wait for current item)
            processor.stop(timeout=0.5)
            
        # Processor should have stopped gracefully
        assert not processor.is_running
        
    def test_statistics_tracking(self, processor):
        """Test processing statistics"""
        # Process some items
        def mock_process_item(item):
            processor.queue.mark_completed(item.id)
            processor._update_stats(success=True, processing_time=0.1)
            
        with patch.object(processor, '_process_item', side_effect=mock_process_item):
            for i in range(3):
                processor.queue.add_item(f"/path/pdf_{i}.pdf", Priority.NORMAL)
                
            for _ in range(3):
                processor._process_next_item()
                
        stats = processor.get_statistics()
        assert stats['total_processed'] == 3
        assert stats['success_count'] == 3
        assert stats['failure_count'] == 0
        assert 'average_processing_time' in stats
        
    def test_stale_recovery_on_start(self, temp_db):
        """Test recovery of stale items on processor start"""
        # Create first processor and leave item in processing
        processor1 = QueueProcessor(db_path=temp_db)
        processor1.queue.add_item("/path/stale.pdf", Priority.NORMAL)
        item = processor1.queue.get_next_item()  # Mark as processing
        
        # Create new processor (simulates restart)
        processor2 = QueueProcessor(db_path=temp_db, stale_timeout_minutes=0)
        
        # Should recover the stale item
        recovered = processor2.queue.recover_stale_items(stale_minutes=0)
        assert recovered == 1
        
        # Item should be available for processing
        next_item = processor2.queue.get_next_item()
        assert next_item is not None
        assert next_item.pdf_path == "/path/stale.pdf"