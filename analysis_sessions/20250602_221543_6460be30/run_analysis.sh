#!/bin/bash
cd /home/puncher/focusquest/analysis_sessions/20250602_221543_6460be30

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
echo '{"execution_complete": true, "timestamp": "'$(date -Iseconds)'"}' > execution_status.json
