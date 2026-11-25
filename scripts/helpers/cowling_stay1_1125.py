# PLAIN ENGLISH (chart 17478013 - the FIRST hospital stay of 10/05-10/12/2026 gets its own referral plan and its own VA CCN authorization)
# Decides: nothing. William said 'use it' (board card, 11/25/2026 08:05Z) for the authorization his 11/25 06:43Z sheet carries
#   (the 12-character part before the slash) on the 8 visits of the 10/05-10/12/2026 admission ($1,430).
# The chart holds TWO referral plans: rplan18462365 (Effinger, rprov13) - the second stay's plan, auth VA9011260694, every visit of
#   both stays points at it - and rplan18462897, a blank plan AMD made on 11/25 with the third referring provider (rprov14), now MAIN,
#   which the 11/25 resaves also stamped with VA9011260694 (the known side effect: a resave with preauth= writes onto the previous plan).
# addreferralplan cannot insert a second Effinger plan (SHARED_LESSONS 11/25: same refprov = get-or-return), so the blank plan is
#   used for the first stay, in this order:
#   (1) REST PUT on rplan18462897: referring provider 14 -> 13 (Effinger), so the claim's referring provider stays Effinger, and its
#       authorization = the first stay's number (refplan_rest.put / set_preauth - the Referral Plans screen's own Save, captured 10/5);
#   (2) per visit of the first stay: FULL-visit echo resave (every live charge, resave.CHG_FIELDS - the void trap) with
#       refplan=rplan18462897 preauth=<first-stay auth> insorder=1 force=1, read back (refplan + charge count);
#   (3) the side effect undone: rplan18462365's authorization restored to VA9011260694 (refplan_rest.set_preauth), read back;
#   (4) both plans read back by XML (getdemographic) - each stay's plan carries its own number - then ONE frequency-1 reset + ONE
#       chargerebill per first-stay visit (freq1_visit.run, the deceased guard inside it).
# --dry (default) reads and prints only. Register registers/cowley_stay1_2026-11-25T0809Z[_dry].json. Never touches the second
#   stay's visits, balances, codes, or any other chart.
# Usage: python3 cowley_stay1_1125.py --auth <first-stay auth> [--live]
import amd, resave, freq1_visit, refplan_rest, re, json, sys, time, copy
import xml.etree.ElementTree as ET
LIVE = "--live" in sys.argv; S = "2026-11-25T0809Z"
AUTH = sys.argv[sys.argv.index("--auth") + 1] if "--auth" in sys.argv else None
if not AUTH or not re.fullmatch(r"(VA|UC)\d{10}", AUTH): sys.exit("--auth must be VA/UC + 10 digits (12 characters)")
PID = "17478013"; STAY1_PLAN = "18462897"; STAY2_PLAN = "18462365"; STAY2_AUTH = "VA9011260694"; SEQ = "1"
VISITS = [("19457321", "23369178"), ("19457281", "23369138"), ("19457280", "23369137"), ("19457476", "23369383"),
          ("19457471", "23369378"), ("19457529", "23369457"), ("19457519", "23369447"), ("19457647", "23369559")]
amd.login_cached()
def refplans():
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": PID, "nocookie": "1"}), timeout=120)
    return {a.get("id"): {k: a.get(k) for k in ("ismain", "refprov", "preauth")} for a in
            (dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<refplan [^>]*/?>', t))}
def resave_visit(cid, rplan, auth, order):
    x = resave.detail(cid); root = ET.fromstring(x)
    pat = root.find(".//patient"); vis = root.find(".//visit")
    _, _, allc = resave.visit_charges(cid)
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None: a[f] = v
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, amd.esc(v)) for k, v in a.items())
    va = dict(vis.attrib); va["refplan"] = rplan; va["preauth"] = auth; va["insorder"] = order; va["force"] = "1"
    vs = " ".join('%s="%s"' % (k, amd.esc(v)) for k, v in va.items())
    body = amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg))
    r = amd.post(body); time.sleep(0.8)
    v2 = ET.fromstring(resave.detail(cid)).find(".//visit")
    live_after = len(resave.visit_charges(cid)[2])
    return ("Fault" not in r), v2.get("refplan"), v2.get("insorder"), len(allc), live_after, (re.search(r"<description>([^<]*)", r).group(1)[:160] if "Fault" in r else "")
