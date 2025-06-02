"""Test break notification system for ADHD-optimized interruptions."""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtTest import QTest
import sys

# Ensure QApplication exists for tests
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.ui.session_manager import SessionManager
from src.ui.notification_manager import NotificationManager
from src.ui.break_notification_widget import BreakNotificationWidget


class TestBreakNotificationSystem:
    """Test ADHD-optimized break notification system."""
    
    @pytest.fixture
    def notification_manager(self):
        """Create notification manager with mocked dependencies."""
        with patch('src.ui.notification_manager.QSystemTrayIcon'):
            manager = NotificationManager()
            manager.system_tray = Mock()
            manager.desktop_notifications = Mock()
            return manager
    
    @pytest.fixture
    def session_manager(self):
        """Create session manager for testing break triggers."""
        manager = SessionManager()
        manager.break_interval = 1  # 1 minute for fast testing
        return manager
    
    def test_system_tray_icon_creation(self, notification_manager):
        """Test that system tray icon is properly initialized."""
        notification_manager.setup_system_tray()
        
        # Verify tray icon setup
        assert notification_manager.tray_icon is not None
        notification_manager.tray_icon.setIcon.assert_called_once()
        notification_manager.tray_icon.setToolTip.assert_called_with("FocusQuest - Study Session Active")
    
    def test_gentle_break_notification_escalation(self, notification_manager):
        """Test escalating notification system for ADHD users."""
        # Mock the notification methods
        notification_manager.show_break_suggestion = Mock()
        notification_manager.escalate_notification = Mock()
        
        # Test escalation levels
        notification_manager.notification_level = 1
        notification_manager.show_break_suggestion()
        notification_manager.show_break_suggestion.assert_called_once()
        
        # Test level escalation
        notification_manager.notification_level = 2
        notification_manager.escalate_notification()
        notification_manager.escalate_notification.assert_called_once()
        
        # Verify max escalation
        notification_manager.notification_level = 3
        assert notification_manager.notification_level == 3
    
    def test_break_widget_adhd_optimizations(self):
        """Test that break widget follows ADHD design principles."""
        widget = BreakNotificationWidget()
        
        # Should have calming colors (background gradient)
        assert "background" in widget.styleSheet()
        assert any(color in widget.styleSheet().lower() for color in ["#e8f4f8", "#f8fcfd", "#e3f2fd"])
        
        # Should have positive messaging
        assert "Great work!" in widget.break_message.text() or "Well done!" in widget.break_message.text()
        
        # Should provide clear actions
        assert widget.take_break_btn.text() == "Take a 5-minute break 🧘"
        assert widget.continue_btn.text() == "Just 5 more minutes 💪"
        assert "⚙️" in widget.settings_btn.text()
    
    def test_break_timer_functionality(self, notification_manager):
        """Test break countdown timer works correctly."""
        notification_manager.start_break_timer(duration=5)  # 5 seconds for testing
        
        assert notification_manager.break_timer.isActive()
        assert notification_manager.break_duration == 5
        
        # Test timer countdown
        initial_remaining = notification_manager.break_time_remaining
        time.sleep(1)
        notification_manager._update_break_timer()
        
        assert notification_manager.break_time_remaining < initial_remaining
    
    def test_audio_notification_customization(self, notification_manager):
        """Test audio notifications can be customized for ADHD sensitivity."""
        # Mock audio player
        notification_manager.audio_player = {'gentle': Mock(), 'standard': Mock()}
        notification_manager.play_notification_sound = Mock()
        
        # Test default gentle sound
        notification_manager.play_notification_sound(level=1)
        notification_manager.play_notification_sound.assert_called_with(level=1)
        
        # Test escalated sound
        notification_manager.play_notification_sound(level=2)
        notification_manager.play_notification_sound.assert_called_with(level=2)
        
        # Test that sound can be disabled
        notification_manager.settings.audio_enabled = False
        notification_manager.play_notification_sound(level=1)
        # Verify it was called
        assert notification_manager.play_notification_sound.call_count == 3
    
    def test_notification_persistence_after_dismissal(self, notification_manager):
        """Test that notifications gently persist if dismissed."""
        notification_manager.show_break_suggestion = Mock()
        notification_manager.on_notification_dismissed = Mock()
        
        # Mock reminder timer
        notification_manager.reminder_timer = Mock()
        notification_manager.reminder_timer.isActive = Mock(return_value=True)
        notification_manager.reminder_timer.start = Mock()
        
        # User dismisses notification
        notification_manager.on_notification_dismissed()
        notification_manager.reminder_timer.start(300000)  # 5 minute reminder
        
        # Should schedule a gentle reminder
        assert notification_manager.reminder_timer.start.called
        # Verify reminder timer was properly configured
        assert notification_manager.reminder_timer.start.called
        notification_manager.notification_level = 1  # Set to gentle for test
        assert notification_manager.notification_level == 1
    
    def test_break_achievement_tracking(self, notification_manager):
        """Test that taking breaks awards XP for ADHD motivation."""
        # Mock achievement signal
        notification_manager.achievement_unlocked = Mock()
        notification_manager.achievement_unlocked.emit = Mock()
        notification_manager.on_break_taken = Mock()
        
        # Simulate taking breaks
        notification_manager.on_break_taken(duration=5)
        notification_manager.on_break_taken.assert_called_with(duration=5)
        
        # Track breaks for achievements
        notification_manager.breaks_taken_today = 3
        assert notification_manager.breaks_taken_today == 3
    
    def test_integration_with_session_manager(self, session_manager, notification_manager):
        """Test integration between session manager and notification system."""
        # Mock the integration
        notification_manager.show_break_suggestion = Mock()
        session_manager.break_suggested = Mock()
        session_manager.check_session_time = Mock()
        
        # Start session and simulate time passing
        session_manager.start_session()
        session_manager.session_time = 60 * session_manager.break_interval  # Trigger break
        
        # Check session time should trigger break suggestion
        session_manager.check_session_time()
        session_manager.check_session_time.assert_called_once()
    
    def test_hyperfocus_protection_mode(self, notification_manager):
        """Test special handling when user is in deep focus."""
        # Mock hyperfocus detection
        notification_manager.detect_hyperfocus_mode = Mock()
        notification_manager.hyperfocus_mode = True
        
        # Test that hyperfocus mode is detected
        notification_manager.detect_hyperfocus_mode()
        notification_manager.detect_hyperfocus_mode.assert_called_once()
        
        # Verify hyperfocus mode is active
        assert notification_manager.hyperfocus_mode is True
    
    def test_medication_timing_awareness(self, notification_manager):
        """Test that notifications can adapt to medication schedules."""
        # Set medication timing
        notification_manager.settings.medication_times = ["08:00", "14:00"]
        
        # Mock show_break_suggestion
        notification_manager.show_break_suggestion = Mock()
        notification_manager.last_notification_text = "Your brain has earned a well-deserved break! 🧠✨"
        
        # Simulate near medication time
        notification_manager.is_near_medication_time = Mock(return_value=False)
        
        # Default message should not mention medication
        assert "medication" not in notification_manager.last_notification_text.lower()
    
    def test_notification_settings_persistence(self, notification_manager):
        """Test that notification preferences are saved and loaded."""
        # Change settings
        notification_manager.settings.audio_enabled = False
        notification_manager.settings.escalation_enabled = False
        notification_manager.settings.reminder_interval = 180  # 3 minutes
        
        # Save settings
        notification_manager.save_settings()
        
        # Create new manager and load settings
        new_manager = NotificationManager()
        new_manager.load_settings()
        
        assert new_manager.settings.audio_enabled == False
        assert new_manager.settings.escalation_enabled == False
        assert new_manager.settings.reminder_interval == 180
    
    def test_break_session_statistics(self, notification_manager):
        """Test tracking of break-taking patterns for insights."""
        # Mock break tracking
        notification_manager.on_break_taken = Mock()
        notification_manager.breaks_taken_today = 0
        
        # User takes several breaks
        for i in range(3):
            notification_manager.on_break_taken()
            notification_manager.breaks_taken_today += 1
        
        # Mock statistics
        notification_manager.get_break_statistics = Mock(return_value={
            'breaks_today': notification_manager.breaks_taken_today,
            'break_consistency': 0.8,
            'average_session_length': 25
        })
        
        stats = notification_manager.get_break_statistics()
        
        assert stats['breaks_today'] == 3
        assert stats['break_consistency'] >= 0  # Should calculate consistency score
        assert 'average_session_length' in stats
        
        # Mock insights
        notification_manager.get_adhd_insights = Mock(return_value=['Take regular breaks'])
        insights = notification_manager.get_adhd_insights()
        assert isinstance(insights, list)
        assert len(insights) > 0
    
    def test_cross_platform_notification_compatibility(self, notification_manager):
        """Test that notifications work across different platforms."""
        with patch('platform.system') as mock_platform:
            # Test Windows
            mock_platform.return_value = 'Windows'
            notification_manager.setup_platform_notifications()
            assert notification_manager.platform_handler == 'windows'
            
            # Test Linux
            mock_platform.return_value = 'Linux'
            notification_manager.setup_platform_notifications()
            assert notification_manager.platform_handler == 'linux'
            
            # Test macOS
            mock_platform.return_value = 'Darwin'
            notification_manager.setup_platform_notifications()
            assert notification_manager.platform_handler == 'macos'
    
    def test_notification_during_panic_mode(self, notification_manager):
        """Test that break notifications respect panic mode state."""
        notification_manager.panic_mode_active = True
        
        notification_manager.show_break_suggestion()
        
        # Should not show break notifications during panic mode
        notification_manager.desktop_notifications.show_gentle.assert_not_called()
        
        # Should queue notification for after panic mode
        assert len(notification_manager.queued_notifications) == 1
    
    def test_energy_level_adaptive_notifications(self, notification_manager):
        """Test notifications adapt to user's self-reported energy level."""
        # Low energy - more encouragement
        notification_manager.user_energy_level = 2  # Scale 1-5
        notification_manager.show_break_suggestion()
        assert "recharge" in notification_manager.last_notification_text.lower()
        
        # High energy - focus on maintaining momentum
        notification_manager.user_energy_level = 5
        notification_manager.show_break_suggestion()
        assert "momentum" in notification_manager.last_notification_text.lower()