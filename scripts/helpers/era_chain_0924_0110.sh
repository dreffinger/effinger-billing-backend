#!/bin/bash
# ERA step 5 chain for the 2026-09-24T0110Z run (9pm ET 9/23 slot): Post button on the 2 new checks, fallback dry+live; era_clear DRY only (live clear after the denial lines are worked)
cd /home/claude/unbilled
export DECEASED_CACHE=/home/claude/unbilled/registers/deceased_cache.json
S=2026-09-24T0110Z
echo "### era_post --all-unposted $(date -u +%H:%M:%S)"; timeout 900 python3 era_post.py --all-unposted
echo "### fallback DRY"; timeout 600 python3 era_fallback_0913b.py --dry --stamp $S --checks era_checks_before_$S.json
echo "### fallback LIVE"; timeout 600 python3 era_fallback_0913b.py --stamp $S --checks era_checks_before_$S.json --max-faults 3
echo "### era_clear DRY"; timeout 600 python3 era_clear.py --dry
echo "### ERA CHAIN PART 1 DONE $(date -u +%H:%M:%S)"
