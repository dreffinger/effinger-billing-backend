#!/bin/bash
# 2026-09-23T0710Z run (1am ET 9/23 slot): inspector live -> columns after -> ERA chain -> run outputs
cd /home/claude/unbilled
export DECEASED_CACHE=/home/claude/unbilled/registers/deceased_cache.json
S=2026-09-23T0710Z
echo "### inspector live $(date -u +%H:%M:%S)"; timeout 1500 python3 insp_0923_0710.py > logs/insp_0923_0710.log 2>&1; echo "insp exit $?"
echo "### columns after $(date -u +%H:%M:%S)"; timeout 900 python3 columns_scan_0912.py after > logs/columns_after_0510.log 2>&1; echo "scan exit $?"
echo "### era chain $(date -u +%H:%M:%S)"; bash era_chain_0923_0710.sh > logs/era_chain_0923_0710.log 2>&1; echo "era exit $?"
echo "### outputs $(date -u +%H:%M:%S)"; python3 run_outputs_0923_0710.py
echo "### CHAIN DONE $(date -u +%H:%M:%S)"
