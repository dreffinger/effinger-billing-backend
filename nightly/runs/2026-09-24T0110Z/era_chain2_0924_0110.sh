#!/bin/bash
# ERA step 5 chain part 2 (2026-09-24T0110Z): after the denial lines are worked - reason-code repair on two Medicare-paid CCM visits whose 819814877 payments were posted code-less
# with no contractual write-off (pat17476094 v19452631, pat17473422 v19452628), era_clear LIVE, after snapshot, payreasons list, columns after-scan
cd /home/claude/unbilled
export DECEASED_CACHE=/home/claude/unbilled/registers/deceased_cache.json
S=2026-09-24T0110Z
while ! grep -q "DENIALS CHAIN DONE" logs/denials_chain_0924_0110.log; do sleep 10; done
echo "### payreasons repair Colby $(date -u +%H:%M:%S)"; timeout 600 python3 payreasons.py --visit 19452631 --pid 17476094 --live --no-release
echo "### payreasons repair Farley $(date -u +%H:%M:%S)"; timeout 600 python3 payreasons.py --visit 19452628 --pid 17473422 --live --no-release
echo "### era_clear LIVE $(date -u +%H:%M:%S)"; timeout 600 python3 era_clear.py
echo "### after snapshot $(date -u +%H:%M:%S)"; timeout 600 python3 era_step_b_0913.py after $S
echo "### payreasons list $(date -u +%H:%M:%S)"; timeout 300 python3 payreasons.py --list
echo "### columns after $(date -u +%H:%M:%S)"; timeout 900 python3 columns_scan_0912.py after > logs/columns_after_0110.log 2>&1; echo "scan exit $?"; grep -E "OVERVIEW|CHARGE REVIEW visits|INSPECTOR visits|UNBILLED totalcount|EXCLUSIONS total" logs/columns_after_0110.log
echo "### ERA CHAIN PART 2 DONE $(date -u +%H:%M:%S)"
