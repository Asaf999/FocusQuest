"""
File watcher for automatic PDF processing
Monitors inbox directory and processes PDFs using Claude Directory Analyzer
"""
import os
import shutil
import time
import threading
import queue
import errno
from contextlib import contextmanager
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

from src.analysis.pdf_processor import PDFProcessor
from src.analysis.claude_directory_analyzer import ClaudeDirectoryAnalyzer
from src.core.processing_queue import ProcessingQueue

logger = logging.getLogger(__name__)


class PDFHandler(FileSystemEventHandler):
    """Handle PDF file events in watched directory"""
    
    def __init__(self, inbox_dir: Path, processed_dir: Path, processing_queue: ProcessingQueue = None):
        self.inbox_dir = Path(inbox_dir)
        self.processed_dir = Path(processed_dir)
        self.processing_queue = processing_queue
        
        # Thread-safe queue for events
        self.event_queue = queue.Queue()
        self.processing_lock = threading.Lock()
        self.active_files = set()  # Track files being processed
        
        # Additional locks for thread safety
        self.file_operation_lock = threading.Lock()
        self._processor = None
        self._analyzer = None
        self._resource_lock = threading.Lock()
        
        # Start worker thread for processing
        self.worker_thread = threading.Thread(target=self._process_events, daemon=True)
        self.worker_thread.start()
        
        # Ensure directories exist
        self.inbox_dir.mkdir(exist_ok=True)
        self.processed_dir.mkdir(exist_ok=True)
        
    def on_created(self, event):
        """Handle new file creation events"""
        if not event.is_directory and event.src_path.endswith('.pdf'):
            # Queue event for processing
            self.event_queue.put(('created', event.src_path))
            
    def on_moved(self, event):
        """Handle file move events (some apps create temp files first)"""
        if not event.is_directory and event.dest_path.endswith('.pdf'):
            # Queue event for processing
            self.event_queue.put(('moved', event.dest_path))
    
    def _process_events(self):
        """Worker thread to process events from queue with enhanced thread safety"""
        while True:
            try:
                event_type, file_path = self.event_queue.get(timeout=1.0)
                
                # Wait for file to be fully written
                time.sleep(1)
                
                pdf_path = Path(file_path)
                
                # Extended lock coverage for entire processing decision
                with self.processing_lock:
                    # Check if file is already being processed
                    if file_path in self.active_files:
                        logger.info(f"File already being processed: {file_path}")
                        continue
                    
                    # Verify file still exists before processing
                    if not pdf_path.exists():
                        logger.warning(f"File no longer exists: {pdf_path}")
                        continue
                    
                    # Verify it's a PDF
                    if pdf_path.suffix.lower() != '.pdf':
                        logger.debug(f"Skipping non-PDF file: {pdf_path}")
                        continue
                    
                    # Mark as active
                    self.active_files.add(file_path)
                
                try:
                    self._process_pdf_safe(file_path)
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    print(f"❌ Error processing {pdf_path.name}: {e}")
                finally:
                    # Remove from active files
                    with self.processing_lock:
                        self.active_files.discard(file_path)
                        
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in event processing thread: {e}")
            
    def _get_processor(self):
        """Get or create thread-safe PDF processor"""
        if self._processor is None:
            with self._resource_lock:
                if self._processor is None:
                    self._processor = PDFProcessor()
        return self._processor
    
    def _get_analyzer(self):
        """Get or create thread-safe Claude analyzer"""
        if self._analyzer is None:
            with self._resource_lock:
                if self._analyzer is None:
                    self._analyzer = ClaudeDirectoryAnalyzer()
        return self._analyzer
    
    def _process_pdf_safe(self, pdf_path: str):
        """Thread-safe PDF processing"""
        if self.processing_queue:
            # Add to persistent queue instead of direct processing
            self.processing_queue.add_item(pdf_path, priority="NORMAL")
            print(f"✅ Added {Path(pdf_path).name} to processing queue")
        else:
            # Direct processing (legacy mode)
            self.process_pdf(pdf_path)
    
    def process_pdf(self, pdf_path: str):
        """Process a PDF file using Claude Directory Analyzer with thread safety"""
        pdf_path = Path(pdf_path)
        
        # Get thread-safe processor instances
        processor = self._get_processor()
        analyzer = self._get_analyzer()
        
        if not pdf_path.exists():
            logger.warning(f"PDF no longer exists: {pdf_path}")
            return
            
        print(f"\n🔄 Processing new PDF: {pdf_path.name}")
        print("=" * 60)
        
        try:
            # Extract content from PDF
            print("📖 Extracting content from PDF...")
            result = processor.process_pdf(str(pdf_path))
            
            if not result or 'error' in result:
                print(f"❌ Error extracting content: {result.get('error', 'Unknown error')}")
                return
                
            problems = result.get('problems', [])
            
            if not problems:
                print("⚠️ No mathematical problems found in PDF")
                # Still move to processed
                self._move_to_processed(pdf_path)
                return
                
            print(f"✅ Found {len(problems)} problems to analyze")
            
            # Submit each problem for analysis
            session_ids = []
            for i, problem in enumerate(problems):
                print(f"\n📝 Submitting problem {i+1}/{len(problems)} for analysis")
                
                # Extract problem metadata
                metadata = {
                    'source': pdf_path.name,
                    'page': problem.get('page', 1),
                    'problem_index': i,
                    'course': problem.get('metadata', {}).get('course', 'Mathematics'),
                    'topic': problem.get('metadata', {}).get('topic', 'General'),
                    'difficulty': problem.get('difficulty', 'medium')
                }
                
                # Get problem text
                problem_text = problem.get('hebrew_text', '')
                if problem.get('english_translation'):
                    problem_text += f"\n\nTranslation: {problem['english_translation']}"
                if problem.get('formulas'):
                    problem_text += f"\n\nFormulas: {', '.join(problem['formulas'])}"
                    
                # Submit for analysis
                session_id = analyzer.analyze_problem_async(problem_text, metadata)
                session_ids.append(session_id)
                print(f"✅ Analysis session started: {session_id}")
                
            print(f"\n🎯 All {len(problems)} problems submitted for background analysis")
            print(f"📁 Check analysis_sessions/ directory for results")
            
            # Move PDF to processed directory
            self._move_to_processed(pdf_path)
            
            print("=" * 60)
            return session_ids
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            print(f"❌ Error processing PDF: {e}")
            return []
            
    def _move_to_processed(self, pdf_path: Path, max_retries: int = 3):
        """Move PDF to processed directory with thread-safe atomic operations"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        # Add thread ID to ensure uniqueness in concurrent scenarios
        thread_id = threading.current_thread().ident % 1000
        new_name = f"{timestamp}_{thread_id:03d}_{pdf_path.name}"
        dest_path = self.processed_dir / new_name
        
        # Use file operation lock to prevent concurrent moves
        with self.file_operation_lock:
            for attempt in range(max_retries):
                try:
                    # Double-check source exists
                    if not pdf_path.exists():
                        logger.info(f"File already processed: {pdf_path}")
                        return
                    
                    # Ensure destination doesn't exist
                    if dest_path.exists():
                        # Generate new unique name
                        counter = 1
                        while dest_path.exists():
                            new_name = f"{timestamp}_{thread_id:03d}_{counter}_{pdf_path.name}"
                            dest_path = self.processed_dir / new_name
                            counter += 1
                    
                    # Try atomic rename first
                    try:
                        pdf_path.rename(dest_path)
                        print(f"📁 Moved to processed: {new_name}")
                        return
                    except OSError as e:
                        if e.errno == errno.EXDEV:
                            # Cross-device move, use copy+delete
                            shutil.copy2(str(pdf_path), str(dest_path))
                            pdf_path.unlink()
                            print(f"📁 Moved to processed: {new_name}")
                            return
                        else:
                            raise
                            
                except FileNotFoundError:
                    logger.info(f"File already moved by another thread: {pdf_path}")
                    return
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Retry {attempt + 1}/{max_retries} for moving {pdf_path}: {e}")
                        time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    else:
                        logger.error(f"Failed to move file after {max_retries} attempts: {e}")
                        print(f"⚠️ Could not move file: {e}")


class FileWatcher:
    """Main file watcher service"""
    
    def __init__(self, inbox_dir: str = None, processed_dir: str = None):
        project_root = Path("/home/puncher/focusquest")
        self.inbox_dir = Path(inbox_dir) if inbox_dir else project_root / "inbox"
        self.processed_dir = Path(processed_dir) if processed_dir else project_root / "processed"
        
        # Create persistent processing queue
        self.processing_queue = ProcessingQueue()
        
        self.observer = Observer()
        self.handler = PDFHandler(self.inbox_dir, self.processed_dir, self.processing_queue)
        self.running = False
        
    def start(self):
        """Start watching the inbox directory"""
        self.observer.schedule(self.handler, str(self.inbox_dir), recursive=False)
        self.observer.start()
        
        print(f"👁️ Watching directory: {self.inbox_dir}")
        print("📥 Drop PDF files here for automatic processing")
        print("🤖 Claude Code will analyze problems in the background")
        print("Press Ctrl+C to stop...")
        
        self.running = True
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """Stop the file watcher gracefully"""
        self.running = False
        self.observer.stop()
        print("\n👋 File watcher stopped")
        self.observer.join(timeout=5.0)
        
        # Cleanup handler resources
        if hasattr(self.handler, '_processor'):
            self.handler._processor = None
        if hasattr(self.handler, '_analyzer'):
            self.handler._analyzer = None
        
    def process_existing_files(self):
        """Process any existing PDF files in inbox"""
        pdf_files = list(self.inbox_dir.glob("*.pdf"))
        
        if pdf_files:
            print(f"\n📋 Found {len(pdf_files)} existing PDFs to process")
            for pdf_file in pdf_files:
                self.handler.process_pdf(str(pdf_file))
                
                
def main():
    """Run the file watcher service"""
    watcher = FileWatcher()
    
    # Process any existing files first
    watcher.process_existing_files()
    
    # Start watching for new files
    watcher.start()
    

if __name__ == "__main__":
    main()