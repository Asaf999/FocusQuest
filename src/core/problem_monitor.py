"""Monitor for completed problem analyses from Claude."""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

logger = logging.getLogger(__name__)


class ProblemMonitor(QObject):
    """Monitor analysis_sessions directory for completed problem analyses.
    
    This runs in the GUI thread using Qt's timer for non-blocking operation.
    Polls the analysis directory and emits signals when new problems are ready.
    """
    
    # Signals
    new_problem_ready = pyqtSignal(dict)  # Emitted when a problem is analyzed
    error_occurred = pyqtSignal(str)      # Emitted on errors
    
    def __init__(self, analysis_dir: str = "analysis_sessions", poll_interval: int = 3000):
        """Initialize problem monitor.
        
        Args:
            analysis_dir: Directory to monitor for analysis results
            poll_interval: How often to check for new results (ms)
        """
        super().__init__()
        self.analysis_dir = Path(analysis_dir)
        self.poll_interval = poll_interval
        self.processed_files = set()
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_for_problems)
        
    def start_monitoring(self):
        """Start monitoring for new problems."""
        logger.info(f"Starting problem monitor on {self.analysis_dir}")
        
        # Create directory if it doesn't exist
        self.analysis_dir.mkdir(exist_ok=True)
        
        # Record existing files to avoid processing old ones
        if self.analysis_dir.exists():
            for entry in self.analysis_dir.iterdir():
                if entry.is_dir() and entry.name.startswith("problem_"):
                    self.processed_files.add(entry.name)
                    
        # Start polling
        self.timer.start(self.poll_interval)
        
    def stop_monitoring(self):
        """Stop monitoring."""
        logger.info("Stopping problem monitor")
        self.timer.stop()
        
    def _check_for_problems(self):
        """Check for new problem analysis results."""
        try:
            if not self.analysis_dir.exists():
                return
                
            # Look for problem directories
            for entry in self.analysis_dir.iterdir():
                if not entry.is_dir():
                    continue
                    
                if not entry.name.startswith("problem_"):
                    continue
                    
                # Skip if already processed
                if entry.name in self.processed_files:
                    continue
                    
                # Check if analysis is complete
                result_file = entry / "analysis_result.json"
                if not result_file.exists():
                    continue
                    
                # Load and emit the result
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        result = json.load(f)
                        
                    # Add metadata
                    problem_data = {
                        'id': entry.name,
                        'source': 'file_watcher',
                        'analyzed_at': datetime.now().isoformat(),
                        'file_path': str(result_file),
                        **result
                    }
                    
                    # Mark as processed
                    self.processed_files.add(entry.name)
                    
                    # Emit signal
                    logger.info(f"New problem ready: {entry.name}")
                    self.new_problem_ready.emit(problem_data)
                    
                except Exception as e:
                    logger.error(f"Error loading problem {entry.name}: {e}")
                    self.error_occurred.emit(f"Failed to load problem: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error checking for problems: {e}")
            self.error_occurred.emit(f"Monitor error: {str(e)}")
            
    def is_monitoring(self) -> bool:
        """Check if actively monitoring."""
        return self.timer.isActive()
        
    def get_pending_count(self) -> int:
        """Get count of unprocessed problems."""
        if not self.analysis_dir.exists():
            return 0
            
        pending = 0
        for entry in self.analysis_dir.iterdir():
            if (entry.is_dir() and 
                entry.name.startswith("problem_") and
                entry.name not in self.processed_files and
                (entry / "analysis_result.json").exists()):
                pending += 1
                
        return pending