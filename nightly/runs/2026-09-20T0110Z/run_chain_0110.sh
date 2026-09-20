#!/bin/bash
cd /home/claude/unbilled
echo "### harwick $(date -u +%T)"; timeout 300 python3 harwick_check_0110.py
echo "### aet12 verify $(date -u +%T)"; timeout 900 python3 aet12_verify_0920_0110.py
bash era_chain_0920_0110.sh
echo "### ALL DONE $(date -u +%T)"
