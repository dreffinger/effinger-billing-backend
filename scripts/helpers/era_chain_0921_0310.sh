#!/bin/bash
# ERA step 5 chain for the 2026-09-21T0310Z run (11pm ET 9/20 slot): b before-snapshot + cache, c era_post --all-unposted, d fallback dry+live, e clear dry+live, after-snapshot
cd /home/claude/unbilled
S=2026-09-21T0310Z
echo "### step b BEFORE $(date -u +%H:%M:%S)"; timeout 900 python3 era_step_b_0913.py before $S
echo "### era_post --all-unposted $(date -u +%H:%M:%S)"; timeout 900 python3 era_post.py --all-unposted
echo "### fallback DRY $(date -u +%H:%M:%S)"; timeout 600 python3 era_fallback_0913b.py --dry --stamp $S --checks era_checks_before_$S.json
echo "### fallback LIVE $(date -u +%H:%M:%S)"; timeout 600 python3 era_fallback_0913b.py --stamp $S --checks era_checks_before_$S.json --max-faults 3
echo "### era_clear DRY $(date -u +%H:%M:%S)"; timeout 600 python3 era_clear.py --dry
echo "### era_clear LIVE $(date -u +%H:%M:%S)"; timeout 600 python3 era_clear.py
echo "### after snapshot $(date -u +%H:%M:%S)"; timeout 600 python3 era_step_b_0913.py after $S
echo "### ERA CHAIN DONE $(date -u +%H:%M:%S)"
