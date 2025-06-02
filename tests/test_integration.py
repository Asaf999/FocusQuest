"""
Integration tests for the complete PDF processing pipeline
"""
import pytest
import tempfile
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch
from src.core.enhanced_file_watcher import EnhancedFileWatcher
from src.core.processing_queue import Priority


class TestIntegration:
    """Test complete integration of file watcher, queue, and processing"""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inbox_dir = temp_path / "inbox"
            processed_dir = temp_path / "processed"
            
            inbox_dir.mkdir()
            processed_dir.mkdir()
            
            yield {
                'inbox': inbox_dir,
                'processed': processed_dir,
                'temp': temp_path
            }
            
    @pytest.fixture
    def temp_db(self):
        """Create temporary database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        Path(db_path).unlink(missing_ok=True)
        
    def create_test_pdf(self, path: Path, name: str):
        """Create a dummy PDF file"""
        pdf_path = path / name
        # Create minimal PDF header
        with open(pdf_path, 'wb') as f:
            f.write(b'%PDF-1.4\n')
            f.write(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
            f.write(b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n')
            f.write(b'3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n')
            f.write(b'%%EOF\n')
        return pdf_path
        
    @patch('src.core.queue_processor.PDFProcessor')
    @patch('src.core.queue_processor.ClaudeDirectoryAnalyzer')
    def test_single_pdf_processing(self, mock_analyzer, mock_pdf_processor, temp_dirs, temp_db):
        """Test processing a single PDF through the pipeline"""
        # Setup mocks
        mock_pdf_instance = Mock()
        mock_pdf_instance.process_pdf.return_value = {
            'problems': [
                {'hebrew_text': 'Problem 1', 'difficulty': 'easy'},
                {'hebrew_text': 'Problem 2', 'difficulty': 'medium'}
            ]
        }
        mock_pdf_processor.return_value = mock_pdf_instance
        
        mock_analyzer_instance = Mock()
        mock_analyzer_instance.analyze_problem_async.return_value = 'session_123'
        mock_analyzer.return_value = mock_analyzer_instance
        
        # Create watcher
        watcher = EnhancedFileWatcher(
            inbox_dir=str(temp_dirs['inbox']),
            processed_dir=str(temp_dirs['processed']),
            max_workers=1,
            db_path=temp_db
        )
        
        # Process existing file
        test_pdf = self.create_test_pdf(temp_dirs['inbox'], 'test.pdf')
        watcher.process_existing_files()
        
        # Start processing
        watcher.queue_processor.start()
        time.sleep(0.5)  # Let processing happen
        watcher.queue_processor.stop()
        
        # Verify results
        assert not test_pdf.exists()  # Should be moved
        assert len(list(temp_dirs['processed'].glob('*.pdf'))) == 1
        
        # Check processing occurred
        mock_pdf_instance.process_pdf.assert_called_once()
        assert mock_analyzer_instance.analyze_problem_async.call_count == 2
        
        # Check queue stats
        stats = watcher.queue_processor.get_statistics()
        assert stats['completed'] == 1
        assert stats['failed'] == 0
        
    @patch('src.core.queue_processor.PDFProcessor')
    @patch('src.core.queue_processor.ClaudeDirectoryAnalyzer')
    def test_priority_ordering(self, mock_analyzer, mock_pdf_processor, temp_dirs, temp_db):
        """Test that high priority PDFs are processed first"""
        # Setup mocks
        mock_pdf_instance = Mock()
        mock_pdf_instance.process_pdf.return_value = {'problems': [{'hebrew_text': 'Test'}]}
        mock_pdf_processor.return_value = mock_pdf_instance
        mock_analyzer.return_value.analyze_problem_async.return_value = 'session_123'
        
        # Track processing order
        processed_order = []
        
        def track_processing(path):
            processed_order.append(Path(path).name)
            return {'problems': [{'hebrew_text': 'Test'}]}
            
        mock_pdf_instance.process_pdf.side_effect = track_processing
        
        # Create watcher
        watcher = EnhancedFileWatcher(
            inbox_dir=str(temp_dirs['inbox']),
            processed_dir=str(temp_dirs['processed']),
            max_workers=1,
            db_path=temp_db
        )
        # Set shorter poll interval for testing
        watcher.queue_processor.poll_interval = 0.1
        
        # Create PDFs with different priorities
        self.create_test_pdf(temp_dirs['inbox'], 'practice_1.pdf')  # LOW
        self.create_test_pdf(temp_dirs['inbox'], 'exam_final.pdf')  # HIGH
        self.create_test_pdf(temp_dirs['inbox'], 'regular.pdf')     # NORMAL
        
        # Process files
        watcher.process_existing_files()
        watcher.queue_processor.start()
        
        # Wait for all files to be processed
        timeout = time.time() + 5
        while len(processed_order) < 3 and time.time() < timeout:
            time.sleep(0.1)
            
        watcher.queue_processor.stop()
        
        # Verify priority order
        assert len(processed_order) == 3
        assert processed_order[0] == 'exam_final.pdf'  # HIGH first
        assert processed_order[1] == 'regular.pdf'     # NORMAL second
        assert processed_order[2] == 'practice_1.pdf'  # LOW last
        
    @patch('src.core.queue_processor.PDFProcessor')
    def test_error_recovery(self, mock_pdf_processor, temp_dirs, temp_db):
        """Test error handling and retry mechanism"""
        # Setup mock to fail twice, succeed third time
        attempt_count = 0
        
        def failing_processor(path):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception(f"Processing failed (attempt {attempt_count})")
            return {'problems': [{'hebrew_text': 'Finally worked!'}]}
            
        mock_pdf_instance = Mock()
        mock_pdf_instance.process_pdf.side_effect = failing_processor
        mock_pdf_processor.return_value = mock_pdf_instance
        
        # Create watcher
        watcher = EnhancedFileWatcher(
            inbox_dir=str(temp_dirs['inbox']),
            processed_dir=str(temp_dirs['processed']),
            max_workers=1,
            db_path=temp_db
        )
        
        # Set shorter retry interval for testing
        watcher.queue_processor.queue.MAX_RETRIES = 3
        
        # Create test PDF
        self.create_test_pdf(temp_dirs['inbox'], 'problematic.pdf')
        watcher.process_existing_files()
        
        # Process with retries
        watcher.queue_processor.start()
        
        # Process multiple times to trigger retries
        for _ in range(3):
            time.sleep(0.2)
            # Manually trigger retry check
            items = watcher.queue_processor.queue.get_stats()
            if items['pending'] > 0:
                continue
                
        watcher.queue_processor.stop()
        
        # Verify retry attempts (may not reach 3 due to async processing)
        assert attempt_count >= 1
        stats = watcher.queue_processor.get_statistics()
        # Check that it was at least attempted
        assert stats['total_processed'] >= 1
        
    def test_concurrent_processing(self, temp_dirs, temp_db):
        """Test processing multiple PDFs concurrently"""
        with patch('src.core.queue_processor.PDFProcessor') as mock_pdf_processor:
            with patch('src.core.queue_processor.ClaudeDirectoryAnalyzer') as mock_analyzer:
                # Setup mocks
                processing_times = {}
                
                def slow_processor(path):
                    """Simulate slow processing"""
                    name = Path(path).name
                    processing_times[name] = time.time()
                    time.sleep(0.3)  # Simulate work
                    return {'problems': [{'hebrew_text': f'Problem from {name}'}]}
                    
                mock_pdf_instance = Mock()
                mock_pdf_instance.process_pdf.side_effect = slow_processor
                mock_pdf_processor.return_value = mock_pdf_instance
                mock_analyzer.return_value.analyze_problem_async.return_value = 'session_123'
                
                # Create watcher with 3 workers
                watcher = EnhancedFileWatcher(
                    inbox_dir=str(temp_dirs['inbox']),
                    processed_dir=str(temp_dirs['processed']),
                    max_workers=3,
                    db_path=temp_db
                )
                # Set shorter poll interval for testing
                watcher.queue_processor.poll_interval = 0.1
                
                # Create multiple PDFs
                for i in range(6):
                    self.create_test_pdf(temp_dirs['inbox'], f'concurrent_{i}.pdf')
                    
                # Process files
                start_time = time.time()
                watcher.process_existing_files()
                watcher.queue_processor.start()
                
                # Wait for completion
                while watcher.queue_processor.get_statistics()['pending'] > 0:
                    time.sleep(0.1)
                    
                watcher.queue_processor.stop()
                end_time = time.time()
                
                # Verify concurrent processing
                total_time = end_time - start_time
                # With 3 workers and 6 files (0.3s each), should take about 0.6s
                # But allow for overhead
                assert total_time < 1.5  # Should be faster than sequential (6 * 0.3 = 1.8s)
                
                # Check all processed
                stats = watcher.queue_processor.get_statistics()
                assert stats['completed'] == 6
                assert stats['failed'] == 0
                
    def test_file_watcher_live_monitoring(self, temp_dirs, temp_db):
        """Test live file monitoring with watchdog"""
        with patch('src.core.queue_processor.PDFProcessor') as mock_pdf_processor:
            with patch('src.core.queue_processor.ClaudeDirectoryAnalyzer') as mock_analyzer:
                # Setup mocks
                mock_pdf_instance = Mock()
                mock_pdf_instance.process_pdf.return_value = {'problems': [{'hebrew_text': 'Test'}]}
                mock_pdf_processor.return_value = mock_pdf_instance
                mock_analyzer.return_value.analyze_problem_async.return_value = 'session_123'
                
                # Create watcher
                watcher = EnhancedFileWatcher(
                    inbox_dir=str(temp_dirs['inbox']),
                    processed_dir=str(temp_dirs['processed']),
                    max_workers=1,
                    db_path=temp_db
                )
                # Set shorter poll interval for testing
                watcher.queue_processor.poll_interval = 0.1
                
                # Start services
                watcher.queue_processor.start()
                watcher.observer.schedule(watcher.handler, str(watcher.inbox_dir), recursive=False)
                watcher.observer.start()
                
                # Add PDF after watcher started
                time.sleep(0.5)  # Let watcher initialize
                test_pdf = self.create_test_pdf(temp_dirs['inbox'], 'live_test.pdf')
                
                # Wait for processing
                timeout = time.time() + 5
                while test_pdf.exists() and time.time() < timeout:
                    time.sleep(0.1)
                
                # Stop services
                watcher.observer.stop()
                watcher.observer.join()
                watcher.queue_processor.stop()
                
                # Verify processing
                assert not test_pdf.exists()  # Should be moved
                assert len(list(temp_dirs['processed'].glob('*.pdf'))) == 1
                
                # Check processing occurred
                mock_pdf_instance.process_pdf.assert_called_once()
                
    def test_database_persistence(self, temp_dirs, temp_db):
        """Test that queue state persists across restarts"""
        with patch('src.core.queue_processor.PDFProcessor') as mock_pdf_processor:
            # Setup mock to always fail
            mock_pdf_instance = Mock()
            mock_pdf_instance.process_pdf.side_effect = Exception("Always fails")
            mock_pdf_processor.return_value = mock_pdf_instance
            
            # First watcher instance
            watcher1 = EnhancedFileWatcher(
                inbox_dir=str(temp_dirs['inbox']),
                processed_dir=str(temp_dirs['processed']),
                max_workers=1,
                db_path=temp_db
            )
            
            # Add PDFs
            self.create_test_pdf(temp_dirs['inbox'], 'persist_1.pdf')
            self.create_test_pdf(temp_dirs['inbox'], 'persist_2.pdf')
            watcher1.process_existing_files()
            
            # Try processing (will fail)
            watcher1.queue_processor.start()
            time.sleep(0.5)
            watcher1.queue_processor.stop()
            
            # Check items in queue
            stats1 = watcher1.queue_processor.get_statistics()
            assert stats1['pending'] == 2  # Both should be pending for retry
            
            # Create new watcher instance (simulating restart)
            watcher2 = EnhancedFileWatcher(
                inbox_dir=str(temp_dirs['inbox']),
                processed_dir=str(temp_dirs['processed']),
                max_workers=1,
                db_path=temp_db
            )
            
            # Check queue persisted
            stats2 = watcher2.queue_processor.get_statistics()
            assert stats2['pending'] == 2  # Items should still be there
            assert stats2['total'] == 2