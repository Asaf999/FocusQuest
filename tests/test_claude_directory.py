"""
Test Claude Directory Analyzer functionality
"""
import pytest
import time
import json
from pathlib import Path
from src.analysis.claude_directory_analyzer import ClaudeDirectoryAnalyzer


class TestClaudeDirectoryAnalyzer:
    """Test directory-based Claude Code analyzer"""
    
    def test_directory_analyzer_creation(self):
        """Test analyzer can be created and directories exist"""
        analyzer = ClaudeDirectoryAnalyzer()
        assert analyzer.sessions_dir.exists()
        assert analyzer.template_path.exists()
        
    def test_session_creation(self):
        """Test that analysis sessions are created properly"""
        analyzer = ClaudeDirectoryAnalyzer()
        
        test_problem = "Prove that sqrt(2) is irrational."
        test_metadata = {
            "course": "Introduction to Proofs",
            "topic": "Number Theory",
            "difficulty": "easy"
        }
        
        session_id = analyzer.analyze_problem_async(test_problem, test_metadata)
        
        assert session_id is not None
        assert len(session_id) > 10  # Should have timestamp and UUID
        
        session_dir = analyzer.sessions_dir / session_id
        assert session_dir.exists()
        assert (session_dir / "CLAUDE.md").exists()
        assert (session_dir / "problem.txt").exists()
        assert (session_dir / "session_info.json").exists()
        assert (session_dir / "run_analysis.sh").exists()
        
        # Check problem.txt content
        problem_content = (session_dir / "problem.txt").read_text()
        assert "sqrt(2) is irrational" in problem_content
        assert "Introduction to Proofs" in problem_content
        assert "ADHD student" in problem_content
        
        # Check session info
        with open(session_dir / "session_info.json", 'r') as f:
            session_info = json.load(f)
        assert session_info['session_id'] == session_id
        assert session_info['status'] == 'pending'
        assert session_info['metadata']['course'] == "Introduction to Proofs"
        
    def test_multiple_sessions(self):
        """Test creating multiple analysis sessions"""
        analyzer = ClaudeDirectoryAnalyzer()
        
        problems = [
            ("Prove that the sum of two odd numbers is even.", {"course": "Discrete Math"}),
            ("Find the derivative of f(x) = sin(x)cos(x).", {"course": "Calculus"}),
            ("Solve the equation: x^2 + 5x + 6 = 0", {"course": "Algebra"})
        ]
        
        session_ids = []
        for problem, metadata in problems:
            session_id = analyzer.analyze_problem_async(problem, metadata)
            session_ids.append(session_id)
            time.sleep(0.1)  # Small delay to ensure unique timestamps
            
        assert len(session_ids) == 3
        assert len(set(session_ids)) == 3  # All unique
        
        # Check all sessions exist
        for session_id in session_ids:
            assert (analyzer.sessions_dir / session_id).exists()
            
    def test_session_listing(self):
        """Test listing analysis sessions"""
        analyzer = ClaudeDirectoryAnalyzer()
        
        # Create a test session
        session_id = analyzer.analyze_problem_async(
            "Test problem",
            {"course": "Test Course"}
        )
        
        # List all sessions
        sessions = analyzer.list_sessions()
        assert len(sessions) > 0
        
        # Find our session
        our_session = next((s for s in sessions if s['session_id'] == session_id), None)
        assert our_session is not None
        assert our_session['status'] == 'pending'
        
    def test_manual_session_for_verification(self):
        """Create a test session for manual Claude Code verification"""
        analyzer = ClaudeDirectoryAnalyzer()
        
        test_problem = '''
Let f: R → R be a continuous function such that f(x+y) = f(x) + f(y) 
for all x, y ∈ R. Prove that f(x) = cx for some constant c.

This is known as Cauchy's functional equation. Provide a proof suitable
for an ADHD student, breaking it down into manageable steps.
'''
        
        metadata = {
            "course": "Real Analysis",
            "topic": "Functional Equations",
            "difficulty": "medium"
        }
        
        session_id = analyzer.analyze_problem_async(test_problem, metadata)
        
        print(f"\n🧪 Manual verification session created:")
        print(f"Session ID: {session_id}")
        print(f"Session directory: {analyzer.sessions_dir / session_id}")
        print("\nTo verify Claude Code integration:")
        print(f"1. cd {analyzer.sessions_dir / session_id}")
        print("2. Check if claude processes the CLAUDE.md automatically")
        print("3. Look for results.json when complete")
        
    def test_template_validation(self):
        """Test that the CLAUDE.md template is properly formatted"""
        analyzer = ClaudeDirectoryAnalyzer()
        
        template_content = analyzer.template_path.read_text()
        
        # Check key sections exist
        assert "AUTOMATIC EXECUTION MODE" in template_content
        assert "ADHD-Specific Requirements" in template_content
        assert "results.json" in template_content
        assert "checkpoint_question" in template_content
        assert "BEGIN ANALYSIS IMMEDIATELY" in template_content
        
        # Check JSON structure is present
        assert '"analysis_complete": true' in template_content
        assert '"steps":' in template_content
        assert '"hints":' in template_content