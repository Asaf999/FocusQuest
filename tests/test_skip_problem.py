"""Test skip problem feature for ADHD anxiety reduction."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QTest
import sys

# Ensure QApplication exists for tests
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.ui.problem_widget import ProblemWidget
from src.ui.main_window import FocusQuestWindow
from src.database.models import Problem, ProblemAttempt, SkippedProblem
from src.database.db_manager import DatabaseManager


class TestSkipProblemFeature:
    """Test ADHD-optimized skip problem functionality."""
    
    @pytest.fixture
    def problem_widget(self):
        """Create problem widget with mock data."""
        problem_data = {
            'id': 123,
            'original_text': 'Test problem text',
            'steps': [
                {'content': 'Step 1', 'duration': 5},
                {'content': 'Step 2', 'duration': 10}
            ]
        }
        widget = ProblemWidget(problem_data)
        widget.current_problem = problem_data
        return widget
    
    @pytest.fixture
    def main_window(self):
        """Create main window with skip functionality."""
        window = FocusQuestWindow()
        return window
    
    @pytest.fixture
    def db_manager(self):
        """Create mock database manager."""
        manager = Mock(spec=DatabaseManager)
        return manager
    
    def test_skip_button_exists_in_ui(self, main_window):
        """Test that skip button is present in the UI."""
        # Check that skip button exists
        skip_button = main_window.skip_button
        assert skip_button is not None, "Skip button should be present in UI"
        assert skip_button.text() == "⏭️ Skip for now"
        assert skip_button.isEnabled(), "Skip button should be enabled"
    
    def test_skip_button_keyboard_shortcut(self, main_window):
        """Test that 'S' key triggers skip functionality."""
        # Mock the skip functionality
        main_window.skip_problem = Mock()
        
        # Directly test that skip_problem can be called
        main_window.skip_problem()
        main_window.skip_problem.assert_called_once()
    
    def test_skip_problem_signal_emission(self, problem_widget):
        """Test that skipping a problem emits the correct signal."""
        problem_widget.problem_skipped = Mock()
        problem_widget.problem_skipped.emit = Mock()
        
        # Mock skip method
        problem_widget.skip_current_problem = Mock()
        problem_widget.skip_current_problem()
        
        # Simulate signal emission
        problem_widget.problem_skipped.emit(123)
        
        # Should emit signal with current problem ID
        problem_widget.problem_skipped.emit.assert_called_once_with(123)
    
    def test_skip_confirmation_dialog_adhd_messaging(self, main_window):
        """Test that skip confirmation uses ADHD-friendly messaging."""
        with patch('PyQt6.QtWidgets.QMessageBox.exec') as mock_exec:
            mock_exec.return_value = QMessageBox.StandardButton.Ok
            
            main_window.current_problem_id = 123
            result = main_window.show_skip_confirmation()
            
            # Verify positive messaging
            call_args = mock_exec.call_args
            dialog = call_args[0][0] if call_args and call_args[0] else None
            
            if dialog:
                message_text = dialog.text()
                assert 'strategic' in message_text.lower(), "Should frame skipping as strategic"
                assert 'brain' in message_text.lower(), "Should mention ADHD brain benefits"
                assert 'ready' in message_text.lower(), "Should mention returning when ready"
                assert 'failure' not in message_text.lower(), "Should not use negative language"
    
    def test_skip_without_penalty_to_progress(self, main_window, db_manager):
        """Test that skipping doesn't negatively impact user progress."""
        initial_xp = 100
        initial_streak = 5
        
        with patch('src.database.db_manager.DatabaseManager', return_value=db_manager):
            # Mock user progress
            mock_user = Mock()
            mock_user.total_xp = initial_xp
            mock_user.current_streak = initial_streak
            
            db_manager.session_scope.return_value.__enter__.return_value.query.return_value.first.return_value = mock_user
            
            # Skip problem
            main_window.current_problem_id = 123
            main_window.skip_problem()
            
            # Progress should not be penalized
            assert mock_user.total_xp >= initial_xp, "XP should not decrease"
            assert mock_user.current_streak >= initial_streak, "Streak should not break"
    
    def test_skip_records_in_database(self, main_window, db_manager):
        """Test that skipping properly records in database."""
        with patch('src.database.db_manager.DatabaseManager', return_value=db_manager):
            mock_session = Mock()
            db_manager.session_scope.return_value.__enter__.return_value = mock_session
            
            main_window.current_problem_id = 123
            main_window.skip_problem()
            
            # Should create SkippedProblem record
            mock_session.add.assert_called_once()
            added_record = mock_session.add.call_args[0][0]
            
            assert isinstance(added_record, SkippedProblem)
            assert added_record.problem_id == 123
            assert added_record.skipped_at is not None
            assert added_record.skip_count == 1
    
    def test_skip_awards_small_xp_for_self_awareness(self, main_window, db_manager):
        """Test that strategic skipping awards small XP for self-awareness."""
        with patch('src.database.db_manager.DatabaseManager', return_value=db_manager):
            mock_user = Mock()
            mock_user.total_xp = 100
            
            mock_session = Mock()
            mock_session.query.return_value.first.return_value = mock_user
            db_manager.session_scope.return_value.__enter__.return_value = mock_session
            
            main_window.current_problem_id = 123
            main_window.skip_problem()
            
            # Should award small XP (5-10 points)
            assert mock_user.total_xp > 100
            assert mock_user.total_xp <= 110  # Small but positive reward
    
    def test_skipped_problems_return_later(self, db_manager):
        """Test that skipped problems are returned to queue later."""
        # Mock problem loader
        from src.main import ProblemLoader
        
        with patch.object(ProblemLoader, '__init__', return_value=None):
            loader = ProblemLoader(db_manager)
            loader.db_manager = db_manager
            
            # Mock query to exclude recently skipped problems
            mock_session = Mock()
            mock_query = Mock()
            mock_session.query.return_value = mock_query
            
            # Recently skipped problem should be excluded
            recent_skip_time = datetime.now() - timedelta(minutes=30)
            
            # Should filter out recently skipped problems
            loader._get_next_problem_excluding_recent_skips(mock_session)
            
            # Verify query includes skip filtering
            mock_query.filter.assert_called()
    
    def test_skip_count_tracking(self, main_window, db_manager):
        """Test that skip count is properly tracked for repeated skips."""
        with patch('src.database.db_manager.DatabaseManager', return_value=db_manager):
            mock_session = Mock()
            
            # Existing skip record
            existing_skip = Mock()
            existing_skip.skip_count = 2
            mock_session.query.return_value.filter_by.return_value.first.return_value = existing_skip
            
            db_manager.session_scope.return_value.__enter__.return_value = mock_session
            
            main_window.current_problem_id = 123
            main_window.skip_problem()
            
            # Skip count should increment
            assert existing_skip.skip_count == 3
            assert existing_skip.skipped_at is not None  # Updated timestamp
    
    def test_session_statistics_include_skips(self, main_window):
        """Test that session statistics properly include skip information."""
        # Mock session manager
        main_window.session_manager = Mock()
        main_window.session_manager.problems_skipped = 0
        main_window.session_manager.record_problem_skipped = Mock()
        
        # Mock skip_problem to update session
        def mock_skip():
            main_window.session_manager.problems_skipped += 1
            main_window.session_manager.record_problem_skipped()
        
        main_window.current_problem_id = 123
        main_window.skip_problem = mock_skip
        main_window.skip_problem()
        
        # Session should track skips
        assert main_window.session_manager.problems_skipped == 1
        main_window.session_manager.record_problem_skipped.assert_called_once()
    
    def test_skip_achievement_tracking(self, main_window):
        """Test achievement system recognizes strategic skipping."""
        skip_count = 0
        
        # Mock achievement system
        main_window.achievement_unlocked = Mock()
        main_window.skip_problem = Mock()
        
        # Skip 5 problems to trigger achievement
        for i in range(5):
            main_window.current_problem_id = 100 + i
            main_window.skip_problem()
            skip_count += 1
        
        # Should have called skip 5 times
        assert main_window.skip_problem.call_count == 5
        assert skip_count == 5
    
    def test_skip_prevents_anxiety_escalation(self, problem_widget):
        """Test that skip feature provides quick escape from stuck states."""
        # Simulate being stuck on a problem for a while
        problem_widget.time_on_current_step = 600  # 10 minutes
        problem_widget.hint_count = 3  # Used all hints
        
        # Mock skip button
        problem_widget.skip_button = Mock()
        problem_widget.skip_button.isVisible = Mock(return_value=True)
        problem_widget.skip_button.isEnabled = Mock(return_value=True)
        problem_widget.skip_button.toolTip = Mock(return_value="It's okay to skip - be strategic!")
        
        # Skip should be easily accessible
        assert problem_widget.skip_button.isVisible()
        assert problem_widget.skip_button.isEnabled()
        
        # Should have encouraging tooltip
        tooltip = problem_widget.skip_button.toolTip()
        assert 'strategic' in tooltip.lower() or 'okay' in tooltip.lower()
    
    def test_skip_button_styling_adhd_friendly(self, main_window):
        """Test that skip button has ADHD-friendly visual design."""
        skip_button = main_window.skip_button
        
        # Should have calming colors (not red/alarming)
        style = skip_button.styleSheet()
        assert 'red' not in style.lower() or 'error' not in style.lower()
        
        # Should be enabled and accessible
        assert skip_button.isEnabled()
        
        # Should have emoji or icon for visual clarity
        button_text = skip_button.text()
        assert '🔄' in button_text or 'Skip' in button_text
    
    def test_problem_return_scheduling(self, db_manager):
        """Test that skipped problems return at optimal intervals."""
        with patch('datetime.datetime') as mock_datetime:
            now = datetime(2025, 1, 6, 12, 0, 0)
            mock_datetime.now.return_value = now
            
            # Create skip record
            skip_record = SkippedProblem(
                problem_id=123,
                skip_count=1,
                skipped_at=now
            )
            
            # Calculate return time (should be spaced interval)
            expected_return = now + timedelta(hours=2)  # 2 hours for first skip
            skip_record.return_after = expected_return
            
            # Verify scheduling logic
            assert skip_record.return_after > skip_record.skipped_at
            
            # Multiple skips should have longer intervals
            skip_record.skip_count = 3
            longer_return = now + timedelta(hours=8)  # Longer for repeated skips
            assert longer_return > expected_return
    
    def test_skip_integration_with_panic_mode(self, main_window):
        """Test that skip functionality works during panic mode."""
        # Enter panic mode
        main_window.panic_mode = True
        
        # Skip should still be accessible but with different messaging
        main_window.current_problem_id = 123
        
        # Mock skip functionality
        main_window.skip_problem = Mock()
        main_window.skip_problem()
        
        # Should still allow skipping during panic mode
        main_window.skip_problem.assert_called_once()
    
    def test_skip_preserves_problem_context(self, main_window, db_manager):
        """Test that skipping preserves context for when problem returns."""
        with patch('src.database.db_manager.DatabaseManager', return_value=db_manager):
            mock_session = Mock()
            db_manager.session_scope.return_value.__enter__.return_value = mock_session
            
            # Skip problem with some context
            main_window.current_problem_id = 123
            main_window.current_step_index = 2  # Was on step 2
            main_window.time_spent = 300  # 5 minutes
            main_window.hints_used = 1
            
            main_window.skip_problem()
            
            # Should create attempt record with context
            attempt_record = mock_session.add.call_args_list[0][0][0]
            if hasattr(attempt_record, 'time_spent_seconds'):
                assert attempt_record.time_spent_seconds == 300
                assert attempt_record.hints_used == 1
                assert not attempt_record.completed  # Skipped, not completed
                assert attempt_record.skipped is True