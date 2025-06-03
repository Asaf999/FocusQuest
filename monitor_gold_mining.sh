#!/bin/bash
# Real-time monitoring of gold mining progress

watch -n 5 '
echo "=== FOCUSQUEST GOLD MINING MONITOR ==="
echo ""
echo "Current Cycle:"
tail -5 current_phase.md
echo ""
echo "Recent Improvements:"
tail -10 golden_nuggets.log | grep "Improved"
echo ""
echo "Test Status:"
pytest tests/ --tb=no 2>/dev/null | grep -E "passed|failed|TOTAL"
echo ""
echo "Recent Commits:"
git log --oneline -5
echo ""
echo "Memory Usage:"
ps aux | grep python | head -3
'