#!/usr/bin/env python3
# PLAIN ENGLISH: William pasted hospital (Epic) demographics on the board 11/25/2026 06:40-06:50Z for charts whose Medicare number
# AdvancedMD rejects (72). Where the pasted Medicare number DIFFERS from the chart's, run medicare_number_fix.fix with that number as
# the only candidate (write it, prove it with AdvancedMD's free 271 - ACTIVE or the old number goes back - then re-send the unpaid
# Medicare visits under 12 months once each). The register's 'source' reads "the facility's feed": here it is William's paste.
# Usage: python3 mbi_paste_fix_1125c.py <pid>=<MBI> [...] [--live]
import sys, json, os
sys.path.insert(0, "/home/claude/unbilled")
import amd, medicare_number_fix as m
LIVE = "--live" in sys.argv
amd.login_cached(); f = "registers/medicare_number_fix.json"; reg = json.load(open(f)) if os.path.exists(f) else {}
for a in sys.argv[1:]:
    if "=" not in a: continue
    pid, mbi = a.split("=", 1)
    m.feed_numbers = (lambda n: (lambda pid: [n]))(m.norm(mbi))
    r = m.fix(pid, LIVE, False, reg); print("pat%s ->" % pid, r.get("number"), {k: v for k, v in r.get("visits", {}).items()})
    if LIVE: json.dump(reg, open(f, "w"), indent=1)
