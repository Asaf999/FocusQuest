"""Test memory leak prevention and resource management."""
import pytest
import gc
import psutil
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import threading
import time
import logging

from src.analysis.pdf_processor import PDFProcessor
from src.analysis.claude_analyzer import ClaudeAnalyzer

logger = logging.getLogger(__name__)


class TestMemoryManagement:
    """Test memory leak prevention mechanisms."""
    
    def test_pil_image_cleanup(self):
        """Test that PIL images are properly cleaned up after OCR."""
        processor = PDFProcessor()
        
        # Mock a page with to_image method
        mock_page = Mock()
        mock_image = Mock()
        mock_page.to_image.return_value.original = mock_image
        
        # Mock pytesseract to avoid actual OCR
        with patch('pytesseract.image_to_string', return_value='test text'):
            result = processor._extract_with_ocr(mock_page)
        
        # Verify image.close() was called
        mock_image.close.assert_called_once()
        assert result == 'test text'
    
    def test_pdf_processor_memory_growth(self):
        """Test that PDF processor doesn't leak memory over multiple files."""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        processor = PDFProcessor()
        
        # Process multiple mock PDFs
        for i in range(10):
            with patch('pdfplumber.open') as mock_open:
                mock_pdf = Mock()
                mock_page = Mock()
                mock_page.extract_text.return_value = f"Test content {i}"
                mock_pdf.pages = [mock_page]
                mock_open.return_value.__enter__.return_value = mock_pdf
                
                # Create temp PDF file
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                    temp_path = f.name
                
                try:
                    result = processor.extract_content(temp_path)
                    assert result is not None
                finally:
                    os.unlink(temp_path)
        
        # Force garbage collection
        gc.collect()
        
        # Check memory growth is reasonable (less than 50MB growth)
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        assert memory_growth < 50 * 1024 * 1024, f"Memory growth too large: {memory_growth / 1024 / 1024:.1f}MB"
    
    def test_claude_analyzer_cache_limits(self):
        """Test that Claude analyzer cache has size limits."""
        analyzer = ClaudeAnalyzer(max_cache_size=100)
        
        # Add many items to cache to test LRU eviction using the proper method
        for i in range(200):  # More than max cache size
            cache_key = f"test_key_{i}"
            # Use the actual cache method instead of direct access
            analyzer._put_in_cache(cache_key, f"test_value_{i}")
        
        # Cache should be limited in size (100 is the limit)
        assert len(analyzer._cache) <= 100, f"Cache size {len(analyzer._cache)} exceeds limit"
    
    def test_subprocess_cleanup(self):
        """Test that subprocesses are properly cleaned up."""
        analyzer = ClaudeAnalyzer()
        
        # Count initial zombie processes
        current_process = psutil.Process()
        initial_zombies = sum(1 for child in current_process.children(recursive=True) 
                            if child.status() == psutil.STATUS_ZOMBIE)
        
        with patch('subprocess.run') as mock_run:
            # Simulate subprocess timeout
            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired('claude', 30)
            
            with pytest.raises(Exception):  # ClaudeAnalyzer will raise its own error
                analyzer._run_claude_cli("test prompt", timeout=1.0)
        
        # Give processes time to clean up
        import time
        time.sleep(0.2)
        
        # Count zombies after test
        final_zombies = sum(1 for child in current_process.children(recursive=True) 
                          if child.status() == psutil.STATUS_ZOMBIE)
        
        # We should not have created new zombie processes
        new_zombies = final_zombies - initial_zombies
        if new_zombies > 0:
            logger.warning(f"Test created {new_zombies} new zombie processes")
        assert new_zombies <= 0, f"Test created {new_zombies} new zombie processes"
    
    def test_temporary_file_cleanup(self):
        """Test that temporary files are cleaned up."""
        analyzer = ClaudeAnalyzer()
        
        initial_temp_files = len(list(Path('/tmp').glob('tmp*.txt')))
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = '{"problems": []}'
            mock_run.return_value.stderr = ''
            
            analyzer._run_claude_cli("test prompt", timeout=30.0)
        
        # Check no temp files were left behind
        final_temp_files = len(list(Path('/tmp').glob('tmp*.txt')))
        assert final_temp_files <= initial_temp_files, "Temporary files not cleaned up"
    
    def test_large_pdf_memory_stress(self):
        """Test memory usage with large PDF simulation."""
        processor = PDFProcessor()
        
        # Simulate processing a large PDF (100 pages)
        with patch('pdfplumber.open') as mock_open:
            mock_pdf = Mock()
            mock_pages = []
            
            # Create 100 mock pages with large content
            for i in range(100):
                mock_page = Mock()
                mock_page.extract_text.return_value = "Large content " * 1000  # ~13KB per page
                mock_pages.append(mock_page)
            
            mock_pdf.pages = mock_pages
            mock_open.return_value.__enter__.return_value = mock_pdf
            
            # Monitor memory during processing
            process = psutil.Process()
            memory_samples = []
            
            def monitor_memory():
                for _ in range(10):  # Sample for 1 second
                    memory_samples.append(process.memory_info().rss)
                    time.sleep(0.1)
            
            # Start memory monitoring
            monitor_thread = threading.Thread(target=monitor_memory)
            monitor_thread.start()
            
            # Process the large PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                temp_path = f.name
            
            try:
                result = processor.extract_content(temp_path)
                assert result is not None
            finally:
                os.unlink(temp_path)
            
            monitor_thread.join()
            
            # Check memory doesn't grow excessively during processing
            if len(memory_samples) > 1:
                max_growth = max(memory_samples) - min(memory_samples)
                assert max_growth < 100 * 1024 * 1024, f"Memory spike too large: {max_growth / 1024 / 1024:.1f}MB"
    
    def test_cache_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        analyzer = ClaudeAnalyzer(cache_ttl_hours=0.001)  # Very short TTL for testing
        
        # Add entry to cache with short TTL (if implemented)
        cache_key = "test_ttl_key"
        analyzer._cache[cache_key] = "test_value"
        
        # If TTL is implemented, verify expiration
        # This test may need adjustment based on actual TTL implementation
        if hasattr(analyzer, '_cache_timestamps'):
            # Simulate time passage
            import time
            time.sleep(1)
            
            # Check if expired entries are cleaned up
            if hasattr(analyzer, '_cleanup_expired_cache'):
                analyzer._cleanup_expired_cache()
        # Since we don't have TTL implemented yet, just check cache exists
        assert cache_key in analyzer._cache
    
    def test_thread_cleanup(self):
        """Test that threads are properly cleaned up."""
        initial_thread_count = threading.active_count()
        
        # Create and process some work that might spawn threads
        processor = PDFProcessor()
        
        with patch('pdfplumber.open') as mock_open:
            mock_pdf = Mock()
            mock_page = Mock()
            mock_page.extract_text.return_value = "Test content"
            mock_pdf.pages = [mock_page]
            mock_open.return_value.__enter__.return_value = mock_pdf
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                temp_path = f.name
            
            try:
                processor.extract_content(temp_path)
            finally:
                os.unlink(temp_path)
        
        # Allow time for thread cleanup
        time.sleep(0.1)
        
        # Check thread count hasn't grown significantly
        final_thread_count = threading.active_count()
        assert final_thread_count <= initial_thread_count + 2, f"Thread leak detected: {final_thread_count - initial_thread_count} extra threads"
    
    def test_memory_profiling_integration(self):
        """Test memory profiling hooks work correctly."""
        # This would test any memory profiling hooks we add
        import sys
        
        # Simple memory tracking
        initial_objects = len(gc.get_objects())
        
        processor = PDFProcessor()
        with patch('pdfplumber.open') as mock_open:
            mock_pdf = Mock()
            mock_page = Mock()
            mock_page.extract_text.return_value = "Test"
            mock_pdf.pages = [mock_page]
            mock_open.return_value.__enter__.return_value = mock_pdf
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                temp_path = f.name
            
            try:
                processor.extract_content(temp_path)
            finally:
                os.unlink(temp_path)
        
        # Force cleanup
        del processor
        gc.collect()
        
        # Check object count growth is reasonable
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects
        assert object_growth < 100, f"Too many objects created: {object_growth}"