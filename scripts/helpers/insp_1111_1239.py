# PLAIN ENGLISH (12:39Z 11/11 columns run): chart pat22322 - Claim Inspector Pattern 4531 (hospital E&M 99223/99233 at POS 13 ALF) on
#   v19460347 (11/04/2026 99223 + 99497 mod 25) and v19460343 (11/05/2026 99233). The 11/7 HCA census William dropped (census paper.pdf)
#   lists this patient as an inpatient at Capital Regional (attending Effinger), so the feed's SODALIS ALF location is wrong:
#   standing rule = facility fac29 (HCA FLORIDA CAPITAL HOSPITAL, POS 21), admission date = the 99223's DOS 11/04/2026
#   (hospitalizationfrom only, NEVER hospitalizationto), full-visit echo resave onhcfa=1, then re-list the batch for fresh ids.
# Decides: nothing beyond that rule. Never touches dx, modifiers, plans, payments.
#   python3 insp_1111_1239.py            # dry: reads only, prints what it would send
#   python3 insp_1111_1239.py --live     # writes; log insp_1111_1239.log
import amd, resave, re, sys, time, json
LIVE = "--live" in sys.argv
amd.login_cached()
LOG = open("insp_1111_1239.log", "a")
def L(m):
    print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
JOBS = [  # (visitid, anchor chargeid, cpts, hospfrom, tag)
    ("19460347", "23373019", ["99223", "99497"], "11/04/2026", "pat22322 11/04 99223+99497"),
    ("19460343", "23373013", ["99233"], "11/04/2026", "pat22322 11/05 99233"),
]
def extins(vid, cpt, hf):
    ch = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" '
          'payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (cpt, hf))
    if not LIVE: return "dry"
    r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"nocookie": "1", "visitid": "vst%s" % vid}, ch))
    return "ok" if "Fault" not in r and "error" not in r.lower()[:200] else r[:250]
def resave_hosp(cid):
    vis, pat, allc = resave.visit_charges(cid)
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None: a[f] = v
        a["pos"] = "21"
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va["onhcfa"] = "1"; va["facility"] = "fac29"
    body = amd.msg("updvisitwithnewcharges", "chargeentry",
                   {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1",
                    "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                   '<visit %s><chargelist>%s</chargelist></visit>' % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg))
    L("  visit %s charges %s was facility=%s insorder=%s onhcfa=%s" % (vis.get("id"), [(c.get("id"), c.get("proccode"), c.get("pos"), c.get("modcodes")) for c in allc], vis.attrib.get("facility"), vis.attrib.get("insorder"), vis.attrib.get("onhcfa")))
    if not LIVE: return "dry (would send %d charges, facility fac29, pos 21, onhcfa 1)" % len(allc)
    r = amd.post(body)
    return "ok" if "Fault" not in r else "FAULT " + re.sub(r"\s+", " ", r[:300])
for vid, cid, cpts, hf, tag in JOBS:
    for cpt in cpts:
        L("EXTINS %s %s %s -> %s" % (tag, cpt, hf, extins(vid, cpt, hf))); time.sleep(0.2)
    L("RESAVE %s -> %s" % (tag, resave_hosp(cid))); time.sleep(0.3)
if LIVE:
    time.sleep(1.5)
    b = amd.post(amd.msg("getclaiminspectorbatches", "chargeentry", {"nocookie": "1"}))
    L("BATCHES after: %s" % re.findall(r'<batch id="([^"]+)"', b))
    for bid in re.findall(r'<batch id="([^"]+)"', b):
        t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
        L("BATCH %s after: %s" % (bid, re.sub(r"\s+", " ", re.sub(r"<charge .*?/>", "", t))[:1200]))
    for vid, cid, cpts, hf, tag in JOBS:
        x = resave.detail(cid)
        L("VERIFY %s onhcfa=%s facility=%s pos=%s extins=%s" % (cid, (re.search(r'onhcfa="([^"]*)"', x) or [None, "?"])[1] if re.search(r'onhcfa="([^"]*)"', x) else "?", re.findall(r'facility="([^"]*)"', x)[:1], re.findall(r' pos="([^"]*)"', x)[:2], re.findall(r'<extins [^>]*hospitalizationfrom="[^"]*"', x)[:1]))
