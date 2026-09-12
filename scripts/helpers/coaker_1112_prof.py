# PLAIN ENGLISH (Orme Simply rebill under Effinger, 9/12 7am ET run): William 08:50 UTC on board row orme-cotterell-simply-npi:
# "rebill these with effinger 122 npi as the rendering provider". The rendering provider on an AMD visit is its profile:
# prof15 = Garcia (the 7 rejected visits), prof13 = Effinger (her Jun-Aug 2026 visits that were accepted). Resave each of the
# 7 excluded visits with profile=prof13 (full charge echo), freq-1 rebill the Simply sequence (2), complete the exclusions.
# Never touches: her other visits, balances, plans.
import amd, resave, era_post, freq1_visit, re, time, json
LOG = open("coaker_1112_prof.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
s = json.load(open("scan_0912/summary_before.json"))
rows = [(rid, r) for rid, rs in s["exclusions"].items() for r in rs if r["patientid"] == "17474046"]
L("coaker rows %d" % len(rows)); amd.login_cached(); batch = era_post.batch()
done = {}
for rid, r in rows:
    vid = r["id"]; cid = r["_chgs"][0].get("id")
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; old = va.get("profile"); va["profile"] = "prof13"
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    x = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "batchid": str(batch), "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg)))
    if "Fault" in x: L("v%s FAULT %s" % (vid, re.sub(r"\s+", " ", x[:200]))); continue
    time.sleep(0.8); v2, p2, c2 = resave.visit_charges(cid)
    L("v%s profile %s -> %s live=%d/%d insorder=%s" % (vid, old, v2.get("profile"), len(c2), len(allc), v2.get("insorder")))
    if v2.get("profile") != "prof13" or len(c2) != len(allc): L("  verify failed - not rebilled"); continue
    res = freq1_visit.run(vid, cid, 2); L("  " + res); time.sleep(0.4)
    if "204" in res: done.setdefault(rid, []).append((vid, r["claimid"]))
for rid, lst in done.items():
    x = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": rid, "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in lst)))
    L("hideexclusions %s x%d -> %s" % (rid, len(lst), "ok" if "Fault" not in x else re.sub(r"\s+", " ", x[:200])))
json.dump(done, open("coaker_1112_results.json", "w"))
