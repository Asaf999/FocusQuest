#!/usr/bin/env python3
"""Demo of FocusQuest with integrated file watching.

This demonstrates:
1. Automatic PDF detection in inbox folder
2. Background processing and analysis
3. Live problem loading in GUI
4. ADHD-friendly queue management
"""
import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ui.main_window_integrated import FocusQuestIntegratedWindow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    """Run the integrated FocusQuest application."""
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("FocusQuest")
    app.setOrganizationName("ADHD Learning")
    
    # Create and show main window
    window = FocusQuestIntegratedWindow()
    window.show()
    
    # Log startup
    logger = logging.getLogger(__name__)
    logger.info("FocusQuest started with file watcher integration")
    logger.info(f"Drop PDFs in: {window.file_watcher.inbox_dir.absolute()}")
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()