#!/bin/bash
# Emergency stop for gold mining

echo "STOPPING GOLD MINER..."
touch /home/puncher/focusquest/STOP_IMPROVEMENT
tmux kill-session -t gold-miner 2>/dev/null
echo "Gold miner stopped."
echo "Results saved in: golden_nuggets.log"