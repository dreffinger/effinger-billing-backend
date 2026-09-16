#!/bin/bash
cd /home/claude/unbilled
bash era_chain_2310.sh > era_chain_2310.log 2>&1
echo "### precheck $(date -u +%H:%M:%S)" >> era_chain_2310.log
timeout 1500 python3 precheck.py --days 3 --max 120 > precheck_2310.log 2>&1
echo "### ALL DONE $(date -u +%H:%M:%S)" >> era_chain_2310.log
