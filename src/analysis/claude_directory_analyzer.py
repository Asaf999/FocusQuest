"""
Fully automated Claude Code directory-based analyzer
Each problem gets its own Claude Code session with custom instructions
"""
import os
import json
import shutil
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import threading
import uuid
import logging

logger = logging.getLogger(__name__)


class ClaudeDirectoryAnalyzer:
    """Fully automated Claude Code directory-based analyzer"""
    
    def __init__(self):
        self.project_root = Path("/home/puncher/focusquest")
        self.sessions_dir = self.project_root / "analysis_sessions"
        self.template_path = self.project_root / "analysis_templates" / "CLAUDE_ANALYSIS_TEMPLATE.md"
        self.sessions_dir.mkdir(exist_ok=True)
        
    def analyze_problem_async(self, problem_text: str, metadata: Dict) -> str:
        """Launch background Claude Code analysis, return session_id"""
        
        # Create unique session
        session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir()
        
        logger.info(f"Creating analysis session: {session_id}")
        
        # Setup session files
        self._setup_session(session_dir, problem_text, metadata)
        
        # Launch Claude Code in background
        self._launch_background_claude(session_dir)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=self._monitor_session,
            args=(session_id,),
            daemon=True
        )
        monitor_thread.start()
        
        return session_id
        
    def _setup_session(self, session_dir: Path, problem_text: str, metadata: Dict):
        """Setup session directory with all needed files"""
        
        # Copy CLAUDE.md template
        shutil.copy(self.template_path, session_dir / "CLAUDE.md")
        
        # Create problem.txt with metadata
        problem_content = f"""PROBLEM METADATA:
Course: {metadata.get('course', 'Mathematics')}
Topic: {metadata.get('topic', 'General')}
Difficulty Estimate: {metadata.get('difficulty', 'medium')}
Source: {metadata.get('source', 'PDF')}
Page: {metadata.get('page', 'Unknown')}

PROBLEM TEXT:
{problem_text}

SPECIAL INSTRUCTIONS:
- This is for an ADHD student
- Final semester at Tel Aviv University
- Prefers visual/concrete explanations
- Gets overwhelmed by abstract notation
- Needs dopamine hits from progress

Analyze this problem according to CLAUDE.md instructions.
"""
        
        (session_dir / "problem.txt").write_text(problem_content, encoding='utf-8')
        
        # Create session_info.json
        session_info = {
            "session_id": session_dir.name,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "metadata": metadata
        }
        
        (session_dir / "session_info.json").write_text(
            json.dumps(session_info, indent=2)
        )
        
    def _launch_background_claude(self, session_dir: Path):
        """Launch Claude Code in background (headless)"""
        
        # Create launch script for background execution
        launch_script = session_dir / "run_analysis.sh"
        script_content = f"""#!/bin/bash
cd {session_dir}

# Log start time
echo "Analysis started at $(date)" > analysis.log

# Set environment for automated execution
export CLAUDE_AUTO_ACCEPT=true
export CLAUDE_AUTO_APPROVE_PATHS="/home/puncher"

# Run claude with the initial prompt
claude << 'EOF' >> analysis.log 2>&1
Read the CLAUDE.md file in this directory for instructions.
Read problem.txt and analyze it according to the CLAUDE.md instructions.
Create results.json with the complete analysis.
This is fully automated - complete all tasks without user input.
EOF

# Log completion
echo "Analysis completed at $(date)" >> analysis.log

# Mark execution complete
echo '{{"execution_complete": true, "timestamp": "'$(date -Iseconds)'"}}' > execution_status.json
"""
        
        launch_script.write_text(script_content)
        launch_script.chmod(0o755)
        
        # Execute in background using nohup
        subprocess.Popen(
            f"nohup {launch_script} > {session_dir}/claude_output.log 2>&1 &",
            shell=True,
            cwd=session_dir
        )
        
        logger.info(f"Launched Claude Code for session in {session_dir}")
        
    def _monitor_session(self, session_id: str):
        """Monitor session for completion and process results"""
        
        session_dir = self.sessions_dir / session_id
        results_path = session_dir / "results.json"
        execution_status_path = session_dir / "execution_status.json"
        timeout = 300  # 5 minutes max
        start_time = time.time()
        
        logger.info(f"Monitoring session {session_id}")
        
        while time.time() - start_time < timeout:
            # Check for results
            if results_path.exists():
                try:
                    # Wait for file to be fully written
                    time.sleep(2)
                    
                    # Read and validate results
                    with open(results_path, 'r') as f:
                        results = json.load(f)
                        
                    if results.get('analysis_complete'):
                        # Process successful results
                        self._process_results(session_id, results)
                        return
                        
                except json.JSONDecodeError:
                    # File still being written
                    logger.debug(f"Results file not ready yet for {session_id}")
                    
            # Check execution status
            if execution_status_path.exists():
                try:
                    with open(execution_status_path, 'r') as f:
                        status = json.load(f)
                    if status.get('execution_complete'):
                        # Claude finished but maybe no results
                        if not results_path.exists():
                            self._mark_session_failed(session_id, "No results generated")
                            return
                except json.JSONDecodeError:
                    pass
                    
            time.sleep(5)
            
        # Timeout - mark as failed
        self._mark_session_failed(session_id, "Timeout after 5 minutes")
        
    def _process_results(self, session_id: str, results: Dict):
        """Process successful analysis results"""
        
        # Update session info
        session_dir = self.sessions_dir / session_id
        session_info_path = session_dir / "session_info.json"
        
        with open(session_info_path, 'r') as f:
            session_info = json.load(f)
            
        session_info['status'] = 'complete'
        session_info['completed_at'] = datetime.now().isoformat()
        session_info['results_summary'] = {
            'steps_count': len(results.get('steps', [])),
            'total_time': results.get('total_time_estimate', 0),
            'difficulty': results.get('difficulty', 'unknown')
        }
        
        with open(session_info_path, 'w') as f:
            json.dump(session_info, f, indent=2)
            
        # TODO: Store in database when db_manager is ready
        # from src.database.db_manager import DatabaseManager
        # db = DatabaseManager()
        # db.store_analysis_results(session_id, results)
        
        logger.info(f"✅ Session {session_id} complete: {len(results['steps'])} steps generated")
        print(f"✅ Session {session_id} complete: {len(results['steps'])} steps generated")
        
    def _mark_session_failed(self, session_id: str, reason: str):
        """Mark session as failed"""
        
        session_dir = self.sessions_dir / session_id
        error_info = {
            "session_id": session_id,
            "status": "failed",
            "error": reason,
            "timestamp": datetime.now().isoformat()
        }
        
        (session_dir / "error.json").write_text(json.dumps(error_info, indent=2))
        
        logger.error(f"Session {session_id} failed: {reason}")
        print(f"❌ Session {session_id} failed: {reason}")
        
    def get_session_results(self, session_id: str) -> Optional[Dict]:
        """Retrieve results for a completed session"""
        
        results_path = self.sessions_dir / session_id / "results.json"
        if results_path.exists():
            with open(results_path, 'r') as f:
                return json.load(f)
        return None
        
    def list_sessions(self, status: Optional[str] = None) -> List[Dict]:
        """List all analysis sessions, optionally filtered by status"""
        
        sessions = []
        for session_dir in self.sessions_dir.iterdir():
            if session_dir.is_dir():
                info_path = session_dir / "session_info.json"
                if info_path.exists():
                    with open(info_path, 'r') as f:
                        info = json.load(f)
                    if status is None or info.get('status') == status:
                        sessions.append(info)
                        
        return sorted(sessions, key=lambda x: x['created_at'], reverse=True)