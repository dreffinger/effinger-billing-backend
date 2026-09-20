#!/bin/bash
cd /home/claude/unbilled
echo "### harris $(date -u +%T)"; timeout 300 python3 harris_check_0710.py
echo "### aet12 verify $(date -u +%T)"; timeout 900 python3 aet12_verify_0920_0710.py
bash era_chain_0920_0710.sh
echo "### ALL DONE $(date -u +%T)"
