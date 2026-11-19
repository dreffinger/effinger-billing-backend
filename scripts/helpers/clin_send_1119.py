# PLAIN ENGLISH (Send the never-billed feed visits William keeps under his own number - 11/19/2026)
# Decides: Nothing. These never-billed feed visits were entered under the physician while the feed message names the nurse
#          practitioner; the 11/10 plan was to move them to her. William 11/19/2026 in chat, asked who they bill under:
#          "bill them under me". So nothing about the clinician changes: each visit listed in ORDER (visit -> insurance order,
#          every plan checked active on the visit's own date by a Stedi eligibility check bought this run) gets its first
#          diagnosis checked, its insurance order saved by the full-visit echo and ONE frequency-1 original claim
#          (freq1_visit.reroute). A visit with a bill date or a payment is refused.
# Never touches: the clinician, codes, plans, balances, any visit not listed.
# Usage: python3 clin_send_1119.py [--live]     Register: registers/clin_send_1119.json
import amd, freq1_visit, dx_primary_fix, json, sys, os, time
ORDER = {"19459190": "1", "19459208": "1", "19459211": "1", "19459209": "1", "19459256": "1", "19459210": "1", "19459257": "1", "19459212": "1", "19459259": "1"}
LIVE = "--live" in sys.argv; amd.login_cached(); V = json.load(open("clin_send_1119_visits.json"))
f = "registers/clin_send_1119.json"; reg = json.load(open(f)) if os.path.exists(f) else {}
for vid, order in ORDER.items():
    v = V[vid]
    if "204" in str(reg.get(vid, "")): print("v%s already sent" % vid); continue
    if v["billdate"]: print("v%s SKIP billed %s" % (vid, v["billdate"])); continue
    st = dx_primary_fix.live_state(v["pid"], vid)
    if any(c["pays"] for c in st): print("v%s SKIP payment posted" % vid); continue
    vis, pat, allc, dxm = dx_primary_fix.visit_dx(v["cid"]); held = None
    for c in allc:
        codes = [dxm.get(d) for d in (c.get("diagcodes") or "").split(",") if d]
        act, _n = dx_primary_fix.plan(codes, None)
        if act != "ok": held = "%s first dx %s -> %s" % (c.get("id"), codes[:1], act)
    if held: reg[vid] = "HELD dx " + held; print("pat%s v%s HELD - %s" % (v["pid"], vid, held)); continue
    res = freq1_visit.reroute(vid, v["cid"], order, None, dry=not LIVE)
    reg[vid] = res[-160:]; print("pat%s v%s %s %s under %s | %s" % (v["pid"], vid, v["dos"], v["cpt"], vis.get("profile"), res[-150:])); time.sleep(0.4)
    if LIVE: json.dump(reg, open(f, "w"), indent=1)
