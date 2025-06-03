"""Integration between GUI and file watcher system."""
import os
import logging
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from src.core.enhanced_file_watcher import EnhancedFileWatcher
from src.core.queue_processor import QueueProcessor
from src.core.problem_monitor import ProblemMonitor
from src.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class FileWatcherThread(QThread):
    """Thread to run file watcher without blocking GUI."""
    
    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str)
    
    def __init__(self, watcher: EnhancedFileWatcher):
        super().__init__()
        self.watcher = watcher
        self._running = False
        
    def run(self):
        """Run the file watcher."""
        self._running = True
        logger.info("File watcher thread started")
        
        try:
            # Start watching
            self.watcher.start()
            self.status_update.emit("File watcher active")
            
            # Keep thread alive while watcher runs
            while self._running and self.watcher.is_running:
                self.msleep(100)  # Check every 100ms
                
        except Exception as e:
            logger.error(f"File watcher error: {e}")
            self.error_occurred.emit(str(e))
        finally:
            logger.info("File watcher thread stopped")
            
    def stop(self):
        """Stop the file watcher."""
        self._running = False
        if self.watcher:
            self.watcher.stop()


class FileWatcherIntegration(QObject):
    """Manages integration between GUI and file watching system.
    
    This class:
    - Starts/stops file watcher in separate thread
    - Manages queue processor
    - Monitors for completed analyses
    - Provides pause/resume for ADHD breaks
    """
    
    # Signals
    new_problem_ready = pyqtSignal(dict)
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    queue_size_changed = pyqtSignal(int)
    
    def __init__(self, inbox_dir: str = "inbox", db_manager: Optional[DatabaseManager] = None):
        """Initialize file watcher integration.
        
        Args:
            inbox_dir: Directory to watch for PDFs
            db_manager: Database manager instance
        """
        super().__init__()
        
        self.inbox_dir = Path(inbox_dir)
        self.db_manager = db_manager or DatabaseManager()
        
        # Create inbox directory if needed
        self.inbox_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.file_watcher = EnhancedFileWatcher(
            watch_dir=str(self.inbox_dir),
            db_manager=self.db_manager
        )
        
        self.queue_processor = QueueProcessor(
            db_manager=self.db_manager,
            num_workers=2  # ADHD-friendly: not too many parallel tasks
        )
        
        self.problem_monitor = ProblemMonitor()
        
        # Connect signals
        self.problem_monitor.new_problem_ready.connect(self.new_problem_ready)
        self.problem_monitor.error_occurred.connect(self.error_occurred)
        
        # Thread for file watcher
        self.watcher_thread = None
        self._is_paused = False
        
    def start(self):
        """Start file watching and processing."""
        logger.info("Starting file watcher integration")
        
        try:
            # Start queue processor
            self.queue_processor.start()
            self.status_changed.emit("Queue processor started")
            
            # Start file watcher in thread
            self.watcher_thread = FileWatcherThread(self.file_watcher)
            self.watcher_thread.error_occurred.connect(self._handle_watcher_error)
            self.watcher_thread.status_update.connect(self.status_changed)
            self.watcher_thread.start()
            
            # Start problem monitor
            self.problem_monitor.start_monitoring()
            self.status_changed.emit("File watcher integration active")
            
            # Initial queue size
            self._update_queue_size()
            
        except Exception as e:
            logger.error(f"Failed to start file watcher integration: {e}")
            self.error_occurred.emit(f"Startup error: {str(e)}")
            
    def stop(self):
        """Stop all components."""
        logger.info("Stopping file watcher integration")
        
        # Stop problem monitor
        self.problem_monitor.stop_monitoring()
        
        # Stop file watcher thread
        if self.watcher_thread and self.watcher_thread.isRunning():
            self.watcher_thread.stop()
            self.watcher_thread.wait(5000)  # Wait up to 5 seconds
            
        # Stop queue processor
        self.queue_processor.stop()
        
        self.status_changed.emit("File watcher integration stopped")
        
    def pause_processing(self):
        """Pause processing for ADHD break."""
        if not self._is_paused:
            logger.info("Pausing file processing")
            self.queue_processor.pause()
            self._is_paused = True
            self.status_changed.emit("Processing paused for break")
            
    def resume_processing(self):
        """Resume processing after break."""
        if self._is_paused:
            logger.info("Resuming file processing")
            self.queue_processor.resume()
            self._is_paused = False
            self.status_changed.emit("Processing resumed")
            
    def is_paused(self) -> bool:
        """Check if processing is paused."""
        return self._is_paused
        
    def get_queue_size(self) -> int:
        """Get number of items in processing queue."""
        try:
            from src.core.processing_queue import ProcessingQueue
            with ProcessingQueue(self.db_manager) as queue:
                return queue.get_pending_count()
        except Exception as e:
            logger.error(f"Error getting queue size: {e}")
            return 0
            
    def _update_queue_size(self):
        """Update queue size signal."""
        size = self.get_queue_size()
        self.queue_size_changed.emit(size)
        
    def _handle_watcher_error(self, error_msg: str):
        """Handle file watcher errors."""
        logger.error(f"File watcher error: {error_msg}")
        self.error_occurred.emit(f"File watcher: {error_msg}")
        
    def show_inbox_hint(self):
        """Show helpful hint about using the inbox."""
        return (
            "📁 Drop PDF files in the 'inbox' folder!\n\n"
            "FocusQuest will automatically:\n"
            "• Extract math problems\n"
            "• Analyze with Claude AI\n"
            "• Present them one at a time\n\n"
            f"Inbox location: {self.inbox_dir.absolute()}"
        )