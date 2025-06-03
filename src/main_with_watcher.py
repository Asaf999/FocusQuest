"""
FocusQuest with File Watcher Integration
Enhanced main application with automatic PDF processing
"""
import sys
import gc
import logging
import signal
import atexit
import json
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon

from src.ui.main_window import FocusQuestWindow
from src.ui.session_manager import SessionManager
from src.ui.notification_manager import NotificationManager
from src.ui.file_watcher_integration import FileWatcherIntegration
from src.database.db_manager import DatabaseManager
from src.database.models import Problem, UserProgress, ProblemAttempt, SkippedProblem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProblemQueue:
    """Manages queue of problems from both database and file watcher"""
    
    def __init__(self):
        self.db_problems = []  # Problems from database
        self.watcher_problems = []  # Problems from file watcher
        self.current_source = 'mixed'  # 'db', 'watcher', or 'mixed'
        
    def add_watcher_problem(self, problem_data: dict):
        """Add problem from file watcher"""
        # Avoid duplicates
        if not any(p.get('session_id') == problem_data.get('session_id') 
                  for p in self.watcher_problems):
            self.watcher_problems.append(problem_data)
            logger.info(f"Added watcher problem: {problem_data.get('session_id')}")
            
    def add_db_problem(self, problem_data: dict):
        """Add problem from database"""
        self.db_problems.append(problem_data)
        
    def get_next_problem(self) -> dict:
        """Get next problem based on strategy"""
        # Prefer watcher problems (they're fresh!)
        if self.watcher_problems:
            return self.watcher_problems.pop(0)
        elif self.db_problems:
            return self.db_problems.pop(0)
        return None
        
    def has_problems(self) -> bool:
        """Check if any problems available"""
        return bool(self.watcher_problems or self.db_problems)
        
    def get_counts(self) -> dict:
        """Get problem counts by source"""
        return {
            'watcher': len(self.watcher_problems),
            'database': len(self.db_problems),
            'total': len(self.watcher_problems) + len(self.db_problems)
        }


