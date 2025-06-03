"""Enhanced main window with file watcher integration."""
import logging
from typing import Optional, List, Dict, Any
from collections import deque
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox

from src.ui.main_window import FocusQuestWindow
from src.ui.file_watcher_integration import FileWatcherIntegration
from src.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class FocusQuestIntegratedWindow(FocusQuestWindow):
    """Main window with integrated file watching and problem queue.
    
    This extends the base window with:
    - Automatic file watching for PDFs
    - Problem queue management
    - Live problem loading from analyses
    - ADHD-friendly status updates
    """
    
    # Additional signals
    queue_status_changed = pyqtSignal(int)  # Queue size changed
    
    def __init__(self):
        """Initialize integrated window."""
        super().__init__()
        
        # Initialize database
        self.db_manager = DatabaseManager()
        
        # Problem queue (from both DB and file watcher)
        self.problem_queue = deque(maxlen=100)  # Limit to prevent memory issues
        
        # File watcher integration
        self.file_watcher = FileWatcherIntegration(db_manager=self.db_manager)
        
        # Connect file watcher signals
        self.file_watcher.new_problem_ready.connect(self._on_new_problem_from_file)
        self.file_watcher.status_changed.connect(self._on_watcher_status_changed)
        self.file_watcher.error_occurred.connect(self._on_watcher_error)
        self.file_watcher.queue_size_changed.connect(self._update_queue_display)
        
        # Connect existing signals
        self.problem_completed.connect(self._load_next_from_queue)
        self.problem_skipped.connect(self._load_next_from_queue)
        
        # Start file watcher
        self.file_watcher.start()
        
        # Show inbox hint on first run
        self._show_initial_hint()
        
        # Update window title with queue status
        self._update_window_title()
        
        # Timer for periodic queue updates
        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self._check_queue_status)
        self.queue_timer.start(5000)  # Check every 5 seconds
        
    def _show_initial_hint(self):
        """Show helpful hint about inbox on startup."""
        hint = self.file_watcher.show_inbox_hint()
        QMessageBox.information(
            self,
            "Welcome to FocusQuest! 🎯",
            hint,
            QMessageBox.StandardButton.Ok
        )
        
    def _on_new_problem_from_file(self, problem_data: Dict[str, Any]):
        """Handle new problem from file watcher."""
        logger.info(f"New problem received from file watcher: {problem_data.get('id')}")
        
        # Add to queue with priority
        self.problem_queue.appendleft(problem_data)  # New problems go to front
        
        # Update display
        self._update_queue_display(len(self.problem_queue))
        
        # If no current problem, load immediately
        if not self.current_problem:
            self._load_next_from_queue()
        else:
            # Show notification if method exists
            if hasattr(self, 'show_notification'):
                self.show_notification(
                    "New Problem Ready! 📚",
                    "A new problem has been analyzed and added to your queue.",
                    duration=3000
                )
            
    def _load_next_from_queue(self, *args):
        """Load next problem from queue."""
        if not self.problem_queue:
            # Try to load from database
            self._load_problem_from_database()
            return
            
        # Get next problem
        problem_data = self.problem_queue.popleft()
        
        # Format for display
        formatted_problem = self._format_problem_for_display(problem_data)
        
        # Load into UI
        self.load_problem(formatted_problem)
        
        # Update queue display
        self._update_queue_display(len(self.problem_queue))
        
    def _format_problem_for_display(self, problem_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format problem data for the problem widget."""
        # Extract relevant fields based on source
        if problem_data.get('source') == 'file_watcher':
            # From Claude analysis
            return {
                'id': problem_data.get('id', 'unknown'),
                'original_text': problem_data.get('problem_text', ''),
                'translated_text': problem_data.get('translated_text', ''),
                'steps': problem_data.get('steps', []),
                'hints': problem_data.get('hints', {}),
                'difficulty': problem_data.get('difficulty_rating', 3),
                'source': 'file_watcher'
            }
        else:
            # From database
            return problem_data
            
    def _load_problem_from_database(self):
        """Load a problem from database when queue is empty."""
        try:
            with self.db_manager.session_scope() as session:
                # Get uncompleted problems
                from src.database.models import Problem
                problem = session.query(Problem).filter_by(
                    is_completed=False
                ).first()
                
                if problem:
                    problem_data = {
                        'id': problem.id,
                        'original_text': problem.original_text,
                        'translated_text': problem.translated_text,
                        'difficulty': problem.difficulty,
                        'source': 'database'
                    }
                    self.load_problem(problem_data)
                else:
                    # No problems available
                    self.show_notification(
                        "No Problems Available",
                        "Drop a PDF in the inbox folder to add new problems!",
                        duration=5000
                    )
        except Exception as e:
            logger.error(f"Error loading from database: {e}")
            
    def _update_queue_display(self, queue_size: int):
        """Update UI elements showing queue status."""
        self.queue_status_changed.emit(queue_size)
        self._update_window_title()
        
    def _update_window_title(self):
        """Update window title with queue status."""
        queue_size = len(self.problem_queue)
        processing_size = self.file_watcher.get_queue_size()
        
        if queue_size > 0:
            self.setWindowTitle(f"FocusQuest - {queue_size} problems ready")
        elif processing_size > 0:
            self.setWindowTitle(f"FocusQuest - Processing {processing_size} files...")
        else:
            self.setWindowTitle("FocusQuest - Drop PDFs in inbox folder")
            
    def _on_watcher_status_changed(self, status: str):
        """Handle file watcher status changes."""
        logger.info(f"File watcher status: {status}")
        
    def _on_watcher_error(self, error_msg: str):
        """Handle file watcher errors."""
        logger.error(f"File watcher error: {error_msg}")
        if hasattr(self, 'show_notification'):
            self.show_notification(
                "File Watcher Issue",
                f"There was an issue with file monitoring: {error_msg}",
                duration=5000
            )
        else:
            # Fallback to message box
            QMessageBox.warning(self, "File Watcher Issue", 
                              f"There was an issue with file monitoring: {error_msg}")
        
    def _check_queue_status(self):
        """Periodic check of queue status."""
        # Update queue size display
        self.file_watcher._update_queue_size()
        
        # Check if we need to pause for break
        if hasattr(self, 'session_manager') and self.session_manager.needs_break():
            if not self.file_watcher.is_paused():
                self.file_watcher.pause_processing()
                
    def enter_panic_mode(self):
        """Pause file processing during panic mode."""
        # Set panic mode flag
        self.panic_mode_active = True
        
        # Pause file processing
        if hasattr(self, 'file_watcher'):
            self.file_watcher.pause_processing()
            
        # Call parent method if it exists
        if hasattr(super(), 'enter_panic_mode'):
            super().enter_panic_mode()
            
    def exit_panic_mode(self):
        """Resume file processing after panic mode."""
        # Clear panic mode flag
        self.panic_mode_active = False
        
        # Resume file processing
        if hasattr(self, 'file_watcher'):
            self.file_watcher.resume_processing()
            
        # Call parent method if it exists
        if hasattr(super(), 'exit_panic_mode'):
            super().exit_panic_mode()
            
    def closeEvent(self, event):
        """Clean shutdown of file watcher."""
        # Stop file watcher
        if hasattr(self, 'file_watcher'):
            self.file_watcher.stop()
            
        # Stop queue timer
        if hasattr(self, 'queue_timer'):
            self.queue_timer.stop()
            
        # Call parent
        super().closeEvent(event)