reg = {"stamp": S, "live": LIVE, "pid": PID, "auth_stay1": AUTH, "plans_before": refplans(), "visits_before": {}, "steps": []}
print("plans before:", reg["plans_before"])
p1 = refplan_rest.get(STAY1_PLAN); p2 = refplan_rest.get(STAY2_PLAN)
for p in (p1, p2):
    assert str(p.get("patientid")) == PID, "plan not on the chart"
print("REST stay1 plan: by/to referring provider %s/%s auths %s" % (p1.get("byreferringproviderid"), p1.get("toreferringproviderid"), [a.get("authorizationnumber") for a in p1.get("authorizations") or []]))
print("REST stay2 plan: by/to referring provider %s/%s auths %s" % (p2.get("byreferringproviderid"), p2.get("toreferringproviderid"), [a.get("authorizationnumber") for a in p2.get("authorizations") or []]))
for vid, cid in VISITS:
    v, _, allc = resave.visit_charges(cid)
    reg["visits_before"][vid] = {"refplan": v.get("refplan"), "insorder": v.get("insorder"), "charges": len(allc), "insbalance": [c.get("insbalance") for c in allc]}
    print("  v%s refplan=%s insorder=%s charges=%d insbal=%s" % (vid, v.get("refplan"), v.get("insorder"), len(allc), [c.get("insbalance") for c in allc]))
if not LIVE:
    print("DRY - would: (1) PUT rplan%s referring provider 13 + auth %s; (2) resave %d visits onto it with %s; (3) restore rplan%s auth %s; (4) verify; (5) freq1 rebill seq %s each" % (STAY1_PLAN, AUTH, len(VISITS), AUTH, STAY2_PLAN, STAY2_AUTH, SEQ))
    json.dump(reg, open("registers/cowley_stay1_%s_dry.json" % S, "w"), indent=1); sys.exit(0)
# (1) the blank plan becomes an Effinger plan carrying the first stay's number
body = refplan_rest._ui_body(p1)
body["byreferringproviderid"] = 13; body["toreferringproviderid"] = 13
for a in body["authorizations"]: a["authorizationnumber"] = AUTH
body["authorization"] = copy.deepcopy(body["authorizations"][0])
code, resp = refplan_rest.put(body); p1b = refplan_rest.get(STAY1_PLAN)
step1 = {"http": code, "by": p1b.get("byreferringproviderid"), "to": p1b.get("toreferringproviderid"), "auths": [a.get("authorizationnumber") for a in p1b.get("authorizations") or []]}
reg["steps"].append({"put_stay1_plan": step1}); print("step 1 PUT stay1 plan ->", step1, "xml:", refplans().get("rplan" + STAY1_PLAN))
if step1["by"] != 13 or step1["auths"] != [AUTH]:
    print("STOP - the plan did not take the referring provider / auth as asked; nothing else written")
    json.dump(reg, open("registers/cowley_stay1_%s.json" % S, "w"), indent=1); sys.exit(2)
# (2) repoint the first stay's visits
ok_all = True
for vid, cid in VISITS:
    ok, rp, io, n_sent, n_after, err = resave_visit(cid, "rplan" + STAY1_PLAN, AUTH, SEQ)
    line = {"ok": ok, "refplan": rp, "insorder": io, "charges_sent": n_sent, "charges_after": n_after, "err": err}
    reg["steps"].append({"resave": vid, **line}); print("  resave v%s" % vid, line)
    if not (ok and rp == "rplan" + STAY1_PLAN and n_after == n_sent): ok_all = False
    time.sleep(0.4)
# (3) undo the side effect on the second stay's plan
r3 = refplan_rest.set_preauth(STAY2_PLAN, PID, STAY2_AUTH); reg["steps"].append({"restore_stay2_plan": r3}); print("step 3 restore stay2 plan ->", r3)
# (4) verify both plans by XML
after = refplans(); reg["plans_after"] = after; print("plans after:", after)
good = (after.get("rplan" + STAY1_PLAN, {}).get("preauth") == AUTH and after.get("rplan" + STAY2_PLAN, {}).get("preauth") == STAY2_AUTH)
if not (good and ok_all):
    print("STOP - plans or visits not as asked; no rebill"); json.dump(reg, open("registers/cowley_stay1_%s.json" % S, "w"), indent=1); sys.exit(2)
# (5) one frequency-1 reset + one chargerebill per first-stay visit
for vid, cid in VISITS:
    res = freq1_visit.run(vid, cid, SEQ); reg["steps"].append({"rebill": vid, "result": str(res)}); print("  rebill v%s -> %s" % (vid, res)); time.sleep(0.4)
json.dump(reg, open("registers/cowley_stay1_%s.json" % S, "w"), indent=1); print("register written")
