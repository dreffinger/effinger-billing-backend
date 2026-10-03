# PLAIN ENGLISH (11 AM ET 10/3 slot, run 2026-10-03T1510Z): ERA check 1052946 (RET01 Railroad Medicare, $0) carries ONE denial-only
#   line: pat12182505 v19452655 CCM 99487+99489 8/23/2026 ($315) PR-B9 'patient is enrolled in a hospice' (MA01). William's standing
#   hospice rule (9/20/2026, rules.md): add GV (mcode713) to every live charge of the visit with a full-visit echo and rebill it frequency 1
#   to the chart's Medicare sequence - never written off, never held. The chart's live Medicare plan is RET01 (car6080) seq 3 (FLO02 ended
#   9/20/2025); the visit was last billed to RET01 9/22/2026, no payment > 0 on either charge.
# Decides: (1) guard - skip if a non-void payment > 0 is on the visit; (2) gv_rebill.add_gv (full-visit echo); (3) freq1_visit.run seq 3;
#   (4) registers (hospice_gv_register.json as a JSON line, era_manual_register.json); (5) DISMISS check 1052946 (no postable money -
#   POST /api/era/checks/dismiss, the captured shape) and re-read GET /api/era/checks. --dry = read + plan only.
# Never touches: any other chart; the Florida Blue takeback check 1052906 (William's decision).
import amd, txh, gv_rebill, freq1_visit, era_post, json, sys, time, requests, re
DRY = "--dry" in sys.argv; STAMP = "2026-10-03T1510Z"; CID = 1052946
PID, VID, SEQ = "12182505", "19452655", "3"
amd.login_cached()
root = txh.fetch("pat" + PID)
chs = [c for c in root.iter("charge") if c.get("visit") == VID and c.get("void") != "1" and not (c.get("fee") or "").startswith("-")]
print("live charges:", [(c.get("id"), c.get("proccode"), c.get("modcodes"), c.get("fee"), c.get("carrier"), c.get("billdate")) for c in chs])
paid = [(p.get("id"), p.get("amount"), p.get("checknumber")) for c in chs for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
print("payments > 0:", paid)
rec = {"stamp": STAMP, "live": not DRY, "pid": PID, "vid": VID, "checkid": CID, "carc": "PR-B9 MA01 (RET01 Railroad Medicare)", "seq": SEQ,
       "charges": [{"id": c.get("id"), "proc": c.get("proccode"), "mods": c.get("modcodes") or "", "fee": c.get("fee")} for c in chs], "payments": paid}
if paid or not chs:
    rec["result"] = "skipped - payment posted or no live charge"; print(rec["result"])
elif DRY:
    rec["result"] = "DRY - would add GV to %d charges and freq-1 rebill seq %s" % (len(chs), SEQ); print(rec["result"])
else:
    g = gv_rebill.add_gv(chs[0].get("id")); print("add GV ->", g); rec["add_gv"] = g
    if g.startswith("FAULT"):
        rec["result"] = "fault-gv"
    else:
        time.sleep(0.6)
        f = freq1_visit.run(VID, chs[0].get("id"), SEQ); print("rebill ->", f); rec["rebill"] = f
        rec["result"] = "GV added + frequency-1 rebill seq %s" % SEQ if "204" in f else "rebill-" + f[:60]
        root2 = txh.fetch("pat" + PID)
        rec["mods_after"] = [(c.get("id"), c.get("modcodes"), c.get("insbilled")) for c in root2.iter("charge") if c.get("visit") == VID and c.get("void") != "1"]
        print("after:", rec["mods_after"])
    with open("registers/hospice_gv_register.json", "a") as fh: fh.write("\n" + json.dumps(rec))
    em = json.load(open("registers/era_manual_register.json"))
    for c in chs:
        em.append({"checkid": str(CID), "checkclaimid": 15443726, "visitid": VID, "chargedetailid": c.get("id"), "cpt": c.get("proccode"),
                   "outcome": "denial-only PR-B9 hospice - GV added + freq-1 rebill seq %s (%s)" % (SEQ, rec["result"]), "pay": 0.0, "wo": 0.0, "wocode": "", "when": STAMP})
    json.dump(em, open("registers/era_manual_register.json", "w"), indent=1)
    if rec["result"].startswith("GV added"):
        r = requests.post(era_post.API + "/era/checks/dismiss", headers=era_post.H(), data=json.dumps(str(CID)), timeout=60)
        print("dismiss %s -> HTTP %s %s" % (CID, r.status_code, r.text[:120])); rec["dismiss"] = r.status_code
        time.sleep(1.0)
        after = era_post.checks(); print("ERA unposted after:", [(c.get("id"), c.get("unpostedamount")) for c in after])
        json.dump({"after": after}, open("registers/era_checks_after_%s.json" % STAMP, "w"), indent=1, default=str)
json.dump(rec, open("registers/act_%s.json" % STAMP + (".dry" if DRY else ""), "w"), indent=1)
