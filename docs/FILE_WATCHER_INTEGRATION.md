# FocusQuest File Watcher Integration Guide

## Overview

The file watcher integration allows FocusQuest to automatically process PDF files dropped in the `inbox` folder and load the analyzed problems into the GUI without blocking the user interface.

## Architecture

```
PDF Drop → File Watcher → Queue Processor → Claude Analyzer → Problem Monitor → GUI
   ↓           ↓              ↓                    ↓                ↓            ↓
inbox/    monitors      processes PDFs      analyzes problems   detects     displays
folder    for PDFs      concurrently        in background      completion   in UI
```

## Key Components

### 1. **EnhancedFileWatcher** (`enhanced_file_watcher.py`)
- Monitors `inbox/` directory for new PDFs
- Moves PDFs to `processed/` after queuing
- Prioritizes based on filename (urgent, exam, quiz = HIGH)
- Non-blocking, runs in separate thread

### 2. **QueueProcessor** (`queue_processor.py`)
- Manages concurrent PDF processing with thread pool
- Extracts problems using PDFProcessor
- Submits to Claude for analysis
- Handles retries and failures gracefully

### 3. **ClaudeDirectoryAnalyzer** (`claude_directory_analyzer.py`)
- Creates separate analysis session for each problem
- Runs Claude Code in background
- Saves results to `analysis_sessions/<session_id>/results.json`
- Monitors for completion

### 4. **ProblemMonitor** (`problem_monitor.py`)
- Polls `analysis_sessions/` for completed analyses
- Converts Claude results to GUI-friendly format
- Emits signals when new problems are ready
- Tracks processed sessions to avoid duplicates

### 5. **FileWatcherIntegration** (`file_watcher_integration.py`)
- Manages file watcher and problem monitor
- Runs file watcher in separate thread
- Connects to main window via signals
- Handles pause/resume for ADHD breaks

## How to Use

### 1. Start the Application

```python
# Use the enhanced main file
python src/main_with_watcher.py
```

### 2. Drop PDFs in Inbox

Simply copy or move PDF files to the `inbox/` folder:
```bash
cp math_problems.pdf /home/puncher/focusquest/inbox/
```

### 3. Automatic Processing Flow

1. **File Detection** (1-2 seconds)
   - File watcher detects new PDF
   - Adds to processing queue
   - Moves to `processed/` folder

2. **PDF Processing** (5-30 seconds)
   - Extracts text and problems
   - Identifies Hebrew/English content
   - Detects mathematical formulas

3. **Claude Analysis** (30-120 seconds)
   - Creates analysis session
   - Runs Claude Code in background
   - Generates step-by-step solution

4. **GUI Loading** (3-5 seconds)
   - Problem monitor detects completion
   - Formats for GUI display
   - Notifies main window
   - Problem appears automatically

## ADHD-Friendly Features

### Non-Blocking Operation
- All processing happens in background
- GUI remains responsive
- Can solve problems while new ones process

### Visual Feedback
- Window title shows queue status
- Notifications for new problems
- Status messages for processing

### Panic Mode Integration
- File processing pauses during panic mode
- Resumes automatically after
- No lost work or crashes

### Priority Processing
- Urgent files processed first
- Name files with keywords:
  - `urgent_*.pdf` → HIGH priority
  - `exam_*.pdf` → HIGH priority
  - `practice_*.pdf` → LOW priority

## Example Integration Code

```python
# In your main window
from src.ui.file_watcher_integration import FileWatcherIntegration

class FocusQuestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Create file watcher integration
        self.file_watcher = FileWatcherIntegration()
        
        # Connect signals
        self.file_watcher.new_problem_ready.connect(self.on_new_problem)
        self.file_watcher.watcher_error.connect(self.show_error)
        
        # Start watching
        self.file_watcher.start()
        
    def on_new_problem(self, problem_data):
        """Handle new problem from file watcher"""
        # Problem data includes:
        # - original_text: Hebrew problem text
        # - translated_text: English translation
        # - steps: List of solution steps
        # - hints: Progressive hints
        # - metadata: Source info
        
        self.load_problem(problem_data)
```

## Monitoring and Debugging

### Check Processing Status
```python
status = file_watcher.get_queue_status()
print(f"Pending: {status['pending']}")
print(f"Processing: {status['processing']}")
print(f"Completed: {status['completed']}")
```

### View Analysis Sessions
```bash
ls -la analysis_sessions/
```

### Check Logs
```bash
# Main application log
tail -f focusquest.log

# Individual session logs
cat analysis_sessions/*/analysis.log
```

## Troubleshooting

### Problem: PDFs Not Being Detected
- Check `inbox/` directory exists
- Verify file has `.pdf` extension
- Check file watcher is running (window title)

### Problem: Analysis Taking Too Long
- Check Claude Code is installed
- Look for errors in session logs
- Verify sufficient disk space

### Problem: Problems Not Appearing in GUI
- Check `analysis_sessions/*/results.json` exists
- Verify `analysis_complete: true` in results
- Check problem monitor is running

## Performance Considerations

### Resource Usage
- Default: 2 concurrent workers
- Each PDF: ~50-200MB memory
- Claude analysis: ~100-500MB per session

### ADHD Optimizations
- Automatic resource monitoring
- Reduces workers if memory low
- Pauses during panic mode
- Resumes after breaks

## Future Enhancements

1. **Smart Queuing**
   - Learn from user patterns
   - Prioritize by time of day
   - Skip similar problems

2. **Progress Tracking**
   - Show analysis progress
   - ETA for completion
   - Queue visualization

3. **Batch Operations**
   - Process entire folders
   - Course organization
   - Semester planning