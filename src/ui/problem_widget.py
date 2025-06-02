"""
Problem display widget with ADHD-optimized step-by-step presentation
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QCheckBox, QTextEdit, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont
from typing import List, Dict


class StepWidget(QFrame):
    """Single step display with checkbox"""
    
    completed = pyqtSignal(int)  # Step index
    
    def __init__(self, step_data: dict, index: int):
        super().__init__()
        self.step_data = step_data
        self.index = index
        self.init_ui()
        
    def init_ui(self):
        """Initialize step UI"""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setObjectName("stepWidget")
        
        layout = QHBoxLayout(self)
        layout.setSpacing(15)
        
        # Checkbox for completion
        self.checkbox = QCheckBox()
        self.checkbox.setObjectName("stepCheckbox")
        self.checkbox.stateChanged.connect(self.on_checkbox_changed)
        layout.addWidget(self.checkbox)
        
        # Step content
        self.content_label = QLabel(self.step_data.get('content', ''))
        self.content_label.setWordWrap(True)
        self.content_label.setObjectName("stepContent")
        font = QFont()
        font.setPointSize(14)
        self.content_label.setFont(font)
        layout.addWidget(self.content_label, stretch=1)
        
        # Duration indicator
        duration = self.step_data.get('duration', 5)
        self.duration_label = QLabel(f"~{duration} min")
        self.duration_label.setObjectName("durationLabel")
        layout.addWidget(self.duration_label)
        
    def on_checkbox_changed(self, state):
        """Handle checkbox state change"""
        if state == Qt.CheckState.Checked.value:
            self.completed.emit(self.index)
            # Visual feedback
            self.setStyleSheet("#stepWidget { background-color: #2d4a2d; }")


class ProblemWidget(QWidget):
    """Main problem display with step-by-step progression"""
    
    step_completed = pyqtSignal(int)  # Step index
    problem_completed = pyqtSignal(int)  # Problem ID
    
    def __init__(self, problem_data: dict):
        super().__init__()
        self.problem_data = problem_data
        self.current_step = 0
        self.current_step_index = 0  # For panic state preservation
        self.current_hint_level = 0
        self.step_widgets: List[StepWidget] = []
        self.timer_paused = False
        self.init_ui()
        self.show_current_step()
        
    def init_ui(self):
        """Initialize problem UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Problem title/description
        self.problem_label = QLabel()
        self.problem_label.setWordWrap(True)
        self.problem_label.setObjectName("problemTitle")
        
        # Set problem text
        problem_text = self.problem_data.get('translated_text', 
                                            self.problem_data.get('original_text', ''))
        self.problem_label.setText(problem_text)
        
        # Large font for problem
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.problem_label.setFont(font)
        
        layout.addWidget(self.problem_label)
        
        # Hint area (initially hidden)
        self.hint_frame = QFrame()
        self.hint_frame.setObjectName("hintFrame")
        self.hint_frame.hide()
        
        hint_layout = QVBoxLayout(self.hint_frame)
        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setObjectName("hintText")
        hint_layout.addWidget(self.hint_label)
        
        layout.addWidget(self.hint_frame)
        
        # Steps area
        self.steps_scroll = QScrollArea()
        self.steps_scroll.setWidgetResizable(True)
        self.steps_scroll.setObjectName("stepsArea")
        
        self.steps_container = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.setSpacing(10)
        
        # Create step widgets
        steps = self.problem_data.get('steps', [])
        for i, step in enumerate(steps):
            step_widget = StepWidget(step, i)
            step_widget.completed.connect(self.on_step_completed)
            step_widget.hide()  # Initially hidden
            self.step_widgets.append(step_widget)
            self.steps_layout.addWidget(step_widget)
            
        self.steps_layout.addStretch()
        self.steps_scroll.setWidget(self.steps_container)
        layout.addWidget(self.steps_scroll, stretch=1)
        
        # Timer for current step
        self.timer_label = QLabel("Time: 0:00")
        self.timer_label.setObjectName("timerLabel")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.timer_label)
        
        # Setup timer
        self.step_timer = QTimer()
        self.step_timer.timeout.connect(self.update_timer)
        self.elapsed_time = 0
        
    def show_current_step(self):
        """Show only the current step"""
        # Update current_step_index for external access
        self.current_step_index = self.current_step
        
        # Hide all steps
        for widget in self.step_widgets:
            widget.hide()
            
        # Show current step with animation
        if self.current_step < len(self.step_widgets):
            current_widget = self.step_widgets[self.current_step]
            current_widget.show()
            
            # Scroll to make visible
            self.steps_scroll.ensureWidgetVisible(current_widget)
            
            # Reset timer
            self.elapsed_time = 0
            self.step_timer.start(1000)  # Update every second
            
            # Fade in animation
            self._animate_widget_opacity(current_widget)
            
    def _animate_widget_opacity(self, widget):
        """Animate widget appearance"""
        # PyQt6 opacity animation would go here
        # For now, just ensure it's visible
        widget.setVisible(True)
        
    def next_step(self):
        """Move to the next step"""
        if self.current_step < len(self.step_widgets) - 1:
            self.current_step += 1
            self.show_current_step()
            # Reset hint level for new step
            self.current_hint_level = 0
            self.hint_frame.hide()
            
    def show_hint(self):
        """Show the next hint level"""
        hints = self.problem_data.get('hints', [])
        
        if self.current_hint_level < len(hints):
            hint = hints[self.current_hint_level]
            self.hint_label.setText(f"Hint {hint['level']}: {hint['content']}")
            self.hint_frame.show()
            self.current_hint_level += 1
            
            # Animate hint appearance
            self._animate_widget_opacity(self.hint_frame)
            
    def submit_current_step(self):
        """Submit/complete the current step"""
        if self.current_step < len(self.step_widgets):
            # Check the checkbox programmatically
            current_widget = self.step_widgets[self.current_step]
            current_widget.checkbox.setChecked(True)
            
    def on_step_completed(self, step_index: int):
        """Handle step completion"""
        self.step_timer.stop()
        self.step_completed.emit(step_index)
        
        # Auto-advance after short delay
        QTimer.singleShot(1000, self.check_next_step)
        
    def check_next_step(self):
        """Check if we should advance to next step"""
        if self.current_step < len(self.step_widgets) - 1:
            self.next_step()
        else:
            # All steps completed
            problem_id = self.problem_data.get('id', 0)
            self.problem_completed.emit(problem_id)
            
    def update_timer(self):
        """Update the step timer display"""
        self.elapsed_time += 1
        minutes = self.elapsed_time // 60
        seconds = self.elapsed_time % 60
        self.timer_label.setText(f"Time: {minutes}:{seconds:02d}")
        
        # Check if taking too long (ADHD consideration)
        expected_duration = self.step_widgets[self.current_step].step_data.get('duration', 5) * 60
        if self.elapsed_time > expected_duration * 1.5:
            # Taking 50% longer than expected - maybe show encouragement
            self.timer_label.setStyleSheet("color: #ff9944;")  # Orange warning
    
    def pause_timer(self):
        """Pause the step timer (for panic mode)"""
        self.timer_paused = True
        self.step_timer.stop()
        
    def resume_timer(self):
        """Resume the step timer after panic mode"""
        if self.timer_paused:
            self.timer_paused = False
            self.step_timer.start(1000)