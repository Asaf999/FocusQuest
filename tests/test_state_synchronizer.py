"""Test database-UI state synchronization."""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QTimer

from src.core.state_synchronizer import StateSynchronizer
from src.database.models import User, Session, ProblemAttempt


class TestStateSynchronizer:
    """Test state synchronization between database and UI."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        manager = Mock()
        
        # Mock session scope context manager
        mock_session = MagicMock()
        manager.session_scope = MagicMock(return_value=mock_session)
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        
        return manager, mock_session
    
    @pytest.fixture
    def synchronizer(self, mock_db_manager):
        """Create state synchronizer with mocked DB."""
        manager, _ = mock_db_manager
        sync = StateSynchronizer(db_manager=manager)
        # Stop auto-save timer for tests
        sync.auto_save_timer.stop()
        return sync
    
    def test_initialize_new_user(self, synchronizer, mock_db_manager):
        """Test initializing a new user."""
        _, mock_session = mock_db_manager
        
        # Mock no existing user
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Initialize user
        result = synchronizer.initialize_user("test_user")
        
        # Should create new user
        assert mock_session.add.called
        added_user = mock_session.add.call_args[0][0]
        assert isinstance(added_user, User)
        assert added_user.username == "test_user"
        assert added_user.total_xp == 0
        assert added_user.level == 1
        
        # Should commit
        mock_session.commit.assert_called()
        
    def test_initialize_existing_user(self, synchronizer, mock_db_manager):
        """Test loading existing user."""
        _, mock_session = mock_db_manager
        
        # Mock existing user
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.username = "existing_user"
        mock_user.level = 5
        mock_user.total_xp = 500
        mock_user.current_streak = 3
        mock_user.problems_completed = 20
        
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user
        
        # Initialize user
        result = synchronizer.initialize_user("existing_user")
        
        # Should return existing user data
        assert result['user_id'] == 1
        assert result['username'] == "existing_user"
        assert result['level'] == 5
        assert result['total_xp'] == 500
        
        # Should not create new user
        assert not mock_session.add.called
        
    def test_start_session(self, synchronizer, mock_db_manager):
        """Test starting a new session."""
        _, mock_session = mock_db_manager
        
        # Set current user
        synchronizer._current_user = Mock(id=1)
        
        # Mock merge
        mock_session.merge.return_value = synchronizer._current_user
        
        # Start session
        session_id = synchronizer.start_session()
        
        # Should create new session
        assert mock_session.add.called
        added_session = mock_session.add.call_args[0][0]
        assert isinstance(added_session, Session)
        assert added_session.user_id == 1
        assert added_session.problems_attempted == 0
        
        # Should commit
        mock_session.commit.assert_called()
        
    def test_end_session(self, synchronizer, mock_db_manager):
        """Test ending a session."""
        _, mock_session = mock_db_manager
        
        # Set current session
        synchronizer._current_session = Mock(id=1, start_time=datetime.now())
        
        # Mock query result
        mock_db_session = Mock()
        mock_db_session.start_time = datetime.now()
        mock_session.query.return_value.get.return_value = mock_db_session
        
        # End session
        synchronizer.end_session()
        
        # Should update end time
        assert mock_db_session.end_time is not None
        assert mock_db_session.total_time_seconds >= 0
        
        # Should commit
        mock_session.commit.assert_called()
        
        # Should clear current session
        assert synchronizer._current_session is None
        
    def test_start_problem_attempt(self, synchronizer, mock_db_manager):
        """Test starting a problem attempt."""
        _, mock_session = mock_db_manager
        
        # Set current user and session
        synchronizer._current_user = Mock(id=1)
        synchronizer._current_session = Mock(id=1)
        
        # Start attempt
        attempt_id = synchronizer.start_problem_attempt(problem_id=123)
        
        # Should create attempt
        assert mock_session.add.called
        added_attempt = mock_session.add.call_args[0][0]
        assert isinstance(added_attempt, ProblemAttempt)
        assert added_attempt.problem_id == 123
        assert added_attempt.user_id == 1
        assert added_attempt.session_id == 1
        assert added_attempt.current_step == 0
        
        # Should commit
        mock_session.commit.assert_called()
        
    def test_update_problem_progress(self, synchronizer, mock_db_manager):
        """Test updating problem progress."""
        _, mock_session = mock_db_manager
        
        # Set current attempt
        synchronizer._current_problem_attempt = Mock(id=1)
        
        # Mock query result
        mock_attempt = Mock()
        mock_session.query.return_value.get.return_value = mock_attempt
        
        # Update progress
        synchronizer.update_problem_progress(step=3, hints_used=2)
        
        # Should update attempt
        assert mock_attempt.current_step == 3
        assert mock_attempt.hints_used == 2
        
        # Should commit
        mock_session.commit.assert_called()
        
    def test_complete_problem(self, synchronizer, mock_db_manager):
        """Test completing a problem."""
        _, mock_session = mock_db_manager
        
        # Set current state
        synchronizer._current_user = Mock(id=1)
        synchronizer._current_session = Mock(id=1)
        synchronizer._current_problem_attempt = Mock(
            id=1,
            started_at=datetime.now()
        )
        
        # Mock query results
        mock_attempt = Mock(started_at=datetime.now())
        mock_db_session = Mock(problems_completed=0, xp_earned=0)
        mock_user = Mock(problems_completed=0, total_xp=0)
        
        mock_session.query.return_value.get.side_effect = [
            mock_attempt,
            mock_db_session,
            mock_user
        ]
        
        # Complete problem
        synchronizer.complete_problem(xp_earned=50)
        
        # Should update attempt
        assert mock_attempt.is_completed is True
        assert mock_attempt.completed_at is not None
        assert mock_attempt.xp_earned == 50
        
        # Should update session
        assert mock_db_session.problems_completed == 1
        assert mock_db_session.xp_earned == 50
        
        # Should update user
        assert mock_user.problems_completed == 1
        assert mock_user.total_xp == 50
        
        # Should commit
        mock_session.commit.assert_called()
        
        # Should clear current attempt
        assert synchronizer._current_problem_attempt is None
        
    def test_skip_problem(self, synchronizer, mock_db_manager):
        """Test skipping a problem."""
        _, mock_session = mock_db_manager
        
        # Set current state
        synchronizer._current_session = Mock(id=1)
        synchronizer._current_problem_attempt = Mock(id=1)
        
        # Mock query results
        mock_attempt = Mock()
        mock_db_session = Mock(problems_skipped=0)
        
        mock_session.query.return_value.get.side_effect = [
            mock_attempt,
            mock_db_session
        ]
        
        # Skip problem
        synchronizer.skip_problem()
        
        # Should update attempt
        assert mock_attempt.is_skipped is True
        assert mock_attempt.skipped_at is not None
        
        # Should update session
        assert mock_db_session.problems_skipped == 1
        
        # Should commit
        mock_session.commit.assert_called()
        
    def test_level_calculation(self, synchronizer):
        """Test ADHD-friendly level calculation."""
        # Test early levels (100 XP each)
        assert synchronizer._calculate_level(0) == 1
        assert synchronizer._calculate_level(99) == 1
        assert synchronizer._calculate_level(100) == 2
        assert synchronizer._calculate_level(499) == 5
        
        # Test mid levels (150 XP each)
        assert synchronizer._calculate_level(500) == 5
        assert synchronizer._calculate_level(650) == 6
        assert synchronizer._calculate_level(1999) == 14
        
        # Test high levels (200 XP each)
        assert synchronizer._calculate_level(2000) == 15
        assert synchronizer._calculate_level(2200) == 16
        
    def test_load_last_state(self, synchronizer, mock_db_manager):
        """Test loading last saved state."""
        _, mock_session = mock_db_manager
        
        # Mock last user
        mock_user = Mock(
            id=1,
            username="last_user",
            level=3,
            total_xp=250,
            last_seen=datetime.now()
        )
        
        # Mock last session
        mock_last_session = Mock(id=10, start_time=datetime.now())
        
        # Mock last attempt
        mock_last_attempt = Mock(
            problem_id=123,
            current_step=2
        )
        
        # Setup query chain
        user_query = Mock()
        user_query.order_by.return_value.first.return_value = mock_user
        
        session_query = Mock()
        session_query.filter_by.return_value.order_by.return_value.first.return_value = mock_last_session
        
        attempt_query = Mock()
        attempt_query.filter_by.return_value.order_by.return_value.first.return_value = mock_last_attempt
        
        mock_session.query.side_effect = [user_query, session_query, attempt_query]
        
        # Load state
        state = synchronizer.load_last_state()
        
        # Should return correct state
        assert state['user']['id'] == 1
        assert state['user']['username'] == "last_user"
        assert state['session']['id'] == 10
        assert state['session']['active'] is True
        assert state['problem']['id'] == 123
        assert state['problem']['step'] == 2
        
    def test_auto_save_timer(self):
        """Test that auto-save timer is configured."""
        sync = StateSynchronizer()
        
        # Timer should be created
        assert isinstance(sync.auto_save_timer, QTimer)
        assert sync.auto_save_timer.interval() == 30000  # 30 seconds
        
        # Stop timer for cleanup
        sync.auto_save_timer.stop()
        
    def test_get_user_stats(self, synchronizer, mock_db_manager):
        """Test getting user statistics."""
        _, mock_session = mock_db_manager
        
        # Set current user
        synchronizer._current_user = Mock(id=1)
        
        # Mock user data
        mock_user = Mock(
            level=5,
            total_xp=500,
            problems_completed=25,
            current_streak=3,
            longest_streak=7,
            total_time_minutes=240
        )
        
        mock_session.query.return_value.get.return_value = mock_user
        
        # Get stats
        stats = synchronizer.get_user_stats()
        
        # Should return correct stats
        assert stats['level'] == 5
        assert stats['total_xp'] == 500
        assert stats['problems_completed'] == 25
        assert stats['current_streak'] == 3
        assert stats['longest_streak'] == 7
        assert stats['total_time_hours'] == 4.0