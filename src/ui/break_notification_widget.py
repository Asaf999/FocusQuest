"""
ADHD-optimized break notification widget with calming design and positive messaging.
Provides gentle, non-intrusive break suggestions with clear action options.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                           QProgressBar, QFrame, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, Qt
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap, QPainter, QLinearGradient
import logging

logger = logging.getLogger(__name__)


class BreakNotificationWidget(QWidget):
    """
    ADHD-friendly break notification widget with calming visual design.
    Features gentle animations, positive messaging, and clear action buttons.
    """
    
    # Signals for user actions
    break_taken = pyqtSignal(int)  # break_duration_minutes
    break_postponed = pyqtSignal(int)  # postpone_minutes
    settings_requested = pyqtSignal()
    widget_closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Widget properties
        self.setWindowTitle("Break Time - FocusQuest")
        self.setFixedSize(400, 280)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # State tracking
        self.break_countdown = 0
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._update_countdown)
        
        # Animations
        self.fade_animation = None
        self.setup_ui()
        self.setup_styling()
        self.setup_animations()
        
    def setup_ui(self):
        """Create ADHD-optimized UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header with calming icon and title
        header_layout = QHBoxLayout()
        
        # Icon (using emoji for now, could be replaced with actual icon)
        icon_label = QLabel("🧘")
        icon_label.setFont(QFont("Arial", 32))
        icon_label.setStyleSheet("color: #4A90A4; margin-right: 10px;")
        
        # Title and subtitle
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        self.title_label = QLabel("Time for a mindful break!")
        self.title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #2C5F71; margin: 0;")
        
        self.subtitle_label = QLabel("Your brain has earned some rest 💙")
        self.subtitle_label.setFont(QFont("Arial", 11))
        self.subtitle_label.setStyleSheet("color: #5A7C87; margin: 0;")
        
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)
        
        header_layout.addWidget(icon_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Encouraging message area
        self.break_message = QLabel()
        self.break_message.setWordWrap(True)
        self.break_message.setFont(QFont("Arial", 12))
        self.break_message.setStyleSheet("""
            color: #3D6A75;
            background-color: #F0F8FB;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #D1E7ED;
            line-height: 1.4;
        """)
        self.break_message.setText(
            "Great work! You've been focused and productive. Taking a short break "
            "helps your ADHD brain reset and maintain that awesome momentum. 🌟"
        )
        
        main_layout.addWidget(self.break_message)
        
        # Progress bar for session visualization (optional)
        self.session_progress = QProgressBar()
        self.session_progress.setMaximum(100)
        self.session_progress.setValue(75)  # Example: 75% through session
        self.session_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #D1E7ED;
                border-radius: 5px;
                background-color: #F0F8FB;
                text-align: center;
                font-size: 10px;
                color: #5A7C87;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #87CEEB, stop:1 #4A90A4);
                border-radius: 3px;
            }
        """)
        self.session_progress.setFormat("Session Progress: %p%")
        
        main_layout.addWidget(self.session_progress)
        
        # Action buttons with ADHD-friendly design
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Take break button (primary action)
        self.take_break_btn = QPushButton("Take a 5-minute break 🧘")
        self.take_break_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.take_break_btn.clicked.connect(lambda: self.take_break(5))
        
        # Continue working button (gentle alternative)
        self.continue_btn = QPushButton("Just 5 more minutes 💪")
        self.continue_btn.setFont(QFont("Arial", 11))
        self.continue_btn.clicked.connect(lambda: self.postpone_break(5))
        
        button_layout.addWidget(self.take_break_btn)
        button_layout.addWidget(self.continue_btn)
        
        main_layout.addLayout(button_layout)
        
        # Secondary actions
        secondary_layout = QHBoxLayout()
        
        # Quick break options
        quick_break_label = QLabel("Or take a:")
        quick_break_label.setFont(QFont("Arial", 9))
        quick_break_label.setStyleSheet("color: #7A9BA6;")
        
        self.micro_break_btn = QPushButton("2min stretch")
        self.micro_break_btn.setFont(QFont("Arial", 9))
        self.micro_break_btn.clicked.connect(lambda: self.take_break(2))
        
        self.short_break_btn = QPushButton("10min walk")
        self.short_break_btn.setFont(QFont("Arial", 9))
        self.short_break_btn.clicked.connect(lambda: self.take_break(10))
        
        # Settings button
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFont(QFont("Arial", 12))
        self.settings_btn.setMaximumWidth(35)
        self.settings_btn.setToolTip("Notification Settings")
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        
        secondary_layout.addWidget(quick_break_label)
        secondary_layout.addWidget(self.micro_break_btn)
        secondary_layout.addWidget(self.short_break_btn)
        secondary_layout.addStretch()
        secondary_layout.addWidget(self.settings_btn)
        
        main_layout.addLayout(secondary_layout)
        
        # Countdown display (hidden initially)
        self.countdown_frame = QFrame()
        countdown_layout = QVBoxLayout(self.countdown_frame)
        
        self.countdown_label = QLabel("Break ending in: 05:00")
        self.countdown_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.countdown_label.setStyleSheet("color: #4A90A4; text-align: center;")
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.end_break_btn = QPushButton("End Break Early ✨")
        self.end_break_btn.setFont(QFont("Arial", 11))
        self.end_break_btn.clicked.connect(self.end_break_early)
        
        countdown_layout.addWidget(self.countdown_label)
        countdown_layout.addWidget(self.end_break_btn)
        
        main_layout.addWidget(self.countdown_frame)
        self.countdown_frame.hide()  # Hidden until break starts
        
    def setup_styling(self):
        """Apply ADHD-friendly styling with calming colors."""
        self.setStyleSheet("""
            BreakNotificationWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F8FCFD, stop:1 #E8F4F8);
                border: 2px solid #B8D4DA;
                border-radius: 15px;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #E3F2FD, stop:1 #BBDEFB);
                border: 2px solid #90CAF9;
                border-radius: 8px;
                padding: 8px 16px;
                color: #1565C0;
                font-weight: 500;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #BBDEFB, stop:1 #90CAF9);
                border-color: #64B5F6;
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #90CAF9, stop:1 #64B5F6);
            }
            
            /* Primary action button styling */
            QPushButton#take_break_btn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #C8E6C9, stop:1 #A5D6A7);
                border: 2px solid #81C784;
                color: #2E7D32;
            }
            
            QPushButton#take_break_btn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #A5D6A7, stop:1 #81C784);
            }
            
            /* Secondary buttons */
            QPushButton#micro_break_btn, 
            QPushButton#short_break_btn {
                background: #F3E5F5;
                border: 1px solid #CE93D8;
                color: #7B1FA2;
                padding: 4px 8px;
                font-size: 9px;
            }
            
            QPushButton#settings_btn {
                background: #FFF3E0;
                border: 1px solid #FFCC02;
                color: #F57C00;
            }
        """)
        
        # Apply specific object names for styling
        self.take_break_btn.setObjectName("take_break_btn")
        self.micro_break_btn.setObjectName("micro_break_btn")
        self.short_break_btn.setObjectName("short_break_btn")
        self.settings_btn.setObjectName("settings_btn")
        
    def setup_animations(self):
        """Setup gentle animations for ADHD-friendly transitions."""
        # Fade in animation
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(800)  # Gentle 800ms fade
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
    def show_animated(self):
        """Show widget with gentle fade-in animation."""
        self.setWindowOpacity(0)
        self.show()
        
        self.fade_animation.setStartValue(0)
        self.fade_animation.setEndValue(1)
        self.fade_animation.start()
        
    def take_break(self, duration_minutes: int):
        """Handle break taken action."""
        logger.info(f"User taking {duration_minutes} minute break")
        
        # Update UI for break mode
        self._switch_to_break_mode(duration_minutes)
        
        # Emit signal
        self.break_taken.emit(duration_minutes)
        
    def postpone_break(self, postpone_minutes: int):
        """Handle break postponement."""
        logger.info(f"Break postponed for {postpone_minutes} minutes")
        
        # Show encouraging message
        self.break_message.setText(
            f"That's okay! We'll gently remind you again in {postpone_minutes} minutes. "
            f"Keep up the great work! 💪"
        )
        
        # Emit signal and close after delay
        self.break_postponed.emit(postpone_minutes)
        QTimer.singleShot(2000, self.close)  # Close after 2 seconds
        
    def _switch_to_break_mode(self, duration_minutes: int):
        """Switch UI to break countdown mode."""
        # Hide main content
        for i in range(self.layout().count() - 1):  # Keep countdown frame
            item = self.layout().itemAt(i)
            if item.widget() != self.countdown_frame:
                item.widget().hide()
                
        # Show countdown frame
        self.countdown_frame.show()
        
        # Start countdown
        self.break_countdown = duration_minutes * 60  # Convert to seconds
        self.countdown_timer.start(1000)  # Update every second
        self._update_countdown()
        
    def _update_countdown(self):
        """Update break countdown display."""
        if self.break_countdown <= 0:
            self.countdown_timer.stop()
            self._break_finished()
            return
            
        # Update display
        minutes = self.break_countdown // 60
        seconds = self.break_countdown % 60
        self.countdown_label.setText(f"Break ending in: {minutes:02d}:{seconds:02d}")
        
        # Decrease countdown
        self.break_countdown -= 1
        
    def _break_finished(self):
        """Handle break completion."""
        # Show completion message
        self.countdown_label.setText("Break complete! Ready to continue? ✨")
        self.end_break_btn.setText("Continue with renewed focus! 🎯")
        
        # Auto-close after showing completion message
        QTimer.singleShot(3000, self.close)
        
    def end_break_early(self):
        """Handle early break ending."""
        self.countdown_timer.stop()
        logger.info("Break ended early by user")
        
        # Show positive message
        self.countdown_label.setText("Great! Feeling refreshed and ready to go! 🌟")
        
        # Close after brief message
        QTimer.singleShot(1500, self.close)
        
    def closeEvent(self, event):
        """Handle widget close event."""
        self.countdown_timer.stop()
        self.widget_closed.emit()
        super().closeEvent(event)
        
    def update_message(self, message: str):
        """Update the break message with personalized content."""
        self.break_message.setText(message)
        
    def update_session_progress(self, percentage: int):
        """Update session progress visualization."""
        self.session_progress.setValue(max(0, min(100, percentage)))
        
    def set_energy_adaptive_styling(self, energy_level: int):
        """Adapt styling based on user's energy level (1-5)."""
        if energy_level <= 2:  # Low energy - warmer, more encouraging colors
            self.setStyleSheet(self.styleSheet() + """
                BreakNotificationWidget {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FFF8E1, stop:1 #FFECB3);
                }
            """)
            self.break_message.setText(
                "You're doing amazing work even when energy is low! 🌱 "
                "A gentle break will help you recharge and feel more centered."
            )
        elif energy_level >= 4:  # High energy - focus on maintaining momentum
            self.setStyleSheet(self.styleSheet() + """
                BreakNotificationWidget {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #E8F5E8, stop:1 #C8E6C9);
                }
            """)
            self.break_message.setText(
                "Fantastic energy today! 🔥 A quick break will help you maintain "
                "this wonderful momentum and stay sharp for what's ahead."
            )