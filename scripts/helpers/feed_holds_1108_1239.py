#!/usr/bin/env python3
# PLAIN ENGLISH (feed-cascade hold on chart 17471478, 7:39 AM ET 11/8 columns run, fired 12:39Z):
# Decides: nothing new. The 11/8 Claimocity file named two payers for this chart - Medicare First Coast (seq 1, on the chart, AMD 271
#   ACTIVE) and Tricare for Life (IN1 set 2 with a member id) - and the chart carried Medicare alone. William's standing rule: a Medicare
#   record with TRICARE = Medicare primary + TRICARE For Life (TRI05 car6559) secondary. The cascade's HOLD ('CMS reports MA/other primary
#   UNITED SERVICES AUTOMOBILE ASSOC') is the CMS 271's Non-Group Health Plan ORM record (an auto-liability MSP file, DOL 11/30/2018,
#   accident diagnoses) - not a health plan, so Medicare stays primary for the 11/7/2026 99232.
# Does: add_ins TRI05 with the feed's member id (no group number), patient order Medicare,TFL (ins_update sequence), the visit's
#   insorder to Medicare,TFL with the full-visit echo (resave.set_insorder - never a single-charge resave), AMD 271 on the new plan.
#   No rebill (the claim has not left yet - it goes on the next claim run with the secondary queued by AMD itself).
# Rules it uses: no group numbers; the void trap (full charge echo); member id never printed. Never touches: payments, write-offs, claims.
# Usage: python3 feed_holds_1108_1239.py [--live]     register: registers/feed_holds_2026-11-08T1239Z[_dry].json
import sys, re, json, time, amd, add_ins, ins_update, resave
LIVE = "--live" in sys.argv
PID, CID, VID = "17471478", "charge23373233", "19460527"
raw = open("inbox/claimocity/download__20261108626627aa54d52f67a80d586a.hl7", "rb").read().decode("latin-1")
member = None
for m in re.split(r"(?=MSH\|)", raw):
    if "66c63e40026452cacfe6daae" in m:
        for seg in re.split(r"[\r\n]+", m):
            f = seg.split("|")
            if f[0] == "IN1" and len(f) > 49 and "tricare" in (f[4] or "").lower():
                member = f[49].strip()
if not member: sys.exit("no TFL member id in the feed message")
out = {"stamp": "2026-11-08T1239Z", "pid": PID, "visit": VID, "live": LIVE, "member_len": len(member), "steps": []}
print("TFL member id found (len %d), live=%s" % (len(member), LIVE))
if LIVE:
    amd.login_cached()
    insid, seq = add_ins.add(PID, "car6559", member, begindate="01/01/2026", coverage="2", finclass="CC")
    out["steps"].append({"add_ins": str(insid), "seq": str(seq)}); print("add_ins ->", insid, "seq", seq)
    order = "1,%s" % seq
    r = ins_update.update(PID, insid, sequence=order); out["steps"].append({"ins_update sequence": order, "r": str(r)[:200]}); print("patient order", order, str(r)[:120])
    time.sleep(0.5)
    r2 = resave.set_insorder(CID, order); out["steps"].append({"set_insorder": order, "r": str(r2)[:300]}); print("visit insorder", order, str(r2)[:200])
    try:
        e = amd.check_eligibility(insid); s = json.dumps(e) if not isinstance(e, str) else e
        st = "ACTIVE" if "ACTIVE" in s.upper() and "INACTIVE" not in s.upper() else ("INACTIVE" if "INACTIVE" in s.upper() else "see raw")
        aaa = re.findall(r'AAA\*[^*]*\*[^*]*\*(\d+)', s)[:3]
        out["steps"].append({"amd271": st, "aaa": aaa}); print("AMD 271 on the new plan:", st, aaa)
    except Exception as ex:
        out["steps"].append({"amd271_error": str(ex)[:200]}); print("271 error", str(ex)[:200])
json.dump(out, open("registers/feed_holds_2026-11-08T1239Z%s.json" % ("" if LIVE else "_dry"), "w"), indent=1)
