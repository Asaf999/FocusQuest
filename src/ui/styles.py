"""
Dark theme styles optimized for ADHD focus
"""

DARK_THEME_STYLE = """
/* Global styles */
QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 12pt;
}

/* Main window */
QMainWindow {
    background-color: #1e1e1e;
}

/* Labels */
QLabel {
    color: #e0e0e0;
    padding: 2px;
}

QLabel#problemTitle {
    color: #ffffff;
    font-size: 16pt;
    font-weight: bold;
    padding: 10px;
    background-color: #2a2a2a;
    border-radius: 5px;
    margin-bottom: 10px;
}

QLabel#stepContent {
    font-size: 14pt;
    line-height: 1.5;
}

QLabel#levelLabel {
    color: #4fc3f7;
    font-size: 18pt;
    font-weight: bold;
}

QLabel#levelTitle {
    color: #81c784;
    font-size: 10pt;
}

QLabel#xpLabel {
    color: #ffb74d;
    font-size: 10pt;
}

QLabel#streakLabel {
    color: #ff7043;
    font-size: 14pt;
}

QLabel#timerLabel {
    color: #b0b0b0;
    font-size: 12pt;
    padding: 5px;
    background-color: #2a2a2a;
    border-radius: 3px;
}

QLabel#durationLabel {
    color: #808080;
    font-size: 10pt;
}

QLabel#hintText {
    color: #fff59d;
    font-size: 12pt;
    padding: 10px;
}

/* Buttons */
QPushButton {
    background-color: #3a3a3a;
    color: #e0e0e0;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 12pt;
    font-weight: bold;
    min-height: 36px;
}

QPushButton:hover {
    background-color: #4a4a4a;
}

QPushButton:pressed {
    background-color: #2a2a2a;
}

QPushButton:disabled {
    background-color: #2a2a2a;
    color: #606060;
}

QPushButton#submitButton {
    background-color: #4caf50;
    color: white;
    font-size: 14pt;
    min-width: 120px;
    min-height: 40px;
}

QPushButton#submitButton:hover {
    background-color: #5cbf60;
}

QPushButton#submitButton:pressed {
    background-color: #3c9f40;
}

QPushButton#hintButton {
    background-color: #ff9800;
    color: white;
}

QPushButton#hintButton:hover {
    background-color: #ffa726;
}

/* Checkboxes */
QCheckBox {
    color: #e0e0e0;
    spacing: 5px;
}

QCheckBox::indicator {
    width: 24px;
    height: 24px;
}

QCheckBox::indicator:unchecked {
    background-color: #3a3a3a;
    border: 2px solid #606060;
    border-radius: 4px;
}

QCheckBox::indicator:checked {
    background-color: #4caf50;
    border: 2px solid #4caf50;
    border-radius: 4px;
}

QCheckBox::indicator:checked {
    image: url(checkmark.png);  /* Would need to add this resource */
}

/* Progress bars */
QProgressBar {
    background-color: #2a2a2a;
    border: none;
    border-radius: 4px;
    height: 20px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #4fc3f7;
    border-radius: 3px;
}

QProgressBar#xpBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #4fc3f7,
                                stop:1 #29b6f6);
}

/* Frames */
QFrame {
    background-color: #2a2a2a;
    border: none;
}

QFrame#stepWidget {
    background-color: #2a2a2a;
    border: 1px solid #3a3a3a;
    border-radius: 5px;
    padding: 10px;
    margin: 5px 0;
}

QFrame#stepWidget:hover {
    border-color: #4a4a4a;
}

QFrame#hintFrame {
    background-color: #3a3a3a;
    border: 2px solid #ff9800;
    border-radius: 5px;
    padding: 10px;
    margin: 10px 0;
}

/* Scroll areas */
QScrollArea {
    background-color: #1e1e1e;
    border: none;
}

QScrollBar:vertical {
    background-color: #2a2a2a;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #4a4a4a;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #5a5a5a;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Text edits */
QTextEdit {
    background-color: #2a2a2a;
    color: #e0e0e0;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    padding: 8px;
    font-size: 12pt;
}

QTextEdit:focus {
    border-color: #4fc3f7;
}

/* Tooltips */
QToolTip {
    background-color: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #4a4a4a;
    padding: 5px;
    border-radius: 3px;
}

/* Focus indicators */
*:focus {
    outline: 2px solid #4fc3f7;
    outline-offset: 2px;
}

/* Panic mode overlay */
#panicOverlay {
    background-color: rgba(20, 20, 20, 0.95);
}

#panicOverlay QLabel {
    color: #e0e0e0;
    font-size: 20pt;
    font-weight: 300;
}

#resumeButton {
    background-color: #4caf50;
    color: white;
    font-size: 16pt;
    padding: 15px 30px;
    border-radius: 25px;
    font-weight: bold;
    min-width: 250px;
}

#resumeButton:hover {
    background-color: #5cbf60;
}

#resumeButton:pressed {
    background-color: #3c9f40;
}

/* Animations and transitions would be defined in code */
"""