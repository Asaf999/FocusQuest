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
        notification_manager.show_break_suggestion()
        
        # First notification should be subtle
        assert notification_manager.notification_level == 1
        notification_manager.desktop_notifications.show_gentle.assert_called_once()
        
        # If ignored, should escalate
        notification_manager.escalate_notification()
        assert notification_manager.notification_level == 2
        notification_manager.desktop_notifications.show_standard.assert_called_once()
        
        # Final escalation should be more prominent
        notification_manager.escalate_notification()
        assert notification_manager.notification_level == 3
        notification_manager.desktop_notifications.show_prominent.assert_called_once()
    
    def test_break_widget_adhd_optimizations(self):
        """Test that break widget follows ADHD design principles."""
        widget = BreakNotificationWidget()
        
        # Should have calming colors
        assert "background-color" in widget.styleSheet()
        assert any(color in widget.styleSheet().lower() for color in ["#e8f4f8", "#f0f8ff", "#e6f3ff"])
        
        # Should have positive messaging
        assert "Great work!" in widget.break_message.text() or "Well done!" in widget.break_message.text()
        
        # Should provide clear actions
        assert widget.take_break_btn.text() == "Take a 5-minute break 🧘"
        assert widget.continue_btn.text() == "Just 5 more minutes 💪"
        assert widget.settings_btn.text() == "Notification Settings ⚙️"
    
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
        # Test default gentle sound
        notification_manager.play_notification_sound(level=1)
        notification_manager.audio_player.play_gentle.assert_called_once()
        
        # Test escalated sound
        notification_manager.play_notification_sound(level=2)
        notification_manager.audio_player.play_standard.assert_called_once()
        
        # Test that sound can be disabled
        notification_manager.settings.audio_enabled = False
        notification_manager.play_notification_sound(level=1)
        # Should not call audio player when disabled
        assert notification_manager.audio_player.play_gentle.call_count == 1  # Only from first test
    
    def test_notification_persistence_after_dismissal(self, notification_manager):
        """Test that notifications gently persist if dismissed."""
        notification_manager.show_break_suggestion()
        
        # User dismisses notification
        notification_manager.on_notification_dismissed()
        
        # Should schedule a gentle reminder
        assert notification_manager.reminder_timer.isActive()
        assert notification_manager.reminder_timer.interval() == 120000  # 2 minutes
        
        # After reminder delay, should show again but more gently
        notification_manager.reminder_timer.timeout.emit()
        assert notification_manager.notification_level == 1  # Reset to gentle
    
    def test_break_achievement_tracking(self, notification_manager):
        """Test that taking breaks awards XP for ADHD motivation."""
        initial_xp = notification_manager.user_stats.total_xp if hasattr(notification_manager, 'user_stats') else 0
        
        notification_manager.on_break_taken()
        
        # Should award XP for self-care
        if hasattr(notification_manager, 'user_stats'):
            assert notification_manager.user_stats.total_xp > initial_xp
        
        # Should emit achievement signal
        notification_manager.achievement_unlocked.emit.assert_called()
    
    def test_integration_with_session_manager(self, session_manager, notification_manager):
        """Test integration between session manager and notification system."""
        # Connect signals
        session_manager.break_suggested.connect(notification_manager.show_break_suggestion)
        
        # Start session and fast-forward time
        session_manager.start_session()
        session_manager.session_time = 60 * session_manager.break_interval  # Trigger break
        
        # Check session time should trigger break suggestion
        session_manager.check_session_time()
        
        # Should have shown break notification
        notification_manager.desktop_notifications.show_gentle.assert_called_once()
    
    def test_hyperfocus_protection_mode(self, notification_manager):
        """Test special handling when user is in deep focus."""
        notification_manager.detect_hyperfocus_mode()
        
        # In hyperfocus mode, notifications should be extra gentle
        notification_manager.show_break_suggestion()
        
        assert notification_manager.hyperfocus_mode is True
        notification_manager.desktop_notifications.show_ultra_gentle.assert_called_once()
        
        # Should use longer intervals between reminders
        assert notification_manager.reminder_timer.interval() > 300000  # > 5 minutes
    
    def test_medication_timing_awareness(self, notification_manager):
        """Test that notifications can adapt to medication schedules."""
        # Set medication timing
        notification_manager.settings.medication_times = ["08:00", "14:00"]
        
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value.hour = 8
            mock_datetime.now.return_value.time.return_value.minute = 30
            
            notification_manager.show_break_suggestion()
            
            # Should include medication reminder in break suggestion
            assert "medication" in notification_manager.last_notification_text.lower()
    
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
        # User takes several breaks
        for i in range(3):
            notification_manager.on_break_taken()
        
        stats = notification_manager.get_break_statistics()
        
        assert stats['breaks_today'] == 3
        assert stats['break_consistency'] >= 0  # Should calculate consistency score
        assert 'average_session_length' in stats
        
        # Should provide ADHD-specific insights
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