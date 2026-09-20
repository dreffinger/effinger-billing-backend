#!/bin/bash
cd /home/claude/unbilled
echo "### aet12 verify $(date -u +%T)"; timeout 900 python3 aet12_verify_0920_1510.py
bash era_chain_0920_1510.sh 2>&1 | tee logs/era_chain_1510.log
echo "### columns AFTER $(date -u +%T)"; timeout 600 python3 columns_scan_0912.py after
echo "### ALL DONE $(date -u +%T)"
