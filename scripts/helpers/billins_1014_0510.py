# PLAIN ENGLISH (Unbilled 'Bill Insurance = No' repair, 1 AM ET 10/14/2026 run 2026-10-14T0510Z)
# Decides: nothing new. The 10/13 patient-balance chat found coverage on four self-pay charts (17469549 Medicaid, 23177 Medicare+Medicaid,
#   24716 Medicare, 24197 Medicare), added the plans and queued 66 visits - but every charge on them still carries billins="0" (self-pay),
#   so the Unbilled column holds them 'Bill Insurance = No at charge level and charge has insurance balance'. This helper echoes each visit
#   in full (resave.visit_charges - every live charge, the void trap) with billins="1" on every charge, force=1, nothing else changed,
#   then releases the Unbilled row (hideunbillablevisits). A visit whose insorder is empty is left (printed) - it needs the plan order first.
# Never touches: payments, write-offs, diagnoses, insurance plans, the claim frequency; no rebill (the chat already queued the claims).
#   python3 billins_1014_0510.py            # dry: prints each visit's charges, billins, finclass, insorder
#   python3 billins_1014_0510.py --live     # register registers/billins_1014_0510.json
import amd, resave, payreasons, json, re, sys, time
LIVE = "--live" in sys.argv; S = "2026-10-14T0510Z"
amd.login_cached()
scan = json.load(open("scan_2026-10-14T0510Z/summary_before.json"))
rows = [r for r in scan["unbilled"] if any("Bill Insurance" in e for e in r["_errs"])]
print("rows:", len(rows), "charts:", sorted({r["patientid"] for r in rows}))
reg = {"stamp": S, "live": LIVE, "done": [], "left": [], "failed": []}
for r in rows:
    vid = r["id"]; cid = r["_chgs"][0]["id"]
    vis, pat, allc = resave.visit_charges(cid)
    info = [(c.get("id"), c.get("billins"), c.get("finclasscode"), c.get("insbalance")) for c in allc]
    if not (vis.get("insorder") or "").strip():
        print("LEFT no insorder", vid, "pat" + r["patientid"], info); reg["left"].append((vid, r["patientid"], "no insorder")); continue
    if all(c.get("billins") == "1" for c in allc):
        print("already billins=1", vid, info); res = (True, "already 1")
    elif not LIVE:
        print("DRY", vid, "pat" + r["patientid"], "insorder", vis.get("insorder"), info); continue
    else:
        chg = ""
        for c in allc:
            a = {"id": c.get("id")}
            for f in resave.CHG_FIELDS:
                if c.get(f) is not None: a[f] = c.get(f)
            a["billins"] = "1"
            chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
        va = dict(vis.attrib); va["force"] = "1"
        x = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1",
                     "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                     "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
        time.sleep(0.8)
        if "Fault" in x:
            print("FAULT", vid, x[:200]); reg["failed"].append((vid, x[:200])); continue
        v2, p2, c2 = resave.visit_charges(cid)
        ok = len(c2) == len(allc) and all(c.get("billins") == "1" for c in c2)
        res = (ok, "resave %d charges, billins now %s" % (len(c2), [c.get("billins") for c in c2]))
        print("resave", vid, res)
        if not ok: reg["failed"].append((vid, res[1])); continue
    if LIVE:
        ok2, msg = payreasons.release_visit(vid); print("  release", vid, ok2, msg[:80])
        reg["done"].append((vid, r["patientid"], res[1], ok2))
json.dump(reg, open("registers/billins_1014_0510%s.json" % ("" if LIVE else "_dry"), "w"), indent=1)
print("done", len(reg["done"]), "left", len(reg["left"]), "failed", len(reg["failed"]))
