#!/bin/bash
cd /home/claude/unbilled
echo "### aet12 verify $(date -u +%T)"; timeout 900 python3 aet12_verify_0920_1310.py
bash era_chain_0920_1310.sh 2>&1 | tee logs/era_chain_1310.log
echo "### columns AFTER $(date -u +%T)"; timeout 600 python3 columns_scan_0912.py after
echo "### ALL DONE $(date -u +%T)"
