#!/bin/bash
cd /home/claude/unbilled
while pgrep -f "era_step_b_0913.py before" >/dev/null; do sleep 10; done
echo "### before-step finished $(date -u +%H:%M:%S)"; tail -3 era_before_1310.log
bash era_chain_1310.sh
