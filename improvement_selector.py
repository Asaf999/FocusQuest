#!/usr/bin/env python3
"""
Intelligent improvement selection for autonomous cycles
"""
import subprocess
import json
import os
from datetime import datetime
from typing import Dict, Tuple, List

class ImprovementSelector:
    def __init__(self):
        self.metrics_file = "improvement_metrics.json"
        self.load_metrics()
    
    def load_metrics(self):
        """Load or initialize metrics tracking"""
        if os.path.exists(self.metrics_file):
            with open(self.metrics_file, 'r') as f:
                self.metrics = json.load(f)
        else:
            self.metrics = {
                'test_coverage': 0,
                'avg_response_time': 999,
                'memory_usage': 999,
                'error_count': 999,
                'adhd_features': 0,
                'complexity_score': 999,
                'doc_coverage': 0,
                'integration_tests': 0,
                'improvements_log': []
            }
    
    def save_metrics(self):
        """Save metrics to file"""
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
    
    def get_test_coverage(self) -> float:
        """Get current test coverage percentage"""
        try:
            result = subprocess.run(
                ['coverage', 'report', '--format=json'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get('totals', {}).get('percent_covered', 0)
        except:
            pass
        return self.metrics.get('test_coverage', 0)
    
    def get_response_time(self) -> float:
        """Measure average UI response time"""
        # This would run performance tests
        # For now, return stored value
        return self.metrics.get('avg_response_time', 999)
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return self.metrics.get('memory_usage', 999)
    
    def count_adhd_features(self) -> int:
        """Count implemented ADHD accommodations"""
        features = [
            'panic_button',
            'break_notifications',
            'skip_problem',
            'medication_timing',
            'focus_mode',
            'progress_visibility',
            'chunked_content',
            'hyperfocus_support'
        ]
        
        count = 0
        for feature in features:
            if os.path.exists(f'src/features/{feature}.py'):
                count += 1
            elif subprocess.run(['grep', '-r', feature, 'src/'], 
                              capture_output=True).returncode == 0:
                count += 1
        
        return count
    
    def select_improvement(self) -> Tuple[str, str]:
        """Select next improvement based on worst metric"""
        current_metrics = {
            'test_coverage': self.get_test_coverage(),
            'response_time': self.get_response_time(),
            'memory_usage': self.get_memory_usage(),
            'adhd_features': self.count_adhd_features(),
        }
        
        # Normalize metrics (lower is worse)
        scores = {
            'TEST_COVERAGE': current_metrics['test_coverage'] / 100,
            'PERFORMANCE': 100 / current_metrics['response_time'],
            'MEMORY': 300 / current_metrics['memory_usage'],
            'ADHD_FEATURES': current_metrics['adhd_features'] / 10,
        }
        
        # Find worst area
        worst_area = min(scores, key=scores.get)
        
        # Map to improvement task
        improvements = {
            'TEST_COVERAGE': 'Find untested functions and add comprehensive tests',
            'PERFORMANCE': 'Profile and optimize slowest operations',
            'MEMORY': 'Find and fix memory leaks',
            'ADHD_FEATURES': 'Implement new ADHD accommodation feature'
        }
        
        # Log the selection
        self.metrics['improvements_log'].append({
            'timestamp': datetime.now().isoformat(),
            'selected': worst_area,
            'metrics': current_metrics
        })
        self.save_metrics()
        
        return worst_area, improvements[worst_area]

if __name__ == "__main__":
    selector = ImprovementSelector()
    target, description = selector.select_improvement()
    print(f"NEXT IMPROVEMENT TARGET: {target}")
    print(f"DESCRIPTION: {description}")