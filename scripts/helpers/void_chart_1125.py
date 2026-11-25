#!/usr/bin/env python3
# PLAIN ENGLISH (VOID every live charge of one chart from a date on - William 11/25/2026 on chart 20752, the older Corvin Castellane:
#   'we need to void all recent charges in the last few years for the old castellane' / 'void the old ones'. Every charge of 06/06/2024 or
#   later on that chart is the younger man's (chart 12182776); the four visits he still needed were moved there first by move_visit_1125.py.)
# Decides: nothing. Per live charge dated on/after --after: a charge that carries a REAL payment (amount other than $0) is NOT voided -
#   listed for William; otherwise its $0 postings and its write-offs are voided first (the order a charge after a date of death is voided,
#   11/25/2026 lesson: the charge voids only after them), then the charge (void_tx.void_charge), then it is read back void=1.
# Never touches: charges before the date, other charts, anything paid. Usage: python3 void_chart_1125.py <pid> --after mm/dd/yyyy [--live]
# Register: registers/void_chart_1125_<pid>.json
import amd, txh, void_tx, json, re, sys, datetime
args = [a for a in sys.argv[1:] if not a.startswith("--")]; PID = args[0]
AFTER = datetime.datetime.strptime(sys.argv[sys.argv.index("--after") + 1], "%m/%d/%Y").date(); LIVE = "--live" in sys.argv
amd.login_cached(); root = txh.fetch(PID); plan = []; skipped = []
for c in root.iter("charge"):
    a = c.attrib
    if a.get("void") == "1": continue
    dos = datetime.datetime.strptime(a.get("dos"), "%m/%d/%Y").date()
    if dos < AFTER: continue
    pays = [(p.get("id"), p.get("amount"), p.get("checknumber")) for p in c.iter("payment") if p.get("void") != "1"]
    real = [p for p in pays if abs(float(p[1] or 0)) > 0.001]
    wos = [(w.get("id"), w.get("amount"), w.get("wocode")) for w in c.iter("writeoff") if w.get("void") != "1"]
    rec = {"cid": re.sub(r"\D", "", a.get("id")), "visit": re.sub(r"\D", "", a.get("visit") or ""), "dos": a.get("dos"), "cpt": a.get("proccode"), "fee": a.get("fee"),
           "insbal": a.get("insbal"), "patbal": a.get("patbal"), "zero_pays": [p for p in pays if p not in real], "wos": wos}
    if real: rec["real_payments"] = real; skipped.append(rec); continue
    plan.append(rec)
print("pat%s: %d charge(s) dated %s or later to void ($%.2f fee), %d with a real payment left alone" % (PID, len(plan), AFTER, sum(float(r["fee"] or 0) for r in plan), len(skipped)))
for r in plan: print("  void v%s c%s %s %s $%s  $0 postings %d  write-offs %s" % (r["visit"], r["cid"], r["dos"], r["cpt"], r["fee"], len(r["zero_pays"]), [(w[0], w[1], w[2]) for w in r["wos"]]))
for r in skipped: print("  KEEP v%s c%s %s %s - real payment %s" % (r["visit"], r["cid"], r["dos"], r["cpt"], r["real_payments"]))
out = {"pid": PID, "after": str(AFTER), "live": LIVE, "plan": plan, "kept": skipped, "done": []}
if LIVE:
    for r in plan:
        for p in r["zero_pays"]:
            ok, m = void_tx.void_payment(PID, r["cid"], p[0]); r.setdefault("void_pays", []).append((p[0], ok))
        for w in r["wos"]:
            ok, m = void_tx.void_writeoff(PID, r["cid"], w[0]); r.setdefault("void_wos", []).append((w[0], ok))
        ok, m = void_tx.void_charge(PID, r["cid"]); r["void_charge"] = [ok, m[:100]]
        st = void_tx.charge_state(r["cid"]); r["readback"] = st if isinstance(st, (str, int, dict, list)) else str(st)
        print("  c%s %s %s -> void %s | readback %s" % (r["cid"], r["dos"], r["cpt"], ok, str(st)[:80]))
        out["done"].append(r)
json.dump(out, open("registers/void_chart_1125_%s.json" % PID, "w"), indent=1)
