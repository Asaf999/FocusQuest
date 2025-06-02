"""
XP and progress tracking widget with gamification elements
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QProgressBar, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, pyqtSignal, QRect
from PyQt6.QtGui import QFont
from typing import Optional


class XPWidget(QWidget):
    """Display XP, level, and streak information"""
    
    level_up = pyqtSignal(int)  # New level
    achievement_unlocked = pyqtSignal(str)  # Achievement name
    
    def __init__(self):
        super().__init__()
        self.current_xp = 0
        self.current_level = 1
        self.current_streak = 0
        self.init_ui()
        
    def init_ui(self):
        """Initialize XP display UI"""
        layout = QHBoxLayout(self)
        layout.setSpacing(20)
        
        # Level display
        level_container = QVBoxLayout()
        level_container.setSpacing(2)
        
        self.level_label = QLabel("Level 1")
        self.level_label.setObjectName("levelLabel")
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        self.level_label.setFont(font)
        level_container.addWidget(self.level_label)
        
        self.level_title = QLabel("Novice Mathematician")
        self.level_title.setObjectName("levelTitle")
        level_container.addWidget(self.level_title)
        
        layout.addLayout(level_container)
        
        # XP Progress bar
        xp_container = QVBoxLayout()
        xp_container.setSpacing(2)
        
        self.xp_label = QLabel("XP: 0 / 100")
        self.xp_label.setObjectName("xpLabel")
        xp_container.addWidget(self.xp_label)
        
        self.xp_bar = QProgressBar()
        self.xp_bar.setObjectName("xpBar")
        self.xp_bar.setMinimum(0)
        self.xp_bar.setMaximum(100)
        self.xp_bar.setValue(0)
        self.xp_bar.setTextVisible(False)
        self.xp_bar.setMinimumWidth(200)
        xp_container.addWidget(self.xp_bar)
        
        layout.addLayout(xp_container)
        
        # Streak display
        streak_container = QVBoxLayout()
        streak_container.setSpacing(2)
        
        self.streak_label = QLabel("🔥 0 day streak")
        self.streak_label.setObjectName("streakLabel")
        font = QFont()
        font.setPointSize(14)
        self.streak_label.setFont(font)
        streak_container.addWidget(self.streak_label)
        
        self.streak_bonus = QLabel("")
        self.streak_bonus.setObjectName("streakBonus")
        streak_container.addWidget(self.streak_bonus)
        
        layout.addLayout(streak_container)
        
        layout.addStretch()
        
    def set_xp(self, current: int, maximum: int):
        """Set current XP within level"""
        self.current_xp = current
        self.xp_bar.setMaximum(maximum)
        self.xp_bar.setValue(current)
        self.xp_label.setText(f"XP: {current} / {maximum}")
        
    def add_xp(self, amount: int):
        """Add XP with animation"""
        old_xp = self.xp_bar.value()
        new_xp = old_xp + amount
        max_xp = self.xp_bar.maximum()
        
        if new_xp >= max_xp:
            # Level up!
            overflow = new_xp - max_xp
            self.animate_xp_gain(old_xp, max_xp)
            QTimer.singleShot(500, lambda: self.trigger_level_up(overflow))
        else:
            self.animate_xp_gain(old_xp, new_xp)
            
    def animate_xp_gain(self, start: int, end: int):
        """Animate XP bar filling"""
        # Simple animation - could be enhanced with QPropertyAnimation
        steps = 10
        increment = (end - start) / steps
        
        def update_step(step):
            if step <= steps:
                value = int(start + increment * step)
                self.xp_bar.setValue(value)
                self.xp_label.setText(f"XP: {value} / {self.xp_bar.maximum()}")
                QTimer.singleShot(50, lambda: update_step(step + 1))
                
        update_step(1)
        
    def trigger_level_up(self, overflow_xp: int):
        """Handle level up event"""
        self.current_level += 1
        self.set_level(self.current_level)
        self.level_up.emit(self.current_level)
        
        # Reset XP bar with overflow
        self.set_xp(overflow_xp, self.calculate_xp_for_level(self.current_level))
        
        # Play animation
        self.play_level_up_animation()
        
    def calculate_xp_for_level(self, level: int) -> int:
        """Calculate XP required for a level"""
        # Simple progression: 100 * level
        return 100 * level
        
    def set_level(self, level: int):
        """Set current level"""
        self.current_level = level
        self.level_label.setText(f"Level {level}")
        self.level_title.setText(self.get_level_title(level))
        
    def get_level_title(self, level: int) -> str:
        """Get title for level"""
        titles = {
            1: "Novice Mathematician",
            5: "Problem Solver",
            10: "Equation Expert",
            15: "Calculus Champion",
            20: "Math Master",
            25: "Grand Mathematician"
        }
        
        # Find appropriate title
        for lvl in sorted(titles.keys(), reverse=True):
            if level >= lvl:
                return titles[lvl]
        return "Student"
        
    def set_streak(self, days: int):
        """Set current streak"""
        self.current_streak = days
        self.streak_label.setText(f"🔥 {days} day streak")
        
        # Show bonus for long streaks
        if days >= 7:
            bonus = 10 + (days // 7) * 5
            self.streak_bonus.setText(f"+{bonus}% XP bonus")
        else:
            self.streak_bonus.setText("")
            
    def play_level_up_animation(self):
        """Play level up animation"""
        # Flash the level label
        effect = QGraphicsOpacityEffect()
        self.level_label.setGraphicsEffect(effect)
        
        self.opacity_anim = QPropertyAnimation(effect, b"opacity")
        self.opacity_anim.setDuration(1000)
        self.opacity_anim.setKeyValueAt(0, 1.0)
        self.opacity_anim.setKeyValueAt(0.5, 0.3)
        self.opacity_anim.setKeyValueAt(1.0, 1.0)
        self.opacity_anim.start()
        
        # Could also show a popup or particle effect
        
    def show_achievement(self, achievement_name: str):
        """Show achievement unlock notification"""
        self.achievement_unlocked.emit(achievement_name)
        # Could show a toast notification here
        
    def unlock_achievement(self, name: str):
        """Unlock an achievement"""
        self.show_achievement(name)