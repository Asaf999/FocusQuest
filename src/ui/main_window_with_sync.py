"""Main window with full database synchronization."""
import logging
from typing import Optional
from PyQt6.QtCore import pyqtSignal

from src.ui.main_window_integrated import FocusQuestIntegratedWindow
from src.core.state_synchronizer import StateSynchronizer

logger = logging.getLogger(__name__)


class FocusQuestSyncWindow(FocusQuestIntegratedWindow):
    """Main window with database state synchronization.
    
    This adds to the integrated window:
    - Automatic state saving to database
    - Session management with persistence
    - User progress tracking
    - Problem attempt recording
    - Crash recovery from last state
    """
    
    # Additional signals
    user_stats_updated = pyqtSignal(dict)
    
    def __init__(self):
        """Initialize window with state sync."""
        super().__init__()
        
        # Initialize state synchronizer
        self.state_sync = StateSynchronizer(db_manager=self.db_manager)
        
        # Connect sync signals
        self.state_sync.state_saved.connect(self._on_state_saved)
        self.state_sync.state_loaded.connect(self._on_state_loaded)
        self.state_sync.sync_error.connect(self._on_sync_error)
        
        # Initialize user and session
        self._initialize_user_session()
        
        # Try to recover last state
        self._recover_last_state()
        
        # Connect UI events to sync
        self._connect_sync_events()
        
    def _initialize_user_session(self):
        """Initialize user and start session."""
        # Initialize default user
        user_data = self.state_sync.initialize_user("default")
        
        if user_data:
            # Update XP widget with user data
            if hasattr(self, 'xp_widget'):
                self.xp_widget.set_level(user_data['level'])
                self.xp_widget.set_xp(user_data['total_xp'])
                
            # Start new session
            session_id = self.state_sync.start_session()
            logger.info(f"Started session {session_id}")
            
            # Emit user stats
            self.user_stats_updated.emit(user_data)
            
    def _recover_last_state(self):
        """Try to recover from last saved state."""
        last_state = self.state_sync.load_last_state()
        
        if last_state and last_state.get('problem'):
            problem_id = last_state['problem']['id']
            if problem_id:
                # Show recovery dialog
                from PyQt6.QtWidgets import QMessageBox
                result = QMessageBox.question(
                    self,
                    "Resume Last Session?",
                    f"You were working on a problem. Would you like to continue where you left off?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if result == QMessageBox.StandardButton.Yes:
                    # Load the problem
                    self._load_problem_by_id(problem_id)
                    
    def _connect_sync_events(self):
        """Connect UI events to state sync."""
        # Problem events
        if hasattr(self, 'problem_widget'):
            self.problem_widget.step_completed.connect(self._on_step_completed)
            self.problem_widget.hint_used.connect(self._on_hint_used)
            
        # Session events
        if hasattr(self, 'session_manager'):
            self.session_manager.break_started.connect(self._on_break_started)
            self.session_manager.break_ended.connect(self._on_break_ended)
            
    def load_problem(self, problem_data):
        """Override to track problem attempts."""
        # Start problem attempt in database
        if 'id' in problem_data:
            attempt_id = self.state_sync.start_problem_attempt(problem_data['id'])
            logger.info(f"Started attempt {attempt_id} for problem {problem_data['id']}")
            
        # Call parent to load problem
        super().load_problem(problem_data)
        
    def _on_problem_completed(self):
        """Override to save completion to database."""
        # Calculate XP earned
        xp_earned = self._calculate_xp_reward()
        
        # Save to database
        self.state_sync.complete_problem(xp_earned)
        
        # Update user stats
        stats = self.state_sync.get_user_stats()
        self.user_stats_updated.emit(stats)
        
        # Call parent
        super()._on_problem_completed()
        
    def skip_problem(self):
        """Override to track skips in database."""
        # Save skip to database
        self.state_sync.skip_problem()
        
        # Call parent
        super().skip_problem()
        
    def _on_step_completed(self, step_index: int):
        """Handle step completion."""
        # Update progress in database
        self.state_sync.update_problem_progress(step=step_index)
        
    def _on_hint_used(self, hint_level: int):
        """Handle hint usage."""
        # Get current hints used
        current_hints = getattr(self, '_hints_used', 0) + 1
        self._hints_used = current_hints
        
        # Update in database
        if hasattr(self, 'problem_widget'):
            step = self.problem_widget.current_step_index
            self.state_sync.update_problem_progress(step=step, hints_used=current_hints)
            
    def _on_break_started(self):
        """Handle break start."""
        # Pause file processing
        if hasattr(self, 'file_watcher'):
            self.file_watcher.pause_processing()
            
        # Save current state
        self.state_sync.save_current_state()
        
    def _on_break_ended(self):
        """Handle break end."""
        # Resume file processing
        if hasattr(self, 'file_watcher'):
            self.file_watcher.resume_processing()
            
    def _calculate_xp_reward(self) -> int:
        """Calculate XP reward for problem completion."""
        base_xp = 50
        
        # Bonus for no hints
        if not hasattr(self, '_hints_used') or self._hints_used == 0:
            base_xp += 20
            
        # Bonus for difficulty
        if self.current_problem:
            difficulty = self.current_problem.get('difficulty', 3)
            base_xp += (difficulty - 3) * 10
            
        # Reset hints counter
        self._hints_used = 0
        
        return max(10, base_xp)  # Minimum 10 XP
        
    def _load_problem_by_id(self, problem_id: int):
        """Load specific problem from database."""
        try:
            with self.db_manager.session_scope() as session:
                from src.database.models import Problem
                problem = session.query(Problem).get(problem_id)
                
                if problem:
                    problem_data = {
                        'id': problem.id,
                        'original_text': problem.original_text,
                        'translated_text': problem.translated_text,
                        'difficulty': problem.difficulty,
                        'source': 'database'
                    }
                    self.load_problem(problem_data)
                    
        except Exception as e:
            logger.error(f"Error loading problem {problem_id}: {e}")
            
    def _on_state_saved(self):
        """Handle successful state save."""
        logger.debug("State saved to database")
        
    def _on_state_loaded(self, state: dict):
        """Handle state loaded from database."""
        logger.info(f"Loaded state: {state}")
        
    def _on_sync_error(self, error_msg: str):
        """Handle sync errors."""
        logger.error(f"Sync error: {error_msg}")
        self.show_notification(
            "Sync Issue",
            f"There was an issue saving your progress: {error_msg}",
            duration=5000
        )
        
    def closeEvent(self, event):
        """Clean shutdown with state saving."""
        # End session
        self.state_sync.end_session()
        
        # Save final state
        self.state_sync.save_current_state()
        
        # Call parent
        super().closeEvent(event)