# PLAIN ENGLISH (1am ET 9/20/2026 run, 2026-09-20T0510Z): William's board note 04:56Z on row ellery-hollis-17477530 - "unvoid them and apply to the correct place".
# Decides: chart pat17477530 - the 9/2, 9/3 and 9/4/2026 HCA 99233 visits (19453715 / 19453774 / 19453755) whose only charge was VOIDED
#   with no live replacement. (1) tries the reverse of the proven void call ONCE (action=void class=void <charge void="0"/>) - if AMD
#   accepts it the original charge id comes back live (and the ERA line on check 1051714 can match it); otherwise re-enters the charge
#   on the same visit with identical attributes (the restore_charge.py recipe, without a live sibling: chargelist = the new charge only),
#   insorder 1,2 (Medicare first, Cigna HealthSpring second - the chart's other visits), onhcfa 1. (2) 9/2 line: Medicare ERA 819814877
#   paid $85.46 - posts it through the ERA Center Post button (era_post.post_check, FORCE_VISITS) so the CARCs travel with it; falls
#   back to manual_post (pay 85.46 + WOINS 52.74, check 819814877) if the Post button refuses. (3) 9/3 + 9/4: never billed - frequency 1
#   original claim to Medicare seq 1. Register: registers/ellery_0920_0510.json
# Never touches: the chart's other visits, any payment already posted.
import amd, resave, era_post, manual_post, freq1_visit, txh, json, re, time, sys
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv
amd.login_cached()
PID = "17477530"
V = [("19453715", "23364598", "09/02/2026"), ("19453774", "23364669", "09/03/2026"), ("19453755", "23364648", "09/04/2026")]
reg = {"stamp": "2026-09-20T0510Z", "visits": []}
def L(m): print(m, flush=True)
def live_charges(vid):
    return [c for c in txh.fetch("pat" + PID).iter("charge") if c.get("visit") == vid and c.get("void") != "1" and not (c.get("fee") or "").startswith("-")]
unvoid_works = None
for vid, vcid, dos in V:
    rec = {"vid": vid, "void_cid": vcid, "dos": dos, "steps": []}
    def S(m): rec["steps"].append(m); L("v%s %s" % (vid, m))
    lc = live_charges(vid)
    if lc: S("already has a live charge %s - nothing to restore" % [c.get("id") for c in lc]); rec["cid"] = lc[0].get("id"); reg["visits"].append(rec); continue
    if DRY: S("DRY would restore"); reg["visits"].append(rec); continue
    newcid = None
    if unvoid_works is not False:
        # ONE probe of the reverse void shape (not in the registry before this run)
        r = amd.post(amd.msg("void", "void", {"patientid": "pat" + PID, "nocookie": "1"}, '<patient id="pat%s"><charge id="%s" void="0"/></patient>' % (PID, vcid)))
        ok = 'success="1"' in r and "Fault" not in r
        time.sleep(0.8); lc = live_charges(vid)
        S("unvoid probe (void=0): success=%s live after=%s resp=%s" % (ok, [c.get("id") for c in lc], re.sub(r"\s+", " ", r)[:160]))
        if lc and lc[0].get("id") == vcid: unvoid_works = True; newcid = vcid
        else: unvoid_works = False
    if not newcid:
        rt = ET.fromstring(resave.detail(vcid)); vis = rt.find(".//visit"); pat = rt.find(".//patient")
        vc = [c for c in rt.iter("charge") if c.get("id") == "charge" + vcid][0]
        b = {}
        for f in resave.CHG_FIELDS:
            if vc.get(f) is not None: b[f] = vc.get(f)
        fee = vc.get("fee") if vc.get("fee") not in (None, "0", "0.00") else "160.00"
        b.update({"fee": fee, "insbalance": fee, "patbalance": "0.00", "insportion": fee, "patportion": "0.00"})
        chg = "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in b.items())
        va = dict(vis.attrib); va.update({"force": "1", "insorder": "1,2", "onhcfa": "1"})
        r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
            "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
        time.sleep(0.8); lc = live_charges(vid)
        S("re-enter charge (restore recipe): %s live after=%s" % ("FAULT " + re.sub(r"\s+", " ", r)[:200] if "Fault" in r else "ok", [(c.get("id"), c.get("proccode"), c.get("insbal")) for c in lc]))
        if lc: newcid = lc[0].get("id")
    if not newcid: S("RESTORE FAILED - left as is"); reg["visits"].append(rec); continue
    rec["cid"] = newcid
    v2, p2, c2 = resave.visit_charges(newcid); S("visit now insorder=%s onhcfa=%s charges=%d" % (v2.get("insorder"), v2.get("onhcfa"), len(c2)))
    if vid == "19453715":
        # Medicare's $85.46 on ERA 819814877 (check entry 1051714): Post button first
        chk = [c for c in era_post.checks() if str(c["id"]) == "1051714"]
        posted = False
        if chk:
            era_post.FORCE_VISITS.clear(); era_post.FORCE_VISITS.add(int(vid))
            n, tot = era_post.post_check(chk[0]); time.sleep(1.5)
            pays = [(p.get("id"), p.get("amount"), p.get("checknumber"), p.get("void")) for c in live_charges(vid) for p in c.iter("payment")]
            posted = any("819814877" in (p[2] or "") and p[3] != "1" for p in pays)
            S("ERA Post button FORCE visit: n=%s $%.2f; payments on charge now %s -> posted=%s" % (n, tot, pays, posted))
        if not posted:
            dep = chk[0]["depositdate"][:10] if chk else "2026-09-22"
            y, m, d = dep.split("-") if "-" in dep else (dep[6:10], dep[0:2], dep[3:5])
            ok, msg = manual_post.post(newcid, "FLO02", 85.46, 52.74, "WOINS", checknumber="819814877", depositdate="%s/%s/%s" % (m, d, y), note="ERA 1051714 manual post 2026-09-20T0510Z (restored 9/2 charge per William)")
            time.sleep(0.8); lc = live_charges(vid)
            S("manual_post 85.46 + WOINS 52.74 check 819814877 -> ok=%s %s; insbal now %s" % (ok, str(msg)[:120], [c.get("insbal") for c in lc]))
    else:
        S("freq1 -> %s" % freq1_visit.run(vid, newcid, 1))
    reg["visits"].append(rec); time.sleep(0.5)
reg["unvoid_probe_works"] = unvoid_works
json.dump(reg, open("registers/ellery_0920_0510.json", "w"), indent=1)
L("=== melvin done; unvoid probe works=%s" % unvoid_works)
