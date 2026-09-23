#!/bin/bash
# ERA step 5 chain for the 2026-09-23T2310Z run (7pm ET 9/23 slot): before snapshot already taken at 21:26Z (0 checks) -> after snapshot + payreasons list only
cd /home/claude/unbilled
export DECEASED_CACHE=/home/claude/unbilled/registers/deceased_cache.json
S=2026-09-23T2310Z
N=$(python3 -c "import json;print(len(json.load(open('era_checks_before_$S.json'))))")
echo "### unposted checks before: $N"
if [ "$N" != "0" ]; then
echo "### era_post --all-unposted $(date -u +%H:%M:%S)"; timeout 900 python3 era_post.py --all-unposted
echo "### fallback DRY"; timeout 600 python3 era_fallback_0913b.py --dry --stamp $S --checks era_checks_before_$S.json
echo "### fallback LIVE"; timeout 600 python3 era_fallback_0913b.py --stamp $S --checks era_checks_before_$S.json --max-faults 3
echo "### era_clear DRY"; timeout 600 python3 era_clear.py --dry
echo "### era_clear LIVE"; timeout 600 python3 era_clear.py
fi
echo "### after snapshot $(date -u +%H:%M:%S)"; timeout 600 python3 era_step_b_0913.py after $S
echo "### payreasons list $(date -u +%H:%M:%S)"; timeout 300 python3 payreasons.py --list
echo "### ERA CHAIN DONE $(date -u +%H:%M:%S)"
