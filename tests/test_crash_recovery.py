"""Test graceful shutdown and crash recovery mechanisms."""
import pytest
import json
import tempfile
from pathlib import Path
import signal
import os
import time
from unittest.mock import Mock, patch

from src.main import FocusQuestApp


class TestCrashRecovery:
    """Test crash recovery and graceful shutdown."""
    
    @pytest.fixture
    def temp_state_file(self):
        """Create temporary state file."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        yield temp_file.name
        try:
            os.unlink(temp_file.name)
        except:
            pass
    
    def test_state_snapshot_creation(self, temp_state_file):
        """Test that state snapshots are created correctly."""
        # Mock state data
        state_data = {
            'session_id': 'test-session-123',
            'current_problem_id': 42,
            'completed_steps': [0, 1, 2],
            'session_time': 1200,
            'problems_completed': 3,
            'timestamp': time.time()
        }
        
        # Write state
        with open(temp_state_file, 'w') as f:
            json.dump(state_data, f)
        
        # Verify can read back
        with open(temp_state_file, 'r') as f:
            loaded = json.load(f)
        
        assert loaded['session_id'] == 'test-session-123'
        assert loaded['current_problem_id'] == 42
        assert loaded['completed_steps'] == [0, 1, 2]
    
    def test_signal_handler_registration(self):
        """Test that signal handlers are properly registered."""
        with patch('signal.signal') as mock_signal:
            # Import triggers signal registration
            import src.main
            
            # Check SIGTERM and SIGINT registered
            calls = mock_signal.call_args_list
            registered_signals = [call[0][0] for call in calls]
            
            assert signal.SIGTERM in registered_signals
            assert signal.SIGINT in registered_signals
    
    def test_cleanup_on_shutdown(self):
        """Test cleanup is performed on shutdown."""
        with patch('src.main.DatabaseManager'), \
             patch('src.main.SessionManager') as mock_session, \
             patch('src.main.QueueProcessor') as mock_queue:
            
            app = FocusQuestApp()
            
            # Simulate shutdown
            app.cleanup_handler()
            
            # Verify cleanup called
            mock_session.return_value.end_session.assert_called_once()
            mock_queue.return_value.stop.assert_called_once()
    
    def test_state_recovery_on_startup(self, temp_state_file):
        """Test state recovery when starting after crash."""
        # Create previous state
        previous_state = {
            'session_id': 'crashed-session',
            'current_problem_id': 10,
            'completed_steps': [0, 1],
            'session_time': 600,
            'timestamp': time.time() - 300  # 5 minutes ago
        }
        
        with open(temp_state_file, 'w') as f:
            json.dump(previous_state, f)
        
        with patch('src.main.FocusQuestApp.STATE_FILE', temp_state_file), \
             patch('src.main.DatabaseManager'), \
             patch('src.main.SessionManager') as mock_session:
            
            app = FocusQuestApp()
            app.recover_state()
            
            # Should detect crashed session
            assert app.recovered_state is not None
            assert app.recovered_state['session_id'] == 'crashed-session'
    
    def test_periodic_state_save(self):
        """Test that state is saved periodically."""
        with patch('src.main.DatabaseManager'), \
             patch('src.main.SessionManager'), \
             patch('src.main.QTimer') as mock_timer:
            
            app = FocusQuestApp()
            
            # Verify timer created for periodic saves
            mock_timer.assert_called()
            timer_instance = mock_timer.return_value
            timer_instance.timeout.connect.assert_called()
            timer_instance.start.assert_called_with(30000)  # 30 second intervals
    
    def test_recovery_dialog_shown(self, temp_state_file):
        """Test that recovery dialog is shown when crashed state detected."""
        # Create crashed state
        crashed_state = {
            'session_id': 'crashed',
            'current_problem_id': 5,
            'timestamp': time.time() - 60
        }
        
        with open(temp_state_file, 'w') as f:
            json.dump(crashed_state, f)
        
        with patch('src.main.FocusQuestApp.STATE_FILE', temp_state_file), \
             patch('src.main.DatabaseManager'), \
             patch('src.main.QMessageBox') as mock_msgbox:
            
            mock_msgbox.question.return_value = mock_msgbox.StandardButton.Yes
            
            app = FocusQuestApp()
            result = app.check_for_recovery()
            
            # Should show dialog
            mock_msgbox.question.assert_called_once()
            assert result == True
    
    def test_graceful_exit_clears_state(self, temp_state_file):
        """Test that graceful exit clears the state file."""
        # Create state file
        with open(temp_state_file, 'w') as f:
            json.dump({'session_id': 'test'}, f)
        
        with patch('src.main.FocusQuestApp.STATE_FILE', temp_state_file):
            app = Mock()
            app.STATE_FILE = temp_state_file
            app.graceful_exit = FocusQuestApp.graceful_exit.__get__(app)
            
            # Graceful exit
            app.graceful_exit()
            
            # State file should be removed
            assert not Path(temp_state_file).exists()
    
    def test_crash_recovery_with_problem_state(self):
        """Test recovery restores problem solving state."""
        recovered_state = {
            'current_problem_id': 10,
            'completed_steps': [0, 1, 2],
            'current_step': 3,
            'elapsed_time': 120
        }
        
        with patch('src.main.DatabaseManager'), \
             patch('src.main.MainWindow') as mock_window:
            
            app = FocusQuestApp()
            app.recovered_state = recovered_state
            
            # Restore state
            app.restore_problem_state()
            
            # Verify problem loaded
            mock_window.return_value.load_problem.assert_called()
            
    def test_multiple_instance_prevention(self, temp_state_file):
        """Test that multiple instances are prevented."""
        # Create lock file
        lock_file = Path(temp_state_file).with_suffix('.lock')
        lock_file.write_text(str(os.getpid()))
        
        with patch('src.main.FocusQuestApp.LOCK_FILE', str(lock_file)), \
             patch('psutil.pid_exists', return_value=True), \
             patch('sys.exit') as mock_exit:
            
            # Should exit when another instance detected
            import src.main
            src.main.check_single_instance()
            
            mock_exit.assert_called_once()