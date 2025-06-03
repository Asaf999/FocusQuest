#!/usr/bin/env python3
"""
Quick 15-minute stability check
"""
import time
import psutil
import subprocess
import sys
import os

def quick_check():
    print("🔍 Quick Stability Check (15 minutes)")
    
    # Start the application
    process = subprocess.Popen([
        sys.executable, 
        "src/main_with_watcher.py"
    ])
    
    initial_memory = psutil.Process(process.pid).memory_info().rss / 1024 / 1024
    print(f"Initial memory: {initial_memory:.1f}MB")
    
    # Monitor for 15 minutes
    for i in range(15):
        time.sleep(60)
        current_memory = psutil.Process(process.pid).memory_info().rss / 1024 / 1024
        growth = current_memory - initial_memory
        print(f"Minute {i+1}: {current_memory:.1f}MB (growth: {growth:+.1f}MB)")
        
        if growth > 50:
            print("⚠️ WARNING: Significant memory growth detected!")
    
    # Cleanup
    process.terminate()
    process.wait()
    
    print("\n✅ Quick check complete")
    print(f"Memory growth: {growth:.1f}MB over 15 minutes")
    print(f"Status: {'PASS' if growth < 50 else 'FAIL'}")

if __name__ == "__main__":
    quick_check()