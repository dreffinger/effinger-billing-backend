#!/bin/bash
cd /home/claude/unbilled
echo "### harris $(date -u +%T)"; timeout 300 python3 harris_check_2310.py
echo "### aet12 verify $(date -u +%T)"; timeout 900 python3 aet12_verify_0919_2310.py
bash era_chain_0919_2310.sh
echo "### precheck $(date -u +%T)"; timeout 1500 python3 precheck.py --days 3 --max 120
echo "### ALL DONE $(date -u +%T)"
