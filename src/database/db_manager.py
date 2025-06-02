"""
Database manager with session handling
"""
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from src.database.models import Base


class DatabaseManager:
    """Manage database connections and sessions"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path("data") / "focusquest.db")
            
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
        
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope for database operations"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()