"""
Queue processor for concurrent PDF processing with retry logic
"""
import time
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Optional
from pathlib import Path

from src.core.processing_queue import ProcessingQueue, QueueItem
from src.analysis.pdf_processor import PDFProcessor
from src.analysis.claude_directory_analyzer import ClaudeDirectoryAnalyzer

logger = logging.getLogger(__name__)


class QueueProcessor:
    """Processes queued PDFs concurrently with thread pool"""
    
    def __init__(
        self,
        db_path: str = None,
        max_workers: int = 3,
        poll_interval: float = 5.0,
        stale_timeout_minutes: int = 30
    ):
        self.queue = ProcessingQueue(db_path=db_path)
        self.max_workers = max_workers
        self.poll_interval = poll_interval
        self.stale_timeout_minutes = stale_timeout_minutes
        
        self.executor: Optional[ThreadPoolExecutor] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False
        
        # Statistics
        self._stats_lock = threading.Lock()
        self._stats = {
            'total_processed': 0,
            'success_count': 0,
            'failure_count': 0,
            'total_processing_time': 0.0
        }
        
        # Initialize processors (will be set during init)
        self._pdf_processor = None
        self._claude_analyzer = None
        
    def start(self):
        """Start the queue processor"""
        if self.is_running:
            logger.warning("Queue processor already running")
            return
            
        logger.info("Starting queue processor")
        
        # Initialize processors if not already done
        if self._pdf_processor is None:
            self._pdf_processor = PDFProcessor()
        if self._claude_analyzer is None:
            self._claude_analyzer = ClaudeDirectoryAnalyzer()
        
        # Recover any stale items
        recovered = self.queue.recover_stale_items(self.stale_timeout_minutes)
        if recovered > 0:
            logger.info(f"Recovered {recovered} stale items")
            
        self.stop_event.clear()
        self.is_running = True
        
        # Start thread pool
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Start monitor thread
        self.monitor_thread = threading.Thread(target=self._monitor_queue, daemon=True)
        self.monitor_thread.start()
        
        logger.info(f"Queue processor started with {self.max_workers} workers")
        
    def stop(self, timeout: float = 30.0):
        """Stop the queue processor gracefully"""
        if not self.is_running:
            return
            
        logger.info("Stopping queue processor")
        
        # Signal stop
        self.stop_event.set()
        self.is_running = False
        
        # Wait for monitor thread
        if self.monitor_thread:
            self.monitor_thread.join(timeout=timeout)
            
        # Shutdown executor
        if self.executor:
            self.executor.shutdown(wait=True)
            
        logger.info("Queue processor stopped")
        
    def _monitor_queue(self):
        """Monitor queue for new items"""
        active_futures: Dict[Future, QueueItem] = {}
        
        while not self.stop_event.is_set():
            try:
                # Check for completed futures
                completed_futures = [f for f in active_futures if f.done()]
                for future in completed_futures:
                    self._handle_future_completion(future, active_futures[future])
                    del active_futures[future]
                    
                # Submit new items if capacity available
                while len(active_futures) < self.max_workers:
                    item = self.queue.get_next_item()
                    if not item:
                        break
                        
                    logger.info(f"Processing {item.pdf_path} (priority: {item.priority})")
                    future = self.executor.submit(self._process_item, item)
                    active_futures[future] = item
                    
            except Exception as e:
                logger.error(f"Monitor thread error: {e}")
                
            # Sleep before next check
            self.stop_event.wait(timeout=self.poll_interval)
            
    def _process_next_item(self):
        """Process next item from queue (for testing)"""
        item = self.queue.get_next_item()
        if item:
            self._process_item(item)
            
    @property
    def pdf_processor(self):
        """Get PDF processor (for testing)"""
        return self._pdf_processor
        
    @pdf_processor.setter
    def pdf_processor(self, value):
        """Set PDF processor (for testing)"""
        self._pdf_processor = value
        
    @property
    def claude_analyzer(self):
        """Get Claude analyzer (for testing)"""
        return self._claude_analyzer
        
    @claude_analyzer.setter
    def claude_analyzer(self, value):
        """Set Claude analyzer (for testing)"""
        self._claude_analyzer = value
        
    def _process_item(self, item: QueueItem):
        """Process a single queue item"""
        start_time = time.time()
        
        try:
            # Extract content from PDF
            logger.info(f"Extracting content from {item.pdf_path}")
            result = self._pdf_processor.process_pdf(item.pdf_path)
            
            if not result or 'error' in result:
                raise Exception(f"PDF processing failed: {result.get('error', 'Unknown error')}")
                
            problems = result.get('problems', [])
            
            if not problems:
                logger.warning(f"No problems found in {item.pdf_path}")
                self.queue.mark_completed(item.id)
                self._update_stats(success=True, processing_time=time.time() - start_time)
                return
                
            # Submit each problem for analysis
            session_ids = []
            for i, problem in enumerate(problems):
                metadata = {
                    'source': Path(item.pdf_path).name,
                    'queue_item_id': item.id,
                    'problem_index': i,
                    'priority': item.priority.name,
                    **problem.get('metadata', {})
                }
                
                problem_text = problem.get('hebrew_text', '')
                if problem.get('english_translation'):
                    problem_text += f"\n\nTranslation: {problem['english_translation']}"
                if problem.get('formulas'):
                    problem_text += f"\n\nFormulas: {', '.join(problem['formulas'])}"
                    
                session_id = self._claude_analyzer.analyze_problem_async(problem_text, metadata)
                session_ids.append(session_id)
                
            logger.info(f"Submitted {len(problems)} problems from {item.pdf_path}")
            
            # Mark as completed
            self.queue.mark_completed(item.id)
            self._update_stats(success=True, processing_time=time.time() - start_time)
            
        except Exception as e:
            logger.error(f"Error processing {item.pdf_path}: {e}")
            self.queue.mark_failed(item.id, str(e))
            self._update_stats(success=False, processing_time=time.time() - start_time)
            
            # Check if retry is possible
            if item.attempts < ProcessingQueue.MAX_RETRIES:
                logger.info(f"Will retry {item.pdf_path} (attempt {item.attempts + 1}/{ProcessingQueue.MAX_RETRIES})")
                self.queue.mark_for_retry(item.id)
                
    def _handle_future_completion(self, future: Future, item: QueueItem):
        """Handle completion of a processing future"""
        try:
            # Future result is None (processing handled in _process_item)
            future.result()
        except Exception as e:
            logger.error(f"Unexpected error in future for {item.pdf_path}: {e}")
            
    def _update_stats(self, success: bool, processing_time: float):
        """Update processing statistics"""
        with self._stats_lock:
            self._stats['total_processed'] += 1
            if success:
                self._stats['success_count'] += 1
            else:
                self._stats['failure_count'] += 1
            self._stats['total_processing_time'] += processing_time
            
    def get_statistics(self) -> Dict:
        """Get processing statistics"""
        with self._stats_lock:
            stats = self._stats.copy()
            
        # Add queue stats
        queue_stats = self.queue.get_stats()
        stats.update(queue_stats)
        
        # Calculate average processing time
        if stats['total_processed'] > 0:
            stats['average_processing_time'] = stats['total_processing_time'] / stats['total_processed']
        else:
            stats['average_processing_time'] = 0.0
            
        return stats
        
    def add_pdf(self, pdf_path: str, priority=None) -> Optional[int]:
        """Add a PDF to the processing queue"""
        from src.core.processing_queue import Priority
        
        if priority is None:
            priority = Priority.NORMAL
            
        return self.queue.add_item(pdf_path, priority)