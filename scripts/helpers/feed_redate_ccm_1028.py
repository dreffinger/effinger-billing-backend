# PLAIN ENGLISH (William 10/28/2026 03:41 ET on the Pattern 24078 CCI holds: "re-date the CCM visit off the E/M day").
# Moves a CCM visit (99487/99489) from the SNF-visit day to the next day with no charge on the chart: full-echo resave of the
# CCM visit with the new visit date and each charge's begindate/enddate/aging (updvisitwithcharges force=1, same charge ids -
# a date edit, not a recode), verified by re-reading the detail; then the held 99309 visit is resaved so the inspector re-runs.
# Usage: python3 feed_redate_ccm_1028.py pat20729:vst19459282:10/23/2026 ...   (arg = chart:ccm visit:new date)
import amd, resave, txh, re, json, sys, time
import xml.etree.ElementTree as ET
amd.login_cached(); out = []
reg = json.load(open("registers/feed_import_1028.json")); byvis = {c["visit"]: c for c in reg["created"]}
for arg in sys.argv[1:]:
    pid, vid, newdate = arg.split(":")
    c = byvis[vid]; cid = re.sub(r"\D", "", c["charges"][0])
    vis, pat, allc = resave.visit_charges(cid)
    old = vis.get("date"); chg = ""
    for ch in allc:
        a = {"id": ch.get("id")}
        for f in resave.CHG_FIELDS:
            if ch.get(f) is not None: a[f] = ch.get(f)
        a["begindate"] = newdate; a["enddate"] = newdate; a["aging"] = newdate
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va["date"] = newdate
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1",
                 "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                 "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)), timeout=180)
    time.sleep(1.0)
    fault = re.search(r"<description>(.*?)</description>", r, re.S)
    v2, p2, c2 = resave.visit_charges(cid)
    after = [(x.get("id"), x.get("begindate"), x.get("proccode"), x.get("void")) for x in c2]
    rec = {"pid": pid, "visit": vid, "from": old, "to": newdate, "visit_date_after": v2.get("date"), "charges_after": after, "fault": fault.group(1)[:200] if fault else None,
           "ok": v2.get("date") == newdate and len(c2) == len(allc) and all(x[1] == newdate for x in after)}
    out.append(rec); print(rec)
json.dump(out, open("registers/feed_redate_ccm_1028.json", "w"), indent=1)
