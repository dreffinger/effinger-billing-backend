#!/bin/bash
cd /home/claude/unbilled
echo "### unbilled fix LIVE $(date -u +%T)"; timeout 900 python3 unbilled_fix_0920_0910.py
echo "### aet12 verify $(date -u +%T)"; timeout 900 python3 aet12_verify_0920_0910.py
echo "### columns AFTER $(date -u +%T)"; timeout 600 python3 columns_scan_0912.py after
bash era_chain_0920_0910.sh
echo "### ALL DONE $(date -u +%T)"
