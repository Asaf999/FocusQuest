"""
Main window for FocusQuest - ADHD-optimized learning interface
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QAction, QPalette, QColor, QShortcut
from typing import Optional

from src.ui.problem_widget import ProblemWidget
from src.ui.xp_widget import XPWidget
from src.ui.styles import DARK_THEME_STYLE


class FocusQuestWindow(QMainWindow):
    """Main application window with ADHD optimizations"""
    
    # Signals
    problem_completed = pyqtSignal(int)  # Problem ID
    session_paused = pyqtSignal()
    focus_mode_toggled = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.current_problem = None
        self.focus_mode = False
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