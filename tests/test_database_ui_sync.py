"""Test database-UI synchronization integration."""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Ensure QApplication exists
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.ui.main_window_with_sync import FocusQuestSyncWindow
from src.database.models import User, Session, Problem, ProblemAttempt


class TestDatabaseUISync:
    """Test full database-UI synchronization."""
    
    @pytest.fixture
    def sync_window(self, qtbot):
        """Create synchronized window for testing."""
        with patch('src.ui.main_window_integrated.DatabaseManager'):
            with patch('src.ui.file_watcher_integration.EnhancedFileWatcher'):
                with patch('src.ui.file_watcher_integration.QueueProcessor'):
                    with patch('src.core.state_synchronizer.DatabaseManager'):
                        window = FocusQuestSyncWindow()
                        qtbot.addWidget(window)
                        
                        # Stop timers for testing
                        if hasattr(window, 'queue_timer'):
                            window.queue_timer.stop()
                        if hasattr(window.state_sync, 'auto_save_timer'):
                            window.state_sync.auto_save_timer.stop()
                            
                        return window
    
    def test_window_initializes_user_session(self, sync_window):
        """Test that window initializes user and session on startup."""
        # Mock methods
        sync_window.state_sync.initialize_user = Mock(return_value={
            'user_id': 1,
            'username': 'default',
            'level': 1,
            'total_xp': 0
        })
        sync_window.state_sync.start_session = Mock(return_value=1)
        
        # Re-initialize
        sync_window._initialize_user_session()
        
        # Should initialize user
        sync_window.state_sync.initialize_user.assert_called_with('default')
        
        # Should start session
        sync_window.state_sync.start_session.assert_called_once()
        
    def test_problem_load_creates_attempt(self, sync_window):
        """Test that loading a problem creates attempt in database."""
        # Mock state sync
        sync_window.state_sync.start_problem_attempt = Mock(return_value=1)
        
        # Load problem
        problem_data = {
            'id': 123,
            'original_text': 'Test problem',
            'steps': []
        }
        
        with patch.object(sync_window, 'problem_widget'):
            sync_window.load_problem(problem_data)
            
        # Should start attempt
        sync_window.state_sync.start_problem_attempt.assert_called_with(123)
        
    def test_problem_completion_saves_to_db(self, sync_window):
        """Test that completing problem saves to database."""
        # Setup current problem
        sync_window.current_problem = {'id': 123, 'difficulty': 4}
        sync_window._hints_used = 0
        
        # Mock methods
        sync_window.state_sync.complete_problem = Mock()
        sync_window.state_sync.get_user_stats = Mock(return_value={
            'level': 2,
            'total_xp': 150
        })
        
        # Complete problem
        sync_window._on_problem_completed()
        
        # Should save completion with XP
        sync_window.state_sync.complete_problem.assert_called_once()
        xp_arg = sync_window.state_sync.complete_problem.call_args[0][0]
        assert xp_arg > 0  # Should earn some XP
        
    def test_skip_problem_saves_to_db(self, sync_window):
        """Test that skipping problem saves to database."""
        # Mock state sync
        sync_window.state_sync.skip_problem = Mock()
        
        # Setup to avoid UI elements
        sync_window.current_problem = {'id': 123}
        
        # Skip problem
        with patch.object(sync_window, 'show_skip_confirmation', return_value=True):
            sync_window.skip_problem()
            
        # Should save skip
        sync_window.state_sync.skip_problem.assert_called_once()
        
    def test_step_progress_updates_db(self, sync_window):
        """Test that step completion updates database."""
        # Mock state sync
        sync_window.state_sync.update_problem_progress = Mock()
        
        # Complete step
        sync_window._on_step_completed(3)
        
        # Should update progress
        sync_window.state_sync.update_problem_progress.assert_called_with(step=3)
        
    def test_hint_usage_updates_db(self, sync_window):
        """Test that using hints updates database."""
        # Mock state sync and widget
        sync_window.state_sync.update_problem_progress = Mock()
        sync_window.problem_widget = Mock(current_step_index=2)
        
        # Use hint
        sync_window._on_hint_used(1)
        
        # Should update with hint count
        sync_window.state_sync.update_problem_progress.assert_called_with(
            step=2,
            hints_used=1
        )
        
    def test_break_pauses_processing_and_saves(self, sync_window):
        """Test that taking break pauses and saves state."""
        # Mock methods
        sync_window.file_watcher.pause_processing = Mock()
        sync_window.state_sync.save_current_state = Mock()
        
        # Start break
        sync_window._on_break_started()
        
        # Should pause processing
        sync_window.file_watcher.pause_processing.assert_called_once()
        
        # Should save state
        sync_window.state_sync.save_current_state.assert_called_once()
        
    def test_xp_calculation_with_bonuses(self, sync_window):
        """Test XP calculation includes appropriate bonuses."""
        # Test base case
        sync_window.current_problem = {'difficulty': 3}
        sync_window._hints_used = 2
        xp = sync_window._calculate_xp_reward()
        assert xp == 50  # Base XP, no bonuses
        
        # Test no hints bonus
        sync_window._hints_used = 0
        xp = sync_window._calculate_xp_reward()
        assert xp == 70  # Base + no hints bonus
        
        # Test difficulty bonus
        sync_window.current_problem = {'difficulty': 5}
        sync_window._hints_used = 0
        xp = sync_window._calculate_xp_reward()
        assert xp == 90  # Base + no hints + difficulty bonus
        
    def test_state_recovery_on_startup(self, sync_window):
        """Test recovering last state on startup."""
        # Mock last state
        last_state = {
            'user': {'id': 1, 'level': 3},
            'session': {'id': 10, 'active': True},
            'problem': {'id': 123, 'step': 2}
        }
        
        sync_window.state_sync.load_last_state = Mock(return_value=last_state)
        
        # Mock dialog to accept recovery
        with patch('PyQt6.QtWidgets.QMessageBox.question') as mock_question:
            mock_question.return_value = QMessageBox.StandardButton.Yes
            
            # Mock problem loading
            sync_window._load_problem_by_id = Mock()
            
            # Trigger recovery
            sync_window._recover_last_state()
            
            # Should offer to recover
            mock_question.assert_called_once()
            
            # Should load the problem
            sync_window._load_problem_by_id.assert_called_with(123)
            
    def test_clean_shutdown_saves_state(self, sync_window):
        """Test that closing window properly saves state."""
        # Mock methods
        sync_window.state_sync.end_session = Mock()
        sync_window.state_sync.save_current_state = Mock()
        sync_window.file_watcher.stop = Mock()
        
        # Close window
        sync_window.close()
        
        # Should end session
        sync_window.state_sync.end_session.assert_called_once()
        
        # Should save state
        sync_window.state_sync.save_current_state.assert_called_once()
        
    def test_sync_error_shows_notification(self, sync_window):
        """Test that sync errors show user-friendly notification."""
        # Mock notification
        sync_window.show_notification = Mock()
        
        # Trigger error
        sync_window._on_sync_error("Database connection failed")
        
        # Should show notification
        sync_window.show_notification.assert_called_once()
        call_args = sync_window.show_notification.call_args[0]
        assert "Sync Issue" in call_args[0]
        assert "Database connection failed" in call_args[1]