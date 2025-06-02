"""
SQLAlchemy database models for FocusQuest
Implements all entities for the ADHD-optimized math learning system
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float,
    ForeignKey, UniqueConstraint, CheckConstraint, Enum
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class DifficultyLevel(enum.Enum):
    """Problem difficulty levels"""
    VERY_EASY = 1
    EASY = 2
    MEDIUM = 3
    HARD = 4
    VERY_HARD = 5


class Problem(Base):
    """Mathematical problem from PDF source"""
    __tablename__ = 'problems'
    
    id = Column(Integer, primary_key=True)
    original_text = Column(Text, nullable=False)  # Hebrew text
    translated_text = Column(Text)  # English translation
    difficulty = Column(Integer, nullable=False)
    category = Column(String(50), nullable=False)  # calculus, algebra, etc.
    pdf_source = Column(String(255))
    page_number = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    steps = relationship("ProblemStep", back_populates="problem", order_by="ProblemStep.step_number")
    attempts = relationship("ProblemAttempt", back_populates="problem")
    
    __table_args__ = (
        CheckConstraint('difficulty >= 1 AND difficulty <= 5', name='check_difficulty_range'),
    )
    
    @validates('difficulty')
    def validate_difficulty(self, key, value):
        if not 1 <= value <= 5:
            raise ValueError(f"Difficulty must be between 1 and 5, got {value}")
        return value


class ProblemStep(Base):
    """ADHD-friendly breakdown of problem into 3-7 steps"""
    __tablename__ = 'problem_steps'
    
    id = Column(Integer, primary_key=True)
    problem_id = Column(Integer, ForeignKey('problems.id'), nullable=False)
    step_number = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    explanation = Column(Text)
    time_estimate = Column(Integer)  # minutes
    
    # Relationships
    problem = relationship("Problem", back_populates="steps")
    hints = relationship("Hint", back_populates="step", order_by="Hint.level")
    
    __table_args__ = (
        UniqueConstraint('problem_id', 'step_number', name='unique_problem_step'),
    )


class Hint(Base):
    """3-tier Socratic hint system for each step"""
    __tablename__ = 'hints'
    
    id = Column(Integer, primary_key=True)
    step_id = Column(Integer, ForeignKey('problem_steps.id'), nullable=False)
    level = Column(Integer, nullable=False)  # 1, 2, or 3
    content = Column(Text, nullable=False)
    xp_penalty = Column(Integer, default=5)
    
    # Relationships
    step = relationship("ProblemStep", back_populates="hints")
    
    __table_args__ = (
        UniqueConstraint('step_id', 'level', name='unique_step_hint_level'),
        CheckConstraint('level >= 1 AND level <= 3', name='check_hint_level'),
    )


class User(Base):
    """User account and preferences"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True)
    created_at = Column(DateTime, default=func.now())
    medication_reminder = Column(Boolean, default=False)
    preferred_session_length = Column(Integer, default=25)  # minutes
    
    # Relationships
    progress = relationship("UserProgress", back_populates="user", uselist=False)
    sessions = relationship("Session", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")
    attempts = relationship("ProblemAttempt", back_populates="user")


class UserProgress(Base):
    """User progress and gamification stats"""
    __tablename__ = 'user_progress'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    total_xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(DateTime)
    problems_solved = Column(Integer, default=0)
    total_time_minutes = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="progress")
    
    def add_xp(self, xp_amount: int):
        """Add XP and handle automatic leveling"""
        self.total_xp += xp_amount
        # Simple leveling: every 100 XP = 1 level
        self.level = (self.total_xp // 100) + 1
    
    def update_streak(self, activity_date: datetime):
        """Update streak based on activity date"""
        if self.last_activity_date:
            days_diff = (activity_date.date() - self.last_activity_date.date()).days
            if days_diff == 1:
                # Consecutive day
                self.current_streak += 1
            elif days_diff > 1:
                # Streak broken
                self.current_streak = 1
            # Same day activity doesn't change streak
        else:
            # First activity
            self.current_streak = 1
        
        # Update longest streak if needed
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
        
        self.last_activity_date = activity_date


class Session(Base):
    """Study session tracking"""
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_minutes = Column(Integer)
    problems_attempted = Column(Integer, default=0)
    problems_solved = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)
    medication_taken = Column(Boolean, default=False)
    initial_focus_level = Column(Integer)  # 1-5 scale
    final_focus_level = Column(Integer)
    success_rate = Column(Float)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    attempts = relationship("ProblemAttempt", back_populates="session")
    
    def end_session(self, end_time: datetime, problems_attempted: int, 
                    problems_solved: int, xp_earned: int, final_focus_level: int):
        """Complete a session with final metrics"""
        self.end_time = end_time
        self.duration_minutes = int((end_time - self.start_time).total_seconds() / 60)
        self.problems_attempted = problems_attempted
        self.problems_solved = problems_solved
        self.xp_earned = xp_earned
        self.final_focus_level = final_focus_level
        if problems_attempted > 0:
            self.success_rate = problems_solved / problems_attempted


