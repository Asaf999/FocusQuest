"""Test ADHD panic button functionality."""
import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from unittest.mock import Mock, patch
import sys

from src.ui.main_window import FocusQuestWindow


class TestPanicButton:
    """Test panic button feature for ADHD support."""
    
    @pytest.fixture
    def app(self, qtbot):
        """Create QApplication for testing."""
        return QApplication.instance() or QApplication(sys.argv)
    
    @pytest.fixture
    def main_window(self, qtbot, app):
        """Create FocusQuestWindow instance for testing."""
        window = FocusQuestWindow()
        qtbot.addWidget(window)
        window.show()
        return window
    
    def test_panic_shortcut_registered(self, main_window):
        """Test that Ctrl+P shortcut is properly registered."""
        # Check if panic action exists
        assert hasattr(main_window, 'panic_action')
        assert main_window.panic_action is not None
        
        # Check shortcut
        from PyQt6.QtGui import QKeySequence
        assert main_window.panic_action.shortcut().toString() == "Ctrl+P"
    
    def test_panic_mode_activated(self, main_window, qtbot):
        """Test panic mode activation pauses all timers and shows overlay."""
        # Setup
        main_window.problem_widget = Mock()
        main_window.session_manager = Mock()
        
        # Trigger panic mode
        main_window.trigger_panic_mode()
        
        # Verify timers paused
        main_window.problem_widget.pause_timer.assert_called_once()
        main_window.session_manager.pause_session.assert_called_once()
        
        # Verify overlay shown
        assert hasattr(main_window, 'panic_overlay')
        assert main_window.panic_overlay.isVisible()
        
    def test_panic_overlay_content(self, main_window, qtbot):
        """Test panic overlay shows calming content."""
        main_window.trigger_panic_mode()
        
        overlay = main_window.panic_overlay
        assert overlay is not None
        
        # Check for calming message
        assert "Take a deep breath" in overlay.message_label.text()
        assert "It's okay to pause" in overlay.message_label.text()
        
        # Check for resume button
        assert overlay.resume_button.text() == "I'm ready to continue"
        
    def test_panic_mode_resume(self, main_window, qtbot):
        """Test resuming from panic mode restores normal state."""
        # Setup
        main_window.problem_widget = Mock()
        main_window.session_manager = Mock()
        
        # Enter panic mode
        main_window.trigger_panic_mode()
        assert main_window.panic_overlay.isVisible()
        
        # Resume
        main_window.resume_from_panic()
        
        # Verify overlay hidden
        assert not main_window.panic_overlay.isVisible()
        
        # Verify timers resumed
        main_window.problem_widget.resume_timer.assert_called_once()
        main_window.session_manager.resume_session.assert_called_once()
        
    def test_panic_mode_blocks_interactions(self, main_window, qtbot):
        """Test that panic mode blocks other interactions."""
        main_window.trigger_panic_mode()
        
        # Try to interact with main content
        main_window.problem_widget = Mock()
        
        # Simulate clicks - should be blocked
        QTest.mouseClick(main_window, Qt.MouseButton.LeftButton)
        
        # Problem widget should not receive events
        main_window.problem_widget.mousePressEvent.assert_not_called()
        
    def test_panic_mode_escape_key_behavior(self, main_window, qtbot):
        """Test ESC key behavior in panic mode."""
        # Enter panic mode
        main_window.trigger_panic_mode()
        
        # Pressing ESC in panic mode should not exit
        QTest.keyClick(main_window, Qt.Key.Key_Escape)
        assert main_window.panic_overlay.isVisible()
        
        # Only clicking resume should exit
        qtbot.mouseClick(main_window.panic_overlay.resume_button, Qt.MouseButton.LeftButton)
        assert not main_window.panic_overlay.isVisible()
        
    def test_panic_mode_with_active_problem(self, main_window, qtbot):
        """Test panic mode during active problem solving."""
        # Setup active problem
        main_window.problem_widget = Mock()
        main_window.problem_widget.current_step_index = 2
        main_window.problem_widget.elapsed_time = 120  # 2 minutes
        
        # Trigger panic
        main_window.trigger_panic_mode()
        
        # Verify state is preserved
        assert main_window.panic_state['step_index'] == 2
        assert main_window.panic_state['elapsed_time'] == 120
        
        # Resume and verify state restored
        main_window.resume_from_panic()
        assert main_window.problem_widget.current_step_index == 2
        
    def test_multiple_panic_triggers(self, main_window, qtbot):
        """Test multiple panic button presses."""
        # First panic
        main_window.trigger_panic_mode()
        assert main_window.panic_overlay.isVisible()
        
        # Try to trigger again - should be ignored
        main_window.trigger_panic_mode()
        assert main_window.panic_overlay.isVisible()
        
        # Resume
        main_window.resume_from_panic()
        assert not main_window.panic_overlay.isVisible()
        
        # Can trigger again after resume
        main_window.trigger_panic_mode()
        assert main_window.panic_overlay.isVisible()
        
    def test_panic_mode_breathing_animation(self, main_window, qtbot):
        """Test breathing guide animation in panic mode."""
        main_window.trigger_panic_mode()
        
        # Check breathing guide exists
        assert hasattr(main_window.panic_overlay, 'breathing_guide')
        breathing_guide = main_window.panic_overlay.breathing_guide
        
        # Verify animation running
        assert breathing_guide.animation.state() == breathing_guide.animation.State.Running
        
        # Verify animation properties
        assert breathing_guide.animation.duration() == 4000  # 4 second breath cycle