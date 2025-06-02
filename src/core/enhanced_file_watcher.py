"""
Enhanced file watcher using processing queue for production reliability
"""
import os
import shutil
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

from src.core.queue_processor import QueueProcessor
from src.core.processing_queue import Priority

logger = logging.getLogger(__name__)


class EnhancedPDFHandler(FileSystemEventHandler):
    """Handle PDF file events using queue system"""
    
    def __init__(self, queue_processor: QueueProcessor, processed_dir: Path):
        self.queue_processor = queue_processor
        self.processed_dir = Path(processed_dir)
        self.processed_dir.mkdir(exist_ok=True)
        
    def on_created(self, event):
        """Handle new file creation events"""
        if not event.is_directory and event.src_path.endswith('.pdf'):
            # Wait a moment for file to be fully written
            time.sleep(1)
            self._queue_pdf(event.src_path)
            
    def on_moved(self, event):
        """Handle file move events (some apps create temp files first)"""
        if not event.is_directory and event.dest_path.endswith('.pdf'):
            time.sleep(1)
            self._queue_pdf(event.dest_path)
            
    def _queue_pdf(self, pdf_path: str):
        """Add PDF to processing queue"""
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            logger.warning(f"PDF no longer exists: {pdf_path}")
            return
            
        # Determine priority based on filename patterns
        priority = self._determine_priority(pdf_path)
        
        print(f"\n📥 New PDF detected: {pdf_path.name}")
        print(f"🎯 Priority: {priority.name}")
        
        # Add to queue
        item_id = self.queue_processor.add_pdf(str(pdf_path), priority)
        
        if item_id:
            print(f"✅ Added to queue (ID: {item_id})")
            # Move to processed directory immediately
            self._move_to_processed(pdf_path)
        else:
            print(f"⚠️ PDF already in queue or processed")
            
    def _determine_priority(self, pdf_path: Path) -> Priority:
        """Determine processing priority based on filename"""
        filename = pdf_path.name.lower()
        
        # High priority patterns - check for whole words to avoid false matches
        if any(f'_{pattern}' in filename or f'{pattern}_' in filename or filename.startswith(pattern) 
               for pattern in ['urgent', 'exam', 'quiz']):
            return Priority.HIGH
            
        # Low priority patterns
        if any(pattern in filename for pattern in ['practice', 'exercise', 'homework']):
            return Priority.LOW
            
        return Priority.NORMAL
        
    def _move_to_processed(self, pdf_path: Path):
        """Move PDF to processed directory with timestamp"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        new_name = f"{timestamp}_{pdf_path.name}"
        dest_path = self.processed_dir / new_name
        
        try:
            shutil.move(str(pdf_path), str(dest_path))
            logger.info(f"Moved to processed: {new_name}")
        except Exception as e:
            logger.error(f"Error moving file: {e}")


class EnhancedFileWatcher:
    """Production-ready file watcher with queue integration"""
    
    def __init__(
        self,
        inbox_dir: str = None,
        processed_dir: str = None,
        max_workers: int = 3,
        db_path: str = None
    ):
        project_root = Path("/home/puncher/focusquest")
        self.inbox_dir = Path(inbox_dir) if inbox_dir else project_root / "inbox"
        self.processed_dir = Path(processed_dir) if processed_dir else project_root / "processed"
        
        # Ensure directories exist
        self.inbox_dir.mkdir(exist_ok=True)
        self.processed_dir.mkdir(exist_ok=True)
        
        # Initialize queue processor
        self.queue_processor = QueueProcessor(
            db_path=db_path,
            max_workers=max_workers
        )
        
        # Initialize observer
        self.observer = Observer()
        self.handler = EnhancedPDFHandler(self.queue_processor, self.processed_dir)
        
    def start(self):
        """Start watching and processing"""
        # Start queue processor
        self.queue_processor.start()
        
        # Start file observer
        self.observer.schedule(self.handler, str(self.inbox_dir), recursive=False)
        self.observer.start()
        
        print(f"""
╔══════════════════════════════════════════════════════╗
║          FocusQuest PDF Processing Service           ║
╠══════════════════════════════════════════════════════╣
║ 📁 Watching: {str(self.inbox_dir):<40} ║
║ 💾 Queue DB: data/processing_queue.db                ║
║ 🔄 Workers:  {self.queue_processor.max_workers}                                    ║
║ ⏱️  Poll:     {self.queue_processor.poll_interval}s                                 ║
╠══════════════════════════════════════════════════════╣
║ Priority Patterns:                                   ║
║   🔴 HIGH: urgent, exam, test, quiz                 ║
║   🟡 NORMAL: (default)                              ║
║   🟢 LOW: practice, exercise, homework              ║
╠══════════════════════════════════════════════════════╣
║ Press Ctrl+C to stop                                 ║
╚══════════════════════════════════════════════════════╝
""")
        
        # Show current queue status
        self._show_queue_status()
        
        try:
            while True:
                time.sleep(30)  # Show status every 30 seconds
                self._show_queue_status()
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """Stop watching and processing"""
        print("\n🛑 Shutting down...")
        
        # Stop observer
        self.observer.stop()
        self.observer.join()
        
        # Stop queue processor
        self.queue_processor.stop()
        
        # Final statistics
        stats = self.queue_processor.get_statistics()
        print(f"""
╔══════════════════════════════════════════════════════╗
║              Final Processing Statistics             ║
╠══════════════════════════════════════════════════════╣
║ ✅ Completed: {stats.get('completed', 0):<38} ║
║ ❌ Failed:    {stats.get('failed', 0):<38} ║
║ 🔄 Pending:   {stats.get('pending', 0):<38} ║
║ ⏱️  Avg Time:  {stats.get('average_processing_time', 0):.2f}s{' ' * 33} ║
╚══════════════════════════════════════════════════════╝
""")
        
    def _show_queue_status(self):
        """Display current queue status"""
        stats = self.queue_processor.get_statistics()
        
        if stats['total'] > 0:
            print(f"\n📊 Queue Status: "
                  f"Pending: {stats['pending']} | "
                  f"Processing: {stats['processing']} | "
                  f"Completed: {stats['completed']} | "
                  f"Failed: {stats['failed']}")
                  
    def process_existing_files(self):
        """Process any existing PDF files in inbox"""
        pdf_files = list(self.inbox_dir.glob("*.pdf"))
        
        if pdf_files:
            print(f"\n📋 Found {len(pdf_files)} existing PDFs to process")
            for pdf_file in pdf_files:
                self.handler._queue_pdf(str(pdf_file))
                
                
def main():
    """Run the enhanced file watcher service"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FocusQuest PDF Processing Service")
    parser.add_argument("--inbox", help="Inbox directory to watch")
    parser.add_argument("--processed", help="Processed files directory")
    parser.add_argument("--workers", type=int, default=3, help="Max concurrent workers")
    parser.add_argument("--db", help="Queue database path")
    
    args = parser.parse_args()
    
    watcher = EnhancedFileWatcher(
        inbox_dir=args.inbox,
        processed_dir=args.processed,
        max_workers=args.workers,
        db_path=args.db
    )
    
    # Process existing files first
    watcher.process_existing_files()
    
    # Start watching for new files
    watcher.start()
    

if __name__ == "__main__":
    main()