class Achievement(Base):
    """Available achievements/badges"""
    __tablename__ = 'achievements'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    icon = Column(String(10))  # emoji or icon code
    xp_reward = Column(Integer, default=0)
    requirement_type = Column(String(50))  # problems_solved, streak_days, etc.
    requirement_value = Column(Integer)
    category = Column(String(50))  # optional category filter
    
    # Relationships
    users = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    """User's earned achievements"""
    __tablename__ = 'user_achievements'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    achievement_id = Column(Integer, ForeignKey('achievements.id'), nullable=False)
    earned_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="users")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'achievement_id', name='unique_user_achievement'),
    )


class ProblemAttempt(Base):
    """Track individual problem attempts for analytics"""
    __tablename__ = 'problem_attempts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    problem_id = Column(Integer, ForeignKey('problems.id'), nullable=False)
    session_id = Column(Integer, ForeignKey('sessions.id'))
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    completed = Column(Boolean, default=False)
    success = Column(Boolean)
    time_spent_seconds = Column(Integer)
    hints_used = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)
    skipped = Column(Boolean, default=False)
    skipped_at = Column(DateTime)
    skip_reason = Column(String(100))  # 'user_skip', 'auto_defer', etc.
    
    # Relationships
    user = relationship("User", back_populates="attempts")
    problem = relationship("Problem", back_populates="attempts")
    session = relationship("Session", back_populates="attempts")
    
    def complete_attempt(self, success: bool, time_spent: timedelta, 
                        hints_used: int, xp_earned: int):
        """Mark attempt as completed with results"""
        self.completed = True
        self.completed_at = datetime.now()
        self.success = success
        self.time_spent_seconds = int(time_spent.total_seconds())
        self.hints_used = hints_used
        self.xp_earned = xp_earned


class SkippedProblem(Base):
    """Track problems that users have strategically skipped"""
    __tablename__ = 'skipped_problems'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    problem_id = Column(Integer, ForeignKey('problems.id'), nullable=False)
    skipped_at = Column(DateTime, default=func.now())
    return_after = Column(DateTime)  # When it can return to queue
    skip_count = Column(Integer, default=1)
    last_attempt_id = Column(Integer, ForeignKey('problem_attempts.id'))
    reason = Column(String(100), default='user_skip')  # user_skip, auto_defer, etc.
    
    # Relationships
    user = relationship("User")
    problem = relationship("Problem")
    last_attempt = relationship("ProblemAttempt")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'problem_id', name='unique_user_skipped_problem'),
    )
    
    def calculate_return_time(self):
        """Calculate when this problem should return based on skip count"""
        # Spaced repetition intervals: 2h, 8h, 1d, 3d, 1w
        intervals = [
            timedelta(hours=2),      # First skip: 2 hours
            timedelta(hours=8),      # Second skip: 8 hours  
            timedelta(days=1),       # Third skip: 1 day
            timedelta(days=3),       # Fourth skip: 3 days
            timedelta(weeks=1),      # Fifth+ skip: 1 week
        ]
        
        # Use the appropriate interval based on skip count
        interval_index = min(self.skip_count - 1, len(intervals) - 1)
        interval = intervals[interval_index]
        
        self.return_after = self.skipped_at + interval
        
    def is_ready_to_return(self) -> bool:
        """Check if enough time has passed for this problem to return"""
        if not self.return_after:
            self.calculate_return_time()
        return datetime.now() >= self.return_after