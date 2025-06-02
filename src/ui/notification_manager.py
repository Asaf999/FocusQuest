"""
ADHD-optimized notification manager for break suggestions and system alerts.
Implements gentle, escalating notifications that respect user focus states.
"""
import json
import platform
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Optional
import logging

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QSettings
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtMultimedia import QSoundEffect, QAudioOutput, QMediaPlayer
from PyQt6.QtCore import QUrl

try:
    from plyer import notification as desktop_notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    logging.warning("plyer not available - desktop notifications will be limited")

logger = logging.getLogger(__name__)


class NotificationSettings:
    """Settings for ADHD-optimized notifications."""
    
    def __init__(self):
        self.audio_enabled = True
        self.desktop_notifications_enabled = True
        self.escalation_enabled = True
        self.reminder_interval = 120  # seconds between gentle reminders
        self.max_escalation_level = 3
        self.hyperfocus_detection = True
        self.medication_reminders = True
        self.medication_times = ["08:00", "14:00"]  # Default medication times
        self.energy_adaptive = True
        self.gentle_mode = True  # Extra gentle for sensory sensitivity


class NotificationManager(QObject):
    """
    ADHD-optimized notification system with gentle escalation and user respect.
    Provides system tray integration, desktop notifications, and audio alerts.
    """
    
    # Signals for achievements and user actions
    achievement_unlocked = pyqtSignal(str, int)  # achievement_name, xp_gained
    break_taken = pyqtSignal(int)  # break_duration_minutes
    notification_dismissed = pyqtSignal(int)  # notification_level
    settings_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Core components
        self.settings = NotificationSettings()
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.current_break_widget = None
        
        # Notification state
        self.notification_level = 0  # 0=none, 1=gentle, 2=standard, 3=prominent
        self.hyperfocus_mode = False
        self.panic_mode_active = False
        self.user_energy_level = 3  # 1-5 scale
        self.last_notification_text = ""
        self.queued_notifications = []
        
        # Timers
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self._show_gentle_reminder)
        
        self.break_timer = QTimer(self)
        self.break_timer.timeout.connect(self._update_break_timer)
        
        self.escalation_timer = QTimer(self)
        self.escalation_timer.timeout.connect(self.escalate_notification)
        
        # Break tracking
        self.break_duration = 0
        self.break_time_remaining = 0
        self.breaks_today = 0
        self.session_breaks = []
        
        # Audio system
        self.audio_player = None
        self.sound_files = {
            'gentle': 'assets/sounds/gentle_chime.wav',
            'standard': 'assets/sounds/soft_bell.wav', 
            'prominent': 'assets/sounds/attention_tone.wav'
        }
        
        # Platform-specific handlers
        self.platform_handler = None
        self.setup_platform_notifications()
        
        # Load saved settings
        self.load_settings()
        
        # Initialize components
        self.setup_system_tray()
        self.setup_audio()
    
    def setup_system_tray(self):
        """Initialize system tray icon with ADHD-friendly menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray not available")
            return
            
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Set icon (you may need to adjust path)
        icon_path = Path("assets/icons/focusquest_tray.png")
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            # Fallback to app icon
            self.tray_icon.setIcon(QApplication.instance().style().standardIcon(QApplication.instance().style().StandardPixmap.SP_ComputerIcon))
        
        # Create context menu
        menu = QMenu()
        
        # Session status
        self.status_action = QAction("Study Session Active", self)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        
        menu.addSeparator()
        
        # Break actions
        break_now_action = QAction("Take Break Now 🧘", self)
        break_now_action.triggered.connect(self._manual_break_request)
        menu.addAction(break_now_action)
        
        skip_break_action = QAction("Skip This Break ⏭️", self)
        skip_break_action.triggered.connect(self._skip_break)
        menu.addAction(skip_break_action)
        
        menu.addSeparator()
        
        # Energy level submenu
        energy_menu = menu.addMenu("Energy Level 🔋")
        for level in range(1, 6):
            action = QAction(f"Level {level} {'⭐' * level}", self)
            action.triggered.connect(lambda checked, l=level: self.set_energy_level(l))
            energy_menu.addAction(action)
        
        menu.addSeparator()
        
        # Settings and quit
        settings_action = QAction("Notification Settings ⚙️", self)
        settings_action.triggered.connect(self.settings_requested.emit)
        menu.addAction(settings_action)
        
        quit_action = QAction("Quit FocusQuest", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.setToolTip("FocusQuest - Study Session Active")
        
        # Show tray icon
        self.tray_icon.show()
        
        logger.info("System tray icon initialized")
    
    def setup_audio(self):
        """Initialize audio system for gentle notification sounds."""
        try:
            # Create audio players for different notification levels
            self.audio_player = {}
            
            for level, sound_file in self.sound_files.items():
                if Path(sound_file).exists():
                    player = QMediaPlayer()
                    player.setSource(QUrl.fromLocalFile(str(Path(sound_file).absolute())))
                    self.audio_player[level] = player
                    
        except Exception as e:
            logger.warning(f"Audio setup failed: {e}")
            self.audio_player = None
    
    def setup_platform_notifications(self):
        """Setup platform-specific notification handlers."""
        system = platform.system()
        
        if system == 'Windows':
            self.platform_handler = 'windows'
        elif system == 'Linux':
            self.platform_handler = 'linux'
        elif system == 'Darwin':
            self.platform_handler = 'macos'
        else:
            self.platform_handler = 'generic'
            
        logger.info(f"Platform notification handler: {self.platform_handler}")
    
    def show_break_suggestion(self):
        """
        Show ADHD-optimized break suggestion with gentle escalation.
        Respects user's current state and energy level.
        """
        # Don't show notifications during panic mode
        if self.panic_mode_active:
            self.queued_notifications.append('break_suggestion')
            return
            
        # Detect hyperfocus mode
        if self.settings.hyperfocus_detection:
            self.detect_hyperfocus_mode()
            
        # Start with gentle notification
        self.notification_level = 1
        
        # Craft ADHD-friendly message based on energy level
        message = self._create_break_message()
        self.last_notification_text = message
        
        # Show appropriate notification type
        if self.hyperfocus_mode:
            self._show_ultra_gentle_notification(message)
        else:
            self._show_gentle_notification(message)
            
        # Setup escalation timer if enabled
        if self.settings.escalation_enabled:
            self.escalation_timer.start(30000)  # 30 seconds
            
        # Play audio if enabled
        if self.settings.audio_enabled:
            self.play_notification_sound(level=1)
            
        logger.info(f"Break suggestion shown (level {self.notification_level})")
    
    def _create_break_message(self) -> str:
        """Create personalized break message based on user state."""
        base_messages = {
            1: "Time for a gentle break! 🌱",
            2: "You've been focused for a while - ready for a quick recharge? 🔋", 
            3: "Your brain has earned a well-deserved break! 🧠✨",
            4: "Amazing focus! Let's take a moment to recharge and celebrate. 🎉",
            5: "Incredible work! Time to maintain that momentum with a energizing break. ⚡"
        }
        
        message = base_messages.get(self.user_energy_level, base_messages[3])
        
        # Add medication reminder if applicable
        if self.settings.medication_reminders and self._is_medication_time():
            message += "\n\n💊 Friendly reminder: Medication time!"
            
        # Add encouragement based on break consistency
        if self.breaks_today > 0:
            message += f"\n\n🌟 Great job taking {self.breaks_today} breaks today!"
            
        return message
    
    def _show_gentle_notification(self, message: str):
        """Show gentle desktop notification."""
        if not self.settings.desktop_notifications_enabled:
            return
            
        if PLYER_AVAILABLE:
            try:
                desktop_notification.notify(
                    title="FocusQuest Break Time 🧘",
                    message=message,
                    app_name="FocusQuest",
                    timeout=8,  # Gentle timeout
                )
            except Exception as e:
                logger.warning(f"Desktop notification failed: {e}")
                
        # Update tray icon to show break suggestion
        if self.tray_icon:
            self.tray_icon.showMessage(
                "Break Time 🧘",
                message,
                QSystemTrayIcon.MessageIcon.Information,
                8000  # 8 seconds
            )
    
    def _show_ultra_gentle_notification(self, message: str):
        """Show extra gentle notification for hyperfocus protection."""
        # Even more subtle for hyperfocus mode
        if self.tray_icon:
            self.tray_icon.setToolTip(f"Break suggested: {message}")
            # Very brief, non-intrusive tray message
            self.tray_icon.showMessage(
                "Gentle break reminder",
                "When you're ready 🌱",
                QSystemTrayIcon.MessageIcon.Information,
                3000  # Very brief
            )
    
    def escalate_notification(self):
        """Escalate notification intensity gradually."""
        if not self.settings.escalation_enabled:
            return
            
        if self.notification_level >= self.settings.max_escalation_level:
            self.escalation_timer.stop()
            return
            
        self.notification_level += 1
        
        # Show escalated notification
        if self.notification_level == 2:
            self._show_standard_notification()
        elif self.notification_level == 3:
            self._show_prominent_notification()
            
        # Play escalated audio
        if self.settings.audio_enabled:
            self.play_notification_sound(level=self.notification_level)
            
        # Continue escalation timer
        self.escalation_timer.start(60000)  # 1 minute intervals
        
        logger.info(f"Notification escalated to level {self.notification_level}")
    
    def _show_standard_notification(self):
        """Show standard intensity notification."""
        message = self.last_notification_text + "\n\nYour focus session has been quite long! 💙"
        
        if PLYER_AVAILABLE:
            try:
                desktop_notification.notify(
                    title="Break Reminder 💙",
                    message=message,
                    app_name="FocusQuest",
                    timeout=12,
                )
            except Exception:
                pass
                
        if self.tray_icon:
            self.tray_icon.showMessage(
                "Break Reminder 💙",
                message,
                QSystemTrayIcon.MessageIcon.Information,
                12000
            )
    
    def _show_prominent_notification(self):
        """Show prominent notification as final escalation."""
        message = "Taking breaks is an important part of ADHD self-care! 💜\n\nEven 2 minutes helps reset your focus. 🧘‍♀️"
        
        if PLYER_AVAILABLE:
            try:
                desktop_notification.notify(
                    title="Self-Care Reminder 💜",
                    message=message,
                    app_name="FocusQuest",
                    timeout=15,
                )
            except Exception:
                pass
                
        if self.tray_icon:
            self.tray_icon.showMessage(
                "Self-Care Reminder 💜",
                message,
                QSystemTrayIcon.MessageIcon.Information,
                15000
            )
    
    def play_notification_sound(self, level: int):
        """Play gentle audio notification based on level."""
        if not self.settings.audio_enabled or not self.audio_player:
            return
            
        sound_map = {1: 'gentle', 2: 'standard', 3: 'prominent'}
        sound_type = sound_map.get(level, 'gentle')
        
        if sound_type in self.audio_player:
            try:
                self.audio_player[sound_type].play()
            except Exception as e:
                logger.warning(f"Audio playback failed: {e}")
    
    def on_notification_dismissed(self):
        """Handle when user dismisses notification."""
        self.notification_dismissed.emit(self.notification_level)
        
        # Reset escalation
        self.escalation_timer.stop()
        self.notification_level = 0
        
        # Schedule gentle reminder if not in hyperfocus mode
        if not self.hyperfocus_mode:
            reminder_delay = self.settings.reminder_interval * 1000
            self.reminder_timer.start(reminder_delay)
            
        logger.info("Notification dismissed, gentle reminder scheduled")
    
    def _show_gentle_reminder(self):
        """Show gentle reminder after dismissal."""
        self.reminder_timer.stop()
        
        # Show very gentle reminder
        message = "Just a gentle reminder when you're ready! 🌸"
        
        if self.tray_icon:
            self.tray_icon.showMessage(
                "When you're ready 🌸",
                message,
                QSystemTrayIcon.MessageIcon.Information,
                5000
            )
    
    def start_break_timer(self, duration: int):
        """Start break countdown timer."""
        self.break_duration = duration
        self.break_time_remaining = duration
        self.break_timer.start(1000)  # Update every second
        
        logger.info(f"Break timer started for {duration} seconds")
    
    def _update_break_timer(self):
        """Update break countdown timer."""
        self.break_time_remaining -= 1
        
        # Update tray icon tooltip with countdown
        if self.tray_icon:
            minutes = self.break_time_remaining // 60
            seconds = self.break_time_remaining % 60
            self.tray_icon.setToolTip(f"Break time: {minutes:02d}:{seconds:02d} remaining")
            
        # Break time finished
        if self.break_time_remaining <= 0:
            self.break_timer.stop()
            self._break_completed()
    
    def _break_completed(self):
        """Handle break completion."""
        self.breaks_today += 1
        self.break_taken.emit(self.break_duration // 60)  # Convert to minutes
        
        # Award XP for taking break
        xp_gained = 10 + (self.break_duration // 60) * 2  # Base 10 + 2 per minute
        self.achievement_unlocked.emit("Self-Care Champion", xp_gained)
        
        # Show completion message
        if self.tray_icon:
            self.tray_icon.showMessage(
                "Break Complete! 🎉",
                f"Great job taking care of yourself! +{xp_gained} XP",
                QSystemTrayIcon.MessageIcon.Information,
                5000
            )
            self.tray_icon.setToolTip("FocusQuest - Ready to continue!")
            
        logger.info(f"Break completed, awarded {xp_gained} XP")
    
    def on_break_taken(self):
        """Handle when user takes a break."""
        self.escalation_timer.stop()
        self.reminder_timer.stop()
        self.notification_level = 0
        
        # Start break timer (default 5 minutes)
        self.start_break_timer(300)
        
        logger.info("User took break, starting break timer")
    
    def detect_hyperfocus_mode(self):
        """Detect if user is in hyperfocus state."""
        # This is a placeholder for more sophisticated detection
        # Could use typing patterns, mouse activity, time since last break, etc.
        
        # For now, simple heuristic: if no breaks for > 2 hours, assume hyperfocus
        if len(self.session_breaks) == 0 or \
           (datetime.now() - self.session_breaks[-1]).total_seconds() > 7200:
            self.hyperfocus_mode = True
        else:
            self.hyperfocus_mode = False
            
        logger.debug(f"Hyperfocus mode: {self.hyperfocus_mode}")
    
    def _is_medication_time(self) -> bool:
        """Check if current time matches medication schedule."""
        if not self.settings.medication_reminders:
            return False
            
        current_time = datetime.now().time()
        current_str = current_time.strftime("%H:%M")
        
        # Check if within 30 minutes of medication time
        for med_time_str in self.settings.medication_times:
            med_time = datetime.strptime(med_time_str, "%H:%M").time()
            
            # Simple 30-minute window check
            med_minutes = med_time.hour * 60 + med_time.minute
            current_minutes = current_time.hour * 60 + current_time.minute
            
            if abs(med_minutes - current_minutes) <= 30:
                return True
                
        return False
    
    def set_energy_level(self, level: int):
        """Set user's current energy level (1-5)."""
        self.user_energy_level = max(1, min(5, level))
        logger.info(f"Energy level set to {self.user_energy_level}")
    
    def set_panic_mode(self, active: bool):
        """Set panic mode state."""
        self.panic_mode_active = active
        
        if not active and self.queued_notifications:
            # Process queued notifications after panic mode
            for notification in self.queued_notifications:
                if notification == 'break_suggestion':
                    self.show_break_suggestion()
            self.queued_notifications.clear()
    
    def get_break_statistics(self) -> Dict:
        """Get break-taking statistics for insights."""
        total_breaks = len(self.session_breaks)
        
        stats = {
            'breaks_today': self.breaks_today,
            'total_session_breaks': total_breaks,
            'break_consistency': self._calculate_break_consistency(),
            'average_session_length': self._calculate_average_session_length(),
            'last_break': self.session_breaks[-1] if self.session_breaks else None
        }
        
        return stats
    
    def get_adhd_insights(self) -> List[str]:
        """Generate ADHD-specific insights about break patterns."""
        insights = []
        stats = self.get_break_statistics()
        
        if stats['breaks_today'] >= 3:
            insights.append("🌟 Excellent break rhythm today! You're taking great care of your ADHD brain.")
        elif stats['breaks_today'] == 0:
            insights.append("💙 Remember: breaks aren't procrastination, they're brain maintenance!")
        
        if stats['break_consistency'] > 0.8:
            insights.append("🎯 Your consistent break pattern shows strong self-awareness!")
            
        return insights
    
    def _calculate_break_consistency(self) -> float:
        """Calculate break consistency score (0-1)."""
        if len(self.session_breaks) < 2:
            return 0.0
            
        # Simple consistency based on regular intervals
        intervals = []
        for i in range(1, len(self.session_breaks)):
            interval = (self.session_breaks[i] - self.session_breaks[i-1]).total_seconds()
            intervals.append(interval)
            
        if not intervals:
            return 0.0
            
        # Calculate coefficient of variation (lower = more consistent)
        mean_interval = sum(intervals) / len(intervals)
        variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
        std_dev = variance ** 0.5
        
        if mean_interval == 0:
            return 0.0
            
        cv = std_dev / mean_interval
        consistency = max(0.0, 1.0 - cv)  # Invert so higher = more consistent
        
        return consistency
    
    def _calculate_average_session_length(self) -> int:
        """Calculate average session length between breaks in minutes."""
        if len(self.session_breaks) < 2:
            return 0
            
        total_time = (self.session_breaks[-1] - self.session_breaks[0]).total_seconds()
        num_sessions = len(self.session_breaks) - 1
        
        if num_sessions == 0:
            return 0
            
        average_seconds = total_time / num_sessions
        return int(average_seconds / 60)  # Convert to minutes
    
    def _manual_break_request(self):
        """Handle manual break request from tray menu."""
        self.on_break_taken()
    
    def _skip_break(self):
        """Handle break skip request."""
        self.escalation_timer.stop()
        self.reminder_timer.stop()
        self.notification_level = 0
        
        # Award small XP for conscious decision
        self.achievement_unlocked.emit("Mindful Choice", 5)
        
        logger.info("Break skipped by user")
    
    def save_settings(self):
        """Save notification settings to persistent storage."""
        settings = QSettings("FocusQuest", "NotificationManager")
        
        settings.setValue("audio_enabled", self.settings.audio_enabled)
        settings.setValue("desktop_notifications_enabled", self.settings.desktop_notifications_enabled)
        settings.setValue("escalation_enabled", self.settings.escalation_enabled)
        settings.setValue("reminder_interval", self.settings.reminder_interval)
        settings.setValue("max_escalation_level", self.settings.max_escalation_level)
        settings.setValue("hyperfocus_detection", self.settings.hyperfocus_detection)
        settings.setValue("medication_reminders", self.settings.medication_reminders)
        settings.setValue("medication_times", self.settings.medication_times)
        settings.setValue("energy_adaptive", self.settings.energy_adaptive)
        settings.setValue("gentle_mode", self.settings.gentle_mode)
        
        logger.info("Notification settings saved")
    
    def load_settings(self):
        """Load notification settings from persistent storage."""
        settings = QSettings("FocusQuest", "NotificationManager")
        
        self.settings.audio_enabled = settings.value("audio_enabled", True, type=bool)
        self.settings.desktop_notifications_enabled = settings.value("desktop_notifications_enabled", True, type=bool)
        self.settings.escalation_enabled = settings.value("escalation_enabled", True, type=bool)
        self.settings.reminder_interval = settings.value("reminder_interval", 120, type=int)
        self.settings.max_escalation_level = settings.value("max_escalation_level", 3, type=int)
        self.settings.hyperfocus_detection = settings.value("hyperfocus_detection", True, type=bool)
        self.settings.medication_reminders = settings.value("medication_reminders", True, type=bool)
        self.settings.medication_times = settings.value("medication_times", ["08:00", "14:00"], type=list)
        self.settings.energy_adaptive = settings.value("energy_adaptive", True, type=bool)
        self.settings.gentle_mode = settings.value("gentle_mode", True, type=bool)
        
        logger.info("Notification settings loaded")