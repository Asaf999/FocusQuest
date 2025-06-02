#!/usr/bin/env python3
"""
Manual test script for Claude Directory Analyzer
Run this to test the automated Claude Code analysis
"""
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from src.analysis.claude_directory_analyzer import ClaudeDirectoryAnalyzer


def main():
    print("🧪 Testing Claude Directory Analyzer")
    print("=" * 50)
    
    analyzer = ClaudeDirectoryAnalyzer()
    
    # Test problem - classic induction proof
    problem = '''
Prove by mathematical induction that for all positive integers n:
1 + 2 + 3 + ... + n = n(n+1)/2

This is the formula for the sum of the first n positive integers.
Show all steps clearly.
'''
    
    metadata = {
        'course': 'Discrete Mathematics',
        'topic': 'Mathematical Induction',
        'difficulty': 'easy',
        'source': 'Manual Test'
    }
    
    print("\n📝 Problem to analyze:")
    print("-" * 40)
    print(problem)
    print("-" * 40)
    
    print("\n📤 Submitting problem for analysis...")
    session_id = analyzer.analyze_problem_async(problem, metadata)
    
    print(f"\n✅ Session created successfully!")
    print(f"📁 Session ID: {session_id}")
    print(f"📂 Session directory: {analyzer.sessions_dir / session_id}")
    
    print("\n🤖 What happens next:")
    print("1. Claude Code will read the CLAUDE.md in the session directory")
    print("2. It will analyze the problem in problem.txt")
    print("3. Results will be saved to results.json")
    print("4. The analysis runs in the background")
    
    print("\n📊 To check results:")
    print(f"cat {analyzer.sessions_dir / session_id}/results.json")
    
    print("\n📝 To view logs:")
    print(f"cat {analyzer.sessions_dir / session_id}/analysis.log")
    print(f"cat {analyzer.sessions_dir / session_id}/claude_output.log")
    
    print("\n💡 Tip: The analysis should complete within 1-2 minutes")
    print("=" * 50)


if __name__ == "__main__":
    main()