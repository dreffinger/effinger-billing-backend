# PLAIN ENGLISH (Send the never-billed hospital visits held for their admission date - William 11/19/2026)
# Decides: Nothing. The feed-order sweep held these never-billed hospital visits because the feed's admission dates disagreed
#          inside a stay or sat after the visit. William 11/19/2026 (chat): "i am now discharging from hospital hca to rehab hca
#          inpatient rehab so there will be some 99223 admission dates after follow up dates which will be valid" - so the
#          standing Claim Inspector rule decides each visit on its own: admission date = the most recent initial hospital visit
#          (99221-99223) on or before the visit. For every visit listed here: when its admission date differs from that rule the
#          date is written (updextrainsinfo hospitalizationfrom - the import's proven call, resave.restore_admit); then the
#          visit's insurance order is saved by the full-visit echo and ONE frequency-1 original claim is sent
#          (freq1_visit.reroute). A visit with a bill date or a payment is refused - these are never-billed visits only.
# Never touches: visits already billed, codes, plans, balances.
# Usage: python3 admit_send_1119.py [--live]     Register: registers/admit_send_1119.json
import amd, resave, freq1_visit, dx_primary_fix, json, sys, os, re, time
LIVE = "--live" in sys.argv; amd.login_cached()
rev = json.load(open("admit_review_1119.json")); f = "registers/admit_send_1119.json"; reg = json.load(open(f)) if os.path.exists(f) else {}
def mdy(d8): return "%s/%s/%s" % (d8[4:6], d8[6:8], d8[:4])
for pid, rows in rev.items():
    for r in rows:
        if r["list"] or r["billdate"] or float(r["paid"] or 0): continue          # never-billed visits only
        vid, cid = r["vid"], r["cid"]; want = mdy(r["rule_admit"]) if r["rule_admit"] else ""
        if "204" in str(reg.get(vid, "")): print("v%s already sent" % vid); continue
        st = dx_primary_fix.live_state(pid, vid)
        if any(c["pays"] for c in st): print("v%s SKIP payment posted" % vid); continue
        vis, pat, allc = resave.visit_charges(cid); now = resave.admit_of(vis); msg = "admission %s ok" % now
        if want and now != want:
            if not LIVE: msg = "DRY admission %s -> %s" % (now, want)
            else:
                done, bad = resave.restore_admit(vid, allc, want); time.sleep(0.4)
                vis, pat, allc = resave.visit_charges(cid); msg = "admission %s -> %s (%s%s)" % (now, resave.admit_of(vis), done, " FAULT %s" % bad if bad else "")
                if bad or resave.admit_of(vis) != want: reg[vid] = "NOT sent - " + msg; print("pat%s v%s %s" % (pid, vid, reg[vid])); continue
        res = freq1_visit.reroute(vid, cid, r["insorder"] or "1", None, dry=not LIVE)
        reg[vid] = (msg + " | " + res)[-200:]; print("pat%s v%s %s %s | %s | %s" % (pid, vid, r["dos"], r["cpt"], msg, res[-110:])); time.sleep(0.4)
        if LIVE: json.dump(reg, open(f, "w"), indent=1)
