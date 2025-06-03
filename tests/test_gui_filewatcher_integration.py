"""Test GUI and file watcher integration."""
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QTest

# Ensure QApplication exists
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.ui.main_window_integrated import FocusQuestIntegratedWindow
from src.ui.file_watcher_integration import FileWatcherIntegration
from src.core.problem_monitor import ProblemMonitor


class TestGUIFileWatcherIntegration:
    """Test integration between GUI and file watcher system."""
    
    @pytest.fixture
    def integrated_window(self, qtbot):
        """Create integrated window for testing."""
        with patch('src.ui.main_window_integrated.DatabaseManager'):
            with patch('src.ui.file_watcher_integration.EnhancedFileWatcher'):
                with patch('src.ui.file_watcher_integration.QueueProcessor'):
                    window = FocusQuestIntegratedWindow()
                    qtbot.addWidget(window)
                    return window
    
    @pytest.fixture
    def file_watcher_integration(self):
        """Create file watcher integration."""
        with patch('src.ui.file_watcher_integration.EnhancedFileWatcher'):
            with patch('src.ui.file_watcher_integration.QueueProcessor'):
                integration = FileWatcherIntegration()
                return integration
    
    def test_file_watcher_starts_on_window_init(self, integrated_window):
        """Test that file watcher starts when window initializes."""
        # File watcher should be created and started
        assert hasattr(integrated_window, 'file_watcher')
        assert integrated_window.file_watcher is not None
        
    def test_new_problem_from_file_updates_queue(self, integrated_window):
        """Test that new problems from files are added to queue."""
        # Set a current problem so new problem goes to queue instead of loading immediately
        integrated_window.current_problem = {'id': 'current_problem'}
        
        initial_queue_size = len(integrated_window.problem_queue)
        
        # Simulate new problem from file watcher
        problem_data = {
            'id': 'problem_123',
            'source': 'file_watcher',
            'problem_text': 'Test problem',
            'steps': [{'description': 'Step 1'}],
            'difficulty_rating': 3
        }
        
        integrated_window._on_new_problem_from_file(problem_data)
        
        # Queue should have new problem (since current_problem exists)
        assert len(integrated_window.problem_queue) == initial_queue_size + 1
        assert integrated_window.problem_queue[0]['id'] == 'problem_123'
        
    def test_window_title_updates_with_queue_status(self, integrated_window):
        """Test that window title shows queue status."""
        # Add problems to queue
        for i in range(3):
            integrated_window.problem_queue.append({
                'id': f'problem_{i}',
                'source': 'file_watcher'
            })
            
        integrated_window._update_window_title()
        
        # Title should show queue count
        assert "3 problems ready" in integrated_window.windowTitle()
        
    def test_panic_mode_pauses_file_processing(self, integrated_window):
        """Test that panic mode pauses file processing."""
        # Mock file watcher pause
        integrated_window.file_watcher.pause_processing = Mock()
        
        # Enter panic mode
        integrated_window.enter_panic_mode()
        
        # File processing should be paused
        integrated_window.file_watcher.pause_processing.assert_called_once()
        
    def test_exit_panic_resumes_file_processing(self, integrated_window):
        """Test that exiting panic mode resumes processing."""
        # Enter panic mode first
        integrated_window.panic_mode_active = True
        
        # Mock file watcher resume
        integrated_window.file_watcher.resume_processing = Mock()
        
        # Exit panic mode
        integrated_window.exit_panic_mode()
        
        # File processing should resume
        integrated_window.file_watcher.resume_processing.assert_called_once()
        
    def test_problem_monitor_detects_new_analyses(self, tmp_path):
        """Test that problem monitor detects completed analyses."""
        # Create test analysis directory
        analysis_dir = tmp_path / "analysis_sessions"
        analysis_dir.mkdir()
        
        # Create monitor
        monitor = ProblemMonitor(str(analysis_dir), poll_interval=100)
        
        # Track emitted signals
        new_problems = []
        monitor.new_problem_ready.connect(lambda p: new_problems.append(p))
        
        # Start monitoring
        monitor.start_monitoring()
        
        # Create a completed analysis
        problem_dir = analysis_dir / "problem_test_123"
        problem_dir.mkdir()
        
        result_data = {
            'problem_text': 'Test problem',
            'steps': [{'description': 'Step 1'}],
            'difficulty_rating': 3
        }
        
        with open(problem_dir / "analysis_result.json", 'w') as f:
            json.dump(result_data, f)
            
        # Wait for detection (poll interval + buffer)
        QTest.qWait(200)
        
        # Should have detected the problem
        assert len(new_problems) == 1
        assert new_problems[0]['id'] == 'problem_test_123'
        assert new_problems[0]['source'] == 'file_watcher'
        
        # Stop monitoring
        monitor.stop_monitoring()
        
    def test_queue_loads_problems_sequentially(self, integrated_window):
        """Test that problems are loaded from queue in order."""
        # Mock load_problem
        integrated_window.load_problem = Mock()
        
        # Add multiple problems
        problems = []
        for i in range(3):
            problem = {
                'id': f'problem_{i}',
                'source': 'file_watcher',
                'problem_text': f'Problem {i}'
            }
            problems.append(problem)
            integrated_window.problem_queue.append(problem)
            
        # Load next problem
        integrated_window._load_next_from_queue()
        
        # Should load first problem
        assert integrated_window.load_problem.called
        loaded = integrated_window.load_problem.call_args[0][0]
        assert loaded['id'] == 'problem_0'
        
        # Queue should have remaining problems
        assert len(integrated_window.problem_queue) == 2
        
    def test_file_watcher_thread_safety(self, file_watcher_integration):
        """Test that file watcher runs in separate thread."""
        # Create mock watcher
        mock_watcher = Mock()
        mock_watcher.is_running = True
        
        # Create thread
        from src.ui.file_watcher_integration import FileWatcherThread
        thread = FileWatcherThread(mock_watcher)
        
        # Thread should not be running yet
        assert not thread.isRunning()
        
        # Start thread
        thread.start()
        QTest.qWait(100)
        
        # Thread should be running
        assert thread.isRunning()
        
        # Stop thread
        thread.stop()
        thread.wait(1000)
        
        # Thread should stop
        assert not thread.isRunning()
        
    def test_integration_handles_errors_gracefully(self, integrated_window):
        """Test that integration handles errors without crashing."""
        # Simulate file watcher error
        error_msg = "Test error"
        integrated_window._on_watcher_error(error_msg)
        
        # Should not crash, should show notification
        # (notification tested separately)
        assert True  # If we get here, no crash
        
    def test_close_window_stops_file_watcher(self, integrated_window):
        """Test that closing window properly stops file watcher."""
        # Mock file watcher stop
        integrated_window.file_watcher.stop = Mock()
        
        # Close window
        integrated_window.close()
        
        # File watcher should be stopped
        integrated_window.file_watcher.stop.assert_called_once()