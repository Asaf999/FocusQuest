"""
Main window for FocusQuest - ADHD-optimized learning interface
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QLabel, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QKeySequence, QAction, QPalette, QColor, QShortcut
from typing import Optional

from src.ui.problem_widget import ProblemWidget
from src.ui.xp_widget import XPWidget
from src.ui.styles import DARK_THEME_STYLE


class FocusQuestWindow(QMainWindow):
    """Main application window with ADHD optimizations"""
    
    # Signals
    problem_completed = pyqtSignal(int)  # Problem ID
    problem_skipped = pyqtSignal(int)  # Problem ID
    session_paused = pyqtSignal()
    focus_mode_toggled = pyqtSignal(bool)
    panic_mode_started = pyqtSignal()
    panic_mode_ended = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.current_problem = None
        self.focus_mode = False
        self.panic_mode = False
        self.panic_overlay = None
        self.panic_state = {}
        self.init_ui()
        self.setup_shortcuts()
        self.apply_dark_theme()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("FocusQuest")
        self.setMinimumSize(800, 600)
        
        # Central widget with main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main vertical layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Top bar with XP/Level (hideable)
        self.top_bar = QWidget()
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        self.xp_widget = XPWidget()
        top_layout.addWidget(self.xp_widget)
        top_layout.addStretch()
        
        main_layout.addWidget(self.top_bar)
        
        # Problem display area (always visible)
        self.problem_stack = QStackedWidget()
        self.problem_widget = None  # Will be set when problem loaded
        main_layout.addWidget(self.problem_stack, stretch=1)
        
        # Bottom action bar
        self.action_bar = QWidget()
        action_layout = QHBoxLayout(self.action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)
        
        # Hint button
        self.hint_button = QPushButton("💡 Hint (Space)")
        self.hint_button.setObjectName("hintButton")
        self.hint_button.clicked.connect(self.show_hint)
        action_layout.addWidget(self.hint_button)
        
        # Skip button
        self.skip_button = QPushButton("⏭️ Skip for now")
        self.skip_button.setObjectName("skipButton")
        self.skip_button.setMinimumHeight(40)
        self.skip_button.setToolTip("Take a strategic break from this problem - it will return when you're ready")
        self.skip_button.clicked.connect(self.skip_problem)
        action_layout.addWidget(self.skip_button)
        
        action_layout.addStretch()
        
        # Submit button
        self.submit_button = QPushButton("✓ Submit (Enter)")
        self.submit_button.setObjectName("submitButton")
        self.submit_button.setMinimumHeight(40)
        self.submit_button.clicked.connect(self.submit_answer)
        action_layout.addWidget(self.submit_button)
        
        main_layout.addWidget(self.action_bar)
        
        # Hide menu bar and status bar for minimal chrome
        self.menuBar().setVisible(False)
        self.setStatusBar(None)
        
        # Achievement widget (initially hidden)
        self.achievement_widget = QWidget()
        self.achievement_widget.hide()
        
    def setup_shortcuts(self):
        """Setup keyboard shortcuts for ADHD-friendly navigation"""
        # Hint shortcut (Space)
        self.show_hint_action = QAction("Show Hint", self)
        self.show_hint_action.setShortcut(QKeySequence(Qt.Key.Key_Space))
        self.show_hint_action.triggered.connect(self.show_hint)
        self.addAction(self.show_hint_action)
        
        # Submit shortcut (Enter)
        self.submit_action = QAction("Submit", self)
        self.submit_action.setShortcut(QKeySequence(Qt.Key.Key_Return))
        self.submit_action.triggered.connect(self.submit_answer)
        self.addAction(self.submit_action)
        
        # Pause shortcut (Esc)
        self.pause_action = QAction("Pause", self)
        self.pause_action.setShortcut(QKeySequence(Qt.Key.Key_Escape))
        self.pause_action.triggered.connect(self.pause_session)
        self.addAction(self.pause_action)
        
        # ADHD Panic button (ESC+P or Ctrl+P)
        self.panic_action = QAction("Panic Mode", self)
        self.panic_action.setShortcut(QKeySequence("Ctrl+P"))
        self.panic_action.triggered.connect(self.trigger_panic_mode)
        self.addAction(self.panic_action)
        
        # Skip problem (S key)
        self.skip_action = QAction("Skip Problem", self)
        self.skip_action.setShortcut(QKeySequence("S"))
        self.skip_action.triggered.connect(self.skip_problem)
        self.addAction(self.skip_action)
        
        # Focus mode (F)
        focus_shortcut = QShortcut(QKeySequence("F"), self)
        focus_shortcut.activated.connect(self.toggle_focus_mode)
        
        # Next step (Right arrow)
        next_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        next_shortcut.activated.connect(self.next_step)
        
    def apply_dark_theme(self):
        """Apply dark theme for reduced eye strain"""
        self.setStyleSheet(DARK_THEME_STYLE)
        
        # Also set palette for native widgets
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(60, 60, 60))
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        self.setPalette(palette)
        
    def load_problem(self, problem_data: dict):
        """Load a new problem for solving"""
        # Remove old problem widget if exists
        if self.problem_widget:
            self.problem_stack.removeWidget(self.problem_widget)
            self.problem_widget.deleteLater()
            
        # Create new problem widget
        self.problem_widget = ProblemWidget(problem_data)
        self.problem_widget.step_completed.connect(self.on_step_completed)
        self.problem_widget.problem_completed.connect(self.on_problem_completed)
        
        self.problem_stack.addWidget(self.problem_widget)
        self.problem_stack.setCurrentWidget(self.problem_widget)
        
        self.current_problem = problem_data
        
        # Reset UI state
        self.hint_button.setEnabled(True)
        self.submit_button.setEnabled(True)
        
    def show_hint(self):
        """Show next hint level"""
        if self.problem_widget:
            self.problem_widget.show_hint()
            
    def next_step(self):
        """Move to next step"""
        if self.problem_widget:
            self.problem_widget.next_step()
            
    def submit_answer(self):
        """Submit current answer"""
        if self.problem_widget:
            self.problem_widget.submit_current_step()
            
    def skip_problem(self):
        """Skip current problem with ADHD-friendly confirmation"""
        if not self.current_problem:
            return
            
        # Show ADHD-friendly confirmation dialog
        if self.show_skip_confirmation():
            problem_id = self.current_problem.get('id')
            if problem_id:
                self.problem_skipped.emit(problem_id)
                
    def show_skip_confirmation(self) -> bool:
        """Show ADHD-friendly skip confirmation dialog"""
        from PyQt6.QtWidgets import QMessageBox
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Strategic Learning Break")
        msg.setIcon(QMessageBox.Icon.Information)
        
        # ADHD-friendly messaging
        msg.setText(
            "Taking a strategic break from this problem! 🧠\n\n"
            "Sometimes stepping back helps our ADHD brains process better.\n"
            "This problem will return when you're ready for it."
        )
        
        # Custom button text
        msg.setStandardButtons(
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        
        ok_button = msg.button(QMessageBox.StandardButton.Ok)
        ok_button.setText("Skip for now ⏭️")
        
        cancel_button = msg.button(QMessageBox.StandardButton.Cancel)
        cancel_button.setText("Keep trying 💪")
        
        # Make it ADHD-friendly with positive colors
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #F0F8FB;
                border: 2px solid #B8D4DA;
                border-radius: 10px;
            }
            QMessageBox QLabel {
                color: #2C5F71;
                font-size: 13px;
                padding: 10px;
            }
            QPushButton {
                background-color: #E3F2FD;
                border: 2px solid #90CAF9;
                border-radius: 6px;
                padding: 8px 16px;
                color: #1565C0;
                font-weight: 500;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
        """)
        
        result = msg.exec()
        return result == QMessageBox.StandardButton.Ok
            
    def pause_session(self):
        """Pause the current session"""
        self.session_paused.emit()
        # Could show a pause overlay here
        
    def toggle_focus_mode(self):
        """Toggle distraction-free focus mode"""
        self.focus_mode = not self.focus_mode
        self.enter_focus_mode() if self.focus_mode else self.exit_focus_mode()
        self.focus_mode_toggled.emit(self.focus_mode)
        
    def enter_focus_mode(self):
        """Enter distraction-free mode"""
        self.top_bar.hide()
        self.achievement_widget.hide()
        # Could also hide window decorations on Linux
        
    def exit_focus_mode(self):
        """Exit focus mode"""
        self.top_bar.show()
        
    def on_step_completed(self, step_index: int):
        """Handle step completion"""
        # XP for completing a step
        self.xp_widget.add_xp(10)
        
    def on_problem_completed(self, problem_id: int):
        """Handle problem completion"""
        self.problem_completed.emit(problem_id)
        # Bigger XP reward for completing whole problem
        self.xp_widget.add_xp(50)
        
    def update_user_progress(self, xp: int, level: int, streak: int):
        """Update the displayed user progress"""
        self.xp_widget.set_xp(xp % 100, 100)  # XP within current level
        self.xp_widget.set_level(level)
        self.xp_widget.set_streak(streak)
    
    def trigger_panic_mode(self):
        """Enter ADHD panic mode - immediate relief"""
        if self.panic_mode:
            return  # Already in panic mode
            
        self.panic_mode = True
        self.panic_mode_started.emit()
        
        # Save current state
        if self.problem_widget:
            self.panic_state = {
                'step_index': getattr(self.problem_widget, 'current_step_index', 0),
                'elapsed_time': getattr(self.problem_widget, 'elapsed_time', 0)
            }
            # Pause timer
            if hasattr(self.problem_widget, 'pause_timer'):
                self.problem_widget.pause_timer()
        
        # Pause session
        if hasattr(self, 'session_manager'):
            self.session_manager.pause_session()
        
        # Create calming overlay
        self._create_panic_overlay()
        
    def _create_panic_overlay(self):
        """Create the panic mode overlay"""
        # Create full-screen overlay
        self.panic_overlay = QWidget(self)
        self.panic_overlay.setObjectName("panicOverlay")
        self.panic_overlay.setStyleSheet("""
            #panicOverlay {
                background-color: rgba(20, 20, 20, 0.95);
            }
        """)
        
        # Center layout
        layout = QVBoxLayout(self.panic_overlay)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(30)
        
        # Breathing guide widget
        self.panic_overlay.breathing_guide = QWidget()
        self.panic_overlay.breathing_guide.setFixedSize(200, 200)
        self.panic_overlay.breathing_guide.setStyleSheet("""
            QWidget {
                background-color: #4fc3f7;
                border-radius: 100px;
            }
        """)
        
        # Breathing animation
        self.panic_overlay.breathing_guide.animation = QPropertyAnimation(
            self.panic_overlay.breathing_guide, b"minimumSize"
        )
        self.panic_overlay.breathing_guide.animation.setDuration(4000)
        self.panic_overlay.breathing_guide.animation.setStartValue(self.panic_overlay.breathing_guide.size())
        self.panic_overlay.breathing_guide.animation.setEndValue(self.panic_overlay.breathing_guide.size() * 0.7)
        self.panic_overlay.breathing_guide.animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.panic_overlay.breathing_guide.animation.setLoopCount(-1)  # Infinite loop
        self.panic_overlay.breathing_guide.animation.start()
        
        layout.addWidget(self.panic_overlay.breathing_guide, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Calming message
        self.panic_overlay.message_label = QLabel(
            "Take a deep breath\n\n"
            "It's okay to pause\n\n"
            "You're doing great"
        )
        self.panic_overlay.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.panic_overlay.message_label.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 20pt;
                font-weight: 300;
                line-height: 1.5;
            }
        """)
        layout.addWidget(self.panic_overlay.message_label)
        
        # Resume button
        self.panic_overlay.resume_button = QPushButton("I'm ready to continue")
        self.panic_overlay.resume_button.setObjectName("resumeButton")
        self.panic_overlay.resume_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                font-size: 16pt;
                padding: 15px 30px;
                border-radius: 25px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5cbf60;
            }
        """)
        self.panic_overlay.resume_button.clicked.connect(self.resume_from_panic)
        layout.addWidget(self.panic_overlay.resume_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Show overlay
        self.panic_overlay.resize(self.size())
        self.panic_overlay.show()
        self.panic_overlay.raise_()
        
        # Fade in effect
        opacity_effect = QGraphicsOpacityEffect()
        self.panic_overlay.setGraphicsEffect(opacity_effect)
        self.fade_animation = QPropertyAnimation(opacity_effect, b"opacity")
        self.fade_animation.setDuration(500)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
        
    def resume_from_panic(self):
        """Resume from panic mode"""
        if not self.panic_mode:
            return
            
        # Stop breathing animation
        if hasattr(self.panic_overlay, 'breathing_guide'):
            self.panic_overlay.breathing_guide.animation.stop()
        
        # Fade out and remove overlay
        opacity_effect = self.panic_overlay.graphicsEffect()
        if opacity_effect:
            self.fade_out_animation = QPropertyAnimation(opacity_effect, b"opacity")
            self.fade_out_animation.setDuration(300)
            self.fade_out_animation.setStartValue(1.0)
            self.fade_out_animation.setEndValue(0.0)
            self.fade_out_animation.finished.connect(self._cleanup_panic_overlay)
            self.fade_out_animation.start()
        else:
            self._cleanup_panic_overlay()
        
    def _cleanup_panic_overlay(self):
        """Clean up panic overlay after fade out"""
        if self.panic_overlay:
            self.panic_overlay.hide()
            self.panic_overlay.deleteLater()
            self.panic_overlay = None
        
        self.panic_mode = False
        self.panic_mode_ended.emit()
        
        # Resume timers
        if self.problem_widget and hasattr(self.problem_widget, 'resume_timer'):
            self.problem_widget.resume_timer()
        
        # Resume session
        if hasattr(self, 'session_manager'):
            self.session_manager.resume_session()
    
    def resizeEvent(self, event):
        """Handle window resize to keep panic overlay full screen"""
        super().resizeEvent(event)
        if self.panic_overlay and self.panic_overlay.isVisible():
            self.panic_overlay.resize(self.size())