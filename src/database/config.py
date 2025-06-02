"""
Database configuration and session management for FocusQuest
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

from .models import Base


class DatabaseConfig:
    """Database configuration and utilities"""
    
    def __init__(self, database_url: str = None):
        """Initialize database configuration
        
        Args:
            database_url: SQLAlchemy database URL. Defaults to SQLite in data directory.
        """
        if database_url is None:
            # Default to SQLite database in data directory
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
            os.makedirs(db_path, exist_ok=True)
            database_url = f"sqlite:///{os.path.join(db_path, 'focusquest.db')}"
        
        self.database_url = database_url
        self._engine = None
        self._SessionLocal = None
    
    @property
    def engine(self):
        """Lazy-load database engine"""
        if self._engine is None:
            if self.database_url.startswith("sqlite"):
                # SQLite specific configuration
                self._engine = create_engine(
                    self.database_url,
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool,
                    echo=False  # Set to True for SQL debugging
                )
            else:
                # Other databases (PostgreSQL, MySQL, etc.)
                self._engine = create_engine(self.database_url, echo=False)
        return self._engine
    
    @property
    def SessionLocal(self):
        """Lazy-load session factory"""
        if self._SessionLocal is None:
            self._SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        return self._SessionLocal
    
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        Base.metadata.drop_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope for database operations
        
        Usage:
            with db_config.session_scope() as session:
                session.add(some_object)
                # Session will auto-commit on success, rollback on error
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global database configuration instance
db_config = DatabaseConfig()


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI/other frameworks to get DB session
    
    Usage in FastAPI:
        @app.get("/users/{user_id}")
        def get_user(user_id: int, db: Session = Depends(get_db)):
            return db.query(User).filter(User.id == user_id).first()
    """
    db = db_config.get_session()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """Initialize database with tables and default data"""
    db_config.create_tables()
    
    # Add default achievements
    from .models import Achievement
    
    default_achievements = [
        {
            "name": "First Steps",
            "description": "Complete your first problem",
            "icon": "🎯",
            "xp_reward": 10,
            "requirement_type": "problems_solved",
            "requirement_value": 1
        },
        {
            "name": "Persistent Learner",
            "description": "Maintain a 3-day streak",
            "icon": "🔥",
            "xp_reward": 25,
            "requirement_type": "streak_days",
            "requirement_value": 3
        },
        {
            "name": "Week Warrior",
            "description": "Maintain a 7-day streak",
            "icon": "💪",
            "xp_reward": 50,
            "requirement_type": "streak_days",
            "requirement_value": 7
        },
        {
            "name": "Problem Solver",
            "description": "Solve 10 problems",
            "icon": "🧮",
            "xp_reward": 30,
            "requirement_type": "problems_solved",
            "requirement_value": 10
        },
        {
            "name": "Calculus Novice",
            "description": "Solve 5 calculus problems",
            "icon": "∫",
            "xp_reward": 20,
            "requirement_type": "category_problems",
            "requirement_value": 5,
            "category": "calculus"
        },
        {
            "name": "Algebra Apprentice",
            "description": "Solve 5 algebra problems",
            "icon": "x²",
            "xp_reward": 20,
            "requirement_type": "category_problems",
            "requirement_value": 5,
            "category": "algebra"
        },
        {
            "name": "Focus Master",
            "description": "Complete a 45-minute focused session",
            "icon": "🎯",
            "xp_reward": 40,
            "requirement_type": "session_minutes",
            "requirement_value": 45
        },
        {
            "name": "Level 10",
            "description": "Reach level 10",
            "icon": "⭐",
            "xp_reward": 100,
            "requirement_type": "level",
            "requirement_value": 10
        }
    ]
    
    with db_config.session_scope() as session:
        # Check if achievements already exist
        existing = session.query(Achievement).first()
        if not existing:
            for achievement_data in default_achievements:
                achievement = Achievement(**achievement_data)
                session.add(achievement)
            session.commit()
            print(f"Added {len(default_achievements)} default achievements")


# Export commonly used items
__all__ = ['db_config', 'get_db', 'init_database', 'DatabaseConfig']