class FocusQuestAppWithWatcher:
    """Main application with file watcher integration"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("FocusQuest")
        self.app.setOrganizationName("FocusQuest")
        
        # State management
        self.state_file = Path("data") / "app_state.json"
        self.running = True
        self.current_problem_id = None
        self.problem_queue = ProblemQueue()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self._cleanup)
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.session_manager = SessionManager()
        self.main_window = FocusQuestWindow()
        self.notification_manager = NotificationManager()
        
        # Initialize file watcher integration
        self.file_watcher_integration = FileWatcherIntegration()
        
        # Override window close event
        self.main_window.closeEvent = self._on_window_close
        
        # Setup timers
        self.setup_timers()
        
        # Check for crash recovery
        self._check_crash_recovery()
        
        # Connect signals
        self.setup_connections()
        
        # Load user progress
        self.load_user_progress()
        
    def setup_timers(self):
        """Setup application timers"""
        # Autosave timer
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self._save_state)
        self.autosave_timer.start(30000)  # Every 30 seconds
        
        # Memory cleanup timer
        self.memory_cleanup_timer = QTimer()
        self.memory_cleanup_timer.timeout.connect(self._periodic_memory_cleanup)
        self.memory_cleanup_timer.start(300000)  # Every 5 minutes
        
        # Queue status timer (for debugging/monitoring)
        self.queue_status_timer = QTimer()
        self.queue_status_timer.timeout.connect(self._log_queue_status)
        self.queue_status_timer.start(60000)  # Every minute
        
    def setup_connections(self):
        """Setup all signal connections"""
        # Original connections (kept for compatibility)
        self.main_window.problem_completed.connect(self.on_problem_completed)
        self.main_window.problem_skipped.connect(self.on_problem_skipped)
        self.main_window.session_paused.connect(self.on_session_paused)
        self.session_manager.break_suggested.connect(self.notification_manager.show_break_suggestion)
        
        # File watcher connections
        self.file_watcher_integration.new_problem_ready.connect(self.on_watcher_problem_ready)
        self.file_watcher_integration.watcher_status_changed.connect(self.on_watcher_status_changed)
        self.file_watcher_integration.watcher_error.connect(self.on_watcher_error)
        
        # Panic mode integration
        self.main_window.panic_mode_started.connect(self.on_panic_mode_started)
        self.main_window.panic_mode_ended.connect(self.on_panic_mode_ended)
        
        # XP updates
        self.main_window.xp_widget.level_up.connect(self.on_level_up)
        
    def load_user_progress(self):
        """Load user progress from database"""
        try:
            with self.db_manager.session_scope() as session:
                user = session.query(UserProgress).first()
                if user:
                    self.main_window.update_user_progress(
                        user.total_xp,
                        user.current_level,
                        user.current_streak
                    )
        except Exception as e:
            logger.error(f"Error loading user progress: {e}")
            
    def start(self):
        """Start the application with file watcher"""
        # Start session
        self.session_manager.start_session()
        
        # Start file watcher integration
        self.file_watcher_integration.start()
        
        # Show status in window title
        self._update_window_title()
        
        # Load initial problems
        self._load_initial_problems()
        
        # Show main window
        self.main_window.show()
        
        # Show welcome message
        self._show_welcome_message()
        
        # Start file watching after a short delay
        QTimer.singleShot(2000, self.file_watcher_integration.start_file_watching)
        
        # Start event loop
        return self.app.exec()
        
    def _show_welcome_message(self):
        """Show ADHD-friendly welcome message"""
        QMessageBox.information(
            self.main_window,
            "Welcome to FocusQuest!",
            "📚 Drop PDF files in the 'inbox' folder for automatic processing\n"
            "🎯 Problems will appear here when ready\n"
            "💡 Use Space for hints, S to skip\n"
            "🧠 Press Ctrl+P anytime for panic mode\n\n"
            "Let's learn together! 🚀"
        )
        
    def _load_initial_problems(self):
        """Load problems from both sources"""
        # Check for existing problems from file watcher
        if self.file_watcher_integration.problem_monitor:
            watcher_problems = self.file_watcher_integration.problem_monitor.get_available_problems()
            for problem in watcher_problems[:5]:  # Limit initial load
                self.problem_queue.add_watcher_problem(problem)
                
        # Load next problem
        self.load_next_problem()
        
    def load_next_problem(self):
        """Load next problem from queue"""
        problem = self.problem_queue.get_next_problem()
        
        if problem:
            if problem.get('is_from_file_watcher'):
                logger.info(f"Loading problem from file watcher: {problem.get('session_id')}")
            else:
                logger.info(f"Loading problem from database: {problem.get('id')}")
                
            self.current_problem_id = problem.get('id') or problem.get('session_id')
            self.main_window.load_problem(problem)
            self._update_window_title()
        else:
            # No problems available
            logger.info("No problems available, waiting for new PDFs...")
            QMessageBox.information(
                self.main_window,
                "No Problems Available",
                "Drop a PDF in the 'inbox' folder to get started!\n\n"
                "The app will automatically process it and load problems."
            )
            
    def on_watcher_problem_ready(self, problem_data: dict):
        """Handle new problem from file watcher"""
        logger.info(f"New problem from watcher: {problem_data.get('session_id')}")
        
        # Add to queue
        self.problem_queue.add_watcher_problem(problem_data)
        
        # If no current problem, load it immediately
        if not self.current_problem_id:
            self.load_next_problem()
        else:
            # Notify user that new problem is available
            self.notification_manager.show_info(
                "New Problem Available",
                f"A new problem from {problem_data.get('source', 'PDF')} is ready!"
            )
            
        self._update_window_title()
        
    def on_watcher_status_changed(self, status: str):
        """Handle file watcher status changes"""
        logger.info(f"File watcher status: {status}")
        # Could show in status bar if we had one
        
    def on_watcher_error(self, error_msg: str):
        """Handle file watcher errors"""
        logger.error(f"File watcher error: {error_msg}")
        self.notification_manager.show_error("File Watcher Error", error_msg)
        
    def on_session_paused(self):
        """Handle session pause"""
        self.session_manager.pause_session()
        # Also pause file processing
        self.file_watcher_integration.pause_processing()
        
    def on_panic_mode_started(self):
        """Handle panic mode start"""
        self.notification_manager.set_panic_mode(True)
        # Pause file processing during panic
        self.file_watcher_integration.pause_processing()
        
    def on_panic_mode_ended(self):
        """Handle panic mode end"""
        self.notification_manager.set_panic_mode(False)
        # Resume file processing
        self.file_watcher_integration.resume_processing()
        
    def on_problem_completed(self, problem_id: int):
        """Handle problem completion"""
        try:
            # Mark in file watcher if it's from there
            if isinstance(problem_id, str) and problem_id.startswith('20'):  # Session IDs start with date
                self.file_watcher_integration.problem_monitor.mark_problem_completed(problem_id)
                
            # Original completion logic
            with self.db_manager.session_scope() as session:
                # Only update if it's a DB problem
                if isinstance(problem_id, int):
                    problem = session.query(Problem).filter_by(id=problem_id).first()
                    if problem:
                        problem.completed = True
                        
                # Update user progress
                user = session.query(UserProgress).first()
                if user:
                    user.problems_solved += 1
                    
                session.commit()
                
            # Record in session
            self.session_manager.record_problem_completed()
            
            # Load next problem after delay
            QTimer.singleShot(2000, self.load_next_problem)
            
        except Exception as e:
            logger.error(f"Error completing problem: {e}")
            
    def on_problem_skipped(self, problem_id: int):
        """Handle problem skip"""
        logger.info(f"Problem {problem_id} skipped")
        
        # Record skip
        self.session_manager.record_problem_skipped()
        
        # Load next problem
        QTimer.singleShot(1000, self.load_next_problem)
        
    def on_level_up(self, new_level: int):
        """Handle level up"""
        QMessageBox.information(
            self.main_window,
            "Level Up!",
            f"Congratulations! You've reached Level {new_level}!\n\n"
            f"Keep up the great work! 🎉"
        )
        
    def _update_window_title(self):
        """Update window title with queue status"""
        counts = self.problem_queue.get_counts()
        watcher_status = "✓" if self.file_watcher_integration.is_running() else "✗"
        
        title = f"FocusQuest - {counts['total']} problems queued | File Watcher {watcher_status}"
        self.main_window.setWindowTitle(title)
        
    def _log_queue_status(self):
        """Log queue processing status"""
        queue_status = self.file_watcher_integration.get_queue_status()
        problem_counts = self.problem_queue.get_counts()
        
        logger.info(
            f"Queue Status - "
            f"Processing: {queue_status.get('processing', 0)}, "
            f"Pending: {queue_status.get('pending', 0)}, "
            f"Problems Ready: {problem_counts['total']}"
        )
        
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        
    def _on_window_close(self, event):
        """Handle window close"""
        logger.info("Window closing...")
        self._save_state()
        self.session_manager.end_session()
        self.file_watcher_integration.stop()
        event.accept()
        
    def _save_state(self):
        """Save application state"""
        if not self.running:
            return
            
        try:
            state = {
                'timestamp': datetime.now().isoformat(),
                'current_problem_id': self.current_problem_id,
                'problem_queue': {
                    'watcher_count': len(self.problem_queue.watcher_problems),
                    'db_count': len(self.problem_queue.db_problems)
                },
                'file_watcher_running': self.file_watcher_integration.is_running(),
                'window_geometry': {
                    'x': self.main_window.x(),
                    'y': self.main_window.y(),
                    'width': self.main_window.width(),
                    'height': self.main_window.height()
                }
            }
            
            # Write atomically
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2)
            temp_file.replace(self.state_file)
            
        except Exception as e:
            logger.error(f"Error saving state: {e}")
            
    def _check_crash_recovery(self):
        """Check for crash recovery"""
        # Similar to original but simpler
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    
                # Check if recent
                timestamp = datetime.fromisoformat(state['timestamp'])
                if (datetime.now() - timestamp).total_seconds() < 3600:
                    logger.info("Recovered from previous session")
                    # Could restore state here
                    
            except Exception as e:
                logger.error(f"Error in crash recovery: {e}")
                
    def _periodic_memory_cleanup(self):
        """Periodic memory cleanup"""
        try:
            collected = gc.collect()
            logger.debug(f"Memory cleanup: collected {collected} objects")
        except Exception as e:
            logger.error(f"Error in memory cleanup: {e}")
            
    def _cleanup(self):
        """Cleanup on exit"""
        logger.info("Cleaning up...")
        self.running = False
        
        # Stop timers
        for timer in [self.autosave_timer, self.memory_cleanup_timer, self.queue_status_timer]:
            if hasattr(self, timer.__name__):
                timer.stop()
                
        # Stop file watcher
        self.file_watcher_integration.stop()
        
        # Save state
        self._save_state()
        
        # End session
        if hasattr(self, 'session_manager'):
            try:
                self.session_manager.end_session()
            except:
                pass
                
        # Close database
        if hasattr(self, 'db_manager'):
            try:
                self.db_manager.close()
            except:
                pass
                
        # Remove state file
        if self.state_file.exists():
            try:
                self.state_file.unlink()
            except:
                pass
                
    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down...")
        self._cleanup()
        if hasattr(self, 'app'):
            self.app.quit()


def main():
    """Main entry point"""
    # Ensure directories exist
    for dir_path in ['data', 'inbox', 'processed', 'analysis_sessions']:
        Path(dir_path).mkdir(exist_ok=True)
        
    try:
        app = FocusQuestAppWithWatcher()
        return app.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")
        return 0
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())