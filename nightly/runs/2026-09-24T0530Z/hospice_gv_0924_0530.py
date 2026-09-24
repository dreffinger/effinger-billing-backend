#!/usr/bin/env python3
# Nightly cascade 2026-09-24T0530Z: hospice COB9 lines on the dismissed $0 Medicare check 1052829 (349992844).
# William's standing rule (9/20): hospice denial = GV modifier + rebill to Medicare. gv_rebill.run reverses every
# COB9 $0 posting in the last 364 days, adds GV (full-visit echo) and rebills; this wrapper adds an UPPER date
# bound so AVERILL's post-death visit (DOD [DOB], deceased_cache 9/22) is left for rule (e), and handles
# DASHWOOD's 8/23 visit directly (its denial arrived tonight and was never posted as $0, so run() does not see it).
import gv_rebill, txh, void_tx, move_to_ins, freq1_visit, amd, resave, json, sys, time, datetime, re
DRY = "--dry" in sys.argv
amd.login_cached()
REG = "registers/hospice_gv_register.json"
try: reg = json.load(open(REG))
except Exception: reg = []
def log(pid, vid, what):
    print(pid, vid, what, flush=True); reg.append({"stamp": "2026-09-24T0530Z", "pid": pid, "visit": vid, "result": what, "check": 1052829})

def run_bounded(pid, seq, until=None, codes=("COB9", "PRB9"), since=datetime.date.today() - datetime.timedelta(days=364)):
    pid = str(pid); h = txh.fetch("pat" + pid); visits = {}
    for c in h.iter("charge"):
        if c.get("void") == "1" or (c.get("fee") or "").startswith("-") or not c.get("dos"): continue
        d = datetime.datetime.strptime(c.get("dos"), "%m/%d/%Y").date()
        if d < since or (until and d > until): continue
        for p in c.iter("payment"):
            if p.get("void") != "1" and float(p.get("amount") or 0) == 0 and any(r.get("code") in codes for r in p.iter("payreason")):
                if DRY: log(pid, c.get("visit"), "DRY %s %s" % (c.get("dos"), c.get("proccode"))); continue
                void_tx.void_payment(pid, c.get("id"), p.get("id")); time.sleep(0.4)
                st = void_tx.charge_state(c.get("id"))
                for wo in st[1]:
                    if wo.get("void") != "1" and wo.get("Writeoffcode") == "WOINS": void_tx.void_writeoff(pid, c.get("id"), wo["id"]); time.sleep(0.4)
                st = void_tx.charge_state(c.get("id")); log(pid, c.get("visit"), "%s %s reversed, insbal %s" % (c.get("dos"), c.get("proccode"), st[0].get("insbalance")))
                visits[c.get("visit")] = c.get("id")
    for v, cid in visits.items():
        g = gv_rebill.add_gv(cid); mv = move_to_ins.move(cid, seq) if not g.startswith("FAULT") else "SKIP rebill"
        log(pid, v, "%s -> %s" % (g, mv)); time.sleep(0.5)

# MACKLIN 12235552 (Medicare seq 1, no DOD) and AVERILL 17472784 (Medicare seq 1, DOD [DOB] -> visits through 7/13 only)
run_bounded("12235552", "1")
run_bounded("17472784", "1", until=datetime.date(2026, 7, 13))
# DASHWOOD 17471496: visit 19452657 (8/23/2026, 99487 charge 23363033 + 99489 charge 23363034), Medicare = seq 2
if DRY: log("17471496", "19452657", "DRY direct GV + rebill seq 2")
else:
    g = gv_rebill.add_gv("23363033"); log("17471496", "19452657", "add_gv -> " + g)
    if not g.startswith("FAULT"):
        r = freq1_visit.run("19452657", "23363033", "2"); log("17471496", "19452657", "freq1_visit seq 2 -> " + str(r)[:200])
if not DRY: json.dump(reg, open(REG, "w"), indent=1)
print("=== done ===")
