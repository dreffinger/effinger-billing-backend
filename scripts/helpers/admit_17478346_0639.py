#!/usr/bin/env python3
# PLAIN ENGLISH (admission date on chart 17478346's two HCA visits, 06:39Z 11/9 run): the full-visit echo with hospfrom did not persist
#   on these feed-created visits (empty <extins/>), so write it the inspector way - updextrainsinfo hospitalizationfrom ONLY (never
#   hospitalizationto) per charge code, then the full-visit resave onhcfa=1 (void trap: every live charge echoed). Admission = 11/06/2026,
#   the stay's own 99223. Read back and print; no rebill (claims have not left yet). Register registers/admit_17478346_2026-11-09T0639Z.json
import amd, resave, re, json, time
amd.login_cached(); ADMIT = "11/06/2026"; out = []
for vid, cid in (("19460523", "23373229"), ("19460531", "23373237")):
    vis, pat, allc = resave.visit_charges(cid)
    codes = set()
    for c in allc:
        x = resave.detail(c.get("id").replace("charge", ""))
        pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', x)); codes.add(pm.get(c.get("proccode"), c.get("proccode")))
    for code in sorted(codes):
        r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"},
            '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, ADMIT)))
        print(vid, code, "updextrainsinfo ->", "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160]))
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va.update({"force": "1", "onhcfa": "1"})
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.8); v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    hf = ex.get("hospitalizationfrom") if ex is not None else None
    msg = "visit %s: live %d/%d insorder=%s onhcfa=%s hospfrom=%s%s" % (vid, len(c2), len(allc), v2.get("insorder"), v2.get("onhcfa"), hf, "" if "Fault" not in r else " RESAVE FAULT " + re.sub(r"\s+", " ", r[:160]))
    print(msg); out.append({"vid": vid, "cid": cid, "hospfrom": hf, "live": len(c2), "was": len(allc)})
json.dump({"stamp": "2026-11-09T0639Z", "pid": "17478346", "admit": ADMIT, "visits": out}, open("registers/admit_17478346_2026-11-09T0639Z.json", "w"), indent=1)
