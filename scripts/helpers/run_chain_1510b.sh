#!/bin/bash
# resume of run_chain_1510.sh after the registers were restored (step b + era_post already done)
cd /home/claude/unbilled
S=2026-09-20T1510Z
echo "### fallback DRY $(date -u +%H:%M:%S)"; timeout 600 python3 era_fallback_0913b.py --dry --stamp $S --checks era_checks_before_$S.json
echo "### fallback LIVE $(date -u +%H:%M:%S)"; timeout 600 python3 era_fallback_0913b.py --stamp $S --checks era_checks_before_$S.json --max-faults 3
echo "### era_clear DRY $(date -u +%H:%M:%S)"; timeout 600 python3 era_clear.py --dry
echo "### era_clear LIVE $(date -u +%H:%M:%S)"; timeout 600 python3 era_clear.py
echo "### after snapshot $(date -u +%H:%M:%S)"; timeout 600 python3 era_step_b_0913.py after $S
echo "### ERA CHAIN DONE $(date -u +%H:%M:%S)"
echo "### aet12 verify $(date -u +%T)"; timeout 900 python3 aet12_verify_0920_1510.py
echo "### columns AFTER $(date -u +%T)"; timeout 600 python3 columns_scan_0912.py after
echo "### ALL DONE $(date -u +%T)"
