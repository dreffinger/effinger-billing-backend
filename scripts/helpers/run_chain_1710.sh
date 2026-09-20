#!/bin/bash
cd /home/claude/unbilled
echo "### aet12 verify $(date -u +%T)"; timeout 900 python3 aet12_verify_0920_1710.py
bash era_chain_0920_1710.sh 2>&1 | tee logs/era_chain_1710.log
echo "### columns AFTER $(date -u +%T)"; timeout 600 python3 columns_scan_0912.py after > logs/columns_after_1710.log 2>&1; tail -3 logs/columns_after_1710.log
echo "### ALL DONE $(date -u +%T)"
