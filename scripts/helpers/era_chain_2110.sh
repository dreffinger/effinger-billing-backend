#!/bin/bash
# ERA step 5 chain for the 2026-09-14T2110Z run (d-e): fallback dry+live, clear dry+live, after-snapshot (era_post --all-unposted already ran at 19:20 UTC: 0 postable)
cd /home/claude/unbilled
S=2026-09-14T2110Z
echo "### fallback DRY $(date -u +%H:%M:%S)"; timeout 600 python3 era_fallback_0913b.py --dry --stamp $S --checks era_checks_before_$S.json
echo "### fallback LIVE $(date -u +%H:%M:%S)"; timeout 600 python3 era_fallback_0913b.py --stamp $S --checks era_checks_before_$S.json --max-faults 3
echo "### era_clear DRY $(date -u +%H:%M:%S)"; timeout 600 python3 era_clear.py --dry
echo "### era_clear LIVE $(date -u +%H:%M:%S)"; timeout 600 python3 era_clear.py
echo "### after snapshot $(date -u +%H:%M:%S)"; timeout 600 python3 era_step_b_0913.py after $S
echo "### ERA CHAIN DONE $(date -u +%H:%M:%S)"
