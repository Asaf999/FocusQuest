"""
Session management with ADHD-friendly break reminders
"""
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
from datetime import datetime, timedelta
from typing import Optional


class SessionManager(QObject):
    """Manage study sessions with break reminders"""
    
    break_suggested = pyqtSignal()
    session_started = pyqtSignal()
    session_ended = pyqtSignal(dict)  # Session stats
    
    def __init__(self, break_interval: int = 25):
        super().__init__()
        self.break_interval = break_interval  # Minutes
        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self.check_session_time)
        self.session_start_time: Optional[datetime] = None
        self.session_time = 0  # Seconds
        self.problems_completed = 0
        self.problems_skipped = 0  # Track strategic skips
        self.xp_earned = 0
        
    def start_session(self):
        """Start a new study session"""
        self.session_start_time = datetime.now()
        self.session_time = 0
        self.problems_completed = 0
        self.problems_skipped = 0
        self.xp_earned = 0
        self.session_timer.start(1000)  # Check every second
        self.session_started.emit()
        
    def pause_session(self):
        """Pause the current session"""
        self.session_timer.stop()
        
    def resume_session(self):
        """Resume the paused session"""
        if self.session_start_time:
            self.session_timer.start(1000)
            
    def end_session(self):
        """End the current session"""
        self.session_timer.stop()
        
        if self.session_start_time:
            stats = {
                'duration': self.session_time,
                'problems_completed': self.problems_completed,
                'xp_earned': self.xp_earned,
                'start_time': self.session_start_time,
                'end_time': datetime.now()
            }
            self.session_ended.emit(stats)
            
        self.session_start_time = None
        
    def check_session_time(self):
        """Check if it's time for a break"""
        self.session_time += 1
        
        # Check for break time
        if self.session_time > 0 and self.session_time % (self.break_interval * 60) == 0:
            self.suggest_break()
            
    def suggest_break(self):
        """Suggest taking a break"""
        self.break_suggested.emit()
        # Could show a notification here
        
    def record_problem_completed(self):
        """Record that a problem was completed"""
        self.problems_completed += 1
        
    def record_problem_skipped(self):
        """Record that a problem was strategically skipped"""
        self.problems_skipped += 1
        
    def record_xp_earned(self, amount: int):
        """Record XP earned in session"""
        self.xp_earned += amount
        
    def get_session_duration(self) -> str:
        """Get formatted session duration"""
        if not self.session_start_time:
            return "0:00"
            
        minutes = self.session_time // 60
        seconds = self.session_time % 60
        return f"{minutes}:{seconds:02d}"
        
    def should_take_break(self) -> bool:
        """Check if user should take a break"""
        return self.session_time >= self.break_interval * 60