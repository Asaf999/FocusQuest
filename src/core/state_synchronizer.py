"""Synchronize state between database and UI components."""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from src.database.db_manager import DatabaseManager
from src.database.models import User, Session, Problem, ProblemAttempt

logger = logging.getLogger(__name__)


class StateSynchronizer(QObject):
    """Manages bi-directional sync between database and UI state.
    
    Responsibilities:
    - Save UI state changes to database
    - Load database state into UI on startup
    - Handle session persistence
    - Track user progress
    - Manage problem attempts
    """
    
    # Signals
    state_saved = pyqtSignal()
    state_loaded = pyqtSignal(dict)
    sync_error = pyqtSignal(str)
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize state synchronizer."""
        super().__init__()
        self.db_manager = db_manager or DatabaseManager()
        
        # Current state cache
        self._current_user = None
        self._current_session = None
        self._current_problem_attempt = None
        
        # Auto-save timer (every 30 seconds)
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.save_current_state)
        self.auto_save_timer.start(30000)  # 30 seconds
        
    def initialize_user(self, username: str = "default") -> Dict[str, Any]:
        """Initialize or load user from database."""
        try:
            with self.db_manager.session_scope() as session:
                # Find or create user
                user = session.query(User).filter_by(username=username).first()
                
                if not user:
                    user = User(
                        username=username,
                        created_at=datetime.now(),
                        total_xp=0,
                        level=1,
                        current_streak=0,
                        longest_streak=0,
                        problems_completed=0,
                        problems_attempted=0,
                        total_time_minutes=0
                    )
                    session.add(user)
                    session.commit()
                    logger.info(f"Created new user: {username}")
                else:
                    logger.info(f"Loaded existing user: {username}")
                    
                self._current_user = user
                
                # Return user state
                return {
                    'user_id': user.id,
                    'username': user.username,
                    'level': user.level,
                    'total_xp': user.total_xp,
                    'current_streak': user.current_streak,
                    'problems_completed': user.problems_completed
                }
                
        except Exception as e:
            logger.error(f"Error initializing user: {e}")
            self.sync_error.emit(f"Failed to initialize user: {str(e)}")
            return {}
            
    def start_session(self) -> Optional[int]:
        """Start a new session for current user."""
        if not self._current_user:
            logger.error("No user initialized")
            return None
            
        try:
            with self.db_manager.session_scope() as session:
                # Merge user to current session
                user = session.merge(self._current_user)
                
                # Create new session
                new_session = Session(
                    user_id=user.id,
                    start_time=datetime.now(),
                    problems_attempted=0,
                    problems_completed=0,
                    problems_skipped=0,
                    xp_earned=0,
                    hints_used=0,
                    total_time_seconds=0,
                    energy_level='normal'
                )
                session.add(new_session)
                session.commit()
                
                self._current_session = new_session
                logger.info(f"Started session {new_session.id}")
                return new_session.id
                
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            self.sync_error.emit(f"Failed to start session: {str(e)}")
            return None
            
    def end_session(self):
        """End current session and save final state."""
        if not self._current_session:
            return
            
        try:
            with self.db_manager.session_scope() as session:
                # Update session end time
                db_session = session.query(Session).get(self._current_session.id)
                if db_session:
                    db_session.end_time = datetime.now()
                    db_session.total_time_seconds = int(
                        (db_session.end_time - db_session.start_time).total_seconds()
                    )
                    session.commit()
                    
                logger.info(f"Ended session {self._current_session.id}")
                self._current_session = None
                
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            
    def start_problem_attempt(self, problem_id: int) -> Optional[int]:
        """Start a new problem attempt."""
        if not self._current_session:
            logger.error("No active session")
            return None
            
        try:
            with self.db_manager.session_scope() as session:
                # Create attempt
                attempt = ProblemAttempt(
                    problem_id=problem_id,
                    user_id=self._current_user.id,
                    session_id=self._current_session.id,
                    started_at=datetime.now(),
                    current_step=0,
                    hints_used=0,
                    is_completed=False,
                    is_skipped=False
                )
                session.add(attempt)
                session.commit()
                
                self._current_problem_attempt = attempt
                logger.info(f"Started problem attempt {attempt.id}")
                return attempt.id
                
        except Exception as e:
            logger.error(f"Error starting problem attempt: {e}")
            return None
            
    def update_problem_progress(self, step: int, hints_used: int = 0):
        """Update current problem attempt progress."""
        if not self._current_problem_attempt:
            return
            
        try:
            with self.db_manager.session_scope() as session:
                attempt = session.query(ProblemAttempt).get(
                    self._current_problem_attempt.id
                )
                if attempt:
                    attempt.current_step = step
                    attempt.hints_used = hints_used
                    session.commit()
                    
        except Exception as e:
            logger.error(f"Error updating problem progress: {e}")
            
    def complete_problem(self, xp_earned: int):
        """Mark current problem as completed."""
        if not self._current_problem_attempt:
            return
            
        try:
            with self.db_manager.session_scope() as session:
                # Update attempt
                attempt = session.query(ProblemAttempt).get(
                    self._current_problem_attempt.id
                )
                if attempt:
                    attempt.is_completed = True
                    attempt.completed_at = datetime.now()
                    attempt.time_spent_seconds = int(
                        (attempt.completed_at - attempt.started_at).total_seconds()
                    )
                    attempt.xp_earned = xp_earned
                    
                # Update session stats
                db_session = session.query(Session).get(self._current_session.id)
                if db_session:
                    db_session.problems_completed += 1
                    db_session.xp_earned += xp_earned
                    
                # Update user stats
                user = session.query(User).get(self._current_user.id)
                if user:
                    user.problems_completed += 1
                    user.total_xp += xp_earned
                    user.level = self._calculate_level(user.total_xp)
                    
                session.commit()
                logger.info(f"Completed problem attempt {attempt.id}")
                
                self._current_problem_attempt = None
                self.state_saved.emit()
                
        except Exception as e:
            logger.error(f"Error completing problem: {e}")
            self.sync_error.emit(f"Failed to save completion: {str(e)}")
            
    def skip_problem(self):
        """Mark current problem as skipped."""
        if not self._current_problem_attempt:
            return
            
        try:
            with self.db_manager.session_scope() as session:
                # Update attempt
                attempt = session.query(ProblemAttempt).get(
                    self._current_problem_attempt.id
                )
                if attempt:
                    attempt.is_skipped = True
                    attempt.skipped_at = datetime.now()
                    
                # Update session stats
                db_session = session.query(Session).get(self._current_session.id)
                if db_session:
                    db_session.problems_skipped += 1
                    
                session.commit()
                logger.info(f"Skipped problem attempt {attempt.id}")
                
                self._current_problem_attempt = None
                
        except Exception as e:
            logger.error(f"Error skipping problem: {e}")
            
    def save_current_state(self):
        """Save current UI state to database."""
        # This is called by auto-save timer
        # Individual components should call specific update methods
        logger.debug("Auto-save triggered")
        
    def load_last_state(self) -> Dict[str, Any]:
        """Load last saved state from database."""
        try:
            with self.db_manager.session_scope() as session:
                # Get last user
                user = session.query(User).order_by(User.last_seen.desc()).first()
                if not user:
                    return {}
                    
                self._current_user = user
                
                # Get last incomplete session
                last_session = session.query(Session).filter_by(
                    user_id=user.id,
                    end_time=None
                ).order_by(Session.start_time.desc()).first()
                
                if last_session:
                    self._current_session = last_session
                    
                # Get last incomplete problem
                last_attempt = session.query(ProblemAttempt).filter_by(
                    user_id=user.id,
                    is_completed=False,
                    is_skipped=False
                ).order_by(ProblemAttempt.started_at.desc()).first()
                
                state = {
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'level': user.level,
                        'total_xp': user.total_xp
                    },
                    'session': {
                        'id': last_session.id if last_session else None,
                        'active': last_session is not None
                    },
                    'problem': {
                        'id': last_attempt.problem_id if last_attempt else None,
                        'step': last_attempt.current_step if last_attempt else 0
                    }
                }
                
                self.state_loaded.emit(state)
                return state
                
        except Exception as e:
            logger.error(f"Error loading last state: {e}")
            return {}
            
    def _calculate_level(self, total_xp: int) -> int:
        """Calculate level from XP using ADHD-friendly progression."""
        # Level up every 100 XP at first, then gradually more
        if total_xp < 500:
            return 1 + (total_xp // 100)
        elif total_xp < 2000:
            return 5 + ((total_xp - 500) // 150)
        else:
            return 15 + ((total_xp - 2000) // 200)
            
    def get_user_stats(self) -> Dict[str, Any]:
        """Get current user statistics."""
        if not self._current_user:
            return {}
            
        try:
            with self.db_manager.session_scope() as session:
                user = session.query(User).get(self._current_user.id)
                if user:
                    return {
                        'level': user.level,
                        'total_xp': user.total_xp,
                        'problems_completed': user.problems_completed,
                        'current_streak': user.current_streak,
                        'longest_streak': user.longest_streak,
                        'total_time_hours': user.total_time_minutes / 60.0
                    }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            
        return {}