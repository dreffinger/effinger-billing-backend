#!/usr/bin/env python3
# PLAIN ENGLISH (chart 17472491 - 'send to railroad', William 11/25/2026 08:22Z on card lawford-leilani-17472491-medicare-plan)
# Decides: nothing. The 0721Z run had written the 11/03/2025 99232 ($111, visit 19422192, charge 23327550) off WOLATE by the 12-month
#   rule (write-off 22509876 and its $0 marker payment 24674822, reference PAYREASON2026-11-25T0721Z). William's word reverses that:
#   Railroad Medicare (plan seq 3, car6080 RET01 - the plan that paid her September-November 2026 visits) is her Medicare. This takes the
#   write-off and the $0 marker back (void_tx), moves any balance that landed on the patient back to insurance, then ONE frequency-1 reset
#   + ONE chargerebill to seq 3 (freq1_visit.run), reads the charge back, and names the visit for the timely-filing watch register (a
#   visit William ordered re-sent past the usual window: written off again only on the payer's own timely-filing answer).
# Never touches: other visits, plans, the chart order (already 3,2,4). Usage: python3 lawford_railroad_1018.py [--live]
# Register: registers/lawford_railroad_<stamp>.json
import amd, txh, void_tx, move_to_ins, freq1_visit, re, json, sys, os, time, datetime
LIVE = "--live" in sys.argv
PID, VID, CID, SEQ = "17472491", "19422192", "23327550", "3"
WO, MARKER = "22509876", "24674822"
stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ"); os.makedirs("registers", exist_ok=True)
rec = {"stamp": stamp, "live": LIVE, "pid": PID, "vid": VID, "cid": CID, "seq": SEQ, "steps": []}
amd.login_cached()
def state():
    root = txh.fetch_visit(PID, VID)
    c = next((x for x in root.iter("charge") if x.get("id") == CID), None)
    if c is None: return None
    return {"carrier": c.get("carrier"), "billdate": c.get("billdate"), "fee": c.get("fee"), "insbal": c.get("insbal"), "patbal": c.get("patbal"), "mods": c.get("modifiers"),
            "pays": [(p.get("id"), p.get("amount"), p.get("void"), (p.get("checknumber") or "")[-10:]) for p in c.iter("payment")],
            "wos": [(w.get("id"), w.get("amount"), w.get("void"), w.get("wocode")) for w in c.iter("writeoff")]}
s = state(); print("before:", s); rec["before"] = s
if s is None: print("charge not found"); sys.exit(2)
live_wo = [w for w in s["wos"] if w[0] == WO and w[2] != "1"]; live_marker = [p for p in s["pays"] if p[0] == MARKER and p[2] != "1"]
real_pay = [p for p in s["pays"] if p[2] != "1" and abs(float(p[1] or 0)) > 0]
if real_pay: print("REFUSED - a real payment sits on the charge:", real_pay); sys.exit(2)
if not LIVE:
    print("DRY: would void write-off %s (%s) and the $0 marker payment %s (%s), move a patient balance back (%s now), then freq1 + chargerebill seq %s (Railroad)" % (
        WO, "live" if live_wo else "already void", MARKER, "live" if live_marker else "already void/absent", s["patbal"], SEQ))
    json.dump(rec, open("registers/lawford_railroad_%s.json" % stamp, "w"), indent=1); sys.exit(0)
if live_wo:
    r = void_tx.void_writeoff(PID, CID, WO); print("void write-off ->", str(r)[:200]); rec["steps"].append({"void_writeoff": str(r)[:200]}); time.sleep(0.5)
if live_marker:
    r = void_tx.void_payment(PID, CID, MARKER); print("void marker payment ->", str(r)[:200]); rec["steps"].append({"void_payment": str(r)[:200]}); time.sleep(0.5)
s2 = state(); print("after voids:", s2); rec["after_voids"] = s2
if float(s2["patbal"] or 0) > 0:
    r = move_to_ins.move(CID, rebill=False); print("move patient balance back ->", str(r)[:200]); rec["steps"].append({"move_to_ins": str(r)[:200]}); time.sleep(0.5)
    s2 = state(); print("after move:", s2)
if float(s2["insbal"] or 0) <= 0:
    print("STOP - no insurance balance to send (%s)" % s2["insbal"]); json.dump(rec, open("registers/lawford_railroad_%s.json" % stamp, "w"), indent=1); sys.exit(2)
r = freq1_visit.run(VID, CID, SEQ); print("freq1 ->", r); rec["steps"].append({"freq1": str(r)[:200]})
time.sleep(1); s3 = state(); print("read back:", s3); rec["after"] = s3
json.dump(rec, open("registers/lawford_railroad_%s.json" % stamp, "w"), indent=1); print("register: registers/lawford_railroad_%s.json" % stamp)
