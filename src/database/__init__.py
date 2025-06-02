"""
FocusQuest Database Package

This package provides SQLAlchemy models and database management for the
ADHD-optimized math learning RPG. It handles:
- Problem storage with Hebrew support
- Step-by-step problem decomposition
- Hint system with XP costs
- User progress tracking
- Energy and medication schedule tracking
"""

from typing import Optional

__version__ = "0.1.0"
__all__ = ["models", "db_manager"]