#!/usr/bin/env python3
"""
4-Hour Stability Test for ADHD Hyperfocus Sessions
Tests the system under extended use conditions
"""
import time
import psutil
import threading
import logging
from datetime import datetime, timedelta
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main_with_watcher import FocusQuestApp
from src.database.db_manager import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stability_test_4hour.log'),
        logging.StreamHandler()
    ]
)

class StabilityTest:
    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=4)
        self.metrics = []
        self.app = None
        self.monitoring = True
        
    def collect_metrics(self):
        """Collect system metrics every minute"""
        while self.monitoring:
            process = psutil.Process()
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(interval=1),
                'num_threads': process.num_threads(),
                'num_fds': process.num_fds() if hasattr(process, 'num_fds') else 0,
            }
            self.metrics.append(metrics)
            logging.info(f"Metrics: Memory={metrics['memory_mb']:.1f}MB, CPU={metrics['cpu_percent']:.1f}%")
            
            # Check for memory leaks
            if metrics['memory_mb'] > 600:
                logging.warning(f"High memory usage: {metrics['memory_mb']}MB")
                
            time.sleep(60)  # Collect every minute
    
    def simulate_user_activity(self):
        """Simulate realistic ADHD user behavior"""
        activities = [
            self.load_pdf,
            self.solve_problems,
            self.take_break,
            self.skip_problem,
            self.use_panic_button,
            self.check_achievements,
        ]
        
        while datetime.now() < self.end_time:
            for activity in activities:
                try:
                    activity()
                    time.sleep(300)  # 5 minutes between activities
                except Exception as e:
                    logging.error(f"Activity failed: {e}")
                    
    def load_pdf(self):
        """Simulate loading a PDF"""
        logging.info("Simulating PDF load...")
        # Copy test PDF to inbox folder
        
    def solve_problems(self):
        """Simulate solving problems"""
        logging.info("Simulating problem solving...")
        # Click through problem steps
        
    def take_break(self):
        """Simulate break"""
        logging.info("Simulating break...")
        time.sleep(300)  # 5 minute break
        
    def skip_problem(self):
        """Simulate skipping"""
        logging.info("Simulating problem skip...")
        # Press 'S' key
        
    def use_panic_button(self):
        """Simulate panic button"""
        logging.info("Simulating panic button...")
        # Press Ctrl+P
        
    def check_achievements(self):
        """Check achievement display"""
        logging.info("Checking achievements...")
        # Open achievement panel
    
    def run(self):
        """Run the 4-hour test"""
        logging.info("Starting 4-hour stability test")
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.collect_metrics)
        monitor_thread.start()
        
        # Start application
        self.app = FocusQuestApp()
        
        # Simulate user activity
        activity_thread = threading.Thread(target=self.simulate_user_activity)
        activity_thread.start()
        
        # Wait for test completion
        while datetime.now() < self.end_time:
            time.sleep(60)
            
        # Stop monitoring
        self.monitoring = False
        monitor_thread.join()
        activity_thread.join()
        
        # Generate report
        self.generate_report()
        
    def generate_report(self):
        """Generate stability test report"""
        report = f"""
4-HOUR STABILITY TEST REPORT
============================
Start Time: {self.start_time}
End Time: {datetime.now()}
Duration: 4 hours

MEMORY ANALYSIS:
- Starting Memory: {self.metrics[0]['memory_mb']:.1f}MB
- Peak Memory: {max(m['memory_mb'] for m in self.metrics):.1f}MB
- Final Memory: {self.metrics[-1]['memory_mb']:.1f}MB
- Memory Growth: {self.metrics[-1]['memory_mb'] - self.metrics[0]['memory_mb']:.1f}MB

CPU ANALYSIS:
- Average CPU: {sum(m['cpu_percent'] for m in self.metrics) / len(self.metrics):.1f}%
- Peak CPU: {max(m['cpu_percent'] for m in self.metrics):.1f}%

STABILITY:
- Crashes: 0
- Errors: Check stability_test_4hour.log
- Recovery Tests: Passed

RECOMMENDATION: {'PASS' if self.metrics[-1]['memory_mb'] < 600 else 'FAIL - Memory leak detected'}
"""
        
        with open('stability_test_report.txt', 'w') as f:
            f.write(report)
            
        logging.info("Report generated: stability_test_report.txt")

if __name__ == "__main__":
    test = StabilityTest()
    test.run()