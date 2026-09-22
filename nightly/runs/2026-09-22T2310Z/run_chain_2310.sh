#!/bin/bash
cd /home/claude/unbilled
S=2026-09-22T2310Z
bash era_chain_0922_2310.sh 2>&1 | tee logs/era_chain_2310.log
echo "### precheck $(date -u +%T)"; timeout 1500 python3 precheck.py --days 3 --max 120 > logs/precheck_2310.log 2>&1; echo "precheck exit=$?"; tail -25 logs/precheck_2310.log
echo "### columns AFTER $(date -u +%T)"; timeout 600 python3 columns_scan_0912.py after > logs/columns_after_2310.log 2>&1; head -3 logs/columns_after_2310.log; grep -n "UNBILLED totalcount\|EXCLUSIONS total\|INSPECTOR visits" logs/columns_after_2310.log
echo "### ALL DONE $(date -u +%T)"
