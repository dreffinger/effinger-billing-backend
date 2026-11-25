#!/usr/bin/env python3
# PLAIN ENGLISH (charts 48458 / 17469674 / 17472573 - one person: every live charge dated after her date of death is voided, [DOB])
# Decides: nothing. Medicare's record (danvers_medicare_1018.py, look-up with the SSN) gives a date of death of [DOB] - the same day
#   the facility's payer history says 'STOP BILLING'. William's standing word (10/4/2026 and again 11/25/2026): "VOID all charges sent
#   after date of death" - never a write-off, never a question. For every non-void charge dated AFTER 12/24/2025 on the three charts this
#   takes back its write-offs and $0 postings first (void_tx.void_writeoff / void_payment - the 11/25 WATCH: a voided charge keeps them
#   until they go first), then voids the charge (void_tx.void_charge) and reads it back void. A charge carrying a real payment (> 0, not
#   void) is listed for William and left alone (a paid charge is not covered by the void rule).
# Never touches: charges on or before the date of death, plans, other charts. Usage: python3 danvers_afterdeath_1018.py [--live]
# Register: registers/danvers_afterdeath_<stamp>.json
import amd, txh, void_tx, re, json, sys, os, time, datetime
LIVE = "--live" in sys.argv
DOD = "[DOB]"; CHARTS = ["48458", "17469674", "17472573"]
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ"); os.makedirs("registers", exist_ok=True)
rec = {"stamp": stamp, "live": LIVE, "dod": DOD, "lines": []}
amd.login_cached()
def iso(d):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", d or ""); return "%s-%s-%s" % (m.group(3), m.group(1), m.group(2)) if m else ""
for pid in CHARTS:
    root = txh.fetch(pid)
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or iso(a.get("dos")) <= DOD: continue
        cid = a.get("id"); pays = [p.attrib for p in c.iter("payment")]; wos = [w.attrib for w in c.iter("writeoff")]
        real = [p for p in pays if p.get("void") != "1" and abs(float(p.get("amount") or 0)) > 0.001]
        line = {"pid": pid, "cid": cid, "vid": a.get("visit"), "dos": a.get("dos"), "cpt": a.get("proccode"), "fee": a.get("fee"), "insbal": a.get("insbal"), "patbal": a.get("patbal"),
                "live_wos": [(w.get("id"), w.get("amount"), w.get("wocode")) for w in wos if w.get("void") != "1"],
                "live_zero_pays": [(p.get("id"), p.get("amount")) for p in pays if p.get("void") != "1" and abs(float(p.get("amount") or 0)) <= 0.001], "real_pays": [(p.get("id"), p.get("amount")) for p in real], "steps": []}
        if real: line["result"] = "LEFT FOR WILLIAM - a real payment sits on a charge dated after the death"; rec["lines"].append(line); print(line); continue
        if not LIVE: line["result"] = "DRY: would void %d write-off(s) and %d $0 posting(s), then the charge" % (len(line["live_wos"]), len(line["live_zero_pays"])); rec["lines"].append(line); print(line); continue
        for w in line["live_wos"]: ok, msg = void_tx.void_writeoff(pid, cid, w[0]); line["steps"].append(["void wo", w[0], ok, str(msg)[:80]]); time.sleep(0.3)
        for p in line["live_zero_pays"]: ok, msg = void_tx.void_payment(pid, cid, p[0]); line["steps"].append(["void pay", p[0], ok, str(msg)[:80]]); time.sleep(0.3)
        ok, msg = void_tx.void_charge(pid, cid); line["steps"].append(["void charge", ok, str(msg)[:80]]); time.sleep(0.5)
        ch2, _, _ = void_tx.charge_state(cid); line["result"] = "after: void=%s insbal=%s patbal=%s" % (ch2.get("void"), ch2.get("insbalance"), ch2.get("patbalance"))
        rec["lines"].append(line); print(line)
print("%d charge(s) dated after %s on %s" % (len(rec["lines"]), DOD, CHARTS))
json.dump(rec, open("registers/danvers_afterdeath_%s.json" % stamp, "w"), indent=1); print("register: registers/danvers_afterdeath_%s.json" % stamp)
