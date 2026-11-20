# PLAIN ENGLISH (Wrong Medicare number on the chart, right one in the feed: fix it and re-send what Medicare never paid - 11/20/2026)
# Decides: Nothing. Standing cascade rule (d) 'MBI MISMATCH -> fix the chart's Medicare number in place and rebill'. For each chart
#          given, the feed's Medicare number (read from in1_mismatch_review_1120.json - never typed here) was answered ACTIVE by
#          Medicare through Stedi on 11/20/2026 while AdvancedMD's free check rejects the chart's number as invalid (72). This:
#          (1) writes the feed's number on the chart's Medicare plan (ins_update), (2) runs AdvancedMD's free check on it and puts
#          the old number back if the answer is not ACTIVE, (3) re-sends as ONE frequency-1 original claim every visit that is
#          open at Medicare, carries no payment at all (a $0 denial posting is not a payment), and is not older than 12 months
#          (older ones are listed, not sent and not written off - William's call).
# Never touches: paid visits, secondary balances, other plans, the insurance order.
# Usage: python3 mbi_fix_resend_1120.py <pid> [<pid> ...] [--live]      Register: registers/mbi_fix_resend_1120.json
import amd, ins_update, elig_amd, freq1_visit, dx_primary_fix, resave, txh, json, re, sys, os, time, datetime, collections
LIVE = "--live" in sys.argv; amd.login_cached()
REV = {r["pid"]: r for r in json.load(open("in1_mismatch_review_1120.json")) if r["code"] == "FLO02" and r["verdict"] == "CHART NOT CONFIRMED"}
f = "registers/mbi_fix_resend_1120.json"; reg = json.load(open(f)) if os.path.exists(f) else {}
today = datetime.date.today()
for pid in [a for a in sys.argv[1:] if not a.startswith("--")]:
    r = REV.get(pid)
    if not r: print("pat%s: not on the reviewed list - nothing done" % pid); continue
    new = re.sub(r"[^A-Za-z0-9]", "", r["feed"]).upper(); insid = r["ins"]; rec = reg.setdefault(pid, {"ins": insid, "visits": {}})
    _, plans, order = ins_update._plans(pid); p = plans[insid]; old = p.get("subscribernum"); seq = p.get("sequence")
    print("\n== pat%s Medicare plan %s seq %s, chart order %s; number on chart %s the feed's" % (pid, insid, seq, order, "already is" if (old or "").upper() == new else "differs from"))
    if (old or "").upper() != new:
        if not LIVE: print("  DRY would write the feed's Medicare number on %s and check it" % insid)
        else:
            print("  update ->", str(ins_update.update(pid, insid, subscribernum=new))[:120]); time.sleep(0.5)
            s = elig_amd.run_plan(pid, insid.replace("ins", ""), True); st = str(s.get("status") or "")
            print("  AdvancedMD 271 on the new number: %s A %s B %s" % (st, s.get("partA"), s.get("partB")))
            if not st.upper().startswith("ACTIVE"):
                print("  NOT ACTIVE - old number put back:", str(ins_update.update(pid, insid, subscribernum=old))[:100]); rec["number"] = "put back - 271 %s" % st[:30]; json.dump(reg, open(f, "w"), indent=1); continue
            rec["number"] = "corrected from the feed; 271 ACTIVE"
    byv = collections.OrderedDict()
    for c in txh.fetch(pid).iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        pays = [x for x in c.iter("payment") if x.get("void") != "1" and abs(float(x.get("amount") or 0)) > 0.005]
        byv.setdefault(a.get("visit"), []).append((a, len(pays)))
    for vid, cs in byv.items():
        if not any(a.get("carrier") == "FLO02" and float(a.get("insbal") or 0) > 0.005 for a, _ in cs): continue
        if any(n for _, n in cs): continue                                   # a payment on any line: settled or a secondary balance - never re-sent
        a0 = cs[0][0]; m, d, y = a0.get("dos").split("/"); age = (today - datetime.date(int(y), int(m), int(d))).days
        amt = sum(float(a.get("insbal") or 0) for a, _ in cs)
        if age > 365: rec["visits"][vid] = "older than 12 months - not sent, not written off (%s, %.2f)" % (a0.get("dos"), amt); print("  v%s %s $%.2f: older than 12 months - listed for William" % (vid, a0.get("dos"), amt)); continue
        if "204" in str(rec["visits"].get(vid, "")): print("  v%s already re-sent" % vid); continue
        vis, pat, allc = resave.visit_charges(a0.get("id")); vorder = (vis.get("insorder") or "").replace(" ", "")
        if vorder.split(",")[0] != str(seq): rec["visits"][vid] = "visit order %s does not start with Medicare - not sent" % vorder; print("  v%s %s $%.2f: visit order %s does not start with Medicare (seq %s) - not sent" % (vid, a0.get("dos"), amt, vorder, seq)); continue
        if not LIVE: print("  v%s %s %s $%.2f order %s: DRY would re-send to Medicare as an original claim" % (vid, a0.get("dos"), [a.get("proccode") for a, _ in cs], amt, vorder)); continue
        res = freq1_visit.run(vid, a0.get("id"), seq); rec["visits"][vid] = "%s %.2f %s" % (a0.get("dos"), amt, res[-40:]); print("  v%s %s $%.2f: %s" % (vid, a0.get("dos"), amt, res[-60:]))
        json.dump(reg, open(f, "w"), indent=1); time.sleep(0.4)
    if LIVE: json.dump(reg, open(f, "w"), indent=1)
