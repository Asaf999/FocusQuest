"""
FocusQuest - ADHD-optimized mathematics learning RPG
Main application entry point
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
from src.database.db_manager import DatabaseManager
from src.database.models import Problem, UserProgress

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProblemLoader(QThread):
    """Background thread for loading problems"""
    
    problem_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        
    def run(self):
        """Load next problem from database"""
        try:
            # Get next unsolved problem
            with self.db_manager.session_scope() as session:
                problem = session.query(Problem).filter(
                    Problem.completed == False
                ).order_by(Problem.difficulty).first()
                
                if problem:
                    # Convert to dict for GUI
                    problem_data = {
                        'id': problem.id,
                        'original_text': problem.original_text,
                        'translated_text': problem.translated_text,
                        'steps': [
                            {
                                'content': step.content,
                                'duration': step.duration_minutes
                            }
                            for step in problem.steps
                        ],
                        'hints': [
                            {
                                'level': hint.level,
                                'content': hint.content
                            }
                            for hint in problem.hints
                        ]
                    }
                    self.problem_loaded.emit(problem_data)
                else:
                    self.error_occurred.emit("No more problems available!")
                    
        except Exception as e:
            logger.error(f"Error loading problem: {e}")
            self.error_occurred.emit(str(e))


class FocusQuestApp:
    """Main application controller with crash recovery"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("FocusQuest")
        self.app.setOrganizationName("FocusQuest")
        
        # State management
        self.state_file = Path("data") / "app_state.json"
        self.running = True
        self.current_problem_id = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self._cleanup)
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.session_manager = SessionManager()
        self.main_window = FocusQuestWindow()
        self.problem_loader = ProblemLoader(self.db_manager)
        self.notification_manager = NotificationManager()
        
        # Override window close event
        self.main_window.closeEvent = self._on_window_close
        
        # Setup autosave timer
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self._save_state)
        self.autosave_timer.start(30000)  # Save every 30 seconds
        
        # Setup memory cleanup timer
        self.memory_cleanup_timer = QTimer()
        self.memory_cleanup_timer.timeout.connect(self._periodic_memory_cleanup)
        self.memory_cleanup_timer.start(300000)  # Clean up every 5 minutes
        
        # Check for crash recovery
        self._check_crash_recovery()
        
        # Connect signals
        self.setup_connections()
        
        # Load user progress
        self.load_user_progress()
        
    def setup_connections(self):
        """Setup signal connections"""
        # Problem loading
        self.problem_loader.problem_loaded.connect(self.on_problem_loaded)
        self.problem_loader.error_occurred.connect(self.on_error)
        
        # Problem completion
        self.main_window.problem_completed.connect(self.on_problem_completed)
        
        # Session management
        self.main_window.session_paused.connect(self.session_manager.pause_session)
        self.session_manager.break_suggested.connect(self.notification_manager.show_break_suggestion)
        
        # Notification management
        self.notification_manager.break_taken.connect(self.on_break_taken)
        self.notification_manager.break_postponed.connect(self.on_break_postponed)
        self.notification_manager.achievement_unlocked.connect(self.on_achievement_unlocked)
        self.notification_manager.settings_requested.connect(self.on_notification_settings_requested)
        
        # Panic mode integration
        self.main_window.panic_mode_started.connect(lambda: self.notification_manager.set_panic_mode(True))
        self.main_window.panic_mode_ended.connect(lambda: self.notification_manager.set_panic_mode(False))
        
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
        """Start the application"""
        # Start session
        self.session_manager.start_session()
        
        # Load first problem
        self.load_next_problem()
        
        # Show main window
        self.main_window.show()
        
        # Start event loop
        return self.app.exec()
        
    def load_next_problem(self):
        """Load the next problem"""
        self.problem_loader.start()
        
    def on_problem_loaded(self, problem_data: dict):
        """Handle problem loaded"""
        self.current_problem_id = problem_data['id']
        self.main_window.load_problem(problem_data)
        self._save_state()  # Save state after loading problem
        
    def on_problem_completed(self, problem_id: int):
        """Handle problem completion"""
        try:
            with self.db_manager.session_scope() as session:
                # Mark problem as completed
                problem = session.query(Problem).filter_by(id=problem_id).first()
                if problem:
                    problem.completed = True
                    
                # Update user progress
                user = session.query(UserProgress).first()
                if user:
                    user.problems_solved += 1
                    # XP already updated via GUI
                    
                session.commit()
                
            # Record in session
            self.session_manager.record_problem_completed()
            
            # Load next problem after delay
            QThread.msleep(2000)
            self.load_next_problem()
            
        except Exception as e:
            logger.error(f"Error completing problem: {e}")
            self.on_error(str(e))
            
    def on_break_taken(self, duration_minutes: int):
        """Handle when user takes a break."""
        logger.info(f"User taking {duration_minutes} minute break")
        
        # Pause session
        self.session_manager.pause_session()
        
        # Auto-resume after break (with some buffer time)
        resume_delay = (duration_minutes + 1) * 60 * 1000  # +1 minute buffer, convert to ms
        QTimer.singleShot(resume_delay, self.session_manager.resume_session)
        
    def on_break_postponed(self, postpone_minutes: int):
        """Handle when user postpones break."""
        logger.info(f"Break postponed for {postpone_minutes} minutes")
        
        # Update notification manager with postponement
        # This could trigger a gentler reminder later
        
    def on_achievement_unlocked(self, achievement_name: str, xp_gained: int):
        """Handle achievement unlocks from break-taking."""
        logger.info(f"Achievement unlocked: {achievement_name} (+{xp_gained} XP)")
        
        # Update user progress in database
        try:
            with self.db_manager.session_scope() as session:
                user = session.query(UserProgress).first()
                if user:
                    user.total_xp += xp_gained
                    # Could also add achievement tracking here
                    session.commit()
                    
                    # Update UI
                    self.main_window.update_user_progress(
                        user.total_xp,
                        user.current_level,
                        user.current_streak
                    )
        except Exception as e:
            logger.error(f"Error updating achievement XP: {e}")
            
    def on_notification_settings_requested(self):
        """Handle notification settings request."""
        # This could open a settings dialog
        # For now, just log the request
        logger.info("Notification settings requested - placeholder for settings dialog")
            
    def on_level_up(self, new_level: int):
        """Handle level up event"""
        QMessageBox.information(
            self.main_window,
            "Level Up!",
            f"Congratulations! You've reached Level {new_level}!\n\n"
            f"Keep up the great work! 🎉"
        )
        
    def on_error(self, error_message: str):
        """Handle errors"""
        QMessageBox.critical(
            self.main_window,
            "Error",
            f"An error occurred:\n{error_message}"
        )
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown()
    
    def _on_window_close(self, event):
        """Handle window close event"""
        logger.info("Window close requested, saving state...")
        self._save_state()
        self.session_manager.end_session()
        event.accept()
    
    def _save_state(self):
        """Save current application state"""
        if not self.running:
            return
            
        try:
            state = {
                'timestamp': datetime.now().isoformat(),
                'session_id': getattr(self.session_manager, 'current_session_id', None),
                'current_problem_id': self.current_problem_id,
                'session_duration': self.session_manager.get_session_duration() if hasattr(self.session_manager, 'get_session_duration') else 0,
                'problems_completed': getattr(self.session_manager, 'problems_completed', 0),
                'window_geometry': {
                    'x': self.main_window.x(),
                    'y': self.main_window.y(),
                    'width': self.main_window.width(),
                    'height': self.main_window.height()
                },
                'ui_state': {
                    'focus_mode': getattr(self.main_window, 'focus_mode', False),
                    'current_step': self._get_current_step()
                }
            }
            
            # Write state atomically
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2)
            temp_file.replace(self.state_file)
            
            logger.debug("State saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def _get_current_step(self):
        """Get current problem step from UI"""
        try:
            if hasattr(self.main_window, 'problem_widget') and self.main_window.problem_widget:
                return getattr(self.main_window.problem_widget, 'current_step', 0)
        except:
            pass
        return 0
    
    def _check_crash_recovery(self):
        """Check for and recover from previous crash"""
        if not self.state_file.exists():
            return
            
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            # Check if state is recent (within last hour)
            timestamp = datetime.fromisoformat(state['timestamp'])
            if (datetime.now() - timestamp).total_seconds() > 3600:
                logger.info("State file too old, ignoring")
                self.state_file.unlink()
                return
            
            # Offer recovery
            reply = QMessageBox.question(
                None,
                "Recover Previous Session?",
                f"FocusQuest didn't shut down properly.\n\n"
                f"Would you like to recover your previous session?\n"
                f"Problem ID: {state.get('current_problem_id', 'Unknown')}\n"
                f"Time in session: {state.get('session_duration', 0) // 60} minutes",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._restore_state(state)
            else:
                self.state_file.unlink()
                
        except Exception as e:
            logger.error(f"Error checking crash recovery: {e}")
            if self.state_file.exists():
                self.state_file.unlink()
    
    def _restore_state(self, state):
        """Restore application state from saved data"""
        try:
            # Restore window position
            if 'window_geometry' in state:
                geo = state['window_geometry']
                self.main_window.setGeometry(geo['x'], geo['y'], geo['width'], geo['height'])
            
            # Restore UI state
            if 'ui_state' in state:
                if state['ui_state'].get('focus_mode'):
                    self.main_window.toggle_focus_mode()
            
            # Set current problem ID for recovery
            self.current_problem_id = state.get('current_problem_id')
            
            # Session will be started fresh but we note the recovery
            logger.info(f"Recovered state from {state['timestamp']}")
            
        except Exception as e:
            logger.error(f"Error restoring state: {e}")
    
    def _periodic_memory_cleanup(self):
        """Periodic memory cleanup to prevent leaks"""
        try:
            # Force garbage collection
            collected = gc.collect()
            
            # Clean up caches in analyzers if they exist
            if hasattr(self, 'problem_loader') and hasattr(self.problem_loader, 'analyzer'):
                analyzer = self.problem_loader.analyzer
                if hasattr(analyzer, '_cleanup_expired_cache'):
                    analyzer._cleanup_expired_cache()
            
            logger.debug(f"Memory cleanup: collected {collected} objects")
            
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
    
    def _cleanup(self):
        """Cleanup resources on exit"""
        logger.info("Performing cleanup...")
        self.running = False
        
        # Stop timers
        if hasattr(self, 'autosave_timer'):
            self.autosave_timer.stop()
        if hasattr(self, 'memory_cleanup_timer'):
            self.memory_cleanup_timer.stop()
        
        # Final memory cleanup
        self._periodic_memory_cleanup()
        
        # Save final state
        self._save_state()
        
        # End session if active
        if hasattr(self, 'session_manager'):
            try:
                self.session_manager.end_session()
            except:
                pass
        
        # Close database connections
        if hasattr(self, 'db_manager'):
            try:
                self.db_manager.close()
            except:
                pass
        
        # Remove state file on clean exit
        if self.state_file.exists():
            try:
                self.state_file.unlink()
            except:
                pass
    
    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Initiating graceful shutdown...")
        self._cleanup()
        
        # Close the application
        if hasattr(self, 'app'):
            self.app.quit()


def main():
    """Main entry point"""
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    try:
        # Create and run application
        app = FocusQuestApp()
        return app.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        return 0
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())