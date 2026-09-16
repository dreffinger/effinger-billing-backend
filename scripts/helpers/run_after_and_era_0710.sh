#!/bin/bash
cd /home/claude/unbilled
echo "### columns after-scan $(date -u +%H:%M:%S)"; timeout 900 python3 columns_scan_0912.py after > columns_after_0710.log 2>&1; tail -3 columns_after_0710.log
bash era_chain_0710.sh
