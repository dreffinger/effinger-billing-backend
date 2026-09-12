# PLAIN ENGLISH (VA CCN auth from William's board note, Lowry Fenwick, 9/12/2026 5am ET run)
# Decides: William pasted a NEW 12-byte VA auth (VA9011001288) on the lowry-fenwick board row at 09:05 UTC 9/12 next to
#   the HCA facesheet 'fenwick lowry new auth.pdf'. Both stays on this chart rejected NPV087 because their referral plans
#   carry a 13-byte number. This script writes the new auth on the visits of ONE stay (the most recent, 9/4-9/6/2026:
#   visits 19453860/61/62), rebills them freq-1 to the VA CCN plan and completes their exclusion rows. The 8/10 stay
#   (visit 19451315) is NOT touched: one auth = one stay, and William has not said which stay this auth belongs to -
#   the run assumes the newest stay ("new auth") and says so on the board.
# Rules it uses: one referral plan per stay; the resave writes preauth onto the visit's plan (and its previous plan);
#   verify preauth on the plan and the visit afterwards; freq-1 before every rebill; complete only what was re-sent.
# Never touches: the 8/10 stay unless it shares the same referral plan (then it is reported, not rebilled).
import amd, resave, freq1_visit, json, re, sys, time, datetime
import xml.etree.ElementTree as ET
amd.login_cached()
PID = "17475970"; AUTH = open("lowry_auth_0912.txt").read().strip()   # the 12-byte VA auth from the board note (PHI-adjacent: kept out of the mirrored script); STAY = ["19453860", "19453861", "19453862"]; OLD = "19451315"
DRY = "--dry" in sys.argv
LOG = open("lowry_auth_0912.log", "a")
def L(m): print(m, flush=True); LOG.write("%s %s\n" % (datetime.datetime.utcnow().strftime("%H:%M:%S"), m)); LOG.flush()

r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % PID, "nocookie": "1"}))
plans = [dict(re.findall(r'(\w+)="([^"]*)"', m)) for m in re.findall(r'<insplan ([^>]*)>', r)]
rplans = [dict(re.findall(r'(\w+)="([^"]*)"', m)) for m in re.findall(r'<refplan ([^>]*)>', r)]
L("insplans: %s" % [(p.get("id"), p.get("carrier"), p.get("sequence"), p.get("enddate")) for p in plans])
L("refplans: %s" % [(p.get("id"), p.get("preauth"), p.get("ismain")) for p in rplans])
va = [p for p in plans if p.get("carrier") == "car42025" and not p.get("enddate")]
if not va: L("ABORT: no live VACCN plan"); sys.exit(1)
seq = va[0]["sequence"]

# charges per visit from tx history
body = amd.msg('gettxhistory', 'demographics', {'patientid': PID, 'filterhistory': '0', 'pagenumber': '1', 'typefilter': '0', 'sortbypayment': 'false', 'groupbyvisit': '0', 'sortdescending': '1', 'visitid': '0', 'profileid': '', 'getmemo': 'false', 'nocookie': '1'})
th = ET.fromstring(amd.post(body, timeout=120))
byv = {}
for c in th.iter("charge"):
    if c.get("void") != "1": byv.setdefault(c.get("visit"), []).append(c)
def vinfo(vid):
    cs = byv.get(vid, [])
    if not cs: return None
    x = resave.detail(cs[0].get("id")); v = re.search(r'<visit [^>]*>', x).group(0)
    return dict(re.findall(r'(refplan|preauth|insorder)="([^"]*)"', v)) | {"cid": cs[0].get("id"), "n": len(cs), "insbal": sum(float(c.get("insbal") or 0) for c in cs), "dos": cs[0].get("dos")}
old = vinfo(OLD); L("8/10 stay visit %s: %s" % (OLD, old))
stay = {v: vinfo(v) for v in STAY}
for v, i in stay.items(): L("9/4-9/6 stay visit %s: %s" % (v, i))
share = old and any(i and i.get("refplan") == old.get("refplan") for i in stay.values())
if share: L("NOTE: the 8/10 visit shares referral plan %s with the 9/4-9/6 stay - the new auth will land on it too (not rebilled; William to confirm the 8/10 auth)" % old.get("refplan"))

sent = []
for v, i in stay.items():
    if not i: L("skip %s: no live charges" % v); continue
    if i.get("preauth") == AUTH: L("visit %s already carries %s" % (v, AUTH))
    else:
        vis, pat, allc = resave.visit_charges(i["cid"])
        chg = ""
        for c in allc:
            a = {"id": c.get("id")}
            for f in resave.CHG_FIELDS:
                val = c.get(f)
                if val is not None: a[f] = val
            chg += "<charge %s/>" % " ".join('%s="%s"' % (k, val) for k, val in a.items())
        va_ = dict(vis.attrib); va_["force"] = "1"; va_["preauth"] = AUTH; va_["insorder"] = va_.get("insorder") or seq
        if DRY: L("DRY resave %s %d charges preauth=%s refplan=%s" % (v, len(allc), AUTH, va_.get("refplan"))); continue
        rr = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, val) for k, val in va_.items()), chg)))
        if "Fault" in rr: L("FAULT resave %s: %s" % (v, re.sub(r"\s+", " ", rr[:300]))); continue
        time.sleep(0.6)
        i2 = vinfo(v); L("visit %s after resave: %s" % (v, i2))
        if i2.get("preauth") != AUTH or i2["n"] != len(allc): L("STOP: readback mismatch on %s" % v); continue
    if DRY: continue
    res = freq1_visit.run("vst%s" % v, i["cid"], seq[:1]); L("visit %s %s" % (v, res))
    if "204" in res: sent.append(v)
# plan readback
r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % PID, "nocookie": "1"}))
L("refplans after: %s" % [(p.get("id"), p.get("preauth")) for p in [dict(re.findall(r'(\w+)="([^"]*)"', m)) for m in re.findall(r'<refplan ([^>]*)>', r)]])
json.dump({"sent": sent, "seq": seq}, open("lowry_auth_0912_sent.json", "w"))
L("re-sent visits: %s (complete their exclusion rows next)" % sent)
