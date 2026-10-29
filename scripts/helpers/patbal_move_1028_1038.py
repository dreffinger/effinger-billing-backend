#!/usr/bin/env python3
# PLAIN ENGLISH (move uninsured visits to the patient balance and release them from Unbilled - ehpa Billing Button run 2026-10-28T1038Z)
# Decides: nothing. Applies William's 10/4/2026 board instruction on row alcott-alfie-17477183 ("no insurance, bill to patient and then
#   write off no pay") to the visits named on the command line, the same way the 10/4 session did its three (act_0310_1004.py step H):
#   the full-visit echo resave (resave.visit_charges - every live charge echoed, never a single charge) with each charge's open insurance
#   balance/portion moved to the patient side, then hideunbillablevisits hide=-1 (numeric visit id). Before it runs this run re-checked
#   the chart: Sunshine INACTIVE (ended 8/31/2026), Florida Medicaid 77027 INACTIVE as of 10/20/2026, Medicare MBILU by SSN = 72 (not a
#   Medicare beneficiary), no facesheet in the Drive folders, no Pam email, no drop. The WOBAD write-off follows the statement cycle (not here).
# Rules it uses: the void trap (full charge echo); a release only hides a row. Never touches: payments, write-offs, plans, claims.
# Usage: python3 patbal_move_1028_1038.py <patientid> <visitid> [<visitid> ...] [--live]      (dry by default)
# Register: registers/patbal_move_2026-10-28T1038Z[_dry].json
import amd, resave, txh, json, re, sys, time, datetime
LIVE = "--live" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
pid, vids = args[0], args[1:]
amd.login_cached()
out = {"stamp": "2026-10-28T1038Z", "live": LIVE, "pid": pid, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "visits": []}
root = txh.fetch(pid)
def first_cid(vid):
    for c in root.iter("charge"):
        if c.get("void") != "1" and re.sub(r"\D", "", c.get("visit") or "") == str(vid): return re.sub(r"\D", "", c.get("id"))
    return None
released = []
for vid in vids:
    cid = first_cid(vid)
    if not cid:
        print("v%s: no live charge found - skipped" % vid); out["visits"].append({"visit": vid, "result": "no live charge"}); continue
    vis, pat, allc = resave.visit_charges(cid); chg = ""; moved = 0.0; paid = False
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        if float(c.get("paid") or 0) != 0: paid = True
        ib = float(c.get("insbalance") or 0)
        if ib > 0:
            a["patbalance"] = "%.2f" % (float(c.get("patbalance") or 0) + ib); a["insbalance"] = "0.00"
            a["patportion"] = "%.2f" % (float(c.get("patportion") or 0) + float(c.get("insportion") or 0)); a["insportion"] = "0.00"; moved += ib
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    if paid:
        print("v%s: a payment is posted - left alone" % vid); out["visits"].append({"visit": vid, "result": "payment posted - skipped"}); continue
    if not LIVE:
        print("v%s DRY: move %.2f to patient (%d charges echoed) + release" % (vid, moved, len(allc))); out["visits"].append({"visit": vid, "cid": cid, "moved": moved, "charges": len(allc), "result": "dry"}); released.append(vid); continue
    va = dict(vis.attrib); va["force"] = "1"
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.8); x2 = resave.detail(cid); st = re.findall(r'id="charge\d+"[^>]*?insbalance="([^"]*)" patbalance="([^"]*)"', x2)
    ok = "Fault" not in r
    print("v%s: moved %.2f to patient -> %s %s" % (vid, moved, "ok" if ok else "FAULT " + re.sub(r"\s+", " ", r[:160]), st))
    out["visits"].append({"visit": vid, "cid": cid, "moved": moved, "charges": len(allc), "resave_ok": ok, "balances_after": st})
    if ok: released.append(vid)
rel = []
for v in released:
    if not LIVE: rel.append((v, "dry")); continue
    r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, '<visitlist><visit id="%s"/></visitlist>' % v))
    rel.append((v, ('success="1"' in r and "<Fault" not in r)))
print("release:", rel)
out["released"] = rel
json.dump(out, open("registers/patbal_move_2026-10-28T1038Z%s.json" % ("" if LIVE else "_dry"), "w"), indent=1)
